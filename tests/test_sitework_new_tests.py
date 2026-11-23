"""Each test a change adds is run on the code before the change, where it has to fail: `python -m sitework new-tests`.

Each test commits a change to a git repository of its own, in a temporary folder, whose tests need nothing but
Python. The command runs them there as it runs this repository's: the agents' tests with their folder on the path,
and the owner's tests as modules of theirs.
"""

import sys
import unittest
from unittest import mock

from test_sitework_guard import RepositoryTest, said

from sitework import newtests, shell

PRODUCT = "def double(number):\n    return number * 2\n"
TRIPLE = "\n\ndef triple(number):\n    return number * 3\n"

SUMS = "tests/test_sums.py"
TESTS = """\
import unittest

from helpers import VALUE

import product


class Doubling(unittest.TestCase):
    def test_it_doubles_a_number(self):
        self.assertEqual(product.double(VALUE), 4)
"""
"""One of the agents' tests, which reads the helpers beside it as this repository's tests do."""

READER = "owner_tests/test_reader.py"
OWNERS = """\
import unittest

from owner_tests.site import ADDRESS


class AReader(unittest.TestCase):
    def test_a_reader_finds_the_board(self):
        self.assertEqual(ADDRESS, "/")
"""
"""One of the owner's tests, which reads a module of its own folder."""

TRIPLES = "\n    def test_it_triples(self):\n        self.assertEqual(product.triple(VALUE), 6)\n"
"""A test of what the change adds. Its name begins another test's name, and only the one named may be run."""

TRIPLES_NOUGHT = "\n    def test_it_triples_nought(self):\n        self.assertEqual(product.triple(0), 0)\n"
DOUBLES_NOUGHT = "\n    def test_it_doubles_nought(self):\n        self.assertEqual(product.double(0), 0)\n"
"""A test that the code passed before the change."""


