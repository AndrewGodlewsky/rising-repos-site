"""History's calendar: which days a month's grid holds, and under which weekday each sits (#50).

`calendar` in `sitebuild/__init__.py` lays the board days out as months of whole weeks from Monday. The tests of a
built page hold the months the example has, and the shade a count takes. The mutation report on `sitebuild/` (#47)
changed how a month's days and its last week are worked out 32 ways that no test noticed: a December whose days
run into the wrong year, a last week left short, a day with no board shown outside the days the site holds.

So these give it a few made-up boards and hold what its docstring says, against the calendar Python itself keeps.
"""

import calendar as months
import unittest
from datetime import date

from sitebuild import History, calendar


def boards(*days: str) -> list[dict]:
    """A board of one row on each of these days, newest first as the index gives them."""
    listed = sorted(days, reverse=True)
    return [{"board_day": day, "rows": [{"github_id": 1, "full_name": "octo/cat"}]} for day in listed]


def laid_out(*days: str) -> dict[str, list[list[dict | None]]]:
    """Each month's weeks, by the month."""
    held = boards(*days)
    return {month["month"]: month["weeks"] for month in calendar(held, History(held))}


class TheCalendar(unittest.TestCase):
    def test_a_month_is_whole_weeks_from_monday_with_each_of_its_days_once_under_its_own_weekday(self):
        # From the first of one month to the last of another, so that every day between has a cell: a November and a
        # December, whose following months are in this year and the next, a February of 28 days, and a month that
        # begins on a Monday.
        spans = (("2026-11-01", "2027-01-31"), ("2027-02-01", "2027-03-31"), ("2026-06-01", "2026-06-30"))
        for first, last in spans:
            for month, weeks in laid_out(first, last).items():
                with self.subTest(month=month):
                    year, number = (int(part) for part in month.split("-"))
                    self.assertTrue(all(len(week) == 7 for week in weeks))
                    cells = [(place, cell) for week in weeks for place, cell in enumerate(week) if cell]
                    self.assertEqual(
                        [cell["day"] for _, cell in cells],
                        [
                            date(year, number, day).isoformat()
                            for day in range(1, months.monthrange(year, number)[1] + 1)
                        ],
                    )
                    for place, cell in cells:
                        self.assertEqual(place, date.fromisoformat(cell["day"]).weekday(), cell["day"])
                    # No week is empty: the grid ends with the week that holds the month's last day.
                    self.assertTrue(all(any(week) for week in weeks))

    def test_a_day_with_no_board_has_a_cell_with_no_count_between_the_first_board_and_the_newest_and_none_outside(self):
        weeks = laid_out("2026-11-10", "2026-11-20")["2026-11"]
        cells = {cell["date"]: cell for week in weeks for cell in week if cell}
        self.assertEqual(sorted(cells), list(range(10, 21)))
        self.assertEqual([cells[day]["count"] for day in (10, 20)], [1, 1])
        self.assertEqual({cells[day]["count"] for day in range(11, 20)}, {None})


if __name__ == "__main__":
    unittest.main()
