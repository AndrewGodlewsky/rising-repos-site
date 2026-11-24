"""`revert` puts the site back: it reverts each merge of a feature that stands, on a branch made from main, in a
worktree of its own, and opens the pull request that `ship --revert` then merges.

No test reaches GitHub, pushes, or makes a worktree. `sitework.shell.run` is replaced by a stand-in that answers
each command from what the test gives it, in the shapes `gh` and `git` answer in, and keeps each command it was
given with the folder it was run in.
"""

import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest import mock

from sitework import revert, shell

MERGE = "e" * 40
MEND = "f" * 40
"""The commit that merged the feature, and the commit that merged its mend, for a test that has one."""
TITLE = "Stop clipping the table on phones"
CREATE = f"gh pr create --base main --head agent/27-revert --title Revert #27: {TITLE} --body Refs #27"


class Shell:
    """Stands in for `sitework.shell.run`. A command is answered by the answer whose words it begins with, the
    longest of them when several do, and a command with no answer fails the test. An answer that is not text is
    given as the JSON `gh` would print, and one that is an error is raised."""

    def __init__(self, answers: dict):
        self.answers = answers
        self.ran = []
        self.cwd = {}

    def __call__(self, *command, cwd=None, check=True, stdin=None):
        line = " ".join(command)
        self.ran.append(line)
        self.cwd[line] = cwd
        starts = [start for start in self.answers if line.startswith(start)]
        if not starts:
            raise AssertionError(f"the test gave no answer for: {line}")
        answer = self.answers[max(starts, key=len)]
        if isinstance(answer, Exception):
            raise answer
        return answer if isinstance(answer, str) else json.dumps(answer)

    def first(self, start: str) -> str:
        """The first command that was run and begins with these words."""
        return next(line for line in self.ran if line.startswith(start))

    def count(self, start: str) -> int:
        return len([line for line in self.ran if line.startswith(start)])


def pull(number: int, branch: str, merge: str, merged: str) -> dict:
    """A merged pull request, as `gh pr list` gives one."""
    return {
        "number": number,
        "state": "MERGED",
        "headRefName": branch,
        "headRefOid": f"{number:040x}",
        "isCrossRepository": False,
        "mergeCommit": {"oid": merge},
        "mergedAt": merged,
    }


