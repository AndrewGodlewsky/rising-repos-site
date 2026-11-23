"""The filter and an opened row, in a browser: what a reader does to the newest board, and what it then shows.
Sentences 11 to 17 of the owner's tests."""

import re
import unittest

from playwright.sync_api import Locator, Page, expect

from owner_tests.scenario import (
    Scenario,
    board,
    boards_it_was_on,
    column,
    facts,
    heading,
    names,
    new_names,
    number,
    open_rows,
    opener,
    reason,
    rows,
)

NONE_SHOWN = re.compile(r"No repository on this board matches")
"""What the board says in place of its rows when the search and the filters leave none."""

ON_A_BOARD = re.compile(r": (rank \d+|not on the board)$")
"""What each day of an opened row's strip of board days says under the pointer: the rank the repository had on that
day's board, or that it was not on it."""


def new_button(page: Page) -> Locator:
    return page.get_by_role("button", name=re.compile(r"^New\b"))


def band_buttons(page: Page) -> dict[str, tuple[int, float]]:
    """The star bands the board offers, each button's words with the fewest stars of its band and the count its band
    stops below: "1k–3k" as 1,000 and 3,000, and "30k+" as 30,000 and no end. The button for every band is not one."""

    def stars(words: str) -> int:
        return int(words.rstrip("k").replace(",", "")) * (1000 if words.endswith("k") else 1)

    bands = {}
    for words in page.get_by_role("group", name="Star band").get_by_role("button").all_inner_texts():
        limits = re.fullmatch(r"([\d,]+k?)(?:–([\d,]+k?)|\+)", words.strip())
        if limits:
            bands[words.strip()] = (stars(limits[1]), stars(limits[2]) if limits[2] else float("inf"))
    return bands


def a_word_of(words: str) -> str:
    """The longest run of letters and digits in `words`, in small letters: a word to search for."""
    return max(re.findall(r"[^\W_]+", words), key=len).lower()


