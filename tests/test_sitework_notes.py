"""The push of a run's notes to main.

Every push here goes to a bare repository in a temporary folder, which stands for `origin`. The repository the
script works in is a clone of it, in the same folder. `sitework.shell.run` is replaced by one that refuses any
command but git, and any git command outside that folder, so that no test can reach the real `origin` or GitHub.
The look at the deploy's run, and the wait between two looks, are replaced in every test.
"""

import codecs
import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sitework import confirm, digest, notes, shell

REAL_RUN = shell.run
WRITE_NOTES = notes.write_notes
ROW = "| #7 | 1,200 | 300 | 40 | 1,600 | no | 5.5 |"
DIGEST = "\n".join(
    ["# Digest of the run on #7", "", "## Tools", "", "Read 2.", "", digest.FIGURES, "", digest.FIGURES_HEADING]
    + [digest.FIGURES_RULE, ROW, "", "A figure in tokens is the sum of the four kinds."]
)
NOTES = "1. The plan was read nine times. Read it once, and keep the lines that matter.\n2. Nothing else."
DONE = {"status": "completed", "conclusion": "success", "databaseId": 1, "createdAt": "2026-11-02T10:00:00Z"}
GOING = {"status": "in_progress", "conclusion": None, "databaseId": 2, "createdAt": "2026-11-02T10:05:00Z"}


def ended(conclusion: str, at: str = "2026-11-02T10:00:00Z") -> dict:
    """A run of the deploy workflow that has ended, as `gh run list` gives one."""
    return {"status": "completed", "conclusion": conclusion, "databaseId": 3, "createdAt": at}


class TheFigures(unittest.TestCase):
    def test_the_row_is_the_one_under_the_heading_of_the_figures(self):
        self.assertEqual(notes.figures_row(DIGEST, 7), ROW)

    def test_a_digest_without_its_figures_is_refused(self):
        for text in ("# Digest of the run on #7\n\nRead 2.", DIGEST.replace(digest.FIGURES_HEADING, "| Issue |")):
            with self.assertRaises(notes.Refused):
                notes.figures_row(text, 7)

    def test_a_digest_made_for_another_issue_or_for_none_is_refused(self):
        for cell in ("#8", "-", "#70"):
            with self.assertRaises(notes.Refused) as refused:
                notes.figures_row(DIGEST.replace("| #7 |", f"| {cell} |"), 7)
            self.assertIn("--issue 7", str(refused.exception))


class TheTable(unittest.TestCase):
    def test_the_first_row_makes_the_table_under_its_heading_row(self):
        made = notes.with_row(None, ROW)
        self.assertTrue(made.startswith("# "))
        self.assertTrue(made.endswith(f"\n{digest.FIGURES_HEADING}\n{digest.FIGURES_RULE}\n{ROW}\n"))

    def test_a_row_is_added_under_the_rows_that_are_there(self):
        earlier = "| #3 | 9 | 9 | 9 | 27 | yes | - |"
        made = notes.with_row(notes.with_row(None, earlier), ROW)
        self.assertTrue(made.endswith(f"\n{digest.FIGURES_RULE}\n{earlier}\n{ROW}\n"))
        self.assertEqual(made.count(digest.FIGURES_HEADING), 1)

    def test_a_row_goes_into_the_table_and_not_under_words_written_after_it(self):
        table = notes.with_row(None, "| #3 | 9 | 9 | 9 | 27 | yes | - |")
        made = notes.with_row(table + "\nA word on the figures.\n", ROW)
        self.assertTrue(made.endswith(f"| #3 | 9 | 9 | 9 | 27 | yes | - |\n{ROW}\n\nA word on the figures.\n"))

    def test_a_row_that_is_already_there_is_not_added_twice(self):
        once = notes.with_row(None, ROW)
        self.assertEqual(notes.with_row(once, ROW), once)


