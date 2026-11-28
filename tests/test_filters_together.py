"""A board's filters, its search, and its order, used together (#41).

A reader narrows a board four ways at once: all rows or the new ones, one star band, one language, and the words
of a search, and puts what is left in one of five orders. The view is kept in the page's address. The owner's
sentences hold each of these by itself, and sentence 16 reopens four addresses of one filter each. Nothing held
them together, or a board on which no row matches.

So these try every pairing of a small set of values for each, 420 views and more, in the Chrome the machine
already has, and hold each to the rule a reader would state: a row shows when every filter and every word lets it
by. What a row is, its band, its language, its words, whether it is new, is read from the page as built, and the
rule is worked out here from that, so the script's own reading of a row is not what it is checked against.

The views are set through the address, as a shared link sets them, without a new page for each: the address is
changed in place and the page is told that it moved, which is what Back and Forward do.
"""

import itertools
import unittest
from datetime import date, timedelta
from urllib.parse import parse_qsl, urlencode

from helpers import BuildTest, read_json, write_json

from sitework.layout import chrome, published, served

NEWEST, OLDER = "2026-11-09", "2026-11-08"

FACTS = """() => ({
  rows: [...document.querySelectorAll("table.chart > tbody > tr")].map((row) => ({
    rank: row.querySelector("td.rk").textContent.trim(),
    words: (row.querySelector(".re a").textContent + " " +
      (row.querySelector(".de").classList.contains("none") ? "" : row.querySelector(".de").textContent)).toLowerCase(),
    stars: Number(row.querySelector(".st").textContent.replace(/\\D/g, "")),
    language: row.getAttribute("data-l") || "",
    fresh: !!row.querySelector(".re .new"),
    often: Number(row.getAttribute("data-o")) || 0,
  })),
  bands: [...document.querySelectorAll("#bands button[data-below]")].map((button) => ({
    word: button.getAttribute("data-word"),
    label: button.textContent.trim(),
    below: button.getAttribute("data-below") ? Number(button.getAttribute("data-below")) : null,
    held: button.hidden,
  })),
  languages: [...document.querySelectorAll("#language option")].map((option) => option.value).filter(Boolean),
})"""
"""What the page as built says of each row, of each star band, and of each language a reader may choose."""

SEEN = """() => ({
  shown: [...document.querySelectorAll("table.chart > tbody > tr")].filter((row) => !row.hidden)
    .map((row) => row.querySelector("td.rk").textContent.trim()),
  said: !document.getElementById("none-shown").hidden,
  search: location.search,
})"""
"""The ranks of the rows shown, in the order shown, whether the line that says nothing matches is shown, and the
address's query."""

MOVE = """(search) => {
  history.pushState(null, "", location.pathname + search);
  dispatchEvent(new PopStateEvent("popstate"));
}"""
"""Change the address in place and tell the page it moved, as Back and Forward do."""

SAID = """() => {
  const none = document.getElementById("none-shown");
  return {
    said: !none.hidden,
    line: (none.querySelector("p") || none).textContent.trim(),
    controls: [...none.querySelectorAll("a, button, input, select, textarea, [tabindex]")]
      .map((control) => [control.tagName.toLowerCase(), control.textContent.trim()]),
  };
}"""
"""Whether the line that says nothing matches is shown, its words, and each control it offers, by its tag and its
name."""

CONTROLS = """() => ({
  kinds: [...document.querySelectorAll("#kinds button")].map((button) => button.getAttribute("aria-pressed")),
  bands: [...document.querySelectorAll("#bands button")].map((button) => button.getAttribute("aria-pressed")),
  language: document.getElementById("language").value,
  sort: document.getElementById("sort").value,
  q: document.getElementById("q").value,
})"""
"""Where each control of the filter stands: which buttons are pressed, the language, the order, and the search."""

ON_ALL = """() => document.activeElement === document.querySelector('#kinds button[data-kind=""]')"""
"""Whether the keyboard is on the All button."""

NOTHING = "No repository on this board matches"
CLEAR = "Clear search and filters"


