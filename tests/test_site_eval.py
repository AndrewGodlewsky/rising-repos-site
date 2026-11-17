"""The site eval turns Lighthouse's reports into numbers, judges each against its limit, and says in the job's
summary which number failed or could not be measured.

Each test runs the eval with tests/fake_lighthouse.py in Lighthouse's place, so no test touches the network,
on reports the test makes up or on one that Lighthouse wrote, cut down to the parts the eval reads:
tests/fixtures/site-eval/phone-report.json, for the preview's first page on 2026-11-12, and
tests/fixtures/site-eval/live-phone-report.json, for the live first page on 2026-11-17, in the eval's first
run there (run 44019660473, its report 1-phone-1.json), with both of its network rows as Lighthouse wrote
them. That run did not ask for the inspector-issues audit, so tests/fixtures/site-eval/live-phone-issues.json
holds that audit alone, from the first run that asked for it at the same address (run 44025134536, its report
1-phone-1.json). What reaches the network in the workflow, main's head and the site's page, is handed to the
eval as a function, which each test replaces.
"""

import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from evals.site import measure
from helpers import EXAMPLE, ROOT, build, read_json
from sitebuild import BOARD, contract

FAKE = ROOT / "tests" / "fake_lighthouse.py"
RECORDED = ROOT / "tests" / "fixtures" / "site-eval" / "phone-report.json"
LIVE = ROOT / "tests" / "fixtures" / "site-eval" / "live-phone-report.json"
LIVE_ISSUES = ROOT / "tests" / "fixtures" / "site-eval" / "live-phone-issues.json"
SITE_PAGE = "https://risingrepos.com/"
TAG = "https://static.cloudflareinsights.com/beacon.min.js/vce701823e78c4301a35b7e07294d87301792088814092"
"""The address of the analytics script that the host adds to the live page, as LIVE's second row gives it."""
COMMIT = "a" * 40
NEWER = "b" * 40
NOW = datetime(2026, 11, 12, 16, 0, 0, tzinfo=UTC)
CHROME = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/156.0.0.0 Safari/537.36"
PROFILES = ("phone", "desktop")

LIMITS = {
    profile: {
        "performance": {"limit": 90, "reason": "made up"},
        "accessibility": {"limit": 90, "reason": "made up"},
        "largest_contentful_paint": {"limit": 2.5, "reason": "made up"},
        "cumulative_layout_shift": {"limit": 0.1, "reason": "made up"},
        "transfer_size": {"limit": 100_000, "reason": "made up"},
        "requests": {"limit": 2, "reason": "made up"},
    }
    for profile in PROFILES
}
"""Limits for the tests, the same on both profiles: the ones in evals/site/limits.json move with the page."""


def report(
    *, performance=0.98, accessibility=1.0, lcp_ms=1234.0, cls=0.0, transfer=74_512, requests=1, rows=None, issues=None
) -> dict:
    """A Lighthouse report with only the parts the eval reads, holding the numbers given. `rows` replaces the
    `requests` rows of network-requests, and `issues`, when given, is the report's inspector-issues audit."""
    made = {
        "lighthouseVersion": "13.5.0",
        "environment": {"hostUserAgent": CHROME},
        "categories": {"performance": {"score": performance}, "accessibility": {"score": accessibility}},
        "audits": {
            "largest-contentful-paint": {"numericValue": lcp_ms},
            "cumulative-layout-shift": {"numericValue": cls},
            "total-byte-weight": {"numericValue": transfer},
            "network-requests": {"details": {"items": [{"url": SITE_PAGE}] * requests if rows is None else rows}},
        },
    }
    if issues is not None:
        made["audits"]["inspector-issues"] = issues
    return made


def answered(url: str, resource_type: str, *, status: int = 200, transfer: int = 2_000, size: int = 6_000) -> dict:
    """A network row as Lighthouse writes one for a request that the page sent and that was answered."""
    return {
        "url": url,
        "protocol": "h2",
        "transferSize": transfer,
        "resourceSize": size,
        "statusCode": status,
        "mimeType": "application/octet-stream",
        "resourceType": resource_type,
    }


def unanswered(url: str, resource_type: str = "Script") -> dict:
    """A network row as Lighthouse writes one for a request that ended before any answer came: no status, no
    protocol, and no bytes. A request the page's policy refused and one that failed on the network both look so."""
    return {
        "url": url,
        "protocol": "",
        "transferSize": 0,
        "resourceSize": 0,
        "statusCode": -1,
        "mimeType": "",
        "resourceType": resource_type,
    }


def policy_issues(*refused: str) -> dict:
    """Lighthouse's inspector-issues audit in the form its source gives it (core/audits/dobetterweb/
    inspector-issues.js at v13.5.0), when Chrome said the page's content security policy refused each address in
    `refused`."""
    sub_items = {"type": "subitems", "items": [{"url": address} for address in refused]}
    return {
        "id": "inspector-issues",
        "score": 0 if refused else 1,
        "scoreDisplayMode": "binary",
        "details": {
            "type": "table",
            "items": [{"issueType": "Content security policy", "subItems": sub_items}] if refused else [],
        },
    }


