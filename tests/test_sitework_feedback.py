"""`feedback` files what a run taught as issues that carry a label of their own, adds a finding that was seen
again to the issue it is filed in, and lists the issues that are open. Nothing a run taught is pushed into the
repository.

No test reaches GitHub. `sitework.shell.run` is replaced by a stand-in that answers each command from what the
test gives it, in the shapes `gh` answers in, and keeps each command it was given with what it was handed to read.
"""

import codecs
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sitework import feedback, rules, shell
from sitework.__main__ import COMMANDS

LABEL = "workflow feedback"
FILED = "https://github.com/the-owner/the-site/issues/52"
"""The address `gh issue create` prints for the issue it opened."""
ADDED = "https://github.com/the-owner/the-site/issues/44#issuecomment-7099"
"""The address `gh issue comment` prints for the comment it posted."""
WORDS = "The plan was read nine times — read it once, and keep the lines that matter.\n\nNothing else."
DIGEST = "# Digest of the run on #27\n\nMade from 1 record.\n\n## Figures\n\n| Issue |\n| --- |\n| #27 |"

LIST = "gh issue list"
CREATE = "gh issue create"
VIEW = "gh issue view 44"
COMMENT = "gh issue comment 44"


class Shell:
    """Stands in for `sitework.shell.run`. A command is answered by the answer whose words it begins with, the
    longest of them when several do, and a command with no answer fails the test. An answer that is not text is
    given as the JSON `gh` would print, and one that is an error is raised."""

    def __init__(self, answers: dict):
        self.answers = answers
        self.ran = []
        self.words = []
        self.stdin = {}

    def __call__(self, *command, cwd=None, check=True, stdin=None):
        line = " ".join(command)
        self.ran.append(line)
        self.words.append(command)
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
        return [line for line in self.ran if not line.startswith((LIST, "gh issue view"))]

    def given(self, start: str, option: str) -> list[str]:
        """Each value the one command that begins with `start` was given for `option`."""
        (command,) = [words for words in self.words if " ".join(words).startswith(start)]
        return [command[at + 1] for at, word in enumerate(command) if word == option]

    def read(self, start: str) -> str:
        """What the one command that begins with `start` was handed to read."""
        (line,) = [line for line in self.ran if line.startswith(start)]
        return self.stdin[line]


def issue(number: int, *labels: str, state: str = "OPEN") -> dict:
    """An issue, as `gh issue view` gives one."""
    return {
        "author": {"login": "the-owner"},
        "labels": [{"name": label} for label in labels],
        "number": number,
        "state": state,
        "title": "The plan is read more than once",
        "url": f"https://github.com/the-owner/the-site/issues/{number}",
    }


class FeedbackTest(unittest.TestCase):
    """A test with the stand-in in place, one feedback issue open as #44, a file that holds a finding, and a file
    that holds a digest."""

    def setUp(self):
        self.answers = {
            LIST: [{"number": 44, "title": "The plan is read more than once"}],
            CREATE: FILED,
            "gh issue close 52": "",
            VIEW: issue(44, LABEL),
            COMMENT: ADDED,
        }
        self.shell = Shell(self.answers)
        self.enterContext(mock.patch.object(shell, "run", self.shell))
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.file = self.folder / "finding.md"
        self.file.write_text(WORDS + "\n", encoding="utf-8")
        self.digest = self.folder / "digest.md"
        self.digest.write_text(DIGEST + "\n", encoding="utf-8")

    def run_command(self, *arguments: str) -> tuple[int, str, str]:
        """Run `feedback`, and give its exit code, what it printed, and what it complained of."""
        printed, complained = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(complained):
            try:
                code = feedback.main("feedback", list(arguments))
            except SystemExit as refused:  # argparse refuses a line it cannot read by exiting with 2
                code = refused.code
        return code, printed.getvalue(), complained.getvalue()

    def file_it(self, *more: str, title: str = "The plan is read more than once") -> tuple[int, str, str]:
        return self.run_command("file", "--run", "27", "--title", title, "--file", str(self.file), *more)

    def add_it(self, number: int = 44) -> tuple[int, str, str]:
        return self.run_command("add", str(number), "--run", "27", "--file", str(self.file))


class TheLabel(unittest.TestCase):
    def test_a_feedback_issue_carries_a_label_of_its_own(self):
        self.assertEqual(rules.FEEDBACK, LABEL)
        others = (rules.IDEA, rules.APPROVED, rules.IN_PROGRESS, rules.NEEDS_OWNER, rules.BLOCKED_ON_DATA)
        self.assertNotIn(rules.FEEDBACK, others)

    def test_the_rules_keep_no_folder_of_the_repository_for_what_a_run_taught(self):
        self.assertFalse(hasattr(rules, "NOTES"))
        patterns = [pattern for patterns in rules.GUARDED.values() for pattern in patterns]
        self.assertEqual([pattern for pattern in patterns if "workflow-notes" in pattern], [])


