"""The site words and rounds every number it shows, by rules that hold for any number and not for the few a test
names (#40).

README.md says that the site "computes no score and no rank: it words and rounds the numbers the file gives".
`figure` and `times` in `sitebuild/__init__.py` do the wording, and their docstrings give the rules. The examples
in `tests/test_reasons.py` hold fourteen numbers to them, none below 0 and none that rounds to 0. Here Hypothesis
makes the numbers up, some hundreds for each rule, and each rule is written from the docstring: what a reader
would check with a pencil, and not what the function did.

The numbers are the same on every run, on the machine and in the job (`derandomize`), because a feature's check
runs these tests with nobody watching, and a number that fails on one run and not on the next would stop a
feature that did not touch the wording. No time limit is set on a test (`deadline`), since the machine runs the
tests slowly at times, and nothing is kept between runs (`database`).
"""

import re
import unittest
from decimal import Decimal

from hypothesis import example, given, settings
from hypothesis import strategies as st

from sitebuild import MINUS, figure, times

SAME_EVERY_RUN = settings(derandomize=True, deadline=None, database=None, max_examples=500)

WRITTEN = re.compile(rf"{MINUS}?(?:0|[1-9]\d{{0,2}}(?:,\d{{3}})*)(?:\.\d*[1-9])?")
"""How a figure is written: the true minus or nothing, whole digits parted in threes by commas, and then at most a
point and decimals that do not end in 0."""

FLOATS = st.floats(min_value=-10_000_000, max_value=10_000_000, allow_nan=False, allow_infinity=False)
THOUSANDTHS = st.integers(min_value=-10_000_000_000, max_value=10_000_000_000).map(lambda count: count / 1000)
"""Numbers with three decimal places at most, which is where a number lies exactly half way between two it could
be rounded to: 8.125 to two places, 10.5 to none."""
NUMBERS = st.one_of(FLOATS, THOUSANDTHS)
PLACES = st.integers(min_value=0, max_value=2)


def as_json_wrote_it(value: float) -> Decimal:
    """The number as the file's JSON holds it, which is what a reader sees and rounds."""
    return Decimal(repr(value))


def read_back(shown: str) -> Decimal:
    """The number a reader takes a written figure for."""
    return Decimal(shown.replace(",", "").replace(MINUS, "-"))


def decimals(shown: str) -> int:
    return len(shown.partition(".")[2])


class AnyNumber(unittest.TestCase):
    @SAME_EVERY_RUN
    @given(NUMBERS, PLACES)
    @example(-0.004, 2)
    @example(-10.5, 0)
    def test_a_figure_is_the_nearest_it_can_be_at_its_places_and_a_half_goes_to_the_larger(self, value, places):
        was, shown = as_json_wrote_it(value), read_back(figure(value, places))
        half = Decimal(5).scaleb(-places - 1)
        self.assertLessEqual(abs(shown - was), half)
        if abs(shown - was) == half:
            self.assertGreater(abs(shown), abs(was))

    @SAME_EVERY_RUN
    @given(NUMBERS, PLACES)
    @example(260.0, 2)
    @example(87779.66666666667, 0)
    def test_a_figure_parts_its_thousands_and_ends_in_no_zero_and_no_point(self, value, places):
        shown = figure(value, places)
        self.assertRegex(shown, rf"^{WRITTEN.pattern}$")
        self.assertLessEqual(decimals(shown), places)

    @SAME_EVERY_RUN
    @given(NUMBERS, PLACES)
    @example(-0.004, 2)
    @example(-3.421, 2)
    def test_a_figure_below_0_takes_the_true_minus_and_one_that_rounds_to_0_takes_no_sign(self, value, places):
        shown = figure(value, places)
        self.assertNotIn("-", shown)
        if read_back(shown) == 0:
            self.assertEqual(shown, "0")
        else:
            self.assertEqual(shown.startswith(MINUS), value < 0)

    @SAME_EVERY_RUN
    @given(NUMBERS, PLACES)
    def test_a_figure_below_0_is_written_as_the_same_figure_above_0_with_the_minus_before_it(self, value, places):
        above = figure(abs(value), places)
        self.assertEqual(figure(-abs(value), places), above if above == "0" else MINUS + above)

    @SAME_EVERY_RUN
    @given(NUMBERS)
    @example(9.96)
    @example(-12.34)
    @example(9.94)
    def test_a_multiple_takes_one_decimal_place_under_10_and_none_from_10_above_0_or_below(self, score):
        shown = times(score)
        size = abs(read_back(shown))
        self.assertLessEqual(decimals(shown), 1 if size < 10 else 0)
        self.assertLessEqual(
            abs(read_back(shown) - as_json_wrote_it(score)), Decimal("0.05") if size < 10 else Decimal("0.5")
        )
        self.assertRegex(shown, rf"^{WRITTEN.pattern}$")


if __name__ == "__main__":
    unittest.main()
