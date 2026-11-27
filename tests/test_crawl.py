"""What the build writes for a crawler: the sitemap and the site's own robots.txt (#170).

Cloudflare Pages serves a robots.txt of its own, which carries a signal that the owner did not choose, when the
site has none. The site's is explicit, so that the signals it states are the ones it means.
"""

import xml.etree.ElementTree as ET

from helpers import BuildTest, read_json

from sitebuild import BASELINE, DAYS, HOW_IT_WORKS, SITE, address, day_address

NEWEST, OLDER = "2026-11-09", "2026-11-08"
SCHEMA = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


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
                    SITE + address(HOW_IT_WORKS),
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
        self.assertIsNone(entries[SITE + address(HOW_IT_WORKS)])

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
