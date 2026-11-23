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

from sitework import guard, shell

GUARDED = {
    ".github/workflows/deploy.yml": "a workflow",
    ".github/dependabot.yml": "a workflow",
    "pyproject.toml": "a dependency",
    "uv.lock": "a dependency",
    ".python-version": "a dependency",
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
    "docs/workflow-notes/2026-11-23.md": "the look back's notes",
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
    "sitebuild/__init__.py",
    "sitebuild/templates/site.css",
    "sitebuild/templates/site.js",
    "tests/test_build.py",
    "tests/helpers.py",
    "tests/fixtures/contract-example/boards/index.json",
    "docs/research/a-note.md",
    "docs/pyproject.toml",
    "sitebuild/AGENTS.md",
]
"""What a feature is made of, and two files that share only a name with a guarded one."""

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
OWNERS = "the owner's tests, which a change adds to and takes nothing from"
READER = "owner_tests/test_reader.py"


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
        owners = {"owner_tests/__init__.py": "", READER: "one\ntwo\nthree\n"}
        self.base = self.on_main({**before, **owners, TEMPLATE: PAGE})

    def guard(self, *arguments: str) -> tuple[int, list[str]]:
        return said(guard.main, "guard", "--repository", str(self.root), *arguments)

    def test_a_change_to_a_workflow_is_named(self):
        self.commit({".github/workflows/deploy.yml": "after\n"})
        self.assertEqual(self.guard(), (1, [".github/workflows/deploy.yml: a workflow"]))

    def test_every_guarded_path_is_named_with_why_it_is_guarded(self):
        self.commit(dict.fromkeys(GUARDED, "after\n"))
        self.assertEqual(self.guard(), (1, [f"{path}: {why}" for path, why in sorted(GUARDED.items())]))

    def test_a_guarded_path_that_a_change_adds_or_removes_is_named(self):
        self.commit({"docs/adr/0009-a-new-record.md": "new\n", "uv.lock": None})
        self.assertEqual(
            self.guard(),
            (1, ["docs/adr/0009-a-new-record.md: the standards and the decision records", "uv.lock: a dependency"]),
        )

    def test_a_change_to_the_pages_their_tests_and_their_documents_touches_nothing_guarded(self):
        self.commit(dict.fromkeys(FREE, "after\n"))
        self.assertEqual(self.guard(), (0, []))

    def test_a_change_to_the_policy_is_named(self):
        self.commit({TEMPLATE: PAGE.replace("default-src 'none'", "default-src *")})
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
        self.commit({"owner_tests/test_search.py": "new\n", READER: "one\ntwo\nthree\nfour\n"})
        self.assertEqual(self.guard(), (0, []))

    def test_one_of_the_owners_tests_that_lost_a_line_is_named(self):
        self.commit({READER: "one\ntwo, reworded\nthree\n"})
        self.assertEqual(self.guard(), (1, [f"{READER}: {OWNERS}: this file lost a line"]))

    def test_one_of_the_owners_tests_that_was_removed_is_named_even_when_it_held_no_line(self):
        self.commit({READER: None, "owner_tests/__init__.py": None})
        self.assertEqual(
            self.guard(),
            (
                1,
                [
                    f"owner_tests/__init__.py: {OWNERS}: this file was removed or renamed",
                    f"{READER}: {OWNERS}: this file was removed or renamed",
                ],
            ),
        )

    def test_one_of_the_owners_tests_that_was_renamed_is_named(self):
        self.commit({READER: None, "owner_tests/test_a_reader.py": "one\ntwo\nthree\n"})
        self.assertEqual(self.guard(), (1, [f"{READER}: {OWNERS}: this file was removed or renamed"]))

    def test_a_path_the_owner_allowed_is_not_named_and_the_rest_still_are(self):
        self.commit({"pyproject.toml": "after\n", "uv.lock": "after\n", "docs/adr/README.md": "new\n", READER: "one\n"})
        self.assertEqual(
            self.guard("--allow", "pyproject.toml", "docs/adr/*"),
            (1, [f"{READER}: {OWNERS}: this file lost a line", "uv.lock: a dependency"]),
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

    def test_an_element_that_states_no_policy_is_not_part_of_it(self):
        self.assertEqual(
            guard.policy('<meta charset="utf-8">\n<meta name="viewport" content="width=device-width">'), []
        )


if __name__ == "__main__":
    unittest.main()
