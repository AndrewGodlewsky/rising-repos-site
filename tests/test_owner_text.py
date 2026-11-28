"""A repository's owner wrote its name, its description, its language, and the licence file GitHub names its licence
from, so the board treats each as text that anyone could have written: escaped where it is shown, and never made a
link."""

import re
import shutil
import unittest

from helpers import BuildTest, Element, Page, read_json, shipped, write_json

from sitebuild import BASELINE, BOARD, TEMPLATES, board_day_page, licence_label

MARKUP_ROW = "rising-repos-example/markup-in-description"
SCRIPT_PARTS = ("theme.js", "old-board.js", "filters.js")
"""The parts of the root's one script, the site's own, as site.js includes them on a board with rows."""

GITHUB = "https://github.com/"
"""Where a row's name leads, with the name after it: the one address off the site that a page links to."""

OWNER = "rising-repos-example"
"""The owner of every made-up repository below. A name's first "/" parts its owner from the rest, and this has none."""

HOSTILE = {
    "markup, with a link to another site": '<b>bold</b> and <a href="https://example.com/">a link</a>',
    "a script element": "<script>alert(1)</script>",
    "an end tag that would close its cell and open another": "</td><td>a cell of its own",
    "quotes of both kinds that would end an attribute and start a handler": '" onmouseover="alert(1)" \' x=\'',
    "an entity, which is to be shown as it was written": "&lt;b&gt; &amp; &#60;i&#62;",
    "a javascript: address": "javascript:alert(1)",
    "a data: address that holds a page": "data:text/html,<script>alert(1)</script>",
    "the start of a comment, which would take in the rest of the page": "<!--",
    "a template's own marks": "{{ 7 * 7 }}{% include 'site.js' %}",
    "a very long word with no space": "W" * 300,
    "characters that turn the text round, and characters of no width": (
        "\N{RIGHT-TO-LEFT OVERRIDE}\N{RIGHT-TO-LEFT ISOLATE}abc\N{POP DIRECTIONAL ISOLATE}"
        "\N{ZERO WIDTH SPACE}\N{ZERO WIDTH JOINER}\N{ZERO WIDTH NO-BREAK SPACE}"
    ),
    "a line break": "one line\nand another",
    "white space alone": " \t ",
}
"""Text written to break a page, each by what it tries (docs/workflow-plan.md, section 6). `HostileText` puts each in
every field of a row that a repository's owner controls. The list is fixed and short, so that it can be read: a new
kind of text is a new line here."""


def exact_text(element: Element) -> str:
    """The text inside the element exactly as the page holds it, entities decoded: every space and line break that
    `Element.text` makes one space, since a text written to break a page is to be shown as it was written."""
    return "".join(child if isinstance(child, str) else exact_text(child) for child in element.children)


def tree(page: Page) -> list[tuple[str, dict]]:
    """Every element of the page, in order, as its tag and its attributes, but for the values of the two attributes
    that carry what an owner wrote: a row's language, in its data-l, and where its name leads on GitHub."""

    def owners(name: str, value: str | None) -> bool:
        return name == "data-l" or (name == "href" and value.startswith(GITHUB))

    return [
        (element.tag, {name: "an owner's" if owners(name, value) else value for name, value in element.attrs.items()})
        for element in page.all()
    ]


class OwnerWrittenText(BuildTest):
    def setUp(self):
        super().setUp()
        self.rows = read_json(self.board_file())["rows"]
        (self.markup,) = [row for row in self.rows if row["full_name"] == MARKUP_ROW]
        self.page = self.build_pages()[BOARD]

    def test_markup_in_a_description_appears_as_text(self):
        """The description holds a script element and a <b>. Neither becomes one: the description's cell holds text
        alone, and the page's only script is the site's own, whose text is that of the templates it comes from."""
        (row,) = [element for element in self.page.rows() if MARKUP_ROW in element.text()]
        (cell,) = [cell for cell in row.all("td") if "de" in cell.classes()]
        self.assertEqual(cell.text(), self.markup["description"])
        self.assertEqual(cell.all(), [])
        (script,) = self.page.all("script")
        expected = "".join(shipped(part) for part in SCRIPT_PARTS)
        self.assertEqual("".join(script.children), expected)
        self.assertEqual(self.page.html.lower().count("<script"), 1)
        # The one <b> a board may carry is its own mark beside a new repository's name, and this board has none.
        self.assertEqual(self.page.all("b"), [])
        self.assertNotIn("<b>", self.page.html.lower())

    def test_no_owner_written_value_is_made_a_link_and_each_name_links_to_its_repository_on_github(self):
        expected = [(f"https://github.com/{row['full_name']}", row["full_name"]) for row in self.rows]
        self.assertEqual(
            [(href, text) for href, text in self.page.links() if not href.startswith(("/", "#"))], expected
        )
        values = [value for element in self.page.all() for value in element.attrs.values() if value]
        self.assertEqual([value for value in values if "javascript:" in value.lower()], [])

    def test_text_beyond_ascii_is_shown_as_the_file_has_it(self):
        (row,) = [row for row in self.rows if row["full_name"] == "rising-repos-example/text-beyond-ascii"]
        self.assertIn(row["description"], self.page.body_text())


