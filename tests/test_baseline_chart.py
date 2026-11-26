"""Baseline's chart on a phone, from the keyboard, and by name (#29).

The chart named the repository nearest a mouse's pointer, and a click went to its line in the table. On a phone a
tap showed nothing: a finger fires no hover, and once it lifts the browser says the pointer has left. So a reader
on a phone saw a cloud of unnamed dots, with the first ranks' marks crowded together. Now a tap chooses a dot: the
readout names it, with its rank, its baseline, its recent pace, and its growth, as the table writes them, and stays
until the next tap or a dismissal, and while a dot is chosen the ranks' marks are not drawn. The keyboard and a
"Find a repository" field choose a dot too.

What a tap, a key, or the field does is something only a browser can show, so these open the pages in the Chrome
the machine already has, through Playwright, as `tests/test_day_bar.py` does, and fail without it. They set the
browser's clock to the newest board's publish time, so that no page hides its board behind the notice of an old
one. A tap is a touch screen's, in a context that has one.
"""

import contextlib
import math
import unittest

from helpers import BuildTest, read_json

from sitebuild import BASELINE
from sitework.layout import chrome, published, served

PHONE, DESKTOP = 390, 1440
"""A phone's width and a desktop's."""

DOTS = """() => {
  const svg = document.querySelector('.plot svg');
  const box = svg.getBoundingClientRect();
  const drawn = [...svg.querySelectorAll('path.dot.lead'), ...svg.querySelectorAll('path.dot:not(.lead):not(.here)')];
  const d = drawn.map(path => path.getAttribute('d')).join('');
  return [...d.matchAll(/M([\\d.]+) ([\\d.]+)h0/g)].map(m => ({
    x: box.left + m[1] / 100 * box.width, y: box.top + m[2] / 100 * box.height, at: `M${m[1]} ${m[2]}h0`,
  }));
}"""
"""Where each dot is drawn on the screen, in the table's order, and the stroke that draws it alone. The build writes
the top ten in the accent's path and the rest in the other, each in the board's order."""

CELLS = """() => [...document.querySelectorAll('.numbers tbody tr')].map(row => [...row.children].map(cell =>
  cell.textContent.trim()))"""
"""The words of each of the table's lines, cell by cell: rank, name, baseline, recent pace, growth."""


