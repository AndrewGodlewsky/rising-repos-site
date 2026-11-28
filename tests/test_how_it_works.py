"""How it works as one flow diagram of the checks a repository goes through on a board day (#214).

The page explained the ranking in six sections of prose, which gave the checks out of the order RisingRepos makes
them. The owner asked for the flow diagram of the issue in their place: every check of formula 2 in that order, each
with its way off the board, the star bands the newest board's file states, a key, and four made-up repositories whose
paths the reader can light. The title block, which names the formula, and "The type", which links to the fonts'
licence, stay as they were.

`TheDiagram` reads the built markup. The rest open the page in the Chrome the machine already has, through
Playwright, as `tests/test_day_bar.py` does, since where a part sits and what the script lights only a browser can
say. They share one build, served once and opened in one Chrome, as `tests/test_search_in_the_day_bar.py` does, so
that the pull request's job stays inside its time (#213).
"""

import shutil
import unittest

from helpers import BuildTest, Page, read_json, write_json

from sitebuild import HOW_IT_WORKS, bands_of
from sitework.layout import chrome, served

PHONE, NARROW, DESKTOP = (390, 844), (360, 740), (1440, 900)
"""The screens the issue names: two phones and a desktop."""

PROSE = (
    "Two days against the twelve before",
    "A floor of 1 star a day",
    "Who makes the board",
    "Before a repository can be scored",
    "Every gain counts",
    "What a row shows",
)
"""The six sections of prose the diagram takes the place of."""

ORDER = [
    ("begin", "One repository, one board day"),
    ("stage", "1 · Collecting"),
    ("check", "Is it followed?"),
    ("answer", "no"),
    ("off", "Never counted"),
    ("answer", "yes"),
    ("stage", "2 · Can it be scored?"),
    ("check", "Was it counted on the board day?"),
    ("answer", "no"),
    ("off", "No score today"),
    ("answer", "yes"),
    ("check", "And two days before it?"),
    ("answer", "no"),
    ("off", "No score today"),
    ("answer", "yes"),
    ("check", "Was it first counted 14 or more days before?"),
    ("answer", "no"),
    ("off", "Too new: no score yet"),
    ("answer", "yes"),
    ("step", "Set large losses aside"),
    ("check", "Are enough days left?"),
    ("answer", "no"),
    ("off", "No score today"),
    ("answer", "yes"),
    ("stage", "3 · Is it rising?"),
    ("step", "Work out its score"),
    ("check", "Is the score 3 or more?"),
    ("answer", "no"),
    ("off", "Not rising"),
    ("answer", "yes"),
    ("check", "Is it far enough above its own trend?"),
    ("answer", "no"),
    ("off", "Not rising"),
    ("answer", "yes"),
    ("stage", "4 · The board"),
    ("check", "Is its star band held today?"),
    ("answer", "yes"),
    ("off", "Left off"),
    ("answer", "no"),
    ("finish", "On the board"),
]
"""The diagram as the issue lists it, top to bottom: each stage, each check and step, each way off the board, and the
word on each branch. A check's way off is NO and its way on YES, but for the held band, whose way off is YES."""

PATHS = {
    "Breaks out": ["followed", "today", "twoback", "history", "losses", "enough", "score", "three", "above", "held"],
    "Fast but steady": ["followed", "today", "twoback", "history", "losses", "enough", "score", "three"],
    "Quiet": ["followed", "today", "twoback", "history", "losses", "enough", "score", "three", "above"],
    "Too new": ["followed", "today", "twoback", "history"],
}
"""The boxes each example passes through, as the issue's source lights them. Breaks out goes on to "On the board"; each
other example stops at its last box, at that check's way off."""

SEEN = """flow => {
  const box = element => element.getBoundingClientRect();
  return {
    sideways: document.documentElement.scrollWidth - window.innerWidth,
    examples: box(document.querySelector('.examples')),
    flow: box(flow),
    checks: [...flow.querySelectorAll('.step.check')].map(step => ({
      box: box(step.querySelector('.box')),
      way: box(step.querySelector('.way .off')),
    })),
  };
}"""
"""How far the page reaches past the screen's right edge; where the examples' figures and the diagram sit; and for
each check, where its box and its way off sit."""

