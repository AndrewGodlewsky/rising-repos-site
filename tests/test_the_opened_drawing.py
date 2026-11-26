"""An opened row's drawing, "Its own pace against what it gained": its shaded gain and the tag that names it (#89).

The shaded gain was a straight wedge from the row's count before the recent days to its count on the board day,
while the line of what it gained ran through each day's count. A row whose two recent days were uneven, as one
that gained 113 stars and then lost 3, had its line rise far above the shading and its shading run under nothing.
So the shading's edge now runs through the same daily points as the line, and back along the dashed line of its
own pace. The tag that names the gain sat beside the board day's point, over the line's last segment, so it now
stands above the line's highest point, where it covers no part of the line.

The drawing is made by the page's script from the board day's `history.json`, so these open a row in the Chrome the
machine already has, through Playwright, as tests/test_opened_row.py does, and hand the page a made-up history for
its first row, so that each holds the very counts its case needs.
"""

import re
import unittest

from helpers import BuildTest

from sitework.layout import chrome, published, served

PHONE, DESKTOP = 390, 1440

HISTORY = "**/history.json"

EVEN = [976 + 2 * day for day in range(12)]
"""Twelve days before the recent days, rising two stars a day, to 998."""

UNEVEN = {
    "stars": [None] * 16 + EVEN + [1000, 1113, 1110],
    "pace": [2, 110, 2],
    "said": ["+106 above its own trend", "At its own pace: +4", "Usual pace, 2 a day", "It gained 110 in 2 days."],
}
"""A row that gained 113 stars on the first recent day and lost 3 on the second, as the idea's farm.js did."""

GAP = {**UNEVEN, "stars": [None] * 16 + EVEN + [1000, None, 1110]}
"""The same row, with no count for the middle of its two recent days."""

STRAIGHT = {**UNEVEN, "stars": None, "month": None}
"""The same row, from a file that gives no daily counts, and so no drawing of its month either."""

PEAK = {
    "stars": [None] * 16 + [1000, 1050, 1100, 1150, 1200, 1180, 1160, 1140, 1120, 1100, 1080, 1060, 1040, 1060, 1090],
    "pace": [3.3, 50, 2],
    "said": ["+43 above its own trend", "At its own pace: +7", "Usual pace, 3.3 a day", "It gained 50 in 2 days."],
}
"""A row whose line rose higher on an earlier day than on either recent day."""

FELL = {
    "stars": [None] * 16 + [400 + 50 * day for day in range(12)] + [1000, 1010, 1020],
    "pace": [50, 20, 2],
    "said": ["−80 below its own trend", "At its own pace: +100", "Usual pace, 50 a day", "It gained 20 in 2 days."],
}
"""A row whose pace fell, so that the dashed line of its own pace ends above every recent count."""

SEEN = """(row) => {
  const figure = row.querySelector("figure.drawing");
  const box = (part) => {
    const edges = part.getBoundingClientRect();
    return { left: edges.left, right: edges.right, top: edges.top, bottom: edges.bottom };
  };
  const path = (name) => figure.querySelector("path." + name).getAttribute("d");
  return {
    above: path("above"),
    gained: path("gained"),
    own: path("own"),
    plot: box(figure.querySelector("svg")),
    figure: box(figure),
    got: box(figure.querySelector(".tag.got")),
    tags: [box(figure.querySelector(".tag.own")), box(figure.querySelector(".tag.usual"))],
    caption: box(figure.querySelector("figcaption")),
  };
}"""
"""Run on a board's row once its drawing is drawn: the paths of the shaded gain, the gained line, and the dashed line
of its own pace, and where the plot, the figure, the tag of the gain, the other two tags, and the caption are."""

NUMBER = re.compile(r"[MLVHZ]|-?\d+(?:\.\d+)?(?:e-?\d+)?")

CLOSE = 1e-6
"""Two points of the drawing's 100 by 100 box that are this near are one point."""

