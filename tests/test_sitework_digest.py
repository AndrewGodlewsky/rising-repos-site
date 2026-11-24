"""The digest of a run, and the `stage` call that lets it tell a run's stages apart.

Every record here is made up, in the shape an agent's record of its run has: one JSON object a line, an agent's
message with its count of tokens and its tool calls, and each call's result in a line after it. No test reads a
real record, and none reaches GitHub: the one that needs an issue's timeline replaces `sitework.shell.run`. The
tests of a run that finds its own records make the folder they are kept in, in a temporary folder, and set the
two variables that lead to it for the length of the test alone.
"""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sitework import digest, shell

CHECKOUT = "C:\\made-up\\checkout"
"""Where the made-up agent worked. It is no folder of this machine, and no digest may name it."""

SUITE = "uv run --locked python -m unittest discover -s tests"


def said(message: str, *blocks: dict, at: str = "2026-11-02T10:00:00.000Z", tokens=(1, 2, 3, 4)) -> dict:
    """A line of a record: part of the agent's message `message`, with the message's count of tokens."""
    kinds = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    return {
        "type": "assistant",
        "timestamp": at,
        "cwd": CHECKOUT,
        "message": {"id": message, "content": list(blocks), "usage": dict(zip(kinds, tokens, strict=True))},
    }


def call(call_id: str, tool: str, **given) -> dict:
    return {"type": "tool_use", "id": call_id, "name": tool, "input": given}


def shell_call(call_id: str, command: str) -> dict:
    return call(call_id, "Bash", command=command)


def stage(name: str, message: str = "", **more) -> dict:
    """The agent's message that begins the stage `name`."""
    return said(
        message or f"stage {name}", shell_call(f"call {name}", f"uv run python -m sitework stage {name}"), **more
    )


def result(call_id: str, at: str = "2026-11-02T10:00:01.000Z", failed: bool = False, background: str = "", printed=""):
    """The line that holds a call's result, as the record keeps it. `printed` is what the command printed, which
    the record keeps as text or as a list of parts."""
    block = {"type": "tool_result", "tool_use_id": call_id, "is_error": failed, "content": printed}
    line = {
        "type": "user",
        "timestamp": at,
        "cwd": CHECKOUT,
        "message": {"content": [block]},
        "toolUseResult": {"stdout": ""},
    }
    if background:
        line["toolUseResult"]["backgroundTaskId"] = background
    return line


def ended(background: str, at: str, status: str = "completed") -> dict:
    """The notice the record keeps when a command that ran in the background ends."""
    notice = f"<task-notification><task-id>{background}</task-id><status>{status}</status></task-notification>"
    return {"type": "queue-operation", "operation": "enqueue", "timestamp": at, "content": notice}


class RecordTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.root = self.folder / "repository"
        self.root.mkdir()
        self.enterContext(mock.patch.object(shell, "ROOT", self.root))

    def record(self, name: str, *lines: dict) -> Path:
        path = self.folder / f"{name}.jsonl"
        path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
        return path

    def digest(self, *lines: dict, **options) -> str:
        return digest.digest([self.record("first", *lines)], **options)

    def run_digest(self, *arguments: str) -> tuple[int, str, str]:
        printed, complained = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(complained):
            code = digest.main("digest", list(arguments))
        return code, printed.getvalue(), complained.getvalue()

    def section(self, text: str, heading: str) -> str:
        """What the digest says under `heading`, up to the next heading."""
        after = text.split(f"\n## {heading}\n", 1)[1]
        return after.split("\n## ", 1)[0].strip()

    def rows(self, text: str, heading: str) -> list[list[str]]:
        """The rows of the table under `heading`, without its heading row and its rule."""
        table = [line for line in self.section(text, heading).splitlines() if line.startswith("|")]
        return [[cell.strip() for cell in line.strip("|").split("|")] for line in table[2:]]


