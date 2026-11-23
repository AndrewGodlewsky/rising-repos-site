"""For every reader: scripts off, the theme, a phone, the keyboard, and the colours of the text. Sentences 21 to 25
of the owner's tests."""

import re
import unittest

from playwright.sync_api import Page, expect
from playwright.sync_api import TimeoutError as NotInTime

from owner_tests.scenario import (
    DESKTOP,
    PHONE,
    Scenario,
    address_of,
    boards_it_was_on,
    day_bar,
    names,
    open_row,
    rows,
)

CONTROLS = ("button", "combobox", "searchbox", "textbox", "checkbox", "radio", "switch", "slider")
"""The roles of the things a reader works a page with. A link is not one: it leads somewhere with scripts off."""

IS_DARK = """dark => {
  const [red, green, blue] = getComputedStyle(document.body).backgroundColor.match(/[\\d.]+/g).map(Number);
  return (0.2126 * red + 0.7152 * green + 0.0722 * blue < 128) === dark;
}"""
"""Whether the page is dark, or light, as it is asked: by how bright the colour behind the whole page is."""

PAST_THE_EDGE = """() => {
  const screen = document.documentElement.clientWidth;
  const past = new Set();
  // A box or a line of text, cut to what each thing round it that clips or scrolls its overflow lets show.
  function check(what, inside, box) {
    let left = box.left, right = box.right;
    for (let round = inside; round; round = round.parentElement) {
      if (getComputedStyle(round).overflowX === 'visible') continue;
      const edge = round.getBoundingClientRect();
      left = Math.max(left, edge.left);
      right = Math.min(right, edge.right);
    }
    if (right > left && (right > screen + 0.5 || left < -0.5)) {
      past.add(what + ', from ' + Math.round(left) + ' to ' + Math.round(right) + ' pixels across');
    }
  }
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
  for (let node = walk.nextNode(); node; node = walk.nextNode()) {
    const element = node.nodeType === 1 ? node : node.parentElement;
    if (!element.checkVisibility({ visibilityProperty: true, contentVisibilityAuto: true })) continue;
    if (node.nodeType === 1) {
      check('a <' + element.tagName.toLowerCase() + '>', element.parentElement, element.getBoundingClientRect());
    } else if (node.nodeValue.trim()) {
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const line of range.getClientRects()) check('the text "' + node.nodeValue.trim() + '"', element, line);
    }
  }
  return [document.documentElement.scrollWidth, screen, [...past]];
}"""
"""How wide the page is and how wide the screen, and everything shown that reaches past either edge of the screen: a
box, or a line of text, which can run on past the box it is in. A thing inside a part of the page that scrolls or
clips what overflows it reaches only as far as that part does."""

CONTROLS_AND_FOCUS = """() => {
  const controls = [...document.querySelectorAll('button, select, input, textarea, summary')]
    .filter(control => control.checkVisibility({ visibilityProperty: true }));
  const focused = document.activeElement;
  const style = getComputedStyle(focused);
  return {
    names: controls.map(control => control.tagName.toLowerCase() + ' "' +
      (control.getAttribute('aria-label') || control.textContent || control.placeholder).trim().split('\\n')[0] + '"'),
    stops: document.querySelectorAll('a[href], button, select, input, textarea, summary').length,
    at: controls.indexOf(focused),
    nowhere: focused === document.body,
    ring: style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0,
  };
}"""
"""The page's controls that are shown, by the tags that make one, how many places the keyboard could stop at, which
control the keyboard is on, if any, and whether the thing it is on is drawn with an outline: its ring."""

