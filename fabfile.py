# Run tasks from this file like this:
#
# fab -H hostname <taskname>
#
# Where "hostname" is defined in your ~/.ssh/config file.
#
# For example, to deploy the latest version of the crawler:
#
# fab -H hostname deploy
from io import StringIO

from fabric import task

SOURCE_PARENT = "/opt/cfpb"
SOURCE_REPO = "https://github.com/cfpb/crawsqueal.git"
SOURCE_DIRNAME = "crawsqueal"
SOURCE_ROOT = f"{SOURCE_PARENT}/{SOURCE_DIRNAME}"

CRAWL_DATABASE = "/var/tmp/crawl.sqlite3"

SYSTEMD_DIR = "/etc/systemd/system/"
SYSTEMD_SERVICE = "crawsqueal"
SYSTEMD_NAME = f"{SYSTEMD_SERVICE}.service"
SYSTEMD_PATH = f"{SYSTEMD_DIR}/{SYSTEMD_NAME}"

CRONTAB_NAME = "crawsqueal"
CRONTAB_DIR = "/etc/cron.d"
CRONTAB_PATH = f"{CRONTAB_DIR}/{CRONTAB_NAME}"


@task
def ls(conn):
    conn.run("ls")


@task
def clean(conn):
    conn.sudo(f"rm -rf {SOURCE_PARENT}")
    conn.sudo(f"rm -f {CRONTAB_PATH}")
    conn.sudo(f"systemctl stop {SYSTEMD_SERVICE}")
    conn.sudo(f"rm -f {SYSTEMD_PATH}")


@task
def deploy(conn):
    print("Cloning and configuring application source code")
    # Create the local directory structure.
    conn.sudo(f"mkdir -p {SOURCE_PARENT}")
    conn.sudo(f"chown -R {conn.user}:{conn.user} {SOURCE_PARENT}")

    # Clone or refresh the source code.
    with conn.cd(SOURCE_PARENT):
        conn.run(
            f"(test -d {SOURCE_DIRNAME} && cd {SOURCE_DIRNAME} && git pull)"
            f"|| (git clone {SOURCE_REPO} {SOURCE_DIRNAME}); "
        )

    # Build the viewer app and update any dependencies.
    with conn.cd(SOURCE_ROOT):
        conn.run("yarn && yarn build")
        conn.run("python3.8 -m venv venv")

        with conn.prefix("source venv/bin/activate"):
            conn.run("pip install -r requirements/base.txt")
            conn.run("pip install -r requirements/gunicorn.txt")

    # Configure gunicorn to run via systemd.
    print("Configuring gunicorn service")
    gunicorn_config = StringIO(
        f"""
[Unit]
Description=cf.gov crawler
After=network.target

[Service]
User={conn.user}
Group={conn.user}
WorkingDirectory={SOURCE_ROOT}
ExecStart={SOURCE_ROOT}/venv/bin/gunicorn --bind 0.0.0.0:8000 wsgi
ExecReload=/bin/kill -s HUP $MAINPID
Environment=CRAWL_DATABASE={CRAWL_DATABASE}

[Install]
WantedBy=multi-user.target
    """.strip()
    )

    conn.put(gunicorn_config, SYSTEMD_NAME)
    conn.sudo(f"mv {SYSTEMD_NAME} {SYSTEMD_PATH}")
    conn.sudo(f"systemctl daemon-reload")
    conn.sudo(f"systemctl reload-or-restart {SYSTEMD_SERVICE}")

    # Configure nightly cron to run crawler.
    print("Configuring nightly cron to run crawler")
    conn.sudo(
        f"bash -c 'cat > {CRONTAB_PATH} <<EOF\n"
        "PATH=/usr/local/bin:/usr/bin:/bin\n"
        "SHELL=/bin/bash\n"
        f"0 0 * * * {conn.user} "
        f"cd {SOURCE_ROOT} && "
        f"./wget_crawl.sh https://www.consumerfinance.gov/ && "
        f"PYTHONPATH=. DJANGO_SETTINGS_MODULE=settings ./venv/bin/django-admin "
        "warc_to_db ./crawl.warc.gz ./crawl.sqlite3 && "
        f"mv crawl.{{cdx,sqlite3,warc.gz}} wget.log /var/tmp/\n"
        "EOF'"
    )

    print("Done!")