STROKE = 1.25
"""Half the width the gained line is drawn at, in pixels: a box this near the line's middle touches it."""


def runs(d: str) -> list[list[tuple[float, float]]]:
    """The points of a path, as a list of runs, a new one at each move: a closed run ends at its first point again."""
    tokens, found, point = NUMBER.findall(d), [], None
    at = 0
    while at < len(tokens):
        command = tokens[at]
        if command == "Z":
            found[-1].append(found[-1][0])
            at += 1
            continue
        if command == "V":
            point = (point[0], float(tokens[at + 1]))
            at += 2
        elif command == "H":
            point = (float(tokens[at + 1]), point[1])
            at += 2
        else:
            point = (float(tokens[at + 1]), float(tokens[at + 2]))
            at += 3
        if command == "M":
            found.append([])
        found[-1].append(point)
    return found


def same(first: tuple[float, float], second: tuple[float, float]) -> bool:
    return abs(first[0] - second[0]) < CLOSE and abs(first[1] - second[1]) < CLOSE


def touches(box: dict, plot: dict, start: tuple[float, float], end: tuple[float, float]) -> bool:
    """Whether a segment of the plot's box, from `start` to `end` in its hundredths, crosses `box`, a box on the
    screen, widened by half the line's stroke: by clipping the segment to the box (Liang and Barsky)."""
    across, down = (plot["right"] - plot["left"]) / 100, (plot["bottom"] - plot["top"]) / 100
    x0, y0 = plot["left"] + start[0] * across, plot["top"] + start[1] * down
    x1, y1 = plot["left"] + end[0] * across, plot["top"] + end[1] * down
    low, high = 0.0, 1.0
    for p, q in (
        (x0 - x1, x0 - (box["left"] - STROKE)),
        (x1 - x0, (box["right"] + STROKE) - x0),
        (y0 - y1, y0 - (box["top"] - STROKE)),
        (y1 - y0, (box["bottom"] + STROKE) - y0),
    ):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            low = max(low, t)
        else:
            high = min(high, t)
    return low <= high


def overlap(first: dict, second: dict) -> bool:
    return (
        first["left"] < second["right"]
        and second["left"] < first["right"]
        and first["top"] < second["bottom"]
        and second["top"] < first["bottom"]
    )


class OpenedDrawing(BuildTest):
    def setUp(self):
        super().setUp()
        self.build_pages()

    def seen(self, case: dict, *widths: int) -> dict[int, dict]:
        """The newest board's first row, given `case` as its pace, its labels, and its daily counts, opened on a
        screen of each of `widths`, and what its drawing shows there."""

        def hand_over(route) -> None:
            response = route.fetch()
            history = response.json()
            history["rows"][0] = {**history["rows"][0], **case}
            route.fulfill(response=response, json=history)

        found = {}
        with served(self.out) as site, chrome() as browser:
            for width in widths:
                page = browser.new_page(viewport={"width": width, "height": 900})
                page.clock.set_fixed_time(published(self.out))
                page.route(HISTORY, hand_over)
                page.goto(site, wait_until="load")
                page.evaluate("document.fonts.ready.then(() => true)")
                row = page.locator("table.chart > tbody > tr").first
                row.locator("summary").first.click()
                row.locator("figure.drawing").wait_for()
                found[width] = row.evaluate(SEEN)
                page.close()
        return found

    def assert_closed_along_the_dashed_line(self, shaded: list, own: list) -> None:
        """The shaded run ends by going straight down or up to the dashed line's end on the board day, and closes
        back to its first point, which lies on the dashed line: so its other edge runs along that line."""
        self.assertTrue(same(shaded[-2], own[-1]), (shaded, own))
        self.assertTrue(same(shaded[-1], shaded[0]), shaded)
        (x0, y0), (x1, y1), (x, y) = own[0], own[-1], shaded[0]
        self.assertAlmostEqual((x1 - x0) * (y - y0) - (y1 - y0) * (x - x0), 0, places=4)


