"""The search, in reach all the way down a board, on a desktop. Sentence 46 of the owner's tests."""

import re
import unittest

from playwright.sync_api import Locator, expect

from owner_tests.scenario import Scenario, column, heading, names, rows

MIDDLE = "element => { const edge = element.getBoundingClientRect(); return (edge.top + edge.bottom) / 2; }"
"""How far down the screen the middle of an element is drawn, in pixels."""


def a_word_to_search(words: str) -> str:
    """The longest run of letters and digits in `words`, in small letters: a word to search for."""
    return max(re.findall(r"[^\W_]+", words), key=len).lower()


class TheSearchDownABoard(Scenario):
    def assert_beside_the_date(self, box: Locator, date: Locator) -> None:
        """The search box is whole on the screen, on the line of the board's date, which the day bar holds."""
        expect(box).to_be_in_viewport(ratio=1)
        expect(date).to_be_in_viewport(ratio=1)
        self.assertAlmostEqual(box.evaluate(MIDDLE), date.evaluate(MIDDLE), delta=2)

    def test_on_a_desktop_the_search_stays_in_view_in_the_day_bar_down_a_board_and_finds_rows_from_its_foot(self):
        """Sentence 46. A reader 1440 pixels wide at the newest board scrolls down to the board's last row. The
        search box is there, whole on the screen, on the line of the board's date in the day bar. A word of the last
        row's name, typed into it there, leaves the rows whose name or description holds the word, and no other, and
        the box is still on that line."""
        page = self.reader()
        self.visit(page)
        self.given(rows(page).count(), "the newest board lists no repository")
        listed = names(page)
        # A row with no description says so in the page's own words, which are not the owner's, so it holds none.
        described = ["" if words == "No description" else words for words in column(page, "Description")]
        word = a_word_to_search(listed[-1].partition("/")[2])
        holding = [
            name for name, words in zip(listed, described, strict=True) if word in name.lower() or word in words.lower()
        ]

        rows(page).last.scroll_into_view_if_needed()
        expect(rows(page).last).to_be_in_viewport()
        box = page.get_by_role("searchbox")
        date = heading(page)
        self.assert_beside_the_date(box, date)

        box.fill(word)
        expect(rows(page)).to_have_count(len(holding))
        self.assertEqual(names(page), holding)
        self.assert_beside_the_date(box, date)


if __name__ == "__main__":
    unittest.main()
