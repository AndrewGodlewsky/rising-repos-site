"""The count of the "Most often" order: what each row says while a reader has the board in that order. Sentence 45
of the owner's tests."""

import re
import unittest

from owner_tests.scenario import Scenario, board, names, open_rows, rows

ON_A_BOARD = re.compile(r": (rank \d+|not on the board)$")
"""What each day of an opened row's strip of board days says under the pointer: the rank the repository had on that
day's board, or that it was not on it."""

COUNT = re.compile(r"^on (\d+) of (\d+) boards?$")
"""The words a row's count says after its name and its New mark, "on 8 of 14 boards"."""


class TheCountOfTheMostOftenOrder(Scenario):
    def headers(self, page) -> list[str]:
        """What the header of each row shown says, as a reader sees it, its words one space apart."""
        return [" ".join(words.split()) for words in board(page).get_by_role("rowheader").all_inner_texts()]

    def test_with_most_often_chosen_each_row_says_on_how_many_of_the_boards_counted_it_was_and_in_no_other_order(
        self,
    ):
        """Sentence 45. The reader chooses the order whose words begin "Most often", which names how many boards it
        counts. Each row then says after its name, and after its New mark when it has one, "on N of W boards": W is
        the same on every row and no more than the order names, and N is how many of the last W days of the row's
        strip of board days it was on, which the reader reads by opening every row, so the rows stand most often
        first. In each other order the board offers, each row's header says its name, and New when it is new, and no
        count. The strip is read last, with the order chosen again, since an opened row holds a table of its own."""
        page = self.reader()
        self.visit(page)
        self.given(rows(page).count(), "the newest board lists no repository")
        by_rank = names(page)
        plain = dict(zip(by_rank, self.headers(page), strict=True))
        for name, said in plain.items():
            self.assertIn(said, [name, name + " New"])
        order = page.get_by_role("combobox", name="Order")
        offered = order.get_by_role("option").all_inner_texts()
        (often,) = [words for words in offered if words.startswith("Most often")]
        named = int(re.search(r"\d+", often).group())

        order.select_option(label=often)
        shown = names(page)
        self.assertCountEqual(shown, by_rank)
        counted, of = {}, set()
        for name, said in zip(shown, self.headers(page), strict=True):
            with self.subTest(name=name):
                self.assertTrue(said.startswith(plain[name] + " "), said)
                count = COUNT.match(said[len(plain[name]) + 1 :])
                self.assertIsNotNone(count, said)
                counted[name] = int(count.group(1))
                of.add(int(count.group(2)))
        (window,) = of
        self.assertLessEqual(window, named)
        self.assertEqual([counted[name] for name in shown], sorted(counted.values(), reverse=True))

        for words in offered:
            if words == often:
                continue
            with self.subTest(words):
                order.select_option(label=words)
                shown = names(page)
                self.assertCountEqual(shown, by_rank)
                self.assertEqual(self.headers(page), [plain[name] for name in shown])

        # Each count against the row's own strip, in the order again: every row opened, and the last `window` of its
        # days read. An opened row holds a table of its own, so no row's header is read after this.
        order.select_option(label=often)
        shown = names(page)
        open_rows(rows(page))
        days = board(page).get_by_title(ON_A_BOARD).evaluate_all("days => days.map(day => day.title)")
        each = len(days) // len(shown)
        self.assertEqual(len(days), each * len(shown))
        self.assertGreaterEqual(each, window)
        on = {
            name: sum("rank" in day for day in days[at * each : (at + 1) * each][-window:])
            for at, name in enumerate(shown)
        }
        self.assertEqual(on, counted)


if __name__ == "__main__":
    unittest.main()
