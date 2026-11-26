"""How Baseline's table sets a repository's name, on a phone and on a desktop (#147).

On a phone the table "Every repository in the chart" squeezed its name column to about 133px, and
`overflow-wrap: anywhere` broke a name wherever its line ran out: "exteraSquad/extera|Gram". Now, below 768px, a
name's owner and its slash stand on a line of their own, in a quieter ink and a smaller type, and the name begins on
the line below, so that a name breaks at its slash and only a single word wider than the column is broken. The link,
what a screen reader hears, and the desktop's table are as they were.

Where a line of text breaks is something only a browser can show, so these open Baseline in the machine's Chrome,
as `tests/test_baseline_chart.py` does, on a board of names the issue found broken.
"""

import re

from helpers import read_json
from test_baseline_chart import DESKTOP, PHONE, ChartTest

BROKEN = (
    "exteraSquad/exteraGram",
    "alirezadir/AIMLInterviews",
    "OpenSenseNova/SenseNova-U1",
    "JoasASantos/Awesome-Red-Team-Operations",
    "Iam5tillLearning/OpenSource-Ai-Glasses",
    "LadybirdBrowser/ladybird",
    "wechat-selkies/wechat-selkies",
)
"""Names the issue and its plan found broken inside a word on a phone, each of whose words fits the column."""

TOO_WIDE = ("o/" + "PentestingEverythingAndMore" * 2, "GenielabsOpenSourceProjects/x")
"""Names that hold a single word wider than a phone's name column, the one in the name and the other in the owner."""

LONGEST = ("o1/" + "a" * 103, "o2/" + "b" * 103)
"""106 characters is the longest name in `site-data/`."""

NAMES = """() => {
  const style = el => { const s = getComputedStyle(el); return {color: s.color, size: parseFloat(s.fontSize)}; };
  return [...document.querySelectorAll('.numbers tbody th')].map(cell => {
    cell.scrollIntoView({block: 'center'});
    const link = cell.querySelector('a');
    const walker = document.createTreeWalker(link, NodeFilter.SHOW_TEXT);
    const chars = [];
    for (let node; (node = walker.nextNode());) {
      for (let i = 0; i < node.length; i++) {
        const range = document.createRange();
        range.setStart(node, i);
        range.setEnd(node, i + 1);
        const box = [...range.getClientRects()].find(r => r.width > 0) || range.getBoundingClientRect();
        chars.push({ch: node.data[i], box, el: node.parentElement});
      }
    }
    const lines = [];
    let bottom = -Infinity;
    for (const [i, c] of chars.entries()) {
      if (c.box.top + c.box.height / 2 > bottom) { lines.push([]); bottom = c.box.bottom; }
      c.line = lines.length - 1;
      lines.at(-1).push(i);
    }
    const pad = getComputedStyle(cell);
    const column = cell.getBoundingClientRect().width - parseFloat(pad.paddingLeft) - parseFloat(pad.paddingRight);
    const text = chars.map(c => c.ch).join('');
    const slash = text.indexOf('/');
    const breaks = lines.slice(1).map(line => line[0]).filter(at => !'/-'.includes(text[at - 1])).map(at => {
      const start = Math.max(text.lastIndexOf('/', at - 1), text.lastIndexOf('-', at - 1)) + 1;
      const ends = [text.indexOf('/', at), text.indexOf('-', at)].filter(end => end >= 0);
      const word = text.slice(start, ends.length ? Math.min(...ends) + 1 : text.length);
      const font = getComputedStyle(chars[at].el);
      const copy = document.createElement('div');
      copy.textContent = word;
      Object.assign(copy.style, {position: 'absolute', visibility: 'hidden', whiteSpace: 'nowrap', font: font.font,
        letterSpacing: font.letterSpacing});
      document.body.append(copy);
      const width = copy.getBoundingClientRect().width;
      copy.remove();
      return {word, width};
    });
    const owner = chars[0], name = chars[slash + 1], hit = document.elementFromPoint(
      owner.box.left + owner.box.width / 2, owner.box.top + owner.box.height / 2);
    return {
      text, lines: lines.map(line => line.map(i => text[i]).join('')), column, breaks,
      ownerLine: chars[slash].line, nameLine: name.line,
      owner: style(owner.el), name: style(name.el),
      links: cell.querySelectorAll('a').length, href: link.getAttribute('href'), target: link.getAttribute('target'),
      ownerIsLink: hit !== null && hit.closest('a') === link, innerText: link.innerText,
      height: cell.parentElement.getBoundingClientRect().height,
    };
  });
}"""
"""For each of the table's names: its text, the characters of each line it is drawn on, the width of its column, and
each line that begins inside a word, with that word measured alone in its own type; the lines its owner's slash and
its name's first character are on, and the ink and size of each; and its link."""

BACKGROUND = "() => getComputedStyle(document.body).backgroundColor"