def live(*, issues: dict | None = None) -> dict:
    """LIVE's report, which holds no inspector-issues audit, with `issues` as that audit when it is given."""
    recorded = read_json(LIVE)
    if issues is not None:
        recorded["audits"]["inspector-issues"] = issues
    return recorded


def page_stating(board_day: str, published_at: str) -> str:
    return (
        f'<!doctype html><html><head><meta name="rr:board-date" content="{board_day}">'
        f'<meta name="rr:published-at" content="{published_at}"></head><body></body></html>'
    )


def newest_board_of_the_example() -> tuple[str, str]:
    board = contract.latest_board(EXAMPLE)
    return board["board_day"], board["published_at"]


def never(*_):
    raise AssertionError("the eval reached for the network")


class EvalTest(unittest.TestCase):
    """Runs the eval with the stand-in for Lighthouse, answering from a plan that each test writes."""

    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.calls = self.folder / "calls.jsonl"
        self.plan_file = self.folder / "plan.json"
        self.enterContext(
            mock.patch.dict(
                os.environ, {"FAKE_LIGHTHOUSE_CALLS": str(self.calls), "FAKE_LIGHTHOUSE_PLAN": str(self.plan_file)}
            )
        )
        self.plan(phone=[report()], desktop=[report(performance=1.0, lcp_ms=600.0)])
        self.pauses = []

    def plan(self, *, phone: list, desktop: list | None = None):
        """What each run answers, in order, as tests/fake_lighthouse.py says. A report on its own is a run that
        writes it and exits 0. The desktop answers as the phone does unless it is given answers of its own."""
        answers = {"phone": phone, "desktop": phone if desktop is None else desktop}
        plan = {profile: [{"report": a} if "audits" in a else a for a in runs] for profile, runs in answers.items()}
        self.plan_file.write_text(json.dumps(plan), encoding="utf-8")

    def lighthouse_calls(self) -> list[list[str]]:
        if not self.calls.exists():
            return []
        return [json.loads(line) for line in self.calls.read_text(encoding="utf-8").splitlines()]

    def evaluate(self, **options) -> "measure.Outcome":
        settings = {
            "lighthouse": [sys.executable, str(FAKE)],
            "out": self.folder / "out",
            "limits": LIMITS,
            "accepted": {},
            "head_of_main": never,
            "read_page": never,
            "pause": self.pauses.append,
            "now": lambda: NOW,
        }
        return measure.evaluate(**{**settings, **options})

    def row(self, outcome: "measure.Outcome", name: str, profile: str = "phone") -> str:
        """The summary's table row for the measure called `name` on `profile`, for the first page."""
        heading = f"### `/` on {'a phone' if profile == 'phone' else 'a desktop'}"
        section = outcome.summary.split(heading, 1)[1].split("###", 1)[0]
        (line,) = [line for line in section.splitlines() if line.startswith(f"| {name} |")]
        return line


