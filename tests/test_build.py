"""The generator, run the way the workflow runs it: `python -m sitebuild <folder> [--noindex]`."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOINDEX = '<meta name="robots" content="noindex">'


def build(out: Path, *options: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "sitebuild", str(out), *options],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


class TheBuild(unittest.TestCase):
    def setUp(self):
        self.out = Path(self.enterContext(tempfile.TemporaryDirectory())) / "dist"

    def built_head_and_body(self, *options: str) -> tuple[str, str]:
        result = build(self.out, *options)
        self.assertEqual(result.returncode, 0, result.stderr)
        head, body = (self.out / "index.html").read_text(encoding="utf-8").split("</head>")
        return head, body

    def test_it_builds_one_placeholder_page_that_says_what_the_site_is(self):
        head, body = self.built_head_and_body()
        self.assertEqual([path.name for path in self.out.rglob("*")], ["index.html"])
        self.assertIn("<title>Rising Repos</title>", head)
        self.assertIn("<h1>Rising Repos</h1>", body)
        self.assertIn("lists the GitHub repositories gaining stars faster than their own pace predicts", body)

    def test_pages_built_for_the_preview_ask_search_engines_not_to_index_them(self):
        head, body = self.built_head_and_body("--noindex")
        self.assertEqual(head.count('name="robots"'), 1)
        self.assertIn(NOINDEX, head)
        self.assertNotIn('name="robots"', body)

    def test_pages_built_without_the_option_carry_no_robots_tag(self):
        head, body = self.built_head_and_body()
        self.assertNotIn('name="robots"', head + body)

    def test_a_folder_that_already_holds_files_is_refused_and_left_as_it_was(self):
        self.out.mkdir()
        (self.out / "keep.txt").write_text("kept", encoding="utf-8")
        result = build(self.out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(self.out), result.stderr)
        self.assertEqual([path.name for path in self.out.iterdir()], ["keep.txt"])
        self.assertEqual((self.out / "keep.txt").read_text(encoding="utf-8"), "kept")


if __name__ == "__main__":
    unittest.main()
