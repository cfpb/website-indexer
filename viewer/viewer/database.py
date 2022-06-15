from django.conf import settings
from django.db import OperationalError, connections
from django.utils.connection import ConnectionDoesNotExist
from django.utils.functional import cached_property


def get_crawl_database_filename():
    try:
        connections["crawl"].cursor()
    except (ConnectionDoesNotExist, OperationalError):
        return None
    else:
        return settings.CRAWL_DATABASE


class DatabaseRouter:
    route_app_labels = {"viewer"}

    @cached_property
    def using_readonly_crawl_database(self):
        return get_crawl_database_filename() is not None

    def db_for_read(self, model, **hints):
        if get_crawl_database_filename():
            return "crawl"
        else:
            return "default"

    def db_for_write(self, model, **hints):
        return None

    def allow_migrate(self, db, *args, **kwargs):
        return False
