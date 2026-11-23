"""The existing tests a change altered or removed are listed for the reviewer: `python -m sitework altered-tests`.

Each test commits a change to a git repository of its own, in a temporary folder, and reads the list made of it.
"""

import unittest
from unittest import mock

from test_sitework_guard import RepositoryTest, said

from sitework import altered, shell

SUMS = "tests/test_sums.py"
BEFORE = """\
import unittest


class Doubling(unittest.TestCase):
    def test_it_doubles_a_number(self):
        self.assertEqual(2 * 2, 4)

    def test_it_doubles_nought(self):
        self.assertEqual(2 * 0, 0)


class Halving(unittest.TestCase):
    def test_it_halves_a_number(self):
        self.assertEqual(4 / 2, 2)
"""
"""The agents' tests as main has them."""

NOTHING = "no existing test was altered or removed"


class TheAlteredTests(RepositoryTest):
    def setUp(self):
        super().setUp()
        self.enterContext(mock.patch.object(shell, "ROOT", self.root))
        owners = {"owner_tests/test_reader.py": BEFORE}
        self.base = self.on_main({SUMS: BEFORE, "tests/helpers.py": "VALUE = 2\n", "README.md": "before\n", **owners})

    def altered(self, *arguments: str) -> tuple[int, list[str]]:
        return said(altered.main, "altered-tests", *arguments)

    def test_a_change_that_alters_no_test_says_so(self):
        self.commit({"README.md": "after\n"})
        self.assertEqual(self.altered(), (0, [NOTHING]))

    def test_a_test_whose_code_differs_is_listed_as_altered_and_stops_nothing(self):
        self.commit({SUMS: BEFORE.replace("self.assertEqual(2 * 2, 4)", "self.assertTrue(2 * 2)")})
        self.assertEqual(self.altered(), (0, [f"altered: {SUMS}::Doubling::test_it_doubles_a_number"]))

    def test_a_test_that_is_now_skipped_is_listed_as_altered(self):
        skipped = BEFORE.replace(
            "    def test_it_doubles_nought", '    @unittest.skip("for now")\n    def test_it_doubles_nought'
        )
        self.commit({SUMS: skipped})
        self.assertEqual(self.altered(), (0, [f"altered: {SUMS}::Doubling::test_it_doubles_nought"]))

    def test_a_test_that_is_gone_is_listed_as_removed(self):
        self.commit({SUMS: BEFORE[: BEFORE.index("class Halving")]})
        self.assertEqual(self.altered(), (0, [f"removed: {SUMS}::Halving::test_it_halves_a_number"]))

    def test_every_test_of_a_file_that_was_removed_or_renamed_is_listed_as_removed(self):
        self.commit({SUMS: None, "tests/test_arithmetic.py": BEFORE})
        self.assertEqual(
            self.altered(),
            (
                0,
                [
                    f"removed: {SUMS}::Doubling::test_it_doubles_a_number",
                    f"removed: {SUMS}::Doubling::test_it_doubles_nought",
                    f"removed: {SUMS}::Halving::test_it_halves_a_number",
                ],
            ),
        )

    def test_a_test_that_was_only_laid_out_again_is_not_listed(self):
        laid_out = BEFORE.replace(
            "self.assertEqual(2 * 2, 4)",
            "# Twice two.\n        self.assertEqual(\n            2 * 2,\n            4,\n        )",
        )
        halving = laid_out[laid_out.index("class Halving") :]
        moved = halving + "\n\n" + laid_out[: laid_out.index("class Halving")].replace("import unittest\n", "")
        self.commit({SUMS: "import unittest\n\n\n" + moved.strip() + "\n"})
        self.assertEqual(self.altered(), (0, [NOTHING]))

    def test_a_test_the_change_adds_is_not_listed(self):
        added = BEFORE + "\n    def test_it_halves_nought(self):\n        self.assertEqual(0 / 2, 0)\n"
        self.commit({SUMS: added, "tests/test_more.py": BEFORE})
        self.assertEqual(self.altered(), (0, [NOTHING]))

    def test_only_the_agents_tests_are_read(self):
        # A change to the owner's tests is the guard's to name, and a file of helpers holds no test.
        self.commit(
            {"owner_tests/test_reader.py": BEFORE.replace("4 / 2, 2", "4 / 2, 2.0"), "tests/helpers.py": "VALUE = 3\n"}
        )
        self.assertEqual(self.altered(), (0, [NOTHING]))

    def test_it_reads_the_change_between_the_two_commits_it_is_given(self):
        first = self.commit({SUMS: BEFORE.replace("2 * 0, 0", "2 * 0, 0.0")})
        second = self.commit({"README.md": "after\n"})
        self.assertEqual(
            self.altered("--base", self.base, "--head", first),
            (0, [f"altered: {SUMS}::Doubling::test_it_doubles_nought"]),
        )
        self.assertEqual(self.altered("--base", first, "--head", second), (0, [NOTHING]))


if __name__ == "__main__":
    unittest.main()
