"""The way from an earlier board to the newest, on a phone. Sentence 35 of the owner's tests."""

import re
import unittest

from playwright.sync_api import expect

from owner_tests.scenario import PHONE, Scenario, address_of, day_bar, heading, the_day


class TheWayToTheNewestOnAPhone(Scenario):
    def test_on_a_phone_an_earlier_boards_day_bar_leads_to_the_newest_board_with_scripts_on_or_off(self):
        """Sentence 35. On a screen 390 pixels wide, with scripts on and then off, the reader takes the day bar's
        link to the board before the newest. On that earlier board the day bar shows one link that leads to the
        root, drawn whole inside the bar and inside the screen. Pressed, it opens the root on the newest board. The
        link is found by where it leads, and not by its words, so that its words may change."""
        for scripts in (True, False):
            with self.subTest(scripts=scripts):
                page = self.reader(width=PHONE, scripts=scripts)
                self.visit(page)
                newest = the_day(heading(page).inner_text())
                before = day_bar(page).get_by_role("link", name=re.compile("^The board before"))
                self.given(before.count(), "the newest board is the first, so no board is before it")
                earlier = address_of(before)
                before.click()
                expect(page).to_have_url(earlier)
                self.assertLess(the_day(heading(page).inner_text()), newest)
                bar = day_bar(page)
                links = bar.get_by_role("link")
                home = [
                    links.nth(at)
                    for at in range(links.count())
                    if address_of(links.nth(at)) == f"{self.site.address}/" and links.nth(at).is_visible()
                ]
                self.assertEqual(len(home), 1, "the earlier board's day bar does not show one link to the newest")
                (link,) = home
                edge, box = bar.bounding_box(), link.bounding_box()
                self.assertGreater(box["width"], 1)
                self.assertGreater(box["height"], 1)
                self.assertGreaterEqual(box["x"], max(edge["x"], 0) - 0.5)
                self.assertLessEqual(box["x"] + box["width"], min(edge["x"] + edge["width"], PHONE) + 0.5)
                self.assertGreaterEqual(box["y"], edge["y"] - 0.5)
                self.assertLessEqual(box["y"] + box["height"], edge["y"] + edge["height"] + 0.5)
                link.click()
                expect(page).to_have_url(f"{self.site.address}/")
                self.assertEqual(the_day(heading(page).inner_text()), newest)


if __name__ == "__main__":
    unittest.main()