class Revert(unittest.TestCase):
    def setUp(self):
        self.answers = {
            "gh pr list --state merged": [pull(40, "agent/27-stop-clipping", MERGE, "2026-11-22T12:00:00Z")],
            "gh issue view 27": {
                "author": {"login": "the-owner"},
                "labels": [{"name": "site-idea"}, {"name": "approved"}, {"name": "in-progress"}],
                "number": 27,
                "state": "OPEN",
                "title": TITLE,
                "url": "https://github.com/the-owner/the-site/issues/27",
            },
            "git fetch origin": "",
            "git worktree add": "",
            "git revert": "",
            "git push origin agent/27-revert": "",
            "git worktree remove": "",
            "gh pr create": "https://github.com/the-owner/the-site/pull/45",
        }
        self.shell = Shell(self.answers)
        self.enterContext(mock.patch.object(shell, "run", self.shell))

    def run_command(self, *arguments: str) -> tuple[int, str]:
        """Run `revert`, and give its exit code and what it printed."""
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            code = revert.main("revert", list(arguments))
        return code, printed.getvalue()

    def worktree(self) -> Path:
        """The folder the temporary worktree was made in."""
        return Path(self.shell.first("git worktree add").split(" ")[-2])

    def test_it_reverts_the_merge_on_a_branch_made_from_main_pushes_it_and_opens_the_pull_request(self):
        code, _ = self.run_command("27")
        self.assertEqual(code, 0)
        tree = self.worktree()
        self.assertEqual(
            self.shell.ran[2:],
            [
                "git fetch origin",
                f"git worktree add --no-track -B agent/27-revert {tree} origin/main",
                f"git revert -m 1 --no-edit {MERGE}",
                "git push origin agent/27-revert",
                f"git worktree remove --force {tree}",
                CREATE,
            ],
        )

    def test_it_prints_the_number_of_the_pull_request_it_opened(self):
        self.assertEqual(self.run_command("27"), (0, "45\n"))

    def test_the_revert_is_made_in_the_temporary_worktree_and_the_agents_own_tree_is_left_as_it_is(self):
        self.run_command("27")
        tree = self.worktree()
        self.assertEqual(self.shell.cwd[f"git revert -m 1 --no-edit {MERGE}"], tree)
        self.assertNotIn(shell.ROOT, [tree, *tree.parents])
        self.assertFalse(tree.parent.exists(), "the temporary folder was left behind")

    def test_a_feature_and_its_mend_are_both_reverted_the_newest_first_on_the_one_branch_of_the_one_pull_request(self):
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping", MERGE, "2026-11-22T12:00:00Z"),
            pull(42, "agent/27-stop-clipping", MEND, "2026-11-22T13:00:00Z"),
        ]
        code, printed = self.run_command("27")
        self.assertEqual((code, printed), (0, "45\n"))
        tree = self.worktree()
        self.assertEqual(
            self.shell.ran[2:],
            [
                "git fetch origin",
                f"git worktree add --no-track -B agent/27-revert {tree} origin/main",
                f"git revert -m 1 --no-edit {MEND}",
                f"git revert -m 1 --no-edit {MERGE}",
                "git push origin agent/27-revert",
                f"git worktree remove --force {tree}",
                CREATE,
            ],
        )
        self.assertEqual({self.shell.cwd[line] for line in self.shell.ran if line.startswith("git revert")}, {tree})

    def test_a_merge_that_a_revert_already_undid_is_not_reverted_again(self):
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping", MERGE, "2026-11-22T12:00:00Z"),
            pull(41, "agent/27-revert", "1" * 40, "2026-11-22T13:00:00Z"),
            pull(43, "agent/27-stop-clipping", MEND, "2026-11-22T14:00:00Z"),
        ]
        self.run_command("27")
        self.assertEqual(
            [line for line in self.shell.ran if line.startswith("git revert")], [f"git revert -m 1 --no-edit {MEND}"]
        )

    def test_a_feature_whose_every_merge_was_reverted_exits_1_says_so_and_pushes_nothing(self):
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping", MERGE, "2026-11-22T12:00:00Z"),
            pull(42, "agent/27-stop-clipping", MEND, "2026-11-22T13:00:00Z"),
            pull(43, "agent/27-revert", "1" * 40, "2026-11-22T14:00:00Z"),
        ]
        code, printed = self.run_command("27")
        self.assertEqual(code, 1)
        for part in ("#27", "nothing to revert"):
            self.assertIn(part, printed)
        self.assertEqual(self.shell.count("git") + self.shell.count("gh pr create"), 0)

    def test_a_mend_that_does_not_revert_exits_1_before_the_feature_is_reverted_and_pushes_nothing(self):
        self.answers[f"git revert -m 1 --no-edit {MEND}"] = shell.Failed("git revert: exit 1\nCONFLICT (content)")
        self.answers["gh pr list --state merged"] = [
            pull(40, "agent/27-stop-clipping", MERGE, "2026-11-22T12:00:00Z"),
            pull(42, "agent/27-stop-clipping", MEND, "2026-11-22T13:00:00Z"),
        ]
        code, printed = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertIn("CONFLICT", printed)
        self.assertEqual(self.shell.count(f"git revert -m 1 --no-edit {MERGE}"), 0)
        self.assertEqual(self.shell.count("git worktree remove --force"), 1)
        self.assertEqual(self.shell.count("git push") + self.shell.count("gh pr create"), 0)

    def test_a_revert_that_does_not_apply_exits_1_removes_the_worktree_and_opens_nothing(self):
        self.answers["git revert"] = shell.Failed("git revert: exit 1\nCONFLICT (content): Merge conflict in site.css")
        code, printed = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertIn("CONFLICT", printed)
        self.assertEqual(self.shell.count("git worktree remove --force"), 1)
        self.assertEqual(self.shell.count("git push") + self.shell.count("gh pr create"), 0)

    def test_a_push_that_is_refused_exits_1_removes_the_worktree_and_opens_nothing(self):
        self.answers["git push origin agent/27-revert"] = shell.Failed("git push: exit 1\n! [rejected]")
        code, _ = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertEqual(self.shell.count("git worktree remove --force"), 1)
        self.assertEqual(self.shell.count("gh pr create"), 0)

    def test_an_issue_with_no_merged_pull_request_exits_1_and_reverts_nothing(self):
        self.answers["gh pr list --state merged"] = [pull(41, "agent/27-revert", "1" * 40, "2026-11-22T13:00:00Z")]
        code, printed = self.run_command("27")
        self.assertEqual(code, 1)
        self.assertIn("#27", printed)
        self.assertEqual(self.shell.count("git"), 0)
        self.assertEqual(self.shell.count("gh pr create"), 0)


if __name__ == "__main__":
    unittest.main()