class TheStage(unittest.TestCase):
    def run_stage(self, *arguments: str) -> tuple[int, str]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = digest.main("stage", list(arguments))
        return code, printed.getvalue()

    def test_it_prints_the_stage_it_was_given_and_nothing_else(self):
        self.assertEqual(self.run_stage("build"), (0, "stage: build\n"))

    def test_the_look_back_is_named_in_two_words_with_or_without_quotes(self):
        self.assertEqual(self.run_stage("look", "back"), (0, "stage: look back\n"))
        self.assertEqual(self.run_stage("look back"), (0, "stage: look back\n"))

    def test_it_refuses_a_name_that_is_not_a_stage(self):
        with contextlib.redirect_stderr(io.StringIO()) as refused, self.assertRaises(SystemExit) as exit_:
            self.run_stage("biuld")
        self.assertEqual(exit_.exception.code, 2)
        self.assertIn("biuld", refused.getvalue())

    def test_a_mend_is_a_stage_a_run_can_mark(self):
        self.assertEqual(self.run_stage("mend"), (0, "stage: mend\n"))

    def test_the_refusal_of_a_name_lists_the_mend_among_the_stages_after_confirm_and_before_the_look_back(self):
        with contextlib.redirect_stderr(io.StringIO()) as refused, self.assertRaises(SystemExit):
            self.run_stage("biuld")
        self.assertIn("ship, confirm, mend, look back", refused.getvalue())


class TheTokens(RecordTest):
    def test_what_comes_before_the_first_stage_is_the_pick_up_and_each_stage_runs_to_the_next(self):
        text = self.digest(
            said("a", tokens=(1, 2, 3, 4)),
            stage("shape", tokens=(10, 20, 30, 40)),
            said("b", tokens=(100, 200, 300, 400)),
            stage("build", tokens=(1000, 2000, 3000, 4000)),
        )
        self.assertEqual(
            self.rows(text, "Tokens by stage"),
            [
                ["pick up", "1", "2", "3", "4", "10"],
                ["shape", "110", "220", "330", "440", "1,100"],
                ["build", "1,000", "2,000", "3,000", "4,000", "10,000"],
                ["Total", "1,111", "2,222", "3,333", "4,444", "11,110"],
            ],
        )

    def test_a_message_the_record_holds_as_several_lines_is_counted_once(self):
        text = self.digest(
            said("a", {"type": "thinking"}, tokens=(5, 5, 5, 5)),
            said("a", {"type": "text"}, tokens=(5, 5, 5, 5)),
            said("a", call("1", "Read", file_path="x"), tokens=(5, 5, 5, 5)),
        )
        self.assertEqual(self.rows(text, "Tokens by stage")[-1], ["Total", "5", "5", "5", "5", "20"])

    def test_the_message_that_begins_a_stage_is_counted_in_it_whichever_of_its_lines_holds_the_call(self):
        text = self.digest(
            said("a", {"type": "thinking"}, tokens=(7, 0, 0, 0)),
            stage("review", message="a", tokens=(7, 0, 0, 0)),
        )
        self.assertEqual(self.rows(text, "Tokens by stage")[0], ["review", "7", "0", "0", "0", "7"])

    def test_a_stage_the_run_comes_back_to_is_one_row(self):
        text = self.digest(stage("build", "a"), stage("check", "b"), stage("build", "c"), said("d"))
        self.assertEqual([row[0] for row in self.rows(text, "Tokens by stage")], ["build", "check", "Total"])
        self.assertEqual(self.rows(text, "Tokens by stage")[0][-1], "30")

    def test_what_follows_the_mark_of_a_mend_is_counted_under_mend_and_not_under_the_stage_before_it(self):
        text = self.digest(
            stage("confirm", tokens=(1, 0, 0, 0)),
            said("a", tokens=(10, 0, 0, 0)),
            stage("mend", tokens=(0, 100, 0, 0)),
            said("b", tokens=(0, 1000, 0, 0)),
            stage("look back", tokens=(0, 0, 0, 10000)),
        )
        self.assertEqual(
            self.rows(text, "Tokens by stage"),
            [
                ["confirm", "11", "0", "0", "0", "11"],
                ["mend", "0", "1,100", "0", "0", "1,100"],
                ["look back", "0", "0", "0", "10,000", "10,000"],
                ["Total", "11", "1,100", "0", "10,000", "11,111"],
            ],
        )

    def test_a_fresh_agent_started_in_a_mend_is_counted_under_mend(self):
        first = self.record(
            "first",
            stage("review", tokens=(1, 0, 0, 0)),
            stage("mend", tokens=(10, 0, 0, 0)),
            said("b", call("start-1", "Agent", prompt="Review the mend."), tokens=(100, 0, 0, 0)),
        )
        reviewer = self.record("agent-reviewer", said("r", tokens=(1000, 0, 0, 0)))
        about = {"agentType": "general-purpose", "toolUseId": "start-1"}
        reviewer.with_suffix(".meta.json").write_text(json.dumps(about), encoding="utf-8")
        text = digest.digest([first, reviewer])
        rows = {row[0]: row[-1] for row in self.rows(text, "Tokens by stage")}
        self.assertEqual(rows, {"review": "1", "mend": "1,110", "Total": "1,111"})
        self.assertEqual(self.rows(text, "Fresh agents"), [["agent-reviewer", "mend", "1,000"]])

    def test_a_later_record_is_named_by_its_file_unless_it_holds_a_stage_call(self):
        first = self.record("first", stage("build"))
        reviewer = self.record("reviewer", said("r1", tokens=(1, 0, 0, 0)), stage("review", tokens=(2, 0, 0, 0)))
        helper = self.record("agent-helper", said("h1", tokens=(4, 0, 0, 0)))
        text = digest.digest([first, reviewer, helper])
        rows = {row[0]: row[-1] for row in self.rows(text, "Tokens by stage")}
        self.assertEqual(rows, {"build": "10", "review": "3", "agent-helper": "4", "Total": "17"})


