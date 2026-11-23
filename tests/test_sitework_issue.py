"""`comment`, `stop`, and `close` write the workflow's comments and labels on an issue, and the reading of an
issue that the other scripts share counts only what the owner's account wrote.

No test reaches GitHub or sends a message. `sitework.shell.run` is replaced by a stand-in that answers each
command from what the test gives it, in the shapes `gh` answers in, and keeps each command it was given. The
function that tells the owner is replaced too.
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sitework import issue, notify, shell

OWNER = "the-owner"
ADDRESS = "https://github.com/the-owner/the-site/issues/27"


class Shell:
    """Stands in for `sitework.shell.run`. A command is answered by the answer whose words it begins with, the
    longest of them when several do, and a command with no answer fails the test. An answer that is not text is
    given as the JSON `gh` would print, and one that is an error is raised."""

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
        """The commands that were run and change something: every one but a reading."""
        reads = ("gh repo view", "gh issue view", "gh pr list", "gh api repos/", "git ls-remote")
        return [line for line in self.ran if not line.startswith(reads)]


def said(body: str, by: str = OWNER, number: int = 1) -> dict:
    """A comment, as GitHub's API gives one."""
    return {
        "id": 7000 + number,
        "html_url": f"{ADDRESS}#issuecomment-{7000 + number}",
        "user": {"login": by},
        "created_at": f"2026-11-22T10:00:{number:02}Z",
        "body": body,
    }


def pull(number: int, branch: str, state: str = "MERGED", fork: bool = False) -> dict:
    """A pull request, as `gh pr list` gives one."""
    return {
        "number": number,
        "state": state,
        "headRefName": branch,
        "headRefOid": f"{number:040x}",
        "isCrossRepository": fork,
        "mergeCommit": {"oid": f"{number + 1000:040x}"} if state == "MERGED" else None,
        "mergedAt": f"2026-11-22T12:00:{number:02}Z" if state == "MERGED" else None,
    }


class IssueTest(unittest.TestCase):
    """A test with the stand-in in place, issue #27 to work on, and a file of text to post."""

    def setUp(self):
        self.answers = {
            "gh repo view": {"owner": {"id": "MDQ6", "login": OWNER}},
            "gh issue view 27": {
                "author": {"login": OWNER},
                "labels": [{"name": "site-idea"}, {"name": "approved"}, {"name": "in-progress"}],
                "number": 27,
                "state": "OPEN",
                "title": "Stop clipping the table on phones",
                "url": ADDRESS,
            },
            "gh api repos/{owner}/{repo}/issues/27/comments": [],
            "gh issue comment 27": f"{ADDRESS}#issuecomment-7099",
            "gh issue edit 27": ADDRESS,
            "gh issue close 27": "",
            "gh pr list": [pull(40, "agent/27-stop-clipping")],
            "git ls-remote origin refs/heads/agent/27-stop-clipping": "",
        }
        self.shell = Shell(self.answers)
        self.enterContext(mock.patch.object(shell, "run", self.shell))
        self.told = []
        self.sent = "sent"
        self.enterContext(mock.patch.object(notify, "send", self.tell))
        self.file = Path(self.enterContext(tempfile.TemporaryDirectory())) / "text.md"
        self.file.write_text("What the comment says.\n", encoding="utf-8")

    def tell(self, message: str) -> str:
        self.told.append(message)
        return self.sent

    def run_command(self, command: str, *arguments: str) -> tuple[int, str]:
        """Run one of the three commands with the file of text, and give its exit code and what it printed."""
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            try:
                code = issue.main(command, [*arguments, "--file", str(self.file)])
            except SystemExit as refused:  # argparse refuses a line it cannot read by exiting with 2
                code = refused.code
        return code, printed.getvalue()


