"""Every published board, held to what the other tests hold of the example's five rows (STANDARDS.md, C19).

The other tests build from the data contract's example, so that the day's data does not change what they check. A fault
that only real data shows is beyond them: the reviews of the redesign found, by running every row in site-data/,
thousands of rows that wrote a pace in two ways. These tests build the pages once from site-data/, the boards that were
really published, as the build job does, and check every page and every row the build wrote (docs/workflow-plan.md,
section 6).

The data changes each day, so nothing here names a board day, a row, or a figure. Each check is one that any row
passes whatever its data: a figure is written one way wherever it is shown, a row's parts agree with one another, and
nothing unfilled reaches a page. A repository's owner may write anything, a name with "undefined" in it or a
description that ends "-1", so a check of the site's words leaves out what an owner wrote, and what an owner wrote is
compared with the file it came from.

A failure names the page in its subTest and the row in its message. It is a finding about the site, and the check
stays as it is.
"""

import re
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

from helpers import Element, Page, build, read_json
from test_build import LICENCE, history_file, strings, wrong_signs
from test_history import told
from test_old_board import (
    assert_one_script_of_the_sites_own_parts,
    assert_policy_is_otherwise_as_it_was,
    assert_script_allowed,
)
from test_owner_text import GITHUB
from test_page_weight import (
    SIZE_LIMIT,
    assert_no_notes_on_the_stylesheet_or_the_script,
    assert_no_script_but_the_sites_own,
    on_this_site,
    page_weight,
    requests,
)

from sitebuild import (
    BASELINE,
    BOARD,
    DATA,
    DAYS,
    HOW_IT_WORKS,
    MINUS,
    NOT_FOUND,
    WINDOW,
    address,
    board_day_page,
    day_address,
    repositories,
)
from sitebuild.contract import boards as published_boards

FIGURE = r"(?:0|[1-9][0-9]{0,2}(?:,[0-9]{3})*)(?:\.[0-9]*[1-9])?"
"""A figure as the site writes one, without its sign: its thousands parted by commas, and no 0 at the end of its
decimal places. "None", "nan", "1e+16", and "12.50" are not figures."""

GAIN = re.compile(rf"[+{MINUS}]{FIGURE}|0")
"""A gain as the site writes one: a figure with its plus or its true minus, or 0."""

NO_COUNT = "\N{EN DASH}"
"""What a board's growth column shows where its file has no count for the day before."""

NO_FIGURE = "\N{EM DASH}"
"""What a table shows where a row has no multiple, and where an earlier board gave no figure."""

PACES = re.compile(rf"Usual ({MINUS}?{FIGURE}) a day, then ({MINUS}?{FIGURE}) a day")
"""What a row's own-pace cell says for a screen reader: its usual pace, then its recent pace, in stars a day."""

MULTIPLE = re.compile(rf"{MINUS}?{FIGURE}×")
"""A row's recent pace as a multiple of its usual pace, as the site writes one: "26×"."""

UNFILLED = re.compile(r"\{\{|\}\}|\{%|%\}|\{#|#\}|\b(?:None|nan|NaN|inf|Infinity|undefined|null|True|False)\b")
"""What a page shows in place of a value that was never filled in: a template's own marks, or the word that Python,
JSON, or the page's script writes for no value, for a number that is none, or for a yes or a no."""

OWNERS_FACTS = ("Language", "Licence", "Listed before as")
"""The facts of an opened row whose value a repository's owner wrote."""


def number(written: str) -> float:
    """A figure the site wrote, read back as a number, as the board's script reads one to order its rows: without its
    plus and its commas, and with its true minus as a hyphen."""
    return float(written.replace("+", "").replace(",", "").replace(MINUS, "-"))


def colour(written: str) -> str:
    """The class that colours a gain written as `written`: "loss" for a figure below 0, which the stylesheet sets in
    the red, "nil" for 0 and for no figure, which it sets in the second ink, and none for a gain."""
    if written.startswith(MINUS):
        return "loss"
    return "nil" if written in ("0", NO_COUNT, NO_FIGURE) else ""


def cells(line: Element) -> dict[str, Element]:
    """A row's cells, in order, each by the first of its classes, which names its column: rk its rank, re its
    repository, de its description, wy why it is on the board, gr its growth, pc its own pace, and st its stars."""
    return {cell.classes()[0]: cell for cell in line.children if isinstance(cell, Element)}