class TheCommand(FeedbackTest):
    def test_feedback_is_one_of_the_workflows_commands_and_notes_is_one_no_longer(self):
        self.assertEqual(COMMANDS["feedback"][0], "sitework.feedback")
        self.assertNotIn("notes", COMMANDS)
        self.assertIsNone(importlib.util.find_spec("sitework.notes"))

    def test_a_line_that_names_none_of_the_three_forms_is_refused(self):
        for arguments in ([], ["push"], ["notes", "27"]):
            code, _, complained = self.run_command(*arguments)
            self.assertEqual(code, 2, arguments)
            for form in ("list", "file", "add"):
                self.assertIn(form, complained)
        self.assertEqual(self.shell.ran, [])


class TheList(FeedbackTest):
    def test_each_open_issue_that_carries_the_label_is_printed_with_its_number_and_its_title_oldest_first(self):
        self.answers[LIST] = [
            {"number": 52, "title": "The reviewer ran at a higher effort than its task needed"},
            {"number": 44, "title": "The plan is read more than once"},
            {"number": 47, "title": "The run on #27"},
        ]
        code, printed, _ = self.run_command("list")
        self.assertEqual(code, 0)
        self.assertEqual(
            printed.splitlines(),
            [
                "#44 The plan is read more than once",
                "#47 The run on #27",
                "#52 The reviewer ran at a higher effort than its task needed",
            ],
        )
        self.assertEqual(self.shell.given(LIST, "--label"), [LABEL])
        self.assertEqual(self.shell.given(LIST, "--state"), ["open"])

    def test_it_asks_for_more_than_the_thirty_issues_github_gives_when_it_is_asked_for_no_number(self):
        self.run_command("list")
        (limit,) = self.shell.given(LIST, "--limit")
        self.assertGreater(int(limit), 30)

    def test_with_no_open_issue_it_says_so_in_one_line_and_exits_0(self):
        self.answers[LIST] = []
        code, printed, _ = self.run_command("list")
        self.assertEqual(code, 0)
        self.assertEqual(len(printed.strip().splitlines()), 1, printed)
        self.assertIn(LABEL, printed)
        self.assertNotIn("#", printed)

    def test_listing_reads_and_changes_nothing(self):
        self.run_command("list")
        self.assertEqual(len(self.shell.ran), 1)
        self.assertEqual(self.shell.changes(), [])

    def test_when_github_does_not_give_the_list_it_exits_1_with_what_github_said(self):
        self.answers[LIST] = shell.Failed("gh issue list: exit 1\nHTTP 502: Bad Gateway")
        code, printed, complained = self.run_command("list")
        self.assertEqual((code, printed), (1, ""))
        self.assertIn("HTTP 502: Bad Gateway", complained)


class TheFiling(FeedbackTest):
    def test_a_finding_is_filed_as_a_new_issue_under_its_title_and_the_issues_address_is_printed(self):
        code, printed, _ = self.file_it()
        self.assertEqual((code, printed), (0, FILED + "\n"))
        self.assertEqual(self.shell.given(CREATE, "--title"), ["The plan is read more than once"])
        self.assertEqual(self.shell.changes(), [line for line in self.shell.ran if line.startswith(CREATE)])
        self.assertEqual(len(self.shell.changes()), 1)

    def test_a_filed_issue_carries_the_label_alone_so_that_no_run_picks_it_up_as_a_feature(self):
        # `pickup` takes up only an issue that carries both `site-idea` and `approved`.
        self.file_it()
        self.assertEqual(self.shell.given(CREATE, "--label"), [LABEL])

    def test_the_body_is_the_files_words_and_then_a_last_line_that_names_the_run(self):
        self.file_it()
        self.assertEqual(self.shell.read(CREATE), f"{WORDS}\n\nFrom the run on #27.\n")

    def test_with_a_digest_the_body_holds_it_as_it_was_printed_between_the_words_and_the_last_line(self):
        self.file_it("--digest", str(self.digest))
        self.assertEqual(self.shell.read(CREATE), f"{WORDS}\n\n{DIGEST}\n\nFrom the run on #27.\n")

    def test_the_issue_that_holds_a_runs_digest_is_closed_once_it_is_filed_since_it_has_nothing_to_mend(self):
        code, printed, _ = self.file_it("--digest", str(self.digest))
        self.assertEqual((code, printed), (0, FILED + "\n"))
        self.assertEqual(self.shell.changes()[-1], "gh issue close 52")

    def test_a_finding_and_a_digest_that_a_shell_on_windows_wrote_are_filed_as_their_words(self):
        self.file.write_bytes(codecs.BOM_UTF16_LE + (WORDS + "\n").replace("\n", "\r\n").encode("utf-16-le"))
        self.digest.write_bytes(codecs.BOM_UTF8 + (DIGEST + "\n").replace("\n", "\r\n").encode("utf-8"))
        self.file_it("--digest", str(self.digest))
        self.assertEqual(self.shell.read(CREATE), f"{WORDS}\n\n{DIGEST}\n\nFrom the run on #27.\n")

    def test_a_title_that_is_empty_or_holds_a_line_break_is_refused_before_anything_is_asked_of_github(self):
        for title in ("", "   ", "One line\nand a second", "One line\r\nand a second", "#52 Its own\n#53 Another's"):
            code, printed, complained = self.file_it(title=title)
            self.assertEqual((code, printed), (2, ""), repr(title))
            self.assertIn("--title", complained)
        self.assertEqual(self.shell.ran, [])

    def test_a_file_that_is_not_there_is_refused_in_one_line_before_anything_is_asked_of_github(self):
        for missing in (["--file", str(self.folder / "gone.md")], ["--digest", str(self.folder / "gone.md")]):
            code, printed, complained = self.file_it(*missing)
            self.assertEqual((code, printed), (1, ""), missing)
            self.assertEqual(len(complained.strip().splitlines()), 1, complained)
            self.assertIn("gone.md", complained)
        self.assertEqual(self.shell.ran, [])

    def test_when_github_refuses_the_issue_it_exits_1_with_what_github_said(self):
        self.answers[CREATE] = shell.Failed(f"gh issue create: exit 1\ncould not add label: '{LABEL}' not found")
        code, printed, complained = self.file_it()
        self.assertEqual((code, printed), (1, ""))
        self.assertIn("could not add label", complained)


