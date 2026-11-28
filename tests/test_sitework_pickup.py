"""`pickup` chooses the issue a run works on, in the order docs/workflow-plan.md, section 3, gives, and changes
nothing on GitHub unless it is asked to claim.

No test reaches GitHub or Orca. `sitework.shell.run` is replaced by a stand-in that answers each
command from what the test gives it, in the shapes `gh`, `git`, and `orca` answer in, and keeps each command it
was given. Each test starts from a healthy site and the four
ideas the owner approved, #27 first, and changes the one thing it is about.
"""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sitework import issue, pickup, shell

OWNER = "the-owner"
HEAD = "d" * 40
DEPLOYS = "gh run list --workflow Build and deploy"
EVALS = "gh run list --workflow Site eval"
COMMENTS = "gh api repos/{owner}/{repo}/issues/%d/comments"
TIMELINE = "gh api repos/{owner}/{repo}/issues/%d/timeline"
SCHEMA = "git show origin/main:site-data/contract/daily.schema.json"
INDEX = "git show origin/main:site-data/boards/index.json"
BOARD = "git show origin/main:site-data/boards/days/%s/daily.json"
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


def run(number: int, conclusion: str = "success", made: str = "23:30:16", done: str = "23:32:23") -> dict:
    """A run of a workflow for the head of main, as `gh run list` gives one. One with no conclusion is still
    running."""
    return {
        "conclusion": conclusion,
        "createdAt": f"2026-11-22T{made}Z",
        "databaseId": number,
        "headSha": HEAD,
        "status": "completed" if conclusion else "in_progress",
        "updatedAt": f"2026-11-22T{done}Z",
        "url": f"https://github.com/the-owner/the-site/actions/runs/{number}",
    }


def idea(number: int, title: str, *labels: str, by: str = OWNER) -> dict:
    """An open issue, as `gh issue list` gives one. With no labels named, it is an idea the owner approved."""
    names = labels or ("site-idea", "approved")
    return {
        "author": {"id": "MDQ6", "is_bot": False, "login": by, "name": ""},
        "labels": [{"id": "LA_", "name": name, "description": "", "color": "0e8a16"} for name in names],
        "number": number,
        "title": title,
    }


def labelled(name: str, when: str, by: str = OWNER) -> dict:
    """A label put on an issue, as the issue's timeline gives it."""
    return {"event": "labeled", "actor": {"login": by}, "created_at": when, "label": {"name": name, "color": "0e8a16"}}


def said(body: str, by: str = OWNER, number: int = 1) -> dict:
    """A comment, as GitHub's API gives one."""
    return {
        "id": 7000 + number,
        "html_url": f"https://github.com/the-owner/the-site/issues/27#issuecomment-{7000 + number}",
        "user": {"login": by},
        "created_at": f"2026-11-22T18:00:{number:02}Z",
        "body": body,
    }


def pull(number: int, branch: str, state: str = "OPEN", fork: bool = False) -> dict:
    """A pull request, as `gh pr list` gives one."""
    return {
        "number": number,
        "state": state,
        "headRefName": branch,
        "headRefOid": f"{number:040x}",
        "isCrossRepository": fork,
        "mergeCommit": {"oid": f"{number + 1000:040x}"} if state == "MERGED" else None,
        "mergedAt": "2026-11-22T20:00:00Z" if state == "MERGED" else None,
    }


def merged(number: int, branch: str, at: str) -> dict:
    """A pull request that merged at `at`, a time of day, for a test that turns on which of two merged later."""
    return {**pull(number, branch, "MERGED"), "mergedAt": f"2026-11-22T{at}Z"}


def worktree(path: str, branch: str) -> str:
    """One worktree, as `git worktree list --porcelain` prints it."""
    return f"worktree {path}\nHEAD {HEAD}\nbranch refs/heads/{branch}\n"


def orca(path: str, *states: str, session: str = "session-1") -> dict:
    """What `orca worktree ps --json` prints for one worktree, with an agent in each of `states`."""
    agents = [{"state": state, "agentType": "claude", "orcaSessionId": session} for state in states]
    row = {"path": path, "branch": "refs/heads/whatever", "repo": "the-site", "agents": agents}
    return {"id": "x", "ok": True, "result": {"worktrees": [row], "totalCount": 1, "truncated": False}}


class PickupTest(unittest.TestCase):
    def setUp(self):
        self.common = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.answers = {
            DEPLOYS: [run(138)],
            EVALS: [run(61, made="23:32:26", done="23:34:58")],
            "git rev-parse --path-format=absolute --git-common-dir": str(self.common),
            "gh repo view": {"owner": {"id": "MDQ6", "login": OWNER}},
            "gh issue list": [
                idea(30, "Mark repo names as links that leave the site"),
                idea(29, "Make the Baseline chart identifiable on a phone"),
                idea(28, "Show a Latest jump in the date bar on phones"),
                idea(27, "Stop clipping the board-history table mid-word on phones"),
            ],
            "gh pr list": [pull(31, "agent/212-agent-instructions", "MERGED")],
            "git ls-remote --heads origin agent/*": "",
            "git worktree list --porcelain": worktree("/work/site", "main"),
            "gh issue edit": "",
            "gh issue comment": "https://github.com/the-owner/the-site/issues/27#issuecomment-7099",
            "git fetch origin main": "",
            "gh api --method PATCH": {"number": 0},
        }
        for number in (27, 28, 29, 30):
            self.answers[COMMENTS % number] = []
            self.answers[TIMELINE % number] = [
                labelled("site-idea", f"2026-11-22T16:59:{number}Z"),
                labelled("approved", f"2026-11-22T17:00:{number}Z"),
            ]
        self.shell = Shell(self.answers)
        self.enterContext(mock.patch.object(shell, "run", self.shell))
        self.enterContext(mock.patch.dict(os.environ))
        os.environ.pop("ORCA_AGENT_SESSION_ID", None)

    def run_command(self, *arguments: str) -> tuple[int, dict]:
        """Run `pickup`, and give its exit code and the JSON object it printed."""
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = pickup.main("pickup", list(arguments))
        return code, json.loads(printed.getvalue())

    def only(self, *numbers: int) -> None:
        """Leave only these of the four ideas open."""
        self.answers["gh issue list"] = [one for one in self.answers["gh issue list"] if one["number"] in numbers]

    def label(self, number: int, *labels: str) -> None:
        """Give an open issue these labels in place of its own."""
        (one,) = [one for one in self.answers["gh issue list"] if one["number"] == number]
        one["labels"] = [{"id": "LA_", "name": name, "description": "", "color": "0e8a16"} for name in labels]


