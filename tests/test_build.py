"""The generator, run the way deploy.yml's build job runs it, on a copy of the data contract's example.

The build writes the newest board at the site's root, a page for each board day and, for each board with rows, the
history its opened rows draw from, the list of board days, the Baseline page, the page on how a board is ranked, the
page for an address that holds no page, and the fonts' licence. A test of something every page holds to reads them
all.
"""

import re
import shutil
import unittest
from datetime import date

from helpers import BuildTest, build, read_json, write_json

from sitebuild import (
    BASELINE,
    BOARD,
    BOARD_DAY,
    DAYS,
    HOW_IT_WORKS,
    NOT_FOUND,
    PAGES,
    STATIC,
    TEMPLATES,
    History,
    board_day_page,
    calendar,
    daily_job,
    figure,
    gain_class,
    gained,
    per_day,
    signed,
    times,
    took,
)

NOINDEX = '<meta name="robots" content="noindex">'

NEWEST, OLDER = "2026-11-09", "2026-11-08"
"""The example's two board days, newest first, as its index lists them."""

HOLD_FIELDS = ("state", "holds", "missed_stars", "unranked")
"""The fields that AndrewGodlewsky/RisingRepos#13 added, which a file published before them lacks."""

LICENCE = "static/fonts/OFL.txt"


def history_file(day: str) -> str:
    """The path of a board day's history, beside its page."""
    return board_day_page(day).replace("index.html", "history.json")


def share_image(day: str) -> str:
    """The path of a board day's share image, beside its page."""
    return board_day_page(day).replace("index.html", "share.png")


def site_bar(page):
    (header,) = [element for element in page.all("header") if "site" in element.classes()]
    return header


def colophon(page):
    (footer,) = [element for element in page.all("footer") if "colophon" in element.classes()]
    return footer


