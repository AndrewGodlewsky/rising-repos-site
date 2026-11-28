"""Following an example down How it works's diagram. Sentence 47 of the owner's tests."""

import unittest

from playwright.sync_api import Locator, Page, expect

from owner_tests.scenario import Scenario, heading


def readout(page: Page, name: str) -> Locator:
    """The figures of the example called `name`, which are headed by its name. Of the two places the name shows, its
    button and its figures, the figures come after the buttons in the page's order."""
    return page.get_by_role("main").get_by_text(name, exact=True).filter(visible=True).last.locator("..")


class FollowingAnExample(Scenario):
    def chosen(self, page: Page, examples: Locator, name: str) -> tuple[tuple[str, ...], int]:
        """What the page shows once the example `name` is chosen: its figures, and on how many ways off the board the
        words "Stops here" show. Only its button is pressed, and of every example only its own name shows besides
        the buttons. It either stops at one way off, or its figures say it is on the board, and not both."""
        main = page.get_by_role("main")
        expect(examples.get_by_role("button", pressed=True)).to_have_count(1)
        expect(examples.get_by_role("button", name=name, exact=True)).to_have_attribute("aria-pressed", "true")
        for other in examples.get_by_role("button").all_inner_texts():
            expect(main.get_by_text(other, exact=True).filter(visible=True)).to_have_count(2 if other == name else 1)
        shown = readout(page, name)
        figures = tuple(shown.get_by_role("definition").all_inner_texts())
        self.assertTrue(figures, f"{name} shows no figures")
        stops = main.get_by_text("Stops here", exact=True).filter(visible=True)
        on_the_board = "On the board" in shown.inner_text()
        expect(stops).to_have_count(0 if on_the_board else 1)
        return figures, stops.count()

    def test_on_how_it_works_an_example_shows_its_figures_alone_and_marks_where_it_stops_or_that_it_is_on_the_board(
        self,
    ):
        """Sentence 47. A reader at How it works, reached from the site's bar, finds one example of the group of
        examples chosen. They press each example's button in turn. That button alone is pressed; of the examples, only
        its name shows besides the buttons, at the head of its figures; its figures are its own, unlike any other
        example's; and either the words "Stops here" show at one way off the board, or none do and its figures say it
        is on the board. At least one example stops, and at least one is on the board. Choosing again the example the
        page opened with puts back what it showed then."""
        page = self.reader()
        self.visit(page)
        page.get_by_role("banner").get_by_role("link", name="How it works").click()
        expect(heading(page)).to_be_visible()
        examples = page.get_by_role("main").get_by_role("group", name="Examples")
        expect(examples.get_by_role("button").first).to_be_visible()
        named = examples.get_by_role("button").all_inner_texts()
        self.assertGreater(len(named), 1, "How it works offers no choice of example")
        first = examples.get_by_role("button", pressed=True).inner_text()
        opened = self.chosen(page, examples, first)

        seen = {}
        for name in named:
            examples.get_by_role("button", name=name, exact=True).click()
            seen[name] = self.chosen(page, examples, name)
        self.assertEqual(len({figures for figures, _ in seen.values()}), len(named), "two examples show one set")
        self.assertEqual({stops for _, stops in seen.values()}, {0, 1}, "no example stops, or none is on the board")

        examples.get_by_role("button", name=first, exact=True).click()
        self.assertEqual(self.chosen(page, examples, first), opened)


if __name__ == "__main__":
    unittest.main()
