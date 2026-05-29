import math
from fractions import Fraction

F = Fraction


def tetrachordal(t1, t2, *, disjunct=True):
    """
    >>> t1 = (Fraction(9, 8), Fraction(28, 27), Fraction(8, 7))
    >>> t2 = (Fraction(28, 27), Fraction(9, 8), Fraction(8, 7))
    >>> tetrachordal(t1, t2)
    [Fraction(1, 1), Fraction(9, 8), Fraction(7, 6), Fraction(4, 3), Fraction(3, 2), Fraction(14, 9), Fraction(7, 4), Fraction(2, 1)]
    >>> tetrachordal(t1, t2, disjunct=False)
    [Fraction(1, 1), Fraction(9, 8), Fraction(7, 6), Fraction(4, 3), Fraction(112, 81), Fraction(14, 9), Fraction(16, 9)]
    """
    for t in (t1, t2):
        assert len(t) == 3
        assert math.prod(t) == Fraction(4, 3)

    if disjunct:
        steps = [*t1, Fraction(9, 8), *t2]
    else:
        steps = [*t1, *t2]

    result = [Fraction(1, 1)]
    for step in steps:
        result.append(result[-1] * step)

    assert result[0] == Fraction(1, 1)
    assert result[-1] == (Fraction(2, 1) if disjunct else Fraction(16, 9))

    return result