class ABoardAndAnEarlierOne(BuildTest):
    """The example's newest board, open at the root, and an earlier board, OLDER, with two of its rows."""

    def setUp(self):
        super().setUp()
        # The example's older board lists two of the newest board's five rows, so the other three are new.
        rows = read_json(self.board_file())["rows"]
        older = read_json(self.board_file(OLDER))
        self.write_board({**older, "state": "rows", "rows": [rows[1], rows[3]]})
        self.build_pages()
        self.site = self.enterContext(served(self.out))
        self.browser = self.enterContext(chrome())
        self.page = self.board()
        self.facts = self.page.evaluate(FACTS)
        # The views below mean something only on a board whose rows differ in each way a view can choose.
        rows = self.facts["rows"]
        self.assertEqual(len(rows), 5)
        self.assertEqual(sorted(row["fresh"] for row in rows), [False, False, True, True, True])
        self.assertGreater(len({self.band_of(row["stars"]) for row in rows}), 2)
        self.assertGreater(len({row["language"] for row in rows}), 3)

    def board(self, search: str = ""):
        page = self.browser.new_page(viewport={"width": 1440, "height": 900})
        page.clock.set_fixed_time(published(self.out))
        page.goto(self.site + search, wait_until="load")
        return page

    def view(self, **chosen: str) -> dict:
        """What the page shows with these in its address."""
        self.page.evaluate(MOVE, "?" + urlencode(chosen) if chosen else "")
        return self.page.evaluate(SEEN)

    def band_of(self, stars: int) -> str:
        """The word of the star band a count falls in: the first band that stops above it."""
        return next(band["word"] for band in self.facts["bands"] if band["below"] is None or stars < band["below"])