class OwnerWrittenLanguage(BuildTest):
    """A row's language reaches the page in two more places since AndrewGodlewsky/RisingRepos#199: its row's data-l,
    which the language filter reads, and the filter's list of languages. Each stays one attribute value and one
    option's text, whatever the owner wrote."""

    LANGUAGE = 'Go" onmouseover="alert(1)"><script>alert(2)</script>'

    def test_markup_in_a_language_stays_one_attribute_value_and_one_options_text(self):
        board = read_json(self.board_file())
        rows = [{**row, "language": self.LANGUAGE} if row["full_name"] == MARKUP_ROW else row for row in board["rows"]]
        self.write_board({**board, "rows": rows})
        page = self.build_pages()[BOARD]
        (row,) = [element for element in page.rows() if MARKUP_ROW in element.text()]
        self.assertEqual(row.attrs["data-l"], self.LANGUAGE)
        self.assertNotIn("onmouseover", row.attrs)
        self.assertIn(self.LANGUAGE, [option.text() for option in page.all("option")])
        self.assertEqual(page.html.lower().count("<script"), 1)
        self.assertEqual(
            [element for element in page.all() if any(name.startswith("on") for name in element.attrs)], []
        )


class TheHistoryFile(BuildTest):
    """What an opened row shows of owner-written text comes from the board day's history.json: a name it was listed
    under before, and its licence. The file holds them as JSON strings, and the page's script writes every value it
    reads from the file as text, never as markup."""

    def test_the_history_file_holds_owner_text_as_strings_and_the_script_writes_text_alone(self):
        self.build_pages()
        history = read_json(self.out / board_day_page("2026-11-09").replace("index.html", "history.json"))
        licences = [fact[1] for entry in history["rows"] for fact in entry["facts"] if fact[0] == "Licence"]
        self.assertEqual(licences, [licence_label(row["license"]) for row in read_json(self.board_file())["rows"]])
        self.assertTrue(all(isinstance(value, str) for value in licences))
        script = shipped("filters.js")
        self.assertNotRegex(script, r"innerHTML|outerHTML|insertAdjacentHTML|document\.write")
        self.assertIn("element.textContent = text", script)
        # Every element it makes is a fixed tag: no tag name comes from the file.
        self.assertEqual(
            sorted(set(re.findall(r'make\("([a-z0-9]+)"', script))),
            ["a", "caption", "dd", "div", "dl", "dt", "figcaption", "figure", "p", "span", "table", "td", "th"],
        )

    def test_no_script_template_uses_an_unsafe_dom_sink_or_eval(self):
        """STANDARDS.md P6 (#251): every script part writes text through textContent and never through HTML sinks
        or eval."""
        unsafe = re.compile(r"\b(?:innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval)\b")
        jinja_comment = re.compile(r"\{#.*?#\}", re.DOTALL)
        scripts = sorted(TEMPLATES.rglob("*.js"))
        self.assertTrue(scripts)
        for path in scripts:
            with self.subTest(path.relative_to(TEMPLATES).as_posix()):
                body = jinja_comment.sub("", path.read_text(encoding="utf-8"))
                self.assertIsNone(unsafe.search(body))


