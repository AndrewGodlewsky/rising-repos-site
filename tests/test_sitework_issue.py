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

from sitework import issue, shell

OWNER = "the-owner"
ADDRESS = "https://github.com/the-owner/the-site/issues/27"
ROW = ("description", "language", "topics")
DAYS = ("2026-11-21", "2026-11-22")
SCHEMA = "git show origin/main:site-data/contract/daily.schema.json"
INDEX = "git show origin/main:site-data/boards/index.json"
BOARD = "git show origin/main:site-data/boards/days/%s/daily.json"
BRANCH = "agent/27-stop-clipping"
ON_GITHUB = f"git ls-remote origin refs/heads/{BRANCH}"
LOCAL = f"git branch --list {BRANCH}"
HELD = f"git merge-base --is-ancestor {BRANCH} origin/main"
DELETE = f"git branch -D {BRANCH}"
"""The feature's branch, and the commands that ask whether GitHub has it, whether this repository has it, and
whether origin/main holds its every commit, and that delete it here."""
BACKLOG = "gh api --method PATCH repos/{owner}/{repo}/issues/27 -f status=Backlog"
"""The command that sets #27's status to Backlog, which GitHub shows under Open."""
STATUS = "gh api --method PATCH repos/{owner}/{repo}/issues/%d -f status=Backlog"
COMMENTS = "gh api repos/{owner}/{repo}/issues/%d/comments"


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
        reads = (
            "gh repo view",
            "gh issue view",
            "gh pr list",
            "gh api repos/",
            "git ls-remote",
            "git fetch",
            "git show",
            "git branch --list",
            "git branch --show-current",
            "git merge-base",
        )
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


def pull(number: int, branch: str, state: str = "MERGED", fork: bool = False, second: int | None = None) -> dict:
    """A pull request, as `gh pr list` gives one. One that merged did so in the second of its own number, so that
    a higher number merged later, unless `second` gives another."""
    return {
        "number": number,
        "state": state,
        "headRefName": branch,
        "headRefOid": f"{number:040x}",
        "isCrossRepository": fork,
        "mergeCommit": {"oid": f"{number + 1000:040x}"} if state == "MERGED" else None,
        "mergedAt": f"2026-11-22T12:00:{number if second is None else second:02}Z" if state == "MERGED" else None,
    }


class IssueTest(unittest.TestCase):
    """A test with the stand-in in place, issue #27 to work on, a file of text to post, and the data on main: a
    daily schema whose rows have a description, a language, and topics, and two board days. Every row holds a
    description, the newer board day's rows hold a language too, and no row holds topics. The feature's pull
    request has merged, and its branch is gone from GitHub and from this repository."""

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
            "gh api --method PATCH repos/{owner}/{repo}/issues/27 -f status=": {"number": 27},
            "gh pr list": [pull(40, BRANCH)],
            ON_GITHUB: "",
            LOCAL: "",
            "git fetch origin main": "",
            SCHEMA: {"properties": {"rows": {"items": {"properties": {name: {} for name in ROW}}}}},
            INDEX: {"schema_version": 1, "board_days": [{"board_day": day, "row_count": 1} for day in DAYS]},
            BOARD % DAYS[0]: {"board_day": DAYS[0], "rows": [{"description": "A tool."}]},
            BOARD % DAYS[1]: {"board_day": DAYS[1], "rows": [{"description": "A tool.", "language": "Go"}]},
        }
        self.shell = Shell(self.answers)
        self.enterContext(mock.patch.object(shell, "run", self.shell))
        self.file = Path(self.enterContext(tempfile.TemporaryDirectory())) / "text.md"
        self.file.write_text("What the comment says.\n", encoding="utf-8")

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

    def test_a_grade_is_posted_as_the_workflows_comment_of_kind_graded(self):
        code, _ = self.run_command("comment", "27", "graded")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.stdin["gh issue comment 27 --body-file -"], "Site workflow: graded\n\nWhat the comment says.\n"
        )

    def test_a_sorted_joined_or_released_comment_cannot_be_posted_by_hand(self):
        # Each of these goes with a change of labels that only `sort` and `release` make, so a comment of one
        # posted alone would say an idea is in a group, or out of one, when its labels say otherwise.
        for kind in ("sorted", "joined", "released"):
            with self.subTest(kind=kind):
                code, _ = self.run_command("comment", "27", kind)
                self.assertEqual(code, 2)
                self.assertEqual(self.shell.ran, [])


