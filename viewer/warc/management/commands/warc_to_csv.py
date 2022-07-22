import csv

import djclick as click

from warc.models import Component, Error, Link, Page, Redirect
from warc.reader import generate_instances


@click.command()
@click.argument("warc", type=click.File("rb"))
@click.option(
    "--pages-csv",
    type=click.File("w", encoding="utf-8-sig"),
    default="pages.csv",
    show_default=True,
)
@click.option(
    "--errors-csv",
    type=click.File("w", encoding="utf-8-sig"),
    default="errors.csv",
    show_default=True,
)
@click.option(
    "--redirects-csv",
    type=click.File("w", encoding="utf-8-sig"),
    default="redirects.csv",
    show_default=True,
)
@click.option(
    "--links-csv",
    type=click.File("w", encoding="utf-8-sig"),
    default="links.csv",
    show_default=True,
)
@click.option(
    "--components-csv",
    type=click.File("w", encoding="utf-8-sig"),
    default="components.csv",
    show_default=True,
)
@click.option(
    "--max-pages", type=int, help="Maximum number of pages to read from the archive"
)
def command(
    warc, pages_csv, errors_csv, redirects_csv, links_csv, components_csv, max_pages
):
    writers = {
        model: csv.writer(model_csv, csv.QUOTE_ALL)
        for model, model_csv in {
            Page: pages_csv,
            Error: errors_csv,
            Redirect: redirects_csv,
            Link: links_csv,
            Component: components_csv,
        }.items()
    }

    for instance in generate_instances(warc, max_pages=max_pages):
        if isinstance(instance, Page):
            writers[Page].writerow(
                [
                    instance.timestamp,
                    instance.url,
                    instance.title,
                    instance.language,
                ]
            )

            for component in instance.components.all():
                writers[Component].writerow(
                    [
                        instance.url,
                        component.class_name,
                    ]
                )

            for link in instance.links.all():
                writers[Link].writerow(
                    [
                        instance.url,
                        link.href,
                    ]
                )
        elif isinstance(instance, Error):
            writers[Error].writerow(
                [
                    instance.timestamp,
                    instance.url,
                    instance.status_code,
                    instance.referrer,
                ]
            )
        elif isinstance(instance, Redirect):
            writers[Redirect].writerow(
                [
                    instance.timestamp,
                    instance.url,
                    instance.status_code,
                    instance.referrer,
                    instance.location,
                ]
            )
        else:
            raise ValueError(instance)