class TheAdding(FeedbackTest):
    def test_a_finding_seen_again_is_added_to_its_issue_as_a_comment_that_begins_by_naming_the_run(self):
        code, printed, _ = self.add_it()
        self.assertEqual((code, printed), (0, ADDED + "\n"))
        self.assertEqual(self.shell.read(COMMENT), f"Seen again in the run on #27.\n\n{WORDS}\n")
        self.assertEqual(self.shell.changes(), [line for line in self.shell.ran if line.startswith(COMMENT)])
        self.assertEqual(len(self.shell.changes()), 1)

    def test_a_finding_is_not_added_to_an_issue_that_does_not_carry_the_label(self):
        # A wrong number is most often a feature's own issue, which carries these.
        self.answers[VIEW] = issue(44, "site-idea", "approved", "in-progress")
        code, printed, complained = self.add_it()
        self.assertEqual((code, printed), (1, ""))
        self.assertEqual(self.shell.changes(), [])
        self.assertIn("#44", complained)
        self.assertIn(LABEL, complained)

    def test_a_finding_is_not_added_to_an_issue_that_is_closed(self):
        self.answers[VIEW] = issue(44, LABEL, state="CLOSED")
        code, printed, complained = self.add_it()
        self.assertEqual((code, printed), (1, ""))
        self.assertEqual(self.shell.changes(), [])
        self.assertIn("#44", complained)
        self.assertIn("closed", complained)

    def test_a_finding_is_added_to_an_issue_that_carries_other_labels_beside_the_one(self):
        self.answers[VIEW] = issue(44, "needs-owner", LABEL)
        self.assertEqual(self.add_it()[0], 0)
        self.assertEqual(len(self.shell.changes()), 1)

    def test_an_issue_github_does_not_have_is_refused_with_what_github_said_and_nothing_is_added(self):
        self.answers["gh issue view 999"] = shell.Failed("gh issue view 999: exit 1\nCould not resolve to an Issue")
        code, printed, complained = self.add_it(999)
        self.assertEqual((code, printed), (1, ""))
        self.assertIn("Could not resolve to an Issue", complained)
        self.assertEqual(self.shell.changes(), [])

    def test_a_file_that_is_not_there_is_refused_before_anything_is_asked_of_github(self):
        code, printed, complained = self.run_command("add", "44", "--run", "27", "--file", str(self.folder / "gone.md"))
        self.assertEqual((code, printed), (1, ""))
        self.assertIn("gone.md", complained)
        self.assertEqual(self.shell.ran, [])

    def test_when_github_refuses_the_comment_it_exits_1_with_what_github_said(self):
        self.answers[COMMENT] = shell.Failed("gh issue comment 44: exit 1\nHTTP 403: Resource not accessible")
        code, printed, complained = self.add_it()
        self.assertEqual((code, printed), (1, ""))
        self.assertIn("HTTP 403", complained)


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
            self.assertEqual(feedback.read_text(folder / name), words, name)


if __name__ == "__main__":
    unittest.main()
