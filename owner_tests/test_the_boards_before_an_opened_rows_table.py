"""The boards before an opened row's table: a repository that was on boards older than the ones the table covers
says how many, and leads to History. Sentence 49 of the owner's tests."""

import re
import tempfile
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect

from owner_tests import made_up, the_site
from owner_tests.scenario import (
    Scenario,
    boards_it_was_on,
    facts,
    heading,
    needs_made_up_boards,
    open_rows,
    rows_that_open,
)

LINE = re.compile(r"^And (\d+) boards? before \d{1,2} \w{3}, (?:the first )?on (\d{1,2} \w{3} \d{4})\. ")
"""The start of the line under an opened row's table: how many boards older than the table's, and the first."""


class TheBoardsBefore(Scenario):
    @needs_made_up_boards
    def test_an_opened_row_on_boards_older_than_its_table_says_how_many_and_leads_to_history(self):
        """Sentence 49. The made-up site's nine board days are all inside an opened row's table, so this builds a
        site of its own, from `made_up.older_boards`, and hands it out as the site's host does. A reader 1440 pixels
        wide opens both rows of its newest board. Each table is named for the last 30 board days. The row whose
        repository was on two boards older than those says so under its table, with the first of them as its
        "First on a board" fact gives it, and its link History leads to History. The other row says nothing of
        older boards."""
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        pages = the_site.built(folder, made_up.older_boards())
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(the_site._Pages, directory=str(pages)))
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()

        page = self.reader()
        page.goto(f"http://127.0.0.1:{server.server_port}/")
        shown = rows_that_open(page)
        self.assertEqual(shown.count(), 2)
        open_rows(shown)
        said = []
        for at in range(shown.count()):
            row = shown.nth(at)
            expect(boards_it_was_on(row)).to_have_accessible_name("The boards it was on, of the last 30")
            said.append(row.get_by_text("Every board day is in"))
        on_older, on_none = said
        expect(on_none).to_have_count(0)
        expect(on_older).to_have_count(1)
        words = LINE.match(on_older.inner_text())
        self.assertIsNotNone(words, on_older.inner_text())
        self.assertEqual(words[1], "2")
        self.assertEqual(words[2], facts(shown.first)["First on a board"])
        expect(on_older).to_have_text(re.compile(r"Every board day is in History\.$"))
        on_older.get_by_role("link", name="History", exact=True).click()
        expect(page).to_have_url(re.compile(r"/days/$"))
        expect(heading(page)).to_have_text("History")


if __name__ == "__main__":
    unittest.main()
