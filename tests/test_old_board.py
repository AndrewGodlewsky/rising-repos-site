"""The notice of an old board (AndrewGodlewsky/RisingRepos#56).

Every board day's page, the root among them, and the list of board days carry one script. It compares the newest
board's publish time with the reader's clock when the page is opened, so it needs no new build: from 26 hours the page
says how old the newest board is, and from 7 days it shows no board and says why. Younger than 26 hours, or with scripts
turned off, the page is as it was built.

These tests lift the script out of a built page, exactly as the page holds it, and hand it to Node with a clock of
their choosing (tests/run_page_script.js). Without Node they fail, never skip.
"""

import base64
import hashlib
import json
import re
import shutil
import subprocess
import unittest
from datetime import datetime, timedelta, timezone

from helpers import ROOT, BuildTest, Page, read_json

from sitebuild import BOARD, DAYS, NOT_FOUND, board_day_page

NODE = shutil.which("node")
RUNNER = ROOT / "tests" / "run_page_script.js"

NEWEST, OLDER = "2026-11-09", "2026-11-08"
"""The example's two board days, newest first."""

PUBLISHED = datetime(2026, 11, 10, 0, 41, 7, tzinfo=timezone.utc)
"""When the example's newest board was published: the moment every page's script measures from."""

CARRIERS = (BOARD, board_day_page(NEWEST), board_day_page(OLDER), DAYS)
"""The pages that carry the notice, as the example builds them: the root, the newest and the earlier board day's
pages, and the list."""

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
"""Everything the script may read or write, as tests/run_page_script.js records it: the notice's two attributes, the
text of its two parts, its hidden attribute, and one attribute on the root element. It reads no other value, so none an
owner wrote, and it writes text, never markup."""

POLICY = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"
"""Each page's Content-Security-Policy before the script: the not-found page's still, and every other page's but for
the one directive that lets the script run."""

HOUR, DAY, SECOND = timedelta(hours=1), timedelta(days=1), timedelta(seconds=1)


def script_of(page: Page) -> str:
    """The text of the page's one script element, exactly as the page holds it."""
    (text,) = re.findall(r"<script>(.*?)</script>", page.html, flags=re.DOTALL)
    return text


def policy_of(page: Page) -> str:
    (policy,) = [
        element.attrs["content"]
        for element in page.all("meta")
        if element.attrs.get("http-equiv") == "Content-Security-Policy"
    ]
    return policy


def directives(policy: str) -> dict[str, list[str]]:
    """A policy's directives, by name, each with its sources."""
    return {name: sources for name, *sources in (part.split() for part in policy.split(";") if part.strip())}


def by_id(page: Page, name: str):
    (element,) = [element for element in page.all() if element.attrs.get("id") == name]
    return element


def stand_ins(page: Page) -> dict:
    """The elements the script may look up, as the built page has them, each by its id: its attributes and its text."""
    return {
        name: {
            "attributes": {key: value or "" for key, value in by_id(page, name).attrs.items()},
            "text": by_id(page, name).text(),
        }
        for name in (NOTICE, TITLE, TEXT)
    }


def run(page: Page, *moments: datetime) -> list[dict]:
    """Run the page's script under Node once for each of `moments`, with the clock at that moment, and return what each
    run did."""
    return run_with(page, [(moment, None) for moment in moments])