class Stop(IssueTest):
    def test_a_stop_posts_stopped_swaps_in_progress_for_needs_owner_unassigns_and_sets_backlog(self):
        # A stopped issue is no longer one a run is at work on, so it leaves the owner's list of assigned issues,
        # and goes back to Backlog, which GitHub shows under Open and not under Active.
        code, _ = self.run_command("stop", "27", "--stage", "check")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.changes(),
            [
                "gh issue comment 27 --body-file -",
                "gh issue edit 27 --remove-label in-progress --add-label needs-owner --remove-assignee the-owner",
                BACKLOG,
            ],
        )
        self.assertEqual(
            self.shell.stdin["gh issue comment 27 --body-file -"],
            "Site workflow: stopped\n\nStage: check\n\nWhat the comment says.\n",
        )

    def test_a_stop_for_data_names_the_risingrepos_issue_and_the_field_and_swaps_in_progress_for_blocked_on_data(self):
        code, _ = self.run_command("stop", "27", "--data", "215", "--field", "homepage")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.changes(),
            [
                "gh issue comment 27 --body-file -",
                "gh issue edit 27 --remove-label in-progress --add-label blocked-on-data --remove-assignee the-owner",
                BACKLOG,
            ],
        )
        body = self.shell.stdin["gh issue comment 27 --body-file -"]
        self.assertTrue(body.startswith("Site workflow: waiting on data\n\n"), body)
        self.assertIn("RisingRepos#215", body)
        self.assertIn("Field: homepage", body.splitlines())
        self.assertIn("What the comment says.", body)

    def test_a_stop_for_data_whose_field_is_already_in_the_schema_and_the_newest_board_is_refused(self):
        for field in ("description", "language"):
            with self.subTest(field=field):
                code, printed = self.run_command("stop", "27", "--data", "215", "--field", field)
                self.assertEqual(code, 1)
                self.assertEqual(self.shell.changes(), [])
                for part in (f"`{field}`", "already", "more exact"):
                    self.assertIn(part, printed)

    def test_a_stop_for_data_whose_field_the_schema_holds_and_the_newest_board_does_not_goes_ahead(self):
        code, _ = self.run_command("stop", "27", "--data", "215", "--field", "topics")
        self.assertEqual(code, 0)
        self.assertIn(
            "gh issue edit 27 --remove-label in-progress --add-label blocked-on-data --remove-assignee the-owner",
            self.shell.ran,
        )

    def test_a_stop_for_data_reads_the_data_as_main_holds_it_on_origin_after_a_fetch(self):
        self.run_command("stop", "27", "--data", "215", "--field", "language")
        self.assertEqual(self.shell.ran, ["git fetch origin main", SCHEMA, INDEX, BOARD % "2026-11-22"])

    def test_a_stop_for_the_owner_reads_none_of_the_data(self):
        self.run_command("stop", "27", "--stage", "check")
        self.assertEqual([line for line in self.shell.ran if line.startswith("git")], [])

    def test_a_stop_for_data_that_names_no_field_is_refused_and_changes_nothing(self):
        code, _ = self.run_command("stop", "27", "--data", "215")
        self.assertEqual(code, 2)
        self.assertEqual(self.shell.ran, [])

    def test_a_stop_with_neither_a_stage_nor_data_is_refused_and_changes_nothing(self):
        code, _ = self.run_command("stop", "27")
        self.assertEqual(code, 2)
        self.assertEqual(self.shell.ran, [])

    def test_an_issue_whose_mend_failed_is_stopped_at_the_stage_named_mend(self):
        code, _ = self.run_command("stop", "27", "--stage", "mend")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.stdin["gh issue comment 27 --body-file -"],
            "Site workflow: stopped\n\nStage: mend\n\nWhat the comment says.\n",
        )
        self.assertIn(
            "gh issue edit 27 --remove-label in-progress --add-label needs-owner --remove-assignee the-owner",
            self.shell.ran,
        )

    def test_a_stage_the_workflow_does_not_have_is_refused(self):
        code, _ = self.run_command("stop", "27", "--stage", "lunch")
        self.assertEqual(code, 2)
        self.assertEqual(self.shell.ran, [])


