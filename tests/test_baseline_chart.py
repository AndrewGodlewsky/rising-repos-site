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

from helpers import ROOT, BuildTest, read_json

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
    def baseline(self, browser, width: int, touch: bool, scripts: bool = True, height: int = 900, init: str = ""):
        """Baseline, on a screen `width` pixels wide, with or without a touch screen, once its type is in, and the
        chart in view. `init` is a script to run in the page before its own."""
        context = browser.new_context(
            viewport={"width": width, "height": height}, has_touch=touch, is_mobile=touch, java_script_enabled=scripts
        )
        page = context.new_page()
        if init:
            page.add_init_script(init)
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


NEWEST = ("2026-11-25", "2026-11-26")
"""The two board days on which a rank's mark covered dots it does not name (#187): on 25 November "2, 4, 5" sat
beside dot 2 and ran across dots 4 and 5, 40 px to its right, and on 26 November "3, 5" covered dots 8 and 9. Board
days keep their files, so these stay in `site-data/`."""

SIZES = ((1440, 900, False), (768, 900, False), (390, 844, True), (360, 800, True))
"""The idea's desktop and phone, with the narrowest desktop layout and the narrowest phone that #34's tests use."""

APART = 12
"""Dots nearer each other than this, in pixels at the chart's drawn size, share one mark (#187)."""

MARKS = """() => {
  const plot = document.querySelector('.plot'), at = plot.getBoundingClientRect();
  const svg = plot.querySelector('svg').getBoundingClientRect();
  const lead = plot.querySelector('path.dot.lead');
  const box = el => { const b = el.getBoundingClientRect();
    return [b.left - at.left, b.top - at.top, b.right - at.left, b.bottom - at.top]; };
  return {
    dots: [...lead.getAttribute('d').matchAll(/M([\\d.]+) ([\\d.]+)h0/g)].map(m => ({
      x: svg.left - at.left + m[1] / 100 * svg.width, y: svg.top - at.top + m[2] / 100 * svg.height})),
    radius: parseFloat(getComputedStyle(lead).strokeWidth) / 2,
    marks: [...plot.querySelectorAll('span.rk')].filter(el => el.checkVisibility({visibilityProperty: true}))
      .map(el => ({text: el.textContent, ranks: el.textContent.split(', ').map(Number), box: box(el)})),
    others: [...plot.querySelectorAll('span.tick, span.glabel, span.axis')].map(el => ({text: el.textContent,
      box: box(el)})),
    card: box(plot.closest('.pace')),
  };
}"""
"""The chart as drawn, in pixels from the plot's top left corner: each top dot's centre, in rank order, and the
radius it is drawn at; each rank's mark that is drawn, by its words, its ranks, and its box; each other label of the
chart by its box; and the chart's card."""

FRAMES = """(() => {
  window.drawn = [];
  const ids = new Map();
  let frames = 0;
  const look = () => {
    const plot = document.querySelector('.plot');
    if (plot) {
      const at = plot.getBoundingClientRect();
      plot.querySelectorAll('span.rk').forEach(el => {
        if (!ids.has(el)) ids.set(el, ids.size);
        if (!el.checkVisibility({visibilityProperty: true})) return;
        const b = el.getBoundingClientRect();
        window.drawn.push([ids.get(el), el.textContent, b.left - at.left, b.top - at.top]);
      });
    }
  };
  const frame = () => {
    look();
    if (++frames < 180) requestAnimationFrame(frame);
    else window.looked = true;
  };
  document.addEventListener('DOMContentLoaded', look);
  requestAnimationFrame(frame);
})();"""
"""Each rank's mark as it would be drawn once the page is parsed, before its own script has run, and as it is drawn
in each of the page's first 180 frames, about three seconds: the mark, its words, and its place, in pixels from the
plot's top left corner. It counts frames, since the page's clock is held still."""


def meet(a: list[float], b: list[float]) -> bool:
    """Whether two boxes, [left, top, right, bottom], overlap."""
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def gap(box: list[float], dot: dict) -> float:
    """How far a dot's centre is from a box, 0 inside it."""
    return math.dist((dot["x"], dot["y"]), (min(max(dot["x"], box[0]), box[2]), min(max(dot["y"], box[1]), box[3])))


def covered(chart: dict) -> list[str]:
    """Each top dot a rank's mark covers, taking the dot as the circle it is drawn as."""
    return [
        f'"{mark["text"]}" covers dot {rank}'
        for mark in chart["marks"]
        for rank, dot in enumerate(chart["dots"], start=1)
        if gap(mark["box"], dot) < chart["radius"]
    ]