class IsTheSiteHealthy(PickupTest):
    def test_a_newest_deploy_that_is_still_running_ends_the_run_with_3(self):
        self.answers[DEPLOYS] = [run(139, conclusion="")]
        code, printed = self.run_command()
        self.assertEqual(code, 3)
        self.assertEqual(list(printed), ["why"])
        self.assertIn("not finished", printed["why"])

    def test_the_newest_deploy_is_looked_for_among_the_pushes_to_main(self):
        self.run_command()
        (asked,) = [line for line in self.shell.ran if line.startswith(DEPLOYS)]
        self.assertIn("--branch main --event push --limit 1", asked)

    def test_a_newest_deploy_that_failed_exits_4_and_says_which_run(self):
        self.answers[DEPLOYS] = [run(139, conclusion="failure")]
        code, printed = self.run_command()
        self.assertEqual(code, 4)
        self.assertEqual(list(printed), ["why"])
        self.assertIn("actions/runs/139", printed["why"])

    def test_an_eval_that_has_not_followed_the_newest_deploy_yet_ends_the_run_with_3(self):
        self.answers[EVALS] = [run(60, conclusion="failure", made="20:32:09", done="20:34:49")]
        code, printed = self.run_command()
        self.assertEqual(code, 3)

    def test_an_eval_that_is_still_running_ends_the_run_with_3(self):
        self.answers[EVALS] = [run(61, conclusion="", made="23:32:26", done="23:32:26")]
        code, printed = self.run_command()
        self.assertEqual(code, 3)
        self.assertEqual(list(printed), ["why"])

    def test_a_failed_eval_exits_4_and_nothing_is_picked_up(self):
        self.answers[EVALS] = [run(61, conclusion="failure", made="23:32:26", done="23:34:58")]
        code, printed = self.run_command("--claim")
        self.assertEqual(code, 4)
        self.assertEqual(list(printed), ["why"])
        self.assertIn("actions/runs/61", printed["why"])
        self.assertEqual(self.shell.changes(), [])


