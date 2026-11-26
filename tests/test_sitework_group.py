"""`sort` records which ideas go with the idea a run claimed, and claims them, and `release` sends one back to wait
for a run of its own (25 November 2026).

No test reaches GitHub. `sitework.shell.run` is replaced by a stand-in that answers each command from what the
test gives it, in the shapes `gh` and `git` answer in, and keeps each command it was given. Each test starts from
#89, which a run has claimed, and three ideas the owner approved after it, #90 first, and changes the one thing
it is about.
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sitework import group, shell

OWNER = "the-owner"
COMMENTS = "gh api repos/{owner}/{repo}/issues/%d/comments"
TIMELINE = "gh api repos/{owner}/{repo}/issues/%d/timeline"
STATUS = "gh api --method PATCH repos/{owner}/{repo}/issues/%d -f status=%s"


class Shell:
    """Stands in for `sitework.shell.run`. A command is answered by the answer whose words it begins with, the
    longest of them when several do, and a command with no answer fails the test. An answer that is not text is
    given as the JSON the command would print, and one that is an error is raised."""

    def __init__(self, answers: dict):
        self.answers = answers
        self.ran = []
        self.stdin = {}

    def __call__(self, *command, cwd=None, check=True, stdin=None):
        line = " ".join(command)
        self.ran.append(line)
        self.stdin[line] = stdin
        starts = [start for start in self.answers if line.startswith(start)]
        if not starts:
            raise AssertionError(f"the test gave no answer for: {line}")
        answer = self.answers[max(starts, key=len)]
        if isinstance(answer, Exception):
            raise answer
        return answer if isinstance(answer, str) else json.dumps(answer)

    def changes(self) -> list[str]:
        """The commands that were run and change something on GitHub."""
        return [line for line in self.ran if line.startswith(("gh issue edit", "gh issue comment", "gh api --method"))]


def idea(number: int, *labels: str) -> dict:
    """An open issue the owner wrote, as `gh issue list` gives one. With no labels named, an approved idea."""
    names = labels or ("site-idea", "approved")
    return {
        "author": {"login": OWNER},
        "labels": [{"name": name} for name in names],
        "number": number,
        "title": f"Idea {number}",
    }


def labelled(name: str, when: str) -> dict:
    """A label the owner put on an issue, as the issue's timeline gives it."""
    return {"event": "labeled", "actor": {"login": OWNER}, "created_at": when, "label": {"name": name}}


def said(body: str, number: int = 1) -> dict:
    """A comment the owner's account wrote, as GitHub's API gives one."""
    return {
        "id": 7000 + number,
        "html_url": f"https://github.com/the-owner/the-site/issues/89#issuecomment-{7000 + number}",
        "user": {"login": OWNER},
        "created_at": f"2026-11-25T18:00:{number:02}Z",
        "body": body,
    }


def graded(effort: int = 3, complexity: int = 2) -> dict:
    """An idea's grade in points, posted before anything else on it. The sort holds a group's effort to its cap, so
    every idea a sort is given has one (25 November 2026)."""
    return said(f"Site workflow: graded\n\nComplexity: {complexity}\nEffort: {effort}\nArea: a row\nCode: x", number=0)


class GroupTest(unittest.TestCase):
    def setUp(self):
        self.answers = {
            "gh repo view": {"owner": {"login": OWNER}},
            "gh issue list": [idea(89, "site-idea", "approved", "in-progress"), idea(90), idea(91), idea(92)],
            "gh pr list": [],
            "git ls-remote --heads origin agent/*": "",
            "gh issue edit": "",
            "gh issue comment": "https://github.com/the-owner/the-site/issues/89#issuecomment-7099",
            "gh api --method PATCH": {"number": 0},
        }
        for number in (89, 90, 91, 92):
            self.answers[COMMENTS % number] = [graded()]
            self.answers[TIMELINE % number] = [
                labelled("site-idea", f"2026-11-25T13:00:{number - 80:02}Z"),
                labelled("approved", f"2026-11-25T13:01:{number - 80:02}Z"),
            ]
        self.shell = Shell(self.answers)
        self.enterContext(mock.patch.object(shell, "run", self.shell))
        self.file = Path(self.enterContext(tempfile.TemporaryDirectory())) / "why.md"
        self.file.write_text("Both change how a row shows its gain.\n", encoding="utf-8")

    def run_command(self, command: str, *arguments: str) -> tuple[int, str]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            code = group.main(command, [*arguments, "--file", str(self.file)])
        return code, printed.getvalue()

    def body(self, number: int) -> str:
        return self.shell.stdin[f"gh issue comment {number} --body-file -"]