class HostileText(BuildTest):
    """Each text of `HOSTILE`, on a made-up board that has one row for each: the row holds the text as its
    description, its language, its licence, and its name, after `OWNER` and a "/".

    The contract's schema lets a name hold only the characters of a GitHub name, and a licence those of an SPDX id, so
    the build refuses most of these texts there before it writes a page. The schema comes with the data, so the pages
    do not lean on it: the copy's schema here lets any name and any licence through, and the page has to show each as
    text all the same."""

    def setUp(self):
        super().setUp()
        schema = read_json(self.daily_schema)
        row = schema["properties"]["rows"]["items"]["properties"]
        for name in ("full_name", "license"):
            del row[name]["pattern"]
        write_json(self.daily_schema, schema)

    def built(self, texts: list[str]) -> dict[str, Page]:
        """Build with the example's newest board made of one row for each of `texts`, each a copy of the example's
        first row but for its rank, its id, and the four fields that hold the text."""
        board = read_json(self.board_file())
        rows = [
            {
                **board["rows"][0],
                "rank": rank,
                "github_id": 990000000 + rank,
                "full_name": f"{OWNER}/{text}",
                "description": text,
                "language": text,
                "license": text,
            }
            for rank, text in enumerate(texts, start=1)
        ]
        self.write_board({**board, "rows": rows})
        shutil.rmtree(self.out, ignore_errors=True)
        return self.build_pages()

    def test_each_hostile_text_is_shown_as_it_was_written_wherever_its_row_shows_it(self):
        """On the board, at the root and on its board day's page: as the text of its description's cell, which holds
        no element; as the text of the row's one link, which leads to GitHub and nowhere else, and of the disclosure
        that names the row; as the value of its data-l; and as one language in the filter's list. On the Baseline
        page, as the text of its row's link. In the board day's history, as the strings an opened row shows for its
        language and its licence, which the script writes as text (`TheHistoryFile`)."""
        day = board_day_page("2026-11-09")
        pages = self.built(list(HOSTILE.values()))
        history = read_json(self.out / day.replace("index.html", "history.json"))
        for path in (BOARD, day):
            page = pages[path]
            (languages,) = [select for select in page.all("select") if select.attrs.get("id") == "language"]
            listed = [exact_text(option) for option in languages.all("option")]
            for (tries, text), row, entry in zip(HOSTILE.items(), page.rows(), history["rows"], strict=True):
                with self.subTest(path, tries=tries):
                    name = f"{OWNER}/{text}"
                    (cell,) = [cell for cell in row.all("td") if "de" in cell.classes()]
                    (link,) = row.all("a")
                    (summary,) = row.all("summary")
                    self.assertEqual(cell.all(), [])
                    self.assertEqual(exact_text(cell), text)
                    self.assertEqual((link.attrs["href"], exact_text(link)), (GITHUB + name, name))
                    self.assertEqual(exact_text(summary), f"More on {name}")
                    self.assertEqual(row.attrs["data-l"], text)
                    self.assertIn(text, listed)
                    facts = {fact[0]: fact[1] for fact in entry["facts"]}
                    self.assertEqual((facts["Language"], facts["Licence"]), (text, text))
        for (tries, text), row in zip(HOSTILE.items(), pages[BASELINE].rows(), strict=True):
            with self.subTest(BASELINE, tries=tries):
                name = f"{OWNER}/{text}"
                (link,) = row.all("a")
                self.assertEqual((link.attrs["href"], exact_text(link)), (GITHUB + name, name))

    def test_no_hostile_text_becomes_an_element_an_attribute_or_a_link_and_each_row_keeps_every_cell(self):
        """Each page built with the hostile texts has, element for element, the tags and the attributes of the page
        built with plain words in their place, but for the values of the two attributes that carry a row's language
        and its name, which the test above holds. So no text made an element, an attribute, or a link, in its row or
        anywhere else on a page, and each row has the cells it had. Nor does the source of a page hold a text as it
        was written, where the text has a character that HTML sets apart: each such character is escaped."""
        plain = self.built([f"plain-{number}" for number in range(len(HOSTILE))])
        hostile = self.built(list(HOSTILE.values()))
        self.assertEqual(list(hostile), list(plain))
        for path, page in hostile.items():
            with self.subTest(path):
                self.assertEqual(tree(page), tree(plain[path]))
                self.assertEqual(len(page.rows()), len(plain[path].rows()))
                for tries, text in HOSTILE.items():
                    if set(text) & set("<>&\"'"):
                        self.assertEqual(page.html.count(text), plain[path].html.count(text), tries)


if __name__ == "__main__":
    unittest.main()