class TheFilterAndAnOpenedRow(Scenario):
    def board_page(self) -> Page:
        """A reader at the newest board, which lists at least one repository."""
        page = self.reader()
        self.visit(page)
        self.given(rows(page).count(), "the newest board lists no repository")
        return page

    def test_new_shows_only_the_repositories_that_are_new_and_says_how_many(self):
        """Sentence 11. The rows the board marks New are counted. The New button says that many, and so does the
        board's foot, where it says what New means. Pressed, the button leaves those rows and no other, and still
        says how many. On the made-up boards, which names are new is known: those on no board before the newest."""
        page = self.board_page()
        self.given(new_button(page).count(), "the newest board cannot tell which of its repositories are new")
        marked = new_names(page)
        self.given(marked, "no repository on the newest board is new")
        if self.site.boards:
            newest, *earlier = self.site.boards
            before = {row["full_name"].lower() for listed in earlier for row in listed["rows"]}
            self.assertEqual(
                marked, [row["full_name"] for row in newest["rows"] if row["full_name"].lower() not in before]
            )
        expect(new_button(page)).to_have_text(re.compile(rf"^New\s*{len(marked)}$"))
        expect(page.get_by_role("main").get_by_text(re.compile(r"^\d+ new\b"))).to_have_text(
            re.compile(rf"^{len(marked)} new\b")
        )
        new_button(page).click()
        expect(rows(page)).to_have_count(len(marked))
        self.assertEqual(names(page), marked)
        self.assertEqual(new_names(page), marked)
        expect(new_button(page)).to_have_text(re.compile(rf"^New\s*{len(marked)}$"))

    def test_a_star_bands_button_shows_only_that_bands_repositories(self):
        """Sentence 12. Each band's button says which star counts it takes. Pressed, it leaves the rows whose total
        stars fall in them, and no other. Every row is in one of the bands the board offers."""
        page = self.board_page()
        bands = band_buttons(page)
        self.given(bands, "the newest board offers no star band")
        stars = dict(zip(names(page), [number(total) for total in column(page, "Total stars")], strict=True))
        shown = 0
        for words, (least, below) in bands.items():
            with self.subTest(words):
                within = [name for name, count in stars.items() if least <= count < below]
                page.get_by_role("group", name="Star band").get_by_role("button", name=words, exact=True).click()
                expect(rows(page)).to_have_count(len(within))
                self.assertEqual(names(page), within)
                shown += len(within)
        self.assertEqual(shown, len(stars))

    def test_choosing_a_language_shows_only_that_languages_repositories(self):
        """Sentence 13. A row's language is among the facts it shows once opened. For each language the filter
        offers, choosing it leaves at least one row, and every row left gives that language."""
        page = self.board_page()
        languages = page.get_by_role("combobox", name="Language")
        offered = languages.get_by_role("option").all_inner_texts()[1:]
        self.given(offered, "the newest board offers no language")
        everything = len(names(page))
        seen = 0
        for language in offered:
            with self.subTest(language):
                languages.select_option(label=language)
                left = rows(page).count()
                self.assertGreater(left, 0)
                open_rows(rows(page))
                # The facts of every row shown, in one reading: a row the filter hides gives none.
                terms = board(page).get_by_role("term").all_inner_texts()
                given = board(page).get_by_role("definition").all_inner_texts()
                read = [value for term, value in zip(terms, given, strict=True) if term == "Language"]
                self.assertEqual(read, [language] * left)
                seen += left
        self.assertLessEqual(seen, everything)

    def test_each_order_puts_the_rows_in_that_order(self):
        """Sentence 14. The five orders, each checked against what a reader can read of every row: its rank, the
        stars it gained on the day, its total stars, and, from the strip of board days in its opened row, how many of
        the last 14 boards it was on. A row with no count for the day has no place among the gains, so it is passed
        over there. Every order keeps every row."""
        page = self.board_page()
        order = page.get_by_role("combobox", name="Order")
        by_rank = names(page)
        rank = dict(zip(by_rank, [number(place) for place in column(page, "Rank")], strict=True))
        gain = dict(zip(by_rank, [number(gained) for gained in column(page, "Stars gained")], strict=True))
        stars = dict(zip(by_rank, [number(total) for total in column(page, "Total stars")], strict=True))
        # How often: every row is opened, and its strip read, the last 14 of its days.
        open_rows(rows(page))
        days = board(page).get_by_title(ON_A_BOARD).evaluate_all("days => days.map(day => day.title)")
        each = len(days) // len(by_rank)
        self.assertEqual(len(days), each * len(by_rank))
        often = {
            name: sum("rank" in day for day in days[at * each : (at + 1) * each][-14:])
            for at, name in enumerate(by_rank)
        }
        orders = {
            "By rank": rank,
            "Most stars gained": {name: -gained for name, gained in gain.items() if gained is not None},
            "Most often in 14 boards": {name: -count for name, count in often.items()},
            "Fewest stars first": stars,
            "Most stars first": {name: -count for name, count in stars.items()},
        }
        self.assertLessEqual(set(orders), set(order.get_by_role("option").all_inner_texts()))
        for words, key in orders.items():
            with self.subTest(words):
                order.select_option(label=words)
                shown = names(page)
                self.assertCountEqual(shown, by_rank)
                read = [key[name] for name in shown if name in key]
                self.assertEqual(read, sorted(read))

    def test_a_search_shows_only_the_rows_whose_name_or_description_holds_it_and_says_so_when_none_does(self):
        """Sentence 15. Four searches: a word of a row's name, a word of a row's description, the word the board
        marks a new row with, and a word that no row holds. Each leaves the rows whose name or description holds the
        word, and no other, and the last leaves none and says so."""
        page = self.board_page()
        box = page.get_by_role("searchbox")
        listed = names(page)
        # A row with no description says so in the page's own words, which are not the owner's, so it holds none.
        described = ["" if words == "No description" else words for words in column(page, "Description")]
        searches = {
            "a word of a name": a_word_of(listed[-1].partition("/")[2]),
            "a word of a description": a_word_of([words for words in described if words][-1]),
            "a word that no row holds": "qzxjv-held-by-no-row",
        }
        if new_names(page):
            searches["the word the board marks a new row with"] = "new"
        for what, word in searches.items():
            with self.subTest(what, word=word):
                holding = [
                    name
                    for name, words in zip(listed, described, strict=True)
                    if word in name.lower() or word in words.lower()
                ]
                box.fill(word)
                expect(rows(page)).to_have_count(len(holding))
                self.assertEqual(names(page), holding)
                if holding:
                    expect(page.get_by_text(NONE_SHOWN)).to_be_hidden()
                else:
                    expect(page.get_by_text(NONE_SHOWN)).to_be_visible()

    def test_a_filtered_boards_address_opened_again_shows_the_same_rows(self):
        """Sentence 16. Four filtered boards: the new rows alone; one star band; a language, the one that leaves
        the most rows, in another order; and a search. Each one's address, given to another reader, shows that reader
        the same rows in the same order."""
        filtered = {}
        page = self.board_page()
        if new_button(page).count():
            new_button(page).click()
            filtered["the new rows"] = (page.url, names(page))
        page = self.board_page()
        for words in band_buttons(page):
            page.get_by_role("group", name="Star band").get_by_role("button", name=words, exact=True).click()
            filtered["a star band"] = (page.url, names(page))
            if names(page):
                break
        page = self.board_page()
        languages = page.get_by_role("combobox", name="Language")
        left = {}
        for language in languages.get_by_role("option").all_inner_texts()[1:]:
            languages.select_option(label=language)
            left[language] = len(names(page))
        if left:
            languages.select_option(label=max(left, key=left.get))
            page.get_by_role("combobox", name="Order").select_option(label="Most stars first")
            filtered["a language and an order"] = (page.url, names(page))
        page = self.board_page()
        page.get_by_role("searchbox").fill(a_word_of(names(page)[-1].partition("/")[2]))
        filtered["a search"] = (page.url, names(page))
        filtered = {what: shown for what, shown in filtered.items() if shown[1]}
        self.given(filtered, "the newest board offers nothing to filter by")
        for what, (address, shown) in filtered.items():
            with self.subTest(what):
                self.assertNotEqual(address, f"{self.site.address}/")
                again = self.reader()
                again.goto(address)
                expect(rows(again)).to_have_count(len(shown))
                self.assertEqual(names(again), shown)

    def test_an_opened_row_shows_its_sum_its_facts_and_the_boards_it_was_on_once_the_history_arrives(self):
        """Sentence 17. Before the first row is opened it shows none of the three. Opened, it shows the sum its
        score came from, its facts, each a term with something given for it, and the table of the boards it was on.
        The first of those boards is the one the page shows, and gives the row the rank and the total stars that the
        row's own line gives."""
        page = self.board_page()
        row = rows(page).first
        place, stars = column(page, "Rank")[0], column(page, "Total stars")[0]
        the_sum = row.get_by_text(re.compile(r"stars ÷ \d+ days? ÷"))
        expect(the_sum).to_be_hidden()
        expect(row.get_by_role("term")).to_have_count(0)
        expect(boards_it_was_on(row)).to_be_hidden()
        opener(row).click()
        expect(reason(row)).to_be_visible()
        expect(the_sum).to_be_visible()
        given = facts(row)
        self.assertGreaterEqual(len(given), 3)
        for term, value in given.items():
            with self.subTest(term):
                self.assertTrue(term.strip() and value.strip())
        expect(boards_it_was_on(row)).to_be_visible()
        this_board = boards_it_was_on(row).get_by_role("row").nth(1)
        today = re.search(r"\d{1,2} [A-Z][a-z]+ \d{4}", heading(page).inner_text()).group()
        expect(this_board.get_by_role("rowheader").get_by_role("link")).to_have_text(today)
        self.assertEqual(this_board.get_by_role("cell").all_inner_texts()[:2], [place, stars])


if __name__ == "__main__":
    unittest.main()
