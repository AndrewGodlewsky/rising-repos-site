"""The page's account of the rows a board went without, read from the fields AndrewGodlewsky/RisingRepos#13 added to a
board day's file: its state, the star bands it holds back with the star counts its own day's snapshot missed, and each
day the ranking needed and lacked, with how many repositories that day kept from it. The site decides none of these.

The made-up boards below follow the shapes of real board days: 2026-07-31, whose snapshot held only its lowest star
counts; 2026-08-02, which came two days later; and 2026-09-04, whose ranking needed 2026-09-02, of which no snapshot
was kept."""

import unittest

from helpers import BuildTest, read_json, write_json

from sitebuild import BOARD, board_day_page, star_run

NEWEST, OLDER = "2026-11-09", "2026-11-08"
HOLD_FIELDS = ("state", "holds", "missed_stars", "unranked")
EVERY_BAND = [
    {"least_stars": 200, "most_stars": 999},
    {"least_stars": 1000, "most_stars": 2999},
    {"least_stars": 3000, "most_stars": 9999},
    {"least_stars": 10000, "most_stars": 29999},
    {"least_stars": 30000, "most_stars": None},
]


class Notes(BuildTest):
    def parts(self, page) -> list:
        """What a board says of itself: the notes that change how it reads, above its rows, and About this board,
        its plain facts, at its foot (AndrewGodlewsky/RisingRepos#199)."""
        return [element for element in page.one("main").all() if {"notes", "about"} & set(element.classes())]

    def notes(self, page, kind: str) -> list:
        """What it says of one kind: each <p class="`kind`"> in those."""
        return [element for part in self.parts(page) for element in part.all("p") if kind in element.classes()]

    def said(self, page) -> str:
        return " ".join(part.text() for part in self.parts(page))

    def state(self, page) -> str | None:
        (about,) = [element for element in page.all("section") if "about" in element.classes()]
        return about.attrs.get("data-state")

    def message(self, page) -> str:
        (message,) = [element for element in page.all("div") if "message" in element.classes()]
        return message.text()

    def older(self, **fields) -> object:
        """Build with the example's older board given `fields`, and read its page."""
        board = read_json(self.board_file(OLDER))
        write_json(self.board_file(OLDER), {**board, **fields})
        return self.build_pages()[board_day_page(OLDER)]


class HeldBands(Notes):
    def test_a_held_board_says_which_band_it_holds_back_and_which_star_counts_its_own_snapshot_missed(self):
        """The example's newest board, whose snapshot missed 2,006 to 2,051 stars: it holds back one band, and its
        five rows all come from the others."""
        page = self.build_pages()[BOARD]
        (note,) = self.notes(page, "held")
        self.assertEqual(
            note.text(),
            "One star band is held back. This day's snapshot missed repositories of 2,006 to 2,051 stars, so the board "
            "leaves out every repository of 1,000 to 2,999 stars rather than rank that band from part of its "
            "repositories.",
        )
        self.assertEqual([strong.text() for strong in note.all("strong")], ["One star band is held back."])
        self.assertEqual(self.state(page), "held")
        self.assertEqual(len(page.rows()), 5)

    def test_a_board_that_holds_every_band_names_each_and_says_no_repository_is_on_it(self):
        page = self.older(
            state="held",
            holds=EVERY_BAND,
            missed_stars=[{"least_stars": 309, "most_stars": None}],
            partial_days=[{"snapshot_day": OLDER, "recent": True}],
        )
        (note,) = self.notes(page, "held")
        self.assertEqual(
            note.text(),
            "5 star bands are held back. This day's snapshot missed repositories of 309 or more stars, so the board "
            "leaves out every repository of 200 to 999, 1,000 to 2,999, 3,000 to 9,999, 10,000 to 29,999, or "
            "30,000 or more stars rather than rank those bands from part of their repositories.",
        )
        self.assertEqual(self.message(page), "No repository is on this board. It holds back the star bands named above.")
        self.assertEqual(self.notes(page, "recent"), [], "the hold says what the board day's own snapshot did")
        self.assertEqual(self.state(page), "held")

    def test_runs_of_missed_star_counts_are_each_named_lowest_first_and_a_run_of_one_count_as_that_count(self):
        page = self.older(
            state="held",
            holds=EVERY_BAND[:2],
            missed_stars=[{"least_stars": 702, "most_stars": 709}, {"least_stars": 2000, "most_stars": 2000}],
        )
        (note,) = self.notes(page, "held")
        self.assertIn("missed repositories of 702 to 709 and 2,000 stars, so", note.text())
        self.assertIn("of 200 to 999 or 1,000 to 2,999 stars rather than rank those bands", note.text())
        self.assertEqual(
            [star_run(run) for run in EVERY_BAND[3:]] + [star_run({"least_stars": 281, "most_stars": 281})],
            ["10,000 to 29,999", "30,000 or more", "281"],
        )


