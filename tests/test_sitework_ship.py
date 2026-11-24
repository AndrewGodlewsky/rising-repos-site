"""`ship` merges a feature's pull request only when every condition of the merge holds
(docs/workflow-plan.md, section 9), and merges exactly the commit it judged.

No test reaches GitHub or merges anything. `sitework.shell.run` is replaced by a stand-in that answers each
command from what the test gives it, in the shapes `gh` and `git` answer in, and keeps each command it was given.
Each test starts from a pull request that meets every condition, and changes the one thing it is about.

Two things only git itself can show: which bytes of a change reach `git patch-id`, and what reverting a merge
gives. Those tests run the real git in a repository of their own in a temporary folder, which has no remote.
"""

import contextlib
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sitework import issue, shell, ship

OWNER = "the-owner"
HEAD = "a" * 40
REVIEWED = "b" * 40
MAIN = "c" * 40
MERGED = "e" * 40
FEATURE = "d" * 40
MEND = "6" * 40
TREE = "7" * 40
REVERT = f"git revert -m 1 --no-commit {FEATURE}"
"""The commit that merged the feature, the commit that merged its mend in a test that has one, the tree that
reverting the feature's merge on the head of main gives, and the command that reverts it without committing."""
TITLE = "Stop clipping the table on phones"
COMMENTS = "gh api repos/{owner}/{repo}/issues/27/comments"
GUARD = f"{sys.executable} -m sitework guard"
NEW_TESTS = f"{sys.executable} -m sitework new-tests"
CRITERIA = f"{sys.executable} -m sitework criteria"
MAIN_NOW = "git ls-remote origin refs/heads/main"
HOW = ["--full-index", "--binary"]
"""How `git diff` is asked to write a change that `git patch-id` then names."""
DIFF = b"diff --git a/x b/x\n+%b\n"
"""What stands in for the diff that ends at a commit."""
MERGE = f"gh pr merge 40 --merge --match-head-commit {HEAD} --subject Merge #27: {TITLE} --body Refs #27"
ITS_BRANCH = "agent/27-revert"
ON_GITHUB = f"git ls-remote origin refs/heads/{ITS_BRANCH}"
OFF_GITHUB = f"git push origin --delete {ITS_BRANCH}"
LOCAL = f"git branch --list {ITS_BRANCH}"
HELD = f"git merge-base --is-ancestor {ITS_BRANCH} origin/main"
DELETE = f"git branch -D {ITS_BRANCH}"
"""The branch a revert is made on, and the commands that ask whether GitHub has it, delete it there, ask whether
this repository has it and whether origin/main holds its every commit, and delete it here."""


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


def merged(number: int, branch: str, merge: str, at: str = "19:00:00") -> dict:
    """A pull request that merged at this time of the day, as `gh pr list` gives one."""
    return {
        **pull(number, branch),
        "state": "MERGED",
        "mergeCommit": {"oid": merge},
        "mergedAt": f"2026-11-22T{at}Z",
    }


def said(body: str, by: str = OWNER, number: int = 1, edited: int | None = None) -> dict:
    """A comment, as GitHub's API gives one. `number` is the second it was posted in, so a higher one is a later
    comment, and `edited` is the second it was last edited in, for one that was edited after it was posted."""
    return {
        "id": 7000 + number,
        "html_url": f"https://github.com/the-owner/the-site/issues/27#issuecomment-{7000 + number}",
        "user": {"login": by},
        "created_at": f"2026-11-22T18:00:{number:02}Z",
        "updated_at": f"2026-11-22T18:00:{edited or number:02}Z",
        "body": body,
    }


def review(verdict: str, commit: str, **more) -> dict:
    return said(f"Site workflow: review\n\nVerdict: {verdict}\nCommit: {commit}\n\nWhat the reviewer read.", **more)


def plan(**more) -> dict:
    return said("Site workflow: plan\n\n## Verdict\n\nGo", **more)


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
            MAIN_NOW: f"{MAIN}\trefs/heads/main",
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

    def test_without_revert_the_features_branch_is_left_for_close_since_a_mend_is_made_on_it(self):
        code, printed = self.run_command("27")
        self.assertEqual(code, 0, printed)
        ran = self.shell.ran
        self.assertEqual(ran[ran.index(MERGE) + 1 :], ["gh pr view 40 --json mergeCommit"])


