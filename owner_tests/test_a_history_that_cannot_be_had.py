"""A history that cannot be had. Sentence 39 of the owner's tests."""

import unittest

from playwright.sync_api import expect

from owner_tests.scenario import Scenario, boards_it_was_on, open_row, reason, rows

HISTORY = "**/history.json"
"""The address of a board day's history, which a row asks for when it is opened."""

SAID = "The rest of this row could not be loaded."


class AHistoryThatCannotBeHad(Scenario):
    def test_an_opened_row_whose_history_cannot_be_had_still_shows_its_reason_and_says_the_rest_could_not_be_loaded(
        self,
    ):
        """Sentence 39. The board day's history is kept from the reader's browser, as a fault on the way to the site
        would keep it. The first row still opens, on the reason it is on the board, and says that the rest could not
        be loaded. It shows no table of the boards it was on, since those come with the history."""
        page = self.reader()
        page.route(HISTORY, lambda route: route.abort())
        self.visit(page)
        self.given(rows(page).count(), "the newest board lists no repository")
        row = rows(page).first
        open_row(row)
        expect(reason(row)).to_be_visible()
        expect(row.get_by_text(SAID)).to_be_visible()
        expect(boards_it_was_on(row)).to_have_count(0)


if __name__ == "__main__":
    unittest.main()