class TheCalls(RecordTest):
    def test_each_tool_is_counted_and_the_one_called_most_comes_first(self):
        text = self.digest(
            said("a", call("1", "Read", file_path="x"), call("2", "Edit", file_path="x")),
            said("b", call("3", "Read", file_path="y")),
        )
        self.assertEqual(self.section(text, "Tools"), "Read 2, Edit 1.")

    def test_a_file_read_is_named_by_its_path_in_the_repository_with_its_reads_and_its_lines(self):
        (self.root / "sitebuild").mkdir()
        (self.root / "sitebuild" / "page.py").write_text("one\ntwo\nthree\n", encoding="utf-8")
        text = self.digest(
            said("a", call("1", "Read", file_path=CHECKOUT + "\\sitebuild\\page.py")),
            said("b", call("2", "Read", file_path=CHECKOUT.lower() + "/sitebuild/page.py")),
            said("c", call("3", "Read", file_path=CHECKOUT + "\\gone.md")),
        )
        self.assertEqual(
            self.rows(text, "Files read most often"), [["sitebuild/page.py", "2", "3"], ["gone.md", "1", "-"]]
        )

    def test_a_file_under_this_checkout_is_in_the_repository_too(self):
        (self.root / "README.md").write_text("one\n", encoding="utf-8")
        text = self.digest(said("a", call("1", "Read", file_path=str(self.root / "README.md"))))
        self.assertEqual(self.rows(text, "Files read most often"), [["README.md", "1", "1"]])

    def test_a_file_outside_the_repository_is_counted_and_never_named(self):
        text = self.digest(
            said("a", call("1", "Read", file_path="D:\\somebody\\private\\notes.txt")),
            said("b", call("2", "Read", file_path=CHECKOUT + "-other\\secret.md")),
            said("c", call("3", "Read", file_path=CHECKOUT + "\\..\\beside\\climbed.md")),
        )
        self.assertEqual(self.rows(text, "Files read most often"), [])
        self.assertIn("3 reads were of files outside the repository", self.section(text, "Files read most often"))
        for private in ("somebody", "notes.txt", "secret.md", "climbed.md", "made-up"):
            self.assertNotIn(private, text)

    def test_only_the_ten_files_read_most_often_are_listed(self):
        reads = [
            said(f"m{number}-{again}", call(f"c{number}-{again}", "Read", file_path=f"{CHECKOUT}\\f{number:02}.py"))
            for number in range(12)
            for again in range(number + 1)
        ]
        rows = self.rows(self.digest(*reads), "Files read most often")
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0][:2], ["f11.py", "12"])
        self.assertEqual(rows[-1][:2], ["f02.py", "3"])

    def test_no_digest_names_the_folder_the_agent_worked_in(self):
        text = self.digest(
            stage("build"),
            said("a", call("1", "Read", file_path=CHECKOUT + "\\README.md")),
            said("b", shell_call("2", f"cd {CHECKOUT} && {SUITE}")),
            result("2", failed=True),
            said("c", shell_call("3", f"uv run python -m sitework stop 7 --note {CHECKOUT}\\note.md")),
        )
        self.assertNotIn("made-up", text)