class Row(NamedTuple):
    """A row of a published board, in each place that gives it: `filed`, as its board day's file has it; `line`, its
    <tr> on the page, and `cells`, that row's cells; and `opened`, its entry in the board day's history.json, which
    the page shows once a reader opens the row."""

    filed: dict
    line: Element
    cells: dict[str, Element]
    opened: dict

    @property
    def name(self) -> str:
        return self.filed["full_name"]

    def reason(self) -> str:
        """The row's line: why it is on the board, in words."""
        (line,) = [p for p in self.cells["wy"].all("p") if "ln" in p.classes()]
        return line.text()

    def paces(self) -> tuple[str, str]:
        """The row's usual pace and its recent pace, as its own-pace cell writes them."""
        return PACES.fullmatch(self.cells["pc"].text()).groups()


def owner_wrote(element: Element) -> bool:
    """Whether what `element` holds is a repository owner's words and not the site's: a row's description; its name,
    where it is a link and where the row's disclosure repeats it; and the languages the language filter lists."""
    return (
        (element.tag == "td" and element.classes() == ["de"])
        or (element.tag == "a" and element.attrs["href"].startswith(GITHUB))
        or element.tag == "summary"
        or (element.tag == "select" and element.attrs.get("id") == "language")
    )


def repository(element: Element) -> str:
    """The name of the repository that `element` is the row of, in a board or in the Baseline page's table, and
    nothing for any other element."""
    if element.tag != "tr":
        return ""
    addresses = [link.attrs["href"] for link in element.all("a")]
    return next((href.removeprefix(GITHUB) for href in addresses if href.startswith(GITHUB)), "")


def site_wrote(element: Element, row: str = "") -> Iterator[tuple[str, str, str]]:
    """Everything inside `element` that the site wrote and no owner did: each attribute's value, under the attribute's
    name, and each run of text, under "text". Each comes with the name of the repository whose row it is in, which is
    empty outside a row, so that a fault names its row. A row's language, in its data-l, is its owner's."""
    for name, value in element.attrs.items():
        if value and name != "data-l":
            yield row, name, value
    for child in element.children:
        if isinstance(child, str):
            yield row, "text", child
        elif not owner_wrote(child):
            yield from site_wrote(child, row or repository(child))


def own_strings(entry: dict) -> list[str]:
    """Every string of an opened row that the site wrote: all but the values of the facts an owner wrote."""
    return strings({**entry, "facts": [fact for fact in entry["facts"] if fact[0] not in OWNERS_FACTS]})