class IsARunStillAtWork(PickupTest):
    """A run takes `in-progress` off its issue when it closes it, and then looks back over itself for some minutes
    more. A check of the schedule that fell in those minutes would start the next issue beside it. So what is
    asked is whether an agent is at work on any feature's branch, whatever the labels say. Here a worktree is
    still on the branch of #26, which is closed and is none of the open ideas."""

    def setUp(self):
        super().setUp()
        self.answers["git worktree list --porcelain"] = "\n".join(
            [worktree("/work/site", "main"), worktree("/work/Earlier-Run", "agent/26-an-earlier-idea")]
        )

    def test_a_run_whose_issue_is_closed_and_whose_agent_is_still_at_work_ends_the_run_with_3(self):
        self.answers["orca worktree ps --json"] = orca("/work/Earlier-Run", "done", "working")
        code, printed = self.run_command("--claim")
        self.assertEqual((code, list(printed)), (3, ["why"]))
        self.assertIn("agent/26-an-earlier-idea", printed["why"])
        self.assertEqual(self.shell.changes(), [])

    def test_nothing_is_asked_of_github_while_a_run_is_at_work(self):
        self.answers["orca worktree ps --json"] = orca("/work/Earlier-Run", "working")
        self.run_command()
        self.assertEqual([line for line in self.shell.ran if line.startswith("gh ")], [])

    def test_a_run_whose_agent_has_ended_holds_nothing_up(self):
        self.answers["orca worktree ps --json"] = orca("/work/Earlier-Run", "done")
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 27, "new"))

    def test_an_agent_at_work_on_a_branch_that_is_no_features_holds_nothing_up(self):
        self.answers["orca worktree ps --json"] = orca("/work/site", "working")
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"]), (0, 27))

    def test_the_agent_that_asks_is_not_a_run_at_work(self):
        self.answers["orca worktree ps --json"] = orca("/work/Earlier-Run", "working", session="this-one")
        os.environ["ORCA_AGENT_SESSION_ID"] = "this-one"
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"]), (0, 27))

    def test_a_run_that_left_its_features_branch_is_still_at_work_while_its_agent_is(self):
        # Which branch a run's worktree is on is the run's own doing, and it may leave the feature's branch once
        # its issue is closed. The checkout it claimed from is written down, so it is found whatever it is on.
        self.answers["git worktree list --porcelain"] = "\n".join(
            [worktree("/work/site", "main"), worktree("/work/Claimed-Run", "the-owner/a-workspace")]
        )
        (self.common / pickup.RUNS).write_text("/work/Claimed-Run\n", encoding="utf-8")
        self.answers["orca worktree ps --json"] = orca("/work/Claimed-Run", "working")
        code, printed = self.run_command("--claim")
        self.assertEqual((code, list(printed)), (3, ["why"]))
        self.assertIn("Claimed-Run", printed["why"])
        self.assertEqual(self.shell.changes(), [])

    def test_a_run_that_claimed_and_whose_agent_finished_its_turn_to_wait_is_still_at_work(self):
        # On #30 a run's agent finished its turn to wait for the owner, and the next check took #30 up again (#95).
        self.answers["git worktree list --porcelain"] = worktree("/work/site", "main")
        (self.common / pickup.RUNS).write_text("/work/Claimed-Run\n", encoding="utf-8")
        self.answers["orca worktree ps --json"] = orca("/work/Claimed-Run", "done")
        code, printed = self.run_command("--claim")
        self.assertEqual((code, list(printed)), (3, ["why"]))
        self.assertIn("Claimed-Run", printed["why"])
        self.assertEqual((self.common / pickup.RUNS).read_text(encoding="utf-8"), "/work/Claimed-Run\n")

    def test_a_run_whose_workspace_holds_no_agent_holds_nothing_up_and_is_forgotten(self):
        self.answers["git worktree list --porcelain"] = worktree("/work/site", "main")
        (self.common / pickup.RUNS).write_text("/work/Claimed-Run\n", encoding="utf-8")
        self.answers["orca worktree ps --json"] = orca("/work/Claimed-Run")
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"]), (0, 27))
        self.assertEqual((self.common / pickup.RUNS).read_text(encoding="utf-8"), "")

    def test_the_run_that_asks_is_not_forgotten_while_it_is_at_work(self):
        # The agent that asks holds nothing up, since it is the one asking. Its checkout stays written down
        # all the same, or the next check of the schedule would no longer find the run.
        self.answers["git worktree list --porcelain"] = worktree("/work/site", "main")
        (self.common / pickup.RUNS).write_text("/work/Claimed-Run\n", encoding="utf-8")
        self.answers["orca worktree ps --json"] = orca("/work/Claimed-Run", "working", session="this-one")
        os.environ["ORCA_AGENT_SESSION_ID"] = "this-one"
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"]), (0, 27))
        self.assertEqual((self.common / pickup.RUNS).read_text(encoding="utf-8"), "/work/Claimed-Run\n")

    def test_claiming_writes_down_the_checkout_the_run_works_in_and_writes_it_once(self):
        self.answers["git worktree list --porcelain"] = worktree("/work/site", "main")
        # The run claims again from its own checkout, where it is the agent that asks.
        os.environ["ORCA_AGENT_SESSION_ID"] = "session-1"
        for _ in range(2):
            code, _ = self.run_command("--claim")
            self.assertEqual(code, 0)
            self.answers["orca worktree ps --json"] = orca(str(shell.ROOT), "done")
        written = (self.common / pickup.RUNS).read_text(encoding="utf-8").splitlines()
        self.assertEqual(written, [str(shell.ROOT)])

    def test_without_claim_no_checkout_is_written_down(self):
        self.answers["git worktree list --porcelain"] = worktree("/work/site", "main")
        self.run_command()
        self.assertFalse((self.common / pickup.RUNS).exists())

    def test_orca_is_not_asked_when_no_worktree_is_on_a_features_branch(self):
        self.answers["git worktree list --porcelain"] = worktree("/work/site", "main")
        code, _ = self.run_command()
        self.assertEqual(code, 0)
        self.assertEqual([line for line in self.shell.ran if line.startswith("orca ")], [])


