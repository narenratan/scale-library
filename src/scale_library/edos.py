"""
Generate scl files for equal divisions of the octave (EDOs).
"""

import logging
import shutil

from scale_library import SCALES_DIR, utils
from scale_library.utils import Tone, build_scl

logger = logging.getLogger(__name__)

OUTPUT_DIR = SCALES_DIR / "edos"

EDOS = range(1, 73)

REFERENCE = "Augusto Novaro, Sistema Natural de la Música, 1951"

COMMENTS = [f"{REFERENCE}."]

INFO = {"source": "EDO"}


def edo_scl(n):
    filename = f"edo-{n:02d}.scl"
    description = f"{n} equal division{'s' if n != 1 else ''} of the octave"
    tones = [Tone(k * 1200 / n, comment=f"{k:{len(str(n))}d}\\{n}") for k in range(1, n + 1)]
    scl_text = build_scl(filename, description, tones, INFO, COMMENTS)
    return filename, scl_text


def main():
    logger.info("Building EDO scales")
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    OUTPUT_DIR.mkdir()

    references = {}
    for n in EDOS:
        filename, scl_text = edo_scl(n)
        (OUTPUT_DIR / filename).write_text(scl_text)
        references[filename] = REFERENCE

    return utils.check_scl_dir(OUTPUT_DIR), references


if __name__ == "__main__":
    utils.setup_logging()
    main()