class ThePullRequest(ShipTest):
    def test_an_issue_with_no_open_pull_request_exits_1(self):
        self.answers["gh pr list --state open"] = [pull(39, "agent/2-another"), pull(271, "agent/270-another")]
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
        patch id where the head's has `head_patch`. `self.diffs` then holds the words of each `git diff` that was
        run, and `self.piped` what each `git patch-id` was given as its standard input, in the order they ran."""
        self.diffs, self.piped = [], []
        self.answers[COMMENTS] = [review("pass", REVIEWED)]
        self.answers[f"git merge-base origin/main {REVIEWED}"] = "f" * 40
        self.answers["git diff --full-index --binary --output="] = self.diff
        self.answers["git patch-id --verbatim"] = lambda command, cwd: (
            f"{reviewed_patch if self.pipe().endswith(DIFF % REVIEWED.encode()) else head_patch} {'0' * 40}"
        )

    def diff(self, command, cwd) -> str:
        """Stands in for `git diff --output=<file> <base> <commit>`: writes a diff that names the two commits to
        the file, as bytes, and prints nothing, as git does."""
        self.diffs.append(command)
        out = Path(command[4].removeprefix("--output="))
        out.write_bytes(b"from " + command[-2].encode() + b"\n" + DIFF % command[-1].encode())
        return ""

    def pipe(self) -> bytes:
        """What the `git patch-id` that is running was given as its standard input, read while the file is still
        there, and kept."""
        self.piped.append(self.shell.stdin["git patch-id --verbatim"])
        return self.piped[-1].read_bytes()

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

    def test_a_plan_edited_after_the_newest_review_was_posted_merges_nothing(self):
        self.answers[COMMENTS] = [plan(number=1, edited=3), review("pass", HEAD, number=2)]
        self.assertNotMerged(fails="the plan was edited after the newest review")

    def test_a_plan_last_edited_before_the_newest_review_was_posted_is_the_plan_that_was_reviewed(self):
        self.answers[COMMENTS] = [
            review("changes needed", HEAD, number=1),
            plan(number=2, edited=3),
            review("pass", HEAD, number=4),
        ]
        code, printed = self.run_command("27")
        self.assertEqual(code, 0, printed)

    def test_an_issue_with_no_plan_comment_is_not_held_to_when_a_plan_was_edited(self):
        self.answers[COMMENTS] = [review("pass", HEAD, number=1), said("Go on.", number=2, edited=5)]
        code, printed = self.run_command("27")
        self.assertEqual(code, 0, printed)

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

    def test_each_change_is_read_from_where_its_commit_left_main_with_whole_object_names_and_binary_files_in_it(self):
        self.other_commit("1" * 40, "1" * 40)
        self.run_command("27")
        asked = [[*words[2:4], *words[5:]] for words in self.diffs]
        self.assertEqual(asked, [[*HOW, "f" * 40, REVIEWED], [*HOW, MAIN, HEAD]])

    def test_a_change_reaches_patch_id_as_the_file_git_wrote_and_never_as_text_that_was_read_and_written_again(self):
        self.other_commit("1" * 40, "1" * 40)
        self.run_command("27")
        written = [Path(words[4].removeprefix("--output=")) for words in self.diffs]
        self.assertEqual(self.piped, written)
        self.assertEqual(len(set(written)), 2)
        self.assertFalse(any(file.parent.exists() for file in written), "a temporary folder was left behind")

    def test_a_review_that_names_its_commit_by_fewer_than_its_40_hex_digits_merges_nothing(self):
        self.answers[COMMENTS] = [review("pass", HEAD[:12])]
        self.assertNotMerged(fails="40 hex digits")


class ARepository(unittest.TestCase):
    """A git repository of its own in a temporary folder, for what only git itself can show: which bytes of a
    change reach `git patch-id`, and what reverting a merge gives. It has one commit, which `origin/main` names,
    and no remote, so nothing in it can reach GitHub."""

    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.enterContext(mock.patch.object(shell, "ROOT", self.root))
        shell.git("init", "--quiet", "--initial-branch=main")
        # Git for Windows may be set to rewrite a line's end as it takes a file in, and here the end is held.
        for key, value in (
            ("user.name", "A test"),
            ("user.email", "test@example.invalid"),
            ("commit.gpgsign", "false"),
            ("core.autocrlf", "false"),
        ):
            shell.git("config", key, value)
        self.main = self.main_is(self.commit(None, "board.txt", b"a board\n"))

    def commit(self, start: str | None, path: str, held: bytes) -> str:
        """A commit on top of `start`, on no branch, that writes these bytes to the file at `path`."""
        if start:
            shell.git("checkout", "--quiet", "--detach", start)
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / path).write_bytes(held)
        shell.git("add", path)
        shell.git("commit", "--quiet", "--message", f"Write {path}")
        return shell.git("rev-parse", "HEAD")

    def main_is(self, commit: str) -> str:
        """Move `origin/main` to the commit, as a fetch does when main has moved on GitHub."""
        shell.git("update-ref", "refs/remotes/origin/main", commit)
        return commit


class ThePatchIdOfAChange(ARepository):
    """The diff goes from git to git as bytes. Read as text on the way, a byte that is not UTF-8 would be
    replaced and a line's end rewritten, and two heads that differ only there would share one id, so that the
    second would merge on the first's review."""

    def test_two_changes_that_differ_only_in_a_byte_that_is_not_utf_8_have_different_ids(self):
        one = self.commit(self.main, "page.txt", b"caf\xe9\n")
        other = self.commit(self.main, "page.txt", b"caf\xe8\n")
        self.assertNotEqual(ship.patch_id(one), ship.patch_id(other))

    def test_two_changes_that_differ_only_in_how_a_line_ends_have_different_ids(self):
        one = self.commit(self.main, "page.txt", b"a row\r\n")
        other = self.commit(self.main, "page.txt", b"a row\n")
        self.assertNotEqual(ship.patch_id(one), ship.patch_id(other))

    def test_two_changes_that_differ_only_in_a_file_that_is_not_text_have_different_ids(self):
        one = self.commit(self.main, "icon.bin", b"\x00\x01an icon")
        other = self.commit(self.main, "icon.bin", b"\x00\x02an icon")
        self.assertNotEqual(ship.patch_id(one), ship.patch_id(other))

    def test_one_change_has_one_id_before_and_after_its_branch_is_brought_up_to_a_main_that_moved(self):
        reviewed = self.commit(self.main, "page.txt", b"caf\xe9\r\na row\n")
        self.main_is(self.commit(self.main, "board.txt", b"a board\nanother board day\n"))
        shell.git("checkout", "--quiet", "--detach", reviewed)
        shell.git("merge", "--quiet", "--no-edit", "origin/main")
        head = shell.git("rev-parse", "HEAD")
        self.assertNotEqual(*(shell.git("merge-base", "origin/main", commit) for commit in (reviewed, head)))
        self.assertRegex(ship.patch_id(reviewed), "^[0-9a-f]{40}$")
        self.assertEqual(ship.patch_id(reviewed), ship.patch_id(head))