class Sort(GroupTest):
    def test_sort_with_no_partner_posts_with_none_on_the_lead_and_claims_nothing(self):
        code, _ = self.run_command("sort", "89")
        self.assertEqual(code, 0)
        self.assertEqual(self.shell.changes(), ["gh issue comment 89 --body-file -"])
        self.assertEqual(
            self.body(89), "Site workflow: sorted\n\nWith: none\n\nBoth change how a row shows its gain.\n"
        )

    def test_sort_claims_each_partner_assigns_it_sets_in_progress_and_posts_joined_with_the_lead(self):
        code, _ = self.run_command("sort", "89", "--with", "90", "91")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.changes(),
            [
                "gh issue comment 89 --body-file -",
                "gh issue edit 90 --add-label in-progress --add-assignee the-owner",
                STATUS % (90, "In progress"),
                "gh issue comment 90 --body-file -",
                "gh issue edit 91 --add-label in-progress --add-assignee the-owner",
                STATUS % (91, "In progress"),
                "gh issue comment 91 --body-file -",
            ],
        )
        self.assertIn("With: #90, #91", self.body(89).splitlines())
        self.assertTrue(self.body(90).startswith("Site workflow: joined\n\nLead: #89\n"), self.body(90))

    def test_sort_refuses_a_number_that_is_not_waiting_and_changes_nothing(self):
        self.answers[COMMENTS % 91] = [graded(), said("Site workflow: plan\n\n## Verdict\n\nGo")]
        code, printed = self.run_command("sort", "89", "--with", "90", "91")
        self.assertEqual(code, 1)
        self.assertEqual(self.shell.changes(), [])
        self.assertIn("#91", printed)

    def test_sort_refuses_the_lead_itself_a_repeated_number_or_a_third_partner(self):
        for given in (["89"], ["90", "90"], ["90", "91", "92"]):
            with self.subTest(given=given):
                code, _ = self.run_command("sort", "89", "--with", *given)
                self.assertEqual(code, 1)
                self.assertEqual(self.shell.changes(), [])

    def test_sort_refuses_a_lead_sorted_already_with_other_partners(self):
        self.answers[COMMENTS % 89] = [graded(), said("Site workflow: sorted\n\nWith: none")]
        code, _ = self.run_command("sort", "89", "--with", "90")
        self.assertEqual(code, 1)
        self.assertEqual(self.shell.changes(), [])

    def test_sort_run_again_with_the_same_partners_claims_those_it_had_not_and_posts_no_second_sort(self):
        # GitHub refused a claim after the sort was posted. Refused when run again, the sort would leave #91 named
        # in the group and never claimed, and its change would ship with #89 while it waited to be worked again.
        self.answers[COMMENTS % 89] = [graded(), said("Site workflow: sorted\n\nWith: #90, #91")]
        self.answers[COMMENTS % 90] = [graded(), said("Site workflow: joined\n\nLead: #89")]
        self.answers["gh issue list"][1] = idea(90, "site-idea", "approved", "in-progress")
        code, _ = self.run_command("sort", "89", "--with", "90", "91")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.changes(),
            [
                "gh issue edit 91 --add-label in-progress --add-assignee the-owner",
                STATUS % (91, "In progress"),
                "gh issue comment 91 --body-file -",
            ],
        )

    def test_sort_refuses_a_group_whose_effort_adds_up_past_13(self):
        # The owner let ideas of different sizes go together, under a cap on their size (25 November 2026).
        self.answers[COMMENTS % 89] = [graded(effort=8)]
        self.answers[COMMENTS % 90] = [graded(effort=8)]
        code, printed = self.run_command("sort", "89", "--with", "90")
        self.assertEqual(code, 1)
        self.assertEqual(self.shell.changes(), [])
        self.assertIn("13", printed)

    def test_sort_refuses_an_idea_with_no_grade_in_points(self):
        self.answers[COMMENTS % 90] = [said("Site workflow: graded\n\nComplexity: Low\nEffort: Low")]
        code, printed = self.run_command("sort", "89", "--with", "90")
        self.assertEqual(code, 1)
        self.assertEqual(self.shell.changes(), [])
        self.assertIn("#90", printed)

    def test_sort_prints_the_lead_and_its_branch_last_for_the_run_to_make_its_branch(self):
        _, printed = self.run_command("sort", "89")
        self.assertEqual(printed.splitlines()[-2:], ["Lead: #89", "Branch: agent/89-idea-89"])

    def test_sort_refuses_a_lead_no_run_has_claimed(self):
        self.answers["gh issue list"][0] = idea(89)
        code, _ = self.run_command("sort", "89")
        self.assertEqual(code, 1)
        self.assertEqual(self.shell.changes(), [])