class IsSomethingInFlight(PickupTest):
    def setUp(self):
        super().setUp()
        self.label(28, "site-idea", "approved", "in-progress")
        self.answers[COMMENTS % 28] = [said("Site workflow: picked up\n\nBranch: agent/28-latest-jump")]
        self.answers["git worktree list --porcelain"] = "\n".join(
            [worktree("/work/site", "main"), worktree("/work/Site-Feature", "agent/28-latest-jump")]
        )

    def test_an_issue_in_progress_whose_agent_is_at_work_ends_the_run_with_3(self):
        self.answers["orca worktree ps --json"] = orca("/work/Site-Feature", "done", "working")
        code, printed = self.run_command("--claim")
        self.assertEqual(code, 3)
        self.assertEqual(list(printed), ["why"])
        self.assertIn("agent/28-latest-jump", printed["why"])
        self.assertEqual(self.shell.changes(), [])

    def test_an_issue_in_progress_whose_agent_has_finished_is_taken_up_again(self):
        self.answers["orca worktree ps --json"] = orca("/work/Site-Feature", "done")
        code, printed = self.run_command()
        self.assertEqual(code, 0)
        self.assertEqual((printed["issue"], printed["take_up"]), (28, "resume"))

    def test_a_feature_that_is_live_is_taken_up_again_though_the_site_is_not_healthy(self):
        # The fault may be the feature's own, and the run that would mend it or put the site back is this one.
        self.answers["orca worktree ps --json"] = orca("/work/Site-Feature", "done")
        self.answers[EVALS] = [run(61, conclusion="failure", made="23:32:26", done="23:34:58")]
        self.answers["gh pr list"] = [pull(41, "agent/28-latest-jump", "MERGED")]
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 28, "resume"))

    def test_an_issue_in_progress_that_is_not_live_waits_while_the_site_is_not_healthy(self):
        self.answers["orca worktree ps --json"] = orca("/work/Site-Feature", "done")
        self.answers[EVALS] = [run(61, conclusion="failure", made="23:32:26", done="23:34:58")]
        for pulls in ([], [pull(41, "agent/28-latest-jump")]):
            with self.subTest(pulls=len(pulls)):
                self.answers["gh pr list"] = pulls
                code, printed = self.run_command()
                self.assertEqual((code, list(printed)), (4, ["why"]))

    def test_a_feature_whose_merges_were_reverted_is_not_live_and_waits_while_the_site_is_not_healthy(self):
        self.answers["orca worktree ps --json"] = orca("/work/Site-Feature", "done")
        self.answers[EVALS] = [run(61, conclusion="failure", made="23:32:26", done="23:34:58")]
        self.answers["gh pr list"] = [
            merged(41, "agent/28-latest-jump", "20:00:00"),
            merged(42, "agent/28-revert", "21:00:00"),
        ]
        code, _ = self.run_command()
        self.assertEqual(code, 4)

    def test_an_issue_in_progress_with_no_worktree_on_its_branch_is_taken_up_again(self):
        self.answers["git worktree list --porcelain"] = worktree("/work/site", "main")
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 28, "resume"))

    def test_an_agent_at_work_in_another_worktree_does_not_hold_the_issue(self):
        self.answers["orca worktree ps --json"] = orca("/work/site", "working")
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 28, "resume"))

    def test_the_agent_that_runs_the_command_is_not_counted_as_at_work_on_the_issue(self):
        self.answers["orca worktree ps --json"] = orca("/work/Site-Feature", "working", session="this-one")
        os.environ["ORCA_AGENT_SESSION_ID"] = "this-one"
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 28, "resume"))

    def test_an_issue_taken_up_again_keeps_the_branch_its_picked_up_comment_names(self):
        self.answers["orca worktree ps --json"] = orca("/work/Site-Feature", "done")
        _, printed = self.run_command()
        self.assertEqual(printed["branch"], "agent/28-latest-jump")

    def test_claiming_an_issue_that_is_in_progress_already_adds_no_label_and_posts_picked_up(self):
        self.answers["orca worktree ps --json"] = orca("/work/Site-Feature", "done")
        self.run_command("--claim")
        self.assertEqual(
            self.shell.changes(),
            [
                "gh issue edit 28 --add-assignee the-owner",
                STATUS % (28, "In progress"),
                "gh issue comment 28 --body-file -",
            ],
        )

    def test_a_partner_in_progress_is_never_taken_up_as_a_run_of_its_own(self):
        # #27 joined #28's group, so both are in progress, and the partner has the lower number. Taken up alone, it
        # would be worked a second time, apart from the branch that holds its work.
        self.label(27, "site-idea", "approved", "in-progress")
        self.answers[COMMENTS % 27] = [said("Site workflow: joined\n\nLead: #28")]
        self.answers["orca worktree ps --json"] = orca("/work/Site-Feature", "done")
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 28, "resume"))


