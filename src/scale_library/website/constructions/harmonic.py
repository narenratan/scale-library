from fractions import Fraction


def harmonic_series_segment(m, n):
    """
    >>> harmonic_series_segment(6, 12)
    [Fraction(1, 1), Fraction(7, 6), Fraction(4, 3), Fraction(3, 2), Fraction(5, 3), Fraction(11, 6), Fraction(2, 1)]
    """
    return [Fraction(i, m) for i in range(m, n + 1)]


def subharmonic_series_segment(m, n):
    """
    >>> subharmonic_series_segment(6, 12)
    [Fraction(1, 1), Fraction(12, 11), Fraction(6, 5), Fraction(4, 3), Fraction(3, 2), Fraction(12, 7), Fraction(2, 1)]
    """
    return sorted(Fraction(n, i) for i in range(m, n + 1))
