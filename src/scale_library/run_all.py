"""
Generate all scl files and README.

Run in the top-level repo directory as:

    $ python3 src/scale_library/run_all.py

"""

import logging

import scale_library.damusc
import scale_library.divisions
import scale_library.mailing_lists
from scale_library import SCALES_DIR, utils
from scale_library.write_readme import write_readme

logger = logging.getLogger(__name__)


def main():
    logger.info("Building scale library")
    SCALES_DIR.mkdir(exist_ok=True)
    damusc_scl_count = scale_library.damusc.main()
    divisions_scl_count = scale_library.divisions.main()
    mailing_lists_scl_count = scale_library.mailing_lists.main()

    total_scl_count = utils.check_scl_dir(SCALES_DIR)
    assert (
        total_scl_count
        == damusc_scl_count + divisions_scl_count + mailing_lists_scl_count
    )
    write_readme(
        total_scl_count=total_scl_count,
        damusc_scl_count=damusc_scl_count,
        divisions_scl_count=divisions_scl_count,
        mailing_lists_scl_count=mailing_lists_scl_count,
    )


if __name__ == "__main__":
    utils.setup_logging()
    main()
