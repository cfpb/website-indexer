#!/usr/bin/env bash

# Exit if any command fails.
set -e

# Echo commands.
set -x

OUTPUT_PATH=/var/tmp
OUTPUT_FILENAME=crawl.sqlite3
OUTPUT="$OUTPUT_PATH/$OUTPUT_FILENAME"

rm -f "$OUTPUT"

# Go up from current directory (deploy) to repository root.
cd "$(dirname "$0")"/..

# Make sure dependencies are up to date.
yarn

# Start the crawler.
yarn start "$OUTPUT"
