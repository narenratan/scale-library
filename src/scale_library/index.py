"""
Generate scale index.

Run on scales in a given scale_dir as

    $ python3 src/scale_library/index.py scale_dir

"""

import logging
import sys
from pathlib import Path

import pandas as pd
import tuning_library as tl
from sympy import Rational, factorrat

from scale_library.utils import base_tone_string

logger = logging.getLogger(__name__)


def build_index(scale_dir, references=None):
    rows = []
    for p in scale_dir.rglob("**/*.scl"):
        scale = tl.read_scl_file(p)
        just = all(t.type == tl.Type.kToneRatio for t in scale.tones)
        if just:
            limit = max(
                max(factorrat(Rational(t.ratio_n, t.ratio_d)), default=0)
                for t in scale.tones
            )
        else:
            limit = 0

        max_tone = max(scale.tones, key=lambda x: x.cents)
        last_tone = scale.tones[-1]
        if last_tone.cents != max_tone.cents:
            logger.debug(
                "Last tone %s lower than %s for %s",
                last_tone.string_rep,
                max_tone.string_rep,
                p,
            )
        period = round(last_tone.cents, 6)

        tones_str = " ".join(base_tone_string(t.string_rep) for t in scale.tones)

        rows.append(
            (
                str(p.relative_to(scale_dir).parent),
                p.name,
                scale.count,
                period,
                just,
                limit,
                scale.description,
                tones_str,
            )
        )

    columns = [
        "directory",
        "scl_file",
        "notes",
        "period",
        "just",
        "limit",
        "description",
        "tones",
    ]

    scale_df = pd.DataFrame(rows, columns=columns)

    scale_df["just_order"] = ~scale_df["just"]
    scale_df = scale_df.sort_values(
        by=["notes", "period", "just_order", "limit", "directory", "scl_file"],
        ignore_index=True,
    ).drop(columns="just_order")

    if references:
        scale_df["reference"] = scale_df["scl_file"].map(references)
        assert scale_df["reference"].notna().all()

    if scale_df["directory"].nunique() == 1:
        scale_df = scale_df.drop(columns="directory")

    logger.info("Built index of %s scales", len(scale_df))

    return scale_df


if __name__ == "__main__":
    scale_dir = Path(sys.argv[1])
    scale_df = build_index(scale_dir)
    scale_df.to_csv("scale-index.csv", index=False)