class TheBuild(BuildTest):
    def test_the_build_writes_each_page_that_pages_names_one_for_each_board_day_and_the_history_of_each_with_rows(self):
        """The older board lists no row, so no opened row of it reads a history, and it has none. Each board day has
        its share image, the empty one too (#35)."""
        self.build_pages()
        written = sorted(path.relative_to(self.out).as_posix() for path in self.out.rglob("*") if path.is_file())
        self.assertEqual(
            written,
            sorted(
                [
                    BOARD,
                    DAYS,
                    HOW_IT_WORKS,
                    BASELINE,
                    NOT_FOUND,
                    board_day_page(NEWEST),
                    board_day_page(OLDER),
                    history_file(NEWEST),
                    share_image(NEWEST),
                    share_image(OLDER),
                    LICENCE,
                    "sitemap.xml",
                    "robots.txt",
                    f"days/{NEWEST}/board.md",
                    f"days/{NEWEST}/board.json",
                    f"days/{OLDER}/board.md",
                    f"days/{OLDER}/board.json",
                    "latest.md",
                    "latest.json",
                ]
            ),
        )
        self.assertEqual(set(PAGES), {BOARD, DAYS, HOW_IT_WORKS, BASELINE, NOT_FOUND, BOARD_DAY})

    def test_the_board_shows_the_latest_board_day_which_is_the_first_in_the_index(self):
        page = self.build_pages()[BOARD]
        self.assertIn("Rising Repos", page.one("title").text())
        self.assertIn("9 November 2026", page.one("title").text())
        self.assertEqual(page.one("h1").all("time")[0].attrs["datetime"], NEWEST)
        self.assertEqual(page.one("h1").text(), "The daily board for 9 Nov 2026")

    def test_the_board_lists_every_row_in_the_files_order_with_its_rank_name_description_language_and_stars(self):
        """The language is the row's data-l, which the language filter reads. The row shows it once opened, from
        the board day's history (tests/test_history.py)."""
        rows = read_json(self.board_file())["rows"]
        shown = self.build_pages()[BOARD].rows()
        self.assertEqual(len(shown), len(rows))
        for row, element in zip(rows, shown, strict=True):
            text = element.text()
            self.assertEqual(text.split()[0], str(row["rank"]), text)
            self.assertEqual(
                [(link.attrs["href"], link.text()) for link in element.all("a")],
                [(f"https://github.com/{row['full_name']}", row["full_name"])],
            )
            self.assertIn(row["description"] or "No description", text)
            self.assertEqual(element.attrs.get("data-l"), row["language"])
            self.assertRegex(text, rf"(^|\s){row['stars']:,}(\s|$)")

    def test_the_boards_column_headings_name_each_figure_and_say_the_last_is_total_stars(self):
        """The description and the reason have no heading on the screen, since a row's name heads them, and keep
        one a screen reader reads, so that every cell of a row has its column's heading."""
        page = self.build_pages()[BOARD]
        headings = page.one("thead").all("th")
        self.assertEqual(
            [heading.text() for heading in headings],
            [
                "Rank",
                "Repository",
                "Description",
                "More: why it is on the board",
                "Stars gained on the board day",
                "Against its own pace the last 14 days",
                "Total stars",
            ],
        )
        self.assertEqual(
            [heading.text() for heading in headings if "sr" in heading.classes()],
            ["Description", "More: why it is on the board"],
        )
        for row in page.rows():
            self.assertEqual(
                len([cell for cell in row.all() if cell.tag in ("td", "th") and cell.parent is row]), len(headings)
            )

    def test_a_row_shows_no_language_when_the_file_has_none(self):
        board = read_json(self.board_file())
        languages = {row["language"] for row in board["rows"] if row["language"]}
        (no_language,) = [
            element for element in self.build_pages()[BOARD].rows() if "octocat/Hello-World" in element.text()
        ]
        self.assertNotIn("data-l", no_language.attrs)
        self.assertFalse(languages & set(no_language.text().split()), no_language.text())
        self.assertNotIn("None", no_language.text().split())

    def test_each_page_says_in_its_colophon_that_there_is_a_new_board_each_day(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                line = colophon(page).all("p")[0].text()
                self.assertTrue(line.startswith("Rising Repos"), line)
                self.assertIn("on a new board each day", line)
                self.assertIn("not affiliated with GitHub", colophon(page).text())

    def test_the_sites_bar_links_to_the_root_the_list_baseline_and_how_it_works_and_marks_the_page_it_is_on(self):
        """RisingRepos#111, and AndrewGodlewsky/RisingRepos#49: the page that says how a board is ranked is the
        site's own, not a README. The list of board days is History, in the bar since
        AndrewGodlewsky/RisingRepos#199, so a board's day bar and foot link only to the days beside it."""
        current = {DAYS: "/days/", BASELINE: "/baseline/", HOW_IT_WORKS: "/how-it-works/"}
        for path, page in self.build_pages().items():
            with self.subTest(path):
                bar = site_bar(page)
                self.assertEqual(
                    [(link.attrs["href"], link.text()) for link in bar.all("a")],
                    [
                        ("/", "Rising Repos"),
                        ("/days/", "History"),
                        ("/baseline/", "Baseline"),
                        ("/how-it-works/", "How it works"),
                    ],
                )
                self.assertEqual(
                    [link.attrs["href"] for link in bar.all("a") if link.attrs.get("aria-current") == "page"],
                    [current[path]] if path in current else [],
                )

    def test_the_root_states_its_board_day_and_publish_time_in_the_contracts_two_meta_tags_once_each(self):
        page = self.build_pages()[BOARD]
        self.assertEqual(page.meta("rr:board-date"), [NEWEST])
        self.assertEqual(page.meta("rr:published-at"), ["2026-11-10T00:41:07Z"])
        head = page.html.split("</head>")[0]
        self.assertIn(f'<meta name="rr:board-date" content="{NEWEST}">', head)
        self.assertIn('<meta name="rr:published-at" content="2026-11-10T00:41:07Z">', head)

    def test_no_page_but_the_root_states_a_board_day_so_whatever_reads_the_tags_reads_the_root(self):
        for path, page in self.build_pages().items():
            if path != BOARD:
                with self.subTest(path):
                    self.assertEqual(page.meta("rr:board-date"), [])
                    self.assertEqual(page.meta("rr:published-at"), [])
                    self.assertNotIn("rr:", page.html)

    def test_the_board_shows_when_the_board_day_was_published_in_utc(self):
        page = self.build_pages()[BOARD]
        (published,) = [time for time in page.all("time") if time.attrs["datetime"] == "2026-11-10T00:41:07Z"]
        self.assertEqual(published.text(), "10 November 2026 at 00:41 UTC")

    def notes(self, page, kind: str) -> list:
        """The notes of one kind that change how a board reads: each <p class="`kind`"> above its rows."""
        boxes = [box for box in page.all("div") if "notes" in box.classes()]
        return [note for box in boxes for note in box.all("p") if kind in note.classes()]

    def facts(self, page, kind: str) -> list:
        """The board's plain facts of one kind: each <p class="`kind`"> in About this board, at its foot."""
        (about,) = [section for section in page.all("section") if "about" in section.classes()]
        return [element for element in about.all("p") if kind in element.classes()]

    def test_the_board_says_its_ranking_is_provisional_while_the_file_says_so_and_names_no_score(self):
        """The example's boards are not provisional since RisingRepos#47, so the test marks the file itself. The note
        names no score; since AndrewGodlewsky/RisingRepos#49 each row's opened view gives its own."""
        board = read_json(self.board_file())
        write_json(self.board_file(), {**board, "score_provisional": True})
        (note,) = self.notes(self.build_pages()[BOARD], "provisional")
        self.assertTrue(note.text().startswith("The ranking is provisional."), note.text())
        self.assertNotIn("score", note.text().lower())

    def test_the_board_says_nothing_about_a_provisional_ranking_once_the_file_says_it_is_not(self):
        board = read_json(self.board_file())
        write_json(self.board_file(), {**board, "score_provisional": False})
        self.assertNotIn("provisional", self.build_pages()[BOARD].body_text().lower())

    def test_each_board_gives_the_number_of_the_formula_that_ranked_it_in_a_plain_line_with_how_it_ranks(self):
        """RisingRepos#47. Both of the example's board days were ranked by formula 2."""
        pages = self.build_pages()
        for path in (BOARD, board_day_page(NEWEST), board_day_page(OLDER)):
            with self.subTest(path):
                (line,) = self.facts(pages[path], "formula")
                self.assertEqual(line.text(), "Ranked by formula version 2. How it ranks")
                self.assertEqual([link.attrs["href"] for link in line.all("a")], ["/how-it-works/"])
                self.assertEqual(line.all("strong"), [])

    def test_a_board_whose_file_predates_the_formula_number_builds_and_names_no_formula(self):
        """The files in site-data/ lacked the field until RisingRepos#47's closeout republished every board day."""
        self.drop_fields("formula_version")
        for path, page in self.build_pages().items():
            if path == HOW_IT_WORKS:
                continue  # it describes the formula it names, whatever the files say (AndrewGodlewsky/RisingRepos#49)
            with self.subTest(path):
                self.assertEqual([p for p in page.all("p") if "formula" in p.classes()], [])
                self.assertNotIn("formula version", page.body_text())

    def partial_notes(self, page) -> list:
        """What a board says of partial days, in order: a note above its rows when a recent one may have moved a row,
        and a plain fact at its foot otherwise. Each is a <p class="partial">."""
        return [element for element in page.one("main").all("p") if "partial" in element.classes()]

    def test_a_board_whose_file_predates_holds_sets_a_recent_partial_day_apart_as_one_that_may_have_moved_a_row(self):
        """RisingRepos#45, for a file older than AndrewGodlewsky/RisingRepos#13's fields, which says nothing of what a
        recent partial day did: such a board read 7 November for a recent pace and 27 October further back."""
        self.drop_fields(*HOLD_FIELDS)
        board = read_json(self.board_file())
        days = [{"snapshot_day": "2026-11-07", "recent": True}, {"snapshot_day": "2026-10-27", "recent": False}]
        write_json(self.board_file(), {**board, "partial_days": days})
        page = self.build_pages()[BOARD]
        recent, earlier = self.partial_notes(page)
        self.assertEqual(self.notes(page, "partial"), [recent])
        self.assertEqual(recent.classes(), ["partial", "recent"])
        self.assertEqual(
            recent.text(),
            "A recent snapshot missed some repositories. The ranking's recent pace takes in 7 November 2026, and a "
            "repository missing then may sit higher or lower here than a full snapshot would put it, or be left out.",
        )
        self.assertEqual(
            [strong.text() for strong in recent.all("strong")], ["A recent snapshot missed some repositories."]
        )
        self.assertEqual(self.facts(page, "partial"), [earlier])
        self.assertEqual(earlier.classes(), ["partial"])
        self.assertEqual(
            earlier.text(),
            "The ranking draws on 1 earlier day whose snapshot missed some repositories, on 27 October 2026.",
        )
        self.assertEqual(earlier.all("strong"), [])

    def test_two_recent_partial_days_are_named_in_one_note(self):
        self.drop_fields(*HOLD_FIELDS)
        board = read_json(self.board_file())
        days = [{"snapshot_day": "2026-11-08", "recent": True}, {"snapshot_day": "2026-11-07", "recent": True}]
        write_json(self.board_file(), {**board, "partial_days": days})
        (note,) = self.partial_notes(self.build_pages()[BOARD])
        self.assertEqual(note.classes(), ["partial", "recent"])
        self.assertTrue(
            note.text().startswith(
                "Recent snapshots missed some repositories. The ranking's recent pace takes in 8 November 2026 and "
                "7 November 2026, and"
            ),
            note.text(),
        )

    def test_a_board_whose_ranking_read_partial_days_only_further_back_gives_their_count_and_span_in_a_plain_line(self):
        """AndrewGodlewsky/RisingRepos#13: a single day and several dozen are worded alike, as a board of
        early August 2026 reads 64, rather than a list of every date."""
        board = read_json(self.board_file())
        sixty = [f"2026-{month:02d}-{day:02d}" for month in (7, 6) for day in range(30, 0, -1)]
        for days, said in (
            (["2026-10-27"], "1 earlier day whose snapshot missed some repositories, on 27 October 2026"),
            (
                ["2026-10-27", "2026-06-12"],
                "2 earlier days whose snapshots missed some repositories, from 12 June 2026 to 27 October 2026",
            ),
            (sixty, "60 earlier days whose snapshots missed some repositories, from 1 June 2026 to 30 July 2026"),
        ):
            with self.subTest(len(days)):
                partial = [{"snapshot_day": day, "recent": False} for day in days]
                write_json(self.board_file(), {**board, "partial_days": partial})
                shutil.rmtree(self.out, ignore_errors=True)
                (note,) = self.facts(self.build_pages()[BOARD], "partial")
                self.assertEqual(note.classes(), ["partial"])
                self.assertEqual(note.all("strong"), [])
                self.assertEqual(note.text(), f"The ranking draws on {said}.")

    def test_a_board_day_whose_own_snapshot_is_partial_says_that_a_repository_it_missed_is_not_on_the_board(self):
        """As 2026-07-31's board was before AndrewGodlewsky/RisingRepos#13: its own snapshot partial, no row on it,
        and a file that says nothing of holds. A file that does is in tests/test_held.py."""
        self.drop_fields(*HOLD_FIELDS)
        board = read_json(self.board_file(OLDER))
        for days, after in (
            ([{"snapshot_day": OLDER, "recent": True}], ""),
            (
                [{"snapshot_day": OLDER, "recent": True}, {"snapshot_day": "2026-11-07", "recent": True}],
                " The recent pace the ranking measures also runs over 7 November 2026, whose snapshot missed some too.",
            ),
        ):
            with self.subTest(len(days)):
                write_json(self.board_file(OLDER), {**board, "partial_days": days})
                shutil.rmtree(self.out, ignore_errors=True)
                page = self.build_pages()[board_day_page(OLDER)]
                (note,) = self.notes(page, "partial")
                self.assertEqual(note.classes(), ["partial", "recent"])
                self.assertEqual(
                    note.text(),
                    "This day's snapshot missed some repositories. A repository it missed could not be ranked, so it "
                    "is not on this board." + after,
                )
                self.assertIn("No repository made the board on this day.", page.body_text())

    def test_a_board_whose_ranking_read_no_partial_day_has_no_note_on_them(self):
        """The example's older board lists none."""
        self.assertEqual(read_json(self.board_file(OLDER))["partial_days"], [])
        page = self.build_pages()[board_day_page(OLDER)]
        self.assertEqual(self.partial_notes(page), [])
        self.assertNotIn("snapshot", page.body_text())

    def test_a_board_whose_file_predates_partial_days_builds_and_says_nothing_about_them(self):
        """As site-data/ held its files until RisingRepos#45's closeout published them again: the schema and every
        board day's file without the field. Such a file neither names a partial day nor says there was none. It is
        older than the holds too (AndrewGodlewsky/RisingRepos#13)."""
        self.drop_fields("partial_days", *HOLD_FIELDS)
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertEqual([p for p in page.all("p") if "partial" in p.classes()], [])
                self.assertNotIn("snapshot", page.body_text())

    def test_a_board_says_when_the_days_update_began_and_how_long_it_took_to_publish_it(self):
        """RisingRepos#51. The example's newest board was published at 00:41:07, and its update began at 00:28:44."""
        (update,) = self.facts(self.build_pages()[BOARD], "update")
        self.assertEqual(
            update.text(), "The day's update began at 00:28 UTC and took 12 minutes to publish this board."
        )
        self.assertEqual([time.attrs["datetime"] for time in update.all("time")], ["2026-11-10T00:28:44Z"])

    def test_an_update_that_began_on_another_day_than_the_publish_names_its_date(self):
        board = read_json(self.board_file())
        write_json(self.board_file(), {**board, "daily_job_started_at": "2026-11-09T22:35:00Z"})
        (update,) = self.facts(self.build_pages()[BOARD], "update")
        self.assertEqual(
            update.text(),
            "The day's update began on 9 November 2026 at 22:35 UTC and took 2 hours and 6 minutes to publish this "
            "board.",
        )

    def test_how_long_an_update_took_is_said_in_words(self):
        for seconds, words in (
            (0, "less than a minute"),
            (59, "less than a minute"),
            (60, "1 minute"),
            (119, "1 minute"),
            (59 * 60, "59 minutes"),
            (3600, "1 hour"),
            (3660, "1 hour and 1 minute"),
            (2 * 3600 + 5 * 60 + 59, "2 hours and 5 minutes"),
            (49 * 3600, "49 hours"),
        ):
            with self.subTest(seconds):
                self.assertEqual(took(seconds), words)

    def test_a_board_that_no_update_published_says_nothing_about_one(self):
        """The example's older board was published by hand: its field is null."""
        self.assertIsNone(read_json(self.board_file(OLDER))["daily_job_started_at"])
        page = self.build_pages()[board_day_page(OLDER)]
        self.assertEqual(self.facts(page, "update"), [])
        self.assertNotIn("update", page.body_text())

    def test_a_file_whose_update_began_after_its_publish_fails_the_build_and_one_that_began_on_the_second_builds(self):
        """AndrewGodlewsky/RisingRepos#133: the contract gives the start no later than `published_at`, to the second,
        as RisingRepos's publish counts it, so a file that breaks that is refused rather than shown with no line."""
        board = read_json(self.board_file())
        write_json(self.board_file(), {**board, "daily_job_started_at": "2026-11-10T00:41:07Z"})
        (update,) = self.facts(self.build_pages()[BOARD], "update")
        self.assertEqual(
            update.text(), "The day's update began at 00:41 UTC and took less than a minute to publish this board."
        )
        shutil.rmtree(self.out)
        write_json(self.board_file(), {**board, "daily_job_started_at": "2026-11-10T00:41:08Z"})
        message = self.assertBuildFails(str(self.board_file()), "2026-11-10T00:41:08Z", "published_at")
        self.assertIn("no later than the publish", message)

    def test_the_days_update_is_given_to_the_page_as_plain_values_which_board_html_words(self):
        """AndrewGodlewsky/RisingRepos#133: `daily_job` words nothing, and the template chooses "at" or "on" once."""
        board = read_json(self.board_file())
        self.assertEqual(daily_job(board), {"started": "2026-11-10T00:28:44Z", "same_day": True, "seconds": 743})
        self.assertEqual(
            daily_job({**board, "daily_job_started_at": "2026-11-09T22:35:00Z"}),
            {"started": "2026-11-09T22:35:00Z", "same_day": False, "seconds": 7567},
        )
        self.assertIsNone(daily_job({**board, "daily_job_started_at": None}))
        template = (TEMPLATES / "board.html").read_text(encoding="utf-8")
        self.assertEqual(template.count("job.same_day"), 1)

    def test_a_board_whose_file_predates_the_update_field_builds_and_says_nothing_about_an_update(self):
        """As site-data/ held its files until RisingRepos#51's closeout published them again."""
        self.drop_fields("daily_job_started_at")
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertEqual([p for p in page.all("p") if "update" in p.classes()], [])
                self.assertNotIn("update", page.body_text())

    def test_a_board_published_two_days_or_more_after_its_day_says_it_was_made_after_its_day(self):
        """As the boards made from the archive's earlier days were. The example's are published the next day."""
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertEqual([p for p in page.all("p") if "late" in p.classes()], [])
        board = read_json(self.board_file(OLDER))
        for published, late in (("2026-11-09T23:59:59Z", False), ("2026-11-10T00:00:00Z", True)):
            with self.subTest(published):
                write_json(self.board_file(OLDER), {**board, "published_at": published})
                shutil.rmtree(self.out, ignore_errors=True)
                notes = self.facts(self.build_pages()[board_day_page(OLDER)], "late")
                if late:
                    (note,) = notes
                    self.assertEqual(
                        note.text(),
                        "This board was made after its day, from the star counts recorded on 8 November 2026.",
                    )
                else:
                    self.assertEqual(notes, [])

    def test_a_board_that_is_empty_says_so_and_states_its_board_day_the_same_way(self):
        write_json(self.index, {"schema_version": 1, "board_days": [{"board_day": OLDER, "row_count": 0}]})
        page = self.build_pages()[BOARD]
        self.assertEqual(page.rows(), [])
        self.assertEqual([href for href, _ in page.links() if "github.com" in href], [])
        self.assertIn("No repository made the board on this day.", page.body_text())
        (published,) = self.facts(page, "published")
        self.assertTrue(published.text().startswith("No repositories. Published"), published.text())
        self.assertEqual(page.one("h1").text(), "The daily board for 8 Nov 2026")
        self.assertEqual(page.meta("rr:board-date"), [OLDER])
        self.assertEqual(page.meta("rr:published-at"), ["2026-11-09T00:38:52Z"])

    def test_an_empty_board_offers_no_filter_and_no_history_to_fetch(self):
        """Nothing to filter, and no row to open: its page has no control, its policy no address to fetch from, and its
        day no history file (AndrewGodlewsky/RisingRepos#199)."""
        page = self.build_pages()[board_day_page(OLDER)]
        self.assertEqual(
            [element.tag for element in page.one("main").all() if element.tag in ("button", "select", "input")], []
        )
        self.assertNotIn("connect-src", page.directives())
        self.assertFalse((self.out / history_file(OLDER)).exists())

    def test_a_board_of_one_row_counts_it_as_one_repository(self):
        board = read_json(self.board_file())
        self.write_board({**board, "rows": board["rows"][:1]})
        page = self.build_pages()[BOARD]
        self.assertIn("1 repository", page.body_text())
        self.assertNotIn("1 repositories", page.body_text())

    def test_the_page_for_an_address_that_holds_none_says_so_and_links_to_the_board_and_the_list(self):
        page = self.build_pages()[NOT_FOUND]
        self.assertIn("not found", page.one("title").text().lower())
        self.assertEqual(page.one("h1").text(), "There is no page at this address")
        self.assertEqual(
            [(link.attrs["href"], link.text()) for link in page.one("main").all("a")],
            [("/", "the latest daily board"), ("/days/", "every board day")],
        )

    def test_the_page_for_an_address_that_holds_none_states_no_board_day(self):
        page = self.build_pages()[NOT_FOUND]
        self.assertEqual(page.meta("rr:board-date"), [])
        self.assertEqual(page.meta("rr:published-at"), [])
        self.assertEqual(page.all("time"), [])

    def test_each_pages_theme_colour_is_its_background_in_each_scheme_and_its_icon_is_inside_it(self):
        """The browser's own bar takes the page's background, light or dark as the browser's setting is. A reader's
        choice of theme on the page cannot reach it: a meta tag the script changed would be read only by some
        browsers."""
        for path, page in self.build_pages().items():
            with self.subTest(path):
                (style,) = page.all("style")
                light, dark = style.text().split("@media (prefers-color-scheme: dark)")[:2]
                expected = {
                    "(prefers-color-scheme: light)": re.search(r"--bg:\s*(#[0-9a-f]{6});", light).group(1),
                    "(prefers-color-scheme: dark)": re.search(r"--bg:\s*(#[0-9a-f]{6});", dark).group(1),
                }
                themes = [element for element in page.all("meta") if element.attrs.get("name") == "theme-color"]
                self.assertEqual({element.attrs["media"]: element.attrs["content"] for element in themes}, expected)
                self.assertEqual(len(themes), 2)
                (icon,) = [link for link in page.all("link") if link.attrs.get("rel") == "icon"]
                self.assertTrue(icon.attrs["href"].startswith("data:image/svg+xml,"), icon.attrs["href"][:40])

    def test_pages_built_for_the_preview_ask_search_engines_not_to_index_them(self):
        for path, page in self.build_pages("--noindex").items():
            with self.subTest(path):
                head, body = page.html.split("</head>")
                self.assertEqual(head.count('name="robots"'), 1)
                self.assertIn(NOINDEX, head)
                self.assertNotIn('name="robots"', body)

    def test_pages_built_without_the_option_carry_no_robots_tag(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertNotIn('name="robots"', page.html)

    def test_a_folder_that_already_holds_files_is_refused_and_left_as_it_was(self):
        self.out.mkdir()
        (self.out / "keep.txt").write_text("kept", encoding="utf-8")
        result = self.build_data()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(self.out), result.stderr)
        self.assertEqual([path.name for path in self.out.iterdir()], ["keep.txt"])
        self.assertEqual((self.out / "keep.txt").read_text(encoding="utf-8"), "kept")

    def test_without_the_data_option_it_builds_from_the_repositorys_site_data(self):
        result = build(self.out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.out / BOARD).is_file())


