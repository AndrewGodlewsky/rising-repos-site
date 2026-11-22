"""A row explains its place on the board with figures that anyone can set against its star count, and opens on its
score and the sum behind it; a page explains in plain sentences how a board is ranked (AndrewGodlewsky/RisingRepos#49).
Since AndrewGodlewsky/RisingRepos#199 the page holds each row's line, in the disclosure that opens it, and the sum
comes with the rest of what an opened row shows, in its board day's history.json.

The example's newest board has one row for each way the page words a row: a usual pace at the floor or over it, a usual
pace under the floor, a falling one, and a row whose recent pace kept one day.
"""

import shutil
import unittest

from helpers import BuildTest, read_json, shipped, write_json

from sitebuild import BOARD, DESCRIBED_FORMULA, HOW_IT_WORKS, board_day_page, figure, times

NUMBERS = ("baseline", "divided_by", "excess", "recent_days", "recent_stars", "days_left_out", "score")
"""The fields a row's reason is read from, as the data contract names them."""

EXAMPLE_REASONS = {
    "rising-repos-example/markup-in-description": (
        "+96 above its own trend · its usual pace was under 1 star a day",
        "Score 48 = 96 stars ÷ 2 days ÷ 1: its usual 0.25 a day counts as 1 star a day.",
    ),
    "octocat/Spoon-Knife": (
        "+615 above its own trend · 26× its usual pace",
        "That multiple is its score: 640 stars ÷ 2 days ÷ its usual 12.5 a day.",
    ),
    "rising-repos-example/text-beyond-ascii": (
        "+150 in 1 day · 20× its usual pace",
        "That multiple is its score: 150 stars ÷ 1 day ÷ its usual 7.5 a day. A recent day that lost too many stars to"
        " be believed is left out.",
    ),
    "octocat/Hello-World": (
        "+30 in 2 days · it had been losing stars",
        "Score 15 = 30 stars ÷ 2 days ÷ 1: it lost 0.5 a day before, which counts as 1 star a day.",
    ),
    "rising-repos-example/no-description": (
        "+11 above its own trend · 4× its usual pace",
        "That multiple is its score: 14 stars ÷ 2 days ÷ its usual 1.75 a day.",
    ),
}
"""What each row of the example's newest board says, by its name: its line, and the sum its opened view adds."""


def reasons(page, history: dict) -> dict[str, tuple[str, str]]:
    """Each row's reason, by the repository's name: the text of its line, which the page holds, and the sum behind
    it, which the board day's history gives the opened row."""
    found = {}
    for row, entry in zip(page.rows(), history["rows"], strict=True):
        (link,) = row.all("a")
        (line,) = [p for p in row.all("p") if "ln" in p.classes()]
        found[link.text()] = (line.text(), entry["why"][0])
    return found


