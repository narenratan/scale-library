from fractions import Fraction
from math import floor, log2


def reduce(x):
    return x * Fraction(2) ** (-floor(log2(x)))


def tritriadic(M, D):
    """
    >>> tritriadic(Fraction(5, 4), Fraction(3, 2))
    [Fraction(1, 1), Fraction(9, 8), Fraction(5, 4), Fraction(4, 3), Fraction(3, 2), Fraction(5, 3), Fraction(15, 8)]
    """
    triad1 = [1, M, D]
    triad2 = [x * D for x in triad1]
    triad3 = [x / D for x in triad1]
    return sorted(set(reduce(x) for x in triad1 + triad2 + triad3))


def tritriadic_mt(M, D):
    """
    >>> tritriadic_mt(Fraction(5, 4), Fraction(3, 2))
    [Fraction(1, 1), Fraction(6, 5), Fraction(5, 4), Fraction(3, 2), Fraction(25, 16), Fraction(8, 5), Fraction(15, 8)]
    """
    triad1 = [1, M, D]
    triad2 = [x * M for x in triad1]
    triad3 = [x / M for x in triad1]
    return sorted(set(reduce(x) for x in triad1 + triad2 + triad3))


def tritriadic_dm(M, D):
    """
    >>> tritriadic_dm(Fraction(5, 4), Fraction(3, 2))
    [Fraction(1, 1), Fraction(25, 24), Fraction(6, 5), Fraction(5, 4), Fraction(3, 2), Fraction(5, 3), Fraction(9, 5)]
    """
    triad1 = [1, M, D]
    triad2 = [x * D / M for x in triad1]
    triad3 = [x * M / D for x in triad1]
    return sorted(set(reduce(x) for x in triad1 + triad2 + triad3))