class TheFiltersTogether(ABoardAndAnEarlierOne):
    def lets_by(self, row: dict, show: str = "", band: str = "", lang: str = "", q: str = "", **_) -> bool:
        """Whether a row shows, by the rule: each filter that names something the board has lets by the rows that
        are that, a value the board does not have is no filter, and every word of the search is in the row's name
        or its description."""
        bands = [one["word"] for one in self.facts["bands"] if not one["held"]]
        language = next((one for one in self.facts["languages"] if one.lower() == lang.lower()), "")
        return (
            (show != "new" or row["fresh"])
            and (band not in bands or self.band_of(row["stars"]) == band)
            and (not language or row["language"] == language)
            and all(word in row["words"] for word in q.lower().split())
        )

    def values(self) -> dict[str, list[str]]:
        """A few values for each part of a view: none, each the board has, and one it does not have."""
        facts = self.facts
        return {
            "show": ["", "new", "old"],
            "band": ["", *(band["word"] for band in facts["bands"]), "9k-10k"],
            "lang": ["", "Rust", "rust", "Go", "COBOL"],
            "q": ["", "octocat", "octocat world", "no-such-word"],
        }

    def test_a_row_shows_when_every_filter_and_every_word_of_the_search_lets_it_by_whatever_is_chosen_together(self):
        values = self.values()
        tried = 0
        for chosen in itertools.product(*values.values()):
            view = {name: value for name, value in zip(values, chosen, strict=True) if value}
            with self.subTest(**view):
                expected = [row["rank"] for row in self.facts["rows"] if self.lets_by(row, **view)]
                self.assertEqual(self.view(**view)["shown"], expected)
                tried += 1
        self.assertGreater(tried, 400)

    def test_the_line_that_says_nothing_matches_is_shown_when_no_row_is_and_only_then(self):
        values = self.values()
        said = set()
        for chosen in itertools.product(*values.values()):
            view = {name: value for name, value in zip(values, chosen, strict=True) if value}
            with self.subTest(**view):
                seen = self.view(**view)
                self.assertEqual(seen["said"], not seen["shown"])
                said.add(seen["said"])
        self.assertEqual(said, {True, False})

    def said(self, show: str = "", band: str = "", lang: str = "", q: str = "", **_) -> str:
        """The line a view that matches nothing is to show, by #33's plan: each part of the view that is chosen,
        named by what its control shows, and a value the board does not hold named nowhere."""
        chosen = ["New"] if show == "new" else []
        labels = {one["word"]: one["label"] for one in self.facts["bands"] if not one["held"]}
        if band in labels:
            chosen.append(f"{labels[band]} stars")
        chosen += [one for one in self.facts["languages"] if one.lower() == lang.lower()]
        listed = {1: "{}", 2: "{} and {}", 3: "{}, {}, and {}"}.get(len(chosen), "").format(*chosen)
        if q.split():
            return f"{NOTHING} the search among {listed}." if chosen else f"{NOTHING} the search."
        return f"{NOTHING} the {'filter' if len(chosen) == 1 else 'filters'}: {listed}."

    def empty_views(self):
        """Each view of `values` that leaves no row shown."""
        values = self.values()
        for chosen in itertools.product(*values.values()):
            view = {name: value for name, value in zip(values, chosen, strict=True) if value}
            if not any(self.lets_by(row, **view) for row in self.facts["rows"]):
                yield view

    def clear(self):
        """Press "Clear search and filters", failing at once where the line offers no such button."""
        button = self.page.locator("#none-shown").get_by_role("button", name=CLEAR)
        self.assertEqual(button.count(), 1, "the line offers no button to clear the view")
        button.click()

    def test_the_line_that_says_nothing_matches_names_each_part_of_the_view_that_is_chosen_and_no_other(self):
        forms = set()
        for view in self.empty_views():
            with self.subTest(**view):
                self.view(**view)
                said = self.page.evaluate(SAID)
                self.assertEqual(said["line"], self.said(**view))
                forms.add(said["line"].removeprefix(NOTHING).split()[1])
        # Each form of the line is met: a search alone, a search among filters, and one filter or more alone.
        self.assertEqual(forms, {"search.", "search", "filter:", "filters:"})

    def test_the_line_that_says_nothing_matches_offers_one_control_clear_search_and_filters(self):
        for view in ({"q": "no-such-word"}, {"show": "new", "lang": "Rust", "q": "octocat"}):
            with self.subTest(**view):
                self.view(**view)
                said = self.page.evaluate(SAID)
                self.assertTrue(said["said"])
                self.assertEqual(said["controls"], [["button", CLEAR]])
                self.assertEqual(self.page.locator("#none-shown").get_by_role("button", name=CLEAR).count(), 1)

    def test_clear_search_and_filters_shows_every_row_and_sets_each_control_back_whatever_was_chosen(self):
        everything = [row["rank"] for row in self.facts["rows"]]
        self.view()
        unchosen = self.page.evaluate(CONTROLS)
        tried = 0
        for view in self.empty_views():
            with self.subTest(**view):
                self.view(**view)
                self.clear()
                self.assertEqual(self.page.evaluate(SEEN)["shown"], everything)
                self.assertEqual(self.page.evaluate(CONTROLS), unchosen)
                self.assertFalse(self.page.evaluate(SAID)["said"])
                tried += 1
        self.assertGreater(tried, 50)

    def test_clear_search_and_filters_keeps_the_order_the_reader_chose(self):
        ordered = [row["rank"] for row in sorted(self.facts["rows"], key=lambda row: -row["stars"])]
        self.view(sort="large", show="new", q="no-such-word")
        self.clear()
        self.assertEqual(self.page.evaluate(CONTROLS)["sort"], "large")
        self.assertEqual(self.page.evaluate(SEEN)["shown"], ordered)

    def test_clear_search_and_filters_leaves_only_the_order_in_the_address_as_a_new_entry(self):
        band = next(one["word"] for one in self.facts["bands"] if not one["held"])
        for view, left in (
            ({"show": "new", "band": band, "lang": "Rust", "sort": "large", "q": "no-such-word"}, "?sort=large"),
            ({"band": band, "q": "no-such-word"}, ""),
        ):
            with self.subTest(**view):
                self.view(**view)
                entries = self.page.evaluate("history.length")
                self.clear()
                self.assertEqual(self.page.evaluate(SEEN)["search"], left)
                self.assertEqual(self.page.evaluate("history.length"), entries + 1)

    def test_back_after_clear_search_and_filters_returns_the_view_that_matched_nothing(self):
        band = next(one["word"] for one in self.facts["bands"] if not one["held"])
        self.view(show="new", band=band, lang="Rust", sort="small", q="no-such-word")
        before = [self.page.evaluate(SEEN), self.page.evaluate(CONTROLS), self.page.evaluate(SAID)]
        self.assertTrue(before[2]["said"])
        self.clear()
        self.page.evaluate("history.back()")
        self.page.wait_for_function("(search) => location.search === search", arg=before[0]["search"])
        self.assertEqual([self.page.evaluate(SEEN), self.page.evaluate(CONTROLS), self.page.evaluate(SAID)], before)

    def test_after_clear_search_and_filters_the_keyboard_is_on_the_all_button(self):
        self.view(lang="Rust", q="no-such-word")
        self.page.locator("#none-shown").get_by_role("button", name=CLEAR).focus()
        self.page.keyboard.press("Enter")
        self.assertFalse(self.page.evaluate(SAID)["said"])
        self.assertTrue(self.page.evaluate(ON_ALL))

    def test_an_order_moves_the_rows_and_changes_no_rank_and_rows_that_tie_keep_their_rank_order(self):
        rows = self.facts["rows"]
        keys = {
            "": lambda row: 0,
            "small": lambda row: row["stars"],
            "large": lambda row: -row["stars"],
            "often": lambda row: -row["often"],
            "sideways": lambda row: 0,
        }
        for (sort, key), show, q in itertools.product(keys.items(), ["", "new"], ["", "octocat"]):
            view = {name: value for name, value in (("sort", sort), ("show", show), ("q", q)) if value}
            with self.subTest(**view):
                # Python's sort keeps rows that tie in the order they came, which is their rank order.
                ordered = sorted((row for row in rows if self.lets_by(row, **view)), key=key)
                self.assertEqual(self.view(**view)["shown"], [row["rank"] for row in ordered])

    def test_a_view_chosen_with_the_controls_is_kept_in_the_address_without_what_was_left_as_it_was(self):
        page = self.page
        self.view()
        page.locator("#kinds button[data-kind=new]").click()
        page.locator("#language").select_option("Rust")
        page.locator("#sort").select_option("large")
        chosen = page.evaluate(SEEN)
        # Each thing chosen is in the address, and the band and the search, left as they were, are not.
        self.assertEqual(
            dict(parse_qsl(chosen["search"].lstrip("?"))), {"show": "new", "lang": "Rust", "sort": "large"}
        )
        again = self.board(chosen["search"])
        self.assertEqual(again.evaluate(SEEN)["shown"], chosen["shown"])
        self.assertEqual(
            chosen["shown"], [row["rank"] for row in self.facts["rows"] if self.lets_by(row, show="new", lang="Rust")]
        )


