"""
Create scl files from scale data in DaMuSc (database of musical scales).

For DaMuSc see https://github.com/jomimc/DaMuSc

"""

import logging
import shutil
import textwrap
from pathlib import Path
from collections import defaultdict

import pandas as pd
import tuning_library as tl

from scale_library import SCALES_DIR, SOURCES_DIR, utils

DAMUSC_DIR = SOURCES_DIR / "DaMuSc"
OUTPUT_DIR = SCALES_DIR / "database-of-musical-scales"

logger = logging.getLogger(__name__)


class Columns:
    authors = "Authors"
    country = "Country"
    culture = "Culture"
    interval = "interval"
    measured_id = "MeasuredID"
    name = "Name"
    octave_modified = "Octave_modified"
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


def measured_df_to_scl(df, filenames):
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

    filename = (
        (
            info[C.country].replace(".", "").replace(" ", "")
            + "_"
            + info[C.name]
            + ".scl"
        )
        .replace(" ", "_")
        .replace("/", "_")
        .replace("'", "_")
    )

    # I didn't want to include the MeasuredID, e.g. M0123, in the scl filenames
    # But this means filename clashes are possible
    # So add a number suffix, e.g. _2, to the filename if it has already been used
    if filename in filenames:
        logger.debug("Filename clash for %s", filename)
        i = 2
        while (new_filename := f"{Path(filename).stem}_{i}.scl") in filenames:
            i += 1
        assert new_filename not in filenames
        filename = new_filename
        logger.debug("Using filename %s", filename)
    filenames.add(filename)

    reference = info[C.reference]
    reference_lines = ["! " + x for x in textwrap.wrap(reference)]

    scl_lines = (
        [
            f"! {filename}",
            "!",
            f"Measured scale {info[C.measured_id]} in DaMuSc",
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
            f"! measured_id = {info[C.measured_id]}",
            f"! ref_id = {info[C.ref_id]}",
        ]
    )

    scl_text = "\n".join(scl_lines) + "\n"

    return filename, scl_text, reference


def write_measured_scales():
    measured_scales = pd.read_csv(DAMUSC_DIR / "Data/measured_scales.csv")
    sources = pd.read_csv(DAMUSC_DIR / "MetaData/sources.csv")
    df = measured_scales.merge(sources[[C.ref_id, C.authors, C.year, C.title]])

    filenames = set()
    references = {}
    tones_to_scl = defaultdict(lambda: [])
    for _, scale_df in df.groupby(C.measured_id):
        filename, scl_text, reference = measured_df_to_scl(scale_df, filenames)
        references[filename] = reference
        tones = tuple(
            sorted(round(tone.cents, 5) for tone in tl.parse_scl_data(scl_text).tones)
        )
        tones_to_scl[tones].append((filename, scl_text))

    # Some measured scales are duplicated from Rechberger and the original source
    # Keep the only the original source
    rechberger = "Rechberger"
    for tones, scales in tones_to_scl.items():
        if len(scales) == 1:
            filename, scl_text = scales[0]
            (OUTPUT_DIR / filename).write_text(scl_text)
        else:
            logger.debug("Duplicate scales %s", [filename for filename, _ in scales])
            assert len(scales) == 2
            assert sum(rechberger in scl_text for _, scl_text in scales) == 1
            for filename, scl_text in scales:
                if rechberger not in scl_text:
                    (OUTPUT_DIR / filename).write_text(scl_text)

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