LIT = """flow => ({
  lit: [...flow.querySelectorAll('[data-step].lit')].map(element => element.dataset.step),
  stops: [...flow.querySelectorAll('[data-step].stop')].map(element => element.dataset.step),
  marked: [...flow.querySelectorAll('.stops')].filter(mark => mark.checkVisibility()).map(mark =>
    mark.closest('[data-step]').dataset.step),
})"""
"""Which boxes are lit, which is marked as where the chosen example stops, and on which box's way off the words
"Stops here" are shown."""


def setUpModule():
    """One build of the example, served once and opened in one Chrome by every test that opens a page."""
    global SHARED, SITE, BROWSER
    SHARED = BuildTest()
    SHARED.setUp()
    unittest.addModuleCleanup(SHARED.doCleanups)
    SHARED.build_pages()
    SITE = unittest.enterModuleContext(served(SHARED.out))
    BROWSER = unittest.enterModuleContext(chrome())


def open_page(width_height=DESKTOP, scripts=True):
    """How it works on a screen of `width_height`, with scripts on or off, once its type is in. The caller closes it."""
    width, height = width_height
    context = BROWSER.new_context(viewport={"width": width, "height": height}, java_script_enabled=scripts)
    page = context.new_page()
    page.goto(f"{SITE}/{HOW_IT_WORKS.removesuffix('index.html')}", wait_until="load")
    if scripts:
        page.evaluate("document.fonts.ready.then(() => true)")
    return context, page


class TheDiagram(BuildTest):
    def page(self):
        return self.build_pages()[HOW_IT_WORKS]

    def flow(self, page):
        (flow,) = [element for element in page.all("div") if "flow" in element.classes()]
        return flow

    def test_below_the_title_block_the_page_holds_the_diagram_and_the_type_and_none_of_the_prose_or_its_drawing(self):
        main = self.page().one("main")
        parts = [child for child in main.children if not isinstance(child, str)]
        self.assertEqual(["head" in part.classes() for part in parts[:3]], [True, False, False])
        self.assertEqual([part.tag for part in parts[3:]], ["footer"], "only the page's foot follows the type")
        diagram, article = parts[1], parts[2]
        self.assertEqual(len([element for element in diagram.all("div") if "flow" in element.classes()]), 1)
        self.assertEqual(article.tag, "article")
        self.assertEqual([heading.text() for heading in article.all("h2")], ["The type"])
        headings = [heading.text() for heading in main.all() if heading.tag in ("h2", "h3")]
        for title in PROSE:
            with self.subTest(title):
                self.assertNotIn(title, headings)
        self.assertEqual([element for element in main.all() if "days14" in element.classes()], [])

    def test_it_holds_every_check_step_and_way_off_in_the_order_risingrepos_makes_them_each_branch_labelled_yes_or_no(
        self,
    ):
        seen = []
        for element in self.flow(self.page()).all():
            kinds = element.classes()
            if "begin" in kinds:
                seen.append(("begin", element.text()))
            elif "stage-name" in kinds:
                seen.append(("stage", element.text()))
            elif "ask" in kinds:
                step = element.parent.parent
                seen.append(("step" if "work" in step.classes() else "check", element.text()))
            elif "answer" in kinds:
                seen.append(("answer", element.text().lower()))
            elif "off-name" in kinds:
                seen.append(("off", element.text()))
            elif "finish-name" in kinds:
                seen.append(("finish", element.text()))
        self.assertEqual(seen, ORDER)

    def test_each_box_states_formula_2s_rule_in_the_issues_figures(self):
        text = self.flow(self.page()).text()
        for words in (
            "every repository it has seen at 200 stars or more, the star floor",
            "If that day's snapshot was partial or missing, the board counts it among the unranked.",
            "15 days of counts in all. A day it was missed in between does not reset this.",
            "lost more than 150 stars, or 3% of its stars if that is more, is taken as bad data and left out of both"
            " paces. A gain of any size always counts.",
            "At least 1 of the 2 recent days, and 7 of the 12 before them.",
            "recent pace stars in the 2 recent days ÷ 2",
            "usual pace stars in the 12 days before ÷ 12",
            "score recent pace ÷ usual pace, taken as at least 1",
            "Is the score 3 or more?",
            "(recent pace − usual pace) × 2",
            "under 1,000 stars 10 1,000 to 9,999 20 10,000 and up 50",
            "A band is held only when the board day's own snapshot was partial and missed counts in that band.",
            "Ranked by score, highest first, with ties going by GitHub id. A board has no set length",
        ):
            with self.subTest(words):
                self.assertIn(words, text)

    def test_it_words_the_stars_above_the_usual_pace_as_above_its_own_trend_and_never_as_excess(self):
        text = self.page().one("main").text()
        self.assertIn("Is it far enough above its own trend?", text)
        self.assertIn("Above its own trend (260 − 30) × 2 = 460, needs 20", text)
        self.assertNotIn("excess", text.lower())

    def test_the_star_bands_it_lists_are_the_newest_boards_own_worded_as_its_filter_words_them(self):
        def listed(page):
            (bands,) = [element for element in self.flow(page).all() if "band-list" in element.classes()]
            return [band.text() for band in bands.all("li")]

        self.assertEqual(listed(self.page()), ["200–1k", "1k–3k", "3k–10k", "10k–30k", "30k+"])
        board = read_json(self.board_file())
        bands = [{"least_stars": 500, "most_stars": 4999}, {"least_stars": 5000, "most_stars": None}]
        write_json(self.board_file(), {**board, "star_bands": bands})
        shutil.rmtree(self.out)  # built above
        built = self.build_data()
        self.assertEqual(built.returncode, 0, built.stderr)
        page = Page((self.out / HOW_IT_WORKS).read_text(encoding="utf-8"))
        self.assertEqual(listed(page), ["500–5k", "5k+"])

    def test_a_key_along_its_foot_names_a_check_a_step_a_way_off_and_the_chosen_path(self):
        flow = self.flow(self.page())
        (key,) = [element for element in flow.all() if "key" in element.classes()]
        self.assertIs(key, [element for element in flow.children if not isinstance(element, str)][-1])
        self.assertEqual(
            [item.text() for item in key.all("li")],
            ["A check", "A step that works something out", "Off the board that day", "The chosen example's path"],
        )


