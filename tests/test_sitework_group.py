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
            self.answers[COMMENTS % number] = []
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
        self.answers[COMMENTS % 91] = [said("Site workflow: plan\n\n## Verdict\n\nGo")]
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

    def test_sort_refuses_a_lead_that_is_sorted_already(self):
        self.answers[COMMENTS % 89] = [said("Site workflow: sorted\n\nWith: none")]
        code, _ = self.run_command("sort", "89", "--with", "90")
        self.assertEqual(code, 1)
        self.assertEqual(self.shell.changes(), [])

    def test_sort_refuses_a_lead_no_run_has_claimed(self):
        self.answers["gh issue list"][0] = idea(89)
        code, _ = self.run_command("sort", "89")
        self.assertEqual(code, 1)
        self.assertEqual(self.shell.changes(), [])


class Release(GroupTest):
    def setUp(self):
        super().setUp()
        self.answers[COMMENTS % 90] = [said("Site workflow: joined\n\nLead: #89")]
        self.answers["gh issue view 90"] = {**idea(90, "site-idea", "approved", "in-progress"), "state": "OPEN"}

    def test_release_sends_a_partner_back_to_the_queue_unassigned_and_in_backlog(self):
        code, _ = self.run_command("release", "90")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.changes(),
            [
                "gh issue comment 90 --body-file -",
                "gh issue edit 90 --remove-label in-progress --remove-assignee the-owner",
                STATUS % (90, "Backlog"),
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
