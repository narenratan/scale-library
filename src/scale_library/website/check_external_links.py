"""
Check that external URLs in recordings.yaml and the site templates respond
with a successful HTTP status code.

Uses HEAD requests (no download). Retries GET if HEAD returns an error,
since some servers reject HEAD from bots. Adds a small delay between
requests to avoid rate-limiting.

Usage:
    uv run python -m scale_library.website.check_external_links

Options:
    --delay SECS    Seconds between requests (default: 0.5)
    --timeout SECS  Request timeout in seconds (default: 10)
"""

import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path


_HERE = Path(__file__).parent
_RECORDINGS = _HERE / "recordings.yaml"
_TEMPLATES = _HERE / "templates"

_USER_AGENT = (
    "scale-library-link-checker/1.0 (https://github.com/narenratan/scale-library)"
)

# Domains known to block HEAD; go straight to GET for these
_GET_ONLY_DOMAINS = {"bandcamp.com"}

# Domains that block automated requests entirely — skip rather than annoy them
_SKIP_DOMAINS = {"en.xen.wiki"}


def _collect_urls() -> list[str]:
    urls: list[str] = []

    # recordings.yaml: all url: lines (track entries use "- url:" with leading spaces)
    for line in _RECORDINGS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s+-\s+url:\s+(https?://\S+)", line)
        if m:
            urls.append(m.group(1))

    # templates: hardcoded https:// links (skip template variables)
    for tmpl in _TEMPLATES.glob("*.html"):
        for m in re.finditer(r'href=["\']?(https://[^"\'<> {%]+)', tmpl.read_text()):
            url = m.group(1)
            if not any(c in url for c in "{}%"):
                urls.append(url)

    # Deduplicate preserving order
    seen: set[str] = set()
    result = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result


def _check_url(url: str, timeout: int, use_get: bool = False) -> tuple[int | None, str]:
    """Return (status_code, error_message). status_code is None on connection error."""
    method = "GET" if use_get else "HEAD"
    req = urllib.request.Request(
        url, method=method, headers={"User-Agent": _USER_AGENT}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as e:
        return e.code, str(e.reason)
    except urllib.error.URLError as e:
        return None, str(e.reason)
    except Exception as e:
        return None, str(e)


def _domain(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url)
    return m.group(1) if m else ""


def check_external_links(delay: float = 0.5, timeout: int = 10) -> int:
    urls = _collect_urls()
    print(f"Checking {len(urls)} external URLs...\n")

    errors: list[str] = []
    for i, url in enumerate(urls, 1):
        domain = _domain(url)

        if any(s in domain for s in _SKIP_DOMAINS):
            print(f"  [{i:3}/{len(urls)}] - skip  {url}")
            continue

        use_get = any(g in domain for g in _GET_ONLY_DOMAINS)

        status, err = _check_url(url, timeout, use_get=use_get)

        # Retry with GET if HEAD returned an error (not just a redirect)
        if not use_get and (status is None or status >= 400):
            status2, err2 = _check_url(url, timeout, use_get=True)
            if status2 is not None and status2 < 400:
                status, err = status2, err2

        ok = status is not None and status < 400
        mark = "✓" if ok else "✗"
        status_str = str(status) if status is not None else "ERR"
        print(f"  [{i:3}/{len(urls)}] {mark} {status_str}  {url}")

        if not ok:
            errors.append(f"  {status_str}  {url}  ({err})")

        if i < len(urls):
            time.sleep(delay)

    print()
    if errors:
        print(f"FAILED: {len(errors)} URL(s) returned errors:\n")
        print("\n".join(errors))
        return 1
    else:
        print(f"All {len(urls)} external links OK.")
        return 0


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--delay", type=float, default=0.5, metavar="SECS")
    parser.add_argument("--timeout", type=int, default=10, metavar="SECS")
    args = parser.parse_args()
    sys.exit(check_external_links(delay=args.delay, timeout=args.timeout))


if __name__ == "__main__":
    main()
