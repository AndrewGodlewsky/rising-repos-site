"""What the site promises a reader: nothing from another site, one script, an owner's words as text, a page of a
bounded size, a notice when the boards have stopped, and a build that refuses bad data. Sentences 26 to 32 of the
owner's tests.

Sentence 33, that the site eval's six numbers are within their limits, has no test here: the site eval is that test.
It measures the live site after each deploy, and evals/site/ holds it and its limits.
"""

import gzip
import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Dialog, Page, expect
from playwright.sync_api import Error as BrowserError

from owner_tests import made_up, the_site
from owner_tests.scenario import (
    Scenario,
    board,
    boards_it_was_on,
    column,
    day_bar,
    facts,
    heading,
    names,
    needs_made_up_boards,
    open_row,
    rows,
    rows_that_open,
    the_day,
)

PAGE_LIMIT = 500_000
"""The most bytes a page may take, with its styles, its script, and its type, which are all inside it."""

WIRE_LIMIT = 150_000
"""The most bytes the root of a board of `made_up.LONG_BOARD` rows may take once gzipped, which is how it is sent."""

NOTICE = re.compile(r"The newest board is \d+ (hours|days) old")
WITHHELD = re.compile(r"No board is shown")
"""What the notice of an old board says once the newest is 26 hours old, and once it is a week old."""

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