class TheShadedGain(OpenedDrawing):
    def test_the_shaded_gain_runs_through_each_daily_point_of_the_gained_line_and_back_along_the_dashed_line(self):
        seen = self.seen(UNEVEN, DESKTOP)[DESKTOP]
        (gained,), (shaded,), (own,) = runs(seen["gained"]), runs(seen["above"]), runs(seen["own"])
        recent = gained[-3:]
        self.assertEqual(len(shaded), len(recent) + 2, seen["above"])
        for edge, point in zip(shaded, recent, strict=False):
            self.assertTrue(same(edge, point), (seen["above"], seen["gained"]))
        self.assert_closed_along_the_dashed_line(shaded, own)

    def test_a_recent_day_with_no_count_is_crossed_by_a_straight_edge_of_the_shading_and_the_line_keeps_its_gap(self):
        seen = self.seen(GAP, DESKTOP)[DESKTOP]
        gained, (shaded,), (own,) = runs(seen["gained"]), runs(seen["above"]), runs(seen["own"])
        self.assertEqual(len(gained), 2, seen["gained"])
        before, board_day = gained[0][-1], gained[1]
        self.assertEqual(len(board_day), 1, seen["gained"])
        self.assertEqual(len(shaded), 4, seen["above"])
        self.assertTrue(same(shaded[0], before), (seen["above"], seen["gained"]))
        self.assertTrue(same(shaded[1], board_day[0]), (seen["above"], seen["gained"]))
        self.assert_closed_along_the_dashed_line(shaded, own)

    def test_a_row_without_daily_counts_keeps_one_straight_line_and_the_straight_wedge_under_it(self):
        none_on_the_day_before = [*UNEVEN["stars"][:28], None, *UNEVEN["stars"][29:]]
        none_on_the_board_day = [*UNEVEN["stars"][:30], None]
        for case in (STRAIGHT, {**UNEVEN, "stars": none_on_the_day_before}, {**UNEVEN, "stars": none_on_the_board_day}):
            with self.subTest(stars=case["stars"]):
                seen = self.seen(case, DESKTOP)[DESKTOP]
                (gained,), (shaded,) = runs(seen["gained"]), runs(seen["above"])
                *_, own = runs(seen["own"])
                self.assertEqual(len(gained), 2, seen["gained"])
                self.assertEqual(len(shaded), 4, seen["above"])
                self.assertTrue(same(shaded[0], gained[0]) and same(shaded[1], gained[1]), seen)
                self.assert_closed_along_the_dashed_line(shaded, own)


class TheGainsTag(OpenedDrawing):
    CASES = {"uneven": UNEVEN, "higher before": PEAK, "fell": FELL, "straight": STRAIGHT}

    def test_the_tag_of_what_it_gained_touches_no_segment_of_the_gained_line_on_a_phone_or_a_desktop(self):
        for name, case in self.CASES.items():
            for width, seen in self.seen(case, PHONE, DESKTOP).items():
                with self.subTest(name, width=width):
                    for run in runs(seen["gained"]):
                        for start, end in zip(run, run[1:], strict=False):
                            self.assertFalse(touches(seen["got"], seen["plot"], start, end), (seen, start, end))

    def test_the_tag_of_what_it_gained_overlaps_no_other_tag_nor_the_caption_and_stays_inside_the_figure(self):
        for name, case in self.CASES.items():
            for width, seen in self.seen(case, PHONE, DESKTOP).items():
                with self.subTest(name, width=width):
                    for other in [*seen["tags"], seen["caption"]]:
                        self.assertFalse(overlap(seen["got"], other), (seen["got"], other))
                    self.assertGreaterEqual(seen["got"]["left"], seen["figure"]["left"] - 0.5)
                    self.assertLessEqual(seen["got"]["right"], seen["figure"]["right"] + 0.5)


if __name__ == "__main__":
    unittest.main()
