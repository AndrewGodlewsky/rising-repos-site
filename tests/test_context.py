"""The standards, the decision records, the glossary, and AGENTS.md each say what is true of the files.

An agent reads these four before it plans or builds a change. A line in one of them that names a test, a file, or
a heading that is gone sends that agent wrong, and nothing fails. These tests hold each of the four to the files:

- every standard in STANDARDS.md says once what holds it, and each test or limit of the site eval it names exists;
- the decision records in docs/adr/ are numbered in order, and each test a record names exists;
- every term in GLOSSARY.md is used somewhere in the pages, the code, the tests, or the documents;
- every path AGENTS.md names is a file or a folder here, and every part of a document it names is a heading or a
  bold lead of that document.

They show that a named test exists, and not that it proves what the line says it proves. That is the reviewer's to
judge when the line is written.
"""

import ast
import json
import re
import unittest
from pathlib import Path
from typing import NamedTuple

from helpers import ROOT

STANDARDS = ROOT / "STANDARDS.md"
RECORDS = ROOT / "docs" / "adr"
GLOSSARY = ROOT / "GLOSSARY.md"
MAP = ROOT / "AGENTS.md"
LIMITS = ROOT / "evals" / "site" / "limits.json"

CODE = re.compile(r"`([^`]+)`")
TEST_ID = re.compile(r"tests/[\w/]+\.py::\w+::\w+")
"""A test as these documents name one: its file, its class, and its name."""

LINK = re.compile(r"\]\(([^)\s]+)\)")
LEAD = re.compile(r"^\*\*([BPC])(\d+)\. ", re.MULTILINE)
"""The start of a standard: its part's letter and its number, in bold, at the start of a line."""

RECORD = re.compile(r"\d{4}-[a-z0-9-]+\.md")
TERM = re.compile(r"^\*\*([^*\n]+)\*\*:$", re.MULTILINE)

USED_IN = (
    "README.md",
    "RUNBOOK.md",
    "AGENTS.md",
    "evals/site/*.md",
    "evals/site/*.py",
    "sitebuild/**/*.py",
    "sitebuild/templates/*.html",
    "sitebuild/templates/*.css",
    "sitebuild/templates/*.js",
    ".github/workflows/*.yml",
    "tests/*.py",
    "tests/*.js",
)
"""Where a term of the glossary has to be used: the pages, the code, the tests, and the documents. The glossary,
the standards, and the decision records are left out, since they are written in the glossary's words by rule."""

FENCED = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
ELSEWHERE = re.compile(r'RisingRepos:\s*`[^`]+`(?:,\s*"[^"]+")?')
"""How AGENTS.md names a path in RisingRepos, with the part of that file it means if it names one."""

SUFFIXES = (".md", ".py", ".yml", ".json", ".js", ".css", ".html", ".toml", ".lock")
NAMED = re.compile(r'((?:[\w.-]+/)*[\w.-]+\.md)|"([^"]+)"')
"""A document by its path, or a phrase in double quotes."""


def what_is_wrong_with(test_id: str) -> str | None:
    """Why `test_id`, written `tests/<file>.py::<Class>::<test>`, names no test. None when it names one."""
    file, cls, name = test_id.split("::")
    path = ROOT / file
    if not path.is_file():
        return f"{file} is not a file"
    classes = [node for node in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(node, ast.ClassDef)]
    found = [node for node in classes if node.name == cls]
    if not found:
        return f"{file} has no class {cls}"
    if not any(isinstance(node, ast.FunctionDef) and node.name == name for node in found[0].body):
        return f"{cls} in {file} has no test {name}"
    return None


def broken_links(path: Path) -> list[str]:
    """Each link in `path` to a file of this repository that is not there. A link to another site is left alone."""
    found = []
    for target in LINK.findall(path.read_text(encoding="utf-8")):
        file = target.split("#")[0]
        if "://" in target or not file:
            continue
        if not (path.parent / file).exists():
            found.append(target)
    return found


class Standard(NamedTuple):
    number: str
    text: str


