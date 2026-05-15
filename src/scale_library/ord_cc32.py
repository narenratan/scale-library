"""
Create scl files from the Open Research Dataset of the 1932 Cairo Congress of
Arab Music (ORD-CC32).

For ORD-CC32 see https://zenodo.org/records/15682346

The dataset contains per-track pickle files with pitch histogram data.
`maxima_locs_cent` is in an octave-warped space referenced to 55 Hz (not the
tonic). For the 67 manually annotated tracks `tonic_pitch_cents` gives the
tonic's position in that space; for the remaining 266 tracks we use the lowest
detected peak as the reference.

Run from the scale-library root with the ord-cc32 data in sources/ORD-CC32, or
set the ORD_CC32_DIR environment variable to point to the data directory.
"""

import csv
import logging
import os
import pickle
import re
import shutil
import textwrap
from pathlib import Path

from scale_library import SCALES_DIR, utils

DATA_DIR = Path(__file__).parents[2] / "sources" / "ORD-CC32"
OUTPUT_DIR = SCALES_DIR / "cairo-congress"

DATASET_DOI = "https://doi.org/10.5281/zenodo.15682346"
REFERENCE = (
    "Bozkurt, B. (2025). An Open Research Dataset of the 1932 Cairo Congress"
    " of Arab Music. arXiv:2506.14503."
)

# Map French/alternative region names from the dataset to English
_REGION_MAP = {
    "Maroc": "Morocco",
}

logger = logging.getLogger(__name__)


def _sanitize(s):
    return re.sub(r"_+", "_", re.sub(r"[^\w]", "_", s)).strip("_")


def _make_filename(cd, track_num, maqam, region, tonic_ref):
    region_s = _sanitize(region) if region else "unknown"
    if tonic_ref == "annotated":
        maqam_s = _sanitize(maqam) if maqam and maqam != "NA" else "unknown"
        return f"CD{cd:02d}_{track_num:02d}_{maqam_s}_{region_s}.scl"
    else:
        return f"CD{cd:02d}_{track_num:02d}_{region_s}.scl"


def _parse_path(path_str):
    """Extract CD number and track number from path like 'CD 1/01. Title'."""
    parts = path_str.split("/")
    cd_str = parts[0]  # e.g. "CD 1"
    track_str = parts[1]  # e.g. "01. Title"

    cd_num = int(re.search(r"\d+", cd_str).group())
    track_num = int(re.match(r"(\d+)", track_str).group(1))
    return cd_num, track_num


def _make_description(title, artist, maqam, region):
    maqam_part = maqam if maqam and maqam != "NA" else "unknown maqam"
    artist_part = f" - {artist}" if artist else ""
    return f"{title}{artist_part} ({maqam_part}, {region})"


def _shift_peaks(maxima_cents, tonic_cents):
    """
    Subtract tonic_cents from each peak (mod 1200) and return sorted result.
    The tonic ends up at 0¢ and is omitted (it's implicit in SCL format).
    """
    shifted = sorted((c - tonic_cents) % 1200.0 for c in maxima_cents)
    return [c for c in shifted if c > 0.0]


def track_to_scl(row):
    """Generate SCL text for a single track. Returns (filename, scl_text)."""
    path_str = row["path"]  # e.g. "CD 1/01. Les nuits damour"
    maqam = row["mode"].strip()
    region = _REGION_MAP.get(row["region"].strip(), row["region"].strip())
    tonic_hz = row["tonic_Hz"].strip()
    link = row["link"].strip()
    title = row["mb_trackTitle"].strip() if row.get("mb_trackTitle") else path_str.split("/")[-1]
    artist = row["artist"].strip() if row.get("artist") else ""

    mbid = link.split("/")[-1] if link else ""

    cd_num, track_num = _parse_path(path_str)

    pickle_path = DATA_DIR / (path_str + ".pickle")

    with open(pickle_path, "rb") as f:
        d = pickle.load(f)

    maxima = d["maxima_locs_cent"]
    if "tonic_pitch_cents" in d:
        tonic_cents = d["tonic_pitch_cents"]
        tonic_ref = "annotated"
    else:
        tonic_cents = float(min(maxima))
        tonic_ref = "lowest_peak"

    pitches = _shift_peaks(maxima, tonic_cents) + [1200.0]

    filename = _make_filename(cd_num, track_num, maqam, region, tonic_ref)
    description = _make_description(title, artist, maqam, region)

    tones = [utils.Tone(p) for p in pitches]

    info = {"source": "ORD-CC32"}
    info["doi"] = DATASET_DOI
    info["cd"] = str(cd_num)
    info["track"] = str(track_num)
    if mbid:
        info["mbid"] = mbid
    if maqam and maqam != "NA":
        info["maqam"] = maqam
    if region:
        info["region"] = region
    info["tonic_ref"] = tonic_ref
    if tonic_hz:
        info["tonic_hz"] = tonic_hz

    comments = textwrap.wrap(REFERENCE)

    scl_text = utils.build_scl(filename, description, tones, info, comments=comments)
    return filename, scl_text


def main():
    logger.info("Building ORD-CC32 scales")

    assert any(DATA_DIR.iterdir()), "No ORD-CC32 data - see https://zenodo.org/records/15682346"

    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    OUTPUT_DIR.mkdir()

    metadata_path = DATA_DIR / "allfiles_metadata.csv"
    with open(metadata_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    filenames_seen = set()
    references = {}
    count = 0
    for row in rows:
        filename, scl_text = track_to_scl(row)
        if filename in filenames_seen:
            logger.warning("Duplicate filename skipped: %s", filename)
            continue
        filenames_seen.add(filename)
        (OUTPUT_DIR / filename).write_text(scl_text, encoding="utf-8")
        references[filename] = REFERENCE
        count += 1

    logger.info("Written %d ORD-CC32 scl files", count)
    return utils.check_scl_dir(OUTPUT_DIR), references


if __name__ == "__main__":
    utils.setup_logging()
    main()