class TheGuard(unittest.TestCase):
    def test_only_a_path_in_the_notes_folder_is_let_through(self):
        inside = ["docs/workflow-notes/runs/7.md", "docs/workflow-notes/features.md"]
        stray = [
            "sitebuild/page.py",
            "docs/workflow-notes.md",
            "docs/workflow/README.md",
            "site-data/boards/index.json",
        ]
        self.assertEqual(notes.outside(inside + stray), stray)
        self.assertEqual(notes.outside(inside), [])


class TheFiles(unittest.TestCase):
    def test_a_file_a_shell_wrote_in_another_encoding_is_read_as_its_words(self):
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        words = "One line — and a second.\nTwo.\n"
        shapes = {
            "utf-8": words.encode("utf-8"),
            "utf-8 with a mark": codecs.BOM_UTF8 + words.encode("utf-8"),
            "utf-16": codecs.BOM_UTF16_LE + words.replace("\n", "\r\n").encode("utf-16-le"),
        }
        for name, written in shapes.items():
            (folder / name).write_bytes(written)
            self.assertEqual(notes.read_text(folder / name), words, name)


def git(*arguments: str, cwd: Path) -> str:
    """Run git for a test's own use, and give what it printed. The script under test never comes through here."""
    done = subprocess.run(["git", *arguments], cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=60)
    if done.returncode != 0:
        raise AssertionError(f"git {' '.join(arguments)}: {done.stderr}")
    return done.stdout.strip()


def commit(tree: Path, files: dict[str, str], subject: str) -> str:
    for name, text in files.items():
        (tree / name).parent.mkdir(parents=True, exist_ok=True)
        (tree / name).write_text(text, encoding="utf-8", newline="\n")
    git("add", "--all", cwd=tree)
    git("commit", "--quiet", "--message", subject, cwd=tree)
    return git("rev-parse", "HEAD", cwd=tree)


class PushTest(unittest.TestCase):
    """A bare repository as `origin`, with one commit on main, and a clone of it as the agent's own checkout."""

    @classmethod
    def setUpClass(cls):
        """Make the repositories once. Each test works in a copy of them, which costs less than making them."""
        cls.template = Path(cls.enterClassContext(tempfile.TemporaryDirectory())).resolve()
        origin = cls.template / "origin.git"
        git("init", "--quiet", "--bare", "--initial-branch=main", str(origin), cwd=cls.template)
        for name in ("checkout", "elsewhere"):
            git("clone", "--quiet", origin.as_posix(), name, cwd=cls.template)
            for key, value in (("user.name", "A test"), ("user.email", "test@example.invalid")):
                git("config", key, value, cwd=cls.template / name)
            git("config", "commit.gpgsign", "false", cwd=cls.template / name)
        checkout = cls.template / "checkout"
        cls.first = commit(checkout, {"sitebuild/page.py": "page = 1\n"}, "Add a page")
        git("push", "--quiet", "origin", "HEAD:main", cwd=checkout)

    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        shutil.copytree(self.template, self.folder, dirs_exist_ok=True)
        self.origin, self.checkout, self.elsewhere = (
            self.folder / name for name in ("origin.git", "checkout", "elsewhere")
        )
        for clone in (self.checkout, self.elsewhere):
            config = clone / ".git" / "config"
            ours = config.read_text(encoding="utf-8").replace(self.template.as_posix(), self.folder.as_posix())
            config.write_text(ours, encoding="utf-8")
        self.assertEqual(git("remote", "get-url", "origin", cwd=self.checkout), self.origin.as_posix())
        self.digest = self.folder / "digest.md"
        self.digest.write_text(DIGEST + "\n", encoding="utf-8")
        self.notes = self.folder / "notes.md"
        self.notes.write_text(NOTES + "\n", encoding="utf-8")

        self.before_push = []
        self.pushes = 0
        self.enterContext(mock.patch.object(tempfile, "tempdir", str(self.folder)))
        self.enterContext(mock.patch.object(shell, "ROOT", self.checkout))
        self.enterContext(mock.patch.object(shell, "run", self.run_inside))
        self.wait = self.enterContext(mock.patch.object(notes, "wait"))
        self.runs = self.enterContext(mock.patch.object(notes, "deploy_runs", return_value=[DONE]))

    def git(self, *arguments: str, cwd: Path) -> str:
        return git(*arguments, cwd=cwd)

    def commit(self, tree: Path, files: dict[str, str], subject: str) -> str:
        return commit(tree, files, subject)

    def push_from_elsewhere(self, files: dict[str, str], subject: str = "Publish board day 2026-11-03") -> str:
        """Another push reaches main, as the daily publish or another run's notes do."""
        self.git("pull", "--quiet", "origin", "main", cwd=self.elsewhere)
        made = self.commit(self.elsewhere, files, subject)
        self.git("push", "--quiet", "origin", "HEAD:main", cwd=self.elsewhere)
        return made

    def run_inside(self, *command: str, cwd: Path | None = None, **more) -> str:
        """`shell.run`, for git alone and inside the temporary folder alone."""
        where = Path(cwd or shell.ROOT).resolve()
        if command[0] != "git" or not where.is_relative_to(self.folder):
            raise AssertionError(f"a test ran {command[:3]} in {where}")
        if command[:2] == ("git", "push"):
            self.pushes += 1
            for step in self.before_push[:1]:
                self.before_push.remove(step)
                step()
        return REAL_RUN(*command, cwd=cwd, **more)

    def main(self, *arguments: str) -> tuple[int, str, str]:
        printed, complained = io.StringIO(), io.StringIO()
        given = arguments or ("7", "--digest", str(self.digest), "--notes", str(self.notes))
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(complained):
            code = notes.main("notes", list(given))
        return code, printed.getvalue(), complained.getvalue()

    def head(self) -> str:
        return self.git("rev-parse", "main", cwd=self.origin)

    def on_main(self, name: str) -> str:
        return self.git("show", f"main:{name}", cwd=self.origin)

    def touched(self, commit: str = "main") -> list[str]:
        return self.git("show", "--name-only", "--format=", commit, cwd=self.origin).splitlines()


