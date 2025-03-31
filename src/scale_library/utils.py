"""
Utility functions used in several places.
"""

import configparser
import io
import logging
import os
import re
from collections import Counter
from fractions import Fraction
from math import log2

import tuning_library as tl

logger = logging.getLogger(__name__)


def check_count_line(scl_text):
    """
    Check the count line contains only a valid digit.

    A few mailing list scl files have the description broken over two lines, and by
    chance the start of the second line is a number. This is a technically a valid
    scl file (where the intended count gets taken as the first note in the scale)
    but should be rejected.
    """
    count = 0
    for line in io.StringIO(scl_text):
        if line.startswith("!"):
            continue
        count += 1
        if count == 2:
            break
    if not line.strip().isdigit():
        logger.debug("Invalid count line: %s", line)
        return False
    return True


def base_tone_string(tone_str):
    """Get basic tone string without comments"""
    return tone_str.split("!")[0].strip().removesuffix("cents")


def validate_scale(scale):
    if not check_count_line(scale.raw_text):
        return False
    if "<div" in scale.raw_text:
        logger.debug("Failed from <div> in scale")
        return False
    if "<p>" in scale.raw_text:
        logger.debug("Failed from <p> in scale")
        return False
    for t in scale.tones:
        tone_text = base_tone_string(t.string_rep)
        if not re.fullmatch(r"[0-9./\s-]*", tone_text):
            logger.debug("Failed tone %s", t)
            return False
        try:
            cent_value = (
                1200 * log2(Fraction(tone_text))
                if "." not in tone_text
                else float(tone_text)
            )
        except ValueError:
            logger.debug("Could not compute cents for %s", t)
            return False
        if abs(cent_value - t.cents) > 1e-3:
            logger.debug("Failed cent check for %s", t)
            return False

        # Check for large integer values
        # Sometimes cent values are input without decimal point, e.g. 1094
        # These are interpreted as frequency ratios 1094/1 - probably not intended
        try:
            int_value = int(tone_text)
            if int_value >= 100:
                logger.debug("Failed large integer check for %s", t)
                return False
        except ValueError:
            pass
    return True


class ScaleValidationError(Exception):
    pass


def check_scl_dir(dir_path):
    counter = Counter()
    for p in dir_path.rglob("*.scl"):
        scale = tl.read_scl_file(p)
        if not validate_scale(scale):
            raise ScaleValidationError(scale)
        counter[p.name] += 1
    assert counter.most_common()[0][1] == 1, "scl filename not unique"
    count = counter.total()
    logger.info("Checked %s scl files in %s", count, dir_path)
    return count


def setup_logging():
    logging.basicConfig(
        level=os.getenv("LOGLEVEL", logging.INFO),
        format="[%(levelname)s %(asctime)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_info(text):
    started = False
    info_lines = []
    for line in text.splitlines():
        stripped_line = line.replace("!", "").strip()
        if not started and stripped_line == "[info]":
            started = True
        if started:
            info_lines.append(stripped_line)

    info = None
    if info_lines:
        c = configparser.ConfigParser()
        c.read_string("\n".join(info_lines))
        info = dict(c["info"])

    return info
