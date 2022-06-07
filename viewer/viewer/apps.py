from django.apps import AppConfig
from django.db import connections


class ViewerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "viewer"

    def ready(self):
        from .models import Page, PageHTML

        with connections["empty"].schema_editor() as empty_db:
            empty_db.create_model(Page)

            # We can't do empty_db.create_model(PageHTML) here because its table
            # is a virtual FTS5 table.
            empty_db.execute(
                "CREATE VIRTUAL TABLE "
                f"{PageHTML._meta.db_table} "
                f"USING fts5(path, pageHtml, content={Page._meta.db_table})"
            )
