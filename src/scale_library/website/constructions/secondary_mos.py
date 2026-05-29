from fractions import Fraction
from math import floor, log2


def step_through(s, n, step, start=0):
    """
    >>> parent = [Fraction(1, 1), Fraction(9, 8), Fraction(81, 64), Fraction(4, 3), Fraction(3, 2), Fraction(27, 16), Fraction(243, 128)]
    >>> step_through(parent, 5, step=3, start=0)
    [Fraction(1, 1), Fraction(81, 64), Fraction(4, 3), Fraction(27, 16), Fraction(243, 128)]
    >>> step_through(parent, 5, step=3, start=3)
    [Fraction(9, 8), Fraction(81, 64), Fraction(4, 3), Fraction(27, 16), Fraction(243, 128)]
    """
    N = len(s)
    count = 0
    i = start
    t = []
    while count < n:
        t.append(s[i])
        i = (i + step) % N
        count += 1
    return sorted(t)


def secondary_mos_family(parent_mos, n, step):
    """
    >>> parent = [Fraction(1, 1), Fraction(9, 8), Fraction(81, 64), Fraction(4, 3), Fraction(3, 2), Fraction(27, 16), Fraction(243, 128)]
    >>> for x in secondary_mos_family(parent, 5, step=3): print(x)
    [Fraction(1, 1), Fraction(81, 64), Fraction(4, 3), Fraction(27, 16), Fraction(243, 128)]
    [Fraction(1, 1), Fraction(9, 8), Fraction(4, 3), Fraction(3, 2), Fraction(243, 128)]
    [Fraction(1, 1), Fraction(9, 8), Fraction(81, 64), Fraction(3, 2), Fraction(27, 16)]
    [Fraction(1, 1), Fraction(9, 8), Fraction(32, 27), Fraction(3, 2), Fraction(27, 16)]
    [Fraction(1, 1), Fraction(81, 64), Fraction(4, 3), Fraction(3, 2), Fraction(243, 128)]
    [Fraction(1, 1), Fraction(9, 8), Fraction(4, 3), Fraction(3, 2), Fraction(27, 16)]
    [Fraction(1, 1), Fraction(9, 8), Fraction(4, 3), Fraction(3, 2), Fraction(27, 16)]
    """
    result = []
    for i in range(len(parent_mos)):
        scale = step_through(parent_mos, n, step, start=i)
        transposed_scale = [x / scale[0] for x in scale]
        result.append(transposed_scale)

    assert len(set(standard_mode_steps(x) for x in result)) == n

    return result


def find_secondary_mos(generator, N, n, step):
    """
    >>> family = find_secondary_mos(Fraction(4, 3), 7, 5, 3)
    >>> len(family)
    7
    >>> family = find_secondary_mos(Fraction(4, 3), 17, 7, 5)
    >>> len(family)
    17
    """
    parent = sorted(reduce(generator**i) for i in range(N))
    family = secondary_mos_family(parent, n, step)

    analytic_step_sizes = secondary_mos_step_sizes(
        generator, parent.index(generator), N, step, n
    )
    computed_step_sizes = {s for scale in family for s in steps(scale)}

    assert set(analytic_step_sizes) == computed_step_sizes

    return family


def steps(scale):
    scale = scale + [Fraction(2)]
    return tuple(y / x for x, y in zip(scale, scale[1:]))


def standard_mode_steps(scale):
    """
    >>> scale = [Fraction(1, 1), Fraction(81, 64), Fraction(4, 3), Fraction(27, 16), Fraction(243, 128)]
    >>> standard_mode_steps(scale)
    (Fraction(81, 64), Fraction(9, 8), Fraction(256, 243), Fraction(81, 64), Fraction(256, 243))
    """
    s = steps(scale)
    return max(s[i:] + s[:i] for i in range(len(s)))


def reduce(x):
    return x * Fraction(2) ** (-floor(log2(x)))


def stern_brocot(num, denom):
    """
    >>> stern_brocot(5, 17)
    [((0, 1), (1, 0)), ((0, 1), (1, 1)), ((0, 1), (1, 2)), ((0, 1), (1, 3)), ((1, 4), (1, 3)), ((2, 7), (1, 3)), ((2, 7), (3, 10))]
    """
    a, c = 0, 1  # left  = 0/1
    b, d = 1, 0  # right = 1/0 (infinity)
    result = []
    while True:
        m, n = a + b, c + d
        result.append(((a, c), (b, d)))
        if (m, n) == (num, denom):
            break
        if d == 0 or num * n < denom * m:
            b, d = m, n  # mediant is to the right of fraction
        else:
            a, c = m, n  # mediant is to the left of fraction
    return result


def secondary_mos_step_sizes(G, M, N, step, n):
    """
    Analytic formulae for secondary MOS family step sizes

    These can be derived by mapping the parent MOS to a two-dimensional keyboard.
    `G` is the generator of the parent MOS, e.g. 4/3. `M` is the index of the
    generator in the parent MOS. `N` is the size of the parent MOS. `step` is the
    step used to find the secondary MOS by stepping through the parent MOS.  `n` is
    the number of notes in the secondary MOS.

    Examples from Wilson's MOS letter:

    Tanabe cycle:

    >>> secondary_mos_step_sizes(Fraction(4, 3), 3, 7, 3, 5)
    (Fraction(9, 8), Fraction(256, 243), Fraction(32, 27), Fraction(81, 64))

    Cycle of 17 scales:

    >>> secondary_mos_step_sizes(Fraction(4, 3), 7, 17, 5, 7)
    (Fraction(2187, 2048), Fraction(65536, 59049), Fraction(16777216, 14348907), Fraction(9, 8))

    """
    M_inv = pow(M, -1, N)
    k = (M_inv * step) % N

    # Secondary MOS size n must be a valid mos size for step/N
    c, d = None, None
    for (a, c), (b, d) in stern_brocot(step, N):
        if c + d == n:
            break
    assert c is not None, f"{n} not a valid MOS size for {step}/{N}"

    neg_kd = (-k * d) % N
    kc = (k * c) % N

    # Analytic formulae for secondary MOS step sizes
    S1 = reduce(G ** (neg_kd - N))
    S2 = reduce(G**neg_kd)
    T1 = reduce(G**kc)
    T2 = reduce(G ** (kc - N))

    # Equal ratio property
    assert S2 / S1 == T1 / T2

    # Equal ratio between two smallest and two largest steps
    sorted_steps = sorted({S1, S2, T1, T2})
    assert sorted_steps[1] / sorted_steps[0] == sorted_steps[3] / sorted_steps[2]

    return (S1, S2, T1, T2)
