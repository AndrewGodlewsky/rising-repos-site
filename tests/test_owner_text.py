"""A repository's owner wrote its name, its description, and its language, so the pages treat each as text
that anyone could have written: escaped where it is shown, and never made a link."""

import unittest

from helpers import BuildTest, read_json

MARKUP_ROW = "rising-repos-example/markup-in-description"


class OwnerWrittenText(BuildTest):
    def setUp(self):
        super().setUp()
        self.rows = read_json(self.board_file())["rows"]
        (self.markup,) = [row for row in self.rows if row["full_name"] == MARKUP_ROW]

    def test_markup_in_a_description_appears_as_text(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                (row,) = [element for element in page.rows() if MARKUP_ROW in element.text()]
                self.assertIn(self.markup["description"], row.text())
                body = page.one("body")
                self.assertEqual([element.tag for element in body.elements() if element.tag in ("script", "b")], [])
                self.assertNotIn("<script", page.html.lower())
                self.assertNotIn("<b>", page.html.lower())

    def test_no_owner_written_value_is_made_a_link_and_each_name_links_to_its_repository_on_github(self):
        expected = [(f"https://github.com/{row['full_name']}", row["full_name"]) for row in self.rows]
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertEqual(page.links(), expected)
                addresses = [value for element in page.all() for value in element.attrs.values() if value]
                self.assertFalse([value for value in addresses if "javascript:" in value.lower()])

    def test_text_beyond_ascii_is_shown_as_the_file_has_it(self):
        (row,) = [row for row in self.rows if row["full_name"] == "rising-repos-example/text-beyond-ascii"]
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertIn(row["description"], page.body_text())


if __name__ == "__main__":
    unittest.main()
