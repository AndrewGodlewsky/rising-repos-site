"""The page's one script: the notice of an old board (AndrewGodlewsky/RisingRepos#56), and the theme.

Every board day's page, the root among them, the list of board days, and the Baseline page carry the notice. It
compares the newest board's publish time with the reader's clock when the page is opened, so it needs no new build:
from 26 hours the page says how old the newest board is, and from 7 days it shows no board and says why. Younger than
26 hours, or with scripts turned off, the page is as it was built.

Each page carries one script, the site's own, in its head (AndrewGodlewsky/RisingRepos#199): the theme on every page,
then the notice on the pages that carry it, then a board's filters, or the Baseline page's readout. These tests lift
that script out of a built page, exactly as the page holds it, and hand it to Node with a clock and a browser of their
choosing (tests/run_page_script.js). Without Node they fail, never skip.
"""

import base64
import hashlib
import json
import re
import shutil
import subprocess
import unittest
from datetime import UTC, datetime, timedelta

from helpers import ROOT, BuildTest, Page, read_json, shipped

from sitebuild import BASELINE, BOARD, DAYS, HOW_IT_WORKS, NOT_FOUND, board_day_page, long_date

NODE = shutil.which("node")
RUNNER = ROOT / "tests" / "run_page_script.js"

NEWEST, OLDER = "2026-11-09", "2026-11-08"
"""The example's two board days, newest first."""

PUBLISHED = datetime(2026, 11, 10, 0, 41, 7, tzinfo=UTC)
"""When the example's newest board was published: the moment every page's script measures from."""

CARRIERS = (BOARD, board_day_page(NEWEST), board_day_page(OLDER), DAYS, BASELINE)
"""The pages that carry the notice, as the example builds them: the root, the newest and the earlier board day's
pages, the list, and the Baseline page, which shows the newest board's chart."""

PARTS = {
    BOARD: ("theme.js", "old-board.js", "filters.js"),
    board_day_page(NEWEST): ("theme.js", "old-board.js", "filters.js"),
    board_day_page(OLDER): ("theme.js", "old-board.js"),
    DAYS: ("theme.js", "old-board.js"),
    BASELINE: ("theme.js", "old-board.js", "baseline.js"),
    HOW_IT_WORKS: ("theme.js",),
    NOT_FOUND: ("theme.js",),
}
"""The parts of each page's one script, in order, as the example builds them: the theme on every page; the notice
where the page carries it; a board's filters where the board has rows, which the example's earlier board has not; and
the Baseline page's readout."""

NOTICE, TITLE, TEXT = "old-board", "old-board-title", "old-board-text"
"""The ids of the notice and of its two parts: the bold sentence, and the rest."""

TOUCHES = {
    f"document.getElementById({NOTICE})",
    f"document.getElementById({TITLE})",
    f"document.getElementById({TEXT})",
    f"{NOTICE}.getAttribute(data-newest-board-day)",
    f"{NOTICE}.getAttribute(data-newest-published-at)",
    f"{TITLE}.textContent=",
    f"{TEXT}.textContent=",
    f"{NOTICE}.removeAttribute(hidden)",
    "document.documentElement",
    "root.setAttribute(data-withheld)",
}
"""Everything the notice's part may read or write, as tests/run_page_script.js records it: the notice's two
attributes, the text of its two parts, its hidden attribute, and one attribute on the root element. It reads no other
value, so none an owner wrote, and it writes text, never markup."""

THEME_TOUCHES = {
    "document.documentElement",
    "root.setAttribute(data-js)",
    "localStorage.getItem(theme)",
    "root.setAttribute(data-theme)",
    "window.matchMedia",
    "window.matchMedia((prefers-color-scheme: dark))",
    "document.addEventListener(DOMContentLoaded)",
}
"""Everything the script's other parts touch while the page loads: the theme marks the root element as running the
script (data-js), reads the theme kept in this browser and the browser's own colour scheme, applies a kept theme
(data-theme), and waits for the page to be parsed to wire its switch, as a board's filters and the Baseline page's
readout wait too. Nothing else runs before the page is parsed."""

POLICY = (
    "default-src 'none'; style-src 'unsafe-inline'; font-src data:; img-src data:; base-uri 'none'; form-action 'none'"
)
"""Each page's Content-Security-Policy but for the directive that lets its one script run, and, on a board with rows,
the one that lets it fetch the board day's history from the site's own address: no request but the page, and its
type inside it as data: addresses."""