class TheNumbers(EvalTest):
    def test_each_profile_reports_both_scores_lcp_cls_the_transfer_size_and_the_requests(self):
        self.plan(phone=[report()], desktop=[report(performance=1.0, lcp_ms=600.0, transfer=74_000)])
        outcome = self.evaluate()
        self.assertTrue(outcome.passed, outcome.problems)
        medians = {
            profile: {key: value["median"] for key, value in outcome.results["pages"]["/"][profile].items()}
            for profile in PROFILES
        }
        self.assertEqual(
            medians,
            {
                "phone": {
                    "performance": 98,
                    "accessibility": 100,
                    "largest_contentful_paint": 1.23,
                    "cumulative_layout_shift": 0.0,
                    "transfer_size": 74_512,
                    "requests": 1,
                },
                "desktop": {
                    "performance": 100,
                    "accessibility": 100,
                    "largest_contentful_paint": 0.6,
                    "cumulative_layout_shift": 0.0,
                    "transfer_size": 74_000,
                    "requests": 1,
                },
            },
        )

    def test_a_report_lighthouse_wrote_for_the_preview_gives_its_numbers(self):
        self.plan(phone=[read_json(RECORDED)], desktop=[report()])
        phone = self.evaluate().results["pages"]["/"]["phone"]
        self.assertEqual(
            {key: value["median"] for key, value in phone.items()},
            {
                "performance": 93,
                "accessibility": 100,
                "largest_contentful_paint": 1.54,
                "cumulative_layout_shift": 0,
                "transfer_size": 74_384,
                "requests": 1,
            },
        )

    def test_each_number_is_the_median_of_five_runs_and_the_summary_gives_their_range(self):
        self.plan(phone=[report(lcp_ms=ms) for ms in (1500, 1100, 1300, 1900, 1200)])
        outcome = self.evaluate()
        lcp = outcome.results["pages"]["/"]["phone"]["largest_contentful_paint"]
        self.assertEqual(lcp, {"median": 1.3, "runs": [1.5, 1.1, 1.3, 1.9, 1.2]})
        self.assertEqual(
            self.row(outcome, "Largest Contentful Paint"),
            "| Largest Contentful Paint | 1.30 s | 1.10 s to 1.90 s | none | at most 2.50 s | pass |",
        )
        self.assertEqual(outcome.results["runs"], 5)
        self.assertEqual(len(self.lighthouse_calls()), 10)

    def test_lighthouse_measures_the_sites_first_page_on_a_phone_and_on_a_desktop_without_error_reporting(self):
        self.evaluate()
        calls = self.lighthouse_calls()
        for arguments in calls:
            self.assertEqual(arguments[0], SITE_PAGE)
            for option in (
                "--output=json",
                "--only-categories=performance,accessibility",
                "--no-enable-error-reporting",
            ):
                self.assertIn(option, arguments)
        self.assertEqual(["--preset=desktop" in arguments for arguments in calls], [False] * 5 + [True] * 5)

    def test_each_run_also_asks_lighthouse_for_inspector_issues_outside_its_two_categories(self):
        self.evaluate()
        for arguments in self.lighthouse_calls():
            self.assertIn("--only-categories=performance,accessibility", arguments)
            self.assertIn("--only-audits=inspector-issues", arguments)

    def test_the_results_record_the_commit_the_date_the_run_and_the_tools(self):
        outcome = self.evaluate(
            commit=COMMIT,
            head_of_main=lambda: COMMIT,
            read_page=lambda address: page_stating(*newest_board_of_the_example()),
            data=EXAMPLE,
            run="https://github.com/AndrewGodlewsky/rising-repos-site/actions/runs/1",
        )
        results = outcome.results
        self.assertEqual(
            {key: results[key] for key in ("commit", "measured_at", "run", "lighthouse", "chrome", "runs", "base")},
            {
                "commit": COMMIT,
                "measured_at": "2026-11-12T16:00:00Z",
                "run": "https://github.com/AndrewGodlewsky/rising-repos-site/actions/runs/1",
                "lighthouse": "13.5.0",
                "chrome": "156",
                "runs": 5,
                "base": "https://risingrepos.com",
            },
        )


class TheLimits(EvalTest):
    def test_the_summary_shows_each_number_beside_the_accepted_one_and_its_limit(self):
        earlier = self.evaluate().results
        earlier["pages"]["/"]["phone"]["performance"] = {"median": 97, "runs": [97] * 5}
        earlier["commit"] = COMMIT
        outcome = self.evaluate(accepted=earlier, out=self.folder / "again")
        self.assertEqual(
            self.row(outcome, "Performance score"), "| Performance score | 98 | 98 to 98 | 97 | at least 90 | pass |"
        )
        self.assertEqual(
            self.row(outcome, "Cumulative Layout Shift"),
            "| Cumulative Layout Shift | 0.000 | 0.000 to 0.000 | 0.000 | at most 0.100 | pass |",
        )
        self.assertEqual(
            self.row(outcome, "Total transfer size"),
            "| Total transfer size | 74,512 bytes | 74,512 bytes to 74,512 bytes | 74,512 bytes "
            "| at most 100,000 bytes | pass |",
        )
        self.assertEqual(self.row(outcome, "Requests", "desktop"), "| Requests | 1 | 1 to 1 | 1 | at most 2 | pass |")
        self.assertIn(f"The accepted numbers were measured on 2026-11-12, at `{COMMIT}`.", outcome.summary)

    def test_a_number_over_its_limit_fails_the_eval_and_the_summary_names_it(self):
        self.plan(phone=[report(lcp_ms=3100.0)], desktop=[report(transfer=100_001)])
        outcome = self.evaluate()
        self.assertFalse(outcome.passed)
        self.assertEqual(
            outcome.problems,
            [
                "Phone, `/`: Largest Contentful Paint 3.10 s is over its limit of 2.50 s",
                "Desktop, `/`: Total transfer size 100,001 bytes is over its limit of 100,000 bytes",
            ],
        )
        self.assertEqual(
            self.row(outcome, "Largest Contentful Paint"),
            "| Largest Contentful Paint | 3.10 s | 3.10 s to 3.10 s | none | at most 2.50 s | **fail** |",
        )
        for problem in outcome.problems:
            self.assertIn(f"- {problem}", outcome.summary)

    def test_a_score_under_its_limit_fails_the_eval(self):
        self.plan(phone=[report(accessibility=0.89)], desktop=[report()])
        outcome = self.evaluate()
        self.assertFalse(outcome.passed)
        self.assertEqual(outcome.problems, ["Phone, `/`: Accessibility score 89 is under its limit of 90"])

    def test_a_number_at_its_limit_passes(self):
        self.plan(
            phone=[report(performance=0.9, accessibility=0.9, lcp_ms=2500.0, cls=0.1, transfer=100_000, requests=2)]
        )
        outcome = self.evaluate()
        self.assertTrue(outcome.passed, outcome.problems)


