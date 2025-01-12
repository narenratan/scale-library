"""
Write out scl files for the Divisions of the Tetrachord catalog.

For Chalmers' Divisions of the Tetrachord, see:

    https://eamusic.dartmouth.edu/~larry/published_articles/divisions_of_the_tetrachord/index.html

"""

import logging
import math
import shutil
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from typing import Optional

from sympy import Expr, Integer, Rational, evaluate, simplify, sqrt

from scale_library import SCALES_DIR, utils

logger = logging.getLogger(__name__)

F = Fraction
Step = Fraction | float

OUTPUT_DIR = SCALES_DIR / "divisions-of-the-tetrachord"
EPSILON = 1e-12
FILENAME = "{:03}_{}.scl"


class Genus:
    H1 = "H1"
    H2 = "H2"
    H3 = "H3"
    H4 = "H4"
    H5 = "H5"
    H6 = "H6"
    H7 = "H7"
    H8 = "H8"
    H9 = "H9"
    H10 = "H10"
    H11 = "H11"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"
    E5 = "E5"
    E6 = "E6"
    E7 = "E7"
    E8 = "E8"
    E9 = "E9"
    E10 = "E10"
    E11 = "E11"
    E12 = "E12"
    E13 = "E13"
    E14 = "E14"
    E15 = "E15"
    E16 = "E16"
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"
    C5 = "C5"
    C6 = "C6"
    C7 = "C7"
    C8 = "C8"
    C9 = "C9"
    C10 = "C10"
    C11 = "C11"
    C12 = "C12"
    C13 = "C13"
    C14 = "C14"
    C15 = "C15"
    C16 = "C16"
    C17 = "C17"
    C18 = "C18"
    C19 = "C19"
    C20 = "C20"
    C21 = "C21"
    C22 = "C22"
    C23 = "C23"
    C24 = "C24"
    C25 = "C25"
    C26 = "C26"
    C27 = "C27"
    C28 = "C28"
    C29 = "C29"
    D1 = "D1"
    D2 = "D2"
    D3 = "D3"
    D4 = "D4"
    D5 = "D5"
    D6 = "D6"
    D7 = "D7"
    D8 = "D8"
    D9 = "D9"
    D10 = "D10"
    D11 = "D11"
    D12 = "D12"
    D13 = "D13"
    D14 = "D14"
    D15 = "D15"
    D16 = "D16"
    D17 = "D17"


G = Genus


CHARACTERISTIC_INTERVAL = {
    G.H1: F(13, 10),
    G.H2: F(35, 27),
    G.H3: F(22, 17),
    G.H4: F(128, 99),
    G.H5: F(31, 24),
    G.H6: F(40, 31),
    G.H7: F(58, 45),
    G.H8: F(9, 7),
    G.H9: F(104, 81),
    G.H10: F(50, 39),
    G.H11: F(32, 25),
    G.E1: F(23, 18),
    G.E2: F(88, 69),
    G.E3: F(51, 40),
    G.E4: F(14, 11),
    G.E5: F(80, 63),
    G.E6: F(33, 26),
    G.E7: F(19, 15),
    G.E8: F(81, 64),
    G.E9: F(24, 19),
    G.E10: F(34, 27),
    G.E11: F(113, 90),
    G.E12: F(64, 51),
    G.E13: F(5, 4),
    G.E14: F(8192, 6561),
    G.E15: F(56, 45),
    G.E16: F(41, 33),
    G.C1: F(36, 29),
    G.C2: F(26, 21),
    G.C3: F(21, 17),
    G.C4: F(100, 81),
    G.C5: F(37, 30),
    G.C6: F(16, 13),
    G.C7: F(27, 22),
    G.C8: F(11, 9),
    G.C9: F(39, 32),
    G.C10: F(28, 23),
    G.C11: F(17, 14),
    G.C12: F(40, 33),
    G.C13: F(29, 24),
    G.C14: F(6, 5),
    G.C15: F(25, 21),
    G.C16: F(19, 16),
    G.C17: F(32, 27),
    G.C18: F(45, 38),
    G.C19: F(13, 11),
    G.C20: F(33, 28),
    G.C21: F(20, 17),
    G.C22: F(27, 23),
    G.C23: F(75, 64),
    G.C24: F(7, 6),
    G.C25: F(136, 117),
    G.C26: F(36, 31),
    G.C27: F(80, 69),
    G.C28: F(22, 19),
    G.C29: F(52, 45),
    G.D1: F(15, 13),
    G.D2: F(38, 33),
    G.D3: F(23, 20),
    G.D4: F(31, 27),
    G.D5: F(39, 34),
    G.D6: F(8, 7),
    G.D7: F(256, 225),
    G.D8: F(25, 22),
    G.D9: F(92, 81),
    G.D10: F(76, 67),
    G.D11: F(17, 15),
    G.D12: F(112, 99),
    G.D13: F(44, 39),
    G.D14: F(152, 135),
    G.D15: F(9, 8),
    G.D16: F(160, 143),
    G.D17: F(10, 9),
}


class Reference:
    al_farabi = "Al-Farabi"
    anonymous = "Anonymous"
    archytas = "Archytas"
    aristides_quintilianus = "Aristides Quint."
    aristoxenos = "Aristoxenos"
    athanasopoulos = "Athanasopoulos"
    avicenna = "Avicenna"
    barbour = "Barbour"
    boethius = "Boethius"
    chapter_3 = "Chapter 3"
    chapter_4 = "Chapter 4"
    chapter_5 = "Chapter 5"
    danielou = "Daniélou"
    didymos = "Didymos"
    eratosthenes = "Eratosthenes"
    euler = "Euler"
    fox_strangways = "Fox-Strangways"
    gaudentius = "Gaudentius"
    helmholtz = "Helmholtz"
    hipkins = "Hipkins"
    hofmann = "Hofmann"
    kornerup = "Kornerup"
    macran = "Macran"
    pachymeres = "Pachymeres"
    palmer = "Palmer"
    partch = "Partch"
    perrett = "Perrett"
    ps_philolaus = "Ps.-Philolaus"
    ptolemy = "Ptolemy"
    pythagoras = "Pythagoras"
    safiyu_d_din = "Safiyu-d-Din"
    salinas = "Salinas"
    savas = "Savas"
    schlesinger = "Schlesinger"
    tiby = "Tiby"
    vogel = "Vogel"
    wilson = "Wilson"
    winnington_ingram = "Winnington-Ingram"
    xenakis = "Xenakis"
    young = "Young"


R = Reference


@dataclass(frozen=True)
class Tetrachord:
    index: int
    steps: tuple[Step, Step, Step]
    genus: str
    reference: Optional[str] = None
    comment: Optional[str] = None

    def __post_init__(self):
        assert math.prod(self.steps) == F(4, 3)

    def to_scl(self):
        filename = FILENAME.format(self.index, self.genus)

        intervals = []
        current_interval = 1
        for step in self.steps:
            current_interval *= step
            intervals.append(current_interval)

        assert len(intervals) == 3
        assert intervals[-1] == F(4, 3)

        description = f"{category(self)} tetrachord " + " * ".join(
            str(x) for x in self.steps
        )
        if self.reference is not None:
            description += f", {self.reference}"

        scl_lines = [
            f"! {filename}",
            "!",
            description,
            " 3",
            "!",
        ] + [f" {x}" for x in intervals]

        if self.comment is not None:
            scl_lines += ["!", f"! {self.comment}"]

        scl_lines += [
            "!",
            "! Chalmers, John H. Divisions of the Tetrachord.",
            "! Frog Peak Music, 1993.",
            "!",
            "! [info]",
            "! source = Divisions of the Tetrachord",
            f"! catalog_index = {self.index}",
        ]

        scl_text = "\n".join(scl_lines) + "\n"

        return filename, scl_text


Part = int | float | Fraction


@dataclass(frozen=True)
class PartsTetrachord:
    index: int
    parts: tuple[Part, Part, Part]
    cents: tuple[int, int, int]
    genus: str
    fourth: Optional[float] = 500.0
    reference: Optional[str] = None
    comment: Optional[str] = None

    def to_scl(self):
        filename = FILENAME.format(self.index, self.genus)

        total_parts = sum(self.parts)
        steps = [self.fourth * x / total_parts for x in self.parts]
        for step, cents in zip(steps, self.cents):
            # Some printed cent values are rounded as e.g. 66.6666 -> 66
            assert abs(round(step) - cents) <= 1

        intervals = []
        current_interval = 0.0
        for step in steps:
            current_interval += step
            intervals.append(current_interval)

        assert len(intervals) == 3
        assert abs(intervals[-1] - self.fourth) < EPSILON

        description = "Aristoxenian style tetrachord " + " + ".join(
            str(x) for x in self.parts
        )
        if self.reference is not None:
            description += f", {self.reference}"

        scl_lines = [
            f"! {filename}",
            "!",
            description,
            " 3",
            "!",
        ] + [f" {round(x, 5)}" for x in intervals]

        if self.comment is not None:
            scl_lines += ["!", f"! {self.comment}"]

        scl_lines += [
            "!",
            "! [info]",
            "! source = Divisions of the Tetrachord",
            f"! catalog_index = {self.index}",
        ]

        scl_text = "\n".join(scl_lines) + "\n"

        return filename, scl_text


@dataclass(frozen=True)
class CentsTetrachord:
    index: int
    cents: tuple[float, float, float]
    genus: str
    reference: Optional[str] = None
    comment: Optional[str] = None

    def to_scl(self):
        filename = FILENAME.format(self.index, self.genus)

        intervals = []
        current_interval = 0.0
        for step in self.cents:
            current_interval += step
            intervals.append(current_interval)

        assert len(intervals) == 3
        assert abs(intervals[-1] - 500.0) <= 0.25

        description = "Tempered tetrachord in cents " + " + ".join(
            str(x) for x in self.cents
        )
        if self.reference is not None:
            description += f", {self.reference}"

        scl_lines = [
            f"! {filename}",
            "!",
            description,
            " 3",
            "!",
        ] + [f" {round(x, 5)}" for x in intervals]

        if self.comment is not None:
            scl_lines += ["!", f"! {self.comment}"]

        scl_lines += [
            "!",
            "! [info]",
            "! source = Divisions of the Tetrachord",
            f"! catalog_index = {self.index}",
        ]

        scl_text = "\n".join(scl_lines) + "\n"

        return filename, scl_text


@dataclass(frozen=True)
class SemiTemperedTetrachord:
    index: int
    steps: tuple[Expr | float, Expr | float, Expr | float]
    cents: tuple[int, int, int]
    genus: str
    reference: Optional[str] = None
    comment: Optional[str] = None

    def __post_init__(self):
        with evaluate(True):
            product = math.prod(self.steps)
            if isinstance(product, Expr):
                assert simplify(product) == Rational(4, 3)
            else:
                assert abs(1200 * math.log2(product / (4 / 3))) <= 0.15

    def to_scl(self):
        filename = FILENAME.format(self.index, self.genus)

        for step, cents in zip(self.steps, self.cents):
            assert abs(round(1200 * math.log2(step)) - cents) <= 1

        intervals = []
        current_interval = 1
        for step in self.steps:
            current_interval *= step
            intervals.append(simplify(current_interval))

        assert len(intervals) == 3

        scl_intervals = [
            x
            if isinstance(x, Expr) and x.is_rational
            else round(1200 * math.log2(x), 5)
            for x in intervals
        ]

        description = "Semi-tempered tetrachord " + " * ".join(
            str(x) for x in self.steps
        )
        if self.reference is not None:
            description += f", {self.reference}"

        scl_lines = [
            f"! {filename}",
            "!",
            description,
            " 3",
            "!",
        ] + [f" {x}" for x in scl_intervals]

        if self.comment is not None:
            scl_lines += ["!", f"! {self.comment}"]

        scl_lines += [
            "!",
            "! [info]",
            "! source = Divisions of the Tetrachord",
            f"! catalog_index = {self.index}",
        ]

        scl_text = "\n".join(scl_lines) + "\n"

        return filename, scl_text


