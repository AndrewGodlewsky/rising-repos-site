"""An opened row, on a phone: the boards it was on. Sentence 34 of the owner's tests."""

import unittest

from playwright.sync_api import expect

from owner_tests.scenario import PHONE, Scenario, boards_it_was_on, open_row, rows

FIGURES = ["Rank", "Total stars", "Stars a day", "Multiple"]
"""The heading of each figure a board gives a row that was on it, in the order it gives them."""

SEEN = """things => things.map(thing => {
  const box = thing.getBoundingClientRect();
  // What shows of it: its box, cut by the screen's two edges and by each thing round it that clips or scrolls.
  let left = Math.max(box.left, 0), right = Math.min(box.right, document.documentElement.clientWidth);
  let top = box.top, bottom = box.bottom;
  for (let round = thing.parentElement; round; round = round.parentElement) {
    const style = getComputedStyle(round);
    if (style.overflowX === 'visible' && style.overflowY === 'visible' && style.clipPath === 'none') continue;
    const edge = round.getBoundingClientRect();
    [left, right] = [Math.max(left, edge.left), Math.min(right, edge.right)];
    [top, bottom] = [Math.max(top, edge.top), Math.min(bottom, edge.bottom)];
  }
  // The words the stylesheet draws in it ahead of its own, when its own words start a line of them lower down.
  const drawn = getComputedStyle(thing, '::before');
  const heading = drawn.content.match(/^"([^"]*)"/);
  const own = document.createRange();
  own.selectNodeContents(thing);
  const under = heading && own.getBoundingClientRect().top - box.top >= parseFloat(drawn.fontSize);
  return {
    words: thing.textContent.trim(),
    heading: under ? heading[1] : '',
    whole: box.width > 1 && box.height > 1 && right - left > box.width - 0.5 && bottom - top > box.height - 0.5 &&
      thing.scrollWidth <= thing.clientWidth + 1,
    left: box.left, right: box.right, top: box.top, bottom: box.bottom,
  };
})"""
"""What a reader sees of each of some parts of a table: its words, the heading the stylesheet draws over them inside
it, if any, whether all of it shows, and where its box is. All of it shows when nothing round it that clips or
scrolls what overflows it cuts it, neither edge of the screen does, and its own words do not run out of it. A
heading that the stylesheet draws has no role and no tag to be found by, so it is read from the part it is drawn
in."""


def heading_over(figure: dict, column: dict) -> str:
    """The heading a reader sees over a figure: the one drawn in the figure's own place, over its words, or else
    its column's heading, when all of that shows and stands over the figure. Nothing, when there is neither."""
    if figure["heading"]:
        return figure["heading"]
    above = column["bottom"] <= figure["top"] + 0.5
    in_line = column["left"] < figure["right"] and figure["left"] < column["right"]
    return column["words"] if column["whole"] and above and in_line else ""


class AnOpenedRowOnAPhone(Scenario):
    def test_on_a_phone_each_board_an_opened_row_was_on_gives_every_figure_under_its_heading_and_none_is_cut(self):
        """Sentence 34. On a screen 390 pixels wide the first row is opened, and its table of the boards it was on
        is read once it has arrived. Each board gives its date and four figures: the row's rank, total stars, stars
        a day, and multiple there. Every date and every figure shows whole, with nothing cut and nothing that has
        to be scrolled to. Each figure has its heading over it in words: drawn in the figure's own place, or at the
        head of its column where all of that heading shows."""
        page = self.reader(width=PHONE)
        self.visit(page)
        self.given(rows(page).count(), "the newest board lists no repository")
        row = rows(page).first
        open_row(row)
        table = boards_it_was_on(row)
        expect(table).to_be_visible()
        columns = table.get_by_role("columnheader").evaluate_all(SEEN)[1:]
        dates = table.get_by_role("rowheader").evaluate_all(SEEN)
        figures = table.get_by_role("cell").evaluate_all(SEEN)
        self.assertEqual([column["words"] for column in columns], FIGURES)
        self.assertGreater(len(dates), 0)
        self.assertEqual(len(figures), len(FIGURES) * len(dates))
        for at, date in enumerate(dates):
            with self.subTest(date["words"]):
                self.assertTrue(date["words"])
                self.assertTrue(date["whole"], date)
                given = figures[at * len(FIGURES) : (at + 1) * len(FIGURES)]
                for figure, column in zip(given, columns, strict=True):
                    self.assertTrue(figure["words"], figure)
                    self.assertTrue(figure["whole"], figure)
                    self.assertEqual(heading_over(figure, column), column["words"], figure)


if __name__ == "__main__":
    unittest.main()
