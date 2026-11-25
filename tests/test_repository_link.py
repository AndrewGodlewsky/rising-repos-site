"""A row's name, the one link on its line, which leads off the site to the repository on GitHub (#30).

The name was the only underlined text in a row, so it looked like the row's own control, and a click on it left the
board for GitHub in the same tab, with nothing to say so, while a click on the rest of the row opened the row. So the
name now carries a mark that it leaves the site, the title "Opens on GitHub", and opens GitHub in a new tab, and the
rest of the row opens the row as before.

The mark is drawn by the stylesheet after the link's text, so the name a reader, the board's search, and a screen
reader read is the name alone. It is Rising Sans's own upwards arrow turned to point up and right: the type holds no
arrow that points that way, and a new character would cut the faces again (P10).

These open the pages in the Chrome the machine already has, through Playwright, as tests/test_opened_row.py does, and
fail without it. They build from the tests' own copy of the data contract's example, serve the pages from this
machine alone, and answer every request to GitHub with a stand-in, so that nothing leaves the machine.
"""

import ast
import contextlib
import unittest
from pathlib import Path

from helpers import BuildTest, read_json

import sitebuild
from sitebuild import BOARD
from sitework.layout import chrome, published, served

PHONE, DESKTOP = 390, 1440

GITHUB = "https://github.com/"

TITLE = "Opens on GitHub"

TURNED = "matrix(0.707107, 0.707107, -0.707107, 0.707107, 0, 0)"
"""A turn of 45 degrees clockwise, as a browser computes `rotate(45deg)`: the upwards arrow then points up and right."""

MARK = """(link) => {
  const after = getComputedStyle(link, "::after");
  const rects = (part) => [...part.getClientRects()].map((box) => ({ top: box.top, right: box.right }));
  return {
    content: after.content,
    display: after.display,
    transform: after.transform,
    colour: after.color,
    linkColour: getComputedStyle(link).color,
    link: rects(link),
    name: rects(link.querySelector(".nm")),
    text: link.innerText,
  };
}"""
"""Run on a row's link: what the stylesheet draws after it and how, the link's own colour, the boxes of each line of
the link and of the name inside it, and the link's text as a reader sees it."""


def held() -> set[int]:
    """Each character the site's type holds, from the list `sitebuild/fonts/subset.py` cuts the faces to. The list is
    read from the script's text, since the script needs fontTools, which the build and the tests do not."""
    script = ast.parse((Path(sitebuild.__file__).parent / "fonts" / "subset.py").read_text(encoding="utf-8"))
    (characters,) = [
        node.value.value
        for node in script.body
        if isinstance(node, ast.Assign) and [target.id for target in node.targets] == ["CHARACTERS"]
    ]
    points = set()
    for part in characters.split(","):
        first, _, last = part.removeprefix("U+").partition("-")
        points.update(range(int(first, 16), int(last or first, 16) + 1))
    return points


def drawn(content: str) -> str:
    """The characters a computed `content` draws: what is inside its first pair of quotes. What follows a slash is
    the text a screen reader is given in their place."""
    return content.split('"')[1] if content.count('"') >= 2 else ""


class LinkTest(BuildTest):
    def setUp(self):
        super().setUp()
        self.build_pages()
        self.names = [row["full_name"] for row in read_json(self.board_file())["rows"]]

    @contextlib.contextmanager
    def board(self, width: int, scripts: bool = True):
        """The root, the newest board, loaded in a browser of its own on a screen `width` pixels wide, with its
        scripts on or off and its type in place. GitHub answers with a stand-in that says which page was asked."""
        with served(self.out) as site, chrome() as browser:
            context = browser.new_context(viewport={"width": width, "height": 900}, java_script_enabled=scripts)
            context.route(
                GITHUB + "**",
                lambda route: route.fulfill(content_type="text/html", body="<title>GitHub stand-in</title>"),
            )
            page = context.new_page()
            if scripts:
                page.clock.set_fixed_time(published(self.out))
            page.goto(f"{site}/{BOARD.removesuffix('index.html')}", wait_until="load")
            if scripts:
                page.evaluate("document.fonts.ready.then(() => true)")
            try:
                yield page
            finally:
                context.close()

    def links(self, page):
        return page.locator("table.chart > tbody > tr th.re a")


