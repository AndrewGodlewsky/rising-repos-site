"""The board's search in the day bar from 768 px up, and in the filter on a phone (#213).

From 768 px up the search box sat at the end of the filter's row, and it asks for 160 px. On a board whose language
menu is wide, as one that lists "DIGITAL Command Language" is, the controls before it left less than that, and the
box fell alone onto a line of its own at the right, 50 px under the rest. The owner chose to move it into the day bar,
which is pinned to the top of the window, so that it stays in reach all the way down a long board and the filter
keeps its row to itself. A phone's day bar has no room beside its dates, so below 768 px the search stays full width
at the top of the filter, as it was. The page holds a box in each place, the stylesheet draws one of them by the
width, and the script keeps the two holding the same words.

Where a box is drawn, which one a screen reader meets, and where the keyboard goes are things only a browser can say,
so these open the pages in the Chrome the machine already has, through Playwright, as `tests/test_day_bar.py` does,
with the browser's clock at the newest board's publish time, so that no page hides its board.
"""

import re
import unittest
from datetime import datetime, timedelta
from itertools import pairwise
from urllib.parse import parse_qs, urlparse

from helpers import BuildTest, read_json, write_json

from sitebuild import BASELINE, DAYS, FOR_AGENTS, HOW_IT_WORKS, board_day_page
from sitework.layout import chrome, published, served

NEWEST, OLDER = "2026-11-09", "2026-11-08"

DESKTOP, LAPTOP, TABLET = 1440, 1024, 768
"""A desktop's width, a smaller laptop's, and the width at which the page first lays itself out as for a desktop."""

PHONES = ((390, 844), (360, 740), (767, 900))
"""A phone, the narrowest phone that has room for Latest, and the widest window that is still laid out as a phone."""

NAME = "Search by name or description"
"""The name a screen reader hears for the search box, as it was before the box moved."""

PARTS = """() => {
  const wrap = document.querySelector('.strip .wrap');
  const box = wrap.getBoundingClientRect();
  const style = getComputedStyle(wrap);
  const kinds = '.before, .here, .after, .latest, .newest, input[type=search]';
  return {
    left: box.left + parseFloat(style.paddingLeft),
    right: box.right - parseFloat(style.paddingRight),
    sideways: document.documentElement.scrollWidth - window.innerWidth,
    parts: [...wrap.querySelectorAll(kinds)].filter(part => part.checkVisibility()).map(part => {
      const edge = part.getBoundingClientRect();
      const look = getComputedStyle(part);
      return {
        kind: part.matches('input') ? 'search' : part.classList[0],
        left: edge.left, right: edge.right, middle: (edge.top + edge.bottom) / 2, height: edge.height,
        padding: parseFloat(look.paddingLeft), gap: getComputedStyle(part.parentElement).columnGap,
      };
    }),
  };
}"""
"""Where the day bar's own room begins and ends, inside its padding; how far the page reaches past the screen's right
edge; and each part of the bar that is drawn, in the order a reader meets them: its kind (the board day before, the
date, the board day after, Latest, the way to the newest board, or a search box), its two sides, the height of its
middle, its height, and its padding."""

FILTER = """() => [...document.querySelectorAll('.toolbar > *')]
  .filter(control => control.checkVisibility() && !control.classList.contains('sr'))
  .map(control => ({id: control.id, top: control.getBoundingClientRect().top}))"""
"""Each control the filter draws, by its id, and the height of its top."""

AT_THE_TOP = """() => {
  const boxes = [...document.querySelectorAll('input[type=search]')].filter(box => box.checkVisibility());
  const filter = document.querySelector('.toolbar').getBoundingClientRect();
  const box = boxes.length ? boxes[0].getBoundingClientRect() : null;
  return {
    shown: boxes.length,
    inFilter: boxes.length === 1 && document.querySelector('.toolbar').contains(boxes[0]),
    left: box && box.left, right: box && box.right, bottom: box && box.bottom,
    filterLeft: filter.left, filterRight: filter.right,
    kindsTop: document.getElementById('kinds').getBoundingClientRect().top,
  };
}"""
"""The search boxes drawn on the page, whether the one drawn is in the filter, its sides and its foot, the filter's
sides, and the top of All and New."""

SHOWN = """() => [...document.querySelectorAll('table.chart tbody tr')]
  .filter(row => row.querySelector('th.re') && row.checkVisibility())
  .map(row => row.querySelector('th.re a').textContent.trim())"""
"""The name of each row the board shows, in the order it shows them."""

