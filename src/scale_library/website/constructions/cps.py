from itertools import combinations
from fractions import Fraction
from math import floor, log2, prod


def reduce(x):
    return x * Fraction(2) ** (-floor(log2(x)))


def cps(A, k, *, root=None):
    """
    >>> cps([1, 3, 5, 7], 2)
    [Fraction(1, 1), Fraction(7, 6), Fraction(5, 4), Fraction(35, 24), Fraction(5, 3), Fraction(7, 4)]
    """
    products = [Fraction(prod(a)) for a in combinations(A, k)]
    if root is None:
        root = products[0]
    return sorted(reduce(x / root) for x in products)
