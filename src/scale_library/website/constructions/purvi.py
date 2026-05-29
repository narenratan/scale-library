from fractions import Fraction
from math import floor, log2

F = Fraction


def tetrachordal_scale(a, b, c):
    """
    >>> tetrachordal_scale(Fraction(28, 27), Fraction(8, 7), Fraction(9, 8))
    [Fraction(1, 1), Fraction(28, 27), Fraction(32, 27), Fraction(4, 3), Fraction(3, 2), Fraction(14, 9), Fraction(16, 9), Fraction(2, 1)]
    """
    steps = [a, b, c]
    return stack(steps + [Fraction(9, 8)] + steps)


def octave_reduce(x):
    if x == 2:
        return x
    return x * Fraction(2) ** (-floor(log2(x)))


def step_through(scale, step):
    """
    >>> step_through([Fraction(1, 1), Fraction(9, 8), Fraction(7, 6), Fraction(4, 3), Fraction(3, 2), Fraction(14, 9), Fraction(7, 4), Fraction(2, 1)], 3)
    [Fraction(4, 3), Fraction(21, 16), Fraction(4, 3), Fraction(4, 3), Fraction(81, 56), Fraction(4, 3), Fraction(4, 3)]
    """
    N = len(scale) - 1
    i = 0
    result = []
    while len(result) < N:
        j = (i + step) % N
        result.append(octave_reduce(scale[j] / scale[i]))
        i = j
    return result


def stack(fs):
    """
    >>> stack([Fraction(4, 3), Fraction(21, 16), Fraction(4, 3), Fraction(4, 3), Fraction(81, 56), Fraction(4, 3), Fraction(4, 3)])
    [Fraction(1, 1), Fraction(9, 8), Fraction(7, 6), Fraction(4, 3), Fraction(3, 2), Fraction(14, 9), Fraction(7, 4), Fraction(2, 1)]
    """
    x = Fraction(1)
    notes = [Fraction(1)]
    for f in fs:
        x = octave_reduce(x * f)
        notes.append(x)
    return sorted(notes)


def rotate(xs, i):
    return xs[i:] + xs[:i]


def mode_rotate(scale, n):
    """Return the mode of scale starting on scale[n]."""
    period = scale[-1]
    notes = scale[:-1]
    n = n % len(notes)
    tonic = notes[n]
    rotated = notes[n:] + [period * x for x in notes[:n]]
    return sorted(octave_reduce(x / tonic) for x in rotated) + [period]


def purvi_permutations(a, b, c, closing_fourth):
    """
    >>> scales = purvi_permutations(Fraction(8, 7), Fraction(9, 8), Fraction(28, 27), Fraction(81, 56))
    >>> len(scales)
    6
    >>> scales[0]
    [Fraction(1, 1), Fraction(28, 27), Fraction(32, 27), Fraction(4, 3), Fraction(112, 81), Fraction(14, 9), Fraction(16, 9), Fraction(2, 1)]
    """
    # Returns the 6 scales from the cyclic permutations described in purvi.md.
    ts = tetrachordal_scale(a, b, c)
    fourths = step_through(ts, 3)
    rot_fourths = rotate(fourths, -((len(fourths) - 1) - fourths.index(closing_fourth)))
    return [stack(rotate(rot_fourths[:-1], i) + [rot_fourths[-1]]) for i in range(6)]


def purvi(a, b, c, closing_fourth):
    # Returns the 7 modulations matching Wilson's figures.
    # The mode rotation (4-3*i)%7 was reverse-engineered to match Wilson's figures.
    raw = purvi_permutations(a, b, c, closing_fourth)
    return [mode_rotate(raw[i % 6], (4 - 3 * i) % 7) for i in range(7)]