def standards() -> list[Standard]:
    """Each standard: its number, and its text from its bold lead to the next standard or the next heading."""
    text = STANDARDS.read_text(encoding="utf-8")
    leads = list(LEAD.finditer(text))
    found = []
    for lead, after in zip(leads, [*leads[1:], None], strict=True):
        body = text[lead.start() : after.start() if after else len(text)]
        found.append(Standard(lead.group(1) + lead.group(2), re.split(r"^## ", body, flags=re.MULTILINE)[0]))
    return found


def holders(standard: Standard) -> list[str]:
    """What follows each "Held by" that starts a line of the standard, to the standard's end."""
    return re.split(r"^Held by\b", standard.text, flags=re.MULTILINE)[1:]


def limits() -> set[str]:
    """The numbers the site eval holds to a limit on both of its profiles."""
    by_profile = json.loads(LIMITS.read_text(encoding="utf-8"))
    return set(by_profile["phone"]) & set(by_profile["desktop"])


def records() -> list[Path]:
    """Every file in docs/adr/ but its README, in the order of their names."""
    return sorted(path for path in RECORDS.iterdir() if path.name != "README.md")


def confirmed_by(record: Path) -> str:
    """The record's section on what confirms it, to the next heading or the record's end."""
    return record.read_text(encoding="utf-8").split("\n## Confirmed by\n", 1)[1].split("\n## ", 1)[0]


def plain(text: str) -> str:
    """`text` in lower case, with a hyphen or an underscore read as a space, so that `star_history` in a file and
    "Star history" in the glossary are the same words."""
    return " ".join(re.sub(r"[_-]", " ", text.lower().replace("’", "'")).split())


def used() -> str:
    """Everything the files of `USED_IN` say, as `plain` reads it."""
    return plain("\n".join(path.read_text(encoding="utf-8") for pattern in USED_IN for path in ROOT.glob(pattern)))


def here(text: str) -> str:
    """AGENTS.md's text without its code blocks, and without what it says is in RisingRepos."""
    return ELSEWHERE.sub("", FENCED.sub("", text))


def paths_named(text: str) -> list[str]:
    """Each path the text names in this repository: a code span that begins with a file or a folder of the
    repository's root, or that has a folder and a file's ending, and each link that is not to another site."""
    top = {entry.name for entry in ROOT.iterdir()}
    found = []
    for span in CODE.findall(" ".join(here(text).split())):
        if re.search(r"[\s<*]", span):
            continue
        if span.rstrip("/").split("/")[0] in top or ("/" in span and span.endswith(SUFFIXES)):
            found.append(span)
    links = [target.split("#")[0] for target in LINK.findall(here(text)) if "://" not in target]
    return found + [link for link in links if link]


def units(text: str) -> list[str]:
    """The text a sentence at a time: each row of a table, and each sentence of a paragraph or of a list's item."""
    found = []
    for block in re.split(r"\n\s*\n", here(text)):
        lines = [line for line in block.splitlines() if line.strip()]
        if lines and all(line.startswith("|") for line in lines):
            found += lines
            continue
        for item in re.split(r"^(?=- |\d+\. )", block, flags=re.MULTILINE):
            found += re.split(r'(?<=[.!?])\s+(?=[A-Z\[`"*])', " ".join(item.split()))
    return [unit for unit in found if unit.strip()]


def parts_named(text: str) -> list[tuple[str, str]]:
    """Each part of a document the text names: a phrase in double quotes, with the document named before it in the
    same sentence, row, or item. A quoted phrase with no document before it names no part."""
    found = []
    for unit in units(text):
        document = None
        for match in NAMED.finditer(unit):
            if match.group(1):
                document = match.group(1)
            elif document:
                found.append((document, match.group(2)))
    return found


def parts_of(document: str) -> set[str]:
    """What a reader can find in a document by name: each heading, and each run of bold text without its full stop."""
    text = (ROOT / document).read_text(encoding="utf-8")
    headings = re.findall(r"^#{1,6} (.+)$", text, re.MULTILINE)
    leads = re.findall(r"\*\*([^*]+?)\.?\*\*", " ".join(text.split()))
    return {part.strip() for part in headings + leads}


