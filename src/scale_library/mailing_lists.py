"""
Extract scl files from the Yahoo tuning groups ultimate backup.

For the backup, see:

    https://github.com/YahooTuningGroupsUltimateBackup/YahooTuningGroupsUltimateBackup

The mailing lists can be browsed in a readable form at:

    https://yahootuninggroupsultimatebackup.github.io

"""

import html
import json
import logging
import quopri
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tuning_library as tl

from scale_library import SCALES_DIR, SOURCES_DIR
from scale_library.utils import check_scl_dir, validate_scale

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Result:
    scale: tl.Scale
    message: dict[str, Any]
    list_name: str
    json_file_path: Path


def extract_scales():
    logger.info("Building mailing list scales")
    results = []

    source_dir = SOURCES_DIR / "YahooTuningGroupsUltimateBackup/src"

    for p in list(source_dir.rglob("*messages*json"))[:]:
        logger.debug("Reading %s", p)
        messages = json.loads(p.read_text())

        for message in messages:
            if "rawEmail" not in message:
                continue

            # Clean up message text
            try:
                email_text = quopri.decodestring(message["rawEmail"]).decode(
                    errors="ignore"
                )
            except ValueError:
                email_text = message["rawEmail"]

            email_text = html.unescape(email_text)
            email_text = email_text.replace("<br>", "")  # .replace("<BR>", "")

            email_lines = email_text.splitlines()

            # Look for possible beginnings of scl files
            scl_starts = [
                i for i, line in enumerate(email_lines) if re.match(".*!.*scl.*", line)
            ]

            for scl_start in scl_starts:
                # Try parsing the lines after the scl file start.
                # Keep adding lines, stop if scl file successfully parsed.
                found = False
                for i in range(len(email_lines) - scl_start):
                    try:
                        tl.parse_scl_data(
                            "\n".join(email_lines[scl_start : scl_start + i])
                        )
                        list_name = p.parents[1].name
                        found = True
                        break
                    except tl.TuningError:
                        pass
                if found:
                    # Some scl files contain comments after the scale notes
                    # So include any comment lines following a successfully parsed scl file
                    while (scl_start + i) < len(email_lines) and email_lines[
                        scl_start + i
                    ].startswith("!"):
                        i += 1
                    scale = tl.parse_scl_data(
                        "\n".join(email_lines[scl_start : scl_start + i])
                    )
                    results.append(
                        Result(
                            scale=scale,
                            message=message,
                            list_name=list_name,
                            json_file_path=p.relative_to(source_dir),
                        )
                    )
    return results


def write_out_results(results):
    result_dir = SCALES_DIR / "mailing-lists"
    shutil.rmtree(result_dir, ignore_errors=True)
    result_dir.mkdir()

    filenames = set()
    all_tones = set()

    # To avoid duplicate scales, keep only the first scl file containing given tones.
    # Choose the scl file from the biggest mailing list, then with the lowest msgId.
    def sort_key(result):
        order = {
            "tuning": 0,
            "makemicromusic": 1,
            "tuning-math": 2,
            "metatuning": 3,
            "mills-tuning-list": 4,
            "harmonic_entropy": 5,
            "crazy_music": 6,
        }
        return (order[result.list_name], result.message["msgId"])

    for i, result in enumerate(sorted(results, key=sort_key)):
        scale = result.scale
        list_name = result.list_name
        message = result.message
        json_file_path = result.json_file_path

        first_line = scale.raw_text.splitlines()[0]
        filename = Path(
            first_line.replace("!", "")
            .replace(" ", "")
            .replace("=", "")
            .replace("\\", "/")
        ).name
        sep = ".scl"
        filename = Path(filename.split(sep)[0] + sep)

        if not validate_scale(scale):
            logger.debug("Failed %s", filename)
            continue

        # Do not include multiple scl files with the same scale in
        tones = tuple(sorted(round(tone.cents, 5) for tone in scale.tones))
        if tones in all_tones:
            continue
        else:
            all_tones.add(tones)

        # If filenames clash, append the list name, topicId, and msgId.
        if filename in filenames:
            logger.debug("Filename clash for %s", filename)
            filename = Path(
                filename.stem
                + f"_{list_name}_{message['topicId']}_{message['msgId']}"
                + filename.suffix
            )
            logger.debug("Using filename %s", filename)

        if filename in filenames:
            raise ValueError(filename)

        filenames.add(filename)
        topicId = message["topicId"]
        msgId = message["msgId"]
        text = (
            "\n".join(
                [
                    scale.raw_text.rstrip(),
                    "!",
                    f"! https://yahootuninggroupsultimatebackup.github.io/{list_name}/topicId_{topicId}.html#{msgId}",
                    "!",
                    "! [info]",
                    "! source = Mailing lists",
                    f"! file = {json_file_path}",
                    f"! topic_id = {topicId}",
                    f"! msg_id = {msgId}",
                ]
            )
            + "\n"
        )
        (result_dir / filename).write_text(text)

    return check_scl_dir(result_dir)


def main():
    results = extract_scales()
    count = write_out_results(results)
    return count


if __name__ == "__main__":
    main()
