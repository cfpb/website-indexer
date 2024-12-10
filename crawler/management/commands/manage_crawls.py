from django.db import transaction
from django.db.models import OuterRef, Subquery

import djclick as click

from crawler.models import Crawl


@click.group()
def cli():
    pass


@cli.command()
def list():
    for crawl in Crawl.objects.all():
        click.secho(crawl)


@cli.command()
@click.argument("crawl_id", type=int)
@click.option("--dry-run", is_flag=True)
def delete(crawl_id, dry_run):
    crawl = Crawl.objects.get(pk=crawl_id)
    click.secho(f"Deleting {crawl}")

    if not dry_run:
        crawl.delete()
    else:
        click.secho("Dry run, skipping deletion")


@cli.command()
@click.option(
    "--keep", type=int, help="Keep this many finished and failed crawls", default=1
)
@click.option("--dry-run", is_flag=True)
@transaction.atomic
def clean(keep, dry_run):
    # If there are no crawls, there's nothing to do.
    if not Crawl.objects.exists():
        return

    # Delete any in-progress crawls that aren't the most recent.
    started_delete = Crawl.objects.filter(status=Crawl.Status.STARTED).exclude(
        pk=Crawl.objects.latest("started").pk
    )

    # Delete any finished and failed crawls except the number to keep.
    keep_subquery = (
        Crawl.objects.filter(status=OuterRef("status"))
        .order_by("-started")
        .values("pk")[:keep]
    )

    completed_delete = Crawl.objects.exclude(status=Crawl.Status.STARTED).exclude(
        pk__in=Subquery(keep_subquery)
    )

    crawls_to_delete = started_delete | completed_delete

    click.secho(f"Deleting {crawls_to_delete.count()} crawls")
    for crawl in crawls_to_delete:
        click.secho(crawl)

    if not dry_run:
        crawls_to_delete.delete()
    else:
        click.secho("Dry run, skipping deletion")