class TheType(BuildTest):
    """AndrewGodlewsky/RisingRepos#199: the site is set in Rising Sans and Rising Mono, modified versions of IBM Plex
    Sans and IBM Plex Mono, inside each page, so that its figures are one width on every system and the page is one
    request. The SIL Open Font License travels with them, published beside the pages and named on How it works."""

    FACES = [("Rising Sans", "400"), ("Rising Sans", "500"), ("Rising Mono", "400"), ("Rising Mono", "500")]

    def test_each_page_holds_the_four_faces_as_data_and_no_font_file_is_published(self):
        pages = self.build_pages()
        for path, page in pages.items():
            with self.subTest(path):
                (style,) = page.all("style")
                faces = re.findall(
                    r'@font-face \{ font-family: "([^"]+)"; src: url\(data:font/woff2;base64,[A-Za-z0-9+/=]+\) '
                    r'format\("woff2"\); font-weight: (\d+); font-display: block; \}',
                    style.text(),
                )
                self.assertEqual(faces, self.FACES)
                self.assertEqual(page.directives()["font-src"], ["data:"])
        published = [path.name for path in self.out.rglob("*") if path.suffix in (".woff2", ".woff", ".ttf", ".otf")]
        self.assertEqual(published, [])

    def test_no_text_is_drawn_in_the_fallback_face_and_then_moved_when_its_own_face_is_in(self):
        """A face inside the page is ready a few milliseconds after the page is first drawn. Drawn in the fallback
        until then, a name that fits one line there and takes two in its own face moved every row under it: on the
        board of 23 November 2026 the site eval measured a layout shift of 0.033 on a phone, against a limit of
        0.010. So each face holds its text back until it is in, and the fallback draws only what the faces lack.
        The eval's limit on the live root is what measures the shift itself (STANDARDS.md, P11)."""
        (style,) = self.build_pages()[BOARD].all("style")
        displays = re.findall(
            r'@font-face \{ font-family: "Rising (?:Sans|Mono)";[^}]*font-display: (\w+);', style.text()
        )
        self.assertEqual(displays, ["block"] * 4)

    def test_the_text_takes_rising_sans_and_every_figure_rising_mono_with_figures_of_one_width(self):
        (style,) = self.build_pages()[BOARD].all("style")
        style = "".join(style.children)  # as written, line by line
        self.assertRegex(style, r'--sans: "Rising Sans", "Rising Sans fallback",')
        self.assertRegex(style, r'--mono: "Rising Mono",')
        for selector in ("td.rk", "td.gr", "td.st"):
            with self.subTest(selector):
                (rule,) = re.findall(rf"(?m)^{re.escape(selector)} \{{([^}}]*)\}}", style)  # its own, outside @media
                self.assertIn("var(--mono)", rule)
                self.assertIn("font-variant-numeric: tabular-nums;", rule)

    def test_the_licence_is_published_as_the_fonts_carry_it_and_how_it_works_names_the_type_and_links_to_it(self):
        pages = self.build_pages()
        self.assertEqual((self.out / LICENCE).read_bytes(), (STATIC / "fonts" / "OFL.txt").read_bytes())
        licence = (self.out / LICENCE).read_text(encoding="utf-8")
        self.assertIn("SIL OPEN FONT LICENSE Version 1.1", licence)
        self.assertIn("Copyright © 2017 IBM Corp.", licence)
        article = pages[HOW_IT_WORKS].one("article")
        (heading,) = [heading for heading in article.all("h2") if heading.text() == "The type"]
        (line,) = [p for p in article.all("p") if "IBM Plex Sans" in p.text()]
        self.assertIn("IBM Plex Mono", line.text())
        self.assertIn("renamed", line.text())
        self.assertEqual([link.attrs["href"] for link in line.all("a")], ["/static/fonts/OFL.txt"])