FAINT_TEXT = """() => {
  function parse(colour) {
    const parts = colour.match(/[\\d.]+/g).map(Number);
    return [parts[0], parts[1], parts[2], parts.length > 3 ? parts[3] : 1];
  }
  function over(top, under) {
    return [0, 1, 2].map(part => top[part] * top[3] + under[part] * (1 - top[3])).concat([1]);
  }
  // The colour a text is set on: the background of each thing round it, the nearest on top, down to one that is solid.
  function behind(element) {
    const layers = [];
    for (let round = element; round; round = round.parentElement) {
      const colour = parse(getComputedStyle(round).backgroundColor);
      if (colour[3] > 0) layers.push(colour);
      if (colour[3] === 1) break;
    }
    return layers.reduceRight((under, top) => over(top, under), [255, 255, 255, 1]);
  }
  function brightness(colour) {
    const [red, green, blue] = colour.slice(0, 3).map(part => {
      part /= 255;
      return part <= 0.04045 ? part / 12.92 : ((part + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
  }
  // Whether any of a box shows, once each thing round it that clips its overflow has cut it.
  function shows(inside, box) {
    let [left, right, top, bottom] = [box.left, box.right, box.top, box.bottom];
    for (let round = inside; round; round = round.parentElement) {
      const style = getComputedStyle(round);
      if (style.overflowX === 'visible' && style.overflowY === 'visible' && style.clipPath === 'none') continue;
      const edge = round.getBoundingClientRect();
      [left, right] = [Math.max(left, edge.left), Math.min(right, edge.right)];
      [top, bottom] = [Math.max(top, edge.top), Math.min(bottom, edge.bottom)];
    }
    return right - left > 1 && bottom - top > 1;
  }
  const faint = new Map();
  let read = 0;
  function check(words, element, colour) {
    const on = behind(element);
    const [lighter, darker] = [brightness(over(parse(colour), on)), brightness(on)].sort((a, b) => b - a);
    const ratio = (lighter + 0.05) / (darker + 0.05);
    read += 1;
    if (ratio < 4.5) {
      faint.set(colour + ' on rgb(' + on.slice(0, 3).map(Math.round).join(', ') + ')',
        ratio.toFixed(2) + ':1, as in "' + words.trim().slice(0, 40) + '"');
    }
  }
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
  for (let node = walk.nextNode(); node; node = walk.nextNode()) {
    const element = node.nodeType === 1 ? node : node.parentElement;
    if (element.closest('script, style, option')) continue;
    if (!element.checkVisibility({ visibilityProperty: true, contentVisibilityAuto: true })) continue;
    if (node.nodeType === 3) {
      if (!node.nodeValue.trim()) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      if ([...range.getClientRects()].some(line => shows(element, line))) {
        check(node.nodeValue, element, getComputedStyle(element).color);
      }
      continue;
    }
    if (!shows(element, element.getBoundingClientRect())) continue;
    for (const part of ['::before', '::after']) {
      const style = getComputedStyle(element, part);
      if (/[A-Za-z0-9]/.test(style.content.replace(/^(none|normal)$/, ''))) check(style.content, element, style.color);
    }
    if (element.matches('select')) {
      check(element.options[element.selectedIndex].text, element, getComputedStyle(element).color);
    }
    if (element.matches('input, textarea') && element.placeholder && !element.value) {
      check(element.placeholder, element, getComputedStyle(element, '::placeholder').color);
    }
  }
  return [read, [...faint].map(([colours, how]) => colours + ': ' + how)];
}"""
"""How many texts the page shows, and each pair of colours among them, a text's on what it is set on, that falls
short of 4.5:1 by the WCAG's measure, with one text that has it. A text is every run of words a reader can see, the
words a stylesheet adds beside a figure, a list's chosen entry, and the hint in an empty search box. What a text is
set on is worked out as the browser paints it, a see-through colour laid over the one behind it."""