class Partners(IssueTest):
    """A group is read from its lead's newest `sorted` comment, and an idea stays in it while its own newest
    comment of the workflow's, past any grade, is `joined` or `stopped` with the lead's `Lead:` line (25 November
    2026). Only what the owner's account wrote counts, as everywhere here."""

    def comments_on(self, number: int, *comments: dict) -> None:
        self.answers[f"gh api repos/{{owner}}/{{repo}}/issues/{number}/comments"] = list(comments)

    def partners(self) -> list[int]:
        return issue.partners(89, lambda number: issue.comments(number, OWNER))

    def test_a_partner_is_one_the_leads_sorted_comment_names_and_that_joined_it(self):
        self.comments_on(89, said("Site workflow: sorted\n\nWith: #90, #91\n\nBoth change the row's gain."))
        self.comments_on(90, said("Site workflow: joined\n\nLead: #89"))
        self.comments_on(91, said("Site workflow: joined\n\nLead: #77"))
        self.assertEqual(self.partners(), [90])

    def test_a_partner_that_was_released_is_no_longer_one(self):
        self.comments_on(89, said("Site workflow: sorted\n\nWith: #90"))
        self.comments_on(
            90,
            said("Site workflow: joined\n\nLead: #89", number=1),
            said("Site workflow: released\n\nLead: #89\n\nIt fits a run of its own.", number=2),
        )
        self.assertEqual(self.partners(), [])


class AGroup(IssueTest):
    """#28 joined #27's group. A stop of the lead stops the group, or at Shape, where no code is written yet,
    sends the partner back to wait for a run of its own. A close of the lead closes the partner first, so that a
    close cut short leaves the lead in progress for the next run to finish (25 November 2026)."""

    PARTNER = "Site workflow: joined\n\nLead: #27"

    def setUp(self):
        super().setUp()
        self.answers[COMMENTS % 27] = [said("Site workflow: sorted\n\nWith: #28")]
        self.answers[COMMENTS % 28] = [said(self.PARTNER)]
        self.answers["gh issue view 28"] = {
            "labels": [{"name": "site-idea"}, {"name": "in-progress"}],
            "number": 28,
            "state": "OPEN",
        }
        for command in ("comment", "edit", "close"):
            self.answers[f"gh issue {command} 28"] = ""
        self.answers["gh api --method PATCH repos/{owner}/{repo}/issues/28 -f status="] = {"number": 28}

    def partner_changes(self) -> list[str]:
        return [line for line in self.shell.changes() if " 28" in line or "/28 " in line]

    def test_a_stop_of_the_lead_stops_each_partner_with_it_and_names_the_lead(self):
        code, _ = self.run_command("stop", "27", "--stage", "check")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.partner_changes(),
            [
                "gh issue comment 28 --body-file -",
                "gh issue edit 28 --remove-label in-progress --add-label needs-owner --remove-assignee the-owner",
                STATUS % 28,
            ],
        )
        body = self.shell.stdin["gh issue comment 28 --body-file -"]
        self.assertTrue(body.startswith("Site workflow: stopped\n\nLead: #27\nStage: check\n"), body)

    def test_a_stop_of_the_lead_at_shape_sends_each_partner_back_to_wait(self):
        # At Shape no code is written, so the partner need not wait for the lead's answer.
        self.run_command("stop", "27", "--stage", "shape")
        self.assertEqual(
            self.partner_changes(),
            [
                "gh issue edit 28 --remove-label in-progress --remove-assignee the-owner",
                STATUS % 28,
                "gh issue comment 28 --body-file -",
            ],
        )
        body = self.shell.stdin["gh issue comment 28 --body-file -"]
        self.assertTrue(body.startswith("Site workflow: released\n\nLead: #27\n"), body)

    def test_a_stop_of_the_lead_for_data_sends_each_partner_back_to_wait(self):
        # Only Shape finds the data wanting, so this too comes before any code is written.
        self.run_command("stop", "27", "--data", "215", "--field", "topics")
        body = self.shell.stdin["gh issue comment 28 --body-file -"]
        self.assertTrue(body.startswith("Site workflow: released\n\nLead: #27\n"), body)

    def test_a_stop_of_a_partner_stops_it_alone_and_it_leaves_the_group(self):
        code, _ = self.run_command("stop", "28", "--stage", "shape")
        self.assertEqual(code, 0)
        self.assertEqual([line for line in self.shell.changes() if " 27" in line or "/27 " in line], [])
        body = self.shell.stdin["gh issue comment 28 --body-file -"]
        self.assertNotIn("Lead:", body)

    def test_a_close_of_the_lead_closes_each_partner_first_with_a_shipped_comment_that_names_the_lead(self):
        code, _ = self.run_command("close", "27")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.changes()[:4],
            [
                "gh issue comment 28 --body-file -",
                "gh issue close 28",
                "gh issue edit 28 --remove-label in-progress",
                "gh issue comment 27 --body-file -",
            ],
        )
        body = self.shell.stdin["gh issue comment 28 --body-file -"]
        self.assertTrue(body.startswith("Site workflow: shipped\n\nLead: #27\n"), body)
        self.assertIn("#40", body)

    def test_a_close_given_a_partner_is_refused_and_names_the_lead(self):
        code, printed = self.run_command("close", "28")
        self.assertEqual(code, 1)
        self.assertEqual(self.shell.changes(), [])
        self.assertIn("#27", printed)

    def test_a_close_that_stopped_after_its_partners_finishes_without_posting_twice(self):
        self.answers[COMMENTS % 28] = [
            said(self.PARTNER, number=1),
            said("Site workflow: shipped\n\nLead: #27\n\nShipped with #27.", number=2),
        ]
        self.answers["gh issue view 28"]["state"] = "CLOSED"
        self.run_command("close", "27")
        self.assertEqual(self.partner_changes(), [])

    def test_a_close_run_again_closes_a_partner_whose_shipped_note_was_posted_and_that_is_still_open(self):
        # GitHub refused the close after the note, so the partner would stay in progress with no run to find it.
        self.answers[COMMENTS % 28] = [
            said(self.PARTNER, number=1),
            said("Site workflow: shipped\n\nLead: #27\n\nShipped with #27.", number=2),
        ]
        self.run_command("close", "27")
        self.assertEqual(self.partner_changes(), ["gh issue close 28", "gh issue edit 28 --remove-label in-progress"])

    def test_a_stop_of_a_partner_after_shape_is_refused_and_says_to_send_it_back(self):
        # Its code is on the lead's branch by then, so stopped alone it would ship with the lead and be worked again.
        code, printed = self.run_command("stop", "28", "--stage", "build")
        self.assertEqual(code, 1)
        self.assertEqual(self.shell.changes(), [])
        self.assertIn("sitework release 28", printed)


