"""
Write out scl files for Xenharmonikon.

For Xenharmonikon, see

    https://frogpeak.org/fpartists/fpchalmers.html

and

    https://www.xenharmonikon.org

"""

import re
import shutil
import math
from decimal import Decimal
from itertools import chain, combinations
from collections import defaultdict, Counter
from dataclasses import dataclass
from fractions import Fraction as F
from math import log2
from pathlib import Path
from typing import Optional
import logging
import itertools
import operator

from scale_library import SCALES_DIR, utils

logger = logging.getLogger(__name__)


def csum(x):
    return list(itertools.accumulate(x))


def cprod(x):
    return list(itertools.accumulate(x, operator.mul))


class Author:
    ayers = "Lydia Ayers"
    bohlen = "Heinz Bohlen"
    burt = "Warren Burt"
    chalmers = "John H. Chalmers, Jr."
    colvig = "William Colvig"
    darreg = "Ivor Darreg"
    erlich = "Paul Erlich"
    forster = "Cris Forster"
    garcia = "Jose L. Garcia"
    gilson = "Bruce R. Gilson"
    grady = "Kraig Grady"
    hanson = "Larry A. Hanson"
    harrison = "Lou Harrison"
    hero = "Barbara Hero"
    keenan = "Dave Keenan"
    leedy = "Douglas Leedy"
    london = "Larry London"
    mclaren = "B. McLaren"
    mitchell = "Geordan Mitchell"
    morrison = "Gary Morrison"
    oconnell = "Walter O'Connell"
    polansky = "Larry Polansky"
    rapoport = "Paul Rapoport"
    rosenthal = "David Rosenthal"
    schulter = "Margo Schulter"
    secor = "George Secor"
    vyshnegradski = "Ivan Vyshnegradski"
    walker = "Douglas Walker"
    wilson = "Erv Wilson"
    wilsonsmithgrady = "Erv Wilson, Steven Smith, Kraig Grady"
    wolf = "Daniel J. Wolf"


JOURNAL = {
    "xen01": (1, "Xenharmonikon 1 (1974)"),
    "xen02": (2, "Xenharmonikon 2 (1974)"),
    "xen03": (3, "Xenharmonikon 3 (1975)"),
    "xen04": (4, "Xenharmonikon 4 (1975)"),
    "xen05": (5, "Xenharmonikon 5 (1976)"),
    "xen06": (6, "Xenharmonikon 6 (1977)"),
    "xen07": ("7 & 8", "Xenharmonikon 7 & 8 (1979)"),
    "xen09": (9, "Xenharmonikon 9 (1986)"),
    "xen10": (10, "Xenharmonikon 10 (1987)"),
    "xen11": (11, "Xenharmonikon 11 (1988)"),
    "xen12": (12, "Xenharmonikon 12 (1989)"),
    "xen13": (13, "Xenharmonikon 13 (1991)"),
    "xen14": (14, "Xenharmonikon 14 (1993)"),
    "xen15": (15, "Xenharmonikon 15 (1993)"),
    "xen16": (16, "Xenharmonikon 16 (1995)"),
    "xen17": (17, "Xenharmonikon 17 (1998)"),
    "xen18": (18, "Xenharmonikon 18 (2006)"),
}


class Tone:
    def __init__(self, x, y=None, comment=None, *, period=1200.0, cents=None):
        if y is None:
            self.cents = x
            self.ratio_n = None
            self.ratio_d = None
        else:
            self.ratio_n = x
            self.ratio_d = y
            self.cents = 1200 * log2(x / y)
            if cents is not None:
                assert abs(cents - self.cents) <= 0.5
        self.comment = comment
        assert (
            0.0 < self.cents <= period
        ), f"Interval '{self}' outside period, check this"

    @property
    def is_ratio(self):
        return self.ratio_n is not None

    @classmethod
    def from_fraction(cls, x, **kwargs):
        return cls(x.numerator, x.denominator, **kwargs)

    def __lt__(self, other):
        if not isinstance(other, Tone):
            return NotImplemented
        return self.cents < other.cents

    def _tone_string(self):
        # scl spec says integers up to 2**31 - 1 should be supported in ratios
        nmax = 2**31 - 1
        rounding = 6
        rounded_cents_str = str(round(self.cents, rounding))
        if self.is_ratio:
            if self.ratio_n <= nmax and self.ratio_d <= nmax:
                return f"{self.ratio_n}/{self.ratio_d}"
            return rounded_cents_str
        elif isinstance(self.cents, float):
            return rounded_cents_str
        elif isinstance(self.cents, Decimal):
            # Rounding a Decimal adds trailing zeros
            if self.cents.as_tuple().exponent >= -rounding:
                return str(self.cents)
            return rounded_cents_str

    def __repr__(self):
        return self._tone_string()

    def scl_line(self, pad=None):
        r = self._tone_string()
        if self.comment is not None:
            n = 1
            if pad is not None:
                n = max(pad - len(r), n)
            r += n * " " + f"! {self.comment}"
        return r


T = Tone


def build_scl(*, description, tones, title, function, comments=None, page=None):
    filename = function.replace("_", "-") + ".scl"
    journal, author, *_ = function.split("_")
    author_name = getattr(Author, author)
    journal_name = JOURNAL[journal][1]
    info = {"source": "Xenharmonikon", "whole_number": JOURNAL[journal][0]}
    tone_strings = [str(x) for x in sorted(tones)]
    max_len = max(len(x) for x in tone_strings)
    # TODO: require Tones here?
    tone_lines = [
        " " + (t.scl_line(pad=max_len + 1) if isinstance(t, Tone) else str(t))
        for t in sorted(tones)
    ]
    if page is not None:
        journal_name = f"{journal_name}, p.{page}"
    scl_lines = (
        [
            f"! {filename}",
            "!",
            description,
            f" {len(tones)}",
            "!",
        ]
        + tone_lines
        + [
            "!",
            f"! {author_name}",
            f"! {title}",
            f"! {journal_name}",
        ]
    )
    if comments is not None:
        scl_lines += ["!"] + [f"! {x}" for x in comments]
    scl_lines += ["!", "! [info]"] + [f"! {k} = {v}" for k, v in info.items()]
    scl_text = "\n".join(scl_lines) + "\n"

    reference = f"{author_name}, {title}, {journal_name}"
    return filename, scl_text, reference


def xen02_wilson_indic(f):
    tones = [
        T(256, 243),
        T(10, 9),
        T(16, 15),
        T(9, 8),
        T(32, 27),
        T(5, 4),
        T(6, 5),
        T(81, 64),
        T(4, 3),
        T(45, 32),
        T(27, 20),
        T(729, 512, "Originally printed as 729/256"),
        T(3, 2),
        T(128, 81),
        T(5, 3),
        T(8, 5),
        T(27, 16),
        T(16, 9),
        T(15, 8),
        T(9, 5),
        T(243, 128),
        T(2, 1),
    ]
    assert len(tones) == 22
    return build_scl(
        description="Indic system of 22 s'ruti (for you, Lou)",
        tones=tones,
        title="Bosanquet - A Bridge - A Doorway To Dialog",
        function=f,
    )


def xen02_wilson_arabic(f):
    tones = [
        T(135, 128),
        T(10, 9),
        T(9, 8),
        T(32, 27),
        T(5, 4),
        T(81, 64),
        T(4, 3),
        T(45, 32),
        T(40, 27),
        T(3, 2),
        T(128, 81, "= 405/256"),
        T(5, 3),
        T(27, 16, "Originally printed as 27/32"),
        T(16, 9),
        T(15, 8),
        T(160, 81),
        T(2, 1),
    ]
    assert len(tones) == 17
    return build_scl(
        description="Classic Arabic System of 17 tones (for Gary)",
        tones=tones,
        title="Bosanquet - A Bridge - A Doorway To Dialog",
        function=f,
    )


def xen02_wilson_combination_sets(f):
    labels = [
        (5, 7, 11),
        (5, 7, 9, 11),
        #
        (3, 5, 7, 11),
        (3, 5, 7, 9, 11),
        (3, 7, 11),
        (3, 7, 9, 11),
        #
        (7, 11),
        (7, 9, 11),
        (5, 11),
        (5, 9, 11),
        #
        (3, 7, 9, 11),
        (3, 5, 11),
        (3, 5, 9, 11),
        (3, 5, 7),
        (3, 5, 7, 9),
        (3, 11),
        #
        (5, 7),
        (5, 7, 9),
        (11,),
        (9, 11),
        (7,),
        (7, 9),
        #
        (3, 11),
        (3, 9, 11),
        (3, 7),
        (3, 7, 9),
        (3, 5),
        (3, 5, 9),
        #
        (5,),
        (5, 9),
        (1,),
        #
        (3, 5, 9),
        (3,),
        (3, 9),
        #
        (9,),
    ]
    factors = sorted(set(labels))
    tones = [
        T.from_fraction(reduce(F(math.prod(x), 3 * 11)), comment="*".join(map(str, x)))
        for x in factors
    ]
    assert len(tones) == 32
    return build_scl(
        description="1*3*5*7*9*11 Combination Sets - 1 3 5 7 9 11 Diamondic Cross-Set",
        tones=tones,
        title="Bosanquet - A Bridge - A Doorway To Dialog",
        function=f,
        comments=["See also Wilson XH12 Figure 21, Beth"],
    )


def xen03_colvig_gamelan_7_11(f):
    tones = [
        T(9, 8),
        T(11, 8),
        T(3, 2),
        T(7, 4),
        T(2, 1),
    ]
    assert len(tones) == 5
    return build_scl(
        description="Colvig's American Gamelan 7-11 scale",
        tones=tones,
        title="An American Gamelan",
        function=f,
        comments=["Written as A C7 D E G11 A"],
    )


def xen03_secor_partch(f):
    tones = [
        T(2, 1),
        T(9, 8),
        T(32, 27),
        T(4, 3),
        T(3, 2),
        T(27, 16),
        T(16, 9),
        #
        T(160, 81),
        T(10, 9),
        T(5, 4),
        T(40, 27),
        T(5, 3),
        T(15, 8),
        #
        T(81, 80),
        T(16, 15),
        T(6, 5),
        T(27, 20),
        T(8, 5),
        T(9, 5),
        #
        T(21, 20),
        T(7, 6),
        T(21, 16),
        T(7, 5),
        T(14, 9),
        T(7, 4),
        #
        T(8, 7),
        T(9, 7),
        T(10, 7),
        T(32, 21),
        T(12, 7),
        T(40, 21),
        #
        T(33, 32),
        T(11, 10),
        T(11, 9),
        T(11, 8),
        T(11, 7),
        T(11, 6),
        #
        T(64, 33),
        T(12, 11),
        T(14, 11),
        T(16, 11),
        T(18, 11),
        T(20, 11),
    ]
    assert len(tones) == 43
    return build_scl(
        description="Partch Monophonic Fabric",
        tones=tones,
        title="A new look at the Partch Monophonic Fabric",
        function=f,
    )


def xen03_wilson_baglama(f):
    tones = [
        T(256, 243),
        T(12, 11),
        T(9, 8),
        T(32, 27),
        T(5, 4),
        T(81, 64),
        T(4, 3),
        T(1024, 729),
        T(16, 11),
        T(3, 2),
        T(128, 81),
        T(5, 3),
        T(27, 16),
        T(16, 9),
        T(15, 8),
        T(243, 128),
        T(2, 1),
    ]
    assert len(tones) == 17
    return build_scl(
        description="Turkish Baglama Scale (as inferred from string lengths by E.W.)",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        function=f,
    )


NEGATIVE = [
    F(64, 63),
    F(28, 27),
    F(16, 15),
    F(12, 11),
    F(9, 8),
    F(8, 7),
    F(7, 6),
    F(6, 5),
    F(27, 22),
    F(5, 4),
    F(80, 63),
    F(35, 27),
    F(4, 3),
    F(256, 189),
    F(112, 81),
    F(64, 45),
    F(16, 11),
    F(3, 2),
    F(32, 21),
    F(14, 9),
    F(8, 5),
    F(18, 11),
    F(27, 16),
    F(12, 7),
    F(7, 4),
    F(9, 5),
    F(81, 44),
    F(15, 8),
    F(40, 21),
    F(35, 18),
    F(2, 1),
]

assert len(NEGATIVE) == 31


