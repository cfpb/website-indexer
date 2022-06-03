from django.db import OperationalError, connections


class DatabaseRouter:
    route_app_labels = {"viewer"}

    def db_for_read(self, *args, **kwargs):
        try:
            connections["crawl"].cursor()
        except OperationalError:
            return "empty"
        else:
            return "crawl"

    def db_for_write(self, *args, **kwargs):
        return None

    def allow_migrate(self, *args, **kwargs):
        return False
