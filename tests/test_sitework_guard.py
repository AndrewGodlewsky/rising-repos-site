"""A change to what judges a feature is named: `python -m sitework guard`.

Each test commits a change to a git repository of its own, in a temporary folder, and reads what the guard says of
it. None reads this repository's history, and none changes it.
"""

import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT

from sitework import guard, rules, shell

GUARDED = {
    ".github/workflows/deploy.yml": "a workflow",
    ".github/dependabot.yml": "a workflow",
    "pyproject.toml": "a dependency",
    "uv.lock": "a dependency",
    ".python-version": "a dependency",
    "uv.toml": "a dependency",
    "ruff.toml": "the settings of the lint and the format",
    "sitebuild/.ruff.toml": "the settings of the lint and the format",
    ".gitattributes": "how git reads and compares a file",
    "tests/fixtures/.gitattributes": "how git reads and compares a file",
    "tests/test_page_weight.py": "a size limit",
    "evals/site/limits.json": "the site eval and its limits",
    "evals/site/README.md": "the site eval and its limits",
    "tests/test_workflow.py": "a check that holds the guards",
    "tests/test_site_eval.py": "a check that holds the guards",
    "tests/test_site_eval_workflow.py": "a check that holds the guards",
    "tests/test_stale_check.py": "a check that holds the guards",
    "tests/test_tokens.py": "a check that holds the guards",
    "tests/test_context.py": "a check that holds the guards",
    "tests/test_runbook.py": "a check that holds the guards",
    "tests/test_sitework_guard.py": "a check that holds the guards",
    "sitebuild/fonts/subset.py": "the type",
    "site-data/boards/index.json": "the data RisingRepos publishes",
    "STANDARDS.md": "the standards and the decision records",
    "docs/adr/0003-the-pages-are-static.md": "the standards and the decision records",
    "sitework/ship.py": "the workflow's own scripts and documents",
    "docs/workflow/README.md": "the workflow's own scripts and documents",
    "docs/workflow-plan.md": "the workflow's own scripts and documents",
    "AGENTS.md": "the workflow's own scripts and documents",
    "CLAUDE.md": "the workflow's own scripts and documents",
    ".claude/settings.json": "the workflow's own scripts and documents",
}
"""One path, or two, of each kind a feature leaves alone, and why the guard says it is guarded."""

FREE = [
    "README.md",
    "STYLE.md",
    "GLOSSARY.md",
    "sitebuild/__init__.py",
    "sitebuild/templates/site.css",
    "sitebuild/templates/site.js",
    "tests/test_build.py",
    "tests/helpers.py",
    "tests/fixtures/contract-example/boards/index.json",
    "docs/research/a-note.md",
    "docs/workflow-notes/runs/27.md",
    "docs/pyproject.toml",
    "sitebuild/AGENTS.md",
]
"""What a feature is made of, a file where the look back's notes were kept until what a run taught became an
issue, and two files that share only a name with a guarded one."""

TEMPLATE = "sitebuild/templates/page.html"
PAGE = """\
<!doctype html>
<head>
{% set script %}{% include "site.js" %}{% endset %}
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src '{{ script|script_hash }}';\
{% if filtering %} connect-src 'self';{% endif %} style-src 'unsafe-inline'">
<title>{% block title %}{% endblock %}</title>
</head>
<body>
<p>A page</p>
</body>
"""
"""A template shaped as the site's page template is: the policy in a <meta>, with the script's hash worked out
when the page is built."""

POLICY = "the policy that lets a page's script run"
AT_THE_TOP = "a new file or folder at the top of the repository, which the checks are run from"
OWNERS = "the owner's tests, which a change adds to and takes nothing from"

READER = "owner_tests/test_reader.py"
READS = '''\
"""What a reader can do on a board."""

import unittest

from owner_tests.scenario import (
    Scenario,
    needs_made_up_boards,
)

WIDE = 1440
"""How wide the reader's screen is, in pixels."""


def first_row(page):
    return page.rows[0]


class AReader(Scenario):
    """A reader of a board."""

    def setUp(self):
        self.page = self.reader(width=WIDE)

    def test_a_reader_finds_the_board(self):
        """1. A reader finds the board."""
        # The board is the first thing on the page.
        self.assertTrue(self.page.rows)

    def test_a_reader_opens_a_row(self):
        """2. A reader opens a row."""
        self.assertTrue(first_row(self.page).opens)


if __name__ == "__main__":
    unittest.main()
'''
"""One of the owner's tests, laid out as the site's own are."""

