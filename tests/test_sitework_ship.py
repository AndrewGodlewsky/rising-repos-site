"""`ship` merges a feature's pull request only when every condition of the merge holds
(docs/workflow-plan.md, section 9), and merges exactly the commit it judged.

No test reaches GitHub or merges anything. `sitework.shell.run` is replaced by a stand-in that answers each
command from what the test gives it, in the shapes `gh` and `git` answer in, and keeps each command it was given.
Each test starts from a pull request that meets every condition, and changes the one thing it is about.
"""

import contextlib
import io
import json
import sys
import tarfile
import unittest
from unittest import mock

from sitework import shell, ship

OWNER = "the-owner"
HEAD = "a" * 40
REVIEWED = "b" * 40
MAIN = "c" * 40
MERGED = "e" * 40
TITLE = "Stop clipping the table on phones"
COMMENTS = "gh api repos/{owner}/{repo}/issues/27/comments"
GUARD = f"{sys.executable} -m sitework guard"
NEW_TESTS = f"{sys.executable} -m sitework new-tests"
CRITERIA = f"{sys.executable} -m sitework criteria"
MERGE = f"gh pr merge 40 --merge --match-head-commit {HEAD} --subject Merge #27: {TITLE} --body Refs #27"


class Shell:
    """Stands in for `sitework.shell.run`. A command is answered by the answer whose words it begins with, the
    longest of them when several do, and a command with no answer fails the test. An answer that is a function
    is called with the command and the folder it was run in. One that is not text is given as the JSON `gh` would
    print, and one that is an error is raised."""

    def __init__(self, answers: dict):
        self.answers = answers
        self.ran = []
        self.stdin = {}
        self.cwd = {}

    def __call__(self, *command, cwd=None, check=True, stdin=None):
        line = " ".join(command)
        self.ran.append(line)
        self.stdin[line] = stdin
        self.cwd[line] = cwd
        starts = [start for start in self.answers if line.startswith(start)]
        if not starts:
            raise AssertionError(f"the test gave no answer for: {line}")
        answer = self.answers[max(starts, key=len)]
        if callable(answer):
            answer = answer(command, cwd)
        if isinstance(answer, Exception):
            raise answer
        return answer if isinstance(answer, str) else json.dumps(answer)

    def first(self, start: str) -> str:
        """The first command that was run and begins with these words."""
        return next(line for line in self.ran if line.startswith(start))

    def count(self, start: str) -> int:
        return len([line for line in self.ran if line.startswith(start)])


def archive(command, cwd) -> str:
    """Stands in for `git archive`: writes the tar it was asked for, holding the scripts' folder with a guard in
    it, as the commit it names would."""
    (out,) = [word.removeprefix("--output=") for word in command if word.startswith("--output=")]
    text = b"# guard, as the commit holds it\n"
    member = tarfile.TarInfo("sitework/guard.py")
    member.size = len(text)
    with tarfile.open(out, "w") as tar:
        tar.addfile(member, io.BytesIO(text))
    return ""


def check(name: str, conclusion: str) -> dict:
    """A check of a pull request, as `gh pr view` gives one. One with no conclusion is still running."""
    return {
        "__typename": "CheckRun",
        "completedAt": "2026-11-22T20:29:12Z",
        "conclusion": conclusion,
        "detailsUrl": "https://github.com/the-owner/the-site/actions/runs/1/job/2",
        "name": name,
        "startedAt": "2026-11-22T20:27:39Z",
        "status": "COMPLETED" if conclusion else "IN_PROGRESS",
        "workflowName": "Build and deploy",
    }


def pull(number: int, branch: str, fork: bool = False) -> dict:
    """An open pull request, as `gh pr list` gives one."""
    return {
        "number": number,
        "state": "OPEN",
        "headRefName": branch,
        "headRefOid": HEAD,
        "isCrossRepository": fork,
        "mergeCommit": None,
        "mergedAt": None,
    }


def said(body: str, by: str = OWNER, number: int = 1) -> dict:
    """A comment, as GitHub's API gives one."""
    return {
        "id": 7000 + number,
        "html_url": f"https://github.com/the-owner/the-site/issues/27#issuecomment-{7000 + number}",
        "user": {"login": by},
        "created_at": f"2026-11-22T18:00:{number:02}Z",
        "body": body,
    }


