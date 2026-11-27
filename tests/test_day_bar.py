"""The way from an earlier board to the newest in its day bar, on a phone as on a desktop (#28).

An earlier board's day bar leads to the newest board, at the root, from Latest. Below 768 px the link was not
drawn, so a reader on a phone paged back one board day at a time, or scrolled up to the note above the rows. Now a
phone's bar holds it too, as "Latest »", with the newest board's date kept for a screen reader, since a bar 390 px
wide has no room for the date beside the board days on either side. Below 390 px the bar's parts sit closer, and
below 360 px, where even that leaves no room, Latest is not drawn, as before.

Where a part of the bar sits on a screen is something only a browser can say, so these open the pages in the Chrome
the machine already has, through Playwright, as `tests/test_opened_row.py` does, and fail without it. They set the
browser's clock to the newest board's publish time, so that no page hides its board behind the notice of an old one.
"""

import re
import unittest

from helpers import BuildTest, read_json, write_json

from sitebuild import board_day_page
from sitework.layout import chrome, published, served

NEWEST, OLDER = "2026-11-09", "2026-11-08"

PHONE, NARROW, NARROWEST, DESKTOP = 390, 360, 320, 1440
"""A phone, the narrowest phone that has room for Latest, a phone narrower still, and a desktop."""

NAME = re.compile(r"^The newest board, ")
"""The start of the name a screen reader hears for Latest, before the newest board's date."""

BAR = """bar => {
  const box = bar.getBoundingClientRect();
  const seen = element => {
    // The words of `element` a reader sees: those of a part cut to a pixel, as a screen reader's words are, are not.
    const words = [];
    const walk = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    for (let node = walk.nextNode(); node; node = walk.nextNode()) {
      let cut = false;
      for (let part = node.parentElement; part !== element.parentElement; part = part.parentElement) {
        const edge = part.getBoundingClientRect();
        if (edge.width <= 1 || edge.height <= 1) cut = true;
      }
      if (!cut && node.parentElement.checkVisibility()) words.push(node.nodeValue);
    }
    return words.join('').replace(/\\s+/g, ' ').trim();
  };
  return {
    left: box.left,
    right: box.right,
    sideways: document.documentElement.scrollWidth - window.innerWidth,
    parts: [...bar.children].filter(part => part.checkVisibility()).map(part => {
      const edge = part.getBoundingClientRect();
      const middle = (edge.top + edge.bottom) / 2;
      return {kind: part.classList[0], words: seen(part), left: edge.left, right: edge.right, middle};
    }),
  };
}"""
"""Where the board days' own room begins and ends: the navigation that holds them, inside the bar's padding, and
before the board's search, which the bar holds beside them from 768 px up (#213); how far the page reaches past the
screen's right edge; and each part of the bar that is drawn: its kind, the words a reader sees in it, its two sides,
and the height of its middle, which parts of the bar's one line share."""


