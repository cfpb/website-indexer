#!/usr/bin/env bash

# Recursively crawl a website and save its HTML locally.
#
# Example usage:
#
# ./wget_crawl.sh [-d depth] https://www.consumerfinance.gov/
#
# Optionally specify -d depth to limit the crawl depth.

# If a command fails, stop executing this script and return its error code.
set -e

depth=0

while getopts ":d:" opt; do
    case $opt in
      d )
        depth="$OPTARG";
        number_regex='^[0-9]+$'
        if ! [[ $depth =~ $number_regex ]] ; then
            echo "Crawl depth must be a number." 1>&2
            exit 1
        fi
        ;;
    \? )
        echo "Invalid option: -$OPTARG." 1>&2
        exit 1
        ;;
    : )
        echo "Invalid option: -$OPTARG requires an argument." 1>&2
        exit 1
        ;;
    esac
done

shift $((OPTIND -1))

url=$1

if [ -z "$url" ]; then
  echo "Must specify URL to crawl."
  exit 1
fi

echo "Starting crawl at $url."

domain=$url
domain="${domain#http://}"
domain="${domain#https://}"
domain="${domain%%:*}"
domain="${domain%%\?*}"
domain="${domain%%/*}"
echo "Limiting crawl to domain $domain."

if [ $depth -ne 0 ]; then
    echo "Limiting crawl to depth $depth."
fi

# Crawl into a temporary directory to avoid potential unexpected overwriting
# due to use of --trust-server-names.
# See https://nvd.nist.gov/vuln/detail/CVE-2010-2252.
tmp_dir=$(mktemp -d -t wget-$(date +%Y-%m-%d-%H-%M-%S)-XXXXXXXX)
echo "Working in $tmp_dir."

pushd "$tmp_dir" > /dev/null

# The --reject-regex below rejects two types of URLs:
#
# 1. Any files, i.e. URLs that end with /something.something, without having
#    a trailing slash. That's the first half of the regex: [^:/]/.*\.[^/]*$
# 2. Any URLs with query string parameters except for ?page, which is the only
#    query string we allow. Because wget only supports POSIX regular
#    expressions out of the box, we have to do this in an ugly way, via the
#    second half of the regex:
#    ([^\?]*(\?([^p]|$)|\?p([^a]|$)|\?pa([^g]|$)|\?pag([^e]|$)|\?page[^=&$]))

time wget \
    --domains="$domain" \
    --no-verbose \
    --delete-after \
    --no-directories \
    --warc-file=crawl \
    --warc-cdx=on \
    --warc-tempdir="$tmp_dir" \
    --execute robots=off \
    --wait=0.5 \
    --random-wait \
    --ignore-case \
    --no-hsts \
    --reject-regex '[^:/]/.*\.[^/]*$|([^\?]*(\?([^p]|$)|\?p([^a]|$)|\?pa([^g]|$)|\?pag([^e]|$)|\?page[^=&$]))' \
    --recursive \
    --level="$depth" \
    --user-agent="crawsqueal" \
    "$url" 2>&1 | tee wget.log

popd > /dev/null

# Copy back log and WARC file from temporary directory.
cp "$tmp_dir"/wget.log .
cp "$tmp_dir"/crawl.{warc.gz,cdx} .

# Clean up temporary directory.
rm -rf "$tmp_dir"