class TheSuite(RecordTest):
    def test_each_run_of_the_whole_suite_is_timed_from_its_call_to_its_result(self):
        text = self.digest(
            stage("build"),
            said("a", shell_call("1", SUITE), at="2026-11-02T10:00:00.000Z"),
            result("1", at="2026-11-02T10:04:31.000Z", failed=True),
            said("b", shell_call("2", "uv run --locked python -m sitework check"), at="2026-11-02T11:00:00.000Z"),
            result("2", at="2026-11-02T11:05:02.500Z"),
            said("c", shell_call("3", "uv run --locked python -m unittest tests.test_build")),
            result("3"),
        )
        self.assertIn("ran 2 times", self.section(text, "The whole suite"))
        self.assertEqual(
            self.rows(text, "The whole suite"), [["build", "4m 31s", "failed"], ["build", "5m 02s", "passed"]]
        )

    def test_a_run_in_the_background_is_timed_to_the_notice_that_it_ended(self):
        text = self.digest(
            said("a", shell_call("1", SUITE), at="2026-11-02T10:00:00.000Z"),
            result("1", at="2026-11-02T10:00:01.000Z", background="task9"),
            ended("task9", at="2026-11-02T10:04:40.000Z", status="failed"),
        )
        self.assertEqual(self.rows(text, "The whole suite"), [["pick up", "4m 40s", "failed"]])

    def test_a_run_whose_result_the_record_does_not_hold_is_said_to_have_none(self):
        text = self.digest(
            said("a", shell_call("1", SUITE)),
            said("b", shell_call("2", SUITE)),
            result("2", background="task9"),
        )
        self.assertEqual(self.rows(text, "The whole suite"), [["pick up", "-", "no result"]] * 2)

    def test_a_run_of_a_part_of_the_suite_is_not_a_run_of_the_whole(self):
        text = self.digest(
            said("a", shell_call("1", SUITE + ' -p "test_build*" 2>&1 | tail -3')),
            result("1"),
            said("b", shell_call("2", SUITE + " -k test_the_root")),
            result("2"),
            said("c", shell_call("3", f"cd tests/.. && {SUITE} -v 2>&1 | tail -3"), at="2026-11-02T10:00:00.000Z"),
            result("3", at="2026-11-02T10:04:00.000Z"),
        )
        self.assertEqual(self.rows(text, "The whole suite"), [["pick up", "4m 00s", "passed"]])

    def test_a_command_that_a_file_written_in_the_shell_only_names_is_not_run(self):
        written = (
            "cat > note.md <<'EOF'\n"
            f"Run `{SUITE}` first.\n"
            "Then uv run python -m sitework stage review, and uv run python -m sitework stop 7.\n"
            "EOF\n"
            "git status"
        )
        text = self.digest(said("a", shell_call("1", written)), result("1", failed=True))
        self.assertEqual([row[0] for row in self.rows(text, "Tokens by stage")], ["pick up", "Total"])
        self.assertEqual(self.section(text, "The whole suite"), "It did not run.")
        self.assertEqual(self.section(text, "Checks that failed"), "None.")
        self.assertEqual(self.section(text, "Stops"), "None.")

    def test_a_run_that_never_ran_the_suite_says_so(self):
        self.assertEqual(self.section(self.digest(said("a")), "The whole suite"), "It did not run.")


