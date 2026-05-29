"""
Parse and cache scale data from scale-index.csv and individual scl files.

Provides ScaleData dataclass and load_all_scales() which reads all 4166
scales, parsing tones and [info] blocks from the scl files.
"""

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

import tuning_library as tl

REPO_ROOT = Path(__file__).parents[3]
SCALE_INDEX = REPO_ROOT / "scale-index.csv"
SCALES_DIR = REPO_ROOT / "scales"


@dataclass
class ToneData:
    string_rep: str  # original string from scl file, e.g. "7/6" or "315.641"
    cents: float
    is_ratio: bool
    ratio_n: int = 0
    ratio_d: int = 1


@dataclass
class ScaleInfo:
    """Parsed [info] block from an scl file."""

    source: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class ScaleData:
    # From scale-index.csv
    directory: str
    scl_file: str
    notes: int
    period: float
    just: bool
    limit: int
    description: str
    tones_str: str  # space-separated tone strings from CSV
    reference: str

    # Derived
    stem: str = ""  # directory + "/" + scl_file without .scl
    tones: list[ToneData] = field(default_factory=list)
    info: ScaleInfo = field(default_factory=ScaleInfo)
    raw_text: str = ""  # full scl file content

    def __post_init__(self):
        if not self.stem:
            self.stem = self.directory + "/" + self.scl_file[:-4]


_INFO_RE = re.compile(r"^!\s+\[info\]\s*$", re.MULTILINE)
_KEY_VAL_RE = re.compile(r"^!\s+(\w+)\s*=\s*(.+)$")


def _parse_info_block(raw_text: str) -> ScaleInfo:
    m = _INFO_RE.search(raw_text)
    if not m:
        return ScaleInfo()
    block = raw_text[m.end() :]
    info_dict: dict = {}
    for line in block.splitlines():
        km = _KEY_VAL_RE.match(line)
        if km:
            key, val = km.group(1), km.group(2).strip()
            info_dict[key] = val
    source = info_dict.get("source", "")
    return ScaleInfo(source=source, raw=info_dict)


def load_scale(row: dict) -> ScaleData:
    """Load a single ScaleData from a CSV row dict."""
    sd = ScaleData(
        directory=row["directory"],
        scl_file=row["scl_file"],
        notes=int(row["notes"]),
        period=float(row["period"]),
        just=row["just"].lower() == "true",
        limit=int(row["limit"]) if row["limit"] else 0,
        description=row["description"],
        tones_str=row.get("tones", ""),
        reference=row.get("reference", ""),
    )

    scl_path = SCALES_DIR / sd.directory / sd.scl_file
    scale = tl.read_scl_file(scl_path)
    sd.raw_text = scl_path.read_text(encoding="utf-8")
    sd.tones = [
        ToneData(
            string_rep=t.string_rep.strip().split("!")[0].strip(),
            cents=t.cents,
            is_ratio=(t.type == tl.Type.kToneRatio),
            ratio_n=t.ratio_n if t.type == tl.Type.kToneRatio else 0,
            ratio_d=t.ratio_d if t.type == tl.Type.kToneRatio else 1,
        )
        for t in scale.tones
    ]
    sd.info = _parse_info_block(sd.raw_text)

    return sd


def load_all_scales() -> list[ScaleData]:
    """Load all scales from scale-index.csv."""
    scales = []
    with open(SCALE_INDEX, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scales.append(load_scale(row))
    return scales
