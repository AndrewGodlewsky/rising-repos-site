"""`/llms.txt`, and the link to it in the site's bar (#178).

A visiting agent that reaches any page has no other way to learn that the site publishes an agent copy of each board
(#176). The file is documentation of what the site holds, and gives an agent no order (#158). These build the example's
boards and read the file the build wrote.
"""

import re

from helpers import BuildTest
from test_build import site_bar

from sitebuild import FOR_AGENTS, SITE
from sitebuild.agent_copy import OWNER_LINE

NEWEST, OLDER = "2026-11-09", "2026-11-08"
ADDRESS = re.compile(r"https://risingrepos\.com/[^\s),>]*")
API = "/api/"
# The worked examples #180 asks for: the two addresses the query service's launch was checked on
# (AndrewGodlewsky/rising-repos-api#1, Task 7 of its plan).
SEARCH_EXAMPLE = "https://risingrepos.com/api/search?q=pdf"
REPO_EXAMPLE = "https://risingrepos.com/api/repo/pallets/flask"


class TheLlmsTxt(BuildTest):
    def text(self) -> str:
        self.build_pages()
        return (self.out / "llms.txt").read_text(encoding="utf-8")

    def test_llms_txt_holds_its_title_summary_and_sections(self):
        lines = self.text().split("\n")
        self.assertEqual(lines[0], "# Rising Repos")
        self.assertEqual(
            lines[2],
            "> GitHub repositories gaining stars faster than their own usual pace, ranked on a new board each day.",
        )
        self.assertEqual(
            [line for line in lines if line.startswith("## ")],
            ["## Boards as text", "## Search every repository", "## More"],
        )

    def test_llms_txt_holds_prose_only_before_its_first_section_and_only_links_after_it(self):
        before, after = self.text().split("\n## ", 1)
        self.assertIn(OWNER_LINE, before)
        self.assertIn("- rank:", before)
        for line in after.split("\n"):
            if (
                line
                and not line.startswith("## ")
                and line not in ("Boards as text", "Search every repository", "More")
            ):
                with self.subTest(line):
                    self.assertRegex(line, r"^- \[[^\]]+\]\(https://risingrepos\.com/[^)\s]*\)(: .+)?$")

    def test_every_address_llms_txt_names_is_a_file_the_build_wrote(self):
        # An address under /api/ is the query service's, which answers from its own repository and is no file here.
        named = [
            address for address in ADDRESS.findall(self.text().replace("<board day>", NEWEST)) if API not in address
        ]
        self.assertIn(f"{SITE}/days/{OLDER}/board.md", named)
        self.assertIn(f"{SITE}/latest.md", named)
        self.assertIn(f"{SITE}/repos.tsv", named)
        for address in named:
            path = address.removeprefix(SITE).lstrip("/")
            built = self.out / path
            with self.subTest(address):
                self.assertTrue(built.is_file() or (built / "index.html").is_file(), address)

    def test_llms_txt_names_both_addresses_of_the_query_service_with_a_worked_example_of_each(self):
        section = self.text().split("## Search every repository\n", 1)[1].split("\n## ", 1)[0]
        self.assertEqual(ADDRESS.findall(section), [SEARCH_EXAMPLE, REPO_EXAMPLE])
        self.assertIn("/api/repo/<owner>/<name>", section)
        self.assertIn("format=json", section)
        self.assertIn("20 to a page", section)

    def test_llms_txt_tells_an_agent_nothing_it_must_do(self):
        self.assertNotRegex(self.text().lower(), r"\bmust\b|\bshould\b|you need to")

    def test_llms_txt_gives_the_marks_and_the_owner_line_in_the_agent_copys_words(self):
        text = self.text()
        header = (self.out / "latest.md").read_text(encoding="utf-8")
        marks = header.split("## What the marks mean\n")[1].split("\n\n")[0]
        self.assertIn(marks, text)
        self.assertIn(OWNER_LINE, text)

    def test_llms_txt_names_the_newest_boards_day_and_size(self):
        text = self.text()
        self.assertIn("9 November 2026", text)
        self.assertIn("which lists 5 repositories", text)

    def test_llms_txt_is_plain_text_with_no_html_entity_in_it(self):
        text = self.text()
        self.assertIn("after the day's stars are counted", text)
        self.assertNotIn("&#", text)
        self.assertNotIn("&amp;", text)

    def test_the_for_agents_page_shows_an_apostrophe_as_a_reader_expects(self):
        self.assertIn("after the day's stars are counted", self.build_pages()[FOR_AGENTS].one("article").text())

    def test_every_pages_bar_links_for_agents_to_its_page_after_how_it_works(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                links = site_bar(page).all("a")
                self.assertEqual((links[-1].attrs["href"], links[-1].text()), ("/for-agents/", "For agents"))
                self.assertEqual(links[-2].text(), "How it works")

    def test_the_for_agents_page_is_marked_in_the_bar_and_no_other_page_marks_it(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                marked = [link.text() for link in site_bar(page).all("a") if link.attrs.get("aria-current") == "page"]
                self.assertEqual("For agents" in marked, path == FOR_AGENTS)

    def test_the_for_agents_page_links_to_llms_txt_and_every_address_it_names(self):
        page = self.build_pages()[FOR_AGENTS]
        hrefs = [link.attrs["href"] for link in page.one("article").all("a")]
        for wanted in ("/llms.txt", "/latest.md", "/latest.json", "/days/"):
            self.assertIn(wanted, hrefs)
        # A browser downloads a tab-separated file, so its address is given as text and not as a link.
        self.assertIn(f"{SITE}/repos.tsv", page.one("article").text())

    def test_the_for_agents_page_names_the_query_services_addresses_as_text_and_not_as_links(self):
        # The owner's tests open every link of the site as a page, and the service answers from another repository.
        article = self.build_pages()[FOR_AGENTS].one("article")
        hrefs = [link.attrs["href"] for link in article.all("a")]
        for example in (SEARCH_EXAMPLE, REPO_EXAMPLE):
            with self.subTest(example):
                self.assertIn(example, article.text())
                self.assertFalse([href for href in hrefs if API in href], hrefs)

    def test_the_for_agents_page_tells_an_agent_nothing_it_must_do(self):
        text = self.build_pages()[FOR_AGENTS].one("article").text().lower()
        self.assertNotRegex(text, r"\bmust\b|\bshould\b|you need to")

    def test_the_for_agents_page_gives_the_marks_and_the_owner_line_in_the_words_of_llms_txt(self):
        page = self.build_pages()[FOR_AGENTS].one("article").text()
        text = (self.out / "llms.txt").read_text(encoding="utf-8")
        marks = text.split("with the marks below.\n\n")[1].split("\n\n")[0].split("\n")
        self.assertTrue(marks)
        for mark in marks:
            self.assertIn(mark.removeprefix("- "), page)
        self.assertIn(OWNER_LINE, page)