class MainAndTheIssue(ShipTest):
    def test_a_head_that_does_not_contain_the_head_of_main_merges_nothing(self):
        self.answers[f"git merge-base origin/main {HEAD}"] = "9" * 40
        self.assertNotMerged(fails="does not contain the head of main")

    def test_main_is_fetched_before_the_head_is_held_against_it(self):
        self.run_command("27")
        ran = self.shell.ran
        self.assertLess(ran.index("git fetch origin"), ran.index("git rev-parse origin/main"))

    def test_a_main_that_moved_while_the_conditions_were_judged_merges_nothing_and_says_to_run_it_again(self):
        self.answers[MAIN_NOW] = f"{'9' * 40}\trefs/heads/main"
        printed = self.assertNotMerged(fails=f"main moved from {MAIN[:7]} to 9999999")
        self.assertIn("Run it again", printed)

    def test_main_is_read_from_github_again_after_the_last_condition_and_just_before_the_merge(self):
        self.run_command("27")
        ran = self.shell.ran
        self.assertLess(ran.index(self.shell.first(CRITERIA)), ran.index(MAIN_NOW))
        self.assertEqual(ran.index(MAIN_NOW) + 1, ran.index(MERGE))

    def test_a_main_that_github_no_longer_names_merges_nothing(self):
        self.answers[MAIN_NOW] = ""
        self.assertNotMerged(fails="main moved")

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

    def test_an_allowed_pattern_that_begins_with_a_dash_is_left_out_since_guard_would_read_it_as_an_option(self):
        self.answers[COMMENTS] = [
            review("pass", HEAD, number=1),
            said("Allowed: --head, pyproject.toml, -h, --repository=/another, uv.lock", number=2),
        ]
        self.run_command("27")
        self.assertTrue(
            self.shell.first(GUARD).endswith(f" --head {HEAD} --allow pyproject.toml uv.lock"), self.shell.first(GUARD)
        )

    def test_an_allowed_line_that_holds_only_patterns_that_begin_with_a_dash_allows_nothing(self):
        self.answers[COMMENTS] = [review("pass", HEAD, number=1), said("Allowed: --head, --base", number=2)]
        self.run_command("27")
        self.assertTrue(self.shell.first(GUARD).endswith(f" --head {HEAD}"), self.shell.first(GUARD))

    def test_a_guarded_path_the_change_touches_merges_nothing_and_is_named(self):
        self.answers[GUARD] = shell.Failed("python -m sitework guard: exit 1\npyproject.toml: a dependency")
        printed = self.assertNotMerged(fails="guard")
        self.assertIn("pyproject.toml: a dependency", printed)

    def test_when_main_holds_no_scripts_nothing_is_merged_and_the_branchs_own_copy_of_guard_judges_nothing(self):
        self.answers["git ls-tree --name-only origin/main sitework"] = ""
        self.assertNotMerged(fails="main holds no guard")
        self.assertEqual(self.shell.count("git archive") + self.shell.count(GUARD), 0)


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


