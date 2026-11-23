"""Every criterion of a feature's plan has a proof that passed: `python -m sitework criteria`.

Each test writes a plan, and has it judged against a git repository of its own, in a temporary folder, whose tests
need nothing but Python. No test reaches GitHub: where a plan is read from an issue, a stand-in answers for
GitHub's CLI.
"""

import contextlib
import io
import json
import unittest
from unittest import mock

from test_sitework_guard import RepositoryTest, said

from sitework import criteria, newtests, shell

SUMS = "tests/test_sums.py"
FOUR = f"{SUMS}::Sums::test_two_and_two_make_four"
FIVE = f"{SUMS}::Sums::test_two_and_two_make_five"
TESTS = """\
import unittest


class Sums(unittest.TestCase):
    def test_two_and_two_make_four(self):
        self.assertEqual(2 + 2, 4)

    def test_two_and_two_make_five(self):
        self.assertEqual(2 + 2, 5)
"""
"""The agents' tests at HEAD: one that passes, and one that fails."""

READER = "owner_tests/test_reader.py"
FINDS = f"{READER}::AReader::test_a_reader_finds_the_board"
OWNERS = """\
import unittest


class AReader(unittest.TestCase):
    def test_a_reader_finds_the_board(self):
        self.assertTrue(True)
"""

OWNER = "the-owner"
"""The account that owns the repository, as the stand-in for GitHub's CLI gives it."""

LOOKED_AT = "looked at: the sum on a screen 360 pixels wide"
PROVEN = {1: f"`{FOUR}`", 2: LOOKED_AT, 3: f"A reader finds it: `{FINDS}`"}
"""A proof for each criterion of the plan below."""


def plan(proofs: dict[int, str]) -> str:
    """A plan with three criteria, in the form docs/workflow/README.md gives the workflow's comment on an issue,
    and a row for each of `proofs`."""
    rows = "\n".join(f"| {number} | {proof} |" for number, proof in proofs.items())
    return f"""\
Site workflow: plan

## Verdict
Go

## What changes for a reader
A reader sees the sum of two numbers.

## Criteria
1. Given two and two, when the page is built, then their sum is shown.
2. The sum reads well on a narrow screen,
   and on a wide one.
3. A reader finds the board.

## How each is proven
| # | Proof |
| --- | --- |
{rows}

## Out of scope
1. Any other sum.
"""


