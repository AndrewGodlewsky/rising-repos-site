"""`confirm` sees that a merged feature was uploaded, passes the owner's tests on the live site, and passed the
site eval that followed its deploy.

No test reaches GitHub, waits, or opens the site. `sitework.shell.run` is replaced by a stand-in that answers
each command from what the test gives it, in the shapes `gh` answers in, and keeps each command it was given.
The sleep between two looks is replaced by one that only counts.
"""

import contextlib
import io
import json
import os
import sys
import unittest
from unittest import mock

from evals.site.measure import DEPLOYED_SITE
from sitework import confirm, shell

MERGE = "a" * 40
NEWER = "b" * 40
NEWEST = "d" * 40
NOTES = "9" * 40
REVERT = "e" * 40
DEPLOYS = "gh run list --workflow Build and deploy --branch main --event push"
EVALS = "gh run list --workflow Site eval --event workflow_run"
OWNERS_TESTS = f"{sys.executable} -m unittest discover -s owner_tests -t ."
FETCH = "git fetch --quiet origin main"
DEPLOYING = "git log --first-parent -1 --format=%H origin/main -- . :(exclude)docs/workflow-notes"
"""The line that asks git for the newest commit on main that changes more than the notes."""


class InTurn:
    """Answers given one at each asking, and the last of them from then on."""

    def __init__(self, *answers):
        self.answers = list(answers)

    def next(self):
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]


class Shell:
    """Stands in for `sitework.shell.run`. A command is answered by the answer whose words it begins with, the
    longest of them when several do, and a command with no answer fails the test. An answer that is not text is
    given as the JSON `gh` would print, and one that is an error is raised."""

    def __init__(self, answers: dict):
        self.answers = answers
        self.ran = []
        self.env = {}

    def __call__(self, *command, cwd=None, check=True, stdin=None, env=None):
        line = " ".join(command)
        self.ran.append(line)
        self.env[line] = env
        starts = [start for start in self.answers if line.startswith(start)]
        if not starts:
            raise AssertionError(f"the test gave no answer for: {line}")
        answer = self.answers[max(starts, key=len)]
        if isinstance(answer, InTurn):
            answer = answer.next()
        if isinstance(answer, Exception):
            raise answer
        return answer if isinstance(answer, str) else json.dumps(answer)

    def count(self, start: str) -> int:
        return len([line for line in self.ran if line.startswith(start)])


def run(number: int, commit: str = MERGE, conclusion: str = "success", made: str = "12:00:00", done: str = "12:02:00"):
    """A run of a workflow, as `gh run list` gives one. One with no conclusion is still running."""
    return {
        "conclusion": conclusion,
        "createdAt": f"2026-11-22T{made}Z",
        "databaseId": number,
        "headSha": commit,
        "status": "completed" if conclusion else "in_progress",
        "updatedAt": f"2026-11-22T{done}Z",
        "url": f"https://github.com/the-owner/the-site/actions/runs/{number}",
    }


def pull(number: int, branch: str, merge: str, merged: str) -> dict:
    """A pull request that merged, as `gh pr list` gives one."""
    return {
        "number": number,
        "state": "MERGED",
        "headRefName": branch,
        "headRefOid": f"{number:040x}",
        "isCrossRepository": False,
        "mergeCommit": {"oid": merge},
        "mergedAt": f"2026-11-22T{merged}Z",
    }


def jobs(upload: str | None) -> dict:
    """A deploy run's jobs, as `gh run view` gives them. With no `upload`, the deploy job ran no step."""
    steps = [
        {"conclusion": "success", "name": "Upload only the newest push", "number": 4, "status": "completed"},
        {"conclusion": upload, "name": "Upload to Cloudflare Pages", "number": 5, "status": "completed"},
    ]
    build = [{"conclusion": "success", "name": "Build the pages", "number": 6, "status": "completed"}]
    return {
        "jobs": [
            {"conclusion": "success", "name": "build", "status": "completed", "steps": build},
            {"conclusion": "success", "name": "deploy", "status": "completed", "steps": steps if upload else []},
        ]
    }


