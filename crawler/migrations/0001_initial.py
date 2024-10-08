# Generated by Django 4.2.15 on 2024-09-11 15:19

from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Component",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("class_name", models.TextField(unique=True)),
            ],
            options={
                "ordering": ["class_name"],
            },
        ),
        migrations.CreateModel(
            name="Crawl",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("started", models.DateTimeField(auto_now_add=True)),
                ("status", models.CharField(default="Started", max_length=64)),
                ("config", models.JSONField()),
                ("failure_message", models.TextField(blank=True, null=True)),
            ],
            options={
                "ordering": ["started"],
            },
        ),
        migrations.CreateModel(
            name="Link",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("href", models.TextField(unique=True)),
            ],
            options={
                "ordering": ["href"],
            },
        ),
        migrations.CreateModel(
            name="Redirect",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("timestamp", models.DateTimeField(db_index=True)),
                ("url", models.TextField(db_index=True)),
                ("status_code", models.PositiveIntegerField()),
                ("referrer", models.TextField(blank=True, null=True)),
                ("location", models.TextField()),
                (
                    "crawl",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)ss",
                        to="crawler.crawl",
                    ),
                ),
            ],
            options={
                "ordering": ["url"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Page",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("timestamp", models.DateTimeField(db_index=True)),
                ("url", models.TextField(db_index=True)),
                ("title", models.TextField()),
                ("language", models.TextField(blank=True, null=True)),
                ("html", models.TextField()),
                ("text", models.TextField()),
                (
                    "components",
                    modelcluster.fields.ParentalManyToManyField(
                        related_name="pages", to="crawler.component"
                    ),
                ),
                (
                    "crawl",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)ss",
                        to="crawler.crawl",
                    ),
                ),
                (
                    "links",
                    modelcluster.fields.ParentalManyToManyField(
                        related_name="links", to="crawler.link"
                    ),
                ),
            ],
            options={
                "ordering": ["url"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Error",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("timestamp", models.DateTimeField(db_index=True)),
                ("url", models.TextField(db_index=True)),
                ("status_code", models.PositiveIntegerField()),
                ("referrer", models.TextField(blank=True, null=True)),
                (
                    "crawl",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)ss",
                        to="crawler.crawl",
                    ),
                ),
            ],
            options={
                "ordering": ["url"],
                "abstract": False,
            },
        ),
        migrations.AddConstraint(
            model_name="redirect",
            constraint=models.UniqueConstraint(
                models.F("crawl"), models.F("url"), name="redirect_crawl_url_key"
            ),
        ),
        migrations.AddIndex(
            model_name="page",
            index=models.Index(
                models.F("crawl"), models.F("title"), name="page_crawl_title_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="page",
            index=models.Index(
                models.F("crawl"), models.F("language"), name="page_crawl_language_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="page",
            constraint=models.UniqueConstraint(
                models.F("crawl"), models.F("url"), name="page_crawl_url_key"
            ),
        ),
        migrations.AddConstraint(
            model_name="error",
            constraint=models.UniqueConstraint(
                models.F("crawl"), models.F("url"), name="error_crawl_url_key"
            ),
        ),
    ]