class HasAStoppedIssueBeenAnswered(PickupTest):
    STOPPED = [
        said("Site workflow: picked up\n\nBranch: agent/29-baseline-chart", number=1),
        said("Site workflow: plan\n\n## Verdict\n\nstop: its criteria can be read two ways", number=2),
        said("Site workflow: stopped\n\nStage: shape\n\nWhich of the two did you mean?", number=3),
        said("The first. Allowed: sitebuild/static/site.css", number=4),
    ]
    WAITING = [
        said("Site workflow: picked up\n\nBranch: agent/30-links-that-leave", number=1),
        said("Site workflow: waiting on data\n\nWaiting on RisingRepos#215.\nField: homepage\n\nWhy.", number=2),
    ]

    def wait_for_data(self, schema: dict, *boards: dict) -> None:
        """Make #30 wait for the field `homepage`, with this daily schema and these board days on main, the
        newest of them first."""
        self.label(30, "site-idea", "approved", "blocked-on-data")
        self.answers[COMMENTS % 30] = self.WAITING
        self.answers[SCHEMA] = schema
        days = [f"2026-11-{22 - back}" for back in range(len(boards))]
        self.answers[INDEX] = {"schema_version": 1, "board_days": [{"board_day": day, "row_count": 1} for day in days]}
        for day, board in zip(days, boards, strict=True):
            self.answers[BOARD % day] = board

    def test_a_stopped_issue_whose_needs_owner_the_owner_removed_is_taken_up_as_answered(self):
        self.answers[COMMENTS % 29] = self.STOPPED
        code, printed = self.run_command()
        self.assertEqual(code, 0)
        self.assertEqual((printed["issue"], printed["take_up"]), (29, "answered"))
        self.assertEqual(printed["branch"], "agent/29-baseline-chart")

    def test_a_stopped_issue_that_still_carries_needs_owner_is_left_and_the_next_idea_is_taken(self):
        self.answers[COMMENTS % 29] = self.STOPPED
        self.label(29, "site-idea", "approved", "needs-owner")
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 27, "new"))

    def test_an_issue_whose_newest_comment_of_the_workflows_is_not_stopped_is_not_answered(self):
        self.answers[COMMENTS % 29] = [*self.STOPPED, said("Site workflow: picked up\n\nBranch: x", number=5)]
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 27, "new"))

    def test_a_partner_stopped_with_its_lead_is_not_answered_on_its_own(self):
        # The owner answers on the lead, and the partner goes on with it.
        self.answers[COMMENTS % 27] = [
            said("Site workflow: joined\n\nLead: #29", number=1),
            said("Site workflow: stopped\n\nLead: #29\nStage: check\n\nThe question is on #29.", number=2),
        ]
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 28, "new"))

    def test_a_stop_whose_own_words_hold_a_line_that_begins_lead_is_still_answered(self):
        # Only the line the scripts write right after the first names a lead. The stop's text is the agent's, and a
        # lead mistaken for a partner would never be taken up again.
        stop = said("Site workflow: stopped\n\nStage: shape\n\nLead: #12 asked the same, and was closed.", number=3)
        self.answers[COMMENTS % 29] = [*self.STOPPED[:2], stop]
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 29, "answered"))

    def test_a_grade_after_the_stop_does_not_hide_the_answer(self):
        self.answers[COMMENTS % 29] = [*self.STOPPED, said("Site workflow: graded\n\nComplexity: Low", number=5)]
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 29, "answered"))

    def test_taking_an_answered_lead_up_takes_back_the_partners_stopped_with_it(self):
        # The sort comes after the pick up and before the plan.
        sort = said("Site workflow: sorted\n\nWith: #30", number=5)
        self.answers[COMMENTS % 29] = [self.STOPPED[0], sort, *self.STOPPED[1:]]
        self.answers[COMMENTS % 30] = [
            said("Site workflow: joined\n\nLead: #29", number=1),
            said("Site workflow: stopped\n\nLead: #29\nStage: shape\n\nThe question is on #29.", number=2),
        ]
        self.label(30, "site-idea", "approved", "needs-owner")
        code, printed = self.run_command("--claim")
        self.assertEqual((code, printed["issue"]), (0, 29))
        self.assertEqual(
            self.shell.changes()[-3:],
            [
                "gh issue edit 30 --remove-label needs-owner --add-label in-progress --add-assignee the-owner",
                STATUS % (30, "In progress"),
                "gh issue comment 30 --body-file -",
            ],
        )
        joined = self.shell.stdin["gh issue comment 30 --body-file -"]
        self.assertTrue(joined.startswith("Site workflow: joined\n\nLead: #29"), joined)

    def test_a_stopped_comment_that_a_stranger_wrote_stops_nothing(self):
        self.only(29)
        self.answers[COMMENTS % 29] = [said("Site workflow: stopped\n\nNot the workflow's.", by="a-stranger")]
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 29, "new"))

    def test_an_answered_issue_whose_approval_was_withdrawn_is_left(self):
        self.only(29)
        self.answers[COMMENTS % 29] = self.STOPPED
        self.label(29, "site-idea")
        code, printed = self.run_command()
        self.assertEqual(code, 3)
        self.assertEqual(list(printed), ["why"])

    def test_a_blocked_issue_whose_field_is_in_the_schema_and_the_newest_board_day_is_taken_up(self):
        row = {"properties": {"full_name": {"type": "string"}, "homepage": {"type": "string"}}}
        self.wait_for_data(
            {"properties": {"rows": {"items": row}}}, {"board_day": "2026-11-22", "rows": [{"homepage": None}]}
        )
        code, printed = self.run_command()
        self.assertEqual(code, 0)
        self.assertEqual((printed["issue"], printed["take_up"]), (30, "data arrived"))
        self.assertIn("homepage", printed["why"])

    def test_a_blocked_issue_whose_field_the_schema_has_and_the_newest_board_day_has_not_is_left(self):
        self.wait_for_data(
            {"properties": {"homepage": {"type": "string"}}},
            {"board_day": "2026-11-22", "rows": [{"full_name": "a/b"}]},
        )
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 27, "new"))

    def test_a_blocked_issue_whose_field_only_an_older_board_day_has_is_left(self):
        self.wait_for_data(
            {"properties": {"homepage": {"type": "string"}}},
            {"board_day": "2026-11-22", "rows": []},
            {"board_day": "2026-11-21", "homepage": "x"},
        )
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 27, "new"))

    def test_a_blocked_issue_whose_field_the_schema_has_not_is_left(self):
        self.wait_for_data({"properties": {"full_name": {}}}, {"board_day": "2026-11-22", "homepage": "x"})
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 27, "new"))

    def test_the_data_is_read_as_main_holds_it_on_origin_after_a_fetch(self):
        self.wait_for_data({"properties": {"homepage": {}}}, {"board_day": "2026-11-22", "homepage": "x"})
        self.run_command()
        reads = [line for line in self.shell.ran if line.startswith(("git fetch", "git show"))]
        self.assertEqual(reads, ["git fetch origin main", SCHEMA, INDEX, BOARD % "2026-11-22"])

    def test_claim_clears_blocked_on_data_where_the_field_arrived_and_adds_in_progress(self):
        self.wait_for_data({"properties": {"homepage": {}}}, {"board_day": "2026-11-22", "homepage": "x"})
        self.run_command("--claim")
        self.assertEqual(
            self.shell.changes(),
            [
                "gh issue edit 30 --add-label in-progress --remove-label blocked-on-data --add-assignee the-owner",
                STATUS % (30, "In progress"),
                "gh issue comment 30 --body-file -",
            ],
        )


