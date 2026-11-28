"""What the build writes for a crawler: the sitemap and the site's own robots.txt (#170).

Cloudflare Pages serves a robots.txt of its own, which carries a signal that the owner did not choose, when the
site has none. The site's is explicit, so that the signals it states are the ones it means.
"""

import xml.etree.ElementTree as ET

from helpers import BuildTest, read_json

from sitebuild import BASELINE, DAYS, FOR_AGENTS, HOW_IT_WORKS, SEARCH, SITE, address, day_address
from sitebuild.crawl import ATOM_SCHEMA, FEED_DAYS

NEWEST, OLDER = "2026-11-09", "2026-11-08"
SCHEMA = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
ATOM = f"{{{ATOM_SCHEMA}}}"


class TheCrawlerFiles(BuildTest):
    def entries(self) -> dict[str, str | None]:
        """Each `<loc>` of the built sitemap, with its `<lastmod>`, or None where it has none."""
        self.build_pages()
        tree = ET.parse(self.out / "sitemap.xml")
        self.assertEqual(tree.getroot().tag, SCHEMA + "urlset")
        return {
            url.findtext(SCHEMA + "loc"): url.findtext(SCHEMA + "lastmod")
            for url in tree.getroot().iter(SCHEMA + "url")
        }

    def test_the_sitemap_lists_every_page_by_its_address_with_the_closing_slash(self):
        found = list(self.entries())
        self.assertEqual(
            sorted(found),
            sorted(
                [
                    SITE + "/",
                    SITE + address(DAYS),
                    SITE + address(BASELINE),
                    SITE + address(SEARCH),
                    SITE + address(HOW_IT_WORKS),
                    SITE + address(FOR_AGENTS),
                    SITE + day_address(NEWEST),
                    SITE + day_address(OLDER),
                ]
            ),
        )
        self.assertTrue(all(loc.endswith("/") for loc in found))

    def test_each_board_days_entry_has_its_publish_time_and_the_roots_has_the_newest(self):
        entries = self.entries()
        published = {day: read_json(self.board_file(day))["published_at"] for day in (NEWEST, OLDER)}
        for day, moment in published.items():
            self.assertEqual(entries[SITE + day_address(day)], moment)
        for page in ("/", address(DAYS), address(BASELINE)):
            self.assertEqual(entries[SITE + page], published[NEWEST], page)
        for page in (SEARCH, HOW_IT_WORKS, FOR_AGENTS):
            self.assertIsNone(entries[SITE + address(page)], page)

    def test_the_robots_txt_allows_every_crawler_states_two_signals_and_names_the_sitemap(self):
        self.build_pages()
        text = (self.out / "robots.txt").read_text(encoding="utf-8")
        self.assertEqual(
            text.split("\n"),
            [
                "User-agent: *",
                "Content-Signal: search=yes, ai-input=yes",
                "Allow: /",
                "",
                f"Sitemap: {SITE}/sitemap.xml",
                "",
            ],
        )
        self.assertNotIn("ai-train", text)

    def test_a_noindex_build_writes_a_robots_txt_that_invites_no_crawler(self):
        self.build_pages("--noindex")
        text = (self.out / "robots.txt").read_text(encoding="utf-8")
        self.assertEqual(text.split("\n"), ["User-agent: *", "Disallow: /", ""])
        self.assertNotIn("Sitemap", text)


class TheAtomFeed(BuildTest):
    """#243: static Atom 1.0 feed at /feed.xml for feed readers."""

    def test_the_atom_feed_is_valid_xml_links_each_board_day_and_is_autodiscovered_on_every_page(self):
        pages = self.build_pages()
        tree = ET.parse(self.out / "feed.xml")
        root = tree.getroot()
        self.assertEqual(root.tag, ATOM + "feed")
        self.assertEqual(root.findtext(ATOM + "id"), SITE + "/")
        self.assertEqual(root.findtext(ATOM + "title"), "Rising Repos")
        links = {
            (el.attrib.get("rel"), el.attrib.get("type")): el.attrib.get("href") for el in root.findall(ATOM + "link")
        }
        self.assertEqual(links[("self", "application/atom+xml")], SITE + "/feed.xml")
        self.assertEqual(links[("alternate", "text/html")], SITE + "/")
        entries = root.findall(ATOM + "entry")
        self.assertEqual(
            [e.findtext(ATOM + "id") for e in entries], [SITE + day_address(NEWEST), SITE + day_address(OLDER)]
        )
        summary = entries[0].findtext(ATOM + "summary")
        self.assertIn("5 repositories on the board for 9 November 2026.", summary)
        self.assertIn("octocat/Spoon-Knife", summary)
        for path, page in pages.items():
            with self.subTest(path):
                alt = [el for el in page.all("link") if el.attrs.get("rel") == "alternate"]
                self.assertEqual(
                    [(el.attrs.get("type"), el.attrs.get("href")) for el in alt],
                    [("application/atom+xml", "/feed.xml")],
                )

    def test_the_atom_feed_strips_xml_illegal_control_chars_escapes_owner_text_and_caps_at_thirty_days(self):
        from sitebuild.crawl import atom_feed

        boards = [
            {
                "board_day": f"2026-{10 + (35 - i) // 31:02d}-{(35 - i) % 31 + 1:02d}",
                "published_at": f"2026-11-09T00:00:{i:02d}Z",
                "rows": [
                    {
                        "rank": 1,
                        "full_name": "owner/repo",
                        "stars": 1234,
                        "language": "C++ & <XML>\x00\x07",
                        "gained_1_day": -5,
                        "score": 10.0,
                        "baseline": 1.0,
                        "divided_by": 1.0,
                        "recent_stars": 20,
                        "recent_days": 2,
                        "days_left_out": 0,
                        "excess": 18.0,
                    }
                ],
            }
            for i in range(35)
        ]
        xml = atom_feed(boards)
        root = ET.fromstring(xml)
        entries = root.findall(ATOM + "entry")
        self.assertEqual(len(entries), FEED_DAYS)
        summary = entries[0].findtext(ATOM + "summary")
        self.assertIn("C++ & <XML>", summary)
        self.assertNotIn("\x00", summary)
        self.assertNotIn("\x07", summary)
        self.assertIn("\N{MINUS SIGN}5 on the day", summary)
