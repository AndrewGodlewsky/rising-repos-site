"""Where a sentence of the site turns: the edge at which one wording gives way to another (#50).

The site says a thing one way on one side of a number and another way on the other: a repository's usual pace at
the floor or under it, a pace that was falling, a gain or a loss, a board made late, the star band a count falls
in. The tests of a built page hold each wording on a row well inside it. The mutation report on `sitebuild/`
(#47) moved these edges 80 ways that no test noticed, since no row stood on one.

So each test here puts a number on the edge and on each side of it, and holds what the function's own docstring
says of the three.
"""

import unittest

from sitebuild import MADE_LATE, Band, band_name, gain_class, growth, made_late, per_day_class, why


def row(baseline: float, divided_by: float = 1, **more) -> dict:
    """A row that gained 96 stars in two days, with this usual pace and the divisor its score took."""
    numbers = {"recent_stars": 96, "recent_days": 2, "days_left_out": 0, "excess": 90.0}
    return {**numbers, "baseline": baseline, "divided_by": divided_by, "score": 48 / divided_by, **more}


class TheReason(unittest.TestCase):
    def test_a_usual_pace_of_nothing_was_under_the_floor_and_one_below_nothing_had_been_losing_stars(self):
        self.assertIn("its usual pace was under 1 star a day", why(row(baseline=0))["line"])
        self.assertIn("it had been losing stars", why(row(baseline=-0.01))["line"])
        self.assertEqual(growth(row(baseline=0))["note"], "baseline under 1 a day")
        self.assertEqual(growth(row(baseline=-0.01))["note"], "it had been losing stars")

    def test_the_stars_above_its_own_trend_are_given_at_a_usual_pace_of_nothing_and_not_below_it(self):
        self.assertEqual(why(row(baseline=0))["above"], "90")
        self.assertIsNone(why(row(baseline=-0.01))["above"])
        self.assertIn("+96 in 2 days", why(row(baseline=-0.01))["line"])


class AGain(unittest.TestCase):
    def test_a_gains_cell_is_a_loss_below_nothing_and_nil_at_nothing_and_neither_for_the_smallest_gain(self):
        self.assertEqual(
            [gain_class(-0.5), gain_class(0), gain_class(None), gain_class(0.5)], [" loss", " nil", " nil", ""]
        )

    def test_a_rows_gain_a_day_takes_its_class_from_what_it_gained_over_its_recent_days(self):
        def gained(stars: int, days: int) -> str:
            return per_day_class({"recent_stars": stars, "recent_days": days})

        # A star in two days is a gain, though it is under one a day, and a star lost in two days is a loss.
        self.assertEqual([gained(1, 2), gained(-1, 2), gained(0, 2), gained(-3, 1)], ["", " loss", " nil", " loss"])


class ABoard(unittest.TestCase):
    def test_a_board_published_many_days_after_its_day_was_made_late_as_one_two_days_after_was(self):
        def published(days_after: int) -> dict:
            return {"board_day": "2026-11-09", "published_at": f"2026-11-{9 + days_after:02}T00:41:07Z"}

        self.assertEqual(MADE_LATE, 2)
        self.assertEqual([made_late(published(after)) for after in (0, 1, 2, 5)], [False, False, True, True])

    def test_a_count_of_stars_at_a_bands_stop_falls_in_the_band_above(self):
        bands = [
            Band(number=0, label="200–1k", below=1000, word="200-1k", name="200–1k"),
            Band(number=1, label="1k–3k", below=3000, word="1k-3k", name="1k–3k"),
            Band(number=2, label="3k+", below=None, word="3k-plus", name="3k or more"),
        ]
        names = [band_name(bands, stars) for stars in (999, 1000, 2999, 3000, 500000)]
        self.assertEqual(names, ["200–1k", "1k–3k", "1k–3k", "3k or more", "3k or more"])


if __name__ == "__main__":
    unittest.main()
