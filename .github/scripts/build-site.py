"""Build the root site and current Agentic HIL documentation for GitHub Pages."""

import shutil
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from mkdocs.commands.build import build
from mkdocs.config import load_config

SITE_URL = "https://agentic-hil.github.io/docs/"
ROOT_FILES = (
    "index.html", "install.sh", "install.ps1", "llms.txt",
    "robots.txt", "sitemap.xml", "CNAME", ".nojekyll",
)


class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if attrs.get("id"):
            self.ids.add(attrs["id"])


def validate_root_links(output):
    page = PageLinks()
    page.feed((output / "index.html").read_text(encoding="utf-8"))
    for href in page.links:
        url = urlsplit(href)
        if url.scheme or url.netloc or not url.path:
            continue
        target = (output / unquote(url.path).lstrip("/")).resolve()
        if not target.is_relative_to(output):
            raise ValueError(f"Link leaves the published site: {href}")
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            raise ValueError(f"Root page link has no published target: {href}")
        if url.fragment and target.suffix == ".html":
            linked = PageLinks()
            linked.feed(target.read_text(encoding="utf-8"))
            if unquote(url.fragment) not in linked.ids:
                raise ValueError(f"Root page link has no target anchor: {href}")


def main():
    source = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    root = Path(__file__).resolve().parents[2]
    if output == root or root not in output.parents:
        raise ValueError("The build output must be a directory inside this repository")
    output.mkdir(parents=True, exist_ok=True)
    for name in ROOT_FILES:
        path = root / name
        if path.is_file():
            shutil.copy2(path, output / name)
    for name in ("index.html", "install.sh", "install.ps1", "llms.txt", "robots.txt", "sitemap.xml"):
        if not (output / name).is_file():
            raise ValueError(f"Missing root file: {name}")
    config = load_config(
        config_file=str(source / "mkdocs.yml"),
        site_url=SITE_URL,
        site_dir=str(output / "docs"),
    )
    build(config)
    sitemap = ET.parse(output / "docs" / "sitemap.xml")
    urls = sitemap.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
    if not urls or any(not node.text.startswith(SITE_URL) for node in urls):
        raise ValueError("Documentation sitemap must use the /docs/ publication URL")
    index = (output / "docs" / "index.html").read_text(encoding="utf-8")
    if f'<link rel="canonical" href="{SITE_URL}">' not in index:
        raise ValueError("Documentation home canonical URL does not match publication URL")
    ET.parse(output / "sitemap.xml")
    validate_root_links(output)
    print(f"Built documentation with {len(urls)} sitemap entries at {SITE_URL}")


if __name__ == "__main__":
    main()
