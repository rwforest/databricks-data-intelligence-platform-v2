import json
import os
import tempfile
import unittest

from tools.assemble_site import assemble


class AssembleSiteTest(unittest.TestCase):
    def test_assembly_adds_reader_without_replacing_upstream(self):
        with tempfile.TemporaryDirectory() as directory:
            upstream = os.path.join(directory, "upstream")
            book = os.path.join(directory, "book")
            output = os.path.join(directory, "site")
            os.makedirs(os.path.join(upstream, "app"))
            os.makedirs(book)
            with open(os.path.join(upstream, "app", "index.html"), "w", encoding="utf-8") as handle:
                handle.write("<html><head></head><body><main>board</main></body></html>")
            with open(os.path.join(upstream, "unchanged.txt"), "w", encoding="utf-8") as handle:
                handle.write("upstream")
            with open(os.path.join(book, "index.html"), "w", encoding="utf-8") as handle:
                handle.write("book")
            assemble(upstream, book, output)
            with open(os.path.join(output, "unchanged.txt"), encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "upstream")
            with open(os.path.join(output, "app", "addons", "book", "index.html"), encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "book")
            with open(os.path.join(output, "app", "addons", "manifest.json"), encoding="utf-8") as handle:
                self.assertEqual(json.load(handle)["addons"][0]["id"], "book")


if __name__ == "__main__":
    unittest.main()
