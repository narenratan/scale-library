from fractions import Fraction
from math import log2, floor


def reduce(x):
    return x * Fraction(2) ** (-floor(log2(x)))


def diamond(A):
    """
    >>> diamond([1, 3, 5])
    [Fraction(1, 1), Fraction(6, 5), Fraction(5, 4), Fraction(4, 3), Fraction(3, 2), Fraction(8, 5), Fraction(5, 3)]
    """
    return sorted(set(reduce(Fraction(x, y)) for x in A for y in A))
