"""
Full website build logic.

Called from __main__.py. Generates site/ with all pages.
"""

import csv
import json
import re
import shutil
import sys
import tarfile
import xml.etree.ElementTree as ET
import time
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlretrieve

import markdown as md
import tuning_library as tl
import yaml
from jinja2 import Environment, FileSystemLoader

from scale_library.contrib import parse_details
from scale_library.website.check_links import check_links
from scale_library.website.config import PROD_BASE
from scale_library.website.data import REPO_ROOT, ScaleData, load_all_scales
from scale_library.website.posts import get_post, get_thread, get_topic_subject
from scale_library.website.scale_workshop import scale_workshop_url
from scale_library.website.similar import compute_similar

# Xenharmonikon "{issue_prefix}-{author_slug}" → article title
from scale_library.xenharmonikon import ARTICLE_TITLES as XEN_ARTICLE_TITLES

# Xenharmonikon "{issue_prefix}-{author_slug}" → URL where article is freely available online
from scale_library.xenharmonikon import ARTICLE_URLS as XEN_ARTICLE_URLS

# Xenharmonikon issue prefix → (issue_number, display_string)
from scale_library.xenharmonikon import JOURNAL as XEN_JOURNAL
from scale_library.xenharmonikon import Author as _Author

SITE_DIR = REPO_ROOT / "site"
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
SIMILAR_JSON = REPO_ROOT / "similar.json"
SCALA_ANALYSIS_DIR = REPO_ROOT / "scala-analysis"
SCALA_ANALYSIS_TAR = REPO_ROOT / "scala-analysis.tar.gz"

SCALE_CENTS_PRECISION = 7

_SCALA_COMMAND_ORDER = [
    "SHOW",
    "SHOW-INTERVAL",
    "SHOW_INTERVALS",
    "SHOW-LINE-CENTS_INTERVALS",
    "SHOW-SPAN_INTERVALS",
    "SHOW_DATA",
    "FIT-MODE",
    "FIT-HARMONIC",
]


# Country → broad region. Covers all countries across DaMuSc, ORD-CC32, and contrib.
# Raises KeyError on build if an unrecognised country is encountered.
_COUNTRY_REGION: dict[str, str] = {
    # Africa
    "Algeria": "Africa",
    "Angola": "Africa",
    "Benin": "Africa",
    "Burkina Faso": "Africa",
    "Central African Republic": "Africa",
    "Congo": "Africa",
    "DR Congo": "Africa",
    "Egypt": "Africa",
    "Equatorial Guinea": "Africa",
    "Ethiopia": "Africa",
    "Gambia": "Africa",
    "Ghana": "Africa",
    "Guinea": "Africa",
    "Malawi": "Africa",
    "Morocco": "Africa",
    "Mozambique": "Africa",
    "Sudan": "Africa",
    "Tanzania": "Africa",
    "Tunisia": "Africa",
    "Uganda": "Africa",
    "Zimbabwe": "Africa",
    # Americas
    "Bolivia": "Americas",
    "Brazil": "Americas",
    "Colombia": "Americas",
    "Guatemala": "Americas",
    "Peru": "Americas",
    # Asia
    "Cambodia": "Asia",
    "China": "Asia",
    "India": "Asia",
    "Indonesia": "Asia",
    "Iraq": "Asia",
    "Japan": "Asia",
    "Korea": "Asia",
    "Laos": "Asia",
    "Myanmar": "Asia",
    "Pakistan": "Asia",
    "Singapore": "Asia",
    "Syria": "Asia",
    "Thailand": "Asia",
    "Turkey": "Asia",
    "Vietnam": "Asia",
    # Europe
    "Georgia": "Europe",  # DaMuSc classifies as Middle East
    "Greece": "Europe",
    "Lithuania": "Europe",
    "Portugal": "Europe",
    "Sweden": "Europe",
    "United Kingdom": "Europe",
    # Oceania
    "Papua New Guinea": "Oceania",
    "Solomon Islands": "Oceania",
}

# Xenharmonikon author slug → full name

AUTHOR_NAMES: dict[str, str] = {
    k: v for k, v in vars(_Author).items() if not k.startswith("_")
}

_RECORDINGS_PATH = Path(__file__).parent / "recordings.yaml"


_SCALA_ANALYSIS_URL = "https://github.com/narenratan/scale-library/releases/download/data/scala-analysis.tar.gz"


def _ensure_scala_analysis() -> None:
    """Ensure scala-analysis/ exists, downloading the tarball from GitHub if needed."""
    if SCALA_ANALYSIS_DIR.exists():
        return
    if not SCALA_ANALYSIS_TAR.exists():
        print(f"Downloading {SCALA_ANALYSIS_TAR.name}…", file=sys.stderr)
        urlretrieve(_SCALA_ANALYSIS_URL, SCALA_ANALYSIS_TAR)
        print("  Done", file=sys.stderr)

    print(f"Extracting {SCALA_ANALYSIS_TAR}…", file=sys.stderr)
    with tarfile.open(SCALA_ANALYSIS_TAR) as tf:
        tf.extractall(REPO_ROOT, filter="data")
    print("  Done", file=sys.stderr)


def _filename_to_command(filename: str) -> str:
    return filename.replace("_", " ").replace("-", "/")


def _load_scala_analysis(stem: str) -> list[tuple[str, str]] | None:
    """Load Scala command outputs for a scale.

    Returns a list of (command_name, content) pairs in display order,
    or None if no scala-analysis directory exists for this scale.
    """
    scale_dir = SCALA_ANALYSIS_DIR / stem
    if not scale_dir.exists():
        return None
    result = []
    for filename in _SCALA_COMMAND_ORDER:
        content = (scale_dir / filename).read_text(encoding="utf-8")
        # Strip first line if it's just '|'
        lines = content.splitlines()
        if lines and lines[0].strip() == "|":
            content = "\n".join(lines[1:])
        result.append((_filename_to_command(filename), content))
    return result


def _load_recordings() -> dict[str, list]:
    """Load recording links keyed by scale stem.

    recordings.yaml uses an album-centric format: each top-level entry is an
    album with artist/album/year/reference fields, and a ``tracks`` list where
    each track has url/title/scales. This
    function expands those into a dict keyed by stem for the rest of the build.
    """
    data = yaml.safe_load(_RECORDINGS_PATH.read_text(encoding="utf-8"))
    album_required = {"artist", "album", "year", "tracks"}
    track_required = {"url", "title", "scales"}
    result: dict[str, list] = {}
    for album in data:
        missing = album_required - album.keys()
        if missing:
            raise ValueError(f"recordings.yaml: album entry missing fields: {missing}")
        if not isinstance(album["year"], int):
            raise ValueError(
                f"recordings.yaml: year must be an int, got {album['year']!r}"
            )
        album_meta = {k: album[k] for k in ("artist", "album", "year") if k in album}
        if "reference" in album:
            album_meta["reference"] = album["reference"]
        for track in album["tracks"]:
            missing = track_required - track.keys()
            if missing:
                raise ValueError(
                    f"recordings.yaml: track entry missing fields: {missing}"
                )
            rec = {**album_meta, **{k: track[k] for k in track if k != "scales"}}
            for stem in track["scales"]:
                result.setdefault(stem, []).append(rec)
    return result


_CONSTRUCTIONS_DIR = Path(__file__).parent / "constructions"