class TheNextNewIdea(PickupTest):
    def test_the_idea_that_was_approved_earliest_goes_first(self):
        self.answers[TIMELINE % 27][1] = labelled("approved", "2026-11-23T09:00:00Z")
        self.answers[TIMELINE % 29][1] = labelled("approved", "2026-11-22T08:00:00Z")
        code, printed = self.run_command()
        self.assertEqual((code, printed["issue"], printed["take_up"]), (0, 29, "new"))

    def test_an_approval_counts_from_when_the_label_was_last_put_on(self):
        self.answers[TIMELINE % 27] = [
            labelled("site-idea", "2026-11-22T16:59:27Z"),
            labelled("approved", "2026-11-20T00:00:00Z"),
            {
                "event": "unlabeled",
                "actor": {"login": OWNER},
                "created_at": "2026-11-21T00:00:00Z",
                "label": {"name": "approved"},
            },
            labelled("approved", "2026-11-23T09:00:00Z"),
        ]
        _, printed = self.run_command()
        self.assertEqual(printed["issue"], 28)

    def test_an_idea_the_owner_did_not_approve_is_never_picked_up(self):
        self.only(27)
        self.answers[TIMELINE % 27][1] = labelled("approved", "2026-11-22T17:00:27Z", by="a-stranger")
        code, printed = self.run_command("--claim")
        self.assertEqual(code, 3)
        self.assertEqual(list(printed), ["why"])
        self.assertEqual(self.shell.changes(), [])

    def test_an_idea_whose_site_idea_label_another_account_put_on_is_never_picked_up(self):
        self.only(27)
        self.answers[TIMELINE % 27][0] = labelled("site-idea", "2026-11-22T16:59:27Z", by="a-stranger")
        self.assertEqual(self.run_command()[0], 3)

    def test_an_idea_another_account_wrote_is_never_picked_up(self):
        self.answers["gh issue list"] = [idea(27, "Add my repository to the board", by="a-stranger")]
        self.assertEqual(self.run_command()[0], 3)

    def test_an_idea_that_is_not_labelled_approved_is_never_picked_up(self):
        self.only(27)
        self.label(27, "site-idea")
        self.assertEqual(self.run_command()[0], 3)

    def test_an_approved_issue_that_is_not_a_site_idea_is_never_picked_up(self):
        self.only(27)
        self.label(27, "approved")
        self.assertEqual(self.run_command()[0], 3)

    def test_an_idea_that_carries_a_label_of_the_workflows_is_not_new(self):
        for mark in ("needs-owner", "blocked-on-data"):
            with self.subTest(label=mark):
                self.label(27, "site-idea", "approved", mark)
                self.answers[COMMENTS % 27] = []
                _, printed = self.run_command()
                self.assertEqual(printed["issue"], 28)

    def test_an_idea_that_has_a_comment_of_the_workflows_is_not_new(self):
        self.answers[COMMENTS % 27] = [said("Site workflow: plan\n\n## Verdict\n\ngo")]
        _, printed = self.run_command()
        self.assertEqual(printed["issue"], 28)

    def test_an_idea_the_owner_commented_on_is_still_new(self):
        self.answers[COMMENTS % 27] = [said("Keep the first column fixed.")]
        _, printed = self.run_command()
        self.assertEqual((printed["issue"], printed["take_up"]), (27, "new"))

    def test_an_idea_whose_only_comment_of_the_workflows_is_a_grade_is_still_new(self):
        # Each run grades the ideas that wait, and a grade is no work begun on one (25 November 2026).
        self.answers[COMMENTS % 27] = [said("Site workflow: graded\n\nComplexity: Low\nEffort: Low")]
        _, printed = self.run_command()
        self.assertEqual((printed["issue"], printed["take_up"]), (27, "new"))

    def test_an_idea_with_a_runs_note_on_it_is_still_new(self):
        # A run's look back adds a finding close to an idea to that idea, as a note (25 November 2026). It is what a
        # run found, and no work begun on the idea.
        self.answers[COMMENTS % 27] = [said("Site workflow: note\n\nFrom the run on #26.\n\nThe hint names a rule.")]
        _, printed = self.run_command()
        self.assertEqual((printed["issue"], printed["take_up"]), (27, "new"))

    def test_an_idea_sent_back_from_a_group_is_new_again(self):
        self.answers[COMMENTS % 27] = [
            said("Site workflow: joined\n\nLead: #26", number=1),
            said("Site workflow: released\n\nLead: #26\n\nIt changes another part of the page.", number=2),
        ]
        _, printed = self.run_command()
        self.assertEqual((printed["issue"], printed["take_up"]), (27, "new"))

    def test_an_idea_that_joined_a_group_is_not_new(self):
        # Its work is on its lead's branch. Taken as new, it would be worked a second time on a branch of its own.
        self.answers[COMMENTS % 27] = [said("Site workflow: joined\n\nLead: #26")]
        _, printed = self.run_command()
        self.assertEqual(printed["issue"], 28)

    def test_an_idea_that_has_a_branch_on_origin_is_not_new(self):
        self.answers["git ls-remote --heads origin agent/*"] = f"{HEAD}\trefs/heads/agent/27-stop-clipping"
        _, printed = self.run_command()
        self.assertEqual(printed["issue"], 28)

    def test_another_issues_branch_whose_number_begins_the_same_does_not_count(self):
        self.answers["git ls-remote --heads origin agent/*"] = f"{HEAD}\trefs/heads/agent/270-something-else"
        _, printed = self.run_command()
        self.assertEqual(printed["issue"], 27)

    def test_an_idea_that_has_a_pull_request_is_not_new(self):
        for state in ("OPEN", "CLOSED", "MERGED"):
            with self.subTest(state=state):
                self.answers["gh pr list"] = [pull(40, "agent/27-stop-clipping", state)]
                _, printed = self.run_command()
                self.assertEqual(printed["issue"], 28)

    def test_a_pull_request_older_than_the_idea_does_not_keep_it_from_being_picked_up(self):
        self.answers["gh pr list"] = [pull(1, "agent/27-preview-site", "MERGED"), pull(2, "agent/27-revert", "MERGED")]
        _, printed = self.run_command()
        self.assertEqual((printed["issue"], printed["take_up"]), (27, "new"))
        self.assertIsNone(printed["facts"]["pull_request"])

    def test_a_pull_request_from_a_fork_does_not_keep_an_idea_from_being_picked_up(self):
        self.answers["gh pr list"] = [pull(40, "agent/27-from-a-fork", fork=True)]
        _, printed = self.run_command()
        self.assertEqual(printed["issue"], 27)

    def test_an_issues_comments_are_read_once_however_many_steps_ask_for_them(self):
        self.run_command()
        for number in (27, 28, 29, 30):
            asked = [line for line in self.shell.ran if line.startswith(COMMENTS % number)]
            self.assertEqual(len(asked), 1, asked)

    def test_with_nothing_to_work_on_it_exits_3_and_the_json_holds_why_alone(self):
        self.answers["gh issue list"] = []
        code, printed = self.run_command("--claim")
        self.assertEqual(code, 3)
        self.assertEqual(list(printed), ["why"])
        self.assertEqual(self.shell.changes(), [])


