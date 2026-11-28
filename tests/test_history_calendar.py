"""History's cells as a browser draws them: a board with no repository, beside a board and a day with no board (#91).

A board with no repository was drawn in the card's own white, or the card's own dark, which is lighter than the
first shade in the light theme and over the page in both, so the empty boards were the brightest cells in a month.
Such a cell now paints no fill of its own, gives its 0 in the third ink, and is edged with a dashed line, and the
legend names it and a day with no board, each drawn as the cell it names. In forced colours, which drop the shades,
the three are told apart by their edges and the hatch alone.

These open History in the Chrome the machine already has, through Playwright, as tests/test_repository_link.py does,
and fail without it. They build from the tests' own copy of the data contract's example, with one more board day
before it, so that a month holds a board, a day with no board, an empty board, and the newest board.
"""

import contextlib
import unittest

from helpers import BuildTest, read_json, write_json

from sitebuild import DAYS
from sitework.layout import chrome, published, served

PHONE, DESKTOP = 390, 1440

BOARD, EMPTY = "2026-11-06", "2026-11-08"
"""A board of three repositories, under the ramp's first step, and the example's own older board, which has no
repository. The day between them, 7 November, is the one day with no board."""

STYLE = """([board, empty]) => {
  const cell = (day) => document.querySelector(`.cal a[href="/days/${day}/"]`);
  const look = (element) => {
    if (!element) return {};
    const style = getComputedStyle(element);
    const count = element.querySelector('.count');
    return {
      fill: style.backgroundColor, image: style.backgroundImage, shadow: style.boxShadow,
      outline: `${style.outlineStyle} ${style.outlineWidth} ${style.outlineColor}`,
      ink: count ? getComputedStyle(count).color : null,
      shown: element.getClientRects().length > 0,
    };
  };
  const resolve = (value) => {
    const probe = document.createElement('i');
    probe.style.cssText = `forced-color-adjust: none; color: ${value}`;
    document.body.append(probe);
    const color = getComputedStyle(probe).color;
    probe.remove();
    return color;
  };
  const COLOURS = ['var(--text)', 'var(--text-3)', 'var(--shade-1)', 'GrayText', 'CanvasText'];
  return {
    board: look(cell(board)), gap: look(document.querySelector('.cal .gap')), empty: look(cell(empty)),
    emptyKey: look(document.querySelector('.ramp-legend i.empty-key')),
    gapKey: look(document.querySelector('.ramp-legend i.gap-key')),
    shadeKeys: [...document.querySelectorAll('.ramp-legend i[class^="shade"]')].map(look),
    colours: Object.fromEntries(COLOURS.map((value) => [value, resolve(value)])),
  };
}"""

NONE = "rgba(0, 0, 0, 0)"


class CalendarTest(BuildTest):
    def setUp(self):
        super().setUp()
        rows = [{**row, "rank": rank} for rank, row in enumerate(read_json(self.board_file())["rows"][:3], 1)]
        older = read_json(self.board_file(EMPTY))
        write_json(self.board_file(BOARD), {**older, "board_day": BOARD, "state": "rows", "rows": rows})
        index = read_json(self.index)
        write_json(self.index, {**index, "board_days": [*index["board_days"], {"board_day": BOARD, "row_count": 3}]})
        self.build_pages()

    @contextlib.contextmanager
    def history(self, width: int, scheme: str = "light", forced: str = "none"):
        """History, on a screen `width` pixels wide, in the colour scheme `scheme`, with forced colours or not."""
        with served(self.out) as site, chrome() as browser:
            context = browser.new_context(viewport={"width": width, "height": 900})
            page = context.new_page()
            page.emulate_media(color_scheme=scheme, forced_colors=forced)
            page.clock.set_fixed_time(published(self.out))
            page.goto(f"{site}/{DAYS.removesuffix('index.html')}", wait_until="load")
            try:
                yield page.evaluate(STYLE, [BOARD, EMPTY])
            finally:
                context.close()

    def each_look(self) -> list[tuple[dict, dict]]:
        """History in each theme at each width: what sets it apart, for a subtest, and how it is drawn."""
        looks = []
        for scheme in ("light", "dark"):
            for width in (PHONE, DESKTOP):
                with self.history(width, scheme) as look:
                    looks.append(({"scheme": scheme, "width": width}, look))
        return looks