def _load_constructions(scales: list) -> tuple[list[dict], dict[str, dict]]:
    """Load constructions.yaml and build a stem → construction lookup.

    Returns (constructions, stem_to_construction) where constructions is the
    list of dicts from the YAML (augmented with matched scales) and
    stem_to_construction maps each matching scale stem to its construction.
    """
    yaml_path = _CONSTRUCTIONS_DIR / "constructions.yaml"

    constructions = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    stem_to_construction: dict[str, dict] = {}

    for c in constructions:
        patterns = c["stem_patterns"]
        excludes = c.get("stem_excludes", [])
        matched = sorted(
            (
                s
                for s in scales
                if any(pat in s.stem for pat in patterns)
                and not any(ex in s.stem for ex in excludes)
            ),
            key=lambda s: s.stem,
        )
        c["scales"] = matched

        md_path = _CONSTRUCTIONS_DIR / f"{c['slug']}.md"
        raw = md_path.read_text(encoding="utf-8")
        c["content"] = md.markdown(raw, extensions=["fenced_code", "tables"])

        py_path = _CONSTRUCTIONS_DIR / f"{c['slug'].replace('-', '_')}.py"
        c["python_code"] = py_path.read_text(encoding="utf-8")

        examples = c.get("examples", {})
        for s in matched:
            call = examples.get(s.stem)
            stem_to_construction[s.stem] = {
                "slug": c["slug"],
                "title": c["title"],
                "label": c["label"],
                "call": call,
            }

    return constructions, stem_to_construction


def _validate_examples(constructions: list[dict]) -> None:
    scales_dir = REPO_ROOT / "scales"
    for c in constructions:
        examples = c.get("examples", {})
        if not examples:
            continue
        py_path = _CONSTRUCTIONS_DIR / f"{c['slug'].replace('-', '_')}.py"
        namespace: dict = {}
        exec(py_path.read_text(encoding="utf-8"), namespace)  # noqa: S102
        for stem, call in examples.items():
            scl_path = scales_dir / f"{stem}.scl"
            scale = tl.read_scl_file(scl_path)
            result = sorted(eval(call, namespace), key=float)  # noqa: S307
            assert scale.count <= len(result) <= scale.count + 1
            for r, t in zip(result[1:], scale.tones[:-1]):
                if t.type == tl.kToneRatio:
                    assert Fraction(r) == Fraction(
                        t.ratio_n, t.ratio_d
                    ), f"{stem}: {call!r} gives {r} but SCL has {t.ratio_n}/{t.ratio_d}"
                else:
                    assert (
                        abs(float(r) - t.cents) < 0.001
                    ), f"{stem}: {call!r} gives {r} but SCL has {t.cents}¢"


def make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    env.filters["domain"] = lambda url: urlparse(url).netloc
    env.globals["prod_base"] = PROD_BASE
    return env


def _tone_cents(tone) -> float:
    """Return cents for a tone, rounded to 3dp if ratio-derived."""
    if tone.is_ratio:
        return round(tone.cents, 3)
    return tone.cents


def compute_steps(tones) -> list[dict]:
    """Compute consecutive step sizes from a list of ToneData."""
    steps = []
    prev_cents = 0.0
    prev_frac = Fraction(1, 1)
    for tone in tones:
        step_cents = tone.cents - prev_cents
        if tone.is_ratio:
            curr_frac = Fraction(tone.ratio_n, tone.ratio_d)
            step_frac = curr_frac / prev_frac
            ratio_str = (
                f"{step_frac.numerator}/{step_frac.denominator}"
                if step_frac.denominator != 1
                else str(step_frac.numerator)
            )
            prev_frac = curr_frac
        else:
            ratio_str = None
        steps.append({"cents": step_cents, "ratio": ratio_str})
        prev_cents = tone.cents
    return steps


def _xen_author_slug(scl_file: str) -> str:
    """Extract author slug from xenharmonikon scl filename."""
    parts = scl_file.replace(".scl", "").split("-")
    return parts[1]


def _xen_issue_prefix(scl_file: str) -> str:
    """Extract issue prefix (e.g. 'xen18') from xenharmonikon scl filename."""
    return scl_file.split("-")[0]


def _xen_issue_slug(issue) -> str:
    """Convert a Xenharmonikon issue number/name to a URL-safe slug."""
    return str(issue).replace(" & ", "-and-")




