"""
Moments of Symmetry.
"""

import math
from decimal import Decimal


def steps(scale):
    return [b - a for a, b in zip(scale, scale[1:])]


def stern_brocot(generator, period, max_n=50):
    """
    Return Stern-Brocot tree entries ((a, c), (b, d)) for the given generator
    and period, where a/c and b/d are the left and right search interval
    endpoints.

    Each entry gives a MOS of size n = c + d, with generator at scale degree
    m = a + b, step sizes

        s = (d * generator - b * period) / delta
        t = (-c * generator + a * period) / delta

    where delta = a * d - b * c = -1, and c steps of s and d steps of t.

    >>> stern_brocot(Decimal('707'), Decimal('1200'), 5)
    [((0, 1), (1, 0)), ((0, 1), (1, 1)), ((1, 2), (1, 1)), ((1, 2), (2, 3))]
    """
    a, c = 0, 1  # left  = 0/1
    b, d = 1, 0  # right = 1/0 (infinity)
    result = []
    while True:
        m, n = a + b, c + d
        if n > max_n:
            break
        result.append(((a, c), (b, d)))
        if d == 0 or generator * n < period * m:
            b, d = m, n  # mediant is to the right of generator/period
        else:
            a, c = m, n  # mediant is to the left of generator/period
    return result


def mos_sizes(generator, period, max_n=50):
    """
    >>> mos_sizes(Decimal('707'), Decimal('1200'), 20)
    [1, 2, 3, 5, 7, 12, 17]
    """
    return [c + d for (a, c), (b, d) in stern_brocot(generator, period, max_n)]


def repeat_scale(scale, k):
    """Repeat a sub-period scale (starting at 0, ending at period) k times."""
    result = scale
    for _ in range(k - 1):
        result = result + [x + result[-1] for x in scale[1:]]
    return result


def mos(generator, period, n, rotation=0, repeat=1):
    """
    Generate an n-note moment of symmetry scale.

    Stack the generator n times modulo the period and sort. `rotation` selects the
    mode. `repeat` copies the result for multi-period scales.

    >>> mos(Decimal('707'), Decimal('1200'), 5)
    [Decimal('0'), Decimal('214'), Decimal('428'), Decimal('707'), Decimal('921')]

    >>> mos(Decimal('707'), Decimal('1200'), 7)
    [Decimal('0'), Decimal('214'), Decimal('428'), Decimal('642'), Decimal('707'), Decimal('921'), Decimal('1135')]
    """
    generator = Decimal(str(generator))
    period = Decimal(str(period))

    notes = sorted((k * generator) % period for k in range(n))
    scale = notes + [period]
    step_sizes = steps(scale)

    # The Stern-Brocot characterisation of MOS is equivalent to the step-size
    # characterisation above: every size in mos_sizes gives a
    # scale with exactly two step sizes, and vice versa.
    assert n in mos_sizes(generator, period, n), f"{n} not a valid MOS size"
    assert len(set(step_sizes)) <= 2

    # The Stern-Brocot parents for the MOS determine step sizes and step counts
    # These formulae can be derived by mapping the MOS to a two-dimensional keyboard
    for (a, c), (b, d) in stern_brocot(generator, period, n):
        if c + d == n:
            break

    if generator in notes:
        assert notes.index(generator) == a + b

    delta = a * d - b * c
    assert delta == -1
    s = (d * generator - b * period) / delta
    t = (-c * generator + a * period) / delta

    # c steps of s and d steps of t; only include a size if it appears.
    assert set(step_sizes) == ({s} if d == 0 else {s, t})
    if s != t:
        assert step_sizes.count(s) == c and step_sizes.count(t) == d

    # (a, b) is determined by (c, d) and generator/period
    if d > 0:
        assert a == math.floor(generator * c / period)
        assert b == math.ceil(generator * d / period)

    # Return requested mode and repeat

    shift = notes[rotation]
    tail = [x - shift for x in notes[rotation:]]
    head = [x - shift + period for x in notes[:rotation]]
    notes = tail + head
    scale = repeat_scale(notes + [period], repeat)

    return scale[:-1]