CATALOG = [
    #
    # MAIN CATALOG
    #
    Tetrachord(index=1, genus=G.H1, steps=(F(80, 79), F(79, 78), F(13, 10))),
    Tetrachord(
        index=2,
        genus=G.H1,
        steps=(F(60, 59), F(118, 117), F(13, 10)),
        comment="Originally printed as 60/49 * 118/117 * 13/10",
    ),
    Tetrachord(index=3, genus=G.H1, steps=(F(120, 119), F(119, 117), F(13, 10))),
    Tetrachord(
        index=4,
        genus=G.H1,
        steps=(F(100, 99), F(66, 65), F(13, 10)),
        reference=R.wilson,
    ),
    #
    Tetrachord(index=5, genus=G.H2, steps=(F(72, 71), F(71, 70), F(35, 27))),
    Tetrachord(index=6, genus=G.H2, steps=(F(108, 107), F(107, 105), F(35, 27))),
    Tetrachord(index=7, genus=G.H2, steps=(F(54, 53), F(106, 105), F(35, 27))),
    Tetrachord(index=8, genus=G.H2, steps=(F(64, 63), F(81, 80), F(35, 27))),
    #
    Tetrachord(index=9, genus=G.H3, steps=(F(68, 67), F(67, 66), F(22, 17))),
    Tetrachord(index=10, genus=G.H3, steps=(F(51, 50), F(100, 99), F(22, 17))),
    Tetrachord(index=11, genus=G.H3, steps=(F(102, 101), F(101, 99), F(22, 17))),
    Tetrachord(
        index=12,
        genus=G.H3,
        steps=(F(85, 84), F(56, 55), F(22, 17)),
        reference=R.wilson,
    ),
    #
    Tetrachord(index=13, genus=G.H4, steps=(F(66, 65), F(65, 64), F(128, 99))),
    Tetrachord(index=14, genus=G.H4, steps=(F(99, 98), F(49, 48), F(128, 99))),
    Tetrachord(index=15, genus=G.H4, steps=(F(99, 97), F(97, 96), F(128, 99))),
    #
    Tetrachord(index=16, genus=G.H5, steps=(F(64, 63), F(63, 62), F(31, 24))),
    Tetrachord(index=17, genus=G.H5, steps=(F(96, 95), F(95, 93), F(31, 24))),
    Tetrachord(index=18, genus=G.H5, steps=(F(48, 47), F(94, 93), F(31, 24))),
    #
    Tetrachord(index=19, genus=G.H6, steps=(F(62, 61), F(61, 60), F(40, 31))),
    Tetrachord(index=20, genus=G.H6, steps=(F(93, 92), F(46, 45), F(40, 31))),
    Tetrachord(index=21, genus=G.H6, steps=(F(93, 91), F(91, 90), F(40, 31))),
    #
    Tetrachord(index=22, genus=G.H7, steps=(F(60, 59), F(59, 58), F(58, 45))),
    Tetrachord(index=23, genus=G.H7, steps=(F(90, 89), F(89, 87), F(58, 45))),
    Tetrachord(index=24, genus=G.H7, steps=(F(45, 44), F(88, 87), F(58, 45))),
    Tetrachord(index=25, genus=G.H7, steps=(F(120, 119), F(119, 116), F(58, 45))),
    #
    Tetrachord(
        index=26, genus=G.H8, steps=(F(56, 55), F(55, 54), F(9, 7)), reference=R.wilson
    ),
    Tetrachord(index=27, genus=G.H8, steps=(F(42, 41), F(82, 81), F(9, 7))),
    Tetrachord(index=28, genus=G.H8, steps=(F(84, 83), F(83, 81), F(9, 7))),
    Tetrachord(index=29, genus=G.H8, steps=(F(64, 63), F(49, 48), F(9, 7))),
    Tetrachord(index=30, genus=G.H8, steps=(F(70, 69), F(46, 45), F(9, 7))),
    Tetrachord(index=31, genus=G.H8, steps=(F(40, 39), F(91, 90), F(9, 7))),
    Tetrachord(index=32, genus=G.H8, steps=(F(112, 111), F(37, 36), F(9, 7))),
    Tetrachord(index=33, genus=G.H8, steps=(F(81, 80), F(2240, 2187), F(9, 7))),
    Tetrachord(index=34, genus=G.H8, steps=(F(9, 7), F(119, 117), F(52, 51))),
    #
    Tetrachord(index=35, genus=G.H9, steps=(F(54, 53), F(53, 52), F(104, 81))),
    Tetrachord(index=36, genus=G.H9, steps=(F(81, 79), F(79, 78), F(104, 81))),
    Tetrachord(index=37, genus=G.H9, steps=(F(81, 80), F(40, 39), F(104, 81))),
    #
    Tetrachord(index=38, genus=G.H10, steps=(F(52, 51), F(51, 50), F(50, 39))),
    Tetrachord(index=39, genus=G.H10, steps=(F(39, 38), F(76, 75), F(50, 39))),
    Tetrachord(index=40, genus=G.H10, steps=(F(78, 77), F(77, 75), F(50, 39))),
    #
    Tetrachord(index=41, genus=G.H11, steps=(F(50, 49), F(49, 48), F(32, 25))),
    Tetrachord(index=42, genus=G.H11, steps=(F(75, 73), F(73, 72), F(32, 25))),
    Tetrachord(index=43, genus=G.H11, steps=(F(75, 74), F(37, 36), F(32, 25))),
    #
    Tetrachord(
        index=44,
        genus=G.E1,
        steps=(F(48, 47), F(47, 46), F(23, 18)),
        reference=R.schlesinger,
    ),
    Tetrachord(
        index=45,
        genus=G.E1,
        steps=(F(36, 35), F(70, 69), F(23, 18)),
        reference=R.wilson,
    ),
    Tetrachord(index=46, genus=G.E1, steps=(F(72, 71), F(71, 69), F(23, 18))),
    Tetrachord(
        index=47,
        genus=G.E1,
        steps=(F(30, 29), F(116, 115), F(23, 18)),
        reference=R.wilson,
    ),
    Tetrachord(index=48, genus=G.E1, steps=(F(60, 59), F(118, 115), F(23, 18))),
    #
    Tetrachord(index=49, genus=G.E2, steps=(F(46, 45), F(45, 44), F(88, 69))),
    Tetrachord(index=50, genus=G.E2, steps=(F(69, 67), F(67, 66), F(88, 69))),
    Tetrachord(index=51, genus=G.E2, steps=(F(69, 68), F(34, 33), F(88, 69))),
    #
    Tetrachord(index=52, genus=G.E3, steps=(F(320, 313), F(313, 306), F(51, 40))),
    Tetrachord(index=53, genus=G.E3, steps=(F(480, 473), F(473, 459), F(51, 40))),
    Tetrachord(index=54, genus=G.E3, steps=(F(240, 233), F(466, 459), F(51, 40))),
    #
    Tetrachord(index=55, genus=G.E4, steps=(F(44, 43), F(43, 42), F(14, 11))),
    Tetrachord(index=56, genus=G.E4, steps=(F(33, 32), F(64, 63), F(14, 11))),
    Tetrachord(index=57, genus=G.E4, steps=(F(66, 65), F(65, 63), F(14, 11))),
    Tetrachord(index=58, genus=G.E4, steps=(F(88, 87), F(29, 28), F(14, 11))),
    Tetrachord(index=59, genus=G.E4, steps=(F(36, 35), F(55, 54), F(14, 11))),
    Tetrachord(index=60, genus=G.E4, steps=(F(50, 49), F(77, 75), F(14, 11))),
    Tetrachord(index=61, genus=G.E4, steps=(F(14, 11), F(143, 140), F(40, 39))),
    #
    Tetrachord(index=62, genus=G.E5, steps=(F(42, 41), F(41, 40), F(80, 63))),
    Tetrachord(index=63, genus=G.E5, steps=(F(63, 61), F(61, 60), F(80, 63))),
    Tetrachord(index=64, genus=G.E5, steps=(F(63, 62), F(31, 30), F(80, 63))),
    #
    Tetrachord(index=65, genus=G.E6, steps=(F(208, 203), F(203, 198), F(33, 26))),
    Tetrachord(index=66, genus=G.E6, steps=(F(312, 307), F(307, 297), F(33, 26))),
    Tetrachord(index=67, genus=G.E6, steps=(F(312, 302), F(302, 297), F(33, 26))),
    Tetrachord(index=68, genus=G.E6, steps=(F(52, 51), F(34, 33), F(33, 26))),
    Tetrachord(index=69, genus=G.E6, steps=(F(26, 25), F(100, 99), F(33, 26))),
    Tetrachord(index=70, genus=G.E6, steps=(F(78, 77), F(28, 27), F(33, 26))),
    #
    Tetrachord(
        index=71,
        genus=G.E7,
        steps=(F(40, 39), F(39, 38), F(19, 15)),
        reference=R.eratosthenes,
    ),
    Tetrachord(index=72, genus=G.E7, steps=(F(30, 29), F(58, 57), F(19, 15))),
    Tetrachord(index=73, genus=G.E7, steps=(F(60, 59), F(59, 57), F(19, 15))),
    Tetrachord(index=74, genus=G.E7, steps=(F(28, 27), F(135, 133), F(19, 15))),
    #
    Tetrachord(
        index=75,
        genus=G.E8,
        steps=(F(512, 499), F(499, 486), F(81, 64)),
        reference=R.boethius,
    ),
    Tetrachord(index=76, genus=G.E8, steps=(F(384, 371), F(742, 729), F(81, 64))),
    Tetrachord(index=77, genus=G.E8, steps=(F(768, 755), F(755, 729), F(81, 64))),
    Tetrachord(index=78, genus=G.E8, steps=(F(40, 39), F(416, 405), F(81, 64))),
    Tetrachord(
        index=79,
        genus=G.E8,
        steps=(F(128, 125), F(250, 243), F(81, 64)),
        reference=R.euler,
    ),
    Tetrachord(
        index=80,
        genus=G.E8,
        steps=(F(64, 63), F(28, 27), F(81, 64)),
        reference=R.wilson,
    ),
    Tetrachord(
        index=81, genus=G.E8, steps=(F(3**24, 2**38), F(2**46, 3**29), F(81, 64))
    ),
    Tetrachord(index=82, genus=G.E8, steps=(F(36, 35), F(2240, 2187), F(81, 64))),
    #
    Tetrachord(index=83, genus=G.E9, steps=(F(38, 37), F(37, 36), F(24, 19))),
    Tetrachord(index=84, genus=G.E9, steps=(F(57, 55), F(55, 54), F(24, 19))),
    Tetrachord(
        index=85,
        genus=G.E9,
        steps=(F(57, 56), F(28, 27), F(24, 19)),
        reference=R.wilson,
    ),
    Tetrachord(index=86, genus=G.E9, steps=(F(76, 75), F(25, 24), F(24, 19))),
    Tetrachord(
        index=87,
        genus=G.E9,
        steps=(F(40, 39), F(247, 240), F(24, 19)),
        comment="Originally printed as 40/39 * 117/95 * 24/19",
    ),
    #
    Tetrachord(index=88, genus=G.E10, steps=(F(36, 35), F(35, 34), F(34, 27))),
    Tetrachord(index=89, genus=G.E10, steps=(F(27, 26), F(52, 51), F(34, 27))),
    Tetrachord(index=90, genus=G.E10, steps=(F(54, 53), F(53, 51), F(34, 27))),
    Tetrachord(index=91, genus=G.E10, steps=(F(24, 23), F(69, 68), F(34, 27))),
    #
    Tetrachord(index=92, genus=G.E11, steps=(F(240, 233), F(233, 226), F(113, 90))),
    Tetrachord(index=93, genus=G.E11, steps=(F(180, 173), F(346, 339), F(113, 90))),
    Tetrachord(index=94, genus=G.E11, steps=(F(360, 353), F(353, 339), F(113, 90))),
    Tetrachord(index=95, genus=G.E11, steps=(F(30, 29), F(116, 113), F(113, 90))),
    Tetrachord(index=96, genus=G.E11, steps=(F(40, 39), F(117, 113), F(113, 90))),
    Tetrachord(index=97, genus=G.E11, steps=(F(60, 59), F(118, 113), F(113, 90))),
    #
    Tetrachord(index=98, genus=G.E12, steps=(F(34, 33), F(33, 32), F(64, 51))),
    Tetrachord(index=99, genus=G.E12, steps=(F(51, 50), F(25, 24), F(64, 51))),
    Tetrachord(index=100, genus=G.E12, steps=(F(49, 48), F(51, 49), F(64, 51))),
    Tetrachord(index=101, genus=G.E12, steps=(F(68, 65), F(65, 64), F(64, 51))),
    Tetrachord(index=102, genus=G.E12, steps=(F(68, 67), F(67, 64), F(64, 51))),
    #
    Tetrachord(
        index=103,
        genus=G.E13,
        steps=(F(32, 31), F(31, 30), F(5, 4)),
        reference=R.didymos,
    ),
    Tetrachord(
        index=104,
        genus=G.E13,
        steps=(F(46, 45), F(24, 23), F(5, 4)),
        reference=R.ptolemy,
    ),
    Tetrachord(
        index=105,
        genus=G.E13,
        steps=(F(48, 47), F(47, 45), F(5, 4)),
    ),
    Tetrachord(
        index=106,
        genus=G.E13,
        steps=(F(28, 27), F(36, 35), F(5, 4)),
        reference=R.archytas,
    ),
    Tetrachord(
        index=107,
        genus=G.E13,
        steps=(F(56, 55), F(22, 21), F(5, 4)),
        reference=R.ptolemy + "?",
    ),
    Tetrachord(
        index=108,
        genus=G.E13,
        steps=(F(40, 39), F(26, 25), F(5, 4)),
        reference=R.avicenna,
    ),
    Tetrachord(
        index=109,
        genus=G.E13,
        steps=(F(25, 24), F(128, 125), F(5, 4)),
        reference=R.salinas,
    ),
    Tetrachord(
        index=110,
        genus=G.E13,
        steps=(F(21, 20), F(64, 63), F(5, 4)),
        reference=R.pachymeres,
    ),
    Tetrachord(
        index=111,
        genus=G.E13,
        steps=(F(256, 243), F(81, 80), F(5, 4)),
        reference=R.fox_strangways + "?",
    ),
    Tetrachord(
        index=112,
        genus=G.E13,
        steps=(F(76, 75), F(20, 19), F(5, 4)),
    ),
    Tetrachord(
        index=113,
        genus=G.E13,
        steps=(F(96, 95), F(19, 18), F(5, 4)),
        reference=R.wilson,
    ),
    Tetrachord(
        index=114,
        genus=G.E13,
        steps=(F(136, 135), F(18, 17), F(5, 4)),
        reference=R.hofmann,
    ),
    Tetrachord(
        index=115,
        genus=G.E13,
        steps=(F(256, 255), F(17, 16), F(5, 4)),
        reference=R.hofmann,
    ),
    Tetrachord(
        index=116,
        genus=G.E13,
        steps=(F(68, 65), F(5, 4), F(52, 51)),
    ),
    #
    Tetrachord(
        index=117,
        genus=G.E14,
        steps=(F(4374, 4235), F(4235, 4096), F(8192, 6561)),
    ),
    Tetrachord(
        index=118,
        genus=G.E14,
        steps=(F(6561, 6283), F(6283, 6144), F(8192, 6561)),
    ),
    Tetrachord(
        index=119,
        genus=G.E14,
        steps=(F(6561, 6422), F(3211, 3072), F(8192, 6561)),
    ),
    Tetrachord(
        index=120,
        genus=G.E14,
        steps=(F(3**24, 2**38), F(2**27, 3**17), F(8192, 6561)),
    ),
    #
    Tetrachord(
        index=121,
        genus=G.E15,
        steps=(F(30, 29), F(29, 28), F(56, 45)),
        reference=R.ptolemy,
    ),
    Tetrachord(
        index=122,
        genus=G.E15,
        steps=(F(45, 43), F(43, 42), F(56, 45)),
    ),
    Tetrachord(
        index=123,
        genus=G.E15,
        steps=(F(45, 44), F(22, 21), F(56, 45)),
    ),
    Tetrachord(
        index=124,
        genus=G.E15,
        steps=(F(25, 24), F(36, 35), F(56, 45)),
    ),
    Tetrachord(
        index=125,
        genus=G.E15,
        steps=(F(80, 77), F(33, 32), F(56, 45)),
    ),
    Tetrachord(
        index=126,
        genus=G.E15,
        steps=(F(60, 59), F(59, 56), F(56, 45)),
    ),
    Tetrachord(
        index=127,
        genus=G.E15,
        steps=(F(40, 39), F(117, 112), F(56, 45)),
    ),
    Tetrachord(
        index=128,
        genus=G.E15,
        steps=(F(26, 25), F(375, 364), F(56, 45)),
    ),
    #
    Tetrachord(
        index=129,
        genus=G.E16,
        steps=(F(88, 85), F(85, 82), F(41, 33)),
    ),
    Tetrachord(
        index=130,
        genus=G.E16,
        steps=(F(42, 41), F(22, 21), F(41, 33)),
    ),
    Tetrachord(
        index=131,
        genus=G.E16,
        steps=(F(44, 43), F(43, 41), F(41, 33)),
    ),
    #
    Tetrachord(
        index=132,
        genus=G.C1,
        steps=(F(29, 28), F(28, 27), F(36, 29)),
    ),
    Tetrachord(
        index=133,
        genus=G.C1,
        steps=(F(87, 85), F(85, 81), F(36, 29)),
    ),
    Tetrachord(
        index=134,
        genus=G.C1,
        steps=(F(87, 83), F(83, 81), F(36, 29)),
    ),
    #
    Tetrachord(
        index=135,
        genus=G.C2,
        steps=(F(28, 27), F(27, 26), F(26, 21)),
        reference=R.schlesinger,
    ),
    Tetrachord(
        index=136,
        genus=G.C2,
        steps=(F(21, 20), F(40, 39), F(26, 21)),
    ),
    Tetrachord(
        index=137,
        genus=G.C2,
        steps=(F(42, 41), F(41, 39), F(26, 21)),
    ),
    Tetrachord(
        index=138,
        genus=G.C2,
        steps=(F(24, 23), F(161, 156), F(26, 21)),
    ),
    #
    Tetrachord(
        index=139,
        genus=G.C3,
        steps=(F(136, 131), F(131, 126), F(21, 17)),
    ),
    Tetrachord(
        index=140,
        genus=G.C3,
        steps=(F(102, 97), F(194, 189), F(21, 17)),
    ),
    Tetrachord(
        index=141,
        genus=G.C3,
        steps=(F(204, 199), F(199, 189), F(21, 17)),
    ),
    Tetrachord(
        index=142,
        genus=G.C3,
        steps=(F(64, 63), F(17, 16), F(21, 17)),
    ),
    Tetrachord(
        index=143,
        genus=G.C3,
        steps=(F(34, 33), F(22, 21), F(21, 17)),
    ),
    Tetrachord(
        index=144,
        genus=G.C3,
        steps=(F(40, 39), F(221, 210), F(21, 17)),
    ),
    Tetrachord(
        index=145,
        genus=G.C3,
        steps=(F(24, 23), F(391, 378), F(21, 17)),
    ),
    Tetrachord(
        index=146,
        genus=G.C3,
        steps=(F(28, 27), F(51, 49), F(21, 17)),
    ),
    #
    Tetrachord(
        index=147,
        genus=G.C4,
        steps=(F(27, 26), F(26, 25), F(100, 81)),
    ),
    Tetrachord(
        index=148,
        genus=G.C4,
        steps=(F(81, 77), F(77, 75), F(100, 81)),
    ),
    Tetrachord(
        index=149,
        genus=G.C4,
        steps=(F(81, 79), F(79, 75), F(100, 81)),
    ),
    Tetrachord(
        index=150,
        genus=G.C4,
        steps=(F(81, 80), F(16, 15), F(100, 81)),
    ),
    Tetrachord(
        index=151,
        genus=G.C4,
        steps=(F(51, 50), F(18, 17), F(100, 81)),
    ),
    Tetrachord(
        index=152,
        genus=G.C4,
        steps=(F(36, 35), F(21, 20), F(100, 81)),
    ),
    Tetrachord(
        index=153,
        genus=G.C4,
        steps=(F(40, 39), F(1053, 1000), F(100, 81)),
    ),
    Tetrachord(
        index=154,
        genus=G.C4,
        steps=(F(135, 128), F(128, 125), F(100, 81)),
        reference=R.danielou,
    ),
    Tetrachord(
        index=155,
        genus=G.C4,
        steps=(F(24, 23), F(207, 200), F(100, 81)),
    ),
    #
    Tetrachord(
        index=156,
        genus=G.C5,
        steps=(F(80, 77), F(77, 74), F(37, 30)),
        reference=R.ptolemy,
    ),
    Tetrachord(
        index=157,
        genus=G.C5,
        steps=(F(20, 19), F(38, 37), F(37, 30)),
    ),
    Tetrachord(
        index=158,
        genus=G.C5,
        steps=(F(40, 39), F(39, 37), F(37, 30)),
    ),
    Tetrachord(
        index=159,
        genus=G.C5,
        steps=(F(30, 29), F(116, 111), F(37, 30)),
    ),
    Tetrachord(
        index=160,
        genus=G.C5,
        steps=(F(60, 59), F(118, 111), F(37, 30)),
    ),
    #
    Tetrachord(
        index=161,
        genus=G.C6,
        steps=(F(26, 25), F(25, 24), F(16, 13)),
    ),
    Tetrachord(
        index=162,
        genus=G.C6,
        steps=(F(39, 37), F(37, 36), F(16, 13)),
    ),
    Tetrachord(
        index=163,
        genus=G.C6,
        steps=(F(39, 38), F(19, 18), F(16, 13)),
    ),
    Tetrachord(
        index=164,
        genus=G.C6,
        steps=(F(65, 64), F(16, 15), F(16, 13)),
    ),
    Tetrachord(
        index=165,
        genus=G.C6,
        steps=(F(52, 51), F(17, 16), F(16, 13)),
    ),
    Tetrachord(
        index=166,
        genus=G.C6,
        steps=(F(40, 39), F(169, 160), F(16, 13)),
    ),
    Tetrachord(
        index=167,
        genus=G.C6,
        steps=(F(28, 27), F(117, 112), F(16, 13)),
    ),
    Tetrachord(
        index=168,
        genus=G.C6,
        steps=(F(169, 168), F(14, 13), F(16, 13)),
    ),
    Tetrachord(
        index=169,
        genus=G.C6,
        steps=(F(22, 21), F(91, 88), F(16, 13)),
    ),
    #
    Tetrachord(
        index=170,
        genus=G.C7,
        steps=(F(176, 169), F(169, 162), F(27, 22)),
    ),
    Tetrachord(
        index=171,
        genus=G.C7,
        steps=(F(132, 125), F(250, 243), F(27, 22)),
    ),
    Tetrachord(
        index=172,
        genus=G.C7,
        steps=(F(264, 257), F(257, 243), F(27, 22)),
    ),
    Tetrachord(
        index=173,
        genus=G.C7,
        steps=(F(28, 27), F(22, 21), F(27, 22)),
    ),
    Tetrachord(
        index=174,
        genus=G.C7,
        steps=(F(55, 54), F(16, 15), F(27, 22)),
    ),
    Tetrachord(
        index=175,
        genus=G.C7,
        steps=(F(40, 39), F(143, 135), F(27, 22)),
    ),
    #
    Tetrachord(
        index=176,
        genus=G.C8,
        steps=(F(24, 23), F(23, 22), F(11, 9)),
        reference=R.winnington_ingram,
    ),
    Tetrachord(
        index=177,
        genus=G.C8,
        steps=(F(18, 17), F(34, 33), F(11, 9)),
    ),
    Tetrachord(
        index=178,
        genus=G.C8,
        steps=(F(36, 35), F(35, 33), F(11, 9)),
    ),
    Tetrachord(
        index=179,
        genus=G.C8,
        steps=(F(45, 44), F(16, 15), F(11, 9)),
    ),
    Tetrachord(
        index=180,
        genus=G.C8,
        steps=(F(56, 55), F(15, 14), F(11, 9)),
    ),
    Tetrachord(
        index=181,
        genus=G.C8,
        steps=(F(78, 77), F(14, 13), F(11, 9)),
    ),
    Tetrachord(
        index=182,
        genus=G.C8,
        steps=(F(20, 19), F(57, 55), F(11, 9)),
    ),
    Tetrachord(
        index=183,
        genus=G.C8,
        steps=(F(30, 29), F(58, 55), F(11, 9)),
    ),
    Tetrachord(
        index=184,
        genus=G.C8,
        steps=(F(28, 27), F(81, 77), F(11, 9)),
    ),
    Tetrachord(
        index=185,
        genus=G.C8,
        steps=(F(40, 39), F(117, 110), F(11, 9)),
    ),
    #
    Tetrachord(
        index=186,
        genus=G.C9,
        steps=(F(256, 245), F(245, 234), F(39, 32)),
    ),
    Tetrachord(
        index=187,
        genus=G.C9,
        steps=(F(384, 373), F(373, 351), F(39, 32)),
    ),
    Tetrachord(
        index=188,
        genus=G.C9,
        steps=(F(192, 181), F(362, 351), F(39, 32)),
    ),
    Tetrachord(
        index=189,
        genus=G.C9,
        steps=(F(64, 63), F(14, 13), F(39, 32)),
    ),
    #
    Tetrachord(
        index=190,
        genus=G.C10,
        steps=(F(23, 22), F(22, 21), F(28, 23)),
        reference=R.wilson,
    ),
    Tetrachord(
        index=191,
        genus=G.C10,
        steps=(F(69, 65), F(65, 63), F(28, 23)),
    ),
    Tetrachord(
        index=192,
        genus=G.C10,
        steps=(F(69, 67), F(67, 63), F(28, 23)),
    ),
    Tetrachord(
        index=193,
        genus=G.C10,
        steps=(F(46, 45), F(15, 14), F(28, 23)),
    ),
    #
    Tetrachord(
        index=194,
        genus=G.C11,
        steps=(F(112, 107), F(107, 102), F(17, 14)),
    ),
    Tetrachord(
        index=195,
        genus=G.C11,
        steps=(F(168, 158), F(158, 153), F(17, 14)),
    ),
    Tetrachord(
        index=196,
        genus=G.C11,
        steps=(F(168, 163), F(163, 153), F(17, 14)),
    ),
    Tetrachord(
        index=197,
        genus=G.C11,
        steps=(F(52, 51), F(14, 13), F(17, 14)),
    ),
    Tetrachord(
        index=198,
        genus=G.C11,
        steps=(F(28, 27), F(18, 17), F(17, 14)),
    ),
    Tetrachord(
        index=199,
        genus=G.C11,
        steps=(F(35, 34), F(16, 15), F(17, 14)),
    ),
    Tetrachord(
        index=200,
        genus=G.C11,
        steps=(F(40, 39), F(91, 85), F(17, 14)),
    ),
    Tetrachord(
        index=201,
        genus=G.C11,
        steps=(F(17, 14), F(56, 55), F(55, 51)),
    ),
    Tetrachord(
        index=202,
        genus=G.C11,
        steps=(F(17, 14), F(56, 53), F(53, 51)),
    ),
    #
    Tetrachord(
        index=203,
        genus=G.C12,
        steps=(F(22, 21), F(21, 20), F(40, 33)),
    ),
    Tetrachord(
        index=204,
        genus=G.C12,
        steps=(F(33, 31), F(31, 30), F(40, 33)),
        comment="Originally printed as 33/32 * 31/30 * 40/33",
    ),
    Tetrachord(
        index=205,
        genus=G.C12,
        steps=(F(33, 32), F(16, 15), F(40, 33)),
    ),
    Tetrachord(
        index=206,
        genus=G.C12,
        steps=(F(55, 54), F(27, 25), F(40, 33)),
    ),
    Tetrachord(
        index=207,
        genus=G.C12,
        steps=(F(66, 65), F(13, 12), F(40, 33)),
    ),
    Tetrachord(
        index=208,
        genus=G.C12,
        steps=(F(18, 17), F(187, 180), F(40, 33)),
    ),
    #
    Tetrachord(
        index=209,
        genus=G.C13,
        steps=(F(64, 61), F(61, 58), F(29, 24)),
    ),
    Tetrachord(
        index=210,
        genus=G.C13,
        steps=(F(16, 15), F(30, 29), F(29, 24)),
        reference=R.schlesinger,
    ),
    Tetrachord(
        index=211,
        genus=G.C13,
        steps=(F(32, 31), F(31, 29), F(29, 24)),
        reference=R.schlesinger,
    ),
    #
    Tetrachord(
        index=212,
        genus=G.C14,
        steps=(F(20, 19), F(19, 18), F(6, 5)),
        reference=R.eratosthenes,
    ),
    Tetrachord(
        index=213,
        genus=G.C14,
        steps=(F(28, 27), F(15, 14), F(6, 5)),
        reference=R.ptolemy,
    ),
    Tetrachord(
        index=214,
        genus=G.C14,
        steps=(F(30, 29), F(29, 27), F(6, 5)),
    ),
    Tetrachord(
        index=215,
        genus=G.C14,
        steps=(F(16, 15), F(25, 24), F(6, 5)),
        reference=R.didymos,
    ),
    Tetrachord(
        index=216,
        genus=G.C14,
        steps=(F(40, 39), F(13, 12), F(6, 5)),
        reference=R.barbour,
    ),
    Tetrachord(
        index=217,
        genus=G.C14,
        steps=(F(55, 54), F(12, 11), F(6, 5)),
        reference=R.barbour,
    ),
    Tetrachord(
        index=218,
        genus=G.C14,
        steps=(F(65, 63), F(14, 13), F(6, 5)),
    ),
    Tetrachord(
        index=219,
        genus=G.C14,
        steps=(F(22, 21), F(35, 33), F(6, 5)),
    ),
    Tetrachord(
        index=220,
        genus=G.C14,
        steps=(F(21, 20), F(200, 189), F(6, 5)),
        reference=R.perrett,
    ),
    Tetrachord(
        index=221,
        genus=G.C14,
        steps=(F(256, 243), F(6, 5), F(135, 128)),
        reference=R.xenakis,
    ),
    Tetrachord(
        index=222,
        genus=G.C14,
        steps=(F(60, 59), F(59, 54), F(6, 5)),
    ),
    Tetrachord(
        index=223,
        genus=G.C14,
        steps=(F(80, 77), F(77, 72), F(6, 5)),
    ),
    Tetrachord(
        index=224,
        genus=G.C14,
        steps=(F(24, 23), F(115, 108), F(6, 5)),
    ),
    Tetrachord(
        index=225,
        genus=G.C14,
        steps=(F(88, 81), F(45, 44), F(6, 5)),
    ),
    Tetrachord(
        index=226,
        genus=G.C14,
        steps=(F(46, 45), F(6, 5), F(25, 23)),
    ),
    Tetrachord(
        index=227,
        genus=G.C14,
        steps=(F(52, 51), F(85, 78), F(6, 5)),
        reference=R.wilson,
    ),
    Tetrachord(
        index=228,
        genus=G.C14,
        steps=(F(100, 99), F(11, 10), F(6, 5)),
        reference=R.hofmann,
    ),
    Tetrachord(
        index=229,
        genus=G.C14,
        steps=(F(34, 33), F(6, 5), F(55, 51)),
    ),
    Tetrachord(
        index=230,
        genus=G.C14,
        steps=(F(6, 5), F(35, 32), F(64, 63)),
    ),
    Tetrachord(
        index=231,
        genus=G.C14,
        steps=(F(6, 5), F(2240, 2187), F(243, 224)),
    ),
    #
    Tetrachord(
        index=232,
        genus=G.C15,
        steps=(F(56, 53), F(53, 50), F(25, 21)),
    ),
    Tetrachord(
        index=233,
        genus=G.C15,
        steps=(F(14, 13), F(26, 25), F(25, 21)),
    ),
    Tetrachord(
        index=234,
        genus=G.C15,
        steps=(F(28, 27), F(27, 25), F(25, 21)),
    ),
    Tetrachord(
        index=235,
        genus=G.C15,
        steps=(F(21, 20), F(16, 15), F(25, 21)),
        reference=R.perrett,
    ),
    Tetrachord(
        index=236,
        genus=G.C15,
        steps=(F(40, 39), F(273, 250), F(25, 21)),
    ),
    #
    Tetrachord(
        index=237,
        genus=G.C16,
        steps=(F(128, 121), F(121, 114), F(19, 16)),
    ),
    Tetrachord(
        index=238,
        genus=G.C16,
        steps=(F(96, 89), F(178, 171), F(19, 16)),
    ),
    Tetrachord(
        index=239,
        genus=G.C16,
        steps=(F(192, 185), F(185, 171), F(19, 16)),
    ),
    Tetrachord(
        index=240,
        genus=G.C16,
        steps=(F(20, 19), F(19, 16), F(16, 15)),
        reference=R.kornerup,
    ),
    Tetrachord(
        index=241,
        genus=G.C16,
        steps=(F(256, 243), F(81, 76), F(19, 16)),
        reference=R.boethius,
    ),
    Tetrachord(
        index=242,
        genus=G.C16,
        steps=(F(96, 95), F(10, 9), F(19, 16)),
        reference=R.wilson,
    ),
    Tetrachord(
        index=243,
        genus=G.C16,
        steps=(F(64, 63), F(21, 19), F(19, 16)),
    ),
    Tetrachord(
        index=244,
        genus=G.C16,
        steps=(F(40, 39), F(104, 95), F(19, 16)),
    ),
    #
    Tetrachord(
        index=245,
        genus=G.C17,
        steps=(F(18, 17), F(17, 16), F(32, 27)),
        reference=R.aristides_quintilianus,
    ),
    Tetrachord(
        index=246,
        genus=G.C17,
        steps=(F(27, 25), F(25, 24), F(32, 27)),
    ),
    Tetrachord(
        index=247,
        genus=G.C17,
        steps=(F(27, 26), F(13, 12), F(32, 27)),
        reference=R.barbour + "?",
    ),
    Tetrachord(
        index=248,
        genus=G.C17,
        steps=(F(28, 27), F(243, 224), F(32, 27)),
        reference=R.archytas,
    ),
    Tetrachord(
        index=249,
        genus=G.C17,
        steps=(F(256, 243), F(2187, 2048), F(32, 27)),
        reference=R.gaudentius,
    ),
    Tetrachord(
        index=250,
        genus=G.C17,
        steps=(F(81, 80), F(10, 9), F(32, 27)),
        reference=R.barbour + "?",
    ),
    Tetrachord(
        index=251,
        genus=G.C17,
        steps=(F(33, 32), F(12, 11), F(32, 27)),
        reference=R.barbour + "?",
    ),
    Tetrachord(
        index=252,
        genus=G.C17,
        steps=(F(45, 44), F(11, 10), F(32, 27)),
        reference=R.barbour + "?",
    ),
    Tetrachord(
        index=253,
        genus=G.C17,
        steps=(F(21, 20), F(15, 14), F(32, 27)),
        reference=R.perrett,
    ),
    Tetrachord(
        index=254,
        genus=G.C17,
        steps=(F(135, 128), F(16, 15), F(32, 27)),
    ),
    Tetrachord(
        index=255,
        genus=G.C17,
        steps=(F(36, 35), F(35, 32), F(32, 27)),
        reference=R.wilson,
    ),
    Tetrachord(
        index=256,
        genus=G.C17,
        steps=(F(49, 48), F(54, 49), F(32, 27)),
        reference=R.wilson,
    ),
    Tetrachord(
        index=257,
        genus=G.C17,
        steps=(F(243, 230), F(230, 216), F(32, 27)),
        reference=R.ps_philolaus + "?",
    ),
    Tetrachord(
        index=258,
        genus=G.C17,
        steps=(F(243, 229), F(229, 216), F(32, 27)),
    ),
    Tetrachord(
        index=259,
        genus=G.C17,
        steps=(F(20, 19), F(171, 160), F(32, 27)),
    ),
    Tetrachord(
        index=260,
        genus=G.C17,
        steps=(F(23, 22), F(99, 92), F(32, 27)),
    ),
    Tetrachord(
        index=261,
        genus=G.C17,
        steps=(F(24, 23), F(69, 64), F(32, 27)),
    ),
    Tetrachord(
        index=262,
        genus=G.C17,
        steps=(F(40, 39), F(351, 320), F(32, 27)),
    ),
    Tetrachord(
        index=263,
        genus=G.C17,
        steps=(F(14, 13), F(117, 112), F(32, 27)),
    ),
    #
    Tetrachord(
        index=264,
        genus=G.C18,
        steps=(F(304, 287), F(287, 270), F(45, 38)),
    ),
    Tetrachord(
        index=265,
        genus=G.C18,
        steps=(F(456, 439), F(439, 405), F(45, 38)),
    ),
    Tetrachord(
        index=266,
        genus=G.C18,
        steps=(F(228, 211), F(422, 405), F(45, 38)),
    ),
    Tetrachord(
        index=267,
        genus=G.C18,
        steps=(F(19, 18), F(16, 15), F(45, 38)),
    ),
    Tetrachord(
        index=268,
        genus=G.C18,
        steps=(F(76, 75), F(10, 9), F(45, 38)),
    ),
    Tetrachord(
        index=269,
        genus=G.C18,
        steps=(F(38, 35), F(28, 27), F(45, 38)),
    ),
    #
    Tetrachord(
        index=270,
        genus=G.C19,
        steps=(F(88, 83), F(83, 78), F(13, 11)),
    ),
    Tetrachord(
        index=271,
        genus=G.C19,
        steps=(F(66, 61), F(122, 117), F(13, 11)),
    ),
    Tetrachord(
        index=272,
        genus=G.C19,
        steps=(F(132, 127), F(127, 117), F(13, 11)),
    ),
    Tetrachord(
        index=273,
        genus=G.C19,
        steps=(F(14, 13), F(22, 21), F(13, 11)),
    ),
    Tetrachord(
        index=274,
        genus=G.C19,
        steps=(F(40, 39), F(11, 10), F(13, 11)),
    ),
    Tetrachord(
        index=275,
        genus=G.C19,
        steps=(F(66, 65), F(10, 9), F(13, 11)),
        reference=R.wilson,
    ),
    Tetrachord(
        index=276,
        genus=G.C19,
        steps=(F(27, 26), F(88, 81), F(13, 11)),
    ),
    Tetrachord(
        index=277,
        genus=G.C19,
        steps=(F(28, 27), F(99, 91), F(13, 11)),
    ),
    #
    Tetrachord(
        index=278,
        genus=G.C20,
        steps=(F(224, 211), F(211, 198), F(33, 28)),
    ),
    Tetrachord(
        index=279,
        genus=G.C20,
        steps=(F(336, 323), F(323, 297), F(33, 28)),
    ),
    Tetrachord(
        index=280,
        genus=G.C20,
        steps=(F(168, 155), F(310, 297), F(33, 28)),
    ),
    Tetrachord(
        index=281,
        genus=G.C20,
        steps=(F(56, 55), F(10, 9), F(33, 28)),
    ),
    Tetrachord(
        index=282,
        genus=G.C20,
        steps=(F(16, 15), F(35, 33), F(33, 28)),
        comment="Originally printed as 16/15 * 35/32 * 33/28",
    ),
    Tetrachord(
        index=283,
        genus=G.C20,
        steps=(F(34, 33), F(33, 28), F(56, 51)),
    ),
    #
    Tetrachord(
        index=284,
        genus=G.C21,
        steps=(F(17, 16), F(16, 15), F(20, 17)),
    ),
    Tetrachord(
        index=285,
        genus=G.C21,
        steps=(F(51, 47), F(47, 45), F(20, 17)),
    ),
    Tetrachord(
        index=286,
        genus=G.C21,
        steps=(F(51, 49), F(49, 45), F(20, 17)),
    ),
    Tetrachord(
        index=287,
        genus=G.C21,
        steps=(F(34, 33), F(11, 10), F(20, 17)),
    ),
    Tetrachord(
        index=288,
        genus=G.C21,
        steps=(F(51, 50), F(10, 9), F(20, 17)),
    ),
    Tetrachord(
        index=289,
        genus=G.C21,
        steps=(F(40, 39), F(221, 200), F(20, 17)),
    ),
    Tetrachord(
        index=290,
        genus=G.C21,
        steps=(F(28, 27), F(153, 140), F(20, 17)),
    ),
    Tetrachord(
        index=291,
        genus=G.C21,
        steps=(F(21, 20), F(20, 17), F(68, 63)),
    ),
    Tetrachord(
        index=292,
        genus=G.C21,
        steps=(F(68, 65), F(13, 12), F(20, 17)),
    ),
    Tetrachord(
        index=293,
        genus=G.C21,
        steps=(F(34, 31), F(31, 30), F(20, 17)),
    ),
    Tetrachord(
        index=294,
        genus=G.C21,
        steps=(F(68, 61), F(61, 60), F(20, 17)),
    ),
    Tetrachord(
        index=295,
        genus=G.C21,
        steps=(F(68, 67), F(67, 57), F(19, 17)),
    ),
    Tetrachord(
        index=296,
        genus=G.C21,
        steps=(F(68, 67), F(67, 60), F(20, 17)),
    ),
    #
    Tetrachord(
        index=297,
        genus=G.C22,
        steps=(F(184, 173), F(173, 162), F(27, 23)),
    ),
    Tetrachord(
        index=298,
        genus=G.C22,
        steps=(F(276, 265), F(265, 243), F(27, 23)),
    ),
    Tetrachord(
        index=299,
        genus=G.C22,
        steps=(F(138, 127), F(254, 243), F(27, 23)),
        comment="Originally printed as 138/127 * 254/243 * 27/2",
    ),
    Tetrachord(
        index=300,
        genus=G.C22,
        steps=(F(28, 27), F(23, 21), F(27, 23)),
    ),
    Tetrachord(
        index=301,
        genus=G.C22,
        steps=(F(23, 22), F(88, 81), F(27, 23)),
    ),
    Tetrachord(
        index=302,
        genus=G.C22,
        steps=(F(46, 45), F(10, 9), F(27, 23)),
    ),
    #
    Tetrachord(
        index=303,
        genus=G.C23,
        steps=(F(512, 481), F(481, 450), F(75, 64)),
    ),
    Tetrachord(
        index=304,
        genus=G.C23,
        steps=(F(768, 737), F(737, 675), F(75, 64)),
    ),
    Tetrachord(
        index=305,
        genus=G.C23,
        steps=(F(384, 353), F(706, 675), F(75, 64)),
    ),
    Tetrachord(
        index=306,
        genus=G.C23,
        steps=(F(16, 15), F(75, 64), F(16, 15)),
        reference=R.helmholtz,
    ),
    #
    Tetrachord(
        index=307,
        genus=G.C24,
        steps=(F(16, 15), F(15, 14), F(7, 6)),
        reference=R.al_farabi,
    ),
    Tetrachord(
        index=308,
        genus=G.C24,
        steps=(F(22, 21), F(12, 11), F(7, 6)),
        reference=R.ptolemy,
    ),
    Tetrachord(
        index=309,
        genus=G.C24,
        steps=(F(24, 23), F(23, 21), F(7, 6)),
    ),
    Tetrachord(
        index=310,
        genus=G.C24,
        steps=(F(20, 19), F(38, 35), F(7, 6)),
        reference=R.ptolemy,
    ),
    Tetrachord(
        index=311,
        genus=G.C24,
        steps=(F(10, 9), F(36, 35), F(7, 6)),
        reference=R.avicenna,
    ),
    Tetrachord(
        index=312,
        genus=G.C24,
        steps=(F(64, 63), F(9, 8), F(7, 6)),
        reference=R.barbour,
    ),
    Tetrachord(
        index=313,
        genus=G.C24,
        steps=(F(92, 91), F(26, 23), F(7, 6)),
    ),
    Tetrachord(
        index=314,
        genus=G.C24,
        steps=(F(256, 243), F(243, 224), F(7, 6)),
        reference=R.hipkins,
    ),
    Tetrachord(
        index=315,
        genus=G.C24,
        steps=(F(40, 39), F(39, 35), F(7, 6)),
    ),
    Tetrachord(
        index=316,
        genus=G.C24,
        steps=(F(18, 17), F(7, 6), F(68, 63)),
    ),
    Tetrachord(
        index=317,
        genus=G.C24,
        steps=(F(50, 49), F(7, 6), F(28, 25)),
    ),
    Tetrachord(
        index=318,
        genus=G.C24,
        steps=(F(14, 13), F(7, 6), F(52, 49)),
    ),
    Tetrachord(
        index=319,
        genus=G.C24,
        steps=(F(46, 45), F(180, 161), F(7, 6)),
    ),
    Tetrachord(
        index=320,
        genus=G.C24,
        steps=(F(28, 27), F(54, 49), F(7, 6)),
    ),
    Tetrachord(
        index=321,
        genus=G.C24,
        steps=(F(120, 113), F(113, 105), F(7, 6)),
    ),
    Tetrachord(
        index=322,
        genus=G.C24,
        steps=(F(60, 59), F(118, 105), F(7, 6)),
    ),
    Tetrachord(
        index=323,
        genus=G.C24,
        steps=(F(30, 29), F(116, 105), F(7, 6)),
    ),
    Tetrachord(
        index=324,
        genus=G.C24,
        steps=(F(88, 81), F(81, 77), F(7, 6)),
    ),
    Tetrachord(
        index=325,
        genus=G.C24,
        steps=(F(120, 119), F(17, 15), F(7, 6)),
    ),
    Tetrachord(
        index=326,
        genus=G.C24,
        steps=(F(27, 25), F(7, 6), F(200, 189)),
    ),
    Tetrachord(
        index=327,
        genus=G.C24,
        steps=(F(26, 25), F(7, 6), F(100, 91)),
    ),
    Tetrachord(
        index=328,
        genus=G.C24,
        steps=(F(7, 6), F(1024, 945), F(135, 128)),
    ),
    #
    Tetrachord(
        index=329,
        genus=G.C25,
        steps=(F(78, 73), F(73, 68), F(136, 117)),
    ),
    Tetrachord(
        index=330,
        genus=G.C25,
        steps=(F(117, 112), F(56, 51), F(136, 117)),
    ),
    Tetrachord(
        index=331,
        genus=G.C25,
        steps=(F(117, 107), F(107, 102), F(136, 117)),
    ),
    Tetrachord(
        index=332,
        genus=G.C25,
        steps=(F(52, 51), F(9, 8), F(136, 117)),
    ),
    #
    Tetrachord(
        index=333,
        genus=G.C26,
        steps=(F(31, 29), F(29, 27), F(36, 31)),
    ),
    Tetrachord(
        index=334,
        genus=G.C26,
        steps=(F(93, 89), F(89, 81), F(36, 31)),
    ),
    Tetrachord(
        index=335,
        genus=G.C26,
        steps=(F(93, 85), F(85, 81), F(36, 31)),
    ),
    #
    Tetrachord(
        index=336,
        genus=G.C27,
        steps=(F(46, 43), F(43, 40), F(80, 69)),
    ),
    Tetrachord(
        index=337,
        genus=G.C27,
        steps=(F(23, 21), F(21, 20), F(80, 69)),
    ),
    Tetrachord(
        index=338,
        genus=G.C27,
        steps=(F(23, 22), F(11, 10), F(80, 69)),
    ),
    Tetrachord(
        index=339,
        genus=G.C27,
        steps=(F(46, 45), F(9, 8), F(80, 69)),
    ),
    #
    Tetrachord(
        index=340,
        genus=G.C28,
        steps=(F(76, 71), F(71, 66), F(22, 19)),
    ),
    Tetrachord(
        index=341,
        genus=G.C28,
        steps=(F(57, 52), F(104, 99), F(22, 19)),
    ),
    Tetrachord(
        index=342,
        genus=G.C28,
        steps=(F(114, 109), F(109, 99), F(22, 19)),
    ),
    Tetrachord(
        index=343,
        genus=G.C28,
        steps=(F(19, 18), F(12, 11), F(22, 19)),
        reference=R.schlesinger,
    ),
    Tetrachord(
        index=344,
        genus=G.C28,
        steps=(F(34, 33), F(19, 17), F(22, 19)),
    ),
    Tetrachord(
        index=345,
        genus=G.C28,
        steps=(F(40, 39), F(247, 220), F(22, 19)),
    ),
    #
    Tetrachord(
        index=346,
        genus=G.C29,
        steps=(F(15, 14), F(14, 13), F(52, 45)),
    ),
    Tetrachord(
        index=347,
        genus=G.C29,
        steps=(F(45, 41), F(41, 39), F(52, 45)),
    ),
    Tetrachord(
        index=348,
        genus=G.C29,
        steps=(F(45, 43), F(43, 39), F(52, 45)),
    ),
    Tetrachord(
        index=349,
        genus=G.C29,
        steps=(F(24, 23), F(115, 104), F(52, 45)),
    ),
    Tetrachord(
        index=350,
        genus=G.C29,
        steps=(F(40, 39), F(9, 8), F(52, 45)),
    ),
    Tetrachord(
        index=351,
        genus=G.C29,
        steps=(F(18, 17), F(85, 78), F(52, 45)),
    ),
    Tetrachord(
        index=352,
        genus=G.C29,
        steps=(F(45, 44), F(44, 39), F(52, 45)),
    ),
    Tetrachord(
        index=353,
        genus=G.C29,
        steps=(F(65, 63), F(189, 169), F(52, 45)),
        comment="Originally printed as 65/63 * 28/25 * 52/45 - not obviously a typo",
    ),
    Tetrachord(
        index=354,
        genus=G.C29,
        steps=(F(55, 52), F(12, 11), F(52, 45)),
    ),
    Tetrachord(
        index=355,
        genus=G.C29,
        steps=(F(60, 59), F(59, 52), F(52, 45)),
        comment="Originally printed as 60/59 * 59/45 * 52/45",
    ),
    Tetrachord(
        index=356,
        genus=G.C29,
        steps=(F(20, 19), F(52, 45), F(57, 52)),
    ),
    Tetrachord(
        index=357,
        genus=G.C29,
        steps=(F(27, 26), F(10, 9), F(52, 45)),
    ),
    Tetrachord(
        index=358,
        genus=G.C29,
        steps=(F(11, 10), F(150, 143), F(52, 45)),
    ),
    #
    Tetrachord(
        index=359,
        genus=G.D1,
        steps=(F(104, 97), F(97, 90), F(15, 13)),
    ),
    Tetrachord(
        index=360,
        genus=G.D1,
        steps=(F(78, 71), F(142, 135), F(15, 13)),
    ),
    Tetrachord(
        index=361,
        genus=G.D1,
        steps=(F(156, 149), F(149, 135), F(15, 13)),
    ),
    Tetrachord(
        index=362,
        genus=G.D1,
        steps=(F(16, 15), F(15, 13), F(13, 12)),
        reference=R.schlesinger,
    ),
    Tetrachord(
        index=363,
        genus=G.D1,
        steps=(F(26, 25), F(10, 9), F(15, 13)),
    ),
    Tetrachord(
        index=364,
        genus=G.D1,
        steps=(F(256, 243), F(351, 320), F(15, 13)),
    ),
    Tetrachord(
        index=365,
        genus=G.D1,
        steps=(F(20, 19), F(247, 225), F(15, 13)),
    ),
    Tetrachord(
        index=366,
        genus=G.D1,
        steps=(F(11, 10), F(15, 13), F(104, 99)),
    ),
    Tetrachord(
        index=367,
        genus=G.D1,
        steps=(F(12, 11), F(15, 13), F(143, 135)),
    ),
    Tetrachord(
        index=368,
        genus=G.D1,
        steps=(F(46, 45), F(26, 23), F(15, 13)),
    ),
    Tetrachord(
        index=369,
        genus=G.D1,
        steps=(F(40, 39), F(169, 150), F(15, 13)),
    ),
    Tetrachord(
        index=370,
        genus=G.D1,
        steps=(F(28, 27), F(39, 35), F(15, 13)),
    ),
    Tetrachord(
        index=371,
        genus=G.D1,
        steps=(F(91, 90), F(8, 7), F(15, 13)),
    ),
    #
    Tetrachord(
        index=372,
        genus=G.D2,
        steps=(F(44, 41), F(41, 38), F(38, 33)),
    ),
    Tetrachord(
        index=373,
        genus=G.D2,
        steps=(F(11, 10), F(20, 19), F(38, 33)),
    ),
    Tetrachord(
        index=374,
        genus=G.D2,
        steps=(F(22, 21), F(21, 19), F(38, 33)),
    ),
    #
    Tetrachord(
        index=375,
        genus=G.D3,
        steps=(F(160, 149), F(149, 138), F(23, 20)),
    ),
    Tetrachord(
        index=376,
        genus=G.D3,
        steps=(F(120, 109), F(218, 207), F(23, 20)),
    ),
    Tetrachord(
        index=377,
        genus=G.D3,
        steps=(F(240, 229), F(229, 207), F(23, 20)),
    ),
    Tetrachord(
        index=378,
        genus=G.D3,
        steps=(F(8, 7), F(70, 69), F(23, 20)),
    ),
    Tetrachord(
        index=379,
        genus=G.D3,
        steps=(F(40, 39), F(26, 23), F(23, 20)),
    ),
    Tetrachord(
        index=380,
        genus=G.D3,
        steps=(F(24, 23), F(23, 20), F(10, 9)),
        reference=R.schlesinger,
    ),
    Tetrachord(
        index=381,
        genus=G.D3,
        steps=(F(28, 27), F(180, 161), F(23, 20)),
    ),
    #
    Tetrachord(
        index=382,
        genus=G.D4,
        steps=(F(72, 67), F(67, 62), F(31, 27)),
    ),
    Tetrachord(
        index=383,
        genus=G.D4,
        steps=(F(108, 103), F(103, 93), F(31, 27)),
    ),
    Tetrachord(
        index=384,
        genus=G.D4,
        steps=(F(54, 49), F(98, 93), F(31, 27)),
    ),
    Tetrachord(
        index=385,
        genus=G.D4,
        steps=(F(32, 31), F(9, 8), F(31, 27)),
    ),
    #
    Tetrachord(
        index=386,
        genus=G.D5,
        steps=(F(272, 253), F(253, 234), F(39, 34)),
    ),
    Tetrachord(
        index=387,
        genus=G.D5,
        steps=(F(408, 389), F(389, 351), F(39, 34)),
    ),
    Tetrachord(
        index=388,
        genus=G.D5,
        steps=(F(204, 185), F(370, 351), F(39, 34)),
    ),
    Tetrachord(
        index=389,
        genus=G.D5,
        steps=(F(40, 39), F(39, 34), F(17, 15)),
    ),
    #
    Tetrachord(
        index=390,
        genus=G.D6,
        steps=(F(14, 13), F(13, 12), F(8, 7)),
        reference=R.avicenna,
    ),
    Tetrachord(
        index=391,
        genus=G.D6,
        steps=(F(19, 18), F(21, 19), F(8, 7)),
        reference=R.safiyu_d_din,
    ),
    Tetrachord(
        index=392,
        genus=G.D6,
        steps=(F(21, 20), F(10, 9), F(8, 7)),
        reference=R.ptolemy,
    ),
    Tetrachord(
        index=393,
        genus=G.D6,
        steps=(F(28, 27), F(8, 7), F(9, 8)),
        reference=R.archytas,
    ),
    Tetrachord(
        index=394,
        genus=G.D6,
        steps=(F(49, 48), F(8, 7), F(8, 7)),
        reference=R.al_farabi,
    ),
    Tetrachord(
        index=395,
        genus=G.D6,
        steps=(F(35, 33), F(11, 10), F(8, 7)),
        reference=R.avicenna,
    ),
    Tetrachord(
        index=396,
        genus=G.D6,
        steps=(F(77, 72), F(12, 11), F(8, 7)),
        reference=R.avicenna,
    ),
    Tetrachord(
        index=397,
        genus=G.D6,
        steps=(F(16, 15), F(35, 32), F(8, 7)),
        reference=R.vogel,
    ),
    Tetrachord(
        index=398,
        genus=G.D6,
        steps=(F(35, 34), F(17, 15), F(8, 7)),
    ),
    Tetrachord(
        index=399,
        genus=G.D6,
        steps=(F(25, 24), F(8, 7), F(28, 25)),
    ),
    Tetrachord(
        index=400,
        genus=G.D6,
        steps=(F(15, 14), F(8, 7), F(49, 45)),
    ),
    Tetrachord(
        index=401,
        genus=G.D6,
        steps=(F(40, 39), F(91, 80), F(8, 7)),
    ),
    Tetrachord(
        index=402,
        genus=G.D6,
        steps=(F(46, 45), F(105, 92), F(8, 7)),
    ),
    Tetrachord(
        index=403,
        genus=G.D6,
        steps=(F(18, 17), F(119, 108), F(8, 7)),
    ),
    Tetrachord(
        index=404,
        genus=G.D6,
        steps=(F(17, 16), F(8, 7), F(56, 51)),
    ),
    Tetrachord(
        index=405,
        genus=G.D6,
        steps=(F(34, 33), F(77, 68), F(8, 7)),
    ),
    Tetrachord(
        index=406,
        genus=G.D6,
        steps=(F(256, 243), F(567, 512), F(8, 7)),
    ),
    #
    Tetrachord(
        index=407,
        genus=G.D7,
        steps=(F(150, 139), F(139, 128), F(256, 225)),
    ),
    Tetrachord(
        index=408,
        genus=G.D7,
        steps=(F(225, 214), F(107, 96), F(256, 225)),
    ),
    Tetrachord(
        index=409,
        genus=G.D7,
        steps=(F(225, 203), F(203, 192), F(256, 225)),
    ),
    Tetrachord(
        index=410,
        genus=G.D7,
        steps=(F(25, 24), F(9, 8), F(256, 225)),
    ),
    #
    Tetrachord(
        index=411,
        genus=G.D8,
        steps=(F(176, 163), F(163, 150), F(25, 22)),
    ),
    Tetrachord(
        index=412,
        genus=G.D8,
        steps=(F(132, 119), F(238, 225), F(25, 22)),
    ),
    Tetrachord(
        index=413,
        genus=G.D8,
        steps=(F(264, 251), F(251, 225), F(25, 22)),
    ),
    Tetrachord(
        index=414,
        genus=G.D8,
        steps=(F(16, 15), F(11, 10), F(25, 22)),
    ),
    Tetrachord(
        index=415,
        genus=G.D8,
        steps=(F(88, 81), F(27, 25), F(25, 22)),
    ),
    Tetrachord(
        index=416,
        genus=G.D8,
        steps=(F(22, 21), F(25, 22), F(28, 25)),
    ),
    Tetrachord(
        index=417,
        genus=G.D8,
        steps=(F(28, 27), F(198, 175), F(25, 22)),
    ),
    Tetrachord(
        index=418,
        genus=G.D8,
        steps=(F(26, 25), F(44, 39), F(25, 22)),
    ),
    #
    Tetrachord(
        index=419,
        genus=G.D9,
        steps=(F(27, 25), F(25, 23), F(92, 81)),
    ),
    Tetrachord(
        index=420,
        genus=G.D9,
        steps=(F(81, 77), F(77, 69), F(92, 81)),
    ),
    Tetrachord(
        index=421,
        genus=G.D9,
        steps=(F(81, 73), F(73, 69), F(92, 81)),
    ),
    Tetrachord(
        index=422,
        genus=G.D9,
        steps=(F(24, 23), F(9, 8), F(92, 81)),
    ),
    Tetrachord(
        index=423,
        genus=G.D9,
        steps=(F(27, 26), F(26, 23), F(92, 81)),
    ),
    #
    Tetrachord(
        index=424,
        genus=G.D10,
        steps=(F(67, 62), F(62, 57), F(76, 67)),
    ),
    Tetrachord(
        index=425,
        genus=G.D10,
        steps=(F(201, 181), F(181, 171), F(76, 67)),
    ),
    Tetrachord(
        index=426,
        genus=G.D10,
        steps=(F(201, 191), F(191, 171), F(76, 67)),
    ),
    Tetrachord(
        index=427,
        genus=G.D10,
        steps=(F(256, 243), F(76, 67), F(5427, 4864)),
        reference=R.euler,
    ),
    #
    Tetrachord(
        index=428,
        genus=G.D11,
        steps=(F(40, 37), F(37, 34), F(17, 15)),
    ),
    Tetrachord(
        index=429,
        genus=G.D11,
        steps=(F(10, 9), F(18, 17), F(17, 15)),
        reference=R.kornerup,
    ),
    Tetrachord(
        index=430,
        genus=G.D11,
        steps=(F(20, 19), F(19, 17), F(17, 15)),
        reference=R.ptolemy,
    ),
    Tetrachord(
        index=431,
        genus=G.D11,
        steps=(F(15, 14), F(56, 51), F(17, 15)),
    ),
    Tetrachord(
        index=432,
        genus=G.D11,
        steps=(F(80, 77), F(77, 68), F(17, 15)),
    ),
    Tetrachord(
        index=433,
        genus=G.D11,
        steps=(F(12, 11), F(55, 51), F(17, 15)),
    ),
    Tetrachord(
        index=434,
        genus=G.D11,
        steps=(F(120, 109), F(109, 102), F(17, 15)),
    ),
    Tetrachord(
        index=435,
        genus=G.D11,
        steps=(F(120, 113), F(113, 102), F(17, 15)),
    ),
    Tetrachord(
        index=436,
        genus=G.D11,
        steps=(F(24, 23), F(115, 102), F(17, 15)),
    ),
    Tetrachord(
        index=437,
        genus=G.D11,
        steps=(F(160, 153), F(9, 8), F(17, 15)),
    ),
    #
    Tetrachord(
        index=438,
        genus=G.D12,
        steps=(F(66, 61), F(61, 56), F(112, 99)),
    ),
    Tetrachord(
        index=439,
        genus=G.D12,
        steps=(F(99, 94), F(47, 42), F(112, 99)),
    ),
    Tetrachord(
        index=440,
        genus=G.D12,
        steps=(F(99, 89), F(89, 84), F(112, 99)),
    ),
    Tetrachord(
        index=441,
        genus=G.D12,
        steps=(F(10, 9), F(297, 280), F(112, 99)),
    ),
    Tetrachord(
        index=442,
        genus=G.D12,
        steps=(F(22, 21), F(9, 8), F(112, 99)),
    ),
    #
    Tetrachord(
        index=443,
        genus=G.D13,
        steps=(F(12, 11), F(13, 12), F(44, 39)),
        reference=R.young,
    ),
    Tetrachord(
        index=444,
        genus=G.D13,
        steps=(F(39, 35), F(35, 33), F(44, 39)),
    ),
    Tetrachord(
        index=445,
        genus=G.D13,
        steps=(F(39, 37), F(37, 33), F(44, 39)),
    ),
    Tetrachord(
        index=446,
        genus=G.D13,
        steps=(F(44, 39), F(9, 8), F(104, 99)),
    ),
    #
    Tetrachord(
        index=447,
        genus=G.D14,
        steps=(F(90, 83), F(83, 76), F(152, 135)),
    ),
    Tetrachord(
        index=448,
        genus=G.D14,
        steps=(F(135, 128), F(64, 57), F(152, 135)),
    ),
    Tetrachord(
        index=449,
        genus=G.D14,
        steps=(F(135, 121), F(121, 114), F(152, 135)),
    ),
    Tetrachord(
        index=450,
        genus=G.D14,
        steps=(F(20, 19), F(9, 8), F(152, 135)),
    ),
    #
    Tetrachord(
        index=451,
        genus=G.D15,
        steps=(F(64, 59), F(59, 54), F(9, 8)),
        reference=R.safiyu_d_din,
    ),
    Tetrachord(
        index=452,
        genus=G.D15,
        steps=(F(48, 43), F(86, 81), F(9, 8)),
        reference=R.safiyu_d_din,
    ),
    Tetrachord(
        index=453,
        genus=G.D15,
        steps=(F(96, 91), F(91, 81), F(9, 8)),
    ),
    Tetrachord(
        index=454,
        genus=G.D15,
        steps=(F(256, 243), F(9, 8), F(9, 8)),
        reference=R.pythagoras + "?",
    ),
    Tetrachord(
        index=455,
        genus=G.D15,
        steps=(F(16, 15), F(9, 8), F(10, 9)),
        reference=f"{R.ptolemy}, {R.didymos}",
    ),
    Tetrachord(
        index=456,
        genus=G.D15,
        steps=(F(2187, 2048), F(65536, 59049), F(9, 8)),
        reference=R.anonymous,
    ),
    Tetrachord(
        index=457,
        genus=G.D15,
        steps=(F(9, 8), F(12, 11), F(88, 81)),
        reference=R.avicenna,
    ),
    Tetrachord(
        index=458,
        genus=G.D15,
        steps=(F(13, 12), F(9, 8), F(128, 117)),
        reference=R.avicenna,
    ),
    Tetrachord(
        index=459,
        genus=G.D15,
        steps=(F(14, 13), F(9, 8), F(208, 189)),
        reference=R.avicenna,
    ),
    Tetrachord(
        index=460,
        genus=G.D15,
        steps=(F(9, 8), F(11, 10), F(320, 297)),
        reference=R.al_farabi,
    ),
    Tetrachord(
        index=461,
        genus=G.D15,
        steps=(F(9, 8), F(15, 14), F(448, 405)),
    ),
    Tetrachord(
        index=462,
        genus=G.D15,
        steps=(F(9, 8), F(17, 16), F(512, 459)),
    ),
    Tetrachord(
        index=463,
        genus=G.D15,
        steps=(F(9, 8), F(18, 17), F(272, 243)),
    ),
    Tetrachord(
        index=464,
        genus=G.D15,
        steps=(F(9, 8), F(19, 18), F(64, 57)),
    ),
    Tetrachord(
        index=465,
        genus=G.D15,
        steps=(F(56, 51), F(9, 8), F(68, 63)),
    ),
    Tetrachord(
        index=466,
        genus=G.D15,
        steps=(F(9, 8), F(200, 189), F(28, 25)),
    ),
    Tetrachord(
        index=467,
        genus=G.D15,
        steps=(F(184, 171), F(9, 8), F(76, 69)),
    ),
    Tetrachord(
        index=468,
        genus=G.D15,
        steps=(F(32, 29), F(9, 8), F(29, 27)),
    ),
    Tetrachord(
        index=469,
        genus=G.D15,
        steps=(F(121, 108), F(9, 8), F(128, 121)),
        reference=R.partch,
    ),
    Tetrachord(
        index=470,
        genus=G.D15,
        steps=(F(9, 8), F(4096, 3645), F(135, 128)),
    ),
    Tetrachord(
        index=471,
        genus=G.D15,
        steps=(F(9, 8), F(7168, 6561), F(243, 224)),
    ),
    Tetrachord(
        index=472,
        genus=G.D15,
        steps=(F(35, 32), F(1024, 945), F(9, 8)),
    ),
    #
    Tetrachord(
        index=473,
        genus=G.D16,
        steps=(F(11, 10), F(13, 12), F(160, 143)),
        reference=R.al_farabi,
    ),
    #
    Tetrachord(
        index=474,
        genus=G.D17,
        steps=(F(12, 11), F(11, 10), F(10, 9)),
        reference=R.ptolemy,
    ),
    Tetrachord(
        index=475,
        genus=G.D17,
        steps=(F(10, 9), F(10, 9), F(27, 25)),
        reference=R.al_farabi,
    ),
    Tetrachord(
        index=476,
        genus=G.D17,
        steps=(F(10, 9), F(13, 12), F(72, 65)),
        reference=R.avicenna,
    ),
    #
    # REDUPLICATED TETRACHORDS
    #
    Tetrachord(
        index=477,
        genus="R1",
        steps=(F(11, 10), F(11, 10), F(400, 363)),
    ),
    Tetrachord(
        index=478,
        genus="R2",
        steps=(F(12, 11), F(12, 11), F(121, 108)),
        reference=R.avicenna,
    ),
    Tetrachord(
        index=479,
        genus="R3",
        steps=(F(13, 12), F(13, 12), F(192, 169)),
        reference=R.avicenna,
    ),
    Tetrachord(
        index=480,
        genus="R4",
        steps=(F(14, 13), F(14, 13), F(169, 147)),
        reference=R.avicenna,
    ),
    Tetrachord(
        index=481,
        genus="R5",
        steps=(F(15, 14), F(15, 14), F(784, 675)),
        reference=R.avicenna,
    ),
    Tetrachord(
        index=482,
        genus="R6",
        steps=(F(2187, 2048), F(16777216, 14348907), F(2187, 2048)),
        reference=R.palmer,
    ),
    Tetrachord(
        index=483,
        genus="R7",
        steps=(F(17, 16), F(17, 16), F(1024, 867)),
    ),
    Tetrachord(
        index=484,
        genus="R8",
        steps=(F(18, 17), F(18, 17), F(289, 243)),
    ),
    Tetrachord(
        index=485,
        genus="R9",
        steps=(F(256, 243), F(256, 243), F(19683, 16384)),
        comment="Originally printed as 256/243 * 256/243 * 19688/16384",
    ),
    Tetrachord(
        index=486,
        genus="R10",
        steps=(F(22, 21), F(147, 121), F(22, 21)),
    ),
    Tetrachord(
        index=487,
        genus="R11",
        steps=(F(25, 24), F(25, 24), F(768, 625)),
    ),
    Tetrachord(
        index=488,
        genus="R12",
        steps=(F(28, 27), F(28, 27), F(243, 196)),
    ),
    Tetrachord(
        index=489,
        genus="R13",
        steps=(F(34, 33), F(34, 33), F(363, 289)),
    ),
    Tetrachord(
        index=490,
        genus="R14",
        steps=(F(36, 35), F(36, 35), F(1225, 972)),
    ),
    Tetrachord(
        index=491,
        genus="R15",
        steps=(F(40, 39), F(40, 39), F(507, 400)),
    ),
    Tetrachord(
        index=492,
        genus="R16",
        steps=(F(46, 45), F(46, 45), F(675, 529)),
    ),
    #
    # Miscellaneous tetrachords
    #
    Tetrachord(
        index=493,
        genus="M1",
        steps=(F(176, 175), F(175, 174), F(29, 22)),
    ),
    Tetrachord(
        index=494,
        genus="M2",
        steps=(F(25, 19), F(931, 925), F(148, 147)),
    ),
    Tetrachord(
        index=495,
        genus="M3",
        steps=(F(128, 127), F(127, 126), F(21, 16)),
    ),
    Tetrachord(
        index=496,
        genus="M4",
        steps=(F(21, 16), F(656, 651), F(124, 123)),
    ),
    Tetrachord(
        index=497,
        genus="M5",
        steps=(F(104, 103), F(103, 102), F(17, 13)),
    ),
    Tetrachord(
        index=498,
        genus="M6",
        steps=(F(17, 13), F(429, 425), F(100, 99)),
    ),
    Tetrachord(
        index=499,
        genus="M7",
        steps=(F(98, 97), F(97, 96), F(64, 49)),
    ),
    Tetrachord(
        index=500,
        genus="M8",
        steps=(F(92, 91), F(91, 90), F(30, 23)),
    ),
    Tetrachord(
        index=501,
        genus="M9",
        steps=(F(90, 89), F(89, 88), F(176, 135)),
    ),
    Tetrachord(
        index=502,
        genus="M10",
        steps=(F(88, 87), F(87, 86), F(43, 33)),
    ),
    Tetrachord(
        index=503,
        genus="M11",
        steps=(F(86, 85), F(85, 84), F(56, 43)),
    ),
    Tetrachord(
        index=504,
        genus="M12",
        steps=(F(84, 83), F(83, 82), F(82, 63)),
    ),
    Tetrachord(
        index=505,
        genus="M13",
        steps=(F(82, 81), F(81, 80), F(160, 123)),
    ),
    Tetrachord(
        index=506,
        genus="M14",
        steps=(F(13, 10), F(250, 247), F(76, 75)),
        comment="Originally printed as 13/10 * 250/247 * 76/74",
    ),
    Tetrachord(
        index=507,
        genus="M15",
        steps=(F(78, 77), F(77, 76), F(152, 117)),
    ),
    Tetrachord(
        index=508,
        genus="M16",
        steps=(F(76, 75), F(75, 74), F(74, 57)),
        comment="Originally printed as 76/75 * 76/75 * 74/57",
    ),
    Tetrachord(
        index=509,
        genus="M17",
        steps=(F(74, 73), F(73, 72), F(48, 37)),
        comment="Originally printed as 74/73 73/72 48/31",
    ),
    Tetrachord(
        index=510,
        genus="M18",
        steps=(F(70, 69), F(69, 68), F(136, 105)),
    ),
    Tetrachord(
        index=511,
        genus="M19",
        steps=(F(22, 17), F(357, 352), F(64, 63)),
    ),
    Tetrachord(
        index=512,
        genus="M20",
        steps=(F(58, 57), F(57, 56), F(112, 87)),
    ),
    Tetrachord(
        index=513,
        genus="M21",
        steps=(F(87, 86), F(43, 42), F(112, 87)),
        comment="Originally printed as 87/80 * 43/42 * 112/87",
    ),
    Tetrachord(
        index=514,
        genus="M22",
        steps=(F(87, 85), F(85, 84), F(112, 87)),
    ),
    Tetrachord(
        index=515,
        genus="M23",
        steps=(F(68, 53), F(53, 52), F(52, 51)),
    ),
    Tetrachord(
        index=516,
        genus="M24",
        steps=(F(136, 133), F(133, 130), F(65, 51)),
    ),
    Tetrachord(
        index=517,
        genus="M25",
        steps=(F(68, 67), F(67, 65), F(65, 51)),
    ),
    Tetrachord(
        index=518,
        genus="M26",
        steps=(F(34, 33), F(66, 65), F(65, 51)),
    ),
    Tetrachord(
        index=519,
        genus="M27",
        steps=(F(68, 67), F(67, 54), F(18, 17)),
    ),
    Tetrachord(
        index=520,
        genus="M28",
        steps=(F(25, 24), F(32, 31), F(31, 25)),
    ),
    Tetrachord(
        index=521,
        genus="M29",
        steps=(F(68, 55), F(55, 54), F(18, 17)),
    ),
    Tetrachord(
        index=522,
        genus="M30",
        steps=(F(68, 67), F(67, 63), F(21, 17)),
    ),
    Tetrachord(
        index=523,
        genus="M31",
        steps=(F(68, 65), F(65, 63), F(21, 17)),
    ),
    Tetrachord(
        index=524,
        genus="M32",
        steps=(F(36, 35), F(256, 243), F(315, 256)),
    ),
    Tetrachord(
        index=525,
        genus="M33",
        steps=(F(64, 63), F(16, 15), F(315, 256)),
    ),
    Tetrachord(
        index=526,
        genus="M34",
        steps=(F(64, 63), F(2187, 2048), F(896, 729)),
    ),
    Tetrachord(
        index=527,
        genus="M35",
        steps=(F(36, 35), F(135, 128), F(896, 729)),
    ),
    Tetrachord(
        index=528,
        genus="M36",
        steps=(F(28, 27), F(2187, 1792), F(256, 243)),
    ),
    Tetrachord(
        index=529,
        genus="M37",
        steps=(F(16, 15), F(2240, 2187), F(2187, 1792)),
    ),
    Tetrachord(
        index=530,
        genus="M38",
        steps=(F(28, 27), F(128, 105), F(135, 128)),
    ),
    Tetrachord(
        index=531,
        genus="M39",
        steps=(F(17, 16), F(32, 31), F(62, 51)),
    ),
    Tetrachord(
        index=532,
        genus="M40",
        steps=(F(20, 19), F(57, 47), F(47, 45)),
    ),
    Tetrachord(
        index=533,
        genus="M41",
        steps=(F(360, 349), F(349, 327), F(109, 90)),
    ),
    Tetrachord(
        index=534,
        genus="M42",
        steps=(F(24, 23), F(115, 109), F(109, 90)),
    ),
    Tetrachord(
        index=535,
        genus="M43",
        steps=(F(240, 229), F(229, 218), F(109, 90)),
    ),
    Tetrachord(
        index=536,
        genus="M44",
        steps=(F(19, 18), F(24, 23), F(23, 19)),
    ),
    Tetrachord(
        index=537,
        genus="M45",
        steps=(F(15, 14), F(36, 35), F(98, 81)),
    ),
    Tetrachord(
        index=538,
        genus="M46",
        steps=(F(28, 27), F(16, 15), F(135, 112)),
    ),
    Tetrachord(
        index=539,
        genus="M47",
        steps=(F(24, 23), F(115, 96), F(16, 15)),
    ),
    Tetrachord(
        index=540,
        genus="M48",
        steps=(F(256, 243), F(243, 230), F(115, 96)),
    ),
    Tetrachord(
        index=541,
        genus="M49",
        steps=(F(68, 67), F(67, 56), F(56, 51)),
    ),
    Tetrachord(
        index=542,
        genus="M50",
        steps=(F(68, 57), F(19, 18), F(18, 17)),
    ),
    Tetrachord(
        index=543,
        genus="M51",
        steps=(F(15, 14), F(266, 255), F(68, 57)),
    ),
    Tetrachord(
        index=544,
        genus="M52",
        steps=(F(256, 243), F(243, 229), F(229, 192)),
    ),
    Tetrachord(
        index=545,
        genus="M53",
        steps=(F(32, 31), F(13, 12), F(31, 26)),
    ),
    Tetrachord(
        index=546,
        genus="M54",
        steps=(F(240, 227), F(227, 214), F(107, 90)),
    ),
    Tetrachord(
        index=547,
        genus="M55",
        steps=(F(360, 347), F(347, 321), F(107, 90)),
    ),
    Tetrachord(
        index=548,
        genus="M56",
        steps=(F(7168, 6561), F(36, 35), F(1215, 1024)),
    ),
    Tetrachord(
        index=549,
        genus="M57",
        steps=(F(16, 15), F(1215, 1024), F(256, 243)),
    ),
    Tetrachord(
        index=550,
        genus="M58",
        steps=(F(28, 27), F(1024, 945), F(1215, 1024)),
    ),
    Tetrachord(
        index=551,
        genus="M59",
        steps=(F(120, 113), F(113, 106), F(53, 45)),
    ),
    Tetrachord(
        index=552,
        genus="M60",
        steps=(F(180, 173), F(173, 159), F(53, 45)),
    ),
    Tetrachord(
        index=553,
        genus="M61",
        steps=(F(90, 83), F(166, 159), F(53, 45)),
    ),
    Tetrachord(
        index=554,
        genus="M62",
        steps=(F(24, 23), F(115, 106), F(53, 45)),
    ),
    Tetrachord(
        index=555,
        genus="M63",
        steps=(F(34, 29), F(58, 57), F(19, 17)),
    ),
    Tetrachord(
        index=556,
        genus="M64",
        steps=(F(10, 9), F(117, 100), F(40, 39)),
    ),
    Tetrachord(
        index=557,
        genus="M65",
        steps=(F(120, 113), F(113, 97), F(97, 90)),
    ),
    Tetrachord(
        index=558,
        genus="M66",
        steps=(F(13, 12), F(55, 52), F(64, 55)),
    ),
    Tetrachord(
        index=559,
        genus="M67",
        steps=(F(68, 65), F(65, 56), F(56, 51)),
    ),
    Tetrachord(
        index=560,
        genus="M68",
        steps=(F(12, 11), F(297, 256), F(256, 243)),
    ),
    Tetrachord(
        index=561,
        genus="M69",
        steps=(F(28, 27), F(81, 70), F(10, 9)),
    ),
    Tetrachord(
        index=562,
        genus="M70",
        steps=(F(81, 70), F(2240, 2187), F(9, 8)),
    ),
    Tetrachord(
        index=563,
        genus="M71",
        steps=(F(81, 70), F(256, 243), F(35, 32)),
    ),
    Tetrachord(
        index=564,
        genus="M72",
        steps=(F(135, 128), F(7168, 6561), F(81, 70)),
    ),
    Tetrachord(
        index=565,
        genus="M73",
        steps=(F(60, 59), F(59, 51), F(17, 15)),
    ),
    Tetrachord(
        index=566,
        genus="M74",
        steps=(F(40, 37), F(37, 32), F(16, 15)),
    ),
    Tetrachord(
        index=567,
        genus="M75",
        steps=(F(16, 15), F(280, 243), F(243, 224)),
    ),
    Tetrachord(
        index=568,
        genus="M76",
        steps=(F(36, 35), F(9, 8), F(280, 243)),
    ),
    Tetrachord(
        index=569,
        genus="M77",
        steps=(F(8, 7), F(81, 80), F(280, 243)),
    ),
    Tetrachord(
        index=570,
        genus="M78",
        steps=(F(46, 45), F(132, 115), F(25, 22)),
    ),
    Tetrachord(
        index=571,
        genus="M79",
        steps=(F(16, 15), F(12, 11), F(55, 48)),
    ),
    Tetrachord(
        index=572,
        genus="M80",
        steps=(F(10, 9), F(63, 55), F(22, 21)),
    ),
    Tetrachord(
        index=573,
        genus="M81",
        steps=(F(30, 29), F(116, 103), F(103, 90)),
    ),
    Tetrachord(
        index=574,
        genus="M82",
        steps=(F(360, 343), F(343, 309), F(103, 90)),
    ),
    Tetrachord(
        index=575,
        genus="M83",
        steps=(F(40, 39), F(143, 125), F(25, 22)),
    ),
    Tetrachord(
        index=576,
        genus="M84",
        steps=(F(68, 65), F(65, 57), F(19, 17)),
    ),
    Tetrachord(
        index=577,
        genus="M85",
        steps=(F(256, 243), F(729, 640), F(10, 9)),
    ),
    Tetrachord(
        index=578,
        genus="M86",
        steps=(F(30, 29), F(58, 51), F(17, 15)),
    ),
    Tetrachord(
        index=579,
        genus="M87",
        steps=(F(23, 21), F(14, 13), F(26, 23)),
    ),
    Tetrachord(
        index=580,
        genus="M88",
        steps=(F(23, 22), F(44, 39), F(26, 23)),
    ),
    Tetrachord(
        index=581,
        genus="M89",
        steps=(F(14, 13), F(260, 231), F(11, 10)),
    ),
    Tetrachord(
        index=582,
        genus="M90",
        steps=(F(4096, 3645), F(35, 32), F(243, 224)),
    ),
    Tetrachord(
        index=583,
        genus="M91",
        steps=(F(38, 35), F(35, 32), F(64, 57)),
    ),
    Tetrachord(
        index=584,
        genus="M92",
        steps=(F(19, 17), F(17, 16), F(64, 57)),
    ),
    Tetrachord(
        index=585,
        genus="M93",
        steps=(F(11, 10), F(95, 88), F(64, 57)),
    ),
    Tetrachord(
        index=586,
        genus="M94",
        steps=(F(240, 221), F(221, 202), F(101, 90)),
    ),
    Tetrachord(
        index=587,
        genus="M95",
        steps=(F(15, 14), F(112, 101), F(101, 90)),
    ),
    Tetrachord(
        index=588,
        genus="M96",
        steps=(F(120, 113), F(113, 101), F(101, 90)),
    ),
    Tetrachord(
        index=589,
        genus="M97",
        steps=(F(533, 483), F(575, 533), F(28, 25)),
    ),
    Tetrachord(
        index=590,
        genus="M98",
        steps=(F(19, 17), F(85, 76), F(16, 15)),
    ),
    Tetrachord(
        index=591,
        genus="M99",
        steps=(F(19, 17), F(1156, 1083), F(19, 17)),
    ),
    Tetrachord(
        index=592,
        genus="M100",
        steps=(F(68, 63), F(21, 19), F(19, 17)),
    ),
    Tetrachord(
        index=593,
        genus="M101",
        steps=(F(10, 9), F(108, 97), F(97, 90)),
    ),
    #
    # TETRACHORDS IN EQUAL TEMPERAMENT
    #
    # ARISTOXENIAN STYLE TETRACHORDS
    #
    PartsTetrachord(
        index=594,
        genus="T1",
        parts=(2, 2, 26),
        cents=(33, 33, 433),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=595,
        genus="T2",
        parts=(2.5, 2.5, 25),
        cents=(42, 42, 417),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=596,
        genus="T3",
        parts=(2, 3, 25),
        cents=(33, 50, 417),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=597,
        genus="T4",
        parts=(3, 3, 24),
        cents=(50, 50, 400),
        reference=R.aristoxenos,
    ),
    PartsTetrachord(
        index=598,
        genus="T5",
        parts=(2, 4, 24),
        cents=(33, 67, 400),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=599,
        genus="T6",
        parts=(2, 5, 23),
        cents=(33, 83, 383),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=600,
        genus="T7",
        parts=(F(7, 3), F(14, 3), 23),
        cents=(39, 78, 383),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=601,
        genus="T8",
        parts=(4, 3, 23),
        cents=(67, 50, 383),
        reference=R.chapter_3,
    ),
    PartsTetrachord(
        index=602,
        genus="T9",
        parts=(3.5, 3.5, 23),
        cents=(58, 58, 383),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=603,
        genus="T10",
        parts=(2, 6, 22),
        cents=(33, 100, 367),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=604,
        genus="T11",
        parts=(4, 4, 22),
        cents=(66, 66, 367),
        reference=R.aristoxenos,
    ),
    PartsTetrachord(
        index=605,
        genus="T12",
        parts=(F(8, 3), F(16, 3), 22),
        cents=(44, 89, 367),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=606,
        genus="T13",
        parts=(3, 5, 22),
        cents=(50, 83, 367),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=607,
        genus="T14",
        parts=(4.5, 3.5, 22),
        cents=(75, 58, 367),
        reference=R.aristoxenos,
    ),
    PartsTetrachord(
        index=608,
        genus="T15",
        parts=(2, 7, 21),
        cents=(33, 117, 350),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=609,
        genus="T16",
        parts=(3, 6, 21),
        cents=(50, 100, 350),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=610,
        genus="T17",
        parts=(4.5, 4.5, 21),
        cents=(75, 75, 350),
        reference=R.aristoxenos,
    ),
    PartsTetrachord(
        index=611,
        genus="T18",
        parts=(4, 5, 21),
        cents=(67, 83, 350),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=612,
        genus="T19",
        parts=(6, 3, 21),
        cents=(100, 50, 350),
        reference=R.aristoxenos,
    ),
    PartsTetrachord(
        index=613,
        genus="T20",
        parts=(6, 20, 4),
        cents=(100, 333, 67),
        reference=R.savas,
    ),
    PartsTetrachord(
        index=614,
        genus="T21",
        parts=(F(10, 3), F(20, 3), 20),
        cents=(56, 111, 333),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=615,
        genus="T22",
        parts=(5, 5, 20),
        cents=(83, 83, 333),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=616,
        genus="T23",
        parts=(5.5, 5.5, 19),
        cents=(92, 92, 317),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=617,
        genus="T24",
        parts=(F(11, 3), F(22, 3), 19),
        cents=(61, 122, 317),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=618,
        genus="T25",
        parts=(5, 19, 6),
        cents=(83, 317, 100),
        reference=R.xenakis,
    ),
    PartsTetrachord(
        index=619,
        genus="T26",
        parts=(5, 6, 19),
        cents=(83, 100, 317),
        reference=R.macran,
    ),
    PartsTetrachord(
        index=620,
        genus="T27",
        parts=(2, 10, 18),
        cents=(33, 167, 300),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=621,
        genus="T28",
        parts=(3, 9, 18),
        cents=(50, 150, 300),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=622,
        genus="T29",
        parts=(4, 8, 18),
        cents=(67, 133, 301),
        reference=R.aristoxenos,
    ),
    PartsTetrachord(
        index=623,
        genus="T30",
        parts=(4.5, 7.5, 18),
        cents=(75, 125, 300),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=624,
        genus="T31",
        parts=(6, 6, 18),
        cents=(100, 100, 300),
        reference=R.aristoxenos,
    ),
    PartsTetrachord(
        index=625,
        genus="T32",
        parts=(5, 7, 18),
        cents=(83, 117, 300),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=626,
        genus="T33",
        parts=(6, 18, 6),
        cents=(100, 300, 100),
        reference=R.athanasopoulos,
    ),
    PartsTetrachord(
        index=627,
        genus="T34",
        parts=(F(13, 3), F(26, 3), 17),
        cents=(72, 144, 283),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=628,
        genus="T35",
        parts=(6.5, 6.5, 17),
        cents=(108, 108, 283),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=629,
        genus="T36",
        parts=(2, 16, 12),
        cents=(33, 267, 200),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=630,
        genus="T37",
        parts=(F(14, 3), F(28, 3), 16),
        cents=(78, 156, 267),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=631,
        genus="T38",
        parts=(5, 9, 16),
        cents=(83, 150, 267),
        reference=R.winnington_ingram,
    ),
    PartsTetrachord(
        index=632,
        genus="T39",
        parts=(8, 16, 6),
        cents=(133, 267, 100),
        reference=R.savas,
    ),
    PartsTetrachord(
        index=633,
        genus="T40",
        parts=(7, 16, 7),
        cents=(117, 267, 117),
        reference=f"{R.xenakis}; {R.chapter_4}",
    ),
    PartsTetrachord(
        index=634,
        genus="T41",
        parts=(2, 13, 15),
        cents=(33, 217, 250),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=635,
        genus="T42",
        parts=(3, 12, 15),
        cents=(50, 200, 250),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=636,
        genus="T43",
        parts=(4, 11, 15),
        cents=(67, 183, 250),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=637,
        genus="T44",
        parts=(5, 10, 15),
        cents=(83, 167, 250),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=638,
        genus="T45",
        parts=(6, 9, 15),
        cents=(100, 150, 250),
        reference=R.aristoxenos,
    ),
    PartsTetrachord(
        index=639,
        genus="T46",
        parts=(7, 8, 15),
        cents=(117, 133, 250),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=640,
        genus="T47",
        parts=(7.5, 7.5, 15),
        cents=(125, 125, 250),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=641,
        genus="T48",
        parts=(9, 15, 6),
        cents=(150, 250, 100),
        reference=R.athanasopoulos,
    ),
    PartsTetrachord(
        index=642,
        genus="T49",
        parts=(2, 14, 14),
        cents=(33, 233, 233),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=643,
        genus="T50",
        parts=(4, 14, 12),
        cents=(67, 233, 200),
        reference=R.aristoxenos,
    ),
    PartsTetrachord(
        index=644,
        genus="T51",
        parts=(5, 11, 14),
        cents=(83, 183, 233),
        reference=R.winnington_ingram,
    ),
    PartsTetrachord(
        index=645,
        genus="T52",
        parts=(F(16, 3), F(32, 3), 14),
        cents=(89, 178, 233),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=646,
        genus="T53",
        parts=(8, 8, 14),
        cents=(133, 133, 233),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=647,
        genus="T54",
        parts=(4.5, 13.5, 12),
        cents=(75, 225, 200),
        reference=R.aristoxenos,
    ),
    PartsTetrachord(
        index=648,
        genus="T55",
        parts=(5, 12, 13),
        cents=(83, 200, 217),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=649,
        genus="T56",
        parts=(4, 13, 13),
        cents=(67, 217, 217),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=650,
        genus="T57",
        parts=(F(17, 3), F(34, 3), 13),
        cents=(94, 189, 217),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=651,
        genus="T58",
        parts=(8.5, 8.5, 13),
        cents=(142, 142, 217),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=652,
        genus="T59",
        parts=(6, 12, 12),
        cents=(100, 200, 200),
        reference=R.aristoxenos,
    ),
    PartsTetrachord(
        index=653,
        genus="T60",
        parts=(12, 11, 7),
        cents=(200, 183, 117),
        reference=R.xenakis,
    ),
    PartsTetrachord(
        index=654,
        genus="T61",
        parts=(10, 8, 12),
        cents=(167, 133, 200),
        reference=R.savas,
    ),
    PartsTetrachord(
        index=655,
        genus="T62",
        parts=(12, 9, 9),
        cents=(200, 150, 150),
        reference=f"{R.al_farabi}; {R.chapter_4}",
    ),
    PartsTetrachord(
        index=656,
        genus="T63",
        parts=(8, 11, 11),
        cents=(133, 183, 183),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=657,
        genus="T64",
        parts=(9.5, 9.5, 11),
        cents=(158, 158, 183),
        reference=R.chapter_4,
    ),
    PartsTetrachord(
        index=658,
        genus="T65",
        parts=(10, 10, 10),
        cents=(166, 167, 167),
        reference=R.al_farabi,
    ),
    PartsTetrachord(
        index=659,
        genus="T66",
        parts=(12, 13, 3),
        cents=(212, 229, 53),
        fourth=494.0,
        reference=R.tiby,
    ),
    PartsTetrachord(
        index=660,
        genus="T67",
        parts=(12, 5, 11),
        cents=(212, 88, 194),
        fourth=494.0,
        reference=R.tiby,
    ),
    PartsTetrachord(
        index=661,
        genus="T68",
        parts=(12, 9, 7),
        cents=(212, 159, 124),
        fourth=494.0,
        reference=R.tiby,
    ),
    PartsTetrachord(
        index=662,
        genus="T69",
        parts=(9, 12, 7),
        cents=(159, 212, 124),
        fourth=494.0,
        reference=R.tiby,
    ),
    #
    # TEMPERED TETRACHORDS IN CENTS
    #
    CentsTetrachord(
        index=663,
        genus="T70",
        cents=(22.7, 22.7, 454.4),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=664,
        genus="T71",
        cents=(37.5, 37.5, 425),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=665,
        genus="T72",
        cents=(62.5, 62.5, 375),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=666,
        genus="T73",
        cents=(95, 115, 290),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=667,
        genus="T74",
        cents=(89, 289, 122),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=668,
        genus="T75",
        cents=(87.5, 287.5, 125),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=669,
        genus="T76",
        cents=(83.3, 283.3, 133.3),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=670,
        genus="T77",
        cents=(75, 275, 150),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=671,
        genus="T78",
        cents=(100, 275, 125),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=672,
        genus="T79",
        cents=(55, 170, 275),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=673,
        genus="T80",
        cents=(66.7, 266.7, 166.7),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=674,
        genus="T81",
        cents=(233.3, 16.7, 250),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=675,
        genus="T82",
        cents=(225, 25, 250),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=676,
        genus="T83",
        cents=(66.7, 183.3, 250),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=677,
        genus="T84",
        cents=(75, 175, 250),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=678,
        genus="T85",
        cents=(125, 125, 250),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=679,
        genus="T86",
        cents=(105, 145, 250),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=680,
        genus="T87",
        cents=(110, 140, 250),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=681,
        genus="T88",
        cents=(87.5, 237.5, 175),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=682,
        genus="T89",
        cents=(233.3, 166.7, 100),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=683,
        genus="T90",
        cents=(212.5, 62.5, 225),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=684,
        genus="T91",
        cents=(225, 75, 200),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=685,
        genus="T92",
        cents=(225, 175, 100),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=686,
        genus="T93",
        cents=(87.5, 187.5, 225),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=687,
        genus="T94",
        cents=(212.5, 162.5, 125),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=688,
        genus="T95",
        cents=(100, 187.5, 212.5),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=689,
        genus="T96",
        cents=(212.5, 137.5, 150),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=690,
        genus="T97",
        cents=(200, 125, 175),
        reference=R.chapter_5,
    ),
    CentsTetrachord(
        index=691,
        genus="T98",
        cents=(145, 165, 190),
        reference=R.chapter_5,
    ),
]


