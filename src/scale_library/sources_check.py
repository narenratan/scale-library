"""
Check and repair DOIs in sources/DaMuSc/MetaData/sources.csv.

The problem
-----------
sources.csv has DOIs embedded in its Reference_Full column, but several
are broken by spaces introduced during line-wrapping of the original data:

    doi: 10.21504/amj. V6i1.1099   →  space mid-suffix
    doi: 10.1109/ ICEAST.2018…     →  space after slash

For references with no DOI at all, we search Crossref by title and accept
the result only when both the publication year and title match closely.

For every resolved DOI we do a direct Crossref lookup (GET /works/{doi})
to obtain canonical title, authors, and year.  The lookup title is also
compared against the sources.csv title to catch DOIs that are simply wrong
in the reference text.

Usage
-----
    uv run python -m scale_library.sources_check          # report only
    uv run python -m scale_library.sources_check --write  # update sources.csv

The --write flag writes src/scale_library/damusc_sources.csv with the
original columns plus doi, crossref_title, crossref_authors, crossref_year,
best_title, best_authors, and best_year.  The upstream sources.csv is never
modified.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path

import requests

from scale_library import SOURCES_DIR

SOURCES_CSV = SOURCES_DIR / "DaMuSc/Metadata/sources.csv"
PROCESSED_CSV = Path(__file__).parent / "damusc_sources.csv"

# Original columns in sources.csv (before we added any columns).
ORIGINAL_COLUMNS = [
    "RefID",
    "Authors",
    "Year",
    "Title",
    "Reference_Full",
    "Measurement device(s)",
    "Notes on the inclusion of scales in the database",
]

CROSSREF_API = "https://api.crossref.org/works"
RATE_DELAY = 0.5  # seconds between Crossref requests

# Crossref results are only accepted when title similarity exceeds this.
# 0.6 is permissive enough to handle minor wording differences while
# rejecting clearly wrong papers.
TITLE_SIMILARITY_THRESHOLD = 0.6

# Known-bad DOI overrides: ref_id → forced DOI (empty string = no DOI).
# Use when Crossref returns a DOI for a different publication (e.g. a news
# report about the paper rather than the paper itself).
DOI_OVERRIDES: dict[str, str] = {
    "3": "",  # Ellis 1885: Crossref finds Nature news article (10.1038/031488a0)
              # instead of the actual paper in Journal of the Society of Arts.
}

# Match "doi:" (with optional URL prefix and surrounding whitespace)
_DOI_MARKER = re.compile(r"doi[:\s]+(https?://doi\.org/)?\s*", re.IGNORECASE)
_TOKEN = re.compile(r"\S+")


def extract_doi(reference: str) -> str | None:
    """
    Extract and clean a DOI from a reference string.

    The simple case is straightforward:
        "... doi: 10.2307/851338" → "10.2307/851338"

    The tricky case is when a space was introduced mid-DOI by line-wrapping:
        "doi: 10.21504/amj. V6i1.1099" — space splits the suffix
        "doi: 10.1109/ ICEAST.2018…"   — space after the slash

    Strategy: grab the first token after "doi:", strip junk, check if it
    forms a valid DOI (10.NNNN/suffix). If the suffix has no separator
    characters (no '.' or '-'), it's likely truncated — grab the second
    token too and join them to repair the space-split case.
    """
    m = _DOI_MARKER.search(reference)
    if not m:
        return None

    rest = reference[m.end():]
    tokens = _TOKEN.findall(rest)
    if not tokens:
        return None

    def _clean(s: str) -> str:
        s = re.sub(r"^https?://doi\.org/", "", s)
        return s.rstrip(".,;)")

    one = _clean("".join(tokens[:1]))
    two = _clean("".join(tokens[:2])) if len(tokens) >= 2 else ""

    def _valid(s: str) -> bool:
        return bool(re.match(r"^10\.\d{4,}/.{2,}$", s))

    def _suffix(doi: str) -> str:
        """Return the part after the first slash."""
        return doi.split("/", 1)[1] if "/" in doi else ""

    if _valid(one):
        # The 1-token DOI looks valid, but the suffix might still be
        # incomplete if it contains no separator characters (e.g. "amj",
        # "musicologist", "09298215"). In those cases check whether joining
        # a second token produces a longer valid DOI and prefer that.
        # Suffixes with '.' or '-' already (e.g. "978-3-030-02695-0") are
        # considered complete.
        if not re.search(r'[-.]', _suffix(one)) and _valid(two) and len(two) > len(one):
            return two
        return one

    if _valid(two):
        return two

    return None


def title_similarity(a: str, b: str) -> float:
    """Return the SequenceMatcher ratio between two title strings (0–1)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def crossref_search(title: str, year: str) -> str | None:
    """
    Search Crossref for a paper by title and return its DOI, or None.

    We fetch the top 3 results and accept the first one where:
      - the publication year matches exactly, AND
      - the title similarity exceeds TITLE_SIMILARITY_THRESHOLD.

    Returns only the DOI string; use crossref_doi_lookup() for full metadata.
    """
    try:
        r = requests.get(
            CROSSREF_API,
            params={
                "query.title": title,
                "rows": 3,
                "select": "DOI,title,published",
            },
            headers={"User-Agent": "scale-library/sources_check"},
            timeout=15,
        )
        r.raise_for_status()
        items = r.json().get("message", {}).get("items", [])
    except Exception as e:
        print(f"  Crossref search error: {e}", file=sys.stderr)
        return None

    for item in items:
        cr_doi = item.get("DOI", "")
        cr_title = " ".join((item.get("title") or [""])[0].split())
        date_parts = (item.get("published") or {}).get("date-parts") or [[""]]
        cr_year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""
        if cr_year != year:
            continue
        if title_similarity(title, cr_title) >= TITLE_SIMILARITY_THRESHOLD:
            return cr_doi

    return None