class TheChecks(RecordTest):
    def test_a_check_that_failed_is_listed_with_the_tries_it_took_to_pass(self):
        check = "uv run --locked python -m sitework check"
        text = self.digest(
            stage("check"),
            said("a", shell_call("1", check)),
            result("1", failed=True),
            said("b", shell_call("2", check)),
            result("2", failed=True),
            said("c", shell_call("3", "uv run --locked ruff check sitebuild")),
            result("3"),
            said("d", shell_call("4", check)),
            result("4"),
        )
        self.assertEqual(self.section(text, "Checks that failed"), "- `sitework check`, in check: passed on try 3.")

    def test_a_run_of_the_check_that_failed_names_each_step_it_stopped_at(self):
        check = "uv run --locked python -m sitework check --issue 7"
        lint = "the lint: started\nthe lint: failed after 0.4 s\nsitebuild\\page.py:3:1: F401 unused"
        tests = "Exit code 1\nthe lint: passed in 0.4 s\nthe agents' tests: failed after 201.3 s\nFAIL: test_the_root"
        text = self.digest(
            stage("check"),
            said("a", shell_call("1", check), at="2026-11-02T10:00:00.000Z"),
            result("1", at="2026-11-02T10:00:03.000Z", failed=True, printed=lint),
            said("b", shell_call("2", check), at="2026-11-02T10:10:00.000Z"),
            result("2", at="2026-11-02T10:13:25.000Z", failed=True, printed=[{"type": "text", "text": tests}]),
            said("c", shell_call("3", check)),
            result("3", failed=True, printed="the lint: started\nthe lint: failed after 0.5 s"),
            said("d", shell_call("4", check)),
            result("4", printed="the lint: passed in 0.4 s"),
        )
        self.assertEqual(
            self.section(text, "Checks that failed"),
            "- `sitework check`, in check: failed at the lint, then at the agents' tests, and passed on try 4.",
        )
        self.assertEqual(
            self.rows(text, "The whole suite")[:2],
            [["check", "0m 03s", "failed at the lint"], ["check", "3m 25s", "failed at the agents' tests"]],
        )
        self.assertNotIn("page.py", text)

    def test_a_step_is_read_only_from_what_the_check_itself_printed(self):
        printed = "a line of the test: failed after 3 s"
        text = self.digest(
            said("a", shell_call("1", "uv run --locked python -m unittest tests.test_build")),
            result("1", failed=True, printed=printed),
            said("b", shell_call("2", "uv run --locked python -m sitework check")),
            result("2", failed=True, printed="C:\\made-up\\checkout: failed after 3 s"),
        )
        self.assertEqual(
            self.section(text, "Checks that failed").splitlines(),
            [
                "- `unittest tests.test_build`, in pick up: failed 1 time, and did not pass in the record.",
                "- `sitework check`, in pick up: failed 1 time, and did not pass in the record.",
            ],
        )

    def test_a_part_of_the_suite_is_a_check_of_its_own_named_by_the_part(self):
        text = self.digest(
            said("a", shell_call("1", SUITE + ' -p "test_build*" -v 2>&1')),
            result("1", failed=True),
            said("b", shell_call("2", SUITE + " -p 'test_data*'")),
            result("2"),
            said("c", shell_call("3", SUITE + f" -p {CHECKOUT}\\tests\\test_build.py")),
            result("3", failed=True),
        )
        never = "in pick up: failed 1 time, and did not pass in the record."
        self.assertEqual(
            self.section(text, "Checks that failed").splitlines(),
            [f"- `unittest discover -s tests -p test_build*`, {never}", f"- `unittest discover -s tests -p`, {never}"],
        )

    def test_the_name_of_a_check_ends_at_the_first_word_that_chooses_no_test(self):
        sentence = 'git commit -m "Run python -m unittest tests.test_build before the tests.pass, on my testimony"'
        text = self.digest(said("a", shell_call("1", sentence)), result("1", failed=True))
        self.assertIn("- `unittest tests.test_build`, in pick up:", self.section(text, "Checks that failed"))
        self.assertNotIn("testimony", text)

    def test_a_check_that_never_passed_is_said_not_to_have(self):
        text = self.digest(
            said("a", shell_call("1", "uv run --locked python -m unittest tests.test_build -v")),
            result("1", failed=True),
            said("b", shell_call("2", "uv run --locked python -m unittest tests.test_build")),
            result("2", failed=True),
        )
        self.assertEqual(
            self.section(text, "Checks that failed"),
            "- `unittest tests.test_build`, in pick up: failed 2 times, and did not pass in the record.",
        )

    def test_a_check_that_fails_again_after_it_passed_is_listed_again(self):
        ruff = "uv run --locked ruff format --check sitework"
        lines = []
        for number, failed in enumerate((True, False, True, False)):
            lines += [said(f"m{number}", shell_call(str(number), ruff)), result(str(number), failed=failed)]
        self.assertEqual(
            self.section(self.digest(*lines), "Checks that failed").splitlines(),
            ["- `ruff format`, in pick up: passed on try 2."] * 2,
        )

    def test_a_command_that_is_no_check_is_not_listed_when_it_fails(self):
        text = self.digest(said("a", shell_call("1", "git push")), result("1", failed=True))
        self.assertEqual(self.section(text, "Checks that failed"), "None.")


