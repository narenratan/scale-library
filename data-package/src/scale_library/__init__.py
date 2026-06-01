import configparser
from pathlib import Path


def scale_dir() -> Path:
    """Return absolute Path to the bundled scales/ directory."""
    return Path(__file__).parent / "scales"


def scale_index_path() -> Path:
    """Return absolute Path for scale-index.csv."""
    return Path(__file__).parent / "scale-index.csv"


def parse_scl_info(text: str) -> dict:
    """
    Parse the [info] block from SCL text and return it as a dict.
    Returns an empty dict if no [info] block is present.

    >>> parse_scl_info("! [info]\\n! source = EDO\\n")
    {'source': 'EDO'}
    >>> parse_scl_info("no info block here")
    {}
    """
    started = False
    info_lines = []
    for line in text.splitlines():
        stripped = line.replace("!", "").strip()
        if not started and stripped == "[info]":
            started = True
        if started:
            info_lines.append(stripped)

    if not info_lines:
        return {}

    c = configparser.ConfigParser()
    c.read_string("\n".join(info_lines))
    return dict(c["info"])
