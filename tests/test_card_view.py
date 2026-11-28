"""A board's rows as cards, beside the list they have always been (#227).

A switch at the end of the filter row, "List" and "Cards", turns a board with rows between the list and a grid of
cards: the same rows, each drawn as a box, as many to a line as fit at 280 px or wider. The owner chose this design,
design A, from three prototypes, and chose that the list stays the first view and that a reader's choice is kept in
the address, as `view=cards`, and in this browser. A card holds its row's own parts and no other, so that the cards
add nothing to a row's markup, which a long board has no room for: the stylesheet lays the same cells out in other
areas.

How the cards lie, what each holds, where the keyboard goes, and what a press keeps are things only a browser can
say, so these open the pages in the Chrome the machine already has, through Playwright, as
`tests/test_search_in_the_day_bar.py` does, with the browser's clock at the newest board's publish time, so that no
page hides its board. What the script does before the page is parsed, and what it keeps, is held under Node in
`tests/test_old_board.py`, `TheView`.
"""

import unittest
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from helpers import BuildTest, read_json, write_json
from test_page_weight import typical_rows

from sitebuild import board_day_page
from sitework.layout import chrome, published, served

NEWEST, EARLIER, EMPTY = "2026-11-10", "2026-11-09", "2026-11-08"
"""The newest board, of twelve rows; an earlier board, of two of them; and the example's board with no rows."""

DESKTOP, LAPTOP, TABLET = 1440, 1024, 768
PHONES = ((390, 844), (360, 740))

LONG = (
    "A description long enough to need more than three lines on a card at any width, so that a card has to cut it, "
    "and an opened card has to show it whole: it says the same thing in more words than a card has room for, and "
    "then a little more, so that even the widest card the grid draws cannot hold it in three lines of its type."
)

CARDS = "#layout [data-layout=cards]"
LIST = '#layout [data-layout=""]'

SWITCH = """() => {
  const group = document.getElementById('layout');
  const toolbar = document.querySelector('.toolbar');
  const drawn = [...toolbar.children].filter(c => c.checkVisibility() && !c.classList.contains('sr'));
  return {
    shown: !!group && group.checkVisibility(),
    ids: drawn.map(c => c.id),
    tops: drawn.map(c => c.getBoundingClientRect().top),
    right: group ? group.getBoundingClientRect().right : null,
    toolbarRight: toolbar.getBoundingClientRect().right,
    role: group && group.getAttribute('role'),
    label: group && group.getAttribute('aria-label'),
    segments: !!group && group.classList.contains('segments'),
    buttons: [...(group ? group.querySelectorAll('button') : [])]
      .map(b => [b.textContent.trim(), b.getAttribute('aria-pressed')]),
  };
}"""
"""The switch: whether it is drawn, the ids of the filter's drawn controls in order and the tops of each, its right
edge and the filter's, its role and name, whether it takes the filter's segmented style, and each button's words and
whether it is pressed."""

ROWS = """() => {
  const table = document.querySelector('table.chart');
  const head = table.querySelector('thead');
  const body = table.querySelector('tbody').getBoundingClientRect();
  const box = element => {
    if (!element) return null;
    const r = element.getBoundingClientRect();
    return {left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height,
            fits: element.scrollWidth <= element.clientWidth + 1};
  };
  return {
    sideways: document.documentElement.scrollWidth - window.innerWidth,
    tableWidth: table.getBoundingClientRect().width,
    bodyWidth: body.width,
    headings: head.checkVisibility() && head.getBoundingClientRect().height > 1,
    rows: [...table.querySelectorAll(':scope > tbody > tr')].filter(row => row.checkVisibility()).map(row => {
      const look = getComputedStyle(row);
      return {
        name: row.querySelector('th.re a').textContent.trim(),
        ...box(row),
        inside: parseFloat(look.paddingRight) + parseFloat(look.borderRightWidth),
        rank: box(row.querySelector('td.rk')), repository: box(row.querySelector('th.re')),
        description: box(row.querySelector('td.de')), chevron: box(row.querySelector('td.wy summary')),
        gain: box(row.querySelector('td.gr')), pace: box(row.querySelector('td.pc')),
        stars: box(row.querySelector('td.st')),
      };
    }),
  };
}"""
"""How the board lies: how far the page reaches past the screen's right edge, the table's width and its body's,
whether the column headings are drawn, and each row it shows, in order: its name, its box, the room inside its right
edge, and the box of each of its parts, with whether each holds what it draws."""

