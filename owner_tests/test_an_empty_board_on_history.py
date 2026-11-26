"""An empty board on History. Sentence 42 of the owner's tests."""

import re
import unittest

from playwright.sync_api import expect

from owner_tests.scenario import Scenario, heading

EMPTY = re.compile(r": 0 repositories")
"""The words a screen reader hears at the end of a day's link on History when its board has no repository."""

LISTED = re.compile(r": [1-9][\d,]* repositor(y|ies)")
"""The words a screen reader hears in a day's link on History when its board lists repositories."""

FILL = "link => getComputedStyle(link).backgroundColor"
"""The colour a day's cell paints over the page. A cell that paints none gives a colour with no alpha."""

NONE = "rgba(0, 0, 0, 0)"


class AnEmptyBoardOnHistory(Scenario):
    def test_history_draws_a_board_with_no_repository_unfilled_with_no_count_of_new_and_its_legend_names_it(self):
        """Sentence 42. History is reached from the site's bar, in the light theme and the dark. Each day whose
        link is heard to have 0 repositories is heard to have nothing after that, and paints no fill of its own over
        the page, where each day whose board lists repositories is shaded: before #91 an empty board took the card's
        own colour and was the brightest cell of its month. The legend names "no repository on the board" and "no
        board" on the screen."""
        for dark in (False, True):
            with self.subTest(dark=dark):
                page = self.reader(dark=dark)
                self.visit(page)
                page.get_by_role("banner").get_by_role("link", name="History").click()
                expect(heading(page)).to_have_text("History")
                days = page.get_by_role("main").get_by_role("link")
                empty = days.filter(has_text=EMPTY)
                listed = days.filter(has_text=LISTED)
                self.given(empty.count(), "History shows no board with no repository")
                self.given(listed.count(), "History shows no board that lists repositories")
                for at in range(empty.count()):
                    link = empty.nth(at)
                    expect(link).to_have_accessible_name(re.compile(r"\S: 0 repositories$"))
                    self.assertEqual(link.evaluate(FILL), NONE, link.get_attribute("href"))
                for at in range(listed.count()):
                    link = listed.nth(at)
                    self.assertNotEqual(link.evaluate(FILL), NONE, link.get_attribute("href"))
                expect(page.get_by_text("no repository on the board", exact=True)).to_be_visible()
                expect(page.get_by_text("no board", exact=True)).to_be_visible()


if __name__ == "__main__":
    unittest.main()