class TheDiagramOnScreen(unittest.TestCase):
    def measure(self, width_height):
        context, page = open_page(width_height)
        try:
            return page.locator(".flow").evaluate(SEEN)
        finally:
            context.close()

    def test_on_a_phone_each_way_off_is_under_its_check_the_figures_above_and_nothing_reaches_past_the_screen(self):
        for screen in (PHONE, NARROW):
            with self.subTest(screen=screen):
                seen = self.measure(screen)
                self.assertLessEqual(seen["sideways"], 0, "the page scrolls sideways")
                self.assertLessEqual(seen["examples"]["bottom"], seen["flow"]["top"] + 1, "the figures are not above")
                self.assertEqual(len(seen["checks"]), 8)
                for check in seen["checks"]:
                    self.assertGreaterEqual(check["way"]["top"], check["box"]["bottom"] - 1, "a way off is not under")
                    self.assertLessEqual(check["way"]["right"], screen[0], "a way off reaches past the screen")

    def test_on_a_desktop_each_way_off_is_to_the_right_of_its_check_and_the_figures_beside_it(self):
        seen = self.measure(DESKTOP)
        self.assertLessEqual(seen["sideways"], 0, "the page scrolls sideways")
        self.assertGreaterEqual(seen["examples"]["left"], seen["flow"]["right"] - 1, "the figures are not beside it")
        self.assertLess(seen["examples"]["top"], seen["flow"]["bottom"], "the figures are not beside it")
        self.assertEqual(len(seen["checks"]), 8)
        for check in seen["checks"]:
            self.assertGreaterEqual(check["way"]["left"], check["box"]["right"] - 1, "a way off is not to the right")
            self.assertLess(check["way"]["top"], check["box"]["bottom"], "a way off is not beside its check")
            self.assertGreater(check["way"]["bottom"], check["box"]["top"], "a way off is not beside its check")

    def test_with_scripts_off_the_whole_diagram_and_breaks_out_show_and_no_example_button_does(self):
        context, page = open_page(DESKTOP, scripts=False)
        try:
            flow = page.locator(".flow")
            for kind in ("stage-name", "ask", "off-name", "answer"):
                for element in flow.locator(f".{kind}").all():
                    with self.subTest(kind, words=element.inner_text()):
                        self.assertTrue(element.is_visible())
            self.assertEqual(
                sorted(flow.locator("[data-step].lit").evaluate_all("all => all.map(e => e.dataset.step)")),
                sorted(["begin", *PATHS["Breaks out"], "finish"]),
            )
            shown = page.locator(".trace").filter(visible=True)
            self.assertEqual(shown.count(), 1)
            self.assertIn("4,200 stars", shown.inner_text())
            self.assertEqual(page.get_by_role("button").filter(visible=True).count(), 0)
        finally:
            context.close()


