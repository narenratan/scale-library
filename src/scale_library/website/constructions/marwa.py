"""
>>> from collections import Counter
>>> ts = tetrachordal_scale(Fraction(28, 27), Fraction(8, 7), Fraction(9, 8))
>>> tetrachordal_fourths = step_through(ts, 3)
>>> fourths = [Fraction(21, 16), Fraction(81, 56)] + 5 * [Fraction(4, 3)]
>>> assert Counter(fourths) == Counter(tetrachordal_fourths)
>>> marwa(fourths)[13]
[Fraction(1, 1), Fraction(28, 27), Fraction(32, 27), Fraction(4, 3), Fraction(3, 2), Fraction(14, 9), Fraction(16, 9), Fraction(2, 1)]
>>> assert marwa(fourths)[13] == ts
>>> marwa(fourths)[7]
[Fraction(1, 1), Fraction(9, 8), Fraction(7, 6), Fraction(4, 3), Fraction(3, 2), Fraction(14, 9), Fraction(7, 4), Fraction(2, 1)]
>>> marwa(fourths)[6]
[Fraction(1, 1), Fraction(9, 8), Fraction(7, 6), Fraction(4, 3), Fraction(3, 2), Fraction(27, 16), Fraction(7, 4), Fraction(2, 1)]
"""

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


