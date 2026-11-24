"""Choosing a dot of Baseline's chart without a mouse: by a tap on a phone, and by a repository's name. Sentences 36
and 37 of the owner's tests."""

import math
import re
import unittest
from datetime import datetime, timedelta

from playwright.sync_api import Locator, Page, expect

from owner_tests.scenario import PHONE, WAIT, Scenario, board, heading, names


def chart(page: Page) -> Locator:
    """Baseline's chart: the one picture on the page that a screen reader is told of."""
    return page.get_by_role("main").get_by_role("img")


def figure(page: Page) -> Locator:
    """The figure that holds the chart, its marks, and what it names."""
    return page.get_by_role("figure").filter(has=page.get_by_role("img"))


def named(page: Page, name: str) -> Locator:
    """The words in the chart's figure that name the repository `name`. A stroke in a pattern would end it where the
    browser reads it, so the name is written as escaped."""
    return figure(page).get_by_text(re.compile(re.escape(name).replace("/", r"\/")))


def line_of(page: Page, name: str) -> list[str]:
    """What Baseline's table gives in the cells of the repository `name`'s line: its rank and its figures."""
    row = (
        board(page)
        .get_by_role("row")
        .filter(has=page.get_by_role("rowheader").get_by_role("link", name=name, exact=True))
    )
    return [" ".join(cell.split()) for cell in row.get_by_role("cell").all_inner_texts()]


def dots(page: Page) -> list[tuple[float, float]]:
    """Where each dot of the chart is on the screen. Each is the start of a stroke of no length, which is how the
    chart's drawing makes a dot, placed in a drawing 100 across and 100 down that fills the chart's box."""
    box = chart(page).bounding_box()
    strokes = chart(page).locator("path").evaluate_all("paths => paths.map(path => path.getAttribute('d') || '')")
    return [
        (box["x"] + float(x) / 100 * box["width"], box["y"] + float(y) / 100 * box["height"])
        for stroke in strokes
        for x, y in re.findall(r"M([\d.]+)[ ,]([\d.]+)", stroke)
    ]


class ChoosingADotOfBaseline(Scenario):
    def baseline(self, width: int, touch: bool) -> tuple[Page, list[str]]:
        """A reader on a screen `width` pixels wide, with a touch screen or without, who has come to Baseline from the
        newest board, and the names that board lists, in its order. The clock is set as `Scenario.reader` sets it,
        which makes no reader with a touch screen."""
        context = self.site.browser.new_context(
            viewport={"width": width, "height": 900}, has_touch=touch, is_mobile=touch
        )
        self.addCleanup(context.close)
        context.set_default_timeout(WAIT)
        context.set_default_navigation_timeout(3 * WAIT)
        if self.site.boards:
            context.clock.set_fixed_time(
                datetime.fromisoformat(self.site.boards[0]["published_at"]) + timedelta(hours=1)
            )
        page = context.new_page()
        self.visit(page)
        listed = names(page)
        self.given(listed, "the newest board lists no repository, so Baseline has none to place")
        page.get_by_role("banner").get_by_role("link", name="Baseline").click()
        expect(heading(page)).to_be_visible()
        expect(chart(page)).to_be_visible()
        chart(page).scroll_into_view_if_needed()
        return page, listed

    def test_on_a_phone_a_tap_on_a_dot_of_baselines_chart_names_its_repository_as_the_table_does_until_a_tap_away(self):
        """Sentence 36. On a touch screen 390 pixels wide, the chart marks the dots of the board's first rows with
        their ranks, each mark a little to the right of its dot. A tap on such a dot names the repository of that
        rank, with its rank and each figure the table gives on its line, and the name is still shown once the finger
        has lifted. A tap on another marked dot names that one instead, and a tap where no dot is near names none.
        A mark that two dots share names either repository."""
        page, listed = self.baseline(PHONE, touch=True)
        plot = chart(page).bounding_box()
        marks = []
        for mark in figure(page).get_by_text(re.compile(r"^\d+(, \d+)*$")).all():
            at = mark.bounding_box()
            across, down = at["x"] + at["width"] / 2, at["y"] + at["height"] / 2
            # A figure of the axes stands outside the plot, and a rank's mark within it.
            if plot["x"] < across < plot["x"] + plot["width"] and plot["y"] < down < plot["y"] + plot["height"]:
                marks.append(([listed[int(rank) - 1] for rank in mark.inner_text().split(", ")], at["x"] - 10, down))
        self.given(len(marks) >= 2, "the chart marks fewer than two dots with their ranks")
        before = None
        for repositories, across, down in marks[:2]:
            with self.subTest(repositories):
                page.touchscreen.tap(across, down)
                either = "|".join(re.escape(name).replace("/", r"\/") for name in repositories)
                readout = figure(page).get_by_text(re.compile(either))
                expect(readout).to_be_visible()
                said = " ".join(readout.inner_text().split())
                name = next(name for name in repositories if name in said)
                for cell in line_of(page, name):
                    self.assertIn(cell, said)
                if before and before not in repositories:
                    expect(named(page, before)).to_be_hidden()
                before = name
        everywhere = dots(page)
        spots = [
            (plot["x"] + plot["width"] * i / 10, plot["y"] + plot["height"] * j / 10)
            for i in range(1, 10)
            for j in range(1, 10)
        ]
        away = max(spots, key=lambda spot: min(math.dist(spot, dot) for dot in everywhere))
        self.given(min(math.dist(away, dot) for dot in everywhere) > 40, "no place on the chart is far from every dot")
        page.touchscreen.tap(*away)
        expect(named(page, before)).to_be_hidden()

    def test_typing_part_of_a_repositorys_name_in_baselines_find_field_names_the_first_by_rank_that_holds_it(self):
        """Sentence 37. On a phone 390 pixels wide, the reader types in the field "Find a repository" the part after
        the slash of the name of the last repository the board lists, in capitals. The chart names the first by rank
        whose name holds those words, in any case. Then the reader types words that no name holds, and the field
        says that none does, and the chart no longer names that repository."""
        page, listed = self.baseline(PHONE, touch=False)
        field = page.get_by_role("searchbox", name="Find a repository")
        expect(field).to_be_visible()
        typed = listed[-1].partition("/")[2]
        first = next(name for name in listed if typed.lower() in name.lower())
        field.fill(typed.upper())
        expect(named(page, first)).to_be_visible()
        nothing = "no-name-holds-these-words-0"
        self.assertFalse([name for name in listed if nothing in name.lower()])
        field.fill(nothing)
        expect(figure(page).get_by_text(re.compile(r"\bnone\b", re.IGNORECASE))).to_be_visible()
        expect(named(page, first)).to_be_hidden()


if __name__ == "__main__":
    unittest.main()
