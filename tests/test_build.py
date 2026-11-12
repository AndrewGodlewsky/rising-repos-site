"""The generator, run the way the workflow runs it, on a copy of the data contract's example.

The build writes two pages: the board, at the site's root, and the page for an address that holds no page. A
test of something every page holds to reads both.
"""

import re
import unittest
from urllib.parse import unquote

from helpers import BuildTest, build, read_json, write_json

from sitebuild import TEMPLATES

NOINDEX = '<meta name="robots" content="noindex">'

BOARD = "index.html"
"""The board's page, at the site's root."""

NOT_FOUND = "404.html"
"""The page for an address that holds none. Cloudflare Pages answers such an address with this page and the
status 404. A site with no 404.html at its root is taken for a single-page app, and every such address gets the
root page and the status 200."""


class TheBuild(BuildTest):
    def test_the_build_writes_the_board_at_the_root_and_a_page_for_an_address_that_holds_none(self):
        self.build_pages()
        written = sorted(path.relative_to(self.out).as_posix() for path in self.out.rglob("*") if path.is_file())
        self.assertEqual(written, [NOT_FOUND, BOARD])

    def test_the_board_shows_the_latest_board_day_which_is_the_first_in_the_index(self):
        page = self.build_pages()[BOARD]
        self.assertIn("Rising Repos", page.one("title").text())
        self.assertIn("9 November 2026", page.one("title").text())
        self.assertEqual(page.one("h1").all("time")[0].attrs["datetime"], "2026-11-09")
        self.assertIn("9 November 2026", page.one("h1").text())

    def test_the_board_lists_every_row_in_the_files_order_with_its_rank_name_description_language_and_stars(self):
        rows = read_json(self.board_file())["rows"]
        shown = self.build_pages()[BOARD].rows()
        self.assertEqual(len(shown), len(rows))
        for row, element in zip(rows, shown):
            text = element.text()
            self.assertEqual(text.split()[0], str(row["rank"]), text)
            self.assertEqual(
                [(link.attrs["href"], link.text()) for link in element.all("a")],
                [(f"https://github.com/{row['full_name']}", row["full_name"])],
            )
            self.assertIn(row["description"] or "No description", text)
            if row["language"]:
                self.assertIn(row["language"], text)
            self.assertRegex(text, rf"(^|\s){row['stars']:,}(\s|$)")

    def test_the_boards_column_headings_say_that_the_number_is_total_stars(self):
        page = self.build_pages()[BOARD]
        self.assertEqual([heading.text() for heading in page.one("thead").all("th")], ["Rank", "Repository", "Total stars"])

    def test_a_row_shows_no_language_when_the_file_has_none(self):
        board = read_json(self.board_file())
        languages = {row["language"] for row in board["rows"] if row["language"]}
        (no_language,) = [element for element in self.build_pages()[BOARD].rows() if "octocat/Hello-World" in element.text()]
        self.assertFalse(languages & set(no_language.text().split()), no_language.text())
        self.assertNotIn("None", no_language.text().split())

    def test_each_page_says_under_the_sites_name_that_there_is_a_new_board_each_day(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                (site,) = [element for element in page.one("header").all("p") if "site" in element.classes()]
                self.assertTrue(site.text().startswith("Rising Repos"), site.text())
                self.assertIn("on a new board each day", site.text())

    def test_the_board_states_its_board_day_and_publish_time_in_the_contracts_two_meta_tags_once_each(self):
        page = self.build_pages()[BOARD]
        self.assertEqual(page.meta("rr:board-date"), ["2026-11-09"])
        self.assertEqual(page.meta("rr:published-at"), ["2026-11-10T00:41:07Z"])
        head = page.html.split("</head>")[0]
        self.assertIn('<meta name="rr:board-date" content="2026-11-09">', head)
        self.assertIn('<meta name="rr:published-at" content="2026-11-10T00:41:07Z">', head)

    def test_the_board_shows_when_the_board_day_was_published_in_utc(self):
        page = self.build_pages()[BOARD]
        (published,) = [time for time in page.all("time") if time.attrs["datetime"] == "2026-11-10T00:41:07Z"]
        self.assertEqual(published.text(), "10 November 2026 at 00:41 UTC")

    def test_the_board_says_its_ranking_is_provisional_while_the_file_says_so_and_names_no_score(self):
        page = self.build_pages()[BOARD]
        self.assertIn("The ranking is provisional.", page.body_text())
        self.assertNotIn("score", page.body_text().lower())

    def test_the_board_says_nothing_about_a_provisional_ranking_once_the_file_says_it_is_not(self):
        board = read_json(self.board_file())
        write_json(self.board_file(), {**board, "score_provisional": False})
        self.assertNotIn("provisional", self.build_pages()[BOARD].body_text().lower())

    def test_a_board_that_is_empty_says_so_and_states_its_board_day_the_same_way(self):
        write_json(self.index, {"schema_version": 1, "board_days": [{"board_day": "2026-11-08"}]})
        page = self.build_pages()[BOARD]
        self.assertEqual(page.rows(), [])
        self.assertEqual(page.links(), [])
        self.assertIn("No repository made the board on this day.", page.body_text())
        self.assertIn("No repositories.", page.body_text())
        self.assertIn("8 November 2026", page.one("h1").text())
        self.assertEqual(page.meta("rr:board-date"), ["2026-11-08"])
        self.assertEqual(page.meta("rr:published-at"), ["2026-11-09T00:38:52Z"])

    def test_a_board_of_one_row_counts_it_as_one_repository(self):
        board = read_json(self.board_file())
        write_json(self.board_file(), {**board, "rows": board["rows"][:1]})
        page = self.build_pages()[BOARD]
        self.assertIn("1 repository", page.body_text())
        self.assertNotIn("1 repositories", page.body_text())

    def test_the_page_for_an_address_that_holds_none_says_so_and_links_to_the_board(self):
        page = self.build_pages()[NOT_FOUND]
        self.assertIn("not found", page.one("title").text().lower())
        self.assertEqual(page.one("h1").text(), "Page not found")
        self.assertEqual(page.links(), [("/", "the latest daily board")])

    def test_the_page_for_an_address_that_holds_none_states_no_board_day(self):
        page = self.build_pages()[NOT_FOUND]
        self.assertEqual(page.meta("rr:board-date"), [])
        self.assertEqual(page.meta("rr:published-at"), [])
        self.assertEqual(page.all("time"), [])

    def test_each_pages_icon_and_theme_colour_take_the_colour_of_its_band(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                (style,) = page.all("style")
                band = re.search(r"--field:\s*(#[0-9a-f]{6});", style.text()).group(1)
                self.assertEqual(page.meta("theme-color"), [band])
                (icon,) = [link for link in page.all("link") if link.attrs.get("rel") == "icon"]
                self.assertEqual(re.findall(r"fill='(#[0-9a-f]{6})'", unquote(icon.attrs["href"])), [band])

    def test_pages_built_for_the_preview_ask_search_engines_not_to_index_them(self):
        for path, page in self.build_pages("--noindex").items():
            with self.subTest(path):
                head, body = page.html.split("</head>")
                self.assertEqual(head.count('name="robots"'), 1)
                self.assertIn(NOINDEX, head)
                self.assertNotIn('name="robots"', body)

    def test_pages_built_without_the_option_carry_no_robots_tag(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertNotIn('name="robots"', page.html)

    def test_a_folder_that_already_holds_files_is_refused_and_left_as_it_was(self):
        self.out.mkdir()
        (self.out / "keep.txt").write_text("kept", encoding="utf-8")
        result = self.build_data()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(self.out), result.stderr)
        self.assertEqual([path.name for path in self.out.iterdir()], ["keep.txt"])
        self.assertEqual((self.out / "keep.txt").read_text(encoding="utf-8"), "kept")

    def test_without_the_data_option_it_builds_from_the_repositorys_site_data(self):
        result = build(self.out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.out / BOARD).is_file())


class TheTemplates(unittest.TestCase):
    """Jinja2 escapes a value only while autoescape is on (ADR 0010 in RisingRepos)."""

    def test_no_template_turns_escaping_off_or_marks_a_value_as_safe(self):
        for template in sorted(TEMPLATES.iterdir()):
            with self.subTest(template.name):
                text = template.read_text(encoding="utf-8")
                self.assertIsNone(re.search(r"autoescape\s+[Ff]alse|\|\s*safe\b", text))


if __name__ == "__main__":
    unittest.main()