def marwa_permute(fourths):
    """
    Permute a list of fourths in the way Wilson does in the Marwa permutations paper.

    The 7th interval (fourths[-1]) is always fixed; only the first six are
    permuted. Special intervals are those not equal to 4/3. Their positions in the
    starting configuration (special_positions) determine the minimum gap enforced
    between them in each permutation — matching Wilson's exact enumeration order in
    the figures. When specials are adjacent in the starting config
    (special_positions=[0,1] or [0,1,2]), this reduces to all C(6, num_specials)
    combinations maintaining relative order. When they start with a gap of 2
    (special_positions=[0,2], figures 11–18), 5 adjacent placements are excluded,
    giving 10 rather than 15 permutations. This gap constraint was
    reverse-engineered to match Wilson's enumeration in the figures.

    >>> for x in marwa_permute([Fraction(729, 512)] + 6 * [Fraction(4, 3)]): print(', '.join(map(str, x)))
    729/512, 4/3, 4/3, 4/3, 4/3, 4/3, 4/3
    4/3, 729/512, 4/3, 4/3, 4/3, 4/3, 4/3
    4/3, 4/3, 729/512, 4/3, 4/3, 4/3, 4/3
    4/3, 4/3, 4/3, 729/512, 4/3, 4/3, 4/3
    4/3, 4/3, 4/3, 4/3, 729/512, 4/3, 4/3
    4/3, 4/3, 4/3, 4/3, 4/3, 729/512, 4/3
    >>>
    >>> for x in marwa_permute([Fraction(45, 32), Fraction(27, 20)] + 5 * [Fraction(4, 3)]): print(', '.join(map(str, x)))
    45/32, 27/20, 4/3, 4/3, 4/3, 4/3, 4/3
    45/32, 4/3, 27/20, 4/3, 4/3, 4/3, 4/3
    45/32, 4/3, 4/3, 27/20, 4/3, 4/3, 4/3
    45/32, 4/3, 4/3, 4/3, 27/20, 4/3, 4/3
    45/32, 4/3, 4/3, 4/3, 4/3, 27/20, 4/3
    4/3, 45/32, 27/20, 4/3, 4/3, 4/3, 4/3
    4/3, 45/32, 4/3, 27/20, 4/3, 4/3, 4/3
    4/3, 45/32, 4/3, 4/3, 27/20, 4/3, 4/3
    4/3, 45/32, 4/3, 4/3, 4/3, 27/20, 4/3
    4/3, 4/3, 45/32, 27/20, 4/3, 4/3, 4/3
    4/3, 4/3, 45/32, 4/3, 27/20, 4/3, 4/3
    4/3, 4/3, 45/32, 4/3, 4/3, 27/20, 4/3
    4/3, 4/3, 4/3, 45/32, 27/20, 4/3, 4/3
    4/3, 4/3, 4/3, 45/32, 4/3, 27/20, 4/3
    4/3, 4/3, 4/3, 4/3, 45/32, 27/20, 4/3
    >>>
    >>> for x in marwa_permute([Fraction(45, 32), Fraction(81, 64), Fraction(64, 45)] + 4 * [Fraction(4, 3)]): print(', '.join(map(str, x)))
    45/32, 81/64, 64/45, 4/3, 4/3, 4/3, 4/3
    45/32, 81/64, 4/3, 64/45, 4/3, 4/3, 4/3
    45/32, 81/64, 4/3, 4/3, 64/45, 4/3, 4/3
    45/32, 81/64, 4/3, 4/3, 4/3, 64/45, 4/3
    45/32, 4/3, 81/64, 64/45, 4/3, 4/3, 4/3
    45/32, 4/3, 81/64, 4/3, 64/45, 4/3, 4/3
    45/32, 4/3, 81/64, 4/3, 4/3, 64/45, 4/3
    45/32, 4/3, 4/3, 81/64, 64/45, 4/3, 4/3
    45/32, 4/3, 4/3, 81/64, 4/3, 64/45, 4/3
    45/32, 4/3, 4/3, 4/3, 81/64, 64/45, 4/3
    4/3, 45/32, 81/64, 64/45, 4/3, 4/3, 4/3
    4/3, 45/32, 81/64, 4/3, 64/45, 4/3, 4/3
    4/3, 45/32, 81/64, 4/3, 4/3, 64/45, 4/3
    4/3, 45/32, 4/3, 81/64, 64/45, 4/3, 4/3
    4/3, 45/32, 4/3, 81/64, 4/3, 64/45, 4/3
    4/3, 45/32, 4/3, 4/3, 81/64, 64/45, 4/3
    4/3, 4/3, 45/32, 81/64, 64/45, 4/3, 4/3
    4/3, 4/3, 45/32, 81/64, 4/3, 64/45, 4/3
    4/3, 4/3, 45/32, 4/3, 81/64, 64/45, 4/3
    4/3, 4/3, 4/3, 45/32, 81/64, 64/45, 4/3
    >>>
    >>> for x in marwa_permute([Fraction(64, 45), Fraction(4, 3), Fraction(45, 32)] + 3 * [Fraction(4, 3)] + [Fraction(81, 64)]): print(', '.join(map(str, x)))
    64/45, 4/3, 45/32, 4/3, 4/3, 4/3, 81/64
    64/45, 4/3, 4/3, 45/32, 4/3, 4/3, 81/64
    64/45, 4/3, 4/3, 4/3, 45/32, 4/3, 81/64
    64/45, 4/3, 4/3, 4/3, 4/3, 45/32, 81/64
    4/3, 64/45, 4/3, 45/32, 4/3, 4/3, 81/64
    4/3, 64/45, 4/3, 4/3, 45/32, 4/3, 81/64
    4/3, 64/45, 4/3, 4/3, 4/3, 45/32, 81/64
    4/3, 4/3, 64/45, 4/3, 45/32, 4/3, 81/64
    4/3, 4/3, 64/45, 4/3, 4/3, 45/32, 81/64
    4/3, 4/3, 4/3, 64/45, 4/3, 45/32, 81/64
    """
    assert len(fourths) == 7
    special_positions = [i for i, f in enumerate(fourths[:-1]) if f != Fraction(4, 3)]

    num_free = len(fourths) - 1
    num_specials = len(special_positions)

    if num_specials == 0:
        return [list(fourths)]
    elif num_specials == 1:
        result = []
        for i in range(num_free):
            perm = num_free * [Fraction(4, 3)] + [fourths[-1]]
            perm[i] = fourths[special_positions[0]]
            result.append(perm)
        return result
    elif num_specials == 2:
        result = []
        for i in range(num_free - 1):
            for j in range(i + special_positions[1], num_free):
                perm = num_free * [Fraction(4, 3)] + [fourths[-1]]
                perm[i] = fourths[special_positions[0]]
                perm[j] = fourths[special_positions[1]]
                result.append(perm)
        return result
    elif num_specials == 3:
        result = []
        for i in range(num_free - 2):
            for j in range(i + special_positions[1], num_free - 1):
                for k in range(
                    j + special_positions[2] - special_positions[1], num_free
                ):
                    perm = num_free * [Fraction(4, 3)] + [fourths[-1]]
                    perm[i] = fourths[special_positions[0]]
                    perm[j] = fourths[special_positions[1]]
                    perm[k] = fourths[special_positions[2]]
                    result.append(perm)
        return result
    else:
        raise ValueError(num_specials)


def marwa(fourths):
    """
    Permutation N in the scl description corresponds to index N-1 in the returned list.

    >>> scales = marwa([Fraction(45, 32), Fraction(27, 20)] + 5 * [Fraction(4, 3)])
    >>> len(scales)
    15
    >>> scales[0]
    [Fraction(1, 1), Fraction(9, 8), Fraction(81, 64), Fraction(45, 32), Fraction(3, 2), Fraction(27, 16), Fraction(243, 128), Fraction(2, 1)]
    """
    return [stack(fs) for fs in marwa_permute(fourths)]
