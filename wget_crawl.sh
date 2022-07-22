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
    --reject '*.css,*.csv,*.do,*.doc,*.docx,*.epub,*.gif,*.ico,*.jpg,*.js,*.json,*.mp3,*.pdf,*.png,*.pptx,*.py,*.r,*.sas,*.sps,*.svg,*.tmp,*.txt,*.wav,*.webmanifest,*.woff,*.woff2,*.xls,*xlsx,*.xml,*.zip' \
    --reject-regex "CatID=|NavCode=|_gl=|activity_type=|authors=|book=|categories=|chartType=|charttype=|clhx=|dateInterval=|date_received_min=|dateinterval=|entx=|fdx=|filter1_topics=|filter2_topics=|form-id=|gib=|gpl=|grade_level=|has_narrative=|hltx=|hous=|houx=|insi=|insl=|inst=|iped=|issue=|language=|lens=|mta=|oid=|othg=|othr=|othx=|parl=|pelg=|perl=|pid=|ppl=|product=|prvf=|prvi=|prvl=|q=|regs=|retx=|schg=|school_subject=|searchField=|search_field=|searchfield=|size=|sort=|stag=|subl=|tab=|taxx=|title=|topic=|topics=|totl=|tran=|trnx=|tuit=|unsl=|utm_campaign=|utm_medium=|utm_source=|wkst=" \
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