class TheBoardDays(BuildTest):
    """RisingRepos#43: each board day has its own page, the pages link to the board days beside them, and one page,
    History, shows them all."""

    def test_each_board_day_has_a_page_of_its_own_with_its_board_and_the_newest_has_the_roots_board(self):
        pages = self.build_pages()
        for day in (NEWEST, OLDER):
            with self.subTest(day):
                page = pages[board_day_page(day)]
                self.assertEqual(page.one("h1").all("time")[0].attrs["datetime"], day)
                self.assertEqual(len(page.rows()), len(read_json(self.board_file(day))["rows"]))
        self.assertEqual(pages[board_day_page(NEWEST)].one("main").text(), pages[BOARD].one("main").text())

    def test_each_board_links_to_the_board_day_before_it_and_after_it_in_the_day_bar_and_the_foot(self):
        """An earlier board's day bar also leads to the newest, at the root."""
        pages = self.build_pages()
        before, after = (f"/days/{OLDER}/", "before", "prev"), (f"/days/{NEWEST}/", "after", "next")
        expected = {
            BOARD: ([before], [before]),
            board_day_page(NEWEST): ([before], [before]),
            board_day_page(OLDER): ([after, ("/", "latest", None)], [after]),
        }
        for path, (strip, foot) in expected.items():
            for part, links in ((self.strip(pages[path]), strip), (self.foot(pages[path]), foot)):
                with self.subTest(path, part=part.classes()):
                    shown = [
                        (link.attrs["href"], link.classes()[0], link.attrs.get("rel"))
                        for link in part.all("a")
                        if link.attrs["href"] != "#top"
                    ]
                    self.assertEqual(shown, links)

    def test_the_day_bar_names_the_board_day_shown_and_says_where_the_board_days_begin(self):
        pages = self.build_pages()
        newest, older = self.strip(pages[board_day_page(NEWEST)]), self.strip(pages[board_day_page(OLDER)])
        self.assertEqual(newest.attrs["aria-label"], "Board days")
        self.assertEqual(newest.all("h1")[0].text(), "The daily board for 9 Nov 2026")
        self.assertIn("The board before, ‹ 8 Nov", newest.text())
        self.assertEqual([link for link in newest.all("a") if link.classes()[0] in ("after", "latest")], [])
        self.assertEqual(older.all("h1")[0].text(), "The daily board for 8 Nov 2026")
        self.assertIn("First board", older.text())
        self.assertIn("The board after, 9 Nov ›", older.text())

    def test_an_earlier_boards_page_says_so_and_links_to_the_newest(self):
        pages = self.build_pages()
        earlier = [
            element for element in pages[board_day_page(OLDER)].one("main").all("p") if "earlier" in element.classes()
        ]
        self.assertEqual(len(earlier), 1)
        self.assertIn("9 November 2026", earlier[0].text())
        self.assertEqual([link.attrs["href"] for link in earlier[0].all("a")], ["/"])
        for path in (BOARD, board_day_page(NEWEST)):
            with self.subTest(path):
                self.assertNotIn("An earlier board", pages[path].body_text())

    def cells(self, month) -> list[tuple[int, object]]:
        """A month's calendar, by the weekday each cell is in, Monday 0: each cell holding a day."""
        (table,) = month.all("table")
        (body,) = table.all("tbody")
        return [(weekday, cell) for week in body.all("tr") for weekday, cell in enumerate(week.all("td")) if cell.all()]

    def months(self, page) -> list:
        return [section for section in page.one("main").all("section") if "month" in section.classes()]

    def test_history_gives_every_board_day_in_its_months_calendar_with_a_link_to_its_page_and_its_count(self):
        page = self.build_pages()[DAYS]
        (month,) = self.months(page)
        self.assertEqual(month.all("h2")[0].text(), "November 2026")
        self.assertEqual(
            [
                (weekday, cell.all("a")[0].attrs["href"], cell.all("time")[0].attrs["datetime"], cell.heard())
                for weekday, cell in self.cells(month)
            ],
            [
                (6, f"/days/{OLDER}/", OLDER, "Sunday 8 November: 0 repositories"),
                (0, f"/days/{NEWEST}/", NEWEST, "Monday 9 November: 5 repositories"),
            ],
        )
        (newest,) = [link for link in month.all("a") if link.attrs.get("aria-current") == "date"]
        self.assertEqual(newest.attrs["href"], f"/days/{NEWEST}/")
        (lede,) = [p for p in page.one("main").all("p") if "lede" in p.classes()]
        self.assertEqual(lede.text(), "2 board days, newest first, from 8 November 2026 to 9 November 2026.")

    def test_history_counts_each_board_days_rows_from_its_own_file_and_marks_a_day_between_with_no_board(self):
        write_json(self.board_file("2026-10-31"), {**read_json(self.board_file(OLDER)), "board_day": "2026-10-31"})
        index = read_json(self.index)
        write_json(
            self.index, {**index, "board_days": [*index["board_days"], {"board_day": "2026-10-31", "row_count": 0}]}
        )
        board = read_json(self.board_file())
        self.write_board({**board, "rows": board["rows"][:3]})
        november, october = self.months(self.build_pages()[DAYS])
        self.assertEqual(
            [month.all("h2")[0].text() for month in (november, october)], ["November 2026", "October 2026"]
        )
        self.assertEqual(
            [cell.heard() for _, cell in self.cells(november)],
            [f"{date(2026, 11, day):%A} {day} November: no board" for day in range(1, 8)]
            + ["Sunday 8 November: 0 repositories", "Monday 9 November: 3 repositories"],
        )
        self.assertEqual([cell.heard() for _, cell in self.cells(october)], ["Saturday 31 October: 0 repositories"])

    def test_a_board_days_shade_is_the_fixed_ramps_step_for_its_count(self):
        """The ramp is the same every month, so that a shade means the same count (`RAMP`)."""
        counts = [0, 1, 199, 200, 274, 275, 349, 350]
        boards = [
            {
                "board_day": f"2026-11-{30 - number:02d}",
                "rows": [{"github_id": number * 1000 + at, "full_name": f"o/r{number}-{at}"} for at in range(count)],
            }
            for number, count in enumerate(counts)
        ]
        (month,) = calendar(boards, History(boards))
        shades = {
            cell["count"]: cell["shade"]
            for week in month["weeks"]
            for cell in week
            if cell and cell["count"] is not None
        }
        self.assertEqual(shades, {0: 0, 1: 1, 199: 1, 200: 2, 274: 2, 275: 3, 349: 3, 350: 4})

    def legend(self, page) -> list[str]:
        """What History's legend says, part by part, its title first."""
        (legend,) = [div for div in page.one("main").all("div") if "ramp-legend" in div.classes()]
        return [span.text() for span in legend.all("span")]

    def test_a_board_with_no_repository_shows_and_says_no_count_of_new(self):
        """#91: an empty board said "0 new" under its 0 when a board that listed its rows came before it. A board
        with none has no repository that could be new, so its cell says its 0 and nothing after it, at any width."""
        rows = [{**row, "rank": rank} for rank, row in enumerate(read_json(self.board_file())["rows"][:3], 1)]
        older = read_json(self.board_file(OLDER))
        write_json(self.board_file("2026-11-07"), {**older, "board_day": "2026-11-07", "state": "rows", "rows": rows})
        index = read_json(self.index)
        write_json(
            self.index, {**index, "board_days": [*index["board_days"], {"board_day": "2026-11-07", "row_count": 3}]}
        )
        (month,) = self.months(self.build_pages()[DAYS])
        (empty,) = [cell for _, cell in self.cells(month) if cell.all("time")[0].attrs["datetime"] == OLDER]
        self.assertEqual(empty.heard(), "Sunday 8 November: 0 repositories")
        self.assertEqual([span for span in empty.all("span") if "fresh" in span.classes()], [])

    def test_the_legend_names_a_board_with_no_repository_and_a_day_with_no_board(self):
        """#91: after the four shades and the newest board, the legend names the two cells that have no shade."""
        legend = self.legend(self.build_pages()[DAYS])
        self.assertEqual(legend[-2:], ["no repository on the board", "no board"])
        self.assertEqual(legend[-3], "the newest board")

    def test_the_note_under_the_legend_no_longer_says_a_blank_day_had_no_board(self):
        """#91: the legend now names a day with no board, so the note says only what the count of new means."""
        (note,) = [p for p in self.build_pages()[DAYS].one("main").all("p") if "ramp-note" in p.classes()]
        self.assertEqual(
            note.text(),
            "Under each count, how many of its repositories were new: under a name on none of the boards before it.",
        )

    def test_three_board_days_link_each_to_the_ones_beside_it(self):
        write_json(self.board_file("2026-11-07"), {**read_json(self.board_file(OLDER)), "board_day": "2026-11-07"})
        index = read_json(self.index)
        write_json(
            self.index, {**index, "board_days": [*index["board_days"], {"board_day": "2026-11-07", "row_count": 0}]}
        )
        page = self.build_pages()[board_day_page(OLDER)]
        self.assertEqual(
            [(link.attrs["href"], link.attrs.get("rel")) for link in self.strip(page).all("a")],
            [("/days/2026-11-07/", "prev"), (f"/days/{NEWEST}/", "next"), ("/", None)],
        )

    def test_the_strip_of_each_page_with_no_board_leads_to_the_newest_board_with_a_class_of_its_own(self):
        """`before` and `after` name the board days either side of a board, and the newest board is neither."""
        pages = self.build_pages()
        for path in (DAYS, BASELINE, HOW_IT_WORKS):
            with self.subTest(path):
                (link,) = self.strip(pages[path]).all("a")
                self.assertEqual((link.attrs["href"], link.classes(), link.attrs.get("rel")), ("/", ["newest"], None))

    def strip(self, page):
        (strip,) = [nav for nav in page.all("nav") if "strip" in nav.classes()]
        return strip

    def foot(self, page):
        (footer,) = page.one("main").all("footer")
        (nav,) = footer.all("nav")
        return nav