class ChartTest(BuildTest):
    def baseline(self, browser, width: int, touch: bool, scripts: bool = True):
        """Baseline, on a screen `width` pixels wide, with or without a touch screen, once its type is in, and the
        chart in view."""
        context = browser.new_context(
            viewport={"width": width, "height": 900}, has_touch=touch, is_mobile=touch, java_script_enabled=scripts
        )
        page = context.new_page()
        page.clock.set_fixed_time(published(self.out))
        page.goto(f"{self.site}/{BASELINE.removesuffix('index.html')}", wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        page.locator(".plot").scroll_into_view_if_needed()
        return page

    def dots(self, page) -> list[dict]:
        return page.evaluate(DOTS)

    def readout(self, page) -> str | None:
        """The readout's words when it is drawn, or None."""
        readout = page.locator(".plot .readout")
        return readout.text_content() if readout.is_visible() else None

    def marked(self, page) -> str:
        """The stroke that marks the chosen dot, or "" when none is."""
        return page.locator(".plot path.dot.here").get_attribute("d")

    def assert_names(self, page, line: list[str]) -> None:
        """The readout is drawn and gives each of the line's cells as the table writes it."""
        said = self.readout(page)
        self.assertIsNotNone(said, "no readout is drawn")
        for cell in line:
            self.assertIn(cell, said)

    def empty_spot(self, page) -> tuple[float, float]:
        """A point inside the chart that is far from every dot."""
        box = page.locator(".plot svg").bounding_box()
        dots = self.dots(page)
        spots = [
            (box["x"] + box["width"] * i / 10, box["y"] + box["height"] * j / 10)
            for i in range(1, 10)
            for j in range(1, 10)
        ]
        return max(spots, key=lambda spot: min(math.dist(spot, (dot["x"], dot["y"])) for dot in dots))

    @contextlib.contextmanager
    def run_chart(self):
        """Build the pages, serve them from this machine, and open Chrome, for the length of a `with`."""
        self.build_pages()
        with served(self.out) as site, chrome() as browser:
            self.site = site
            yield browser


class OnAPhone(ChartTest):
    def test_a_tap_on_a_dot_names_it_as_the_table_does_and_the_readout_stays(self):
        with self.run_chart() as browser:
            page = self.baseline(browser, PHONE, touch=True)
            dots, lines = self.dots(page), page.evaluate(CELLS)
            for i in (1, 4):
                with self.subTest(rank=lines[i][0]):
                    page.touchscreen.tap(dots[i]["x"], dots[i]["y"])
                    page.wait_for_timeout(400)
                    self.assert_names(page, lines[i])
                    self.assertEqual(self.marked(page), dots[i]["at"])

    def test_a_tap_on_another_dot_names_that_one_and_a_tap_away_from_every_dot_dismisses(self):
        with self.run_chart() as browser:
            page = self.baseline(browser, PHONE, touch=True)
            dots, lines = self.dots(page), page.evaluate(CELLS)
            page.touchscreen.tap(dots[1]["x"], dots[1]["y"])
            page.touchscreen.tap(dots[2]["x"], dots[2]["y"])
            self.assert_names(page, lines[2])
            self.assertNotIn(lines[1][1], self.readout(page))
            self.assertEqual(self.marked(page), dots[2]["at"])
            page.touchscreen.tap(*self.empty_spot(page))
            self.assertIsNone(self.readout(page))
            self.assertEqual(self.marked(page), "")

    def test_a_second_tap_on_the_chosen_dot_goes_to_its_line_in_the_table(self):
        with self.run_chart() as browser:
            page = self.baseline(browser, PHONE, touch=True)
            dots, lines = self.dots(page), page.evaluate(CELLS)
            page.touchscreen.tap(dots[2]["x"], dots[2]["y"])
            self.assertNotEqual(page.evaluate("document.activeElement.textContent"), lines[2][1])
            page.touchscreen.tap(dots[2]["x"], dots[2]["y"])
            self.assertEqual(page.evaluate("document.activeElement.textContent"), lines[2][1])
            line = page.locator(".numbers tbody tr").nth(2).bounding_box()
            self.assertGreaterEqual(line["y"], 0)
            self.assertLessEqual(line["y"] + line["height"], 900)

    def test_while_a_dot_is_chosen_no_ranks_mark_is_drawn(self):
        with self.run_chart() as browser:
            page = self.baseline(browser, PHONE, touch=True)
            marks = page.locator(".plot .rk")
            self.assertGreater(marks.count(), 0)
            drawn = "marks => marks.filter(mark => mark.checkVisibility({visibilityProperty: true})).length"
            self.assertEqual(marks.evaluate_all(drawn), marks.count())
            dot = self.dots(page)[0]
            page.touchscreen.tap(dot["x"], dot["y"])
            self.assertEqual(marks.evaluate_all(drawn), 0)
            page.touchscreen.tap(*self.empty_spot(page))
            self.assertEqual(marks.evaluate_all(drawn), marks.count())

    def test_the_readout_of_the_longest_name_stays_in_the_card_at_either_edge_and_the_middle(self):
        """106 characters is the longest name in `site-data/`. Three rows carry such names, one at the floor of the
        baseline, on the chart's left edge, one in the middle, and one with the largest baseline, on its right."""
        board = read_json(self.board_file())
        model = board["rows"][1]
        rows = []
        for rank, baseline in enumerate((0.5, 30.0, 900.0), start=1):
            name = f"o{rank}/" + "a" * 103
            pace = baseline * 3 if baseline >= 1 else 3.0
            rows.append(
                {
                    **model,
                    "rank": rank,
                    "github_id": model["github_id"] + rank,
                    "full_name": name,
                    "baseline": baseline,
                    "divided_by": max(baseline, 1.0),
                    "recent_stars": round(pace * 2),
                    "recent_days": 2,
                    "score": round(pace * 2) / 2 / max(baseline, 1.0),
                }
            )
        rows.sort(key=lambda row: -row["score"])
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank
        self.write_board({**board, "rows": rows})
        with self.run_chart() as browser:
            page = self.baseline(browser, PHONE, touch=True)
            card = page.locator(".pace").bounding_box()
            for i, dot in enumerate(self.dots(page)):
                with self.subTest(dot=i):
                    page.touchscreen.tap(dot["x"], dot["y"])
                    self.assertIsNotNone(self.readout(page))
                    box = page.locator(".plot .readout").bounding_box()
                    self.assertGreaterEqual(box["x"], card["x"])
                    self.assertLessEqual(box["x"] + box["width"], card["x"] + card["width"])
                    self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth - innerWidth"), 0)


class OnADesktop(ChartTest):
    def test_a_click_on_a_dot_goes_to_its_line_in_the_table_and_the_dot_stays_chosen(self):
        with self.run_chart() as browser:
            page = self.baseline(browser, DESKTOP, touch=False)
            dots, lines = self.dots(page), page.evaluate(CELLS)
            page.mouse.move(dots[2]["x"], dots[2]["y"])
            page.mouse.down()
            page.mouse.up()
            self.assertEqual(page.evaluate("document.activeElement.textContent"), lines[2][1])
            page.locator(".plot").scroll_into_view_if_needed()
            page.mouse.move(1, 1)
            self.assert_names(page, lines[2])
            self.assertEqual(self.marked(page), dots[2]["at"])


class FromTheKeyboard(ChartTest):
    def test_focus_names_the_first_and_the_keys_step_open_and_dismiss(self):
        with self.run_chart() as browser:
            page = self.baseline(browser, DESKTOP, touch=False)
            dots, lines = self.dots(page), page.evaluate(CELLS)
            page.get_by_label("Find a repository").focus()
            page.keyboard.press("Shift+Tab")
            self.assertEqual(page.evaluate("document.activeElement.tagName.toLowerCase()"), "svg")
            self.assert_names(page, lines[0])
            self.assertEqual(self.marked(page), dots[0]["at"])
            for key, i in (("ArrowRight", 1), ("ArrowDown", 2), ("ArrowLeft", 1), ("ArrowUp", 0), ("End", 4)):
                with self.subTest(key):
                    page.keyboard.press(key)
                    self.assert_names(page, lines[i])
                    self.assertEqual(self.marked(page), dots[i]["at"])
            page.keyboard.press("Escape")
            self.assertIsNone(self.readout(page))
            self.assertEqual(self.marked(page), "")
            page.keyboard.press("Home")
            page.keyboard.press("ArrowRight")
            page.keyboard.press("Enter")
            self.assertEqual(page.evaluate("document.activeElement.textContent"), lines[1][1])


class TheFindField(ChartTest):
    def test_typing_part_of_a_name_marks_and_names_the_first_that_holds_it_and_enter_the_next(self):
        """The example board lists two repositories of octocat's, its second and its fourth."""
        with self.run_chart() as browser:
            page = self.baseline(browser, PHONE, touch=True)
            dots, lines = self.dots(page), page.evaluate(CELLS)
            held = [i for i, line in enumerate(lines) if "octocat" in line[1].lower()]
            self.assertEqual(len(held), 2)
            field = page.get_by_label("Find a repository")
            field.fill("OCTOCAT")
            self.assert_names(page, lines[held[0]])
            self.assertEqual(self.marked(page), dots[held[0]]["at"])
            count = page.locator(".find").inner_text()
            self.assertIn("2", count)
            field.press("Enter")
            self.assert_names(page, lines[held[1]])
            self.assertEqual(self.marked(page), dots[held[1]]["at"])
            field.press("Enter")
            self.assert_names(page, lines[held[0]])

    def test_text_no_name_holds_is_said_to_match_none_and_marks_no_dot(self):
        with self.run_chart() as browser:
            page = self.baseline(browser, PHONE, touch=True)
            field = page.get_by_label("Find a repository")
            field.fill("octocat")
            field.fill("no-name-holds-this")
            self.assertIsNone(self.readout(page))
            self.assertEqual(self.marked(page), "")
            self.assertRegex(page.locator(".find").inner_text(), r"(?i)\bnone\b")


WORDS = """() => {
  const plot = document.querySelector('.plot').getBoundingClientRect();
  const labels = document.querySelectorAll('.plot span.glabel, .plot span.tick, .plot span.axis, .plot span.rk');
  return [...labels].map(el => {
    const range = document.createRange();
    range.selectNodeContents(el);
    const box = range.getBoundingClientRect();
    return {text: el.textContent, own: el.classList.contains('own'),
      x0: box.left - plot.left, x1: box.right - plot.left, y0: box.top - plot.top, y1: box.bottom - plot.top};
  });
}"""
"""Each of the chart's labels by the box of its words, in pixels from the plot's top left corner: the guide labels,
the ticks, the two axis titles, and the ranks' marks. The box of the words, and not of the element, since a label's
element is padded."""

PLOT = """() => { const box = document.querySelector('.plot').getBoundingClientRect();
  return {width: box.width, height: box.height}; }"""

ELEMENTS = """() => {
  const plot = document.querySelector('.plot').getBoundingClientRect();
  return [...document.querySelectorAll('.plot span.glabel')].map(el => {
    const box = el.getBoundingClientRect();
    return {text: el.textContent, x0: box.left - plot.left, x1: box.right - plot.left, y1: box.bottom - plot.top};
  });
}"""
"""Each guide label's own box, padding and all, in pixels from the plot's top left corner."""


class TheGuideLabels(ChartTest):
    """The guide labels on a phone (#34). Both the dashed line of a board's own pace and the 3× line left the chart
    at its top right corner, and both labels were set at the line's end, on the plot's top edge, so on a phone
    "own pace" printed on top of "3×"."""

    def corner_board(self) -> None:
        """The example board with one row more, at 300 stars a day and a score of 3, which gives the guides of the
        newest board in `site-data/`: the dashed line leaves the chart at its top right corner, and the 3× line
        just left of it."""
        board = read_json(self.board_file())
        rows = board["rows"]
        rows.append(
            {
                **rows[-1],
                "rank": len(rows) + 1,
                "github_id": rows[-1]["github_id"] + 1000,
                "full_name": "o/corner",
                "baseline": 300.0,
                "divided_by": 300.0,
                "recent_stars": 1800,
                "recent_days": 2,
                "score": 3.0,
            }
        )
        self.write_board({**board, "rows": rows})

    def dashed_line(self, page) -> tuple[tuple[float, float], tuple[float, float]]:
        """The ends of the dashed line of the board's own pace, in pixels from the plot's top left corner."""
        line = page.locator(".plot line.guide.own")
        plot = page.evaluate(PLOT)
        x1, y1, x2, y2 = (float(line.get_attribute(name)) for name in ("x1", "y1", "x2", "y2"))
        return (
            (x1 / 100 * plot["width"], y1 / 100 * plot["height"]),
            (x2 / 100 * plot["width"], y2 / 100 * plot["height"]),
        )

    def test_on_a_phone_no_two_of_the_charts_labels_overlap_with_the_script_or_without(self):
        self.corner_board()
        with self.run_chart() as browser:
            for width in (360, 375, 390, 412, 430):
                for scripts in (True, False):
                    page = self.baseline(browser, width, touch=True, scripts=scripts)
                    labels = page.evaluate(WORDS)
                    for i, a in enumerate(labels):
                        for b in labels[i + 1 :]:
                            with self.subTest(width=width, scripts=scripts, a=a["text"], b=b["text"]):
                                apart = (
                                    a["x1"] <= b["x0"] or b["x1"] <= a["x0"] or a["y1"] <= b["y0"] or b["y1"] <= a["y0"]
                                )
                                self.assertTrue(apart, f"{a} overlaps {b}")
                    page.context.close()

    def test_on_a_phone_own_pace_sits_beside_its_dashed_line_below_and_to_the_right_of_it(self):
        """Tried on the board whose dashed line leaves by the top right corner, and on the example as it is, whose
        dashed line leaves by the right edge."""
        for corner in (True, False):
            with self.subTest(corner=corner):
                # A fresh copy of the example, and a fresh folder to build into, for each board.
                self.setUp()
                if corner:
                    self.corner_board()
                with self.run_chart() as browser:
                    for width in (360, 390, 430):
                        for scripts in (True, False):
                            with self.subTest(corner=corner, width=width, scripts=scripts):
                                page = self.baseline(browser, width, touch=True, scripts=scripts)
                                plot = page.evaluate(PLOT)
                                (ax, ay), (bx, by) = self.dashed_line(page)
                                own = next(label for label in page.evaluate(WORDS) if label["own"])
                                page.context.close()
                                corners = [(x, y) for x in (own["x0"], own["x1"]) for y in (own["y0"], own["y1"])]
                                # Inside the plot.
                                self.assertGreaterEqual(own["x0"], 0)
                                self.assertGreaterEqual(own["y0"], 0)
                                self.assertLessEqual(own["x1"], plot["width"])
                                self.assertLessEqual(own["y1"], plot["height"])
                                # Below and to the right of the line: on a screen, whose y runs down, a point is
                                # below a line that rises to the right when the cross product of the line's
                                # direction and the point is positive.
                                for x, y in corners:
                                    self.assertGreater((bx - ax) * (y - ay) - (by - ay) * (x - ax), 0, (x, y))
                                # Within 6 px of it: the corner nearest a line that rises to the right is the top
                                # left one.
                                length = math.dist((ax, ay), (bx, by))
                                gap = ((bx - ax) * (own["y0"] - ay) - (by - ay) * (own["x0"] - ax)) / length
                                self.assertLessEqual(gap, 6)

    def test_on_a_desktop_each_guide_label_sits_at_the_end_of_its_line_as_before(self):
        self.corner_board()
        with self.run_chart() as browser:
            page = self.baseline(browser, DESKTOP, touch=False)
            plot = page.evaluate(PLOT)
            guides = page.locator(".plot line.guide")
            ends = [
                tuple(float(guides.nth(i).get_attribute(name)) for name in ("x2", "y2")) for i in range(guides.count())
            ]
            labels = page.evaluate(ELEMENTS)
            self.assertEqual(len(labels), len(ends))
            self.assertIn("own pace", [label["text"] for label in labels])
            for label, (x2, y2) in zip(labels, ends, strict=True):
                with self.subTest(label=label["text"]):
                    x, y = x2 / 100 * plot["width"], y2 / 100 * plot["height"]
                    self.assertAlmostEqual(label["y1"], y, delta=0.5)
                    if x2 > 80:
                        self.assertAlmostEqual(label["x1"], x, delta=0.5)
                    else:
                        self.assertAlmostEqual(label["x0"], x + 4, delta=0.5)


class WithoutTheScript(ChartTest):
    def test_with_scripts_off_the_find_field_is_not_shown_and_the_chart_is_as_built(self):
        with self.run_chart() as browser:
            on = self.baseline(browser, PHONE, touch=False)
            self.assertTrue(on.get_by_label("Find a repository").is_visible())
            off = self.baseline(browser, PHONE, touch=False, scripts=False)
            self.assertEqual(off.locator("#find").count(), 1)
            self.assertFalse(off.get_by_label("Find a repository").is_visible())
            self.assertEqual(off.locator(".plot svg").get_attribute("tabindex"), None)
            self.assertEqual(self.marked(off), "")
            self.assertIsNone(self.readout(off))
            self.assertEqual(sum(dot["at"].count("M") for dot in self.dots(off)), len(off.evaluate(CELLS)))


if __name__ == "__main__":
    unittest.main()
