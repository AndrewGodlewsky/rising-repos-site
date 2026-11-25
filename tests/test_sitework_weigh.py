"""`weigh` says what a change adds to the pages, in bytes: `python -m sitework weigh` (#80).

No test builds the site. Two folders of made-up pages stand in for the site before a change and after it.
"""

import gzip
import tempfile
import unittest
from pathlib import Path

import test_page_weight

from sitework import weigh


def write(folder: Path, files: dict[str, str]) -> Path:
    for path, text in files.items():
        (folder / path).parent.mkdir(parents=True, exist_ok=True)
        (folder / path).write_text(text, encoding="utf-8", newline="\n")
    return folder


class TheWeights(unittest.TestCase):
    def report(self, base: dict[str, str], head: dict[str, str]) -> str:
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        return weigh.report(write(folder / "base", base), write(folder / "head", head))

    def rows(self, report: str) -> list[list[str]]:
        table = [line for line in report.splitlines() if line.startswith("|")]
        return [[cell.strip() for cell in line.strip("|").split("|")] for line in table[2:]]

    def test_each_kind_gives_its_heaviest_page_before_and_after_the_change_and_what_was_added(self):
        base = {
            "index.html": "r" * 100,
            "days/2026-11-22/index.html": "d" * 300,
            "days/2026-11-23/index.html": "d" * 200,
        }
        head = {
            "index.html": "r" * 100,
            "days/2026-11-22/index.html": "d" * 340,
            "days/2026-11-23/index.html": "d" * 240,
        }
        self.assertEqual(
            self.rows(self.report(base, head)),
            [
                ["The root", "`/`", "100", "100", "the same", "499,900"],
                ["A board day", "`/days/2026-11-22/`", "300", "340", "+40", "499,660"],
            ],
        )

    def test_a_page_the_base_does_not_have_is_said_to_be_new(self):
        rows = self.rows(self.report({"index.html": "r"}, {"index.html": "r", "baseline/index.html": "b" * 50}))
        self.assertEqual(rows[1], ["Baseline", "`/baseline/`", "-", "50", "new", "499,950"])

    def test_the_root_is_given_gzipped_as_the_size_test_packs_it(self):
        before, after = "<p>row</p>" * 40, "<p>row</p>" * 40 + "<a>Latest</a>"
        was = len(gzip.compress(before.encode(), compresslevel=6, mtime=0))
        now = len(gzip.compress(after.encode(), compresslevel=6, mtime=0))
        report = self.report({"index.html": before}, {"index.html": after})
        self.assertIn(f"The root gzipped at level 6: {was:,} before, {now:,} after ({now - was:+,}).", report)

    def test_the_two_limits_it_names_are_the_size_tests_own(self):
        self.assertEqual(
            (weigh.PAGE_LIMIT, weigh.WIRE_BUDGET), (test_page_weight.SIZE_LIMIT, test_page_weight.WIRE_BUDGET)
        )


if __name__ == "__main__":
    unittest.main()
