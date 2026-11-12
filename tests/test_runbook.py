"""The runbook names the lines that going live changes, and those lines are what the files hold.

RUNBOOK.md has a table of each line that the change taking the site live edits: the line before go-live, and
the line after it. These tests hold the table to the files, before the switch and after it:

- each row's file holds the row's line before go-live or its line after, once, so the change has one place to
  make each edit;
- every row is on the same side, because a switch made half way would upload to production while a check still
  reads the preview, or the other way round;
- every line of a workflow or of the eval's code that names the preview or the live address, or sets the Pages
  branch, is in the table, so a line added later cannot be missed at the switch. A comment is left out: it says
  why, and is rewritten with the line beside it. A docstring or a string is not a comment, so it counts.
"""

import re
import unittest
from typing import NamedTuple

from helpers import ROOT

RUNBOOK = ROOT / "RUNBOOK.md"
TABLE_HEADING = "## The lines the switch changes"
ADDRESSES = ("preview.risingrepos.pages.dev", "risingrepos.com")
CODE = re.compile(r"`([^`]+)`")
"""A cell that is one code span, and nothing else."""

SCANNED = (".github/workflows/*.yml", "evals/site/*.py")
"""The files whose lines decide where the site is uploaded, which address its checks read, and which address the
eval measures."""


class Row(NamedTuple):
    file: str
    before: str
    after: str


def rows() -> list[Row]:
    """Each row of the runbook's table, after its heading row and the line under that: the file, the line before
    go-live, and the line after it, each as one code span."""
    lines = RUNBOOK.read_text(encoding="utf-8").splitlines()
    table = []
    for line in lines[lines.index(TABLE_HEADING) + 1 :]:
        if line.startswith("## "):
            break
        if line.startswith("|"):
            table.append(line)
    found = []
    for line in table[2:]:
        matches = [CODE.fullmatch(cell.strip()) for cell in line.strip().strip("|").split("|")]
        if len(matches) != 3 or None in matches:
            raise AssertionError(f"a row of the runbook's table does not give its file and two lines as code: {line}")
        found.append(Row(*(match.group(1) for match in matches)))
    return found


def held(file: str) -> list[str]:
    """The lines of `file`, each without the space around it."""
    return [line.strip() for line in (ROOT / file).read_text(encoding="utf-8").splitlines()]


def lines_that_decide_the_address() -> set[tuple[str, str]]:
    """Each line, outside a comment, of the scanned files that names either address or sets the Pages branch."""
    found = set()
    for pattern in SCANNED:
        for path in ROOT.glob(pattern):
            file = path.relative_to(ROOT).as_posix()
            for line in held(file):
                if line.startswith("#"):
                    continue
                if any(address in line for address in ADDRESSES) or line.startswith("PAGES_BRANCH:"):
                    found.add((file, line))
    return found


class TheRunbook(unittest.TestCase):
    def test_its_table_lists_the_lines_the_switch_changes(self):
        self.assertGreater(len(rows()), 0)

    def test_each_rows_file_holds_its_line_before_go_live_or_its_line_after_once(self):
        for row in rows():
            with self.subTest(file=row.file, before=row.before):
                self.assertTrue((ROOT / row.file).is_file(), f"{row.file} is not a file of this repository")
                lines = held(row.file)
                self.assertEqual(sorted([lines.count(row.before), lines.count(row.after)]), [0, 1])

    def test_every_row_is_on_the_same_side_of_the_switch(self):
        sides = {row: row.before in held(row.file) for row in rows()}
        before = [f"{row.file}: {row.before}" for row, side in sides.items() if side]
        after = [f"{row.file}: {row.after}" for row, side in sides.items() if not side]
        self.assertFalse(before and after, f"half switched. Before go-live: {before}. After: {after}")

    def test_every_line_of_a_workflow_or_the_eval_that_names_an_address_is_in_its_table(self):
        listed = {(row.file, line) for row in rows() for line in (row.before, row.after)}
        for file, line in sorted(lines_that_decide_the_address()):
            with self.subTest(file=file, line=line):
                self.assertIn((file, line), listed)

    def test_the_readme_links_to_it(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertTrue("](RUNBOOK.md)" in readme, "README.md has no link to RUNBOOK.md")


if __name__ == "__main__":
    unittest.main()