LINKS = """() => [...document.querySelectorAll(
  ".strip a[rel=prev], .strip a[rel=next], .strip a.latest, p.earlier a, " +
  "nav.foot-links a[rel=prev], nav.foot-links a[rel=next]"
)].map((a) => a.getAttribute("href"))"""
"""Each of a board's links to another board day, as its address is written, in the page's order: the day bar's
previous, next, and Latest links, the earlier-board note's link to the newest board, and the foot's previous and
next links. As written, so that a bare "?" on a plain address is told from the address itself."""

CHOSEN = """() => ({
  show: (document.querySelector('#kinds button[aria-pressed="true"]') || {}).getAttribute?.("data-kind") || "",
  band: (document.querySelector('#bands button[aria-pressed="true"]') || {}).getAttribute?.("data-word") || "",
  lang: document.getElementById("language").value,
  sort: document.getElementById("sort").value,
  q: document.getElementById("q").value,
})"""
"""What each control of the filter shows chosen: the kind and the band pressed, by their words in the address, the
language, the order, and the search."""

ADDRESS = "() => location.pathname + location.search"

EARLIER = f"/days/{OLDER}/"


class TheLinksToOtherBoardDays(ABoardAndAnEarlierOne):
    """A board's links to the board day before and after it, to the newest, and the earlier-board note's link carry
    the filters and the order chosen, and never the search, so that stepping a day keeps the view (#148). The owner
    chose on 26 November 2026 that the search's words stay out of the links, so that P22 holds whole: they come from
    the address or the reader's typing, and are written nowhere in the page.

    The root has a previous link, in the day bar and at the foot, and the earlier board has a next link in each,
    Latest, and the note. The root holds back the 1k-3k band, and the earlier board has HTML alone and no New."""

    def plain(self, path: str) -> list[str]:
        """The links of a board as the build wrote them, read with scripts off."""
        page = self.browser.new_page(viewport={"width": 1440, "height": 900}, java_script_enabled=False)
        page.goto(self.site + path, wait_until="load")
        links = page.evaluate(LINKS)
        page.close()
        return links

    def choose(self, page, show: str = "", band: str = "", lang: str = "", sort: str = "") -> None:
        """Choose a view with the controls, as a reader does."""
        if show:
            page.locator(f'#kinds button[data-kind="{show}"]').click()
        if band:
            page.locator(f'#bands button[data-word="{band}"]').click()
        if lang:
            page.locator("#language").select_option(lang)
        if sort:
            page.locator("#sort").select_option(sort)

    def test_each_link_to_another_board_day_carries_the_filters_and_order_chosen_with_the_controls_in_any_combination(
        self,
    ):
        values = {
            "/": {"show": "new", "band": "3k-10k", "lang": "Rust", "sort": "large"},
            EARLIER: {"band": "10k-30k", "lang": "HTML", "sort": "small"},
        }
        for path, these in values.items():
            plain = self.plain(path)
            for size in range(1, len(these) + 1):
                for names in itertools.combinations(these, size):
                    chosen = {name: these[name] for name in names}
                    with self.subTest(path=path, **chosen):
                        page = self.board(path)
                        self.choose(page, **chosen)
                        search = page.evaluate("() => location.search")
                        self.assertEqual(dict(parse_qsl(search.lstrip("?"))), chosen)
                        # Exactly the query the address holds, each on its own link's path.
                        self.assertEqual(page.evaluate(LINKS), [link + search for link in plain])
                        page.close()

    def test_no_link_to_another_board_day_carries_the_search_alone_or_with_the_filters(self):
        plain = self.plain("/")
        page = self.board()
        page.get_by_role("searchbox").fill("octocat")
        self.assertEqual(page.evaluate("() => location.search"), "?q=octocat")
        self.assertEqual(page.evaluate(LINKS), plain)
        self.choose(page, lang="Rust", sort="large")
        self.assertEqual(page.evaluate("() => location.search"), "?lang=Rust&sort=large&q=octocat")
        self.assertEqual(page.evaluate(LINKS), [link + "?lang=Rust&sort=large" for link in plain])
        # A search typed after the filters are chosen is left out as well.
        page = self.board()
        self.choose(page, show="new")
        page.get_by_role("searchbox").fill("octocat")
        self.assertEqual(page.evaluate("() => location.search"), "?show=new&q=octocat")
        self.assertEqual(page.evaluate(LINKS), [link + "?show=new" for link in plain])

    def test_a_board_opened_at_an_address_that_holds_a_view_gives_each_link_to_another_board_day_its_filters_and_order(
        self,
    ):
        for path, opened, carried in [
            ("/", "?show=new&band=3k-10k&lang=Rust&sort=large", "?show=new&band=3k-10k&lang=Rust&sort=large"),
            # The language is carried as the board writes it, and the search not at all.
            ("/", "?sort=often&q=octocat&lang=rust", "?lang=Rust&sort=often"),
            (EARLIER, "?lang=HTML&q=octocat", "?lang=HTML"),
        ]:
            with self.subTest(path=path, opened=opened):
                plain = self.plain(path)
                page = self.board(path + opened)
                self.assertEqual(page.evaluate(LINKS), [link + carried for link in plain])

    def test_following_previous_next_or_latest_opens_that_board_with_the_same_filters_and_order_and_an_empty_search(
        self,
    ):
        for start, link, lands in [
            ("/", ".strip a[rel=prev]", EARLIER),
            ("/", "nav.foot-links a[rel=prev]", EARLIER),
            (EARLIER, ".strip a[rel=next]", "/days/2026-11-09/"),
            (EARLIER, "nav.foot-links a[rel=next]", "/days/2026-11-09/"),
            (EARLIER, ".strip a.latest", "/"),
        ]:
            with self.subTest(start=start, link=link):
                page = self.board(start + "?band=10k-30k&lang=HTML&sort=small&q=octocat")
                with page.expect_navigation(wait_until="load"):
                    page.locator(link).click()
                self.assertEqual(page.evaluate(ADDRESS), lands + "?band=10k-30k&lang=HTML&sort=small")
                self.assertEqual(
                    page.evaluate(CHOSEN), {"show": "", "band": "10k-30k", "lang": "HTML", "sort": "small", "q": ""}
                )
                # The rows that are HTML and in the 10k-30k band, fewest stars first.
                rows = page.evaluate(FACTS)["rows"]
                fits = [row for row in rows if row["language"] == "HTML" and self.band_of(row["stars"]) == "10k-30k"]
                shown = page.evaluate(SEEN)["shown"]
                self.assertEqual(shown, [row["rank"] for row in sorted(fits, key=lambda row: row["stars"])])
                self.assertLess(len(shown), len(rows))

    def test_with_the_default_view_each_link_to_another_board_day_has_no_query(self):
        for path in ["/", EARLIER]:
            with self.subTest(path=path):
                plain = self.plain(path)
                self.assertTrue(plain)
                self.assertFalse([link for link in plain if "?" in link])
                page = self.board(path)
                self.assertEqual(page.evaluate(LINKS), plain)
                # A view chosen, and then cleared with the order left at rank.
                self.choose(page, lang="HTML")
                page.get_by_role("searchbox").fill("no repository is called this")
                self.assertEqual(page.evaluate(LINKS), [link + "?lang=HTML" for link in plain])
                page.locator("#none-shown").get_by_role("button", name=CLEAR).click()
                self.assertEqual(page.evaluate("() => location.search"), "")
                self.assertEqual(page.evaluate(LINKS), plain)

    def test_a_value_the_board_does_not_hold_is_not_carried_by_its_links(self):
        for path, opened, carried in [
            ("/", "?lang=Cobol", ""),
            ("/", "?band=1k-3k", ""),
            ("/", "?sort=sideways", ""),
            ("/", "?band=1k-3k&lang=Cobol&sort=large", "?sort=large"),
            (EARLIER, "?show=new&lang=Rust", ""),
            (EARLIER, "?show=new&lang=Rust&band=3k-10k", "?band=3k-10k"),
        ]:
            with self.subTest(path=path, opened=opened):
                plain = self.plain(path)
                page = self.board(path + opened)
                self.assertEqual(page.evaluate(LINKS), [link + carried for link in plain])

    def test_back_and_forward_give_the_links_the_view_they_return(self):
        plain = self.plain("/")
        page = self.board()
        self.choose(page, lang="Rust")
        self.choose(page, sort="large")
        self.assertEqual(page.evaluate(LINKS), [link + "?lang=Rust&sort=large" for link in plain])
        page.go_back()
        self.assertEqual(page.evaluate(LINKS), [link + "?lang=Rust" for link in plain])
        page.go_forward()
        self.assertEqual(page.evaluate(LINKS), [link + "?lang=Rust&sort=large" for link in plain])

    def test_back_and_forward_walk_the_views_chosen_one_entry_each(self):
        page = self.board()
        everything = page.evaluate(SEEN)
        self.choose(page, lang="Rust")
        first = page.evaluate(SEEN)
        self.choose(page, sort="large")
        second = page.evaluate(SEEN)
        self.assertEqual([first["search"], second["search"]], ["?lang=Rust", "?lang=Rust&sort=large"])
        page.go_back()
        self.assertEqual(page.evaluate(SEEN), first)
        page.go_back()
        self.assertEqual(page.evaluate(SEEN), everything)
        page.go_forward()
        self.assertEqual(page.evaluate(SEEN), first)
        page.go_forward()
        self.assertEqual(page.evaluate(SEEN), second)