class TheRow(BuildTest):
    """RisingRepos#107: a row reads as a row of a table to assistive technology however it is laid out, searching
    the page for owner/name reaches it, and the board ends with a foot."""

    def setUp(self):
        super().setUp()
        self.page = self.build_pages()[BOARD]
        (style,) = self.page.all("style")
        self.style = style.text()
        self.phone, _, self.desktop = self.style.partition("@media (min-width: 768px)")

    def test_the_chart_names_the_role_of_each_part_so_a_stacked_row_is_still_read_as_a_tables(self):
        (table,) = self.page.all("table")
        self.assertEqual(table.attrs["role"], "table")
        self.assertEqual(
            [part.attrs["role"] for part in table.all() if part.tag in ("thead", "tbody")], ["rowgroup"] * 2
        )
        for row in table.all("tr"):
            self.assertEqual(row.attrs["role"], "row")
            roles = [cell.attrs["role"] for cell in row.all() if cell.tag in ("td", "th") and cell.parent is row]
            self.assertIn(roles, (["columnheader"] * 7, ["cell", "rowheader", "cell", "cell", "cell", "cell", "cell"]))

    def test_the_owner_and_the_name_are_one_run_of_text_so_a_search_for_owner_slash_name_finds_the_row(self):
        for row in read_json(self.board_file())["rows"]:
            with self.subTest(row["full_name"]):
                owner, _, name = row["full_name"].partition("/")
                self.assertIn(f"<span class=ow>{owner}/</span><span class=nm>{name}</span>", self.page.html)
        for selector in (".ow", ".nm", ".re a"):
            for rule in re.findall(rf"(?<![\w-]){re.escape(selector)}\s*\{{([^}}]*)\}}", self.style):
                with self.subTest(selector, rule=rule):
                    self.assertNotRegex(rule, r"float|display:\s*(block|flex|grid|table)|position:\s*absolute")

    def areas(self, css: str) -> list[list[str]]:
        rule = re.search(r"\.chart (?:thead tr, \.chart )?tbody tr \{[^}]*grid-template-areas:([^;]*);", css).group(1)
        return [area.split() for area in rule.split('"')[1::2]]

    def test_on_a_phone_a_closed_row_is_its_name_its_description_and_a_line_of_figures(self):
        """The reason, under them, takes no line until the row is opened: its chevron sits under the rank."""
        self.assertEqual(
            self.areas(self.phone),
            [
                ["rank", "repository", "repository", "repository"],
                [".", "description", "description", "description"],
                [".", "growth", "own", "stars"],
                [".", "why", "why", "why"],
            ],
        )
        self.assertRegex(self.phone, r'td\.gr\.g::after \{ content: " on the day"; \}')

    def test_on_a_desktop_the_figures_sit_beside_the_name_and_the_description_under_their_headings(self):
        self.assertEqual(
            self.areas(self.desktop),
            [
                ["rank", "repository", "growth", "own", "stars"],
                [".", "description", "growth", "own", "stars"],
                [".", "why", "why", "why", "why"],
            ],
        )
        self.assertNotRegex(self.desktop, r"\.chart thead \.(de|wy)[^{]*\{[^}]*display:\s*none")

    def test_a_boards_foot_names_its_board_day_again_and_links_up_to_the_sites_bar(self):
        (footer,) = self.page.one("main").all("footer")
        self.assertEqual(footer.all("p")[0].text(), "End of the daily board for 9 November 2026")
        self.assertEqual(footer.all("time")[0].attrs["datetime"], NEWEST)
        self.assertIn(("#top", "Back to the top ↑"), [(link.attrs["href"], link.text()) for link in footer.all("a")])
        self.assertEqual(site_bar(self.page).attrs["id"], "top")

    def test_an_empty_board_has_the_foot_too(self):
        write_json(self.index, {"schema_version": 1, "board_days": [{"board_day": OLDER, "row_count": 0}]})
        shutil.rmtree(self.out)  # built by setUp
        (footer,) = self.build_pages()[BOARD].one("main").all("footer")
        self.assertIn("End of the daily board for 8 November 2026", footer.text())


