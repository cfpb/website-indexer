import os.path

from django import template

from ..database import get_crawl_database_filename


register = template.Library()


@register.simple_tag()
def get_database_file_size():
    if filename := get_crawl_database_filename():
        return os.path.getsize(filename)