class TheRequestsCounted(EvalTest):
    """Requests is how many requests the page sent. The eval drops a network row only if the report's
    inspector-issues audit names that very address as refused by the page's content security policy, and the row
    shows no answer and no bytes. Any other row counts, whatever its host, and so does a row or an audit that the
    eval cannot read as that rule needs."""

    PAGE = answered(SITE_PAGE, "Document", transfer=39_939, size=213_544)
    LEFT_OUT = (
        "Lighthouse's `inspector-issues` audit lists it as refused by the page's content security policy, and its "
        "row shows no answer and no bytes"
    )

    def requests(self, rows, issues=None) -> int:
        """The median of Requests on the phone, for five runs that each report `rows` and `issues`, once it is
        checked that the summary names no request as not counted."""
        self.calls.unlink(missing_ok=True)
        self.plan(phone=[report(rows=rows, issues=issues)], desktop=[report()])
        outcome = self.evaluate()
        self.assertNotIn("Not counted", outcome.summary)
        return outcome.results["pages"]["/"]["phone"]["requests"]["median"]

    def section(self, outcome: "measure.Outcome", profile: str) -> str:
        heading = f"### `/` on {'a phone' if profile == 'phone' else 'a desktop'}"
        return outcome.summary.split(heading, 1)[1].split("###", 1)[0]

    def test_the_first_live_runs_rows_give_two_requests_as_its_reports_hold_no_inspector_issues_audit(self):
        self.plan(phone=[live()])
        outcome = self.evaluate()
        for profile in PROFILES:
            with self.subTest(profile):
                self.assertEqual(
                    {key: value["median"] for key, value in outcome.results["pages"]["/"][profile].items()},
                    {
                        "performance": 98,
                        "accessibility": 100,
                        "largest_contentful_paint": 1.78,
                        "cumulative_layout_shift": 0,
                        "transfer_size": 39_939,
                        "requests": 2,
                    },
                )
        self.assertNotIn("Not counted", outcome.summary)

    def test_the_first_live_runs_rows_give_one_request_with_the_audit_a_later_run_there_recorded(self):
        self.plan(phone=[live(issues=read_json(LIVE_ISSUES))])
        outcome = self.evaluate()
        for profile in PROFILES:
            with self.subTest(profile):
                self.assertEqual(outcome.results["pages"]["/"][profile]["requests"]["median"], 1)
                self.assertIn(f"- `{TAG}`, in every run: {self.LEFT_OUT}.", self.section(outcome, profile))

    def test_the_made_up_audit_is_the_one_lighthouse_wrote_for_the_live_page(self):
        self.assertEqual(policy_issues(TAG), read_json(LIVE_ISSUES))

    def test_the_summary_names_each_request_left_out_and_says_why(self):
        other = "https://example.com/widget.js"
        rows = [self.PAGE, unanswered(TAG), unanswered(other)]
        self.plan(phone=[report(rows=rows, issues=policy_issues(TAG, other))], desktop=[report()])
        outcome = self.evaluate()
        phone = self.section(outcome, "phone")
        self.assertIn("| Requests | 1 | 1 to 1 | none | at most 2 | pass |", phone)
        self.assertIn(
            "\nNot counted in Requests, because the page never sent them:\n\n"
            f"- `{TAG}`, in every run: {self.LEFT_OUT}.\n"
            f"- `{other}`, in every run: {self.LEFT_OUT}.\n",
            phone,
        )
        self.assertNotIn("Not counted", self.section(outcome, "desktop"))

    def test_the_summary_says_in_which_runs_a_request_was_left_out(self):
        refused, unread = live(issues=policy_issues(TAG)), live()
        for runs, words in (
            ([unread, refused, unread, unread, unread], "in run 2"),
            ([refused, unread, refused, unread, unread], "in runs 1 and 3"),
            ([refused, refused, unread, refused, unread], "in runs 1, 2 and 4"),
        ):
            with self.subTest(words):
                self.calls.unlink(missing_ok=True)
                self.plan(phone=runs, desktop=[report()])
                outcome = self.evaluate()
                self.assertIn(f"- `{TAG}`, {words}: {self.LEFT_OUT}.", self.section(outcome, "phone"))

    def test_a_script_that_was_sent_counts(self):
        self.assertEqual(self.requests([self.PAGE, answered("https://cdn.example.com/app.js", "Script")]), 2)

    def test_an_image_that_was_sent_counts(self):
        self.assertEqual(self.requests([self.PAGE, answered("https://images.example.org/board.png", "Image")]), 2)

    def test_a_request_to_cloudflares_analytics_host_that_was_sent_counts(self):
        self.assertEqual(self.requests([self.PAGE, answered(TAG, "Script")], policy_issues()), 2)

    def test_a_request_that_broke_only_a_report_only_policy_and_was_answered_counts(self):
        # Chrome reports such a request as a policy issue too, but sends it, so its row has an answer.
        self.assertEqual(self.requests([self.PAGE, answered(TAG, "Script")], policy_issues(TAG)), 2)

    def test_a_request_that_failed_on_the_network_counts(self):
        failed = unanswered("https://api.example.com/data.json", "Fetch")
        self.assertEqual(self.requests([self.PAGE, failed]), 2)
        self.assertEqual(self.requests([self.PAGE, failed], policy_issues(TAG)), 2)

    def test_only_the_exact_address_the_audit_lists_is_left_out(self):
        for listed in ("https://static.cloudflareinsights.com", TAG + "/", TAG + "?v=2", TAG.upper()):
            with self.subTest(listed):
                self.assertEqual(self.requests([self.PAGE, unanswered(TAG)], policy_issues(listed)), 2)

    def test_a_row_lacking_a_field_or_holding_an_odd_one_counts(self):
        refused = unanswered(TAG)

        def without(field: str) -> dict:
            return {key: value for key, value in refused.items() if key != field}

        for name, row in (
            ("no status", without("statusCode")),
            ("a status written as text", {**refused, "statusCode": "-1"}),
            ("a status that is a fraction", {**refused, "statusCode": -1.5}),
            ("no transfer size", without("transferSize")),
            ("a transfer size written as text", {**refused, "transferSize": "0"}),
            ("a transfer size that is false", {**refused, "transferSize": False}),
            ("a resource size of null", {**refused, "resourceSize": None}),
            ("some bytes transferred", {**refused, "transferSize": 120}),
            ("some bytes of resource", {**refused, "resourceSize": 64}),
            ("no address", without("url")),
            ("an address that is a number", {**refused, "url": 5}),
            ("a row that is a list", [TAG]),
            ("a row that is text", TAG),
            ("a row of null", None),
        ):
            with self.subTest(name):
                self.assertEqual(self.requests([self.PAGE, row], policy_issues(TAG)), 2)

    def test_a_refused_request_whose_address_the_summary_could_not_print_counts(self):
        for address in (
            "http://static.example.com/a.js",
            "https://example.com/a b.js",
            "https://example.com/`a`.js",
            "https://example.com/a.js\n::warning::made up",
            "https://example.com/a|b.js",
            "https://example.com/it's.js",
        ):
            with self.subTest(address):
                self.assertEqual(self.requests([self.PAGE, unanswered(address)], policy_issues(address)), 2)

    def test_an_inspector_issues_audit_that_failed_or_is_shaped_otherwise_leaves_nothing_out(self):
        listed = policy_issues(TAG)
        row = listed["details"]["items"][0]

        def items(*made_up) -> dict:
            return {**listed, "details": {"type": "table", "items": list(made_up)}}

        def sub_items(made_up) -> dict:
            return items({**row, "subItems": {"type": "subitems", "items": made_up}})

        for name, issues in (
            ("an audit that failed", {"id": "inspector-issues", "score": None, "scoreDisplayMode": "error"}),
            ("details of null", {**listed, "details": None}),
            ("items that are not a list", {**listed, "details": {"type": "table", "items": {"0": row}}}),
            ("an item that is text", items("Content security policy")),
            ("another issue type", items({**row, "issueType": "Mixed content"})),
            ("no sub-items", items({"issueType": "Content security policy"})),
            ("sub-items that are a list", items({**row, "subItems": [{"url": TAG}]})),
            ("sub-items whose items are not a list", sub_items(TAG)),
            ("a sub-item that is text", sub_items([TAG])),
            ("a sub-item address that is a list", sub_items([{"url": [TAG]}])),
            ("an audit that is text", "made up"),
            ("an audit that is a list", [listed]),
        ):
            with self.subTest(name):
                self.assertEqual(self.requests([self.PAGE, unanswered(TAG)], issues), 2)