def xen03_wilson_negative_05(f):
    steps = [
        F(6, 5),
        F(10, 9),
        F(9, 8),
        F(6, 5),
        F(10, 9),
    ]
    counts = [
        8,
        5,
        5,
        8,
        5,
    ]
    assert sum(counts) == len(NEGATIVE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [NEGATIVE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Negative, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagram 4"],
        function=f,
    )


def xen03_wilson_negative_07(f):
    steps = [
        F(16, 15),
        F(9, 8),
        F(10, 9),
        F(9, 8),
        F(16, 15),
        F(9, 8),
        F(10, 9),
    ]
    counts = [
        3,
        5,
        5,
        5,
        3,
        5,
        5,
    ]
    assert sum(counts) == len(NEGATIVE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [NEGATIVE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Negative, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagram 4"],
        function=f,
    )


def xen03_wilson_negative_12(f):
    steps = [
        F(16, 15),
        F(135, 128),
        F(16, 15),
        F(25, 24),
        F(16, 15),
        F(16, 15),
        F(135, 128),
        F(16, 15),
        F(135, 128),
        F(16, 15),
        F(25, 24),
        F(16, 15),
    ]
    counts = [
        3,
        2,
        3,
        2,
        3,
        3,
        2,
        3,
        2,
        3,
        2,
        3,
    ]
    assert sum(counts) == len(NEGATIVE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [NEGATIVE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Negative, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagram 4"],
        function=f,
    )


def xen03_wilson_negative_19(f):
    steps = [
        F(28, 27),
        F(36, 35),
        F(135, 128),
        F(28, 27),
        F(36, 35),
        F(25, 24),
        F(28, 27),
        F(36, 35),
        F(28, 27),
        F(36, 35),
        F(135, 128),
        F(28, 27),
        F(36, 35),
        F(135, 128),
        F(28, 27),
        F(36, 35),
        F(25, 24),
        F(28, 27),
        F(36, 35),
    ]
    counts = [
        2,
        1,
        2,
        2,
        1,
        2,
        2,
        1,
        2,
        1,
        2,
        2,
        1,
        2,
        2,
        1,
        2,
        2,
        1,
    ]
    assert sum(counts) == len(NEGATIVE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [NEGATIVE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Negative, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagram 4"],
        function=f,
    )


def xen03_wilson_negative_31(f):
    steps = [
        F(64, 63),
        F(49, 48),
        F(36, 35),
        F(45, 44),
        F(33, 32),
        F(64, 63),
        F(49, 48),
        F(36, 35),
        F(45, 44),
        F(55, 54),
        F(64, 63),
        F(49, 48),
        F(36, 35),
        F(64, 63),
        F(49, 48),
        F(36, 35),
        F(45, 44),
        F(33, 32),
        F(64, 63),
        F(49, 48),
        F(36, 35),
        F(45, 44),
        F(33, 32),
        F(64, 63),
        F(49, 48),
        F(36, 35),
        F(45, 44),
        F(55, 54),
        F(64, 63),
        F(49, 48),
        F(36, 35),
    ]
    counts = 31 * [1]
    assert sum(counts) == len(NEGATIVE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [NEGATIVE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Negative, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagrams 4 and 7"],
        function=f,
    )


POSITIVE = [
    F(64, 63),
    F(28, 27),
    F(256, 243),
    F(16, 15),
    F(12, 11),
    F(10, 9),
    F(9, 8),
    F(8, 7),
    F(7, 6),
    F(32, 27),
    F(6, 5),
    F(27, 22),
    F(5, 4),
    F(81, 64),
    F(9, 7),
    F(21, 16),
    F(4, 3),
    F(256, 189),
    F(112, 81),
    F(1024, 729),
    F(64, 45),
    F(16, 11),
    F(40, 27),
    F(3, 2),
    F(32, 21),
    F(14, 9),
    F(128, 81),
    F(8, 5),
    F(18, 11),
    F(5, 3),
    F(27, 16),
    F(12, 7),
    F(7, 4),
    F(16, 9),
    F(9, 5),
    F(81, 44),
    F(15, 8),
    F(243, 128),
    F(27, 14),
    F(63, 32),
    F(2, 1),
]

assert len(POSITIVE) == 41


def xen03_wilson_positive_05(f):
    steps = [
        F(32, 27),
        F(9, 8),
        F(9, 8),
        F(32, 27),
        F(9, 8),
    ]
    counts = [
        10,
        7,
        7,
        10,
        7,
    ]
    assert sum(counts) == len(POSITIVE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [POSITIVE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Positive, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagram 5"],
        function=f,
    )


def xen03_wilson_positive_07(f):
    steps = [
        F(256, 243),
        F(9, 8),
        F(9, 8),
        F(9, 8),
        F(256, 243),
        F(9, 8),
        F(9, 8),
    ]
    counts = [
        3,
        7,
        7,
        7,
        3,
        7,
        7,
    ]
    assert sum(counts) == len(POSITIVE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [POSITIVE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Positive, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagram 5"],
        function=f,
    )


def xen03_wilson_positive_12(f):
    steps = [
        F(256, 243),
        F(2187, 2048),
        F(256, 243),
        F(2187, 2048),
        F(256, 243),
        F(256, 243),
        F(2187, 2048),
        F(256, 243),
        F(2187, 2048),
        F(256, 243),
        F(2187, 2048),
        F(256, 243),
    ]
    counts = [
        3,
        4,
        3,
        4,
        3,
        3,
        4,
        3,
        4,
        3,
        4,
        3,
    ]
    assert sum(counts) == len(POSITIVE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [POSITIVE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Positive, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagram 5"],
        function=f,
    )


def xen03_wilson_positive_17(f):
    steps = [
        F(256, 243),
        F(135, 128),
        F(81, 80),
        F(256, 243),
        F(135, 128),
        F(81, 80),
        F(256, 243),
        F(256, 243),
        F(135, 128),
        F(81, 80),
        F(256, 243),
        F(135, 128),
        F(81, 80),
        F(256, 243),
        F(135, 128),
        F(81, 80),
        F(256, 243),
    ]
    counts = [
        3,
        3,
        1,
        3,
        3,
        1,
        3,
        3,
        3,
        1,
        3,
        3,
        1,
        3,
        3,
        1,
        3,
    ]
    assert sum(counts) == len(POSITIVE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [POSITIVE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Positive, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagram 5"],
        function=f,
    )


def xen03_wilson_positive_29(f):
    steps = [
        F(28, 27),
        F(64, 63),
        F(81, 80),
        F(25, 24),
        F(81, 80),
        F(28, 27),
        F(64, 63),
        F(81, 80),
        F(25, 24),
        F(81, 80),
        F(28, 27),
        F(64, 63),
        F(28, 27),
        F(64, 63),
        F(81, 80),
        F(25, 24),
        F(81, 80),
        F(28, 27),
        F(64, 63),
        F(81, 80),
        F(25, 24),
        F(81, 80),
        F(28, 27),
        F(64, 63),
        F(81, 80),
        F(25, 24),
        F(81, 80),
        F(28, 27),
        F(64, 63),
    ]
    counts = [
        2,
        1,
        1,
        2,
        1,
        2,
        1,
        1,
        2,
        1,
        2,
        1,
        2,
        1,
        1,
        2,
        1,
        2,
        1,
        1,
        2,
        1,
        2,
        1,
        1,
        2,
        1,
        2,
        1,
    ]
    assert sum(counts) == len(POSITIVE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [POSITIVE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Positive, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagram 5"],
        function=f,
    )


def xen03_wilson_positive_41(f):
    steps = [
        F(64, 63),
        F(49, 48),
        F(64, 63),
        F(81, 80),
        F(45, 44),
        F(55, 54),
        F(81, 80),
        F(64, 63),
        F(49, 48),
        F(64, 63),
        F(81, 80),
        F(45, 44),
        F(55, 54),
        F(81, 80),
        F(64, 63),
        F(49, 48),
        F(64, 63),
        F(64, 63),
        F(49, 48),
        F(64, 63),
        F(81, 80),
        F(45, 44),
        F(55, 54),
        F(81, 80),
        F(64, 63),
        F(49, 48),
        F(64, 63),
        F(81, 80),
        F(45, 44),
        F(55, 54),
        F(81, 80),
        F(64, 63),
        F(49, 48),
        F(64, 63),
        F(81, 80),
        F(45, 44),
        F(55, 54),
        F(81, 80),
        F(64, 63),
        F(49, 48),
        F(64, 63),
    ]
    counts = 41 * [1]
    assert sum(counts) == len(POSITIVE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [POSITIVE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Positive, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagrams 5 and 8"],
        function=f,
    )


ACUTE = [
    F(28, 27),
    F(16, 15),
    F(10, 9),
    F(9, 8),
    F(7, 6),
    F(6, 5),
    F(5, 4),
    F(35, 27),
    F(4, 3),
    F(112, 81),
    F(64, 45),
    F(40, 27),
    F(3, 2),
    F(14, 9),
    F(8, 5),
    F(5, 3),
    F(27, 16),
    F(7, 4),
    F(9, 5),
    F(15, 8),
    F(35, 18),
    F(2, 1),
]

assert len(ACUTE) == 22


def xen03_wilson_acute_05(f):
    steps = [
        F(7, 6),
        F(8, 7),
        F(9, 8),
        F(7, 6),
        F(8, 7),
    ]
    counts = [
        5,
        4,
        4,
        5,
        4,
    ]
    assert sum(counts) == len(ACUTE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [ACUTE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Acute, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagram 6"],
        function=f,
    )


def xen03_wilson_acute_07(f):
    steps = [
        F(28, 27),
        F(9, 8),
        F(8, 7),
        F(9, 8),
        F(28, 27),
        F(9, 8),
        F(8, 7),
    ]
    counts = [
        1,
        4,
        4,
        4,
        1,
        4,
        4,
    ]
    assert sum(counts) == len(ACUTE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [ACUTE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Acute, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagram 6"],
        function=f,
    )


def xen03_wilson_acute_12(f):
    steps = [
        F(28, 27),
        F(243, 224),
        F(28, 27),
        F(10, 9),
        F(36, 35),
        F(28, 27),
        F(243, 224),
        F(28, 27),
        F(243, 224),
        F(28, 27),
        F(10, 9),
        F(36, 35),
    ]
    counts = [
        1,
        3,
        1,
        3,
        1,
        1,
        3,
        1,
        3,
        1,
        3,
        1,
    ]
    assert sum(counts) == len(ACUTE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [ACUTE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Acute, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagram 6"],
        function=f,
    )


def xen03_wilson_acute_17(f):
    steps = [
        F(28, 27),
        F(36, 35),
        F(135, 128),
        F(28, 27),
        F(36, 35),
        F(175, 162),
        F(36, 35),
        F(28, 27),
        F(36, 35),
        F(135, 128),
        F(28, 27),
        F(36, 35),
        F(135, 128),
        F(28, 27),
        F(36, 35),
        F(175, 162),
        F(36, 35),
    ]
    counts = [
        1,
        1,
        2,
        1,
        1,
        2,
        1,
        1,
        1,
        2,
        1,
        1,
        2,
        1,
        1,
        2,
        1,
    ]
    assert sum(counts) == len(ACUTE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [ACUTE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Acute, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagram 6"],
        function=f,
    )


def xen03_wilson_acute_22(f):
    steps = [
        F(28, 27),
        F(36, 35),
        F(25, 24),
        F(81, 80),
        F(28, 27),
        F(36, 35),
        F(25, 24),
        F(28, 27),
        F(36, 35),
        F(28, 27),
        F(36, 35),
        F(25, 24),
        F(81, 80),
        F(28, 27),
        F(36, 35),
        F(25, 24),
        F(81, 80),
        F(28, 27),
        F(36, 35),
        F(25, 24),
        F(28, 27),
        F(36, 35),
    ]
    counts = 22 * [1]
    assert sum(counts) == len(ACUTE)
    intervals_from_steps = cprod(steps)
    intervals_from_counts = [ACUTE[i - 1] for i in csum(counts)]
    assert intervals_from_steps == intervals_from_counts
    tones = [T.from_fraction(x) for x in intervals_from_steps]
    N = int(f.split("_")[-1])
    assert len(tones) == N
    return build_scl(
        description=f"Acute, linear-mapped intonational system, {N} notes",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        comments=["Diagrams 6 and 9"],
        function=f,
    )


def xen03_wilson_partch(f):
    tones = [
        T(81, 80),
        T(33, 32),
        T(21, 20),
        T(16, 15),
        T(12, 11),
        T(11, 10, "or 10/9"),
        T(9, 8),
        T(8, 7),
        T(7, 6),
        T(32, 27),
        T(6, 5),
        T(11, 9),
        T(5, 4),
        T(14, 11),
        T(9, 7),
        T(21, 16),
        T(4, 3),
        T(27, 20),
        T(11, 8),
        T(7, 5),
        T(10, 7),
        T(16, 11),
        T(40, 27),
        T(3, 2),
        T(32, 21),
        T(14, 9),
        T(11, 7),
        T(8, 5),
        T(18, 11),
        T(5, 3),
        T(27, 16),
        T(12, 7),
        T(7, 4),
        T(16, 9),
        T(9, 5, "or 20/11"),
        T(11, 6),
        T(15, 8),
        T(40, 21),
        T(64, 33),
        T(160, 81),
        T(2, 1),
    ]
    assert len(tones) == 41
    return build_scl(
        description="Harry Partch's Scale on the Bosanquet keyboard",
        tones=tones,
        title="On the development of intonational systems by extended linear mapping",
        function=f,
    )


def xen05_walker_golden(f):
    tones_and_cents = [
        (T(16, 15), 111.7),
        (T(10, 9), 182.4),
        (T(9, 8), 203.9),
        (T(7, 6), 266.9),
        (T(32, 27), 294.1),
        (T(11, 9), 347.4),
        (T(5, 4), 386.3),
        (T(4, 3), 498.0),
        (T(11, 8), 551.3),
        (T(10, 7), 617.5),
        (T(40, 27), 680.5),
        (T(3, 2), 702.0),
        (T(14, 9), 764.9),
        (T(5, 3), 884.4),
        (T(27, 16), 905.9),
        (T(7, 4), 968.8),
        (T(16, 9), 996.1),
        (T(20, 11), 1035.0),
        (T(11, 6), 1049.4),
        (T(40, 21), 1115.5),
        (T(2, 1), 1200.0),
    ]
    for tone, cents in tones_and_cents:
        assert abs(tone.cents - cents) <= 1.0
    tones = [x[0] for x in tones_and_cents]
    assert len(tones) == 21
    return build_scl(
        description="Scale used in the composition 'The Golden Net'",
        tones=tones,
        title="The Golden Net",
        function=f,
    )


def xen05_wilson_scott(f):
    tones = [
        T(16, 15),
        T(25, 24),
        T(9, 8),
        T(6, 5),
        T(32, 25),
        T(75, 64),
        T(5, 4),
        T(4, 3),
        T(36, 25),
        T(45, 32),
        T(3, 2),
        T(8, 5),
        T(25, 16),
        T(5, 3),
        T(9, 5),
        T(48, 25),
        T(225, 128),
        T(15, 8),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="A Scale for Scott",
        tones=tones,
        title="The Pitches of Meantone Assigned to the 19-tone Generalized Keyboard",
        function=f,
    )


def xen05_secor_3(f):
    tones = [
        T(310.3),
        T(393.4),
        T(503.4),
        T(602.7),
        T(696.6),
        T(812.0),
        T(891.4),
        T(1006.8),
        T(1095.4),
        T(1200.0),
        T(110.0),
        T(193.2),
    ]
    assert len(tones) == 12
    return build_scl(
        description="Secor No. 3",
        tones=tones,
        title="The Trouble with Equal Temperaments",
        function=f,
    )


def xen05_secor_2(f):
    tones = [
        T(308.6),
        T(398.8),
        T(503.4),
        T(602.7),
        T(696.6),
        T(806.6),
        T(896.8),
        T(1006.8),
        T(1100.7),
        T(1200.0),
        T(104.6),
        T(194.9),
    ]
    assert len(tones) == 12
    return build_scl(
        description="Secor No. 2",
        tones=tones,
        title="The Trouble with Equal Temperaments",
        function=f,
    )


SECOR_HTT = [
    T(235.158),
    T(731.579),
    T(28.000),
    T(524.422),
    T(1020.843),
    T(317.264),
    T(813.686),
    T(110.107),
    T(614.000),
    T(1117.893),
    T(414.314),
    T(910.736),
    T(207.157),
    T(703.578),
    T(1200.000),
    T(496.421),
    T(996.846),
    T(293.268),
    T(789.669),
    T(86.110),
    T(582.512),
    T(1078.933),
    T(375.354),
    T(871.776),
    T(168.197),
    T(664.618),
    T(1161.040),
    T(457.461),
    T(953.882),
    T(250.304),
    T(746.725),
]


def xen05_secor_high_tolerance(f):
    tones = SECOR_HTT[:29]
    assert len(tones) == 29
    return build_scl(
        description="Secor 15-limit high tolerance temperament",
        tones=tones,
        title="The Trouble with Equal Temperaments",
        function=f,
    )


def xen05_secor_high_tolerance_31(f):
    tones = SECOR_HTT
    assert len(tones) == 31
    return build_scl(
        description="Secor 15-limit high tolerance temperament, extended for 31-tone keyboard",
        tones=tones,
        title="The Trouble with Equal Temperaments",
        function=f,
    )


def xen05_secor_high_tolerance_19(f):
    indices = [2, 3, 4, 5, 6, 11, 12, 13, 14, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
    tones = [SECOR_HTT[i] for i in indices]
    assert len(tones) == 19
    return build_scl(
        description="Secor 15-limit high tolerance temperament, 19-tone subset",
        tones=tones,
        title="The Trouble with Equal Temperaments",
        function=f,
    )


def xen05_harrison_cinna(f):
    tones = [
        T(16, 15),
        T(10, 9),
        T(7, 6),
        T(5, 4),
        T(4, 3),
        T(25, 18),
        T(3, 2),
        T(8, 5),
        T(5, 3),
        T(7, 4),
        T(15, 8),
        T(2, 1),
    ]
    assert len(tones) == 12
    return build_scl(
        description="Scale for 'Incidental Music for Corneille's \"Cinna\"'",
        tones=tones,
        title='Incidental Music for Corneille\'s "Cinna"',
        function=f,
    )


def xen06_vyshnegradski_nonoctave_1(f):
    steps = [
        1,
        3 / 4,
        1,
        1 / 2,
        3 / 4,
        3 / 4,
        3 / 4,
        3 / 4,
    ]
    assert sum(steps) == 6 + 1 / 4
    tones = [T(200.0 * x, period=1250.0) for x in csum(steps)]
    assert len(tones) == 8
    return build_scl(
        description="Non-octave scale based on the subminor ninth",
        tones=tones,
        title="Manual of Quartertone Harmony, translated by Ivor Darreg",
        function=f,
    )


def xen06_vyshnegradski_nonoctave_2(f):
    steps = [
        5 / 4,
        1,
        3 / 4,
        1 / 2,
        3 / 4,
    ]
    assert sum(steps) == 4 + 1 / 4
    tones = [T(200.0 * x, period=850.0) for x in csum(steps)]
    assert len(tones) == 5
    return build_scl(
        description="Non-octave scale based on the neutral sixth",
        tones=tones,
        title="Manual of Quartertone Harmony, translated by Ivor Darreg",
        function=f,
    )


def xen06_vyshnegradski_nonoctave_3(f):
    steps = [
        3 / 4,
        5 / 4,
        5 / 4,
        1,
        3 / 4,
        5 / 4,
        1,
        5 / 4,
        5 / 4,
        1,
        5 / 4,
    ]
    assert sum(steps) == 12
    tones = [T(200.0 * x, period=2400.0) for x in csum(steps)]
    assert len(tones) == 11
    return build_scl(
        description="Non-octave scale based on the double octave",
        tones=tones,
        title="Manual of Quartertone Harmony, translated by Ivor Darreg",
        function=f,
    )


OCTAVE_1 = [
    F(21, 20),
    F(9, 8),
    F(6, 5),
    F(5, 4),
    F(4, 3),
    F(7, 5),
    F(3, 2),
    F(8, 5),
    F(5, 3),
    F(7, 4),
    F(15, 8),
    F(2, 1),
]

OCTAVE_3 = [
    F(33, 32),
    F(9, 8),
    F(6, 5),
    F(5, 4),
    F(21, 16),
    F(11, 8),
    F(3, 2),
    F(8, 5),
    F(13, 8),
    F(7, 4),
    F(15, 8),
    F(2, 1),
]

OCTAVE_4 = [
    F(21, 20),
    F(9, 8),
    F(7, 6),
    F(5, 4),
    F(4, 3),
    F(11, 8),
    F(3, 2),
    F(8, 5),
    F(27, 16),
    F(7, 4),
    F(15, 8),
    F(2, 1),
]


def xen06_polansky_study_1(f):
    tones = [T.from_fraction(x) for x in OCTAVE_1]
    assert len(tones) == 12
    return build_scl(
        description="Octave I and II tuning for 'Piano Study #5 (For JPR)'",
        tones=tones,
        title="Piano Study #5 (for JPR), for Just Fender Rhodes",
        function=f,
    )


def xen06_polansky_study_3(f):
    tones = [T.from_fraction(x) for x in OCTAVE_3]
    assert len(tones) == 12
    return build_scl(
        description="Octave III tuning for 'Piano Study #5 (For JPR)'",
        tones=tones,
        title="Piano Study #5 (for JPR), for Just Fender Rhodes",
        function=f,
    )


def xen06_polansky_study_4(f):
    tones = [T.from_fraction(x) for x in OCTAVE_4]
    assert len(tones) == 12
    return build_scl(
        description="Octave IV tuning for 'Piano Study #5 (For JPR)'",
        tones=tones,
        title="Piano Study #5 (for JPR), for Just Fender Rhodes",
        function=f,
    )


def xen06_polansky_study_full(f):
    all_notes = (
        OCTAVE_1
        + [2 * x for x in OCTAVE_1]
        + [2**2 * x for x in OCTAVE_3]
        + [2**3 * x for x in OCTAVE_4]
    )
    tones = [T.from_fraction(x, period=4800.0) for x in all_notes]
    assert len(tones) == 48
    return build_scl(
        description="Full four octave tuning for 'Piano Study #5 (For JPR)'",
        tones=tones,
        title="Piano Study #5 (for JPR), for Just Fender Rhodes",
        function=f,
    )


def xen06_london_ditone_diatonic(f):
    steps = [
        F(9, 8),
        F(9, 8),
        F(256, 243),
        F(9, 8),
        F(9, 8),
        F(9, 8),
        F(256, 243),
    ]
    tones = [T.from_fraction(x) for x in cprod(steps)]
    assert len(tones) == 7
    return build_scl(
        description="Tuning for 'Eight Pieces for Harp in Ditone Diatonic'",
        tones=tones,
        title="Eight Pieces for Harp in Ditone Diatonic",
        function=f,
    )


def reduce(x):
    while x <= 1:
        x *= 2
    while x > 2:
        x /= 2
    return x


def xen06_wilson_clavichord_19(f):
    labels = [
        # (F(1, 7), 264),
        (F(5, 3 * 11), 280),
        #
        (F(1, 3**3), 273.78),  # Printed as 373.78
        (F(7, 11), 294),
        (F(3 * 5, 11), 315),
        (F(1, 11), 336),
        #
        (F(1, 3), 308),
        (F(1, 3**2 * 5), 328.53),
        (F(1, 3 * 7), 352),
        (F(3**2, 11), 378),
        #
        (F(1, 5), 369.6),
        (F(3, 7), 396),
        (F(5, 11), 420),
        #
        (F(1, 3**2), 410.67),
        (F(3 * 7, 11), 441),
        (F(3**2 * 5, 11), 472.5),
        (F(3, 11), 504),
        #
        (F(1, 1), 462),
        (F(1, 3 * 5), 492.8),
        (F(1, 7), 528),
    ]
    assert len(labels) == 19
    ratio_pairs = [(reduce(7 * x), freq / 264) for x, freq in labels]
    for ratio, freq_ratio in ratio_pairs:
        assert abs(1200 * log2(ratio / freq_ratio)) < 1.0
    tones = [T.from_fraction(x) for x, _ in ratio_pairs]
    assert len(tones) == 19
    return build_scl(
        description="Scale for the Clavichord-19",
        tones=tones,
        title="19-tone Scale for the Clavichord-19",
        function=f,
    )


def xen07_forster_diamond(f):
    p = [1, 5, 3, 7, 9, 11, 13]
    ratios = sorted({reduce(F(x, y)) for x in p for y in p})
    tones = [T.from_fraction(x) for x in ratios]
    return build_scl(
        description="Tuning of the Diamond Marimba II",
        tones=tones,
        title="Introduction to Everything",
        function=f,
    )


def xen07_walker_fathomless(f):
    tones = [
        T(16, 15),
        T(10, 9),
        T(9, 8),
        T(8, 7),
        T(7, 6),
        T(32, 27),
        T(6, 5),
        T(5, 4),
        T(9, 7),
        T(4, 3),
        T(3, 2),
        T(14, 9),
        T(8, 5),
        T(5, 3),
        T(27, 16),
        T(12, 7),
        T(7, 4),
        T(16, 9),
        T(9, 5),
        T(15, 8),
        T(2, 1),
    ]
    assert len(tones) == 21
    return build_scl(
        description="Scale for '...out of the fathomless Dark / into the limitless Light...'",
        tones=tones,
        title="Out of fathomless dark/into limitless light",
        function=f,
    )


def xen07_morrison_decimal(f):
    tones = [
        T(15, 14),
        T(8, 7),
        T(16, 13),
        T(4, 3),
        T(7, 5),
        T(3, 2),
        T(13, 8),
        T(7, 4),
        T(28, 15),
        T(2, 1),
    ]
    assert len(tones) == 10
    return build_scl(
        description="Just approximation to ten tone equal temperament.",
        tones=tones,
        title="Decimal Music",
        function=f,
    )


def xen07_harrison_thoughts_1(f):
    partials = [12, 13, 14, 17, 18, 19, 21]
    tones = [T.from_fraction(reduce(F(x, partials[0]))) for x in partials]
    assert len(tones) == 7
    return build_scl(
        description="Pelog based on partials " + "/".join(str(x) for x in partials),
        tones=tones,
        title="ITEM: Thoughts while designing a Gamelan",
        function=f,
    )


def xen07_harrison_thoughts_2(f):
    partials = [10, 11, 12, 14, 15, 16, 18]
    tones = [T.from_fraction(reduce(F(x, partials[0]))) for x in partials]
    assert len(tones) == 7
    return build_scl(
        description="Pelog based on partials " + "/".join(str(x) for x in partials),
        tones=tones,
        title="ITEM: Thoughts while designing a Gamelan",
        function=f,
    )


def xen07_harrison_thoughts_3(f):
    partials = [30, 32, 35, 40, 44, 47, 54]
    tones = [T.from_fraction(reduce(F(x, partials[0]))) for x in partials]
    assert len(tones) == 7
    return build_scl(
        description="Pelog based on partials " + "/".join(str(x) for x in partials),
        tones=tones,
        title="ITEM: Thoughts while designing a Gamelan",
        function=f,
    )


def xen07_harrison_thoughts_4(f):
    steps = [F(8, 7), F(7, 6), F(9, 8), F(8, 7), F(7, 6)]
    tones = [T.from_fraction(x) for x in cprod(steps)]
    assert len(tones) == 5
    return build_scl(
        description="Slendro with steps " + ", ".join(str(x) for x in steps),
        tones=tones,
        title="ITEM: Thoughts while designing a Gamelan",
        function=f,
    )


def xen07_harrison_thoughts_5(f):
    partials = [12, 14, 16, 18, 21]
    tones = [T.from_fraction(reduce(F(x, partials[0]))) for x in partials]
    assert len(tones) == 5
    return build_scl(
        description="Slendro based on partials " + "/".join(str(x) for x in partials),
        tones=tones,
        title="ITEM: Thoughts while designing a Gamelan",
        function=f,
    )


def xen07_harrison_thoughts_6(f):
    partials = [12, 14, 16, 19, 21]
    tones = [T.from_fraction(reduce(F(x, partials[0]))) for x in partials]
    assert len(tones) == 5
    return build_scl(
        description="Slendro based on partials " + "/".join(str(x) for x in partials),
        tones=tones,
        title="ITEM: Thoughts while designing a Gamelan",
        function=f,
    )


def xen07_harrison_thoughts_7(f):
    steps = [F(5, 4), F(16, 15), F(9, 8), F(81, 64), F(256, 243)]
    tones = [T.from_fraction(x) for x in cprod(steps)]
    assert len(tones) == 5
    return build_scl(
        description="Slendro with steps " + ", ".join(str(x) for x in steps),
        tones=tones,
        title="ITEM: Thoughts while designing a Gamelan",
        function=f,
    )


def xen07_harrison_thoughts_8(f):
    partials = [6, 7, 8, 9, 11]
    tones = [T.from_fraction(reduce(F(x, partials[0]))) for x in partials]
    assert len(tones) == 5
    return build_scl(
        description="Partials " + "/".join(str(x) for x in partials),
        tones=tones,
        title="ITEM: Thoughts while designing a Gamelan",
        function=f,
    )


def xen07_rosenthal_four_duets_1(f):
    tones = [
        T(6, 5),
        T(5, 4),
        T(4, 3),
        T(3, 2),
        T(9, 5),
        T(15, 8),
        T(2, 1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Scale for part I of 'Four duets for bowed psaltery and harp'",
        tones=tones,
        title="Four duets for bowed psaltery and harp",
        function=f,
    )


def xen07_rosenthal_four_duets_2(f):
    tones = [
        T(9, 8),
        T(5, 4),
        T(4, 3),
        T(45, 32),
        T(3, 2),
        T(5, 3),
        T(15, 8),
        T(2, 1),
    ]
    assert len(tones) == 8
    return build_scl(
        description="Scale for part II of 'Four duets for bowed psaltery and harp'",
        tones=tones,
        title="Four duets for bowed psaltery and harp",
        function=f,
    )


def xen07_rosenthal_four_duets_3(f):
    tones = [
        T(6, 5),
        T(5, 4),
        T(45, 32),
        T(3, 2),
        T(9, 5),
        T(15, 8),
        T(2, 1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Scale for parts III and IV of 'Four duets for bowed psaltery and harp'",
        tones=tones,
        title="Four duets for bowed psaltery and harp",
        function=f,
    )


def xen07_rosenthal_helix(f):
    tones = [
        T(9, 8),
        T(7, 6),
        T(5, 4),
        T(4, 3),
        T(11, 8),
        T(3, 2),
        T(5, 3),
        T(7, 4),
        T(11, 6),
        T(2, 1),
    ]
    assert len(tones) == 10
    return build_scl(
        description="Scale for 'Helix Song'",
        tones=tones,
        title="Helix Song",
        function=f,
    )


def xen07_london_didymus(f):
    steps = [
        F(25, 24),
        F(6, 5),
        F(16, 15),
        F(9, 8),
        F(25, 24),  # printed as 24/25
        F(6, 5),
        F(16, 15),
    ]
    tones = [T.from_fraction(x) for x in cprod(steps)]
    assert len(tones) == 7
    return build_scl(
        description="Scale for 'Solo in Didymus's Chromatic'",
        tones=tones,
        title="Four Pieces in Didymus' Chromatic",
        function=f,
    )


def xen07_chalmers_fokker_h(f):
    tones = [
        T(25, 24),
        T(16, 15),
        T(10, 9),
        T(75, 64),
        T(6, 5),
        T(5, 4),
        T(32, 25),
        T(4, 3),
        T(25, 18),
        T(36, 25),
        T(3, 2),
        T(25, 16),
        T(8, 5),
        T(5, 3),
        T(128, 75),
        T(9, 5),
        T(15, 8),
        T(48, 25),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Fokker-H",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_fokker_k(f):
    tones = [
        T(25, 24),
        T(27, 25),
        T(10, 9),
        T(125, 108),
        T(6, 5),
        T(5, 4),
        T(162, 125),
        T(4, 3),
        T(25, 18),
        T(36, 25),
        T(3, 2),
        T(125, 81),
        T(8, 5),
        T(5, 3),
        T(216, 125),
        T(9, 5),
        T(50, 27),
        T(48, 25),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Fokker-K",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_fokker_l(f):
    tones = [
        T(28, 27),
        T(175, 162),
        T(125, 112),
        T(144, 125),
        T(6, 5),
        T(56, 45),
        T(35, 27),
        T(75, 56),
        T(25, 18),
        T(36, 25),
        T(112, 75),
        T(54, 35),
        T(45, 28),
        T(5, 3),
        T(125, 72),
        T(224, 125),
        T(324, 175),
        T(27, 14),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Fokker-L",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_fokker(f):
    tones = [
        T(25, 24),
        T(16, 15),
        T(9, 8),
        T(75, 64),
        T(6, 5),
        T(5, 4),
        T(32, 25),
        T(4, 3),
        T(45, 32),
        T(36, 25),
        T(3, 2),
        T(25, 16),
        T(8, 5),
        T(5, 3),
        T(128, 75),
        T(9, 5),
        T(15, 8),
        T(48, 25),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Fokker",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


# Duplicates xen05-wilson-scott.scl
#
# def xen07_chalmers_wilson_1(f):
#     tones = [
#         T(25, 24),
#         T(16, 15),
#         T(9, 8),
#         T(75, 64),
#         T(6, 5),
#         T(5, 4),
#         T(32, 25),
#         T(4, 3),
#         T(45, 32),
#         T(36, 25),
#         T(3, 2),
#         T(25, 16),
#         T(8, 5),
#         T(5, 3),
#         T(225, 128),
#         T(9, 5),
#         T(15, 8),
#         T(48, 25),
#         T(2, 1),
#     ]
#     assert len(tones) == 19
#     return build_scl(
#         description="Wilson-1",
#         tones=tones,
#         title="A Collection of Scales With Nineteen Tones",
#         function=f,
#     )

# Duplicates xen03-wilson-negative-19.scl
#
# def xen07_chalmers_wilson_2(f):
#     tones = [
#         T(28, 27),
#         T(16, 15),
#         T(9, 8),
#         T(7, 6),
#         T(6, 5),
#         T(5, 4),
#         T(35, 27),
#         T(4, 3),
#         T(112, 81),
#         T(64, 45),
#         T(3, 2),
#         T(14, 9),
#         T(8, 5),
#         T(27, 16),
#         T(7, 4),
#         T(9, 5),
#         T(15, 8),
#         T(35, 18),
#         T(2, 1),
#     ]
#     assert len(tones) == 19
#     return build_scl(
#         description="Wilson-2",
#         tones=tones,
#         title="A Collection of Scales With Nineteen Tones",
#         function=f,
#     )


def xen07_chalmers_ariel(f):
    tones = [
        T(25, 24),
        T(16, 15),
        T(10, 9),
        T(125, 108),
        T(6, 5),
        T(5, 4),
        T(32, 25),
        T(4, 3),
        T(25, 18),
        T(36, 25),
        T(3, 2),
        T(25, 16),
        T(8, 5),
        T(5, 3),
        T(216, 125),
        T(9, 5),
        T(15, 8),
        T(48, 25),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Ariel",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_opelt(f):
    tones = [
        T(25, 24),
        T(27, 25),
        T(9, 8),
        T(75, 64),
        T(6, 5),
        T(5, 4),
        T(32, 25),
        T(4, 3),
        T(25, 18),
        T(36, 25),
        T(3, 2),
        T(25, 16),
        T(8, 5),
        T(5, 3),
        T(125, 72),
        T(9, 5),
        T(15, 8),
        T(48, 25),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Opelt",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_wurschmidt_1(f):
    tones = [
        T(25, 24),
        T(16, 15),
        T(9, 8),
        T(75, 64),
        T(6, 5),
        T(5, 4),
        T(32, 25),
        T(4, 3),
        T(25, 18),
        T(36, 25),
        T(3, 2),
        T(25, 16),
        T(8, 5),
        T(5, 3),
        T(128, 75),
        T(16, 9),
        T(15, 8),
        T(48, 25),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Wurschmidt-1",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_wurschmidt_2(f):
    tones = [
        T(25, 24),
        T(27, 25),
        T(9, 8),
        T(75, 64),
        T(6, 5),
        T(5, 4),
        T(32, 25),
        T(4, 3),
        T(25, 18),
        T(36, 25),
        T(3, 2),
        T(25, 16),
        T(8, 5),
        T(5, 3),
        T(128, 75),
        T(16, 9),
        T(50, 27),
        T(48, 25),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Wurschmidt-2",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_mandelbaum_1(f):
    tones = [
        T(25, 24),
        T(27, 25),
        T(10, 9),
        T(125, 108),
        T(6, 5),
        T(5, 4),
        T(125, 96),
        T(4, 3),
        T(25, 18),
        T(36, 25),
        T(3, 2),
        T(125, 81),
        T(8, 5),
        T(5, 3),
        T(125, 72),
        T(9, 5),
        T(50, 27),
        T(48, 25),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Mandelbaum-1",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_mandelbaum_2(f):
    tones = [
        T(25, 24),
        T(15, 14),
        T(9, 8),
        T(7, 6),
        T(6, 5),
        T(5, 4),
        T(9, 7),
        T(4, 3),
        T(7, 5),
        T(36, 25),
        T(3, 2),
        T(14, 9),
        T(8, 5),
        T(5, 3),
        T(7, 4),
        T(9, 5),
        T(15, 8),
        T(27, 14),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Mandelbaum-2",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_perrett(f):
    tones = [
        T(21, 20),
        T(35, 32),
        T(9, 8),
        T(7, 6),
        T(6, 5),
        T(5, 4),
        T(21, 16),
        T(4, 3),
        T(7, 5),
        T(35, 24),
        T(3, 2),
        T(63, 40),
        T(8, 5),
        T(5, 3),
        T(7, 4),
        T(9, 5),
        T(15, 8),
        T(63, 32),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Perrett",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_chalmers(f):
    tones = [
        T(21, 20),
        T(16, 15),
        T(9, 8),
        T(7, 6),
        T(6, 5),
        T(5, 4),
        T(21, 16),
        T(4, 3),
        T(7, 5),
        T(35, 24),
        T(3, 2),
        T(63, 40),
        T(8, 5),
        T(5, 3),
        T(7, 4),
        T(9, 5),
        T(28, 15),
        T(63, 32),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Chalmers",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_19_31(f):
    tones = [
        T(25, 24, "Originally printed as 25/27"),
        T(16, 15),
        T(9, 8),
        T(7, 6),
        T(6, 5),
        T(5, 4),
        T(9, 7),
        T(4, 3),
        T(7, 5),
        T(10, 7),
        T(3, 2),
        T(14, 9),
        T(8, 5),
        T(5, 3),
        T(7, 4),
        T(16, 9),
        T(15, 8),
        T(27, 14),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="19-31",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


# Duplicates xen06-wilson-clavichord-19.scl
#
# def xen07_chalmers_wilson_3(f):
#     tones = [
#         T(28, 27),
#         T(35, 33),
#         T(49, 44),
#         T(7, 6),
#         T(105, 88),
#         T(56, 45),
#         T(14, 11),
#         T(4, 3),
#         T(7, 5),
#         T(63, 44),
#         T(3, 2),
#         T(14, 9),
#         T(35, 22),
#         T(147, 88),
#         T(7, 4),
#         T(315, 176),
#         T(28, 15),
#         T(21, 11),
#         T(2, 1),
#     ]
#     assert len(tones) == 19
#     return build_scl(
#         description="Wilson-3",
#         tones=tones,
#         title="A Collection of Scales With Nineteen Tones",
#         function=f,
#     )


def xen07_chalmers_partch(f):
    tones = [
        T(10, 9),
        T(9, 8),
        T(8, 7),
        T(7, 6),
        T(6, 5),
        T(5, 4),
        T(9, 7),
        T(4, 3),
        T(7, 5),
        T(10, 7),
        T(3, 2),
        T(14, 9),
        T(8, 5),
        T(5, 3),
        T(12, 7),
        T(7, 4),
        T(16, 9),
        T(9, 5),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Partch",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_19_equal(f):
    tones = [
        T(63.2),
        T(126.3),
        T(189.5),
        T(252.6),
        T(315.8),
        T(378.9),
        T(442.1),
        T(505.3),
        T(568.4),
        T(631.6),
        T(694.7),
        T(757.9),
        T(821.1),
        T(884.2),
        T(947.4),
        T(1010.5),
        T(1073.7),
        T(1136.8),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="19-Equal",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_kornerup(f):
    tones = [
        T(73.5),
        T(118.9),
        T(192.4),
        T(265.9),
        T(311.4),
        T(384.1),
        T(458.4),
        T(503.8),
        T(577.3),
        T(622.7),
        T(696.2),
        T(769.7),
        T(815.1),
        T(888.6),
        T(962.1),
        T(1007.6),
        T(1081.1),
        T(1154.6),
        T(1200.0, comment="Originally printed as 12.0"),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Kornerup",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_meantone(f):
    tones = [
        T(76.0),
        T(117.1),
        T(193.2),
        T(269.2),
        T(310.3),
        T(386.3),
        T(462.4),
        T(503.4),
        T(579.5),
        T(620.5),
        T(696.6),
        T(772.6),
        T(813.7),
        T(889.7),
        T(965.8),
        T(1006.8),
        T(1082.9),
        T(1158.9),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="19 of Meantone",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_19_31_equal(f):
    tones = [
        T(77.4),
        T(116.1),
        T(193.5),
        T(271.0),
        T(309.7),
        T(387.1),
        T(464.5),
        T(503.2),
        T(580.6),
        T(619.4),
        T(696.8),
        T(774.2),
        T(812.9),
        T(890.3),
        T(967.7),
        T(1006.5),
        T(1083.9),
        T(1161.3),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="19 of 31-Equal",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_fifth_comma(f):
    tones = [
        T(83.6),
        T(111.7),
        T(195.3),
        T(278.9),
        T(307.0),
        T(390.6),
        T(474.2),
        T(502.3, comment="Originally printed as 507.3"),
        T(585.9),
        T(614.1),
        T(697.7),
        T(781.2),
        T(809.4),
        T(893.0),
        T(976.5),
        T(1004.7),
        T(1088.3),
        T(1171.8),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="19 of 1/5 Comma",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_sixth_comma(f):
    tones = [
        T(88.6),
        T(108.1),
        T(196.7),
        T(285.3),
        T(304.9),
        T(393.5),
        T(482.1),
        T(501.6),
        T(590.2),
        T(609.8),
        T(698.4),
        T(787.0),
        T(806.5),
        T(895.1),
        T(983.7),
        T(1003.3),
        T(1091.9),
        T(1180.4),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="19 of 1/6 Comma",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_19_50_equal(f):
    tones = [
        T(72.0),
        T(120.0),
        T(192.0),
        T(264.0),
        T(312.0),
        T(384.0),
        T(456.0),
        T(504.0),
        T(576.0),
        T(624.0),
        T(696.0),
        T(768.0),
        T(816.0),
        T(888.0),
        T(960.0),
        T(1008.0),
        T(1080.0),
        T(1152.0),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="19 of 50 Equal",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_two_seventh_comma(f):
    tones = [
        T(70.7),
        T(120.9),
        T(191.6),
        T(262.3),
        T(312.6),
        T(383.2),
        T(453.9),
        T(504.2),
        T(574.9),
        T(625.1),
        T(695.8),
        T(766.5),
        T(816.8),
        T(887.4),
        T(958.1),
        T(1008.2),
        T(1079.1),
        T(1149.7, comment="Originally printed as 1148.7, see XH18 errata p.299"),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="19 of 2/7 Comma",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_two_ninth_comma(f):
    tones = [
        T(80.2),
        T(114.1),
        T(194.4),
        T(274.6),
        T(308.5),
        T(388.7),
        T(468.9),
        T(502.8),
        T(583.1),
        T(616.9),
        T(697.2),
        T(777.4),
        T(811.3),
        T(891.5),
        T(971.8),
        T(1005.6),
        T(1085.9),
        T(1166.1),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="19 of 2/9 Comma",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_lst(f):
    tones = [
        T(78.2),
        T(115.6),
        T(193.8),
        T(271.9),
        T(309.4),
        T(387.5),
        T(465.7, comment="Originally printed as 424.9, see XH18 errata p.299"),
        T(503.1),
        T(581.3, comment="Originally printed as 583.1, see XH18 errata p.299"),
        T(618.7),
        T(696.9),
        T(775.1),
        T(812.5),
        T(890.7, comment="Originally printed as 890.6, see XH18 errata p.299"),
        T(968.8),
        T(1006.2),
        T(1084.4),
        T(1162.6),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="3.5.7 LST",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_rvf_1(f):
    tones = [
        T(68.25),
        T(118.75),
        T(190.75),
        T(261.0),
        T(312.0),
        T(381.0),
        T(454.75),
        T(504.25),
        T(572.25),
        T(621.75),
        T(695.5),
        T(764.5),
        T(815.5),
        T(885.75),
        T(957.75),
        T(1008.25),
        T(1076.5),
        T(1152.0),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="RVF-1",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_rvf_2(f):
    tones = [
        T(72.9),
        T(109.8),
        T(191.8),
        T(269.6),
        T(307.7),
        T(382.4),
        T(468.7),
        T(503.2),
        T(575.5),
        T(610.0),
        T(696.2),
        T(770.9),
        T(809.1),
        T(886.8),
        T(968.8),
        T(1005.7),
        T(1078.6),
        T(1169.1),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="RVF-2",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_rvf_3(f):
    tones = [
        T(73.6),
        T(106.3, comment="Originally printed as 110.3, see XH18 errata p.299"),
        T(191.9),
        T(271.9),
        T(306.2, comment="Originally printed as 308.6, see XH18 errata p.299"),
        T(382.2),
        T(473.4),
        T(502.9, comment="Originally printed as 503.7, see XH18 errata p.299"),
        T(575.6),
        T(605.1, comment="Originally printed as 609.9, see XH18 errata p.299"),
        T(696.3),
        T(772.3),
        T(806.6, comment="Originally printed as 809.8, see XH18 errata p.299"),
        T(886.6),
        T(972.2),
        T(1004.9, comment="Originally printed as 1006.5, see XH18 errata p.299"),
        T(1078.5),
        T(1175.3),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="RVF-3",
        tones=tones,
        title="A Collection of Scales With Nineteen Tones",
        function=f,
    )


def xen07_chalmers_hanson_just(f):
    tones = [
        T(25, 24),
        T(27, 25),
        T(9, 8),
        T(125, 108),
        T(6, 5),
        T(5, 4),
        T(125, 96),
        T(4, 3),
        T(25, 18),
        T(36, 25),
        T(3, 2),
        T(25, 16),
        T(8, 5),
        T(5, 3),
        T(125, 72),
        T(9, 5),
        T(15, 8),
        T(48, 25),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Hanson-19",
        tones=tones,
        title="Some additional nineteen-tone scales",
        function=f,
    )


def xen07_chalmers_smith_just(f):
    tones = [
        T(21, 20),
        T(35, 32),
        T(9, 8),
        T(7, 6),
        T(6, 5),
        T(5, 4),
        T(21, 16),
        T(4, 3),
        T(7, 5),
        T(35, 24),
        T(3, 2),
        T(14, 9),
        T(8, 5),
        T(5, 3),
        T(7, 4),
        T(9, 5),
        T(28, 15),
        T(35, 18),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Smith-19",
        tones=tones,
        title="Some additional nineteen-tone scales",
        function=f,
    )


def xen07_chalmers_scalatron(f):
    tones = [
        T(25, 24),
        T(16, 15),
        T(9, 8),
        T(75, 64),
        T(6, 5),
        T(5, 4),
        T(125, 96),
        T(4, 3),
        T(45, 32),
        T(36, 25),
        T(3, 2),
        T(25, 16),
        T(8, 5),
        T(5, 3),
        T(225, 128),
        T(9, 5),
        T(15, 8),
        T(125, 64),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Scalatron-19",
        tones=tones,
        title="Some additional nineteen-tone scales",
        function=f,
    )


def xen07_chalmers_diaphonic_a(f):
    tones = [
        T(32, 31),
        T(16, 15),
        T(32, 29),
        T(8, 7),
        T(32, 27),
        T(16, 13),
        T(32, 25),
        T(4, 3),
        T(32, 23),
        T(16, 11),
        T(3, 2),
        T(48, 31),
        T(8, 5),
        T(48, 29),
        T(12, 7),
        T(16, 9),
        T(24, 13),
        T(48, 25),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Wilson's Diaphonic Cycles A",
        tones=tones,
        title="Some additional nineteen-tone scales",
        function=f,
    )


def xen07_chalmers_diaphonic_b(f):
    tones = [
        T(33, 32),
        T(33, 31),
        T(11, 10),
        T(33, 29),
        T(33, 28),
        T(11, 9),
        T(33, 26),
        T(33, 25),
        T(11, 8),
        T(44, 31),
        T(22, 15),
        T(44, 29),
        T(11, 7),
        T(44, 27),
        T(22, 13),
        T(44, 25),
        T(11, 6),
        T(44, 23),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Wilson's Diaphonic Cycles B",
        tones=tones,
        title="Some additional nineteen-tone scales",
        function=f,
    )


def xen07_chalmers_diaphonic_c(f):
    tones = [
        T(32, 31),
        T(16, 15),
        T(32, 29),
        T(8, 7),
        T(32, 27),
        T(16, 13),
        T(32, 25),
        T(4, 3),
        T(11, 8),
        T(44, 31),
        T(22, 15),
        T(44, 29),
        T(11, 7),
        T(44, 27),
        T(22, 13),
        T(44, 25),
        T(11, 6),
        T(44, 23),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Wilson's Diaphonic Cycles C",
        tones=tones,
        title="Some additional nineteen-tone scales",
        function=f,
    )


def xen07_chalmers_diaphonic_d(f):
    tones = [
        T(33, 32),
        T(33, 31),
        T(11, 10),
        T(33, 29),
        T(33, 28),
        T(11, 9),
        T(33, 26),
        T(33, 25),
        T(11, 8),
        T(33, 23),
        T(3, 2),
        T(48, 31),
        T(8, 5),
        T(48, 29, comment="Originally printed as 48/31"),
        T(12, 7),
        T(16, 9),
        T(24, 13),
        T(48, 25),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Wilson's Diaphonic Cycles D",
        tones=tones,
        title="Some additional nineteen-tone scales",
        function=f,
    )


def xen07_chalmers_hanson(f):
    tones = [
        T(67.9),
        T(135.8),
        T(203.8),
        T(249.1),
        T(317.0),
        T(384.9),
        T(452.8),
        T(498.1),
        T(566.0),
        T(634.0),
        T(701.9),
        T(769.8),
        T(815.1),
        T(883.0),
        T(950.9),
        T(1018.9),
        T(1086.8),
        T(1132.1),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Hanson-19",
        tones=tones,
        title="Some additional nineteen-tone scales",
        function=f,
    )


def xen07_chalmers_mercator(f):
    tones = [
        T(67.9),
        T(113.2),
        T(181.1),
        T(271.7),
        T(339.6),
        T(384.9),
        T(430.2),
        T(498.1),
        T(566.0),
        T(611.3),
        T(679.2),
        T(769.8),
        T(815.1),
        T(883.0),
        T(950.9),
        T(996.2),
        T(1086.8),
        T(1154.7),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Mercator",
        tones=tones,
        title="Some additional nineteen-tone scales",
        function=f,
    )


def xen07_chalmers_smith(f):
    tones = [
        T(84.3),
        T(154.9),
        T(203.9),
        T(266.7),
        T(315.7),
        T(386.3),
        T(470.6),
        T(498.0),
        T(582.4),
        T(652.9),
        T(702.0),
        T(764.7),
        T(813.7),
        T(884.3),
        T(968.6),
        T(1017.6),
        T(1080.4),
        T(1151.0),
        T(1200.0),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Smith-19",
        tones=tones,
        title="Some additional nineteen-tone scales",
        function=f,
    )


def tritriadic(a, b, c):
    M = F(b, a)
    D = F(c, a)
    subdominant = [2 / D, M / D, F(2, 1)]
    tonic = [F(1, 1), M, D]
    dominant = [D, D * M, D * D]
    tones = tuple(sorted({reduce(x) for x in subdominant + tonic + dominant}))
    assert len(tones) == 7
    return tones


TRITRIADIC_TONES = set()


def add_tritriadic(a, b, c):
    name = f"xen09_chalmers_tritriadic_{a}_{b}_{c}"

    tones = tritriadic(a, b, c)
    TRITRIADIC_TONES.add(tones)

    def build(f, tones=tones):
        return build_scl(
            description=f"Tritriadic scale built from {a}:{b}:{c}",
            tones=tones,
            title="Tritriadic Scales with Seven Tones",
            function=f,
        )

    globals()[name] = build


TRITRIADIC = [
    (4, 5, 6),
    (10, 12, 15),
    (6, 7, 9),
    (14, 18, 21),
    (18, 22, 27),
    (22, 27, 33),
    (22, 28, 33),
    (28, 33, 42),
    (26, 32, 39),
    (32, 39, 48),
    (10, 13, 15),
    (26, 30, 39),
    (22, 26, 33),
    (26, 33, 39),
    (14, 17, 21),
    (34, 42, 51),
    (38, 48, 47),
    (16, 19, 24),
    (64, 81, 96),
    (54, 64, 81),
    (26, 34, 39),
    (34, 39, 51),
    (16, 21, 24),
    (14, 16, 21),
    (8, 11, 12),
    (22, 24, 33),
    (12, 17, 18),
    (34, 36, 51),
    #
    (8, 9, 10),
    (9, 10, 11),
    (10, 11, 12),
    (13, 14, 16),
    (14, 15, 17),
    (14, 16, 17),
    (17, 19, 21),
    (22, 24, 27),
    (22, 25, 27),
    (9, 13, 10),
    (10, 15, 11),
    (11, 8, 6),
    (22, 33, 24),
    (24, 35, 26),
    (9, 7, 10),
    (11, 18, 15),
    (5, 9, 8),
    (11, 20, 18),
    (6, 10, 11),
    (8, 14, 13),
    (17, 15, 14),
    (17, 16, 14),
    (21, 19, 17),
    (27, 24, 22),
    (27, 25, 22),
    (10, 13, 18),
    (11, 15, 20),
    (6, 8, 11),
    (24, 33, 44),
    (26, 35, 48),
    (5, 7, 9),
    (15, 18, 22),
    #
    (1, 3, 5),
    (1, 3, 7),
    (1, 5, 7),
    (1, 5, 11),
    (1, 5, 13),
    (1, 7, 9),
    (1, 7, 11),
    (1, 11, 13),
    (3, 4, 5),
    (3, 7, 9),
    (3, 5, 7),
    (6, 7, 8),
    (12, 13, 18),
    (5, 6, 7),
    (10, 14, 15),
    (10, 11, 15),
    # (10, 13, 15),
    (7, 8, 11),
    (7, 9, 11),
    (7, 9, 13),
    (7, 10, 13),
    (7, 11, 13),
    (9, 11, 13),
    (11, 16, 20),
    (11, 14, 20),
    (11, 13, 15),
]

assert len(TRITRIADIC) == 85
assert len(set(TRITRIADIC)) == 85

for a, b, c in TRITRIADIC:
    add_tritriadic(a, b, c)


# Duplicated in xen12_wilson_13_eikosany
# def xen09_grady_eikosany(f):
#     ratios = [
#         reduce(F(x * y * z, 1 * 3 * 5))
#         for x, y, z in combinations([1, 3, 5, 7, 9, 11], 3)
#     ]
#     tones = [T.from_fraction(x) for x in ratios]
#     assert len(tones) == 20
#     return build_scl(
#         description="1-3-5-7-9-11 Eikosany",
#         tones=tones,
#         title="Combination-Product Set Patterns",
#         function=f,
#     )


def xen09_grady_dekany_a(f):
    labels = [
        3 * 5 * 11,
        1 * 3 * 5,
        3 * 5 * 7,
        1 * 5 * 7,
        5 * 7 * 9,
        1 * 7 * 9,
        7 * 9 * 11,
        1 * 9 * 11,
        3 * 9 * 11,
        1 * 3 * 11,
    ]
    ratios = [reduce(F(label, 1 * 3 * 5)) for label in labels]
    tones = [T.from_fraction(x) for x in ratios]
    assert len(tones) == 10
    return build_scl(
        description="Dekany A",
        tones=tones,
        title="Combination-Product Set Patterns",
        function=f,
    )


def xen09_grady_dekany_b(f):
    labels = [
        5 * 9 * 11,
        1 * 5 * 11,
        5 * 7 * 11,
        1 * 7 * 11,
        3 * 7 * 11,
        1 * 3 * 7,
        3 * 7 * 9,
        1 * 3 * 9,
        3 * 5 * 9,
        1 * 5 * 9,
    ]
    ratios = [reduce(F(label, 1 * 3 * 7)) for label in labels]
    tones = [T.from_fraction(x) for x in ratios]
    assert len(tones) == 10
    return build_scl(
        description="Dekany B",
        tones=tones,
        title="Combination-Product Set Patterns",
        function=f,
    )


def xen09_polansky_will_you_miss_me(f):
    tones = [
        T(3, 2),
        T(25, 16),
        T(13, 8),
        T(5, 3),
        T(27, 16),
        T(7, 4),
        T(15, 8),
        T(2, 1),
        T(65, 64),
        T(35, 32),
        T(9, 8),
        T(7, 6),
        T(6, 5),
        T(39, 32),
        T(5, 4),
        T(21, 16),
        T(4, 3),
    ]
    assert len(tones) == 17
    return build_scl(
        description="Scale for 'Will You Miss Me'",
        tones=tones,
        title="Will You Miss Me",
        function=f,
    )


def permute(fourths):
    assert len(fourths) == 7
    index = []
    for i, f in enumerate(fourths[:-1]):
        if f != F(4, 3):
            index.append(i)

    N = len(fourths) - 1
    M = len(index)

    permutations = []

    if M == 0:
        return [fourths]
    elif M == 1:
        for i in range(N):
            new = N * [F(4, 3)] + [fourths[-1]]
            new[i] = fourths[index[0]]
            permutations.append(new)
    elif M == 2:
        for i in range(N - 1):
            for j in range(i + index[1], N):
                new = N * [F(4, 3)] + [fourths[-1]]
                new[i] = fourths[index[0]]
                new[j] = fourths[index[1]]
                permutations.append(new)
    elif M == 3:
        for i in range(N - 2):
            for j in range(i + index[1], N - 1):
                for k in range(j + index[2] - index[1], N):
                    new = N * [F(4, 3)] + [fourths[-1]]
                    new[i] = fourths[index[0]]
                    new[j] = fourths[index[1]]
                    new[k] = fourths[index[2]]
                    permutations.append(new)
    else:
        raise ValueError(M)

    return permutations


def stack(fs):
    x = F(1)
    new_scale = []
    for f in fs:
        x = reduce(x * f)
        new_scale.append(x)
    return sorted(new_scale)


MARWA = {
    "2": ([F(729, 512)] + 6 * [F(4, 3)], "Pythagoras 256/243 9/8 9/8"),
    "3": ([F(45, 32), F(27, 20)] + 5 * [F(4, 3)], "Ptolemy 16/15 9/8 10/9"),
    "4": ([F(27, 20), F(45, 32)] + 5 * [F(4, 3)], "Didymus 16/15 10/9 9/8"),
    "5": (6 * [F(4, 3)] + [F(729, 512)], "Pythagoras 256/243 9/8 9/8"),
    "6": ([F(27, 20)] + 5 * [F(4, 3)] + [F(45, 32)], "Didymus/Ptolemy 16/15 9/8 10/9"),
    "7": ([F(21, 16), F(81, 56)] + 5 * [F(4, 3)], "Archytas 28/27 8/7 9/8"),
    "8": ([F(21, 16)] + 5 * [F(4, 3)] + [F(81, 56)], "Archytas 28/27 8/7 9/8"),
    "9": (
        [F(45, 32), F(81, 64), F(64, 45)] + 4 * [F(4, 3)],
        "Hawkins 16/15 135/128 32/27",
    ),
    "10": ([F(11, 8), F(9, 7), F(63, 44)] + 4 * [F(4, 3)], "Ptolemy 7/6 12/11 22/21"),
    "11a": (
        [F(64, 45), F(4, 3), F(45, 32), F(4, 3), F(4, 3), F(4, 3), F(81, 64)],
        "Hawkins 16/15 135/128 32/27",
    ),
    "11b": (
        [F(45, 32), F(4, 3), F(64, 45), F(4, 3), F(4, 3), F(4, 3), F(81, 64)],
        "Hawkins 135/128 16/15 32/27",
    ),
    "12": (
        [F(45, 32), F(4, 3), F(45, 32), F(4, 3), F(4, 3), F(4, 3), F(32, 25)],
        "Helmholtz 16/15 16/15 75/64",
    ),
    "13": (
        [F(27, 20), F(4, 3), F(27, 20), F(4, 3), F(4, 3), F(4, 3), F(25, 18)],
        "Al-Farabi 10/9 10/9 27/25",
    ),
    "14a": (
        [F(36, 25), F(4, 3), F(45, 32), F(4, 3), F(4, 3), F(4, 3), F(5, 4)],
        "Didymus 16/15 25/24 6/5",
    ),
    "14b": (
        [F(45, 32), F(4, 3), F(36, 25), F(4, 3), F(4, 3), F(4, 3), F(5, 4)],
        "Didymus 25/24 16/15 6/5",
    ),
    "15a": (
        [F(63, 44), F(4, 3), F(11, 8), F(4, 3), F(4, 3), F(4, 3), F(9, 7)],
        "Ptolemy 12/11 22/21 7/6",
    ),
    "15b": (
        [F(11, 8), F(4, 3), F(63, 44), F(4, 3), F(4, 3), F(4, 3), F(9, 7)],
        "Ptolemy 22/21 12/11 7/6",
    ),
    "16a": (
        [F(45, 32), F(4, 3), F(18, 13), F(4, 3), F(4, 3), F(4, 3), F(13, 10)],
        "Schlesinger 16/15 15/13 13/12",
    ),
    "16b": (
        [F(18, 13), F(4, 3), F(45, 32), F(4, 3), F(4, 3), F(4, 3), F(13, 10)],
        "Schlesinger 13/12 15/13 16/15",
    ),
    "17a": (
        [F(35, 24), F(4, 3), F(81, 56), F(4, 3), F(4, 3), F(4, 3), F(6, 5)],
        "Archytas 28/27 36/35 5/4",
    ),
    "17b": (
        [F(81, 56), F(4, 3), F(35, 24), F(4, 3), F(4, 3), F(4, 3), F(6, 5)],
        "Archytas 36/35 28/27 5/4",
    ),
    "18a": (
        [F(11, 8), F(4, 3), F(27, 20), F(4, 3), F(4, 3), F(4, 3), F(15, 11)],
        "Ptolemy 12/11 11/10 10/9",
    ),
    "18b": (
        [F(27, 20), F(4, 3), F(11, 8), F(4, 3), F(4, 3), F(4, 3), F(15, 11)],
        "Ptolemy 10/9 11/10 12/11",
    ),
}


def pad_label(s):
    m = re.search(r"(\d*)(.*)", s)
    number = int(m.group(1))
    label = m.group(2)
    return f"{number:02}{label}"


def add_marwa_permutations(label, fourths, description):
    permutations = permute(fourths)
    for i, fs in enumerate(permutations, 1):
        name = f"xen09_wilson_marwa_{pad_label(label)}_{i:02}"

        def build(f, i=i, fs=fs):
            tones = [T.from_fraction(x) for x in stack(fs)]
            return build_scl(
                description=f"Marwa permutation {i} from Figure {label}, {description}",
                tones=tones,
                title="The Marwa Permutations",
                function=f,
            )

        globals()[name] = build


for label, (fourths, description) in MARWA.items():
    add_marwa_permutations(label, fourths, description)


def add_tritriadic_2(a, b, c):
    name = f"xen10_chalmers_tritriadic_{a}_{b}_{c}"

    tones = tritriadic(a, b, c)
    if tones in TRITRIADIC_TONES:
        return
    TRITRIADIC_TONES.add(tones)

    def build(f):
        return build_scl(
            description=f"Tritriadic scale built from {a}:{b}:{c}",
            tones=tones,
            title="Tritriadic Scales with Seven Tones, Part Two: Derived Forms and Structural Properties",
            function=f,
        )

    globals()[name] = build


TRITRIADIC_2 = [
    (1, 5, 3),
    (3, 1, 11),
    (1, 9, 5),
    (1, 7, 13),
    (7, 1, 17),
    (3, 11, 15),
    (7, 3, 19),
    (5, 7, 9),
    (9, 5, 11),
    (5, 13, 9),
    (5, 15, 11),
    (7, 15, 17),
    (11, 9, 15),
    (17, 13, 19),
    (5, 1, 27),
    (21, 1, 23),
    (11, 3, 27),
    (5, 27, 9),
    (17, 5, 25),
    (5, 17, 27),
    #
    (7, 9, 25),
    # (7, 13, 13),  # 13 repeated?
    (7, 17, 21),
    (17, 7, 23),
    (19, 7, 21),
    (7, 23, 19),
    (7, 19, 25),
    (7, 25, 23),
    (9, 11, 27),
    (11, 25, 27),
    (13, 23, 21),
    (21, 15, 23),
    (15, 27, 25),
    (17, 19, 21),
    (17, 25, 19),
    (17, 21, 25),
    (23, 17, 25),
    (19, 21, 23),
    (19, 27, 21),
    (26, 32, 39),
    (24, 35, 26),
]

assert len(TRITRIADIC_2) == 40
assert len(set(TRITRIADIC_2)) == 40

assert len(set(TRITRIADIC_2) - set(TRITRIADIC)) == 36

for a, b, c in TRITRIADIC_2:
    add_tritriadic_2(a, b, c)


A = F(4, 3)
PURVI = {
    "1": (6 * [A] + [F(729, 512)], "Pythagoras (9/8 9/8 256/243) all 3 permutations"),
    "2a": (
        [A, A, F(45, 32), A, F(45, 32), A, F(32, 25)],
        "Helmholtz (75/64 16/15 16/15), (16/15 16/15 75/64)",
    ),
    "2b": (
        [A, F(45, 64), A, A, F(45, 64), A, F(32, 25)],
        "Helmholtz (16/15 75/64 16/15)",
    ),
    "3a": (
        [A, F(21, 16), A, F(21, 16), A, A, F(72, 49)],
        "Al-Farabi (8/7 8/7 49/48), (49/48 8/7 8/7)",
    ),
    "3b": ([A, F(21, 16), A, A, F(21, 16), A, F(72, 49)], "Al-Farabi (8/7 49/48 8/7)"),
    "4": (
        [A, A, A, F(21, 16), A, A, F(81, 56)],
        "Archytas (8/7 9/8 28/27) all 6 permutations",
    ),
    "5": (
        [A, A, A, F(27, 20), A, A, F(45, 32)],
        "Didymus/Ptolemy (10/9 9/8 16/15) all 6 permutations",
    ),
    "6a": (
        [A, F(27, 20), A, F(27, 20), A, A, F(25, 18)],
        "Al-Farabi (10/9 10/9 27/25), (27/25 10/9 10/9)",
    ),
    "6b": (
        [A, F(27, 20), A, A, F(27, 20), A, F(25, 18)],
        "Al-Farabi (10/9 27/25 10/9)",
    ),
    "7a": (
        [A, F(45, 32), A, F(18, 13), A, A, F(13, 10)],
        "Kathleen Schlesinger (13/12 16/15 15/13), (15/13 13/12 16/15)",
    ),
    "7b": (
        [A, A, F(18, 13), A, F(45, 32), A, F(13, 10)],
        "Kathleen Schlesinger (15/13 16/15 13/12), (16/15 13/12 15/13)",
    ),
    "7c": (
        [A, F(45, 32), A, A, F(18, 13), A, F(13, 10)],
        "Kathleen Schlesinger (16/15 15/13 13/12), (13/12 15/13 16/15)",
    ),
    "8a": (
        [A, F(63, 44), A, F(11, 8), A, A, F(9, 7)],
        "Ptolemy (12/11 22/21 7/6), (7/6 12/11 22/21)",
    ),
    "8b": (
        [A, A, F(11, 8), A, F(63, 44), A, F(9, 7)],
        "Ptolemy (7/6 22/21 12/11), (22/21 12/11 7/6)",
    ),
    "8c": (
        [A, F(63, 44), A, A, F(11, 8), A, F(9, 7)],
        "Ptolemy (22/21 7/6 12/11), (12/11 7/6 22/21)",
    ),
    "9a": (
        [A, F(45, 32), A, F(64, 45), A, A, F(81, 64)],
        "Hawkins (135/128 16/15 32/27), (32/27 135/128 16/15)",
    ),
    "9b": (
        [A, A, F(64, 45), A, F(45, 32), A, F(81, 64)],
        "Hawkins (32/27 16/15 135/128), (16/15 135/128 32/27)",
    ),
    "9c": (
        [A, F(64, 45), A, A, F(45, 32), A, F(81, 64)],
        "Hawkins (135/128 32/27 16/15) (16/15 32/27 135/128)",
    ),
    "10a": (
        [A, F(36, 25), A, F(45, 32), A, A, F(5, 4)],
        "Didymus (16/15 25/24 6/5), (6/5 16/15 25/24)",
    ),
    "10b": (
        [A, A, F(45, 32), A, F(36, 25), A, F(5, 4)],
        "Didymus (6/5 25/24 16/15), (25/24 16/15 6/5)",
    ),
    "10c": (
        [A, F(36, 25), A, A, F(45, 32), A, F(5, 4)],
        "Didymus (25/24 6/5 16/15), (16/15 6/5 25/24)",
    ),
    "11a": (
        [A, F(35, 24), A, F(81, 56), A, A, F(6, 5)],
        "Archytas (28/27 36/35 5/4), (5/4 28/27 36/35)",
    ),
    "11b": (
        [A, A, F(81, 56), A, F(35, 24), A, F(6, 5)],
        "Archytas (5/4 36/35 28/27), (36/35 28/27 5/4)",
    ),
    "11c": (
        [A, F(81, 56), A, A, F(35, 24), A, F(6, 5)],
        "Archytas (28/27 5/4 36/35), (36/35 5/4 28/27)",
    ),
}
del A


def modulate(fourths):
    assert len(fourths) == 7
    modulations = [fourths[i:-1] + fourths[:i] + [fourths[-1]] for i in range(7)]
    return modulations


def rotate(scale, n):
    n = n % len(scale)
    period = scale[-1]
    new_scale = [F(1)] + scale
    new_scale = new_scale[n:-1] + [period * x for x in new_scale[:n]]
    new_scale = [x / new_scale[0] for x in new_scale[1:]] + [period]
    assert len(new_scale) == len(scale)
    return new_scale


def add_purvi_modulations(label, fourths, description):
    modulations = modulate(fourths)
    for i, fs in enumerate(modulations, 1):
        name = f"xen10_wilson_purvi_{pad_label(label)}_{i:02}"

        def build(f, i=i, fs=fs, description=description):
            tones = [
                T.from_fraction(x) for x in rotate(stack(fs), (4 - 3 * (i - 1)) % 7)
            ]
            return build_scl(
                description=f"Purvi modulation {i} from Figure {label}, {description}",
                tones=tones,
                title="The Purvi Modulations",
                function=f,
            )

        globals()[name] = build


for name, (fourths, description) in PURVI.items():
    add_purvi_modulations(name, fourths, description)


def xen10_wolf_sands(f):
    tones = [
        T(21, 20),
        T(28, 25),
        T(6, 5),
        T(32, 25),
        T(21, 16),
        T(7, 5),
        T(3, 2),
        T(8, 5),
        T(42, 25),
        T(7, 4),
        T(48, 25),
        T(2, 1),
    ]
    assert len(tones) == 12
    return build_scl(
        description="Scale from 'Trio: The Sands'",
        tones=tones,
        title="Trio: The Sands",
        function=f,
    )


def xen11_chalmers_tetrachordal_04_01(f):
    tones = [
        T(28, 27),
        T(32, 27),
        T(4, 3),
        T(3, 2),
        T(14, 9),
        T(16, 9),
        T(2, 1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Sterea, a Lyra tuning: Tonic Diatonic",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_04_02a(f):
    tones = [
        T(28, 27),
        T(10, 9),
        T(4, 3),
        T(3, 2),
        T(14, 9),
        T(16, 9),
        T(2, 1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Malaka, a Lyra tuning: Soft or Intense Chromatic and Tonic Diatonic",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_04_02b(f):
    tones = [
        T(22, 21),
        T(8, 7),
        T(4, 3),
        T(3, 2),
        T(14, 9),
        T(16, 9),
        T(2, 1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Malaka, a Lyra tuning: Soft or Intense Chromatic and Tonic Diatonic",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_04_03(f):
    tones = [
        T(21, 20),
        T(7, 6),
        T(4, 3),
        T(3, 2),
        T(14, 9),
        T(16, 9),
        T(2, 1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Metabolika, another Lyra tuning: Soft Diatonic and Tonic Diatonic",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_04_04(f):
    tones = [
        T(28, 27),
        T(32, 27),
        T(4, 3),
        T(3, 2),
        T(27, 16),
        T(16, 9),
        T(2, 1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Iasti-Aiolikai, a Kithara tuning: Tonic Diatonic and Ditonic Diatonic",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_04_05(f):
    tones = [
        T(28, 27),
        T(32, 27),
        T(4, 3),
        T(3, 2),
        T(8, 5),
        T(9, 5),
        T(2, 1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Iastia or Lydia, Kithara tunings: Intense Diatonic and Tonic Diatonic",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_06_01(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(784, 729, cents=126),
        T(448, 405, cents=175),
        T(4, 3, cents=498),
        T(112, 81, cents=561),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition by A",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_06_02(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(448, 405, cents=175),
        T(256, 225, cents=223),
        T(4, 3, cents=498),
        T(64, 45, cents=610, comment="Originally printed as 64/32"),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition by B",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_06_03(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(4, 3, cents=498),
        T(112, 81, cents=561),
        T(64, 45, cents=610),
        T(16, 9, cents=996),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition by 4/3, Mixolydian Mode",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_06_04(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(4, 3, cents=498),
        T(3, 2, cents=702),
        T(14, 9, cents=765),
        T(8, 5, cents=814),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition by 3/2, Dorian Mode",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_06_05(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(5, 4, cents=386),
        T(4, 3, cents=498),
        T(15, 8, cents=1088),
        T(35, 18, cents=1151),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition by 2/B",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_06_06(f):
    tones = [
        T(36, 35, cents=49),
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(9, 7, cents=435),
        T(4, 3, cents=498),
        T(27, 14, cents=1137),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition by 2/A",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_06_07(f):
    tones = [
        T(9, 8, cents=204),
        T(7, 6, cents=267),
        T(6, 5, cents=316),
        T(3, 2, cents=702),
        T(14, 9, cents=765),
        T(8, 5, cents=814),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition by 9/8 & 3/2, Hypodorian Mode",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_06_08(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(5, 4, cents=386),
        T(35, 27, cents=449),
        T(4, 3, cents=498),
        T(5, 3, cents=884),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition by 4/3B",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_06_09(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(9, 7, cents=435),
        T(4, 3, cents=498),
        T(48, 35, cents=547),
        T(12, 7, cents=933),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition by 4/3A",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_06_10(f):
    tones = [
        T(245, 243, cents=14),
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(35, 27, cents=449),
        T(4, 3, cents=498),
        T(35, 18, cents=1151),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition by A/B",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_06_11(f):
    tones = [
        T(36, 35, cents=49),
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(192, 175, cents=161),
        T(4, 3, cents=498),
        T(48, 35, cents=547),  # cents printed as 561
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition by B/A",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_01(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(35, 27, cents=449),
        T(4, 3, cents=498),
        T(112, 81, cents=561),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 6
    return build_scl(
        description="Transposition and Inversion by A, 6 tones, a Hexany",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_02(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(4, 3, cents=498),
        T(48, 35, cents=547),
        T(64, 45, cents=610),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 6
    return build_scl(
        description="Transposition and Inversion by B, 6 tones, a Hexany",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_03(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(4, 3, cents=498),
        T(5, 3, cents=884),
        T(12, 7, cents=933),
        T(16, 9, cents=996),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition and Inversion by 4/3, 7 tones, Psi-Mixolydian",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_04(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(4, 3, cents=498),
        T(3, 2, cents=702),
        T(15, 8, cents=1088),
        T(27, 14, cents=1137),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition and Inversion by 3/2, 7 tones, Psi-Dorian",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_05(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(75, 64, cents=275),
        T(135, 112, cents=323),
        T(5, 4, cents=386),
        T(4, 3, cents=498),
        T(15, 8, cents=1088),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 8
    return build_scl(
        description="Transposition and Inversion by 2/B, 8 tones, an Octony",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_06(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(135, 112, cents=323),
        T(243, 196, cents=372),
        T(9, 7, cents=435),
        T(4, 3, cents=498),
        T(27, 14, cents=1137),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 8
    return build_scl(
        description="Transposition and Inversion by 2/A, 8 tones, an Octony",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_07(f):
    tones = [
        T(9, 8, cents=204),
        T(45, 32, cents=590),
        T(81, 56, cents=639),
        T(3, 2, cents=702),
        T(14, 9, cents=765),
        T(8, 5, cents=814),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition and Inversion by 9/8 & 3/2, 7 tones, Psi-Hypodorian 1",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_08(f):
    tones = [
        T(9, 8, cents=204),
        T(7, 6, cents=267),
        T(6, 5, cents=316),
        T(3, 2, cents=702),
        T(15, 8, cents=1088),
        T(27, 14, cents=1137),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition and Inversion by 9/8 & 3/2, 7 tones, Psi-Hypodorian 2",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_09(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(5, 4, cents=386),
        T(9, 7, cents=435),
        T(4, 3, cents=498),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 6
    return build_scl(
        description="Transposition and Inversion by 1/1, 6 tones, a Hexany",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_10(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(5, 4, cents=386),
        T(4, 3, cents=498),
        T(25, 16, cents=773),
        T(45, 28, cents=821),
        T(5, 3, cents=884),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 8
    return build_scl(
        description="Transposition and Inversion by 4/3B, 8 tones, an Octony",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_11(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(9, 7, cents=435),
        T(4, 3, cents=498),
        T(45, 28, cents=821),
        T(81, 49, cents=870),
        T(12, 7, cents=933),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 8
    return build_scl(
        description="Transposition and Inversion by 4/3A, 8 tones, an Octony",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_12(f):
    tones = [
        T(36, 35, cents=49),
        T(16, 15, cents=112),
        T(9, 7, cents=435),
        T(4, 3, cents=498),
        T(48, 35, cents=547),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 6
    return build_scl(
        description="Tetrachordal Hexany, 6 tones, A-Mode",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_13(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(448, 405, cents=175),
        T(4, 3, cents=498),
        T(112, 81, cents=561),
        T(64, 45, cents=610),
        T(1792, 1215, cents=673),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 8
    return build_scl(
        description="Euler's Genus Musicum, 8 tones, an Octony",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_14(f):
    tones = [
        T(36, 35, cents=49),
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(9, 7, cents=435),
        T(324, 245, cents=484),
        T(4, 3, cents=498),
        T(48, 35, cents=547),  # cents printed as 561
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 8
    return build_scl(
        description="Transposition and Inversion by B/A, 8 tones, an Octony",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_08_15(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(175, 144, cents=338),
        T(5, 4, cents=386),
        T(35, 27, cents=449),
        T(4, 3, cents=498),
        T(35, 18, cents=1151),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 8
    return build_scl(
        description="Transposition and Inversion by A/B, 8 tones, an Octony",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_10_01(f):
    tones = [
        T(36, 35, cents=49),
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(5, 4, cents=386),
        T(9, 7, cents=435),
        T(4, 3, cents=498),
        T(3, 2, cents=702),
        T(14, 9, cents=765),
        T(8, 5, cents=814),
        T(15, 8, cents=1088),
        T(27, 14, cents=1137),
        T(35, 18, cents=1151),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 13
    return build_scl(
        description="Thirteen Tone Octave Modular Diamond",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_10_02(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(5, 4, cents=386),
        T(9, 7, cents=435),
        T(35, 27, cents=449),
        T(4, 3, cents=498),
        T(48, 35, cents=547),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 8
    return build_scl(
        description="Eight Tone Fourth Modular Diamond",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_10_03(f):
    tones = [
        T(36, 35, cents=49),
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(9, 8, cents=204),
        T(7, 6, cents=267),
        T(6, 5, cents=316),
        T(5, 4, cents=386),
        T(9, 7, cents=435),
        T(35, 27, cents=449),
        T(4, 3, cents=498),
        T(48, 35, cents=547),
        T(112, 81, cents=561),
        T(45, 32, cents=590),
        T(64, 45, cents=610),
        T(81, 56, cents=639),
        T(35, 24, cents=653),
        T(3, 2, cents=702),
        T(54, 35, cents=751),
        T(14, 9, cents=765),
        T(8, 5, cents=814),
        T(5, 3, cents=884),
        T(12, 7, cents=933),
        T(16, 9, cents=996),
        T(15, 8, cents=1088),
        T(27, 14, cents=1137),
        T(35, 18, cents=1151),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 27
    return build_scl(
        description="Prime-Prime and Inverted-Inverted Heptatonic Diamonds, 27 Tones",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_10_04(f):
    tones = [
        T(36, 35, cents=49),
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(784, 729, cents=126),
        T(448, 405, cents=175),
        T(9, 8, cents=204),
        T(256, 225, cents=223),
        T(5, 4, cents=386),
        T(9, 7, cents=435),
        T(4, 3, cents=498),
        T(112, 81, cents=561),
        T(45, 32, cents=590),
        T(64, 45, cents=610),
        T(81, 56, cents=639),
        T(3, 2, cents=702),
        T(14, 9, cents=765),
        T(8, 5, cents=814),
        T(225, 128, cents=977),
        T(16, 9, cents=996),
        T(405, 224, cents=1025),
        T(729, 392, cents=1074),
        T(15, 8, cents=1088),
        T(27, 14, cents=1137),
        T(35, 18, cents=1151),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 25
    return build_scl(
        description="Prime-Inverted Heptatonic Diamond, 25 Tones",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_10_05(f):
    tones = [
        T(36, 35, cents=49),
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(9, 8, cents=204),
        T(7, 6, cents=267),
        T(6, 5, cents=316),
        T(98, 81, cents=330),
        T(56, 45, cents=379),
        T(5, 4, cents=386),
        T(32, 25, cents=427),
        T(9, 7, cents=435),
        T(4, 3, cents=498),
        T(3, 2, cents=702),
        T(14, 9, cents=765),
        T(25, 16, cents=773),
        T(8, 5, cents=814),
        T(45, 28, cents=821),
        T(81, 49, cents=870),
        T(5, 3, cents=884),
        T(12, 7, cents=933),
        T(16, 9, cents=996),
        T(15, 8, cents=1088),
        T(27, 14, cents=1137),
        T(35, 18, cents=1151),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 25
    return build_scl(
        description="Inverted-Prime Heptatonic Diamond, 25 Tones",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_10_06(f):
    tones = [
        T(28, 27, cents=63),
        T(16, 15, cents=112),
        T(784, 729, cents=126),
        T(448, 405, cents=175),
        T(256, 225, cents=223),
        T(35, 27, cents=449),
        T(4, 3, cents=498),
        T(48, 35, cents=547),
        T(112, 81, cents=561),
        T(64, 45, cents=610),
        T(1792, 1215, cents=673),
        T(224, 135, cents=877),
        T(16, 9, cents=996),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 14
    return build_scl(
        description="Stellated Tetrachordal Hexany, 14 Tones",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_chalmers_tetrachordal_10_07(f):
    tones = [
        T(36, 35, cents=49),
        T(1296, 1225, cents=98),
        T(16, 15, cents=112),
        T(192, 175, cents=161),
        T(256, 225, cents=223),
        T(9, 7, cents=435),
        T(4, 3, cents=498),
        T(48, 35, cents=547),
        T(112, 81, cents=561),
        T(64, 45, cents=610),
        T(256, 175, cents=659),
        T(288, 175, cents=862),
        T(16, 9, cents=996),
        T(2, 1, cents=1200),
    ]
    assert len(tones) == 14
    return build_scl(
        description="Stellated Hexany, Entry #1 of Table 7., 14 tones, Permuted Tetrachord",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_wolf_pelog(f):
    tones = [
        T(134.5),
        T(266.9),
        T(533.8),
        T(666.0),
        T(800.7),
        T(932.9),
        T(1202.1, period=1202.1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Pelog based on stacking 7/6",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_wolf_pelog_2(f):
    tones = [
        T(128.3),
        T(266.9),
        T(533.8),
        T(666.0),
        T(794.5),
        T(932.9),
        T(1202.1, period=1202.1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Pelog based on stacking 7/6, pitches 2 and 6 lowered",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_wolf_pelog_extended(f):
    tones = [
        T(134.5),
        T(266.9),
        T(401.4),
        T(533.8),
        T(666.0),
        T(800.7),
        T(932.9),
        T(1067.6),
        T(1202.1, period=1202.1),
    ]
    assert len(tones) == 9
    return build_scl(
        description="Pelog based on stacking 7/6, extended to 9 tones",
        tones=tones,
        title="Tetrachordal Scales and Complexes",
        function=f,
    )


def xen11_garcia_linear_29(f):
    tones = [
        T(40, 39),
        T(27, 26),
        T(16, 15),
        T(128, 117),
        T(9, 8),
        T(15, 13),
        T(32, 27),
        T(6, 5),
        T(16, 13),
        T(81, 64),
        T(135, 104),
        T(4, 3),
        T(160, 117),
        T(18, 13),
        T(64, 45),
        T(512, 351),
        T(3, 2),
        T(20, 13),
        T(81, 52),
        T(8, 5),
        T(64, 39),
        T(27, 16),
        T(45, 26),
        T(16, 9),
        T(9, 5),
        T(24, 13),
        T(256, 135),
        T(405, 208),
        T(2, 1),
    ]
    assert len(tones) == 29
    return build_scl(
        description="Linear series of alternating 15/13 and 52/45",
        tones=tones,
        title="A Linear Twenty-Nine Tone Scale",
        function=f,
    )


def xen11_wilsonsmithgrady_marimba(f):
    labels = [
        F(1 * 9 * 11),
        F(3),
        F(3 * 7 * 9),
        #
        F(1 * 7 * 11, 3),
        F(3 * 3 * 5 * 9),
        #
        F(1 * 5 * 11),
        F(1 * 3 * 9),
        F(3 * 5 * 7),
        #
        F(3 * 7 * 11),
        F(7),
        #
        F(5 * 9 * 11),
        F(1 * 3 * 5),
        F(1 * 3 * 5 * 7 * 9),
        #
        F(1 * 3 * 11),
        F(1),
        F(1 * 7 * 9),
        #
        F(1 * 7 * 11, 9),
        F(3 * 5 * 9),
        #
        F(3 * 9 * 11),
        F(9),
        F(1 * 5 * 7),
        #
        F(1 * 7 * 11),
        F(9 * 3 * 5 * 9),
        #
        F(3 * 5 * 11),
        F(5),
        F(5 * 7 * 9),
        #
        F(11),
        F(7 * 9 * 11),
        F(1 * 3 * 7),
        #
        F(1 * 3 * 5 * 9 * 11),
        F(1 * 5 * 9),
        #
        F(1 * 9 * 11),
        F(5 * 7 * 11),
        F(3),
        F(3 * 7 * 9),
        #
        F(1 * 7 * 11, 3),
        F(3 * 3 * 5 * 9),
        #
        F(1 * 5 * 11),
        F(1 * 5 * 7 * 9 * 11),
        F(1 * 3 * 9),
        F(3 * 5 * 7),
        #
        F(3 * 7 * 11),
        F(7),
        #
        F(5 * 9 * 11),
        F(1 * 3 * 5),
        F(1 * 3 * 5 * 7 * 9),
        #
        F(1 * 3 * 11),
        F(1 * 3 * 7 * 9 * 11),
        F(1 * 7 * 9),
        #
        F(1 * 7 * 11, 9),
        F(3 * 5 * 9),
        #
        F(3 * 9 * 11),
        F(1 * 3 * 5 * 7 * 11),
        F(1 * 5 * 7),
        #
        F(1 * 7 * 11),
        F(9 * 3 * 5 * 9),
        #
        F(3 * 5 * 11),
        F(3 * 5 * 7 * 9 * 11),
        F(5 * 7 * 9),
        #
        F(11),
        F(7 * 9 * 11),
        F(1 * 3 * 7),
        #
        F(1 * 3 * 5 * 9 * 11),
        F(1 * 5 * 9),
        #
        F(1 * 9 * 11),
        F(5 * 7 * 11),
        F(3 * 7 * 9),
        #
        F(1 * 7 * 11, 3),
        F(3 * 3 * 5 * 9),
        #
        F(1 * 5 * 11),
        F(1 * 5 * 7 * 9 * 11),
        F(3 * 5 * 7),
    ]
    tones = [T.from_fraction(reduce(x)) for x in sorted(set(labels))]
    assert len(tones) == 36
    return build_scl(
        description="Marimba design, Inverted D'alessandro Kbd Program",
        tones=tones,
        title="Notes on a New Marimba, its Tuning, and its Music",
        function=f,
    )


def cps(numbers, count, root=None):
    factors = combinations(numbers, count)
    if root is None:
        root = math.prod(numbers[:count])
    tones = [
        T.from_fraction(reduce(F(math.prod(x), root)), comment="*".join(map(str, x)))
        for x in factors
    ]
    assert len(tones) == len(set(tones))
    return tones


def xen12_wilson_02_hexany(f):
    tones = cps([3, 5, 7, 11], 2, 5 * 7)
    assert len(tones) == 6
    return build_scl(
        description="3-5-7-11 Hexany, Figure 2",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_06_mandala(f):
    labels = [
        F(3 * 5 * 11, 7),
        F(5 * 5),
        F(3 * 5 * 7, 11),
        F(7 * 7),
        F(3 * 7 * 11, 5),
        F(11 * 11),
        #
        F(5 * 11),
        F(3 * 5),
        F(5 * 7),
        F(3 * 7),
        F(7 * 11),
        F(3 * 11),
        #
        F(5 * 7 * 11, 3),
        F(3 * 3),
    ]
    tones = [T.from_fraction(reduce(x / (5 * 7))) for x in labels]
    assert len(tones) == 14
    return build_scl(
        description="The 3-5-7-11 Mandala, Figure 6",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_06b_genus(f):
    factors = chain.from_iterable(combinations([3, 5, 7, 11], i) for i in range(5))
    tones = [
        T.from_fraction(reduce(F(math.prod(x))), comment="*".join(map(str, x)))
        for x in factors
    ]
    assert len(tones) == 16
    return build_scl(
        description="3*5*7*11 Genus, Figure 6b",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_06c_4C1_tetrany(f):
    tones = cps([3, 5, 7, 11], 1)
    assert len(tones) == 4
    return build_scl(
        description="3-5-7-11 4C1 tetrany, Figure 6c",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_06c_4C3_tetrany(f):
    tones = cps([3, 5, 7, 11], 3)
    assert len(tones) == 4
    return build_scl(
        description="3-5-7-11 4C3 tetrany, Figure 6c",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_06d_diamond(f):
    p = [1, 3, 5, 7]
    ratios = sorted({reduce(F(x, y)) for x in p for y in p})
    tones = [T.from_fraction(x) for x in ratios]
    assert len(tones) == 13
    return build_scl(
        description="1-3-5-7 diamond, Figure 6d",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_06d_major_tetrad(f):
    p = [1, 3, 5, 7]
    ratios = sorted({reduce(F(x)) for x in p})
    tones = [T.from_fraction(x) for x in ratios]
    assert len(tones) == 4
    return build_scl(
        description="1-3-5-7 major tetrad, Figure 6d",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_06d_minor_tetrad(f):
    p = [1, 3, 5, 7]
    ratios = sorted({reduce(F(1, x)) for x in p})
    tones = [T.from_fraction(x) for x in ratios]
    assert len(tones) == 4
    return build_scl(
        description="1-3-5-7 minor tetrad, Figure 6d",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_07_eikosany(f):
    tones = cps([1, 3, 7, 9, 11, 15], 3, 1 * 9 * 11)
    assert len(tones) == 20
    return build_scl(
        description="1-3-7-9-11-15 Eikosany, Figure 7",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_07_eikosany_extended(f):
    root = 1 * 9 * 11
    tones = cps([1, 3, 7, 9, 11, 15], 3, root)
    extra = [(3, 9, 33), (1, 7, 5)]
    tones.extend(
        [
            Tone.from_fraction(
                reduce(F(math.prod(x), root)), comment="*".join(map(str, x))
            )
            for x in extra
        ]
    )
    assert len(tones) == 22
    return build_scl(
        description="1-3-7-9-11-15 Eikosany with two added tones, Figure 7",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


FOURS = []


def add_hexanies_and_tetranies():
    for i, fours in enumerate(combinations([1, 3, 7, 9, 11, 15], 4)):
        FOURS.append(fours)
        label = f"{i:02}"
        tetrany_1_name = f"xen12_wilson_08_4C1_tetrany_{label}"
        tetrany_3_name = f"xen12_wilson_08_4C3_tetrany_{label}"
        hexany_name = f"xen12_wilson_09_4C2_hexany_{label}"

        def build_tetrany_1(f, fours=fours):
            tones = cps(fours, 1)
            description = "-".join(map(str, fours)) + " 4C1 Tetrany, Figure 8"
            return build_scl(
                description=description,
                tones=tones,
                title="D'Alessandro, like a Hurricane",
                function=f,
            )

        def build_tetrany_3(f, fours=fours):
            tones = cps(fours, 3)
            description = "-".join(map(str, fours)) + " 4C3 Tetrany, Figure 8"
            return build_scl(
                description=description,
                tones=tones,
                title="D'Alessandro, like a Hurricane",
                function=f,
            )

        def build_hexany(f, fours=fours):
            tones = cps(fours, 2)
            description = "-".join(map(str, fours)) + " 4C2 Hexany, Figure 9"
            return build_scl(
                description=description,
                tones=tones,
                title="D'Alessandro, like a Hurricane",
                function=f,
            )

        globals()[tetrany_1_name] = build_tetrany_1
        globals()[tetrany_3_name] = build_tetrany_3
        globals()[hexany_name] = build_hexany


add_hexanies_and_tetranies()


def xen12_wilson_13_eikosany(f):
    tones = cps([1, 3, 5, 7, 9, 11], 3)
    assert len(tones) == 20
    return build_scl(
        description="1-3-5-7-9-11 Eikosany, Figure 13",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_14_diamond(f):
    p = [1, 3, 5, 7, 9, 11]
    ratios = sorted({reduce(F(x, y)) for x in p for y in p})
    tones = [T.from_fraction(x) for x in ratios]
    assert len(tones) == 29
    return build_scl(
        description="1-3-5-7-9-11 Diamond, Figure 14",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_15_diamond_eikosany_intersection(f):
    numbers = [1, 3, 5, 7, 9, 11]
    eikosany_tones = cps(numbers, 3, 3 * 5 * 11)
    diamond_ratios = {reduce(F(x, y)) for x in numbers for y in numbers}
    # 6/5 and 12/11 are not in the intersection on the diagram
    tones = [
        t
        for t in eikosany_tones
        if F(t.ratio_n, t.ratio_d) in (diamond_ratios - {F(6, 5), F(12, 11)})
    ]
    assert len(tones) == 10
    return build_scl(
        description="Intersection of Diamond & Eikosany (1 3 5 7 9 11), Figure 15",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_15_diamond_eikosany_union(f):
    numbers = [1, 3, 5, 7, 9, 11]
    eikosany_tones = cps(numbers, 3, 3 * 5 * 11)
    eikosany_ratios = {F(t.ratio_n, t.ratio_d) for t in eikosany_tones}
    diamond_ratios = {reduce(F(x, y)) for x in numbers for y in numbers}
    diamond_tones = [T.from_fraction(x) for x in diamond_ratios]
    tones = sorted(
        eikosany_tones
        + [T.from_fraction(x) for x in sorted(diamond_ratios - eikosany_ratios)]
    )
    assert len(tones) == 37
    return build_scl(
        description="Union of Diamond & Eikosany (1 3 5 7 9 11), see Figure 15",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_20b_genus(f):
    numbers = [1, 3, 5, 7, 9, 11]
    factors = chain.from_iterable(
        combinations(numbers, i) for i in range(len(numbers) + 1)
    )
    # Multiple factors can give same ratio (because of 1)
    tones_and_labels = defaultdict(lambda: [])
    for x in factors:
        tones_and_labels[reduce(F(math.prod(x)))].append("*".join(map(str, x)))
    tones = [
        T.from_fraction(k, comment=", ".join(v)) for k, v in tones_and_labels.items()
    ]
    assert len(tones) == 32
    return build_scl(
        description="Combination-product Sets (0,6) thru (6,6) 1 3 5 7 9 11, Figure 20b",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        comments=['See also "Beth", Figure 21'],
        function=f,
    )


def xen12_wilson_23_dalessandro(f):
    labels = [
        (1,),
        #
        (3, 3, 3, 5, 7, F(1, 11)),
        (3,),
        (3, 3, 3),
        (3, 5),
        (3, 3, 3, 5),
        #
        (3, 3),
        (5,),
        (3, 3, 5),
        (3, 3, 3, 3, 5),
        (7,),
        (3, 3, 7),
        #
        (3, 3, 3, 5),
        (7, F(1, 3)),
        (3, 7),
        (3, 3, 3, 7),
        (3, 5, 7),
        (3, 3, 3, 5, 7),
        (3, 11),
        #
        (5, 7),
        (3, 3, 5, 7),
        (11,),
        (3, 3, 11),
        (5, 11),
        (3, 3, 5, 11),
        #
        (3, 11),
        (3, 3, 3, 11),
        (3, 5, 11),
        (3, 3, 3, 5, 11),
        (7, 11, F(1, 3)),
        (3, 7, 11),
        (3, 3, 3, 7, 11),
        #
        (3, 3, 3, 3, 5, 11),
        (7, 11),
        (3, 3, 7, 11),
        (5, 7, 11),
        (3, 3, 5, 7, 11),
        (11, 11),
        #
        (3, 3, 3, 7, 11),
        (3, 5, 7, 11),
        (3, 3, 3, 5, 7, 11),
        (3, 11, 11),
        (3, 3, 3, 11, 11),
        (3, 5, 11, 11),
        (3, 3, 3, 5, 11, 11),
        #
        (3, 3, 11, 11),
        (5, 11, 11),
        (3, 3, 5, 11, 11),
        (3, 3, 3, 3, 5, 11, 11),
        (7, 11, 11),
        (3, 3, 7, 11, 11),
        #
        (3, 3, 3, 5, 11, 11),
        (7, 11, 11, F(1, 3)),
        (3, 7, 11, 11),
        (3, 3, 3, 7, 11, 11),
        (3, 5, 7, 11, 11),
        (3, 3, 3, 5, 7, 11, 11),
        #
        (5, 7, 11, 11),
        (3, 3, 5, 7, 11, 11),
        (11, 11, 11),
    ]
    tones = [
        T.from_fraction(reduce(F(math.prod(x))), comment="*".join(map(str, x)))
        for x in sorted(set(labels))
    ]
    assert len(tones) == 56
    return build_scl(
        description="Genus 3*3*3*5*7*11*11 (& 8 pigtails), D'Alessandro, Figure 23",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_23_genus(f):
    numbers = [3, 3, 3, 5, 7, 11, 11]
    factors = sorted(
        set(
            chain.from_iterable(
                combinations(numbers, i) for i in range(len(numbers) + 1)
            )
        )
    )
    # Multiple factors can give same ratio (because of 1)
    tones_and_labels = defaultdict(lambda: [])
    for x in factors:
        tones_and_labels[reduce(F(math.prod(x)))].append("*".join(map(str, x)))
    tones = [
        T.from_fraction(k, comment=", ".join(v)) for k, v in tones_and_labels.items()
    ]
    assert len(tones) == 48
    return build_scl(
        description="Genus 3*3*3*5*7*11*11, subset of D'Alessandro, see Figure 23",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_23_repeated_1(f):
    numbers = [3, 3, 3, 5, 7, 11]
    factors = sorted(
        set(
            chain.from_iterable(
                combinations(numbers, i) for i in range(len(numbers) + 1)
            )
        )
    )
    pigtails = [
        (7, 11, F(1, 3)),
        (7, F(1, 3)),
        (11, 11),
        (3, 3, 3, 3, 5, 11),
        (3, 3, 3, 3, 5),
        (3, 3, 3, 5, 7, F(1, 11)),
    ]
    assert len(pigtails) == 6
    factors = factors + pigtails
    tones = [
        T.from_fraction(reduce(F(math.prod(x))), comment="*".join(map(str, x)))
        for x in factors
    ]
    assert len(tones) == 38
    return build_scl(
        description='Lattice for Genus 3*3*3*5*7*11 (plus 6 pigtails), Repeated Patterins in "Dalessandro", Figure 23',
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_23_repeated_2(f):
    numbers = [3, 3, 3, 5, 7]
    factors = sorted(
        set(
            chain.from_iterable(
                combinations(numbers, i) for i in range(len(numbers) + 1)
            )
        )
    )
    pigtails = [
        (7, F(1, 3)),
        (11,),
        (3, 3, 3, 5, 7, F(1, 11)),
        (3, 3, 3, 3, 5),
    ]
    assert len(pigtails) == 4
    factors = factors + pigtails
    tones = [
        T.from_fraction(reduce(F(math.prod(x))), comment="*".join(map(str, x)))
        for x in factors
    ]
    assert len(tones) == 20
    return build_scl(
        description='Lattice for Genus 3*3*3*5*7 (plus 4 pigtails), Repeated Patterins in "Dalessandro", Figure 23',
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_24_dalessandro(f):
    labels = [
        (),
        #
        (3, 5, 7, 9, F(1, 11)),  # or (F(1, 3),)
        (3,),
        (3, 9),
        (3, 5),
        #
        (),
        (9,),
        (5,),
        (5, 9),
        (3, 3, 5, 9),  # Bracketed
        (7,),
        (7, 9),
        #
        (3, 5, 9),
        (7, F(1, 3)),  # Bracketed, or (9, 3, 5, 9)
        (3, 7),
        (3, 7, 9),
        (3, 5, 7),
        (3, 5, 7, 9),
        #
        (7, 9),
        (5, 7),
        (5, 7, 9),
        (11,),
        (9, 11),
        (5, 11),
        (5, 9, 11),
        #
        (3, 11),
        (3, 9, 11),
        (3, 5, 11),
        (3, 5, 9, 11),
        (7, 11, F(1, 3)),  # Bracketed
        (3, 7, 11),
        #
        (5, 9, 11),
        (3, 3, 5, 9, 11),  # Bracketed, or (7, 11, F(1, 9))
        (7, 11),
        (7, 9, 11),
        (5, 7, 11),
        (5, 7, 9, 11),
        (11, 11),  # Bracketed, or (3, 3, 5, 7, 9, 11)
        #
        (3, 7, 9, 11),
        (3, 5, 7, 11),
        (3, 5, 7, 9, 11),
    ]
    factors = sorted(set(labels))
    tones = [
        T.from_fraction(reduce(F(math.prod(x))), comment="*".join(map(str, x)))
        for x in factors
    ]
    assert len(tones) == 38
    return build_scl(
        description='"D\'alessandro", 1.3.5.7.9.11 Combination-Product Set series, Figure 24',
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        comments=["Note Figure 24 gives other options for some notes"],
        function=f,
    )


def xen12_wilson_25_6C5_hexany(f):
    tones = cps([1, 3, 5, 7, 9, 11], 5, 1 * 3 * 7 * 9 * 11)
    assert len(tones) == 6
    return build_scl(
        description="1.3.5.7.9.11 6C5 Hexany, Figure 25",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_25_6C4_pentadekany(f):
    tones = cps([1, 3, 5, 7, 9, 11], 4, 3 * 7 * 9 * 11)
    assert len(tones) == 15
    return build_scl(
        description="1.3.5.7.9.11 6C4 Pentadekany, Figure 25",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_25_6C3_eikosany(f):
    tones = cps([1, 3, 5, 7, 9, 11], 3, 1 * 3 * 11)
    assert len(tones) == 20
    return build_scl(
        description="1.3.5.7.9.11 6C3 Eikosany, Figure 25",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_25_6C2_pentadekany(f):
    tones = cps([1, 3, 5, 7, 9, 11], 2, 3 * 11)
    assert len(tones) == 15
    return build_scl(
        description="1.3.5.7.9.11 6C2 Pentadekany, Figure 25",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_25_6C1_hexany(f):
    tones = cps([1, 3, 5, 7, 9, 11], 1, 1)
    assert len(tones) == 6
    return build_scl(
        description="1.3.5.7.9.11 6C1 Hexany, Figure 25",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_26_inverted_dallesandro(f):
    labels = [
        (3, 11),
        #
        (11,),
        (9, 11),
        (5, 11),
        (5, 9, 11),
        #
        (3, 11),
        (3, 9, 11),
        (3, 5, 11),
        (3, 5, 9, 11),
        (7, 11, F(1, 3)),
        (3, 7, 11),
        (1,),
        (3, 7, 9, 11),
        #
        (3, 3, 5, 9, 11),  # Bracketed
        (7, 11),
        (7, 9, 11),
        (3,),
        (5, 7, 11),
        (3, 9),
        (5, 7, 9, 11),
        (3, 5),
        #
        (1,),
        (3, 7, 9, 11),
        (9,),
        (3, 5, 7, 11),
        (5,),
        (3, 5, 7, 9, 11),
        (5, 9),
        (3, 3, 5, 9),  # Bracketed
        (7,),
        (7, 9),
        #
        (3, 5, 9),
        (7, F(1, 3)),
        (3, 7),
        (3, 7, 9),
        (3, 5, 7),
        (3, 5, 7, 9),
        #
        (7, 9),
        (5, 7),
        (5, 7, 9),
    ]
    factors = sorted(set(labels))
    tones = [
        T.from_fraction(reduce(F(math.prod(x))), comment="*".join(map(str, x)))
        for x in factors
    ]
    assert len(tones) == 36
    return build_scl(
        description='inverted "D\'alessandro", Figure 26',
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_30_double_dekany(f):
    numbers = [1, 5, 7, 11, 15]
    root = 1 * 5
    dekany1 = {
        reduce(F(math.prod(x), root)): "*".join(map(str, x))
        for x in combinations(numbers, 2)
    }
    dekany2 = {
        reduce(F(math.prod(x), root)): "*".join(map(str, x))
        for x in combinations(numbers, 3)
    }

    double_dekany = {k: [v] for k, v in dekany1.items()}
    for k, v in dekany2.items():
        if k in dekany1:
            double_dekany[k].append(v)
        else:
            double_dekany[k] = [v]

    tones = [T.from_fraction(k, comment=", ".join(v)) for k, v in double_dekany.items()]
    assert len(tones) == 14
    return build_scl(
        description="5C2 + 5C3 1-5-7-11-15 Double-Dekany, Figure 30",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_31_pentadic_diamond(f):
    p = [1, 5, 7, 11, 15]
    ratios = sorted({reduce(F(x, y)) for x in p for y in p})
    tones = [T.from_fraction(x) for x in ratios]
    return build_scl(
        description="1-5-7-11-15 Pentadic Diamond, Figure 31",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_32_dekany(f):
    tones = cps([1, 5, 7, 11, 15], 2)
    assert len(tones) == 10
    return build_scl(
        description="5C2 1.5.7.11.15 Dekany, Figure 32",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_33_dekany(f):
    tones = cps([1, 5, 7, 11, 15], 3)
    assert len(tones) == 10
    return build_scl(
        description="5C3 1.5.7.11.15 Dekany, Figure 33",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def add_hexanies_and_tetranies_2():
    for i, fours in enumerate(combinations([1, 3, 5, 7, 9, 11], 4)):
        if fours in FOURS:
            continue
        label = f"{i:02}"
        tetrany_1_name = f"xen12_wilson_38_4C1_tetrany_{label}"
        tetrany_3_name = f"xen12_wilson_38_4C3_tetrany_{label}"
        hexany_name = f"xen12_wilson_39_4C2_hexany_{label}"

        def build_tetrany_1(f, fours=fours):
            tones = cps(fours, 1)
            description = "-".join(map(str, fours)) + " 4C1 Tetrany, Figure 38"
            return build_scl(
                description=description,
                tones=tones,
                title="D'Alessandro, like a Hurricane",
                function=f,
            )

        def build_tetrany_3(f, fours=fours):
            tones = cps(fours, 3)
            description = "-".join(map(str, fours)) + " 4C3 Tetrany, Figure 38"
            return build_scl(
                description=description,
                tones=tones,
                title="D'Alessandro, like a Hurricane",
                function=f,
            )

        def build_hexany(f, fours=fours):
            tones = cps(fours, 2)
            description = "-".join(map(str, fours)) + " 4C2 Hexany, Figure 39"
            return build_scl(
                description=description,
                tones=tones,
                title="D'Alessandro, like a Hurricane",
                function=f,
            )

        globals()[tetrany_1_name] = build_tetrany_1
        globals()[tetrany_3_name] = build_tetrany_3
        globals()[hexany_name] = build_hexany


add_hexanies_and_tetranies_2()


def add_dekanies():
    for i, fives in enumerate(combinations([1, 3, 5, 7, 9, 11], 5)):
        label = f"{i:02}"
        dekany_2_name = f"xen12_wilson_40_5C2_dekany_{label}"
        dekany_3_name = f"xen12_wilson_40_5C3_dekany_{label}"

        def build_dekany_2(f, fives=fives):
            tones = cps(fives, 2)
            description = "-".join(map(str, fives)) + " 5C2 Dekany, Figure 40"
            return build_scl(
                description=description,
                tones=tones,
                title="D'Alessandro, like a Hurricane",
                function=f,
            )

        def build_dekany_3(f, fives=fives):
            tones = cps(fives, 3)
            description = "-".join(map(str, fives)) + " 5C3 Dekany, Figure 40"
            return build_scl(
                description=description,
                tones=tones,
                title="D'Alessandro, like a Hurricane",
                function=f,
            )

        globals()[dekany_2_name] = build_dekany_2
        globals()[dekany_3_name] = build_dekany_3


add_dekanies()


def xen12_wilson_41_hexadic_tileburst_1(f):
    labels = [
        (1,),
        (3,),
        (5,),
        (7,),
        (9,),
        (11,),
        (3, 5, 11),
        (3, 5),
        (3, 5, 7),
        (5, 7),
        (5, 7, 9),
        (7, 9),
        (7, 9, 11),
        (9, 11),
        (3, 9, 11),
        (3, 11),
    ]
    tones = [
        T.from_fraction(reduce(F(math.prod(x))), comment="*".join(map(str, x)))
        for x in labels
    ]
    assert len(tones) == 16
    return build_scl(
        description="Four Hexadic Tilebursts, Figure 41, top left",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_41_hexadic_tileburst_2(f):
    labels = [
        (3,),
        (3, 7),
        (3, 9),
        (3, 7, 9),
        (3, 7, 9, 11),
        (3, 5, 7, 9),
        (3, 5, 11),
        (3, 5),
        (3, 5, 7),
        (5, 7),
        (5, 7, 9),
        (7, 9),
        (7, 9, 11),
        (9, 11),
        (3, 9, 11),
        (3, 11),
    ]
    tones = [
        T.from_fraction(reduce(F(math.prod(x), 3)), comment="*".join(map(str, x)))
        for x in labels
    ]
    assert len(tones) == 16
    return build_scl(
        description="Four Hexadic Tilebursts, Figure 41, top right",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_41_hexadic_tileburst_3(f):
    labels = [
        (F(1, 1),),
        #
        (F(5, 7),),
        (F(7, 9),),
        (F(9, 11),),
        (F(11, 3),),
        (F(3, 5),),
        #
        (F(3, 9),),
        (F(5, 9),),
        (F(5, 11),),
        (F(7, 11),),
        (F(7, 3),),
        (9, F(1, 3)),
        (F(9, 5),),
        (F(11, 5),),
        (F(11, 7),),
        (F(3, 7),),
    ]
    tones = [
        T.from_fraction(reduce(F(math.prod(x))), comment="*".join(map(str, x)))
        for x in labels
    ]
    assert len(tones) == 16
    return build_scl(
        description="Four Hexadic Tilebursts, Figure 41, bottom left",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_41_hexadic_tileburst_4(f):
    labels = [
        (3, 9, F(1, 7), F(1, 11)),
        (F(3, 11),),
        (5, 9, F(1, 7), F(1, 11)),
        (F(9, 11),),
        (3, 9, F(1, 5), F(1, 11)),
        (F(9, 7),),
        #
        (F(3, 9),),
        (F(5, 9),),
        (F(5, 11),),
        (F(7, 11),),
        (F(7, 3),),
        (9, F(1, 3)),
        (F(9, 5),),
        (F(11, 5),),
        (F(11, 7),),
        (F(3, 7),),
    ]
    tones = [
        T.from_fraction(reduce(F(math.prod(x), 3)), comment="*".join(map(str, x)))
        for x in labels
    ]
    assert len(tones) == 16
    return build_scl(
        description="Four Hexadic Tilebursts, Figure 41, bottom right",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_42_ogdoadic_tileburst_1(f):
    labels = [
        (1,),
        #
        (3,),
        (5,),
        (7,),
        (9,),
        (11,),
        (13,),
        (15,),
        #
        (3, 5),
        (5, 7),
        (7, 9),
        (9, 11),
        (11, 13),
        (13, 15),
        (3, 15),
        #
        (3, 5, 15),
        (3, 5, 7, 15),
        (3, 5, 7),
        (3, 5, 7, 9),
        (5, 7, 9),
        (5, 7, 9, 11),
        (7, 9, 11),
        (7, 9, 11, 13),
        (9, 11, 13),
        (9, 11, 13, 15),
        (11, 13, 15),
        (3, 11, 13, 15),
        (3, 13, 15),
        (3, 5, 13, 15),
    ]
    assert len(labels) == len(set(labels))
    ratios_dict = defaultdict(lambda: [])
    for x in labels:
        ratio = reduce(F(math.prod(x)))
        label_str = "*".join(map(str, x))
        ratios_dict[ratio].append(label_str)
    tones = [T.from_fraction(k, comment=", ".join(v)) for k, v in ratios_dict.items()]
    assert len(tones) == 28
    return build_scl(
        description="Four Ogdoadic Tilebursts, Figure 42, top left",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_42_ogdoadic_tileburst_2(f):
    labels = [
        (3, 7, 9, 13, 15),
        (3, 5, 7, 9, 13, 15),
        (5, 7, 9, 13, 15),
        (7, 9, 13, 15),
        (3, 5, 7, 13, 15),
        (3, 5, 7, 9, 15),
        (5, 7, 9, 15),
        (5, 7, 9, 13),
        (7, 9),
        (7, 9, 13),
        (7, 9, 11, 13, 15),
        (9, 13, 15),
        (13, 15),
        (3, 9, 13, 15),
        (3, 7, 13, 15),
        #
        (3, 5, 15),
        (3, 5, 7, 15),
        (3, 5, 7),
        (3, 5, 7, 9),
        (5, 7, 9),
        (5, 7, 9, 11),
        (7, 9, 11),
        (7, 9, 11, 13),
        (9, 11, 13),
        (9, 11, 13, 15),
        (11, 13, 15),
        (3, 11, 13, 15),
        (3, 13, 15),
        (3, 5, 13, 15),
    ]
    assert len(labels) == len(set(labels))
    ratios_dict = defaultdict(lambda: [])
    for x in labels:
        ratio = reduce(F(math.prod(x), 7 * 9))
        label_str = "*".join(map(str, x))
        ratios_dict[ratio].append(label_str)
    tones = [T.from_fraction(k, comment=", ".join(v)) for k, v in ratios_dict.items()]
    assert len(tones) == 28
    return build_scl(
        description="Four Ogdoadic Tilebursts, Figure 42, top right",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_42_ogdoadic_tileburst_3(f):
    labels = [
        (F(9, 7),),
        (9, 15, F(1, 7), F(1, 13)),
        (3, 9, F(1, 7), F(1, 13)),
        (3, 9, F(1, 7), F(1, 15)),
        (F(11, 7),),
        (11, 15, F(1, 7), F(1, 13)),
        (9, 15, F(1, 7), F(1, 11)),
        (3, 9, F(1, 7), F(1, 11)),
        (F(3, 13),),
        (5, 9, F(1, 7), F(1, 13)),
        (5, 9, F(1, 7), F(1, 15)),
        (F(9, 13),),
        (3, 9, F(1, 5), F(1, 15)),
        (F(9, 5),),
        (F(3, 7),),
        #
        (F(3, 11),),
        (F(5, 11),),
        (F(5, 13),),
        (F(7, 13),),
        (F(7, 15),),
        (F(9, 15),),
        (F(9, 3),),
        (F(11, 3),),
        (F(11, 5),),
        (F(13, 5),),
        (F(13, 7),),
        (F(15, 7),),
        (F(15, 9),),
        (F(3, 9),),
    ]
    assert len(labels) == len(set(labels))
    ratios_dict = defaultdict(lambda: [])
    for x in labels:
        ratio = reduce(F(7 * math.prod(x), 3))
        label_str = "*".join(map(str, x))
        ratios_dict[ratio].append(label_str)
    tones = [T.from_fraction(k, comment=", ".join(v)) for k, v in ratios_dict.items()]
    assert len(tones) == 28
    return build_scl(
        description="Four Ogdoadic Tilebursts, Figure 42, bottom left",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def xen12_wilson_42_ogdoadic_tileburst_4(f):
    labels = [
        (F(1, 1),),
        #
        (F(7, 9),),
        (F(9, 11),),
        (F(11, 13),),
        (F(13, 15),),
        (F(15, 3),),
        (F(3, 5),),
        (F(5, 7),),
        #
        (F(5, 9),),
        (F(7, 11),),
        (F(9, 13),),
        (F(11, 15),),
        (F(13, 3),),
        (15, F(1, 5)),
        (F(3, 7),),
        #
        (F(3, 11),),
        (F(5, 11),),
        (F(5, 13),),
        (F(7, 13),),
        (F(7, 15),),
        (9, F(1, 15)),
        (9, F(1, 3)),
        (F(11, 3),),
        (F(11, 5),),
        (F(13, 5),),
        (F(13, 7),),
        (F(15, 7),),
        (F(15, 9),),
        (F(3, 9),),
    ]
    assert len(labels) == len(set(labels))
    ratios_dict = defaultdict(lambda: [])
    for x in labels:
        ratio = reduce(F(math.prod(x)))
        label_str = "*".join(map(str, x))
        ratios_dict[ratio].append(label_str)
    tones = [T.from_fraction(k, comment=", ".join(v)) for k, v in ratios_dict.items()]
    assert len(tones) == 27
    return build_scl(
        description="Four Ogdoadic Tilebursts, Figure 42, bottom right",
        tones=tones,
        title="D'Alessandro, like a Hurricane",
        function=f,
    )


def tritriadic_mt(a, b, c):
    M = F(b, a)
    D = F(c, a)
    subdominant = [2 / M, F(2, 1), D / M]
    tonic = [F(1, 1), M, D]
    dominant = [M, M * M, D * M]
    tones = tuple(sorted({reduce(x) for x in subdominant + tonic + dominant}))
    assert len(tones) == 7
    return tones


def tritriadic_dm(a, b, c):
    M = F(b, a)
    D = F(c, a)
    subdominant = [M / D, M * M / D, M]
    tonic = [F(1, 1), M, D]
    dominant = [D / M, D, D * D / M]
    tones = tuple(sorted({reduce(x) for x in subdominant + tonic + dominant}))
    assert len(tones) == 7
    return tones


def add_tritriadic_mt(a, b, c):
    name = f"xen12_chalmers_tritriadic_mt_{a}_{b}_{c}"

    tones = tritriadic_mt(a, b, c)
    if tones in TRITRIADIC_TONES:
        return
    TRITRIADIC_TONES.add(tones)

    def build(f):
        return build_scl(
            description=f"Tritriadic M->T scale built from {a}:{b}:{c}",
            tones=tones,
            title="Tritriadic Scales with Seven Tones, Part Three",
            function=f,
        )

    globals()[name] = build


def add_tritriadic_dm(a, b, c):
    name = f"xen12_chalmers_tritriadic_dm_{a}_{b}_{c}"

    tones = tritriadic_dm(a, b, c)
    if tones in TRITRIADIC_TONES:
        return
    TRITRIADIC_TONES.add(tones)

    def build(f):
        return build_scl(
            description=f"Tritriadic D->M scale built from {a}:{b}:{c}",
            tones=tones,
            title="Tritriadic Scales with Seven Tones, Part Three",
            function=f,
        )

    globals()[name] = build


TRITRIADIC_MT = [
    (1, 3, 5),
    (11, 3, 1),
    (1, 5, 9),
    (27, 5, 1),
    (1, 13, 7),
    (17, 7, 1),
    (1, 21, 23),
    (11, 5, 3),
    (3, 5, 15),
    (3, 7, 19),
    (3, 11, 27),
    (7, 9, 5),
    (5, 9, 11),
    (13, 9, 5),
    (27, 9, 5),
    (15, 11, 5),
    (5, 15, 27),
    (5, 17, 25),
    (17, 27, 5),
    (9, 25, 7),
    (13, 23, 7),
    (5, 17, 7),
    (17, 21, 7),
    (7, 17, 23),
    (7, 19, 21),
    (23, 19, 7),
    (19, 25, 7),
    (25, 23, 7),
    (9, 11, 15),
    (11, 27, 9),
    (25, 27, 11),
    (13, 17, 19),
    (23, 21, 13),
    (15, 21, 23),
    (27, 25, 15),
    (19, 21, 17),
    (25, 19, 17),
    (21, 25, 17),
    (17, 23, 25),
    (27, 23, 17),
    (21, 23, 19),
    (27, 21, 19),
]

assert len(TRITRIADIC_MT) == 42
assert len(set(TRITRIADIC_MT)) == len(TRITRIADIC_MT)

for a, b, c in TRITRIADIC_MT:
    add_tritriadic_mt(a, b, c)

TRITRIADIC_DM = [
    (5, 3, 1),
    (1, 3, 11),
    (9, 5, 1),
    (1, 5, 27),
    (7, 13, 1),
    (1, 7, 17),
    (1, 21, 23),
    (11, 5, 3),
    (3, 5, 15),
    (3, 7, 19),
    (3, 11, 27),
    (7, 9, 5),
    (5, 9, 11),
    (13, 9, 5),
    (27, 9, 5),
    (15, 11, 5),
    (5, 15, 27),
    (5, 17, 25),
    (17, 27, 5),
    (9, 25, 7),
    (13, 23, 7),
    (5, 17, 7),
    (17, 21, 7),
    (7, 17, 23),
    (7, 19, 21),
    (23, 19, 7),
    (19, 25, 7),
    (25, 23, 7),
    (9, 11, 15),
    (11, 27, 9),
    (25, 27, 11),
    (13, 17, 19),
    (23, 21, 13),
    (15, 21, 23),
    (27, 25, 15),
    (19, 21, 17),
    (25, 19, 17),
    (21, 25, 17),
    (17, 23, 25),
    (27, 23, 17),
    (21, 23, 19),
    (27, 21, 19),
]

assert len(TRITRIADIC_DM) == 42
assert len(set(TRITRIADIC_DM)) == len(TRITRIADIC_DM)

for a, b, c in TRITRIADIC_DM:
    add_tritriadic_dm(a, b, c)


def xen12_hanson_02_ten(f):
    tones = [
        T(9, 8),
        T(6, 5),
        T(5, 4),
        T(4, 3),
        T(3, 2),
        T(8, 5),
        T(5, 3),
        T(9, 5),
        T(15, 8),
        T(2, 1),
    ]
    assert len(tones) == 10
    return build_scl(
        description="Ten tones, Figure 2",
        tones=tones,
        title="Development of a 53-Tone Keyboard Layout",
        function=f,
    )


def xen12_hanson_06_basic(f):
    labels = [
        3,
        6,
        9,
        11,
        14,
        17,
        20,
        22,
        25,
        28,
        31,
        34,
        36,
        39,
        42,
        45,
        48,
        50,
        53,
    ]
    assert len(labels) == 19
    tones = [T(1200.0 * x / 53, comment=str(x)) for x in labels]
    assert len(tones) == 19
    return build_scl(
        description="Basic group of 19 of 53 tones, Figure 6",
        tones=tones,
        title="Development of a 53-Tone Keyboard Layout",
        function=f,
    )


def xen12_hanson_06_basic_just(f):
    tones = [
        T(25, 24),
        T(27, 25),
        T(9, 8),
        T(144, 125),
        T(6, 5),
        T(5, 4),
        T(125, 96),
        T(4, 3),
        T(25, 18),
        T(36, 25),
        T(3, 2),
        T(25, 16),
        T(8, 5),
        T(5, 3),
        T(125, 72),
        T(9, 5),
        T(15, 8),
        T(48, 25),
        T(2, 1),
    ]
    assert len(tones) == 19
    return build_scl(
        description="Basic group of 19 of 53 tones, tonal function, Figure 6",
        tones=tones,
        title="Development of a 53-Tone Keyboard Layout",
        function=f,
    )


def xen12_hanson_06_53_just(f):
    tones = [
        T(81, 80),
        T(250, 243),
        T(25, 24),
        T(135, 128),
        T(16, 15),
        T(27, 25),
        T(2187, 2000),
        T(10, 9),
        T(9, 8),
        T(256, 225, comment="or 729/640"),
        T(144, 125),
        T(729, 625),
        T(32, 27),
        T(6, 5),
        T(243, 200),
        T(100, 81),
        T(5, 4),
        T(81, 64),
        T(625, 486),
        T(125, 96),
        T(320, 243, comment="or 675/512"),
        T(4, 3),
        T(27, 20),
        T(1000, 729),
        T(25, 18),
        T(45, 32),
        T(64, 45),
        T(36, 25),
        T(729, 500),
        T(40, 27),
        T(3, 2),
        T(243, 160),
        T(125, 81),
        T(25, 16),
        T(128, 81, comment="or 405/256"),
        T(8, 5),
        T(81, 50),
        T(400, 243),
        T(5, 3),
        T(27, 16),
        T(1250, 729),
        T(125, 72),
        T(225, 128),
        T(16, 9),
        T(9, 5),
        T(729, 400),
        T(50, 27),
        T(15, 8),
        T(256, 135, comment="or 243/128"),
        T(48, 25),
        T(243, 125),
        T(160, 81),
        T(2, 1),
    ]
    assert len(tones) == 53
    return build_scl(
        description="53 tones, tonal function, Figure 6",
        tones=tones,
        title="Development of a 53-Tone Keyboard Layout",
        function=f,
    )


def xen12_hanson_11_chain_19(f):
    labels = range(1, 20)
    assert len(labels) == 19
    tones = [T(1200.0 * x / 19, comment=str(x)) for x in labels]
    assert len(tones) == 19
    return build_scl(
        description="Chain of minor thirds in 19EDO, Figure 11",
        tones=tones,
        title="Development of a 53-Tone Keyboard Layout",
        function=f,
    )


def xen12_hanson_11_chain_34(f):
    labels = [
        2,
        4,
        6,
        7,
        9,
        11,
        13,
        14,
        16,
        18,
        20,
        22,
        23,
        25,
        27,
        29,
        31,
        32,
        34,
    ]
    assert len(labels) == 19
    tones = [T(1200.0 * x / 34, comment=str(x)) for x in labels]
    assert len(tones) == 19
    return build_scl(
        description="Chain of minor thirds in 34EDO, Figure 11",
        tones=tones,
        title="Development of a 53-Tone Keyboard Layout",
        function=f,
    )


def xen12_hanson_11_chain_72(f):
    labels = [
        4,
        8,
        12,
        15,
        19,
        23,
        27,
        30,
        34,
        38,
        42,
        46,
        49,
        53,
        57,
        61,
        65,
        68,
        72,
    ]
    assert len(labels) == 19
    tones = [T(1200.0 * x / 72, comment=str(x)) for x in labels]
    assert len(tones) == 19
    return build_scl(
        description="Chain of minor thirds in 72EDO, Figure 11",
        tones=tones,
        title="Development of a 53-Tone Keyboard Layout",
        function=f,
    )


def xen12_hanson_11_chain_87(f):
    labels = [
        5,
        10,
        15,
        18,
        23,
        28,
        33,
        36,
        41,
        46,
        51,
        56,
        59,
        64,
        69,
        74,
        79,
        82,
        87,
    ]
    assert len(labels) == 19
    tones = [T(1200.0 * x / 87, comment=str(x)) for x in labels]
    assert len(tones) == 19
    return build_scl(
        description="Chain of minor thirds in 87EDO, Figure 11",
        tones=tones,
        title="Development of a 53-Tone Keyboard Layout",
        function=f,
    )


def xen12_hanson_12_ogdoadic_diamond(f):
    p = [1, 3, 5, 7, 9, 11, 13, 15]
    ratios = sorted({reduce(F(x, y)) for x in p for y in p})
    tones = [T.from_fraction(x) for x in ratios]
    return build_scl(
        description="Ogdoadic Diamond, Figure 12",
        tones=tones,
        title="Development of a 53-Tone Keyboard Layout",
        function=f,
    )


def xen12_hanson_13_three_ogdoadic_diamonds(f):
    p = [1, 3, 5, 7, 9, 11, 13, 15]
    diamond = {reduce(F(x, y)) for x in p for y in p}
    diamond2 = {reduce(F(4, 3) * x) for x in diamond}
    diamond3 = {reduce(F(3, 2) * x) for x in diamond}
    ratios = sorted(diamond | diamond2 | diamond3)
    tones = [T.from_fraction(x) for x in ratios]
    return build_scl(
        description="3 Ogdoadic Diamonds (at 1/1, 4/3 & 3/2), Figure 13",
        tones=tones,
        title="Development of a 53-Tone Keyboard Layout",
        function=f,
    )


def xen13_mclaren_log_factorial_1(f):
    period = 1644.170
    tones = [
        T(296.025, period=period),
        T(444.169, period=period),
        T(744.591, period=period),
        T(945.192, period=period),
        T(1644.170, period=period),
    ]
    assert len(tones) == 5
    return build_scl(
        description="Log factorial scale #1",
        tones=tones,
        title="General Methods for Generating Musical Scales",
        page=21,
        function=f,
    )


def xen13_mclaren_log_factorial_2(f):
    period = 1644.170
    tones = [
        T(448.558, period=period),
        T(550.386, period=period),
        T(709.348, period=period),
        T(992.114, period=period),
        T(1644.170, period=period),
    ]
    assert len(tones) == 5
    return build_scl(
        description="Log factorial scale #2",
        tones=tones,
        title="General Methods for Generating Musical Scales",
        page=21,
        function=f,
    )


def xen13_mclaren_factorable_numbers(f):
    period = 1200 * log2(5 / 3)
    tones = [
        T(11, 10, period=period),
        T(5, 4, period=period),
        T(13, 10, period=period),
        T(7, 5, period=period),
        T(5, 3, period=period),
    ]
    assert len(tones) == 5
    return build_scl(
        description="Factorable numbers scale",
        tones=tones,
        title="General Methods for Generating Musical Scales",
        page=22,
        function=f,
    )


def xen13_mclaren_totient(f):
    period = 1200 * log2(15 / 8)
    tones = [
        T(31, 30, period=period),
        T(29, 28, period=period),
        T(19, 18, period=period),
        T(17, 16, period=period),
        T(13, 12, period=period),
        T(11, 10, period=period),
        T(7, 6, period=period),
        T(5, 4, period=period),
        T(29, 22, period=period),
        T(3, 2, period=period),
        T(7, 4, period=period),
        T(15, 8, period=period),
    ]
    assert len(tones) == 12
    return build_scl(
        description="n/totient(n) scale",
        tones=tones,
        title="General Methods for Generating Musical Scales",
        page=23,
        function=f,
    )


def xen13_mclaren_infinite_continued_fraction_1(f):
    period = 1080.763
    tones = [
        T(17.585, period=period),
        T(
            35.32,
            comment="Originally printed as 35.23, period=period, see XH18 errata p.300",
        ),
        T(144.500, period=period),
        T(170.032, period=period),
        T(262.821, period=period),
        T(393.346, period=period),
        T(466.179, period=period),
        T(591.807, period=period),
        T(692.772, period=period),
        T(770.282, period=period),
        T(818.652, period=period),
        T(932.361, period=period),
        T(1049.642, period=period),
        T(1080.763, period=period),
    ]
    assert len(tones) == 14
    return build_scl(
        description="Infinite continued fraction scale #1",
        tones=tones,
        title="General Methods for Generating Musical Scales",
        page=26,
        function=f,
    )


def xen13_mclaren_infinite_continued_fraction_2(f):
    period = 1187.298
    tones = [
        T(45.985, period=period),
        T(143.132, period=period),
        T(164.847, period=period),
        T(257.353, period=period),
        T(272.964, period=period),
        T(400.012, period=period),
        T(518.435, period=period),
        T(646.615, period=period),
        T(704.861, period=period),
        T(841.880, period=period),
        T(871.559, period=period),
        T(1024.862, period=period),
        T(1064.796, period=period),
        T(1187.298, period=period),
    ]
    assert len(tones) == 14
    return build_scl(
        description="Infinite continued fraction scale #2",
        tones=tones,
        title="General Methods for Generating Musical Scales",
        page=28,
        function=f,
    )


def xen13_mclaren_infinite_continued_fraction_3(f):
    period = 1174.4849
    tones = [
        T(17.5914, period=period),
        T(35.3231, period=period),
        T(170.0317, period=period),
        T(198.5402, period=period),
        T(313.7431, period=period),
        T(477.4963, period=period),
        T(477.8234, period=period),
        T(619.5159, period=period),
        T(669.1979, period=period),
        T(797.0003, period=period),
        T(818.6521, period=period),
        T(879.3628, period=period),
        T(932.3607, period=period),
        T(998.4472, period=period),
        T(1033.1992, period=period),
        T(1174.4849, period=period),
    ]
    assert len(tones) == 16
    return build_scl(
        description="Infinite continued fraction scale #3",
        tones=tones,
        title="General Methods for Generating Musical Scales",
        page=29,
        function=f,
    )


def xen13_mclaren_recurrence_1(f):
    tones = [
        T(17, 16, cents=104.9554),
        T(5, 4, cents=386.3137),
        T(21, 16, cents=470.7809),
        T(89, 64, cents=570.8801),
        T(3, 2, cents=701.955),
        T(13, 8, cents=840.5276),
        T(55, 32, cents=937.6316),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 8
    return build_scl(
        description="Fibonacci scale (recurrence scale #1)",
        tones=tones,
        title="General Methods for Generating Musical Scales",
        page=30,
        function=f,
    )


def xen13_mclaren_recurrence_2(f):
    tones = [
        T(65, 64, cents=26.8414),
        T(2273, 2048, cents=180.4582),
        T(321, 256, cents=391.7160),
        T(3, 2, cents=701.955),
        T(
            107587,
            65536,
            cents=858.1731,
            comment="Cents originally printed as 749.3669",
        ),
        T(7, 4, cents=968.8259),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Recurrence scale #2",
        tones=tones,
        title="General Methods for Generating Musical Scales",
        page=31,
        function=f,
    )


def xen13_mclaren_prime_indices(f):
    tones = [
        T(362880, 11 * 2**15, cents=11.6293),
        T(720, 11 * 2**6, cents=38.8935),
        T(24, 22, cents=150.638),
        T(125, 112, cents=190.1130),
        T(6, 5, cents=315.6413),
        T(
            3628800,
            11 * 2**18,
            cents=397.9554,
            comment="Cents originally printed as 426.5893",
        ),
        T(4, 3, cents=498.0449),
        T(125, 88, cents=607.6225),
        T(16, 11, cents=648.6815),
        T(8, 5, cents=813.6863),
        T(12, 7, cents=933.1284),
        T(40320, 11 * 2**11, cents=1007.731),
    ]
    assert len(tones) == 12
    return build_scl(
        description="Prime indices scale",
        tones=tones,
        title="General Methods for Generating Musical Scales",
        page=32,
        function=f,
    )


def xen13_mclaren_finite_continued_fraction_1(f):
    period = 1151.3156
    tones = [
        T(48.7646, period=period),
        T(82.4037, period=period),
        T(231.1724, period=period),
        T(266.8758, period=period),
        T(315.6412, period=period),
        T(498.0449, period=period),
        T(884.3586, period=period),
        T(933.1284, period=period),
        T(1151.3156, period=period),
    ]
    assert len(tones) == 9
    return build_scl(
        description="Finite continued fraction scale #1",
        tones=tones,
        title="General Methods for Generating Musical Scales",
        page=33,
        function=f,
    )


def xen13_mclaren_difference_table(f):
    tones = [
        T(119.4428),
        T(203.91),
        T(266.8699),
        T(315.6413),
        T(354.5470),
        T(412.7453),
        T(767.9233),
        T(1017.5963),
        T(1200.0),
    ]
    assert len(tones) == 9
    return build_scl(
        description="9-tone difference table scale",
        tones=tones,
        title="General Methods for Generating Musical Scales",
        page=41,
        function=f,
    )


def xen13_rapoport_13tet_diatonic(f):
    tones = [
        T(92.0, comment="K"),
        T(185.0, comment="A"),
        T(277.0, comment="B"),
        T(462.0, comment="C"),
        T(554.0, comment="D"),
        T(646.0, comment="E"),
        T(831.0, comment="F"),
        T(923.0, comment="G"),
        T(1015.0, comment="H"),
        T(1200.0, comment="J"),
    ]
    assert len(tones) == 10
    return build_scl(
        description="13-tet diatonic scale",
        tones=tones,
        title="Notes Towards Quasi-Tonal Treiskaidekaphilia",
        page=47,
        function=f,
    )


def xen13_chalmers_13tet_5L3S(f):
    L = 2 * 1200.0 / 13
    S = 1 * 1200.0 / 13
    steps = [L, L, S, L, L, S, L, S]
    tones = [T(x) for x in csum(steps)]
    assert len(tones) == 8
    return build_scl(
        description="5L+3S Eight-Tone Moment of Symmetry (MOS)",
        tones=tones,
        title="Three Approaches to Harmony in 13-TET",
        page=53,
        function=f,
    )


def xen13_grady_sophia(f):
    numbers = [1, 3, 5, 7, 9]
    root = 1 * 3
    dekany1 = {
        reduce(F(math.prod(x), root)): "*".join(map(str, x))
        for x in combinations(numbers, 2)
    }
    dekany2 = {
        reduce(F(math.prod(x), root)): "*".join(map(str, x))
        for x in combinations(numbers, 3)
    }

    double_dekany = {k: [v] for k, v in dekany1.items()}
    for k, v in dekany2.items():
        if k in dekany1:
            double_dekany[k].append(v)
        else:
            double_dekany[k] = [v]

    tones = [T.from_fraction(k, comment=", ".join(v)) for k, v in double_dekany.items()]
    assert len(tones) == 14
    return build_scl(
        description="Sophia, 1.3.5.7.9 Double Dexany",
        tones=tones,
        title="The Discovery of a 14-Tone Scale",
        page=88,
        function=f,
    )


def xen13_grady_19_1(f):
    labels = [
        (5, 9),
        (3, 7, 9),
        #
        (1, 3),
        (3, 9, 15),
        (3, 5, 7),
        #
        (3, 9),
        (1, 7),
        (3, 5, 7, 9),
        #
        (3, 5),
        (7, 9),
        #
        (1,),
        (3, 5, 9),
        (5, 7),
        #
        (1, 9),
        (7, F(1, 3)),
        (5, 7, 9),
        #
        (1, 5),
        (3, 7),
        (3, 7, 9, 15),
        #
        (5, 9),
        (3, 7, 9),
    ]
    comments = {
        (7, F(1, 3)): " (or 3*9*11)",
        (3, 7, 9, 15): " (or 7*9*11)",
    }
    tones = [
        T.from_fraction(
            reduce(F(math.prod(x))), comment="*".join(map(str, x)) + comments.get(x, "")
        )
        for x in sorted(set(labels))
    ]
    assert len(tones) == 19
    return build_scl(
        description="19 tone scale 1",
        tones=tones,
        title="The Discovery of a 14-Tone Scale",
        page=89,
        function=f,
    )


def xen13_grady_19_2(f):
    labels = [
        (1, 11),
        (9, 11, 15),
        #
        (3,),
        (9, 11),
        (7, 15),
        #
        (3, 9),
        (1, 7),
        (7, 9, 15),
        #
        (1, 15),
        (7, 9),
        #
        (1,),
        (9, 15),
        (5, 7),
        #
        (9,),
        (3, 9, 11),
        (7, 11),
        #
        (7, 9, 11, 15),
        (1, 11, 15),
        (7, 9, 11),
    ]
    comments = {(3, 9): " (or 3*7*11*15)"}
    tones = [
        T.from_fraction(
            reduce(F(math.prod(x))), comment="*".join(map(str, x)) + comments.get(x, "")
        )
        for x in sorted(set(labels))
    ]
    assert len(tones) == 19
    return build_scl(
        description="19 tone scale 2",
        tones=tones,
        title="The Discovery of a 14-Tone Scale",
        page=89,
        function=f,
    )


def xen13_morrison_7_steps_per_11_over_5(f):
    period = 1200 * log2(11 / 5)
    tones = [T(i * period / 7, period=period) for i in range(1, 7)] + [
        T(11, 5, period=period)
    ]
    assert len(tones) == 7
    return build_scl(
        description="7 steps per 11:5",
        tones=tones,
        title="A Graphical Technique for Finding Equally-Tempered Scales by Their Harmonic Resources",
        page=94,
        function=f,
    )


def nth_root_of_k(n, k):
    r = k ** (1 / n)
    period = 1200 * log2(k)
    tones = [T(i * period / n, period=period) for i in range(1, n)] + [
        T(k, 1, period=period)
    ]
    assert len(tones) == n
    return tones


def xen14_mclaren_nonoctave_31_5(f):
    tones = nth_root_of_k(31, 5)
    return build_scl(
        description="31st root of 5 non-octave scale",
        tones=tones,
        title="The Uses and Characteristics of Non-Octave Scales",
        page=13,
        function=f,
    )


def xen14_mclaren_nonoctave_13_3(f):
    tones = nth_root_of_k(13, 3)
    return build_scl(
        description="Pierce-Bohlen scale, 13th root of 3",
        tones=tones,
        title="The Uses and Characteristics of Non-Octave Scales",
        page=13,
        function=f,
    )


def xen14_mclaren_nonoctave_25_5(f):
    tones = nth_root_of_k(25, 5)
    return build_scl(
        description="Stockhausen's Studie II 25th root of 5 non-octave scale",
        tones=tones,
        title="The Uses and Characteristics of Non-Octave Scales",
        page=14,
        function=f,
    )


def xen14_mclaren_nonoctave_37_31(f):
    tones = nth_root_of_k(37, 31)
    return build_scl(
        description="37th root of 31 non-octave scale",
        tones=tones,
        title="The Uses and Characteristics of Non-Octave Scales",
        page=14,
        function=f,
    )


def xen14_mclaren_nonoctave_e_pi(f):
    step = 1200 * log2(math.pi ** (1 / (math.e**math.pi)))
    tones = [T(step)]
    return build_scl(
        description="(e to the pi)th root of pi non-octave scale",
        tones=tones,
        title="The Uses and Characteristics of Non-Octave Scales",
        page=14,
        function=f,
    )


def xen14_mclaren_nonoctave_30_3(f):
    tones = nth_root_of_k(30, 3)
    return build_scl(
        description="Erv Wilson's 30th root of 3 non-octave scale",
        tones=tones,
        title="The Uses and Characteristics of Non-Octave Scales",
        page=16,
        function=f,
    )


def xen14_mclaren_nonoctave_21_17(f):
    tones = nth_root_of_k(21, 17)
    return build_scl(
        description="21st root of 17 non-octave scale",
        tones=tones,
        title="The Uses and Characteristics of Non-Octave Scales",
        page=16,
        function=f,
    )


def xen14_mclaren_nonoctave_44_5(f):
    tones = nth_root_of_k(44, 5)
    return build_scl(
        description="Erv Wilson's 44th root of 5 non-octave scale",
        tones=tones,
        title="The Uses and Characteristics of Non-Octave Scales",
        page=21,
        function=f,
    )


PHI = (1 + 5**0.5) / 2


def xen14_mclaren_nonoctave_phi_9(f):
    period = 1200 * log2(PHI)
    N = 9
    step = period / N
    tones = [T(i * step) for i in range(1, N + 1)]
    assert len(tones) == N
    return build_scl(
        description="Walter O'Connell's 9 parts of Golden Section",
        tones=tones,
        title="The Uses and Characteristics of Non-Octave Scales",
        page=22,
        function=f,
    )


# Duplicates xen15_oconnell_golden_section_25
#
# def xen14_mclaren_nonoctave_phi_25(f):
#     period = 1200 * log2(PHI)
#     N = 25
#     step = period / N
#     tones = [T(i * step) for i in range(1, N + 1)]
#     assert len(tones) == N
#     return build_scl(
#         description="Walter O'Connell's 25 parts of Golden Section",
#         tones=tones,
#         title="The Uses and Characteristics of Non-Octave Scales",
#         page=22,
#         function=f,
#     )


def xen14_mclaren_nonoctave_12_3(f):
    tones = nth_root_of_k(12, 3)
    return build_scl(
        description="Enrique Moreno's 12th root of 3 non-octave scale",
        tones=tones,
        title="The Uses and Characteristics of Non-Octave Scales",
        page=22,
        function=f,
    )


def add_nonoctave():
    roots = [
        (14, 3),
        (15, 3),
        (16, 3),
        (17, 3),
        (38, 7),
    ]
    for n, k in roots:
        name = f"xen14_mclaren_nonoctave_{n}_{k}"

        def build(f, n=n, k=k):
            tones = nth_root_of_k(n, k)
            return build_scl(
                description=f"{n}th root of {k} non-octave scale",
                tones=tones,
                title="The Uses and Characteristics of Non-Octave Scales",
                page=22,
                function=f,
            )

        globals()[name] = build


add_nonoctave()


def xen14_mclaren_nonoctave_phi_5(f):
    period = 1200 * log2(PHI)
    N = 5
    step = period / N
    tones = [T(i * step) for i in range(1, N + 1)]
    assert len(tones) == N
    return build_scl(
        description="John McBryde's 5th root of phi",
        tones=tones,
        title="The Uses and Characteristics of Non-Octave Scales",
        page=22,
        function=f,
    )


def xen14_mclaren_nonoctave_phi_7(f):
    period = 1200 * log2(PHI)
    N = 7
    step = period / N
    tones = [T(i * step) for i in range(1, N + 1)]
    assert len(tones) == N
    return build_scl(
        description="John McBryde's 7th root of phi",
        tones=tones,
        title="The Uses and Characteristics of Non-Octave Scales",
        page=22,
        function=f,
    )


def xen14_darreg_telephone(f):
    period = 1473.96
    tones = [
        T(172.43, period=period),
        T(347.63, period=period),
        T(519.64, period=period),
        T(953.50, period=period),
        T(1126.43, period=period),
        T(1300.01, period=period),
        T(1473.96, period=period),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Notes used for two-tone signalling on push-button telephones",
        tones=tones,
        title="Xenharmonic Bulletin No. 12",
        page=76,
        function=f,
    )


def xen14_darreg_telephone_14(f):
    period = 1215.0
    step = period / 14
    tones = [T(round(i * step, 2), period=period) for i in range(1, 15)]
    assert len(tones) == 14
    return build_scl(
        description="Streched 14-tone equal temperament approximating push-button telephone tones",
        tones=tones,
        title="Xenharmonic Bulletin No. 12",
        page=76,
        function=f,
    )


def xen14_polansky_horn(f):
    harmonics = range(1, 18)
    series_on_f = [(x,) for x in harmonics]
    series_on_c = [(3, x) for x in harmonics]
    series_on_a = [(5, x) for x in harmonics]
    ratios = defaultdict(lambda: [])
    for x in series_on_f + series_on_c + series_on_a:
        ratios[reduce(F(math.prod(x)))].append("*".join(map(str, x)))
    tones = [T.from_fraction(k, comment=", ".join(v)) for k, v in ratios.items()]
    assert len(tones) == 21
    return build_scl(
        description="Scale from 'Horn'",
        tones=tones,
        title="Horn",
        page=83,
        comments=["All pitches reduced to one octave. See the score for octaves used."],
        function=f,
    )


def xen15_oconnell_golden_section_25(f):
    period = 1200 * log2(PHI)
    N = 25
    step = period / N
    tones = [T(i * step) for i in range(1, N + 1)]
    assert len(tones) == N
    return build_scl(
        description="25 parts of the Golden Section",
        tones=tones,
        title="The Tonality of the Golden Section",
        page=8,
        function=f,
    )


def xen15_oconnell_golden_section_25_pure(f):
    period = 1200 * log2(PHI)
    N = 25
    tones = [T((i * 1200.0) % period) for i in range(1, N)] + [T(period)]
    assert len(tones) == N
    return build_scl(
        description="25 pure octaves reduced by phi",
        tones=tones,
        title="The Tonality of the Golden Section",
        page=8,
        function=f,
    )


def xen15_oconnell_golden_section_7(f):
    step = 1200 * log2(PHI) / 25
    steps = [4, 3, 4, 3, 4, 3, 4]
    tones = [T(x * step, comment=x) for x in csum(steps)]
    assert len(tones) == 7
    return build_scl(
        description="7-note scale in 25 parts of Golden Section",
        tones=tones,
        title="The Tonality of the Golden Section",
        page=9,
        function=f,
    )


def xen15_oconnell_golden_section_9(f):
    step = 1200 * log2(PHI) / 25
    steps = [3, 3, 2, 3, 3, 3, 2, 3, 3]
    tones = [T(x * step, comment=x) for x in csum(steps)]
    assert len(tones) == 9
    return build_scl(
        description="9-note scale in 25 parts of Golden Section",
        tones=tones,
        title="The Tonality of the Golden Section",
        page=9,
        function=f,
    )


def xen15_oconnell_golden_section_11(f):
    step = 1200 * log2(PHI) / 25
    steps = [2, 3, 2, 2, 2, 3, 2, 2, 2, 3, 2]
    tones = [T(x * step, comment=x) for x in csum(steps)]
    assert len(tones) == 11
    return build_scl(
        description="11-note scale in 25 parts of Golden Section",
        tones=tones,
        title="The Tonality of the Golden Section",
        page=9,
        function=f,
    )


def xen15_oconnell_golden_section_14(f):
    step = 1200 * log2(PHI) / 25
    steps = [2, 2, 1, 2, 2, 2, 2, 1, 2, 2, 2, 2, 1, 2]
    tones = [T(x * step, comment=x) for x in csum(steps)]
    assert len(tones) == 14
    return build_scl(
        description="14-note scale in 25 parts of Golden Section",
        tones=tones,
        title="The Tonality of the Golden Section",
        page=9,
        function=f,
    )


def xen15_oconnell_golden_section_18(f):
    period = 1200 * log2(PHI)
    N = 18
    step = period / N
    tones = [T(i * step) for i in range(1, N + 1)]
    assert len(tones) == N
    return build_scl(
        description="18 parts of the Golden Section",
        tones=tones,
        title="The Tonality of the Golden Section",
        page=16,
        function=f,
    )


def xen15_mclaren_e(f):
    period = 1731.234
    tones = [
        T(4.29, period=period),
        T(11.66, period=period),
        T(31.7086, period=period),
        T(86.193, period=period),
        T(234.297, period=period),
        T(636.885, period=period),
        T(1731.234, period=period),
    ]
    assert len(tones) == 7
    return build_scl(
        description="e scale",
        tones=tones,
        title="The Uses and Characteristics of Non-Just Non-Equal-Tempered Scales",
        page=29,
        function=f,
    )


def xen15_mclaren_pi(f):
    period = 1981.795
    tones = [
        T(2.061, period=period),
        T(6.476, period=period),
        T(20.34, period=period),
        T(63.915, period=period),
        T(200.79, period=period),
        T(630.825, period=period),
        T(1981.795, period=period),
    ]
    assert len(tones) == 7
    return build_scl(
        description="pi scale",
        tones=tones,
        title="The Uses and Characteristics of Non-Just Non-Equal-Tempered Scales",
        page=29,
        function=f,
    )


def xen15_mclaren_root_3(f):
    period = 950.9775
    tones = [
        T(11.74, period=period),
        T(20.335, period=period),
        T(35.221, period=period),
        T(61.005, period=period),
        T(105.664, period=period),
        T(183.015, period=period),
        T(316.992, period=period),
        T(549.047, period=period),
        T(950.9775, period=period),
    ]
    assert len(tones) == 9
    return build_scl(
        description="Square root of 3 scale",
        tones=tones,
        title="The Uses and Characteristics of Non-Just Non-Equal-Tempered Scales",
        page=30,
        function=f,
    )


def xen15_mclaren_root_5(f):
    period = 1393.15
    tones = [
        T(4.98, period=period),
        T(11.14, period=period),
        T(24.92, period=period),
        T(55.72, period=period),
        T(124.6, period=period),
        T(278.63, period=period),
        T(623.03, period=period),
        T(1393.15, period=period),
    ]
    assert len(tones) == 8
    return build_scl(
        description="Square root of 5 scale",
        tones=tones,
        title="The Uses and Characteristics of Non-Just Non-Equal-Tempered Scales",
        page=30,
        function=f,
    )


def xen15_mclaren_root_7(f):
    period = 1684.412
    tones = [
        T(4.9107, period=period),
        T(12.992, period=period),
        T(34.375, period=period),
        T(90.949, period=period),
        T(240.628, period=period),
        T(636.643, period=period),
        T(1684.412, period=period),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Square root of 7 scale",
        tones=tones,
        title="The Uses and Characteristics of Non-Just Non-Equal-Tempered Scales",
        page=30,
        function=f,
    )


def xen15_mclaren_integrated(f):
    period = 950.9775
    tones = [
        T(13.442, period=period),
        T(48.466, period=period),
        T(160.744, period=period),
        T(425.290, period=period),
        T(950.9775, period=period),
    ]
    assert len(tones) == 5
    return build_scl(
        description="Integrated non-self-similar scale #1",
        tones=tones,
        title="The Uses and Characteristics of Non-Just Non-Equal-Tempered Scales",
        page=31,
        function=f,
    )


def xen15_mclaren_metal_bar(f):
    tones = [
        T(1200.0),
        T(555.8),
        T(520.8),
        T(191.0),
        T(885.8),
        T(264.2),
        T(759.7),
        T(1193.1),
        T(378.2),
        T(724.7),
        T(1039.7),
        T(128.4),
        T(394.9),
        T(642.3),
    ]
    assert len(tones) == 14
    return build_scl(
        description="Metal bar scale",
        tones=tones,
        title="The Uses and Characteristics of Non-Just Non-Equal-Tempered Scales",
        page=32,
        function=f,
    )


def xen15_leedy_mixolydian(f):
    tones = [
        T(9, 8),
        T(5, 4),
        T(4, 3),
        T(3, 2),
        T(5, 3),
        T(7, 4),
        T(2, 1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Just mixolydian",
        tones=tones,
        title="Giving Number a Voice",
        page=59,
        function=f,
    )


TRIADIC_DIAMOND_TITLE = "The Triadic Diamond, the Triadic Reversed Diamond, and their Constituent Tetrachords when D=3/2"


def add_triadic_diamond(M):
    D = F(3, 2)
    triadic_diamond = [
        M / D,
        M,
        2 / D,
        F(1, 1),
        D,
        2 / M,
        D / M,
    ]
    triadic_diamond_ratios = sorted(reduce(x) for x in triadic_diamond)

    # Take upper tetrachord
    assert triadic_diamond_ratios[3] == D
    tetrachord_ratios = [x / D for x in triadic_diamond_ratios[4:]]
    assert tetrachord_ratios[-1] == F(4, 3)

    triadic_diamond_name = (
        f"xen15_chalmers_triadic_diamond_{M.numerator}_{M.denominator}"
    )

    def build_triadic_diamond(f, M=M, ratios=triadic_diamond_ratios):
        tones = [T.from_fraction(x) for x in ratios]
        return build_scl(
            description=f"Triadic diamond for M={M}, D=3/2",
            tones=tones,
            title=TRIADIC_DIAMOND_TITLE,
            page=64,
            function=f,
        )

    triadic_diamond_tetrachord_name = (
        f"xen15_chalmers_triadic_diamond_{M.numerator}_{M.denominator}_tetrachord"
    )

    def build_triadic_diamond_tetrachord(f, M=M, ratios=tetrachord_ratios):
        tones = [T.from_fraction(x) for x in ratios]
        steps = [y / x for x, y in zip([1] + ratios, ratios)]
        steps_label = " * ".join(map(str, steps))
        return build_scl(
            description=f"Upper tetrachord {steps_label} of triadic diamond for M={M}, D=3/2",
            tones=tones,
            title=TRIADIC_DIAMOND_TITLE,
            page=64,
            function=f,
        )

    globals()[triadic_diamond_name] = build_triadic_diamond
    globals()[triadic_diamond_tetrachord_name] = build_triadic_diamond_tetrachord


def add_triadic_diamonds():
    Ms = [
        F(5, 4),
        F(7, 6),
        F(11, 9),
        F(16, 13),
        F(14, 11),
        F(15, 13),
        F(13, 11),
        F(17, 14),
        F(19, 16),
        F(17, 13),
        F(8, 7),
        F(23, 20),
        F(23, 18),
        F(23, 19),
        F(81, 64),
        F(8192, 6561),
        F(40, 33),
        F(26, 21),
        F(56, 45),
        F(64, 51),
        F(34, 27),
        F(32, 25),
        F(22, 17),
        F(35, 27),
    ]
    assert len(Ms) == 24

    for M in Ms:
        add_triadic_diamond(M)


add_triadic_diamonds()


def add_triadic_reversed_diamond(M, i):
    D = F(3, 2)
    triadic_reversed_diamond = [
        M,
        D * M,
        2 / D,
        F(1, 1),
        D,
        (2 / D) / M,
        2 / M,
    ]
    triadic_reversed_diamond_ratios = sorted(
        reduce(x) for x in triadic_reversed_diamond
    )

    # Take upper tetrachord
    assert triadic_reversed_diamond_ratios[3] == D
    tetrachord_ratios = [x / D for x in triadic_reversed_diamond_ratios[4:]]
    assert tetrachord_ratios[-1] == F(4, 3)

    triadic_reversed_diamond_name = (
        f"xen15_chalmers_triadic_reversed_diamond_{M.numerator}_{M.denominator}"
    )

    page = 65 if i < 20 else 66

    def build_triadic_reversed_diamond(
        f, M=M, ratios=triadic_reversed_diamond_ratios, page=page
    ):
        tones = [T.from_fraction(x) for x in ratios]
        return build_scl(
            description=f"Triadic reversed diamond for M={M}, D=3/2",
            tones=tones,
            title=TRIADIC_DIAMOND_TITLE,
            page=page,
            function=f,
        )

    triadic_reversed_diamond_tetrachord_name = f"xen15_chalmers_triadic_reversed_diamond_{M.numerator}_{M.denominator}_tetrachord"

    def build_triadic_reversed_diamond_tetrachord(
        f, M=M, ratios=tetrachord_ratios, page=page
    ):
        tones = [T.from_fraction(x) for x in ratios]
        steps = [y / x for x, y in zip([1] + ratios, ratios)]
        steps_label = " * ".join(map(str, steps))
        return build_scl(
            description=f"Tetrachord {steps_label} of triadic reversed diamond for M={M}, D=3/2",
            tones=tones,
            title=TRIADIC_DIAMOND_TITLE,
            page=page,
            function=f,
        )

    globals()[triadic_reversed_diamond_name] = build_triadic_reversed_diamond
    globals()[triadic_reversed_diamond_tetrachord_name] = (
        build_triadic_reversed_diamond_tetrachord
    )


def add_triadic_reversed_diamonds():
    Ms = [
        F(7, 6),
        F(32, 27),
        F(6, 5),
        F(40, 33),
        F(11, 9),
        F(16, 13),
        F(26, 21),
        F(56, 45),
        F(8192, 6561),
        F(5, 4),
        F(64, 51),
        F(34, 27),
        F(81, 64),
        F(14, 11),
        F(32, 25),
        F(9, 7),
        F(22, 17),
        F(35, 27),
        F(13, 10),
        F(30, 23),
        #
        F(27, 22),
        F(39, 32),
        F(33, 28),
        F(15, 13),
        F(13, 11),
        F(33, 26),
        F(17, 14),
        F(21, 17),
        F(19, 16),
        F(24, 19),
        F(17, 13),
        F(39, 34),
        F(21, 16),
        F(23, 30),
        F(23, 18),
        F(27, 23),
        F(23, 19),
        F(57, 46),
    ]
    assert len(Ms) == 38

    for i, M in enumerate(Ms):
        add_triadic_reversed_diamond(M, i)


add_triadic_reversed_diamonds()


def xen15_chalmers_stretched_14_1(f):
    period = 1213.5142
    step = period / 14
    tones = [T(round(i * step, 2), period=period) for i in range(1, 15)]
    assert len(tones) == 14
    return build_scl(
        description="Least-Squares Stretched 14-Tone Equal Temperament, Table 4",
        tones=tones,
        title="The TOUCH-TONE(R) Signal Pitches as Subsets of Stretched 14-Tone ET's",
        page=78,
        function=f,
    )


def xen15_chalmers_stretched_14_2(f):
    period = 1209.5150
    step = period / 14
    tones = [T(round(i * step, 2), period=round(period, 2)) for i in range(1, 15)]
    assert len(tones) == 14
    return build_scl(
        description="Least-Squares Stretched 14-Tone Equal Temperament, Table 6",
        tones=tones,
        title="The TOUCH-TONE(R) Signal Pitches as Subsets of Stretched 14-Tone ET's",
        page=80,
        function=f,
    )


def xen15_gilson_pythagorean_diatonic(f):
    x = F(4, 3)
    ratios = [x]
    for i in range(6):
        x = reduce(x * 3)
        ratios.append(x)
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Pythagorean Intonation Diatonic Scale (PIDS)",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=102,
        function=f,
    )


def millioctaves(x):
    return f"{round(1000 * log2(x)):4} moc"


def xen15_gilson_pythagorean_chromatic(f):
    x = F(4, 3)
    ratios = [x]
    for i in range(11):
        x = reduce(x * 3)
        ratios.append(x)
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 12
    return build_scl(
        description="Pythagorean Intonation Chromatic Scale (PICS)",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=102,
        function=f,
    )


def xen15_gilson_just_diatonic(f):
    ratios = [
        F(9, 8),
        F(5, 4),
        F(4, 3),
        F(3, 2),
        F(5, 3),
        F(15, 8),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Just Intonation Diatonic Scale (JIDS)",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=105,
        function=f,
    )


def xen15_gilson_just_chromatic(f):
    ratios = [
        F(25, 24),
        F(9, 8),
        F(75, 64),
        F(5, 4),
        F(4, 3),
        F(45, 32),
        F(3, 2),
        F(25, 16),
        F(5, 3),
        F(225, 128),
        F(15, 8),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 12
    return build_scl(
        description="Just Intonation Chromatic Scale (JICS)",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=105,
        function=f,
    )


def xen15_gilson_pythagorean_pentatonic(f):
    x = F(4, 3)
    ratios = [x]
    for i in range(4):
        x = reduce(x * 3)
        ratios.append(x)
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 5
    return build_scl(
        description="Pythagorean Intonation Pentatonic Scale (PIPS)",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=114,
        function=f,
    )


def xen15_gilson_just_pentatonic(f):
    ratios = [
        F(9, 8),
        F(4, 3),
        F(3, 2),
        F(5, 3),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 5
    return build_scl(
        description="Just Intonation Pentatonic Scale (JIPS)",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=114,
        function=f,
    )


def add_generalized_pythagorean_scales():
    scales = {
        F(3, 2): [5, 12, 41, 53],
        F(5, 4): [28, 59],
        F(7, 4): [5, 26],
        F(11, 8): [11, 13, 24, 37],
        F(13, 8): [3, 7, 10],
        F(15, 8): [10, 11, 32, 43],
        F(18, 17): [12],
    }
    for g, ns in scales.items():
        for n in ns:
            name = f"xen15_gilson_generalized_pythagorean_{g.numerator}_{g.denominator}_{n}"

            def build(f, g=g, n=n):
                ratios = stack([1] + (n - 1) * [g])
                tones = [
                    T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)
                ]
                assert len(tones) == n
                nearest_octave_number = round(log2(g**n))
                label = f"{nearest_octave_number}+{n - nearest_octave_number}"
                return build_scl(
                    description=f"Generalized Pythagorean Scale, {g} stacked {n}={label} times",
                    tones=tones,
                    title="A Numerical Theory of Scale Invention",
                    page=118,
                    function=f,
                )

            globals()[name] = build


add_generalized_pythagorean_scales()


def xen15_gilson_generalized_just_1(f):
    ratios = [
        F(75, 64),
        F(6, 5),
        F(5, 4),
        F(32, 25),
        F(3, 2),
        F(25, 16),
        F(8, 5),
        F(15, 8),
        F(48, 25),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 10
    return build_scl(
        description="Ten note just scale, two rows and five columns of chart on p.119",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=120,
        function=f,
    )


def xen15_gilson_generalized_just_2(f):
    ratios = [
        F(8, 7),
        F(6, 5),
        F(5, 4),
        F(10, 7),
        F(3, 2),
        F(25, 16),
        F(25, 14),
        F(15, 8),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 9
    return build_scl(
        description="Scale based on product (25/24)**2 * (21/20)**3 * 16/15 * (8/7)**3 = 2",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=121,
        function=f,
    )


def xen15_gilson_generalized_just_3(f):
    ratios = [
        F(15, 14),
        F(8, 7),
        F(6, 5),
        F(9, 7),
        F(10, 7),
        F(3, 2),
        F(8, 5),
        F(12, 7),
        F(9, 5),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 10
    return build_scl(
        description="Scale based on product (21/20)**3 * (16/15)**2 * (15/14)**3 * (10/9)**2 = 2",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=121,
        function=f,
    )


def xen15_gilson_archytas_diatonic(f):
    ratios = [
        F(28, 27),
        F(32, 27),
        F(4, 3),
        F(3, 2),
        F(14, 9),
        F(16, 9),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Archytas' Diatonic (or Ptolemy's Diatonic Tonaion)",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=131,
        function=f,
    )


def xen15_gilson_aristoxenus_diatonic_malakon(f):
    ratios = [
        F(20, 19),
        F(8, 7),
        F(4, 3),
        F(3, 2),
        F(30, 19),
        F(12, 7),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Aristoxenus' Diatonic Malakon",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=131,
        function=f,
    )


def xen15_gilson_aristoxenus_diatonic_syntonon(f):
    ratios = [
        F(20, 19),
        F(20, 17),
        F(4, 3),
        F(3, 2),
        F(30, 19),
        F(30, 17),
        F(2),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Aristoxenus' Diatonic Syntonon",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=131,
        function=f,
    )


def xen15_gilson_eratosthenes_diatonic(f):
    ratios = [
        F(256, 243),
        F(32, 27),
        F(4, 3),
        F(3, 2),
        F(128, 81),
        F(16, 9),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Eratosthenes' Diatonic (or Ptolemy's Diatonic Ditonaion)",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=131,
        function=f,
    )


def xen15_gilson_didymus_diatonic(f):
    ratios = [
        F(16, 15),
        F(32, 27),
        F(4, 3),
        F(3, 2),
        F(8, 5),
        F(16, 9),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Didymus' Diatonic",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=131,
        function=f,
    )


def xen15_gilson_ptolemy_diatonic_malakon(f):
    ratios = [
        F(21, 20),
        F(7, 6),
        F(4, 3),
        F(3, 2),
        F(63, 40),
        F(7, 4),
        F(2, 1),
    ]
    tones = [
        T.from_fraction(
            x,
            comment=millioctaves(x)
            + ("; originally printed as 14/9" if x == F(63, 40) else ""),
        )
        for x in sorted(ratios)
    ]
    assert len(tones) == 7
    return build_scl(
        description="Ptolemy's Diatonic Malakon",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=131,
        function=f,
    )


def xen15_gilson_ptolemy_diatonic_syntonon(f):
    ratios = [
        F(16, 15),
        F(6, 5),
        F(4, 3),
        F(3, 2),
        F(8, 5),
        F(9, 5),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Ptolemy's Diatonic Syntonon",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=131,
        function=f,
    )


def xen15_gilson_ptolemy_diatonic_hemiolon(f):
    ratios = [
        F(12, 11),
        F(6, 5),
        F(4, 3),
        F(3, 2),
        F(18, 11),
        F(9, 5),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Ptolemy's Diatonic Hemiolon",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=132,
        function=f,
    )


def xen15_gilson_archytas_chromatic(f):
    ratios = [
        F(28, 27),
        F(9, 8),
        F(4, 3),
        F(3, 2),
        F(14, 9),
        F(27, 16),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Archytas' Chromatic",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=132,
        function=f,
    )


def xen15_gilson_aristoxenus_chromatic_malakon(f):
    ratios = [
        F(30, 29),
        F(15, 14),
        F(4, 3),
        F(3, 2),
        F(45, 29),
        F(45, 28),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Aristoxenus' Chromatic Malakon",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=132,
        function=f,
    )


def xen15_gilson_aristoxenus_chromatic_hemiolon(f):
    ratios = [
        F(80, 77),
        F(40, 37),
        F(4, 3),
        F(3, 2),
        F(120, 77),
        F(60, 37),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Aristoxenus' Chromatic Hemiolon",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=132,
        function=f,
    )


def xen15_gilson_aristoxenus_chromatic_tonikon(f):
    ratios = [
        F(20, 19),
        F(10, 9),
        F(4, 3),
        F(3, 2),
        F(30, 19),
        F(5, 3),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Aristoxenus' Chromatic Tonikon (or Eratosthenes' Chromatic)",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=132,
        function=f,
    )


def xen15_gilson_didymus_chromatic(f):
    ratios = [
        F(16, 15),
        F(10, 9),
        F(4, 3),
        F(3, 2),
        F(8, 5),
        F(5, 3),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Didymus Chromatic",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=132,
        function=f,
    )


def xen15_gilson_ptolemy_chromatic_malakon(f):
    ratios = [
        F(28, 27),
        F(10, 9),
        F(4, 3),
        F(3, 2),
        F(14, 9),
        F(5, 3),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Ptolemy's Chromatic Malakon",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=132,
        function=f,
    )


def xen15_gilson_ptolemy_chromatic_syntonon(f):
    ratios = [
        F(22, 21),
        F(8, 7),
        F(4, 3),
        F(3, 2),
        F(11, 7),
        F(12, 7),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Ptolemy's Chromatic Syntonon",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=132,
        function=f,
    )


def xen15_gilson_archytas_enharmonic(f):
    ratios = [
        F(28, 27),
        F(16, 15),
        F(4, 3),
        F(3, 2),
        F(14, 9),
        F(8, 5),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Archytas' Enharmonic",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=132,
        function=f,
    )


def xen15_gilson_aristoxenus_enharmonic(f):
    ratios = [
        F(40, 39),
        F(20, 19),
        F(4, 3),
        F(3, 2),
        F(20, 13),
        F(30, 19),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Aristoxenus' Enharmonic",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=132,
        function=f,
    )


def xen15_gilson_eratosthenes_enharmonic(f):
    ratios = [
        F(46, 45),
        F(16, 15),
        F(4, 3),
        F(3, 2),
        F(23, 15),
        F(8, 5),
        F(2, 1),
    ]
    tones = [T.from_fraction(x, comment=millioctaves(x)) for x in sorted(ratios)]
    assert len(tones) == 7
    return build_scl(
        description="Eratosthenes' Enharmonic",
        tones=tones,
        title="A Numerical Theory of Scale Invention",
        page=132,
        function=f,
    )


def xen16_mclaren_carlos_alpha(f):
    tones = [
        T(78.0),
    ]
    assert len(tones) == 1
    return build_scl(
        description="Wendy Carlos' Alpha scale",
        tones=tones,
        title="More About Non-Octave Scales",
        page=46,
        function=f,
    )


def xen16_mclaren_carlos_beta(f):
    tones = [
        T(63.8),
    ]
    assert len(tones) == 1
    return build_scl(
        description="Wendy Carlos' Beta scale",
        tones=tones,
        title="More About Non-Octave Scales",
        page=47,
        function=f,
    )


def xen16_mclaren_carlos_gamma(f):
    tones = [
        T(35.1),
    ]
    assert len(tones) == 1
    return build_scl(
        description="Wendy Carlos' Gamma scale",
        tones=tones,
        title="More About Non-Octave Scales",
        page=47,
        function=f,
    )


def add_more_nonoctave():
    # Commented roots are in Mclaren's XH14 nonoctave paper too
    roots = [
        (20, 3, 47),
        (24, 3, 48),
        # (30, 3, 48),
        (29, 3, 48),
        (34, 3, 48),
        (16, 5, 49),
        (20, 5, 49),
        (24, 5, 49),
        (32, 5, 49),
        (36, 5, 50),
        (40, 5, 50),
        (43, 5, 50),
        # (44, 5, 50),
        (47, 5, 50),
        (52, 5, 50),
        (59, 5, 51),
        (60, 5, 51),
        (64, 5, 51),
        (67, 5, 51),
        (71, 5, 51),
        (79, 5, 51),
        (87, 5, 51),
        (88, 5, 51),
        (24, 7, 51),
        # (38, 7, 51),
        (53, 7, 51),
        (58, 7, 52),
        (63, 7, 52),
        (67, 7, 52),
        (71, 7, 52),
        (72, 7, 52),
        (77, 7, 52),
        (53, 11, 52),
        (54, 11, 52),
        (65, 11, 52),
        (77, 11, 52),
        (89, 11, 52),
        (88, 11, 52),
        (95, 11, 53),
    ]
    for n, k, page in roots:
        name = f"xen16_mclaren_nonoctave_{n}_{k}"

        def build(f, n=n, k=k, page=page):
            tones = nth_root_of_k(n, k)
            steps = round(1 / log2(k ** (1 / n)), 4)
            ending = {"2": "nd", "3": "rd"}.get(str(n)[-1], "th")
            desc = f"{n}{ending} root of {k}, {steps} tones/octave"
            return build_scl(
                description=desc,
                tones=tones,
                title="More About Non-Octave Scales",
                page=page,
                function=f,
            )

        globals()[name] = build


add_more_nonoctave()


def xen16_grady_centaur(f):
    tones = [
        T(21, 20),
        T(9, 8),
        T(7, 6),
        T(5, 4),
        T(4, 3),
        T(7, 5),
        T(3, 2),
        T(14, 9),
        T(5, 3),
        T(7, 4),
        T(15, 8),
        T(2, 1),
    ]
    assert len(tones) == 12
    return build_scl(
        description="Centaur",
        tones=tones,
        title="CENTAUR - A 7-Limit 12 Tone Tuning",
        page=93,
        function=f,
    )


def xen16_burt_drones_all(f):
    labels = [
        (70, 81, -253),
        (72, 81, -204),
        (81, 81, 0),
        (81, 80, 22),
        (98, 81, 330),
        (100, 81, 365),
        (81, 64, 408),
        (81, 63, 435),
        (126, 81, 765),
        (128, 81, 792),
        (81, 50, 835),
        (81, 49, 870),
        (160, 81, 1178),
        (162, 81, 1200),
        (81, 36, 1404),
        (81, 35, 1453),
    ]
    assert len(labels) == 16
    ratios = defaultdict(lambda: [])
    for numerator, denominator, cents in labels:
        assert round(1200 * log2(numerator / denominator)) == cents
        ratio = reduce(F(numerator, denominator))
        ratios[ratio].append(f"{numerator}/{denominator}")
    tones = [
        T.from_fraction(k, comment=", ".join(map(str, v))) for k, v in ratios.items()
    ]
    assert len(tones) == 15
    return build_scl(
        description="All notes from Drones 1994 #2",
        tones=tones,
        title="Drones 1994 #2: Old Commas Inverted and Revisited",
        page=99,
        function=f,
    )


def add_burt_drones():
    scales = [
        [
            (70, 81),
            (72, 81),
            (81, 81),
            (81, 80),
            (98, 81),
            (100, 81),
            (81, 64),
            (81, 63),
            (81, 50),
            (81, 49),
            (81, 36),
            (81, 35),
        ],
        [
            (81, 81),
            (81, 80),
            (81, 64),
            (81, 63),
            (126, 81),
            (128, 81),
            (81, 50),
            (81, 49),
            (160, 81),
            (162, 81),
            (81, 36),
            (81, 35),
        ],
        [
            (70, 81),
            (72, 81),
            (81, 81),
            (81, 80),
            (81, 64),
            (81, 63),
            (126, 81),
            (128, 81),
            (81, 50),
            (81, 49),
            (81, 36),
            (81, 35),
        ],
        [
            (81, 81),
            (81, 80),
            (98, 81),
            (100, 81),
            (81, 64),
            (81, 63),
            (81, 50),
            (81, 49),
            (160, 81),
            (162, 81),
            (81, 36),
            (81, 35),
        ],
        [
            (70, 81),
            (72, 81),
            (81, 81),
            (81, 80),
            (98, 81),
            (100, 81),
            (81, 64),
            (81, 63),
            (126, 81),
            (128, 81),
            (160, 81),
            (162, 81),
        ],
        [
            (70, 81),
            (72, 81),
            (98, 81),
            (100, 81),
            (126, 81),
            (128, 81),
            (81, 50),
            (81, 49),
            (160, 81),
            (162, 81),
            (81, 36),
            (81, 35),
        ],
        [
            (70, 81),
            (72, 81),
            (81, 81),
            (81, 80),
            (98, 81),
            (100, 81),
            (126, 81),
            (128, 81),
            (81, 50),
            (81, 49),
            (160, 81),
            (162, 81),
        ],
        [
            (70, 81),
            (72, 81),
            (98, 81),
            (100, 81),
            (81, 64),
            (81, 63),
            (126, 81),
            (128, 81),
            (160, 81),
            (162, 81),
            (81, 36),
            (81, 35),
        ],
        [
            (70, 81),
            (72, 81),
            (81, 81),
            (81, 80),
            (98, 81),
            (100, 81),
            (126, 81),
            (128, 81),
            (160, 81),
            (162, 81),
            (81, 36),
            (81, 35),
        ],
        [
            (70, 81),
            (72, 81),
            (98, 81),
            (100, 81),
            (81, 64),
            (81, 63),
            (126, 81),
            (128, 81),
            (81, 50),
            (81, 49),
            (160, 81),
            (162, 81),
        ],
        [
            (70, 81),
            (72, 81),
            (81, 81),
            (81, 80),
            (81, 64),
            (81, 63),
            (81, 50),
            (81, 49),
            (160, 81),
            (162, 81),
            (81, 36),
            (81, 35),
        ],
        [
            (81, 81),
            (81, 80),
            (98, 81),
            (100, 81),
            (81, 64),
            (81, 63),
            (126, 81),
            (128, 81),
            (81, 50),
            (81, 49),
            (81, 36),
            (81, 35),
        ],
    ]
    assert len(scales) == 12
    assert len(set(chain.from_iterable(scales))) == 16

    for i, labels in enumerate(scales, 1):
        name = f"xen16_burt_drones_{i:02}"

        def build(f, labels=labels, i=i):
            assert len(labels) == 12
            ratios = defaultdict(lambda: [])
            for numerator, denominator in labels:
                ratio = reduce(F(numerator, denominator))
                ratios[ratio].append(f"{numerator}/{denominator}")
            tones = [
                T.from_fraction(k, comment=", ".join(map(str, v)))
                for k, v in ratios.items()
            ]
            assert len(tones) in {11, 12}
            page = 99 if i < 5 else 100
            return build_scl(
                description=f"Scale {i} from Drones 1994 #2",
                tones=tones,
                title="Drones 1994 #2: Old Commas Inverted and Revisited",
                page=page,
                function=f,
            )

        globals()[name] = build


add_burt_drones()


def xen16_burt_commas(f):
    tones = [
        T(10, 9),
        T(8, 7),
        T(32, 27),
        T(1215, 1024),
        T(5, 4),
        T(81, 64),
        T(1024, 729),
        T(729, 512),
        T(25, 16),
        T(8, 5),
        T(7, 4),
        T(16, 9),
        T(2, 1),
    ]
    assert len(tones) == 13
    return build_scl(
        description="Tuning for COMMAS",
        tones=tones,
        title="COMMAS",
        page=103,
        function=f,
    )


def xen16_hero_lambdoma_16(f):
    n = range(1, 17)
    ratios = sorted({F(x, y) for x in n for y in n})
    root = min(ratios)
    period = 1200 * log2(max(ratios) / root)
    tones = [
        T.from_fraction(
            x / root, comment=f"{x.numerator}/{x.denominator}", period=period
        )
        for x in ratios
        if x != root
    ]
    return build_scl(
        description="16 by 16 Lambdoma matrix",
        tones=tones,
        title="A Brief History of the Lambdoma",
        page=106,
        function=f,
    )


def xen16_hero_lambdoma_08(f):
    n = range(1, 9)
    ratios = sorted({F(x, y) for x in n for y in n})
    root = min(ratios)
    period = 1200 * log2(max(ratios) / root)
    tones = [
        T.from_fraction(
            x / root, comment=f"{x.numerator}/{x.denominator}", period=period
        )
        for x in ratios
        if x != root
    ]
    return build_scl(
        description="8 by 8 Lambdoma matrix",
        tones=tones,
        title="A Brief History of the Lambdoma",
        page=108,
        function=f,
    )


def xen17_chalmers_ursell_quiggle_1(f):
    tones = [
        T(601.0),
        T(851.0),
        T(983.0),
        T(1060.0),
        T(1109.0),
        T(1141.0),
        T(1162.0),
        T(1176.0),
        T(1186.0),
        T(1192.0),
        T(1197.0),
        T(1200.0),
    ]
    assert len(tones) == 12
    return build_scl(
        description="Sarn Ursell's Quiggle Temperament, first kind",
        tones=tones,
        title="Notes & Comments 17",
        page=3,
        function=f,
        comments=["Note the root 1.415114418 is printed as 1.415511418"],
    )


def xen17_chalmers_ursell_quiggle_2(f):
    period = 6699.0
    tones = [
        T(248.0, period=period),
        T(286.0, period=period),
        T(330.0, period=period),
        T(381.0, period=period),
        T(440.0, period=period),
        T(508.0, period=period),
        T(586.0, period=period),
        T(676.0, period=period),
        T(781.0, period=period),
        T(901.0, period=period),
        T(1040.0, period=period),
        T(1200.0, period=period),
        T(1385.0, period=period),
        T(1598.0, period=period),
        T(1845.0, period=period),
        T(2129.0, period=period),
        T(2457.0, period=period),
        T(2835.0, period=period),
        T(3272.0, period=period),
        T(3776.0, period=period),
        T(4358.0, period=period),
        T(5030.0, period=period),
        T(5804.0, period=period),
        T(6699.0, period=period),
    ]
    assert len(tones) == 24
    return build_scl(
        description="Sarn Ursell's Quiggle Temperament, second kind",
        tones=tones,
        title="Notes & Comments 17",
        page=3,
        function=f,
    )


def xen17_erlich_standard_pentachordal_major(f):
    labels = [2, 4, 7, 9, 11, 13, 16, 18, 20, 22]
    step = 1200 / 22
    tones = [T(i * step, comment=f"{i:>2}") for i in labels]
    assert len(tones) == 10
    return build_scl(
        description="Decatonic mode: Standard Pentachordal Major",
        tones=tones,
        title="Tuning, Tonality, and Twenty-Two-Tone Temperament",
        page=23,
        function=f,
    )


def xen17_erlich_static_symmetrical_major(f):
    labels = [2, 4, 7, 9, 11, 13, 15, 18, 20, 22]
    step = 1200 / 22
    tones = [T(i * step, comment=f"{i:>2}") for i in labels]
    assert len(tones) == 10
    return build_scl(
        description="Decatonic mode: Static Symmetrical Major",
        tones=tones,
        title="Tuning, Tonality, and Twenty-Two-Tone Temperament",
        page=23,
        function=f,
    )


def xen17_erlich_alternate_pentachordal_major(f):
    labels = [2, 5, 7, 9, 11, 13, 15, 18, 20, 22]
    step = 1200 / 22
    tones = [T(i * step, comment=f"{i:>2}") for i in labels]
    assert len(tones) == 10
    return build_scl(
        description="Decatonic mode: Alternate Pentachordal Major",
        tones=tones,
        title="Tuning, Tonality, and Twenty-Two-Tone Temperament",
        page=23,
        function=f,
    )


def xen17_erlich_dynamic_symmetrical_major(f):
    labels = [2, 5, 7, 9, 11, 13, 16, 18, 20, 22]
    step = 1200 / 22
    tones = [T(i * step, comment=f"{i:>2}") for i in labels]
    assert len(tones) == 10
    return build_scl(
        description="Decatonic mode: Dynamic Symmetrical Major",
        tones=tones,
        title="Tuning, Tonality, and Twenty-Two-Tone Temperament",
        page=24,
        function=f,
    )


def xen17_erlich_standard_pentachordal_minor(f):
    labels = [2, 4, 6, 9, 11, 13, 15, 17, 19, 22]
    step = 1200 / 22
    tones = [T(i * step, comment=f"{i:>2}") for i in labels]
    assert len(tones) == 10
    return build_scl(
        description="Decatonic mode: Standard Pentachordal Minor",
        tones=tones,
        title="Tuning, Tonality, and Twenty-Two-Tone Temperament",
        page=24,
        function=f,
    )


def xen17_erlich_static_symmetrical_minor(f):
    labels = [2, 4, 6, 9, 11, 13, 15, 17, 20, 22]
    step = 1200 / 22
    tones = [T(i * step, comment=f"{i:>2}") for i in labels]
    assert len(tones) == 10
    return build_scl(
        description="Decatonic mode: Static Symmetrical Minor",
        tones=tones,
        title="Tuning, Tonality, and Twenty-Two-Tone Temperament",
        page=24,
        function=f,
    )


def xen17_erlich_alternate_pentachordal_minor(f):
    labels = [2, 4, 6, 8, 11, 13, 15, 17, 20, 22]
    step = 1200 / 22
    tones = [T(i * step, comment=f"{i:>2}") for i in labels]
    assert len(tones) == 10
    return build_scl(
        description="Decatonic mode: Alternate Pentachordal Minor",
        tones=tones,
        title="Tuning, Tonality, and Twenty-Two-Tone Temperament",
        page=24,
        function=f,
    )


def xen17_erlich_dynamic_symmetrical_minor(f):
    labels = [2, 4, 6, 8, 11, 13, 15, 17, 19, 22]
    step = 1200 / 22
    tones = [T(i * step, comment=f"{i:>2}") for i in labels]
    assert len(tones) == 10
    return build_scl(
        description="Decatonic mode: Dynamic Symmetrical Minor",
        tones=tones,
        title="Tuning, Tonality, and Twenty-Two-Tone Temperament",
        page=24,
        function=f,
    )


# Table 4 removed in XH18 errata p.301
#
# def xen17_erlich_resonant_1(f):
#     tones = [
#         T(21, 20, cents=84),  # cents printed as 85
#         T(15, 14, cents=119),
#         T(12, 11, cents=151),
#         T(9, 8, cents=204),
#         T(8, 7, cents=231),
#         T(7, 6, cents=267),
#         T(6, 5, cents=316),
#         T(5, 4, cents=386),
#         T(9, 7, cents=435),
#         T(21, 16, cents=471),  # cents printed as 473
#         T(4, 3, cents=498),
#         T(11, 8, cents=551),
#         T(7, 5, cents=583),
#         T(10, 7, cents=617),
#         T(3, 2, cents=702),
#         T(8, 5, cents=814),
#         T(5, 3, cents=884),
#         T(12, 7, cents=933),
#         T(7, 4, cents=969),
#         T(9, 5, cents=1018),
#         T(15, 8, cents=1088),
#         T(2, 1, cents=1200),
#     ]
#     assert len(tones) == 22
#     return build_scl(
#         description="22 resonant tones from Table 4",
#         tones=tones,
#         title="Tuning, Tonality, and Twenty-Two-Tone Temperament",
#         page=33,
#         function=f,
#     )
#
#
# def xen17_erlich_resonant_2(f):
#     tones = [
#         T(33, 32, cents=53),
#         T(21, 20, cents=84),  # cents printed as 85
#         T(15, 14, cents=119),
#         T(12, 11, cents=151),
#         T(9, 8, cents=204),
#         T(8, 7, cents=231),
#         T(7, 6, cents=267),
#         T(6, 5, cents=316),
#         T(5, 4, cents=386),
#         T(9, 7, cents=435),
#         T(21, 16, cents=471),  # cents printed as 473
#         T(4, 3, cents=498),
#         T(11, 8, cents=551),
#         T(7, 5, cents=583),
#         T(10, 7, cents=617),
#         T(16, 11, cents=649),
#         T(3, 2, cents=702),
#         T(14, 9, cents=765),
#         T(8, 5, cents=814),
#         T(5, 3, cents=884),
#         T(12, 7, cents=933),
#         T(7, 4, cents=969),
#         T(9, 5, cents=1018),
#         T(15, 8, cents=1088),
#         T(27, 14, cents=1137),
#         T(2, 1, cents=1200),
#     ]
#     assert len(tones) == 26
#     return build_scl(
#         description="22 resonant tones plus four transposed by 3/2, from Table 4",
#         tones=tones,
#         title="Tuning, Tonality, and Twenty-Two-Tone Temperament",
#         page=33,
#         function=f,
#     )


def xen17_erlich_unequal_22(f):
    tones = [
        T(50.25),
        T(105.75, comment="or 100.5 or 111"),
        T(161.25),
        T(211.5),
        T(272.25),
        T(322.5),
        T(383.25),
        T(428.25),
        T(494.25),
        T(539.25),
        T(594.75),
        T(650.25),
        T(705.75),
        T(761.25),
        T(816.75),
        T(872.25),
        T(917.25),
        T(983.25),
        T(1028.25),
        T(1089.0),
        T(1139.25),
        T(1200.0),
    ]
    assert len(tones) == 22
    return build_scl(
        description="Unequal 22-tone tuning, Table 5",
        tones=tones,
        title="Tuning, Tonality, and Twenty-Two-Tone Temperament",
        page=39,
        function=f,
    )


def xen17_bohlen_harmonic_1(f):
    period = 1200 * log2(3)
    tones = [
        T(27, 25, period=period),
        T(25, 21, period=period),
        T(9, 7, period=period),
        T(7, 5, period=period),
        T(75, 49, period=period),
        T(5, 3, period=period),
        T(9, 5, period=period),
        T(49, 25, period=period),
        T(15, 7, period=period),
        T(7, 3, period=period),
        T(63, 25, period=period),
        T(25, 9, period=period),
        T(3, 1, period=period),
    ]
    assert len(tones) == 13
    return build_scl(
        description="13-tone non-tempered scale",
        tones=tones,
        title="Letter to the Editor",
        page=124,
        function=f,
    )


def xen17_bohlen_harmonic_2(f):
    period = 1200 * log2(3)
    tones = [
        T(11, 10, period=period),
        T(6, 5, period=period),
        T(30, 23, period=period),
        T(10, 7, period=period),
        T(11, 7, period=period),
        T(7, 4, period=period),
        T(21, 11, period=period),
        T(21, 10, period=period),
        T(23, 10, period=period),
        T(5, 2, period=period),
        T(11, 4, period=period),
        T(3, 1, period=period),
    ]
    assert len(tones) == 12
    return build_scl(
        description="12-tone non-tempered scale based on 4:7:10 triad",
        tones=tones,
        title="Letter to the Editor",
        page=124,
        function=f,
    )


# Duplicates xen15_gilson_didymus_diatonic
# def xen18_secor_didymus_diatonic(f):
#     tones = [
#         T(16, 15),
#         T(32, 27),
#         T(4, 3),
#         T(3, 2),
#         T(8, 5),
#         T(16, 9),
#         T(2, 1),
#     ]
#     assert len(tones) == 7
#     return build_scl(
#         description="Diatonic scale of Didymus",
#         tones=tones,
#         title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
#         page=58,
#         function=f,
#     )


# Duplicates xen15_gilson_ptolemy_diatonic_syntonon
# def xen18_secor_ptolemy_diatonic_syntonon(f):
#     tones = [
#         T(16, 15),
#         T(6, 5),
#         T(4, 3),
#         T(3, 2),
#         T(8, 5),
#         T(9, 5),
#         T(2, 1),
#     ]
#     assert len(tones) == 7
#     return build_scl(
#         description="Ptolemy's diatonic syntonon",
#         tones=tones,
#         title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
#         page=58,
#         function=f,
#     )

# Duplicates xen15_gilson_archytas_diatonic
# def xen18_secor_archytas_diatonic(f):
#     tones = [
#         T(28, 27),
#         T(32, 27),
#         T(4, 3),
#         T(3, 2),
#         T(14, 9),
#         T(16, 9),
#         T(2, 1),
#     ]
#     assert len(tones) == 7
#     return build_scl(
#         description="Archytas' diatonic",
#         tones=tones,
#         title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
#         page=58,
#         function=f,
#     )


SECOR = {
    "C#": 144.856,
    "F#": 640.479,
    "B": 1136.102,
    "E": 428.882,
    "A": 921.661,
    "D": 214.441,
    "G": 707.220,
    "C": 0.0,
    "F": 492.780,
    "Bb": 985.559,
    "Eb": 278.339,
    "Ab": 771.118,
    "Db": 66.741,
    "Gb": 562.364,
    "A#": 1057.987,
    "D#": 353.610,
    "G#": 849.233,
    r"F#\!": 600.755,
    r"B\!": 1093.534,
    r"E\!": 386.314,
    r"A\!": 879.760,
    r"D\!": 173.961,
}

SECOR["Dd"] = SECOR["C#"]
SECOR["Gd"] = SECOR["F#"]
SECOR["Cd"] = SECOR["B"]

SECOR["A=/"] = SECOR["Bb"]
SECOR["D=/"] = SECOR["Eb"]
SECOR["G=/"] = SECOR["Ab"]
SECOR["C=/"] = SECOR["Db"]
SECOR["F=/"] = SECOR["Gb"]
SECOR["Bd"] = SECOR["A#"]
SECOR["Ed"] = SECOR["D#"]
SECOR["Ad"] = SECOR["G#"]


def reduce_cents(x, period=1200.0):
    while x <= 0.0:
        x += period
    while x > period:
        x -= period
    return x


def xen18_secor_13_limit_1_tempered(f):
    tones = [
        T(reduce_cents(SECOR[x]), comment=x)
        for x in ["C", "Dd", "Eb", "F", "G", "Ad", "Bd"]
    ]
    assert len(tones) == 7
    return build_scl(
        description="13-limit tempered scale",
        tones=tones,
        title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
        page=69,
        function=f,
    )


def xen18_secor_13_limit_1_just(f):
    tones = [
        T(13, 12),
        T(7, 6),
        T(4, 3),
        T(3, 2),
        T(13, 8),
        T(11, 6),
        T(2, 1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="13-limit just scale",
        tones=tones,
        title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
        page=69,
        function=f,
    )


def xen18_secor_neutral_third_mos_1_tempered(f):
    tones = [
        T(reduce_cents(SECOR[x]), comment=x)
        for x in ["C", "Dd", "Ed", "F", "G", "Ad", "Bd"]
    ]
    assert len(tones) == 7
    return build_scl(
        description="MOS generated by a neutral third, tempered",
        tones=tones,
        title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
        page=71,
        function=f,
    )


def xen18_secor_neutral_third_mos_1_just(f):
    tones = [
        T(13, 12),
        T(11, 9),
        T(4, 3),
        T(3, 2),
        T(13, 8),
        T(11, 6),
        T(2, 1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="MOS generated by a neutral third, just",
        tones=tones,
        title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
        page=71,
        function=f,
    )


def xen18_secor_neutral_third_mos_2_tempered(f):
    tones = [
        T(reduce_cents(SECOR[x] - SECOR["D"]), comment=x)
        for x in ["D", "E", "F=/", "G=/", "A", "Bd", "C=/"]
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition of a mode of MOS generated by a neutral third, tempered",
        tones=tones,
        title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
        page=72,
        function=f,
    )


def xen18_secor_neutral_third_mos_2_just(f):
    tones = [
        T(9, 8),
        T(39, 32),
        T(11, 8),
        T(3, 2),
        T(13, 8),
        T(11, 6),
        T(2, 1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposition of a mode of MOS generated by a neutral third, just",
        tones=tones,
        title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
        page=72,
        function=f,
    )


def xen18_secor_13_limit_2_tempered(f):
    tones = [
        T(reduce_cents(SECOR[x]), comment=x)
        for x in ["C", "Dd", "Eb", "F", "G", "Ad", "Bb"]
    ]
    assert len(tones) == 7
    return build_scl(
        description="13-limit tempered scale, enharmonic alteration",
        tones=tones,
        title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
        page=75,
        function=f,
    )


def xen18_secor_13_limit_2_just(f):
    tones = [
        T(13, 12),
        T(7, 6),
        T(4, 3),
        T(3, 2),
        T(13, 8),
        T(7, 4),
        T(2, 1),
    ]
    assert len(tones) == 7
    return build_scl(
        description="13-limit just scale, enharmonic alteration",
        tones=tones,
        title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
        page=75,
        function=f,
    )


def xen18_secor_neutral_second_mos_1(f):
    tones = [
        T(reduce_cents(SECOR[x] - SECOR["D"]), comment=x)
        for x in ["D", "Ed", "F", "Gd", "Ab", "A", "Bd", "C", "C=/"]
    ]
    assert len(tones) == 9
    return build_scl(
        description="MOS generated by a neutral second",
        tones=tones,
        title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
        page=76,
        function=f,
    )


def xen18_secor_neutral_second_mos_2(f):
    tones = [
        T(reduce_cents(SECOR[x] - SECOR["D"]), comment=x)
        for x in ["D", "Ed", "F", "Gd", "Ab", "A", "Bd", "C"]
    ]
    assert len(tones) == 8
    return build_scl(
        description="MOS generated by a neutral second",
        tones=tones,
        title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
        page=76,
        function=f,
    )


def xen18_secor_11_17_mos(f):
    tones = [
        T(reduce_cents(SECOR[x]), comment=x)
        for x in ["C", "D", "Eb", "Ed", "F=/", "F#", "G", "Ab", "A=/", "Bd", "B"]
    ]
    assert len(tones) == 11
    return build_scl(
        description="MOS generated by 11o17",
        tones=tones,
        title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
        page=76,
        function=f,
    )


def xen18_secor_17_wt(f):
    tones = [
        T(reduce_cents(SECOR[x]), comment=x)
        for x in [
            "C#",
            "F#",
            "B",
            "E",
            "A",
            "D",
            "G",
            "C",
            "F",
            "Bb",
            "Eb",
            "Ab",
            "Db",
            "Gb",
            "A#",
            "D#",
            "G#",
        ]
    ]
    assert len(tones) == 17
    return build_scl(
        description="Secor 17-tone Well Temperament",
        tones=tones,
        title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
        page=79,
        function=f,
    )


def xen18_secor_17_plus_5_wt(f):
    tones = [
        T(reduce_cents(SECOR[x]), comment=x)
        for x in [
            "C#",
            "F#",
            "B",
            "E",
            "A",
            "D",
            "G",
            "C",
            "F",
            "Bb",
            "Eb",
            "Ab",
            "Db",
            "Gb",
            "A#",
            "D#",
            "G#",
            r"F#\!",
            r"B\!",
            r"E\!",
            r"A\!",
            r"D\!",
        ]
    ]
    assert len(tones) == 22
    return build_scl(
        description="Secor 17+5 Temperament",
        tones=tones,
        title="The 17-tone Puzzle - And the Neo-medieval Key that Unlocks It",
        page=80,
        function=f,
    )


def xen18_schulter_pythagorean(f):
    tones = [
        T(2187, 2048, cents=113.69, comment="C#"),
        T(9, 8, cents=203.91, comment="D"),
        T(32, 27, cents=294.13, comment="Eb"),
        T(81, 64, cents=407.82, comment="E"),
        T(4, 3, cents=498.04, comment="F"),
        T(729, 512, cents=611.73, comment="F#, originally printed as 729:612"),
        T(3, 2, cents=701.96, comment="G"),
        T(6561, 4096, cents=815.64, comment="G#"),
        T(27, 16, cents=905.87, comment="A"),
        T(16, 9, cents=996.09, comment="Bb"),
        T(243, 128, cents=1109.78, comment="B, originally printed as 256:243"),
        T(2, 1, cents=1200, comment="C"),
    ]
    assert len(tones) == 12
    return build_scl(
        description="12-note Pythagorean tuning",
        tones=tones,
        title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
        page=83,
        function=f,
    )


def xen18_schulter_pure_11_14(f):
    tones = [
        T(130.64, comment="C#"),
        T(208.75, comment="D"),
        T(286.87, comment="Eb"),
        T(417.51, comment="E, 14:11"),
        T(495.62, comment="F"),
        T(626.26, comment="F#"),
        T(704.38, comment="G"),
        T(835.02, comment="G#, 196:121"),
        T(913.13, comment="A"),
        T(991.25, comment="Bb"),
        T(1121.88, comment="B"),
        T(1200.0, comment="C, 2:1"),
    ]
    assert len(tones) == 12
    return build_scl(
        description="Temperament with pure 11:14 major thirds, fifth of 704.377 cents",
        tones=tones,
        title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
        page=85,
        function=f,
    )


def stack_fifths(g, N, start, rounding=None):
    tones = []
    names = ["F", "C", "G", "D", "A", "E", "B"]
    for i in range(start, start + N):
        n = (i + 1) // 7
        if n == 2:
            s = "x"
        elif n > 0:
            s = abs(n) * "#"
        else:
            s = abs(n) * "b"
        name = names[(i + 1) % 7] + s
        cents = reduce_cents(i * g)
        if rounding is not None:
            cents = round(cents, rounding)
        tones.append(T(cents, comment=name))
    assert len(tones) == N
    return tones


def xen18_schulter_pure_11_14_17(f):
    tones = stack_fifths(704.377, 17, -6)
    return build_scl(
        description="Temperament with pure 11:14 major thirds, fifth of 704.377 cents",
        tones=tones,
        title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
        page=85,
        function=f,
    )


def xen18_schulter_pure_11_14_24(f):
    tones = stack_fifths(704.377, 24, -9)
    return build_scl(
        description="Temperament with pure 11:14 major thirds, fifth of 704.377 cents",
        tones=tones,
        title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
        page=85,
        function=f,
    )


def add_archytan_and_didymic_temperaments():
    for frac, comma, n, page in [
        (F(1, 4), F(64, 63), 12, 88),
        (F(1, 4), F(64, 63), 17, 88),
        (F(1, 3), F(64, 63), 12, 88),
        (F(1, 3), F(64, 63), 17, 88),
        (F(1, 2), F(64, 63), 12, 88),
        (F(1, 2), F(64, 63), 17, 88),
        (F(1, 5), F(64, 63), 12, 88),
        (F(1, 5), F(64, 63), 17, 88),
        (F(5, 26), F(64, 63), 12, 89),
        (F(5, 26), F(64, 63), 17, 89),
        (-F(1, 4), F(81, 80), 12, 89),
        (-F(1, 4), F(81, 80), 17, 89),
    ]:
        kind = {F(64, 63): "Archytan", F(81, 80): "Didymic"}[comma]
        abs_frac = abs(frac)
        name = f"xen18_schulter_{kind.lower()}_{abs_frac.numerator}_{abs_frac.denominator}_{n}"

        def build(f, frac=frac, n=n, page=page, comma=comma, kind=kind):
            g = 1200 * (log2(3 / 2) + frac * log2(comma))
            starts = {12: -3, 17: -6}
            tones = stack_fifths(g, n, starts[n])
            return build_scl(
                description=f"{abs(frac)}-{kind} temperament",
                tones=tones,
                title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
                page=page,
                function=f,
            )

        globals()[name] = build


add_archytan_and_didymic_temperaments()


def xen18_schulter_707_10(f):
    tones = stack_fifths(707.22045, 10, -4, rounding=3)
    return build_scl(
        description="Ab-B portion in 17-WT",
        tones=tones,
        title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
        page=89,
        function=f,
    )


def add_707_temperaments():
    for n, start in [
        (12, -3),
        (17, -6),
        (24, -9),
        (56, -25),
    ]:
        name = f"xen18_schulter_707_{n}"

        def build(f, n=n, start=start):
            tones = stack_fifths(707.22045, n, start)
            return build_scl(
                description="Temperament with fifth of 707.22045",
                tones=tones,
                title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
                page=90,
                function=f,
            )

        globals()[name] = build


add_707_temperaments()


def xen18_schulter_zalzal(f):
    tones = [
        T(9, 8, cents=203.91),
        T(27, 22, cents=354.55),
        T(4, 3, cents=498.04),
        T(3, 2, cents=701.96),
        T(18, 11, cents=852.59),
        T(16, 9, cents=996.09),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Zalzal's scale",
        tones=tones,
        title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
        page=102,
        function=f,
    )


def xen18_schulter_zalzal_d(f):
    labels = ["D", "E", "F=/", "G", "A", "Bd", "C"]
    tones = [
        T(round(reduce_cents(SECOR[x] - SECOR[labels[0]]), 2), comment=x)
        for x in labels
    ]
    assert len(tones) == 7
    return build_scl(
        description="Zalzal's scale in 17-WT, on D",
        tones=tones,
        title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
        page=102,
        function=f,
    )


def xen18_schulter_zalzal_g(f):
    labels = ["G", "A", "Bd", "C", "D", "E", "F=/"]
    tones = [
        T(round(reduce_cents(SECOR[x] - SECOR[labels[0]]), 2), comment=x)
        for x in labels
    ]
    assert len(tones) == 7
    return build_scl(
        description="Mode of Zalzal's scale in 17-WT, on G",
        tones=tones,
        title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
        page=104,
        function=f,
    )


def xen18_schulter_symmetrical(f):
    tones = [
        T(14, 13, cents=128.30),
        T(7, 6, cents=266.87),
        T(4, 3, cents=498.04),
        T(3, 2, cents=701.96),
        T(21, 13, cents=830.25),
        T(7, 4, cents=968.83),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 7
    return build_scl(
        description="A JI version of a symmetrical scale in 17-WT",
        tones=tones,
        title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
        page=105,
        function=f,
    )


def xen18_schulter_pelog_like(f):
    labels = ["E", "F", "G", "B", "C"]
    tones = [
        T(round(reduce_cents(SECOR[x] - SECOR[labels[0]]), 2), comment=x)
        for x in labels
    ]
    assert len(tones) == 5
    return build_scl(
        description="A Pelog-like pentatonic in 17-WT",
        tones=tones,
        title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
        page=108,
        function=f,
    )


def xen18_schulter_harrison_17_wt(f):
    labels = ["E", "F", "A", "B", "C"]
    tones = [
        T(round(reduce_cents(SECOR[x] - SECOR[labels[0]]), 2), comment=x)
        for x in labels
    ]
    assert len(tones) == 5
    return build_scl(
        description="17-WT realization of a JI scale of Lou Harrison",
        tones=tones,
        title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
        page=108,
        function=f,
    )


def xen18_schulter_harrison(f):
    tones = [
        T(28, 27),
        T(4, 3),
        T(3, 2),
        T(14, 9),
        T(2, 1),
    ]
    assert len(tones) == 5
    return build_scl(
        description="A JI scale of Lou Harrison",
        tones=tones,
        title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
        page=108,
        function=f,
    )


def xen18_schulter_circulating(f):
    tones = [
        T(70.100, comment="Db, 126:121"),
        T(130.639, comment="C#"),
        T(208.754, comment="D"),
        T(286.869, comment="Eb"),
        T(343.787, comment="D#"),
        T(417.508, comment="E, 14:11"),
        T(495.623, comment="F"),
        T(561.329, comment="Gb"),
        T(626.262, comment="F#"),
        T(704.377, comment="G"),
        T(778.871, comment="Ab"),
        T(853.016, comment="G#, 196:121"),
        T(913.131, comment="A"),
        T(991.247, comment="Bb"),
        T(1052.558, comment="A#"),
        T(1121.885, comment="B"),
        T(1200.0, comment="C, 2:1"),
    ]
    assert len(tones) == 17
    return build_scl(
        description="17-note circulating temperament",
        tones=tones,
        title="George Secor's 17-Tone Well-Temperament and Neo-Medieval Music",
        page=123,
        function=f,
    )


# Duplicates scales/mailing-lists/duodene.scl
# def xen18_keenan_five_limit(f):
#     tones = [
#         T(5, 3),
#         T(5, 4),
#         T(15, 8),
#         T(45, 32),
#         T(4, 3),
#         T(2, 1),
#         T(3, 2),
#         T(9, 8),
#         T(16, 15),
#         T(8, 5),
#         T(6, 5),
#         T(9, 5),
#     ]
#     assert len(tones) == 12
#     return build_scl(
#         description="12-note 5-limit scale",
#         tones=tones,
#         title="Optimising JI guitar designs using linear microtemperaments",
#         page=136,
#         function=f,
#     )


def xen18_keenan_just_blackjack(f):
    tones = [
        T(21, 20),
        T(15, 14),
        T(9, 8),
        T(8, 7),
        T(6, 5),
        T(128, 105),
        T(5, 4),
        T(21, 16),
        T(4, 3),
        T(7, 5),
        T(10, 7),
        T(3, 2),
        T(32, 21),
        T(8, 5),
        T(105, 64),
        T(12, 7),
        T(7, 4),
        T(64, 35),
        T(15, 8),
        T(63, 32),
        T(2, 1),
    ]
    assert len(tones) == 21
    return build_scl(
        description="7-limit just-ification of Blackjack",
        tones=tones,
        title="Optimising JI guitar designs using linear microtemperaments",
        page=145,
        function=f,
    )


def xen18_keenan_blackjack_guitar(f):
    tones = [
        T(33.0),
        T(117.0),
        T(150.0),
        T(233.0),
        T(267.0),
        T(350.0),
        T(383.0),
        T(467.0),
        T(500.0),
        T(583.0),
        T(617.0),
        T(700.0),
        T(733.0),
        T(817.0),
        T(850.0),
        T(883.0),
        T(967.0),
        T(1000.0),
        T(1083.0),
        T(1117.0),
        T(1200.0),
    ]
    assert len(tones) == 21
    return build_scl(
        description="Fret tunings for a blackjack guitar fretboard",
        tones=tones,
        title="Optimising JI guitar designs using linear microtemperaments",
        page=146,
        function=f,
    )


def steps(s):
    return [y - x for x, y in zip(s, s[1:])]


def stack_alternating(p, g, n):
    s = [Decimal(0)]
    right = False
    for _ in range(n):
        if right:
            x = reduce_cents(s[-1] + g, p)
            s.append(x)
        else:
            x = reduce_cents(s[0] - g, p)
            s = [x] + s
        right = not right
    return sorted(s) + [p]


def concat(s, t):
    return s + [x + s[-1] for x in t[1:]]


def repeat(s, n):
    r = s
    for _ in range(n - 1):
        r = concat(r, s)
    return r


D = Decimal


TEMPERAMENTS = {
    # Table 1
    "Father": (D("1185.9"), D("447.4"), 1, 8, 186),
    "Bug": (D("1200.0"), D("260.3"), 1, 9, 183),
    #
    "Dicot": (D("1207.66"), D("353.22"), 1, 17, 185),
    "Meantone": (D("1201.70"), D("504.13"), 1, 50, 190),
    "Augmented": (D("399.02"), D("93.15"), 3, 27, 182),
    "Mavila": (D("1206.55"), D("685.03"), 1, 16, 190),
    "Porcupine": (D("1196.91"), D("1034.59"), 1, 37, 196),
    "Blackwood": (D("238.87"), D("158.78"), 5, 25, 183),
    "Dimipent": (D("299.16"), D("197.49"), 4, 20, 185),
    "Srutal": (D("599.56"), D("494.86"), 2, 46, 198),
    "Magic": (D("1201.28"), D("380.80"), 1, 60, 190),
    "Ripple": (D("1203.32"), D("101.99"), 1, 35, 196),
    "Hanson": (D("1200.29"), D("317.07"), 1, 53, 187),
    "Negripent": (D("1201.82"), D("1075.68"), 1, 29, 193),
    "Tetracot": (D("1199.03"), D("176.11"), 1, 41, 198),
    "Superpyth": (D("1197.60"), D("708.17"), 1, 27, 198),
    "Helmholtz": (D("1200.07"), D("701.79"), 1, 53, 188),
    "Sensipent": (D("1199.59"), D("756.60"), 1, 46, 197),
    "Passion": (D("1198.31"), D("98.40"), 1, 49, 195),
    "Wurschmidt": (D("1199.69"), D("812.05"), 1, 65, 199),
    "Compton": (D("100.05"), D("15.13"), 12, 72, 184),
    "Amity": (D("1199.85"), D("860.38"), 1, 53, 182),
    "Orson": (D("1200.24"), D("271.65"), 1, 53, 194),
    #
    "Vishnu": (D("599.97"), D("71.15"), 2, 118 - 1, 199),
    "Luna": (D("1199.98"), D("193.196"), 1, 118 - 1, 189),
    #
    #
    # Table 2
    "Blacksmith": (D("239.18"), D("155.35"), 5, 25, 183),
    "Dimisept": (D("298.53"), D("197.08"), 4, 20, 185),
    "Dominant": (D("1195.23"), D("495.88"), 1, 17, 185),
    "August": (D("399.99"), D("107.31"), 3, 21, 183),
    "Pajara": (D("598.45"), D("491.88"), 2, 34, 194),
    "Semaphore": (D("1203.67"), D("252.48"), 1, 24, 197),
    # "Meantone": (D("1201.70"), D("504.13"), 1, ,),
    "Injera": (D("600.89"), D("507.28"), 2, 38, 188),
    "Negrisept": (D("1203.19"), D("1078.35"), 1, 29, 193),
    "Augene": (D("399.02"), D("92.46"), 3, 39, 182),
    "Keemun": (D("1203.19"), D("317.84"), 1, 34, 188),
    "Catler": (D("99.81"), D("75.22"), 12, 48, 183),
    "Hedgehog": (D("598.45"), D("436.13"), 2, 30, 187),
    # "Superpyth": (D("1197.60"), D("708.17"), 1, 27, 198),
    "Sensisept": (D("1198.39"), D("755.23"), 1, 46, 197),
    "Lemba": (D("601.70"), D("230.87"), 2, 42, 189),
    "Porcupine": (D("1196.91"), D("1034.59"), 1, 37, 196),
    "Flattone": (D("1202.54"), D("507.14"), 1, 45, 186),
    # "Magic": (D("1201.28"), D("380.80"), 1, 60, 190),
    "Doublewide": (D("599.28"), D("326.96"), 2, 40, 185),
    "Nautilus": (D("1202.66"), D("1119.69"), 1, 43, 192),
    "Beatles": (D("1197.10"), D("842.38"), 1, 37, 183),
    "Liese": (D("1202.62"), D("569.05"), 1, 55, 189),
    "Cynder": (D("1201.7"), D("969.18"), 1, 31, 184),
    "Orwell": (D("1199.53"), D("271.49"), 1, 53, 194),
    "Garibaldi": (D("1200.76"), D("702.64"), 1, 53, 187),
    "Myna": (D("1198.83"), D("888.94"), 1, 58, 191),
    "Miracle": (D("1200.63"), D("116.72"), 1, 72, 191),
    #
    "Ennealimmal": (D("133.337"), D("84.313"), 9, 99, 186),
}


def find_mos(p, g, k, nmax):
    r = []
    for n in range(round(nmax / k)):
        s = repeat(stack_alternating(p, g, n), k)
        if len(set(steps(s))) <= 2:
            r.append(s[1:])
    return r


def add_mos():
    for temperament, (
        period,
        generator,
        n_periods,
        n_max,
        page,
    ) in TEMPERAMENTS.items():
        for scale in find_mos(period, generator, n_periods, n_max):
            if len(scale) == 1:
                continue
            assert len(scale) < 100
            name = f"xen18_erlich_{temperament.lower()}_{len(scale):02}"

            def build(f, scale=scale, temperament=temperament, page=page):
                step_list = steps([0] + scale)
                step_counter = Counter(step_list)
                step_labels = {
                    k: v for k, v in zip(sorted(step_counter, reverse=True), ["L", "s"])
                }
                mos_name = " ".join(
                    f"{step_counter[k]}{v}" for k, v in step_labels.items()
                )
                desc = f"{mos_name} MOS for {temperament}, " + ", ".join(
                    f"{v}={k}" for k, v in step_labels.items()
                )
                tones = [
                    T(x, comment=step_labels[step], period=scale[-1])
                    for x, step in zip(scale, step_list)
                ]
                return build_scl(
                    description=desc,
                    tones=tones,
                    title="A Middle Path Between Just Intonation and the Equal Temperaments Part 1",
                    page=page,
                    function=f,
                )

            globals()[name] = build


add_mos()


def xen18_ayers_table_04(f):
    tones = [
        T(9, 8, cents=203.910),
        T(5, 4, cents=386.314),
        T(11, 8, cents=551.318),
        T(3, 2, cents=701.955),
        T(13, 8, cents=840.528),
        T(7, 4, cents=968.826),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 7
    return build_scl(
        description="7 Iterated Arithmetic Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=202,
        function=f,
    )


def xen18_ayers_table_05(f):
    tones = [
        T(8, 7, cents=231.174),
        T(9, 7, cents=435.084),
        T(10, 7, cents=617.488),
        T(11, 7, cents=782.492),
        T(12, 7, cents=933.129),
        T(13, 7, cents=1071.699),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 7
    return build_scl(
        description="6 Generalized Arithmetic Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=202,
        function=f,
    )


# Duplicates xen07-harrison-thoughts-4.scl
# def xen18_ayers_table_09_10(f):
#     tones = [
#         T(8, 7, cents=231.174),
#         T(4, 3, cents=498.045),
#         T(3, 2, cents=701.955),
#         T(12, 7, cents=933.129),
#         T(2, 1, cents=1200.0),
#     ]
#     assert len(tones) == 5
#     return build_scl(
#         description="Harmonic Mean scale from Table 9 and Table 10",
#         tones=tones,
#         title="Making Scales from Mathematical Means",
#         page=204,
#         function=f,
#     )


def xen18_ayers_table_11(f):
    tones = [
        T(16, 15, cents=111.731),
        T(8, 7, cents=231.174),
        T(16, 13, cents=359.472),
        T(4, 3, cents=498.045),
        T(16, 11, cents=648.682),
        T(8, 5, cents=813.686),
        T(16, 9, cents=996.090),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Harmonic Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=204,
        function=f,
    )


def xen18_ayers_table_12(f):
    tones = [
        T(12, 11, cents=150.637),
        T(6, 5, cents=315.641),
        T(4, 3, cents=498.045),
        T(3, 2, cents=701.955),
        T(12, 7, cents=933.129),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 6
    return build_scl(
        description="5 Generalized Harmonic Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=204,
        function=f,
    )


def xen18_ayers_table_13_14(f):
    tones = [
        T(20, 19, cents=88.801),
        T(10, 9, cents=182.404),
        T(20, 17, cents=281.358),
        T(5, 4, cents=386.314),
        T(4, 3, cents=498.045),
        T(7, 5, cents=582.512),
        T(28, 19, cents=671.313),
        T(14, 9, cents=764.916),  # Cents printed as 746.916
        T(28, 17, cents=863.87),
        T(7, 4, cents=968.826),
        T(28, 15, cents=1080.56),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 12
    return build_scl(
        description="Generalized Harmonic Mean scale from Table 13 and Table 14",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=205,
        function=f,
    )


def xen18_ayers_table_16(f):
    tones = [
        T(8, 7, cents=231.174),
        T(7, 6, cents=266.871),
        T(4, 3, cents=498.045),
        T(3, 2, cents=701.955),
        T(12, 7, cents=933.129),
        T(7, 4, cents=968.826),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 7
    return build_scl(
        description="2nd Iteration of Musical Proportion between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=206,
        function=f,
    )


def xen18_ayers_table_17(f):
    tones = [
        T(9, 8, cents=203.910),
        T(5, 4, cents=386.314),
        T(11, 8, cents=551.318),
        T(3, 2, cents=701.955),
        T(13, 8, cents=840.528),
        T(7, 4, cents=968.826),
        T(15, 8, cents=1088.269),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Arithmetic Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=206,
        function=f,
    )


def xen18_ayers_table_18(f):
    tones = [
        T(433, 348, cents=378.336),
        T(17, 12, cents=603.0),
        T(689, 444, cents=760.733),
        T(5, 3, cents=884.359),
        T(3373, 1914, cents=980.93),
        T(61, 33, cents=1063.612),
        T(8077, 4191, cents=1135.830),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Subcontraries to the Harmonic Mean",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=207,
        function=f,
    )


def xen18_ayers_table_19(f):
    tones = [
        T(8, 7, cents=231.174),
        T(4, 3, cents=498.045),
        T(17, 12, cents=603.0),
        T(8, 5, cents=813.686),
        T(5, 3, cents=884.359),
        T(61, 33, cents=1063.612),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 7
    return build_scl(
        description="3 Iterated Harmonic Means and 3 Iterated Subcontraries to the Harmonic Mean",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=207,
        function=f,
    )


def xen18_ayers_table_20(f):
    tones = [
        T(150.0),
        T(300.0),
        T(450.0),
        T(600.0),
        T(750.0),
        T(900.0),
        T(1050.0),
        T(1200.0),
    ]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Geometric Means Between 1/1 and 2/1 (8-tone Equal Temperament)",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=207,
        function=f,
    )


def xen18_ayers_table_23(f):
    tones = [
        T(256, 243, cents=90.275),
        T(9, 8, cents=203.91),
        T(32, 27, cents=294.135),
        T(4, 3, cents=498.045),
        T(3, 2, cents=701.955),
        T(27, 16, cents=905.865),
        T(16, 9, cents=996.09),
        T(243, 128, cents=1109.775),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 9
    return build_scl(
        description="Inverted Geometric Means Between 1/1 and 2/1 Produce a Symmetrical Scale",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=208,
        function=f,
    )


def xen18_ayers_table_24(f):
    tones = [
        T(240.0),
        T(480.0),
        T(720.0),
        T(960.0),
        T(1200.0),
    ]
    assert len(tones) == 5
    return build_scl(
        description="Generalized Geometric Means in Slendro Between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=209,
        function=f,
    )


def xen18_ayers_table_26(f):
    ratios_and_cents = [
        (1.19353, 306.278),
        (1.35567, 526.813),
        (1.49319, 694.073),
        (1.61803, 833.090),
        (1.72230, 941.201),
        (1.82025, 1036.963),
        (1.91234, 1122.409),
        (2.0, 1200.0),
    ]
    for ratio, cents in ratios_and_cents:
        assert abs(1200 * log2(ratio) - cents) < 0.01
    tones = [T(cents) for _, cents in ratios_and_cents]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated First Subcontraries to Geometric Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=209,
        function=f,
    )


def xen18_ayers_table_28(f):
    ratios_and_cents = [
        (1.16183, 259.681),
        (1.30582, 461.945),
        (1.43891, 629.974),
        (1.56155, 771.578),
        (1.68088, 899.057),
        (1.79276, 1010.614),
        (1.89906, 1110.343),
        (2.0, 1200.0),
    ]
    for ratio, cents in ratios_and_cents:
        assert abs(1200 * log2(ratio) - cents) < 0.01
    tones = [T(cents) for _, cents in ratios_and_cents]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Second Subcontraries to Geometric Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=210,
        function=f,
    )


def xen18_ayers_table_30(f):
    ratios_and_cents = [
        (1.04970, 83.979),
        (1.10765, 176.997),
        (1.17645, 281.327),
        (1.25992, 400.0),
        (1.36669, 540.827),
        (1.50628, 709.191),
        (1.70137, 920.040),
        (2.0, 1200.0),
    ]
    for ratio, cents in ratios_and_cents:
        assert abs(1200 * log2(ratio) - cents) < 0.01
    tones = [T(cents) for _, cents in ratios_and_cents]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Logarithmic Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=210,
        function=f,
    )


def xen18_ayers_table_32(f):
    ratios_and_cents = [
        (1.17552, 279.960),
        (1.32777, 490.809),
        (1.46339, 659.173),
        (1.58740, 800.0),
        (1.70003, 918.673),
        (1.80563, 1023.0),
        (1.90530, 1116.02),
        (2.0, 1200.0),
    ]
    for ratio, cents in ratios_and_cents:
        assert abs(1200 * log2(ratio) - cents) < 0.01
    tones = [T(cents) for _, cents in ratios_and_cents]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Counter-Logarithmic Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=211,
        function=f,
    )


def xen18_ayers_table_33(f):
    ratios_and_cents = [
        (1.10765, 176.997),
        (1.25992, 400.0),
        (1.32777, 490.809),
        (1.50628, 709.191),
        (1.58740, 800.0),
        (1.80563, 1023.0),
        (2.0, 1200.0),
    ]
    for ratio, cents in ratios_and_cents:
        assert abs(1200 * log2(ratio) - cents) < 0.01
    tones = [T(cents) for _, cents in ratios_and_cents]
    assert len(tones) == 7
    return build_scl(
        description="Logarithmic Means scale from Table 33",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=211,
        function=f,
    )


def xen18_ayers_table_34(f):
    ratios_and_cents = [
        (1.17260, 275.659),
        (1.32288, 484.413),
        (1.45774, 652.478),
        (1.58114, 793.157),
        (1.69558, 914.137),
        (1.80278, 1020.264),
        (1.90394, 1114.789),
        (2.0, 1200.0),
    ]
    for ratio, cents in ratios_and_cents:
        assert abs(1200 * log2(ratio) - cents) < 0.01
    tones = [T(cents) for _, cents in ratios_and_cents]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Root Mean Squares between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=211,
        function=f,
    )


def xen18_ayers_table_35(f):
    ratios_and_cents = [
        (1.12135, 198.289),
        (1.25743, 396.578),
        (1.41003, 594.868),
        (1.58114, 793.157),
        (1.77302, 991.446),
        (1.98818, 1189.74),
        (2.22945, 1388.02),
        (2.5, 1586.31),
    ]
    for ratio, cents in ratios_and_cents:
        assert abs(1200 * log2(ratio) - cents) < 0.01
    tones = [T(cents, period=1586.31) for _, cents in ratios_and_cents]
    assert len(tones) == 8
    return build_scl(
        description="7 Generalized Root Mean Squares between 1 and 2.5",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=212,
        function=f,
    )


def xen18_ayers_table_37(f):
    tones = [
        T(16384, 14321, cents=232.986),
        T(4096, 3281, cents=384.096),
        T(32768, 24305, cents=517.241),
        T(128, 89, cents=629.120),
        T(4096, 2705, cents=718.305),
        T(64, 41, cents=770.938),
        T(8, 5, cents=813.686),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Harmonic Square Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=213,
        function=f,
    )


def xen18_ayers_table_38(f):
    tones = [
        T(2048, 1649, cents=375.149),
        T(32, 25, cents=427.37),
        T(4, 3, cents=498.045),
        T(3, 2, cents=701.955),
        T(1296, 1201, cents=131.795),
        T(36, 25, cents=631.283),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Harmonic Square Means in Tetrachords between 1/1 and 4/3 and 3/2 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=213,
        function=f,
    )


def xen18_ayers_table_39(f):
    ratios_and_cents = [
        (1.05045, 85.2114),
        (1.1094, 179.736),
        (1.17954, 285.863),
        (1.26491, 406.843),
        (1.37199, 547.522),
        (1.51186, 715.587),
        (1.70561, 924.341),
        (2.0, 1200.0),
    ]
    for ratio, cents in ratios_and_cents:
        assert abs(1200 * log2(ratio) - cents) < 0.01
    tones = [T(cents) for _, cents in ratios_and_cents]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Root Harmonic Square Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=213,
        function=f,
    )


def xen18_ayers_table_40(f):
    ratios_and_cents = [
        (1.06051, 101.711),
        (1.12468, 203.422),
        (1.19274, 305.132),
        (1.26491, 406.843),
        (1.34145, 508.554),
        (1.42262, 610.265),
        (1.50871, 711.976),
        (1.6, 813.686),
    ]
    for ratio, cents in ratios_and_cents:
        assert abs(1200 * log2(ratio) - cents) < 0.01
    tones = [T(cents) for _, cents in ratios_and_cents]
    assert len(tones) == 8
    return build_scl(
        description="7 Generalized Root Harmonic Square Means between 1.0 and 1.6",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=214,
        function=f,
    )


def xen18_ayers_table_41_42(f):
    tones = [
        T(6, 5, cents=315.641),
        T(5, 4, cents=386.314),
        T(4, 3, cents=498.045),
        T(3, 2, cents=701.955),
        T(8, 5, cents=813.686),
        T(5, 3, cents=884.359),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Fibonacci-Type Means scale from Table 41 and Table 42",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=214,
        function=f,
    )


def xen18_ayers_table_43(f):
    tones = [
        T(3, 2, cents=701.955),
        T(8, 5, cents=813.686),
        T(21, 13, cents=830.254),
        T(55, 34, cents=832.676),
        T(34, 21, cents=834.174),
        T(13, 8, cents=840.528),
        T(5, 3, cents=884.359),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 8
    return build_scl(
        description="7 Fibonacci-Type Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=215,
        function=f,
    )


def xen18_ayers_table_44(f):
    tones = [
        T(16, 15, cents=111.731),
        T(13, 12, cents=138.572),
        T(4, 3, cents=498.045),
        T(3, 2, cents=701.955),
        T(8, 5, cents=813.686),
        T(13, 8, cents=840.528),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Transposing 3 Fibonacci-Type Means to Lower Tetrachord Between 1/1 and 4/3",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=215,
        function=f,
    )


def xen18_ayers_table_45(f):
    tones = [
        T(6, 5, cents=315.641),
        T(26, 21, cents=369.747),
        T(4, 3, cents=498.045),
        T(3, 2, cents=701.955),
        T(21, 13, cents=830.253),
        T(5, 3, cents=884.359),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 7
    return build_scl(
        description="Complementary Ratios to 3 Fibonacci-Type Means for Lower Tetrachord Between 1/1 and 4/3",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=215,
        function=f,
    )


def xen18_ayers_table_46(f):
    ratios_and_cents = [
        (1.11615, 190.236),
        (1.19458, 307.809),
        (1.33333, 498.045),
    ]
    for ratio, cents in ratios_and_cents:
        assert abs(1200 * log2(ratio) - cents) < 0.01
    tones = [T(cents) for _, cents in ratios_and_cents]
    assert len(tones) == 3
    return build_scl(
        description="Reciprocals of Golden Mean in P4",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=215,
        function=f,
    )


def xen18_ayers_table_47(f):
    ratios_and_cents = [
        (1.10642, 175.078),
        (1.17778, 283.282),
        (1.30312, 458.359),
        (1.53478, 741.641),
        (2.0, 1200.0),
    ]
    for ratio, cents in ratios_and_cents:
        assert abs(1200 * log2(ratio) - cents) < 0.01
    tones = [T(cents) for _, cents in ratios_and_cents]
    assert len(tones) == 5
    return build_scl(
        description="Reciprocals of Golden Mean in Octave",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=215,
        function=f,
    )


def xen18_ayers_table_48(f):
    ratios_and_cents = [
        (1.17778, 283.282),
        (1.30312, 458.359),
        (1.44179, 633.437),
        (1.53478, 741.641),
        (1.69811, 916.719),
        (1.80763, 1024.92),
        (1.92422, 1133.13),
        (2.0, 1200.0),
    ]
    for ratio, cents in ratios_and_cents:
        assert abs(1200 * log2(ratio) - cents) < 0.01
    tones = [T(cents) for _, cents in ratios_and_cents]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Reciprocals of Golden Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=216,
        function=f,
    )


def xen18_ayers_table_49(f):
    tones = [
        T(5, 4, cents=386.314),
        T(4, 3, cents=498.045),
        T(40, 27, cents=680.449),
        T(3, 2, cents=701.955),
        T(9, 5, cents=1017.596),
        T(15, 8, cents=1088.269),
        T(255, 128, cents=1193.224),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated First Unnamed Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=216,
        function=f,
    )


def xen18_ayers_table_54(f):
    tones = [
        T(35, 27, cents=449.275),
        T(13, 9, cents=636.618),
        T(43, 27, cents=805.653),
        T(5, 3, cents=884.359),
        T(49, 27, cents=1031.79),
        T(17, 9, cents=1101.05),
        T(53, 27, cents=1167.64),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated First Unnamed Means between 1/1 and 2/1, Weighted by Ratio 3/2",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=217,
        function=f,
    )


def xen18_ayers_table_55(f):
    tones = [
        T(7, 6),
        T(4, 3),
        T(3, 2),
        T(5, 3),
        T(11, 6),
        T(2, 1),
        T(13, 12),
    ]
    assert len(tones) == 7
    return build_scl(
        description="First Unnamed Mean scale from window in Table 55",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=217,
        function=f,
    )


def xen18_ayers_table_56(f):
    tones = [
        T(43, 42, cents=40.737),
        T(7, 6, cents=266.871),
        T(67, 54, cents=373.442),
        T(3, 2, cents=701.955),
        T(157, 104, cents=713.017),
        T(13, 8, cents=840.528),
        T(217, 128, cents=913.862),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Second Unnamed Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=218,
        function=f,
    )


def xen18_ayers_table_59(f):
    tones = [
        T(28, 27, cents=62.961),
        T(10, 9, cents=182.404),
        T(32, 27, cents=294.135),
        T(4, 3, cents=498.045),
        T(38, 27, cents=591.648),
        T(14, 9, cents=764.916),
        T(46, 27, cents=922.409),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Second Unnamed Means between 1/1 and 2/1, Weighted by Ratio 3/2",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=218,
        function=f,
    )


def xen18_ayers_table_61(f):
    ratios_and_cents = [
        (1.32564, 488.029),
        (1.43168, 621.255),
        (1.59858, 812.148),
        (1.61803, 833.090),
        (1.89103, 1103.005),
        (1.93709, 1144.667),
        (1.99808, 1198.337),
        (2.0, 1200.0),
    ]
    for ratio, cents in ratios_and_cents:
        assert abs(1200 * log2(ratio) - cents) < 0.01
    tones = [T(cents) for _, cents in ratios_and_cents]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Third Unnamed Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=219,
        function=f,
    )


def xen18_ayers_table_62(f):
    tones = [
        T(256, 255, cents=6.776),
        T(16, 15, cents=111.731),
        T(10, 9, cents=182.404),
        T(4, 3, cents=498.045),
        T(27, 20, cents=519.551),
        T(3, 2, cents=701.955),
        T(8, 5, cents=813.686),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Fourth Unnamed Means between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=220,
        function=f,
    )


def xen18_ayers_table_63(f):
    tones = [
        T(6, 5, cents=315.641),
        T(5, 4, cents=386.314),
        T(4, 3, cents=498.045),
    ]
    assert len(tones) == 3
    return build_scl(
        description="Didymos' Chromatic Tetrachord",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=220,
        function=f,
    )


def xen18_ayers_table_64(f):
    tones = [
        T(5, 4, cents=386.314),
        T(9, 7, cents=435.084),
        T(4, 3, cents=498.045),
    ]
    assert len(tones) == 3
    return build_scl(
        description="Archytas' Enharmonic Tetrachord",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=220,
        function=f,
    )


def xen18_ayers_table_65(f):
    tones = [
        T(5, 4, cents=386.314),
        T(4, 3, cents=498.045),
        T(7, 5, cents=582.512),
        T(3, 2, cents=701.955),
        T(8, 5, cents=813.686),
        T(5, 3, cents=884.359),
        T(7, 4, cents=968.826),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 8
    return build_scl(
        description="7 Iterated Mediants between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=220,
        function=f,
    )


def xen18_ayers_table_71(f):
    tones = [
        T(6, 5, cents=315.641),
        T(5, 4, cents=386.314),
        T(4, 3, cents=498.045),
        T(3, 2, cents=701.955),
        T(5, 3, cents=884.359),
        T(7, 4, cents=968.826),
        T(9, 5, cents=1017.596),
        T(2, 1, cents=1200.0),
    ]
    assert len(tones) == 8
    return build_scl(
        description="7 Weighted Mediants between 1/1 and 2/1",
        tones=tones,
        title="Making Scales from Mathematical Means",
        page=222,
        function=f,
    )


def xen18_darreg_djami_17(f):
    notes = [
        90,
        180,
        204,
        294,
        384,
        408,
        498,
        588,
        678,
        702,
        792,
        882,
        906,
        996,
        1086,
        1176,
        1200,
    ]
    steps = [90, 90, 24, 90, 90, 24, 90, 90, 90, 24, 90, 90, 24, 90, 90, 90, 24]
    assert notes == csum(steps)
    tones = [T(float(x)) for x in notes]
    assert len(tones) == 17
    return build_scl(
        description="Seventeen-tone system",
        tones=tones,
        title='Abdurakhman Djami\'s "Treatise on Music", translated from the Russian by Ivor Darreg',
        page=228,
        function=f,
    )


def xen18_darreg_djami_ushshak(f):
    notes = [204, 408, 498, 702, 906, 996, 1200]
    steps = [204, 204, 90, 204, 204, 90, 204]
    assert notes == csum(steps)
    tones = [T(float(x)) for x in notes]
    assert len(tones) == 7
    return build_scl(
        description="Maqam Ushshak",
        tones=tones,
        title='Abdurakhman Djami\'s "Treatise on Music", translated from the Russian by Ivor Darreg',
        page=233,
        function=f,
    )


def xen18_darreg_djami_nawa(f):
    notes = [204, 294, 498, 702, 792, 996, 1200]
    steps = [204, 90, 204, 204, 90, 204, 204]
    assert notes == csum(steps)
    tones = [T(float(x)) for x in notes]
    assert len(tones) == 7
    return build_scl(
        description="Maqam Nawa",
        tones=tones,
        title='Abdurakhman Djami\'s "Treatise on Music", translated from the Russian by Ivor Darreg',
        page=233,
        function=f,
    )


def xen18_darreg_djami_busalik(f):
    notes = [90, 294, 498, 588, 792, 996, 1200]
    steps = [90, 204, 204, 90, 204, 204, 204]
    assert notes == csum(steps)
    tones = [T(float(x)) for x in notes]
    assert len(tones) == 7
    return build_scl(
        description="Maqam Busalik",
        tones=tones,
        title='Abdurakhman Djami\'s "Treatise on Music", translated from the Russian by Ivor Darreg',
        page=233,
        function=f,
    )


def xen18_darreg_djami_rast(f):
    notes = [204, 384, 498, 702, 882, 996, 1200]
    steps = [204, 180, 114, 204, 180, 114, 204]
    assert notes == csum(steps)
    tones = [T(float(x)) for x in notes]
    assert len(tones) == 7
    return build_scl(
        description="Maqam Rast",
        tones=tones,
        title='Abdurakhman Djami\'s "Treatise on Music", translated from the Russian by Ivor Darreg',
        page=234,
        function=f,
    )


def xen18_darreg_djami_husayni(f):
    notes = [180, 294, 498, 678, 792, 996, 1200]
    steps = [180, 114, 204, 180, 114, 204, 204]
    assert notes == csum(steps)
    tones = [T(float(x)) for x in notes]
    assert len(tones) == 7
    return build_scl(
        description="Maqam Husayni",
        tones=tones,
        title='Abdurakhman Djami\'s "Treatise on Music", translated from the Russian by Ivor Darreg',
        page=234,
        function=f,
    )


def xen18_darreg_djami_hidjaz(f):
    notes = [180, 294, 498, 678, 882, 996, 1200]
    steps = [180, 114, 204, 180, 204, 114, 204]
    assert notes == csum(steps)
    tones = [T(float(x)) for x in notes]
    assert len(tones) == 7
    return build_scl(
        description="Maqam Hidjaz",
        tones=tones,
        title='Abdurakhman Djami\'s "Treatise on Music", translated from the Russian by Ivor Darreg',
        page=234,
        function=f,
    )


def xen18_darreg_djami_rahawi(f):
    notes = [180, 384, 498, 678, 792, 996, 1200]
    steps = [180, 204, 114, 180, 114, 204, 204]
    assert notes == csum(steps)
    tones = [T(float(x)) for x in notes]
    assert len(tones) == 7
    return build_scl(
        description="Maqam Rahawi",
        tones=tones,
        title='Abdurakhman Djami\'s "Treatise on Music", translated from the Russian by Ivor Darreg',
        page=234,
        function=f,
    )


def xen18_darreg_djami_zangule(f):
    notes = [204, 384, 498, 678, 882, 996, 1200]
    steps = [204, 180, 114, 180, 204, 114, 204]
    assert notes == csum(steps)
    tones = [T(float(x)) for x in notes]
    assert len(tones) == 7
    return build_scl(
        description="Maqam Zangule",
        tones=tones,
        title='Abdurakhman Djami\'s "Treatise on Music", translated from the Russian by Ivor Darreg',
        page=234,
        function=f,
    )


def xen18_darreg_djami_iraq_1(f):
    notes = [180, 384, 498, 678, 882, 996, 1200]
    steps = [180, 204, 114, 180, 204, 114, 204]
    assert notes == csum(steps)
    tones = [T(float(x)) for x in notes]
    assert len(tones) == 7
    return build_scl(
        description="Maqam Iraq, without bakiye",
        tones=tones,
        title='Abdurakhman Djami\'s "Treatise on Music", translated from the Russian by Ivor Darreg',
        page=234,
        function=f,
    )


def xen18_darreg_djami_iraq_2(f):
    notes = [180, 384, 498, 678, 882, 996, 1176, 1200]
    steps = [180, 204, 114, 180, 204, 114, 180, 24]
    assert notes == csum(steps)
    tones = [T(float(x)) for x in notes]
    assert len(tones) == 8
    return build_scl(
        description="Maqam Iraq, with bakiye",
        tones=tones,
        title='Abdurakhman Djami\'s "Treatise on Music", translated from the Russian by Ivor Darreg',
        page=234,
        function=f,
    )


def xen18_darreg_djami_isfahan_1(f):
    notes = [204, 384, 498, 702, 882, 996, 1176, 1200]
    steps = [204, 180, 114, 204, 180, 114, 180, 24]
    assert notes == csum(steps)
    tones = [T(float(x)) for x in notes]
    assert len(tones) == 8
    return build_scl(
        description="Maqam Isfahan, bakiye between seventh and eighth degrees",
        tones=tones,
        title='Abdurakhman Djami\'s "Treatise on Music", translated from the Russian by Ivor Darreg',
        page=235,
        function=f,
    )


def xen18_darreg_djami_isfahan_2(f):
    notes = [180, 294, 498, 678, 792, 906, 996, 1200]
    steps = [180, 114, 204, 180, 114, 114, 90, 204]
    assert notes == csum(steps)
    tones = [T(float(x)) for x in notes]
    assert len(tones) == 8
    return build_scl(
        description="Maqam Isfahan, bakiye between sixth and seventh degrees",
        tones=tones,
        title='Abdurakhman Djami\'s "Treatise on Music", translated from the Russian by Ivor Darreg',
        page=235,
        function=f,
    )


def xen18_mitchell_fractal_1(f):
    lengths = [
        100.0,
        96.70,
        90.35,
        83.82,
        77.40,
        70.71,
        66.15,
        61.45,
        57.05,
        52.45,
        50.0,
    ]
    tones = [T(1200 * log2(lengths[0] / x), comment=str(x)) for x in lengths[1:]]
    assert len(tones) == 10
    return build_scl(
        description="Geordan's Scale, by eyeball",
        tones=tones,
        title="Fractal Tone Monochord Octave",
        page=245,
        function=f,
    )


def xen18_mitchell_fractal_2(f):
    lengths = [
        100.0,
        96.75,
        90.27,
        83.79,
        77.31,
        70.83,
        66.20,
        61.57,
        56.94,
        52.31,
        50.0,
    ]
    tones = [T(1200 * log2(lengths[0] / x), comment=str(x)) for x in lengths[1:]]
    assert len(tones) == 10
    return build_scl(
        description="Geordan's Scale, Erv Wilson's calculation",
        tones=tones,
        title="Fractal Tone Monochord Octave",
        page=245,
        function=f,
    )


def main():
    logger.info("Building Xenharmonikon scales")
    output_dir = SCALES_DIR / "xenharmonikon"
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir()

    # Call functions to generate scl files
    count = 0
    last = ""
    references = {}
    for k, v in globals().items():
        if k.startswith("xen"):
            # Call each function with its name as argument
            filename, scl_text, reference = v(k)
            references[filename] = reference
            (output_dir / filename).write_text(scl_text)
            count += 1
            last = k
    logger.info("Called %s functions", count)
    logger.info("Last called: %s", last)
    return utils.check_scl_dir(output_dir), references


if __name__ == "__main__":
    utils.setup_logging()
    main()
