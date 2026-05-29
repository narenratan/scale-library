"""
>>> scale1 = iterated_arithmetic_mean([Fraction(1, 1), Fraction(2, 1)], 3)
>>> harmonic_series_segment = [Fraction(i, 2**3) for i in range(2**3, 2**4 + 1)]
>>> assert scale1 == harmonic_series_segment

>>> scale2 = iterated_harmonic_mean([Fraction(1, 1), Fraction(2, 1)], 3)
>>> subharmonic_series_segment = sorted(Fraction(2**4, i) for i in range(2**3, 2**4 + 1))
>>> assert scale2 == subharmonic_series_segment
"""

from fractions import Fraction


def iterated_arithmetic_mean(s, k):
    """
    >>> iterated_arithmetic_mean([Fraction(1, 1), Fraction(2, 1)], 1)
    [Fraction(1, 1), Fraction(3, 2), Fraction(2, 1)]
    >>> iterated_arithmetic_mean([Fraction(1, 1), Fraction(2, 1)], 2)
    [Fraction(1, 1), Fraction(5, 4), Fraction(3, 2), Fraction(7, 4), Fraction(2, 1)]
    >>> iterated_arithmetic_mean([Fraction(1, 1), Fraction(2, 1)], 3)
    [Fraction(1, 1), Fraction(9, 8), Fraction(5, 4), Fraction(11, 8), Fraction(3, 2), Fraction(13, 8), Fraction(7, 4), Fraction(15, 8), Fraction(2, 1)]
    """
    result = list(s)
    for _ in range(k):
        new = [(x + y) / 2 for x, y in zip(result, result[1:])]
        result = sorted(result + new)
    return result


def iterated_harmonic_mean(s, k):
    """
    >>> iterated_harmonic_mean([Fraction(1, 1), Fraction(2, 1)], 1)
    [Fraction(1, 1), Fraction(4, 3), Fraction(2, 1)]
    >>> iterated_harmonic_mean([Fraction(1, 1), Fraction(2, 1)], 2)
    [Fraction(1, 1), Fraction(8, 7), Fraction(4, 3), Fraction(8, 5), Fraction(2, 1)]
    >>> iterated_harmonic_mean([Fraction(1, 1), Fraction(2, 1)], 3)
    [Fraction(1, 1), Fraction(16, 15), Fraction(8, 7), Fraction(16, 13), Fraction(4, 3), Fraction(16, 11), Fraction(8, 5), Fraction(16, 9), Fraction(2, 1)]
    """
    result = list(s)
    for _ in range(k):
        new = [2 / (1 / x + 1 / y) for x, y in zip(result, result[1:])]
        result = sorted(result + new)
    return result