class AMeasurementThatCouldNotBeMade(EvalTest):
    def assertCouldNotMeasure(self, outcome: "measure.Outcome", reason: str, profile: str = "Phone"):
        self.assertFalse(outcome.passed)
        self.assertIn(f"{profile}, `/`: could not be measured: {reason}", outcome.problems)
        heading = f"### `/` on {'a phone' if profile == 'Phone' else 'a desktop'}"
        self.assertIn(f"{heading}\n\nCould not be measured: {reason}.", outcome.summary)

    def test_a_run_that_lighthouse_reports_an_error_for_fails_the_eval_and_says_which(self):
        failed = {
            **report(performance=None, accessibility=None),
            "runtimeError": {"code": "FAILED_DOCUMENT_REQUEST", "message": "x"},
        }
        self.plan(phone=[report(), failed], desktop=[report()])
        outcome = self.evaluate()
        self.assertCouldNotMeasure(outcome, "run 2 of 5: Lighthouse reported FAILED_DOCUMENT_REQUEST")
        self.assertEqual(len(outcome.problems), 1, "the desktop is still measured and passes")
        self.assertIn("desktop", outcome.results["pages"]["/"])

    def test_an_error_code_that_is_not_a_code_is_not_repeated(self):
        failed = {**report(), "runtimeError": {"code": "<b>made</b> | up", "message": "x"}}
        self.plan(phone=[failed], desktop=[report()])
        self.assertCouldNotMeasure(self.evaluate(), "run 1 of 5: Lighthouse reported an error")

    def test_a_run_that_exits_with_an_error_and_writes_no_report_fails_the_eval(self):
        self.plan(phone=[{"exit": 1}], desktop=[report()])
        self.assertCouldNotMeasure(self.evaluate(), "run 1 of 5: Lighthouse exited with status 1")

    def test_a_run_that_writes_no_report_fails_the_eval(self):
        self.plan(phone=[report()], desktop=[report(), {"exit": 0}])
        self.assertCouldNotMeasure(self.evaluate(), "run 2 of 5: Lighthouse wrote no report", "Desktop")

    def test_a_report_without_one_of_the_numbers_fails_the_eval_and_names_the_number(self):
        incomplete = report()
        del incomplete["audits"]["largest-contentful-paint"]["numericValue"]
        self.plan(phone=[incomplete], desktop=[report()])
        self.assertCouldNotMeasure(self.evaluate(), "run 1 of 5: the report holds no Largest Contentful Paint")

    def test_network_rows_that_are_not_a_list_fail_the_eval_and_name_the_requests(self):
        for rows in ("made up", {"0": {"url": SITE_PAGE}}):
            with self.subTest(rows=rows):
                self.calls.unlink(missing_ok=True)
                self.plan(phone=[report(rows=rows)], desktop=[report()])
                self.assertCouldNotMeasure(self.evaluate(), "run 1 of 5: the report holds no Requests")

    def test_a_report_without_a_score_fails_the_eval_and_names_the_score(self):
        self.plan(phone=[report(performance=None)], desktop=[report()])
        self.assertCouldNotMeasure(self.evaluate(), "run 1 of 5: the report holds no Performance score")

    def test_a_run_that_takes_too_long_fails_the_eval(self):
        self.plan(phone=[{"sleep": 30, "report": report()}], desktop=[report()])
        with mock.patch.object(measure, "RUN_TIMEOUT", 3):
            outcome = self.evaluate()
        self.assertCouldNotMeasure(outcome, "run 1 of 5: Lighthouse did not finish within 3 seconds")

    def test_lighthouse_that_cannot_be_started_fails_the_eval(self):
        outcome = self.evaluate(lighthouse=[str(self.folder / "no-such-program")])
        self.assertCouldNotMeasure(outcome, "run 1 of 5: Lighthouse could not be started")