class Queue(PickupTest):
    """`queue` lists the ideas a run could take as new, with their grades, for the sort's agent to grade those
    that have none and to choose the lead's partners from (25 November 2026)."""

    GRADE = "Site workflow: graded\n\nComplexity: 5\nEffort: 2\nArea: the date bar\nCode: filters.js jump()\n\nWhy."

    def run_queue(self, *arguments: str) -> tuple[int, dict]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = pickup.main("queue", list(arguments))
        return code, json.loads(printed.getvalue())

    def test_the_queue_lists_the_waiting_ideas_oldest_approval_first_with_their_grades(self):
        self.answers[COMMENTS % 28] = [said(self.GRADE)]
        code, printed = self.run_queue()
        self.assertEqual(code, 0)
        self.assertEqual([one["number"] for one in printed["waiting"]], [27, 28, 29, 30])
        self.assertEqual(
            printed["waiting"][1]["grade"],
            {"complexity": 5, "effort": 2, "area": "the date bar", "code": "filters.js jump()"},
        )
        self.assertIsNone(printed["waiting"][0]["grade"])
        self.assertIsNone(printed["lead"])

    def test_a_grade_that_is_not_in_points_counts_as_none_so_the_idea_is_graded_again(self):
        # Grades moved from Low, Medium, and High to Fibonacci points on 25 November 2026. An idea graded the old
        # way, or with a number that is no point, has nothing the sort's cap can add up, so it is graded again.
        for given in ("Medium", "4"):
            with self.subTest(given=given):
                self.answers[COMMENTS % 28] = [said(self.GRADE.replace("Complexity: 5", f"Complexity: {given}"))]
                _, printed = self.run_queue()
                self.assertIsNone(printed["waiting"][1]["grade"])

    def test_the_queue_gives_the_lead_apart_from_the_ideas_that_wait(self):
        self.label(27, "site-idea", "approved", "in-progress")
        _, printed = self.run_queue("--lead", "27")
        self.assertEqual(printed["lead"]["number"], 27)
        self.assertEqual([one["number"] for one in printed["waiting"]], [28, 29, 30])

    def test_the_queue_changes_nothing_on_github(self):
        self.run_queue("--lead", "27")
        self.assertEqual(self.shell.changes(), [])