SAID_BY_ROWS = """() => [...document.querySelectorAll("table.chart > tbody > tr")].filter((row) => !row.hidden)
  .map((row) => [
    row.querySelector(".re a").textContent,
    row.querySelector("th.re").innerText.split(/\\s+/).join(" "),
  ])"""
"""For each row shown, in the order shown: its link's text, and its row header's text as a reader sees it."""

INSIDE = """() => ({
  counts: [...document.querySelectorAll("table.chart > tbody > tr")].map((row) => {
    const box = row.getBoundingClientRect(), count = row.querySelector(".re .often").getBoundingClientRect();
    return count.width > 0 && count.left >= box.left && count.right <= box.right && count.top >= box.top &&
      count.bottom <= box.bottom;
  }),
  sideways: document.documentElement.scrollWidth > document.documentElement.clientWidth,
})"""
"""Whether each row's count is drawn inside its row, and whether the page scrolls sideways."""

LONG = "antigravity-cn-community/Antigravity-Chinese-Localization"


class TheOftenCount(BuildTest):
    """With "Most often in 14 boards" chosen, each row says the count the order sorts it by, "on 8 of 14 boards",
    after its name (#186). The board is the example's newest with 13 boards before it, a day apart, so that its order
    counts 14. Its first row is on none of the earlier boards, and so is new; its second is on the 3 boards before it,
    its third on the 6, its fourth, given a long name, on the 9, and its fifth on all 13. The earlier boards stand for
    the site's first 13 board days, whose order counts fewer boards: the board `back` days before the newest counts
    14 - `back`."""

    ON = [1, 4, 7, 10, 14]
    """How many of the 14 boards list each row of the newest, in its order."""

    def setUp(self):
        super().setUp()
        board = read_json(self.board_file())
        rows = board["rows"]
        rows[1] = {**rows[1], "description": "Keeps a team's boards in one place."}
        rows[3] = {**rows[3], "full_name": LONG}
        self.write_board(board)
        older = read_json(self.board_file(OLDER))
        newest = date.fromisoformat(NEWEST)
        for back in range(1, 14):
            day = (newest - timedelta(days=back)).isoformat()
            listed = [row for i, row in enumerate(rows) if i == 4 or back <= 3 * i]
            listed = [{**row, "rank": rank} for rank, row in enumerate(listed, 1)]
            index = read_json(self.index)
            kept = [entry for entry in index["board_days"] if entry["board_day"] != day]
            entries = [*kept, {"board_day": day, "row_count": len(listed)}]
            write_json(self.index, {**index, "board_days": sorted(entries, key=lambda e: e["board_day"], reverse=True)})
            published_at = f"{(newest - timedelta(days=back - 1)).isoformat()}T00:38:52Z"
            self.write_board({**older, "board_day": day, "published_at": published_at, "state": "rows", "rows": listed})
        self.rows = rows
        self.build_pages()
        self.site = self.enterContext(served(self.out))
        self.browser = self.enterContext(chrome())

    def board(self, search: str = "", path: str = "/", width: int = 1440, height: int = 900):
        page = self.browser.new_page(viewport={"width": width, "height": height})
        page.clock.set_fixed_time(published(self.out))
        page.goto(self.site + path + search, wait_until="load")
        return page

    def plain(self, row: int) -> list[str]:
        """What the newest board's row `row` shows in any order but "Most often": its link's text, and its header's,
        which is its name, with New after it on the first row."""
        name = self.rows[row]["full_name"]
        return [name, name + (" New" if row == 0 else "")]

    def counted(self, row: int) -> list[str]:
        """What the newest board's row `row` shows with "Most often in 14 boards" chosen."""
        name, said = self.plain(row)
        return [name, f"{said} on {self.ON[row]} of 14 boards"]

    def most_often_first(self) -> list[list[str]]:
        """Every row of the newest board, most often first, each with its count."""
        return [self.counted(row) for row in (4, 3, 2, 1, 0)]

    def none_counted(self) -> list[list[str]]:
        return sorted(self.plain(row) for row in range(5))

    def test_with_most_often_chosen_every_row_shown_says_on_how_many_of_the_last_14_boards_it_was_after_its_name(self):
        page = self.board()
        self.assertEqual(page.evaluate(SAID_BY_ROWS), [self.plain(row) for row in range(5)])
        page.locator("#sort").select_option("often")
        self.assertEqual(page.evaluate(SAID_BY_ROWS), self.most_often_first())

    def test_a_board_opened_with_the_most_often_order_in_its_address_shows_each_rows_count_at_once(self):
        page = self.board("?sort=often")
        self.assertEqual(page.evaluate(SAID_BY_ROWS), self.most_often_first())

    def test_in_every_other_order_no_count_is_shown_and_choosing_most_often_again_shows_them_again(self):
        page = self.board("?sort=often")
        for order in ("rank", "gained", "small", "large"):
            with self.subTest(order=order):
                page.locator("#sort").select_option(order)
                self.assertEqual(sorted(page.evaluate(SAID_BY_ROWS)), self.none_counted())
                page.locator("#sort").select_option("often")
                self.assertEqual(page.evaluate(SAID_BY_ROWS), self.most_often_first())
        # Back from the counts to a view in another order, and Forward to them again.
        page = self.board("?sort=large")
        page.locator("#sort").select_option("often")
        page.go_back()
        self.assertEqual(sorted(page.evaluate(SAID_BY_ROWS)), self.none_counted())
        page.go_forward()
        self.assertEqual(page.evaluate(SAID_BY_ROWS), self.most_often_first())

    def test_with_most_often_chosen_a_row_a_filter_or_a_search_shows_later_says_its_count_too(self):
        language = self.rows[0]["language"]
        speaks = [row for row in (4, 3, 2, 1, 0) if self.rows[row]["language"] == language]
        self.assertLess(len(speaks), 5)
        for opened, shown, widen in [
            ("?sort=often&show=new", [0], lambda page: page.locator('#kinds button[data-kind=""]').click()),
            ("?sort=often&q=text-beyond-ascii", [2], lambda page: page.get_by_role("searchbox").fill("")),
            (f"?sort=often&lang={language}", speaks, lambda page: page.locator("#language").select_option("")),
        ]:
            with self.subTest(opened=opened):
                page = self.board(opened)
                self.assertEqual(page.evaluate(SAID_BY_ROWS), [self.counted(row) for row in shown])
                widen(page)
                self.assertEqual(page.evaluate(SAID_BY_ROWS), self.most_often_first())

    def test_on_a_board_with_fewer_than_13_boards_before_it_the_count_says_how_many_boards_it_counted(self):
        newest = date.fromisoformat(NEWEST)
        for back in (1, 6, 11, 13):
            day = (newest - timedelta(days=back)).isoformat()
            boards = 14 - back
            with self.subTest(day=day):
                page = self.board("?sort=often", path=f"/days/{day}/")
                expected = []
                # A row is on every board from this one back to the first that listed it: the fifth row is on the
                # first board of all, 13 days before the newest, and the others on the boards 3, 6, or 9 days before.
                for row in (4, 3, 2, 1):
                    first = 13 if row == 4 else 3 * row
                    if back <= first:
                        name = self.rows[row]["full_name"]
                        new = " New" if back == first and back < 13 else ""
                        expected.append([name, f"{name}{new} on {first - back + 1} of {boards} boards"])
                if boards == 1:
                    expected = [[name, said.replace(" boards", " board")] for name, said in expected]
                    self.assertEqual(
                        expected, [[self.rows[4]["full_name"], f"{self.rows[4]['full_name']} on 1 of 1 board"]]
                    )
                self.assertEqual(page.evaluate(SAID_BY_ROWS), expected)

    def test_on_a_phone_each_count_lies_inside_its_row_and_the_page_does_not_scroll_sideways(self):
        page = self.board("?sort=often", width=390, height=844)
        self.assertEqual(page.evaluate(INSIDE), {"counts": [True] * 5, "sideways": False})

    def test_with_most_often_chosen_each_link_reads_its_name_alone_and_a_search_for_boards_finds_names_and_descriptions(
        self,
    ):
        page = self.board("?sort=often")
        self.assertEqual(
            [name for name, _ in page.evaluate(SAID_BY_ROWS)], [self.rows[row]["full_name"] for row in (4, 3, 2, 1, 0)]
        )
        page.get_by_role("searchbox").fill("boards")
        self.assertEqual([name for name, _ in page.evaluate(SAID_BY_ROWS)], [self.rows[1]["full_name"]])

    def test_typing_in_search_or_toggling_filters_does_not_reappend_rows_until_the_order_changes(self):
        """#244: searching or toggling filters hides/shows rows in place without re-appending every <tr>."""
        page = self.board()
        page.evaluate("""() => {
            window.__rowMoves = 0;
            new MutationObserver((records) => { window.__rowMoves += records.length; })
                .observe(document.querySelector("table.chart > tbody"), { childList: true });
        }""")
        page.get_by_role("searchbox").fill("octocat")
        page.locator('#kinds button[data-kind="new"]').click()
        page.locator('#kinds button[data-kind=""]').click()
        page.get_by_role("searchbox").fill("")
        self.assertEqual(page.evaluate("() => window.__rowMoves"), 0)
        page.locator("#sort").select_option("large")
        self.assertGreater(page.evaluate("() => window.__rowMoves"), 0)
        after_sort = page.evaluate("() => window.__rowMoves")
        page.get_by_role("searchbox").fill("octocat")
        self.assertEqual(page.evaluate("() => window.__rowMoves"), after_sort)

    def test_unknown_day_gains_sort_last_in_most_stars_gained_even_after_losses(self):
        """#239: a row whose board day gain is '–' (unknown) sorts after negative losses, not as 0."""
        board = read_json(self.board_file())
        edited = [
            {**board["rows"][0], "gained_1_day": None},
            {**board["rows"][1], "gained_1_day": -5},
            {**board["rows"][2], "gained_1_day": 0},
            {**board["rows"][3], "gained_1_day": 42},
            {**board["rows"][4], "gained_1_day": -20},
        ]
        self.write_board({**board, "rows": edited})
        self.out = self.out.with_name("dist-unknown-gain")
        self.build_pages()
        with served(self.out) as site:
            page = self.browser.new_page(viewport={"width": 1440, "height": 900})
            page.clock.set_fixed_time(published(self.out))
            page.goto(f"{site}/?sort=gained", wait_until="load")
            shown = page.evaluate(
                "() => [...document.querySelectorAll('table.chart > tbody > tr')]"
                ".map(r => r.querySelector('td.gr').textContent.trim())"
            )
            page.close()
            self.assertEqual(shown, ["+42", "0", "\N{MINUS SIGN}5", "\N{MINUS SIGN}20", "\N{EN DASH}"])


if __name__ == "__main__":
    unittest.main()