class TheStandards(unittest.TestCase):
    def test_each_of_the_three_parts_holds_standards(self):
        self.assertEqual({standard.number[0] for standard in standards()}, {"B", "P", "C"})

    def test_each_standard_says_once_what_holds_it(self):
        for standard in standards():
            with self.subTest(standard.number):
                held = holders(standard)
                self.assertEqual(
                    len(held),
                    1,
                    f'{standard.number} has {len(held)} lines that start "Held by". Give it one, after its rule.',
                )
                self.assertTrue(
                    CODE.search(held[0]) or "the reviewer" in held[0],
                    f"{standard.number} names nothing that holds it. "
                    "Name a test, a limit of the site eval, or the reviewer.",
                )

    def test_each_test_and_each_limit_a_standard_names_exists(self):
        for standard in standards():
            for held in holders(standard):
                for name in CODE.findall(held):
                    with self.subTest(standard=standard.number, name=name):
                        if "::" in name:
                            self.assertIsNone(
                                what_is_wrong_with(name),
                                f"{standard.number} is held by a test that is gone. Name the test that holds it now, "
                                "or say that the reviewer does.",
                            )
                        else:
                            self.assertIn(
                                name,
                                limits(),
                                f"{standard.number} names `{name}` after Held by, which is neither a test, written "
                                "tests/<file>.py::<Class>::<test>, nor a limit in evals/site/limits.json.",
                            )

    def test_no_number_is_used_twice_and_each_parts_numbers_rise(self):
        numbers = [standard.number for standard in standards()]
        self.assertEqual(len(numbers), len(set(numbers)), "a standard's number is used twice")
        for part in "BPC":
            of_part = [int(number[1:]) for number in numbers if number[0] == part]
            self.assertEqual(of_part, sorted(of_part), f"part {part}'s standards are out of order")

    def test_each_link_leads_to_a_file_here(self):
        self.assertEqual(broken_links(STANDARDS), [])


class TheDecisionRecords(unittest.TestCase):
    def test_the_records_are_numbered_from_0001_with_no_gap_and_nothing_else_is_in_the_folder(self):
        names = [record.name for record in records()]
        for name in names:
            self.assertRegex(name, RECORD, "docs/adr/ holds its README.md and records named <number>-<slug>.md")
        self.assertEqual(
            [int(name[:4]) for name in names],
            list(range(1, len(names) + 1)),
            "A record takes the next number, and a record that is replaced stays (docs/adr/README.md).",
        )

    def test_each_record_has_a_title_a_status_and_says_what_confirms_it(self):
        for record in records():
            with self.subTest(record.name):
                text = record.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("# "), "a record begins with its title")
                for heading in ("## Status", "## Confirmed by"):
                    self.assertIn(f"\n{heading}\n", text, f"a record has a section {heading} (docs/adr/README.md)")

    def test_each_test_a_record_names_exists_or_the_record_says_that_no_check_holds_it(self):
        for record in records():
            section = confirmed_by(record)
            named = TEST_ID.findall(section)
            with self.subTest(record.name):
                if not named:
                    self.assertIn("No check holds this", section)
            for name in named:
                with self.subTest(record=record.name, name=name):
                    self.assertIsNone(
                        what_is_wrong_with(name),
                        "The record is confirmed by a test that is gone. Name the test that would fail now if the "
                        "decision were undone.",
                    )

    def test_each_link_leads_to_a_file_here(self):
        for record in [*records(), RECORDS / "README.md"]:
            with self.subTest(record.name):
                self.assertEqual(broken_links(record), [])


class TheGlossary(unittest.TestCase):
    def test_no_term_is_defined_twice(self):
        terms = [plain(term) for term in TERM.findall(GLOSSARY.read_text(encoding="utf-8"))]
        self.assertGreater(len(terms), 0)
        self.assertEqual(sorted(terms), sorted(set(terms)))

    def test_each_term_is_used_in_the_pages_the_code_the_tests_or_the_documents(self):
        text = used()
        for term in TERM.findall(GLOSSARY.read_text(encoding="utf-8")):
            with self.subTest(term):
                self.assertIn(
                    plain(term),
                    text,
                    f'Nothing here says "{term}". Take the term out of GLOSSARY.md, or give it the name the files use.',
                )