class Status(IssueTest):
    """GitHub's status of an issue decides the tab it shows under: Backlog under Open, and In progress under
    Active. Taking the owner off an issue does not move it back from Active, so a stop sets the status itself.
    The statuses are a preview of GitHub's, so one GitHub refuses is told and fails nothing (25 November 2026)."""

    def test_a_status_github_refuses_is_one_printed_line_and_the_stop_still_exits_0(self):
        self.answers[BACKLOG] = shell.Failed("gh api: exit 1\nHTTP 422: statuses are not available")
        code, printed = self.run_command("stop", "27", "--stage", "build")
        self.assertEqual(code, 0)
        self.assertIn(
            "gh issue edit 27 --remove-label in-progress --add-label needs-owner --remove-assignee the-owner",
            self.shell.ran,
        )
        self.assertIn("#27", printed)
        self.assertIn("Backlog", printed)


class Close(IssueTest):
    def test_a_close_posts_shipped_closes_the_issue_and_removes_in_progress(self):
        code, _ = self.run_command("close", "27")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.changes(),
            ["gh issue comment 27 --body-file -", "gh issue close 27", "gh issue edit 27 --remove-label in-progress"],
        )
        self.assertEqual(
            self.shell.stdin["gh issue comment 27 --body-file -"], "Site workflow: shipped\n\nWhat the comment says.\n"
        )

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

    def test_a_close_refuses_an_issue_whose_pull_request_has_not_merged_and_changes_nothing(self):
        self.answers["gh pr list --state merged"] = [pull(38, "agent/2-other")]
        code, printed = self.run_command("close", "27")
        self.assertEqual(code, 1)
        self.assertIn("#27", printed)
        self.assertEqual(self.shell.changes(), [])

    def test_a_close_refuses_a_feature_whose_every_merge_was_reverted_and_changes_nothing(self):
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping"),
            pull(42, "agent/27-stop-clipping"),
            pull(43, "agent/27-revert"),
        ]
        code, printed = self.run_command("close", "27")
        self.assertEqual(code, 1)
        for part in ("#27", "reverted", "nothing was changed"):
            self.assertIn(part, printed)
        self.assertEqual(self.shell.changes(), [])

    def test_a_close_of_a_feature_that_was_reverted_and_then_landed_again_goes_ahead(self):
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping"),
            pull(41, "agent/27-revert"),
            pull(43, "agent/27-stop-clipping-again"),
        ]
        self.answers["git ls-remote origin refs/heads/agent/27-stop-clipping-again"] = (
            f"{43:040x}\trefs/heads/agent/27-stop-clipping-again"
        )
        self.answers["git push origin --delete"] = ""
        code, _ = self.run_command("close", "27")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.changes(),
            [
                "gh issue comment 27 --body-file -",
                "gh issue close 27",
                "gh issue edit 27 --remove-label in-progress",
                "git push origin --delete agent/27-stop-clipping-again",
            ],
        )

    def test_a_close_after_a_mend_goes_ahead_since_both_merges_stand(self):
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping"),
            pull(42, "agent/27-stop-clipping"),
        ]
        code, _ = self.run_command("close", "27")
        self.assertEqual(code, 0)
        self.assertIn("gh issue close 27", self.shell.ran)

    def test_a_command_that_github_refuses_exits_1_with_what_it_printed(self):
        self.answers["gh issue close 27"] = shell.Failed("gh issue close 27: exit 1\nHTTP 403")
        code, printed = self.run_command("close", "27")
        self.assertEqual(code, 1)
        self.assertIn("HTTP 403", printed)