class TheGrowthColumn(BuildTest):
    """The growth column gives what a row gained on its board day, when the file carries it (RisingRepos#194), and
    otherwise the stars a day of its recent days, as the board did before."""

    def test_the_stars_a_row_gained_on_its_day_are_signed_and_a_day_without_a_count_is_a_dash(self):
        """A loss takes the true minus, which the site's type draws as wide as the plus, not the hyphen."""
        for gain, shown in ((147, "+147"), (1234, "+1,234"), (0, "0"), (-600, "−600"), (-1234, "−1,234"), (None, "–")):
            with self.subTest(gain):
                self.assertEqual(gained({"gained_1_day": gain}), shown)
        self.assertEqual("−", "\N{MINUS SIGN}")

    def test_a_loss_is_in_the_red_and_a_gain_of_0_or_no_count_in_the_second_ink(self):
        """AndrewGodlewsky/RisingRepos#199: the green is for what a repository gained, so a loss takes the red, whose
        one job it is, and a gain of 0 and the dash of no count take the second ink, by one rule that is the place to
        change them. The stylesheet sets each by the cell's class, and sets a loss the same way where an opened row
        gives one: its gains over 7 and 30 days, and the stars a day in its table of the boards it was on."""
        board = read_json(self.board_file())
        gains = [147, -600, 0, None, 12]
        self.write_board(
            {**board, "rows": [{**row, "gained_1_day": gain} for row, gain in zip(board["rows"], gains, strict=True)]}
        )
        page = self.build_pages()[BOARD]
        cells = [[cell for cell in row.all("td") if "gr" in cell.classes()][0] for row in page.rows()]
        self.assertEqual([cell.text() for cell in cells], ["+147", "−600", "0", "–", "+12"])
        self.assertEqual(
            [sorted(set(cell.classes()) - {"gr", "g"}) for cell in cells], [[], ["loss"], ["nil"], ["nil"], []]
        )
        style = "".join(page.one("style").children)
        self.assertIn("td.gr.loss, .more-days td.gain.loss, .fa dd.loss { color: var(--loss); }", style)
        self.assertIn("td.gr.nil, .more-days td.gain.nil { color: var(--text-2); }", style)

    def test_an_opened_row_writes_and_marks_a_gain_as_the_board_does(self):
        """The history file words an opened row's gains as the board words its own, and gives each its class, which
        the script sets as it is: the facts give "Not known" for no count, where the board's cell gives a dash, and are
        in the ink, so only a loss takes a class there. The script reads no figure back but the board's own, for its
        order, which takes the true minus as a loss."""
        board = read_json(self.board_file())
        rows = [
            {**row, "gained_7_days": gain, "gained_30_days": month}
            for row, gain, month in zip(
                board["rows"], [147, -252, 0, None, 12], [1234, -1234, 0, None, 12], strict=True
            )
        ]
        rows[1]["recent_stars"] = -13
        self.write_board({**board, "rows": rows})
        self.build_pages()
        history = read_json(self.out / history_file(NEWEST))
        facts = [[fact for fact in entry["facts"] if fact[0].startswith("Gained in")] for entry in history["rows"]]
        self.assertEqual(
            facts,
            [
                [["Gained in 7 days", "+147"], ["Gained in 30 days", "+1,234"]],
                [
                    ["Gained in 7 days", "\N{MINUS SIGN}252", "loss"],
                    ["Gained in 30 days", "\N{MINUS SIGN}1,234", "loss"],
                ],
                [["Gained in 7 days", "0"], ["Gained in 30 days", "0"]],
                [["Gained in 7 days", "Not known"], ["Gained in 30 days", "Not known"]],
                [["Gained in 7 days", "+12"], ["Gained in 30 days", "+12"]],
            ],
        )
        self.assertEqual(history["rows"][1]["on"][-1][3:5], ["\N{MINUS SIGN}6.5", "loss"])
        self.assertEqual(
            [entry["on"][-1][3:5] for entry in history["rows"]],
            [[per_day(row), gain_class(row["recent_stars"]).strip()] for row in rows],
        )
        script = (TEMPLATES / "filters.js").read_text(encoding="utf-8")
        self.assertIn('make("dd", fact[2], fact[1])', script)
        self.assertIn('make("td", "num gain " + e[4], e[3])', script)
        self.assertIn('parseFloat(grew.textContent.replace(/[+,]/g, "").replace("\N{MINUS SIGN}", "-"))', script)

    def test_a_board_whose_file_gives_the_days_gains_shows_them_and_orders_by_them(self):
        rows = read_json(self.board_file())["rows"]
        page = self.build_pages()[BOARD]
        cells = [[cell for cell in row.all("td") if "gr" in cell.classes()][0] for row in page.rows()]
        self.assertEqual([cell.text() for cell in cells], [gained(row) for row in rows])
        self.assertTrue(all("g" in cell.classes() for cell in cells))
        self.assertIn("Most stars gained", [option.text() for option in page.all("option")])

    def test_a_board_whose_file_predates_the_gains_shows_its_stars_a_day_as_before(self):
        self.drop_row_fields("gained_1_day", "gained_7_days", "gained_30_days", "star_history")
        rows = read_json(self.board_file())["rows"]
        page = self.build_pages()[BOARD]
        (heading,) = [heading for heading in page.one("thead").all("th") if "gr" in heading.classes()]
        self.assertEqual(heading.text(), "Stars a day over the last 2 days")
        cells = [[cell for cell in row.all("td") if "gr" in cell.classes()][0] for row in page.rows()]
        self.assertEqual([cell.text() for cell in cells], [per_day(row) for row in rows])
        self.assertFalse(any("g" in cell.classes() for cell in cells))
        self.assertIn("Most stars a day", [option.text() for option in page.all("option")])

    def test_stars_a_day_are_whole_from_ten_and_to_one_place_below(self):
        self.assertEqual(per_day({"recent_stars": 295, "recent_days": 2}), "+148")
        self.assertEqual(per_day({"recent_stars": 13, "recent_days": 2}), "+6.5")

    def test_stars_a_day_are_signed_as_a_days_gain_is_since_the_contract_does_not_bar_a_loss(self):
        self.assertEqual(per_day({"recent_stars": 0, "recent_days": 2}), "0")
        self.assertEqual(per_day({"recent_stars": -13, "recent_days": 2}), "−6.5")
        self.drop_row_fields("gained_1_day", "gained_7_days", "gained_30_days", "star_history")
        board = read_json(self.board_file())
        self.write_board({**board, "rows": [{**board["rows"][0], "recent_stars": -13}, *board["rows"][1:]]})
        cell = [cell for cell in self.build_pages()[BOARD].rows()[0].all("td") if "gr" in cell.classes()][0]
        self.assertEqual((cell.text(), sorted(cell.classes())), ("−6.5", ["gr", "loss"]))