def run_with(page: Page, cases: list[tuple[datetime, dict | None]]) -> list[dict]:
    """Run the page's script under Node once for each case: the clock's moment, and attributes that replace the
    notice's, as a page that held others would have them, or None to keep the page's own."""
    if NODE is None:
        raise AssertionError("Node is needed to run the page's script, and none is on the PATH.")
    root = {"attributes": dict(page.one("html").attrs)}
    runs = []
    for moment, notice in cases:
        elements = stand_ins(page)
        if notice is not None:
            elements[NOTICE]["attributes"] = notice
        runs.append({"now": round(moment.timestamp() * 1000), "elements": elements, "root": root})
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
        """Each run left the page as it was built: the notice hidden and empty, and the root as it was."""
        for outcome in outcomes:
            self.assertIsNone(outcome["error"])
            self.assertEqual(outcome["elements"], stand_ins(page))
            self.assertEqual(outcome["root"], dict(page.one("html").attrs))
            self.assertLessEqual(set(outcome["operations"]), TOUCHES)

    def assertNotice(self, outcome: dict, words: dict, *, hides_boards: bool):
        self.assertIsNone(outcome["error"])
        self.assertLessEqual(set(outcome["operations"]), TOUCHES)
        elements = outcome["elements"]
        self.assertNotIn("hidden", elements[NOTICE]["attributes"])
        self.assertEqual({name: elements[name]["text"] for name in (TITLE, TEXT)}, words)
        self.assertEqual("data-withheld" in outcome["root"], hides_boards)

    def test_each_page_with_a_board_or_the_list_carries_the_newest_boards_day_and_publish_time_for_the_script(self):
        """An earlier board day's page and the list measure from the newest board too."""
        for path in CARRIERS:
            with self.subTest(path):
                notice = by_id(self.pages[path], NOTICE)
                self.assertEqual(notice.attrs["data-newest-board-day"], NEWEST)
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
            for outcome, words in zip(outcomes, cases.values()):
                with self.subTest(path, age=words):
                    self.assertNotice(outcome, stale(words), hides_boards=False)

    def test_from_7_days_the_page_shows_no_board_and_says_why(self):
        cases = {7 * DAY: "7 days", 10 * DAY: "10 days", 400 * DAY: "400 days"}
        for path in CARRIERS:
            page = self.pages[path]
            outcomes = run(page, *(PUBLISHED + age for age in cases))
            for outcome, words in zip(outcomes, cases.values()):
                with self.subTest(path, age=words):
                    self.assertNotice(outcome, withheld(words), hides_boards=True)

    def test_a_malformed_or_impossible_publish_time_or_board_day_changes_nothing(self):
        built = {key: value or "" for key, value in by_id(self.pages[BOARD], NOTICE).attrs.items()}
        unreadable = {
            "data-newest-published-at": [
                "",
                "not a time",
                "2026-11-10 00:41:07Z",
                "2026-11-10T00:41:07+00:00",
                "2026-11-10T00:41:07.000Z",
                "2026-11-10T00:41Z",
                "2026-13-10T00:41:07Z",
                "2026-02-30T00:41:07Z",
                "2026-11-10T24:00:00Z",
            ],
            "data-newest-board-day": ["", "9 November 2026", "2026-11-9", "2026-13-09", "2026-11-31"],
        }
        notices = []  # each value in place of the page's own, and each attribute left out (None)
        for name, values in unreadable.items():
            for value in [*values, None]:
                attributes = {key: text for key, text in built.items() if key != name}
                if value is not None:
                    attributes[name] = value
                notices.append((name, value, attributes))
        for path in CARRIERS:
            page = self.pages[path]
            outcomes = run_with(page, [(PUBLISHED + 30 * DAY, attributes) for _, _, attributes in notices])
            for (name, value, attributes), outcome in zip(notices, outcomes, strict=True):
                with self.subTest(path, name=name, value=value):
                    self.assertIsNone(outcome["error"])
                    self.assertEqual(outcome["elements"][NOTICE]["attributes"], attributes)
                    self.assertEqual([outcome["elements"][part]["text"] for part in (TITLE, TEXT)], ["", ""])
                    self.assertEqual(outcome["root"], dict(page.one("html").attrs))
                    self.assertLessEqual(set(outcome["operations"]), TOUCHES)

    def test_the_script_reads_only_the_notices_two_attributes_and_writes_only_its_text_and_one_attribute(self):
        """It inserts no value an owner wrote, makes no request, stores nothing, and sets no cookie: the context it
        runs in has no way to make a request, and a script that reached for one would throw."""
        page = self.pages[BOARD]
        outcomes = run(page, PUBLISHED, PUBLISHED + 30 * HOUR, PUBLISHED + 10 * DAY)
        for outcome in outcomes:
            self.assertIsNone(outcome["error"])
            self.assertLessEqual(set(outcome["operations"]), TOUCHES)
        self.assertEqual(
            sorted(set(outcomes[-1]["operations"])),
            sorted(TOUCHES),
            "a run from 7 days should touch each thing the script may touch",
        )
        self.assertNotRegex(script_of(page), r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|cookie|Storage")


class ThePolicy(BuildTest):
    """The Content-Security-Policy lets the one script run by the hash of its text, and nothing else in it changes."""

    def setUp(self):
        super().setUp()
        self.pages = self.build_pages()

    def assertScriptAllowed(self, page: Page):
        """The policy's `script-src` names one source: the SHA-256 of the exact text of the page's one script."""
        digest = base64.b64encode(hashlib.sha256(script_of(page).encode("utf-8")).digest()).decode("ascii")
        self.assertEqual(directives(policy_of(page))["script-src"], [f"'sha256-{digest}'"])

    def test_each_page_with_a_board_or_the_list_carries_one_script_and_the_same_one(self):
        scripts = set()
        for path in CARRIERS:
            with self.subTest(path):
                page = self.pages[path]
                self.assertEqual(len(page.all("script")), 1)
                self.assertEqual(page.one("script").attrs, {})  # inline, so it requests nothing
                scripts.add(script_of(page))
        self.assertEqual(len(scripts), 1)

    def test_the_policy_lets_the_script_run_by_the_hash_of_its_exact_text(self):
        for path in CARRIERS:
            with self.subTest(path):
                self.assertScriptAllowed(self.pages[path])

    def test_the_policy_is_otherwise_as_it_was(self):
        for path in CARRIERS:
            with self.subTest(path):
                policy = policy_of(self.pages[path])
                self.assertEqual(re.sub(r" script-src [^;]*;", "", policy), POLICY)
                self.assertTrue(policy.startswith("default-src 'none'; script-src 'sha256-"), policy)

    def test_the_not_found_page_has_no_script_and_a_policy_that_forbids_every_script(self):
        page = self.pages[NOT_FOUND]
        self.assertEqual(page.all("script"), [])
        self.assertEqual(policy_of(page), POLICY)
        self.assertEqual([element for element in page.all() if element.attrs.get("id") == NOTICE], [])

    def test_a_script_changed_without_its_hash_in_the_policy_fails_the_check(self):
        """The build computes the hash, so a change to the script's text alone keeps them in step. A change that put
        the old hash in the policy, such as text added around the script in a template, would leave the browser to
        refuse the script, and the check above fails on it."""
        page = self.pages[BOARD]
        changed = Page(page.html.replace("<script>", "<script> ", 1))
        self.assertNotEqual(script_of(changed), script_of(page))
        self.assertEqual(policy_of(changed), policy_of(page))
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
        self.assertEqual(len(page.one("main").all("li")), len(read_json(self.index)["board_days"]))
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
                # The list's days, a board's rows, or, for the example's earlier board, which has none, its message.
                held = page.all("li") if path == DAYS else page.rows() or [page.one("main").all("div")[0]]
                self.assertTrue(held)
                self.assertLessEqual(set(held), inside, "the board's rows, or the list, should be in <main>")
                self.assertNotIn(by_id(page, NOTICE), inside)

    def test_the_script_runs_right_after_the_notice_and_before_anything_that_its_notice_could_move(self):
        """The notice comes right after the site's line, and the script right after the notice, so everything the
        notice could push down, the date, the board's facts, the strip, and the main content, is parsed after the
        script has run, and nothing on the screen moves when the notice is shown."""
        for path in CARRIERS:
            with self.subTest(path):
                page = self.pages[path]
                notice, script = by_id(page, NOTICE), page.one("script")
                band = page.one("header").all()[0]  # the band's .wrap
                parts = [child for child in band.children if not isinstance(child, str)]
                self.assertEqual(parts[1:3], [notice, script])
                self.assertEqual(parts[0].classes(), ["site"])
                order = page.all()
                (strip,) = [nav for nav in page.all("nav") if "strip" in nav.classes()]
                for later in (page.one("h1"), strip, page.one("main")):
                    self.assertLess(order.index(script), order.index(later))


if __name__ == "__main__":
    unittest.main()
