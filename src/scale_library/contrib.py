import logging
import shutil

import tuning_library as tl

from scale_library import SCALES_DIR, SOURCES_DIR, utils

CONTRIB_RAW_DIR = SOURCES_DIR / "contrib"
OUTPUT_DIR = SCALES_DIR / "contrib"

logger = logging.getLogger(__name__)


def _comment(block):
    return "\n".join("! " + line for line in block.split("\n")[:-1])


def parse_details(scl_text: str) -> str:
    """
    Extract details text from a contrib scl file.

    Details are the comment lines appearing after the scale tones and before the
    [info] block, with the leading '! ' prefix stripped.
    """
    non_comment_seen = 0
    note_count = 0
    tones_seen = 0
    collecting = False
    detail_lines = []

    for line in scl_text.splitlines():
        if collecting:
            if line == "! [info]":
                break
            detail_lines.append(line)
        elif line.startswith("!"):
            continue
        else:
            non_comment_seen += 1
            if non_comment_seen == 2:
                note_count = int(line.strip())
            elif non_comment_seen > 2:
                tones_seen += 1
                if tones_seen == note_count:
                    collecting = True

    return "\n".join(line[2:] if line.startswith("! ") else "" for line in detail_lines).strip("\n")


def main():
    logger.info("Building contrib scales")
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)

    references = {}
    for p in sorted(CONTRIB_RAW_DIR.rglob("*.scl")):
        scl = p.read_text()

        header = scl.split("\n")[0]
        assert p.name in header, f"header {header} doesn't match filename {p.name}"

        info_dict = utils.parse_info(scl)
        assert info_dict['source'] == 'contrib', f"{p}: missing 'source = contrib' in info block"
        assert 'contributor' in info_dict, f"{p}: missing 'contributor' in info block"
        assert info_dict['contributor'] == p.parent.name, (
            f"{p}: 'contributor = {info_dict['contributor']}' does not match directory '{p.parent.name}'"
        )
        assert 'reference' in info_dict, f"{p}: missing 'reference' in info block"
        references[p.name] = info_dict['reference']

        # Check for putting a smaller number of tones and so getting an unexpected period
        # Remove/refine if non-octave scales contributed
        assert abs(tl.parse_scl_data(scl).tones[-1].cents - 1200.0) <= 25.0

        output_path = OUTPUT_DIR / "/".join(p.parts[-2:])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Copying %s", output_path)
        shutil.copy2(p, output_path)

    return utils.check_scl_dir(OUTPUT_DIR), references


if __name__ == "__main__":
    utils.setup_logging()
    main()
