"""What the board days say about each other, worked out at build time from the lists the files hold
(AndrewGodlewsky/RisingRepos#199): each board day's history.json, which an opened row reads, and what is New.

The history follows a repository by its GitHub id, which a rename or a transfer keeps, so its boards stay whole. New
goes by name: a repository whose name, in any case, was on no earlier board is new, so a renamed one is new under its
new name and still lists the boards it was on before. The site computes no score and no rank: it compares lists, and
words each figure as the page's own cells word it."""

import unittest

from helpers import BuildTest, read_json

from sitebuild import (BOARD, HISTORY_WINDOW, MINUS, History, board_day_page, day_name, drawing_words, figure,
                       gain_class, growth, history_file, month_words, per_day, rounded, short_date, times, why)

NEWEST, OLDER = "2026-11-09", "2026-11-08"


class Boards(BuildTest):
    def newest_rows(self) -> list[dict]:
        return read_json(self.board_file())["rows"]

    def earlier(self, rows: list[dict], **fields) -> None:
        """Make the example's older board, empty in the example, a board that lists `rows`, ranked in their order."""
        board = read_json(self.board_file(OLDER))
        ranked = [{**row, "rank": rank} for rank, row in enumerate(rows, start=1)]
        self.write_board({**board, "state": "rows", **fields, "rows": ranked})

    def history(self, day: str = NEWEST) -> dict:
        return read_json(self.out / board_day_page(day).replace("index.html", "history.json"))

    def new_marks(self, page) -> list[str]:
        """The repositories the board marks New, by name."""
        return [row.all("a")[0].text() for row in page.rows() if any("new" in mark.classes() for mark in row.all("b"))]


def told(entry: dict) -> dict[str, str]:
    """An opened row's facts, by their terms."""
    return {fact[0]: fact[1] for fact in entry["facts"]}