def astray(chart: dict, nearest: bool) -> list[str]:
    """Each mark that sits beside no dot it names: level with it, within 1 px, and with its nearer side within 12 px
    of its centre, to its left or its right. With `nearest`, also each mark that a top dot it does not name is
    nearer than every dot it names."""
    faults = []
    for mark in chart["marks"]:
        box, named = mark["box"], [chart["dots"][rank - 1] for rank in mark["ranks"]]
        beside = [
            dot
            for dot in named
            if abs((box[1] + box[3]) / 2 - dot["y"]) <= 1
            and (0 <= box[0] - dot["x"] <= APART or 0 <= dot["x"] - box[2] <= APART)
        ]
        if not beside:
            faults.append(f'"{mark["text"]}" sits beside no dot it names')
        others = [dot for rank, dot in enumerate(chart["dots"], start=1) if rank not in mark["ranks"]]
        if nearest and min(gap(box, dot) for dot in others) < min(gap(box, dot) for dot in named):
            faults.append(f'"{mark["text"]}" is nearer a dot it does not name than one it names')
    return faults


def misnamed(chart: dict) -> list[str]:
    """Each fault in which ranks the marks name: each of the first five ranks named by exactly one mark, and ranks
    that share a mark only when each of their dots is less than 12 px from another of them."""
    ranks = sorted(rank for mark in chart["marks"] for rank in mark["ranks"])
    faults = [] if ranks == [1, 2, 3, 4, 5] else [f"the marks name the ranks {ranks}"]
    for mark in chart["marks"]:
        named = [chart["dots"][rank - 1] for rank in mark["ranks"]]
        for rank, dot in zip(mark["ranks"], named, strict=True):
            if len(named) > 1 and not any(0 < math.dist((dot["x"], dot["y"]), (o["x"], o["y"])) < APART for o in named):
                faults.append(f'"{mark["text"]}": dot {rank} is {APART} px or more from the others it names')
    return faults


def crowded(chart: dict) -> list[str]:
    """Each mark that meets another mark or another of the chart's labels, or leaves the chart's card."""
    marks, card = chart["marks"], chart["card"]
    faults = [
        f'"{a["text"]}" meets "{b["text"]}"'
        for i, a in enumerate(marks)
        for b in marks[i + 1 :] + chart["others"]
        if meet(a["box"], b["box"])
    ]
    return faults + [
        f'"{mark["text"]}" leaves the card'
        for mark in marks
        if not (card[0] <= mark["box"][0] and card[1] <= mark["box"][1])
        or not (mark["box"][2] <= card[2] and mark["box"][3] <= card[3])
    ]


GUIDE = "the board whose first dot is just left of the 10× label"
"""A made-up board whose first dot sits on the plot's top edge just left of where the 10× line leaves it, so that a
mark to the right of that dot would meet the "10×" label."""