class WhatTheSitePromises(Scenario):
    def refusals(self, page: Page) -> list[str]:
        """A list that fills with what the browser refuses `page` under the page's own policy, on this page and each
        it goes on to: the kind of thing refused, and where it was from. The browser tells a page of each refusal,
        and a listener put into the page ahead of its own script passes that on.

        What is passed on reaches the list a moment after the browser refused, and by then the reader may be on
        the next page. So each page keeps its own refusals too, as `refusedHere`, for a test that has to say
        which page a refusal was of."""
        refused: list[str] = []
        page.expose_function("toldOfARefusal", lambda kind, source: refused.append(f"{kind}: {source}"))
        page.add_init_script(
            "window.refusedHere = [];"
            "document.addEventListener('securitypolicyviolation', refusal => {"
            " refusedHere.push(refusal.effectiveDirective + ': ' + refusal.blockedURI);"
            " toldOfARefusal(refusal.effectiveDirective, refusal.blockedURI); })"
        )
        return refused

    def test_a_page_asks_nothing_of_another_site_and_its_browser_refuses_nothing(self):
        """Sentence 26. A page of each kind is loaded and used: on a board the first row is opened, which fetches
        the board day's history, and on every page the theme is switched and switched back. Every request that
        leaves the browser goes to the site's own address, and the browser refuses the page nothing. A request the
        browser refused to send is counted among the refusals, and not among the requests."""
        page = self.reader()
        asked, stopped = [], []
        page.on("request", lambda request: asked.append(request.url))
        page.on("requestfailed", lambda request: stopped.append(request.url) if request.failure == "csp" else None)
        refused = self.refusals(page)
        for place in self.each_kind_of_page(page):
            page.goto(place)
            if rows_that_open(page).count():
                open_row(rows_that_open(page).first)
                expect(boards_it_was_on(rows_that_open(page).first)).to_be_visible()
            for _ in range(2):
                page.get_by_role("button", name="Dark theme").click()
        elsewhere = [
            address
            for address in asked
            if address not in stopped
            and urlsplit(address).scheme not in ("data", "blob")
            and f"{urlsplit(address).scheme}://{urlsplit(address).netloc}" != self.site.address
        ]
        self.assertTrue(asked)
        self.assertEqual(elsewhere, [])
        self.assertEqual(refused, [])

    def test_a_page_runs_one_script_and_no_other(self):
        """Sentence 27. On a page of each kind, one of the scripts the page holds runs: the browser refuses every
        other one, and no script is fetched. The one that runs is the site's: the theme switch shows only where it
        has run. A second script put into the page does not run either, so the page's title stays as it was."""
        page = self.reader()
        fetched = []
        page.on(
            "response", lambda answer: fetched.append(answer.url) if answer.request.resource_type == "script" else None
        )
        self.refusals(page)
        for place in self.each_kind_of_page(page):
            with self.subTest(place):
                page.goto(place)
                held = page.locator("script").count()
                # The page's own count of what it was refused. The list `refusals` gives is filled a moment
                # late: the refusal of the second script put into the page before reached it once after
                # this page was open, and was counted against this one (the job of #77, 24 November 2026).
                refused = page.evaluate(
                    "() => refusedHere.filter(refusal => refusal.startsWith('script-src-elem')).length"
                )
                self.assertEqual(held - refused, 1)
                expect(page.get_by_role("button", name="Dark theme")).to_be_visible()
                title = page.title()
                try:
                    page.add_script_tag(content="document.title = 'a second script ran'")
                except BrowserError:
                    pass  # The browser's refusal of the script, which is what the page promises.
                self.assertEqual(page.title(), title)
        self.assertEqual(fetched, [])

    @needs_made_up_boards
    def test_what_a_repositorys_owner_wrote_is_shown_as_text_and_is_never_a_link(self):
        """Sentence 28. The made-up newest board holds a description and a language written as markup, a
        description with no place to break, and one in several scripts. With scripts on and off, each description is
        on the page as its owner wrote it, character for character. None of it ran or became a link: the page keeps
        its title, raises no dialog, lists every row, and gives each row one link, to its repository on GitHub. With
        scripts on, the language is one entry of the filter's list, and one fact of its opened row, as written."""
        for scripts in (True, False):
            with self.subTest(scripts=scripts):
                self.read_what_the_owners_wrote(scripts)

    def read_what_the_owners_wrote(self, scripts: bool) -> None:
        newest = self.site.boards[0]
        written = [row["description"] or "No description" for row in newest["rows"]]
        self.assertIn(made_up.MARKUP, written)
        page = self.reader(scripts=scripts)
        dialogs = []

        def raised(dialog: Dialog) -> None:
            dialogs.append(dialog.message)
            dialog.dismiss()

        page.on("dialog", raised)
        self.visit(page)
        self.assertEqual(column(page, "Description"), written)
        self.assertEqual(names(page), [row["full_name"] for row in newest["rows"]])
        self.assert_no_owner_made_a_link(page, newest)
        if scripts:
            languages = page.get_by_role("combobox", name="Language")
            self.assertEqual(languages.get_by_role("option").all_inner_texts().count(made_up.MARKUP_LANGUAGE), 1)
            languages.select_option(label=made_up.MARKUP_LANGUAGE)
            expect(rows(page)).to_have_count(1)
            self.assertEqual(column(page, "Description"), [made_up.MARKUP])
            open_row(rows(page).first)
            expect(boards_it_was_on(rows(page).first)).to_be_visible()
            self.assertEqual(facts(rows(page).first)["Language"], made_up.MARKUP_LANGUAGE)
            languages.select_option(index=0)
            self.assert_no_owner_made_a_link(page, newest)
        self.assertNotIn(page.title(), ("owned", "1"))
        self.assertEqual(dialogs, [])

    def assert_no_owner_made_a_link(self, page: Page, newest: dict) -> None:
        """Every link in the board leads to a row's repository on GitHub, one for each row, or to a page of the
        site, and no link anywhere on the page leads where the made-up owners' markup points."""
        leads = board(page).locator("a[href]").evaluate_all("links => links.map(link => link.href)")
        beyond = [lead for lead in leads if not lead.startswith(f"{self.site.address}/")]
        self.assertEqual(beyond, [f"https://github.com/{row['full_name']}" for row in newest["rows"]])
        everywhere = page.locator("a[href]").evaluate_all("links => links.map(link => link.href)")
        self.assertEqual(
            [lead for lead in everywhere if "made-up.invalid" in lead or lead.startswith("javascript")], []
        )

    @needs_made_up_boards
    def test_no_page_is_over_500000_bytes_and_the_root_of_a_long_board_is_under_150000_on_the_wire(self):
        """Sentence 29. A page asks for nothing but itself (sentence 26), so its file's size is its weight. No page
        of the made-up site is over the limit, and none of a site whose board has the most rows the earlier site
        published, 316, each as long as the data contract lets a row be. The root of a board of 713 rows of the usual
        length is under its own limit once gzipped at level 6, which tests/test_page_weight.py records as packing a
        little less tightly than the site's server does. That board's root is over 500,000 bytes before it is packed:
        the first limit is held at the 316 rows, and the second at the 713."""
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        largest = the_site.built(folder / "largest", made_up.largest_board())
        self.assertEqual((largest / "index.html").read_bytes().count(b"https://github.com/"), made_up.LARGEST_BOARD)
        for which, site in (("the made-up site", self.site.pages), ("the largest board", largest)):
            pages = sorted(site.rglob("*.html"))
            self.assertGreater(len(pages), 4)
            for page in pages:
                with self.subTest(which, page=page.relative_to(site).as_posix()):
                    self.assertLessEqual(page.stat().st_size, PAGE_LIMIT)
        root = (the_site.built(folder / "long", made_up.long_board()) / "index.html").read_bytes()
        self.assertEqual(root.count(b"https://github.com/"), made_up.LONG_BOARD)
        self.assertLess(len(gzip.compress(root, compresslevel=6, mtime=0)), WIRE_LIMIT)

    def test_a_newest_board_that_is_26_hours_old_says_so_and_after_a_week_the_boards_are_not_shown(self):
        """Sentence 30. The root gives the newest board's publish time, and a reader's clock is set from it. A minute
        short of 26 hours on, the page says nothing of the board's age. At 26 hours it says the newest board is that
        old, and still shows it. A week on it says that no board is shown, and shows none: not the newest, not the
        board before it, and not History's list of them."""
        page = self.reader()
        self.visit(page)
        published = datetime.fromisoformat(page.locator('meta[name="rr:published-at"]').get_attribute("content"))
        listed = rows(page).count()
        self.given(listed, "the newest board lists no repository")

        fresh = self.reader(clock=published + timedelta(hours=26) - timedelta(minutes=1))
        self.visit(fresh)
        expect(fresh.get_by_text(NOTICE)).to_have_count(0)
        expect(fresh.get_by_text(WITHHELD)).to_have_count(0)
        expect(rows(fresh)).to_have_count(listed)

        old = self.reader(clock=published + timedelta(hours=26))
        self.visit(old)
        expect(old.get_by_text(NOTICE)).to_be_visible()
        expect(old.get_by_text(NOTICE)).to_have_text(re.compile("26 hours old"))
        expect(rows(old)).to_have_count(listed)

        stopped = self.reader(clock=published + timedelta(days=7))
        self.visit(stopped)
        expect(stopped.get_by_text(WITHHELD)).to_be_visible()
        expect(rows(stopped)).to_have_count(0)
        before = day_bar(stopped).get_by_role("link", name=re.compile("^The board before"))
        if before.count():
            before.click()
            expect(heading(stopped)).not_to_have_text(" ".join(heading(page).inner_text().split()))
            expect(stopped.get_by_text(WITHHELD)).to_be_visible()
            expect(rows(stopped)).to_have_count(0)
        stopped.get_by_role("banner").get_by_role("link", name="History").click()
        expect(stopped.get_by_text(WITHHELD)).to_be_visible()
        expect(stopped.get_by_role("main").get_by_role("link")).to_have_count(0)

    def test_the_root_states_its_board_day_and_its_publish_time_in_the_data_contracts_two_tags(self):
        """Sentence 31. The root's head holds each of the two tags once: rr:board-date, a day, and rr:published-at,
        a time in UTC to the second. They state what the page shows a reader: the day in its heading, and the time
        that About this board gives as when it was published. On the made-up boards the newest board's file is at
        hand, and the tags state its board day and its publish time."""
        page = self.reader()
        self.visit(page)
        day, published = page.locator('meta[name="rr:board-date"]'), page.locator('meta[name="rr:published-at"]')
        expect(day).to_have_count(1)
        expect(published).to_have_count(1)
        expect(day).to_have_attribute("content", re.compile(r"^\d{4}-\d{2}-\d{2}$"))
        expect(published).to_have_attribute("content", re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"))
        self.assertEqual(day.get_attribute("content"), the_day(heading(page).inner_text()).isoformat())
        if self.site.boards:
            self.assertEqual(day.get_attribute("content"), self.site.boards[0]["board_day"])
            self.assertEqual(published.get_attribute("content"), self.site.boards[0]["published_at"])
        at = datetime.fromisoformat(published.get_attribute("content"))
        shown = f"{at.day} {MONTHS[at.month - 1]} {at.year} at {at:%H:%M}"
        expect(page.get_by_role("main").get_by_text(shown)).to_be_visible()

    @needs_made_up_boards
    def test_a_data_file_that_breaks_the_data_contract_fails_the_build(self):
        """Sentence 32. The made-up boards build. Each of seven faults, put into a copy of them one at a time, makes
        the build command end in failure, name the file at fault, and write no page."""
        newest = self.site.boards[0]
        row = newest["rows"][0]

        def with_row(changed: dict) -> dict:
            return {**newest, "rows": [changed, *newest["rows"][1:]]}

        faults = {
            "a row without its stars": with_row({name: value for name, value in row.items() if name != "stars"}),
            "a rank that is not a number": with_row({**row, "rank": "1"}),
            "a field the contract does not have": with_row({**row, "homepage": "https://made-up.invalid/"}),
            "a description longer than the contract allows": with_row({**row, "description": "a" * 351}),
            "a name that is not an owner and a repository": with_row({**row, "full_name": "made-up/owner/name"}),
            "a board that holds a band back and names none": {**newest, "state": "held"},
        }
        for what, broken in faults.items():
            with self.subTest(what):
                folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
                made_up.write(folder / "site-data", self.site.boards)
                at_fault = made_up.board_file(folder / "site-data", newest["board_day"])
                made_up.write_json(at_fault, broken)
                self.assert_build_fails(folder, at_fault)
        with self.subTest("an index that gives a board day the wrong count of rows"):
            folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
            made_up.write(folder / "site-data", self.site.boards)
            at_fault = folder / "site-data" / "boards" / "index.json"
            index = json.loads(at_fault.read_text(encoding="utf-8"))
            index["board_days"][0]["row_count"] += 1
            made_up.write_json(at_fault, index)
            self.assert_build_fails(folder, at_fault)

    def assert_build_fails(self, folder: Path, at_fault: Path) -> None:
        result = the_site.build(folder / "dist", folder / "site-data")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(str(at_fault), result.stderr)
        self.assertFalse((folder / "dist").exists() and any((folder / "dist").iterdir()), "a failed build wrote pages")


if __name__ == "__main__":
    unittest.main()
