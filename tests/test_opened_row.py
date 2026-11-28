"""An opened row's table of the boards it was on, as a browser lays it out (#27).

On a phone the table's five columns do not fit an opened row's box. They were cut at the edge of the part that
holds them, with the last column out of sight and nothing to say so. So below 768 px each board day is stacked: its
date, and under it its four figures, each under its column's heading. From 768 px up it is a table under its
headings.

Every other test here reads what the build writes. Where a part sits on a screen is something only a browser can
say, so these open a row in the Chrome the machine already has, through Playwright, as the owner's tests do, and
fail without it. They build from the tests' own copy of the data contract's example, serve the pages from this
machine alone, and set the browser's clock to the newest board's publish time, so that no page hides its board
behind the notice of an old one.
"""

import json
import unittest

from helpers import BuildTest, read_json

from sitebuild import board_day_page
from sitework.layout import chrome, published, served

NEWEST, OLDER = "2026-11-09", "2026-11-08"

HEADINGS = ["Board day", "Rank", "Total stars", "Stars a day", "Multiple"]

PHONE, DESKTOP = 390, 1440
NARROW = 320
"""The narrowest phone the table is held to: an opened row's box is 240 pixels wide there."""

LONGEST = {"stars": 1234567, "recent_stars": 24690, "recent_days": 2, "score": 1286.0, "baseline": 9.6}
"""A row whose figures are as long as a board writes them: 1,234,567 stars, +12,345 a day, and 1,286× its pace."""

SEEN = """(row) => {
  const table = row.querySelector(".op table");
  const part = table.parentElement;
  const edges = (thing) => {
    const box = thing.getBoundingClientRect();
    return { left: box.left, right: box.right, top: box.top, bottom: box.bottom };
  };
  const words = (cell) => {
    const range = document.createRange();
    range.selectNodeContents(cell);
    return edges(range);
  };
  const drawn = (cell) => {
    const before = getComputedStyle(cell, "::before");
    return before.display === "none" || before.content === "none" ? "" : before.content.replace(/^"|"$/g, "");
  };
  return {
    box: edges(row.querySelector(".op")),
    scrolls: part.scrollWidth > part.clientWidth,
    headings: edges(table.tHead),
    days: [...table.tBodies[0].rows].map((day) => [...day.cells].map((cell) => ({
      tag: cell.tagName.toLowerCase(),
      text: cell.textContent,
      heading: drawn(cell),
      spills: cell.scrollWidth > cell.clientWidth,
      words: words(cell),
      ...edges(cell),
    }))),
  };
}"""
"""Run on a board's row once it is opened: where the opened row's box is, whether the part that holds the table
scrolls sideways, where the table's row of headings is, and each board day's cells in order. A cell gives its tag,
its text, the heading the stylesheet draws inside it, if any, whether its words spill out of its own box, where its
words are, and where its box is."""

ROLES = """(row) => {
  const table = row.querySelector(".op table");
  const role = (part) => part.getAttribute("role");
  return {
    table: role(table),
    groups: [table.tHead, table.tBodies[0]].map(role),
    rows: [...table.rows].map(role),
    headings: [...table.tHead.rows[0].cells].map(role),
    days: [...table.tBodies[0].rows].map((day) => [...day.cells].map(role)),
  };
}"""
"""Run on a board's row once it is opened: the role each part of its table names, as its own attribute."""


BEFORE = "And 14 boards before 28 Oct, the first on 7 Aug 2026. Its best rank on any board: 1."
"""The line of boards older than the window that #9 openJiuwen-ai/jiuwenswarm gives on the 26 Nov 2026 board (#221)."""

RING = 4
"""How far out from a focused link its ring reaches: an outline 2 px wide, drawn 2 px from it (site.css)."""

LINE = """(row) => {
  const opened = row.querySelector(".op");
  const table = opened.querySelector("table");
  const part = [...opened.children].find((child) => child.contains(table));
  const line = [...opened.querySelectorAll("p")].find((p) => p.textContent.includes("Every board day is in"));
  const edges = (thing) => {
    const box = thing.getBoundingClientRect();
    return { left: box.left, right: box.right, top: box.top, bottom: box.bottom };
  };
  return {
    box: edges(opened),
    part: edges(part),
    table: edges(table),
    line: edges(line),
    link: edges(line.querySelector("a")),
    cut: part.scrollHeight > part.clientHeight || part.scrollWidth > part.clientWidth,
    wider: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  };
}"""
"""Run on a board's row once it is opened: where its box, the part of it that holds the table, the table, the line
of earlier boards, and the line's link are, whether that part cuts what it holds, and whether the page is wider than
the screen."""


