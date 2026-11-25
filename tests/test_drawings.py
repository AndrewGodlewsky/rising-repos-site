"""The two drawings: that a mark is where its figures say (#50).

`pace_chart` places every row of a board on Baseline's chart, by its usual pace across and its recent pace up,
and `own_pace` draws one row's two paces as levels. The tests of a built page see that each drawing is there and
what it says. The mutation report on `sitebuild/` (#47) changed where a mark is put 247 ways that no test
noticed, the name of a guide among them.

A test of each coordinate would take its value from a run of the code. These hold what a reader could lose: a
dot at the tick of its pace, a row on the guide of its multiple, rows that sit close under one label, a higher
pace drawn higher. Each is a relation between what a row's figures are and where its mark is, so a change to the
drawing's room or its size leaves them standing, and a mark put in the wrong place does not.
"""

import math
import re
import unittest

from sitebuild import LABELLED, PACE_SCALE, TOP, own_pace, pace_chart

DOT = re.compile(r"M([\d.-]+) ([\d.-]+)h0")
"""A dot in one of the chart's two paths: how far across it is and how far down, in hundredths of the plot."""

TENTH = 0.1
"""A dot is placed to a tenth of a hundredth of the plot, and a label and a tick to a hundredth."""


def chart(*paces: tuple[float, float]) -> dict:
    """The chart of a board whose rows have these paces, in rank order: the usual pace, and the recent one."""
    return pace_chart(
        [{"rank": rank, "divided_by": usual, "score": recent / usual} for rank, (usual, recent) in enumerate(paces, 1)]
    )


def dots(drawn: dict) -> list[tuple[float, float]]:
    """Each dot, in the order drawn: across and down."""
    return [(float(across), float(down)) for across, down in DOT.findall(drawn["lead"] + drawn["rest"])]


def levels(row: dict) -> dict[str, float]:
    """The levels of a row's own pace, by their names in its style."""
    return {name: float(value) for name, value in re.findall(r"--(\w):([\d.]+)", own_pace(row)["style"])}


def pace(usual: float, recent: float, days: int = 2) -> dict:
    """A row whose usual pace and recent pace are these, over `days` recent days."""
    return {"baseline": usual, "recent_stars": recent * days, "recent_days": days}


class BaselinesChart(unittest.TestCase):
    def test_every_row_is_one_dot_in_the_boards_order_with_the_first_rows_in_a_path_of_their_own(self):
        drawn = chart(*[(2.0**place, 2.0 ** (place + 2)) for place in range(TOP + 5)])
        across = [dot[0] for dot in dots(drawn)]
        self.assertEqual((drawn["count"], len(across)), (TOP + 5, TOP + 5))
        self.assertEqual((len(DOT.findall(drawn["lead"])), len(DOT.findall(drawn["rest"]))), (TOP, 5))
        # Each row's usual pace is twice the one before, so each dot is further across than the last.
        self.assertEqual(across, sorted(across))
        self.assertEqual(len(set(across)), len(across))

    def test_a_dot_sits_at_the_tick_of_its_usual_pace_across_and_of_its_recent_pace_up(self):
        drawn = chart((1, 10), (10, 100), (100, 1000))
        across = {tick["text"]: tick["at"] for tick in drawn["xticks"]}
        up = {tick["text"]: tick["at"] for tick in drawn["yticks"]}
        self.assertEqual((list(across), list(up)), (["1", "10", "100"], ["1", "10", "100", "1,000"]))
        for (left, top), usual, recent in zip(dots(drawn), ("1", "10", "100"), ("10", "100", "1,000"), strict=True):
            self.assertAlmostEqual(left, across[usual], delta=TENTH)
            self.assertAlmostEqual(top, up[recent], delta=TENTH)
        # Ten times the pace is the same step every time, and a faster recent pace is higher up the plot.
        self.assertAlmostEqual(across["10"] - across["1"], across["100"] - across["10"], delta=0.02)
        self.assertAlmostEqual(up["1"] - up["10"], up["100"] - up["1,000"], delta=0.02)
        self.assertGreater(up["1"], up["1,000"])
        self.assertGreater(across["100"], across["1"])
        # The axis fills the plot, and its first tick and its last stand a little inside the frame.
        self.assertTrue(0 < across["1"] < 10 and 90 < across["100"] < 100, across)

    def test_a_row_gaining_at_a_guides_multiple_of_its_usual_pace_lies_on_that_guide(self):
        multiples = (1, 3, 10, 100, 1000)
        # Once on a board whose usual paces begin at 1 star a day, and once on one where they begin at 100.
        for slowest in (1.0, 100.0):
            rows = [(10 * slowest, 10 * slowest * multiple) for multiple in multiples]
            drawn = chart(*rows, (slowest, 2 * slowest), (100 * slowest, 150 * slowest))
            guides = {guide["multiple"]: guide for guide in drawn["guides"]}
            self.assertEqual(sorted(guides), list(multiples))
            self.on_their_guides(dots(drawn), guides, multiples, slowest)

    def on_their_guides(self, placed: list, guides: dict, multiples: tuple, slowest: float) -> None:
        for (left, top), multiple in zip(placed, multiples, strict=False):
            with self.subTest(multiple=multiple, slowest=slowest):
                guide = guides[multiple]
                run, rise = guide["x2"] - guide["x1"], guide["y2"] - guide["y1"]
                # How far the dot is from the line through the guide's two ends, in hundredths of the plot.
                away = abs((left - guide["x1"]) * rise - (top - guide["y1"]) * run) / math.hypot(run, rise)
                self.assertLess(away, 2 * TENTH)
                # The guide runs up to the right, across the plot and not along one edge of it.
                self.assertGreater(run, 10)
                self.assertLess(rise, -10)

    def test_a_guide_that_would_lie_outside_the_plot_is_not_drawn(self):
        # Usual paces from 1 to 10 and recent paces up to 50, so the plot reaches 100 stars a day at most. Ten times
        # a usual pace is in it for every row, and 1,000 times the slowest usual pace is ten times past its top.
        drawn = [guide["multiple"] for guide in chart((1.0, 2.0), (10.0, 50.0))["guides"]]
        self.assertNotIn(1000, drawn)
        self.assertEqual(drawn[:3], [1, 3, 10])

    def test_the_first_rows_are_named_by_rank_at_their_dot_and_rows_that_sit_close_share_one_label(self):
        drawn = chart((1.0, 10.0), (1.05, 10.5), (100.0, 5000.0), *[(3.0 * 3**place, 2.0) for place in range(LABELLED)])
        placed = dots(drawn)
        labels = {label["text"]: (label["left"], label["top"]) for label in drawn["labels"]}
        # Ranks 1 and 2 are a hair apart, and rank 3 is far from both. Only the first LABELLED rows are named.
        self.assertEqual(list(labels)[:2], ["1, 2", "3"])
        self.assertEqual(sum(len(text.split(", ")) for text in labels), LABELLED)
        for text, rank in (("1, 2", 1), ("3", 3)):
            self.assertAlmostEqual(labels[text][0], placed[rank - 1][0], delta=TENTH)
            self.assertAlmostEqual(labels[text][1], placed[rank - 1][1], delta=TENTH)

    def test_rows_far_apart_across_or_up_each_keep_a_label_of_their_own(self):
        # The same usual pace and recent paces far apart, and then the same recent pace and usual paces far apart.
        self.assertEqual([label["text"] for label in chart((10.0, 20.0), (10.0, 2000.0))["labels"]], ["1", "2"])
        self.assertEqual([label["text"] for label in chart((1.0, 500.0), (100.0, 500.0))["labels"]], ["1", "2"])

    def test_the_floor_counts_the_rows_whose_usual_pace_is_one_star_a_day(self):
        self.assertEqual(chart((1, 10), (1, 30), (2, 30), (40, 80))["floor"], 2)