def review(verdict: str, commit: str, **more) -> dict:
    return said(f"Site workflow: review\n\nVerdict: {verdict}\nCommit: {commit}\n\nWhat the reviewer read.", **more)


class ShipTest(unittest.TestCase):
    def setUp(self):
        self.guard_saw_the_copy = None
        self.answers = {
            "gh pr list --state open": [pull(40, "agent/27-stop-clipping")],
            "gh pr view 40 --json headRefOid,statusCheckRollup": {
                "headRefOid": HEAD,
                "statusCheckRollup": [check("build", "SUCCESS"), check("deploy", "SKIPPED")],
            },
            "git fetch origin": "",
            "git rev-parse origin/main": MAIN,
            f"git merge-base origin/main {HEAD}": MAIN,
            "gh issue view 27": {
                "author": {"login": OWNER},
                "labels": [{"name": "site-idea"}, {"name": "approved"}, {"name": "in-progress"}],
                "number": 27,
                "state": "OPEN",
                "title": TITLE,
                "url": "https://github.com/the-owner/the-site/issues/27",
            },
            "gh repo view": {"owner": {"id": "MDQ6", "login": OWNER}},
            COMMENTS: [review("pass", HEAD)],
            "git ls-tree --name-only origin/main sitework": "sitework",
            "git archive": archive,
            GUARD: self.guard,
            "git rev-parse HEAD": HEAD,
            "git status --porcelain": "",
            NEW_TESTS: "",
            CRITERIA: "",
            "gh pr merge 40": "",
            "gh pr view 40 --json mergeCommit": {"mergeCommit": {"oid": MERGED}},
        }
        self.shell = Shell(self.answers)
        self.enterContext(mock.patch.object(shell, "run", self.shell))

    def guard(self, command, cwd) -> str:
        """Stands in for `guard`, and notes whether the folder it was run in holds a copy of the scripts."""
        self.guard_saw_the_copy = (cwd / "sitework" / "guard.py").is_file()
        return ""

    def run_command(self, *arguments: str) -> tuple[int, str]:
        """Run `ship`, and give its exit code and what it printed."""
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            code = ship.main("ship", list(arguments))
        return code, printed.getvalue()

    def assertNotMerged(self, *arguments: str, fails: str) -> str:
        """Run `ship`, and expect it to exit 1 with a `fails:` line that holds `fails`, having merged nothing."""
        code, printed = self.run_command(*(arguments or ("27",)))
        self.assertEqual(code, 1, printed)
        failed = [line for line in printed.splitlines() if line.startswith("fails: ")]
        self.assertTrue(any(fails in line for line in failed), printed)
        self.assertEqual(self.shell.count("gh pr merge"), 0)
        return printed


class TheMerge(ShipTest):
    def test_a_pull_request_that_meets_every_condition_is_merged_as_one_merge_commit_named_for_the_issue(self):
        code, printed = self.run_command("27")
        self.assertEqual(code, 0, printed)
        self.assertEqual([line for line in self.shell.ran if line.startswith("gh pr merge")], [MERGE])

    def test_it_prints_that_each_of_the_eight_conditions_holds_and_then_the_merge_commit(self):
        _, printed = self.run_command("27")
        lines = printed.splitlines()
        self.assertEqual([line.split(":")[0] for line in lines[:-1]], ["holds"] * 8, printed)
        self.assertEqual(lines[-1], MERGED)

    def test_every_condition_is_reported_when_several_fail(self):
        self.answers[COMMENTS] = []
        self.answers[NEW_TESTS] = shell.Failed("tests/test_new.py::test_it passes on the commit before")
        code, printed = self.run_command("27")
        self.assertEqual(code, 1)
        starts = [line.split(":")[0] for line in printed.splitlines() if line.startswith(("holds: ", "fails: "))]
        self.assertEqual(starts, ["holds", "fails", "holds", "holds", "holds", "holds", "fails", "holds"])

    def test_a_merge_that_github_refuses_exits_1_with_what_it_printed(self):
        self.answers["gh pr merge 40"] = shell.Failed("gh pr merge 40: exit 1\nhead branch was modified")
        code, printed = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertIn("head branch was modified", printed)

    def test_a_merge_whose_commit_github_has_not_named_yet_still_exits_0(self):
        self.answers["gh pr view 40 --json mergeCommit"] = {"mergeCommit": None}
        code, printed = self.run_command("27")
        self.assertEqual(code, 0)
        self.assertIn("merged", printed.splitlines()[-1])


