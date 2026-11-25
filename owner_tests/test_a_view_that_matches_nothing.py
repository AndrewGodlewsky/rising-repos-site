"""A view that matches nothing. Sentence 40 of the owner's tests."""

import re
import unittest
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect

from owner_tests.scenario import Scenario, names, rows

NONE_SHOWN = re.compile(r"No repository on this board matches")
"""What the board says in place of its rows when the search and the filters leave none."""

CLEAR = "Clear search and filters"

HELD_BY_NO_ROW = "qzxjv-held-by-no-row"
"""A search that no repository's name or description holds."""

CHOSEN = "s => s.options[s.selectedIndex].text"
"""The words of the option a list shows as chosen."""


class AViewThatMatchesNothing(Scenario):
    def test_a_view_that_leaves_no_row_says_what_is_chosen_and_clear_search_and_filters_shows_all_rows_until_back(
        self,
    ):
        """Sentence 40. The reader puts the board in the order of most stars first, chooses the first language the
        filter offers, and searches for a word that no row holds. No row is left, and the board says that nothing
        matches the search among that language, and offers the button "Clear search and filters". Pressed, it shows
        every row again in the order chosen, with the search empty, every language, and nothing that says no row
        matches. The address keeps the order alone. Back then returns the view that matched nothing: its address,
        its search, its language, and its line."""
        page = self.reader()
        self.visit(page)
        self.given(rows(page).count(), "the newest board lists no repository")
        order = page.get_by_role("combobox", name="Order")
        languages = page.get_by_role("combobox", name="Language")
        box = page.get_by_role("searchbox")
        offered = languages.get_by_role("option").all_inner_texts()[1:]
        self.given(offered, "the newest board offers no language")
        order.select_option(label="Most stars first")
        ordered = names(page)
        language = offered[0]
        languages.select_option(label=language)
        box.fill(HELD_BY_NO_ROW)
        expect(rows(page)).to_have_count(0)
        said = page.get_by_text(NONE_SHOWN)
        expect(said).to_have_text(f"No repository on this board matches the search among {language}.")
        clear = page.get_by_role("button", name=CLEAR, exact=True)
        expect(clear).to_be_visible()
        nothing = page.url

        clear.click()
        expect(rows(page)).to_have_count(len(ordered))
        self.assertEqual(names(page), ordered)
        expect(box).to_have_value("")
        self.assertEqual(languages.evaluate(CHOSEN), "All languages")
        self.assertEqual(order.evaluate(CHOSEN), "Most stars first")
        expect(said).to_be_hidden()
        expect(clear).to_be_hidden()
        self.assertEqual(set(parse_qs(urlsplit(page.url).query)), {"sort"})

        page.go_back()
        expect(page).to_have_url(nothing)
        expect(rows(page)).to_have_count(0)
        expect(box).to_have_value(HELD_BY_NO_ROW)
        self.assertEqual(languages.evaluate(CHOSEN), language)
        self.assertEqual(order.evaluate(CHOSEN), "Most stars first")
        expect(said).to_have_text(f"No repository on this board matches the search among {language}.")


if __name__ == "__main__":
    unittest.main()
