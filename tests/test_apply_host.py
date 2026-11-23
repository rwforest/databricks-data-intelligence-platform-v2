import os
import tempfile
import unittest

from integration.apply_host import apply


class ApplyHostTest(unittest.TestCase):
    def test_patch_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            index_path = os.path.join(directory, "index.html")
            with open(index_path, "w", encoding="utf-8") as handle:
                handle.write("<html><head></head><body></body></html>")
            apply(directory)
            apply(directory)
            with open(index_path, encoding="utf-8") as handle:
                html = handle.read()
            self.assertEqual(html.count("addon-host.css"), 1)
            self.assertEqual(html.count("addon-host.js"), 1)


if __name__ == "__main__":
    unittest.main()