class WhatItPrints(PickupTest):
    def test_the_json_names_the_issue_its_title_its_branch_how_it_is_taken_up_and_why(self):
        code, printed = self.run_command()
        self.assertEqual(code, 0)
        self.assertEqual(list(printed), ["issue", "title", "branch", "take_up", "why", "facts"])
        self.assertEqual(printed["issue"], 27)
        self.assertEqual(printed["title"], "Stop clipping the board-history table mid-word on phones")
        self.assertEqual(printed["take_up"], "new")
        self.assertTrue(printed["why"])

    def test_a_new_ideas_branch_is_agent_its_number_and_a_short_slug_of_its_title(self):
        _, printed = self.run_command()
        self.assertEqual(printed["branch"], "agent/27-stop-clipping-the-board-history")

    def test_an_idea_titled_revert_is_not_given_the_branch_that_reverts_a_feature(self):
        for title in ("Revert", "Revert!", "  revert  "):
            with self.subTest(title=title):
                self.answers["gh issue list"] = [idea(27, title)]
                _, printed = self.run_command()
                self.assertNotEqual(printed["branch"], "agent/27-revert")
                on_it = [pull(40, printed["branch"])]
                self.assertEqual(issue.feature(on_it, 27), on_it)
                self.assertEqual(issue.revert(on_it, 27), [])

    def test_an_idea_whose_title_only_begins_with_revert_keeps_the_slug_of_its_title(self):
        self.answers["gh issue list"] = [idea(27, "Revert the sort to stars")]
        _, printed = self.run_command()
        self.assertEqual(printed["branch"], "agent/27-revert-the-sort-to-stars")

    def test_the_facts_of_a_new_idea_are_its_labels_and_nothing_done_yet(self):
        _, printed = self.run_command()
        self.assertEqual(
            printed["facts"],
            {
                "labels": ["site-idea", "approved"],
                "plan": {"exists": False, "verdict": None},
                "pull_request": None,
                "review": None,
                "merged": False,
                "standing": 0,
                "reverted": False,
                "partners": [],
            },
        )

    def test_the_facts_name_the_partners_of_the_group(self):
        self.label(28, "site-idea", "approved", "in-progress")
        self.label(27, "site-idea", "approved", "in-progress")
        self.answers[COMMENTS % 28] = [
            said("Site workflow: picked up\n\nBranch: agent/28-latest-jump", number=1),
            said("Site workflow: sorted\n\nWith: #27", number=2),
        ]
        self.answers[COMMENTS % 27] = [said("Site workflow: joined\n\nLead: #28")]
        _, printed = self.run_command()
        self.assertEqual((printed["issue"], printed["facts"]["partners"]), (28, [27]))

    def test_the_facts_of_an_issue_taken_up_again_show_how_far_it_came(self):
        self.only(29)
        self.label(29, "site-idea", "approved", "in-progress")
        self.answers[COMMENTS % 29] = [
            said("Site workflow: picked up\n\nBranch: agent/29-baseline-chart", number=1),
            said("Site workflow: plan\n\n## What changes\n\nThe chart.\n\n## Verdict\n\ngo\n\n## Criteria", number=2),
            said("Site workflow: review\n\nVerdict: changes needed\nCommit: " + "1" * 40, number=3),
            said("Site workflow: review\n\nVerdict: pass\nCommit: " + "2" * 40, number=4),
            said("Site workflow: review\n\nVerdict: fail\nCommit: " + "3" * 40, by="a-stranger", number=5),
        ]
        self.answers["gh pr list"] = [pull(41, "agent/29-baseline-chart", "MERGED"), pull(42, "agent/29-revert")]
        _, printed = self.run_command()
        self.assertEqual(
            printed["facts"],
            {
                "labels": ["site-idea", "approved", "in-progress"],
                "plan": {"exists": True, "verdict": "go"},
                "pull_request": {"number": 41, "state": "MERGED"},
                "review": {"verdict": "pass", "commit": "2" * 40},
                "merged": True,
                "standing": 1,
                "reverted": False,
                "partners": [],
            },
        )

    def test_the_facts_tell_a_feature_from_a_feature_with_its_mend_and_from_one_that_was_reverted(self):
        # A run that takes an issue up again reads these to know whether a mend was tried, and whether the site
        # was put back, which the newest pull request alone does not say.
        self.only(29)
        self.label(29, "site-idea", "approved", "in-progress")
        self.answers[COMMENTS % 29] = [said("Site workflow: picked up\n\nBranch: agent/29-baseline-chart")]
        feature, mend = (
            merged(41, "agent/29-baseline-chart", "20:00:00"),
            merged(43, "agent/29-baseline-chart", "21:00:00"),
        )
        cases = {
            "the mend's pull request is open": ([feature, pull(43, "agent/29-baseline-chart")], (False, 1, False)),
            "the mend merged": ([feature, mend], (True, 2, False)),
            "both were reverted": ([feature, mend, merged(44, "agent/29-revert", "22:00:00")], (True, 0, True)),
            "landed again after a revert": (
                [feature, merged(42, "agent/29-revert", "20:30:00"), mend],
                (True, 1, False),
            ),
        }
        for case, (pulls, expected) in cases.items():
            with self.subTest(case):
                self.answers["gh pr list"] = pulls
                facts = self.run_command()[1]["facts"]
                self.assertEqual((facts["merged"], facts["standing"], facts["reverted"]), expected)


class Claim(PickupTest):
    def test_without_claim_nothing_on_github_changes(self):
        code, _ = self.run_command()
        self.assertEqual(code, 0)
        self.assertEqual(self.shell.changes(), [])

    def test_claim_adds_in_progress_assigns_the_owner_sets_in_progress_and_posts_picked_up_with_the_branch(self):
        # The owner's list of assigned issues, and GitHub's Active tab, are how the owner sees what a run is at
        # work on. Assigning moves an issue from Backlog to Todo by itself, so the status is set after the owner.
        code, printed = self.run_command("--claim")
        self.assertEqual(code, 0)
        self.assertEqual(
            self.shell.changes(),
            [
                "gh issue edit 27 --add-label in-progress --add-assignee the-owner",
                STATUS % (27, "In progress"),
                "gh issue comment 27 --body-file -",
            ],
        )
        body = self.shell.stdin["gh issue comment 27 --body-file -"]
        self.assertTrue(body.startswith("Site workflow: picked up\n\n"), body)
        self.assertIn(f"Branch: {printed['branch']}", body.splitlines())

    def test_a_status_github_refuses_leaves_the_json_whole_and_the_claim_made(self):
        self.answers[STATUS % (27, "In progress")] = shell.Failed("gh api: exit 1\nHTTP 422: no statuses here")
        printed, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(errors):
            code = pickup.main("pickup", ["--claim"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(printed.getvalue())["issue"], 27)
        self.assertIn("In progress", errors.getvalue())
        self.assertIn("gh issue comment 27 --body-file -", self.shell.ran)

    def test_a_command_that_github_refuses_exits_1_and_prints_no_issue(self):
        self.answers["gh issue list"] = shell.Failed("gh issue list: exit 1\nHTTP 401")
        printed, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(errors):
            code = pickup.main("pickup", [])
        self.assertEqual(code, 1)
        self.assertEqual(printed.getvalue(), "")
        self.assertIn("HTTP 401", errors.getvalue())

    def test_write_runs_replaces_atomically_and_runs_lock_cleans_up(self):
        runs = Path(self.enterContext(tempfile.TemporaryDirectory())) / "sitework-runs"
        with pickup._runs_lock(runs):
            self.assertTrue(runs.with_name("sitework-runs.lock").is_file())
            pickup._write_runs(runs, ["/work/one", "/work/two"])
        self.assertFalse(runs.with_name("sitework-runs.lock").exists())
        self.assertEqual(runs.read_text(encoding="utf-8").splitlines(), ["/work/one", "/work/two"])


if __name__ == "__main__":
    unittest.main()
