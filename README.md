# crawsqueal 🦜

CLI version of [cfgov-crawler-app](https://github.com/cfpb/cfgov-crawler-app). Crawls the consumerfinance.gov website and saves notable things in a SQLite database.

![crawsqueal-screenshot](screenshot.png)

## Usage

```
npx cfpb/crawsqueal
```

It'll create a SQLite database named `./cfgov.sqlite3`, crawl the cf.gov website, and create a record for every page that has a unique URL (including query params and hashes). Takes a couple hours. You can optionally pass a custom filename for the database, e.g. `npx cfpb/crawsqueal db.sqlite3`.

FYI [DB4S](https://github.com/sqlitebrowser/sqlitebrowser) is a neat SQLite browser.

## Development

```
yarn
yarn start
```

----

## Open source licensing info
1. [TERMS](TERMS.md)
2. [LICENSE](LICENSE)
3. [CFPB Source Code Policy](https://github.com/cfpb/source-code-policy/)
