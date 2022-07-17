import os
import os.path
from collections import defaultdict

from django.db import connections
from django.conf import settings
from django.core.management import call_command
from django.test import override_settings

import djclick as click

from warc.reader import generate_records
from warc.writer import DatabaseWriter


@click.command()
@click.argument("warc", type=click.File("rb"))
@click.argument("db_filename", type=click.Path())
@click.option(
    "--max-pages", type=int, help="Maximum number of pages to read from the archive"
)
@click.option(
    "--recreate",
    is_flag=True,
    show_default=True,
    default=False,
    help="Recreate database file if it already exists.",
)
@click.option(
    "--noinput",
    "--no-input",
    is_flag=True,
    default=False,
    help="Do not prompt the user for input of any kind.",
)
def command(warc, db_filename, max_pages, recreate, noinput):
    if os.path.exists(db_filename):
        if not recreate:
            if noinput:
                raise click.ClickException(
                    f"File {db_filename} already exists, use --recreate to recreate."
                )

            click.confirm(
                f"File {db_filename} already exists, do you wish to recreate?",
                abort=True,
            )

        os.remove(db_filename)

    db_alias = "warc_to_db"

    connections.databases[db_alias] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": db_filename,
    }

    click.echo("Creating empty database tables...")
    call_command("migrate", database=db_alias, app_label="warc", run_syncdb=True)

    click.echo("Reading WARC content into database tables...")
    writer = DatabaseWriter(db_alias)

    for record in generate_records(
        warc, max_pages=max_pages, include_page_content=True
    ):
        writer.write(record)

    writer.flush()