class ThePullRequest(ShipTest):
    def test_an_issue_with_no_open_pull_request_exits_1(self):
        self.answers["gh pr list --state open"] = [pull(39, "agent/2-another"), pull(41, "agent/270-another")]
        self.assertNotMerged(fails="#27 has 0 open pull requests")

    def test_an_issue_with_two_open_pull_requests_exits_1(self):
        self.answers["gh pr list --state open"] = [pull(40, "agent/27-stop-clipping"), pull(41, "agent/27-again")]
        self.assertNotMerged(fails="#27 has 2 open pull requests")

    def test_a_pull_request_from_a_fork_is_not_the_features(self):
        self.answers["gh pr list --state open"] = [pull(40, "agent/27-stop-clipping", fork=True)]
        self.assertNotMerged(fails="#27 has 0 open pull requests")

    def test_without_revert_the_pull_request_on_the_revert_branch_is_not_the_features(self):
        self.answers["gh pr list --state open"] = [pull(40, "agent/27-revert")]
        self.assertNotMerged(fails="#27 has 0 open pull requests")


class TheChecks(ShipTest):
    def rollup(self, *checks: dict) -> None:
        self.answers["gh pr view 40 --json headRefOid,statusCheckRollup"] = {
            "headRefOid": HEAD,
            "statusCheckRollup": list(checks),
        }

    def test_a_check_that_failed_merges_nothing(self):
        self.rollup(check("build", "FAILURE"), check("measure", "SUCCESS"))
        self.assertNotMerged(fails="build (failure)")

    def test_a_check_that_has_not_finished_merges_nothing(self):
        self.rollup(check("build", ""))
        self.assertNotMerged(fails="build (no conclusion yet)")

    def test_a_pull_request_with_no_check_merges_nothing(self):
        self.rollup()
        self.assertNotMerged(fails="no check")

    def test_a_check_that_was_skipped_is_not_one_that_passed(self):
        self.rollup(check("deploy", "SKIPPED"))
        self.assertNotMerged(fails="no check")

    def test_a_check_of_a_kind_that_gives_no_conclusion_merges_nothing(self):
        self.rollup(check("build", "SUCCESS"), {"__typename": "StatusContext", "state": "SUCCESS"})
        self.assertNotMerged(fails="StatusContext (no conclusion yet)")


class TheReview(ShipTest):
    def other_commit(self, reviewed_patch: str, head_patch: str) -> None:
        """Make the newest review pass another commit than the head, whose change has `reviewed_patch` as its
        patch id where the head's has `head_patch`."""
        self.answers[COMMENTS] = [review("pass", REVIEWED)]
        self.answers[f"git merge-base origin/main {REVIEWED}"] = "f" * 40
        self.answers[f"git diff --full-index {'f' * 40} {REVIEWED}"] = "diff --git a/x b/x\n+reviewed"
        self.answers[f"git diff --full-index {MAIN} {HEAD}"] = "diff --git a/x b/x\n+head"
        self.answers["git patch-id --verbatim"] = lambda command, cwd: (
            f"{reviewed_patch if 'reviewed' in self.shell.stdin['git patch-id --verbatim'] else head_patch} {'0' * 40}"
        )

    def test_an_issue_with_no_review_merges_nothing(self):
        self.answers[COMMENTS] = [said("Site workflow: plan\n\n## Verdict\n\ngo")]
        self.assertNotMerged(fails="no review")

    def test_a_review_that_did_not_pass_merges_nothing(self):
        self.answers[COMMENTS] = [review("changes needed", HEAD)]
        self.assertNotMerged(fails="changes needed")

    def test_only_the_newest_review_counts(self):
        self.answers[COMMENTS] = [review("pass", HEAD, number=1), review("changes needed", HEAD, number=2)]
        self.assertNotMerged(fails="changes needed")

    def test_a_review_that_a_stranger_wrote_passes_nothing(self):
        self.answers[COMMENTS] = [review("pass", HEAD, by="a-stranger")]
        self.assertNotMerged(fails="no review")

    def test_a_review_that_names_no_commit_merges_nothing(self):
        self.answers[COMMENTS] = [said("Site workflow: review\n\nVerdict: pass")]
        self.assertNotMerged(fails="names no commit")

    def test_a_review_of_another_commit_holds_when_the_head_carries_the_same_change(self):
        self.other_commit("1" * 40, "1" * 40)
        code, printed = self.run_command("27")
        self.assertEqual(code, 0, printed)
        self.assertIn("carries the same change", printed)

    def test_a_review_of_another_commit_merges_nothing_when_the_head_carries_another_change(self):
        self.other_commit("1" * 40, "2" * 40)
        self.assertNotMerged(fails="carries another change")

    def test_two_changes_are_compared_with_their_white_space_kept(self):
        self.other_commit("1" * 40, "1" * 40)
        self.run_command("27")
        self.assertEqual(self.shell.count("git patch-id --verbatim"), 2)
        self.assertEqual(self.shell.stdin["git patch-id --verbatim"], "diff --git a/x b/x\n+head\n")