HOUR, DAY, SECOND = timedelta(hours=1), timedelta(days=1), timedelta(seconds=1)


def script_of(page: Page) -> str:
    """The text of the page's one script element, exactly as the page holds it."""
    (text,) = re.findall(r"<script>(.*?)</script>", page.html, flags=re.DOTALL)
    return text


def by_id(page: Page, name: str):
    (element,) = [element for element in page.all() if element.attrs.get("id") == name]
    return element


def stand_ins(page: Page, names=(NOTICE, TITLE, TEXT)) -> dict:
    """The elements the script may look up, as the built page has them, each by its id: its attributes and its text."""
    return {
        name: {
            "attributes": {key: value or "" for key, value in by_id(page, name).attrs.items()},
            "text": by_id(page, name).text(),
        }
        for name in names
    }


def loaded(page: Page) -> dict:
    """The root element's attributes once the script has run on a fresh page: the page's own, and the mark the theme
    sets so that the stylesheet shows the controls that need the script."""
    return {**page.one("html").attrs, "data-js": ""}


def run(page: Page, *moments: datetime, **browser) -> list[dict]:
    """Run the page's script under Node once for each of `moments`, with the clock at that moment, and return what each
    run did. `browser` is the rest of each run, as tests/run_page_script.js reads it."""
    return run_with(page, [(moment, None) for moment in moments], **browser)