def luminance(colour: str) -> float:
    """The relative luminance of a colour written as `rgb(r, g, b)`, by WCAG 2's formula."""
    channels = [int(c) / 255 for c in re.findall(r"\d+(?:\.\d+)?", colour)[:3]]
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(one: str, other: str) -> float:
    lighter, darker = sorted((luminance(one), luminance(other)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


class TableTest(ChartTest):
    def name_board(self, names: tuple[str, ...]) -> None:
        """Make the newest board hold one line for each of `names`, in that order, each with the first line's
        figures."""
        board = read_json(self.board_file())
        model = board["rows"][0]
        rows = [
            {**model, "rank": rank, "github_id": model["github_id"] + rank, "full_name": name}
            for rank, name in enumerate(names, start=1)
        ]
        self.write_board({**board, "rows": rows})

    def names(self, page) -> list[dict]:
        return page.evaluate(NAMES)


class OnAPhone(TableTest):
    def test_each_owner_stands_on_its_own_line_above_its_name_quieter_and_smaller_with_the_script_or_without(self):
        self.name_board(BROKEN + TOO_WIDE)
        with self.run_chart() as browser:
            for scripts in (True, False):
                page = self.baseline(browser, PHONE, touch=True, scripts=scripts)
                ground = page.evaluate(BACKGROUND)
                for line in self.names(page):
                    with self.subTest(scripts=scripts, name=line["text"]):
                        self.assertGreater(line["nameLine"], line["ownerLine"], line["lines"])
                        self.assertLess(
                            contrast(line["owner"]["color"], ground), contrast(line["name"]["color"], ground)
                        )
                        self.assertLess(line["owner"]["size"], line["name"]["size"])

    def test_no_name_breaks_inside_a_word_unless_that_word_is_wider_than_the_column(self):
        self.name_board(BROKEN + TOO_WIDE)
        with self.run_chart() as browser:
            page = self.baseline(browser, PHONE, touch=True)
            lines = self.names(page)
            for line in lines:
                with self.subTest(name=line["text"]):
                    for broken in line["breaks"]:
                        self.assertGreater(broken["width"], line["column"], f"{broken['word']} in {line['lines']}")
            self.assertTrue(any(line["breaks"] for line in lines), "no word wider than the column was broken to fit")

    def test_with_the_longest_names_neither_the_table_nor_the_page_scrolls_sideways(self):
        self.name_board(LONGEST + BROKEN + TOO_WIDE)
        with self.run_chart() as browser:
            page = self.baseline(browser, PHONE, touch=True)
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth - innerWidth"), 0)
            table = page.locator(".numbers").bounding_box()
            figures = page.locator(".figures").bounding_box()
            self.assertLessEqual(table["x"] + table["width"], figures["x"] + figures["width"] + 0.5)


class TheNameCell(TableTest):
    def test_the_whole_owner_and_name_is_one_link_to_the_repository_in_the_same_tab(self):
        self.name_board(BROKEN + TOO_WIDE)
        with self.run_chart() as browser:
            for width in (PHONE, DESKTOP):
                page = self.baseline(browser, width, touch=width == PHONE)
                for line in self.names(page):
                    with self.subTest(width=width, name=line["text"]):
                        self.assertEqual(line["links"], 1)
                        self.assertEqual(line["href"], f"https://github.com/{line['text']}")
                        self.assertIsNone(line["target"])
                        self.assertTrue(line["ownerIsLink"], "the owner's line is not part of the link")

    def test_the_links_name_and_text_read_owner_slash_name_as_one_run(self):
        names = BROKEN + TOO_WIDE
        self.name_board(names)
        with self.run_chart() as browser:
            for width in (PHONE, DESKTOP):
                page = self.baseline(browser, width, touch=width == PHONE)
                table = page.locator(".numbers")
                read = {line["text"]: line["innerText"] for line in self.names(page)}
                for name in names:
                    with self.subTest(width=width, name=name):
                        link = table.get_by_role("rowheader").get_by_role("link", name=name, exact=True)
                        self.assertEqual(link.count(), 1)
                        self.assertEqual(read[name], name)


class OnADesktop(TableTest):
    def test_each_name_is_one_line_in_one_ink_and_type_and_the_table_is_as_wide_and_tall_as_before(self):
        """As before is one line of the table's own type to a name: each line is as tall as the line of the
        shortest name, and the table is as wide as its section."""
        self.name_board(("a/b",) + BROKEN + TOO_WIDE)
        with self.run_chart() as browser:
            page = self.baseline(browser, DESKTOP, touch=False)
            lines = self.names(page)
            for line in lines:
                with self.subTest(name=line["text"]):
                    self.assertEqual(len(line["lines"]), 1, line["lines"])
                    self.assertEqual(line["owner"], line["name"])
                    self.assertAlmostEqual(line["height"], lines[0]["height"], delta=1)
            table = page.locator(".numbers").bounding_box()
            figures = page.locator(".figures").bounding_box()
            self.assertEqual(table["width"], figures["width"])
