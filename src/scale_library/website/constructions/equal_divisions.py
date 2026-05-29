def equal_division(period, n):
    """
    >>> equal_division(1200, 5)
    [0.0, 240.0, 480.0, 720.0, 960.0, 1200.0]
    >>> [round(x) for x in equal_division(1902, 13)]
    [0, 146, 293, 439, 585, 732, 878, 1024, 1170, 1317, 1463, 1609, 1756, 1902]
    """
    return [i * period / n for i in range(n + 1)]
