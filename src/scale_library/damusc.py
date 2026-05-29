"""
Create scl files from scale data in DaMuSc (database of musical scales).

For DaMuSc see https://github.com/jomimc/DaMuSc

"""

import logging
import re
import shutil
import textwrap
from pathlib import Path
from collections import Counter

import pandas as pd
import tuning_library as tl

from scale_library import SCALES_DIR, SOURCES_DIR, utils

DAMUSC_DIR = SOURCES_DIR / "DaMuSc"
OUTPUT_DIR = SCALES_DIR / "database-of-musical-scales"
DAMUSC_SOURCES_CSV = Path(__file__).parent / "damusc_sources.csv"

logger = logging.getLogger(__name__)

DUPE_TOLERANCE_CENTS = 5.0


class Columns:
    authors = "Authors"
    country = "Country"
    culture = "Culture"
    instrument = "Instrument"
    interval = "interval"
    measured_id = "MeasuredID"
    name = "Name"
    octave_modified = "Octave_modified"
    primary_source = "Primary_source?"
    ref_id = "RefID"
    reference = "Reference"
    region = "Region"
    scale_id = "ScaleID"
    step = "step"
    theory = "Theory"
    theory_id = "TheoryID"
    title = "Title"
    tonic_intervals = "tonic_intervals"
    tuning = "Tuning"
    year = "Year"


C = Columns


def _parse_cumulative_cents(intervals_str):
    steps = [float(x) for x in intervals_str.strip().split(";")]
    cumulative = []
    total = 0.0
    for s in steps:
        total += s
        cumulative.append(total)
    return tuple(cumulative)


def _find_near_dupe_ids(measured_scales):
    """Return set of MeasuredIDs to exclude: non-primary scales that are
    near-identical (within DUPE_TOLERANCE_CENTS) to a primary source scale."""
    primary_cents = {}
    for _, row in measured_scales[measured_scales[C.primary_source] == "Y"].iterrows():
        primary_cents[row[C.measured_id]] = _parse_cumulative_cents(row["Intervals"])

    exclude = set()
    for _, row in measured_scales[measured_scales[C.primary_source] == "N"].iterrows():
        cents = _parse_cumulative_cents(row["Intervals"])
        for pcents in primary_cents.values():
            if len(cents) == len(pcents) and max(abs(a - b) for a, b in zip(cents, pcents)) <= DUPE_TOLERANCE_CENTS:
                exclude.add(row[C.measured_id])
                break
    return exclude


_COUNTRY_CORRECTIONS = {
    "Solomon Is.": "Solomon_Islands",
    "Eq. Guinea": "Equatorial_Guinea",
    "Central African Rep.": "Central_African_Republic",
    "Dem. Rep. Congo": "DR_Congo",
}


def _make_base_stem(row):
    def clean(s):
        return (re.sub(r' -\s*', '_', s)
                 .replace(".", "")
                 .replace("'", "").replace("\u2019", "")
                 .replace(" ", "_")
                 .replace("/", "_")
                 .replace("&", "and")
                 .replace("[", "")
                 .replace("]", ""))

    def pad_numbers(s):
        return re.sub(r'\d+', lambda m: m.group().zfill(2), s)

    raw_country = row[C.country]
    country = _COUNTRY_CORRECTIONS.get(raw_country, clean(raw_country))

    name_clean = clean(row[C.name])
    # Strip redundant leading "Country_" prefix that DaMuSc uses in some names
    if name_clean.startswith(country + "_"):
        name_clean = name_clean[len(country) + 1:]

    # Enrich bare catalogue numbers with the instrument name
    instrument = _normalise_instrument(row[C.instrument])
    if re.match(r'^\d+$', name_clean) and instrument:
        instrument_stem = clean(instrument).replace(" ", "_")
        name_clean = f"{instrument_stem}_{name_clean}"

    name = pad_numbers(name_clean)
    return country + "_" + name


def _assign_filenames(df):
    """Return dict MeasuredID -> filename, using _a/_b suffixes for clashes."""
    stems = {row[C.measured_id]: _make_base_stem(row) for _, row in df.iterrows()}
    stem_counts = Counter(stems.values())
    clash_stems = {s for s, count in stem_counts.items() if count > 1}

    filenames = {}
    clash_counter = Counter()
    for mid in sorted(stems):  # sorted by MeasuredID so lower ID gets _a
        stem = stems[mid]
        if stem in clash_stems:
            idx = clash_counter[stem]
            clash_counter[stem] += 1
            filenames[mid] = f"{stem}_{chr(ord('a') + idx)}.scl"
        else:
            filenames[mid] = f"{stem}.scl"
    return filenames


_INSTRUMENT_CORRECTIONS = {
    # Encoding corruption: spilåpipa (Swedish bagpipe), mangled as UTF-8 mojibake
    "spil\ufffd\xc3\ufffd\xa5pipa": "spilåpipa",
    # Typo
    "Gamband and Bonang and Saron": "Gambang and Bonang and Saron",
    # Capitalisation
    "saron demung or gender barung": "Saron Demung or Gender Barung",
    "Ranat ek": "Ranat Ek",
}


def _normalise_instrument(instrument):
    s = str(instrument)
    if s in ("N/A", "nan", "", "Varied"):
        return None
    return _INSTRUMENT_CORRECTIONS.get(s, s)


def _display_country(raw_country):
    """Human-readable country name, consistent with the filename stem."""
    return _COUNTRY_CORRECTIONS.get(raw_country, raw_country).replace("_", " ")


