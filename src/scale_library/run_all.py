"""
Generate all scl files, README, and scale index.

Run in the top-level repo directory as:

    $ python3 src/scale_library/run_all.py

"""

import logging
import shutil

from scale_library import damusc, divisions, edos, mailing_lists, ord_cc32, xenharmonikon
from scale_library import SCALES_DIR, utils
from scale_library.write_readme import write_readme
from scale_library.index import build_index

logger = logging.getLogger(__name__)


def main():
    logger.info("Building scale library")
    shutil.rmtree(SCALES_DIR, ignore_errors=True)
    SCALES_DIR.mkdir()
    damusc_scl_count, damusc_references = damusc.main()
    divisions_scl_count, divisions_references = divisions.main()
    edos_scl_count, edos_references = edos.main()
    mailing_lists_scl_count, mailing_lists_references = mailing_lists.main()
    ord_cc32_scl_count, ord_cc32_references = ord_cc32.main()
    xenharmonikon_scl_count, xenharmonikon_references = xenharmonikon.main()

    total_scl_count = utils.check_scl_dir(SCALES_DIR)
    assert (
        total_scl_count
        == damusc_scl_count
        + divisions_scl_count
        + edos_scl_count
        + mailing_lists_scl_count
        + ord_cc32_scl_count
        + xenharmonikon_scl_count
    )
    write_readme(
        total_scl_count=total_scl_count,
        damusc_scl_count=damusc_scl_count,
        divisions_scl_count=divisions_scl_count,
        edos_scl_count=edos_scl_count,
        mailing_lists_scl_count=mailing_lists_scl_count,
        ord_cc32_scl_count=ord_cc32_scl_count,
        xenharmonikon_scl_count=xenharmonikon_scl_count,
    )

    references = (
        xenharmonikon_references
        | mailing_lists_references
        | damusc_references
        | divisions_references
        | edos_references
        | ord_cc32_references
    )
    assert len(references) == len(xenharmonikon_references) + len(
        mailing_lists_references
    ) + len(damusc_references) + len(divisions_references) + len(edos_references) + len(ord_cc32_references)
    scale_index = build_index(SCALES_DIR, references)
    scale_index.to_csv("scale-index.csv", index=False)


if __name__ == "__main__":
    utils.setup_logging()
    main()