def run_with(
    page: Page, cases: list[tuple[datetime, dict | None]], names=(NOTICE, TITLE, TEXT), **browser
) -> list[dict]:
    """Run the page's script under Node once for each case: the clock's moment, and attributes that replace the
    notice's, as a page that held others would have them, or None to keep the page's own."""
    if NODE is None:
        raise AssertionError("Node is needed to run the page's script, and none is on the PATH.")
    root = {"attributes": {key: value or "" for key, value in page.one("html").attrs.items()}}
    runs = []
    for moment, notice in cases:
        elements = stand_ins(page, names)
        if notice is not None:
            elements[NOTICE]["attributes"] = notice
        runs.append({"now": round(moment.timestamp() * 1000), "elements": elements, "root": root, **browser})
    result = subprocess.run(
        [NODE, str(RUNNER)],
        input=json.dumps({"script": script_of(page), "runs": runs}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


def stale(age: str) -> dict:
    return {
        TITLE: f"The newest board is {age} old.",
        TEXT: "It is the board for 9 November 2026. A board is due every day, and none has come out since.",
    }


def withheld(age: str) -> dict:
    return {
        TITLE: f"No board is shown: the newest is {age} old.",
        TEXT: "It is the board for 9 November 2026. When a week passes with no new board, the site stops showing its "
        "boards, so that an old ranking is not taken for a current one.",
    }


class TheNotice(BuildTest):
    def setUp(self):
        super().setUp()
        self.pages = self.build_pages()

    def assertAsBuilt(self, page: Page, outcomes: list[dict]):
        """Each run left the page as it was built: the notice hidden and empty, and the root as it was, but for the
        theme's mark."""
        for outcome in outcomes:
            self.assertIsNone(outcome["error"])
            self.assertEqual(outcome["elements"], stand_ins(page))
            self.assertEqual(outcome["root"], loaded(page))
            self.assertLessEqual(set(outcome["operations"]), TOUCHES | THEME_TOUCHES)

    def assertNotice(self, outcome: dict, words: dict, *, hides_boards: bool):
        self.assertIsNone(outcome["error"])
        self.assertLessEqual(set(outcome["operations"]), TOUCHES | THEME_TOUCHES)
        elements = outcome["elements"]
        self.assertNotIn("hidden", elements[NOTICE]["attributes"])
        self.assertEqual({name: elements[name]["text"] for name in (TITLE, TEXT)}, words)
        self.assertEqual("data-withheld" in outcome["root"], hides_boards)

    def test_each_page_with_a_board_or_the_list_carries_the_newest_boards_day_and_publish_time_for_the_script(self):
        """An earlier board day's page, the list, and the Baseline page measure from the newest board too. The build
        writes the day as it writes every other date on the page, and the script puts it in the notice unchanged."""
        for path in CARRIERS:
            with self.subTest(path):
                notice = by_id(self.pages[path], NOTICE)
                self.assertEqual(notice.attrs["data-newest-board-day"], long_date(NEWEST))
                self.assertEqual(notice.attrs["data-newest-published-at"], "2026-11-10T00:41:07Z")
                self.assertIn("hidden", notice.attrs)
                self.assertEqual(notice.text(), "")

    def test_a_board_younger_than_26_hours_leaves_the_page_as_it_was_built(self):
        for path in CARRIERS:
            with self.subTest(path):
                page = self.pages[path]
                self.assertAsBuilt(page, run(page, PUBLISHED, PUBLISHED + HOUR, PUBLISHED + 26 * HOUR - SECOND))

    def test_a_clock_set_behind_the_publish_time_leaves_the_page_as_it_was_built(self):
        for path in CARRIERS:
            with self.subTest(path):
                page = self.pages[path]
                self.assertAsBuilt(page, run(page, PUBLISHED - SECOND, PUBLISHED - DAY, PUBLISHED - 400 * DAY))

    def test_from_26_hours_the_page_says_how_old_the_newest_board_is_in_hours_and_then_in_days(self):
        """26 hours exactly is old, as it is for the stale check. The age is in hours while it is under two days."""
        cases = {
            26 * HOUR: "26 hours",
            48 * HOUR - SECOND: "47 hours",
            48 * HOUR: "2 days",
            3 * DAY + 5 * HOUR: "3 days",
            7 * DAY - SECOND: "6 days",
        }
        for path in CARRIERS:
            page = self.pages[path]
            outcomes = run(page, *(PUBLISHED + age for age in cases))
            for outcome, words in zip(outcomes, cases.values(), strict=True):
                with self.subTest(path, age=words):
                    self.assertNotice(outcome, stale(words), hides_boards=False)

    def test_from_7_days_the_page_shows_no_board_and_says_why(self):
        cases = {7 * DAY: "7 days", 10 * DAY: "10 days", 400 * DAY: "400 days"}
        for path in CARRIERS:
            page = self.pages[path]
            outcomes = run(page, *(PUBLISHED + age for age in cases))
            for outcome, words in zip(outcomes, cases.values(), strict=True):
                with self.subTest(path, age=words):
                    self.assertNotice(outcome, withheld(words), hides_boards=True)

    def test_a_malformed_or_impossible_publish_time_changes_nothing(self):
        """The last value is a moment that Date.parse reads and that reads back as the same text, in a shape the page
        never writes: a year of six digits, and no seconds."""
        built = {key: value or "" for key, value in by_id(self.pages[BOARD], NOTICE).attrs.items()}
        name = "data-newest-published-at"
        unreadable = [
            "",
            "Z",
            "not a time",
            "2026-11-10 00:41:07Z",
            "2026-11-10T00:41:07+00:00",
            "2026-11-10T00:41:07.000Z",
            "2026-11-10T00:41Z",
            "2026-13-10T00:41:07Z",
            "2026-02-30T00:41:07Z",
            "2026-11-10T24:00:00Z",
            "-000001-01-01T00:00Z",
        ]
        notices = []  # each value in place of the page's own, and the attribute left out (None)
        for value in [*unreadable, None]:
            attributes = {key: text for key, text in built.items() if key != name}
            if value is not None:
                attributes[name] = value
            notices.append((value, attributes))
        for path in CARRIERS:
            page = self.pages[path]
            outcomes = run_with(page, [(PUBLISHED + 30 * DAY, attributes) for _, attributes in notices])
            for (value, attributes), outcome in zip(notices, outcomes, strict=True):
                with self.subTest(path, value=value):
                    self.assertIsNone(outcome["error"])
                    self.assertEqual(outcome["elements"][NOTICE]["attributes"], attributes)
                    self.assertEqual([outcome["elements"][part]["text"] for part in (TITLE, TEXT)], ["", ""])
                    self.assertEqual(outcome["root"], loaded(page))
                    self.assertLessEqual(set(outcome["operations"]), TOUCHES | THEME_TOUCHES)

    def test_the_notice_is_filled_the_moment_the_parser_reaches_it_when_the_script_runs_before_it(self):
        """The script runs in the head, before the notice is parsed. It watches the document, and fills and shows the
        notice once the parser has inserted it, as it does when the notice is already there, then stops watching."""
        watching = ["new MutationObserver", "MutationObserver.observe", "MutationObserver.disconnect"]
        for path in CARRIERS:
            page = self.pages[path]
            for age, words, hides in ((30 * HOUR, stale("30 hours"), False), (10 * DAY, withheld("10 days"), True)):
                with self.subTest(path, age=age):
                    (late,) = run(page, PUBLISHED + age, late=True)
                    (at_once,) = run(page, PUBLISHED + age)
                    self.assertEqual([op for op in late["operations"] if "MutationObserver" in op], watching)
                    late["operations"] = [op for op in late["operations"] if op not in watching]
                    self.assertNotice(late, words, hides_boards=hides)
                    self.assertEqual((late["elements"], late["root"]), (at_once["elements"], at_once["root"]))
            with self.subTest(path, age="fresh"):
                (late,) = run(page, PUBLISHED + HOUR, late=True)
                self.assertIsNone(late["error"])
                self.assertEqual(late["elements"], stand_ins(page))
                self.assertEqual([op for op in late["operations"] if "MutationObserver" in op], watching)

    def test_the_script_reads_only_what_it_needs_and_writes_only_the_notices_text_and_the_roots_attributes(self):
        """It inserts no value an owner wrote, makes no request as the page loads, and keeps nothing but the reader's
        theme: the context it runs in has no way to make a request, and a script that reached for one would throw."""
        page = self.pages[BOARD]
        outcomes = run(page, PUBLISHED, PUBLISHED + 30 * HOUR, PUBLISHED + 10 * DAY)
        for outcome in outcomes:
            self.assertIsNone(outcome["error"])
            self.assertLessEqual(set(outcome["operations"]), TOUCHES | THEME_TOUCHES)
        self.assertEqual(
            sorted(set(outcomes[-1]["operations"])),
            sorted(TOUCHES | THEME_TOUCHES - {"root.setAttribute(data-theme)"}),
            "a run from 7 days should touch each thing the script may touch as the page loads, with no theme kept",
        )
        for path in CARRIERS:
            with self.subTest(path):
                text = script_of(self.pages[path])
                self.assertNotRegex(
                    text, r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|cookie|sessionStorage|eval\("
                )
                # It keeps one thing, the reader's theme: every call to localStorage names that key and no other.
                self.assertEqual(re.findall(r"localStorage\.\w+\(\s*([^,)]*)", text), ['"theme"'] * 3)

    def test_the_one_request_a_board_may_make_is_its_own_board_days_history_from_the_sites_own_address(self):
        """A reader who opens a row fetches that board day's history.json, once. The policy lets the page fetch only
        from its own address (connect-src 'self'), and only a board with rows may."""
        page = self.pages[BOARD]
        self.assertEqual(re.findall(r"\bfetch\(([^,]*),", script_of(page)), ['table.getAttribute("data-history")'])
        (table,) = page.all("table")
        self.assertEqual(table.attrs["data-history"], f"/days/{NEWEST}/history.json")
        for path, page in self.pages.items():
            with self.subTest(path):
                self.assertEqual("fetch(" in script_of(page), "filters.js" in PARTS[path])


class TheTheme(BuildTest):
    """The theme follows the browser's own setting until the reader presses the switch. A choice is kept in this
    browser alone, and is set before the page is first drawn, so the page never flashes the other theme. A press back to
    the browser's own setting clears the kept choice. Without the script the switch is hidden and the page follows the
    browser by the stylesheet alone."""

    def setUp(self):
        super().setUp()
        self.pages = self.build_pages()

    def opened(self, path: str, **browser) -> dict:
        page = self.pages[path]
        (outcome,) = run_with(page, [(PUBLISHED, None)], names=(NOTICE, TITLE, TEXT, "theme"), **browser)
        self.assertIsNone(outcome["error"])
        return outcome

    def test_a_kept_choice_is_set_on_the_root_before_the_page_is_parsed_and_nothing_else_is(self):
        for stored, theme in (("dark", "dark"), ("light", "light"), (None, None), ("blue", None), ("", None)):
            with self.subTest(stored):
                (outcome,) = run(self.pages[BOARD], PUBLISHED, stored=stored, late=True)
                self.assertIsNone(outcome["error"])
                self.assertEqual(outcome["root"].get("data-theme"), theme)
                self.assertEqual(outcome["root"]["data-js"], "")

    def test_the_switch_says_whether_the_page_is_dark_and_a_press_keeps_the_other_theme(self):
        for dark in (False, True):
            with self.subTest(dark=dark):
                shown = self.opened(BOARD, dark=dark, ready=True)
                self.assertEqual(shown["elements"]["theme"]["attributes"]["aria-pressed"], "true" if dark else "false")
                pressed = self.opened(BOARD, dark=dark, ready=True, clicks=["theme"])
                self.assertEqual(pressed["stored"], "light" if dark else "dark")
                self.assertEqual(pressed["root"]["data-theme"], "light" if dark else "dark")
                self.assertEqual(
                    pressed["elements"]["theme"]["attributes"]["aria-pressed"], "false" if dark else "true"
                )

    def test_a_press_back_to_the_browsers_own_setting_clears_the_kept_choice(self):
        for dark in (False, True):
            with self.subTest(dark=dark):
                back = self.opened(BOARD, dark=dark, ready=True, clicks=["theme", "theme"])
                self.assertIsNone(back["stored"])
                self.assertNotIn("data-theme", back["root"])
                self.assertEqual(back["elements"]["theme"]["attributes"]["aria-pressed"], "true" if dark else "false")

    def test_every_page_carries_the_switch_for_the_script_to_show_and_the_stylesheet_hides_it_without_the_script(self):
        for path, page in self.pages.items():
            with self.subTest(path):
                button = by_id(page, "theme")
                self.assertEqual((button.tag, button.attrs["aria-pressed"]), ("button", "false"))
                self.assertIn("js-only", button.classes())
                self.assertEqual(button.text(), "Dark theme")
                self.assertIn(":root:not([data-js]) .js-only { display: none !important; }", page.one("style").text())


class ThePolicy(BuildTest):
    """The Content-Security-Policy lets the page's one script run by the hash of its text, and nothing else in it
    changes."""

    def setUp(self):
        super().setUp()
        self.pages = self.build_pages()

    def assertScriptAllowed(self, page: Page):
        """The policy's `script-src` names one source: the SHA-256 of the exact text of the page's one script."""
        digest = base64.b64encode(hashlib.sha256(script_of(page).encode("utf-8")).digest()).decode("ascii")
        self.assertEqual(page.directives()["script-src"], [f"'sha256-{digest}'"])

    def test_each_page_carries_one_script_the_sites_own_parts_that_it_uses_and_no_other(self):
        """AndrewGodlewsky/RisingRepos#199 made the theme, the notice, and a board's filters one script a page, each
        page carrying only the parts it uses, in the order site.js includes them."""
        self.assertEqual(set(PARTS), set(self.pages))
        for path, parts in PARTS.items():
            with self.subTest(path):
                page = self.pages[path]
                self.assertEqual(len(page.all("script")), 1)
                self.assertEqual(page.one("script").attrs, {})  # inline, so it requests nothing
                expected = "".join(shipped(part) for part in parts)
                self.assertEqual(script_of(page), expected)

    def test_the_policy_lets_the_script_run_by_the_hash_of_its_exact_text(self):
        for path, page in self.pages.items():
            with self.subTest(path):
                self.assertScriptAllowed(page)

    def test_the_policy_is_otherwise_as_it_was_and_only_a_board_with_rows_may_fetch_from_its_own_address(self):
        for path, page in self.pages.items():
            with self.subTest(path):
                policy = page.policy()
                fetches = "filters.js" in PARTS[path]
                self.assertEqual(" connect-src 'self';" in policy, fetches)
                self.assertEqual(re.sub(r" (script|connect)-src [^;]*;", "", policy), POLICY)
                self.assertTrue(policy.startswith("default-src 'none'; script-src 'sha256-"), policy)

    def test_the_not_found_page_and_how_it_works_carry_the_theme_alone_and_no_notice(self):
        """The notice hides what an old board's page holds, and neither page holds a board."""
        for path in (NOT_FOUND, HOW_IT_WORKS):
            with self.subTest(path):
                page = self.pages[path]
                self.assertEqual(PARTS[path], ("theme.js",))
                self.assertEqual([element for element in page.all() if element.attrs.get("id") == NOTICE], [])
                self.assertNotIn("old-board", script_of(page))

    def test_a_script_changed_without_its_hash_in_the_policy_fails_the_check(self):
        """The build computes the hash, so a change to the script's text alone keeps them in step. A change that put
        the old hash in the policy, such as text added around the script in a template, would leave the browser to
        refuse the script, and the check above fails on it."""
        page = self.pages[BOARD]
        changed = Page(page.html.replace("<script>", "<script> ", 1))
        self.assertNotEqual(script_of(changed), script_of(page))
        self.assertEqual(changed.policy(), page.policy())
        with self.assertRaises(AssertionError):
            self.assertScriptAllowed(changed)


class WithoutScripts(BuildTest):
    """With scripts turned off a page is the fresh page: its board, or the list, and its publish time in plain text."""

    def setUp(self):
        super().setUp()
        self.pages = self.build_pages()

    def test_with_scripts_off_a_boards_page_holds_its_rows_and_its_publish_time_and_no_notice(self):
        for path, day in ((BOARD, NEWEST), (board_day_page(NEWEST), NEWEST), (board_day_page(OLDER), OLDER)):
            with self.subTest(path):
                page, board = self.pages[path], read_json(self.board_file(day))
                self.assertEqual(len(page.rows()), len(board["rows"]))
                (published,) = [time for time in page.all("time") if time.attrs["datetime"] == board["published_at"]]
                self.assertIn(f"Published {published.text()}.", page.body_text())
                self.assertNoNotice(page)

    def test_with_scripts_off_the_list_holds_every_board_day_and_no_notice(self):
        page = self.pages[DAYS]
        days = [entry["board_day"] for entry in read_json(self.index)["board_days"]]
        self.assertEqual(
            sorted(
                link.attrs["href"] for link in page.one("main").all("a") if link.attrs["href"].startswith("/days/2")
            ),
            sorted(f"/days/{day}/" for day in days),
        )
        self.assertNoNotice(page)

    def assertNoNotice(self, page: Page):
        """The notice is hidden and holds no words, so no word of it is on a fresh page."""
        notice = by_id(page, NOTICE)
        self.assertIn("hidden", notice.attrs)
        self.assertEqual(notice.text(), "")
        for words in ("The newest board is", "No board is shown", "none has come out since"):
            self.assertNotIn(words, page.body_text())

    def test_from_7_days_the_stylesheet_hides_the_main_content_which_holds_the_board_or_the_list(self):
        """What is in <main> is hidden, and <main> stays, so the page keeps its main landmark: Lighthouse's
        accessibility check fails a page with none."""
        for path in CARRIERS:
            with self.subTest(path):
                page = self.pages[path]
                style = page.one("style").text()
                self.assertIn(":root[data-withheld] main > * { display: none; }", style)
                self.assertNotRegex(style, r"data-withheld\] main\s*\{")
                main = page.one("main")
                inside = set(main.all())
                # The list's days, a board's rows, the Baseline page's chart, or, for the example's earlier board,
                # which has none, its message.
                held = (
                    [link for link in main.all("a") if link.attrs["href"].startswith("/days/2")]
                    if path == DAYS
                    else page.all("figure")
                    if path == BASELINE
                    else page.rows() or [element for element in main.all("div") if "message" in element.classes()]
                )
                self.assertTrue(held)
                self.assertLessEqual(set(held), inside, "the board's rows, or the list, should be in <main>")
                self.assertNotIn(by_id(page, NOTICE), inside)

    def test_the_script_is_in_the_head_and_the_notice_before_everything_it_could_move(self):
        """The script runs in the head, before the notice is parsed, and fills the notice as the parser inserts it
        (above). The notice comes right after the site's bar, before the date, the strip, and the main content, so
        everything the notice could push down is parsed after it is filled, and nothing on the screen moves when it
        is shown."""
        for path in CARRIERS:
            with self.subTest(path):
                page = self.pages[path]
                head, body = page.html.split("<body>", 1)
                self.assertIn("<script>", head)
                self.assertNotIn("<script", body)
                order = page.all()
                notice, site = by_id(page, NOTICE), page.one("header")
                self.assertEqual(site.classes(), ["site"])
                after_site = order[order.index(site) + len(site.all()) + 1 :]  # what follows the bar and all it holds
                self.assertIs(
                    [element for element in after_site if element.tag in ("p", "nav", "main", "h1")][0], notice
                )
                (strip,) = [nav for nav in page.all("nav") if "strip" in nav.classes()]
                for later in (page.one("h1"), strip, page.one("main")):
                    self.assertLess(order.index(notice), order.index(later))


if __name__ == "__main__":
    unittest.main()
