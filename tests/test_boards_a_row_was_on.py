"""What the boards say of each other: how long a row has been on the board, when it was last on, and what it was
called (#50).

`History` in `sitebuild/__init__.py` compares the lists the boards hold, and a board's rows and an opened row say
what it finds: "new", how many boards in a row, the board day a row was last on, and the name it was listed under
before. The tests of a built page hold these for the example's two boards, where a run is one or two boards long
and no row has come back or been renamed. The mutation report on `sitebuild/` (#47) changed this class 59 ways
that no test noticed: a run counted from the wrong board, a last board that was not the nearest, an earlier name
taken from a later board.

So these give the class a few made-up boards, newest first as the index gives them, and hold what its docstring
says of each. A board here is its day and the repositories on it, each a number and a name.
"""

import unittest

from sitebuild import WINDOW, History

DAYS = [f"2026-11-{day:02}" for day in range(30, 0, -1)]
"""Thirty board days, newest first."""


def boards(*lists: dict[int, str]) -> list[dict]:
    """Boards, newest first, each from the repositories on it: a GitHub id and the name it was listed under."""
    return [
        {
            "board_day": day,
            "state": "rows",
            "rows": [{"github_id": number, "full_name": name} for number, name in on.items()],
        }
        for day, on in zip(DAYS, lists, strict=False)
    ]


def mark(history: History, number: int = 0, row: int = 0) -> dict:
    """What the board at `number` says of its row at `row`."""
    return history.rows(number)["marks"][row]


class TheBoardsARowWasOn(unittest.TestCase):
    def test_a_row_on_the_board_before_too_is_still_on_it_with_the_boards_in_a_row_it_has_been_on(self):
        ours = {7: "octo/cat"}
        for length in (2, 3, 5):
            with self.subTest(length=length):
                # On the newest `length` boards, off the next, and on the one after that, which is no part of the run.
                history = History(boards(*[ours] * length, {8: "other/one"}, ours))
                found = mark(history)
                self.assertEqual((found["status"], found["run"]), ("still", length))

    def test_a_run_is_counted_from_the_board_it_is_asked_of_and_not_from_the_newest(self):
        ours = {7: "octo/cat"}
        history = History(boards(ours, ours, ours, ours, {8: "other/one"}))
        self.assertEqual([mark(history, number)["run"] for number in (0, 1, 2)], [4, 3, 2])

    def test_a_run_that_reaches_the_oldest_board_ends_there(self):
        ours = {7: "octo/cat"}
        history = History(boards(ours, ours, ours))
        self.assertEqual(mark(history)["run"], 3)

    def test_a_row_that_comes_back_after_a_gap_says_the_nearest_earlier_board_day_it_was_on(self):
        ours, others = {7: "octo/cat"}, {8: "other/one"}
        history = History(boards(ours, others, others, ours, ours))
        found = mark(history)
        self.assertEqual((found["status"], found["last"]), ("back", DAYS[3]))

    def test_a_row_whose_name_another_repository_held_on_the_board_before_was_last_on_that_board(self):
        # It is not new, since its name was listed, and not still on, since the repository of its number was not.
        history = History(boards({7: "octo/cat"}, {9: "octo/cat"}, {8: "other/one"}))
        found = mark(history)
        self.assertEqual((found["status"], found["last"]), ("back", DAYS[1]))

    def test_a_row_whose_name_was_on_no_earlier_board_is_new_and_is_counted(self):
        history = History(boards({7: "octo/cat", 8: "other/one"}, {8: "other/one"}, {8: "other/one"}))
        told = history.rows(0)
        self.assertEqual([one["status"] for one in told["marks"]], ["new", "still"])
        self.assertEqual(told["new"], 1)

    def test_how_often_a_row_was_on_counts_the_boards_of_the_window_that_listed_it_its_own_among_them(self):
        ours, others = {7: "octo/cat"}, {8: "other/one"}
        # On three of the window's boards, and on one more that is older than the window reaches.
        lists = [ours, others, ours, others, ours, *[others] * (WINDOW - 5), ours]
        history = History(boards(*lists))
        self.assertEqual((history.rows(0)["window"], mark(history)["on"]), (WINDOW, 3))

    def test_a_renamed_row_says_the_name_it_had_on_the_latest_earlier_board_that_listed_it_under_another(self):
        now = {"github_id": 7, "full_name": "specular-org/Specular"}
        history = History(
            boards(
                {7: "specular-org/Specular"},
                {8: "other/one"},
                {7: "specular-org/Specular"},
                {7: "specula-org/Specula"},
                {7: "first-org/First"},
            )
        )
        self.assertEqual(history.was(0, now), "specula-org/Specula")
        # Renamed since the board before: that board's name is the one, with no board between.
        self.assertEqual(
            History(boards({7: "new/name"}, {7: "old/name"})).was(0, {"github_id": 7, "full_name": "new/name"}),
            "old/name",
        )

    def test_an_earlier_name_is_looked_for_on_the_boards_before_the_one_asked_of_and_on_no_later_board(self):
        # Asked of the third board, where it was still called by its first name, it had no other name before.
        then = {"github_id": 7, "full_name": "specula-org/Specula"}
        history = History(
            boards({7: "specular-org/Specular"}, {7: "specular-org/Specular"}, {7: "specula-org/Specula"})
        )
        self.assertIsNone(history.was(2, then))
        self.assertIsNone(history.was(0, {"github_id": 9, "full_name": "never/renamed"}))


if __name__ == "__main__":
    unittest.main()
