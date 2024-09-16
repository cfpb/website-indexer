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
    "--keep", type=int, help="Keep this many crawls of each status", default=1
)
@click.option("--dry-run", is_flag=True)
def clean(keep, dry_run):
    crawls_to_keep = (
        Crawl.objects.filter(status=OuterRef("status"))
        .order_by("-started")
        .values("pk")[:keep]
    )

    crawls_to_delete = Crawl.objects.exclude(pk__in=Subquery(crawls_to_keep))

    click.secho(f"Deleting {crawls_to_delete.count()} crawls")
    for crawl in crawls_to_delete:
        click.secho(crawl)

    if not dry_run:
        crawls_to_delete.delete()
    else:
        click.secho("Dry run, skipping deletion")
