import os
import os.path
import re


ENV_FILENAME_RE = re.compile(r"[A-Z_]+")


def patch_environ(path, environ=os.environ):
    """Patch the environment with file-based values.

    Given a path to a directory containing files named for environment
    variables, set those variables with the content of the files.
    Do not overwrite variables already set in the environment.
    """
    if not path:
        return

    for filename in os.listdir(path):
        if ENV_FILENAME_RE.match(filename):
            with open(os.path.join(path, filename)) as f:
                environ.setdefault(filename, f.read())