def strings(value) -> list[str]:
    """Every string in a value read from JSON, at any depth."""
    if isinstance(value, str):
        return [value]
    inside = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
    return [text for part in inside for text in strings(part)]


HYPHEN_FIGURE = re.compile(r"(?<![\w\N{EN DASH}-])-(?=\d)")
"""A hyphen-minus before a digit that is no part of a word or a date, as in "-3.42", not "2026-11-09"."""

TWO_SIGNS = re.compile("[+][-\N{MINUS SIGN}]|[-\N{MINUS SIGN}][+]")

SIGNED_ZERO = re.compile("[+\N{MINUS SIGN}]0(?![.,0-9])")
"""A figure that rounds to 0 with a sign, "+0" or "−0": a 0 is written bare."""


def wrong_signs(text: str) -> list[str]:
    """Each place where `text` writes a figure's sign as the site does not: a hyphen for a minus, a plus beside a
    minus, or a sign on a 0. `TheSigns` holds the example's pages to it, and tests/test_published_boards.py every
    page built from site-data/."""
    return [match for pattern in (HYPHEN_FIGURE, TWO_SIGNS, SIGNED_ZERO) for match in pattern.findall(text)]


class TheSigns(BuildTest):
    """AndrewGodlewsky/RisingRepos#199: a figure below 0 is written with the true minus, never the hyphen, wherever
    the site writes it, and a sign stands alone: no page writes a plus beside a minus."""

    def words(self, page) -> list[str]:
        """What a page gives a reader in words: its text, without its stylesheet and its script, and the titles and
        labels its elements carry."""
        texts = [page.one("body").text()]
        texts += [
            element.attrs[name] for element in page.all() for name in ("title", "aria-label") if element.attrs.get(name)
        ]
        return texts

    def test_a_figure_takes_the_sign_of_what_it_rounds_to_and_a_gain_a_plus_only_above_0(self):
        """One rule, in `figure`, which `times` and every count go through, and `signed`, which reads the figure."""
        self.assertEqual(
            [figure(-3.421, 2), figure(-0.004, 2), figure(-0.5, 0), figure(0.004, 2)],
            ["\N{MINUS SIGN}3.42", "0", "\N{MINUS SIGN}1", "0"],
        )
        self.assertEqual([times(-12.34), times(12.34), times(-0.04)], ["\N{MINUS SIGN}12", "12", "0"])
        self.assertEqual(
            [signed(figure(147, 0)), signed(figure(-600, 0)), signed(figure(0, 0)), signed(times(0.04))],
            ["+147", "\N{MINUS SIGN}600", "0", "0"],
        )

    def test_no_page_and_no_opened_row_writes_a_figure_with_the_hyphen_or_a_plus_beside_a_minus(self):
        """With losses on the day and over 7 and 30 days, a loss over the recent days, the example's own falling pace,
        and an own pace that rounds to 0 from above and from below, on the board and on an older one an opened row
        lists. No figure that rounds to 0 takes a sign either."""
        board = read_json(self.board_file())
        rows = [
            {**row, "gained_1_day": gain, "gained_7_days": gain, "gained_30_days": gain}
            for row, gain in zip(board["rows"], [147, -600, 0, None, -12], strict=True)
        ]
        rows[1]["recent_stars"] = -13
        self.assertTrue(any(row["baseline"] < 0 for row in rows))
        (falling,) = [row for row in rows if row["baseline"] < 0]
        falling["baseline"], rows[0]["baseline"] = -0.02, 0.02
        self.write_board({**board, "rows": rows})
        older = read_json(self.board_file(OLDER))
        self.write_board(
            {**older, "state": "rows", "rows": [{**row, "rank": rank} for rank, row in enumerate(rows, 1)]}
        )
        pages = self.build_pages()
        texts = [(path, text) for path, page in pages.items() for text in self.words(page)]
        histories = [read_json(self.out / history_file(day)) for day in (NEWEST, OLDER)]
        texts += [
            (day, text) for day, history in zip((NEWEST, OLDER), histories, strict=True) for text in strings(history)
        ]
        found = [(where, match) for where, text in texts for match in wrong_signs(text)]
        self.assertEqual(found, [])
        shown = " ".join(self.words(pages[BOARD]) + self.words(pages[BASELINE]))
        self.assertIn("Usual \N{MINUS SIGN}0.02 a day", shown)
        self.assertIn("\N{MINUS SIGN}600", shown)
        own = [entry["said"][1] for entry in histories[0]["rows"]]
        self.assertEqual([own[0], own[rows.index(falling)]], ["At its own pace: 0", "At its own pace: 0"])


