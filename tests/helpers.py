"""What the tests share: running the generator as deploy.yml's build job runs it, a copy of the contract's
example to change, a reading of a built page, and a reading of a workflow file."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "tests" / "fixtures" / "contract-example"
"""The data contract's example and schemas, laid out as site-data/ is. site-data/ holds the same files until
the daily publish replaces them. Every test but one builds from this copy, so that the day's data does not
change what they check. The one that builds from site-data/ shows that the build reads it when no folder is
given."""

SECRET = re.compile(r"\bsecrets\b")
"""A reference to the repository's secrets, anywhere in a workflow."""


def load_workflow(name: str) -> dict:
    """The workflow `.github/workflows/<name>`, as YAML reads it."""
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"))
    workflow["on"] = workflow.pop(True)  # YAML 1.1 reads the key `on` as true
    return workflow


def build(out: Path, *options: str) -> subprocess.CompletedProcess:
    """Run `python -m sitebuild <out> <options>` from the repository, as deploy.yml's build job does."""
    return subprocess.run(
        [sys.executable, "-m", "sitebuild", str(out), *options],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


class BuildTest(unittest.TestCase):
    """A test with a temporary folder, a copy of the example in it to change, and a folder to build into."""

    def setUp(self):
        temporary = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.data = temporary / "site-data"
        shutil.copytree(EXAMPLE, self.data)
        self.out = temporary / "dist"

    @property
    def index(self) -> Path:
        return self.data / "boards" / "index.json"

    @property
    def daily_schema(self) -> Path:
        return self.data / "contract" / "daily.schema.json"

    @property
    def index_schema(self) -> Path:
        return self.data / "contract" / "index.schema.json"

    def board_file(self, day: str = "2026-11-09") -> Path:
        return self.data / "boards" / "days" / day / "daily.json"

    def build_data(self, *options: str) -> subprocess.CompletedProcess:
        return build(self.out, "--data", str(self.data), *options)

    def build_pages(self, *options: str) -> dict[str, "Page"]:
        """Build from the copy, expect success, and read every page the build wrote, by its path in the site."""
        result = self.build_data(*options)
        self.assertEqual(result.returncode, 0, result.stderr)
        return {
            path.relative_to(self.out).as_posix(): Page(path.read_text(encoding="utf-8"))
            for path in sorted(self.out.rglob("*.html"))
        }

    def assertBuildFails(self, *names: str) -> str:
        """Expect the build to fail, write nothing, and name each of `names` in its message."""
        result = self.build_data()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for name in names:
            self.assertIn(name, result.stderr)
        self.assertFalse(self.out.exists() and any(self.out.iterdir()), "a failed build wrote pages")
        return result.stderr


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
BLOCK = {
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt", "footer", "h1", "h2", "h3",
    "h4", "header", "hr", "li", "main", "nav", "ol", "p", "section", "table", "td", "th", "tr", "ul",
}


class Element:
    def __init__(self, tag: str, attrs: dict[str, str | None], parent: "Element | None"):
        self.tag, self.attrs, self.parent = tag, attrs, parent
        self.children: list[Element | str] = []

    def elements(self):
        """This element and every element inside it, in document order."""
        yield self
        for child in self.children:
            if isinstance(child, Element):
                yield from child.elements()

    def all(self, tag: str | None = None) -> list["Element"]:
        """Every element inside this one, or every one with the tag `tag`, in document order."""
        return [element for element in self.elements() if element is not self and tag in (None, element.tag)]

    def text(self) -> str:
        """The text inside the element as a reader sees it: entities decoded, a block set apart from what is
        around it, and runs of white space made one space."""
        parts = []
        for child in self.children:
            if isinstance(child, str):
                parts.append(child)
            else:
                parts.append(f" {child.text()} " if child.tag in BLOCK else child.text())
        return " ".join("".join(parts).split())

    def classes(self) -> list[str]:
        return (self.attrs.get("class") or "").split()


class _TreeBuilder(HTMLParser):
    """Reads HTML into a tree of elements. An end tag closes every element left open inside its own."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.document = self._open = Element("#document", {}, None)

    def handle_starttag(self, tag, attrs):
        element = Element(tag, dict(attrs), self._open)
        self._open.children.append(element)
        if tag not in VOID:
            self._open = element

    def handle_startendtag(self, tag, attrs):
        self._open.children.append(Element(tag, dict(attrs), self._open))

    def handle_endtag(self, tag):
        element = self._open
        while element is not self.document and element.tag != tag:
            element = element.parent
        if element is not self.document:
            self._open = element.parent

    def handle_data(self, data):
        self._open.children.append(data)


class Page:
    """A built page, read into a tree of elements."""

    def __init__(self, html: str):
        self.html = html
        builder = _TreeBuilder()
        builder.feed(html)
        builder.close()
        self.document = builder.document

    def all(self, tag: str | None = None) -> list[Element]:
        return self.document.all(tag)

    def one(self, tag: str) -> Element:
        (element,) = self.all(tag)
        return element

    def meta(self, name: str) -> list[str]:
        """The content of each <meta name="<name>">."""
        return [element.attrs.get("content") for element in self.all("meta") if element.attrs.get("name") == name]

    def links(self) -> list[tuple[str, str]]:
        """Each link on the page, in order: its address and its text."""
        return [(element.attrs.get("href"), element.text()) for element in self.all("a")]

    def rows(self) -> list[Element]:
        """The board's rows, in order. Each design marks the element that holds a row with the class `row`."""
        return [element for element in self.all() if "row" in element.classes()]

    def body_text(self) -> str:
        return self.one("body").text()