SHOWN = """() => [...document.querySelectorAll('table.chart > tbody > tr')]
  .filter(row => row.checkVisibility())
  .map(row => row.querySelector('th.re a').textContent.trim())"""
"""The name of each row the board shows, in the order it shows them."""

LAID = """() => ({
  layout: document.documentElement.getAttribute('data-layout'),
  pressed: [...document.querySelectorAll('#layout button')].map(b => b.getAttribute('aria-pressed')),
})"""
"""The root's mark for the cards, and whether List and Cards are pressed."""


def lines(rows: list[dict]) -> list[list[dict]]:
    """The rows in the lines the board lays them out in, by the height of each one's top."""
    found: dict[int, list[dict]] = {}
    for row in rows:
        found.setdefault(round(row["top"]), []).append(row)
    return [found[top] for top in sorted(found)]


class CardTest(BuildTest):
    @classmethod
    def setUpClass(cls):
        """One build, served once and opened in one Chrome by every test: a build and a browser for each test made
        the pull request's job longer than it is given (#213). The newest board has twelve rows, so that it has a
        top three, a top ten, and ranks past them; its first row's language is "DIGITAL Command Language", the
        widest a board has shown; its second has a description longer than three lines of a card; and its third has
        no language. The earlier board lists two of them, so that it has a filter, and the newest's other rows are
        New. The example's board with no rows stays as it is."""
        shared = cls()
        shared.setUp()
        cls.addClassCleanup(shared.doCleanups)
        empty = read_json(shared.board_file(EMPTY))
        rows = typical_rows(12)
        rows[0]["language"] = "DIGITAL Command Language"
        rows[1]["description"] = LONG
        rows[2]["language"] = None
        cls.rows = rows
        earlier = [{**rows[4], "rank": 1}, {**rows[7], "rank": 2}]
        for day, held, at in ((NEWEST, rows, "2026-11-11T00:41:07Z"), (EARLIER, earlier, "2026-11-10T00:41:07Z")):
            write_json(
                shared.board_file(day),
                {
                    **empty,
                    "board_day": day,
                    "published_at": at,
                    "daily_job_started_at": at,
                    "state": "rows",
                    "rows": held,
                },
            )
        entries = [{"board_day": NEWEST, "row_count": 12}, {"board_day": EARLIER, "row_count": 2}]
        entries.append({"board_day": EMPTY, "row_count": 0})
        write_json(shared.index, {**read_json(shared.index), "board_days": entries})
        shared.build_pages()
        cls.built = shared.out
        cls.site = cls.enterClassContext(served(cls.built))
        cls.browser = cls.enterClassContext(chrome())

    def open(self, path: str = "index.html", width: int = DESKTOP, height: int = 900, query: str = "", context=None):
        """The page at `path`, with `query` as its address's query, on a screen `width` by `height` pixels, in a
        browser of its own or in `context`, with the clock at the newest board's publish time, once its type is in."""
        if context is None:
            page = self.browser.new_page(viewport={"width": width, "height": height})
        else:
            page = context.new_page()
        page.set_default_timeout(10_000)
        page.clock.set_fixed_time(datetime.fromisoformat(published(self.built)) + timedelta(minutes=5))
        page.goto(f"{self.site}/{path.removesuffix('index.html')}{query}", wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        return page

    def as_cards(self, page):
        """Press Cards, and give the page."""
        page.click(CARDS)
        return page


class TheSwitch(CardTest):
    def test_on_a_first_visit_the_filter_row_ends_in_list_and_cards_with_list_pressed(self):
        for path in ("index.html", board_day_page(EARLIER)):
            with self.subTest(path):
                page = self.open(path)
                seen = page.evaluate(SWITCH)
                self.assertTrue(seen["shown"], seen)
                self.assertEqual(seen["ids"][-1], "layout")
                self.assertAlmostEqual(seen["right"], seen["toolbarRight"], delta=1)
                self.assertEqual((seen["role"], seen["label"], seen["segments"]), ("group", "View", True))
                self.assertEqual(seen["buttons"], [["List", "true"], ["Cards", "false"]])
                self.assertIsNone(page.evaluate(LAID)["layout"])
                page.close()

    def test_at_1440_px_the_switch_ends_the_filters_one_line_on_a_board_listing_digital_command_language(self):
        page = self.open()
        self.assertIn("DIGITAL Command Language", page.locator("#language option").all_text_contents())
        seen = page.evaluate(SWITCH)
        self.assertEqual(seen["ids"], ["kinds", "bands", "language", "sort", "layout"])
        self.assertEqual(len({round(top) for top in seen["tops"]}), 1, seen)
        self.assertAlmostEqual(seen["right"], seen["toolbarRight"], delta=1)
        page.close()


class TheList(CardTest):
    def assertTheList(self, seen: dict, headings: bool):
        """Every row is laid out as the list lays it out: one to a line, as wide as the table."""
        self.assertTrue(seen["rows"])
        tops = [row["top"] for row in seen["rows"]]
        self.assertEqual(tops, sorted(tops))
        self.assertEqual(len({round(top) for top in tops}), len(tops), "one row to a line")
        for row in seen["rows"]:
            self.assertAlmostEqual(row["width"], seen["tableWidth"], delta=1, msg=row["name"])
        self.assertEqual(seen["headings"], headings)

    def test_on_a_first_visit_every_row_is_laid_out_as_the_list_was(self):
        for width, height in ((DESKTOP, 900), (TABLET, 900), *PHONES[:1]):
            with self.subTest(width=width):
                page = self.open(width=width, height=height)
                self.assertTheList(page.evaluate(ROWS), headings=width >= TABLET)
                page.close()

    def test_with_scripts_off_the_board_is_the_list_and_no_switch_shows_even_with_view_cards_in_the_address(self):
        for width, height in ((DESKTOP, 900), PHONES[0]):
            context = self.browser.new_context(viewport={"width": width, "height": height}, java_script_enabled=False)
            for query in ("", "?view=cards"):
                with self.subTest(width=width, query=query):
                    page = context.new_page()
                    page.goto(f"{self.site}/{query}", wait_until="load")
                    self.assertFalse(page.get_by_role("button", name="Cards").is_visible())
                    self.assertFalse(page.get_by_role("button", name="List").is_visible())
                    self.assertTheList(page.evaluate(ROWS), headings=width >= TABLET)
                    page.close()
            context.close()

    def test_a_board_with_no_rows_shows_no_switch_even_with_view_cards_in_the_address(self):
        for query in ("", "?view=cards"):
            with self.subTest(query=query):
                page = self.open(board_day_page(EMPTY), query=query)
                self.assertEqual(page.locator("table.chart").count(), 0)
                self.assertEqual(page.get_by_role("button", name="Cards").count(), 0)
                self.assertEqual(page.get_by_role("button", name="List").count(), 0)
                page.close()


class TheCards(CardTest):
    def test_with_cards_pressed_the_rows_lie_three_two_or_one_to_a_line_by_the_width_and_no_phone_scrolls_sideways(
        self,
    ):
        for width, height, across in (
            (DESKTOP, 900, 3),
            (LAPTOP, 768, 3),
            (TABLET, 900, 2),
            (*PHONES[0], 1),
            (*PHONES[1], 1),
        ):
            with self.subTest(width=width):
                page = self.as_cards(self.open(width=width, height=height))
                seen = page.evaluate(ROWS)
                laid = lines(seen["rows"])
                self.assertEqual(len(laid[0]), across, [len(line) for line in laid])
                self.assertTrue(all(len(line) <= across for line in laid))
                self.assertLessEqual(seen["sideways"], 0)
                for row in seen["rows"]:
                    for part in ("gain", "pace", "stars"):
                        self.assertTrue(row[part]["fits"], (row["name"], part, width))
                    self.assertLessEqual(row["gain"]["right"], row["pace"]["left"] + 0.5, row["name"])
                    self.assertLessEqual(row["pace"]["right"], row["stars"]["left"] + 0.5, row["name"])
                    self.assertLessEqual(row["stars"]["right"], row["right"] - row["inside"] + 0.5, row["name"])
                page.close()

    def test_each_card_holds_its_rank_language_name_description_and_line_of_figures_in_that_order(self):
        page = self.as_cards(self.open())
        page.select_option("#sort", "often")
        seen = page.evaluate(ROWS)
        drawn = page.evaluate(
            """() => [...document.querySelectorAll('table.chart > tbody > tr')].map(row => {
              const after = getComputedStyle(row, '::after');
              return {
                cells: [...row.children].filter(cell => cell.checkVisibility()).map(cell => cell.classList[0]),
                rank: row.querySelector('td.rk').textContent,
                hash: getComputedStyle(row.querySelector('td.rk'), '::before').content,
                language: row.getAttribute('data-l'),
                after: [after.content, after.gridColumnStart, after.gridRowStart, after.justifySelf],
                gain: getComputedStyle(row.querySelector('td.gr'), '::after').content,
                stars: getComputedStyle(row.querySelector('td.st'), '::after').content,
                often: !!row.querySelector('th.re .often') && row.querySelector('th.re .often').checkVisibility(),
                isNew: !!row.querySelector('th.re b.new') && row.querySelector('th.re b.new').checkVisibility(),
              };
            })"""
        )
        by_name = {row["full_name"]: row for row in self.rows}
        news = 0
        for row, card in zip(seen["rows"], drawn, strict=True):
            with self.subTest(row["name"]):
                self.assertEqual(card["cells"], ["rk", "re", "de", "wy", "gr", "pc", "st"])
                self.assertEqual(card["rank"], str(by_name[row["name"]]["rank"]))
                self.assertIn('"#"', card["hash"])
                self.assertLessEqual(row["rank"]["bottom"], row["repository"]["top"] + 0.5)
                self.assertLessEqual(row["repository"]["bottom"], row["description"]["top"] + 0.5)
                self.assertLessEqual(row["description"]["bottom"], row["gain"]["top"] + 0.5)
                self.assertAlmostEqual(row["gain"]["top"], row["pace"]["top"], delta=1)
                self.assertAlmostEqual(row["gain"]["top"], row["stars"]["top"], delta=1)
                self.assertLess(row["chevron"]["bottom"], row["repository"]["top"] + 0.5)
                self.assertAlmostEqual(row["chevron"]["right"], row["right"] - 10, delta=2)
                self.assertEqual(card["language"], by_name[row["name"]]["language"])
                self.assertEqual(card["after"][1:], ["language", "language", "end"])
                self.assertNotIn(card["after"][0], ("none", "normal"))
                self.assertEqual(card["gain"], '" on the day"')
                self.assertEqual(card["stars"], '" stars"')
                self.assertTrue(card["often"])
                news += card["isNew"]
        self.assertEqual(news, 10, "every row but the two the earlier board listed is New")
        page.close()

    def test_a_cards_rank_is_on_the_accent_for_the_top_three_in_it_for_the_top_ten_and_quiet_for_the_rest(self):
        page = self.as_cards(self.open())
        seen = page.evaluate(
            """() => {
              const ink = name => {
                const probe = document.createElement('i');
                probe.style.color = `var(${name})`;
                document.body.append(probe);
                const value = getComputedStyle(probe).color;
                probe.remove();
                return value;
              };
              const names = ['--accent', '--on-accent', '--raised', '--text-3'];
              const tokens = Object.fromEntries(names.map(n => [n, ink(n)]));
              const ranks = [...document.querySelectorAll('table.chart > tbody > tr > td.rk')].map(cell => {
                const look = getComputedStyle(cell);
                return [look.color, look.backgroundColor];
              });
              return {tokens, ranks};
            }"""
        )
        tokens, ranks = seen["tokens"], seen["ranks"]
        for rank, (colour, background) in enumerate(ranks, start=1):
            with self.subTest(rank=rank):
                if rank <= 3:
                    self.assertEqual((colour, background), (tokens["--on-accent"], tokens["--accent"]))
                elif rank <= 10:
                    self.assertEqual((colour, background), (tokens["--accent"], tokens["--raised"]))
                else:
                    self.assertEqual((colour, background), (tokens["--text-3"], tokens["--raised"]))
        page.close()

    def test_a_cards_description_takes_at_most_three_lines_and_an_opened_card_shows_it_whole(self):
        # On a phone a card is as wide opened as closed, so the long description takes more than three lines once
        # it is whole; the opened card on a desktop spans the grid, where it needs fewer.
        page = self.as_cards(self.open(width=PHONES[0][0], height=PHONES[0][1]))
        measure = """() => [...document.querySelectorAll('table.chart > tbody > tr > td.de')].map(cell => ({
          height: cell.getBoundingClientRect().height,
          line: parseFloat(getComputedStyle(cell).lineHeight),
          cut: cell.scrollHeight > cell.clientHeight + 1,
        }))"""
        for cell in page.evaluate(measure):
            self.assertLessEqual(round(cell["height"] / cell["line"]), 3, cell)
        long = page.evaluate(measure)[1]
        self.assertTrue(long["cut"], long)
        page.locator("table.chart > tbody > tr").nth(1).locator("td.de").click()
        page.wait_for_selector("table.chart > tbody > tr:nth-child(2) details[open]")
        opened = page.evaluate(measure)[1]
        self.assertGreater(round(opened["height"] / opened["line"]), 3, opened)
        self.assertFalse(opened["cut"], opened)
        page.close()

    def test_the_cards_of_a_line_are_of_one_height_and_their_figures_line_up(self):
        for width in (DESKTOP, TABLET):
            with self.subTest(width=width):
                page = self.as_cards(self.open(width=width))
                for line in lines(page.evaluate(ROWS)["rows"]):
                    heights = [row["height"] for row in line]
                    figures = [row["gain"]["top"] for row in line]
                    self.assertLessEqual(max(heights) - min(heights), 1, heights)
                    self.assertLessEqual(max(figures) - min(figures), 1, figures)
                page.close()

    def test_a_card_opens_across_the_whole_grid_on_what_a_row_opens_on_and_closes_back_into_its_place(self):
        page = self.as_cards(self.open())
        before = page.evaluate(ROWS)
        fifth = page.locator("table.chart > tbody > tr").nth(4)
        fifth.locator("td.de").click()
        page.wait_for_selector("table.chart > tbody > tr:nth-child(5) details[data-drawn]")
        opened = page.evaluate(ROWS)
        self.assertAlmostEqual(opened["rows"][4]["width"], opened["bodyWidth"], delta=1)
        for was, now in zip(before["rows"][:4], opened["rows"][:4], strict=True):
            self.assertAlmostEqual(was["left"], now["left"], delta=1)
            self.assertAlmostEqual(was["top"], now["top"], delta=1)
        self.assertTrue(fifth.locator(".op .rs .ln").inner_text().strip())
        self.assertTrue(fifth.locator(".op .su").inner_text().strip())
        self.assertTrue(fifth.locator(".op .fa").is_visible())
        fifth.locator("td.de").click()
        self.assertFalse(fifth.locator("details").evaluate("details => details.open"))
        closed = page.evaluate(ROWS)
        for key in ("left", "top", "width", "height"):
            self.assertAlmostEqual(closed["rows"][4][key], before["rows"][4][key], delta=1, msg=key)
        page.close()

    def test_the_keyboard_opens_a_card_from_its_chevron_which_shows_its_ring(self):
        page = self.as_cards(self.open())
        chevron = "table.chart > tbody > tr:first-child td.wy summary"
        for _ in range(12):
            page.keyboard.press("Tab")
            if page.evaluate(f"() => document.activeElement.matches('{chevron}')"):
                break
        ring = page.evaluate(
            """() => { const look = getComputedStyle(document.activeElement);
              return look.outlineStyle !== 'none' && parseFloat(look.outlineWidth) > 0; }"""
        )
        self.assertTrue(page.evaluate(f"() => document.activeElement.matches('{chevron}')"))
        self.assertTrue(ring)
        page.keyboard.press("Enter")
        page.wait_for_selector("table.chart > tbody > tr:first-child details[open]")
        page.close()

    def test_each_filter_order_and_search_gives_the_cards_the_rows_and_the_order_the_list_gives(self):
        probe = self.open()
        bands = probe.eval_on_selector_all("#bands button[data-word]:not([hidden])", "b => b.map(x => x.dataset.word)")
        languages = probe.eval_on_selector_all("#language option", "o => o.map(x => x.value).filter(Boolean)")
        probe.close()
        word = self.rows[5]["full_name"].split("/")[1].split("-")[0]
        queries = ["?show=new", *[f"?band={b}" for b in bands], *[f"?lang={language}" for language in languages]]
        queries += [f"?sort={order}" for order in ("gained", "often", "small", "large")] + [f"?q={word}"]
        context = self.browser.new_context(viewport={"width": DESKTOP, "height": 900})
        for query in queries:
            with self.subTest(query=query):
                page = self.open(query=query, context=context)
                if page.evaluate(LAID)["layout"]:
                    page.click(LIST)
                listed = page.evaluate(SHOWN)
                self.assertTrue(listed or query.startswith("?band"))
                page.click(CARDS)
                self.assertEqual(page.evaluate(SHOWN), listed)
                page.close()
        with self.subTest("Clear search and filters"):
            page = self.open(query="?q=zzzzzzzzzz&sort=small", context=context)
            self.assertEqual(page.evaluate(LAID)["layout"], "cards")
            self.assertEqual(page.evaluate(SHOWN), [])
            page.click("#none-shown button")
            cleared = page.evaluate(SHOWN)
            page.click(LIST)
            self.assertEqual(cleared, page.evaluate(SHOWN))
            self.assertEqual(len(cleared), 12)
            page.close()
        context.close()


class TheChoice(CardTest):
    def test_a_press_of_cards_puts_view_cards_in_the_address_and_the_links_to_other_board_days_and_list_takes_it_out(
        self,
    ):
        links = "[rel=prev], [rel=next], .latest, .earlier a"

        def queries(page) -> list[dict]:
            hrefs = [*page.eval_on_selector_all(links, "a => a.map(x => x.getAttribute('href'))"), page.url]
            return [parse_qs(urlparse(href).query) for href in hrefs]

        page = self.open(board_day_page(EARLIER), query="?sort=gained")
        page.click(CARDS)
        for query in queries(page):
            self.assertEqual(query.get("view"), ["cards"], query)
            self.assertEqual(query.get("sort"), ["gained"], query)
        page.reload(wait_until="load")
        self.assertEqual(page.evaluate(LAID), {"layout": "cards", "pressed": ["false", "true"]})
        page.click(LIST)
        for query in queries(page):
            self.assertNotIn("view", query)
            self.assertEqual(query.get("sort"), ["gained"], query)
        self.assertEqual(page.evaluate(LAID), {"layout": None, "pressed": ["true", "false"]})
        page.close()

    def test_a_choice_of_cards_is_kept_in_this_browser_and_a_press_of_list_clears_it(self):
        context = self.browser.new_context(viewport={"width": DESKTOP, "height": 900})
        first = self.as_cards(self.open(context=context))
        self.assertEqual(first.evaluate("() => localStorage.getItem('layout')"), "cards")
        first.close()
        again = self.open(context=context)
        self.assertEqual(urlparse(again.url).query, "")
        self.assertEqual(again.evaluate(LAID), {"layout": "cards", "pressed": ["false", "true"]})
        again.click(LIST)
        self.assertIsNone(again.evaluate("() => localStorage.getItem('layout')"))
        again.close()
        last = self.open(context=context)
        self.assertEqual(last.evaluate(LAID), {"layout": None, "pressed": ["true", "false"]})
        last.close()
        context.close()


if __name__ == "__main__":
    unittest.main()
