"""The cards: a board's rows laid out as boxes side by side, and the choice kept in the reader's browser. Sentence 48
of the owner's tests."""

import unittest

from playwright.sync_api import Page, expect

from owner_tests.scenario import Scenario, board, names, rows

WHERE = "rows => rows.map(row => { const edge = row.getBoundingClientRect(); return [edge.left, edge.top]; })"
"""Where each row is drawn on the page: its left edge and its top, in pixels."""


def lines(page: Page) -> list[list[float]]:
    """The left edge of each row shown, gathered into the lines the board draws them on, from the top down."""
    found: dict[int, list[float]] = {}
    for left, top in rows(page).evaluate_all(WHERE):
        found.setdefault(round(top), []).append(left)
    return [found[top] for top in sorted(found)]


class TheCards(Scenario):
    def assert_laid_out(self, page: Page, chosen: str) -> None:
        """The switch shows `chosen` pressed and the other not, and the board lies as `chosen` lays it: as cards,
        more than one row to its first line, side by side from the left; as the list, one row to every line."""
        view = page.get_by_role("group", name="View")
        other = "List" if chosen == "Cards" else "Cards"
        expect(view.get_by_role("button", name=chosen, exact=True, pressed=True)).to_be_visible()
        expect(view.get_by_role("button", name=other, exact=True, pressed=False)).to_be_visible()
        laid = lines(page)
        if chosen == "Cards":
            self.assertGreater(len(laid[0]), 1, laid[:2])
            self.assertEqual(laid[0], sorted(laid[0]))
        else:
            self.assertEqual([len(line) for line in laid], [1] * len(laid))

    def test_pressing_cards_lays_the_rows_out_side_by_side_and_the_browser_keeps_it_until_list_is_pressed(self):
        """Sentence 48. A new reader 1440 pixels wide at the newest board finds the list, with List pressed in the
        group named View. Pressing Cards lays the rows out as boxes side by side, more than one to the first line,
        with the same rows in the same order. The reader comes back to the plain address in the same browser and
        finds the board in cards again, with Cards pressed. Pressing List brings the list back, one row to a line,
        and the next visit in that browser finds the list."""
        page = self.reader()
        self.visit(page)
        self.given(rows(page).count() > 1, "the newest board lists fewer than two repositories")
        expect(board(page)).to_be_visible()
        listed = names(page)
        self.assert_laid_out(page, "List")

        page.get_by_role("group", name="View").get_by_role("button", name="Cards", exact=True).click()
        self.assert_laid_out(page, "Cards")
        self.assertEqual(names(page), listed)

        again = page.context.new_page()
        self.visit(again)
        self.assert_laid_out(again, "Cards")
        self.assertEqual(names(again), listed)
        again.get_by_role("group", name="View").get_by_role("button", name="List", exact=True).click()
        self.assert_laid_out(again, "List")

        last = page.context.new_page()
        self.visit(last)
        self.assert_laid_out(last, "List")
        self.assertEqual(names(last), listed)


if __name__ == "__main__":
    unittest.main()