class ThePush(PushTest):
    def test_the_notes_and_the_row_reach_main_in_one_commit_that_holds_nothing_else(self):
        code, printed, complained = self.main()
        self.assertEqual(code, 0, complained)
        self.assertEqual(
            self.git("log", "--format=%s", "main", cwd=self.origin).splitlines()[0], "Add the notes of the run on #7"
        )
        self.assertEqual(self.git("rev-parse", "main~1", cwd=self.origin), self.first)
        self.assertEqual(self.touched(), ["docs/workflow-notes/features.md", "docs/workflow-notes/runs/7.md"])
        self.assertIn(self.head()[:7], printed)

    def test_the_runs_file_is_a_heading_then_the_notes_then_the_digest(self):
        self.main()
        written = self.on_main("docs/workflow-notes/runs/7.md")
        self.assertTrue(written.startswith("# The run on #7\n"))
        self.assertLess(written.index(NOTES), written.index("Digest of the run on #7"))
        self.assertIn(ROW, written)
        self.assertEqual([line for line in written.splitlines() if line.startswith("# ")], ["# The run on #7"])

    def test_the_first_run_makes_the_table_of_every_feature_and_the_next_adds_its_row(self):
        self.main()
        self.assertIn(
            f"{digest.FIGURES_HEADING}\n{digest.FIGURES_RULE}\n{ROW}", self.on_main("docs/workflow-notes/features.md")
        )
        later = ROW.replace("#7", "#9")
        self.digest.write_text(DIGEST.replace("#7", "#9"), encoding="utf-8")
        code, _, complained = self.main("9", "--digest", str(self.digest), "--notes", str(self.notes))
        self.assertEqual(code, 0, complained)
        self.assertTrue(self.on_main("docs/workflow-notes/features.md").endswith(f"{ROW}\n{later}"))
        self.assertEqual(self.touched(), ["docs/workflow-notes/features.md", "docs/workflow-notes/runs/9.md"])

    def test_the_agents_own_tree_is_left_as_it_is(self):
        self.git("checkout", "--quiet", "-b", "agent/7-a-feature", cwd=self.checkout)
        mine = self.commit(self.checkout, {"sitebuild/page.py": "page = 2\n"}, "Change the page")
        (self.checkout / "half-done.txt").write_text("not committed\n", encoding="utf-8")
        self.assertEqual(self.main()[0], 0)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.checkout), mine)
        self.assertEqual(self.git("branch", "--show-current", cwd=self.checkout), "agent/7-a-feature")
        self.assertEqual(self.git("status", "--porcelain", cwd=self.checkout), "?? half-done.txt")
        self.assertFalse((self.checkout / "docs").exists())
        self.assertEqual(self.on_main("sitebuild/page.py"), "page = 1")

    def test_the_temporary_worktree_is_removed_after_a_push_and_after_a_refusal(self):
        self.assertEqual(self.main()[0], 0)
        with mock.patch.object(notes, "write_notes", self.write_a_page_too):
            self.assertEqual(self.main()[0], 1)
        self.assertEqual(len(self.git("worktree", "list", cwd=self.checkout).splitlines()), 1)
        self.assertEqual(
            sorted(path.name for path in self.folder.iterdir() if path.is_dir()),
            ["checkout", "elsewhere", "origin.git"],
        )

    def write_a_page_too(self, tree: Path, *given) -> None:
        """What the script's own writing would be if a change to it ever reached past the notes' folder."""
        WRITE_NOTES(tree, *given)
        (tree / "sitebuild" / "page.py").write_text("page = 3\n", encoding="utf-8")

    def test_a_commit_that_touches_a_page_is_refused_and_nothing_is_pushed(self):
        with mock.patch.object(notes, "write_notes", self.write_a_page_too):
            code, printed, complained = self.main()
        self.assertEqual(code, 1)
        self.assertIn("sitebuild/page.py", complained)
        self.assertEqual(self.head(), self.first)
        self.assertEqual(self.pushes, 0)

    def test_the_commit_is_made_on_the_newest_main_and_not_on_what_the_checkout_last_saw(self):
        newer = self.push_from_elsewhere({"site-data/day.json": "{}\n"})
        self.assertEqual(self.main()[0], 0)
        self.assertEqual(self.git("rev-parse", "main~1", cwd=self.origin), newer)
        self.assertEqual(self.pushes, 1)

    def test_when_main_moved_before_the_push_the_commit_is_made_again_on_the_new_head(self):
        other = "| #5 | 1 | 1 | 1 | 3 | no | 0.5 |"
        moved = []
        self.before_push.append(
            lambda: moved.append(
                self.push_from_elsewhere(
                    {"docs/workflow-notes/features.md": notes.with_row(None, other)}, "Add the notes of the run on #5"
                )
            )
        )
        code, _, complained = self.main()
        self.assertEqual(code, 0, complained)
        self.assertEqual(self.pushes, 2)
        self.assertEqual(self.git("rev-parse", "main~1", cwd=self.origin), moved[0])
        self.assertTrue(self.on_main("docs/workflow-notes/features.md").endswith(f"{other}\n{ROW}"))
        self.assertEqual(self.touched(), ["docs/workflow-notes/features.md", "docs/workflow-notes/runs/7.md"])

    def test_when_main_moves_a_second_time_it_gives_up_and_pushes_nothing(self):
        moved = []
        for number in (1, 2):
            self.before_push.append(
                lambda n=number: moved.append(self.push_from_elsewhere({f"site-data/{n}.json": "{}\n"}))
            )
        code, _, complained = self.main()
        self.assertEqual(code, 1)
        self.assertEqual(self.pushes, 2)
        self.assertEqual(self.head(), moved[1])
        self.assertIn("moved", complained)

    def test_a_push_refused_while_main_stood_still_is_reported_and_not_tried_again(self):
        hook = self.origin / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\necho 'main is protected' >&2\nexit 1\n", encoding="utf-8", newline="\n")
        hook.chmod(0o755)
        code, _, complained = self.main()
        self.assertEqual(code, 1)
        self.assertEqual(self.pushes, 1)
        self.assertEqual(self.head(), self.first)
        self.assertIn("main is protected", complained)

    def test_notes_that_are_already_on_main_are_not_pushed_again(self):
        self.assertEqual(self.main()[0], 0)
        pushed = self.head()
        code, printed, _ = self.main()
        self.assertEqual((code, self.head(), self.pushes), (0, pushed, 1))
        self.assertIn("already on main", printed)

    def test_a_digest_without_this_issues_figures_is_refused_before_anything_is_fetched(self):
        self.digest.write_text("# Digest of a run\n", encoding="utf-8")
        with mock.patch.object(shell, "run", side_effect=AssertionError("a command was run")):
            code, _, complained = self.main()
        self.assertEqual(code, 1)
        self.assertIn("Figures", complained)