class ARevert(ShipTest):
    """A test that starts from a revert that meets every condition. Git is a stand-in, one merge of the feature
    stands, the pull request's tree is the tree of that merge's revert, and the revert's branch is already gone
    from GitHub and from this repository, unless a test says otherwise."""

    def setUp(self):
        super().setUp()
        self.answers["gh pr list --state open"] = [pull(40, ITS_BRANCH), pull(39, "agent/27-again")]
        self.answers["gh pr list --state merged"] = [merged(38, "agent/27-stop-clipping", FEATURE)]
        self.answers[COMMENTS] = []
        self.answers["git worktree add --detach"] = ""
        self.answers[REVERT] = ""
        self.answers["git write-tree"] = TREE
        self.answers[f"git rev-parse {HEAD}^{{tree}}"] = TREE
        self.answers["git worktree remove --force"] = ""
        self.answers[ON_GITHUB] = ""
        self.answers[LOCAL] = ""


class TheRevert(ARevert):
    """No reviewer reads a revert, so the lane merges one thing alone: the pull request that holds exactly what
    reverting each merge of the feature that stands gives on the head of main."""

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

    def test_with_revert_a_main_that_moved_while_the_conditions_were_judged_still_merges_nothing(self):
        self.answers[MAIN_NOW] = f"{'9' * 40}\trefs/heads/main"
        self.assertNotMerged("27", "--revert", fails="main moved")

    def test_a_revert_that_holds_anything_but_the_revert_is_not_merged(self):
        self.answers[f"git rev-parse {HEAD}^{{tree}}"] = "8" * 40
        self.assertNotMerged("27", "--revert", fails=f"{HEAD[:7]} holds something other than the revert of #27's merge")

    def test_with_revert_an_issue_with_no_merged_pull_request_merges_nothing(self):
        self.answers["gh pr list --state merged"] = [merged(271, "agent/270-another", FEATURE)]
        self.assertNotMerged("27", "--revert", fails="#27 has no merged pull request that a revert has not undone")
        self.assertEqual(self.shell.count("git worktree") + self.shell.count("git revert"), 0)

    def test_with_revert_a_feature_whose_every_merge_was_already_reverted_merges_nothing(self):
        self.answers["gh pr list --state merged"] = [
            merged(36, "agent/27-stop-clipping", FEATURE, at="19:00:00"),
            merged(37, "agent/27-revert", "5" * 40, at="19:30:00"),
        ]
        self.assertNotMerged("27", "--revert", fails="#27 has no merged pull request that a revert has not undone")
        self.assertEqual(self.shell.count("git worktree") + self.shell.count("git revert"), 0)

    def test_with_revert_a_feature_and_its_mend_are_reverted_in_one_command_the_newest_first(self):
        self.answers["gh pr list --state merged"] = [
            merged(36, "agent/27-stop-clipping", FEATURE, at="19:00:00"),
            merged(38, "agent/27-stop-clipping", MEND, at="19:30:00"),
        ]
        self.answers["git revert -m 1 --no-commit"] = ""
        code, printed = self.run_command("27", "--revert")
        self.assertEqual(code, 0, printed)
        reverted = [line for line in self.shell.ran if line.startswith("git revert")]
        self.assertEqual(reverted, [f"git revert -m 1 --no-commit {MEND} {FEATURE}"])
        self.assertIn(f"the revert of #27's merges, {MEND[:7]} and {FEATURE[:7]}, on the head of main", printed)

    def test_with_revert_a_merge_that_does_not_revert_on_the_head_of_main_merges_nothing_and_git_says_why(self):
        self.answers[REVERT] = shell.Failed(f"{REVERT}: exit 1\nCONFLICT (content): Merge conflict in page.css")
        printed = self.assertNotMerged("27", "--revert", fails="cannot be made")
        self.assertIn("Merge conflict in page.css", printed)
        self.assertTrue(self.shell.ran[-1].startswith("git worktree remove --force "), self.shell.ran[-1])

    def test_with_revert_the_merge_is_reverted_on_the_head_of_main_in_a_worktree_that_is_removed_afterwards(self):
        self.run_command("27", "--revert")
        tree = self.shell.cwd[REVERT]
        steps = [
            f"git worktree add --detach {tree} {MAIN}",
            REVERT,
            "git write-tree",
            f"git worktree remove --force {tree}",
        ]
        self.assertEqual([line for line in self.shell.ran if line in steps], steps)
        self.assertEqual(self.shell.cwd["git write-tree"], tree)
        self.assertNotIn(shell.ROOT, [tree, *tree.parents])
        self.assertEqual(self.shell.count("git commit") + self.shell.count("git push"), 0)

    def test_with_revert_guard_is_not_run_since_it_would_refuse_a_revert_that_takes_a_line_from_the_owners_tests(self):
        self.answers[GUARD] = shell.Failed("owner_tests/README.md: the owner's tests: this file lost a line")
        code, printed = self.run_command("27", "--revert")
        self.assertEqual(code, 0, printed)
        self.assertEqual(self.shell.count(GUARD) + self.shell.count("git archive"), 0)

    def test_with_revert_no_comment_is_read_since_nothing_in_the_lane_turns_on_one(self):
        self.answers[COMMENTS] = shell.Failed("gh api: exit 1\nHTTP 502")
        code, printed = self.run_command("27", "--revert")
        self.assertEqual(code, 0, printed)
        self.assertEqual(self.shell.count(COMMENTS), 0)