def _make_description(row):
    name = row[C.name].replace("_", " ")
    country = _display_country(row[C.country])
    instrument = _normalise_instrument(row[C.instrument])
    if instrument:
        return f"{name} ({instrument}), {country}"
    return f"{name}, {country}"


def measured_df_to_scl(df, filename, source_info):
    assert len(df) == 1
    df = df.copy()
    info = df.squeeze()

    df[C.step] = df["Intervals"].str.split(";")
    scale_df = df.explode(C.step)
    scale_df[C.step] = scale_df[C.step].astype(float)
    scale_df[C.interval] = scale_df.groupby("MeasuredID")[C.step].transform("cumsum")
    intervals = [" " + x for x in scale_df[C.interval].round(6).astype(str)]

    if info[C.octave_modified] == "Y":
        intervals.append(" 1200.0 ! Octave added to measured scale")

    description = _make_description(info)

    reference_text = source_info.get("best_reference") or source_info.get("Reference_Full") or info[C.reference]
    reference_lines = ["! " + x for x in textwrap.wrap(reference_text)]

    info_lines = [
        "! [info]",
        "! source = DaMuSc",
        f"! measured_id = {info[C.measured_id]}",
        f"! ref_id = {info[C.ref_id]}",
        f"! country = {_display_country(info[C.country])}",
    ]
    doi = source_info.get("doi", "")
    if doi and str(doi) != "nan":
        info_lines.append(f"! doi = https://doi.org/{doi}")

    scl_lines = (
        [
            f"! {filename}",
            "!",
            description,
            f" {len(intervals)}",
            "!",
        ]
        + intervals
        + ["!"]
        + reference_lines
        + ["!"]
        + info_lines
    )

    scl_text = "\n".join(scl_lines) + "\n"

    return scl_text


def write_measured_scales():
    measured_scales = pd.read_csv(DAMUSC_DIR / "Data/measured_scales.csv")
    sources = pd.read_csv(DAMUSC_SOURCES_CSV)
    source_info = {str(row["RefID"]): row.to_dict() for _, row in sources.iterrows()}

    exclude_ids = _find_near_dupe_ids(measured_scales)
    logger.info("Excluding %d near-duplicate non-primary scales", len(exclude_ids))

    df = measured_scales[~measured_scales[C.measured_id].isin(exclude_ids)].copy()
    filenames = _assign_filenames(df)

    references = {}
    for mid, scale_df in df.groupby(C.measured_id):
        filename = filenames[mid]
        ref_id = str(scale_df.iloc[0][C.ref_id])
        info = source_info.get(ref_id, {})
        scl_text = measured_df_to_scl(scale_df, filename, info)
        (OUTPUT_DIR / filename).write_text(scl_text)
        references[filename] = info["best_reference"]

    return references


def theory_df_to_scl(df):
    assert len(df) == 1
    df = df.copy()
    info = df.squeeze()

    df[C.interval] = df[C.tonic_intervals].str.split(";")
    scale_df = df.explode(C.interval)
    scale_df[C.interval] = scale_df[C.interval].astype(float)
    intervals = [" " + x for x in scale_df[C.interval].round(6).astype(str)]

    filename = (
        (info[C.theory_id] + "_" + info[C.name] + "_" + info[C.tuning] + ".scl")
        .replace(" ", "_")
        .replace("/", "_")
    )

    reference_lines = ["! " + x for x in textwrap.wrap(info[C.reference])]

    scl_lines = (
        [
            f"! {filename}",
            "!",
            f"Theory scale {info[C.theory_id]} in DaMuSc in {info[C.tuning]}",
            f" {len(intervals)}",
            "!",
        ]
        + intervals
        + ["!"]
        + reference_lines
        + [
            "!",
            "! [info]",
            "! source = DaMuSc",
            f"! scale_id = {info[C.scale_id]}",
            f"! theory_id = {info[C.theory_id]}",
            f"! tuning = {info[C.tuning]}",
            f"! ref_id = {info[C.ref_id]}",
        ]
    )

    scl_text = "\n".join(scl_lines) + "\n"

    return filename, scl_text


def write_theory_scales():
    octave_scales = pd.read_csv(DAMUSC_DIR / "Data/octave_scales.csv")
    theory_scales = pd.read_csv(DAMUSC_DIR / "Data/theory_scales.csv")
    sources = pd.read_csv(DAMUSC_DIR / "MetaData/sources.csv")

    theory_octave_scales = octave_scales.loc[octave_scales[C.theory] == "Y"]

    # TODO: check rows with multiple references per theory ID
    ref_df = theory_scales[[C.theory_id, C.reference, C.ref_id]].drop_duplicates(
        subset=[C.theory_id]
    )
    df = theory_octave_scales.merge(ref_df)
    assert len(df) == len(theory_octave_scales)
    df2 = df.merge(sources[[C.ref_id, C.authors, C.year, C.title]].drop_duplicates())
    assert len(df2) == len(df)

    df3 = df2.loc[
        ~(
            df2[C.culture].isin({"Diatonic modes", "Western Classical", "Jazz"})
            | (df2[C.tuning] == "12-tet")
        )
    ]

    for _, scale_df in df3.groupby(C.scale_id):
        filename, scl_text = theory_df_to_scl(scale_df)
        (OUTPUT_DIR / filename).write_text(scl_text)


def main():
    logger.info("Building DaMuSc scales")
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    OUTPUT_DIR.mkdir()
    references = write_measured_scales()

    # TODO: Check tunings of theory scales in sources
    # write_theory_scales()

    return utils.check_scl_dir(OUTPUT_DIR), references


if __name__ == "__main__":
    utils.setup_logging()
    main()