class TheAddress(EvalTest):
    def test_only_an_https_address_is_measured(self):
        for address in (
            "http://preview.risingrepos.pages.dev/",
            "HTTPS://preview.risingrepos.pages.dev/",
            "javascript:alert(1)",
            "file:///etc/hostname",
            "https://",
            "https:///a-path",
            "https://user@example.com/",
            " https://example.com/",
            "https://example.com/a page",
            "https://example.com/\n::warning::made up",
            "https://example.com/`code`",
            "https://example.com/it's",
            'https://example.com/a"b',
            "https://example.com/a|b",
            "-https://example.com/",
        ):
            with self.subTest(address):
                outcome = self.evaluate(address=address)
                self.assertFalse(outcome.passed)
                self.assertEqual(
                    outcome.problems, ["The address given is not an https address, so nothing was measured"]
                )
                self.assertNotIn(address.strip(), outcome.summary)
                self.assertEqual(self.lighthouse_calls(), [])

    def test_an_address_given_by_hand_is_measured_in_place_of_the_sites_and_compared_by_its_path(self):
        accepted = self.evaluate().results
        self.calls.unlink()
        outcome = self.evaluate(address="https://www.risingrepos.com/", accepted=accepted, out=self.folder / "by-hand")
        self.assertTrue(outcome.passed, outcome.problems)
        self.assertEqual({arguments[0] for arguments in self.lighthouse_calls()}, {"https://www.risingrepos.com/"})
        self.assertEqual(outcome.results["base"], "https://www.risingrepos.com")
        self.assertEqual(
            self.row(outcome, "Performance score"), "| Performance score | 98 | 98 to 98 | 98 | at least 90 | pass |"
        )
        self.assertIn("Measured `https://www.risingrepos.com/`, the address given by hand,", outcome.summary)

    def test_the_summary_shows_an_address_as_code_so_that_none_of_it_is_read_as_markdown(self):
        outcome = self.evaluate(address="https://example.com/a_b*c*[x](https://example.org)")
        self.assertIn(
            "Measured `https://example.com/a_b*c*[x](https://example.org)`, the address given by hand,", outcome.summary
        )
        self.assertIn("### `/a_b*c*[x](https://example.org)` on a phone", outcome.summary)