class TheReason(BuildTest):
    def newest(self) -> dict:
        return read_json(self.board_file())

    def shown(self, path: str = BOARD) -> dict[str, tuple[str, str]]:
        """Build, and read each row's reason on the page at `path`, a page of the newest board."""
        page = self.build_pages()[path]
        return reasons(page, read_json(self.out / board_day_page("2026-11-09").replace("index.html", "history.json")))

    def with_numbers(self, numbers: dict) -> dict:
        """The example's newest board with its first row given `numbers`, written as its file."""
        board = self.newest()
        board["rows"][0].update(numbers)
        self.write_board(board)
        return board

    def test_the_example_holds_a_row_of_each_kind_the_page_words_differently(self):
        rows = self.newest()["rows"]
        self.assertEqual({row["full_name"] for row in rows}, set(EXAMPLE_REASONS))

        def kind(row: dict) -> str:
            if row["days_left_out"]:
                return "a recent day left out"
            if row["baseline"] < 0:
                return "losing stars"
            return "under the floor" if row["baseline"] < row["divided_by"] else "at the floor or over it"

        kinds = {"a recent day left out", "losing stars", "under the floor", "at the floor or over it"}
        self.assertEqual({kind(row) for row in rows}, kinds)

    def test_each_row_says_why_it_is_on_the_board_and_opens_on_its_score_and_the_sum_behind_it(self):
        """Above the floor, the line gives the stars above its own trend and its multiple of its usual pace. Under the
        floor it gives no multiple, which would be of the floor and not of the repository's pace. After losing stars,
        and with a recent day left out, it gives the stars gained, since the stars above its own trend are not what
        the file counts there. Each opens on the sum that gives its score from the stars and the days: with the score
        written out where the line gives no multiple, and naming the multiple as the score where it does."""
        self.assertEqual(self.shown(), EXAMPLE_REASONS)

    def test_each_board_days_page_gives_the_same_reasons_as_the_root(self):
        self.assertEqual(self.shown(board_day_page("2026-11-09")), EXAMPLE_REASONS)

    def test_the_line_opens_without_a_script_and_from_the_keyboard(self):
        """A <details> opens on its <summary>, a control a browser gives a keyboard and assistive technology itself,
        named for its row. Without the script it opens on the line; the script adds the rest once its file is in."""
        for row in self.build_pages()[BOARD].rows():
            (cell,) = [cell for cell in row.all("td") if "wy" in cell.classes()]
            self.assertEqual(cell.attrs["role"], "cell")
            (details,) = cell.all("details")
            self.assertEqual(details.children[0].tag, "summary")
            self.assertEqual(details.children[0].text(), f"More on {row.all('a')[0].text()}")
            self.assertNotIn("open", details.attrs)
            self.assertEqual(len([p for p in details.all("p") if "ln" in p.classes()]), 1)

    def test_a_large_multiple_is_given_in_full_without_a_cap(self):
        """The highest score of formula 2 to 14 November 2026, on 5 October."""
        self.with_numbers(
            {
                "score": 1285.909090909091,
                "recent_stars": 4715,
                "recent_days": 2,
                "days_left_out": 0,
                "baseline": 1.8333333333333333,
                "divided_by": 1.8333333333333333,
                "excess": 4711.333333333333,
            }
        )
        line, opened = self.shown()["rising-repos-example/markup-in-description"]
        self.assertEqual(line, "+4,711 above its own trend · 1,286× its usual pace")
        self.assertEqual(opened, "That multiple is its score: 4,715 stars ÷ 2 days ÷ its usual 1.83 a day.")

    def test_the_page_works_out_no_score_and_shows_the_numbers_its_file_gives(self):
        """A score the file gives that its stars do not give is shown as the file gives it: the site only rounds."""
        self.with_numbers({"score": 99.25, "excess": 1234.5})
        line, opened = self.shown()["rising-repos-example/markup-in-description"]
        self.assertEqual(line, "+1,235 above its own trend · its usual pace was under 1 star a day")
        self.assertTrue(opened.startswith("Score 99.25 = 96 stars ÷ 2 days ÷ 1:"), opened)

    def test_a_row_whose_usual_pace_is_under_the_floor_gives_no_multiple(self):
        """However far it is above it: a multiple of the floor is no multiple of the repository's own pace."""
        self.with_numbers({"score": 640.0, "recent_stars": 1280, "baseline": 0.9166666666666666, "excess": 1278.1666666666667})
        line, _ = self.shown()["rising-repos-example/markup-in-description"]
        self.assertEqual(line, "+1,278 above its own trend · its usual pace was under 1 star a day")
        self.assertNotIn("×", line)

    def test_a_board_whose_file_predates_the_rows_numbers_builds_and_gives_no_row_a_reason(self):
        """As site-data/ holds its files until RisingRepos's publish writes every board day with the numbers."""
        schema = read_json(self.daily_schema)
        row = schema["properties"]["rows"]["items"]
        for name in NUMBERS:
            del row["properties"][name]
            row["required"].remove(name)
        write_json(self.daily_schema, schema)
        board = self.newest()
        for row in board["rows"]:
            for name in NUMBERS:
                del row[name]
        self.write_board(board)
        page = self.build_pages()[BOARD]
        self.assertEqual(len(page.rows()), len(board["rows"]))
        self.assertEqual(page.all("details"), [])
        self.assertEqual([cell for cell in page.all("td") if "wy" in cell.classes()], [])
        self.assertEqual([heading.text() for heading in page.one("thead").all("th") if "why" in heading.text()], [])
        self.assertNotIn("its usual pace", page.body_text())


