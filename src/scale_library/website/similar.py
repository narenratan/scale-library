"""
Similar-scales precomputation.

Three relationships, all capped at 10 results:
  - similar: same note count, every tone within 25 cents in some mode rotation
  - parents: larger scales that contain all notes of this scale within 25 cents
  - children: smaller scales whose notes are all within 25 cents of some note
               here (inverse of parent), sorted largest-first
"""

import math
from collections import defaultdict

import numpy as np


CENTS_TOL = 25.0
SIMILAR_CAP = 10
MIN_CHILD_NOTES = 4
_PARENT_SIZE_K = 10.0 / math.log(2)  # cents cost per doubling of parent size


def _tone_cents(tones) -> tuple[np.ndarray, float]:
    """Return (cents array, period) for a scale's tones (sorted, excluding period tone)."""
    arr = np.array([t.cents for t in tones], dtype=float)
    period = float(arr[-1])
    return np.sort(arr[:-1]), period  # exclude period tone


def _canonical_mode_key(cents: np.ndarray, period: float) -> tuple:
    """
    Return a tuple identifying the modal equivalence class of a scale.

    Two scales are exact modes of each other iff they share the same key.
    Uses the lexicographically largest rotation of the step-interval vector,
    rounded to 4 decimal places to absorb float noise.
    """
    if len(cents) == 0:
        return (round(period, 4),)
    assert cents[0] != 0.0
    assert cents[-1] != period
    full = np.concatenate([[0.0], cents, [period]])
    steps = tuple(round(float(s), 4) for s in np.diff(full))
    return max(steps[i:] + steps[:i] for i in range(len(steps)))


def _min_mode_distance(
    a: np.ndarray, b: np.ndarray, period_a: float, period_b: float
) -> tuple[float, int]:
    """
    Minimum over all mode rotations of b of max(|a_i - b_i|), including period diff.
    Both arrays must be sorted and same length (n tones, period excluded).
    Returns (min_distance, best_mode) where best_mode is 0-indexed:
    0 = no rotation (b as-is matches a), k = rotate b starting from b[k-1].
    Period difference is folded into the returned distance (matching the reference).
    """
    if len(a):
        assert a[0] != 0.0
        assert a[-1] != period_a
    if len(b):
        assert b[0] != 0.0
        assert b[-1] != period_b
    assert len(a) == len(b)

    n = len(a)
    if n == 0:
        return abs(period_a - period_b), 0
    # Include implicit root (0¢) to allow rotations starting from it
    full_b = np.concatenate([[0.0], b])  # n+1 notes
    best = np.inf
    best_mode = 0
    for r in range(n + 1):
        pivot = full_b[r]
        rot_full = np.sort((full_b - pivot) % period_b)
        rot = rot_full[1:]  # exclude new root (0)
        d = float(np.max(np.abs(a - rot)))
        if d < best:
            best = d
            best_mode = r
    max_diff = max(best, abs(period_a - period_b))

    # Validate: best rotation of b achieves the reported mode distance
    pivot = full_b[best_mode]
    rot_full = np.sort((full_b - pivot) % period_b)
    rot = rot_full[1:]
    reconstruction_error = np.max(
        np.abs(np.concatenate([a, [period_a]]) - np.concatenate([rot, [period_b]]))
    )
    assert (
        abs(reconstruction_error - max_diff) <= 1e-9
    ), f"Reconstruction error inconsistent with max_diff"

    # Period difference counts toward overall distance (as in the reference)
    return max_diff, best_mode


def _max_nearest_distance(
    parent_cents: np.ndarray,
    child_cents: np.ndarray,
    parent_period: float,
    child_period: float,
) -> float:
    """
    Return the worst-case nearest-note distance from child to parent, including periods.

    For each child note, finds the nearest parent note (root 0¢ included). Returns the
    max of those distances and the absolute period difference.
    """
    if len(parent_cents):
        assert parent_cents[0] != 0.0
        assert parent_cents[-1] != parent_period
    if len(child_cents):
        assert child_cents[0] != 0.0
        assert child_cents[-1] != child_period

    assert len(parent_cents) >= len(child_cents)
    full_parent = np.concatenate([[0.0], parent_cents, [parent_period]])
    diffs = np.abs(np.subtract.outer(child_cents, full_parent))
    min_per_child = diffs.min(axis=1)
    return float(max(min_per_child.max(), abs(parent_period - child_period)))


