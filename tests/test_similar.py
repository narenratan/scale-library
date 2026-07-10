"""Unit tests for similar-scales similarity logic."""

from dataclasses import dataclass

import numpy as np
import pytest

from scale_library.website.similar import CENTS_TOL, MIN_PARENT_NOTES, _max_nearest_distance, _min_mode_distance, compute_similar


# --- _min_mode_distance ---


def test_identical_scales():
    a = np.array([200.0, 400.0, 700.0, 900.0])
    dist, mode = _min_mode_distance(a, a.copy(), period_a=1200.0, period_b=1200.0)
    assert dist == pytest.approx(0.0)
    assert mode == 0


def test_close_but_not_identical():
    a = np.array([200.0, 400.0, 700.0, 900.0])
    b = a + 10.0  # 10¢ shift on every note
    dist, mode = _min_mode_distance(a, b, period_a=1200.0, period_b=1200.0)
    assert dist == pytest.approx(10.0)
    assert mode == 0


def test_rotation_detected():
    # Mode 1 of a=[200,700] (period 1200): start from b[0]=200 → [500, 1000]
    # Steps of a: 200, 500, 500. Rotation starting from 200: [500, 1000].
    a = np.array([200.0, 700.0])
    b = np.array([500.0, 1000.0])  # mode 1 of a
    dist, mode = _min_mode_distance(a, b, period_a=1200.0, period_b=1200.0)
    assert dist == pytest.approx(0.0)
    assert mode != 0  # some non-zero rotation required


def test_scales_outside_tolerance():
    a = np.array([200.0, 400.0, 700.0])
    b = np.array([250.0, 450.0, 760.0])  # all 50-60¢ off, no rotation helps
    dist, _ = _min_mode_distance(a, b, period_a=1200.0, period_b=1200.0)
    assert dist > 25.0


def test_non_octave_period_identical():
    period = 1136.0
    a = np.array([212.0, 400.0, 590.0, 778.0, 931.0])
    dist, mode = _min_mode_distance(a, a.copy(), period_a=period, period_b=period)
    assert dist == pytest.approx(0.0)
    assert mode == 0


def test_empty_scale_same_period():
    a = np.array([])
    dist, mode = _min_mode_distance(a, a.copy(), period_a=1200.0, period_b=1200.0)
    assert dist == pytest.approx(0.0)
    assert mode == 0


def test_empty_scale_different_periods():
    # Two 1-note scales with different periods: dist = period difference
    a = np.array([])
    dist, mode = _min_mode_distance(a, a.copy(), period_a=78.0, period_b=1200.0)
    assert dist == pytest.approx(1122.0)
    assert mode == 0


def test_different_periods_outside_tolerance():
    # Same tones, but periods 30¢ apart — should exceed tolerance.
    a = np.array([200.0, 400.0, 700.0, 900.0])
    dist, _ = _min_mode_distance(a, a.copy(), period_a=1200.0, period_b=1230.0)
    assert dist == pytest.approx(30.0)
    assert dist > CENTS_TOL


def test_different_periods_within_tolerance():
    # Same tones, periods 10¢ apart — distance is the period diff, within tolerance.
    a = np.array([200.0, 400.0, 700.0, 900.0])
    dist, _ = _min_mode_distance(a, a.copy(), period_a=1200.0, period_b=1210.0)
    assert dist == pytest.approx(10.0)
    assert dist <= CENTS_TOL


# --- _max_nearest_distance ---


def test_parent_exactly_inside_child():
    child = np.array([200.0, 400.0, 500.0, 700.0, 900.0, 1100.0])
    parent = np.array([200.0, 700.0])
    result = _max_nearest_distance(child, parent, 1200.0, 1200.0)
    assert result == pytest.approx(0.0)


def test_parent_within_tolerance():
    child = np.array([200.0, 700.0, 900.0])
    parent = np.array([210.0, 715.0])  # 10¢ and 15¢ off
    result = _max_nearest_distance(child, parent, 1200.0, 1200.0)
    assert result == pytest.approx(15.0)


def test_parent_outside_tolerance():
    child = np.array([200.0, 700.0, 900.0])
    parent = np.array([200.0, 740.0])  # 740 is 40¢ from nearest child note (700)
    result = _max_nearest_distance(child, parent, 1200.0, 1200.0)
    assert result == pytest.approx(40.0)


def test_peru27_not_contained_in_octave_scale():
    # Peru_27 raw tones (period 1136¢, unnormalised). 931¢ is 55¢ from nearest
    # note in terrain.
    child = np.array([35.0, 182.0, 214.0, 399.0, 435.0, 583.0, 617.0, 801.0, 835.0, 986.0, 1018.0])
    parent = np.array([212.0, 400.0, 590.0, 778.0, 931.0])
    result = _max_nearest_distance(child, parent, 1200.0, 1136.0)
    assert result == pytest.approx(64.0)  # period diff (64¢) dominates note distance (55¢)


# --- Tests from definitions.md ---

def test_definitions_1():
    a = [203.9, 386.3, 498.0, 702.0, 884.4, 1088.3]
    b = [200.0, 400.0, 500.0, 700.0, 900.0, 1100.0]
    dist, rot = _min_mode_distance(a, b, period_a=1200.0, period_b=1200.0)
    assert dist == pytest.approx(15.6)
    assert rot == 0


def test_definitions_2():
    a = [203.9, 386.3, 702.0, 884.4]
    b = [300.0, 500.0, 700.0, 1000.0]
    dist, rot = _min_mode_distance(a, b, period_a=1200.0, period_b=1200.0)
    assert dist == pytest.approx(15.6)
    assert rot == 1


def test_definitions_3():
    parent = np.array([200.0, 400.0, 700.0, 900.0])
    child = np.array([200.0, 400.0, 500.0, 700.0, 900.0, 1100.0])
    dist = _max_nearest_distance(child, parent, 1200.0, 1200.0)
    assert dist == pytest.approx(0.0)


def test_definitions_4():
    parent = np.array([200.0, 400.0, 700.0, 900.0])
    child = np.array([203.9, 386.3, 498.0, 702.0, 884.4, 1088.3])
    dist = _max_nearest_distance(child, parent, 1200.0, 1200.0)
    assert dist == pytest.approx(15.6)


# --- compute_similar ---

@dataclass
class _Tone:
    cents: float

@dataclass
class _Scale:
    stem: str
    tones: list


def test_parent_found_for_small_scale():
    # A scale with fewer than MIN_PARENT_NOTES inner notes should still have parents listed.
    # 2-note scale [400, 700] (period 1200) is exactly contained in the 4-note parent.
    small = _Scale(stem='small', tones=[_Tone(400), _Tone(700), _Tone(1200)])
    large = _Scale(stem='large', tones=[_Tone(200), _Tone(400), _Tone(700), _Tone(900), _Tone(1200)])
    assert len(small.tones) - 1 < MIN_PARENT_NOTES  # confirm small has fewer than MIN_PARENT_NOTES inner notes
    result = compute_similar([small, large])
    assert result['small']['children'], "scale with fewer than MIN_PARENT_NOTES notes should still have children"