class AfterADeploy(EvalTest):
    """After a deploy the eval is given the deployed commit. It measures the site only while that commit is
    the head of main, which shows that the deploy uploaded its pages, and once the site states that commit's
    newest board day."""

    def test_nothing_is_measured_once_main_has_moved_on_from_the_deployed_commit(self):
        outcome = self.evaluate(commit=COMMIT, head_of_main=lambda: NEWER)
        self.assertTrue(outcome.passed)
        self.assertEqual(outcome.problems, [])
        self.assertIsNone(outcome.results)
        self.assertIn(
            f"Not measured. `main` has moved on from `{COMMIT}`, whose deploy this run follows, to `{NEWER}`.",
            outcome.summary,
        )
        self.assertEqual(self.lighthouse_calls(), [])

    def test_the_numbers_are_not_judged_when_main_moves_on_while_the_site_is_measured(self):
        heads = iter([COMMIT, NEWER])
        self.plan(phone=[report(lcp_ms=9000.0)])
        outcome = self.evaluate(
            commit=COMMIT,
            head_of_main=lambda: next(heads),
            read_page=lambda address: page_stating(*newest_board_of_the_example()),
            data=EXAMPLE,
        )
        self.assertTrue(outcome.passed)
        self.assertEqual(outcome.problems, [])
        self.assertIsNone(outcome.results)
        self.assertIn(
            f"Not judged. `main` moved on from `{COMMIT}` to `{NEWER}` while the site was measured", outcome.summary
        )

    def test_the_site_is_measured_once_it_states_the_commits_newest_board_day(self):
        day, published = newest_board_of_the_example()
        answers = iter([OSError("made up"), page_stating(day, "2026-01-01T00:00:00Z"), page_stating(day, published)])

        def read_page(address):
            self.assertEqual(address, SITE_PAGE)
            answer = next(answers)
            if isinstance(answer, Exception):
                raise answer
            return answer

        outcome = self.evaluate(commit=COMMIT, head_of_main=lambda: COMMIT, read_page=read_page, data=EXAMPLE)
        self.assertTrue(outcome.passed, outcome.problems)
        self.assertEqual(len(self.pauses), 2)
        self.assertEqual(outcome.results["commit"], COMMIT)
        self.assertIn(f"Measured `{SITE_PAGE}` after the deploy of `{COMMIT}`,", outcome.summary)

    def test_a_site_that_never_states_the_commits_newest_board_day_is_not_measured_and_fails_the_eval(self):
        day, published = newest_board_of_the_example()
        outcome = self.evaluate(
            commit=COMMIT,
            head_of_main=lambda: COMMIT,
            read_page=lambda address: page_stating("2026-01-01", published),
            data=EXAMPLE,
        )
        self.assertFalse(outcome.passed)
        self.assertEqual(
            outcome.problems,
            [
                f"`/` does not state the newest board day of `{COMMIT}`, {day} published at {published}, "
                "so nothing was measured"
            ],
        )
        self.assertEqual(len(self.pauses), measure.SERVED_TRIES - 1)
        self.assertEqual(self.lighthouse_calls(), [])

    def test_a_page_the_build_wrote_from_the_commits_data_is_measured_on_its_first_reading(self):
        built = self.folder / "dist"
        result = build(built, "--data", str(EXAMPLE), "--noindex")
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (built / BOARD).read_text(encoding="utf-8")
        outcome = self.evaluate(
            commit=COMMIT, head_of_main=lambda: COMMIT, read_page=lambda address: page, data=EXAMPLE
        )
        self.assertTrue(outcome.passed, outcome.problems)
        self.assertEqual(self.pauses, [])

    def test_data_the_build_could_not_read_fails_the_eval_and_measures_nothing(self):
        outcome = self.evaluate(commit=COMMIT, head_of_main=lambda: COMMIT, data=self.folder / "no-site-data")
        self.assertFalse(outcome.passed)
        self.assertEqual(
            outcome.problems, ["The deployed commit's newest board day could not be read, so nothing was measured"]
        )
        self.assertEqual(self.lighthouse_calls(), [])

    def test_a_head_of_main_that_cannot_be_read_fails_the_eval(self):
        def unreadable():
            raise measure.CouldNotMeasure("the head of main could not be read")

        outcome = self.evaluate(commit=COMMIT, head_of_main=unreadable)
        self.assertFalse(outcome.passed)
        self.assertEqual(outcome.problems, ["The head of main could not be read, so nothing was measured"])

    def test_a_head_of_main_that_cannot_be_read_after_the_measurement_fails_the_eval(self):
        heads = iter([COMMIT, measure.CouldNotMeasure("the head of main could not be read")])

        def head_of_main():
            head = next(heads)
            if isinstance(head, Exception):
                raise head
            return head

        outcome = self.evaluate(
            commit=COMMIT,
            head_of_main=head_of_main,
            read_page=lambda address: page_stating(*newest_board_of_the_example()),
            data=EXAMPLE,
        )
        self.assertFalse(outcome.passed)
        self.assertEqual(
            outcome.problems,
            ["The head of main could not be read after the measurement, so the numbers were not judged"],
        )