class TheLocalBranch(IssueTest):
    """A finished run leaves no branch behind, so `close` deletes the feature's branch in this repository as well
    as on GitHub, and throws no work away to do it. Here the repository has the branch, origin/main holds its
    every commit, and the checkout is on main, unless a test says otherwise."""

    def setUp(self):
        super().setUp()
        self.answers[LOCAL] = BRANCH
        self.answers[HELD] = ""
        self.answers["git branch --show-current"] = "main"
        self.answers["git switch --detach"] = ""
        self.answers[DELETE] = f"Deleted branch {BRANCH} (was 0000028)."

    def git(self) -> list[str]:
        """The git commands that were run, in the order they ran."""
        return [line for line in self.shell.ran if line.startswith("git")]

    def assertLeft(self, printed: str, *parts: str) -> None:
        """Expect exactly one printed line to name the branch, with each of `parts` in it."""
        (line,) = [line for line in printed.splitlines() if BRANCH in line]
        for part in parts:
            self.assertIn(part, line)

    def test_a_close_deletes_the_branch_on_github_and_then_locally_once_origin_main_holds_its_every_commit(self):
        self.answers[ON_GITHUB] = f"{40:040x}\trefs/heads/{BRANCH}"
        self.answers["git push origin --delete"] = ""
        code, printed = self.run_command("close", "27")
        self.assertEqual(code, 0, printed)
        self.assertEqual(
            self.git(),
            [
                ON_GITHUB,
                f"git push origin --delete {BRANCH}",
                LOCAL,
                "git fetch origin main",
                HELD,
                "git branch --show-current",
                DELETE,
            ],
        )
        self.assertNotIn(BRANCH, printed)

    def test_main_is_fetched_from_origin_before_it_is_asked_whether_it_holds_the_local_branch(self):
        self.run_command("close", "27")
        self.assertLess(self.shell.ran.index("git fetch origin main"), self.shell.ran.index(HELD))

    def test_a_local_branch_that_holds_a_commit_main_does_not_is_left_and_says_so(self):
        self.answers[HELD] = shell.Failed(f"{HELD}: exit 1")
        code, printed = self.run_command("close", "27")
        self.assertEqual(code, 0, printed)
        self.assertLeft(printed, "is left", "a commit that main does not", "not thrown away")
        self.assertNotIn(DELETE, self.shell.ran)

    def test_a_checkout_that_is_on_the_branch_leaves_it_with_switch_detach_before_the_branch_is_deleted(self):
        self.answers["git branch --show-current"] = BRANCH
        code, printed = self.run_command("close", "27")
        self.assertEqual(code, 0, printed)
        self.assertEqual(self.git()[-3:], ["git branch --show-current", "git switch --detach", DELETE])

    def test_a_checkout_on_a_branch_whose_work_main_does_not_hold_stays_on_that_branch(self):
        self.answers["git branch --show-current"] = BRANCH
        self.answers[HELD] = shell.Failed(f"{HELD}: exit 1")
        code, printed = self.run_command("close", "27")
        self.assertEqual(code, 0, printed)
        self.assertLeft(printed, "is left")
        self.assertNotIn("git switch --detach", self.shell.ran)
        self.assertNotIn(DELETE, self.shell.ran)

    def test_a_local_branch_that_is_not_there_is_nothing_to_delete_and_is_no_error(self):
        self.answers[LOCAL] = ""
        code, printed = self.run_command("close", "27")
        self.assertEqual(code, 0, printed)
        self.assertEqual(self.git(), [ON_GITHUB, LOCAL])
        self.assertNotIn(BRANCH, printed)

    def test_a_local_delete_that_git_refuses_is_one_printed_line_and_no_failure(self):
        refusal = f"error: cannot delete branch '{BRANCH}' used by worktree at '/another/checkout'"
        self.answers[DELETE] = shell.Failed(f"{DELETE}: exit 1\n{refusal}")
        code, printed = self.run_command("close", "27")
        self.assertEqual(code, 0, printed)
        self.assertEqual(self.git()[-1], DELETE)
        self.assertLeft(printed, "is left", refusal)
        self.assertIn("gh issue close 27", self.shell.ran)

    def test_a_main_that_cannot_be_fetched_leaves_the_local_branch_with_one_printed_line_and_no_failure(self):
        refusal = "fatal: unable to access 'https://github.com/the-owner/the-site/'"
        self.answers["git fetch origin main"] = shell.Failed(f"git fetch origin main: exit 128\n{refusal}", 128)
        code, printed = self.run_command("close", "27")
        self.assertEqual(code, 0, printed)
        self.assertLeft(printed, "is left", refusal)
        self.assertEqual(self.git()[-1], "git fetch origin main")

    def test_a_local_branch_git_cannot_hold_against_main_is_left_with_what_git_said_and_no_failure(self):
        refusal = "fatal: Not a valid object name origin/main"
        self.answers[HELD] = shell.Failed(f"{HELD}: exit 128\n{refusal}", 128)
        code, printed = self.run_command("close", "27")
        self.assertEqual(code, 0, printed)
        self.assertLeft(printed, "is left", refusal)
        self.assertNotIn("a commit that main does not", printed)
        self.assertEqual(self.git()[-1], HELD)


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

    def test_a_comment_whose_first_line_is_nearly_the_workflows_is_not_the_owners_own(self):
        nearly = [
            "Site workflow: Review",
            "**Site workflow: review**",
            "Site workflow: look back",
            "> Site workflow: plan",
            "## site workflow: stopped",
            "  SITE WORKFLOW: review",
            "- `Site workflow: review`",
            "1. Site workflow: review",
            "\n\n_Site workflow:review_",
        ]
        comments = [said(f"{first}\n\nAllowed: pyproject.toml", number=number) for number, first in enumerate(nearly)]
        self.assertEqual(issue.owners_own(comments), [])
        self.assertEqual(issue.of_kind(comments, "review"), [])

    def test_a_comment_that_names_the_workflows_first_line_anywhere_but_at_its_start_is_the_owners_own(self):
        comments = [
            said("I read the Site workflow: review comment.\n\nAllowed: pyproject.toml", number=1),
            said("Yes, go on.\nSite workflow: review", number=2),
            said("", number=3),
        ]
        self.assertEqual([comment["id"] for comment in issue.owners_own(comments)], [7001, 7002, 7003])

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

    def test_a_pull_request_older_than_the_issue_is_not_the_issues(self):
        pulls = [
            pull(1, "agent/38-preview-site"),
            pull(2, "agent/38-revert"),
            pull(38, "agent/38-its-own-number"),
            pull(45, "agent/38-wrap-the-table"),
            pull(46, "agent/38-revert"),
        ]
        self.assertEqual([found["number"] for found in issue.feature(pulls, 38)], [45])
        self.assertEqual([found["number"] for found in issue.revert(pulls, 38)], [46])

    def test_an_issue_whose_only_merged_pull_request_is_older_than_it_has_none(self):
        self.answers["gh pr list --state merged"] = [pull(1, "agent/38-preview-site")]
        self.assertIsNone(issue.merged(38))

    def test_the_merged_pull_request_is_the_features_newest_that_merged(self):
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping"),
            pull(41, "agent/27-revert"),
            pull(43, "agent/27-stop-clipping-again"),
            pull(45, "agent/28-latest-jump"),
        ]
        self.assertEqual(issue.merged(27)["number"], 43)

    def test_the_merged_revert_is_the_newest_merged_pull_request_that_reverts_the_feature(self):
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping"),
            pull(41, "agent/27-revert"),
            pull(43, "agent/27-stop-clipping-again"),
            pull(44, "agent/27-revert"),
            pull(45, "agent/28-revert"),
            pull(46, "agent/27-revert", fork=True),
        ]
        self.assertEqual(issue.reverted(27)["number"], 44)

    def test_an_issue_whose_feature_merged_and_was_not_reverted_has_no_merged_revert(self):
        self.answers["gh pr list --state merged"] = [pull(40, "agent/27-stop-clipping"), pull(45, "agent/28-revert")]
        self.assertIsNone(issue.reverted(27))

    def test_every_merge_of_a_feature_stands_while_no_revert_of_it_has_merged_the_newest_first(self):
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping"),
            pull(42, "agent/27-stop-clipping"),
            pull(45, "agent/28-latest-jump"),
        ]
        self.assertEqual([found["number"] for found in issue.standing(27)], [42, 40])

    def test_a_merge_that_a_merged_revert_already_undid_does_not_stand(self):
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping"),
            pull(41, "agent/27-revert"),
            pull(43, "agent/27-stop-clipping"),
            pull(44, "agent/27-stop-clipping"),
        ]
        self.assertEqual([found["number"] for found in issue.standing(27)], [44, 43])

    def test_no_merge_stands_once_a_revert_has_merged_after_the_newest_of_them(self):
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping"),
            pull(42, "agent/27-stop-clipping"),
            pull(43, "agent/27-revert"),
        ]
        self.assertEqual(issue.standing(27), [])

    def test_a_merge_stands_by_when_it_merged_and_not_by_its_number(self):
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping", second=50),
            pull(41, "agent/27-revert", second=45),
            pull(43, "agent/27-stop-clipping", second=44),
            pull(44, "agent/27-stop-clipping", second=55),
        ]
        self.assertEqual([found["number"] for found in issue.standing(27)], [44, 40])

    def test_a_revert_of_another_issue_or_from_a_fork_undoes_no_merge_of_this_one(self):
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping"),
            pull(45, "agent/28-revert"),
            pull(46, "agent/27-revert", fork=True),
        ]
        self.assertEqual([found["number"] for found in issue.standing(27)], [40])

    def test_an_issue_with_no_merged_pull_request_has_no_merge_that_stands(self):
        self.answers["gh pr list --state merged"] = [pull(41, "agent/27-revert"), pull(45, "agent/28-latest-jump")]
        self.assertEqual(issue.standing(27), [])

    def test_the_merges_that_stand_are_read_from_one_asking_for_the_merged_pull_requests(self):
        self.answers["gh pr list --state merged"] = [pull(40, "agent/27-stop-clipping"), pull(41, "agent/27-revert")]
        issue.standing(27)
        (asked,) = self.shell.ran
        self.assertTrue(asked.startswith("gh pr list --state merged "), asked)

    def test_only_a_pull_request_into_main_is_asked_for(self):
        issue.pulls("open")
        (asked,) = self.shell.ran
        self.assertTrue(asked.startswith("gh pr list --state open --base main "), asked)

    def test_an_issue_with_no_merged_pull_request_has_none(self):
        self.answers["gh pr list --state merged"] = [pull(41, "agent/27-revert"), pull(45, "agent/28-latest-jump")]
        self.assertIsNone(issue.merged(27))


if __name__ == "__main__":
    unittest.main()
