import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from integration.apply_host import apply


def assemble(upstream, book, output):
    shutil.rmtree(output, ignore_errors=True)
    shutil.copytree(upstream, output, ignore=shutil.ignore_patterns(".git", "node_modules"))
    app_dir = os.path.join(output, "app")
    apply(app_dir)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(output, "tools"), exist_ok=True)
    shutil.copyfile(os.path.join(root, "integration", "smoke_addon.js"), os.path.join(output, "tools", "smoke_addon.js"))
    addons_dir = os.path.join(app_dir, "addons")
    os.makedirs(addons_dir, exist_ok=True)
    shutil.copytree(book, os.path.join(addons_dir, "book"), dirs_exist_ok=True)
    manifest = {
        "schemaVersion": 1,
        "addons": [{
            "id": "book",
            "label": "Book",
            "title": "Databricks Data Intelligence Platform",
            "icon": "book",
            "entry": "book/index.html",
        }],
    }
    with open(os.path.join(addons_dir, "manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream")
    parser.add_argument("book")
    parser.add_argument("output")
    args = parser.parse_args()
    assemble(os.path.abspath(args.upstream), os.path.abspath(args.book), os.path.abspath(args.output))