class TheMap(unittest.TestCase):
    def test_each_path_it_names_is_a_file_or_a_folder_here(self):
        named = paths_named(MAP.read_text(encoding="utf-8"))
        self.assertGreater(len(named), 0)
        for path in named:
            with self.subTest(path):
                self.assertTrue(
                    (ROOT / path).exists(),
                    f"AGENTS.md names {path}, which is not here. Name where it went, or take the line out.",
                )

    def test_each_part_of_a_document_it_names_is_a_heading_or_a_bold_lead_of_that_document(self):
        named = parts_named(MAP.read_text(encoding="utf-8"))
        self.assertGreater(len(named), 0)
        for document, part in named:
            with self.subTest(document=document, part=part):
                self.assertTrue((ROOT / document).is_file(), f"AGENTS.md names {document}, which is not here")
                self.assertIn(
                    part,
                    parts_of(document),
                    f'AGENTS.md sends a reader to "{part}" in {document}, and no heading or bold lead there says that.',
                )


class TheChecks(unittest.TestCase):
    """The checks above find what they look for, so that none passes because it read nothing."""

    def test_a_named_test_is_found_only_when_its_file_its_class_and_its_name_all_match(self):
        this = (
            "tests/test_context.py::TheChecks::"
            "test_a_named_test_is_found_only_when_its_file_its_class_and_its_name_all_match"
        )
        self.assertIsNone(what_is_wrong_with(this))
        self.assertIn("is not a file", what_is_wrong_with(this.replace("test_context.py", "test_gone.py")))
        self.assertIn("has no class", what_is_wrong_with(this.replace("TheChecks", "TheGone")))
        self.assertIn("has no test", what_is_wrong_with(this + "_and_more"))

    def test_a_standard_runs_from_its_bold_lead_to_the_next_standard_or_the_next_heading(self):
        found = standards()
        self.assertGreater(len(found), 0)
        for standard in found:
            with self.subTest(standard.number):
                self.assertEqual(len(LEAD.findall(standard.text)), 1)
                self.assertNotRegex(standard.text, r"(?m)^## ")

    def test_a_term_is_the_same_words_in_any_case_and_with_a_space_a_hyphen_or_an_underscore(self):
        self.assertEqual(plain("Star history"), plain("star_history"))
        self.assertEqual(plain("Owner-written text"), plain("owner written\ntext"))

    def test_a_path_or_a_part_that_is_in_risingrepos_or_in_a_code_block_is_not_looked_for_here(self):
        text = (
            'Read `tests/helpers.py` and README.md, "The data". The rule is RisingRepos:\n'
            '`docs/agents/gone.md`, "Gone".\n\n```sh\nrm `gone/` `tests/gone.py`\n```\n'
        )
        self.assertEqual(paths_named(text), ["tests/helpers.py"])
        self.assertEqual(parts_named(text), [("README.md", "The data")])

    def test_a_quoted_phrase_is_a_part_of_the_document_named_before_it_in_its_sentence_its_row_or_its_item(self):
        text = (
            'RUNBOOK.md has it. A subject is "Fix it". README.md, "The pages", under "Its\nsize", gives them.\n\n'
            '| Change the data | README.md, "The data" |\n| Name it | "Baseline" |\n\n'
            '- See RUNBOOK.md, "Going back".\n- "Plex" is reserved.\n'
        )
        self.assertEqual(
            parts_named(text),
            [
                ("README.md", "The pages"),
                ("README.md", "Its size"),
                ("README.md", "The data"),
                ("RUNBOOK.md", "Going back"),
            ],
        )

    def test_a_path_that_is_gone_is_named_though_its_folder_is_gone_too(self):
        self.assertEqual(
            paths_named("See `gone/file.py`, `tests/gone.py`, `main`, and `site.css`."),
            ["gone/file.py", "tests/gone.py"],
        )


if __name__ == "__main__":
    unittest.main()