class TheNumbers(unittest.TestCase):
    def test_a_number_is_rounded_half_up_as_a_reader_rounds_it_and_parts_its_thousands(self):
        cases = [
            ((10.5, 0), "11"),
            ((95.5, 0), "96"),
            ((8.125, 2), "8.13"),
            ((30.166666666666668, 2), "30.17"),
            ((260.0, 2), "260"),
            ((0.25, 2), "0.25"),
            ((87779.66666666667, 0), "87,780"),
        ]
        for (value, places), shown in cases:
            with self.subTest(value=value, places=places):
                self.assertEqual(figure(value, places), shown)

    def test_a_multiple_takes_one_decimal_place_under_10_and_none_from_10(self):
        cases = [(3.0, "3"), (4.45, "4.5"), (8.63, "8.6"), (9.94, "9.9"), (9.96, "10"), (25.6, "26"), (1285.9, "1,286")]
        for score, shown in cases:
            with self.subTest(score):
                self.assertEqual(times(score), shown)


class HowItWorks(BuildTest):
    def page(self):
        return self.build_pages()[HOW_IT_WORKS]

    def test_it_says_in_plain_sentences_how_the_formula_ranks_a_board(self):
        """The two recent days against the twelve before them, the floor, what a repository needs to be scored, and
        that every gain counts, with a large, flat project's gain of about 100 stars in a day as the example."""
        text = self.page().one("main").text()
        for words in (
            "the board day and the day before it",
            "across the twelve days before those two",
            "A usual pace under 1 star a day counts as 1",
            "its score is 3 or more",
            "at least 10 for a repository with fewer than 1,000 stars, 20 for one with fewer than 10,000",
            "its first count must be fourteen or more days older than the board day",
            "at least one of the two recent days and seven of the twelve before them must be left",
            "Nothing is filtered out.",
            "gains about 100 stars in a day is listed too",
            "more than 150 stars, and more than 3% of the repository's stars",
            "this site only rounds them",
        ):
            with self.subTest(words):
                self.assertIn(words, text)

    def test_it_names_the_formula_it_describes(self):
        (line,) = [p for p in self.page().one("main").all("p") if "formula" in p.classes()]
        self.assertEqual(line.text(), f"How formula version {DESCRIBED_FORMULA} ranks a board.")

    def test_it_says_first_when_the_newest_board_was_ranked_by_a_formula_it_does_not_describe(self):
        self.assertEqual([p for p in self.page().all("p") if "provisional" in p.classes()], [])
        board = read_json(self.board_file())
        write_json(self.board_file(), {**board, "formula_version": DESCRIBED_FORMULA + 1})
        shutil.rmtree(self.out)  # built above
        (note,) = [p for p in self.page().all("p") if "provisional" in p.classes()]
        self.assertEqual(
            note.text(),
            f"The newest board was ranked by formula version {DESCRIBED_FORMULA + 1}, which this page does not"
            f" describe. It describes version {DESCRIBED_FORMULA}.",
        )

    def test_it_leads_back_to_the_boards_and_its_one_script_is_the_theme_alone(self):
        """The theme switch, in the site's bar, is on every page. The page runs nothing else and fetches nothing."""
        page = self.page()
        self.assertIn(("/", "The newest board"), page.links())
        self.assertIn(("/days/", "History"), page.links())
        (script,) = page.all("script")
        self.assertEqual("".join(script.children), shipped("theme.js"))
        self.assertNotIn("connect-src", page.directives())


if __name__ == "__main__":
    unittest.main()