SCENARIO = "owner_tests/scenario.py"
STARTS = '''\
"""What every one of the owner's tests starts from."""

import unittest

WAIT = 10_000


def needs_made_up_boards(test):
    test.needs_made_up_boards = True
    return test


class Scenario(unittest.TestCase):
    def setUp(self):
        self.site = None

    def reader(self, *, width):
        return self.site
'''
"""The helpers of the owner's tests."""

LOADER = "owner_tests/__init__.py"
LOADS = """\
import unittest


def load_tests(loader, tests, pattern):
    found = loader.loadTestsFromName(f"{__name__}.test_reader")
    return unittest.TestSuite(found)
"""
"""The loader of the owner's tests, which says which of them a run holds."""

SENTENCES = "owner_tests/README.md"
"""The one file among the owner's tests that is not Python, and is held by its lines."""

A_TEST = """\

    def test_a_reader_closes_a_row(self):
        self.assertFalse(first_row(self.page).opens)
"""
MORE = """\

NARROW = 390


def last_row(page):
    return page.rows[-1]


class AReaderOnAPhone(Scenario):
    def test_a_reader_finds_the_board(self):
        self.assertTrue(last_row(self.reader(width=NARROW)))
"""
"""What a change may add to one of the owner's tests: a test to a class that is there, and a constant, a helper,
and a class under names the file did not have."""


def swap(text: str, old: str, new: str) -> str:
    """`text` with `new` in the place of `old`. It fails when `old` is not there, so that a test never commits the
    text it began with and reads the guard's silence as a pass."""
    assert text.count(old) == 1, old
    return text.replace(old, new)


def put(text: str, new: str, *, before: str) -> str:
    """`text` with `new` put in ahead of `before`, and nothing taken out."""
    return swap(text, before, new + before)


def gained(line: int) -> str:
    """What the guard says of a statement that a change adds at the top of one of the owner's tests, and that
    may not be added there."""
    return (
        f"this file gained a statement on line {line} that is not an import of names, a function, a class, an "
        "assignment to a name, or a docstring"
    )


def said(main, command: str, *arguments: str) -> tuple[int, list[str]]:
    """Run one of the workflow's commands, and give its exit code and the lines it printed."""
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        code = main(command, list(arguments))
    return code, printed.getvalue().splitlines()


class RepositoryTest(unittest.TestCase):
    """A test with a git repository of its own in a temporary folder. The tests of the workflow's other commands
    that read a change are made from it too."""

    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        shell.git("init", "--quiet", cwd=self.root)
        # A commit needs a name, and the settings of the machine a test runs on must not change what it sees.
        with (self.root / ".git" / "config").open("a", encoding="utf-8") as settings:
            settings.write(
                "[user]\n\tname = A test\n\temail = none\n[core]\n\tautocrlf = false\n[commit]\n\tgpgsign = false\n"
            )

    def commit(self, files: dict[str, str | None]) -> str:
        """Write each of `files` at its path, or remove the one whose text is None, and give the commit that
        holds the result."""
        for path, text in files.items():
            if text is None:
                (self.root / path).unlink()
            else:
                (self.root / path).parent.mkdir(parents=True, exist_ok=True)
                (self.root / path).write_text(text, encoding="utf-8", newline="\n")
        shell.git("add", "--all", cwd=self.root)
        shell.git("commit", "--quiet", "--message", "A change", cwd=self.root)
        return shell.git("rev-parse", "HEAD", cwd=self.root)

    def on_main(self, files: dict[str, str | None]) -> str:
        """Commit `files`, and have origin/main name that commit, as it names where a feature's branch began."""
        commit = self.commit(files)
        shell.git("update-ref", "refs/remotes/origin/main", commit, cwd=self.root)
        return commit


