"""One command runs every check a change has to pass, the cheapest first: `python -m sitework check`.

No test here runs a check. A stand-in takes the place of `sitework.shell.run`, notes each command it is asked to
run, and fails the ones a test names, so that the owner's tests and the rest of the suite are only ever named.
"""

import io
import sys
import unittest
from unittest import mock

from test_sitework_guard import said

from sitework import check, issue, shell

PYTHON = (sys.executable, "-m")
LINT = (*PYTHON, "ruff", "check", ".")
FORMAT = (*PYTHON, "ruff", "format", "--check", ".")
WHITE_SPACE = ("git", "diff", "--check", "origin/main...HEAD")
GUARD = (*PYTHON, "sitework", "guard")
AGENTS = (*PYTHON, "unittest", "discover", "-s", "tests")
OWNERS = (*PYTHON, "unittest", "discover", "-s", "owner_tests", "-t", ".")
NEW = (*PYTHON, "sitework", "new-tests")
CRITERIA = (*PYTHON, "sitework", "criteria", "--issue", "12")


class TheCheck(unittest.TestCase):
    def setUp(self):
        self.ran: list[tuple[str, ...]] = []
        self.failing: dict[tuple[str, ...], str] = {}  # what each command that is to fail prints
        self.said: list[dict] = []  # the comments of the owner's account on the issue
        self.enterContext(mock.patch.object(shell, "run", self.stand_in))
        self.enterContext(mock.patch.object(issue, "owner", return_value="the-owner"))
        self.comments = self.enterContext(mock.patch.object(issue, "comments", side_effect=lambda *asked: self.said))

    def stand_in(self, *command: str, **options) -> str:
        self.ran.append(command)
        if command in self.failing:
            raise shell.Failed(self.failing[command])
        return ""

    def check(self, *arguments: str) -> tuple[int, list[str]]:
        return said(check.main, "check", *arguments)

    def test_it_runs_every_check_of_a_change_the_cheapest_first(self):
        code, _ = self.check()
        self.assertEqual((code, self.ran), (0, [LINT, FORMAT, WHITE_SPACE, GUARD, AGENTS, OWNERS, NEW]))

    def test_the_criteria_are_checked_last_and_only_when_an_issue_is_given(self):
        code, _ = self.check("--issue", "12")
        self.assertEqual((code, self.ran), (0, [LINT, FORMAT, WHITE_SPACE, GUARD, AGENTS, OWNERS, NEW, CRITERIA]))

    def test_with_an_issue_the_guard_lets_through_what_the_owner_allowed_for_it(self):
        # Without this a change the owner allowed could never pass on the machine, though the ship script lets it by.
        self.said = [
            {"body": "Go on.\n\nAllowed: pyproject.toml, uv.lock"},
            {"body": "Site workflow: picked up"},
            {"body": "Allowed: docs/adr/*"},
        ]
        code, _ = self.check("--issue", "12")
        allowing = (*GUARD, "--allow", "pyproject.toml", "uv.lock", "docs/adr/*")
        self.assertEqual((code, self.ran), (0, [LINT, FORMAT, WHITE_SPACE, allowing, AGENTS, OWNERS, NEW, CRITERIA]))
        self.assertEqual(self.comments.mock_calls, [mock.call(12, "the-owner")])

    def test_without_an_issue_no_comment_is_read_and_the_guard_allows_nothing(self):
        self.said = [{"body": "Allowed: uv.lock"}]
        for arguments in ([], ["--suite"]):
            with self.subTest(arguments=arguments):
                self.check(*arguments)
                self.assertEqual((issue.owner.mock_calls, self.comments.mock_calls), ([], []))
                self.assertFalse([command for command in self.ran if "--allow" in command])

    def test_the_steps_are_made_from_what_they_are_given_and_read_nothing(self):
        steps = dict(check.steps(12, False, ["uv.lock", "docs/adr/*"]))
        self.assertEqual(tuple(steps["the guarded paths"]), (*GUARD, "--allow", "uv.lock", "docs/adr/*"))
        self.assertEqual(tuple(dict(check.steps(12, False, []))["the guarded paths"]), GUARD)
        self.assertEqual((self.ran, issue.owner.mock_calls, self.comments.mock_calls), ([], [], []))

    def test_the_suite_is_the_lint_the_format_and_the_two_sets_of_tests_alone(self):
        # A checkout on GitHub holds no history, so nothing that reads the change runs there.
        code, _ = self.check("--suite")
        self.assertEqual((code, self.ran), (0, [LINT, FORMAT, AGENTS, OWNERS]))

    def test_it_stops_at_the_first_step_that_fails_and_shows_what_that_step_printed(self):
        self.failing = {GUARD: "uv.lock: a dependency\nAGENTS.md: the workflow's own scripts and documents"}
        code, lines = self.check()
        self.assertEqual((code, self.ran), (1, [LINT, FORMAT, WHITE_SPACE, GUARD]))
        self.assertEqual(lines[-2:], ["uv.lock: a dependency", "AGENTS.md: the workflow's own scripts and documents"])

    def test_it_prints_a_line_as_each_step_starts_and_one_as_it_ends_with_how_long_it_took(self):
        self.failing = {OWNERS: "FAILED (failures=1)"}
        clock = mock.Mock(monotonic=mock.Mock(side_effect=[0.0, 0.3, 10.0, 12.1, 20.0, 261.4, 300.0, 301.0]))
        with mock.patch.object(check, "time", clock):
            code, lines = self.check("--suite")
        self.assertEqual(
            (code, lines),
            (
                1,
                [
                    "the lint: started",
                    "the lint: passed in 0.3 s",
                    "the format: started",
                    "the format: passed in 2.1 s",
                    "the agents' tests: started",
                    "the agents' tests: passed in 241.4 s",
                    "the owner's tests: started",
                    "the owner's tests: failed after 1.0 s",
                    "FAILED (failures=1)",
                ],
            ),
        )

    def test_every_step_is_named_as_it_starts(self):
        _, lines = self.check("--issue", "12")
        self.assertEqual(
            [line.removesuffix(": started") for line in lines[::2]],
            [
                "the lint",
                "the format",
                "white space",
                "the guarded paths",
                "the agents' tests",
                "the owner's tests",
                "the new tests",
                "the criteria",
            ],
        )

    def test_what_a_step_printed_is_shown_where_the_output_cannot_write_one_of_its_characters(self):
        self.failing = {LINT: "a row reads 1 → 2"}
        written = io.BytesIO()
        pipe = io.TextIOWrapper(written, encoding="cp1252")
        with mock.patch.object(sys, "stdout", pipe):
            code = check.main("check", [])
        pipe.flush()
        self.assertEqual(code, 1)
        self.assertEqual(written.getvalue().decode("cp1252").splitlines()[-1], "a row reads 1 \\u2192 2")

    def test_the_suite_and_an_issue_are_not_given_together(self):
        with mock.patch.object(sys, "stderr", io.StringIO()), self.assertRaises(SystemExit) as stopped:
            check.main("check", ["--suite", "--issue", "12"])
        self.assertEqual((stopped.exception.code, self.ran), (2, []))


class AStepOfPython(unittest.TestCase):
    """A step is run for real here, and it is a short program of this test's own."""

    def test_what_it_prints_outside_ascii_is_read_and_shown(self):
        # A failing test's message often holds such a character. `shell.run` has each Python it starts write UTF-8.
        program = "import sys; sys.stderr.write('a row reads 1 ' + chr(8594) + ' 2 ' + chr(183)); sys.exit(1)"
        with mock.patch.object(check, "steps", return_value=[("a step", [sys.executable, "-c", program])]):
            code, lines = said(check.main, "check")
        self.assertEqual((code, lines[-1]), (1, "a row reads 1 → 2 ·"))


if __name__ == "__main__":
    unittest.main()
