#!/usr/bin/env bash

CRAWLER_REPO=${CRAWLER_REPO:-https://github.com/cfpb/crawsqueal.git}
CRAWLER_DIR=${CRAWLER_DIR:-/opt/cfpb/crawsqueal}
CRAWLER_USER=${CRAWLER_USER:-ec2-user}

# Exit if any command fails.
set -e

# Echo commands.
set -x

# Install Node package repository from Nodesource.
# https://github.com/nodesource/distributions/blob/master/README.md
# Node 18 doesn't seem to work on RHEL 7.
# https://github.com/nodejs/node/blob/master/doc/changelogs/CHANGELOG_V18.md#toolchain-and-compiler-upgrades
curl -fsSL https://rpm.nodesource.com/setup_17.x | bash -

# Install the Yarn package repository.
# https://classic.yarnpkg.com/lang/en/docs/install/#centos-stable
curl --silent --location https://dl.yarnpkg.com/rpm/yarn.repo | tee /etc/yum.repos.d/yarn.repo

# Add the nginx package repository.
# https://nginx.org/en/linux_packages.html#RHEL-CentOS
cat > /etc/yum.repos.d/nginx.repo <<EOF
[nginx-stable]
name=nginx stable repo
baseurl=http://nginx.org/packages/centos/7/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://nginx.org/keys/nginx_signing.key
module_hotfixes=true
EOF

# Install packages:
#
# - git to clone the crawler repository
# - nginx to serve the crawler website
# - nodejs to run Node
# - yarn to run Yarn
yum install -y git nginx nodejs yarn

# Clone or pull the crawler repository.
# Make it writeable by the crawler user.
if [ ! -d "$CRAWLER_DIR" ] ; then
    mkdir -p "$CRAWLER_DIR"
    cd "$CRAWLER_DIR"
    git clone "$CRAWLER_REPO" "$CRAWLER_DIR"
else
    cd "$CRAWLER_DIR"
    git pull $URL
fi

chown -R "$CRAWLER_USER":"$CRAWLER_USER" "$CRAWLER_DIR"

# Configure nightly cron to run crawler.
cat > /etc/cron.d/nightly-crawl <<EOF
0 0 * * * $CRAWLER_USER "$CRAWLER_DIR/deploy/crawl.sh"
EOF

# Copy over nginx configuration, setting the correct path to the crawler.
CRAWLER_DIR=$CRAWLER_DIR envsubst '$CRAWLER_DIR' \
    <"$CRAWLER_DIR/deploy/nginx.conf" \
    >/etc/nginx/conf.d/default.conf

# Start the webserver.
systemctl restart nginx
