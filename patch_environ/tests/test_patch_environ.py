import os.path
from tempfile import TemporaryDirectory
from unittest import TestCase

from patch_environ import patch_environ


def make_file(filename, contents):
    with open(filename, "w") as f:
        f.write(contents)


class PatchEnvironTests(TestCase):
    def test_pass_none_does_nothing(self):
        environ = {
            "FOO": "foo",
            "BAR": "bar",
        }

        patch_environ(None, environ)

        self.assertEqual(
            environ,
            {
                "FOO": "foo",
                "BAR": "bar",
            },
        )

    def test_patching(self):
        environ = {
            "FOO": "foo",
            "BAR": "bar",
        }

        with TemporaryDirectory() as tempdir:
            make_file(os.path.join(tempdir, "BAR"), "test")
            make_file(os.path.join(tempdir, "FOO_BAR"), "baz")
            make_file(os.path.join(tempdir, "ignore_lowercase"), "ignore")

            patch_environ(tempdir, environ)

            self.assertEqual(
                environ,
                {
                    "FOO": "foo",
                    "BAR": "bar",
                    "FOO_BAR": "baz",
                },
            )
