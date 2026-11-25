"""How a board's page asks for its history: once, however many rows are opened, and again after it failed (#42).

An opened row's sum, its facts, and the boards it was on come from one file, the board day's `history.json`, which
the page asks for when the first row is opened. The owner's sentence 17 holds an opened row once the history has
arrived, and sentence 38 what a reader sees when it cannot be had. These hold the two things a reader does not
see: that two rows opened while the file is on its way ask for it once, and that a file which could not be had is
asked for again.

A file that is late or does not come is something only a browser can show, so these open rows in the Chrome the
machine already has, through Playwright, as the tests of an opened row's table do. Each test stands between the
page and the file, and lets the file through, holds it, or refuses it.
"""

import unittest

from helpers import BuildTest

from sitework.layout import chrome, published, served

HISTORY = "**/history.json"
ROWS = "table.chart > tbody > tr"
DRAWN = "details[data-drawn]"
"""A row whose detail the script has drawn from the history."""
FAULT = ".more-wait"
"""The line a row holds while its history has not been had."""


class TheHistoryIsAskedFor(BuildTest):
    def board(self, browser, site: str, answer):
        """The newest board in a new page, with each asking for the history handed to `answer`."""
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.clock.set_fixed_time(published(self.out))
        page.route(HISTORY, answer)
        page.goto(site, wait_until="load")
        return page

    def test_two_rows_opened_while_the_history_is_on_its_way_ask_for_it_once_and_both_show_it(self):
        self.build_pages()
        held = []
        with served(self.out) as site, chrome() as browser:
            page = self.board(browser, site, lambda route: held.append(route))
            first, second = page.locator(ROWS).nth(0), page.locator(ROWS).nth(1)
            first.locator("summary").first.click()
            second.locator("summary").first.click()
            page.wait_for_timeout(300)
            self.assertEqual(len(held), 1)
            self.assertEqual(page.locator(DRAWN).count(), 0)
            held[0].continue_()
            first.locator(DRAWN).wait_for()
            second.locator(DRAWN).wait_for()
            self.assertEqual(len(held), 1)

    def test_a_history_that_could_not_be_had_is_asked_for_again_and_the_row_then_shows_it_and_no_fault(self):
        self.build_pages()
        asked = []

        def refuse_the_first(route) -> None:
            asked.append(route)
            if len(asked) == 1:
                route.abort()
            else:
                route.continue_()

        with served(self.out) as site, chrome() as browser:
            page = self.board(browser, site, refuse_the_first)
            row = page.locator(ROWS).first
            row.locator("summary").first.click()
            row.locator(FAULT).wait_for()
            self.assertEqual(row.locator(DRAWN).count(), 0)
            # Closed and opened again, as a reader would try it.
            row.locator("summary").first.click()
            row.locator("summary").first.click()
            row.locator(DRAWN).wait_for()
            self.assertEqual(len(asked), 2)
            self.assertEqual(row.locator(FAULT).count(), 0)


if __name__ == "__main__":
    unittest.main()