class MainAndTheIssue(ShipTest):
    def test_a_head_that_does_not_contain_the_head_of_main_merges_nothing(self):
        self.answers[f"git merge-base origin/main {HEAD}"] = "9" * 40
        self.assertNotMerged(fails="does not contain the head of main")

    def test_main_is_fetched_before_the_head_is_held_against_it(self):
        self.run_command("27")
        ran = self.shell.ran
        self.assertLess(ran.index("git fetch origin"), ran.index("git rev-parse origin/main"))

    def test_a_closed_issue_merges_nothing(self):
        self.answers["gh issue view 27"]["state"] = "CLOSED"
        self.assertNotMerged(fails="#27 is closed")

    def test_an_issue_whose_approval_was_withdrawn_merges_nothing(self):
        self.answers["gh issue view 27"]["labels"] = [{"name": "site-idea"}, {"name": "in-progress"}]
        self.assertNotMerged(fails="no longer carries approved")


class TheGuard(ShipTest):
    def test_guard_reads_the_change_from_mains_copy_of_the_scripts_in_a_temporary_folder(self):
        self.run_command("27")
        self.assertTrue(
            self.shell.first("git archive").endswith(" origin/main sitework"), self.shell.first("git archive")
        )
        self.assertTrue(self.guard_saw_the_copy)
        ran_in = self.shell.cwd[self.shell.first(GUARD)]
        self.assertNotEqual(ran_in, shell.ROOT)
        self.assertFalse(ran_in.exists(), "the temporary folder was left behind")

    def test_guard_is_given_this_repository_the_merge_base_and_the_head(self):
        self.run_command("27")
        self.assertEqual(self.shell.first(GUARD), f"{GUARD} --repository {shell.ROOT} --base {MAIN} --head {HEAD}")

    def test_each_allowed_line_of_the_owners_own_comments_gives_guard_its_patterns(self):
        self.answers[COMMENTS] = [
            review("pass", HEAD, number=1),
            said("Yes, move the limit.\nAllowed: evals/site/limits.json, tests/test_page_weight.py", number=2),
            said("Allowed: pyproject.toml", number=3),
        ]
        self.run_command("27")
        self.assertTrue(
            self.shell.first(GUARD).endswith(
                " --allow evals/site/limits.json tests/test_page_weight.py pyproject.toml"
            ),
            self.shell.first(GUARD),
        )

    def test_an_allowed_line_the_owner_did_not_write_allows_nothing(self):
        self.answers[COMMENTS] = [
            said("Site workflow: review\n\nVerdict: pass\nCommit: " + HEAD + "\nAllowed: pyproject.toml", number=1),
            said("Allowed: .github/workflows/*.yml", by="a-stranger", number=2),
        ]
        self.run_command("27")
        self.assertNotIn("--allow", self.shell.first(GUARD))

    def test_a_guarded_path_the_change_touches_merges_nothing_and_is_named(self):
        self.answers[GUARD] = shell.Failed("python -m sitework guard: exit 1\npyproject.toml: a dependency")
        printed = self.assertNotMerged(fails="guard")
        self.assertIn("pyproject.toml: a dependency", printed)

    def test_when_main_has_no_scripts_yet_the_branchs_copy_is_used_and_that_is_said(self):
        self.answers["git ls-tree --name-only origin/main sitework"] = ""
        code, printed = self.run_command("27")
        self.assertEqual(code, 0, printed)
        (archived,) = [line for line in self.shell.ran if line.startswith("git archive")]
        self.assertTrue(archived.endswith(f" {HEAD} sitework"), archived)
        self.assertIn("the branch's copy", printed)