class TheHistoryFile(Boards):
    def test_it_lists_its_board_days_oldest_first_ending_with_its_own_and_each_row_the_boards_that_listed_it(self):
        """Each board that listed a row gives [the day's place in `days`, its rank, its stars, its stars a day over its
        recent days, the class that colours those, its multiple], each worded as that board's own cells word it."""
        rows = self.newest_rows()
        self.earlier(rows[1:3])
        self.build_pages()
        history = self.history()
        self.assertEqual(history["days"], [OLDER, NEWEST])
        self.assertEqual(history["dates"], [["8 Nov", "8 Nov 2026"], ["9 Nov", "9 Nov 2026"]])
        firsts = [told(entry)["First on a board"] for entry in history["rows"]]
        self.assertEqual(firsts, ["This board", "8 Nov 2026", "8 Nov 2026", "This board", "This board"])
        spoon_knife = history["rows"][1]
        self.assertEqual(spoon_knife["on"], [[0, 1, "13,250", "+320", "", "26\N{MULTIPLICATION SIGN}"],
                                             [1, 2, "13,250", "+320", "", "26\N{MULTIPLICATION SIGN}"]])
        for row, entry in zip(rows, history["rows"], strict=True):
            with self.subTest(row["full_name"]):
                pace = row["recent_stars"] / row["recent_days"]
                self.assertEqual(entry["on"][-1], [1, row["rank"], f"{row['stars']:,}", per_day(row),
                                                   gain_class(pace).strip(), growth(row)["multiple"] or "\N{EM DASH}"])
                self.assertNotIn("Listed before as", told(entry))

    def test_each_row_gives_its_facts_its_sum_and_the_words_and_numbers_of_its_drawings_from_the_file(self):
        """The script places what the file words and writes no figure of its own, so an opened row says what the
        board says, in its words. `pace` is what the drawing's lines are drawn from: the baseline a day to two places,
        the recent stars, and the recent days."""
        self.build_pages()
        rows, entries = self.newest_rows(), self.history()["rows"]
        self.assertEqual(entries[0]["facts"], [
            ["Multiple", "None: baseline under 1 a day"], ["Gained in 7 days", "+97"], ["Gained in 30 days", "Not known"],
            ["Language", "TypeScript"], ["Licence", "MIT"], ["Star band", "200\N{EN DASH}1k"], ["Created", "18 Oct 2026"],
            ["Last pushed", "9 Nov 2026"], ["First on a board", "This board"], ["On the last 2 boards", "1 of 2"],
            ["Best rank in them", "1"],
        ])
        self.assertEqual(entries[0]["said"], [
            "+96 above its own trend", "At its own pace: +0.5", "Usual pace, 0.25 a day",
            "Over the 12 days before, its usual pace was 0.25 stars a day. Over the last 2 days it gained 96, where its "
            "own pace would have given 0.5: 96 above its own trend.",
        ])
        for row, entry in zip(rows, entries, strict=True):
            with self.subTest(row["full_name"]):
                self.assertEqual(entry["pace"], [float(rounded(row["baseline"], 2)), row["recent_stars"], row["recent_days"]])
                self.assertEqual(entry["sum"], why(row)["detail"])
                self.assertEqual(entry["stars"], row["star_history"])
                self.assertEqual(len(entry["stars"]), 31)
                self.assertEqual(told(entry)["Multiple"], growth(row)["multiple"] or "None: " + growth(row)["note"])
                self.assertEqual(told(entry)["Licence"], row["license"] or "None given")
                self.assertIn(f"Usual pace, {figure(row['baseline'], 2)} a day", entry["said"])
        # A day left out, or a falling pace, is not above its own trend: it gives what it gained instead.
        self.assertEqual([entry["said"][0].endswith("above its own trend") for entry in entries], [True, True, False, False, True])

    def test_a_falling_pace_is_written_with_the_true_minus_and_its_own_pace_takes_no_plus(self):
        """AndrewGodlewsky/RisingRepos#199: every figure below 0 takes the true minus."""
        (row,) = [row for row in self.newest_rows() if row["baseline"] < 0]
        pace, said = drawing_words(row)
        usual, own = figure(-pace[0], 2), times(-pace[2] * pace[0])
        self.assertEqual(said[1:3], [f"At its own pace: {MINUS}{own}", f"Usual pace, {MINUS}{usual} a day"])
        self.assertIn(f"its usual pace was {MINUS}{usual} stars a day", said[3])
        self.assertTrue(said[3].endswith(f"would have given {MINUS}{own}."), said[3])
        _, said = drawing_words({**row, "recent_stars": -13})
        self.assertEqual(said[0], f"{MINUS}13 in {row['recent_days']} days")
        self.assertIn(f"it gained {MINUS}13,", said[3])

    def test_a_row_gives_the_words_of_its_line_of_stars_over_a_month_and_none_without_two_counts(self):
        counts = [None] * 10 + [380, 381] + [None] + list(range(382, 400))
        self.assertEqual(len(counts), 31)
        self.assertEqual(month_words(counts, NEWEST), [
            "20 Oct: 380", "9 Nov: 399",
            "From 380 stars on 20 Oct 2026 to 399 on 9 Nov 2026, with 11 days uncounted.",
        ])
        self.assertEqual(month_words([None] * 30 + [5], NEWEST), None)
        self.assertEqual(month_words(list(range(31)), NEWEST)[2], "From 0 stars on 10 Oct 2026 to 30 on 9 Nov 2026.")

    def test_a_row_renamed_since_an_earlier_board_gives_the_name_it_was_listed_under_and_keeps_its_boards(self):
        rows = self.newest_rows()
        self.earlier([{**rows[1], "full_name": "octocat/Spork-Knife"}])
        self.build_pages()
        entry = self.history()["rows"][1]
        self.assertEqual(told(entry)["Listed before as"], "octocat/Spork-Knife")
        self.assertEqual([on[0] for on in entry["on"]], [0, 1])
        self.assertEqual(told(entry)["First on a board"], "8 Nov 2026")

    def test_a_rename_older_than_the_thirty_board_days_is_still_named(self):
        """A renamed repository is New, and its opened row gives the name it had before, however long ago
        (AndrewGodlewsky/RisingRepos#199). Of the 125 renames across site-data/'s boards on 21 November 2026, 67 came
        back more than 29 boards after the name before."""
        boards = [
            {"board_day": f"2026-{10 + (40 - number) // 31:02d}-{(40 - number) % 31 + 1:02d}",
             "rows": [{"rank": 1, "github_id": 7, "full_name": "o/new" if number < 5 else "o/old", "stars": 500}]
             if number in (0, 1, 38) else []}
            for number in range(40)
        ]
        history = History(boards)
        (entry,) = history_file(boards, history, 0)["rows"]
        self.assertEqual(told(entry)["Listed before as"], "o/old")
        self.assertEqual([on[0] for on in entry["on"]], [28, 29])  # the boards in the window, by its id
        self.assertEqual(told(entry)["First on a board"], day_name(boards[38]["board_day"]))
        (entry,) = history_file(boards, history, 1)["rows"]
        self.assertEqual(told(entry)["Listed before as"], "o/old")
        self.assertIsNone(history.was(38, boards[38]["rows"][0]))

    def test_it_covers_the_last_thirty_board_days_and_a_row_off_a_board_has_no_entry_for_it(self):
        """So the chart leaves a gap, never a zero. A listing without a score gives a dash for what that board did
        not give, in the second ink."""
        boards = [
            {"board_day": f"2026-{10 + (40 - number) // 31:02d}-{(40 - number) % 31 + 1:02d}",
             "rows": [{"rank": 1, "github_id": 7, "full_name": "o/r", "stars": 500 + number}] if number % 2 == 0 else []}
            for number in range(40)
        ]
        file = history_file(boards, History(boards), 0)
        self.assertEqual(HISTORY_WINDOW, 30)
        self.assertEqual(file["days"], [board["board_day"] for board in reversed(boards[:30])])
        self.assertEqual(file["dates"], [[short_date(day), day_name(day)] for day in file["days"]])
        (entry,) = file["rows"]
        self.assertEqual([on[0] for on in entry["on"]], list(range(1, 30, 2)))
        self.assertEqual(entry["on"][-1], [29, 1, "500", "\N{EM DASH}", "nil", "\N{EM DASH}"])
        self.assertEqual(told(entry)["First on a board"], day_name(boards[38]["board_day"]))  # by its id, before the window
        self.assertEqual(told(entry)["On the last 30 boards"], "15 of 30")
        self.assertNotIn("sum", entry)


