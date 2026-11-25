"""The feature workflow's documents say only what its scripts do.

A run follows docs/workflow/README.md and nothing else, so a command that document names and the scripts do not
have, or a label the two spell differently, would stop a run where nobody is watching.
"""

import contextlib
import importlib.util
import io
import re
import unittest

from helpers import ROOT

from sitework import rules
from sitework.__main__ import COMMANDS, main

WORKFLOW = ROOT / "docs" / "workflow"
DOCUMENTS = [*sorted(WORKFLOW.glob("*.md")), ROOT / "AGENTS.md", ROOT / "README.md"]
"""Every document that tells a reader to run one of the workflow's commands."""

NAMED = re.compile(r"(?:python -m sitework|`sitework) ([a-z][a-z-]*)")
"""A command as a document names it: after `python -m sitework`, or after `sitework` at the start of code."""


class TheDocuments(unittest.TestCase):
    def test_every_command_a_document_names_is_one_the_scripts_have(self):
        for document in DOCUMENTS:
            for command in NAMED.findall(document.read_text(encoding="utf-8")):
                with self.subTest(document=document.name, command=command):
                    self.assertIn(command, COMMANDS)

    def test_the_document_a_run_follows_names_every_stage_s_command(self):
        text = (WORKFLOW / "README.md").read_text(encoding="utf-8")
        named = set(NAMED.findall(text))
        for command in ("pickup", "stage", "comment", "stop", "check", "ship", "confirm", "revert", "close"):
            with self.subTest(command=command):
                self.assertIn(command, named)
        # A run takes no pictures: the pull request's job does, and keeps them.
        for command in ("altered-tests", "layout-report", "digest", "feedback", "guard"):
            with self.subTest(command=command):
                self.assertIn(command, named)

    def test_the_labels_a_run_is_told_of_are_the_ones_the_scripts_set(self):
        text = (WORKFLOW / "README.md").read_text(encoding="utf-8")
        table = text[text.index("## The labels") :]
        in_table = set(re.findall(r"^\| `([a-z -]+)` \|", table, flags=re.MULTILINE))
        self.assertEqual(
            in_table,
            {rules.IDEA, rules.APPROVED, rules.IN_PROGRESS, rules.NEEDS_OWNER, rules.BLOCKED_ON_DATA, rules.FEEDBACK},
        )

    def test_the_review_s_form_has_the_two_lines_the_ship_script_reads(self):
        form = (WORKFLOW / "reviewer.md").read_text(encoding="utf-8")
        self.assertRegex(form, r"(?m)^Verdict: pass$")
        self.assertRegex(form, r"(?m)^Commit: ")

    def test_the_plan_s_form_has_the_two_sections_the_criteria_check_reads(self):
        form = (WORKFLOW / "README.md").read_text(encoding="utf-8")
        self.assertLess(form.index("\n## Criteria\n"), form.index("\n## How each is proven\n"))
        self.assertIn("| # | Proof |", form)

    def test_the_document_a_run_follows_names_the_sorts_commands(self):
        # The sort grades the ideas that wait and records the lead's group, and Shape or a later stage sends a
        # partner back (25 November 2026).
        named = set(NAMED.findall((WORKFLOW / "README.md").read_text(encoding="utf-8")))
        for command in ("queue", "sort", "release"):
            with self.subTest(command=command):
                self.assertIn(command, named)

    def test_the_sorts_brief_has_the_lines_the_scripts_read(self):
        brief = (WORKFLOW / "sort.md").read_text(encoding="utf-8")
        for line in ("Complexity: ", "Effort: ", "Area: ", "Code: "):
            with self.subTest(line=line):
                self.assertRegex(brief, rf"(?m)^{line}")

    def test_the_statuses_a_run_is_told_of_are_the_ones_the_scripts_set(self):
        text = (WORKFLOW / "README.md").read_text(encoding="utf-8")
        labels = text[text.index("## The labels") :]
        for status in (rules.BACKLOG, rules.WORKING):
            with self.subTest(status=status):
                self.assertIn(f"`{status}`", labels)

    def test_a_run_is_told_the_first_line_that_marks_its_own_comments(self):
        self.assertIn(f"`{rules.FIRST_LINE.strip()}`", (WORKFLOW / "README.md").read_text(encoding="utf-8"))


class TheCommands(unittest.TestCase):
    def test_every_command_has_a_module_with_a_main(self):
        for command, (module, _) in COMMANDS.items():
            with self.subTest(command=command):
                self.assertIsNotNone(importlib.util.find_spec(module), f"{module} is not there")
                self.assertTrue(callable(getattr(importlib.import_module(module), "main", None)))

    def test_a_command_that_is_not_one_prints_the_list_and_exits_2(self):
        for argv in (["sitework", "no-such-command"], ["sitework"]):
            with self.subTest(argv=argv), contextlib.redirect_stdout(io.StringIO()) as printed:
                self.assertEqual(main(argv), 2)
            for command in COMMANDS:
                self.assertIn(f"  {command} ", printed.getvalue())
