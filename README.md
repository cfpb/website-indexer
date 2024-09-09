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

```
docker build -t website-indexer:main .
```

#### Viewing a sample crawl using Docker

To then run the viewer application using sample data:

```
docker run -it \
    -p 8000:8000 \
    website-indexer:main
```

The web application using sample data will be accessible at http://localhost:8000/.

#### Crawling a website and viewing the crawl results using Docker

To crawl a website using the Docker image,
storing the result in a local SQLite database named `crawl.sqlite3`:

```
docker run -it \
    -v `pwd`:/data \
    website-indexer:main \
    python manage.py crawl https://www.consumerfinance.gov /data/crawl.sqlite3
```

To then run the viewer web application to view that crawler database:

```
docker run -it \
    -p 8000:8000 \
    -v `pwd`:/data \
    -e DATABASE_URL=sqlite:////data/crawl.sqlite3 \
    website-indexer:main
```

The web application with the crawl results will be accessible at http://localhost:8000/.

### Using a Python virtual environment

Create a Python virtual environment and install required packages:

```
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements/base.txt
```

From the repo's root, compile frontend assets:

```
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

```
./manage.py runserver
```

The web application using sample data will be accessible at http://localhost:8000/.

#### Crawling a website and viewing the crawl results using a Python virtual environment

To crawl a website and store the result in a local SQLite database named `crawl.sqlite3`:

```sh
./manage.py crawl https://www.consumerfinance.gov crawl.sqlite3
```

To then run the viewer web application to view that crawler database:

```
DATABASE_URL=sqlite:///crawl.sqlite3 ./manage.py runserver
```

The web application with the crawl results will be accessible at http://localhost:8000/

## Configuration

### Database configuration

The `DATABASE_URL` environment variable can be used to specify the database
used for crawl results by the viewer application.
This project makes use of the
[dj-database-url](https://github.com/jazzband/dj-database-url)
project to convert that variable into a Django database specification.

For example, to use a SQLite file at `/path/to/db.sqlite`:

```
export DATABASE_URL=sqlite:////path/to/db.sqlite
```

(Note use of four slashes when referring to an absolute path;
only three are needed when referring to a relative path.)

To point to a PostgreSQL database instead:

```
export DATABASE_URL=postgres://username:password@localhost/dbname
```

Please see
[the dj-database-url documentation](https://github.com/jazzband/dj-database-url)
for additional examples.

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

The `--keepdb` parameter is used because tests are run using
[a fixed, pre-existing test database](#sample-test-data).

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
yarn prettier:fix
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

(This uses a local Python virtual environment; see
[above](#crawling-a-website-and-viewing-the-crawl-results-using-docker)
for instructions on using Docker instead.)

This command will overwrite the sample database with a fresh crawl.

## Deployment

_For information on how this project is deployed at the CFPB,
employees and contractors should refer to the internal
[CFGOV/crawler-deploy](https://github.local/CFGOV/crawler-deploy/) 🔒
repository._

This repository includes a [Fabric](https://www.fabfile.org/) script
that can be used to configure a RHEL8 Linux server to run this project
and to deploy both the crawler and the viewer application to that server.

To install Fabric in your virtual environment:

```
pip install -r requirements/deploy.txt
```

### Configuring a server

To configure a remote RHEL8 server with the appropriate system requirements,
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

- Installs Node and Git
- Installs Python 3.12

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

---

## Open source licensing info

1. [TERMS](TERMS.md)
2. [LICENSE](LICENSE)
3. [CFPB Source Code Policy](https://github.com/cfpb/source-code-policy/)