class TheRevertsBranch(ARevert):
    """A finished run leaves no branch behind, and nothing else removes the branch a revert was made on, since
    `close` is not run for a feature that was put back. So `ship --revert` deletes it once its pull request has
    merged, on GitHub and in this repository, and fails for neither, because the merge is made by then. Here both
    have the branch, origin/main holds its every commit once the merge is made, and the checkout is on the
    feature's branch, unless a test says otherwise."""

    def setUp(self):
        super().setUp()
        self.answers[ON_GITHUB] = f"{HEAD}\trefs/heads/{ITS_BRANCH}"
        self.answers[OFF_GITHUB] = ""
        self.answers[LOCAL] = ITS_BRANCH
        self.answers[HELD] = ""
        self.answers["git branch --show-current"] = "agent/27-stop-clipping"
        self.answers["git switch --detach"] = ""
        self.answers[DELETE] = f"Deleted branch {ITS_BRANCH} (was {HEAD[:7]})."

    def after_the_merge(self) -> list[str]:
        """The git commands that were run after the pull request was merged, in the order they ran."""
        ran = self.shell.ran
        return [line for line in ran[ran.index(self.shell.first("gh pr merge")) + 1 :] if line.startswith("git")]

    def asked_of_the_branch(self) -> int:
        """How many commands asked about the revert's branch or changed it, on GitHub or here."""
        return sum(self.shell.count(start) for start in (ON_GITHUB, OFF_GITHUB, LOCAL, HELD, DELETE, "git switch"))

    def assertMergedAndLeft(self, *parts: str) -> None:
        """Run `ship --revert`, and expect it to exit 0 with the merge made, exactly one printed line that names
        the branch, with each of `parts` in it, and the merge commit as the last line all the same."""
        code, printed = self.run_command("27", "--revert")
        self.assertEqual(code, 0, printed)
        self.assertEqual(self.shell.count("gh pr merge"), 1)
        (line,) = [line for line in printed.splitlines() if ITS_BRANCH in line]
        for part in parts:
            self.assertIn(part, line)
        self.assertEqual(printed.splitlines()[-1], MERGED)

    def test_once_the_revert_has_merged_its_branch_is_deleted_on_github_and_then_in_this_repository(self):
        code, printed = self.run_command("27", "--revert")
        self.assertEqual(code, 0, printed)
        self.assertEqual(
            self.after_the_merge(),
            [ON_GITHUB, OFF_GITHUB, LOCAL, "git fetch origin main", HELD, "git branch --show-current", DELETE],
        )
        self.assertNotIn(ITS_BRANCH, printed)
        self.assertEqual(printed.splitlines()[-1], MERGED)

    def test_a_reverts_branch_that_is_already_gone_from_github_and_from_here_is_no_error(self):
        self.answers[ON_GITHUB] = ""
        self.answers[LOCAL] = ""
        code, printed = self.run_command("27", "--revert")
        self.assertEqual(code, 0, printed)
        self.assertEqual(self.after_the_merge(), [ON_GITHUB, LOCAL])
        self.assertNotIn(ITS_BRANCH, printed)

    def test_a_delete_that_github_refuses_is_one_printed_line_and_no_failure_and_the_local_branch_still_goes(self):
        refusal = f"! [remote rejected] {ITS_BRANCH} (protected branch hook declined)"
        self.answers[OFF_GITHUB] = shell.Failed(f"{OFF_GITHUB}: exit 1\n{refusal}")
        self.assertMergedAndLeft("is left on GitHub", refusal)
        self.assertEqual(self.after_the_merge()[-1], DELETE)

    def test_a_github_that_cannot_be_asked_for_the_branch_is_one_printed_line_and_no_failure(self):
        refusal = "fatal: unable to access 'https://github.com/the-owner/the-site/'"
        self.answers[ON_GITHUB] = shell.Failed(f"{ON_GITHUB}: exit 128\n{refusal}", 128)
        self.assertMergedAndLeft("is left on GitHub", refusal)
        self.assertEqual(self.shell.count(OFF_GITHUB), 0)

    def test_a_local_delete_that_git_refuses_is_one_printed_line_and_no_failure(self):
        refusal = f"error: cannot delete branch '{ITS_BRANCH}' used by worktree at '/another/checkout'"
        self.answers[DELETE] = shell.Failed(f"{DELETE}: exit 1\n{refusal}")
        self.assertMergedAndLeft("The local branch", "is left", refusal)
        self.assertEqual(self.shell.count(OFF_GITHUB), 1)

    def test_a_local_reverts_branch_that_holds_a_commit_main_does_not_is_left_and_says_so(self):
        self.answers[HELD] = shell.Failed(f"{HELD}: exit 1")
        self.assertMergedAndLeft("The local branch", "is left", "a commit that main does not")
        self.assertEqual(self.shell.count(DELETE) + self.shell.count("git switch"), 0)

    def test_a_checkout_that_is_on_the_reverts_branch_leaves_it_before_the_branch_is_deleted(self):
        self.answers["git branch --show-current"] = ITS_BRANCH
        code, printed = self.run_command("27", "--revert")
        self.assertEqual(code, 0, printed)
        self.assertEqual(self.after_the_merge()[-3:], ["git branch --show-current", "git switch --detach", DELETE])

    def test_a_revert_whose_condition_fails_keeps_its_branch(self):
        self.answers["gh pr view 40 --json headRefOid,statusCheckRollup"]["statusCheckRollup"] = [
            check("build", "FAILURE")
        ]
        self.assertNotMerged("27", "--revert", fails="build (failure)")
        self.assertEqual(self.asked_of_the_branch(), 0)

    def test_a_revert_whose_merge_github_refuses_keeps_its_branch(self):
        self.answers["gh pr merge 40"] = shell.Failed("gh pr merge 40: exit 1\nhead branch was modified")
        code, printed = self.run_command("27", "--revert")
        self.assertEqual(code, 1, printed)
        self.assertEqual(self.asked_of_the_branch(), 0)


