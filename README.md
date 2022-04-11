# crawsqueal 🦜

CLI version of [cfgov-crawler-app](https://github.com/cfpb/cfgov-crawler-app). Crawls the consumerfinance.gov website and saves notable things in a SQLite database.

![crawsqueal-screenshot](screenshot.png)

## Usage

```
npx cfpb/crawsqueal
```

It'll create a SQLite database named `./cfgov.sqlite3`, crawl the cf.gov website, and create a record for every page that has a unique URL (including query params and hashes). Takes a couple hours. You can optionally pass a custom filename for the database, e.g. `npx cfpb/crawsqueal db.sqlite3`.

## How to query the crawler database

You can use the SQLite command-line client to make queries against the crawl result,
or a graphical client such as [DB4S](https://github.com/sqlitebrowser/sqlitebrowser) if you prefer.

To run the command-line client:

```
sqlite3 cfgov.sqlite3
```

The following examples describe some common use cases.

### Dump database statistics

To list the total number of URLs and crawl timestamps:

```sql
sqlite> SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM cfgov;
25279|2022-04-11T04:00:12.336Z|2022-04-11T06:18:11.608Z
```

Note that page data is stored in a table named `cfgov`.

### List pages that link to a certain URL

```sql
sqlite> SELECT DISTINCT cfgov.path FROM cfgov, json_each(json(cfgov.links)) WHERE json_each.value LIKE '/plain-writing/' ORDER BY cfgov.path;
```

To dump results to a CSV instead of the terminal:

```sql
sqlite> .mode csv
sqlite> .output filename.csv
sqlite> ... run your query here
sqlite> .output stdout
sqlite> .mode list
```

To search with wildcards, use the `%` character:

```sql
sqlite> SELECT cfgov.path, json_each.value AS link FROM cfgov, json_each(json(cfgov.links)) WHERE json_each.value LIKE '/about-us/blog/%' ORDER BY cfgov.path, link;
```

### List pages that contain a specific design component

```sql
sqlite> SELECT DISTINCT cfgov.path FROM cfgov, json_each(json(cfgov.components)) WHERE json_each.value LIKE 'o-featured-content-module' ORDER BY cfgov.path;
```

See the [CFPB Design System](https://cfpb.github.io/design-system/)
for a list of common components used on CFPB websites.

### List pages that contain a certain phrase

```sql
sqlite> SELECT path FROM cfgov_fts WHERE cfgov_fts MATCH 'diamonds' ORDER BY path;
```

Note that this query uses a distinct `cfgov_fts` table that uses the SQLite [FTS5 extension](https://www.sqlite.org/fts5.html) for full-text search.

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