class TheDeploy(PushTest):
    """A notes commit starts no deploy, so it must not land on a commit whose own deploy has yet to upload."""

    def test_it_waits_while_the_deploy_is_in_progress_and_pushes_once_it_has_ended(self):
        heads = []

        def look(commit: str) -> list[dict]:
            heads.append(self.head())
            return [GOING] if len(heads) == 1 else [DONE]

        self.runs.side_effect = look
        code, _, complained = self.main()
        self.assertEqual(code, 0, complained)
        self.assertEqual(heads, [self.first, self.first])
        self.wait.assert_called_once_with(20)
        self.assertNotEqual(self.head(), self.first)

    def test_a_run_github_has_not_made_yet_is_waited_for(self):
        self.runs.side_effect = [[], [], [DONE]]
        self.assertEqual(self.main()[0], 0)
        self.assertEqual(self.wait.call_count, 2)

    def test_every_run_of_the_commit_has_to_have_ended(self):
        self.runs.side_effect = [[DONE, GOING], [DONE, DONE]]
        self.assertEqual(self.main()[0], 0)
        self.assertEqual(self.wait.call_count, 1)

    def test_a_deploy_that_never_ends_is_given_up_on_after_twenty_minutes_and_nothing_is_pushed(self):
        self.runs.return_value = [GOING]
        code, _, complained = self.main()
        self.assertEqual(code, 1)
        self.assertEqual(sum(call.args[0] for call in self.wait.call_args_list), 20 * 60)
        self.assertEqual(self.runs.call_count, 61)
        self.assertEqual((self.head(), self.pushes), (self.first, 0))
        self.assertIn(self.first[:7], complained)

    def test_a_deploy_that_ended_any_way_but_success_is_refused_in_one_line_and_nothing_is_pushed(self):
        for conclusion in ("failure", "cancelled", "timed_out"):
            self.runs.return_value = [ended(conclusion)]
            code, printed, complained = self.main()
            self.assertEqual((code, printed), (1, ""), conclusion)
            self.assertEqual((self.head(), self.pushes), (self.first, 0), conclusion)
            self.assertEqual(len(complained.strip().splitlines()), 1, complained)
            for word in (self.first[:7], conclusion, "not live", "re-run"):
                self.assertIn(word, complained)
        self.wait.assert_not_called()

    def test_of_several_runs_of_the_commit_the_newest_is_the_one_whose_end_counts(self):
        failed_first = [ended("success", at="2026-11-02T11:00:00Z"), ended("failure", at="2026-11-02T10:00:00Z")]
        failed_last = [ended("success", at="2026-11-02T10:00:00Z"), ended("failure", at="2026-11-02T11:00:00Z")]
        self.runs.return_value = failed_last
        self.assertEqual(self.main()[0], 1)
        self.assertEqual((self.head(), self.pushes), (self.first, 0))
        self.runs.return_value = failed_first
        self.assertEqual(self.main()[0], 0)
        self.assertEqual(self.pushes, 1)

    def test_the_deploy_it_asks_about_is_that_of_the_newest_commit_that_changes_more_than_the_notes(self):
        self.push_from_elsewhere({"docs/workflow-notes/runs/5.md": "notes\n"}, "Add the notes of the run on #5")
        self.assertEqual(self.main()[0], 0)
        self.runs.assert_called_once_with(self.first)

    def test_the_commit_whose_deploy_it_waits_for_is_the_one_confirm_finds_beneath_the_head_of_main(self):
        with mock.patch.object(confirm, "deploy_commit", return_value="c" * 40) as found:
            self.assertEqual(self.main()[0], 0)
        found.assert_called_once_with(self.first)
        self.runs.assert_called_once_with("c" * 40)

    def test_the_commit_confirm_follows_beneath_a_commit_of_the_notes_is_the_newest_that_changes_more(self):
        page = self.push_from_elsewhere({"sitebuild/page.py": "page = 4\n"}, "Change the page")
        told = self.push_from_elsewhere({"docs/workflow-notes/runs/5.md": "notes\n"}, "Add the notes of the run on #5")
        self.git("fetch", "--quiet", "origin", "main", cwd=self.checkout)
        self.assertEqual(self.git("rev-parse", "origin/main", cwd=self.checkout), told)
        self.assertEqual(confirm.deploy_commit("origin/main"), page)

    def test_a_merge_is_asked_about_by_the_merges_own_commit_which_is_the_one_that_was_pushed(self):
        self.git("pull", "--quiet", "origin", "main", cwd=self.elsewhere)
        self.git("checkout", "--quiet", "-b", "agent/5-a-feature", cwd=self.elsewhere)
        self.commit(self.elsewhere, {"sitebuild/page.py": "page = 5\n"}, "Change the page")
        self.git("checkout", "--quiet", "main", cwd=self.elsewhere)
        self.git("merge", "--quiet", "--no-ff", "--message", "Merge #5", "agent/5-a-feature", cwd=self.elsewhere)
        merge = self.git("rev-parse", "HEAD", cwd=self.elsewhere)
        self.git("push", "--quiet", "origin", "HEAD:main", cwd=self.elsewhere)
        self.assertEqual(self.main()[0], 0)
        self.runs.assert_called_once_with(merge)

    def test_when_main_moved_it_waits_for_the_deploy_of_the_commit_that_moved_it(self):
        moved = []
        self.before_push.append(lambda: moved.append(self.push_from_elsewhere({"site-data/day.json": "{}\n"})))
        self.assertEqual(self.main()[0], 0)
        self.assertEqual([call.args[0] for call in self.runs.call_args_list], [self.first, moved[0]])


class TheLook(unittest.TestCase):
    def test_the_run_is_asked_of_github_by_its_workflow_its_branch_and_its_commit(self):
        with mock.patch.object(shell, "run", return_value='[{"status": "queued", "conclusion": null}]') as asked:
            self.assertEqual(notes.deploy_runs("abc123"), [{"status": "queued", "conclusion": None}])
        command = asked.call_args.args
        self.assertEqual(command[:3], ("gh", "run", "list"))
        for option, value in (("--workflow", "deploy.yml"), ("--branch", "main"), ("--commit", "abc123")):
            self.assertEqual(command[command.index(option) + 1], value)

    def test_only_a_run_for_a_push_is_asked_for_and_never_one_for_a_pull_request_from_a_forks_main(self):
        with mock.patch.object(shell, "run", return_value="[]") as asked:
            self.assertEqual(notes.deploy_runs("abc123"), [])
        command = asked.call_args.args
        self.assertIn("--event", command)
        self.assertEqual(command[command.index("--event") + 1], "push")


if __name__ == "__main__":
    unittest.main()
