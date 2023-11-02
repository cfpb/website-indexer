import os
import os.path

import djclick as click
from wpull.application.builder import Builder
from wpull.application.options import AppArgumentParser

from crawler import wpull_plugin


@click.command()
@click.argument("start_url")
@click.argument("db_filename", type=click.Path())
@click.option(
    "--max-pages", type=int, help="Maximum number of pages to crawl", default=0
)
@click.option("--depth", type=int, help="Maximum crawl depth", default=0)
@click.option(
    "--recreate",
    is_flag=True,
    show_default=True,
    default=False,
    help="Overwrite SQLite database if it already exists",
)
@click.option("--resume", is_flag=True)
def command(start_url, db_filename, max_pages, depth, recreate, resume):
    """Crawl a website to a SQLite database."""
    if os.path.exists(db_filename):
        if not recreate and not resume:
            raise click.ClickException(
                f"File {db_filename} already exists, "
                "use --recreate to recreate "
                "or --resume to resume a previous crawl."
            )

        if recreate:
            os.remove(db_filename)

    wpull_progress_filename = f"{db_filename}.wpull.db"
    click.echo(
        f"Storing crawl progress in {wpull_progress_filename}, use --resume to resume."
    )

    if not resume and os.path.exists(wpull_progress_filename):
        os.path.remove(wpull_progress_filename)

    arg_parser = AppArgumentParser()
    args = arg_parser.parse_args(
        [
            start_url,
            "--quiet",
            "--recursive",
            "--delete-after",
            "--no-robots",
            "--wait=0.5",
            "--random-wait",
            "--dns-timeout=5",
            "--connect-timeout=5",
            "--read-timeout=30",
            "--session-timeout=30",
            "--span-hosts",
            "--link-extractors=html",
            "--follow-tags=a",
            "--user-agent=CFPB website indexer",
            "--no-check-certificate",
            f"--level={depth}",
            f"--plugin-script={wpull_plugin.__file__}",
            f"--plugin-args={db_filename},{max_pages}",
            f"--database={wpull_progress_filename}",
        ]
    )
    builder = Builder(args)
    app = builder.build()

    # This is required due to the use of async code in wpull. Unfortunately
    # wpull hooks aren't called in a way that allows us to wrap Django database
    # calls with sync_to_async. This is only safe because we only download one
    # URL at a time.
    # https://docs.djangoproject.com/en/3.2/topics/async/#async-safety
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

    exit_status = app.run_sync()
    click.echo(f"done, exiting with status {exit_status}")
    return exit_status