# Symbolic Fraction
def f(x, y):
    return Integer(x) / y


A = f(4, 3)

# Add semi-tempered tetrachords
# Use sympy evaluate False so 1/sqrt(3) isn't rewritten as sqrt(3)/3
with evaluate(False):
    CATALOG += [
        SemiTemperedTetrachord(
            index=692,
            genus="S1",
            steps=(16 / (9 * sqrt(3)), 16 / (9 * sqrt(3)), F(81, 64)),
            cents=(45, 45, 408),
        ),
        SemiTemperedTetrachord(
            index=693,
            genus="S2",
            steps=(1.26376, 1.05231, 1.00260),
            cents=(405, 88, 4),
            comment="Originally printed as 1.26376 * 1.05321 * 1.00260",
        ),
        SemiTemperedTetrachord(
            index=694,
            genus="S3",
            steps=(A ** f(1, 10), A ** f(1, 10), A ** f(8, 10)),
            cents=(50, 50, 398),
        ),
        SemiTemperedTetrachord(
            index=695,
            genus="S4",
            steps=(A ** f(2, 15), A ** f(2, 15), A ** f(11, 15)),
            cents=(66, 66, 365),
        ),
        SemiTemperedTetrachord(
            index=696,
            genus="S5",
            steps=(A ** f(3, 20), A ** f(7, 60), A ** f(11, 15)),
            cents=(75, 58, 365),
        ),
        SemiTemperedTetrachord(
            index=697,
            genus="S6",
            steps=(A ** f(3, 20), A ** f(3, 20), A ** f(7, 10)),
            cents=(75, 75, 349),
        ),
        SemiTemperedTetrachord(
            index=698,
            genus="S7",
            steps=(A ** f(1, 5), A ** f(1, 10), A ** f(7, 10)),
            cents=(100, 50, 349),
        ),
        SemiTemperedTetrachord(
            index=699,
            genus="S8",
            steps=(1.21677, 1.03862, 1.05505),
            cents=(340, 66, 93),
        ),
        SemiTemperedTetrachord(
            index=700,
            genus="S9",
            steps=(A ** f(1, 5), A ** f(1, 5), A ** f(3, 5)),
            cents=(100, 100, 299),
        ),
        SemiTemperedTetrachord(
            index=701,
            genus="S10",
            steps=(A ** f(2, 15), A ** f(4, 15), A ** f(3, 5)),
            cents=(66, 133, 299),
        ),
        SemiTemperedTetrachord(
            index=702,
            genus="S11",
            steps=((3 * sqrt(2)) / 4, (3 * sqrt(2)) / 4, f(32, 27)),
            cents=(102, 102, 294),
        ),
        SemiTemperedTetrachord(
            index=703,
            genus="S12",
            steps=(1.18046, 1.06685, 1.05873),
            cents=(287, 112, 99),
        ),
        SemiTemperedTetrachord(
            index=704,
            genus="S13",
            steps=(1.05956, 1.06763, 1.17876),
            cents=(100, 113, 285),
        ),
        SemiTemperedTetrachord(
            index=705,
            genus="S14",
            steps=(1.17867, 1.06763, 1.05963),
            cents=(285, 113, 100),
        ),
        SemiTemperedTetrachord(
            index=706,
            genus="S15",
            steps=(1.17851, 1.06771, 1.05963),
            cents=(284, 113, 100),
        ),
        # TODO calculate S16 using mean 6
        SemiTemperedTetrachord(
            index=707,
            genus="S16",
            steps=(1.17691, 1.06807, 1.06069),
            cents=(282, 114, 102),
            comment="Originally printed as 1.17851 * 1.06771 * 1.05963, same as S15",
        ),
        SemiTemperedTetrachord(
            index=708,
            genus="S17",
            steps=(A ** f(1, 5), A ** f(3, 10), A ** f(1, 2)),
            cents=(100, 149, 250),
        ),
        SemiTemperedTetrachord(
            index=709,
            genus="S18",
            steps=(1.07457, 1.07457, 1.154701),
            cents=(125, 125, 249),
        ),
        SemiTemperedTetrachord(
            index=710,
            genus="S19",
            steps=(A ** f(2, 15), A ** f(7, 15), A ** f(2, 5)),
            cents=(66, 232, 199),
        ),
        SemiTemperedTetrachord(
            index=711,
            genus="S20",
            steps=(1.13847, 1.1250, 1.0410),
            cents=(225, 204, 70),
        ),
        SemiTemperedTetrachord(
            index=712,
            genus="S21",
            steps=(A ** f(3, 20), A ** f(9, 20), A ** f(2, 5)),
            cents=(75, 224, 199),
        ),
        SemiTemperedTetrachord(
            index=713,
            genus="S22",
            steps=(1.13371, 1.1250, 1.04540),
            cents=(217, 204, 77),
        ),
        SemiTemperedTetrachord(
            index=714,
            genus="S23",
            steps=(1.13315, 1.1250, 1.04595),
            cents=(216, 204, 78),
        ),
        SemiTemperedTetrachord(
            index=715,
            genus="S24",
            steps=(1.09185, 1.07803, 1.13278),
            cents=(152, 130, 216),
        ),
        SemiTemperedTetrachord(
            index=716,
            genus="S25",
            steps=(1.09291, 1.078328, 1.13137),
            cents=(154, 131, 214),
        ),
        SemiTemperedTetrachord(
            index=717,
            genus="S26",
            steps=(1.09301, 1.07837, 1.13122),
            cents=(154, 131, 213),
        ),
        SemiTemperedTetrachord(
            index=718,
            genus="S27",
            steps=(1.09429, 1.07874, 1.12950),
            cents=(156, 131, 211),
        ),
        SemiTemperedTetrachord(
            index=719,
            genus="S28",
            steps=(1.12950, 1.1250, 1.04930),
            cents=(211, 204, 83),
        ),
        SemiTemperedTetrachord(
            index=720,
            genus="S29",
            steps=(1.08866, 1.1250, 1.08866),
            cents=(147, 204, 147),
        ),
        SemiTemperedTetrachord(
            index=721,
            genus="S30",
            steps=(A ** f(1, 5), A ** f(2, 5), A ** f(2, 5)),
            cents=(100, 199, 199),
        ),
        SemiTemperedTetrachord(
            index=722,
            genus="S31",
            steps=(A ** f(1, 3), A ** f(1, 3), A ** f(1, 3)),
            cents=(166, 166, 166),
        ),
        SemiTemperedTetrachord(
            index=723,
            genus="S32",
            steps=(A ** f(2, 5), A ** f(3, 10), A ** f(3, 10)),
            cents=(200, 149, 149),
        ),
    ]


