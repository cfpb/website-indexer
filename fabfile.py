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

# Node 18 doesn't seem to work on RHEL 7.
# https://github.com/nodejs/node/blob/master/doc/changelogs/CHANGELOG_V18.md#toolchain-and-compiler-upgrades
NODE_VERSION = "16"

SQLITE_VERSION = "3390200"
SQLITE_BASENAME = f"sqlite-autoconf-{SQLITE_VERSION}"
SQLITE_INSTALL_ROOT = f"{DEPLOY_ROOT}/{SQLITE_BASENAME}"

PYTHON_VERSION = "3.6.15"
PYTHON_BASENAME = f"Python-{PYTHON_VERSION}"
PYTHON_INSTALL_ROOT = f"{DEPLOY_ROOT}/{PYTHON_BASENAME}"

SOURCE_PARENT = f"{DEPLOY_ROOT}/cfpb"
SOURCE_REPO = "https://github.com/cfpb/website-indexer.git"
SOURCE_DIRNAME = "website-indexer"
SOURCE_ROOT = f"{SOURCE_PARENT}/{SOURCE_DIRNAME}"

CRAWL_DIR = "/var/tmp"
CRAWL_DATABASE = f"{CRAWL_DIR}/crawl.sqlite3"
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

    # Install the Yarn package repository.
    # https://classic.yarnpkg.com/lang/en/docs/install/#centos-stable
    conn.run(
        "curl --silent --location https://dl.yarnpkg.com/rpm/yarn.repo | sudo tee /etc/yum.repos.d/yarn.repo"
    )
    conn.sudo("yum install -y yarn")

    # Install git to be able to clone source code repository.
    conn.sudo("yum install -y git")

    # Set up deploy root and grant permissions to deploy user.
    conn.sudo(f"mkdir -p {DEPLOY_ROOT}")
    conn.sudo(f"chown -R {conn.user}:{conn.user} {DEPLOY_ROOT}")

    # Build and install SQLite (needs to happen before installing Python).
    conn.sudo("yum install -y gcc sqlite-devel")
    with conn.cd(DEPLOY_ROOT):
        conn.run(f"curl -O https://www.sqlite.org/2022/{SQLITE_BASENAME}.tar.gz")
        conn.run(f"tar xzf {SQLITE_BASENAME}.tar.gz")
        conn.run(f"rm {SQLITE_BASENAME}.tar.gz")

    with conn.cd(SQLITE_INSTALL_ROOT):
        conn.run("./configure && make")

    # https://github.com/pyinvoke/invoke/issues/459
    conn.sudo(f'bash -c "cd {SQLITE_INSTALL_ROOT} && make install"')

    # Build and install Python 3.
    # This sets /usr/local/bin python and python3 commands to point to Python 3.
    # This doesn't update /usr/bin/python (used by sudo)
    conn.sudo("yum install -y openssl-devel bzip2-devel libffi-devel")

    with conn.cd(DEPLOY_ROOT):
        conn.run(
            f"curl -O https://www.python.org/ftp/python/{PYTHON_VERSION}/{PYTHON_BASENAME}.tgz"
        )
        conn.run(f"tar xzf {PYTHON_BASENAME}.tgz")
        conn.run(f"rm {PYTHON_BASENAME}.tgz")

    with conn.cd(PYTHON_INSTALL_ROOT):
        conn.run("LD_RUN_PATH=/usr/local/lib ./configure --enable-optimizations")

    # https://github.com/pyinvoke/invoke/issues/459
    conn.sudo(
        f"bash -c "
        f'"cd {PYTHON_INSTALL_ROOT} && LD_RUN_PATH=/usr/local/lib make install"'
    )
    conn.sudo("ln -sf /usr/local/bin/python3 /usr/local/bin/python")


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
        conn.run("python -m venv venv")

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
    conn.sudo(f"semanage fcontext -a -t var_log_t '{LOG_DIR}(/.*)?'")

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
Environment=CRAWL_DATABASE={CRAWL_DATABASE}

[Install]
WantedBy=multi-user.target
    """.strip()
    )

    conn.put(gunicorn_config, SYSTEMD_NAME)
    conn.sudo(f"mv {SYSTEMD_NAME} {SYSTEMD_PATH}")
    conn.sudo(f"systemctl daemon-reload")
    conn.sudo(f"systemctl restart {SYSTEMD_SERVICE}")

    conn.sudo(f"systemctl status {SYSTEMD_SERVICE}")
    print("Done!")
