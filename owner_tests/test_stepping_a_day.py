"""Stepping a day with a view chosen. Sentence 44 of the owner's tests."""

import re
import unittest
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Locator, Page, expect

from owner_tests.scenario import Scenario, address_of, day_bar, heading, in_the_bar, names, rows, the_day

CHOSEN = "s => s.options[s.selectedIndex].text"
"""The words of the option a list shows as chosen."""

ORDER = "Most stars first"
"""An order other than by rank, which every board with rows offers."""

HELD_BY_NO_ROW = "qzxjv-held-by-no-row"
"""A search that no repository's name or description holds, so that a board it reached would show no row."""


class SteppingADay(Scenario):
    def offered(self, page: Page) -> list[str]:
        """The languages a board's filter offers, by their words, after the first option, which is every language."""
        return page.get_by_role("combobox", name="Language").get_by_role("option").all_inner_texts()[1:]

    def chosen_there(self, address: str, language: str) -> list[str]:
        """The rows a new reader sees who opens `address` with no view in it, and chooses the language and the order
        there with the controls."""
        page = self.reader()
        page.goto(address)
        page.get_by_role("combobox", name="Language").select_option(label=language)
        page.get_by_role("combobox", name="Order").select_option(label=ORDER)
        return names(page)

    def step(self, page: Page, link: Locator, language: str) -> None:
        """Follow a link of the day bar, and hold the board it opens to the view chosen: the same language and order
        shown chosen, an empty search, no search in the address, and the rows a reader who chose them there sees."""
        plain = urlsplit(address_of(link))
        link.click()
        # The board the link names, whatever query its address holds: each step leads to another path.
        expect(page).to_have_url(
            re.compile("^" + re.escape(f"{plain.scheme}://{plain.netloc}{plain.path}") + r"(\?.*)?$")
        )
        expect(heading(page)).to_be_visible()
        self.assertEqual(page.get_by_role("combobox", name="Language").evaluate(CHOSEN), language)
        self.assertEqual(page.get_by_role("combobox", name="Order").evaluate(CHOSEN), ORDER)
        expect(page.get_by_role("searchbox")).to_have_value("")
        self.assertNotIn("q", parse_qs(urlsplit(in_the_bar(page)).query))
        there = self.chosen_there(f"{plain.scheme}://{plain.netloc}{plain.path}", language)
        self.assertGreater(len(there), 0)
        expect(rows(page)).to_have_count(len(there))
        self.assertEqual(names(page), there)

    def test_stepping_to_the_board_day_before_after_or_the_newest_keeps_the_language_and_order_and_not_the_search(
        self,
    ):
        """Sentence 44. On the newest board the reader chooses a language that the board before it offers too, the
        order of most stars first, and a search that no row holds, so that no row is shown. The reader then takes
        the day bar's link to the board before, from there the link to the newest board, from the root the board
        before again, and from there the link to the board after. Each board opened shows that language and that
        order chosen, its search empty, no search in its address, and the very rows that a reader who opened it
        plainly and chose that language and order there would see."""
        page = self.reader()
        self.visit(page)
        newest = the_day(heading(page).inner_text())
        before = day_bar(page).get_by_role("link", name=re.compile("^The board before"))
        self.given(before.count(), "the newest board is the first, so no board is before it")
        earlier = self.reader()
        earlier.goto(address_of(before))
        common = [language for language in self.offered(page) if language in self.offered(earlier)]
        self.given(common, "no language is offered by both the newest board and the one before it")
        language = common[0]
        page.get_by_role("combobox", name="Language").select_option(label=language)
        page.get_by_role("combobox", name="Order").select_option(label=ORDER)
        page.get_by_role("searchbox").fill(HELD_BY_NO_ROW)
        expect(rows(page)).to_have_count(0)

        self.step(page, day_bar(page).get_by_role("link", name=re.compile("^The board before")), language)
        self.assertLess(the_day(heading(page).inner_text()), newest)
        self.step(page, day_bar(page).get_by_role("link", name=re.compile("^The newest board")), language)
        self.assertEqual(the_day(heading(page).inner_text()), newest)
        self.assertEqual(urlsplit(in_the_bar(page)).path, "/")
        self.step(page, day_bar(page).get_by_role("link", name=re.compile("^The board before")), language)
        self.step(page, day_bar(page).get_by_role("link", name=re.compile("^The board after")), language)
        self.assertEqual(the_day(heading(page).inner_text()), newest)


if __name__ == "__main__":
    unittest.main()