class Comment(IssueTest):
    def test_a_comment_is_the_workflows_first_line_then_a_blank_line_then_the_files_text(self):
        code, _ = self.run_command("comment", "27", "review")
        self.assertEqual(code, 0)
        self.assertEqual(self.shell.changes(), ["gh issue comment 27 --body-file -"])
        self.assertEqual(
            self.shell.stdin["gh issue comment 27 --body-file -"], "Site workflow: review\n\nWhat the comment says.\n"
        )

    def test_a_plan_is_posted_when_the_issue_has_none(self):
        self.answers["gh api repos/{owner}/{repo}/issues/27/comments"] = [said("Site workflow: picked up\n\nBranch: x")]
        self.run_command("comment", "27", "plan")
        self.assertEqual(self.shell.changes(), ["gh issue comment 27 --body-file -"])

    def test_a_plan_that_is_already_there_is_edited_in_place_and_never_posted_a_second_time(self):
        self.answers["gh api repos/{owner}/{repo}/issues/27/comments"] = [
            said("Site workflow: plan\n\nThe first plan.", number=1),
            said("I would rather it wrapped.", number=2),
        ]
        self.answers["gh api --method PATCH"] = {"id": 7001}
        code, printed = self.run_command("comment", "27", "plan")
        self.assertEqual(code, 0)
        edit = "gh api --method PATCH repos/{owner}/{repo}/issues/comments/7001 --input -"
        self.assertEqual(self.shell.changes(), [edit])
        self.assertEqual(
            json.loads(self.shell.stdin[edit]), {"body": "Site workflow: plan\n\nWhat the comment says.\n"}
        )
        self.assertIn(f"{ADDRESS}#issuecomment-7001", printed)

    def test_a_strangers_comment_that_opens_as_a_plan_does_is_not_edited(self):
        self.answers["gh api repos/{owner}/{repo}/issues/27/comments"] = [
            said("Site workflow: plan\n\nNot the workflow's.", by="a-stranger")
        ]
        self.run_command("comment", "27", "plan")
        self.assertEqual(self.shell.changes(), ["gh issue comment 27 --body-file -"])

    def test_a_kind_the_workflow_does_not_write_is_refused_and_nothing_is_posted(self):
        code, _ = self.run_command("comment", "27", "approved")
        self.assertEqual(code, 2)
        self.assertEqual(self.shell.ran, [])


class Stop(IssueTest):
    def test_a_stop_posts_the_stopped_comment_swaps_in_progress_for_needs_owner_and_tells_the_owner(self):
        code, _ = self.run_command("stop", "27", "--stage", "check")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.changes(),
            [
                "gh issue comment 27 --body-file -",
                "gh issue edit 27 --remove-label in-progress --add-label needs-owner",
            ],
        )
        self.assertEqual(
            self.shell.stdin["gh issue comment 27 --body-file -"],
            "Site workflow: stopped\n\nStage: check\n\nWhat the comment says.\n",
        )
        (message,) = self.told
        for part in ("#27", "check", "Stop clipping the table on phones", ADDRESS):
            self.assertIn(part, message)

    def test_a_stop_whose_message_cannot_be_sent_warns_and_still_exits_0(self):
        self.sent = "not sent: no credential store"
        code, printed = self.run_command("stop", "27", "--stage", "ship")
        self.assertEqual(code, 0)
        self.assertIn("warning", printed)
        self.assertIn("not sent: no credential store", printed)
        self.assertIn("gh issue edit 27 --remove-label in-progress --add-label needs-owner", self.shell.ran)

    def test_a_stop_for_data_names_the_risingrepos_issue_and_the_field_and_swaps_in_progress_for_blocked_on_data(self):
        code, _ = self.run_command("stop", "27", "--data", "215", "--field", "license")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.changes(),
            [
                "gh issue comment 27 --body-file -",
                "gh issue edit 27 --remove-label in-progress --add-label blocked-on-data",
            ],
        )
        body = self.shell.stdin["gh issue comment 27 --body-file -"]
        self.assertTrue(body.startswith("Site workflow: waiting on data\n\n"), body)
        self.assertIn("RisingRepos#215", body)
        self.assertIn("Field: license", body.splitlines())
        self.assertIn("What the comment says.", body)

    def test_a_stop_for_data_sends_the_owner_no_message(self):
        self.run_command("stop", "27", "--data", "215", "--field", "license")
        self.assertEqual(self.told, [])

    def test_a_stop_for_data_that_names_no_field_is_refused_and_changes_nothing(self):
        code, _ = self.run_command("stop", "27", "--data", "215")
        self.assertEqual(code, 2)
        self.assertEqual(self.shell.ran, [])

    def test_a_stop_with_neither_a_stage_nor_data_is_refused_and_changes_nothing(self):
        code, _ = self.run_command("stop", "27")
        self.assertEqual(code, 2)
        self.assertEqual(self.shell.ran, [])

    def test_a_stage_the_workflow_does_not_have_is_refused(self):
        code, _ = self.run_command("stop", "27", "--stage", "lunch")
        self.assertEqual(code, 2)
        self.assertEqual(self.shell.ran, [])