class ConfirmTest(unittest.TestCase):
    """A test with the stand-in in place, and issue #27 merged, uploaded, and measured, so that each test changes
    the one answer it is about."""

    def setUp(self):
        self.answers = {
            "gh pr list --state merged": [pull(40, "agent/27-stop-clipping", MERGE, "11:59:58")],
            f"{DEPLOYS} --commit {MERGE}": [run(500)],
            "gh run view 500": jobs("success"),
            f"{EVALS} --commit {MERGE}": [run(600, made="12:02:03", done="12:04:30")],
            OWNERS_TESTS: "",
        }
        self.shell = Shell(self.answers)
        self.enterContext(mock.patch.object(shell, "run", self.shell))
        self.slept = []
        self.enterContext(mock.patch.object(confirm, "sleep", self.slept.append))
        self.enterContext(mock.patch.dict(os.environ))
        os.environ.pop("SITE", None)

    def run_command(self, *arguments: str) -> tuple[int, dict | None, str]:
        """Run `confirm`, and give its exit code, the JSON object it printed last, and its progress."""
        printed, progress = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(progress):
            code = confirm.main("confirm", list(arguments))
        text = printed.getvalue()
        return code, json.loads(text) if text.lstrip().startswith("{") else None, text + progress.getvalue()


class TheRuns(ConfirmTest):
    def test_the_newest_deploy_is_looked_for_among_the_pushes_to_main_alone(self):
        self.answers[DEPLOYS] = [run(501)]
        self.assertEqual(confirm.deploy_run()["databaseId"], 501)
        (asked,) = self.shell.ran
        self.assertTrue(asked.startswith(f"{DEPLOYS} --limit 1 "), asked)

    def test_the_eval_that_followed_a_deploy_is_the_first_made_for_its_commit_once_the_deploy_had_finished(self):
        self.answers[f"{EVALS} --commit {MERGE}"] = [
            run(603, made="12:09:00", done="12:11:00"),
            run(602, made="12:02:03", done="12:04:30"),
            run(601, made="12:01:10", done="12:01:40"),
        ]
        self.assertEqual(confirm.eval_after(run(500))["databaseId"], 602)

    def test_no_eval_followed_a_deploy_when_each_one_for_its_commit_was_made_before_it_finished(self):
        self.answers[f"{EVALS} --commit {MERGE}"] = [run(601, made="12:01:10", done="12:01:40")]
        self.assertIsNone(confirm.eval_after(run(500)))


