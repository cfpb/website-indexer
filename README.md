# website-indexer 🪱

Crawl a website and search its content.

This project consists of two components:
a **crawler** application to crawl the contents of a website and store its content in a database; and a **viewer** web application that allows for searching of that crawled content.

Both components require
[Python 3.12](https://www.python.org/)
to run and are built using the
[Django](https://www.djangoproject.com/)
web application framework.
The crawler piece is built on top of the Archive Team's
[ludios_wpull](https://github.com/ArchiveTeam/ludios_wpull)
web crawler.

## Getting started

This project can be run
[using Docker](#using-docker)
or a local
[Python virtual environment](#using-a-python-virtual-environment).

### Using Docker

To build the Docker image:

```sh
docker build -t website-indexer:main .
```

#### Viewing a sample crawl using Docker

To then run the viewer application using sample data:

```sh
docker run -it \
    -p 8000:8000 \
    website-indexer:main
```

The web application using sample data will be accessible at http://localhost:8000/.

#### Crawling a website and viewing the crawl results using Docker

To crawl a website using the Docker image,
storing the result in a local SQLite database named `crawl.sqlite3`,
first create the database file:

```sh
docker run -it \
    -v `pwd`:/data \
    -e DATABASE_URL=sqlite:////data/crawl.sqlite3 \
    website-indexer:main \
    python manage.py migrate
```

and then run the crawl, storing results into that database file:

```sh
docker run -it \
    -v `pwd`:/data \
    -e DATABASE_URL=sqlite:////data/crawl.sqlite3 \
    website-indexer:main \
    python manage.py crawl https://www.consumerfinance.gov
```

To then run the viewer web application to view that crawler database:

```sh
docker run -it \
    -p 8000:8000 \
    -v `pwd`:/data \
    -e DATABASE_URL=sqlite:////data/crawl.sqlite3 \
    website-indexer:main
```

The web application with the crawl results will be accessible at http://localhost:8000/.

### Using a Python virtual environment

Create a Python virtual environment and install required packages:

```sh
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements/base.txt
```

From the repo's root, compile frontend assets:

```sh
yarn
yarn build
```

Alternatively, to continuously watch the frontend assets and rebuild as necessary:

```
yarn
yarn watch
```

#### Viewing a sample crawl using a Python virtual environment

Run the viewer application using sample data:

```sh
./manage.py runserver
```

The web application using sample data will be accessible at http://localhost:8000/.

#### Crawling a website and viewing the crawl results using a Python virtual environment

To crawl a website and store the result in a local SQLite database named `crawl.sqlite3`:

```sh
DATABASE_URL=sqlite:///crawl.sqlite3 /manage.py crawl https://www.consumerfinance.gov
```

To then run the viewer web application to view that crawler database:

```sh
DATABASE_URL=sqlite:///crawl.sqlite3 ./manage.py runserver
```

The web application with the crawl results will be accessible at http://localhost:8000/

### Managing crawls in the database

The `./manage.py manage_crawls` command can be used to list, delete, and cleanup old crawls (assuming `DATABASE_URL` is set appropriately).

Crawls in the database have a `status` field which can be one of `Started`, `Finished`, or `Failed`.

#### Listing crawls

To list crawls in the database:

```sh
./manage.py manage_crawls list
```

This will list crawls in the database, including each crawl's unique ID.

#### Deleting crawls

To delete an existing crawl, for example one with ID `123`:

```sh
./manage.py manage_crawls delete 123
```

`--dry-run` can be added to the `delete` command to preview its output
without modifying the database.

#### Cleaning crawls

To clean old crawls, leaving behind one crawl of each status:

```sh
./manage.py manage_crawls clean
```

To modify the number of crawls left behind, for example leaving behind two of each status:

```sh
./manage.py manage_crawls clean --keep=2
```

`--dry-run` can also be added to the `clean` command to preview its output
without modifying the database.

## Configuration

### Database configuration

The `DATABASE_URL` environment variable can be used to specify the database
used for crawl results by the viewer application.
This project makes use of the
[dj-database-url](https://github.com/jazzband/dj-database-url)
project to convert that variable into a Django database specification.

For example, to use a SQLite file at `/path/to/db.sqlite`:

```sh
export DATABASE_URL=sqlite:////path/to/db.sqlite
```

(Note use of four slashes when referring to an absolute path;
only three are needed when referring to a relative path.)

To point to a PostgreSQL database instead:

```sh
export DATABASE_URL=postgres://username:password@localhost/dbname
```

Please see
[the dj-database-url documentation](https://github.com/jazzband/dj-database-url)
for additional examples.

If the `DATABASE_URL` environment variable is left unset, the
[sample SQLite database file](#sample-test-data)
will be used.

### Google Tag Manager

To enable Google Tag Manager on all pages on the viewer application,
define the `GOOGLE_TAG_ID` environment variable.

### Using files as an alternative to environment variables

As alternative to configuration via environment variable,
values may be provided in files instead.

Set the `PATCH_ENVIRON_PATH` environment variable to the location of a directory
containing files named for environment variables to set,
each containing the desired value for that variable.

When configured this way,
the application environment will be populated with those file-based values.
Values that already exist in the environment will not be overwritten.

## Development

### Sample test data

This repository includes a sample database file for testing purposes at `sample/sample.sqlite3`.

The sample database file is used by the viewer application when no other crawl
database file has been specified.

The source website content used to generate this file is included in this repository
under the `sample/src` subdirectory.

To regenerate the same database file, first delete it:

```sh
rm ./sample/sample.sqlite3
```

Then, start a Python webserver to serve the sample website locally:

```sh
cd ./sample/src && python -m http.server
```

This starts the sample website running at http://localhost:8000.

Then, in another terminal, recreate the database file:

```sh
./manage.py migrate
```

Finally, perform the crawl against the locally running site:

```sh
./manage.py crawl http://localhost:8000/
```

These commands assume use of a local Python virtual environment;
alternatively consider
[using Docker](#crawling-a-website-and-viewing-the-crawl-results-using-docker).

This command will receate the sample database file
`sample/sample.sqlite3`
with a fresh crawl.
To write to a different database, use
[the `DATABASE_URL` environment variable](#database-configuration).

For consistency, the
[Python test fixture](#testing)
should be updated at the same time as the sample database.

### Testing

To run Python unit tests, first install the test dependencies in your virtual environment:

```sh
pip install -r requirements/test.txt
```

To run the tests:

```sh
pytest
```

The Python tests make use of a test fixture generated from
[the sample database](#sample-test-data).

To recreate this test fixture:

```sh
./manage.py dumpdata --indent=4 crawler > crawler/fixtures/sample.json
```

### Code formatting

This project uses [Black](https://github.com/psf/black) as a Python code formatter.

To check if your changes to project code match the desired coding style:

```sh
black . --check
```

You can fix any problems by running:

```sh
black .
```

This project uses [Prettier](https://prettier.io/) as a code formatter
for JavaScript, CSS, and HTML templates.

To check if your changes to project code match the desired coding style:

```sh
yarn prettier
```

You can fix any problems by running:

```sh
yarn prettier:fix
```

## Deployment

For information on how this project is deployed at the CFPB,
employees and contractors should refer to the internal
[CFGOV/crawler-deploy](https://github.local/CFGOV/crawler-deploy/) 🔒
repository.

## Open source licensing info

1. [TERMS](TERMS.md)
2. [LICENSE](LICENSE)
3. [CFPB Source Code Policy](https://github.com/cfpb/source-code-policy/)
