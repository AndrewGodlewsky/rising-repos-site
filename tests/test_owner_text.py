"""A repository's owner wrote its name, its description, and its language, so the board treats each as text
that anyone could have written: escaped where it is shown, and never made a link."""

import unittest

from helpers import BuildTest, read_json

from sitebuild import BOARD

MARKUP_ROW = "rising-repos-example/markup-in-description"


class OwnerWrittenText(BuildTest):
    def setUp(self):
        super().setUp()
        self.rows = read_json(self.board_file())["rows"]
        (self.markup,) = [row for row in self.rows if row["full_name"] == MARKUP_ROW]
        self.page = self.build_pages()[BOARD]

    def test_markup_in_a_description_appears_as_text(self):
        (row,) = [element for element in self.page.rows() if MARKUP_ROW in element.text()]
        self.assertIn(self.markup["description"], row.text())
        body = self.page.one("body")
        self.assertEqual([element.tag for element in body.elements() if element.tag in ("script", "b")], [])
        self.assertNotIn("<script", self.page.html.lower())
        self.assertNotIn("<b>", self.page.html.lower())

    def test_no_owner_written_value_is_made_a_link_and_each_name_links_to_its_repository_on_github(self):
        expected = [(f"https://github.com/{row['full_name']}", row["full_name"]) for row in self.rows]
        self.assertEqual([(href, text) for href, text in self.page.links() if not href.startswith(("/", "#"))], expected)
        values = [value for element in self.page.all() for value in element.attrs.values() if value]
        self.assertEqual([value for value in values if "javascript:" in value.lower()], [])

    def test_text_beyond_ascii_is_shown_as_the_file_has_it(self):
        (row,) = [row for row in self.rows if row["full_name"] == "rising-repos-example/text-beyond-ascii"]
        self.assertIn(row["description"], self.page.body_text())


if __name__ == "__main__":
    unittest.main()