class Close(IssueTest):
    def test_a_close_posts_shipped_closes_the_issue_removes_in_progress_and_tells_the_owner(self):
        code, _ = self.run_command("close", "27")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.changes(),
            ["gh issue comment 27 --body-file -", "gh issue close 27", "gh issue edit 27 --remove-label in-progress"],
        )
        self.assertEqual(
            self.shell.stdin["gh issue comment 27 --body-file -"], "Site workflow: shipped\n\nWhat the comment says.\n"
        )
        (message,) = self.told
        for part in ("#27", "shipped", "Stop clipping the table on phones", ADDRESS):
            self.assertIn(part, message)

    def test_a_close_deletes_the_features_branch_when_origin_still_has_it(self):
        self.answers["git ls-remote origin refs/heads/agent/27-stop-clipping"] = (
            f"{40:040x}\trefs/heads/agent/27-stop-clipping"
        )
        self.answers["git push origin --delete"] = ""
        self.run_command("close", "27")
        self.assertEqual(self.shell.changes()[-1], "git push origin --delete agent/27-stop-clipping")

    def test_a_close_asks_origin_to_delete_nothing_when_the_branch_is_already_gone(self):
        self.run_command("close", "27")
        self.assertEqual([line for line in self.shell.ran if line.startswith("git push")], [])

    def test_a_close_whose_message_cannot_be_sent_warns_and_still_exits_0(self):
        self.sent = "not sent: URLError"
        code, printed = self.run_command("close", "27")
        self.assertEqual(code, 0)
        self.assertIn("warning", printed)

    def test_a_close_refuses_an_issue_whose_pull_request_has_not_merged_and_changes_nothing(self):
        self.answers["gh pr list --state merged"] = [pull(38, "agent/2-other")]
        code, printed = self.run_command("close", "27")
        self.assertEqual(code, 1)
        self.assertIn("#27", printed)
        self.assertEqual(self.shell.changes(), [])
        self.assertEqual(self.told, [])

    def test_a_command_that_github_refuses_exits_1_with_what_it_printed(self):
        self.answers["gh issue close 27"] = shell.Failed("gh issue close 27: exit 1\nHTTP 403")
        code, printed = self.run_command("close", "27")
        self.assertEqual(code, 1)
        self.assertIn("HTTP 403", printed)


class Reading(IssueTest):
    def test_only_a_comment_the_owners_account_wrote_counts(self):
        self.answers["gh api repos/{owner}/{repo}/issues/27/comments"] = [
            said("Site workflow: review\n\nVerdict: pass", by="a-stranger", number=1),
            said("Allowed: pyproject.toml", number=2),
        ]
        self.assertEqual([comment["id"] for comment in issue.comments(27, OWNER)], [7002])

    def test_a_comment_is_the_workflows_by_its_first_line_and_the_owners_own_without_one(self):
        comments = [
            said("Site workflow: plan\n\nA plan.", number=1),
            said("Allowed: pyproject.toml", number=2),
            said("Site workflow: review\n\nVerdict: pass", number=3),
        ]
        self.assertEqual([comment["id"] for comment in issue.of_kind(comments, "review")], [7003])
        self.assertEqual([comment["id"] for comment in issue.owners_own(comments)], [7002])

    def test_a_value_is_the_rest_of_the_first_line_that_begins_with_its_name(self):
        body = "Site workflow: review\r\n\r\nVerdict: pass\r\nCommit: abc1234\r\nVerdict: later"
        self.assertEqual(issue.value(body, "Verdict"), "pass")
        self.assertEqual(issue.value(body, "Commit"), "abc1234")
        self.assertIsNone(issue.value(body, "Field"))

    def test_a_features_pull_requests_are_those_from_this_repositorys_own_branches_for_the_issue(self):
        pulls = [
            pull(38, "agent/2-other"),
            pull(39, "agent/27-from-a-fork", state="OPEN", fork=True),
            pull(40, "agent/27-stop-clipping"),
            pull(41, "agent/27-revert"),
            pull(42, "agent/270-another"),
        ]
        self.assertEqual([found["number"] for found in issue.feature(pulls, 27)], [40])
        self.assertEqual([found["number"] for found in issue.revert(pulls, 27)], [41])

    def test_the_merged_pull_request_is_the_features_newest_that_merged(self):
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping"),
            pull(41, "agent/27-revert"),
            pull(43, "agent/27-stop-clipping-again"),
            pull(45, "agent/28-latest-jump"),
        ]
        self.assertEqual(issue.merged(27)["number"], 43)

    def test_only_a_pull_request_into_main_is_asked_for(self):
        issue.pulls("open")
        (asked,) = self.shell.ran
        self.assertTrue(asked.startswith("gh pr list --state open --base main "), asked)

    def test_an_issue_with_no_merged_pull_request_has_none(self):
        self.answers["gh pr list --state merged"] = [pull(41, "agent/27-revert"), pull(45, "agent/28-latest-jump")]
        self.assertIsNone(issue.merged(27))


if __name__ == "__main__":
    unittest.main()