def crossref_doi_lookup(doi: str) -> dict | None:
    """
    Look up a DOI directly in Crossref and return canonical metadata.

    Returns a dict with keys: doi, title, authors, year
    or None if the DOI is not registered in Crossref.

    Authors are formatted as "Family, Given; Family, Given; …"
    """
    try:
        r = requests.get(
            f"{CROSSREF_API}/{doi}",
            headers={"User-Agent": "scale-library/sources_check"},
            timeout=15,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        item = r.json()["message"]
    except Exception as e:
        print(f"  Crossref lookup error for {doi}: {e}", file=sys.stderr)
        return None

    cr_title = " ".join((item.get("title") or [""])[0].split())
    date_parts = (item.get("published") or {}).get("date-parts") or [[""]]
    cr_year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""
    raw_authors = item.get("author") or []
    cr_authors = "; ".join(
        f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
        for a in raw_authors
    )

    container = html.unescape((item.get("container-title") or [""])[0].strip())
    volume = str(item.get("volume") or "")
    issue = str(item.get("issue") or "")
    page = str(item.get("page") or "")
    publisher = str(item.get("publisher") or "")
    cr_type = str(item.get("type") or "")

    return {
        "doi": item.get("DOI", doi),
        "title": cr_title,
        "authors": cr_authors,
        "year": cr_year,
        "journal": container,
        "volume": volume,
        "issue": issue,
        "page": page,
        "publisher": publisher,
        "type": cr_type,
    }


def _titlecase_authors(authors: str) -> str:
    """
    Title-case family names that are entirely uppercase.

    Crossref sometimes registers metadata with all-caps family names
    (e.g. "WACHSMANN, K. P." or "MZHAVANADZE, Nana").  We title-case
    the family part when it is all uppercase, leaving given names alone.
    """
    def fix_one(author: str) -> str:
        parts = author.split(",", 1)
        family = parts[0].strip()
        given = parts[1].strip() if len(parts) > 1 else ""
        if family == family.upper() and family.isalpha():
            family = family.title()
        return f"{family}, {given}".strip(", ") if given else family

    return "; ".join(fix_one(a) for a in authors.split(";") if a.strip())


def _count_authors(csv_authors: str) -> int:
    """Count authors in CSV format (comma-separated surnames)."""
    return len([a for a in csv_authors.split(",") if a.strip()]) if csv_authors.strip() else 0


def _count_cr_authors(cr_authors: str) -> int:
    """Count authors in Crossref format (semicolon-separated 'Family, Given')."""
    return len([a for a in cr_authors.split(";") if a.strip()]) if cr_authors.strip() else 0


def best_fields(row: dict) -> dict:
    """
    Select the best available author, title, and year for a row.

    Rules
    -----
    best_authors:
        Use Crossref when it has at least as many authors as the CSV and
        at least one author is registered.  Title-case any ALL-CAPS family
        names in the Crossref data.  Otherwise keep the CSV value.

    best_title:
        Use Crossref when available.  Fall back to CSV for RefID 23
        where Crossref has the typo "Acomparison" (missing space).

    best_year:
        Use Crossref when it agrees with the CSV year.  Keep the CSV
        value when they differ (signals a potential mismatch to investigate).
    """
    csv_authors = row.get("Authors", "").strip()
    cr_authors = row.get("crossref_authors", "").strip()
    csv_title = row.get("Title", "").strip()
    cr_title = row.get("crossref_title", "").strip()
    csv_year = row.get("Year", "").strip()
    cr_year = row.get("crossref_year", "").strip()

    # Authors
    cr_n = _count_cr_authors(cr_authors)
    csv_n = _count_authors(csv_authors)
    if cr_authors and cr_n >= csv_n and cr_n > 0:
        authors = _titlecase_authors(cr_authors)
    else:
        authors = csv_authors

    # Title — use Crossref unless there's a known data error
    if cr_title and "Acomparison" not in cr_title:
        title = cr_title
    else:
        title = csv_title

    # Year
    year = cr_year if (cr_year and (cr_year == csv_year or not csv_year)) else csv_year

    return {"best_authors": authors, "best_title": title, "best_year": year}


def best_reference(row: dict) -> str:
    """
    Build a formatted citation string for use in scl files.

    Uses Crossref structured data when available, falling back to
    Reference_Full from the CSV.

    Journal article format:
        Authors (Year). Title. Journal, Vol(Issue):Pages.
    Book format:
        Authors (Year). Title. Publisher.
    Fallback:
        Reference_Full as-is.
    """
    authors = row.get("best_authors", "").strip()
    title = row.get("best_title", "").strip()
    year = row.get("best_year", "").strip()
    journal = row.get("crossref_journal", "").strip()
    volume = row.get("crossref_volume", "").strip()
    issue = row.get("crossref_issue", "").strip()
    page = row.get("crossref_page", "").strip()
    publisher = row.get("crossref_publisher", "").strip()
    cr_type = row.get("crossref_type", "").strip()

    if not (authors and title and year):
        return (row.get("Reference_Full") or "").strip()

    head = f"{authors} ({year}). {title}."

    if journal:
        loc = journal
        if volume and issue:
            loc += f", {volume}({issue})"
        elif volume:
            loc += f", {volume}"
        if page:
            loc += f":{page}"
        return f"{head} {loc}."
    elif publisher and cr_type in ("book", "monograph"):
        return f"{head} {publisher}."
    else:
        ref_full = (row.get("Reference_Full") or "").strip()
        return ref_full if ref_full else head


def check_sources(write: bool = False) -> None:
    with open(SOURCES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    results = []

    for row in rows:
        title = row["Title"]
        year = row["Year"]
        reference = row.get("Reference_Full") or ""

        if row["RefID"] in DOI_OVERRIDES:
            results.append(
                {"row": row, "doi": DOI_OVERRIDES[row["RefID"]], "status": "override",
                 "note": "manual DOI override", "cr_meta": None}
            )
            continue

        extracted = extract_doi(reference)

        if extracted:
            # Direct DOI lookup: verifies the DOI is real and the title
            # matches, and gives us canonical metadata if so.
            lookup = crossref_doi_lookup(extracted)
            time.sleep(RATE_DELAY)

            if lookup:
                sim = title_similarity(title, lookup["title"])
                if sim >= TITLE_SIMILARITY_THRESHOLD:
                    status = "extracted"
                    cr_meta = lookup
                    note = f"sim={sim:.2f}"
                else:
                    # The DOI resolves to a different paper — flag it.
                    status = "extracted⚠"
                    cr_meta = None
                    note = (
                        f"DOI resolves to different paper: sim={sim:.2f} "
                        f"cr_title={lookup['title']!r}"
                    )
            else:
                # Not in Crossref (some books/chapters aren't registered).
                status = "extracted"
                cr_meta = None
                note = "not in Crossref"

            results.append(
                {"row": row, "doi": extracted, "status": status,
                 "note": note, "cr_meta": cr_meta}
            )

        else:
            # No DOI in the reference — search Crossref by title to find one.
            found_doi = crossref_search(title, year)
            time.sleep(RATE_DELAY)

            if found_doi:
                # Verify and get canonical metadata via direct lookup.
                lookup = crossref_doi_lookup(found_doi)
                time.sleep(RATE_DELAY)

                if lookup:
                    sim = title_similarity(title, lookup["title"])
                    if sim >= TITLE_SIMILARITY_THRESHOLD:
                        status = "crossref"
                        cr_meta = lookup
                        note = f"sim={sim:.2f}"
                    else:
                        # Direct lookup contradicts the title search — reject.
                        status = "crossref⚠"
                        cr_meta = None
                        found_doi = ""
                        note = (
                            f"lookup mismatch: sim={sim:.2f} "
                            f"cr_title={lookup['title']!r}"
                        )
                else:
                    # Rare: search found a DOI but direct lookup failed.
                    status = "crossref"
                    cr_meta = None
                    note = "DOI lookup failed"

                results.append(
                    {"row": row, "doi": found_doi, "status": status,
                     "note": note, "cr_meta": cr_meta}
                )
            else:
                results.append(
                    {"row": row, "doi": "", "status": "missing",
                     "note": "", "cr_meta": None}
                )

    # --- Report ---
    print(f"\n{'ID':>4}  {'Authors':<32}  {'Status':<12}  DOI")
    print("-" * 110)
    for r in results:
        row = r["row"]
        print(
            f"{row['RefID']:>4}  {row['Authors']:<32}  {r['status']:<12}  {r['doi']}"
        )
        if r["note"] and r["note"] != f"sim={1.00:.2f}":
            print(f"            {r['note']}")
        if r["cr_meta"]:
            m = r["cr_meta"]
            print(f"            cr: {m['authors']} ({m['year']}) {m['title']!r}")

    n_extracted = sum(1 for r in results if r["status"] == "extracted")
    n_warned = sum(1 for r in results if "⚠" in r["status"])
    n_crossref = sum(1 for r in results if r["status"] == "crossref")
    n_missing = sum(1 for r in results if r["status"] == "missing")
    n_overrides = sum(1 for r in results if r["status"] == "override")
    print(
        f"\nExtracted from reference: {n_extracted}"
        + (f"  Warnings: {n_warned}" if n_warned else "")
        + f"  Found via Crossref: {n_crossref}"
        + f"  No DOI found: {n_missing}"
        + (f"  Overrides: {n_overrides}" if n_overrides else "")
    )

    if write:
        out_fieldnames = ORIGINAL_COLUMNS + [
            "doi", "crossref_title", "crossref_authors", "crossref_year",
            "crossref_journal", "crossref_volume", "crossref_issue",
            "crossref_page", "crossref_publisher", "crossref_type",
            "best_title", "best_authors", "best_year", "best_reference",
        ]
        for r in results:
            r["row"]["doi"] = r["doi"]
            m = r["cr_meta"] or {}
            r["row"]["crossref_title"] = m.get("title", "")
            r["row"]["crossref_authors"] = m.get("authors", "")
            r["row"]["crossref_year"] = m.get("year", "")
            r["row"]["crossref_journal"] = m.get("journal", "")
            r["row"]["crossref_volume"] = m.get("volume", "")
            r["row"]["crossref_issue"] = m.get("issue", "")
            r["row"]["crossref_page"] = m.get("page", "")
            r["row"]["crossref_publisher"] = m.get("publisher", "")
            r["row"]["crossref_type"] = m.get("type", "")
            best = best_fields(r["row"])
            r["row"]["best_title"] = best["best_title"]
            r["row"]["best_authors"] = best["best_authors"]
            r["row"]["best_year"] = best["best_year"]
            r["row"]["best_reference"] = best_reference(r["row"])
        with open(PROCESSED_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=out_fieldnames, extrasaction="ignore",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(r["row"] for r in results)
        print(f"\nWritten {PROCESSED_CSV}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check and repair DOIs in DaMuSc sources.csv"
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "Write src/scale_library/damusc_sources.csv with doi and Crossref "
            "metadata columns (default: report only). The upstream sources.csv "
            "is never modified."
        ),
    )
    args = parser.parse_args()
    check_sources(write=args.write)


if __name__ == "__main__":
    main()

