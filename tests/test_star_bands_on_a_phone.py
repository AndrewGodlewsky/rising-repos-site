"""How the star-band filter lies on a phone, and from 768 px up (#32).

The band buttons wrapped as a row of words does, so on a phone 375 to 414 px wide the sixth, "30k+", fell alone onto
a line of its own, and on a board that holds a band back the fifth did so at 320 px. Now a phone lays the group out as
a grid as wide as the toolbar, of three columns, so that six buttons lie in two lines of three of one width, and of two
columns when two or four buttons show, so that no button is left alone on a line whatever bands the board holds back.
From 768 px up the group is the single row it was, each button as wide as its own label.

Where a button lies is something only a browser can say, so these open the root in the Chrome the machine already
has, through Playwright, as `tests/test_day_bar.py` does, with the browser's clock at the board's publish time so
that the page does not hide its board behind the notice of an old one.
"""

import unittest

from helpers import BuildTest, read_json

from sitebuild import BOARD
from sitework.layout import chrome, published, served

NEWEST = "2026-11-09"

PHONES = (360, 375, 390, 414, 430)
"""The widths of phone a reader holds, from the narrowest the site is drawn for to the widest."""

DESKTOPS = (768, 1440)
"""The width at which the page first lays itself out as for a desktop, and a desktop's."""

BANDS = [
    {"least_stars": 200, "most_stars": 999},
    {"least_stars": 1000, "most_stars": 2999},
    {"least_stars": 3000, "most_stars": 9999},
    {"least_stars": 10000, "most_stars": 29999},
    {"least_stars": 30000, "most_stars": None},
]
"""The five star bands every board day's file gives, in the order the filter shows them."""

LINES = """group => {
  const lines = new Map();
  for (const button of group.querySelectorAll('button')) {
    if (!button.checkVisibility()) continue;
    const box = button.getBoundingClientRect();
    const style = getComputedStyle(button);
    const words = document.createRange();
    words.selectNodeContents(button);
    const label = words.getBoundingClientRect().width + parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
    const top = Math.round(box.top);
    if (!lines.has(top)) lines.set(top, []);
    lines.get(top).push({words: button.textContent.trim(), width: box.width, label});
  }
  return [...lines.entries()].sort((a, b) => a[0] - b[0]).map(entry => entry[1]);
}"""
"""The band buttons that are drawn, by the line each lies on, from the top: each one's words, its width, and the
width its label asks for, which is its words' width and its padding."""

GROUP = """group => {
  const box = group.getBoundingClientRect();
  const style = getComputedStyle(group);
  const shown = [...group.querySelectorAll('button')].filter(button => button.checkVisibility());
  const sides = ['paddingLeft', 'paddingRight', 'borderLeftWidth', 'borderRightWidth'];
  const kinds = document.getElementById('kinds').getBoundingClientRect();
  return {
    width: box.width,
    contents: shown.at(-1).getBoundingClientRect().right - shown[0].getBoundingClientRect().left
      + sides.reduce((sum, side) => sum + parseFloat(style[side]), 0),
    middle: (box.top + box.bottom) / 2,
    kinds: (kinds.top + kinds.bottom) / 2,
  };
}"""
"""The band group's width, the width its buttons on one line ask for, which is from the first's left side to the
last's right side and the group's padding and border, and the height of its middle and of All and New's."""


class TheBandsOnAPhone(BuildTest):
    def holding(self, *held: int) -> None:
        """Make the example's newest board hold back the bands numbered `held`, counted from 0, and keep only the
        rows of the bands it does not, ranked again from 1, as a publish would give it."""
        board = read_json(self.board_file(NEWEST))
        holds = [BANDS[number] for number in held]

        def is_held(row: dict) -> bool:
            return any(
                band["least_stars"] <= row["stars"]
                and (band["most_stars"] is None or row["stars"] <= band["most_stars"])
                for band in holds
            )

        rows = [row for row in board["rows"] if not is_held(row)]
        rows = [{**row, "rank": rank} for rank, row in enumerate(rows, start=1)]
        fields = {"state": "held", "holds": holds} if holds else {"state": "rows", "holds": [], "missed_stars": []}
        self.write_board({**board, **fields, "rows": rows})

    def lines(self, browser, site: str, width: int) -> list:
        """The band buttons of the root by line, on a screen `width` pixels wide, once its type is in."""
        return self.seen(browser, site, width)[0]

    def seen(self, browser, site: str, width: int) -> tuple[list, dict]:
        """The band buttons of the root by line, and its band group, on a screen `width` pixels wide, once its type
        is in."""
        page = browser.new_page(viewport={"width": width, "height": 800})
        page.clock.set_fixed_time(published(self.out))
        page.goto(f"{site}/{BOARD.removesuffix('index.html')}", wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        group = page.get_by_role("group", name="Star band", exact=True)
        seen = group.evaluate(LINES), group.evaluate(GROUP)
        page.close()
        return seen

    def test_on_a_phone_six_band_buttons_lie_in_two_lines_of_three_of_one_width(self):
        self.holding()
        self.build_pages()
        with served(self.out) as site, chrome() as browser:
            for width in PHONES:
                with self.subTest(width=width):
                    lines = self.lines(browser, site, width)
                    self.assertEqual(
                        [[button["words"] for button in line] for line in lines],
                        [["All stars", "200–1k", "1k–3k"], ["3k–10k", "10k–30k", "30k+"]],
                    )
                    widths = [button["width"] for line in lines for button in line]
                    self.assertLessEqual(max(widths) - min(widths), 0.5, widths)

    def test_on_a_phone_no_band_button_lies_alone_on_a_line_whatever_bands_the_board_holds_back(self):
        """The example's rows have 482, 13,250, 4,207, 3,021, and 205 stars: none is in 1k–3k or 30k+, and taking
        10k–30k and then 3k–10k away leaves rows in the bands that stay."""
        for held, shown in (((1,), 5), ((1, 4), 4), ((1, 4, 3), 3), ((1, 4, 3, 2), 2)):
            with self.subTest(shown=shown):
                self.setUp()
                self.holding(*held)
                self.build_pages()
                with served(self.out) as site, chrome() as browser:
                    for width in PHONES:
                        with self.subTest(width=width):
                            lines = self.lines(browser, site, width)
                            self.assertEqual(sum(len(line) for line in lines), shown, lines)
                            self.assertGreaterEqual(min(len(line) for line in lines), 2, lines)

    def test_from_768_px_the_band_buttons_lie_on_one_line_each_as_wide_as_its_label(self):
        """As they do today: and so the group is only as wide as its buttons, and lies beside All and New, on their
        line, and not stretched across the toolbar on a line of its own."""
        for held in ((), (1,), (1, 4), (1, 4, 3), (1, 4, 3, 2)):
            with self.subTest(held=held):
                self.setUp()
                self.holding(*held)
                self.build_pages()
                with served(self.out) as site, chrome() as browser:
                    for width in DESKTOPS:
                        with self.subTest(width=width):
                            lines, group = self.seen(browser, site, width)
                            self.assertEqual(len(lines), 1, lines)
                            for button in lines[0]:
                                self.assertAlmostEqual(button["width"], button["label"], delta=1, msg=button)
                            self.assertAlmostEqual(group["width"], group["contents"], delta=1, msg=group)
                            self.assertAlmostEqual(group["middle"], group["kinds"], delta=1, msg=group)


if __name__ == "__main__":
    unittest.main()
