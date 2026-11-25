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
from urllib.parse import parse_qsl, urlencode

from helpers import BuildTest, read_json

from sitework.layout import chrome, published, served

OLDER = "2026-11-08"

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


class TheFiltersTogether(BuildTest):
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


if __name__ == "__main__":
    unittest.main()
