"""The site eval turns Lighthouse's reports into numbers, judges each against its limit, and says in the job's
summary which number failed or could not be measured.

Each test runs the eval with tests/fake_lighthouse.py in Lighthouse's place, so no test touches the network,
on reports the test makes up or on tests/fixtures/site-eval/phone-report.json: a report that Lighthouse wrote
for the preview's first page on 2026-11-12, cut down to the parts the eval reads. What reaches the network in
the workflow, main's head and the preview's page, is handed to the eval as a function, which each test
replaces.
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
from sitebuild import contract

FAKE = ROOT / "tests" / "fake_lighthouse.py"
RECORDED = ROOT / "tests" / "fixtures" / "site-eval" / "phone-report.json"
PREVIEW_PAGE = "https://preview.risingrepos.pages.dev/"
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


def report(*, performance=0.98, accessibility=1.0, lcp_ms=1234.0, cls=0.0, transfer=74_512, requests=1) -> dict:
    """A Lighthouse report with only the parts the eval reads, holding the numbers given."""
    return {
        "lighthouseVersion": "13.5.0",
        "environment": {"hostUserAgent": CHROME},
        "categories": {"performance": {"score": performance}, "accessibility": {"score": accessibility}},
        "audits": {
            "largest-contentful-paint": {"numericValue": lcp_ms},
            "cumulative-layout-shift": {"numericValue": cls},
            "total-byte-weight": {"numericValue": transfer},
            "network-requests": {"details": {"items": [{"url": PREVIEW_PAGE}] * requests}},
        },
    }


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

    def test_lighthouse_measures_the_previews_first_page_on_a_phone_and_on_a_desktop_without_error_reporting(self):
        self.evaluate()
        calls = self.lighthouse_calls()
        for arguments in calls:
            self.assertEqual(arguments[0], PREVIEW_PAGE)
            for option in (
                "--output=json",
                "--only-categories=performance,accessibility",
                "--no-enable-error-reporting",
            ):
                self.assertIn(option, arguments)
        self.assertEqual(["--preset=desktop" in arguments for arguments in calls], [False] * 5 + [True] * 5)

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
                "base": "https://preview.risingrepos.pages.dev",
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

    def test_an_address_given_by_hand_is_measured_in_place_of_the_preview_and_compared_by_its_path(self):
        accepted = self.evaluate().results
        self.calls.unlink()
        outcome = self.evaluate(address="https://risingrepos.com/", accepted=accepted, out=self.folder / "by-hand")
        self.assertTrue(outcome.passed, outcome.problems)
        self.assertEqual({arguments[0] for arguments in self.lighthouse_calls()}, {"https://risingrepos.com/"})
        self.assertEqual(outcome.results["base"], "https://risingrepos.com")
        self.assertEqual(
            self.row(outcome, "Performance score"), "| Performance score | 98 | 98 to 98 | 98 | at least 90 | pass |"
        )
        self.assertIn("Measured `https://risingrepos.com/`, the address given by hand,", outcome.summary)

    def test_the_summary_shows_an_address_as_code_so_that_none_of_it_is_read_as_markdown(self):
        outcome = self.evaluate(address="https://example.com/a_b*c*[x](https://example.org)")
        self.assertIn(
            "Measured `https://example.com/a_b*c*[x](https://example.org)`, the address given by hand,", outcome.summary
        )
        self.assertIn("### `/a_b*c*[x](https://example.org)` on a phone", outcome.summary)


class AfterADeploy(EvalTest):
    """After a deploy the eval is given the deployed commit. It measures the preview only while that commit is
    the head of main, which shows that the deploy uploaded its pages, and once the preview states that commit's
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

    def test_the_numbers_are_not_judged_when_main_moves_on_while_the_preview_is_measured(self):
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
            f"Not judged. `main` moved on from `{COMMIT}` to `{NEWER}` while the preview was measured", outcome.summary
        )

    def test_the_preview_is_measured_once_it_states_the_commits_newest_board_day(self):
        day, published = newest_board_of_the_example()
        answers = iter([OSError("made up"), page_stating(day, "2026-01-01T00:00:00Z"), page_stating(day, published)])

        def read_page(address):
            self.assertEqual(address, PREVIEW_PAGE)
            answer = next(answers)
            if isinstance(answer, Exception):
                raise answer
            return answer

        outcome = self.evaluate(commit=COMMIT, head_of_main=lambda: COMMIT, read_page=read_page, data=EXAMPLE)
        self.assertTrue(outcome.passed, outcome.problems)
        self.assertEqual(len(self.pauses), 2)
        self.assertEqual(outcome.results["commit"], COMMIT)
        self.assertIn(f"Measured `{PREVIEW_PAGE}` after the deploy of `{COMMIT}`,", outcome.summary)

    def test_a_preview_that_never_states_the_commits_newest_board_day_is_not_measured_and_fails_the_eval(self):
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
        page = (built / "index.html").read_text(encoding="utf-8")
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
