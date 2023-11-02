# website-indexer 🪱

This repository crawls a website and stores its content in a SQLite database file.

Use the SQLite command-line interface to
[make basic queries](#searching-the-crawl-database)
about website content including:

- URLs
- Page titles
- Full text search
- HTML search
- Link URLs
- Design components (CSS class names)
- Crawler errors (404s and more)
- Redirects

This repository also contains a Django-based
[web application](#running-the-viewer-application)
to explore crawled website content in your browser.
Make queries through an easy-to-use web form, review page details,
and export results as CSV or JSON reports.

## Crawling a website

Create a Python virtual environment and install required packages:

```
python3.6 -m venv venv
source venv/bin/activate
pip install -r requirements/base.txt
```

Crawl a website:

```sh
./manage.py crawl https://www.consumerfinance.gov crawl.sqlite3
```

## Searching the crawl database

You can use the
[SQLite command-line client](https://www.sqlite.org/cli.html)
to make queries against the crawl database,
or a graphical client such as [DB4S](https://github.com/sqlitebrowser/sqlitebrowser) if you prefer.

To run the command-line client:

```
sqlite3 crawl.sqlite3
```

The following examples describe some common use cases.

### Dump database statistics

To list the total number of URLs and crawl timestamps:

```sql
sqlite> SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM crawler_page;
23049|2022-07-20 02:50:02|2022-07-20 08:35:23
```

Note that page data is stored in a table named `crawler_page`.

### List pages that link to a certain URL

```sql
sqlite> SELECT DISTINCT url
FROM crawler_page
INNER JOIN crawler_page_links ON (crawler_page.id = crawler_page_links.page_id)
INNER JOIN crawler_link ON (crawler_page_links.link_id = crawler_page_link.id)
WHERE href LIKE "/plain-writing/"
ORDER BY url ASC;
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
sqlite> SELECT DISTINCT url
FROM crawler_page
INNER JOIN crawler_page_links ON (crawler_page.id = crawler_page_links.page_id)
INNER JOIN crawler_link ON (crawler_page_links.link_id = crawler_link.id)
WHERE href LIKE "/about-us/blog/"
ORDER BY url ASC;
```

### List pages that contain a specific design component

```sql
sqlite> SELECT DISTINCT url
FROM crawler_page
INNER JOIN crawler_page_components ON (crawler_page.id = crawler_page_components.page_id)
INNER JOIN crawler_component ON (crawler_page_components.component_id = crawler_component.id)
WHERE crawler_component.class_name LIKE "o-featured-content-module"
ORDER BY url ASC
```

See the [CFPB Design System](https://cfpb.github.io/design-system/)
for a list of common components used on CFPB websites.

### List pages with titles containing a specific string

```sql
SELECT url FROM crawler_page WHERE title LIKE "%housing%" ORDER BY url ASC;
```

### List pages with body text containing a certain string

```sql
sqlite> SELECT url FROM crawler_page WHERE text LIKE "%diamond%" ORDER BY URL asc;
```

### List pages with HTML containing a certain string

```sql
sqlite> SELECT url FROM crawler_page WHERE html LIKE "%<br>%" ORDER BY URL asc;
```

## Running the viewer application

From the repo's root, compile front-end assets:

```
yarn
yarn build
```

Create a Python virtual environment and install required packages:

```
python3.6 -m venv venv
source venv/bin/activate
pip install -r requirements/base.txt
```

Optionally set the `CRAWL_DATABASE` environment variable to point to a local crawl database:

```
export CRAWL_DATABASE=crawl.sqlite3
```

Finally, run the Django webserver:

```
./manage.py runserver
```

The viewer application will be available locally at http://localhost:8000.

## Development

### Testing

To run Python unit tests, first install the test dependencies in your virtual environment:

```
pip install -r requirements/test.txt
```

To run the tests:

```
./manage.py test --keepdb
```

The `--keepdb` parameter is used because tests are run using a fixed,
pre-existing test database.

### Code formatting

This project uses [Black](https://github.com/psf/black) as a Python code formatter.

To check if your changes to project code match the desired coding style:

```
black . --check
```

You can fix any problems by running:

```
black .
```

This project uses [Prettier](https://prettier.io/) as a code formatter
for JavaScript, CSS, and HTML templates.

To check if your changes to project code match the desired coding style:

```
yarn prettier
```

You can fix any problems by running:

```
yarn fix
```

### Sample test data

This repository includes a sample database file for testing purposes at `/sample/sample.sqlite3`.

The sample database file is used by the viewer application when no other crawl
database file has been specified.

The source website content used to generate this file is included in this repository
under the `/sample/src` subdirectory.
To regenerate these files, first serve the sample website locally:

```
cd ./sample/src && python -m http.server
```

This starts the sample website running at http://localhost:8000.

Then, in another terminal, start a crawl against the locally running site:

```
./manage.py crawl http://localhost:8000/ --recreate ./sample/src/sample.sqlite3
```

This will overwrite the test database with a fresh crawl.

## Deployment

_For information on how this project is deployed at the CFPB,
employees and contractors should refer to the internal "CFGOV/crawler-deploy" repository._

This repository includes a [Fabric](https://www.fabfile.org/) script
that can be used to configure a RHEL7 Linux server to run this project
and to deploy both the crawler and the viewer application to that server.

To install Fabric in your virtual environment:

```
pip install -r requirements/deploy.txt
```

### Configuring a server

To configure a remote RHEL7 server with the appropriate system requirements,
you'll need to use some variation of this command:

```
fab configure
```

You'll need to provide some additional connection information depending
on the specific server you're targeting, for example, hostname and user.
See [the Fabric documentation](https://docs.fabfile.org/en/latest/cli.html)
for possible options; for example, to connect using a host configuration
defined as `crawler` in your `~/.ssh/config`, you might run:

```
fab configure -H crawler
```

The `configure` command:

- Installs Node, Yarn, and Git
- Installs a modern version of SQLite
- Installs Python 3

### Deploying the application

To run the deployment, you'll need to use some variation of this command:

```
fab deploy
```

The `deploy` command:

- Pulls down the latest version of the source code from GitHub
- Installs the latest dependencies
- Runs the frontend build script
- Configures the crawler to run nightly
- Sets up webserver logging and log rotation
- Serves the viewer application on port 8000

See [fabfile.py](fabfile.py) for additional detail.

----

## Open source licensing info
1. [TERMS](TERMS.md)
2. [LICENSE](LICENSE)
3. [CFPB Source Code Policy](https://github.com/cfpb/source-code-policy/)
