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


DEPLOY_ROOT = "/opt"

NODE_VERSION = "20"

SOURCE_PARENT = f"{DEPLOY_ROOT}/cfpb"
SOURCE_REPO = "https://github.com/cfpb/website-indexer.git"
SOURCE_DIRNAME = "website-indexer"
SOURCE_ROOT = f"{SOURCE_PARENT}/{SOURCE_DIRNAME}"

CRAWL_DIR = "/var/tmp"
CRAWL_DATABASE = f"{SOURCE_ROOT}/crawl.sqlite3"
CRAWL_DATABASE_TMP = f"{CRAWL_DIR}/crawl-new.sqlite3"

LOGROTATE_DIR = "/etc/logrotate.d"
LOGROTATE_NAME = "website-indexer"
LOGROTATE_PATH = f"{LOGROTATE_DIR}/{LOGROTATE_NAME}"

SYSTEMD_DIR = "/etc/systemd/system"
SYSTEMD_SERVICE = "website-indexer"
SYSTEMD_NAME = f"{SYSTEMD_SERVICE}.service"
SYSTEMD_PATH = f"{SYSTEMD_DIR}/{SYSTEMD_NAME}"

CRONTAB_NAME = "website-indexer"
CRONTAB_DIR = "/etc/cron.d"
CRONTAB_PATH = f"{CRONTAB_DIR}/{CRONTAB_NAME}"

LOG_DIR = "/var/log/website-indexer"

GOOGLE_TAG_ID = "GTM-MLPGQ6J7"


@task
def ls(conn):
    conn.run("ls")


@task
def configure(conn):
    # Install Node package repository from Nodesource.
    # https://github.com/nodesource/distributions/blob/master/README.md
    conn.run(
        f"curl -fsSL https://rpm.nodesource.com/setup_{NODE_VERSION}.x | sudo bash -"
    )
    conn.sudo("yum install -y nodejs")

    # Install git to be able to clone source code repository.
    conn.sudo("yum install -y git")

    # Install Python 3.12.
    conn.sudo("yum install -y python3.12")

    # Install libraries needed to build lxml from source.
    conn.sudo("yum install -y python3.12-devel libxml2-devel libxslt-devel")

    # Set up deploy root and grant permissions to deploy user.
    conn.sudo(f"mkdir -p {DEPLOY_ROOT}")
    conn.sudo(f"chown -R {conn.user}:{conn.user} {DEPLOY_ROOT}")


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
            f"|| (git clone -b ec2 --single-branch {SOURCE_REPO} {SOURCE_DIRNAME} ); "
        )

    # Build the viewer app and update any dependencies.
    with conn.cd(SOURCE_ROOT):
        conn.sudo("corepack enable")
        conn.run("yarn && yarn build")
        conn.run(f"python3.12 -m venv venv")

        with conn.prefix("source venv/bin/activate"):
            conn.run("pip install -r requirements/base.txt")
            conn.run("pip install -r requirements/gunicorn.txt")

    # Configure nightly cron to run crawler.
    print("Configuring nightly cron to run crawler")
    conn.sudo(
        f"bash -c 'cat > {CRONTAB_PATH} <<EOF\n"
        "PATH=/usr/local/bin:/usr/bin:/bin\n"
        "SHELL=/bin/bash\n"
        f"0 0 * * * {conn.user} "
        f"cd {SOURCE_ROOT} && "
        f"./venv/bin/python manage.py crawl --recreate "
        f"https://www.consumerfinance.gov {CRAWL_DATABASE_TMP} "
        f"> {CRAWL_DIR}/crawl.log 2>&1 && "
        f"mv {CRAWL_DATABASE_TMP} {CRAWL_DATABASE}\n"
        "EOF'"
    )

    # Set up log directory and log rotation.
    print("Configuring logging")
    conn.sudo(f"mkdir -p {LOG_DIR}")
    conn.sudo(f"chown -R {conn.user}:{conn.user} {LOG_DIR}")

    logrotate_config = StringIO(
        f"""
{LOG_DIR}/*.log {{
    dateext
    daily
    rotate 90
    missingok
    notifempty
    copytruncate
    compress
    create 644 {conn.user} {conn.user}
    sharedscripts
    postrotate
      systemctl reload {SYSTEMD_SERVICE} > /dev/null 2>/dev/null || true
    endscript
}}
    """.strip()
    )
    conn.put(logrotate_config, LOGROTATE_NAME)
    conn.sudo(f"mv {LOGROTATE_NAME} {LOGROTATE_PATH}")
    conn.sudo(f"chown root:root {LOGROTATE_PATH}")
    conn.sudo(f"chmod 644 {LOGROTATE_PATH}")

    # SELinux: Allow logrotate to write to log files.
    # This gets persisted to /etc/selinux/targeted/contexts/files/file_contexts.local
    conn.sudo(f"semanage fcontext -m -t var_log_t '{LOG_DIR}(/.*)?'")

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
ExecStart={SOURCE_ROOT}/venv/bin/gunicorn \\
    --bind 0.0.0.0:8000 \\
    --access-logfile {LOG_DIR}/access.log \\
    --error-logfile {LOG_DIR}/error.log \\
    --capture-output \\
    --timeout 600 \\
    wsgi
ExecReload=/bin/kill -s HUP $MAINPID
Environment=DATABASE_URL=sqlite:///{CRAWL_DATABASE}
Environment=GOOGLE_TAG_ID={GOOGLE_TAG_ID}

[Install]
WantedBy=multi-user.target
    """.strip()
    )

    conn.put(gunicorn_config, SYSTEMD_NAME)
    conn.sudo(f"mv {SYSTEMD_NAME} {SYSTEMD_PATH}")
    conn.sudo(f"systemctl daemon-reload")
    conn.sudo(f"systemctl restart {SYSTEMD_SERVICE}")

    conn.sudo(f"systemctl status {SYSTEMD_SERVICE}")

    # Open firewall so gunicorn can run on port 8000.
    conn.sudo("firewall-cmd --zone=public --permanent --add-port 8000/tcp")
    conn.sudo("firewall-cmd --reload")

    print("Done!")