class TheCheckout(ShipTest):
    """`new-tests` and `criteria` read the checkout they run in, so it has to hold the commit that is merged."""

    def test_a_checkout_at_another_commit_than_the_pull_requests_head_merges_nothing(self):
        self.answers["git rev-parse HEAD"] = REVIEWED
        self.assertNotMerged(fails=f"the checkout is at {REVIEWED[:7]}, and not at the pull request's head, {HEAD[:7]}")

    def test_a_checkout_whose_working_tree_is_not_clean_merges_nothing_and_what_differs_is_named(self):
        self.answers["git status --porcelain"] = "M sitebuild/static/site.css\n?? notes.txt"
        printed = self.assertNotMerged(fails="the checkout's working tree is not clean")
        self.assertIn("M sitebuild/static/site.css", printed)
        self.assertIn("?? notes.txt", printed)

    def test_the_checkout_is_judged_before_the_two_commands_that_read_it(self):
        self.run_command("27")
        ran = self.shell.ran
        for asked in ("git rev-parse HEAD", "git status --porcelain"):
            self.assertLess(ran.index(asked), ran.index(self.shell.first(NEW_TESTS)))
            self.assertLess(ran.index(asked), ran.index(self.shell.first(CRITERIA)))


class NewTestsAndCriteria(ShipTest):
    def test_a_new_test_that_was_not_shown_to_fail_merges_nothing(self):
        self.answers[NEW_TESTS] = shell.Failed("tests/test_new.py::test_it passes on the commit before")
        printed = self.assertNotMerged(fails="new-tests")
        self.assertIn("passes on the commit before", printed)

    def test_a_criterion_without_a_proof_that_passes_merges_nothing(self):
        self.answers[CRITERIA] = shell.Failed("criterion 2 has no proof")
        self.assertNotMerged(fails="criteria")

    def test_new_tests_are_asked_about_the_change_from_the_merge_base_to_the_head_and_criteria_about_the_issue(self):
        self.run_command("27")
        self.assertEqual(self.shell.first(NEW_TESTS), f"{NEW_TESTS} --base {MAIN} --head {HEAD}")
        self.assertEqual(self.shell.first(CRITERIA), f"{CRITERIA} --issue 27")


class TheRevert(ShipTest):
    def setUp(self):
        super().setUp()
        self.answers["gh pr list --state open"] = [pull(40, "agent/27-revert"), pull(38, "agent/27-stop-clipping")]
        self.answers[COMMENTS] = []

    def test_with_revert_the_pull_request_on_the_revert_branch_is_merged_and_named_as_a_revert(self):
        code, printed = self.run_command("27", "--revert")
        self.assertEqual(code, 0, printed)
        (merge,) = [line for line in self.shell.ran if line.startswith("gh pr merge")]
        self.assertEqual(merge, MERGE.replace("Merge #27", "Merge the revert of #27"))

    def test_with_revert_no_review_no_new_test_and_no_criterion_is_asked_for(self):
        code, printed = self.run_command("27", "--revert")
        self.assertEqual(code, 0, printed)
        self.assertEqual(self.shell.count(NEW_TESTS) + self.shell.count(CRITERIA), 0)
        self.assertEqual([line.split(":")[0] for line in printed.splitlines()[:-1]], ["holds"] * 4)

    def test_with_revert_the_checkout_is_not_asked_about_since_nothing_is_run_in_it(self):
        self.answers["git rev-parse HEAD"] = REVIEWED
        self.answers["git status --porcelain"] = "M sitebuild/static/site.css"
        code, printed = self.run_command("27", "--revert")
        self.assertEqual(code, 0, printed)
        self.assertEqual(self.shell.count("git rev-parse HEAD") + self.shell.count("git status"), 0)

    def test_with_revert_a_check_that_failed_still_merges_nothing(self):
        self.answers["gh pr view 40 --json headRefOid,statusCheckRollup"]["statusCheckRollup"] = [
            check("build", "FAILURE")
        ]
        self.assertNotMerged("27", "--revert", fails="build (failure)")

    def test_with_revert_a_guarded_path_still_merges_nothing(self):
        self.answers[GUARD] = shell.Failed("python -m sitework guard: exit 1\npyproject.toml: a dependency")
        self.assertNotMerged("27", "--revert", fails="guard")


if __name__ == "__main__":
    unittest.main()
