"""A repository's owner wrote its name, its description, its language, and the licence file GitHub names its licence
from, so the board treats each as text that anyone could have written: escaped where it is shown, and never made a
link."""

import re
import unittest

from helpers import BuildTest, read_json, shipped

from sitebuild import BOARD, TEMPLATES, board_day_page

MARKUP_ROW = "rising-repos-example/markup-in-description"
SCRIPT_PARTS = ("theme.js", "old-board.js", "filters.js")
"""The parts of the root's one script, the site's own, as site.js includes them on a board with rows."""


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
        self.assertEqual([(href, text) for href, text in self.page.links() if not href.startswith(("/", "#"))], expected)
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
        self.assertEqual([element for element in page.all() if any(name.startswith("on") for name in element.attrs)], [])


class TheHistoryFile(BuildTest):
    """What an opened row shows of owner-written text comes from the board day's history.json: a name it was listed
    under before, and its licence. The file holds them as JSON strings, and the page's script writes every value it
    reads from the file as text, never as markup."""

    def test_the_history_file_holds_owner_text_as_strings_and_the_script_writes_text_alone(self):
        self.build_pages()
        history = read_json(self.out / board_day_page("2026-11-09").replace("index.html", "history.json"))
        licences = [entry["about"][0] for entry in history["rows"]]
        self.assertEqual(licences, [row["license"] for row in read_json(self.board_file())["rows"]])
        self.assertTrue(all(value is None or isinstance(value, str) for value in licences))
        script = (TEMPLATES / "filters.js").read_text(encoding="utf-8")
        self.assertNotRegex(script, r"innerHTML|outerHTML|insertAdjacentHTML|document\.write")
        self.assertIn("element.textContent = text", script)
        # Every element it makes is a fixed tag: no tag name comes from the file.
        self.assertEqual(
            sorted(set(re.findall(r'make\("([a-z0-9]+)"', script))),
            ["a", "caption", "dd", "div", "dl", "dt", "figcaption", "figure", "p", "span", "table", "td", "th"],
        )


if __name__ == "__main__":
    unittest.main()
