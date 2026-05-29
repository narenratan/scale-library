"""
Check that every internal href in the built site resolves to a real file,
and that every URL in sitemap.xml exists.

Usage:
    uv run python -m scale_library.website.check_links        # checks site/
    uv run python -m scale_library.website.check_links site/  # explicit path
"""

import re
import sys
from pathlib import Path
from html.parser import HTMLParser

from scale_library.website.config import PROD_BASE




class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    self.hrefs.append(value)


def check_links(site_dir: Path, verbose: bool = False) -> int:
    errors = []

    html_files = sorted(site_dir.rglob("*.html"))
    if not html_files:
        print(f"No HTML files found in {site_dir}", file=sys.stderr)
        return 1

    for html_file in html_files:
        parser = LinkExtractor()
        parser.feed(html_file.read_text(encoding="utf-8"))

        for href in parser.hrefs:
            # Skip external links (including protocol-relative), anchors, mailto, javascript
            if href.startswith(("http://", "https://", "//", "#", "mailto:", "javascript:")):
                continue

            # Strip fragment unless the # is literally part of the filename.
            href_path = href
            if "#" in href:
                candidate = (
                    site_dir / href.lstrip("/")
                    if href.startswith("/")
                    else html_file.parent / href
                )
                if not (candidate.exists() or (candidate / "index.html").exists()):
                    href_path = href.split("#")[0]

            # Resolve relative to site root (all our links are absolute paths)
            if href_path.startswith("/"):
                target = site_dir / href_path.lstrip("/")
            else:
                target = html_file.parent / href_path

            # Directory links resolve to index.html
            if target.is_dir():
                target = target / "index.html"

            if not target.exists():
                rel_source = html_file.relative_to(site_dir)
                errors.append(f"  {rel_source}: broken link → {href}")

    # Check every URL in sitemap.xml resolves to an index.html
    sitemap = site_dir / "sitemap.xml"
    if sitemap.exists():
        locs = re.findall(r"<loc>(.*?)</loc>", sitemap.read_text(encoding="utf-8"))
        for loc in locs:
            path = loc[len(PROD_BASE) :].lstrip("/").replace("&amp;", "&")
            target = site_dir / path
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                errors.append(f"  sitemap.xml: missing page → {loc}")

    if errors:
        print(f"Found {len(errors)} broken link(s):\n")
        print("\n".join(errors))
        return 1
    if verbose:
        print(f"All links OK ({len(html_files)} pages checked, sitemap validated)")
    return 0


def main():
    site_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("site")
    if not site_dir.is_dir():
        print(f"Site directory not found: {site_dir}", file=sys.stderr)
        sys.exit(1)
    sys.exit(check_links(site_dir, verbose=True))


if __name__ == "__main__":
    main()