class ARowsOwnPace(unittest.TestCase):
    def test_a_recent_pace_above_the_usual_is_drawn_higher_and_one_below_it_lower(self):
        above, level, below = levels(pace(10, 80)), levels(pace(10, 10)), levels(pace(10, 2))
        self.assertLess(above["r"], above["u"])
        self.assertEqual(level["r"], level["u"])
        self.assertGreater(below["r"], below["u"])
        # The usual pace is the same in all three, and so is its level.
        self.assertEqual({above["u"], level["u"], below["u"]}, {level["u"]})

    def test_ten_times_the_pace_is_the_same_step_up_wherever_it_starts(self):
        usual = [levels(pace(value, value))["u"] for value in (0.5, 5, 50, 500, 5000)]
        steps = [lower - higher for lower, higher in zip(usual, usual[1:], strict=False)]
        # Each level is written to a hundredth, so two steps may differ by that and no more.
        self.assertLess(max(steps) - min(steps), 0.011, steps)
        self.assertGreater(min(steps), 0.1)

    def test_a_pace_off_either_end_of_the_scale_sits_at_that_end_and_the_scale_is_the_same_for_every_row(self):
        bottom, top = PACE_SCALE
        self.assertEqual(levels(pace(bottom / 100, bottom / 100))["u"], levels(pace(bottom, bottom))["u"])
        self.assertEqual(levels(pace(top * 100, top * 100))["u"], levels(pace(top, top))["u"])
        # A falling pace sits on the bottom with them, and the bottom is lower down than the top.
        self.assertEqual(levels(pace(-3, -3))["u"], levels(pace(bottom, bottom))["u"])
        self.assertGreater(levels(pace(bottom, bottom))["u"], levels(pace(top, top))["u"])
        # Both ends are inside the row's small chart, which a level measures from 0 at its top to 1 at its foot.
        self.assertTrue(0 < levels(pace(top, top))["u"] < levels(pace(bottom, bottom))["u"] < 1)

    def test_the_recent_pace_is_what_was_gained_over_the_recent_days_it_was_gained_in(self):
        # 40 stars in two days and 20 in the one day the loss rule kept are the same pace, at the same level.
        two, one = (
            {"baseline": 5, "recent_stars": 40, "recent_days": 2},
            {"baseline": 5, "recent_stars": 20, "recent_days": 1},
        )
        self.assertEqual(levels(two)["r"], levels(one)["r"])
        self.assertNotEqual(levels(two)["r"], levels({**two, "recent_stars": 400})["r"])

    def test_when_the_loss_rule_kept_one_day_the_usual_pace_runs_thirteen_of_the_fourteen_days(self):
        self.assertAlmostEqual(levels(pace(10, 80, days=1))["e"], 13 / 14, places=3)
        self.assertNotIn("e", levels(pace(10, 80, days=2)))


if __name__ == "__main__":
    unittest.main()