def compute_similar(
    scales,
) -> dict[str, dict[str, list[str]]]:
    """
    Compute similar/parent/child relationships for all scales.

    Returns:
        Dict mapping stem → {"similar": [...], "parents": [...], "children": [...]}
        where each list contains up to SIMILAR_CAP stems.
    """
    stems = [s.stem for s in scales]
    cents_arrays = [_tone_cents(s.tones) for s in scales]
    notes_counts = [len(arr) for arr, _ in cents_arrays]
    canonical_keys = [_canonical_mode_key(arr, period) for arr, period in cents_arrays]

    # Group by note count for O(n_group²) similar search

    by_count: dict[int, list[int]] = defaultdict(list)
    for i, n in enumerate(notes_counts):
        by_count[n].append(i)

    similar: dict[int, list[tuple[int, float]]] = {i: [] for i in range(len(scales))}
    parents: dict[int, list[tuple[int, float]]] = {i: [] for i in range(len(scales))}
    children: dict[int, list[tuple[int, float]]] = {i: [] for i in range(len(scales))}

    # Similar: same note count — collect all matches, then keep closest SIMILAR_CAP
    for n, group in by_count.items():
        for pos_a, i in enumerate(group):
            a, period_a = cents_arrays[i]
            for j in group[pos_a + 1 :]:
                b, period_b = cents_arrays[j]
                dist_ij, mode_of_j = _min_mode_distance(
                    a, b, period_a=period_a, period_b=period_b
                )
                dist_ji, mode_of_i = _min_mode_distance(
                    b, a, period_a=period_b, period_b=period_a
                )
                if dist_ij <= CENTS_TOL:
                    similar[i].append((j, dist_ij, mode_of_j))
                if dist_ji <= CENTS_TOL:
                    similar[j].append((i, dist_ji, mode_of_i))

    def _sort_key(item):
        j, dist, *_ = item
        return (dist, notes_counts[j], stems[j].split("/")[-1])

    def _dedup_by_modal_class(candidates):
        """Keep only the closest candidate per modal equivalence class."""
        best: dict[tuple, tuple] = {}
        for item in candidates:
            j, _, mode = item
            key = canonical_keys[j]
            if key not in best or mode < best[key][2]:
                best[key] = item
        return list(best.values())

    def _sort_key_parent(item, ni):
        j, dist = item
        nj = notes_counts[j]
        score = dist + _PARENT_SIZE_K * math.log(nj / ni)
        return (score, stems[j].split("/")[-1])

    def _sort_key_children(item):
        j, dist, *_ = item
        return (dist, -notes_counts[j], stems[j].split("/")[-1])

    for i in similar:
        similar[i] = sorted(_dedup_by_modal_class(similar[i]), key=_sort_key)[
            :SIMILAR_CAP
        ]

    # Parent/child: collect all, then keep closest SIMILAR_CAP
    for i in range(len(scales)):
        ni = notes_counts[i]
        if ni == 0:
            continue
        child_cents, period_i = cents_arrays[i]
        for j in range(len(scales)):
            if i == j:
                continue
            nj = notes_counts[j]
            if nj == 0:
                continue
            if nj <= ni:
                continue
            parent_cents, period_j = cents_arrays[j]
            result = _max_nearest_distance(
                parent_cents, child_cents, period_j, period_i
            )
            if result <= CENTS_TOL:
                parents[i].append((j, result))
                if ni >= MIN_CHILD_NOTES:
                    children[j].append((i, result))

    for i in parents:
        ni = notes_counts[i]
        parents[i] = sorted(parents[i], key=lambda item: _sort_key_parent(item, ni))[
            :SIMILAR_CAP
        ]
    for i in children:
        children[i] = sorted(children[i], key=_sort_key_children)[:SIMILAR_CAP]

    return {
        stems[i]: {
            "similar": [
                {"stem": stems[j], "max_diff": round(dist, 1), "mode": mode}
                for j, dist, mode in similar[i]
            ],
            "parents": [
                {"stem": stems[j], "max_diff": round(dist, 1)} for j, dist in parents[i]
            ],
            "children": [
                {"stem": stems[j], "max_diff": round(dist, 1)}
                for j, dist in children[i]
            ],
        }
        for i in range(len(scales))
    }