class UnrankedRepositories(Notes):
    def test_a_day_the_ranking_needed_that_was_partial_says_how_many_repositories_could_not_be_ranked(self):
        """The example's newest board: 7 November, two days before it, kept 2,183 repositories from the ranking."""
        (note,) = self.notes(self.build_pages()[BOARD], "unranked")
        self.assertEqual(
            note.text(),
            "2,183 repositories could not be ranked. The ranking needs each repository's stars on 7 November 2026, "
            "and that day's snapshot missed them, so they are not on this board.",
        )
        self.assertEqual([strong.text() for strong in note.all("strong")], ["2,183 repositories could not be ranked."])

    def test_a_day_that_kept_one_repository_from_the_ranking_says_so_in_the_singular(self):
        page = self.older(unranked=[{"snapshot_day": "2026-11-06", "status": "partial", "repositories": 1}])
        (note,) = self.notes(page, "unranked")
        self.assertEqual(
            note.text(),
            "1 repository could not be ranked. The ranking needs each repository's stars on 6 November 2026, and that "
            "day's snapshot missed it, so it is not on this board.",
        )

    def test_a_partial_day_that_kept_none_from_the_ranking_is_a_plain_line(self):
        page = self.older(unranked=[{"snapshot_day": "2026-11-06", "status": "partial", "repositories": 0}])
        self.assertEqual(self.notes(page, "unranked"), [])
        (line,) = self.notes(page, "partial")
        self.assertEqual(
            line.text(),
            "The ranking needs each repository's stars on 6 November 2026, whose snapshot missed some repositories, "
            "though none it could otherwise have ranked.",
        )
        self.assertEqual(line.classes(), ["partial"])

    def test_an_empty_board_two_days_after_a_missing_day_says_no_repository_could_be_ranked_not_that_none_rose(self):
        """As 2026-09-04's board: 2026-09-02 kept no snapshot, so nothing could be ranked."""
        page = self.older(unranked=[{"snapshot_day": "2026-11-06", "status": "missing", "repositories": 269078}])
        (note,) = self.notes(page, "unranked")
        self.assertEqual(
            note.text(),
            "No repository could be ranked. The ranking needs each repository's stars on 6 November 2026, and no "
            "snapshot was kept that day, so none of the 269,078 repositories it could otherwise have ranked is on "
            "this board.",
        )
        self.assertEqual(
            self.message(page),
            "No repository could be ranked on this day. A day the ranking needs has no snapshot, as the note above says.",
        )
        self.assertNotIn("made the board", self.message(page))
        self.assertEqual(self.state(page), "empty")

    def test_an_empty_board_after_a_partial_day_says_none_that_could_be_ranked_made_it(self):
        """As 2026-08-02's board, two days after 2026-07-31 (AndrewGodlewsky/RisingRepos#137's second check)."""
        page = self.older(unranked=[{"snapshot_day": "2026-11-06", "status": "partial", "repositories": 120369}])
        (note,) = self.notes(page, "unranked")
        self.assertTrue(note.text().startswith("120,369 repositories could not be ranked."), note.text())
        self.assertEqual(
            self.message(page),
            "No repository that could be ranked made the board on this day. The note above says how many could not "
            "be. A repository makes the board when it gains stars faster than its own pace predicts.",
        )

    def test_an_empty_board_that_held_nothing_and_lacked_no_day_says_nothing_rose(self):
        """The example's older board."""
        page = self.build_pages()[board_day_page(OLDER)]
        self.assertEqual(
            self.message(page),
            "No repository made the board on this day. A repository makes the board when it gains stars faster than "
            "its own pace predicts.",
        )
        self.assertEqual((self.notes(page, "held"), self.notes(page, "unranked")), ([], []))
        self.assertEqual(self.state(page), "empty")


class RecentPartialDays(Notes):
    def test_a_recent_partial_day_that_kept_no_repository_from_the_ranking_is_named_without_a_warning(self):
        """AndrewGodlewsky/RisingRepos#137's first criterion: the file names the days that left repositories off, so a
        recent day it does not name gets a plain line that guesses at nothing, as 2026-10-28's board needs."""
        page = self.older(
            partial_days=[{"snapshot_day": "2026-11-07", "recent": True}],
            unranked=[],
        )
        (line,) = self.notes(page, "partial")
        self.assertEqual(line.classes(), ["partial"])
        self.assertEqual(
            line.text(), "The ranking's recent pace takes in 7 November 2026, whose snapshot missed some repositories."
        )
        self.assertNotIn("may", self.said(page))
        self.assertNotIn("left out", self.said(page))

    def test_a_recent_partial_day_that_the_file_names_as_lacked_is_said_once_as_the_repositories_it_kept_off(self):
        """The example's newest board reads 7 November for its recent pace, and its file names that day as one that
        kept 2,183 repositories from the ranking: the page says that, and not that a repository may have moved."""
        said = self.said(self.build_pages()[BOARD])
        self.assertEqual(said.count("7 November 2026"), 1)
        self.assertNotIn("may sit higher or lower", said)

    def test_a_board_whose_file_predates_the_fields_names_no_state_and_no_hold(self):
        self.drop_fields(*HOLD_FIELDS)
        for path, page in self.build_pages().items():
            if not path.startswith(("index", "days/2026")):
                continue
            with self.subTest(path):
                self.assertEqual((self.notes(page, "held"), self.notes(page, "unranked")), ([], []))
                self.assertIsNone(self.state(page))
                self.assertNotIn("held back", page.body_text())


if __name__ == "__main__":
    unittest.main()