class TheExamples(unittest.TestCase):
    def setUp(self):
        self.context, self.page = open_page(DESKTOP)
        self.addCleanup(self.context.close)

    def choose(self, name):
        self.page.get_by_role("button", name=name, exact=True).click()

    def assert_chosen(self, name, figures, stop):
        """Only `name` is pressed, its path is lit, `stop` is marked as where it stops (None for "On the board"),
        and of the four readouts only its own shows, with `figures` in it."""
        buttons = self.page.locator(".examples").get_by_role("button")
        self.assertEqual(
            {button.inner_text(): button.get_attribute("aria-pressed") for button in buttons.all()},
            {each: "true" if each == name else "false" for each in PATHS},
        )
        seen = self.page.locator(".flow").evaluate(LIT)
        expected = ["begin", *PATHS[name], *(["finish"] if stop is None else [])]
        self.assertEqual(sorted(seen["lit"]), sorted(expected))
        self.assertEqual(seen["stops"], [] if stop is None else [stop])
        self.assertEqual(seen["marked"], [] if stop is None else [stop])
        shown = self.page.locator(".trace").filter(visible=True)
        self.assertEqual(shown.count(), 1)
        text = " ".join(shown.inner_text().split())
        for words in figures:
            with self.subTest(name, words=words):
                self.assertIn(words, text)

    def test_when_the_page_opens_breaks_out_is_chosen_its_path_lit_to_on_the_board_and_its_figures_shown(self):
        board = read_json(SHARED.board_file())
        (band,) = [band for band in bands_of(board) if band.below is None or 4200 < band.below][:1]
        self.assert_chosen(
            "Breaks out",
            [
                "4,200 stars",
                "30 a day for 12 days, then 520 in two",
                "360 ÷ 12 = 30",
                "520 ÷ 2 = 260",
                "260 ÷ 30 = 8.67",
                "(260 − 30) × 2 = 460, needs 20",
                f"{band.label}, not held",
                "On the board",
            ],
            None,
        )

    def test_fast_but_steady_lights_its_path_to_the_score_of_3_and_stops_there_not_rising(self):
        self.choose("Fast but steady")
        self.assert_chosen(
            "Fast but steady",
            [
                "52,000 stars",
                "400 a day for 12 days, then 900 in two",
                "4,800 ÷ 12 = 400",
                "900 ÷ 2 = 450",
                "450 ÷ 400 = 1.13, under 3",
                "Not rising",
            ],
            "three",
        )

    def test_quiet_lights_its_path_to_above_its_own_trend_and_stops_there_not_rising(self):
        self.choose("Quiet")
        self.assert_chosen(
            "Quiet",
            [
                "640 stars",
                "3 stars in 12 days, then 8 in two",
                "0.25 a day, so the floor of 1",
                "8 ÷ 2 = 4",
                "4.00",
                "(4 − 0.25) × 2 = 7.5, needs 10",
                "Not rising",
            ],
            "above",
        )

    def test_too_new_lights_its_path_to_first_counted_14_days_before_and_stops_there(self):
        self.choose("Too new")
        self.assert_chosen(
            "Too new",
            [
                "First counted 9 days before the board day",
                "10 days, of the 15 a score needs",
                "1,200 stars",
                "No score yet",
            ],
            "history",
        )

    def test_choosing_breaks_out_again_puts_the_page_back_as_it_opened(self):
        opened = self.page.locator(".flow").evaluate(LIT)
        self.choose("Quiet")
        self.choose("Breaks out")
        self.assertEqual(self.page.locator(".flow").evaluate(LIT), opened)
        self.assertEqual(opened["marked"], [])
        self.assertEqual(self.page.locator(".trace").filter(visible=True).count(), 1)
        self.assertIn("4,200 stars", self.page.locator(".trace").filter(visible=True).inner_text())


if __name__ == "__main__":
    unittest.main()
