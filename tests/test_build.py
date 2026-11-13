"""The generator, run the way deploy.yml's build job runs it, on a copy of the data contract's example.

The build writes the newest board at the site's root, a page for each board day, the list of board days, and the
page for an address that holds no page. A test of something every page holds to reads them all.
"""

import re
import shutil
import unittest
from urllib.parse import unquote

from helpers import BuildTest, build, read_json, write_json

from sitebuild import BOARD, BOARD_DAY, DAYS, NOT_FOUND, PAGES, TEMPLATES, board_day_page

NOINDEX = '<meta name="robots" content="noindex">'

NEWEST, OLDER = "2026-11-09", "2026-11-08"
"""The example's two board days, newest first, as its index lists them."""


class TheBuild(BuildTest):
    def test_the_build_writes_each_page_that_pages_names_and_one_for_each_board_day(self):
        self.build_pages()
        written = sorted(path.relative_to(self.out).as_posix() for path in self.out.rglob("*") if path.is_file())
        self.assertEqual(written, sorted([BOARD, DAYS, NOT_FOUND, board_day_page(NEWEST), board_day_page(OLDER)]))
        self.assertEqual(set(PAGES), {BOARD, DAYS, NOT_FOUND, BOARD_DAY})

    def test_the_board_shows_the_latest_board_day_which_is_the_first_in_the_index(self):
        page = self.build_pages()[BOARD]
        self.assertIn("Rising Repos", page.one("title").text())
        self.assertIn("9 November 2026", page.one("title").text())
        self.assertEqual(page.one("h1").all("time")[0].attrs["datetime"], NEWEST)
        self.assertIn("9 November 2026", page.one("h1").text())

    def test_the_board_lists_every_row_in_the_files_order_with_its_rank_name_description_language_and_stars(self):
        rows = read_json(self.board_file())["rows"]
        shown = self.build_pages()[BOARD].rows()
        self.assertEqual(len(shown), len(rows))
        for row, element in zip(rows, shown):
            text = element.text()
            self.assertEqual(text.split()[0], str(row["rank"]), text)
            self.assertEqual(
                [(link.attrs["href"], link.text()) for link in element.all("a")],
                [(f"https://github.com/{row['full_name']}", row["full_name"])],
            )
            self.assertIn(row["description"] or "No description", text)
            if row["language"]:
                self.assertIn(row["language"], text)
            self.assertRegex(text, rf"(^|\s){row['stars']:,}(\s|$)")

    def test_the_boards_column_headings_say_that_the_number_is_total_stars(self):
        page = self.build_pages()[BOARD]
        self.assertEqual(
            [heading.text() for heading in page.one("thead").all("th")],
            ["Rank", "Repository", "Description", "Language", "Total stars"],
        )

    def test_a_row_shows_no_language_when_the_file_has_none(self):
        board = read_json(self.board_file())
        languages = {row["language"] for row in board["rows"] if row["language"]}
        (no_language,) = [element for element in self.build_pages()[BOARD].rows() if "octocat/Hello-World" in element.text()]
        self.assertFalse(languages & set(no_language.text().split()), no_language.text())
        self.assertNotIn("None", no_language.text().split())

    def test_each_page_says_under_the_sites_name_that_there_is_a_new_board_each_day(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                (site,) = [element for element in page.one("header").all("p") if "site" in element.classes()]
                self.assertTrue(site.text().startswith("Rising Repos"), site.text())
                self.assertIn("on a new board each day", site.text())

    def test_the_sites_name_links_to_the_root_from_every_page(self):
        """RisingRepos#111."""
        for path, page in self.build_pages().items():
            with self.subTest(path):
                (site,) = [element for element in page.one("header").all("p") if "site" in element.classes()]
                self.assertEqual(
                    [(link.attrs["href"], link.text(), link.classes()) for link in site.all("a")],
                    [("/", "Rising Repos", ["home"])],
                )

    def test_the_ranks_take_the_condensed_cut_as_the_date_does_so_they_are_one_width_on_every_system(self):
        """RisingRepos#111: `--display` with `font-stretch: condensed` narrowed Bahnschrift and not DIN Alternate."""
        html = self.build_pages()[BOARD].html
        for selector in ("td.rank", "h1"):
            with self.subTest(selector):
                rule = re.findall(rf"(?m)^{re.escape(selector)} \{{([^}}]*)\}}", html)[0]  # its own, outside @media
                self.assertIn("font-family: var(--display-condensed);", rule)
                self.assertIn("font-stretch: condensed;", rule)

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

    def test_the_board_says_its_ranking_is_provisional_while_the_file_says_so_and_names_no_score(self):
        page = self.build_pages()[BOARD]
        self.assertIn("The ranking is provisional.", page.body_text())
        self.assertNotIn("score", page.body_text().lower())

    def test_the_board_says_nothing_about_a_provisional_ranking_once_the_file_says_it_is_not(self):
        board = read_json(self.board_file())
        write_json(self.board_file(), {**board, "score_provisional": False})
        self.assertNotIn("provisional", self.build_pages()[BOARD].body_text().lower())

    def partial_notes(self, page) -> list:
        """The band's notes on partial days: each <p class="partial"> in the board's facts."""
        return [element for element in page.one("header").all("p") if "partial" in element.classes()]

    def test_a_board_whose_ranking_read_partial_days_names_each_and_sets_a_recent_one_apart(self):
        """RisingRepos#45. The example's newest board read 7 November for a recent pace and 27 October further back."""
        recent, earlier = self.partial_notes(self.build_pages()[BOARD])
        self.assertEqual(recent.classes(), ["partial", "recent"])
        self.assertEqual(
            recent.text(),
            "A recent snapshot missed some repositories. The ranking measures each repository's recent pace over "
            "7 November 2026, so one missing then may be placed higher or lower than a full snapshot would place it.",
        )
        self.assertEqual([strong.text() for strong in recent.all("strong")], ["A recent snapshot missed some repositories."])
        self.assertEqual(earlier.classes(), ["partial"])
        self.assertEqual(
            earlier.text(),
            "Among the earlier days the ranking draws on, 27 October 2026 had a snapshot that missed some repositories.",
        )
        self.assertEqual(earlier.all("strong"), [])

    def test_two_recent_partial_days_are_named_in_one_note(self):
        board = read_json(self.board_file())
        days = [{"snapshot_day": "2026-11-08", "recent": True}, {"snapshot_day": "2026-11-07", "recent": True}]
        write_json(self.board_file(), {**board, "partial_days": days})
        (note,) = self.partial_notes(self.build_pages()[BOARD])
        self.assertEqual(note.classes(), ["partial", "recent"])
        self.assertTrue(
            note.text().startswith(
                "Recent snapshots missed some repositories. The ranking measures each repository's recent pace over "
                "8 November 2026 and 7 November 2026, so"
            ),
            note.text(),
        )

    def test_a_board_whose_ranking_read_partial_days_only_further_back_says_so_in_a_plain_line(self):
        board = read_json(self.board_file())
        for days, named in (
            (["2026-10-27", "2026-06-12"], "27 October 2026 and 12 June 2026"),
            (["2026-10-27", "2026-09-26", "2026-06-12"], "27 October 2026, 26 September 2026, and 12 June 2026"),
        ):
            with self.subTest(len(days)):
                partial = [{"snapshot_day": day, "recent": False} for day in days]
                write_json(self.board_file(), {**board, "partial_days": partial})
                shutil.rmtree(self.out, ignore_errors=True)
                (note,) = self.partial_notes(self.build_pages()[BOARD])
                self.assertEqual(note.classes(), ["partial"])
                self.assertEqual(note.all("strong"), [])
                self.assertEqual(
                    note.text(),
                    f"Among the earlier days the ranking draws on, {named} had snapshots that missed some repositories.",
                )

    def test_a_board_day_whose_own_snapshot_is_partial_says_that_a_repository_it_missed_is_not_on_the_board(self):
        # As 2026-07-31's board was: its own snapshot partial, and no row on it.
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
                (note,) = self.partial_notes(page)
                self.assertEqual(note.classes(), ["partial", "recent"])
                self.assertEqual(
                    note.text(),
                    "This day's snapshot missed some repositories. A repository it missed could not be ranked, so it is "
                    "not on this board." + after,
                )
                self.assertIn("No repository made the board on this day.", page.body_text())

    def test_a_board_whose_ranking_read_no_partial_day_has_no_note_on_them(self):
        """The example's older board lists none."""
        self.assertEqual(read_json(self.board_file(OLDER))["partial_days"], [])
        page = self.build_pages()[board_day_page(OLDER)]
        self.assertEqual(self.partial_notes(page), [])
        self.assertNotIn("snapshot", page.body_text())

    def test_a_board_whose_file_predates_partial_days_builds_and_says_nothing_about_them(self):
        """As site-data/ holds its files until RisingRepos#45's closeout publishes them again: the schema and every
        board day's file without the field. Such a file neither names a partial day nor says there was none."""
        schema = read_json(self.daily_schema)
        del schema["properties"]["partial_days"]
        schema["required"].remove("partial_days")
        write_json(self.daily_schema, schema)
        for day in (NEWEST, OLDER):
            board = read_json(self.board_file(day))
            del board["partial_days"]
            write_json(self.board_file(day), board)
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertEqual([p for p in page.all("p") if "partial" in p.classes()], [])
                self.assertNotIn("snapshot", page.body_text())

    def test_a_board_that_is_empty_says_so_and_states_its_board_day_the_same_way(self):
        write_json(self.index, {"schema_version": 1, "board_days": [{"board_day": OLDER, "row_count": 0}]})
        page = self.build_pages()[BOARD]
        self.assertEqual(page.rows(), [])
        self.assertEqual([href for href, _ in page.links() if "github.com" in href], [])
        self.assertIn("No repository made the board on this day.", page.body_text())
        self.assertIn("No repositories.", page.body_text())
        self.assertIn("8 November 2026", page.one("h1").text())
        self.assertEqual(page.meta("rr:board-date"), [OLDER])
        self.assertEqual(page.meta("rr:published-at"), ["2026-11-09T00:38:52Z"])

    def test_a_board_of_one_row_counts_it_as_one_repository(self):
        board = read_json(self.board_file())
        self.write_board({**board, "rows": board["rows"][:1]})
        page = self.build_pages()[BOARD]
        self.assertIn("1 repository", page.body_text())
        self.assertNotIn("1 repositories", page.body_text())

    def test_the_page_for_an_address_that_holds_none_says_so_and_links_to_the_board(self):
        page = self.build_pages()[NOT_FOUND]
        self.assertIn("not found", page.one("title").text().lower())
        self.assertEqual(page.one("h1").text(), "Page not found")
        self.assertEqual(
            [(link.attrs["href"], link.text()) for link in page.one("main").all("a")], [("/", "the latest daily board")]
        )

    def test_the_page_for_an_address_that_holds_none_states_no_board_day(self):
        page = self.build_pages()[NOT_FOUND]
        self.assertEqual(page.meta("rr:board-date"), [])
        self.assertEqual(page.meta("rr:published-at"), [])
        self.assertEqual(page.all("time"), [])

    def test_each_pages_icon_and_theme_colour_take_the_colour_of_its_band(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                (style,) = page.all("style")
                band = re.search(r"--field:\s*(#[0-9a-f]{6});", style.text()).group(1)
                self.assertEqual(page.meta("theme-color"), [band])
                (icon,) = [link for link in page.all("link") if link.attrs.get("rel") == "icon"]
                self.assertEqual(re.findall(r"fill='(#[0-9a-f]{6})'", unquote(icon.attrs["href"])), [band])

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


class TheBoardDays(BuildTest):
    """RisingRepos#43: each board day has its own page, the pages link to the board days beside them, and one page
    lists them all."""

    def test_each_board_day_has_a_page_of_its_own_with_its_board_and_the_newest_has_the_roots_board(self):
        pages = self.build_pages()
        for day in (NEWEST, OLDER):
            with self.subTest(day):
                page = pages[board_day_page(day)]
                self.assertEqual(page.one("h1").all("time")[0].attrs["datetime"], day)
                self.assertEqual(len(page.rows()), len(read_json(self.board_file(day))["rows"]))
        self.assertEqual(pages[board_day_page(NEWEST)].one("main").text(), pages[BOARD].one("main").text())

    def test_each_board_links_to_the_board_day_before_it_and_after_it_and_to_the_list_in_the_strip_and_the_foot(self):
        pages = self.build_pages()
        expected = {
            BOARD: [(OLDER, "before"), (None, "all")],
            board_day_page(NEWEST): [(OLDER, "before"), (None, "all")],
            board_day_page(OLDER): [(NEWEST, "after"), (None, "all")],
        }
        for path, links in expected.items():
            for part in (self.strip(pages[path]), self.foot(pages[path])):
                with self.subTest(path, part=part.tag):
                    shown = [
                        (link.attrs["href"], link.classes()[0], link.attrs.get("rel"))
                        for link in part.all("a")
                        if link.attrs["href"] != "#top"
                    ]
                    self.assertEqual(
                        shown,
                        [
                            ("/days/", "all", None) if day is None else (f"/days/{day}/", kind, "prev" if kind == "before" else "next")
                            for day, kind in links
                        ],
                    )

    def test_the_strip_names_the_board_day_shown_and_says_where_the_board_days_end(self):
        pages = self.build_pages()
        newest, older = self.strip(pages[board_day_page(NEWEST)]), self.strip(pages[board_day_page(OLDER)])
        self.assertEqual(newest.attrs["aria-label"], "Board days")
        self.assertIn("9 Nov 2026", newest.text())
        self.assertIn("Newest board", newest.text())
        self.assertIn("8 Nov 2026", older.text())
        self.assertIn("First board", older.text())
        self.assertIn("The board before, ‹ 8 Nov", newest.text())

    def test_an_earlier_boards_page_says_so_and_links_to_the_newest(self):
        pages = self.build_pages()
        earlier = [element for element in pages[board_day_page(OLDER)].one("header").all("p") if "earlier" in element.classes()]
        self.assertEqual(len(earlier), 1)
        self.assertIn("9 November 2026", earlier[0].text())
        self.assertEqual([link.attrs["href"] for link in earlier[0].all("a")], ["/"])
        for path in (BOARD, board_day_page(NEWEST)):
            with self.subTest(path):
                self.assertNotIn("An earlier board", pages[path].body_text())

    def test_the_list_gives_every_board_day_newest_first_with_a_link_to_its_page_and_its_count_of_repositories(self):
        page = self.build_pages()[DAYS]
        items = page.one("main").all("li")
        self.assertEqual(
            [(item.all("a")[0].attrs["href"], item.all("time")[0].attrs["datetime"], item.text()) for item in items],
            [
                (f"/days/{NEWEST}/", NEWEST, "Monday 9 November 5 repositories"),
                (f"/days/{OLDER}/", OLDER, "Sunday 8 November No repositories"),
            ],
        )
        self.assertEqual([heading.text() for heading in page.one("main").all("h2")], ["November 2026"])
        self.assertIn("2 board days, newest first", page.one("header").text())

    def test_the_list_counts_each_board_days_rows_from_its_own_file_and_groups_the_days_by_month(self):
        write_json(self.board_file("2026-10-31"), {**read_json(self.board_file(OLDER)), "board_day": "2026-10-31"})
        index = read_json(self.index)
        write_json(self.index, {**index, "board_days": [*index["board_days"], {"board_day": "2026-10-31", "row_count": 0}]})
        board = read_json(self.board_file())
        self.write_board({**board, "rows": board["rows"][:3]})
        main = self.build_pages()[DAYS].one("main")
        self.assertEqual([heading.text() for heading in main.all("h2")], ["November 2026", "October 2026"])
        self.assertEqual([item.text() for item in main.all("li")][0], "Monday 9 November 3 repositories")
        self.assertEqual(main.all("li")[-1].text(), "Saturday 31 October No repositories")

    def test_three_board_days_link_each_to_the_ones_beside_it(self):
        write_json(self.board_file("2026-11-07"), {**read_json(self.board_file(OLDER)), "board_day": "2026-11-07"})
        index = read_json(self.index)
        write_json(self.index, {**index, "board_days": [*index["board_days"], {"board_day": "2026-11-07", "row_count": 0}]})
        page = self.build_pages()[board_day_page(OLDER)]
        self.assertEqual(
            [(link.attrs["href"], link.attrs.get("rel")) for link in self.strip(page).all("a")],
            [("/days/2026-11-07/", "prev"), (f"/days/{NEWEST}/", "next"), ("/days/", None)],
        )

    def test_the_lists_strip_leads_to_the_newest_board_with_a_class_of_its_own(self):
        """`before` and `after` name the board days either side of a board, and the newest board is neither."""
        (link,) = self.strip(self.build_pages()[DAYS]).all("a")
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
        self.phone, _, self.desktop = self.style.partition("@media (min-width: 48rem)")

    def test_the_chart_names_the_role_of_each_part_so_a_stacked_row_is_still_read_as_a_tables(self):
        (table,) = self.page.all("table")
        self.assertEqual(table.attrs["role"], "table")
        self.assertEqual([part.attrs["role"] for part in table.all() if part.tag in ("thead", "tbody")], ["rowgroup"] * 2)
        for row in table.all("tr"):
            self.assertEqual(row.attrs["role"], "row")
            roles = [cell.attrs["role"] for cell in row.all() if cell.tag in ("td", "th")]
            self.assertIn(roles, (["columnheader"] * 5, ["cell", "rowheader", "cell", "cell", "cell"]))

    def test_the_owner_and_the_name_are_one_run_of_text_so_a_search_for_owner_slash_name_finds_the_row(self):
        for row in read_json(self.board_file())["rows"]:
            with self.subTest(row["full_name"]):
                owner, _, name = row["full_name"].partition("/")
                self.assertIn(f'<span class="owner">{owner}/</span><span class="name">{name}</span>', self.page.html)
        for selector in (".owner", ".name", ".repository a"):
            for rule in re.findall(rf"(?<![\w-]){re.escape(selector)}\s*\{{([^}}]*)\}}", self.style):
                with self.subTest(selector, rule=rule):
                    self.assertNotRegex(rule, r"float|display:\s*(block|flex|grid|table)|position:\s*absolute")

    def test_on_a_phone_a_row_is_stacked_with_the_description_at_its_full_width(self):
        areas = re.search(r"\.chart tbody tr \{[^}]*grid-template-areas:([^;]*);", self.phone).group(1).split('"')[1::2]
        self.assertEqual(
            [area.split() for area in areas],
            [
                ["rank", "repository", "repository"],
                ["description", "description", "description"],
                ["language", "language", "stars"],
            ],
        )
        self.assertRegex(self.phone, r'td\.stars::after \{ content: " stars";')

    def test_on_a_desktop_the_description_sits_under_the_name_beside_the_language_and_the_stars(self):
        areas = re.search(r"grid-template-areas:([^;]*);", self.desktop).group(1).split('"')[1::2]
        self.assertEqual(
            [area.split() for area in areas],
            [["rank", "repository", "language", "stars"], ["rank", "description", "language", "stars"]],
        )

    def test_the_name_link_is_padded_to_a_fingers_height_without_moving_the_lines_around_it(self):
        (rule,) = re.findall(r"(?<![\w-])\.repository a \{([^}]*)\}", self.phone)
        self.assertIn("padding-block: 0.75rem;", rule)  # 46 px tall at 390 px wide, measured on RisingRepos#43

    def test_a_boards_foot_names_its_board_day_again_and_links_up_to_the_band(self):
        (footer,) = self.page.one("main").all("footer")
        self.assertEqual(footer.all("p")[0].text(), "End of the daily board for 9 November 2026")
        self.assertEqual(footer.all("time")[0].attrs["datetime"], NEWEST)
        self.assertIn(("#top", "Back to the top ↑"), [(link.attrs["href"], link.text()) for link in footer.all("a")])
        self.assertEqual(self.page.one("header").attrs["id"], "top")

    def test_an_empty_board_has_the_foot_too(self):
        write_json(self.index, {"schema_version": 1, "board_days": [{"board_day": OLDER, "row_count": 0}]})
        shutil.rmtree(self.out)  # built by setUp
        (footer,) = self.build_pages()[BOARD].one("main").all("footer")
        self.assertIn("End of the daily board for 8 November 2026", footer.text())


class TheTemplates(unittest.TestCase):
    """Jinja2 escapes a value only while autoescape is on (ADR 0010 in RisingRepos)."""

    def test_no_template_turns_escaping_off_or_marks_a_value_as_safe(self):
        for template in sorted(TEMPLATES.iterdir()):
            with self.subTest(template.name):
                text = template.read_text(encoding="utf-8")
                self.assertIsNone(re.search(r"autoescape\s+[Ff]alse|\|\s*safe\b", text))


if __name__ == "__main__":
    unittest.main()