class TheBoardsItWasOn(BuildTest):
    def earlier(self, **fields) -> None:
        """Make the example's older board, empty in the example, a board that lists the newest board's rows, the
        first of them with `fields`, so that every row was on two boards."""
        first, *rest = read_json(self.board_file())["rows"]
        board = read_json(self.board_file(OLDER))
        self.write_board({**board, "state": "rows", "rows": [{**first, **fields}, *rest]})

    def history(self) -> dict:
        self.build_pages()
        return read_json(self.out / board_day_page(NEWEST).replace("index.html", "history.json"))

    def opened(self, browser, site: str, width: int):
        """The newest board's first row, opened on a screen `width` pixels wide, once its table has arrived. The
        page is closed with its browser."""
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.clock.set_fixed_time(published(self.out))
        page.goto(site, wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        row = page.locator("table.chart > tbody > tr").first
        row.locator("summary").first.click()
        row.locator(".op table").wait_for()
        return row

    def assert_each_day_is_stacked_and_whole(self, seen: dict, history: dict) -> None:
        """Each board day gives its date and then its four figures, each under its heading, as `history` words
        them, newest first, and every one of them is whole inside the opened row's box."""
        on = list(reversed(history["rows"][0]["on"]))
        self.assertEqual(len(seen["days"]), len(on))
        self.assertFalse(seen["scrolls"], "the part that holds the table scrolls sideways")
        for day, (place, rank, stars, a_day, _, multiple) in zip(seen["days"], on, strict=True):
            date, *figures = day
            with self.subTest(history["days"][place]):
                self.assertEqual((date["tag"], date["text"], date["heading"]), ("th", history["dates"][place][1], ""))
                self.assertEqual(
                    [(cell["tag"], cell["heading"], cell["text"]) for cell in figures],
                    [("td", *pair) for pair in zip(HEADINGS[1:], [str(rank), stars, a_day, multiple], strict=True)],
                )
                for cell in day:
                    self.assertGreaterEqual(cell["left"], seen["box"]["left"] - 0.5, cell)
                    self.assertLessEqual(cell["right"], seen["box"]["right"] + 0.5, cell)
                    self.assertFalse(cell["spills"], cell)
                for cell in figures:
                    # Under the date, with room over its own words for the heading the stylesheet draws there.
                    self.assertGreaterEqual(cell["top"], date["bottom"] - 0.5, cell)
                    self.assertGreaterEqual(cell["words"]["top"] - cell["top"], 12, cell)

    def test_on_a_phone_each_board_day_is_stacked_with_each_figure_under_its_heading_and_nothing_cut(self):
        self.earlier()
        history = self.history()
        with served(self.out) as site, chrome() as browser:
            seen = self.opened(browser, site, PHONE).evaluate(SEEN)
        self.assertEqual(len(seen["days"]), 2)
        self.assert_each_day_is_stacked_and_whole(seen, history)
        # The row of headings is kept for a screen reader, cut to a pixel, so that no heading is drawn twice.
        self.assertLessEqual(seen["headings"]["right"] - seen["headings"]["left"], 1)
        self.assertLessEqual(seen["headings"]["bottom"] - seen["headings"]["top"], 1)

    def test_the_longest_figures_a_board_writes_are_whole_on_a_screen_320_pixels_wide(self):
        self.earlier(**LONGEST, divided_by=LONGEST["baseline"])
        history = self.history()
        self.assertEqual(history["rows"][0]["on"][0][2:], ["1,234,567", "+12,345", "", "1,286×"])
        with served(self.out) as site, chrome() as browser:
            seen = self.opened(browser, site, NARROW).evaluate(SEEN)
        self.assert_each_day_is_stacked_and_whole(seen, history)

    def test_the_table_and_each_of_its_parts_names_its_role_at_a_phones_width_and_at_a_desktops(self):
        """The board's own table names its parts' roles because some browsers stop telling assistive technology
        that a table is one once its parts' display changes, as a stacked board day's does. This table does the
        same, and a reader of roles finds in it what the page shows: the table by its caption, its five headings,
        and each board day as a row headed by its date."""
        self.earlier()
        history = self.history()
        dates = [history["dates"][place][1] for place, *_ in reversed(history["rows"][0]["on"])]
        with served(self.out) as site, chrome() as browser:
            for width in (PHONE, DESKTOP):
                with self.subTest(width=width):
                    row = self.opened(browser, site, width)
                    self.assertEqual(
                        row.evaluate(ROLES),
                        {
                            "table": "table",
                            "groups": ["rowgroup", "rowgroup"],
                            "rows": ["row"] * 3,
                            "headings": ["columnheader"] * 5,
                            "days": [["rowheader", "cell", "cell", "cell", "cell"]] * 2,
                        },
                    )
                    table = row.get_by_role("table", name="The boards it was on")
                    self.assertEqual(table.get_by_role("columnheader").all_text_contents(), HEADINGS)
                    self.assertEqual(table.get_by_role("rowheader").get_by_role("link").all_text_contents(), dates)
                    self.assertEqual(table.get_by_role("cell").count(), 8)

    def with_earlier_boards(self) -> None:
        """Build the example with every row on both its boards, and give the newest board's first row, in its
        history, the line of boards older than its window that a board with more than 30 boards before it gives. The
        example holds two boards, so the line is written into the file, as the build words it, for the script to
        place."""
        self.earlier()
        history = self.history()
        history["rows"][0]["before"] = BEFORE
        path = self.out / board_day_page(NEWEST).replace("index.html", "history.json")
        path.write_text(json.dumps(history), encoding="utf-8")

    def test_the_table_of_the_boards_it_was_on_is_named_with_the_number_of_board_days_it_covers(self):
        """#221: the table covers only the board days the strip above it does, and its name says how many. The
        example's newest board has one board before it, so the window is its two board days."""
        self.earlier()
        self.history()
        with served(self.out) as site, chrome() as browser:
            row = self.opened(browser, site, DESKTOP)
            self.assertEqual(row.locator(".op table caption").text_content(), "The boards it was on, of the last 2")

    def test_a_row_on_boards_before_the_window_shows_the_line_under_its_table_with_a_link_to_history(self):
        """#221: the line the file gives, and then "Every board day is in History.", where History links to the
        page the site's bar calls History. A row whose file gives no line shows none."""
        self.with_earlier_boards()
        with served(self.out) as site, chrome() as browser:
            row = self.opened(browser, site, DESKTOP)
            line = row.locator(".op p", has_text="Every board day is in")
            self.assertEqual(line.count(), 1)
            self.assertEqual(line.text_content(), BEFORE + " Every board day is in History.")
            link = line.get_by_role("link")
            self.assertEqual((link.text_content(), link.get_attribute("href")), ("History", "/days/"))
            table, said = row.locator(".op table").bounding_box(), line.bounding_box()
            self.assertGreaterEqual(said["y"], table["y"] + table["height"] - 0.5)
            page = row.page
            second = page.locator("table.chart > tbody > tr").nth(1)
            second.locator("summary").first.click()
            second.locator(".op table").wait_for()
            self.assertEqual(second.locator(".op p", has_text="Every board day is in").count(), 0)

    def test_on_a_phone_the_line_of_earlier_boards_is_whole_and_the_page_does_not_scroll_sideways(self):
        """#221: on a phone the line is whole inside the opened row's box, and nothing of it pushes the page wider
        than the screen. From 768 px up it sits under the table, inside the table's part of the opened row."""
        self.with_earlier_boards()
        with served(self.out) as site, chrome() as browser:
            for width in (PHONE, DESKTOP):
                with self.subTest(width=width):
                    seen = self.opened(browser, site, width).evaluate(LINE)
                    self.assertFalse(seen["wider"], "the page scrolls sideways")
                    self.assertGreaterEqual(seen["line"]["left"], seen["box"]["left"] - 0.5)
                    self.assertLessEqual(seen["line"]["right"], seen["box"]["right"] + 0.5)
                    self.assertLessEqual(seen["line"]["bottom"], seen["box"]["bottom"] + 0.5)
                    self.assertGreaterEqual(seen["line"]["top"], seen["table"]["bottom"] - 0.5)
                    self.assertGreaterEqual(seen["line"]["left"], seen["part"]["left"] - 0.5)
                    self.assertLessEqual(seen["line"]["right"], seen["part"]["right"] + 0.5)
                    self.assertFalse(seen["cut"], "the part that holds the line cuts it")
                    # The part scrolls sideways, so it cuts what falls outside it: the ring that a focused link draws
                    # 2 px out from it, 2 px wide, falls inside.
                    self.assertLessEqual(seen["link"]["bottom"] + RING, seen["part"]["bottom"] + 0.5)
                    self.assertGreaterEqual(seen["link"]["left"] - RING, seen["part"]["left"] - 0.5)


if __name__ == "__main__":
    unittest.main()