class TheStops(RecordTest):
    def test_each_stop_is_listed_with_its_stage_its_time_and_whom_it_waits_for(self):
        stop = "uv run --locked python -m sitework stop 7"
        text = self.digest(
            stage("review"),
            said("a", shell_call("1", f"{stop} --stage review --file note.md"), at="2026-11-02T12:30:00.000Z"),
            stage("build"),
            said("b", shell_call("2", f"{stop} --data 212 --field pace --file n.md"), at="2026-11-03T08:05:00.000Z"),
        )
        self.assertEqual(
            self.section(text, "Stops").splitlines(),
            ["- in review, at 2026-11-02 12:30 UTC, for the owner.", "- in build, at 2026-11-03 08:05 UTC, for data."],
        )

    def test_a_stop_after_the_mark_of_a_mend_is_listed_as_a_stop_in_mend(self):
        stop = "uv run --locked python -m sitework stop 7 --stage mend --file note.md"
        text = self.digest(
            stage("confirm"), stage("mend"), said("a", shell_call("1", stop), at="2026-11-02T12:30:00.000Z")
        )
        self.assertEqual(self.section(text, "Stops"), "- in mend, at 2026-11-02 12:30 UTC, for the owner.")

    def test_a_run_that_did_not_stop_says_so(self):
        self.assertEqual(self.section(self.digest(said("a")), "Stops"), "None.")


class TheFigures(RecordTest):
    def figures(self, text: str) -> list[str]:
        return self.section(text, "Figures").splitlines()[:3]

    def test_the_row_adds_shape_to_build_and_gives_review_the_look_back_and_every_stage(self):
        text = self.digest(
            said("a", tokens=(1, 0, 0, 0)),
            stage("shape", tokens=(10, 0, 0, 0)),
            stage("build", tokens=(0, 100, 0, 0)),
            stage("review", tokens=(0, 0, 1000, 0)),
            stage("look back", tokens=(0, 0, 0, 10000)),
            issue=None,
        )
        self.assertEqual(
            self.figures(text),
            [digest.FIGURES_HEADING, digest.FIGURES_RULE, "| - | 110 | 1,000 | 10,000 | 11,111 | no | - |"],
        )

    def test_a_mends_tokens_are_in_every_stage_and_in_no_other_figure_of_the_row(self):
        text = self.digest(
            stage("shape", tokens=(10, 0, 0, 0)),
            stage("build", tokens=(0, 100, 0, 0)),
            stage("review", tokens=(0, 0, 1000, 0)),
            stage("mend", tokens=(0, 50000, 0, 0)),
            stage("look back", tokens=(0, 0, 0, 10000)),
        )
        self.assertEqual(self.figures(text)[2], "| - | 110 | 1,000 | 10,000 | 61,110 | no | - |")

    def test_the_heading_row_is_the_one_the_notes_add_a_row_under(self):
        self.assertEqual(
            digest.FIGURES_HEADING,
            "| Issue | Shape and build | Review | Look back | Every stage | Stopped | Hours from approval to close |",
        )

    def test_a_run_that_stopped_says_so_in_its_row(self):
        text = self.digest(said("a", shell_call("1", "uv run python -m sitework stop 7 --stage build --file n.md")))
        self.assertEqual(self.figures(text)[2].split("|")[6].strip(), "yes")

    def test_the_hours_run_from_the_last_approval_before_the_close_to_the_close(self):
        timeline = "\n".join(
            [
                "labeled\tsite-idea\t2026-11-01T08:00:00Z",
                "labeled\tapproved\t2026-11-01T09:00:00Z",
                "labeled\tapproved\t2026-11-02T09:00:00Z",
                "closed\t\t2026-11-02T14:30:00Z",
                "labeled\tapproved\t2026-11-03T00:00:00Z",
            ]
        )
        with mock.patch.object(shell, "run", return_value=timeline) as asked:
            text = self.digest(said("a", tokens=(1, 1, 1, 1)), issue=7)
        self.assertEqual(self.figures(text)[2], "| #7 | 0 | 0 | 0 | 4 | no | 5.5 |")
        self.assertEqual(asked.call_args.args[:2], ("gh", "api"))
        self.assertIn("issues/7/timeline", " ".join(asked.call_args.args))

    def test_an_issue_that_is_still_open_has_no_hours(self):
        with mock.patch.object(shell, "run", return_value="labeled\tapproved\t2026-11-01T09:00:00Z"):
            text = self.digest(said("a"), issue=7)
        self.assertEqual(self.figures(text)[2].split("|")[7].strip(), "-")