class TheWayToTheNewest(BuildTest):
    def day_bar(self, browser, site: str, path: str, width: int):
        """The day bar of the page at `path`, on a screen `width` pixels wide, once its type is in. The page is
        closed with its browser."""
        page = browser.new_page(viewport={"width": width, "height": 800})
        page.clock.set_fixed_time(published(self.out))
        page.goto(f"{site}/{path.removesuffix('index.html')}", wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        return page, page.get_by_role("navigation", name="Board days", exact=True)

    def assert_whole(self, seen: dict) -> None:
        """Every part of the bar is on the bar's one line, centred on it as the bar's date is, and inside its room,
        and the page scrolls no way sideways."""
        self.assertLessEqual(seen["sideways"], 0, "the page scrolls sideways")
        self.assertEqual(len({round(part["middle"]) for part in seen["parts"]}), 1, seen["parts"])
        for part in seen["parts"]:
            with self.subTest(part=part["kind"]):
                self.assertGreaterEqual(part["left"], seen["left"] - 0.5, part)
                self.assertLessEqual(part["right"], seen["right"] + 0.5, part)

    def assert_latest(self, bar, seen: dict, newest: str, words: str) -> None:
        """The bar's last board day is Latest, which reads `words`, ends at the right end of the board days' room,
        leads to the root, and is heard as the newest board with its date."""
        latest = bar.get_by_role("link", name=NAME)
        self.assertEqual(latest.count(), 1)
        self.assertEqual(latest.get_attribute("href"), "/")
        self.assertEqual(bar.get_by_role("link", name=f"The newest board, {newest}", exact=True).count(), 1)
        self.assertEqual(seen["parts"][-1]["kind"], "latest")
        self.assertEqual(seen["parts"][-1]["words"], words)
        self.assertAlmostEqual(seen["parts"][-1]["right"], seen["right"], delta=0.5)

    def test_on_a_phone_an_earlier_boards_day_bar_leads_to_the_newest_and_holds_every_part_whole(self):
        self.build_pages()
        with served(self.out) as site, chrome() as browser:
            for width, words in ((PHONE, "Latest »"), (NARROW, "Latest »"), (DESKTOP, "Latest: 9 Nov »")):
                with self.subTest(width=width):
                    _, bar = self.day_bar(browser, site, board_day_page(OLDER), width)
                    seen = bar.evaluate(BAR)
                    self.assertEqual([part["kind"] for part in seen["parts"]], ["before", "here", "after", "latest"])
                    self.assert_latest(bar, seen, "9 Nov", words)
                    self.assert_whole(seen)
            with self.subTest(width=NARROWEST):
                _, bar = self.day_bar(browser, site, board_day_page(OLDER), NARROWEST)
                seen = bar.evaluate(BAR)
                self.assertEqual([part["kind"] for part in seen["parts"]], ["before", "here", "after"])
                self.assertEqual(bar.get_by_role("link", name=NAME).count(), 0)
                self.assert_whole(seen)

    def test_pressing_latest_on_a_phone_opens_the_newest_board(self):
        self.build_pages()
        with served(self.out) as site, chrome() as browser:
            page, bar = self.day_bar(browser, site, board_day_page(OLDER), PHONE)
            bar.get_by_role("link", name=NAME).click(timeout=5000)
            page.wait_for_url(f"{site}/")
            self.assertEqual(page.get_by_role("heading", level=1).locator("time").get_attribute("datetime"), NEWEST)

    def test_the_widest_dates_a_day_bar_shows_leave_latest_whole_on_a_phone(self):
        """Rising Sans gives every figure one width, so a date is widest with two figures and the widest month,
        May. The first board day's bar says "First board", wider than any date, and that day is 29 July 2026, the
        first board RisingRepos published, with the board day after it in July too, the narrowest month. So these
        are the widest bars there are: the first board day's, and one in May between two days of May."""
        days = ["2027-05-30", "2027-05-29", "2027-05-28", "2027-05-27", "2026-07-30", "2026-07-29"]
        empty = read_json(self.board_file(OLDER))
        for day in days:
            write_json(self.board_file(day), {**empty, "board_day": day, "published_at": f"{day}T23:38:52Z"})
        write_json(
            self.index, {**read_json(self.index), "board_days": [{"board_day": day, "row_count": 0} for day in days]}
        )
        self.build_pages()
        cases = {
            "2026-07-29": ["before", "here", "after", "latest"],
            "2027-05-28": ["before", "here", "after", "latest"],
        }
        with served(self.out) as site, chrome() as browser:
            for day, kinds in cases.items():
                for width in (PHONE, NARROW):
                    with self.subTest(day, width=width):
                        _, bar = self.day_bar(browser, site, board_day_page(day), width)
                        seen = bar.evaluate(BAR)
                        self.assertEqual([part["kind"] for part in seen["parts"]], kinds)
                        self.assert_latest(bar, seen, "30 May", "Latest »")
                        self.assert_whole(seen)


if __name__ == "__main__":
    unittest.main()
