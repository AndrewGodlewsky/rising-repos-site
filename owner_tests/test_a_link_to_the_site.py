"""A link to the site, shared on Discord or X. Sentence 43 of the owner's tests."""

import struct
import unittest
from urllib.parse import urlsplit

from playwright.sync_api import Page

from owner_tests.scenario import Scenario, heading, the_day

PNG = b"\x89PNG\r\n\x1a\n"
"""The eight bytes every PNG file starts with. Its first chunk, IHDR, gives its width and its height after them."""

CARD = (1200, 630)
"""The size, in pixels, at which Discord and X draw a large card's image whole."""


def head(page: Page, attribute: str, name: str) -> list[str]:
    """Every value the page's head gives the tag named `name` by `attribute`, `property` or `name`. The tags in a
    page's head have no role, so they are found by their tag."""
    tags = page.locator(f'head meta[{attribute}="{name}"]')
    return [tags.nth(at).get_attribute("content") for at in range(tags.count())]


class ALinkToTheSite(Scenario):
    def test_a_link_to_any_page_shows_a_large_card_with_its_title_a_description_and_a_board_days_image(self):
        """Sentence 43. A card is drawn from a page's head as a crawler reads it, without scripts, so the reader has
        scripts off. For a page of each kind, as a reader comes to them from the root, the head asks for a large
        card, once, and gives it the page's own title, a description, and an image on https. The image's path,
        asked of the site being read, is a PNG of 1200 by 630 pixels. The root's image is the board day's of its
        heading, and the board before's is its own, beside its page."""
        page = self.reader(scripts=False)
        places = self.each_kind_of_page(page)
        self.visit(page)
        newest = the_day(heading(page).inner_text())
        days = [
            place for place in places if urlsplit(place).path.startswith("/days/") and urlsplit(place).path != "/days/"
        ]
        self.given(days, "the newest board is the first, so no board day's page is reached but the root's")
        for place in places:
            with self.subTest(place):
                page.goto(place)
                self.assertEqual(head(page, "name", "twitter:card"), ["summary_large_image"])
                self.assertEqual(head(page, "property", "og:title"), [page.title()])
                (described,) = head(page, "property", "og:description")
                self.assertTrue(described.strip())
                (image,) = head(page, "property", "og:image")
                self.assertEqual(urlsplit(image).scheme, "https", image)
                path = urlsplit(image).path
                answer = page.request.get(self.site.address + path)
                self.assertEqual(answer.status, 200, path)
                self.assertEqual(answer.headers.get("content-type", "").split(";")[0], "image/png", path)
                body = answer.body()
                self.assertEqual(body[:8], PNG, path)
                self.assertEqual(struct.unpack(">II", body[16:24]), CARD, path)
                if place == f"{self.site.address}/":
                    self.assertEqual(path, f"/days/{newest.isoformat()}/share.png")
                elif place in days:
                    self.assertEqual(path, urlsplit(place).path + "share.png")


if __name__ == "__main__":
    unittest.main()