class AGroupElsewhere(GroupTest):
    """The sort may take a group from anywhere in the queue, led by an idea other than the one pickup claimed, which
    then waits for the next run (25 November 2026)."""

    def setUp(self):
        super().setUp()
        self.answers["gh issue view 89"] = {**idea(89, "site-idea", "approved", "in-progress"), "state": "OPEN"}

    def test_sort_hands_the_claim_to_a_lead_elsewhere_in_the_queue_and_sends_the_claimed_idea_back(self):
        code, printed = self.run_command("sort", "89", "--lead", "90", "--with", "91")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.changes(),
            [
                "gh issue edit 90 --add-label in-progress --add-assignee the-owner",
                STATUS % (90, "In progress"),
                "gh issue comment 90 --body-file -",
                "gh issue comment 90 --body-file -",
                "gh issue edit 91 --add-label in-progress --add-assignee the-owner",
                STATUS % (91, "In progress"),
                "gh issue comment 91 --body-file -",
                "gh issue edit 89 --remove-label in-progress --remove-assignee the-owner",
                STATUS % (89, "Backlog"),
                "gh issue comment 89 --body-file -",
            ],
        )
        self.assertTrue(self.body(89).startswith("Site workflow: released\n\nLead: #90\n"), self.body(89))
        self.assertEqual(printed.splitlines()[-2:], ["Lead: #90", "Branch: agent/90-idea-90"])

    def test_sort_refuses_a_lead_that_does_not_wait(self):
        self.answers[COMMENTS % 92] = [graded(), said("Site workflow: plan\n\n## Verdict\n\nGo")]
        code, _ = self.run_command("sort", "89", "--lead", "92")
        self.assertEqual(code, 1)
        self.assertEqual(self.shell.changes(), [])

    def test_a_handover_cut_short_is_finished_by_running_it_again(self):
        # GitHub refused a step after the new lead was claimed. Run again, the sort claims it no second time.
        self.answers["gh issue list"][1] = idea(90, "site-idea", "approved", "in-progress")
        picked = "Site workflow: picked up\n\nBranch: agent/90-idea-90\nTaken up: handed over from #89."
        self.answers[COMMENTS % 90] = [graded(), said(picked)]
        code, _ = self.run_command("sort", "89", "--lead", "90", "--with", "91")
        self.assertEqual(code, 0)
        self.assertNotIn("gh issue edit 90 --add-label in-progress --add-assignee the-owner", self.shell.changes())
        self.assertIn("gh issue comment 89 --body-file -", self.shell.changes())


class Release(GroupTest):
    def setUp(self):
        super().setUp()
        self.answers[COMMENTS % 90] = [said("Site workflow: joined\n\nLead: #89")]
        self.answers["gh issue view 90"] = {**idea(90, "site-idea", "approved", "in-progress"), "state": "OPEN"}

    def test_release_sends_a_partner_back_unassigned_and_in_backlog_before_it_says_so(self):
        # The labels change first: a `released` comment posted before a label change GitHub refused would leave
        # the partner in progress with no run to find it, and a second release would refuse it.
        code, _ = self.run_command("release", "90")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.changes(),
            [
                "gh issue edit 90 --remove-label in-progress --remove-assignee the-owner",
                STATUS % (90, "Backlog"),
                "gh issue comment 90 --body-file -",
            ],
        )
        self.assertTrue(self.body(90).startswith("Site workflow: released\n\nLead: #89\n"), self.body(90))

    def test_release_refuses_an_issue_that_is_no_partner(self):
        self.answers[COMMENTS % 90] = []
        code, _ = self.run_command("release", "90")
        self.assertEqual(code, 1)
        self.assertEqual(self.shell.changes(), [])


if __name__ == "__main__":
    unittest.main()
