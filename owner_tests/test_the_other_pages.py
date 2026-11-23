"""The other pages: Baseline and How it works. Sentences 18 to 20 of the owner's tests."""

import re
import unittest

from playwright.sync_api import Locator, Page, expect

from owner_tests.scenario import Scenario, heading, names


def chart(page: Page) -> Locator:
    """Baseline's chart: the one picture on the page that a screen reader is told of."""
    return page.get_by_role("main").get_by_role("img")


class TheOtherPages(Scenario):
    def baseline(self) -> tuple[Page, list[str]]:
        """A reader who has come to Baseline from the newest board, and the names that board lists, in its order."""
        page = self.reader()
        self.visit(page)
        listed = names(page)
        self.given(listed, "the newest board lists no repository, so Baseline has none to place")
        page.get_by_role("banner").get_by_role("link", name="Baseline").click()
        expect(heading(page)).to_be_visible()
        expect(chart(page)).to_be_visible()
        return page, listed

    def test_baseline_draws_and_lists_every_repository_of_the_newest_board(self):
        """Sentence 18. Baseline's table lists the names the newest board lists, in the board's order. Its chart is
        described as holding that many repositories, and draws that many dots: each is the start of a stroke of no
        length, which is how the chart's drawing makes a dot."""
        page, listed = self.baseline()
        table = page.get_by_role("main").get_by_role("table")
        self.assertEqual([name.strip() for name in table.get_by_role("link").all_inner_texts()], listed)
        expect(chart(page)).to_have_accessible_name(re.compile(rf"\b{len(listed):,} repositor"))
        strokes = chart(page).locator("path").evaluate_all("paths => paths.map(path => path.getAttribute('d'))")
        self.assertEqual(sum(stroke.count("M") for stroke in strokes), len(listed))

    def test_moving_over_baselines_chart_names_the_nearest_repository(self):
        """Sentence 19. The chart marks the dots of the board's first rows with their ranks, each mark a little to
        the right of its dot. With the pointer on such a dot, the chart names the repository of that rank, as the
        table lists it. On another, it names that one instead. Off the chart, it names none."""
        page, listed = self.baseline()
        figure = page.get_by_role("figure").filter(has=page.get_by_role("img"))
        chart(page).scroll_into_view_if_needed()
        plot = chart(page).bounding_box()
        marks = []
        for mark in figure.get_by_text(re.compile(r"^\d+(, \d+)*$")).all():
            at = mark.bounding_box()
            across, down = at["x"] + at["width"] / 2, at["y"] + at["height"] / 2
            # A figure of the axes stands outside the plot, and a rank's mark within it.
            if plot["x"] < across < plot["x"] + plot["width"] and plot["y"] < down < plot["y"] + plot["height"]:
                marks.append(([listed[int(rank) - 1] for rank in mark.inner_text().split(", ")], at["x"] - 10, down))
        self.given(marks, "the chart marks no dot with its rank")
        named = None
        for repositories, across, down in marks[:2]:
            with self.subTest(repositories):
                page.mouse.move(across, down)
                # A stroke in a pattern would end it where the browser reads it, so each is written as escaped.
                either = "|".join(re.escape(name).replace("/", r"\/") for name in repositories)
                readout = figure.get_by_text(re.compile(either))
                expect(readout).to_be_visible()
                if named:
                    expect(figure.get_by_text(named)).to_be_hidden()
                named = repositories[0]
        page.mouse.move(plot["x"] + plot["width"] / 2, 2)
        expect(figure.get_by_text(named)).to_be_hidden()

    def test_how_it_works_names_the_formula_that_ranked_the_newest_board(self):
        """Sentence 20. The newest board says which version of the formula ranked it, and How it works, reached from
        the site's bar, names that version."""
        page = self.reader()
        self.visit(page)
        ranked_by = page.get_by_role("main").get_by_text(re.compile(r"Ranked by formula version \d+")).inner_text()
        version = re.search(r"formula version (\d+)", ranked_by).group(1)
        page.get_by_role("banner").get_by_role("link", name="How it works").click()
        expect(heading(page)).to_be_visible()
        expect(page.get_by_role("main").get_by_text(re.compile(rf"formula version {version}\b")).first).to_be_visible()


if __name__ == "__main__":
    unittest.main()
