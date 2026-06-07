"""
Main build entry point.

Usage:
    uv run python -m scale_library.website                    # build site
    uv run python -m scale_library.website --regenerate-similar
    uv run python -m scale_library.website --scale damusc/Angola_Chisende_10450
"""

import argparse
import json
import sys

from scale_library.website.build import (
    SIMILAR_JSON,
    _load_constructions,
    _load_recordings,
    build,
    make_env,
    render_scale_page,
)
from scale_library.website.data import load_all_scales


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build scale-library website")
    parser.add_argument(
        "--scale", metavar="STEM", help="Render a single scale page to stdout"
    )
    parser.add_argument(
        "--allow-missing-scala",
        action="store_true",
        help="Allow scales with no scala-analysis data (skips their scala page)",
    )
    parser.add_argument(
        "--regenerate-similar",
        action="store_true",
        help="Recompute similar/parent/child and overwrite similar.json",
    )
    args = parser.parse_args(argv)


    if args.scale:
        scales = load_all_scales()
        scales_by_stem = {s.stem: s for s in scales}
        scale = scales_by_stem.get(args.scale)
        if scale is None:
            print(f"Scale not found: {args.scale}", file=sys.stderr)
            sys.exit(1)
        similar_data = (
            json.loads(SIMILAR_JSON.read_text()) if SIMILAR_JSON.exists() else None
        )
        _, construction_lookup = _load_constructions(scales)
        print(
            render_scale_page(
                scale,
                scales_by_stem,
                make_env(),
                similar_data=similar_data,
                recordings=_load_recordings(),
                construction_lookup=construction_lookup,
            )
        )
        return

    build(regenerate_similar=args.regenerate_similar, allow_missing_scala=args.allow_missing_scala)


if __name__ == "__main__":
    main()