class TheCommand(RecordTest):
    def test_it_prints_the_digest_of_the_records_it_is_given(self):
        first = self.record("first", stage("build"))
        second = self.record("second", said("x"))
        code, printed, _ = self.run_digest(str(first), str(second))
        self.assertEqual(code, 0)
        self.assertTrue(printed.startswith("# Digest of a run\n"))
        self.assertEqual(printed, digest.digest([first, second]) + "\n")

    def test_with_an_issue_it_names_the_issue_and_asks_github_for_its_hours(self):
        first = self.record("first", said("a"))
        timeline = "labeled\tapproved\t2026-11-01T09:00:00Z\nclosed\t\t2026-11-01T10:00:00Z"
        with mock.patch.object(shell, "run", return_value=timeline):
            code, printed, _ = self.run_digest(str(first), "--issue", "7")
        self.assertEqual(code, 0)
        self.assertTrue(printed.startswith("# Digest of the run on #7\n"))
        self.assertIn("| #7 | 0 | 0 | 0 | 10 | no | 1.0 |", printed)

    def test_when_github_does_not_answer_it_prints_the_digest_without_the_hours_and_exits_1(self):
        first = self.record("first", said("a"))
        with mock.patch.object(shell, "run", side_effect=shell.Failed("gh api: exit 1")):
            code, printed, complained = self.run_digest(str(first), "--issue", "7")
        self.assertEqual(code, 1)
        self.assertIn("| #7 | 0 | 0 | 0 | 10 | no | - |", printed)
        self.assertIn("gh api: exit 1", complained)

    def test_a_record_that_is_not_there_is_refused(self):
        code, printed, complained = self.run_digest(str(self.folder / "missing.jsonl"))
        self.assertEqual((code, printed), (1, ""))
        self.assertIn("missing.jsonl", complained)

    def test_the_usage_says_that_the_records_or_this_run_is_given(self):
        with contextlib.redirect_stdout(io.StringIO()) as printed, self.assertRaises(SystemExit):
            digest.main("digest", ["--help"])
        self.assertIn("(--this-run | RECORD [RECORD ...])", " ".join(printed.getvalue().split()))

    def test_the_records_and_this_run_are_not_both_given_and_one_of_them_has_to_be(self):
        first = self.record("first", said("a"))
        for arguments in ([], ["--this-run", str(first)]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as refused:
                digest.main("digest", arguments)
            self.assertEqual(refused.exception.code, 2, arguments)


SESSION = "5e55104d-made-up"
"""The name a made-up session goes by. A real one's is longer, and is never written here."""


class ThisRun(RecordTest):
    """A run finds its own records: its session's, and beside it the record of each fresh agent the session
    started, in a made-up folder that is laid out as the one Claude Code keeps its records in."""

    def setUp(self):
        super().setUp()
        self.config = self.folder / "kept-by-claude-code"
        self.project = self.config / "projects" / "named-for-a-checkout"
        self.enterContext(
            mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.config), "CLAUDE_CODE_SESSION_ID": SESSION})
        )

    def write(self, path: Path, *lines: dict) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
        return path

    def session(self, *lines: dict) -> Path:
        return self.write(self.project / f"{SESSION}.jsonl", *lines)

    def agent(self, name: str, *lines: dict, started_by: str = "") -> Path:
        """The record of a fresh agent of the session. `started_by` is the call that started it, which the file
        beside its record names."""
        path = self.write(self.project / SESSION / "subagents" / f"agent-{name}.jsonl", *lines)
        if started_by:
            about = {"agentType": "general-purpose", "description": "Words of the run's agent", "toolUseId": started_by}
            path.with_suffix(".meta.json").write_text(json.dumps(about), encoding="utf-8")
        return path

    def test_it_finds_the_sessions_record_and_then_each_agents_record_oldest_first(self):
        session = self.session(said("a"))
        late = self.agent("a-late", said("l", at="2026-11-02T12:00:00.000Z"))
        early = self.agent("z-early", said("e", at="2026-11-02T11:00:00.000Z"))
        self.assertEqual(digest.this_run(), [session, early, late])

    def test_the_folder_is_the_one_that_holds_the_sessions_record_and_no_other_sessions_agent_is_read(self):
        self.write(self.config / "projects" / "another-checkout" / "another-session.jsonl", said("o"))
        self.write(self.project / "another-session.jsonl", said("p"))
        self.write(self.project / "another-session" / "subagents" / "agent-other.jsonl", said("q"))
        session, mine = self.session(said("a")), self.agent("mine", said("m"))
        self.assertEqual(digest.this_run(), [session, mine])

    def test_an_agents_tokens_are_counted_in_the_stage_it_was_started_in(self):
        self.session(
            said("a", tokens=(1, 0, 0, 0)),
            stage("review", tokens=(10, 0, 0, 0)),
            said("b", call("start-1", "Agent", prompt="Review the change."), tokens=(100, 0, 0, 0)),
            stage("ship", tokens=(1000, 0, 0, 0)),
        )
        reviewer = (said("r", call("start-2", "Agent", prompt="Find the page."), tokens=(5, 0, 0, 0)),)
        self.agent("reviewer", *reviewer, started_by="start-1")
        self.agent("helper", said("h", at="2026-11-02T10:30:00.000Z", tokens=(7, 0, 0, 0)), started_by="start-2")
        text = digest.digest(digest.this_run())
        self.assertEqual(
            [[row[0], row[-1]] for row in self.rows(text, "Tokens by stage")],
            [["pick up", "1"], ["review", "122"], ["ship", "1,000"], ["Total", "1,123"]],
        )

    def test_an_agent_that_marks_a_stage_itself_is_counted_in_that_one(self):
        self.session(stage("build"), said("b", call("start-1", "Agent", prompt="Look back.")))
        self.agent("looks-back", said("l"), stage("look back"), started_by="start-1")
        rows = self.rows(digest.digest(digest.this_run()), "Tokens by stage")
        self.assertEqual([[row[0], row[-1]] for row in rows], [["build", "20"], ["look back", "20"], ["Total", "40"]])

    def test_each_fresh_agent_is_listed_by_its_file_with_the_stage_it_began_in_and_its_tokens(self):
        self.session(stage("review"), said("b", call("start-1", "Agent", prompt="Review the change.")))
        self.agent("reviewer", said("r1"), said("r2"), started_by="start-1")
        self.agent("stray", said("s", at="2026-11-02T13:00:00.000Z"))
        text = digest.digest(digest.this_run())
        self.assertEqual(
            self.rows(text, "Fresh agents"), [["agent-reviewer", "review", "20"], ["agent-stray", "agent-stray", "10"]]
        )
        self.assertEqual(self.section(self.digest(said("a")), "Fresh agents"), "None was started.")

    def test_with_this_run_the_command_prints_the_digest_of_the_sessions_own_records(self):
        self.session(stage("build"))
        self.agent("one", said("x"))
        code, printed, _ = self.run_digest("--this-run")
        self.assertEqual(code, 0)
        self.assertIn("Made from 2 records", printed)
        self.assertEqual(printed, digest.digest(digest.this_run()) + "\n")

    def test_the_digest_of_this_run_names_nothing_of_the_folder_its_records_are_kept_in(self):
        self.session(stage("build"), said("b", call("start-1", "Agent", prompt="Help.")))
        self.agent("one", said("x"), started_by="start-1")
        self.agent("two", said("y"))
        _, printed, _ = self.run_digest("--this-run")
        for kept in (self.config.name, self.project.name, SESSION, "Words of the run's agent", self.folder.name):
            self.assertNotIn(kept, printed)

    def test_when_a_variable_is_not_set_it_says_which_in_one_line_and_exits_1(self):
        self.session(said("a"))
        for name in ("CLAUDE_CONFIG_DIR", "CLAUDE_CODE_SESSION_ID"):
            with mock.patch.dict(os.environ):
                del os.environ[name]
                code, printed, complained = self.run_digest("--this-run")
            self.assertEqual((code, printed), (1, ""), name)
            self.assertEqual(len(complained.strip().splitlines()), 1, complained)
            self.assertIn(name, complained)

    def test_when_the_sessions_record_is_not_there_it_says_so_in_one_line_and_exits_1(self):
        self.write(self.project / "another-session.jsonl", said("p"))
        code, printed, complained = self.run_digest("--this-run")
        self.assertEqual((code, printed), (1, ""))
        self.assertEqual(len(complained.strip().splitlines()), 1, complained)
        self.assertIn("CLAUDE_CODE_SESSION_ID", complained)
        self.assertNotIn(self.config.name, complained)


if __name__ == "__main__":
    unittest.main()