class TheRanksMarks(ChartTest):
    """The ranks' marks at the size the chart is drawn (#187). The build groups the first five dots by 6 % of the plot
    across and up, which on a desktop's 1,030 px chart is 60 px, and sets a group's mark beside its first dot: so the
    mark ran across the other dots it named. The script now groups them at the drawn size, and sets each mark where
    it covers no top dot."""

    def charts(self, boards=NEWEST, sizes=SIZES, init: str = ""):
        """For each board of `boards` as the newest, and each size of `sizes`, where it is tried, its page, and its
        chart as drawn."""
        for day in boards:
            # A fresh copy of the example, and a fresh folder to build into, for each board.
            self.setUp()
            rows = (
                self.guide_rows()
                if day == GUIDE
                else read_json(ROOT / "site-data" / "boards" / "days" / day / "daily.json")["rows"]
            )
            self.write_board({**read_json(self.board_file()), "rows": rows})
            with self.run_chart() as browser:
                for width, height, touch in sizes:
                    page = self.baseline(browser, width, touch, height=height, init=init)
                    yield f"{day} at {width}", page, page.evaluate(MARKS)
                    page.context.close()

    def guide_rows(self) -> list[dict]:
        """The rows of `GUIDE`. The first gains 1,000 stars a day on a baseline of 95, a score of 10.5: 1,000 is the top
        of the plot, and the 10× line leaves it at a baseline of 100, about 8 px to the right on a desktop, with its
        label to the right of that, since a line that leaves left of 80 % of the plot is labelled there. The others
        score less and keep away from it, and the last, at a baseline of 500, takes the axis to 1,000."""
        model = read_json(self.board_file())["rows"][1]
        rows = []
        for rank, (baseline, stars, days) in enumerate(
            ((95.0, 2000, 2), (30.0, 600, 2), (10.0, 190, 2), (0.5, 18, 2), (3.0, 51, 2), (500.0, 1200, 2)), start=1
        ):
            divided_by = max(baseline, 1.0)
            rows.append(
                {
                    **model,
                    "rank": rank,
                    "github_id": model["github_id"] + rank,
                    "full_name": f"o/guide-{rank}",
                    "baseline": baseline,
                    "divided_by": divided_by,
                    "recent_stars": stars,
                    "recent_days": days,
                    "score": stars / days / divided_by,
                }
            )
        return rows

    def test_on_the_25_november_board_on_a_desktop_the_marks_read_1_2_3_and_4_5(self):
        for _, _, chart in self.charts(boards=NEWEST[:1], sizes=SIZES[:1]):
            self.assertEqual(sorted(mark["text"] for mark in chart["marks"]), ["1", "2", "3", "4, 5"])

    def test_no_ranks_mark_covers_a_top_ten_dot_at_a_phones_or_a_desktops_width(self):
        for tried, _, chart in self.charts():
            with self.subTest(tried):
                self.assertEqual(len(chart["dots"]), 10)
                self.assertEqual(covered(chart), [])

    def test_every_mark_sits_beside_a_dot_it_names_and_no_dot_it_does_not_name_is_nearer(self):
        """The second half is held at the idea's two sizes alone: at 768 px, on 25 November, "3" has no place beside
        its dot that is clear of every other dot and label and nearer its own than any other."""
        for tried, _, chart in self.charts():
            with self.subTest(tried):
                self.assertEqual(astray(chart, nearest=tried.endswith(("1440", "390"))), [])

    def test_each_of_the_first_five_ranks_is_named_once_and_ranks_share_a_mark_only_when_their_dots_touch(self):
        for tried, _, chart in self.charts():
            with self.subTest(tried):
                self.assertEqual(misnamed(chart), [])

    def test_no_mark_meets_another_mark_or_another_of_the_charts_labels_and_each_stays_in_the_card(self):
        """Tried on `GUIDE` too, where the place a mark takes first, to the right of its dot, meets the "10×" label."""
        for tried, _, chart in self.charts(boards=(*NEWEST, GUIDE)):
            with self.subTest(tried):
                self.assertGreater(len(chart["marks"]), 0)
                self.assertEqual(crowded(chart), [])

    def test_no_ranks_mark_is_drawn_in_one_place_and_then_another_as_the_page_loads(self):
        sizes = (SIZES[0], SIZES[2])
        for tried, page, _ in self.charts(sizes=sizes, init=FRAMES):
            with self.subTest(tried):
                # Waited for from inside the page: the page's policy refuses the eval that `wait_for_function` uses.
                page.evaluate(
                    "() => new Promise(done => { const wait = () => window.looked ? done() : "
                    "requestAnimationFrame(wait); wait(); })"
                )
                seen: dict[int, list[tuple[str, float, float]]] = {}
                for mark, words, x, y in page.evaluate("window.drawn"):
                    seen.setdefault(mark, []).append((words, x, y))
                self.assertGreater(len(seen), 0)
                for drawn in seen.values():
                    # A layout's fraction of a pixel is no move: a mark set again 0.2 px aside is not seen to move.
                    first, *_ = drawn
                    moved = [d for d in drawn if d[0] != first[0] or math.dist(d[1:], first[1:]) > 1]
                    self.assertEqual(moved, [], f'"{first[0]}" first drawn at {first[1]:.1f}, {first[2]:.1f}')

    def test_when_the_window_narrows_to_a_phones_width_the_marks_are_placed_again_for_it(self):
        for tried, page, _ in self.charts(sizes=SIZES[:1]):
            with self.subTest(tried):
                page.set_viewport_size({"width": 390, "height": 844})
                page.wait_for_timeout(300)
                chart = page.evaluate(MARKS)
                self.assertEqual(covered(chart) + astray(chart, nearest=True) + misnamed(chart) + crowded(chart), [])


class WithoutTheScript(ChartTest):
    def test_with_scripts_off_the_ranks_marks_are_the_builds_each_drawn_at_the_first_dot_it_names(self):
        """On 25 November the build writes "1, 3" and "2, 4, 5", each set 10 px right of its first dot, its middle
        level with it."""
        self.setUp()
        rows = read_json(ROOT / "site-data" / "boards" / "days" / NEWEST[0] / "daily.json")["rows"]
        self.write_board({**read_json(self.board_file()), "rows": rows})
        with self.run_chart() as browser:
            for width, height, touch in SIZES:
                with self.subTest(width=width):
                    page = self.baseline(browser, width, touch, scripts=False, height=height)
                    chart = page.evaluate(MARKS)
                    page.context.close()
                    self.assertEqual([mark["text"] for mark in chart["marks"]], ["1, 3", "2, 4, 5"])
                    for mark in chart["marks"]:
                        first = chart["dots"][mark["ranks"][0] - 1]
                        self.assertAlmostEqual(mark["box"][0], first["x"] + 10, delta=1)
                        self.assertAlmostEqual((mark["box"][1] + mark["box"][3]) / 2, first["y"], delta=1)

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
