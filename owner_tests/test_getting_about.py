"""Getting about: the site's bar, the day bar, History, and every link between the pages. Sentences 7 to 10 of the
owner's tests."""

import re
import unittest
from datetime import date
from urllib.parse import urlsplit

from playwright.sync_api import expect

from owner_tests.scenario import (
    Scenario,
    address_of,
    boards_it_was_on,
    day_bar,
    heading,
    needs_made_up_boards,
    opener,
    rows,
    rows_that_open,
    the_day,
)

MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


class GettingAbout(Scenario):
    def test_every_page_has_the_sites_bar_and_each_link_in_it_leads_to_a_page_that_is_there(self):
        """Sentence 7. A page of each kind, the one for an address that holds no page among them, has the bar the
        root has, with the same links to the same places, one of them the way home. Each place answers with a page."""
        page = self.reader()
        bars = {}
        for place in self.each_kind_of_page(page):
            page.goto(place)
            links = page.get_by_role("banner").get_by_role("link")
            bars[place] = {links.nth(at).inner_text().strip(): address_of(links.nth(at)) for at in range(links.count())}
        root = bars[f"{self.site.address}/"]
        self.assertGreater(len(root), 1)
        self.assertIn(f"{self.site.address}/", root.values())
        for place, bar in bars.items():
            with self.subTest(place):
                self.assertEqual(bar, root)
        for name, place in root.items():
            with self.subTest(link=name):
                self.assertEqual(page.goto(place).status, 200)
                expect(heading(page)).to_be_visible()

    def test_the_day_bar_leads_to_the_board_day_before_and_to_the_one_after(self):
        """Sentence 8. From the newest board, the day bar's link to the board before leads to the board of the day it
        names, and from there the link to the board after leads back to the newest board day's."""
        page = self.reader()
        self.visit(page)
        newest = the_day(heading(page).inner_text())
        before = day_bar(page).get_by_role("link", name=re.compile("^The board before"))
        self.given(before.count(), "the newest board is the first, so no board is before it")
        named = re.search(r"\d{1,2} [A-Z][a-z]+", before.inner_text()).group()
        before.click()
        expect(heading(page)).to_have_text(re.compile(rf"\b{named}\b"))
        self.assertLess(the_day(heading(page).inner_text()), newest)
        after = day_bar(page).get_by_role("link", name=re.compile("^The board after"))
        named = re.search(r"\d{1,2} [A-Z][a-z]+", after.inner_text()).group()
        after.click()
        expect(heading(page)).to_have_text(re.compile(rf"\b{named}\b"))
        self.assertEqual(the_day(heading(page).inner_text()), newest)

    @needs_made_up_boards
    def test_history_lists_every_board_day_and_each_leads_to_its_board(self):
        """Sentence 9. History, reached from the site's bar, has one link for each board day in the index, under its
        month, which gives the day's count of repositories. Each leads to the board of that day."""
        page = self.reader()
        self.visit(page)
        page.get_by_role("banner").get_by_role("link", name="History").click()
        expect(heading(page)).to_have_text("History")
        days = page.get_by_role("main").get_by_role("link", name=re.compile(r"repositor(y|ies)"))
        expect(days).to_have_count(len(self.site.boards))
        history = page.url
        for published in self.site.boards:
            with self.subTest(published["board_day"]):
                day = date.fromisoformat(published["board_day"])
                page.goto(history)
                month = page.get_by_role("region", name=f"{MONTHS[day.month - 1]} {day.year}")
                link = month.get_by_role("link", name=re.compile(rf"(?<!\d){day.day} {MONTHS[day.month - 1]}\b"))
                expect(link).to_have_accessible_name(re.compile(rf"\b{len(published['rows'])} repositor"))
                link.click()
                expect(heading(page)).to_have_text(re.compile(rf"\b{day.day} {MONTHS[day.month - 1][:3]}"))
                self.assertEqual(the_day(heading(page).inner_text()), day)
                expect(rows(page)).to_have_count(len(published["rows"]))

    @needs_made_up_boards
    def test_no_link_within_the_site_leads_to_a_page_the_build_did_not_write(self):
        """Sentence 10. Every page a reader can come to from the root is walked, with every row of every board
        opened, since an opened row links to the boards it was on. Each link that stays within the site leads to a
        file the build wrote, and the site answers for it."""
        page = self.reader()
        found = {"/": "the root"}
        waiting = ["/"]
        while waiting:
            path = waiting.pop()
            with self.subTest(path, linked_from=found[path]):
                written = self.site.pages / (path + "index.html" if path.endswith("/") else path).lstrip("/")
                self.assertTrue(written.is_file(), f"{found[path]} links to {path}, which the build did not write")
                self.assertEqual(self.visit(page, path).status, 200)
            for at in range(rows_that_open(page).count()):
                opener(rows_that_open(page).nth(at)).click()
                expect(boards_it_was_on(rows_that_open(page).nth(at))).to_be_visible()
            for link in page.locator("a[href]").evaluate_all("links => links.map(link => link.href)"):
                to = urlsplit(link)
                if f"{to.scheme}://{to.netloc}" == self.site.address and to.path not in found:
                    found[to.path] = path
                    waiting.append(to.path)
        # The walk reached every board day, History, Baseline, How it works, and the fonts' licence.
        self.assertGreaterEqual(len(found), len(self.site.boards) + 5)


if __name__ == "__main__":
    unittest.main()