class TheMark(LinkTest):
    def test_every_rows_name_is_followed_by_the_mark_that_it_leaves_the_site_with_scripts_on_or_off(self):
        """The mark is drawn after the name, on the name's own line, inside the link and in the link's colour, so it
        dims with the name once the repository is visited, and it is no part of the link's text."""
        for width in (PHONE, DESKTOP):
            for scripts in (True, False):
                with self.subTest(width=width, scripts=scripts), self.board(width, scripts) as page:
                    seen = [link.evaluate(MARK) for link in self.links(page).all()]
                    self.assertEqual(len(seen), len(self.names))
                    for name, mark in zip(self.names, seen, strict=True):
                        self.assertEqual(drawn(mark["content"]), "\N{UPWARDS ARROW}", name)
                        self.assertEqual(mark["display"], "inline-block", name)
                        self.assertEqual(mark["transform"], TURNED, name)
                        self.assertEqual(mark["colour"], mark["linkColour"], name)
                        self.assertEqual(mark["text"], name)
                        # The mark comes after the name: the link's last line runs on past the name's by it, or, where
                        # the name ends at the edge of its column, the mark begins the line under the name's, since a
                        # line may break before a part that is turned.
                        last, name_last = mark["link"][-1], mark["name"][-1]
                        if abs(last["top"] - name_last["top"]) <= 4:
                            self.assertGreater(last["right"] - name_last["right"], 6, name)
                        else:
                            self.assertGreater(last["top"], name_last["top"], name)

    def test_the_mark_is_a_character_the_type_holds(self):
        with self.board(DESKTOP) as page:
            content = self.links(page).first.evaluate("(link) => getComputedStyle(link, '::after').content")
        mark = drawn(content)
        self.assertTrue(mark, content)
        self.assertEqual([character for character in mark if ord(character) not in held()], [])


class TheLink(LinkTest):
    def test_a_click_or_enter_on_a_name_opens_github_in_a_new_tab_and_the_board_stays_with_scripts_on_or_off(self):
        """The new tab has no hold on the board's: its `window.opener` is null, so GitHub's page cannot move it."""
        for scripts in (True, False):
            for how in ("click", "Enter"):
                with self.subTest(scripts=scripts, how=how), self.board(DESKTOP, scripts) as page:
                    board = page.url
                    link = self.links(page).first
                    with page.context.expect_page() as opening:
                        if how == "click":
                            link.click()
                        else:
                            link.focus()
                            page.keyboard.press("Enter")
                    tab = opening.value
                    tab.wait_for_load_state()
                    self.assertEqual(tab.url, GITHUB + self.names[0])
                    self.assertTrue(tab.evaluate("() => window.opener === null"))
                    self.assertEqual(page.url, board)
                    self.assertEqual(self.links(page).count(), len(self.names))

    def test_the_name_is_titled_and_described_opens_on_github(self):
        """The title is what the browser shows under the pointer, and what it gives a screen reader as the link's
        description, read after its name."""
        with self.board(DESKTOP) as page:
            links = self.links(page)
            self.assertEqual([link.get_attribute("title") for link in links.all()], [TITLE] * len(self.names))
            tree = page.context.new_cdp_session(page)
            document = tree.send("DOM.getDocument")["root"]["nodeId"]
            found = tree.send("DOM.querySelectorAll", {"nodeId": document, "selector": "table.chart th.re a"})
            for name, node in zip(self.names, found["nodeIds"], strict=True):
                (link, *_) = tree.send("Accessibility.getPartialAXTree", {"nodeId": node, "fetchRelatives": False})[
                    "nodes"
                ]
                self.assertEqual(link["role"]["value"], "link", name)
                self.assertEqual(link["name"]["value"], name)
                self.assertEqual(link.get("description", {}).get("value"), TITLE, name)


class TheRow(LinkTest):
    def test_a_click_on_a_rows_line_away_from_its_name_opens_and_closes_it_and_opens_no_tab(self):
        with self.board(DESKTOP) as page:
            row = page.locator("table.chart > tbody > tr").first
            details = row.locator("td.wy details")
            row.locator("td.de").click()
            # Opening a row waits for the board day's history, so the row is open once it has arrived.
            page.wait_for_function("(details) => details.open", arg=details.element_handle())
            row.locator("td.de").click()
            page.wait_for_function("(details) => !details.open", arg=details.element_handle())
            self.assertEqual(len(page.context.pages), 1)


class TheName(LinkTest):
    def test_the_links_text_and_accessible_name_are_owner_slash_name_alone(self):
        """The board's search and every reader's tools read the name as before, with no mark or arrow in it."""
        with self.board(DESKTOP) as page:
            links = self.links(page)
            self.assertEqual(links.all_inner_texts(), self.names)
            board = page.locator("table.chart")
            for name in self.names:
                self.assertEqual(board.get_by_role("link", name=name, exact=True).count(), 1, name)


if __name__ == "__main__":
    unittest.main()
