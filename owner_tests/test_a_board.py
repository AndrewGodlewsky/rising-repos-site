"""A board: what the root and each board day's page show a reader. Sentences 1 to 6 of the owner's tests."""

import re
import unittest
from datetime import date

from playwright.sync_api import expect

from owner_tests.scenario import (
    Scenario,
    board,
    column,
    heading,
    names,
    needs_made_up_boards,
    number,
    opener,
    reason,
    rows,
    the_day,
)

NOTES = {
    "an earlier board": re.compile(r"An earlier board"),
    "a provisional ranking": re.compile(r"The ranking is provisional"),
    "a star band held back": re.compile(r"star bands? (is|are) held back"),
    "repositories that could not be ranked": re.compile(r"repositor(y|ies) could not be ranked"),
}
"""What a board says above its rows, for each thing that changes how it reads."""


class ABoard(Scenario):
    @needs_made_up_boards
    def test_the_root_shows_the_newest_board_with_every_repository_its_file_lists_in_the_files_order(self):
        """Sentence 1. The root's heading names the newest board day, and its rows are the file's rows, in the file's
        order, each with the rank, the day's gain, and the total stars the file gives it."""
        newest = self.site.boards[0]
        page = self.reader()
        self.visit(page)
        self.assertEqual(the_day(heading(page).inner_text()), date.fromisoformat(newest["board_day"]))
        expect(rows(page)).to_have_count(len(newest["rows"]))
        self.assertEqual(names(page), [row["full_name"] for row in newest["rows"]])
        self.assertEqual(column(page, "Rank"), [str(row["rank"]) for row in newest["rows"]])
        self.assertEqual(
            [number(gain) for gain in column(page, "Stars gained")], [row["gained_1_day"] for row in newest["rows"]]
        )
        self.assertEqual(
            [number(stars) for stars in column(page, "Total stars")], [row["stars"] for row in newest["rows"]]
        )

    @needs_made_up_boards
    def test_every_board_day_that_was_published_has_a_page_at_its_own_address(self):
        """Sentence 2. Each board day in the index answers at /days/<board day>/ with the board of that day: its
        heading names the day, and it lists as many rows as the day's file holds."""
        page = self.reader()
        for published in self.site.boards:
            with self.subTest(published["board_day"]):
                answer = self.visit(page, f"/days/{published['board_day']}/")
                self.assertEqual(answer.status, 200)
                self.assertEqual(the_day(heading(page).inner_text()), date.fromisoformat(published["board_day"]))
                expect(rows(page)).to_have_count(len(published["rows"]))

    def test_a_row_gives_its_rank_its_name_linked_to_github_the_stars_it_gained_on_the_day_and_its_total_stars(self):
        """Sentence 3. Every row of the newest board: its rank is its place, its name reads owner/name and leads to
        that repository on GitHub, its gain on the day is a figure with its sign, or a dash where there is no count,
        and its total is a figure."""
        page = self.reader()
        self.visit(page)
        listed = names(page)
        self.given(listed, "the newest board lists no repository")
        self.assertEqual(column(page, "Rank"), [str(place) for place in range(1, len(listed) + 1)])
        links = board(page).get_by_role("rowheader").get_by_role("link")
        self.assertEqual(
            links.evaluate_all("links => links.map(link => link.href)"),
            [f"https://github.com/{name}" for name in listed],
        )
        for name, gain, stars in zip(listed, column(page, "Stars gained"), column(page, "Total stars"), strict=True):
            with self.subTest(name):
                self.assertRegex(name, r"^[\w.-]+/[\w.-]+$")
                self.assertRegex(gain, r"^([+−-]?[\d,]+|[–—-])$")
                self.assertRegex(stars, r"^[\d,]+$")

    def test_a_row_opens_on_the_reason_it_is_on_the_board_with_scripts_on_or_off(self):
        """Sentence 4. The first row's reason does not show until the row is opened, and then it does: with scripts
        on, with scripts off, and with scripts on when nothing the page asks for after it has loaded arrives, which is
        how the history an opened row fetches fails."""
        for scripts in (True, False):
            with self.subTest(scripts=scripts):
                page = self.reader(scripts=scripts)
                self.visit(page)
                self.given(rows(page).count(), "the newest board lists no repository")
                expect(reason(rows(page).first)).to_be_hidden()
                opener(rows(page).first).click()
                expect(reason(rows(page).first)).to_be_visible()
        with self.subTest("the history does not arrive"):
            page = self.reader()
            page.route(
                "**/*",
                lambda route: route.continue_() if route.request.resource_type == "document" else route.abort(),
            )
            self.visit(page)
            opener(rows(page).first).click()
            expect(reason(rows(page).first)).to_be_visible()

    @needs_made_up_boards
    def test_a_board_says_above_its_rows_when_it_is_earlier_provisional_holds_a_band_back_or_could_not_rank_some(self):
        """Sentence 5. A board says above its rows when it is an earlier board, when its ranking is provisional, when
        a star band is held back, and when repositories could not be ranked. Each is looked for on a made-up board
        that has it, above that board's first row, and the newest board, which has none of the four, says none."""
        newest, *earlier = self.site.boards
        told = {
            "an earlier board": earlier[0],
            "a provisional ranking": next(listed for listed in earlier if listed["score_provisional"]),
            "a star band held back": next(listed for listed in earlier if listed["holds"] and listed["rows"]),
            "repositories that could not be ranked": next(
                listed for listed in earlier if listed["unranked"] and listed["rows"]
            ),
        }
        page = self.reader()
        for what, listed in told.items():
            with self.subTest(what):
                self.visit(page, f"/days/{listed['board_day']}/")
                note = page.get_by_role("main").get_by_text(NOTES[what])
                expect(note).to_be_visible()
                foot = note.bounding_box()
                self.assertLessEqual(foot["y"] + foot["height"], rows(page).first.bounding_box()["y"])
        self.visit(page)
        for what, words in NOTES.items():
            with self.subTest(what, board="the newest"):
                expect(page.get_by_role("main").get_by_text(words)).to_have_count(0)

    @needs_made_up_boards
    def test_a_board_with_no_rows_says_why(self):
        """Sentence 6. The made-up boards hold three with no rows, each for its own cause: nothing rose, a star band
        is held back, and a day the ranking needs has no snapshot. Each one's page says that it lists no repository,
        and which of those is why."""
        page = self.reader()
        empty = [listed for listed in self.site.boards if not listed["rows"]]
        self.assertEqual(len(empty), 3)
        for listed in empty:
            if listed["holds"]:
                none, why = r"No repository is on this board", r"holds back the star bands? named above"
            elif listed["unranked"]:
                none, why = r"No repository could be ranked on this day", r"A day the ranking needs has no snapshot"
            else:
                none, why = r"No repository made the board on this day", r"faster than its own pace predicts"
            with self.subTest(listed["board_day"]):
                self.visit(page, f"/days/{listed['board_day']}/")
                expect(rows(page)).to_have_count(0)
                expect(page.get_by_role("main").get_by_text(re.compile(none))).to_be_visible()
                expect(page.get_by_role("main").get_by_text(re.compile(why))).to_be_visible()


if __name__ == "__main__":
    unittest.main()
