"""Tests for the website build outputs."""

from collections import defaultdict

import numpy as np

from scale_library.website.build import SCALE_CENTS_PRECISION
from scale_library.website.data import load_all_scales
from scale_library.website.similar import _canonical_mode_key


def _modal_class_partition(
    cents_by_stem: dict[str, list[float]],
) -> set[frozenset[str]]:
    """Partition stems into modal-equivalence classes from their cents arrays.

    Each cents array includes the period as its last element. Uses the same canonical
    key as similar.py, so the partition matches its modal deduplication.
    """
    groups: dict[tuple, set[str]] = defaultdict(set)
    for stem, cents in cents_by_stem.items():
        arr = np.asarray(cents, dtype=float)
        key = _canonical_mode_key(np.sort(arr[:-1]), float(arr[-1]))
        groups[key].add(stem)
    return {frozenset(members) for members in groups.values()}


def test_scale_cents_precision_reproduces_modal_classes():
    """scale-cents.json must be precise enough to reproduce similar.py's modal classes.

    If SCALE_CENTS_PRECISION is ever too coarse, rounding perturbs the step
    intervals enough to split (or merge) a class relative to the full-precision
    computation in similar.py. This checks the served precision against full
    precision over the whole library; if it fails, increase SCALE_CENTS_PRECISION.
    """
    scales = load_all_scales()

    full = _modal_class_partition({s.stem: [t.cents for t in s.tones] for s in scales})
    # Mirror how build.py rounds tone cents for scale-cents.json.
    served = _modal_class_partition(
        {
            s.stem: [round(t.cents, SCALE_CENTS_PRECISION) for t in s.tones]
            for s in scales
        }
    )

    assert served == full
