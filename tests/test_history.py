"""What the board days say about each other, worked out at build time from the lists the files hold
(AndrewGodlewsky/RisingRepos#199): each board day's history.json, which an opened row reads, and what is New.

The history follows a repository by its GitHub id, which a rename or a transfer keeps, so its boards stay whole. New
goes by name: a repository whose name, in any case, was on no earlier board is new, so a renamed one is new under its
new name and still lists the boards it was on before. The site computes no score and no rank: it compares lists, and
words each figure as the page's own cells word it."""

import unittest

from helpers import BuildTest, read_json

from sitebuild import BOARD, HISTORY_WINDOW, History, board_day_page, figure, growth, history_file, rounded, times, why

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


class TheHistoryFile(Boards):
    def test_it_lists_its_board_days_oldest_first_ending_with_its_own_and_each_row_the_boards_that_listed_it(self):
        """Each board that listed a row gives [the day's place in `days`, its rank, its stars, its recent stars, its
        recent days, its multiple as the growth column words it or None, its score as stars a day to one place]."""
        rows = self.newest_rows()
        self.earlier(rows[1:3])
        self.build_pages()
        history = self.history()
        self.assertEqual(history["days"], [OLDER, NEWEST])
        self.assertEqual([entry["first"] for entry in history["rows"]], [NEWEST, OLDER, OLDER, NEWEST, NEWEST])
        spoon_knife = history["rows"][1]
        self.assertEqual(spoon_knife["on"], [[0, 1, 13250, 640, 2, "26", "25.6"], [1, 2, 13250, 640, 2, "26", "25.6"]])
        for row, entry in zip(rows, history["rows"], strict=True):
            with self.subTest(row["full_name"]):
                multiple = times(row["score"]) if row["baseline"] >= row["divided_by"] else None
                self.assertEqual(entry["on"][-1], [1, row["rank"], row["stars"], row["recent_stars"], row["recent_days"],
                                                   multiple, figure(row["score"], 1)])
                self.assertNotIn("was", entry)

    def test_each_row_gives_its_drawing_its_detail_its_star_history_its_gains_and_its_facts_from_the_file(self):
        """`pace`: its baseline a day, its recent stars and days, and its stars above its own trend, or None when a
        day was left out or its pace was falling, which the drawing does not show as above a trend."""
        self.build_pages()
        for row, entry in zip(self.newest_rows(), self.history()["rows"], strict=True):
            with self.subTest(row["full_name"]):
                kept = not row["days_left_out"] and row["baseline"] >= 0
                self.assertEqual(entry["pace"], [float(figure(row["baseline"], 2)), row["recent_stars"], row["recent_days"],
                                                 int(rounded(row["excess"], 0)) if kept else None])
                grew = growth(row)
                self.assertEqual(entry["why"], [why(row)["detail"], grew["multiple"] or "None: " + grew["note"], row["language"]])
                self.assertEqual(entry["stars"], row["star_history"])
                self.assertEqual(len(entry["stars"]), 31)
                self.assertEqual(entry["gains"], [row["gained_7_days"], row["gained_30_days"]])
                self.assertEqual(entry["about"], [row["license"], row["created_at"], row["pushed_at"]])
        paces = [entry["pace"][3] for entry in self.history()["rows"]]
        self.assertEqual(paces, [96, 615, None, None, 11])  # a day left out, and a falling pace, give none

    def test_a_row_renamed_since_an_earlier_board_gives_the_name_it_was_listed_under_and_keeps_its_boards(self):
        rows = self.newest_rows()
        self.earlier([{**rows[1], "full_name": "octocat/Spork-Knife"}])
        self.build_pages()
        entry = self.history()["rows"][1]
        self.assertEqual(entry["was"], "octocat/Spork-Knife")
        self.assertEqual([on[0] for on in entry["on"]], [0, 1])
        self.assertEqual(entry["first"], OLDER)

    def test_it_covers_the_last_thirty_board_days_and_a_row_off_a_board_has_no_entry_for_it(self):
        """So the chart leaves a gap, never a zero."""
        boards = [
            {"board_day": f"2026-{10 + (40 - number) // 31:02d}-{(40 - number) % 31 + 1:02d}",
             "rows": [{"rank": 1, "github_id": 7, "full_name": "o/r", "stars": 500 + number}] if number % 2 == 0 else []}
            for number in range(40)
        ]
        file = history_file(boards, History(boards), 0)
        self.assertEqual(HISTORY_WINDOW, 30)
        self.assertEqual(file["days"], [board["board_day"] for board in reversed(boards[:30])])
        (entry,) = file["rows"]
        self.assertEqual([on[0] for on in entry["on"]], list(range(1, 30, 2)))
        self.assertEqual(entry["on"][-1], [29, 1, 500, None, None, None, None])
        self.assertEqual(entry["first"], boards[38]["board_day"])  # by its id, before the window too


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
        self.assertNotIn("was", entry)

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