def validate_catalog():
    group = defaultdict(lambda: set())
    for i, t in enumerate(CATALOG, 1):
        assert t.index == i
        # Tetrachord 295 doesn't contain the characteristic interval of its genus
        if t.genus in CHARACTERISTIC_INTERVAL and t.index not in {295}:
            assert CHARACTERISTIC_INTERVAL[t.genus] in t.steps
        if isinstance(t, (Tetrachord, SemiTemperedTetrachord)):
            group[t.steps].add(t.index)
        elif isinstance(t, PartsTetrachord):
            group[t.parts].add(t.index)
        elif isinstance(t, CentsTetrachord):
            group[t.cents].add(t.index)
        else:
            raise ValueError(t)
    duplicates = {k: v for k, v in group.items() if len(v) > 1}
    assert not duplicates

    assert len(CATALOG) == 723


def category(t: Tetrachord):
    return {
        "H": "Hyperenharmonic",
        "E": "Enharmonic",
        "C": "Chromatic",
        "D": "Diatonic",
        "R": "Reduplicated",
        "M": "Miscellaneous",
    }[t.genus[0]]


def write_tetrachord_scl(t: Tetrachord):
    filename, scl_text = t.to_scl()
    (OUTPUT_DIR / filename).write_text(scl_text)


def main():
    logger.info("Building Divisions of the Tetrachord scales")
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    OUTPUT_DIR.mkdir()
    validate_catalog()
    for tetrachord in CATALOG:
        write_tetrachord_scl(tetrachord)

    return utils.check_scl_dir(OUTPUT_DIR)


if __name__ == "__main__":
    utils.setup_logging()
    main()