class Confirm(ConfirmTest):
    def test_a_feature_that_was_uploaded_passes_the_owners_tests_and_passed_the_eval_exits_0(self):
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 0)
        self.assertEqual(
            report,
            {
                "issue": 27,
                "merge": MERGE,
                "deploy": {"run": 500, "commit": MERGE, "result": "success"},
                "live": {"result": "passed", "tries": 1},
                "eval": {"run": 600, "result": "success"},
                "failed": [],
            },
        )
        self.assertEqual(self.slept, [])

    def test_it_looks_every_20_seconds_until_the_deploy_has_finished(self):
        self.answers[f"{DEPLOYS} --commit {MERGE}"] = InTurn([], [run(500, conclusion="")], [run(500)])
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 0)
        self.assertEqual(self.slept, [20, 20])
        self.assertEqual(report["deploy"]["result"], "success")

    def test_a_deploy_that_has_not_finished_after_20_minutes_fails_and_nothing_else_is_tried(self):
        self.answers[f"{DEPLOYS} --commit {MERGE}"] = [run(500, conclusion="")]
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertEqual(sum(self.slept), 20 * 60)
        self.assertEqual(set(self.slept), {20})
        self.assertEqual(report["deploy"]["result"], "not finished")
        self.assertEqual((report["live"]["result"], report["eval"]["result"]), ("not run", "not run"))
        self.assertEqual(report["failed"], ["deploy", "live", "eval"])
        self.assertEqual(self.shell.count(OWNERS_TESTS), 0)

    def test_a_deploy_that_failed_exits_1_and_the_owners_tests_are_not_run(self):
        self.answers[f"{DEPLOYS} --commit {MERGE}"] = [run(500, conclusion="failure")]
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertEqual(report["deploy"], {"run": 500, "commit": MERGE, "result": "failure"})
        self.assertIn("deploy", report["failed"])
        self.assertEqual(self.shell.count(OWNERS_TESTS), 0)

    def test_when_the_upload_was_left_to_a_newer_push_the_run_for_that_push_is_followed(self):
        self.answers["gh run view 500"] = jobs("skipped")
        self.answers[FETCH] = ""
        self.answers[DEPLOYING] = NEWER
        self.answers[f"{DEPLOYS} --commit {NEWER}"] = InTurn([run(510, NEWER, "")], [run(510, NEWER, done="12:05:00")])
        self.answers["gh run view 510"] = jobs("success")
        self.answers[f"{EVALS} --commit {NEWER}"] = [run(610, NEWER, made="12:05:02", done="12:07:30")]
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 0)
        self.assertEqual(report["merge"], MERGE)
        self.assertEqual(report["deploy"], {"run": 510, "commit": NEWER, "result": "success"})
        self.assertEqual(report["eval"], {"run": 610, "result": "success"})

    def test_when_the_head_of_main_is_a_commit_of_the_notes_the_newest_commit_that_changes_more_is_followed(self):
        # The head of main is asked of nothing, so a commit of the notes there, which has no run, is never the
        # one followed. The two answers for it are what a script that followed the head would be given.
        self.answers["gh run view 500"] = jobs("skipped")
        self.answers["git ls-remote origin refs/heads/main"] = f"{NOTES}\trefs/heads/main"
        self.answers[f"{DEPLOYS} --commit {NOTES}"] = []
        self.answers[FETCH] = ""
        self.answers[DEPLOYING] = NEWER
        self.answers[f"{DEPLOYS} --commit {NEWER}"] = [run(510, NEWER, done="12:05:00")]
        self.answers["gh run view 510"] = jobs("success")
        self.answers[f"{EVALS} --commit {NEWER}"] = [run(610, NEWER, made="12:05:02", done="12:07:30")]
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 0)
        self.assertEqual(report["deploy"], {"run": 510, "commit": NEWER, "result": "success"})
        self.assertEqual(self.slept, [])
        self.assertEqual([line for line in self.shell.ran if line.startswith("git")], [FETCH, DEPLOYING])

    def test_a_run_that_left_its_upload_to_a_push_of_the_notes_alone_fails_the_deploy_and_waits_for_no_run(self):
        # A script that followed the head of main would wait 20 minutes here, for a run that is never made.
        self.answers["gh run view 500"] = jobs("skipped")
        self.answers["git ls-remote origin refs/heads/main"] = f"{NOTES}\trefs/heads/main"
        self.answers[f"{DEPLOYS} --commit {NOTES}"] = []
        self.answers[FETCH] = ""
        self.answers[DEPLOYING] = MERGE
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertEqual(report["deploy"], {"run": 500, "commit": MERGE, "result": "not uploaded"})
        self.assertEqual(self.slept, [])

    def test_a_run_for_the_newest_push_whose_upload_did_not_run_fails_the_deploy(self):
        self.answers["gh run view 500"] = jobs(None)
        self.answers[FETCH] = ""
        self.answers[DEPLOYING] = MERGE
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertEqual(report["deploy"], {"run": 500, "commit": MERGE, "result": "not uploaded"})

    def test_the_owners_tests_are_run_against_the_live_address_that_the_eval_owns(self):
        self.run_command("27")
        self.assertEqual(self.shell.env[OWNERS_TESTS], {"SITE": DEPLOYED_SITE})

    def test_the_live_address_is_handed_to_the_owners_tests_alone_and_does_not_outlive_them(self):
        self.run_command("27")
        others = {line: env for line, env in self.shell.env.items() if line != OWNERS_TESTS}
        self.assertEqual(set(others.values()), {None})
        self.assertNotIn("SITE", os.environ)

    def test_owners_tests_that_fail_while_a_cache_serves_the_old_page_are_tried_again_each_minute(self):
        stale = shell.Failed("FAIL: test_the_table_wraps\nAssertionError")
        self.answers[OWNERS_TESTS] = InTurn(stale, stale, "")
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 0)
        self.assertEqual(report["live"], {"result": "passed", "tries": 3})
        self.assertEqual(self.slept, [60, 60])

    def test_owners_tests_that_still_fail_after_ten_minutes_fail_and_what_they_printed_is_shown(self):
        self.answers[OWNERS_TESTS] = shell.Failed("FAIL: test_the_table_wraps\nAssertionError")
        code, report, printed = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertEqual(self.slept, [60] * 10)
        self.assertEqual(self.shell.count(OWNERS_TESTS), 11)
        self.assertEqual(report["live"], {"result": "failed", "tries": 11})
        self.assertEqual(report["failed"], ["live"])
        self.assertIn("FAIL: test_the_table_wraps", printed)

    def test_an_eval_that_failed_exits_1_and_is_named_as_what_failed(self):
        self.answers[f"{EVALS} --commit {MERGE}"] = [run(600, conclusion="failure", made="12:02:03", done="12:04:30")]
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertEqual(report["eval"], {"run": 600, "result": "failure"})
        self.assertEqual(report["failed"], ["eval"])

    def test_it_looks_every_20_seconds_until_the_eval_has_finished(self):
        running = run(600, conclusion="", made="12:02:03", done="12:02:03")
        self.answers[f"{EVALS} --commit {MERGE}"] = InTurn([], [running], [run(600, made="12:02:03", done="12:04:30")])
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 0)
        self.assertEqual(self.slept, [20, 20])

    def test_an_eval_that_has_not_finished_after_20_minutes_fails(self):
        self.answers[f"{EVALS} --commit {MERGE}"] = [run(600, conclusion="", made="12:02:03", done="12:02:03")]
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertEqual(sum(self.slept), 20 * 60)
        self.assertEqual(report["eval"], {"run": 600, "result": "not finished"})

    def test_an_eval_that_measured_nothing_is_not_read_and_the_eval_of_the_newest_deploy_to_main_is_waited_for(self):
        for ended in ("cancelled", "skipped"):
            with self.subTest(ended=ended):
                self.slept.clear()
                self.answers[f"{EVALS} --commit {MERGE}"] = [
                    run(600, conclusion=ended, made="12:02:03", done="12:03:01")
                ]
                self.answers[DEPLOYS] = [run(510, NEWER, made="12:01:00", done="12:02:58")]
                running = run(610, NEWER, "", made="12:03:00", done="12:03:00")
                self.answers[f"{EVALS} --commit {NEWER}"] = InTurn(
                    [], [running], [run(610, NEWER, made="12:03:00", done="12:05:30")]
                )
                code, report, printed = self.run_command("27")
                self.assertEqual(code, 0)
                self.assertEqual(report["deploy"], {"run": 500, "commit": MERGE, "result": "success"})
                self.assertEqual(report["eval"], {"run": 610, "result": "success"})
                self.assertEqual(self.slept, [20, 20])
                for part in (ended, "actions/runs/600", NEWER[:7], "actions/runs/610"):
                    self.assertIn(part, printed)

    def test_the_eval_of_the_newest_deploy_that_failed_fails_and_is_the_run_that_is_named(self):
        self.answers[f"{EVALS} --commit {MERGE}"] = [run(600, conclusion="cancelled", made="12:02:03", done="12:03:01")]
        self.answers[DEPLOYS] = [run(510, NEWER, made="12:01:00", done="12:02:58")]
        self.answers[f"{EVALS} --commit {NEWER}"] = [run(610, NEWER, "failure", made="12:03:00", done="12:05:30")]
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertEqual(report["eval"], {"run": 610, "result": "failure"})
        self.assertEqual(report["failed"], ["eval"])

    def test_when_the_newest_deploys_eval_was_cancelled_in_its_turn_the_deploy_that_is_then_newest_is_followed(self):
        self.answers[f"{EVALS} --commit {MERGE}"] = [run(600, conclusion="cancelled", made="12:02:03", done="12:03:01")]
        self.answers[DEPLOYS] = InTurn(
            [run(510, NEWER, made="12:01:00", done="12:02:58")], [run(511, NEWEST, made="12:02:00", done="12:04:00")]
        )
        self.answers[f"{EVALS} --commit {NEWER}"] = [run(610, NEWER, "cancelled", made="12:03:00", done="12:04:02")]
        self.answers[f"{EVALS} --commit {NEWEST}"] = [run(611, NEWEST, made="12:04:01", done="12:06:30")]
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 0)
        self.assertEqual(report["eval"], {"run": 611, "result": "success"})

    def test_an_eval_that_measured_nothing_after_the_newest_deploy_itself_is_reported_as_it_ended(self):
        self.answers[f"{EVALS} --commit {MERGE}"] = [run(600, conclusion="cancelled", made="12:02:03", done="12:03:01")]
        self.answers[DEPLOYS] = [run(500)]
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertEqual(report["eval"], {"run": 600, "result": "cancelled"})
        self.assertEqual(self.slept, [])

    def test_an_eval_that_measured_is_read_without_asking_for_the_newest_deploy(self):
        for ended in ("success", "failure", "timed_out"):
            with self.subTest(ended=ended):
                self.answers[f"{EVALS} --commit {MERGE}"] = [
                    run(600, conclusion=ended, made="12:02:03", done="12:04:30")
                ]
                _, report, _ = self.run_command("27")
                self.assertEqual(report["eval"], {"run": 600, "result": ended})
        self.assertEqual([line for line in self.shell.ran if line.startswith(f"{DEPLOYS} --limit")], [])

    def test_an_issue_with_no_merged_pull_request_exits_1_and_waits_for_nothing(self):
        self.answers["gh pr list --state merged"] = []
        code, report, printed = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertIsNone(report)
        self.assertIn("#27", printed)
        self.assertEqual(self.shell.count("gh run"), 0)


