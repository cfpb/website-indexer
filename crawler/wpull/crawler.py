import os
import os.path
import traceback

from wpull.application.builder import Builder
from wpull.application.options import AppArgumentParser

from crawler.wpull import plugin
from crawler.models import Crawl, CrawlConfig


class WpullCrawler:
    def crawl(self, config: CrawlConfig):
        crawl_record = Crawl.start(config)

        try:
            exit_code = self._do_crawl(crawl_record)
        except Exception:
            crawl_record.fail(traceback.format_exc())
            raise

        if exit_code:
            crawl_record.fail(f"Crawler finished with non-zero exit code {exit_code}")
        else:
            crawl_record.finish()

    def _do_crawl(self, crawl_record):
        arg_parser = AppArgumentParser()
        args = arg_parser.parse_args(
            [
                crawl_record.config["start_url"],
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
                f"--level={crawl_record.config['depth']}",
                f"--plugin-script={plugin.__file__}",
                f"--plugin-args={crawl_record.pk}",
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

        return app.run_sync()
