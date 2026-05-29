"""
>>> scale1 = recurrent_sequence_scale((1, 1), (1, 1), 3, 8)
>>> scale2 = recurrent_sequence_scale((1, 1), (1, 1), 6, 11)
>>> scale3 = sorted((i * 833) % 1200 for i in range(6))
>>> print([round(1200 * log2(x)) for x in scale1])
[0, 139, 498, 603, 884, 969]
>>> print([round(1200 * log2(x)) for x in scale2])
[0, 97, 464, 563, 830, 930]
>>> print(scale3)
[0, 99, 466, 565, 833, 932]
"""

from fractions import Fraction
from math import log2, floor


def reduce(x):
    return x * Fraction(2) ** (-floor(log2(x)))


def recurrent_sequence_scale(coeffs, seed, start, stop):
    """
    >>> recurrent_sequence_scale((1, 1), (1, 1), 3, 8)
    [Fraction(1, 1), Fraction(13, 12), Fraction(4, 3), Fraction(17, 12), Fraction(5, 3), Fraction(7, 4)]
    """
    seq = list(seed)
    while len(seq) <= stop:
        seq.append(sum(c * seq[-i] for i, c in enumerate(coeffs, 1)))
    segment = seq[start : stop + 1]
    return sorted(set(reduce(Fraction(x, segment[0])) for x in segment))