class ConfirmARevert(ConfirmTest):
    """The feature's merge failed its eval and was reverted, and the revert's merge was uploaded and measured in
    its turn. An older revert of the feature merged before it."""

    def setUp(self):
        super().setUp()
        self.answers["gh pr list --state merged"] += [
            pull(39, "agent/27-revert", "f" * 40, "09:00:00"),
            pull(41, "agent/27-revert", REVERT, "12:30:00"),
        ]
        self.answers[f"{EVALS} --commit {MERGE}"] = [run(600, conclusion="failure", made="12:02:03", done="12:04:30")]
        self.answers[f"{DEPLOYS} --commit {REVERT}"] = [run(520, REVERT, made="12:30:02", done="12:32:00")]
        self.answers["gh run view 520"] = jobs("success")
        self.answers[f"{EVALS} --commit {REVERT}"] = [run(620, REVERT, made="12:32:03", done="12:34:30")]

    def test_with_revert_the_merge_of_the_newest_merged_revert_is_followed_through_the_same_three_steps(self):
        code, report, _ = self.run_command("27", "--revert")
        self.assertEqual(code, 0)
        self.assertEqual(
            report,
            {
                "issue": 27,
                "merge": REVERT,
                "deploy": {"run": 520, "commit": REVERT, "result": "success"},
                "live": {"result": "passed", "tries": 1},
                "eval": {"run": 620, "result": "success"},
                "failed": [],
            },
        )
        self.assertEqual(self.shell.count(OWNERS_TESTS), 1)

    def test_with_revert_a_revert_whose_own_deploy_failed_is_not_confirmed_by_the_features_deploy(self):
        self.answers[f"{DEPLOYS} --commit {REVERT}"] = [run(520, REVERT, "failure")]
        code, report, _ = self.run_command("27", "--revert")
        self.assertEqual(code, 1)
        self.assertEqual(report["deploy"], {"run": 520, "commit": REVERT, "result": "failure"})
        self.assertEqual(report["failed"], ["deploy", "live", "eval"])

    def test_without_revert_the_features_merge_is_still_the_one_followed(self):
        code, report, _ = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertEqual((report["merge"], report["eval"]), (MERGE, {"run": 600, "result": "failure"}))

    def test_with_revert_and_no_merged_revert_it_says_so_and_exits_1(self):
        self.answers["gh pr list --state merged"] = [pull(40, "agent/27-stop-clipping", MERGE, "11:59:58")]
        code, report, printed = self.run_command("27", "--revert")
        self.assertEqual(code, 1)
        self.assertIsNone(report)
        self.assertIn("#27", printed)
        self.assertIn("reverts", printed)
        self.assertEqual(self.shell.count("gh run"), 0)


if __name__ == "__main__":
    unittest.main()