class TheRevertOfAMerge(ARepository):
    """What the lane holds a pull request against, made by git itself: a feature that changed a page and whose
    reviewer added to the owner's tests is merged into main, and a board day is published on top of it. The
    merged pull requests are a stand-in that names the real merges, so that which of them stand is worked out as
    it is for a real issue, and `landed` holds them."""

    def setUp(self):
        super().setUp()
        start = self.commit(self.main, "owner_tests/README.md", b"A reader can sort the board.\n")
        feature = self.commit(start, "page.css", b"table { overflow: auto }\n")
        sentences = b"A reader can sort the board.\nA reader can scroll the table.\n"
        feature = self.commit(feature, "owner_tests/README.md", sentences)
        shell.git("checkout", "--quiet", "--detach", start)
        shell.git("merge", "--quiet", "--no-ff", "--no-edit", feature)
        self.merge = shell.git("rev-parse", "HEAD")
        self.main = self.main_is(self.commit(self.merge, "board.txt", b"a board\nanother board day\n"))
        self.landed = [merged(40, "agent/27-scroll-the-table", self.merge, at="19:00:00")]
        self.enterContext(mock.patch.object(issue, "pulls", lambda state="all": list(self.landed)))

    def merged_into(self, main: str, head: str) -> str:
        """The commit that merges `head` into `main`, as GitHub merges a pull request here: one merge commit
        whose first parent is main."""
        shell.git("checkout", "--quiet", "--detach", main)
        shell.git("merge", "--quiet", "--no-ff", "--no-edit", head)
        return shell.git("rev-parse", "HEAD")

    def revert(self, on: str, *merges: str) -> str:
        """The commit `sitework revert` makes: each of these merges reverted on top of this commit, in this
        order, or the feature's one merge when none is given."""
        shell.git("checkout", "--quiet", "--detach", on)
        for merge in merges or (self.merge,):
            shell.git("revert", "-m", "1", "--no-edit", merge)
        return shell.git("rev-parse", "HEAD")

    def mended(self) -> str:
        """Land a mend of the feature, and give its merge: a second pull request of the same issue, from the
        feature's branch brought up to main, which changes the line the feature wrote. Main is then that merge."""
        fix = self.commit(self.main, "page.css", b"table { overflow: scroll }\n")
        mend = self.merged_into(self.main, fix)
        self.landed.append(merged(42, "agent/27-scroll-the-table", mend, at="20:00:00"))
        self.main = self.main_is(mend)
        return mend

    def checkouts(self) -> int:
        return shell.git("worktree", "list", "--porcelain").count("worktree ")

    def test_with_a_feature_and_its_mend_both_standing_a_revert_of_both_holds(self):
        mend = self.mended()
        head = self.revert(self.main, mend, self.merge)
        self.assertEqual(shell.git("ls-tree", "--name-only", head, "page.css"), "")
        holds, what = ship.reverts(27, self.main, head)
        self.assertTrue(holds, what)
        self.assertEqual(self.checkouts(), 1)

    def test_with_a_feature_and_its_mend_both_standing_a_revert_of_the_mend_alone_does_not_hold(self):
        mend = self.mended()
        head = self.revert(self.main, mend)
        self.assertEqual(shell.git("show", f"{head}:page.css"), "table { overflow: auto }")
        holds, what = ship.reverts(27, self.main, head)
        self.assertFalse(holds, what)
        self.assertIn("holds something other than the revert", what)

    def test_a_merge_that_an_earlier_revert_undid_is_not_reverted_again_when_the_feature_landed_a_second_time(self):
        # The first merge was reverted, and the revert merged. Another change has since brought the rule that
        # the first merge had brought, so reverting that merge a second time would take the rule out again.
        undone = self.merged_into(self.main, self.revert(self.main))
        self.landed.append(merged(41, "agent/27-revert", undone, at="20:00:00"))
        self.main = self.main_is(self.commit(undone, "page.css", b"table { overflow: auto }\n"))
        second = self.merged_into(self.main, self.commit(self.main, "detail.css", b"td { white-space: normal }\n"))
        self.landed.append(merged(43, "agent/27-scroll-the-table", second, at="21:00:00"))
        self.main = self.main_is(second)
        head = self.revert(self.main, second)
        holds, what = ship.reverts(27, self.main, head)
        self.assertTrue(holds, what)
        both = self.revert(self.main, second, self.merge)
        self.assertEqual(shell.git("ls-tree", "--name-only", both, "page.css"), "")
        holds, what = ship.reverts(27, self.main, both)
        self.assertFalse(holds, what)

    def test_the_revert_of_the_merge_holds_though_it_takes_from_the_owners_tests_the_lines_the_feature_added(self):
        head = self.revert(self.main)
        self.assertEqual(shell.git("diff", "--numstat", self.main, head, "--", "owner_tests/")[:3], "0\t1")
        holds, what = ship.reverts(27, self.main, head)
        self.assertTrue(holds, what)
        self.assertEqual(self.checkouts(), 1)

    def test_a_revert_made_before_main_moved_and_then_brought_up_to_main_still_holds(self):
        head = self.revert(self.main)
        self.main = self.main_is(self.commit(self.main, "board.txt", b"a board\nanother board day\nand one more\n"))
        shell.git("checkout", "--quiet", "--detach", head)
        shell.git("merge", "--quiet", "--no-edit", "origin/main")
        holds, what = ship.reverts(27, self.main, shell.git("rev-parse", "HEAD"))
        self.assertTrue(holds, what)

    def test_a_revert_with_one_more_change_in_it_does_not_hold(self):
        head = self.commit(self.revert(self.main), ".github/workflows/deploy.yml", b"on: push\n")
        holds, what = ship.reverts(27, self.main, head)
        self.assertFalse(holds, what)
        self.assertIn("holds something other than the revert", what)

    def test_a_branch_that_reverts_nothing_does_not_hold(self):
        head = self.commit(self.main, "page.css", b"table { overflow: hidden }\n")
        self.assertFalse(ship.reverts(27, self.main, head)[0])

    def test_a_merge_that_does_not_revert_on_the_head_of_main_does_not_hold_and_no_worktree_is_left_behind(self):
        self.main = self.main_is(self.commit(self.main, "page.css", b"table { overflow: scroll }\n"))
        holds, what = ship.reverts(27, self.main, self.main)
        self.assertFalse(holds, what)
        self.assertIn("cannot be made", what)
        self.assertEqual(self.checkouts(), 1)


if __name__ == "__main__":
    unittest.main()
