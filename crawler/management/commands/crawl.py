import djclick as click

from crawler.models import CrawlConfig
from crawler.wpull.crawler import WpullCrawler


@click.command()
@click.argument("start_url")
@click.option(
    "--max-pages", type=int, help="Maximum number of pages to crawl", default=0
)
@click.option("--depth", type=int, help="Maximum crawl depth", default=0)
def command(start_url, max_pages, depth):
    config = CrawlConfig(start_url=start_url, max_pages=max_pages, depth=depth)
    return WpullCrawler().crawl(config)
