"""Every script of the feature workflow runs its commands through one function.

A script that cannot read what a command printed stops a run where nobody is watching, so the function reads
whatever a command prints, on a machine whose own encoding is not UTF-8 as well.

A script that commits, or that needs the code of another commit, works in a temporary worktree, so that the
agent's own tree is left as it is. The tests of that make a git repository of their own in a temporary folder.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sitework import shell


class RunningACommand(unittest.TestCase):
    def test_it_gives_what_the_command_printed_without_the_white_space_at_its_ends(self):
        self.assertEqual(shell.run(sys.executable, "-c", "print('  a board  ')"), "a board")

    def test_a_command_that_fails_raises_with_what_it_printed_and_its_exit_code(self):
        with self.assertRaises(shell.Failed) as raised:
            shell.run(sys.executable, "-c", "import sys; print('no such issue'); sys.exit(3)")
        self.assertIn("no such issue", str(raised.exception))
        self.assertEqual(raised.exception.code, 3)

    def test_a_command_that_fails_gives_what_it_printed_when_it_is_not_checked(self):
        self.assertEqual(shell.run(sys.executable, "-c", "import sys; print('held'); sys.exit(1)", check=False), "held")

    def test_a_python_it_runs_writes_utf_8_whatever_the_machine_s_own_encoding_is(self):
        # A half, U+00BD, is one byte in the encoding Windows gives a piped Python, and that byte is not UTF-8.
        self.assertEqual(shell.run(sys.executable, "-c", "print(chr(189))"), "½")

    def test_a_byte_that_is_not_utf_8_is_replaced_and_does_not_stop_the_script(self):
        printed = shell.run(sys.executable, "-c", "import sys; sys.stdout.buffer.write(bytes([0x62, 0xBD, 0x62]))")
        self.assertEqual(printed, "b�b")

    def test_what_is_passed_as_the_environment_reaches_the_command_beside_the_machine_s_own(self):
        printed = shell.run(sys.executable, "-c", "import os; print(os.environ['SITE'])", env={"SITE": "an address"})
        self.assertEqual(printed, "an address")

    def test_what_is_passed_as_standard_input_reaches_the_command(self):
        self.assertEqual(
            shell.run(sys.executable, "-c", "import sys; print(sys.stdin.read())", stdin="a plan"), "a plan"
        )

    def test_a_file_passed_as_standard_input_reaches_the_command_byte_for_byte(self):
        # A byte that is not UTF-8, a line that ends in CRLF, and one that ends in LF: what text passed as
        # standard input would have had replaced or rewritten on the way.
        held = bytes([0x62, 0xBD, 0x0D, 0x0A, 0x62, 0x0A])
        file = Path(self.enterContext(tempfile.TemporaryDirectory())) / "held"
        file.write_bytes(held)
        read = "import sys; print(sys.stdin.buffer.read().hex())"
        self.assertEqual(shell.run(sys.executable, "-c", read, stdin=file), held.hex())


class ATemporaryWorktree(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.enterContext(mock.patch.object(shell, "ROOT", self.root))
        shell.git("init", "--quiet", "--initial-branch=main")
        for key, value in (
            ("user.name", "A test"),
            ("user.email", "test@example.invalid"),
            ("commit.gpgsign", "false"),
        ):
            shell.git("config", key, value)
        self.first, self.second = self.commit("one"), self.commit("two")

    def commit(self, words: str) -> str:
        (self.root / "page.txt").write_text(words, encoding="utf-8")
        shell.git("add", "page.txt")
        shell.git("commit", "--quiet", "--message", f"Write {words}")
        return shell.git("rev-parse", "HEAD")

    def checkouts(self) -> int:
        return shell.git("worktree", "list", "--porcelain").count("worktree ")

    def test_it_holds_the_commit_it_was_made_from_and_the_agents_own_tree_is_left_as_it_is(self):
        (self.root / "page.txt").write_text("not committed", encoding="utf-8")
        with shell.worktree(self.first) as tree:
            self.assertNotIn(self.root, [tree, *tree.parents])
            self.assertEqual((tree / "page.txt").read_text(encoding="utf-8"), "one")
            self.assertEqual(shell.git("rev-parse", "HEAD", cwd=tree), self.first)
            self.assertEqual(shell.git("branch", "--show-current", cwd=tree), "")
            (tree / "page.txt").write_text("written in the worktree", encoding="utf-8")
        self.assertEqual((self.root / "page.txt").read_text(encoding="utf-8"), "not committed")
        self.assertEqual(shell.git("rev-parse", "HEAD"), self.second)
        self.assertEqual(shell.git("branch", "--show-current"), "main")

    def test_it_is_removed_when_the_block_ends_and_also_when_the_block_fails(self):
        with shell.worktree(self.first) as tree:
            self.assertEqual(self.checkouts(), 2)
        self.assertEqual((self.checkouts(), tree.parent.exists()), (1, False))
        with self.assertRaises(shell.Failed), shell.worktree(self.first) as tree:
            shell.git("revert", "--no-edit", "no-such-commit", cwd=tree)
        self.assertEqual((self.checkouts(), tree.parent.exists()), (1, False))

    def test_the_options_it_is_given_are_git_s_and_take_the_place_of_a_checkout_on_no_branch(self):
        with shell.worktree(self.first, "--no-track", "-B", "agent/7-revert") as tree:
            self.assertEqual(shell.git("branch", "--show-current", cwd=tree), "agent/7-revert")
            self.assertEqual(shell.git("rev-parse", "HEAD", cwd=tree), self.first)
        self.assertEqual(shell.git("rev-parse", "agent/7-revert"), self.first)