class TheEmptyBoard(CalendarTest):
    def test_a_board_with_no_repository_paints_no_fill_and_a_muted_0_where_a_board_under_200_is_shaded_in_both_themes(
        self,
    ):
        for where, look in self.each_look():
            with self.subTest(**where):
                self.assertEqual((look["empty"]["fill"], look["empty"]["image"]), (NONE, "none"))
                self.assertEqual(look["empty"]["ink"], look["colours"]["var(--text-3)"])
                self.assertEqual(look["board"]["fill"], look["colours"]["var(--shade-1)"])
                self.assertEqual(look["board"]["ink"], look["colours"]["var(--text)"])

    def test_a_board_with_no_repository_is_edged_with_a_dashed_line_in_both_themes(self):
        for where, look in self.each_look():
            with self.subTest(**where):
                self.assertTrue(look["empty"]["outline"].startswith("dashed 1px"), look["empty"]["outline"])
                self.assertFalse(look["board"]["outline"].startswith("dashed"), look["board"]["outline"])
                self.assertIn("inset", look["board"]["shadow"])


class TheForcedColours(CalendarTest):
    def test_in_forced_colours_an_empty_boards_edge_is_dashed_a_boards_is_solid_and_a_day_with_no_board_is_hatched(
        self,
    ):
        for scheme in ("light", "dark"):
            with self.subTest(scheme), self.history(DESKTOP, scheme, "active") as look:
                colours = look["colours"]
                self.assertEqual(look["empty"]["outline"], f"dashed 1px {colours['GrayText']}")
                self.assertEqual(look["board"]["outline"], f"solid 1px {colours['CanvasText']}")
                self.assertIn("repeating-linear-gradient", look["gap"]["image"])
                self.assertNotIn("repeating-linear-gradient", look["empty"]["image"])
                self.assertNotIn("repeating-linear-gradient", look["board"]["image"])


class TheFocus(CalendarTest):
    """P14: the dashed edge of an empty board was drawn as an outline, which took the place of the focus ring, so a
    reader who reached an empty board with the keyboard could not see where they were (the review of #91)."""

    def test_an_empty_boards_link_shows_the_same_focus_ring_as_a_boards_when_the_keyboard_reaches_it(self):
        ring = """(element) => { const style = getComputedStyle(element);
          return [element.matches(':focus-visible'), style.outlineStyle, style.outlineWidth, style.outlineColor,
                  style.outlineOffset]; }"""
        for scheme in ("light", "dark"):
            with self.subTest(scheme), served(self.out) as site, chrome() as browser:
                context = browser.new_context(viewport={"width": DESKTOP, "height": 900})
                page = context.new_page()
                page.emulate_media(color_scheme=scheme)
                page.clock.set_fixed_time(published(self.out))
                page.goto(f"{site}/{DAYS.removesuffix('index.html')}", wait_until="load")
                board, empty = (page.locator(f'.cal a[href="/days/{day}/"]') for day in (BOARD, EMPTY))
                board.focus()
                page.keyboard.press("Tab")  # 7 November has no board, and so no link: Tab goes on to 8 November
                on_empty = empty.evaluate(ring)
                page.keyboard.press("Shift+Tab")
                on_board = board.evaluate(ring)
                context.close()
                self.assertEqual(on_empty, on_board)
                self.assertEqual(on_board[:3], [True, "solid", "2px"])