class New(Boards):
    def test_a_repository_whose_name_was_on_no_earlier_board_is_new_and_the_board_counts_them(self):
        rows = self.newest_rows()
        self.earlier(rows[1:3])
        page = self.build_pages()[BOARD]
        new = [row["full_name"] for row in rows if row not in rows[1:3]]
        self.assertEqual(self.new_marks(page), new)
        (count,) = [span for span in page.all("span") if span.attrs.get("id") == "count-new"]
        self.assertEqual(count.text(), "3")
        (button,) = [button for button in page.all("button") if button.attrs.get("data-kind") == "new"]
        self.assertEqual(button.attrs["aria-describedby"], "new-means")
        (means,) = [p for p in page.all("p") if p.attrs.get("id") == "new-means"]
        self.assertEqual(
            means.text(),
            "3 new. New means under a name on none of the boards before this one, back to the first on 8 November 2026. "
            "A repository renamed or moved since counts as new, and its opened row still lists the boards it was on "
            "before.",
        )

    def test_new_goes_by_name_so_a_renamed_repository_is_new_and_a_name_seen_in_another_case_is_not(self):
        rows = self.newest_rows()
        self.earlier([{**rows[1], "full_name": "octocat/Spork-Knife"}, {**rows[3], "full_name": "OCTOCAT/hello-world"}])
        page = self.build_pages()[BOARD]
        self.assertIn("octocat/Spoon-Knife", self.new_marks(page))
        self.assertNotIn("octocat/Hello-World", self.new_marks(page))

    def test_a_name_another_repository_held_is_not_new_and_the_history_does_not_join_the_two(self):
        rows = self.newest_rows()
        self.earlier([{**rows[0], "github_id": 42}])
        page = self.build_pages()[BOARD]
        self.assertNotIn(rows[0]["full_name"], self.new_marks(page))
        entry = self.history()["rows"][0]
        self.assertEqual([on[0] for on in entry["on"]], [1])
        self.assertNotIn("Listed before as", told(entry))

    def test_what_is_new_cannot_be_told_after_a_board_that_held_a_band_or_listed_nothing_or_on_the_first(self):
        """The example's older board is empty. A held board left whole bands off, so a repository missing from it
        may have been kept off. The first board has no board before it at all."""
        rows = self.newest_rows()
        for case, change in (("empty", None), ("held", True)):
            with self.subTest(case):
                if change:
                    board = read_json(self.board_file())
                    self.earlier(rows[1:2], holds=board["holds"], missed_stars=board["missed_stars"], state="held")
                pages = self.build_pages()
                page = pages[BOARD]
                self.assertEqual(self.new_marks(page), [])
                self.assertEqual([button for button in page.all("button") if button.attrs.get("data-kind") == "new"], [])
                (means,) = [p for p in page.all("p") if p.attrs.get("id") == "new-means"]
                self.assertTrue(means.text().startswith("What is new on this board cannot be told"), means.text())
                self.out.rename(self.out.with_name(f"dist-{case}"))
        first = self.build_pages()[board_day_page(OLDER)]
        self.assertEqual([p for p in first.all("p") if p.attrs.get("id") == "new-means"], [])

    def test_a_rows_count_of_recent_boards_is_by_its_id_for_the_most_often_order(self):
        rows = self.newest_rows()
        self.earlier([{**rows[1], "full_name": "octocat/Spork-Knife"}, rows[2]])
        page = self.build_pages()[BOARD]
        self.assertEqual([row.attrs["data-o"] for row in page.rows()], ["1", "2", "2", "1", "1"])


if __name__ == "__main__":
    unittest.main()