class TheCriteria(RepositoryTest):
    def setUp(self):
        super().setUp()
        self.enterContext(mock.patch.object(shell, "ROOT", self.root))
        self.commit({SUMS: TESTS, READER: OWNERS, "owner_tests/__init__.py": ""})

    def criteria(self, proofs: dict[int, str]) -> tuple[int, list[str]]:
        """What the command says of a plan in a file, with a row for each of `proofs`."""
        (self.root / "plan.md").write_text(plan(proofs), encoding="utf-8", newline="\n")
        return said(criteria.main, "criteria", "--plan", str(self.root / "plan.md"))

    def github_answers(self, *comments: tuple[str, str]) -> list[tuple[str, ...]]:
        """Have a stand-in answer for GitHub's CLI with these comments on the issue, each the account that wrote it
        and its body, the oldest first as GitHub lists them. Gives the list that each command the stand-in was asked
        is added to."""
        asked, run = [], shell.run

        def stand_in(*command: str, **options) -> str:
            if command[0] != "gh":
                return run(*command, **options)
            asked.append(command)
            if command[1:3] == ("repo", "view"):
                return json.dumps({"owner": {"login": OWNER}})
            return json.dumps([{"user": {"login": account}, "body": body} for account, body in comments])

        self.enterContext(mock.patch.object(shell, "run", stand_in))
        return asked

    def test_a_plan_whose_every_criterion_has_a_proof_that_passes_is_proven(self):
        self.assertEqual(
            self.criteria(PROVEN), (0, [f"1: proven by {FOUR}", f"2: {LOOKED_AT}", f"3: proven by {FINDS}"])
        )

    def test_a_criterion_with_no_row_is_not_proven(self):
        code, lines = self.criteria({1: PROVEN[1], 3: PROVEN[3]})
        self.assertEqual((code, lines[1]), (1, "2: not proven: no row of the table says how it is proven"))

    def test_a_test_that_fails_is_not_proven(self):
        code, lines = self.criteria({**PROVEN, 1: f"`{FIVE}`"})
        self.assertEqual(
            (code, lines), (1, [f"1: not proven: {FIVE} fails", f"2: {LOOKED_AT}", f"3: proven by {FINDS}"])
        )

    def test_every_test_a_row_names_has_to_pass(self):
        self.assertEqual(self.criteria({**PROVEN, 1: f"`{FOUR}` and `{FINDS}`"})[1][0], f"1: proven by {FOUR}, {FINDS}")
        code, lines = self.criteria({**PROVEN, 1: f"`{FOUR}` and `{FIVE}`"})
        self.assertEqual((code, lines[0]), (1, f"1: not proven: {FIVE} fails"))

    def test_a_test_that_proves_two_criteria_is_run_once(self):
        with mock.patch.object(newtests, "passes", return_value=True) as passes:
            code, _ = self.criteria({1: f"`{FOUR}`", 2: f"`{FOUR}`", 3: LOOKED_AT})
        self.assertEqual((code, passes.mock_calls), (0, [mock.call(FOUR)]))

    def test_what_was_looked_at_may_begin_its_row_with_a_capital(self):
        with mock.patch.object(newtests, "passes", return_value=True):
            code, lines = self.criteria({**PROVEN, 2: "Looked at: the sum, on a telephone"})
        self.assertEqual((code, lines[1]), (0, "2: Looked at: the sum, on a telephone"))

    def test_a_test_that_is_not_at_head_is_not_proven_and_is_not_run(self):
        # The second of these is in the working folder, where it would pass, and no commit holds it.
        missing, uncommitted = (
            f"{SUMS}::Sums::test_it_is_not_there",
            "tests/test_later.py::Sums::test_two_and_two_make_four",
        )
        (self.root / "tests" / "test_later.py").write_text(TESTS, encoding="utf-8", newline="\n")
        with mock.patch.object(newtests, "command", side_effect=AssertionError("a test was run")):
            code, lines = self.criteria({1: f"`{missing}`", 2: f"`{uncommitted}`", 3: f"`{READER}::Gone::test_it`"})
        self.assertEqual(
            (code, lines),
            (
                1,
                [
                    f"1: not proven: {missing} is not at HEAD",
                    f"2: not proven: {uncommitted} is not at HEAD",
                    f"3: not proven: {READER}::Gone::test_it is not at HEAD",
                ],
            ),
        )

    def test_a_row_that_names_no_test_and_nothing_that_was_looked_at_is_not_proven(self):
        unproven = "its row names no test, and nothing that was looked at"
        code, lines = self.criteria({1: "The tests pass.", 2: "looked at:", 3: f"`{SUMS}`"})
        self.assertEqual((code, lines), (1, [f"{number}: not proven: {unproven}" for number in (1, 2, 3)]))

    def test_a_plan_with_no_criteria_is_not_proven(self):
        unlisted = "Site workflow: plan\n\n## How each is proven\n| 1 | looked at: it |\n\n## Out of scope\n1. A sum.\n"
        (self.root / "plan.md").write_text(unlisted, encoding="utf-8", newline="\n")
        self.assertEqual(
            said(criteria.main, "criteria", "--plan", str(self.root / "plan.md")),
            (1, ['the plan has no numbered criterion under "## Criteria"']),
        )

    def test_the_plan_of_an_issue_is_the_newest_plan_the_owners_account_posted(self):
        asked = self.github_answers(
            (OWNER, plan({1: f"`{FIVE}`"})),
            (OWNER, plan(PROVEN)),
            (OWNER, "The owner's own words.\n\n## Criteria\n\n1. Another thing.\n"),
            (OWNER, "Site workflow: review\n\n## Criteria\n\n1. Read by the reviewer.\n"),
        )
        code, lines = said(criteria.main, "criteria", "--issue", "12")
        self.assertEqual((code, lines), (0, [f"1: proven by {FOUR}", f"2: {LOOKED_AT}", f"3: proven by {FINDS}"]))
        self.assertEqual(
            asked,
            [
                ("gh", "repo", "view", "--json", "owner"),
                ("gh", "api", "repos/{owner}/{repo}/issues/12/comments?per_page=100", "--paginate"),
            ],
        )

    def test_a_plan_that_another_account_posted_counts_for_nothing(self):
        # The repository is public, so anyone can comment on an issue, and a plan whose every proof is something
        # looked at would pass a change that proves nothing.
        self.github_answers(
            (OWNER, plan({**PROVEN, 1: f"`{FIVE}`"})),
            ("a-stranger", plan({1: LOOKED_AT, 2: LOOKED_AT, 3: LOOKED_AT})),
        )
        code, lines = said(criteria.main, "criteria", "--issue", "12")
        self.assertEqual((code, lines[0]), (1, f"1: not proven: {FIVE} fails"))

    def test_an_issue_with_no_plan_is_not_proven(self):
        self.github_answers((OWNER, "Site workflow: picked up"), (OWNER, "Go on."), ("a-stranger", plan(PROVEN)))
        self.assertEqual(
            said(criteria.main, "criteria", "--issue", "12"),
            (1, ['issue 12 has no comment that begins "Site workflow: plan"']),
        )

    def test_it_takes_a_plan_or_an_issue_and_not_both_and_not_neither(self):
        for arguments in ([], ["--plan", "plan.md", "--issue", "12"]):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as stopped:
                    criteria.main("criteria", arguments)
                self.assertEqual(stopped.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
