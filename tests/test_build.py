"""The generator, run the way the workflow runs it: `python -m sitebuild <folder> [--noindex]`."""

import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build(out: Path, *options: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "sitebuild", str(out), *options],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


class Page(HTMLParser):
    """The parts of a built page that the tests read."""

    def __init__(self, html: str):
        super().__init__()
        self.head_meta: list[dict[str, str | None]] = []
        self.text: dict[str, str] = {}
        self._open: list[str] = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "meta" and "head" in self._open:
            self.head_meta.append(dict(attrs))
        if tag not in ("meta", "link"):
            self._open.append(tag)

    def handle_endtag(self, tag):
        if tag in self._open:
            del self._open[len(self._open) - 1 - self._open[::-1].index(tag)]

    def handle_data(self, data):
        if self._open and data.strip():
            tag = self._open[-1]
            self.text[tag] = (self.text.get(tag, "") + " " + data.strip()).strip()

    def robots(self) -> list[str | None]:
        return [meta.get("content") for meta in self.head_meta if meta.get("name") == "robots"]


class TheBuild(unittest.TestCase):
    def setUp(self):
        self.out = Path(self.enterContext(tempfile.TemporaryDirectory())) / "dist"

    def built_page(self, *options: str) -> Page:
        result = build(self.out, *options)
        self.assertEqual(result.returncode, 0, result.stderr)
        return Page((self.out / "index.html").read_text(encoding="utf-8"))

    def test_it_builds_one_placeholder_page_that_says_what_the_site_is(self):
        page = self.built_page()
        self.assertEqual([p.name for p in self.out.rglob("*")], ["index.html"])
        self.assertEqual(page.text["title"], "Rising Repos")
        self.assertEqual(page.text["h1"], "Rising Repos")
        self.assertIn("GitHub repositories gaining stars faster than their own pace", page.text["p"])

    def test_pages_built_for_the_preview_ask_search_engines_not_to_index_them(self):
        self.assertEqual(self.built_page("--noindex").robots(), ["noindex"])
        html = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertIn('<meta name="robots" content="noindex">', html)

    def test_pages_built_without_the_option_carry_no_robots_tag(self):
        self.assertEqual(self.built_page().robots(), [])

    def test_a_folder_that_already_holds_files_is_refused_and_left_as_it_was(self):
        self.out.mkdir()
        (self.out / "keep.txt").write_text("kept", encoding="utf-8")
        result = build(self.out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(self.out), result.stderr)
        self.assertEqual([p.name for p in self.out.iterdir()], ["keep.txt"])
        self.assertEqual((self.out / "keep.txt").read_text(encoding="utf-8"), "kept")


if __name__ == "__main__":
    unittest.main()