class TheGuard(RepositoryTest):
    def setUp(self):
        super().setUp()
        before = dict.fromkeys([*GUARDED, *FREE], "before\n")
        owners = {LOADER: "", READER: READS, SCENARIO: STARTS, SENTENCES: "one\ntwo\nthree\n"}
        self.base = self.on_main({**before, **owners, TEMPLATE: PAGE})

    def guard(self, *arguments: str) -> tuple[int, list[str]]:
        return said(guard.main, "guard", "--repository", str(self.root), *arguments)

    def add(self, files: dict[str, str]) -> None:
        """Commit a change to the owner's tests that adds lines and takes none away, which is all that a rule
        for lines can ask of it."""
        self.commit(files)
        base = shell.git("merge-base", "origin/main", "HEAD", cwd=self.root)
        self.assertEqual(guard.lost_lines(base, "HEAD", self.root), set())

    def names(self, path: str, what: str) -> tuple[int, list[str]]:
        """What the guard says when it names one of the owner's tests alone, for `what`."""
        return 1, [f"{path}: {OWNERS}: {what}"]

    def test_a_change_to_a_workflow_is_named(self):
        self.commit({".github/workflows/deploy.yml": "after\n"})
        self.assertEqual(self.guard(), (1, [".github/workflows/deploy.yml: a workflow"]))

    def test_every_guarded_path_is_named_with_why_it_is_guarded(self):
        self.commit(dict.fromkeys(GUARDED, "after\n"))
        self.assertEqual(self.guard(), (1, [f"{path}: {why}" for path, why in sorted(GUARDED.items())]))

    def test_the_guarded_paths_here_are_guarded_for_every_reason_the_rules_give_and_for_no_other(self):
        # So a reason that is added to the rules gets a path here, and one that is taken out leaves none behind.
        self.assertEqual(set(GUARDED.values()), set(rules.GUARDED))

    def test_a_guarded_path_that_a_change_adds_or_removes_is_named(self):
        # The second of these is new at the top of the repository too, and is named for the settings it holds.
        self.commit({"docs/adr/0009-a-new-record.md": "new\n", ".ruff.toml": "new\n", "uv.lock": None})
        self.assertEqual(
            self.guard(),
            (
                1,
                [
                    ".ruff.toml: the settings of the lint and the format",
                    "docs/adr/0009-a-new-record.md: the standards and the decision records",
                    "uv.lock: a dependency",
                ],
            ),
        )

    def test_a_change_to_the_pages_their_tests_and_their_documents_touches_nothing_guarded(self):
        self.commit(dict.fromkeys(FREE, "after\n"))
        self.assertEqual(self.guard(), (0, []))

    def test_a_file_or_a_folder_that_a_change_adds_at_the_top_of_the_repository_is_named(self):
        # Python reads the folder it is run from ahead of its own modules, and every check is run from the top: a
        # `fnmatch.py` there took the place of the module this guard matches a pattern with, and a `unittest/`
        # there ran in place of the one that runs the tests.
        self.commit({"fnmatch.py": "new\n", "unittest/__init__.py": "new\n", "tools/deep/down/a-script.py": "new\n"})
        self.assertEqual(
            self.guard(),
            (
                1,
                [
                    f"fnmatch.py: {AT_THE_TOP}",
                    f"tools/deep/down/a-script.py: {AT_THE_TOP}",
                    f"unittest/__init__.py: {AT_THE_TOP}",
                ],
            ),
        )

    def test_a_file_added_inside_a_folder_the_repository_had_is_free(self):
        self.commit(
            {
                "sitebuild/charts.py": "new\n",
                "sitebuild/templates/parts/a-chart.html": "new\n",
                "tests/test_charts.py": "new\n",
                "docs/research/another-note.md": "new\n",
            }
        )
        self.assertEqual(self.guard(), (0, []))

    def test_a_file_that_takes_the_place_of_a_folder_at_the_top_is_named(self):
        self.on_main({"tools/a-script.py": "before\n"})
        (self.root / "tools" / "a-script.py").unlink()
        (self.root / "tools").rmdir()
        self.commit({"tools": "new\n"})
        self.assertEqual(self.guard(), (1, [f"tools: {AT_THE_TOP}"]))

    def test_the_owner_can_allow_what_a_change_adds_at_the_top(self):
        self.commit({"CHANGELOG.md": "new\n", "tools/a-script.py": "new\n"})
        self.assertEqual(self.guard("--allow", "CHANGELOG.md"), (1, [f"tools/a-script.py: {AT_THE_TOP}"]))
        self.assertEqual(self.guard("--allow", "CHANGELOG.md", "tools/*"), (0, []))

    def test_a_change_to_the_policy_is_named(self):
        self.commit({TEMPLATE: PAGE.replace("default-src 'none'", "default-src *")})
        self.assertEqual(self.guard(), (1, [f"{TEMPLATE}: {POLICY}"]))

    def test_a_policy_put_inside_a_template_comment_is_named(self):
        # The element's own text is as it was, and no page carries it, since the build leaves a comment out.
        (element,) = guard.policy(PAGE)
        self.commit({TEMPLATE: PAGE.replace(element, f"{{# {element} #}}")})
        self.assertEqual(self.guard(), (1, [f"{TEMPLATE}: {POLICY}"]))

    def test_a_change_to_the_rest_of_the_template_that_holds_the_policy_is_free(self):
        page = PAGE.replace("<p>A page</p>", "<p>A page</p>\n<p>And more of it</p>")
        page = page.replace("<title>", '<meta name="robots" content="noindex">\n<title>')
        self.assertNotEqual(page, PAGE)
        self.commit({TEMPLATE: page})
        self.assertEqual(self.guard(), (0, []))

    def test_a_policy_stated_in_another_template_is_named(self):
        self.commit({"sitebuild/templates/other.html": PAGE})
        self.assertEqual(self.guard(), (1, [f"sitebuild/templates/other.html: {POLICY}"]))

    def test_a_template_removed_with_its_policy_is_named(self):
        self.commit({TEMPLATE: None})
        self.assertEqual(self.guard(), (1, [f"{TEMPLATE}: {POLICY}"]))

    def test_a_file_added_to_the_owners_tests_and_a_line_added_to_one_are_free(self):
        search = READS.replace("AReader", "ASearch")
        self.add({"owner_tests/test_search.py": search, SENTENCES: "one\ntwo\nthree\nfour\n"})
        self.assertEqual(self.guard(), (0, []))

    def test_a_test_a_class_a_helper_a_constant_and_an_import_added_to_one_of_the_owners_tests_are_free(self):
        reads = put(READS, "import re\n", before="import unittest\n")
        reads = put(reads, A_TEST, before="\n\nif __name__")
        self.add({READER: put(reads, MORE, before="\n\nif __name__")})
        self.assertEqual(self.guard(), (0, []))

    def test_a_name_added_to_an_import_one_of_the_owners_tests_had_is_free(self):
        # The lint wants the names a file takes from one module in one import, so a new test that needs another
        # helper adds its name to the import the file had.
        self.add({READER: put(READS, "    board,\n", before="    needs_made_up_boards,\n")})
        self.assertEqual(self.guard(), (0, []))

    def test_a_name_added_to_an_import_that_the_file_gives_a_meaning_of_its_own_is_named(self):
        self.add({READER: put(READS, "    first_row,\n", before="    needs_made_up_boards,\n")})
        self.assertEqual(self.guard(), self.names(READER, "this file defines `first_row` a second time"))

    def test_the_docstring_of_a_file_and_of_a_class_of_the_owners_tests_may_change(self):
        # A new sentence can change what a file's docstring lists, and what a class's says its tests are about.
        reads = swap(READS, "can do on a board.", "can do on a board, and on a phone.")
        self.commit({READER: swap(reads, "A reader of a board.", "A reader of a board, on any screen.")})
        self.assertEqual(self.guard(), (0, []))

    def test_a_comment_and_the_layout_of_one_of_the_owners_tests_may_change(self):
        # The rule holds what a file means to Python, and a comment and where a line breaks mean nothing to it.
        reads = swap(READS, "        # The board is the first thing on the page.\n", "")
        self.commit({READER: swap(reads, "(width=WIDE)", "(\n            width=WIDE,\n        )")})
        self.assertEqual(self.guard(), (0, []))

    def test_a_return_added_to_one_of_the_owners_tests_is_named(self):
        self.add({READER: put(READS, "        return\n", before="        self.assertTrue(self.page.rows)")})
        self.assertEqual(
            self.guard(),
            self.names(READER, "this file changed, moved, or lost `AReader.test_a_reader_finds_the_board`"),
        )

    def test_a_skip_added_to_one_of_the_owners_tests_is_named(self):
        skip = '    @unittest.skip("for now")\n'
        self.add({READER: put(READS, skip, before="    def test_a_reader_finds_the_board")})
        self.assertEqual(
            self.guard(),
            self.names(READER, "this file changed, moved, or lost `AReader.test_a_reader_finds_the_board`"),
        )

    def test_a_mark_that_leaves_one_of_the_owners_tests_out_of_a_run_against_a_live_site_is_named(self):
        self.add({READER: put(READS, "    @needs_made_up_boards\n", before="    def test_a_reader_opens_a_row")})
        self.assertEqual(
            self.guard(), self.names(READER, "this file changed, moved, or lost `AReader.test_a_reader_opens_a_row`")
        )

    def test_a_skip_added_to_a_class_of_the_owners_tests_is_named(self):
        self.add({READER: put(READS, '@unittest.skip("for now")\n', before="class AReader")})
        self.assertEqual(self.guard(), self.names(READER, "this file changed, moved, or lost `AReader`"))

    def test_a_second_definition_of_what_the_owners_tests_start_from_is_named(self):
        # Whichever of the two comes later is the one every test then starts from.
        seconds = {
            "needs_made_up_boards": "\n\ndef needs_made_up_boards(test):\n    return test\n",
            "WAIT": "\nWAIT = 0\n",
            "Scenario": "\n\nclass Scenario(unittest.TestCase):\n    pass\n",
            "unittest": "\nimport owner_tests.stand_in as unittest\n",
        }
        for name, second in seconds.items():
            with self.subTest(name=name):
                self.add({SCENARIO: STARTS + second})
                self.assertEqual(self.guard(), self.names(SCENARIO, f"this file defines `{name}` a second time"))

    def test_a_second_member_of_a_class_under_a_name_the_class_had_is_named(self):
        again = "\n    def setUp(self):\n        self.skipTest('for now')\n"
        self.add({READER: put(READS, again, before="\n\nif __name__")})
        self.assertEqual(self.guard(), self.names(READER, "this file defines `AReader.setUp` a second time"))

    def test_a_filter_added_to_the_loader_of_the_owners_tests_is_named(self):
        self.on_main({LOADER: LOADS})
        self.add({LOADER: put(LOADS, "    found = unittest.TestSuite()\n", before="    return")})
        self.assertEqual(self.guard(), self.names(LOADER, "this file changed, moved, or lost `load_tests`"))

    def test_a_new_file_among_the_owners_tests_that_changes_the_others_when_it_is_imported_is_named(self):
        patches = (
            "import unittest\n\nfrom owner_tests.scenario import Scenario\n\nScenario.setUp = unittest.TestCase.setUp\n"
        )
        self.add({"owner_tests/test_nothing.py": patches})
        self.assertEqual(self.guard(), self.names("owner_tests/test_nothing.py", gained(5)))

    def test_a_statement_added_at_the_top_of_one_of_the_owners_tests_that_only_runs_is_named(self):
        # Each of these runs when the file is imported, and none is a definition that a test could be read for.
        statements = (
            "Scenario.setUp = None",
            "setattr(Scenario, 'setUp', None)",
            "for name in ('setUp', 'reader'):\n    delattr(Scenario, name)",
            "if True:\n    unittest.main()",
            "from owner_tests.stand_in import *",
            "HIGH, LOW = 900, 600",
            "print(f'{WIDE}')",
        )
        for statement in statements:
            with self.subTest(statement=statement):
                self.add({READER: f"{READS}\n{statement}\n"})
                self.assertEqual(self.guard(), self.names(READER, gained(READS.count("\n") + 2)))

    def test_one_of_the_owners_tests_that_changed_moved_or_lost_a_statement_is_named(self):
        last = '\n\nif __name__ == "__main__":\n    unittest.main()\n'
        set_up = "    def setUp(self):\n        self.page = self.reader(width=WIDE)\n\n"
        changes = {
            "`AReader.test_a_reader_opens_a_row`": swap(
                READS, "self.assertTrue(first_row", "self.assertFalse(first_row"
            ),
            "`AReader.setUp`": swap(READS, set_up, ""),
            "`AReader`": swap(READS, "class AReader(Scenario):", "class AReader(unittest.TestCase):"),
            "`WIDE`": swap(READS, "WIDE = 1440", "WIDE = 390"),
            "`Scenario`": swap(READS, "owner_tests.scenario", "owner_tests.stand_in"),
            "`needs_made_up_boards`": swap(READS, "    needs_made_up_boards,\n", ""),
            "what was on line 11": swap(READS, "in pixels.", "in points."),
            "what was on line 34": put(swap(READS, last, "\n"), last.strip() + "\n\n\n", before="class AReader"),
        }
        self.assertEqual(READS.splitlines()[33], 'if __name__ == "__main__":')
        for what, reads in changes.items():
            with self.subTest(what=what):
                self.commit({READER: reads})
                self.assertEqual(self.guard(), self.names(READER, f"this file changed, moved, or lost {what}"))

    def test_one_of_the_owners_tests_that_cannot_be_read_as_python_is_named(self):
        unread = "this file cannot be read as Python, before the change or after it"
        self.add({READER: READS + "\nclass:\n"})
        self.assertEqual(self.guard(), self.names(READER, unread))
        shell.git("update-ref", "refs/remotes/origin/main", "HEAD", cwd=self.root)
        self.commit({READER: READS})
        self.assertEqual(self.guard(), self.names(READER, unread))

    def test_a_file_among_the_owners_tests_that_is_not_python_is_named_when_it_lost_a_line(self):
        self.commit({SENTENCES: "one\ntwo, reworded\nthree\n"})
        self.assertEqual(self.guard(), self.names(SENTENCES, "this file lost a line"))

    def test_one_of_the_owners_tests_that_was_removed_is_named_even_when_it_held_no_line(self):
        self.commit({READER: None, LOADER: None})
        self.assertEqual(
            self.guard(),
            (
                1,
                [
                    f"{LOADER}: {OWNERS}: this file was removed or renamed",
                    f"{READER}: {OWNERS}: this file was removed or renamed",
                ],
            ),
        )

    def test_one_of_the_owners_tests_that_was_renamed_is_named(self):
        self.commit({READER: None, "owner_tests/test_a_reader.py": READS})
        self.assertEqual(self.guard(), self.names(READER, "this file was removed or renamed"))

    def test_a_path_the_owner_allowed_is_not_named_and_the_rest_still_are(self):
        self.commit(
            {"pyproject.toml": "after\n", "uv.lock": "after\n", "docs/adr/README.md": "new\n", SENTENCES: "one\n"}
        )
        self.assertEqual(
            self.guard("--allow", "pyproject.toml", "docs/adr/*"),
            (1, [f"{SENTENCES}: {OWNERS}: this file lost a line", "uv.lock: a dependency"]),
        )
        self.assertEqual(
            self.guard("--allow", "pyproject.toml", "uv.lock", "--allow", "docs/*", "owner_tests/*"), (0, [])
        )

    def test_allowing_a_template_lets_its_policy_change(self):
        self.commit({TEMPLATE: PAGE.replace("default-src 'none'", "default-src *")})
        self.assertEqual(self.guard("--allow", TEMPLATE), (0, []))

    def test_what_main_changed_after_the_branch_began_is_not_the_branchs_change(self):
        feature = self.commit({"README.md": "after\n"})
        shell.git("checkout", "--quiet", "--detach", self.base, cwd=self.root)
        self.on_main({"uv.lock": "main moved on\n"})
        shell.git("checkout", "--quiet", "--detach", feature, cwd=self.root)
        self.assertEqual(self.guard(), (0, []))

    def test_it_reads_the_change_between_the_two_commits_it_is_given(self):
        first = self.commit({"uv.lock": "after\n"})
        second = self.commit({"README.md": "after\n"})
        self.assertEqual(self.guard("--base", self.base, "--head", first), (1, ["uv.lock: a dependency"]))
        self.assertEqual(self.guard("--base", first, "--head", second), (0, []))

    def test_a_copy_of_it_in_another_folder_reads_the_repository_it_is_pointed_at(self):
        # The ship script runs main's copy from a temporary folder, with the rules and the shell and nothing more.
        self.commit({"uv.lock": "after\n"})
        elsewhere = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (elsewhere / "sitework").mkdir()
        for name in ("__init__.py", "__main__.py", "guard.py", "rules.py", "shell.py"):
            shutil.copy(ROOT / "sitework" / name, elsewhere / "sitework" / name)
        result = subprocess.run(
            [sys.executable, "-m", "sitework", "guard", "--repository", str(self.root)],
            cwd=elsewhere,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        self.assertEqual((result.returncode, result.stdout, result.stderr), (1, "uv.lock: a dependency\n", ""))


class TheSitesOwnOwnersTests(unittest.TestCase):
    """The rule for the owner's tests, read against the tests the site has."""

    def test_each_of_them_compared_with_itself_is_read_as_python_and_only_added_to(self):
        files = sorted((ROOT / "owner_tests").glob("*.py"))
        self.assertIn(ROOT / "owner_tests" / "scenario.py", files)
        for file in files:
            with self.subTest(file=file.name):
                text = file.read_text(encoding="utf-8")
                self.assertIsNone(guard.more_than_added(text, text))

    def test_each_file_of_tests_among_them_would_be_free_as_a_new_file(self):
        # A file of tests written as these are must be free to add, so the rule allows every kind of statement
        # that stands at the top of one, the two lines that run the file as a program among them.
        files = sorted((ROOT / "owner_tests").glob("test_*.py"))
        self.assertIn(ROOT / "owner_tests" / "test_a_board.py", files)
        for file in files:
            with self.subTest(file=file.name):
                self.assertIsNone(guard.more_than_added("", file.read_text(encoding="utf-8")))


class ThePolicy(unittest.TestCase):
    """What the guard reads as the policy's own text."""

    def test_the_policy_of_the_sites_page_template_is_read_whole(self):
        (policy,) = guard.policy((ROOT / TEMPLATE).read_text(encoding="utf-8"))
        self.assertTrue(policy.startswith('<meta http-equiv="Content-Security-Policy" content="default-src '), policy)
        self.assertTrue(policy.endswith("form-action 'none'\">"), policy)

    def test_a_comparison_inside_a_template_tag_does_not_end_the_element_early(self):
        policy = (
            '<meta http-equiv="Content-Security-Policy" content="{% if rows > 3 %}connect-src \'self\'{% endif %}">'
        )
        self.assertEqual(guard.policy(f"<head>\n{policy}\n<title>A page</title>\n</head>"), [policy])

    def test_what_a_template_comment_holds_is_no_part_of_the_policy(self):
        policy = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'">'
        for comment in (f"{{# {policy} #}}", f"{{#-\nA note, and after it the element.\n{policy}\n-#}}"):
            with self.subTest(comment=comment):
                self.assertEqual(guard.policy(f"<head>\n{comment}\n<title>A page</title>\n</head>"), [])
        self.assertEqual(guard.policy(f"<head>\n{{# The policy. #}}\n{policy}\n{{# The title. #}}\n</head>"), [policy])
        noted = policy.replace(" content=", " {# what a page may load > #}content=")
        self.assertEqual(guard.policy(f"<head>\n{noted}\n</head>"), [policy])

    def test_an_element_that_states_no_policy_is_not_part_of_it(self):
        self.assertEqual(
            guard.policy('<meta charset="utf-8">\n<meta name="viewport" content="width=device-width">'), []
        )


if __name__ == "__main__":
    unittest.main()