class ForEveryReader(Scenario):
    def test_with_scripts_off_every_row_is_listed_and_no_control_shows_that_would_do_nothing(self):
        """Sentence 21. With scripts off the newest board lists every row it lists with them on, in the same order.
        No page of any kind shows a control: with scripts off, the filter and the theme switch would do nothing. A
        row's disclosure is the browser's own, and sentence 4 holds that it still opens."""
        on = self.reader()
        self.visit(on)
        listed = names(on)
        self.given(listed, "the newest board lists no repository")
        off = self.reader(scripts=False)
        self.visit(off)
        expect(rows(off)).to_have_count(len(listed))
        self.assertEqual(names(off), listed)
        for place in self.each_kind_of_page(off):
            off.goto(place)
            for role in CONTROLS:
                with self.subTest(place, role=role):
                    expect(off.get_by_role(role)).to_have_count(0)

    def expect_theme(self, page: Page, dark: bool) -> None:
        try:
            page.wait_for_function(IS_DARK, arg=dark)
        except NotInTime:
            self.fail(f"the page at {page.url} is not {'dark' if dark else 'light'}")

    def test_the_theme_switch_turns_the_page_light_or_dark_and_the_choice_is_kept(self):
        """Sentence 22. A reader whose browser asks for light gets a light page, and one whose browser asks for dark
        a dark one. The switch turns it to the other, and it stays so when the page is loaded again, on another page
        of the site, and in a new tab. Pressed again, it turns the page back, and that is kept too."""
        for dark in (False, True):
            with self.subTest(the_browser_asks_for="dark" if dark else "light"):
                page = self.reader(dark=dark)
                self.visit(page)
                switch = page.get_by_role("button", name="Dark theme")
                self.expect_theme(page, dark)
                expect(switch).to_have_attribute("aria-pressed", str(dark).lower())
                for chosen in (not dark, dark):
                    switch.click()
                    self.expect_theme(page, chosen)
                    expect(switch).to_have_attribute("aria-pressed", str(chosen).lower())
                    page.reload()
                    self.expect_theme(page, chosen)
                    page.get_by_role("banner").get_by_role("link", name="History").click()
                    self.expect_theme(page, chosen)
                    tab = page.context.new_page()
                    self.visit(tab)
                    self.expect_theme(tab, chosen)
                    tab.close()
                    self.visit(page)

    def test_on_a_phone_nothing_reaches_past_the_edge_of_the_screen_with_a_row_opened(self):
        """Sentence 23. On a screen 390 pixels wide, with the first row opened and everything it shows arrived, the
        page is no wider than the screen, and nothing shown reaches past either edge of it."""
        page = self.reader(width=PHONE)
        self.visit(page)
        self.given(rows(page).count(), "the newest board lists no repository")
        open_row(rows(page).first)
        expect(boards_it_was_on(rows(page).first)).to_be_visible()
        wide, screen, past = page.evaluate(PAST_THE_EDGE)
        self.assertEqual(past, [])
        self.assertLessEqual(wide, screen)

    def test_the_keyboard_reaches_every_control_and_each_shows_its_ring(self):
        """Sentence 24. On the newest board, the Tab key is pressed until it has been everywhere it goes. It stops
        on every control the page shows: the theme switch, each button of the filter, both lists, the search box,
        and each row's disclosure. Each one it stops on is drawn with its ring."""
        page = self.reader()
        self.visit(page)
        start = page.evaluate(CONTROLS_AND_FOCUS)
        self.given(len(start["names"]) > 1, "the newest board shows no control but the theme switch")
        reached, without_ring = set(), []
        for _ in range(start["stops"] + 2):
            page.keyboard.press("Tab")
            now = page.evaluate(CONTROLS_AND_FOCUS)
            if now["nowhere"]:
                break
            if now["at"] >= 0:
                reached.add(now["at"])
                if not now["ring"]:
                    without_ring.append(start["names"][now["at"]])
        missed = [name for at, name in enumerate(start["names"]) if at not in reached]
        self.assertEqual(missed, [], "the keyboard did not reach these")
        self.assertEqual(without_ring, [], "these show no ring when the keyboard is on them")

    def test_every_text_colour_meets_4_5_to_1_against_what_it_is_set_on_in_both_themes(self):
        """Sentence 25. In the light theme and in the dark, every text is measured against what it is set on: on a
        page of each kind, on each of the eight boards before the newest, where a board's notes are, and on the
        newest board at both widths, with a row opened, each button of the filter pressed in turn, and a search that
        leaves no row."""
        for dark in (False, True):
            theme = "dark" if dark else "light"
            page = self.reader(dark=dark)
            for place in self.each_kind_of_page(page):
                with self.subTest(place, theme=theme):
                    page.goto(place)
                    self.assert_no_faint_text(page)
            self.visit(page)
            for back in range(1, 9):
                before = day_bar(page).get_by_role("link", name=re.compile("^The board before"))
                if not before.count():
                    break
                page.goto(address_of(before))
                with self.subTest(f"{back} before the newest board", theme=theme):
                    self.assert_no_faint_text(page)
            for width in (PHONE, DESKTOP):
                with self.subTest("the newest board, in use", theme=theme, width=width):
                    page = self.reader(dark=dark, width=width)
                    self.visit(page)
                    self.assert_no_faint_text(page)
                    if rows(page).count():
                        open_row(rows(page).first)
                        expect(boards_it_was_on(rows(page).first)).to_be_visible()
                        buttons = page.get_by_role("main").get_by_role("button")
                        for at in range(buttons.count()):
                            buttons.nth(at).click()
                            self.assert_no_faint_text(page)
                        page.get_by_role("searchbox").fill("qzxjv-held-by-no-row")
                        self.assert_no_faint_text(page)

    def assert_no_faint_text(self, page: Page) -> None:
        # A colour that is on its way from one to another is neither, so the page is read once it has settled.
        page.wait_for_function("() => document.getAnimations().length === 0")
        read, faint = page.evaluate(FAINT_TEXT)
        self.assertGreater(read, 0)
        self.assertEqual(faint, [])


if __name__ == "__main__":
    unittest.main()
