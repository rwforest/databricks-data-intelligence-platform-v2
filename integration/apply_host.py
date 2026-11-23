import argparse
import os
import shutil


def apply(app_dir):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_path = os.path.join(app_dir, "index.html")
    with open(index_path, encoding="utf-8") as handle:
        html = handle.read()
    css_tag = '<link rel="stylesheet" href="addon-host.css">'
    js_tag = '<script src="addon-host.js"></script>'
    if css_tag not in html:
        html = html.replace("</head>", "  " + css_tag + "\n</head>", 1)
    if js_tag not in html:
        html = html.replace("</body>", "  " + js_tag + "\n</body>", 1)
    with open(index_path, "w", encoding="utf-8") as handle:
        handle.write(html)
    shutil.copyfile(os.path.join(root, "integration", "addon-host.css"), os.path.join(app_dir, "addon-host.css"))
    shutil.copyfile(os.path.join(root, "integration", "addon-host.js"), os.path.join(app_dir, "addon-host.js"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("app_dir")
    apply(os.path.abspath(parser.parse_args().app_dir))