class TheBands(BuildTest):
    """The board's star bands, which its filter offers, are the file's own (AndrewGodlewsky/RisingRepos#196): the
    contract has the site keep no limits of its own."""

    def buttons(self, page) -> list:
        (group,) = [element for element in page.all("div") if element.attrs.get("id") == "bands"]
        return group, [button for button in group.all("button") if "data-below" in button.attrs]

    def test_each_band_the_file_gives_is_a_button_worded_from_its_own_limits(self):
        """Its word in the board's address too, which a reader may have shared, so the build makes it from the limits
        and the script reads it from the button, never from the label."""
        _, buttons = self.buttons(self.build_pages()[BOARD])
        self.assertEqual(
            [(button.text(), button.attrs["data-below"], button.attrs["data-word"]) for button in buttons],
            [
                ("200–1k", "1000", "200-1k"),
                ("1k–3k", "3000", "1k-3k"),
                ("3k–10k", "10000", "3k-10k"),
                ("10k–30k", "30000", "10k-30k"),
                ("30k+", "", "30k-plus"),
            ],
        )
        self.assertIn('return b.getAttribute("data-word");', (TEMPLATES / "filters.js").read_text(encoding="utf-8"))

    def test_bands_the_file_changes_are_the_bands_the_board_offers(self):
        board = read_json(self.board_file())
        bands = [
            {"least_stars": 200, "most_stars": 1499},
            {"least_stars": 1500, "most_stars": 2999},
            {"least_stars": 3000, "most_stars": None},
        ]
        write_json(self.board_file(), {**board, "star_bands": bands})
        _, buttons = self.buttons(self.build_pages()[BOARD])
        self.assertEqual(
            [(button.text(), button.attrs["data-below"], button.attrs["data-word"]) for button in buttons],
            [("200–1,500", "1500", "200-1,500"), ("1,500–3k", "3000", "1,500-3k"), ("3k+", "", "3k-plus")],
        )

    def test_a_band_the_board_holds_back_keeps_its_button_hidden_so_no_filter_shows_nothing(self):
        """The example's newest board holds back 1k–3k. The script tells a row's band from every band's limits, so the
        button stays, hidden."""
        _, buttons = self.buttons(self.build_pages()[BOARD])
        self.assertEqual([button.text() for button in buttons if "hidden" in button.attrs], ["1k–3k"])

    def test_a_file_from_before_the_bands_gives_its_board_no_band_filter(self):
        self.drop_fields("star_bands")
        group, buttons = self.buttons(self.build_pages()[BOARD])
        self.assertEqual(buttons, [])
        self.assertIn("hidden", group.attrs)


class TheGuides(BuildTest):
    def test_the_guide_at_a_repositorys_own_pace_is_called_own_pace_and_each_other_by_its_multiple(self):
        # The chart's dashed line is where a repository gains at its own pace, and the others are 3 times that and
        # more. With the two names changed about, no test failed (#47's report, `sitebuild/__init__.py:725`).
        labels = [span for span in self.build_pages()[BASELINE].all("span") if "glabel" in span.classes()]
        own = [label.text() for label in labels if "own" in label.classes()]
        others = [label.text() for label in labels if "own" not in label.classes()]
        self.assertEqual(own, ["own pace"])
        self.assertTrue(others)
        for name in others:
            self.assertRegex(name, r"^[\d,]+\N{MULTIPLICATION SIGN}$")


class TheBaseline(BuildTest):
    """The Baseline page: each repository on the newest board, placed by its baseline against its recent pace, with
    a table that gives every one in words (AndrewGodlewsky/RisingRepos#199)."""

    def test_it_draws_and_lists_every_row_of_the_newest_board_in_its_order(self):
        rows = read_json(self.board_file())["rows"]
        page = self.build_pages()[BASELINE]
        self.assertIn("9 November 2026", page.one("main").all("p")[0].text())
        (svg,) = [svg for svg in page.all("svg") if svg.attrs.get("role") == "img"]  # not the mark or the switch
        self.assertEqual(svg.attrs["role"], "img")
        self.assertIn(f"the {len(rows)} repositories", svg.attrs["aria-label"])
        dots = [path for path in svg.all("path") if "dot" in path.classes()]
        self.assertEqual(sum(path.attrs["d"].count("h0") for path in dots), len(rows))
        (table,) = page.all("table")
        listed = [(row.all("td")[0].text(), row.all("a")[0].attrs["href"]) for row in table.all("tbody")[0].all("tr")]
        self.assertEqual(listed, [(str(row["rank"]), f"https://github.com/{row['full_name']}") for row in rows])

    def test_a_row_below_the_floor_or_falling_has_no_multiple_in_the_table(self):
        rows = read_json(self.board_file())["rows"]
        table = self.build_pages()[BASELINE].one("table")
        growth = [row.all("td")[-1].text() for row in table.all("tbody")[0].all("tr")]
        for row, shown in zip(rows, growth, strict=True):
            with self.subTest(row["full_name"]):
                self.assertEqual(shown == "—", row["baseline"] < row["divided_by"])

    def test_an_empty_newest_board_says_it_has_nothing_to_place(self):
        write_json(self.index, {"schema_version": 1, "board_days": [{"board_day": OLDER, "row_count": 0}]})
        page = self.build_pages()[BASELINE]
        self.assertIn("The newest board has no repository to place.", page.body_text())
        self.assertEqual(page.all("table"), [])


class TheTemplates(unittest.TestCase):
    """Jinja2 escapes a value only while autoescape is on (ADR 0010 in RisingRepos)."""

    def test_no_template_turns_escaping_off_or_marks_a_value_as_safe(self):
        for template in sorted(TEMPLATES.iterdir()):
            if template.is_file():
                with self.subTest(template.name):
                    text = template.read_text(encoding="utf-8")
                    self.assertIsNone(re.search(r"autoescape\s+[Ff]alse|\|\s*safe\b", text))


if __name__ == "__main__":
    unittest.main()