class TheNewTests(RepositoryTest):
    def setUp(self):
        super().setUp()
        self.enterContext(mock.patch.object(shell, "ROOT", self.root))
        agents = {SUMS: TESTS, "tests/helpers.py": "VALUE = 2\n"}
        owners = {READER: OWNERS, "owner_tests/__init__.py": "", "owner_tests/site.py": 'ADDRESS = "/"\n'}
        self.on_main({"product.py": PRODUCT, **agents, **owners})

    def new_tests(self, *arguments: str) -> tuple[int, list[str]]:
        return said(newtests.main, "new-tests", *arguments)

    def checkouts(self) -> int:
        """How many checkouts the repository has: its own folder, and each worktree made from it."""
        return shell.git("worktree", "list", "--porcelain").count("worktree ")

    def test_a_change_that_adds_no_test_says_so_and_passes(self):
        self.commit({"product.py": PRODUCT + TRIPLE, SUMS: TESTS.replace("VALUE), 4", "VALUE), 4.0")})
        self.assertEqual(self.new_tests(), (0, ["the change adds no test"]))

    def test_a_new_test_that_fails_on_the_code_before_passes(self):
        self.commit({"product.py": PRODUCT + TRIPLE, SUMS: TESTS + TRIPLES})
        self.assertEqual(self.new_tests(), (0, [f"fails before: {SUMS}::Doubling::test_it_triples"]))

    def test_a_new_test_that_passes_on_the_code_before_proves_nothing_whatever_the_others_do(self):
        self.commit({"product.py": PRODUCT + TRIPLE, SUMS: TESTS + TRIPLES + DOUBLES_NOUGHT + TRIPLES_NOUGHT})
        self.assertEqual(
            self.new_tests(),
            (
                1,
                [
                    f"fails before: {SUMS}::Doubling::test_it_triples",
                    f"passes before, so it proves nothing: {SUMS}::Doubling::test_it_doubles_nought",
                    f"fails before: {SUMS}::Doubling::test_it_triples_nought",
                ],
            ),
        )

    def test_a_test_under_a_new_class_is_new_though_its_name_is_not(self):
        again = "\n\nclass DoublingAgain(unittest.TestCase):\n    def test_it_doubles_a_number(self):\n        pass\n"
        self.commit({SUMS: TESTS + again})
        self.assertEqual(
            self.new_tests(),
            (1, [f"passes before, so it proves nothing: {SUMS}::DoublingAgain::test_it_doubles_a_number"]),
        )

    def test_a_new_test_runs_beside_the_helpers_as_the_change_has_them(self):
        # The test reads a name the change added to the helpers, and would fail for want of it and of nothing else.
        more = TESTS.replace("VALUE", "OTHER").replace("4)", "6)").replace("Doubling", "DoublingAnother")
        self.commit({"tests/helpers.py": "VALUE = 2\nOTHER = 3\n", "tests/test_more.py": more})
        self.assertEqual(
            self.new_tests(),
            (1, ["passes before, so it proves nothing: tests/test_more.py::DoublingAnother::test_it_doubles_a_number"]),
        )

    def test_one_of_the_owners_tests_is_run_as_a_module_of_its_folder(self):
        added = (
            '\n    def test_a_reader_finds_it_at_the_root(self):\n        self.assertTrue(ADDRESS.startswith("/"))\n'
        )
        self.commit({READER: OWNERS + added})
        self.assertEqual(
            self.new_tests(),
            (1, [f"passes before, so it proves nothing: {READER}::AReader::test_a_reader_finds_it_at_the_root"]),
        )

    def test_a_test_that_prints_a_character_outside_ascii_is_judged_as_any_other(self):
        # On Windows a Python that writes to no terminal has no way to write an arrow unless it is told to write
        # UTF-8, as `shell.run` tells it. Otherwise the test would end in that error, and be taken to fail.
        prints = "\n    def test_it_prints_an_arrow(self):\n        print(chr(183), chr(8594))\n"
        self.commit({SUMS: TESTS + prints})
        self.assertEqual(
            self.new_tests(), (1, [f"passes before, so it proves nothing: {SUMS}::Doubling::test_it_prints_an_arrow"])
        )

    def test_it_reads_the_change_between_the_two_commits_it_is_given(self):
        first = self.commit({"product.py": PRODUCT + TRIPLE, SUMS: TESTS + TRIPLES})
        second = self.commit({SUMS: TESTS + TRIPLES + TRIPLES_NOUGHT})
        self.assertEqual(
            self.new_tests("--base", first, "--head", second),
            (1, [f"passes before, so it proves nothing: {SUMS}::Doubling::test_it_triples_nought"]),
        )

    def test_the_checkout_of_the_code_before_is_removed_and_the_working_folder_is_left_as_it_was(self):
        feature = self.commit({"product.py": PRODUCT + TRIPLE, SUMS: TESTS + TRIPLES})
        self.new_tests()
        self.assertEqual(self.checkouts(), 1)
        self.assertEqual(shell.git("status", "--porcelain"), "")
        self.assertEqual(shell.git("rev-parse", "HEAD"), feature)

    def test_the_checkout_of_the_code_before_is_removed_after_an_error_too(self):
        self.commit({"product.py": PRODUCT + TRIPLE, SUMS: TESTS + TRIPLES})
        seen = []

        def breaks(test: str) -> list[str]:
            seen.append(self.checkouts())
            raise RuntimeError("the run of a test broke")

        with mock.patch.object(newtests, "command", breaks), self.assertRaises(RuntimeError):
            self.new_tests()
        self.assertEqual((seen, self.checkouts()), ([2], 1))

    def test_the_command_that_runs_a_test_can_be_replaced(self):
        self.commit({"product.py": PRODUCT + TRIPLE, SUMS: TESTS + TRIPLES})
        with mock.patch.object(newtests, "command", lambda test: [sys.executable, "-c", "raise SystemExit(0)"]):
            self.assertEqual(
                self.new_tests(), (1, [f"passes before, so it proves nothing: {SUMS}::Doubling::test_it_triples"])
            )


if __name__ == "__main__":
    unittest.main()