DRAWN = "() => [...document.querySelectorAll('input[type=search]')].filter(box => box.checkVisibility()).length"
"""How many search boxes the page draws."""

LABELS = f"""() => [...document.querySelectorAll('label')]
  .filter(label => label.textContent.trim() === '{NAME}' && label.checkVisibility()).length"""
"""How many labels that name the search the page renders, drawn or kept for a screen reader alone: a label whose box
is not drawn would still be heard, naming nothing."""

FOCUS = """() => {
  const focused = document.activeElement;
  if (!focused) return {at: ''};
  const look = getComputedStyle(focused);
  const at = focused.matches('.latest') ? 'latest'
    : focused.matches('input[type=search]') ? 'search'
    : focused.matches('#kinds button[data-kind=""]') ? 'all'
    : focused.tagName.toLowerCase();
  return {at, ring: look.outlineStyle !== 'none' && parseFloat(look.outlineWidth) > 0};
}"""
"""Where the keyboard is: on Latest, on a search box, on the filter's All button, or on another element by its tag;
and whether it draws its ring there."""


class TheSearchInTheDayBar(BuildTest):
    def setUp(self):
        super().setUp()
        # The newest board lists "DIGITAL Command Language", whose name made the language menu wide enough on 26
        # November 2026 to push the search off the filter's row, so that every test meets the widest menu a board has
        # shown. The example's older board has no row, and so no filter and no search: give it two of the newest's.
        newest = read_json(self.board_file())
        self.rows = [{**newest["rows"][0], "language": "DIGITAL Command Language"}, *newest["rows"][1:]]
        self.write_board({**newest, "rows": self.rows})
        older = read_json(self.board_file(OLDER))
        self.write_board({**older, "state": "rows", "rows": [self.rows[1], self.rows[3]]})

    @classmethod
    def setUpClass(cls):
        """One build of the example as setUp makes it, served once and opened in one Chrome by every test that leaves
        it as it is: a build and a browser for each test made the pull request's job longer than the ten minutes it
        is given (#213). The test that makes boards of its own builds them, and opens them in the same Chrome."""
        shared = cls()
        shared.setUp()
        cls.addClassCleanup(shared.doCleanups)
        shared.build_pages()
        cls.built = shared.out
        cls.site = cls.enterClassContext(served(cls.built))
        cls.browser = cls.enterClassContext(chrome())

    def open(self, site: str, path: str = "index.html", width: int = DESKTOP, height: int = 900, days=0, built=None):
        """The page at `path` of the site served at `site`, on a screen `width` by `height` pixels, with the clock
        `days` after the newest board of the build `built` (the shared one, unless another is given) was published,
        once its type is in."""
        page = self.browser.new_page(viewport={"width": width, "height": height})
        page.clock.set_fixed_time(datetime.fromisoformat(published(built or self.built)) + timedelta(days=days))
        page.goto(f"{site}/{path.removesuffix('index.html')}", wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        return page

    def matching(self, word: str) -> list[str]:
        """The names of the newest board's rows whose name or description holds `word`, in rank order: what a
        search for it is to show."""
        return [
            row["full_name"]
            for row in self.rows
            if word in (row["full_name"] + " " + (row.get("description") or "")).lower()
        ]

    def test_from_768_px_up_the_search_box_is_on_the_day_bars_line_at_its_right_hand_end(self):
        site = self.site
        for path in ("index.html", board_day_page(OLDER)):
            for width, height in ((DESKTOP, 900), (LAPTOP, 768)):
                with self.subTest(path, width=width):
                    page = self.open(site, path, width, height)
                    seen = page.evaluate(PARTS)
                    kinds = [part["kind"] for part in seen["parts"]]
                    self.assertIn("search", kinds, seen["parts"])
                    search = seen["parts"][kinds.index("search")]
                    date = seen["parts"][kinds.index("here")]
                    self.assertAlmostEqual(search["middle"], date["middle"], delta=1, msg=seen["parts"])
                    self.assertAlmostEqual(search["right"], seen["right"], delta=1, msg=seen)
                    self.assertEqual(page.evaluate(DRAWN), 1)
                    page.close()

    def test_at_1440_px_the_filters_lie_on_one_row_on_a_board_listing_digital_command_language(self):
        page = self.open(self.site)
        self.assertIn("DIGITAL Command Language", page.locator("#language option").all_text_contents())
        controls = page.evaluate(FILTER)
        # The switch between the list and the cards ends the filter's row (#227).
        self.assertEqual([control["id"] for control in controls], ["kinds", "bands", "language", "sort", "layout"])
        self.assertEqual(len({round(control["top"]) for control in controls}), 1, controls)
        page.close()

    def test_on_an_earlier_board_the_search_box_follows_latest_and_overlaps_no_part_of_the_bar(self):
        """The widest bars there are, as `tests/test_day_bar.py` makes them: the first board day's, which says
        "First board", and one in May between two days of May, each board with rows, so that it has a search."""
        days = ["2027-05-30", "2027-05-29", "2027-05-28", "2027-05-27", "2026-07-30", "2026-07-29"]
        older = read_json(self.board_file(OLDER))
        for day in days:
            write_json(
                self.board_file(day),
                {**older, "board_day": day, "published_at": f"{day}T23:38:52Z", "state": "rows", "rows": self.rows},
            )
        entries = [{"board_day": day, "row_count": len(self.rows)} for day in days]
        write_json(self.index, {**read_json(self.index), "board_days": entries})
        self.build_pages()
        with served(self.out) as site:
            for day in ("2026-07-29", "2027-05-28"):
                for width in (TABLET, LAPTOP, DESKTOP):
                    with self.subTest(day, width=width):
                        page = self.open(site, board_day_page(day), width, built=self.out)
                        seen = page.evaluate(PARTS)
                        parts = seen["parts"]
                        self.assertEqual(
                            [part["kind"] for part in parts], ["before", "here", "after", "latest", "search"]
                        )
                        self.assertLessEqual(seen["sideways"], 0, "the page scrolls sideways")
                        self.assertLessEqual(
                            max(p["middle"] for p in parts) - min(p["middle"] for p in parts), 1, parts
                        )
                        for before, after in pairwise(parts):
                            self.assertLessEqual(before["right"], after["left"] + 0.5, (before, after))
                        for part in parts:
                            self.assertGreaterEqual(part["left"], seen["left"] - 0.5, part)
                            self.assertLessEqual(part["right"], seen["right"] + 0.5, part)
                        page.close()

    def test_on_a_phone_the_day_bar_holds_the_parts_it_held_and_no_search_box(self):
        """As it was: the board day before and the date on the newest board; on an earlier one, the board day after
        and Latest too, Latest at the bar's right-hand end; every part on one line from the bar's left-hand edge, 32 px
        tall, with 8 px at each side of a link (4 px below 390 px) and 4 px at each side of the date, and 4 px
        between parts (2 px below 390 px)."""
        site = self.site
        for path, kinds in (
            ("index.html", ["before", "here"]),
            (board_day_page(OLDER), ["before", "here", "after", "latest"]),
        ):
            for width, height in PHONES:
                with self.subTest(path, width=width):
                    page = self.open(site, path, width, height)
                    seen = page.evaluate(PARTS)
                    parts = seen["parts"]
                    self.assertEqual([part["kind"] for part in parts], kinds)
                    self.assertAlmostEqual(parts[0]["left"], seen["left"], delta=0.5, msg=parts)
                    self.assertLessEqual(max(p["middle"] for p in parts) - min(p["middle"] for p in parts), 1, parts)
                    if kinds[-1] == "latest":
                        self.assertAlmostEqual(parts[-1]["right"], seen["right"], delta=0.5, msg=parts)
                    for part in parts:
                        self.assertAlmostEqual(part["height"], 32, delta=0.5, msg=part)
                        self.assertEqual(part["padding"], 4 if part["kind"] == "here" or width < 390 else 8, part)
                        self.assertEqual(part["gap"], "4px" if width >= 390 else "2px", part)
                    page.close()

    def test_on_a_phone_the_search_box_is_full_width_at_the_top_of_the_filter(self):
        site = self.site
        for path in ("index.html", board_day_page(OLDER)):
            for width, height in PHONES:
                with self.subTest(path, width=width):
                    page = self.open(site, path, width, height)
                    seen = page.evaluate(AT_THE_TOP)
                    self.assertEqual(seen["shown"], 1, seen)
                    self.assertTrue(seen["inFilter"], seen)
                    self.assertAlmostEqual(seen["left"], seen["filterLeft"], delta=0.5, msg=seen)
                    self.assertAlmostEqual(seen["right"], seen["filterRight"], delta=0.5, msg=seen)
                    self.assertLessEqual(seen["bottom"], seen["kindsTop"], seen)
                    page.close()

    def test_typing_in_the_day_bars_search_box_shows_only_the_rows_that_hold_the_words(self):
        """At 1440 px in the day bar's box, and at 390 px in the filter's, as before."""
        expected = self.matching("octocat")
        self.assertTrue(0 < len(expected) < len(self.rows), expected)
        site = self.site
        for width, height, where in ((DESKTOP, 900, "search"), (390, 844, "toolbar")):
            with self.subTest(width=width):
                page = self.open(site, width=width, height=height)
                scope = page.get_by_role("search") if where == "search" else page.locator(".toolbar")
                box = scope.get_by_role("searchbox", name=NAME, exact=True)
                self.assertEqual(box.count(), 1)
                box.fill("octocat")
                self.assertEqual(page.evaluate(SHOWN), expected)
                self.assertEqual(page.locator("#shown").text_content(), f"{len(expected)} of {len(self.rows)} shown")
                self.assertEqual(parse_qs(urlparse(page.url).query).get("q"), ["octocat"])
                page.close()

    def test_the_words_searched_stay_in_view_and_the_rows_stay_as_the_window_crosses_768_px(self):
        site = self.site
        page = self.open(site)
        for word, width, height in (("octocat", 390, 844), ("hello", DESKTOP, 900)):
            with self.subTest(word):
                page.get_by_role("searchbox", name=NAME, exact=True).fill(word)
                rows = page.evaluate(SHOWN)
                self.assertEqual(rows, self.matching(word))
                page.set_viewport_size({"width": width, "height": height})
                box = page.get_by_role("searchbox", name=NAME, exact=True)
                self.assertEqual(box.count(), 1)
                self.assertEqual(box.input_value(), word)
                self.assertEqual(page.evaluate(SHOWN), rows)

    def test_on_a_phone_clear_search_and_filters_empties_the_search_box_and_a_step_leaves_it_empty(self):
        site = self.site
        page = self.open(site, width=390, height=844)
        box = page.get_by_role("searchbox", name=NAME, exact=True)
        box.fill("no-such-word")
        self.assertEqual(page.evaluate(SHOWN), [])
        page.get_by_role("button", name="Clear search and filters", exact=True).click()
        self.assertEqual(box.input_value(), "")
        self.assertEqual(len(page.evaluate(SHOWN)), len(self.rows))
        page.go_back()
        self.assertEqual(box.input_value(), "no-such-word")
        self.assertEqual(page.evaluate(SHOWN), [])
        bar = page.get_by_role("navigation", name="Board days", exact=True)
        bar.get_by_role("link", name=re.compile("^The board before, ")).click()
        page.wait_for_url(re.compile(f"/days/{OLDER}/"))
        self.assertNotIn("q", parse_qs(urlparse(page.url).query))
        self.assertEqual(page.get_by_role("searchbox", name=NAME, exact=True).input_value(), "")

    def test_with_scripts_off_no_search_box_is_shown_at_either_width(self):
        site = self.site
        for path in ("index.html", board_day_page(OLDER)):
            for width, height in ((DESKTOP, 900), (390, 844)):
                with self.subTest(path, width=width):
                    context = self.browser.new_context(
                        java_script_enabled=False, viewport={"width": width, "height": height}
                    )
                    page = context.new_page()
                    page.goto(f"{site}/{path.removesuffix('index.html')}", wait_until="load")
                    self.assertEqual(page.evaluate(DRAWN), 0)
                    self.assertEqual(page.get_by_role("searchbox").count(), 0)
                    self.assertEqual(page.get_by_role("search").count(), 0)
                    context.close()

    def test_a_screen_reader_hears_one_search_box_in_a_search_landmark_and_not_among_the_board_days(self):
        site = self.site
        for width, height in ((DESKTOP, 900), (390, 844)):
            with self.subTest(width=width):
                page = self.open(site, board_day_page(OLDER), width, height)
                self.assertEqual(page.get_by_role("searchbox").count(), 1)
                self.assertEqual(page.get_by_role("searchbox", name=NAME, exact=True).count(), 1)
                self.assertEqual(page.evaluate(LABELS), 1, "the search's name is heard once, beside its box")
                days = page.get_by_role("navigation", name="Board days", exact=True)
                self.assertEqual(days.get_by_role("searchbox").count(), 0)
                # The board days' links are the ones the bar held: the board after and Latest, here.
                self.assertEqual(days.get_by_role("link").count(), 2)
                self.assertEqual(days.get_by_role("link", name="The board after, 9 Nov", exact=True).count(), 1)
                self.assertEqual(days.get_by_role("link", name="The newest board, 9 Nov", exact=True).count(), 1)
                if width == DESKTOP:
                    landmark = page.get_by_role("search")
                    self.assertEqual(landmark.count(), 1)
                    self.assertEqual(landmark.get_by_role("searchbox", name=NAME, exact=True).count(), 1)
                page.close()

    def test_the_keyboard_reaches_the_search_box_after_latest_and_before_the_filter_with_its_ring(self):
        site = self.site
        page = self.open(site, board_day_page(OLDER))
        stops = []
        for _ in range(40):
            page.keyboard.press("Tab")
            stops.append(page.evaluate(FOCUS))
            if stops[-1]["at"] == "all":
                break
        path = [stop["at"] for stop in stops]
        self.assertIn("latest", path)
        self.assertIn("search", path)
        self.assertIn("all", path)
        self.assertLess(path.index("latest"), path.index("search"), path)
        self.assertLess(path.index("search"), path.index("all"), path)
        self.assertTrue(stops[path.index("search")]["ring"], stops)

    def test_a_board_seven_days_old_shows_no_search_box_at_either_width(self):
        site = self.site
        for width, height in ((DESKTOP, 900), (390, 844)):
            with self.subTest(width=width):
                page = self.open(site, width=width, height=height, days=8)
                self.assertTrue(page.evaluate("document.documentElement.hasAttribute('data-withheld')"))
                self.assertEqual(page.evaluate(DRAWN), 0)
                self.assertEqual(page.get_by_role("searchbox").count(), 0)
                page.close()

    def test_the_day_bars_of_history_baseline_how_it_works_and_for_agents_are_as_they_were(self):
        """As they were: no search box, every part on the bar's one line from its left-hand edge, each 32 px tall,
        with 8 px at each side, and 4 px below 390 px."""
        site = self.site
        for path in (DAYS, BASELINE, HOW_IT_WORKS, FOR_AGENTS):
            for width in (DESKTOP, TABLET, 390, 360):
                with self.subTest(path, width=width):
                    page = self.open(site, path, width)
                    seen = page.evaluate(PARTS)
                    parts = seen["parts"]
                    self.assertTrue(parts, seen)
                    self.assertNotIn("search", [part["kind"] for part in parts])
                    self.assertAlmostEqual(parts[0]["left"], seen["left"], delta=0.5, msg=parts)
                    self.assertLessEqual(max(p["middle"] for p in parts) - min(p["middle"] for p in parts), 1, parts)
                    for part in parts:
                        self.assertAlmostEqual(part["height"], 32, delta=0.5, msg=part)
                        self.assertEqual(part["padding"], 8 if width >= 390 else 4, part)
                    page.close()

    def test_keyboard_shortcuts_focus_and_clear_search_and_step_between_board_days(self):
        """#240: / focuses the visible search box at either width, Escape clears then blurs it, [ and ] step to
        previous/next board days, and typing inside an input or select does not trigger navigation."""
        for width, height, expected_id in ((DESKTOP, 900, "day-q"), (390, 844, "q")):
            with self.subTest(width=width):
                page = self.open(self.site, width=width, height=height)
                page.keyboard.press("/")
                self.assertEqual(page.evaluate("document.activeElement && document.activeElement.id"), expected_id)
                page.keyboard.type("octocat")
                self.assertEqual(page.evaluate(SHOWN), self.matching("octocat"))
                # Typing [ inside the search box stays text and does not navigate away.
                page.keyboard.type("[")
                self.assertIn("index.html", page.url + "index.html")
                self.assertNotIn(f"/days/{OLDER}/", page.url)
                # First Escape clears the search; second Escape leaves the search box.
                page.keyboard.press("Escape")
                self.assertEqual(page.locator(f"#{expected_id}").input_value(), "")
                self.assertEqual(len(page.evaluate(SHOWN)), len(self.rows))
                page.keyboard.press("Escape")
                self.assertNotEqual(page.evaluate("document.activeElement && document.activeElement.id"), expected_id)
                page.close()

        # Outside form controls, [ steps to the board before and ] steps to the board after.
        page = self.open(self.site)
        with page.expect_navigation(wait_until="load"):
            page.keyboard.press("[")
        self.assertIn(f"/days/{OLDER}/", page.url)
        with page.expect_navigation(wait_until="load"):
            page.keyboard.press("]")
        self.assertIn(f"/days/{NEWEST}/", page.url)
        page.close()


if __name__ == "__main__":
    unittest.main()