def write_page(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def render_scale_page(
    scale: ScaleData,
    scales_by_stem: dict[str, ScaleData],
    env: Environment,
    similar_data: dict,
    recordings: dict,
    construction_lookup: dict,
    has_scala_analysis: bool = True,
) -> str:
    lines = [t.string_rep for t in scale.tones]
    sw_url = scale_workshop_url(scale.description, lines)
    steps = compute_steps(scale.tones)

    sim = similar_data[scale.stem]

    def _lookup_with_diff(key: str) -> list[dict]:
        entries = []
        for d in sim[key]:
            assert (
                d["stem"] in scales_by_stem
            ), f"stem {d['stem']!r} in similar.json not found in scales — regenerate similar.json"
            entries.append(
                {
                    "scale": scales_by_stem[d["stem"]],
                    "max_diff": d["max_diff"],
                    **({"mode": d["mode"]} if "mode" in d else {}),
                }
            )
        return entries

    similar = _lookup_with_diff("similar")
    parents = _lookup_with_diff("parents")
    children = _lookup_with_diff("children")

    # Related scales
    related_count = 0
    related_label = None
    related_more_url = None
    src = scale.info.source

    if src == "Xenharmonikon":
        issue = scale.info.raw["whole_number"]
        author_slug = _xen_author_slug(scale.scl_file)
        article_slug = scale.info.raw.get("article")
        if article_slug:
            related_count = sum(
                s.info.raw.get("whole_number") == issue
                and _xen_author_slug(s.scl_file) == author_slug
                and s.info.raw.get("article") == article_slug
                for s in scales_by_stem.values()
            )
            if related_count:
                related_label = "article"
                related_more_url = f"/source/xenharmonikon/{_xen_issue_slug(issue)}/{author_slug}-{article_slug}/"
        else:
            related_count = sum(
                s.info.raw.get("whole_number") == issue
                and _xen_author_slug(s.scl_file) == author_slug
                for s in scales_by_stem.values()
            )
            if related_count:
                related_label = "article"
                related_more_url = (
                    f"/source/xenharmonikon/{_xen_issue_slug(issue)}/{author_slug}/"
                )

    elif src == "Mailing lists":
        topic_id = scale.info.raw["topic_id"]
        list_name = _mailing_list_name(scale)
        related_count = sum(
            s.info.raw.get("topic_id") == topic_id for s in scales_by_stem.values()
        )
        if related_count and list_name:
            related_label = "thread"
            related_more_url = (
                f"/source/mailing-lists/{list_name}/{int(topic_id)}/"
            )

    elif src == "DaMuSc":
        ref_id = scale.info.raw["ref_id"]
        related_count = sum(
            s.info.raw.get("ref_id") == ref_id for s in scales_by_stem.values()
        )
        related_label = "reference"
        related_more_url = f"/source/damusc/{ref_id}/"

    # Country (DaMuSc and contrib)
    country = None
    country_slug = None
    if src == "DaMuSc":
        country = scale.info.raw["country"]
        country_slug = country.replace(" ", "_")
    elif src == "contrib":
        country = scale.info.raw.get("country")
        if country:
            country_slug = country.replace(" ", "_")

    # Mailing list post + thread (mailing-lists source only)
    post = None
    thread = None
    if src == "Mailing lists":
        list_name = _mailing_list_name(scale)
        msg_id = scale.info.raw["msg_id"]
        topic_id = scale.info.raw["topic_id"]
        if list_name and msg_id:
            post = get_post(list_name, int(msg_id))
        if list_name and topic_id:
            thread = get_thread(list_name, int(topic_id), int(topic_id))

    # Xenharmonikon author (for properties table link)
    xen_author_slug = None
    xen_author_name = None
    xen_issue_slug = None
    if src == "Xenharmonikon":
        xen_author_slug = _xen_author_slug(scale.scl_file)
        xen_author_name = AUTHOR_NAMES.get(xen_author_slug, xen_author_slug)
        xen_issue_slug = _xen_issue_slug(scale.info.raw["whole_number"])

    # Xenharmonikon article URL (for "Read online" link)
    xen_article_url = None
    if src == "Xenharmonikon":
        issue_int = int(str(scale.info.raw["whole_number"]).split()[0])
        prefix = f"xen{issue_int:02d}"
        article_slug = scale.info.raw.get("article")
        if article_slug:
            article_key = f"{prefix}-{xen_author_slug}-{article_slug}"
        else:
            article_key = f"{prefix}-{xen_author_slug}"
        xen_article_url = XEN_ARTICLE_URLS.get(article_key)

    # Divisions of the Tetrachord type
    div_type = None
    div_type_display = None
    if src == "Divisions of the Tetrachord":
        div_type = _divisions_type(scale.description)
        div_type_display = scale.description.split()[0] if scale.description else div_type.capitalize()

    # ORD-CC32 fields
    cc_maqam = None
    cc_maqam_slug = None
    cc_region = None
    cc_tonic_ref = None
    if src == "ORD-CC32":
        cc_maqam = scale.info.raw.get("maqam")
        cc_maqam_slug = _maqam_slug(cc_maqam) if cc_maqam else None
        cc_region = scale.info.raw.get("region")
        cc_tonic_ref = scale.info.raw.get("tonic_ref")

    # Contrib fields
    details_text = None
    ref_url = None
    contributor = None
    if src == "contrib":
        details_text = parse_details(scale.raw_text) or None
        ref_url = scale.info.raw["ref_url"]
        contributor = scale.info.raw["contributor"]

    construction = construction_lookup.get(scale.stem)

    tmpl = env.get_template("scale.html")
    return tmpl.render(
        scale=scale,
        sw_url=sw_url,
        steps=steps,
        similar=similar,
        parents=parents,
        children=children,
        related_count=related_count,
        related_label=related_label,
        related_more_url=related_more_url,
        country=country,
        country_slug=country_slug,
        xen_author_slug=xen_author_slug,
        xen_author_name=xen_author_name,
        xen_issue_slug=xen_issue_slug,
        xen_article_url=xen_article_url,
        cc_maqam=cc_maqam,
        cc_maqam_slug=cc_maqam_slug,
        cc_region=cc_region,
        cc_tonic_ref=cc_tonic_ref,
        div_type=div_type,
        div_type_display=div_type_display,
        post=post,
        thread=thread,
        recordings=recordings.get(scale.stem, []),
        show_reference=any(
            r.get("reference")
            for r in recordings.get(scale.stem, [])
        ),
        construction=construction,
        details_text=details_text,
        ref_url=ref_url,
        contributor=contributor,
        has_scala_analysis=has_scala_analysis,
    )


def _render_scala_analysis_page(
    scale: ScaleData,
    commands: list[tuple[str, str]],
    env: Environment,
) -> str:
    tmpl = env.get_template("scala-analysis.html")
    return tmpl.render(scale=scale, commands=commands)


def _filter_page(
    page_title: str,
    scales: list[ScaleData],
    intro: str,
    env: Environment,
) -> str:
    tmpl = env.get_template("filter.html")
    return tmpl.render(
        page_title=page_title,
        scales=scales,
        intro=intro,
    )


def _mailing_list_name(scale: ScaleData) -> str:
    file_field = scale.info.raw["file"]
    return file_field.split("/")[0]


def _maqam_slug(maqam: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", maqam.lower().replace(" ", "-").replace(",", ""))


def _divisions_type(description: str) -> str:
    first_word = description.split()[0] if description else "Miscellaneous"
    # Normalise to lowercase URL slug
    return first_word.lower().replace("-", "")


def _write_recordings_json() -> None:
    """Write recordings.json — recordings.yaml as JSON with full scale page URLs."""
    data = yaml.safe_load(_RECORDINGS_PATH.read_text(encoding="utf-8"))
    output = []
    for album in data:
        entry = {k: album[k] for k in ("artist", "album", "year") if k in album}
        if "reference" in album:
            entry["reference"] = album["reference"]
        tracks = []
        for track in album.get("tracks", []):
            t = {k: v for k, v in track.items() if k != "scales"}
            t["scales"] = [
                f"{PROD_BASE}/scales/{stem}/" for stem in track.get("scales", [])
            ]
            tracks.append(t)
        entry["tracks"] = tracks
        output.append(entry)
    (SITE_DIR / "recordings.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _write_supporting_files(scales: list[ScaleData]) -> None:
    """Write sitemap.xml, robots.txt, llms.txt, scale-index.csv, scales.json, recordings.json."""
    prod_base = PROD_BASE

    # sitemap.xml — all pages except thin filter pages and scala analysis sub-pages
    _filter_prefixes = (
        "/notes/",                            # per-note-count filter pages
        "/limit/",                            # per-limit filter pages
        "/region/",                           # per-region (overlaps with /country/)
        "/source/cairo-congress/tonic_ref/",  # niche technical filter
    )
    all_urls = []
    for index_html in sorted(SITE_DIR.rglob("index.html")):
        rel = index_html.parent.relative_to(SITE_DIR)
        rel_str = str(rel).replace("\\", "/")
        url = "/" if rel_str == "." else f"/{rel_str}/"
        if "/scala/" in url:
            continue
        if any(url.startswith(p) for p in _filter_prefixes) and url not in {"/notes/", "/limit/"}:
            continue
        # /source/damusc/{ref_id}/ — numeric ID, not search-meaningful
        if url.startswith("/source/damusc/") and url != "/source/damusc/":
            continue
        all_urls.append(url)
    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in all_urls:
        escaped = u.replace("&", "&amp;")
        sitemap_lines.append(f"  <url><loc>{prod_base}{escaped}</loc></url>")
    sitemap_lines.append("</urlset>")
    (SITE_DIR / "sitemap.xml").write_text(
        "\n".join(sitemap_lines) + "\n", encoding="utf-8"
    )

    # robots.txt
    (SITE_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {prod_base}/sitemap.xml\n",
        encoding="utf-8",
    )

    # llms.txt — machine-readable summary for LLMs / crawlers
    llms_text = f"""\
# scale-library

> A collection of {len(scales)} microtonal scales from seven sources:
> Xenharmonikon (journal), the tuning mailing lists, the Database of
> Musical Scales (DaMuSc), Divisions of the Tetrachord, EDOs, the
> ORD-CC32 dataset of the Cairo Congress of Arab Music, and Contrib
> (scales contributed by users).

## Python package

If you are running in a sandbox with internet access, install the `scale-library`
Python package to get direct access to all scl files and the scale index without
fetching remote URLs:

```
pip install scale-library
```

```python
import scale_library as sl

scale_dir = sl.scale_dir()          # pathlib.Path to directory of all scl files
index_path = sl.scale_index_path()  # pathlib.Path to scale-index.csv
```

scale-index.csv columns:
- `directory`: source subdirectory (e.g. `xenharmonikon`, `mailing-lists`, `damusc`, `contrib`)
- `scl_file`: scl filename within that directory
- `notes`: number of notes (int)
- `period`: period in cents (float)
- `just`: `True` if all tones are pure ratios, `False` otherwise
- `limit`: prime limit (int); 0 if not just
- `description`: human-readable description of the scale
- `tones`: space-separated tone values (ratios e.g. `11/10 5/4 2/1` if just, cents if not)
- `reference`: bibliographic reference

## Data files

- {prod_base}/scale-index.csv: CSV index of all scales
- {prod_base}/scales.json: JSON array of all scales with tones
- {prod_base}/scale-cents.json: compact JSON dict of all scale stems mapped to cents arrays (no url; derive as /scales/{{stem}}/ on scalelibrary.org)
- {prod_base}/similar.json: JSON map of similar/parent/child scales (keyed by stem, top 10 by max cent diff)
- {prod_base}/recordings.json: JSON array of recordings linked to scales (album-centric; each track has a scales array of full scale page URLs)

## Browse

- {prod_base}/: Front page
- {prod_base}/scales/: All {len(scales)} scales
- {prod_base}/constructions/: Scale construction methods with examples
- {prod_base}/definitions/: Definitions of terms used on scale pages
- {prod_base}/source/mailing-lists/topics/: Index of mailing list threads containing scales

## Full content

- {prod_base}/constructions.md: All scale construction explanations and Python code. Load into context first when answering questions about microtonal theory or scale construction.
- {prod_base}/definitions.md: Definitions of terms used on scale pages (max diff, period, rotation, similar, parent/child).
- {prod_base}/mailing-list-threads.txt: Full text of all mailing list threads containing scales (for RAG / offline use)

## Scale page format

Each scale at `/scales/<source>/<slug>/` has (e.g. `/scales/xenharmonikon/xen02-wilson-arabic/`):
- `index.html`: human-readable page with tones, steps, Scale Workshop link
- `<slug>.scl`: raw Scala scl file
- `scale.json`: machine-readable JSON (description, notes, tones, steps, source, similar/parent/child scales with max cent diff)

Use `scale.json` for the authoritative tones/steps of a specific scale — the HTML page may include mailing list threads that contain other scales, so parsing the page prose is not a reliable way to identify which scale belongs to this URL.

scale.json schema:
- `stem`: `"directory/slug"` identifier (e.g. `"xenharmonikon/xen02-wilson-arabic"`)
- `description`: human-readable description
- `notes`: number of notes (int)
- `period`: period in cents (float)
- `just`: bool — whether all tones are pure ratios
- `limit`: prime limit (int); 0 if not just
- `source`: source name
- `reference`: bibliographic reference
- `tones`: list of `{{"scl": "<ratio or cents>", "cents": <float>}}` — one entry per tone
- `steps`: list of `{{"cents": <float>, "ratio": "<ratio or cents>"}}` — intervals between consecutive tones
- `similar`: list of `{{"stem": "...", "max_diff": <float>, "mode": <int>}}` — scales similar by max cent diff, with the mode (rotation) of that scale that is closest
- `parents`: list of `{{"stem": "...", "max_diff": <float>}}` — scales that are subsets of this one
- `children`: list of `{{"stem": "...", "max_diff": <float>}}` — scales that are supersets of this one

## Sources

- **Xenharmonikon**: peer-reviewed microtonal journal, 18 issues (1974–2006)
- **Mailing lists**: archived discussions from the Yahoo microtonal tuning communities
- **DaMuSc**: measured scales from world music traditions, with country metadata
- **Divisions of the Tetrachord**: catalog from John Chalmers' book
- **EDO**: equal divisions of the octave (1-EDO through 72-EDO)
- **Cairo Congress of Arab Music**: measured maqams from the 1932 Cairo Congress, from the ORD-CC32 dataset
- **Contrib**: scales contributed by users

## [info] block format

Each scl file ends with a machine-readable `[info]` block embedded in scl comment
lines (lines starting with `!`). The block uses INI-style `key = value` pairs.
This is a lightweight way to add structured metadata to any scl file. Example:

```
! [info]
! source = Xenharmonikon
! whole_number = 12
```
"""
    (SITE_DIR / "llms.txt").write_text(llms_text, encoding="utf-8")

    # scale-index.csv
    shutil.copy(REPO_ROOT / "scale-index.csv", SITE_DIR / "scale-index.csv")

    # scales.json — full array matching per-scale scale.json (without similar/parents/children)
    scales_data = [
        {
            "stem": s.stem,
            "description": s.description,
            "notes": s.notes,
            "period_cents": _tone_cents(s.tones[-1]),
            "just": s.just,
            "limit": s.limit,
            "source": s.info.source,
            "reference": s.reference,
            "url": f"{prod_base}/scales/{s.stem}/",
            "tones": [{"scl": t.string_rep, "cents": _tone_cents(t)} for t in s.tones],
        }
        for s in scales
    ]
    (SITE_DIR / "scales.json").write_text(
        json.dumps(scales_data, indent=2), encoding="utf-8"
    )

    # scale-cents.json — compact cents-only json
    scale_cents_data = {
        s.stem: [round(t.cents, SCALE_CENTS_PRECISION) for t in s.tones]
        for s in scales
    }
    (SITE_DIR / "scale-cents.json").write_text(
        json.dumps(scale_cents_data), encoding="utf-8"
    )

    # npm-package/scale-cents.json — copy for npm publishing
    shutil.copy(SITE_DIR / "scale-cents.json", REPO_ROOT / "npm-package" / "scale-cents.json")

    # similar.json — precomputed similar/parent/child (generated separately, committed to repo)
    shutil.copy(SIMILAR_JSON, SITE_DIR / "similar.json")

    # recordings.json — album-centric recording data with full scale URLs
    _write_recordings_json()

    # _headers — Cloudflare Pages CORS headers for JSON files
    (SITE_DIR / "_headers").write_text("/*.json\n  Access-Control-Allow-Origin: *\n", encoding="utf-8")


def build(regenerate_similar: bool = False, allow_missing_scala: bool = False) -> None:
    t0 = time.time()

    # ── 1. Load data ───────────────────────────────────────────────────────────
    print("Loading scale data…", file=sys.stderr)
    scales = load_all_scales()
    scales_by_stem = {s.stem: s for s in scales}
    total = len(scales)
    print(f"  {total} scales loaded", file=sys.stderr)

    recordings = _load_recordings()
    print(
        f"  {sum(len(v) for v in recordings.values())} recordings loaded",
        file=sys.stderr,
    )
    unknown = [stem for stem in recordings if stem not in scales_by_stem]
    if unknown:
        raise ValueError(f"recordings.yaml contains unknown scale stems: {unknown}")
    constructions, construction_lookup = _load_constructions(scales)
    print(f"  {len(constructions)} constructions loaded", file=sys.stderr)
    _validate_examples(constructions)
    print("  ✓ construction examples match SCL files", file=sys.stderr)
    _ensure_scala_analysis()

    xen_scales = [s for s in scales if s.info.source == "Xenharmonikon"]

    # ── 2. Similar scales ──────────────────────────────────────────────────────
    if regenerate_similar or not SIMILAR_JSON.exists():
        print("Computing similar/parent/child scales…", file=sys.stderr)
        similar_data = compute_similar(scales)
        SIMILAR_JSON.write_text(json.dumps(similar_data))
        print(f"  Done ({time.time()-t0:.1f}s) → {SIMILAR_JSON}", file=sys.stderr)
    else:
        print(f"Loading similar/parent/child from {SIMILAR_JSON}…", file=sys.stderr)
        similar_data = json.loads(SIMILAR_JSON.read_text())

    missing = [s.stem for s in scales if s.stem not in similar_data]
    if missing:
        raise ValueError(
            f"{len(missing)} scale(s) missing from similar.json — run with --regenerate-similar. "
            f"First missing: {missing[0]}"
        )

    env = make_env()

    # ── 3. Create site/ skeleton ───────────────────────────────────────────────
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir()
    static_out = SITE_DIR / "static"
    static_out.mkdir(exist_ok=True)
    for fname in ("style.css", "favicon.svg", "apple-touch-icon.png"):
        shutil.copy(STATIC_DIR / fname, static_out / fname)

    # ── 4. Scale pages ─────────────────────────────────────────────────────────
    print("Generating scale pages…", file=sys.stderr)
    for i, scale in enumerate(scales):
        if i % 500 == 0:
            print(f"  {i}/{total}…", file=sys.stderr)

        scala_commands = _load_scala_analysis(scale.stem)
        if scala_commands is None and not allow_missing_scala:
            raise FileNotFoundError(
                f"No scala-analysis data for {scale.stem!r}. "
                "Run with --allow-missing-scala to skip missing analyses."
            )
        html = render_scale_page(
            scale,
            scales_by_stem,
            env,
            similar_data,
            recordings,
            construction_lookup,
            has_scala_analysis=scala_commands is not None,
        )
        out_dir = SITE_DIR / "scales" / scale.stem
        write_page(out_dir / "index.html", html)

        # Copy scl file
        scl_src = REPO_ROOT / "scales" / scale.directory / scale.scl_file
        scl_dst = out_dir / scale.scl_file
        shutil.copy(scl_src, scl_dst)

        # scale.json
        scale_json = {
            "stem": scale.stem,
            "description": scale.description,
            "notes": scale.notes,
            "period": _tone_cents(scale.tones[-1]),
            "just": scale.just,
            "limit": scale.limit,
            "source": scale.info.source,
            "reference": scale.reference,
            "tones": [
                {"scl": t.string_rep, "cents": _tone_cents(t)} for t in scale.tones
            ],
            "steps": compute_steps(scale.tones),
            "similar": similar_data[scale.stem]["similar"],
            "parents": similar_data[scale.stem]["parents"],
            "children": similar_data[scale.stem]["children"],
        }
        (out_dir / "scale.json").write_text(
            json.dumps(scale_json, indent=2), encoding="utf-8"
        )

        # Scala analysis page (skipped if no analysis data available)
        if scala_commands is not None:
            sa_html = _render_scala_analysis_page(scale, scala_commands, env)
            write_page(out_dir / "scala" / "index.html", sa_html)

    print(f"  Scale pages done ({time.time()-t0:.1f}s)", file=sys.stderr)

    # ── 5. Filter pages ────────────────────────────────────────────────────────
    print("Generating filter pages…", file=sys.stderr)

    filter_tmpl = env.get_template("filter.html")

    def _write_filter(
        rel_path: str,
        title: str,
        subset: list[ScaleData],
        intro: str = "",
        meta_description: str = "",
        presorted: bool = False,
        **extra,
    ) -> None:
        # Filter to only scales that were actually loaded, sorted by filename
        filtered = (s for s in subset if s.stem in scales_by_stem)
        valid = list(filtered) if presorted else sorted(filtered, key=lambda s: s.stem)
        sources = {s.info.source for s in valid}
        html = filter_tmpl.render(
            page_title=title,
            scales=valid,
            intro=intro,
            meta_description=meta_description,
            show_source=len(sources) > 1,
            show_limit=any(s.just for s in valid),
            **extra,
        )
        write_page(SITE_DIR / rel_path / "index.html", html)

    # All scales
    _write_filter(
        "scales",
        "All scales",
        scales,
        f"{total} scales",
    )

    # Per-source (excluding mailing lists, which has its own landing page below)
    for src_name, src_title, src_slug, src_dir, src_desc in [
        (
            "Xenharmonikon",
            "Xenharmonikon",
            "xenharmonikon",
            "xenharmonikon",
            '<p>Scales from the 18 printed issues of <a href="https://www.xenharmonikon.org">Xenharmonikon</a>, an informal journal of experimental music, published 1974–2006.</p>',
        ),
        (
            "DaMuSc",
            "DaMuSc",
            "damusc",
            "damusc",
            '<p>Measured scales from the <a href="https://github.com/jomimc/DaMuSc">Database of Musical Scales (DaMuSc)</a>, a collection of scales from around the world with references to their sources.</p>',
        ),
        (
            "Divisions of the Tetrachord",
            "Divisions of the Tetrachord",
            "divisions-of-the-tetrachord",
            "divisions-of-the-tetrachord",
            '<p>Tetrachords from the catalog in chapter 9 of John Chalmers\' book <a href="https://eamusic.dartmouth.edu/~larry/published_articles/divisions_of_the_tetrachord/index.html"><em>Divisions of the Tetrachord</em></a>.</p>',
        ),
        (
            "EDO",
            "EDOs",
            "edos",
            "edos",
            "<p>Equal divisions of the octave from 1-EDO through 72-EDO.</p>",
        ),
    ]:
        subset = [s for s in scales if s.info.source == src_name]
        _write_filter(
            f"source/{src_slug}",
            src_title,
            subset,
            intro=f"{len(subset)} scales",
            description=src_desc,
        )

    contrib_scales = [s for s in scales if s.info.source == "contrib"]
    _write_filter(
        "source/contrib",
        "Contrib",
        contrib_scales,
        intro=f"{len(contrib_scales)} scales",
        description="<p>Scales people have contributed.</p>",
        show_contributor=True,
    )
    by_contributor: dict[str, list[ScaleData]] = defaultdict(list)
    for s in contrib_scales:
        by_contributor[s.info.raw["contributor"]].append(s)
    for contributor, subset in by_contributor.items():
        _write_filter(
            f"contributor/{contributor}",
            f"Contributor: {contributor}",
            subset,
            f"{len(subset)} scale{'s' if len(subset) != 1 else ''}",
        )

    # Cairo Congress of Arab Music
    cc_scales = [s for s in scales if s.info.source == "ORD-CC32"]
    cc_by_region: dict[str, list[ScaleData]] = defaultdict(list)
    for s in cc_scales:
        region = s.info.raw.get("region", "Unknown")
        cc_by_region[region].append(s)
    for region, subset in sorted(cc_by_region.items()):
        _write_filter(
            f"source/cairo-congress/{region}",
            f"Cairo Congress — {region}",
            subset,
            f"{len(subset)} scales",
        )
    cc_by_maqam: dict[str, list[ScaleData]] = defaultdict(list)
    for s in cc_scales:
        maqam = s.info.raw.get("maqam")
        if maqam:
            cc_by_maqam[maqam].append(s)
    for maqam, subset in sorted(cc_by_maqam.items()):
        _write_filter(
            f"source/cairo-congress/maqam/{_maqam_slug(maqam)}",
            f"Cairo Congress — {maqam}",
            subset,
            f"{len(subset)} scales",
        )
    for tonic_ref in ("annotated", "lowest_peak"):
        subset = [s for s in cc_scales if s.info.raw.get("tonic_ref") == tonic_ref]
        _write_filter(
            f"source/cairo-congress/tonic_ref/{tonic_ref}",
            f"Cairo Congress — tonic ref: {tonic_ref}",
            subset,
            f"{len(subset)} scales",
        )
    _write_filter(
        "source/cairo-congress",
        "Cairo Congress of Arab Music",
        cc_scales,
        intro=f"{len(cc_scales)} scales",
        description=(
            '<p>Maqams from the 1932 Cairo Congress of Arab Music, from the <a href="https://doi.org/10.5281/zenodo.15682346">ORD-CC32 dataset</a>.</p>'
            "<p>Tracks where the tonic was annotated in the dataset are marked"
            ' <a href="/source/cairo-congress/tonic_ref/annotated/">tonic_ref = annotated</a>;'
            " the remaining tracks did not have the tonic annotated, so their scl files omit the maqam"
            " from the filename and use the lowest detected peak"
            ' (<a href="/source/cairo-congress/tonic_ref/lowest_peak/">tonic_ref = lowest_peak</a>)'
            " as the tonic reference, so might not be the expected mode of the maqam.</p>"
        ),
    )

    # Per-mailing-list
    ml_by_list: dict[str, list[ScaleData]] = defaultdict(list)
    ml_topic_ids: set[tuple[str, int]] = set()
    for s in scales:
        if s.info.source == "Mailing lists":
            list_name = _mailing_list_name(s)
            ml_by_list[list_name].append(s)
            topic_id = s.info.raw.get("topic_id")
            if topic_id:
                ml_topic_ids.add((list_name, int(topic_id)))
    for list_name, subset in ml_by_list.items():
        _write_filter(
            f"source/mailing-lists/{list_name}",
            f"{list_name} mailing list",
            subset,
            f"{len(subset)} scales",
        )

    # Mailing lists landing page
    ml_subset = [s for s in scales if s.info.source == "Mailing lists"]
    _write_filter(
        "source/mailing-lists",
        "Mailing lists",
        ml_subset,
        intro=f"{len(ml_subset)} scales",
        description='<p>Scales extracted from the <a href="https://yahootuninggroupsultimatebackup.github.io">Yahoo tuning groups archive</a>, an archive of several tuning-related mailing lists. Browse by <a href="/source/mailing-lists/topics/">topic</a>.</p>',
    )

    # Per-mailing-list topic
    ml_by_topic: dict[tuple[str, int], list[ScaleData]] = defaultdict(list)
    for s in scales:
        if s.info.source == "Mailing lists":
            list_name = _mailing_list_name(s)
            topic_id = s.info.raw["topic_id"]
            ml_by_topic[(list_name, int(topic_id))].append(s)
    topics_data = []
    threads_for_dump: list[dict] = []
    for (list_name, topic_id), subset in ml_by_topic.items():
        subject = get_topic_subject(list_name, topic_id) or f"Topic {topic_id}"
        thread = get_thread(list_name, topic_id, topic_id)
        date_ts = int(thread[0]["date_ts"]) if thread else 0
        date = thread[0]["date"] if thread else ""
        topics_data.append(
            {
                "list_name": list_name,
                "topic_id": topic_id,
                "subject": subject,
                "count": len(subset),
                "date_ts": date_ts,
                "date": date,
            }
        )
        threads_for_dump.append(
            {
                "list_name": list_name,
                "topic_id": topic_id,
                "subject": subject,
                "date_ts": date_ts,
                "date": date,
                "thread": thread,
            }
        )
        _write_filter(
            f"source/mailing-lists/{list_name}/{topic_id}",
            f"Topic: {subject}",
            subset,
            f"{len(subset)} scales",
            thread=thread,
        )

    topics_data.sort(key=lambda t: (t["date_ts"] == 0, t["date_ts"]))
    topics_index_html = env.get_template("topics_index.html").render(
        topics=topics_data,
    )
    write_page(
        SITE_DIR / "source" / "mailing-lists" / "topics" / "index.html",
        topics_index_html,
    )

    # mailing-list-threads.txt — full thread content for LLMs / RAG pipelines
    threads_for_dump.sort(key=lambda t: (t["date_ts"] == 0, t["date_ts"]))
    dump_lines = [
        "# scale-library: mailing list threads",
        "",
        f"Full text of {len(threads_for_dump)} threads from the tuning mailing lists (Yahoo Tuning Groups) that contain extracted scales.",
        f"Scale data in machine-readable form: {PROD_BASE}/scales.json",
        "",
        "=" * 72,
        "",
    ]
    for t in threads_for_dump:
        url = f"{PROD_BASE}/source/mailing-lists/{t['list_name']}/{t['topic_id']}/"
        dump_lines.append(
            f"List: {t['list_name']}  |  Date: {t['date']}  |  URL: {url}"
        )
        dump_lines.append(f"Subject: {t['subject']}")
        extracted = ", ".join(
            s.scl_file for s in ml_by_topic[(t["list_name"], t["topic_id"])]
        )
        dump_lines.append(f"Extracted scales: {extracted}")
        dump_lines.append("")
        if t["thread"]:
            for msg in t["thread"]:
                dump_lines.append(f"From: {msg['author']} ({msg['date']})")
                dump_lines.append(msg["body"])
                dump_lines.append("")
        dump_lines.append("-" * 72)
        dump_lines.append("")
    (SITE_DIR / "mailing-list-threads.txt").write_text(
        "\n".join(dump_lines), encoding="utf-8"
    )

    # Per-Xenharmonikon issue
    xen_by_issue: dict[str, list[ScaleData]] = defaultdict(list)
    for s in scales:
        if s.info.source == "Xenharmonikon":
            xen_by_issue[s.info.raw["whole_number"]].append(s)
    for issue, subset in sorted(
        xen_by_issue.items(), key=lambda kv: int(str(kv[0]).split()[0])
    ):
        issue_int = int(str(issue).split()[0])
        prefix = f"xen{issue_int:02d}"
        _, display = XEN_JOURNAL.get(prefix, (issue, f"Xenharmonikon {issue}"))
        _write_filter(
            f"source/xenharmonikon/{_xen_issue_slug(issue)}",
            f"Xenharmonikon {issue}",
            subset,
            f"{len(subset)} scales",
        )
        # Per-article (issue + author, with sub-article pages for multi-article authors)
        by_author: dict[str, list[ScaleData]] = defaultdict(list)
        for s in subset:
            by_author[_xen_author_slug(s.scl_file)].append(s)
        for author_slug, art_scales in by_author.items():
            author_name = AUTHOR_NAMES.get(author_slug, author_slug)
            page_title = f"Xenharmonikon {issue} — {author_name}"
            has_article_field = any(s.info.raw.get("article") for s in art_scales)
            issue_slug = _xen_issue_slug(issue)
            if has_article_field:
                # Combined page preserves the existing URL
                _write_filter(
                    f"source/xenharmonikon/{issue_slug}/{author_slug}",
                    page_title,
                    art_scales,
                    f"{len(art_scales)} scales",
                )
                # Per-article sub-pages
                by_article: dict[str, list[ScaleData]] = defaultdict(list)
                for s in art_scales:
                    by_article[s.info.raw.get("article", "")].append(s)
                for article_slug, article_scales in by_article.items():
                    if not article_slug:
                        continue
                    article_key = f"{prefix}-{author_slug}-{article_slug}"
                    article_title = XEN_ARTICLE_TITLES.get(article_key)
                    _write_filter(
                        f"source/xenharmonikon/{issue_slug}/{author_slug}-{article_slug}",
                        page_title,
                        article_scales,
                        f"{len(article_scales)} scales",
                        article_title=article_title,
                        article_url=XEN_ARTICLE_URLS.get(article_key),
                    )
            else:
                article_key = f"{prefix}-{author_slug}"
                article_title = XEN_ARTICLE_TITLES.get(article_key)
                _write_filter(
                    f"source/xenharmonikon/{issue_slug}/{author_slug}",
                    page_title,
                    art_scales,
                    f"{len(art_scales)} scales",
                    article_title=article_title,
                    article_url=XEN_ARTICLE_URLS.get(article_key),
                )

    # Per-author (cross-journal)
    by_author_all: dict[str, list[ScaleData]] = defaultdict(list)
    for s in scales:
        if s.info.source == "Xenharmonikon":
            by_author_all[_xen_author_slug(s.scl_file)].append(s)
    for author_slug, subset in by_author_all.items():
        author_name = AUTHOR_NAMES.get(author_slug, author_slug)
        _write_filter(
            f"author/{author_slug}",
            author_name,
            subset,
            f"{len(subset)} scales",
        )

    # Per-Divisions type
    div_by_type: dict[str, list[ScaleData]] = defaultdict(list)
    for s in scales:
        if s.info.source == "Divisions of the Tetrachord":
            div_by_type[_divisions_type(s.description)].append(s)
    for div_type, subset in div_by_type.items():
        display_type = subset[0].description.split()[0] if subset else div_type
        _write_filter(
            f"source/divisions-of-the-tetrachord/{div_type}",
            f"{display_type} tetrachords",
            subset,
            f"{len(subset)} scales",
        )

    # Per-country and per-region (DaMuSc + ORD-CC32)
    damusc_scales = [s for s in scales if s.info.source == "DaMuSc"]

    # Build country slug → (display_name, region) lookup
    country_slug_info: dict[str, tuple[str, str]] = {}
    for s in damusc_scales:
        country = s.info.raw["country"]
        slug = country.replace(" ", "_")
        if slug not in country_slug_info:
            country_slug_info[slug] = (country, _COUNTRY_REGION[country])

    # ORD-CC32 regions are country names
    for s in cc_scales:
        country = s.info.raw.get("region")
        if not country:
            continue
        slug = country.replace(" ", "_")
        if slug not in country_slug_info:
            country_slug_info[slug] = (country, _COUNTRY_REGION[country])

    by_country: dict[str, list[ScaleData]] = defaultdict(list)
    by_region: dict[str, list[ScaleData]] = defaultdict(list)
    for s in damusc_scales:
        slug = s.info.raw["country"].replace(" ", "_")
        display, region = country_slug_info[slug]
        by_country[slug].append(s)
        by_region[region].append(s)
    for s in cc_scales:
        country = s.info.raw.get("region")
        if not country:
            continue
        slug = country.replace(" ", "_")
        display, region = country_slug_info[slug]
        by_country[slug].append(s)
        by_region[region].append(s)

    # Add contrib scales with country
    for s in contrib_scales:
        country = s.info.raw.get("country")
        if not country:
            continue
        slug = country.replace(" ", "_")
        if slug not in country_slug_info:
            country_slug_info[slug] = (country, _COUNTRY_REGION[country])  # raises KeyError if country unrecognised
        _, region = country_slug_info[slug]
        by_country[slug].append(s)
        by_region[region].append(s)

    # Country index page
    countries_sorted = sorted(
        country_slug_info.items(), key=lambda kv: -len(by_country[kv[0]])
    )
    countries_for_tmpl = [
        {"slug": slug, "display": disp, "count": len(by_country[slug])}
        for slug, (disp, _) in countries_sorted
    ]
    country_index_html = env.get_template("country_index.html").render(
        page_title="Browse by country",
        countries=countries_for_tmpl,
    )
    write_page(SITE_DIR / "country" / "index.html", country_index_html)

    for country_slug, subset in by_country.items():
        display, _ = country_slug_info.get(country_slug, (country_slug, "Unknown"))
        _write_filter(
            f"country/{country_slug}",
            display,
            subset,
            f"{len(subset)} scales",
        )

    for region, subset in by_region.items():
        _write_filter(
            f"region/{region}",
            f"{region} scales",
            subset,
            f"{len(subset)} scales",
        )

    # Per-DaMuSc reference
    by_ref: dict[int, list[ScaleData]] = defaultdict(list)
    for s in damusc_scales:
        ref_id = s.info.raw.get("ref_id")
        if ref_id is not None:
            by_ref[ref_id].append(s)
    for ref_id, subset in by_ref.items():
        ref_text = subset[0].reference if subset else f"Reference {ref_id}"
        short = f"{len(subset)} scales from: {ref_text[:120]}{'…' if len(ref_text) > 120 else ''}"
        _write_filter(
            f"source/damusc/{ref_id}",
            f"Reference {ref_id}",
            subset,
            intro=f"{len(subset)} scales from: {ref_text}",
            meta_description=short,
        )

    # Per-notes
    by_notes: dict[int, list[ScaleData]] = defaultdict(list)
    for s in scales:
        by_notes[s.notes].append(s)
    for n, subset in sorted(by_notes.items()):
        _write_filter(
            f"notes/{n}",
            f"{n}-note scales",
            subset,
            f"{len(subset)} scales",
        )

    # Notes index page
    notes_index_html = env.get_template("notes_index.html").render(
        page_title="Browse by scale size",
        notes=[{"n": n, "count": len(subset)} for n, subset in sorted(by_notes.items())],
    )
    write_page(SITE_DIR / "notes" / "index.html", notes_index_html)

    # Per-limit (just scales only)
    by_limit: dict[int, list[ScaleData]] = defaultdict(list)
    for s in scales:
        if s.just and s.limit:
            by_limit[s.limit].append(s)
    for limit, subset in sorted(by_limit.items()):
        _write_filter(
            f"limit/{limit}",
            f"{limit}-limit scales",
            subset,
            f"{len(subset)} scales",
        )

    # Limit index page
    limit_index_html = env.get_template("limit_index.html").render(
        page_title="Browse by JI limit",
        limits=[{"limit": lim, "count": len(subset)} for lim, subset in sorted(by_limit.items())],
    )
    write_page(SITE_DIR / "limit" / "index.html", limit_index_html)

    # Scales with recordings
    recording_scales = sorted(
        (scales_by_stem[stem] for stem in recordings if stem in scales_by_stem),
        key=lambda s: s.stem,
    )
    _write_filter(
        "recordings",
        "Scales with recordings",
        recording_scales,
        f"{len(recording_scales)} scales",
        presorted=True,
        all_recordings_url="/all-recordings/",
    )

    # All recordings page (grouped by artist then album)
    album_map: dict[tuple, list] = {}
    for stem, recs in recordings.items():
        scale = scales_by_stem.get(stem)
        if scale is None:
            continue
        for rec in recs:
            key = (
                rec.get("artist", ""),
                rec.get("year", 9999),
                rec.get("album") or rec.get("title", ""),
            )
            album_map.setdefault(key, []).append(
                {
                    "title": rec.get("title", ""),
                    "url": rec.get("url", ""),
                    "scale": scale,
                }
            )
    artist_map: dict[str, list] = {}
    for (artist, year, album), tracks in sorted(album_map.items()):
        artist_map.setdefault(artist, []).append(
            {
                "year": year,
                "album": album,
                "tracks": sorted(tracks, key=lambda t: t["title"]),
            }
        )
    artists = [{"artist": a, "albums": al} for a, al in sorted(artist_map.items())]
    all_recordings_html = env.get_template("all_recordings.html").render(
        artists=artists
    )
    write_page(SITE_DIR / "all-recordings" / "index.html", all_recordings_html)

    # Definitions page
    definitions_md_path = Path(__file__).parent / "definitions.md"
    definitions_md = definitions_md_path.read_text(encoding="utf-8")
    definitions_content = md.markdown(
        definitions_md, extensions=["fenced_code", "tables"]
    )
    definitions_html = env.get_template("definitions.html").render(
        content=definitions_content
    )
    write_page(SITE_DIR / "definitions" / "index.html", definitions_html)
    (SITE_DIR / "definitions.md").write_text(definitions_md, encoding="utf-8")

    # Construction pages
    construction_tmpl = env.get_template("construction.html")
    constructions_index_html = env.get_template("constructions.html").render(
        constructions=constructions
    )
    write_page(SITE_DIR / "constructions" / "index.html", constructions_index_html)
    for c in constructions:
        html = construction_tmpl.render(
            title=c["title"],
            content=c["content"],
            python_code=c.get("python_code"),
            examples=c.get("examples", {}),
            scales=c["scales"],
        )
        write_page(SITE_DIR / "constructions" / c["slug"] / "index.html", html)

    # constructions.md — all construction prose + Python for RAG / offline use
    parts = ["# Scale constructions\n"]
    for c in constructions:
        md_path = _CONSTRUCTIONS_DIR / f"{c['slug']}.md"
        py_path = _CONSTRUCTIONS_DIR / f"{c['slug'].replace('-', '_')}.py"
        raw = md_path.read_text(encoding="utf-8").strip()
        raw = raw.replace('<pre class="narrow">', "```").replace("</pre>", "```")
        parts.append(raw)
        parts.append("## Python code")
        parts.append(
            f"```python\n{py_path.read_text(encoding='utf-8').strip()}\n```"
        )
        parts.append("\n---\n")
    (SITE_DIR / "constructions.md").write_text("\n\n".join(parts), encoding="utf-8")

    # ── 6. Front page ──────────────────────────────────────────────────────────
    source_counts = {
        "Xenharmonikon": sum(1 for s in scales if s.info.source == "Xenharmonikon"),
        "Mailing lists": sum(1 for s in scales if s.info.source == "Mailing lists"),
        "DaMuSc": sum(1 for s in scales if s.info.source == "DaMuSc"),
        "Divisions of the Tetrachord": sum(
            1 for s in scales if s.info.source == "Divisions of the Tetrachord"
        ),
        "EDO": sum(1 for s in scales if s.info.source == "EDO"),
        "ORD-CC32": sum(1 for s in scales if s.info.source == "ORD-CC32"),
        "contrib": sum(1 for s in scales if s.info.source == "contrib"),
    }
    notes_counts = Counter(s.notes for s in scales)
    index_html = env.get_template("index.html").render(
        total=total,
        source_counts=source_counts,
        notes_counts=notes_counts,
    )
    write_page(SITE_DIR / "index.html", index_html)

    # 404 page
    write_page(
        SITE_DIR / "404.html",
        env.get_template("404.html").render(),
    )

    # ── 7. Supporting files ────────────────────────────────────────────────────
    _write_supporting_files(scales)

    # ── 8. Build assertions ────────────────────────────────────────────────────
    print("Checking assertions…", file=sys.stderr)
    scale_pages = list((SITE_DIR / "scales").rglob("index.html"))
    # Exclude the /scales/index.html itself and scala/index.html pages
    scale_pages = [p for p in scale_pages if p.parent.name not in ("scales", "scala")]
    assert (
        len(scale_pages) == total
    ), f"Expected {total} scale pages, got {len(scale_pages)}"
    print(f"  ✓ {len(scale_pages)} scale pages generated", file=sys.stderr)

    sa_pages = list((SITE_DIR / "scales").rglob("scala/index.html"))
    if not allow_missing_scala:
        assert (
            len(sa_pages) == total
        ), f"Expected {total} scala-analysis pages, got {len(sa_pages)}"
    print(f"  ✓ {len(sa_pages)} scala-analysis pages generated", file=sys.stderr)

    scl_copies = list((SITE_DIR / "scales").rglob("*.scl"))
    assert (
        len(scl_copies) == total
    ), f"Expected {total} scl copies, got {len(scl_copies)}"
    print(f"  ✓ {len(scl_copies)} scl files copied", file=sys.stderr)

    scale_jsons = list((SITE_DIR / "scales").rglob("scale.json"))
    assert (
        len(scale_jsons) == total
    ), f"Expected {total} scale.json files, got {len(scale_jsons)}"
    print(f"  ✓ {len(scale_jsons)} scale.json files generated", file=sys.stderr)

    for fname in (
        "sitemap.xml",
        "robots.txt",
        "llms.txt",
        "mailing-list-threads.txt",
        "scale-index.csv",
        "scales.json",
        "similar.json",
        "recordings.json",
    ):
        assert (SITE_DIR / fname).exists(), f"Missing {fname}"
    print(
        "  ✓ sitemap.xml, robots.txt, llms.txt, mailing-list-threads.txt, scale-index.csv, scales.json, similar.json, recordings.json",
        file=sys.stderr,
    )
    ET.parse(SITE_DIR / "sitemap.xml")
    print("  ✓ sitemap.xml is valid XML", file=sys.stderr)

    scales_json_data = json.loads((SITE_DIR / "scales.json").read_text())
    assert (
        len(scales_json_data) == total
    ), f"scales.json has {len(scales_json_data)} entries, expected {total}"
    print(f"  ✓ scales.json is valid JSON with {len(scales_json_data)} entries", file=sys.stderr)

    json.loads((SITE_DIR / "similar.json").read_text())
    print("  ✓ similar.json is valid JSON", file=sys.stderr)

    json.loads((SITE_DIR / "recordings.json").read_text())
    print("  ✓ recordings.json is valid JSON", file=sys.stderr)

    with (SITE_DIR / "scale-index.csv").open(encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))
    assert (
        len(csv_rows) == total
    ), f"scale-index.csv has {len(csv_rows)} rows, expected {total}"
    print(f"  ✓ scale-index.csv has {len(csv_rows)} rows", file=sys.stderr)

    _CLOUDFLARE_PAGES_FREE_LIMIT = 20_000
    file_count = sum(1 for p in SITE_DIR.rglob("*") if p.is_file())
    print(f"  {file_count} files in site/", file=sys.stderr)
    if file_count > _CLOUDFLARE_PAGES_FREE_LIMIT:
        raise SystemExit(
            f"Build failed: {file_count} files exceeds Cloudflare Pages free plan limit of {_CLOUDFLARE_PAGES_FREE_LIMIT}."
            " Upgrade to a paid plan and set PAGES_WRANGLER_MAJOR_VERSION=4."
        )

    _CLOUDFLARE_MAX_FILE_SIZE = 25 * 1024 * 1024
    too_large = [
        p
        for p in SITE_DIR.rglob("*")
        if p.is_file() and p.stat().st_size > _CLOUDFLARE_MAX_FILE_SIZE
    ]
    if too_large:
        raise SystemExit(
            f"Build failed: files exceed 25 MiB Cloudflare Pages limit: {too_large}"
        )
    print("  ✓ all files under 25 MiB", file=sys.stderr)

    print("Checking links…", file=sys.stderr)
    if check_links(SITE_DIR) != 0:
        raise SystemExit("Build failed: broken links found")
    print("  ✓ all links OK", file=sys.stderr)

    elapsed = time.time() - t0
    print(f"\nBuild complete in {elapsed:.1f}s  →  {SITE_DIR}/", file=sys.stderr)