class TheCommand(EvalTest):
    """`python -m evals.site.measure`, as the workflow runs it, with the limits in evals/site/limits.json."""

    def run_command(self, *, address: str = "https://example.com/") -> subprocess.CompletedProcess:
        summary = self.folder / "summary.md"
        summary.write_text("Earlier steps' summary.\n", encoding="utf-8")
        environment = {
            **os.environ,
            "SITE_EVAL_LIGHTHOUSE": shlex.join([sys.executable, str(FAKE)]),
            "SITE_EVAL_ADDRESS": address,
            "SITE_EVAL_COMMIT": "",
            "GITHUB_STEP_SUMMARY": str(summary),
        }
        return subprocess.run(
            [sys.executable, "-m", "evals.site.measure", "--out", str(self.folder / "out")],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )

    def test_it_writes_the_summary_and_the_results_and_fails_naming_a_number_over_its_limit(self):
        self.plan(phone=[report(lcp_ms=60_000.0)], desktop=[report(lcp_ms=500.0, performance=1.0, accessibility=1.0)])
        result = self.run_command()
        self.assertEqual(result.returncode, 1, result.stderr)
        summary = (self.folder / "summary.md").read_text(encoding="utf-8")
        self.assertTrue(summary.startswith("Earlier steps' summary.\n## Site eval\n"), summary[:200])
        self.assertIn("Phone, `/`: Largest Contentful Paint 60.00 s is over its limit of", summary)
        self.assertRegex(
            result.stdout,
            r"(?m)^::error title=Site eval::Phone, `/`: Largest Contentful Paint 60\.00 s is over its limit of ",
        )
        results = read_json(self.folder / "out" / "results.json")
        self.assertEqual(results["pages"]["/"]["phone"]["largest_contentful_paint"]["median"], 60.0)

    def test_it_passes_when_every_number_is_within_its_limit(self):
        self.plan(phone=[report(performance=1.0, accessibility=1.0, lcp_ms=400.0, transfer=1_000, requests=1)])
        result = self.run_command()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("::error", result.stdout)

    def test_nothing_lighthouse_prints_reaches_the_jobs_log_where_github_would_read_it_as_a_command(self):
        self.plan(
            phone=[{"print": "::warning::text a measured page could put in Lighthouse's output", "report": report()}]
        )
        result = self.run_command()
        self.assertNotIn("text a measured page could put", result.stdout + result.stderr)
        logs = sorted((self.folder / "out").glob("*.log"))
        self.assertEqual(len(logs), 10)
        self.assertIn("text a measured page could put", logs[0].read_text(encoding="utf-8"))

    def test_an_address_that_is_not_https_fails_the_command_and_measures_nothing(self):
        result = self.run_command(address="http://example.com/")
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "::error title=Site eval::The address given is not an https address, so nothing was measured", result.stdout
        )
        self.assertEqual(self.lighthouse_calls(), [])


class TheEvalFolder(unittest.TestCase):
    """evals/site/ holds the limits, each with its reason, and the accepted numbers with the run that measured
    them."""

    def test_every_number_on_each_profile_has_a_limit_and_a_reason(self):
        limits = read_json(ROOT / "evals" / "site" / "limits.json")
        self.assertEqual(set(limits), set(PROFILES))
        for profile in PROFILES:
            self.assertEqual(set(limits[profile]), set(measure.MEASURES))
            for key, limit in limits[profile].items():
                with self.subTest(profile=profile, measure=key):
                    self.assertIsInstance(limit["limit"], int | float)
                    self.assertGreater(len(limit["reason"]), 40)

    def test_the_accepted_numbers_say_which_commit_and_run_measured_them_and_when(self):
        accepted = read_json(ROOT / "evals" / "site" / "accepted.json")
        self.assertRegex(accepted["commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(accepted["measured_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertRegex(
            accepted["run"], r"^https://github\.com/AndrewGodlewsky/rising-repos-site/actions/runs/\d+/attempts/\d+$"
        )
        self.assertEqual(accepted["base"], measure.PREVIEW)
        self.assertEqual(set(accepted["pages"]), set(measure.PAGES))
        for page in measure.PAGES:
            for profile in PROFILES:
                with self.subTest(page=page, profile=profile):
                    numbers = accepted["pages"][page][profile]
                    self.assertEqual(set(numbers), set(measure.MEASURES))
                    for value in numbers.values():
                        self.assertEqual(len(value["runs"]), accepted["runs"])


if __name__ == "__main__":
    unittest.main()
