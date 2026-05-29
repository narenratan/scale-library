from fractions import Fraction
from math import floor, log2


def reduce(x):
    return x * Fraction(2) ** (-floor(log2(x)))


def triadic_diamond(M, D):
    """
    >>> triadic_diamond(Fraction(5, 4), Fraction(3, 2))
    [Fraction(1, 1), Fraction(6, 5), Fraction(5, 4), Fraction(4, 3), Fraction(3, 2), Fraction(8, 5), Fraction(5, 3)]
    """
    notes = [1, M, D, 2 / M, 2 / D, D / M, M / D]
    return sorted(reduce(x) for x in notes)


def triadic_reversed_diamond(M, D):
    """
    >>> triadic_reversed_diamond(Fraction(5, 4), Fraction(3, 2))
    [Fraction(1, 1), Fraction(16, 15), Fraction(5, 4), Fraction(4, 3), Fraction(3, 2), Fraction(8, 5), Fraction(15, 8)]
    """
    notes = [1, M, D, 2 / M, 2 / D, D * M, 2 / (D * M)]
    return sorted(reduce(x) for x in notes)
