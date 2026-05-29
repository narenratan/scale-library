"""
>>> numbers = [3, 3, 5]
>>> all_cps = []
>>> for k in range(len(numbers) + 1):
...     root, scale = cps_with_root(numbers, k)
...     shifted_scale = sorted(reduce(x * reduce(root)) for x in scale)
...     print(shifted_scale)
...     all_cps.extend(shifted_scale)
[Fraction(1, 1)]
[Fraction(5, 4), Fraction(3, 2)]
[Fraction(9, 8), Fraction(15, 8)]
[Fraction(45, 32)]
>>> print(euler_fokker_genus(numbers))
[Fraction(1, 1), Fraction(9, 8), Fraction(5, 4), Fraction(45, 32), Fraction(3, 2), Fraction(15, 8)]
>>> assert sorted(all_cps) == euler_fokker_genus(numbers)
"""

from itertools import combinations
from fractions import Fraction
from math import prod, log2, floor


def reduce(x):
    return x * Fraction(2) ** (-floor(log2(x)))


def euler_fokker_genus(numbers):
    """
    >>> euler_fokker_genus([3, 3, 5])
    [Fraction(1, 1), Fraction(9, 8), Fraction(5, 4), Fraction(45, 32), Fraction(3, 2), Fraction(15, 8)]
    """
    products = [
        prod(a) for k in range(len(numbers) + 1) for a in combinations(numbers, k)
    ]
    return sorted({reduce(x) for x in products})


def cps_with_root(numbers, k):
    products = [Fraction(prod(a)) for a in combinations(numbers, k)]
    root = products[0]
    return root, sorted({reduce(x / root) for x in products})
