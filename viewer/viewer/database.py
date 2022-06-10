from django.conf import settings
from django.db import OperationalError, connections


def get_crawl_database_filename():
    try:
        connections["crawl"].cursor()
    except OperationalError:
        return None
    else:
        return settings.CRAWL_DATABASE


class DatabaseRouter:
    route_app_labels = {"viewer"}

    def db_for_read(self, *args, **kwargs):
        if get_crawl_database_filename():
            return "crawl"
        else:
            return "empty"

    def db_for_write(self, *args, **kwargs):
        return None

    def allow_migrate(self, *args, **kwargs):
        return False