class TheLegend(CalendarTest):
    def test_each_new_swatch_is_drawn_as_the_cell_it_names_in_both_themes_and_in_forced_colours(self):
        looks = [("light", "none"), ("dark", "none"), ("light", "active"), ("dark", "active")]
        for scheme, forced in looks:
            with self.subTest(scheme=scheme, forced=forced), self.history(DESKTOP, scheme, forced) as look:
                self.assertTrue(look["emptyKey"].get("shown") and look["gapKey"].get("shown"))
                self.assertEqual(look["emptyKey"]["outline"], look["empty"]["outline"])
                self.assertEqual(look["emptyKey"]["fill"], look["empty"]["fill"])
                self.assertEqual(look["gapKey"]["image"], look["gap"]["image"])
                self.assertEqual(look["gapKey"]["fill"], look["gap"]["fill"])
                if forced == "active":
                    self.assertFalse(any(key["shown"] for key in look["shadeKeys"]))


class TheHeldMarkerAndYearJump(BuildTest):
    """#241: History marks held boards with a corner dot, screen-reader note, and legend swatch, and shows a
    year-jump navigation when the archive spans more than one calendar year."""

    def test_a_held_board_shows_its_marker_and_multi_year_history_shows_year_jump_links(self):
        newest = read_json(self.board_file())
        older = read_json(self.board_file(EMPTY))
        rows = [{**row, "rank": rank} for rank, row in enumerate(newest["rows"][:2], 1)]
        # Make 2026-11-08 a held board and add a 2025-12-31 board so History spans two years.
        write_json(
            self.board_file(EMPTY),
            {
                **older,
                "state": "held",
                "holds": newest["holds"],
                "missed_stars": newest["missed_stars"],
                "rows": rows,
            },
        )
        prior_year = "2025-12-31"
        write_json(
            self.board_file(prior_year),
            {**older, "board_day": prior_year, "published_at": "2026-01-01T00:00:00Z", "state": "rows", "rows": rows},
        )
        index = read_json(self.index)
        write_json(
            self.index,
            {
                **index,
                "board_days": [
                    index["board_days"][0],
                    {"board_day": EMPTY, "row_count": len(rows)},
                    {"board_day": prior_year, "row_count": len(rows)},
                ],
            },
        )
        pages = self.build_pages()
        days_page = pages[DAYS]
        held_links = [a for a in days_page.all("a") if "held" in a.classes()]
        self.assertEqual([a.attrs["href"] for a in held_links], [f"/days/{EMPTY}/", "/days/2026-11-09/"])
        self.assertEqual(held_links[0].attrs.get("aria-describedby"), "held-legend")
        self.assertEqual(held_links[0].attrs.get("title"), "Some star bands held back")
        years_nav = [nav for nav in days_page.all("nav") if "years" in nav.classes()]
        self.assertEqual(len(years_nav), 1)
        self.assertEqual(
            [(a.attrs["href"], a.text()) for a in years_nav[0].all("a")],
            [("#year-2026", "2026"), ("#year-2025", "2025")],
        )
        section_ids = {section.attrs["id"] for section in days_page.all("section") if "id" in section.attrs}
        self.assertTrue({"year-2026", "year-2025"} <= section_ids)

        with served(self.out) as site, chrome() as browser:
            page = browser.new_page(viewport={"width": DESKTOP, "height": 900})
            page.clock.set_fixed_time(published(self.out))
            page.goto(f"{site}/{DAYS.removesuffix('index.html')}", wait_until="load")
            dot = page.evaluate(
                """(day) => {
                  const a = document.querySelector(`.cal a[href="/days/${day}/"]`);
                  const after = getComputedStyle(a, '::after');
                  const key = getComputedStyle(document.querySelector('.ramp-legend i.held-key'), '::after');
                  return {
                    aBg: after.backgroundColor, aWidth: after.width,
                    keyBg: key.backgroundColor, keyWidth: key.width,
                  };
                }""",
                EMPTY,
            )
            self.assertEqual(dot["aWidth"], "6px")
            self.assertEqual(dot["keyWidth"], "6px")
            self.assertEqual(dot["aBg"], dot["keyBg"])
            page.close()


if __name__ == "__main__":
    unittest.main()