class EveryPublishedBoard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Build once from site-data/, which the generator reads when it is given no other folder, and read every
        page, every board day's file, and the history of each board day that has rows. `shows` gives each page that
        shows a board, and the board it shows: the root, which shows the newest, and each board day's own page."""
        cls.out = Path(cls.enterClassContext(tempfile.TemporaryDirectory())) / "dist"
        result = build(cls.out)
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        cls.pages = {
            path.relative_to(cls.out).as_posix(): Page(path.read_text(encoding="utf-8"))
            for path in sorted(cls.out.rglob("*.html"))
        }
        cls.boards = published_boards(DATA)
        cls.shows = {BOARD: cls.boards[0], **{board_day_page(board["board_day"]): board for board in cls.boards}}
        cls.histories = {
            board["board_day"]: read_json(cls.out / history_file(board["board_day"]))
            for board in cls.boards
            if board["rows"]
        }

    def with_rows(self) -> list[tuple[str, dict]]:
        """Each page that shows a board with rows, and that board."""
        return [(path, board) for path, board in self.shows.items() if board["rows"]]

    def rows(self, path: str, board: dict) -> list[Row]:
        """The rows of `board` as the page at `path` shows them, each with its row in the file and its entry in the
        board day's history. A page or a history that holds another number of rows than the file fails here."""
        lines, opened = self.pages[path].rows(), self.histories[board["board_day"]]["rows"]
        self.assertEqual((len(lines), len(opened)), (len(board["rows"]), len(board["rows"])))
        return [
            Row(filed, line, cells(line), entry)
            for filed, line, entry in zip(board["rows"], lines, opened, strict=True)
        ]

    def opened(self) -> Iterator[tuple[str, list[tuple[str, dict]]]]:
        """Each board day's history, by its path in the site, with the name and the entry of each of its rows."""
        for board in self.boards:
            if board["rows"]:
                entries = self.histories[board["board_day"]]["rows"]
                names = [row["full_name"] for row in board["rows"]]
                yield history_file(board["board_day"]), list(zip(names, entries, strict=True))

    def parts(self, path: str) -> tuple[str, ...]:
        """The parts of the site's script that the page at `path` carries, in the order site.js includes them: the
        theme on every page; the notice of an old board on every page but the two that hold no board; a board's
        filters where the board has rows; and the Baseline page's readout where the newest board has rows to place."""
        parts = ["theme.js"]
        if path not in (NOT_FOUND, HOW_IT_WORKS):
            parts.append("old-board.js")
        if path in self.shows and self.shows[path]["rows"]:
            parts.append("filters.js")
        if path == BASELINE and self.boards[0]["rows"]:
            parts.append("baseline.js")
        return tuple(parts)

    def test_the_build_writes_the_sites_pages_a_page_for_each_board_day_and_the_history_of_each_that_has_rows(self):
        written = sorted(path.relative_to(self.out).as_posix() for path in self.out.rglob("*") if path.is_file())
        days = [board["board_day"] for board in self.boards]
        expected = [BOARD, DAYS, HOW_IT_WORKS, BASELINE, NOT_FOUND, LICENCE]
        expected += [board_day_page(day) for day in days]
        expected += [history_file(day) for day in self.histories]
        self.assertEqual(written, sorted(expected))

    def test_no_page_is_over_the_size_limit(self):
        """The limit is tests/test_page_weight.py's, which says what set it."""
        for path, page in self.pages.items():
            with self.subTest(path):
                self.assertLessEqual(page_weight(self.out, path, page), SIZE_LIMIT)

    def test_no_page_requests_anything_from_another_site(self):
        for path, page in self.pages.items():
            with self.subTest(path):
                self.assertEqual([asked for asked in requests(page) if not on_this_site(asked)], [])

    def test_each_page_carries_one_script_the_sites_own_parts_that_it_uses_and_nothing_else_that_runs_one(self):
        """The text an owner wrote is escaped, so the page's source opens a script element once too, however a
        browser reads the rest of it."""
        for path, page in self.pages.items():
            with self.subTest(path):
                assert_no_script_but_the_sites_own(self, page)
                assert_one_script_of_the_sites_own_parts(self, page, self.parts(path))
                assert_no_notes_on_the_stylesheet_or_the_script(self, page)
                self.assertEqual(page.html.lower().count("<script"), 1)

    def test_each_pages_policy_lets_its_script_run_by_its_hash_and_only_a_board_with_rows_fetch_from_the_site(self):
        for path, page in self.pages.items():
            with self.subTest(path):
                assert_script_allowed(self, page)
                assert_policy_is_otherwise_as_it_was(self, page, fetches="filters.js" in self.parts(path))

    def test_every_link_within_the_site_leads_to_a_file_the_build_wrote_or_to_a_place_on_its_own_page(self):
        """So does the address a board's table gives its script for the history that an opened row fetches."""
        written = {address(path.relative_to(self.out).as_posix()) for path in self.out.rglob("*") if path.is_file()}
        for path, page in self.pages.items():
            with self.subTest(path):
                places = {"#" + element.attrs["id"] for element in page.all() if "id" in element.attrs}
                asked = [href for href, _ in page.links() if not href.startswith(GITHUB)]
                asked += [table.attrs["data-history"] for table in page.all("table") if "data-history" in table.attrs]
                self.assertEqual([href for href in asked if href not in written | places], [])

    def test_the_only_links_off_the_site_are_each_rows_to_its_own_repository_on_github(self):
        """On a board and on the Baseline page, which lists the newest board's rows. No other page has one, so no
        value an owner wrote is made a link."""
        lists = {**self.shows, BASELINE: self.boards[0]}
        for path, page in self.pages.items():
            with self.subTest(path):
                rows = lists[path]["rows"] if path in lists else []
                self.assertEqual(
                    [(href, text) for href, text in page.links() if not href.startswith(("/", "#"))],
                    [(GITHUB + row["full_name"], row["full_name"]) for row in rows],
                )

    def test_each_rows_link_opens_github_in_a_new_tab_and_is_titled_opens_on_github(self):
        """So that a reader who follows a row's name leaves the board where it was (#30)."""
        for path, board in self.with_rows():
            with self.subTest(path):
                for row in self.rows(path, board):
                    (link,) = [element for element in row.line.all("a") if element.attrs["href"].startswith(GITHUB)]
                    self.assertEqual(
                        (link.attrs.get("target"), link.attrs.get("title")),
                        ("_blank", "Opens on GitHub"),
                        row.filed["full_name"],
                    )

    def test_the_root_shows_the_newest_board_as_that_board_days_own_page_does(self):
        own = self.pages[board_day_page(self.boards[0]["board_day"])]
        self.assertEqual(self.pages[BOARD].one("main").text(), own.one("main").text())

    def test_each_board_lists_its_files_rows_in_order_with_the_rank_name_description_language_and_stars_of_each(self):
        """A description is compared as a reader sees it, its runs of white space as one, and its cell holds text
        alone: an owner's markup makes no element."""
        for path, board in self.with_rows():
            with self.subTest(path):
                shown = [
                    (
                        row.cells["rk"].text(),
                        [(link.attrs["href"], link.text()) for link in row.line.all("a")],
                        row.cells["de"].text(),
                        [element.tag for element in row.cells["de"].all()],
                        row.line.attrs.get("data-l"),
                        row.cells["st"].text(),
                    )
                    for row in self.rows(path, board)
                ]
                filed = [
                    (
                        str(row["rank"]),
                        [(GITHUB + row["full_name"], row["full_name"])],
                        " ".join((row["description"] or "No description").split()),
                        [],
                        row["language"],
                        f"{row['stars']:,}",
                    )
                    for row in board["rows"]
                ]
                self.assertEqual(shown, filed)

    def test_each_row_has_a_cell_under_every_heading_of_its_board_and_no_cell_the_site_fills_is_empty(self):
        """The description's cell is its owner's to fill, and the test above compares it with the file."""
        for path, board in self.with_rows():
            with self.subTest(path):
                headings = [heading.classes()[0] for heading in self.pages[path].one("thead").all("th")]
                faults = []
                for row in self.rows(path, board):
                    empty = [name for name, cell in row.cells.items() if name != "de" and not cell.text()]
                    if list(row.cells) != headings or empty:
                        faults.append((row.name, list(row.cells), empty))
                self.assertEqual(faults, [])

    def test_each_rows_gain_on_its_board_day_is_its_files_count_with_its_sign_and_a_dash_where_the_file_has_none(self):
        for path, board in self.with_rows():
            with self.subTest(path):
                faults = []
                for row in self.rows(path, board):
                    shown, gain = row.cells["gr"].text(), row.filed["gained_1_day"]
                    counted = gain is not None and GAIN.fullmatch(shown) and number(shown) == gain
                    if not (counted or (gain is None and shown == NO_COUNT)):
                        faults.append((row.name, shown, gain))
                self.assertEqual(faults, [])

    def test_each_gain_on_a_board_and_in_an_opened_row_is_coloured_by_the_sign_of_the_figure_it_is_written_as(self):
        """A board's growth cell and each board in an opened row's table take the red for a loss and the second ink for
        0 and for no figure. An opened row's gains over 7 and 30 days are in the ink, so only a loss is marked."""
        for path, board in self.with_rows():
            with self.subTest(path):
                faults = []
                for row in self.rows(path, board):
                    cell = row.cells["gr"]
                    marked = [(cell.text(), " ".join(sorted(set(cell.classes()) - {"gr", "g"})))]
                    marked += [(seen[3], seen[4]) for seen in row.opened["on"]]
                    wrong = [(written, mark) for written, mark in marked if mark != colour(written)]
                    gains = [fact for fact in row.opened["facts"] if fact[0].startswith("Gained in")]
                    wrong += [fact for fact in gains if fact[2:] != (["loss"] if fact[1].startswith(MINUS) else [])]
                    if wrong:
                        faults.append((row.name, wrong))
                self.assertEqual(faults, [])

    def test_each_rows_line_and_its_opened_view_give_the_same_gain_and_the_same_multiple_or_none(self):
        """The line's first half is the label of the opened row's drawing. Its multiple is the one among the row's
        facts and in its table of boards, and where the line gives none, neither does, and the sum behind the line
        writes the score out instead."""
        for path, board in self.with_rows():
            with self.subTest(path):
                faults = []
                for row in self.rows(path, board):
                    line, opened = row.reason(), row.opened
                    places = (line, told(opened)["Multiple"], opened["on"][-1][5])
                    multiples = {found.group() if (found := MULTIPLE.search(place)) else None for place in places}
                    agree = (
                        line.partition(" · ")[0] == opened["said"][0]
                        and len(multiples) == 1
                        and opened["sum"].startswith("Score ") == (multiples == {None})
                    )
                    if not agree:
                        faults.append((row.name, line, opened["said"][0], places[1:], opened["sum"]))
                self.assertEqual(faults, [])

    def test_each_row_writes_its_usual_pace_and_its_recent_pace_one_way_in_its_cell_and_in_its_opened_view(self):
        """The usual pace is in the row's own-pace cell, in the label and the sentence of its opened drawing, where
        the drawing's line is drawn, and in the sum behind its line, which gives a falling pace as a loss, without
        its minus. The recent pace is in the cell and in the opened row's table of boards, which signs it."""
        for path, board in self.with_rows():
            with self.subTest(path):
                faults = []
                for row in self.rows(path, board):
                    if not PACES.fullmatch(row.cells["pc"].text()):
                        faults.append((row.name, row.cells["pc"].text()))
                        continue
                    (usual, recent), opened = row.paces(), row.opened
                    agree = (
                        opened["said"][2] == f"Usual pace, {usual} a day"
                        and f"its usual pace was {usual} stars a day" in opened["said"][3]
                        and opened["pace"][0] == number(usual)
                        and f" {usual.removeprefix(MINUS)} a day" in opened["sum"]
                        and opened["on"][-1][3].removeprefix("+") == recent
                    )
                    if not agree:
                        faults.append((row.name, usual, recent, opened["said"], opened["sum"], opened["on"][-1]))
                self.assertEqual(faults, [])

    def test_the_baseline_page_lists_the_newest_boards_rows_with_the_rank_usual_pace_and_multiple_of_each(self):
        """As the row on the board gives them. Its table's columns are the rank, the repository, the baseline a day,
        the recent pace a day, which it writes to two places where a board writes it whole from 10, and the growth."""
        newest = self.boards[0]
        listed = []
        for line in self.pages[BASELINE].rows():
            rank, usual, _, multiple = (cell.text() for cell in line.all("td"))
            listed.append((rank, [link.attrs["href"] for link in line.all("a")], usual, multiple))
        ranked = [
            (
                row.cells["rk"].text(),
                [GITHUB + row.name],
                row.paces()[0],
                found.group() if (found := MULTIPLE.search(row.reason())) else NO_FIGURE,
            )
            for row in (self.rows(BOARD, newest) if newest["rows"] else [])
        ]
        self.assertEqual(listed, ranked)

    def test_each_opened_row_lists_its_own_board_last_with_the_rank_and_the_stars_its_row_shows(self):
        """Its line of stars over the month ends at that count too, where the row has one."""
        for path, board in self.with_rows():
            with self.subTest(path):
                history = self.histories[board["board_day"]]
                self.assertEqual(history["days"][-1], board["board_day"])
                faults = []
                for row in self.rows(path, board):
                    rank, stars = row.cells["rk"].text(), row.cells["st"].text()
                    place, listed_rank, listed_stars = row.opened["on"][-1][:3]
                    month = row.opened.get("month")
                    agree = (
                        (place, str(listed_rank), listed_stars) == (len(history["days"]) - 1, rank, stars)
                        and row.opened["stars"][-1] == number(stars)
                        and (month is None or month[1].endswith(f": {stars}"))
                    )
                    if not agree:
                        faults.append((row.name, rank, stars, row.opened["on"][-1], row.opened["stars"][-1], month))
                self.assertEqual(faults, [])

    def test_each_row_is_counted_on_the_boards_its_opened_row_lists_in_its_facts_and_for_the_most_often_order(self):
        """An opened row's facts count the boards its table lists, and give the best rank among them. The board's
        "Most often" order, in the row's data-o, counts those among the last `WINDOW` board days, worked out apart."""
        for path, board in self.with_rows():
            with self.subTest(path):
                days = len(self.histories[board["board_day"]]["days"])
                faults = []
                for row in self.rows(path, board):
                    on, facts = row.opened["on"], told(row.opened)
                    said = (
                        facts.get(f"On the last {days} boards"),
                        facts.get("Best rank in them"),
                        row.line.attrs.get("data-o"),
                    )
                    counted = (
                        f"{len(on)} of {days}",
                        str(min(seen[1] for seen in on)),
                        str(sum(seen[0] >= days - WINDOW for seen in on)),
                    )
                    if said != counted:
                        faults.append((row.name, said, counted))
                self.assertEqual(faults, [])

    def test_a_board_that_an_opened_row_lists_is_written_there_as_that_boards_own_history_writes_it(self):
        """A row's rank, stars, stars a day, and multiple on an earlier board are the ones that board's own opened row
        gives, whichever board day's page shows them. A repository is followed by its GitHub id, as the build does."""
        own = {
            board["board_day"]: {
                row["github_id"]: entry["on"][-1][1:]
                for row, entry in zip(board["rows"], self.histories[board["board_day"]]["rows"], strict=True)
            }
            for board in self.boards
            if board["rows"]
        }
        for board in self.boards:
            if not board["rows"]:
                continue
            with self.subTest(history_file(board["board_day"])):
                history = self.histories[board["board_day"]]
                faults = [
                    (row["full_name"], history["days"][seen[0]], seen[1:])
                    for row, entry in zip(board["rows"], history["rows"], strict=True)
                    for seen in entry["on"]
                    if own.get(history["days"][seen[0]], {}).get(row["github_id"]) != seen[1:]
                ]
                self.assertEqual(faults, [])

    def test_each_board_gives_one_count_of_its_rows_and_one_of_its_new_rows_on_its_page_and_in_the_calendar(self):
        """Its rows: the rows it lists, the count on its All button, the count in About this board, and the count in
        its day of History's calendar. Its new rows: the rows it marks New, the count on its New button, the count at
        its foot, and the count in the calendar, which gives one exactly where the board's foot does, but for a board
        with no repository, which has none that could be new and says no count in its cell (#91). A board that cannot
        tell what is new gives no count and marks no row."""
        calendar = {link.attrs["href"]: link for link in self.pages[DAYS].one("main").all("a")}
        for path, board in self.shows.items():
            with self.subTest(path):
                page, count = self.pages[path], len(board["rows"])
                ids = {element.attrs["id"]: element for element in page.all() if "id" in element.attrs}
                day = calendar[day_address(board["board_day"])]
                (published,) = [p for p in page.all("p") if "published" in p.classes()]
                (counted,) = [span for span in day.all("span") if "count" in span.classes()]
                self.assertEqual(len(page.rows()), count)
                self.assertTrue(published.text().startswith(f"{repositories(count)}. "), published.text())
                self.assertEqual(number(counted.text().split()[0]), count)
                if count:  # a board with no row has no filter, and so no button
                    self.assertEqual(number(ids["count-all"].text()), count)
                new = sum(1 for row in page.rows() if any("new" in mark.classes() for mark in row.all("b")))
                foot = [strong.text() for strong in ids["new-means"].all("strong")] if "new-means" in ids else []
                button = [ids["count-new"].text()] if "count-new" in ids else []
                cell = [span.text() for span in day.all("span") if "fresh" in span.classes()]
                if foot:
                    self.assertEqual(
                        (foot, cell, button),
                        ([f"{new} new."], [f"{new} new"] if count else [], [str(new)] if count else []),
                    )
                else:
                    self.assertEqual((new, cell, button), (0, [], []))

    def test_no_page_and_no_opened_row_writes_a_figure_with_a_hyphen_two_signs_or_a_sign_on_a_0(self):
        """In the words the site gives a reader: its text, and the titles and labels its elements carry."""
        for path, page in self.pages.items():
            with self.subTest(path):
                found = [
                    (row, text, wrong)
                    for row, name, text in site_wrote(page.one("body"))
                    if name in ("text", "title", "aria-label") and (wrong := wrong_signs(text))
                ]
                self.assertEqual(found, [])
        for path, rows in self.opened():
            with self.subTest(path):
                found = [
                    (row, text, wrong)
                    for row, entry in rows
                    for text in own_strings(entry)
                    if (wrong := wrong_signs(text))
                ]
                self.assertEqual(found, [])

    def test_no_page_and_no_opened_row_shows_a_templates_marks_or_a_value_that_was_never_filled_in(self):
        """In everything the site wrote: its text and each attribute's value on a page, and each string of an opened
        row. A row with no multiple says "None: " and why among its facts, which is the site's own word and is taken
        off before the search."""
        for path, page in self.pages.items():
            with self.subTest(path):
                found = [wrote for wrote in site_wrote(page.one("body")) if UNFILLED.search(wrote[2])]
                self.assertEqual(found, [])
        for path, rows in self.opened():
            with self.subTest(path):
                found = [
                    (row, text)
                    for row, entry in rows
                    for text in own_strings(entry)
                    if UNFILLED.search(text.removeprefix("None: "))
                ]
                self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
