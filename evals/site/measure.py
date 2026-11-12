"""The site eval: how fast the site's pages load, how heavy they are, and how they score for accessibility.

It runs Lighthouse on each page, on a phone profile and a desktop profile, RUNS times each, and takes the
median of each number. It judges each median against its limit in limits.json, writes a summary that sets the
numbers beside the accepted ones in accepted.json, and fails when a number is outside its limit or could not be
measured. README.md says what each number means. .github/workflows/site-eval.yml runs it:

    python evals/site/measure.py --out <folder>

It reads these from its environment, which the workflow sets:

    SITE_EVAL_LIGHTHOUSE  the command that runs Lighthouse, pinned to one version
    SITE_EVAL_ADDRESS     an https address to measure in place of the preview's pages, or nothing
    SITE_EVAL_COMMIT      the commit whose deploy to the preview is measured, or nothing
    GITHUB_STEP_SUMMARY   the file the summary is added to, when it runs in a workflow

Into <folder> it writes results.json, in the shape accepted.json has, and each run's report and log. It uses
only Python's standard library.
"""

import argparse
import json
import os
import re
import shlex
import statistics
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
DATA = HERE.parent.parent / "site-data"

PREVIEW = "https://preview.risingrepos.pages.dev"
PAGES = ("/",)
"""The pages measured on the preview, by their path. A change that adds a page to the site adds it here."""

RUNS = 5
"""Lighthouse runs for each page on each profile. Lighthouse's documentation on variability says that the
median of five runs is about twice as stable as one run."""

RUN_TIMEOUT = 180
"""Seconds one Lighthouse run may take. A run of the first page takes under a minute."""

SERVED_TRIES = 10
SERVED_PAUSE = 15
"""After a deploy, how many times the eval reads the preview, SERVED_PAUSE seconds apart, before it gives up
waiting for the preview to state the deployed commit's newest board day."""

PROFILES = {"phone": (), "desktop": ("--preset=desktop",)}
"""Lighthouse's own two profiles. With no preset it emulates a mid-range phone on a slow 4G connection, and
`--preset=desktop` a desktop on a wired one. Both simulate the throttling, which varies least from run to run."""

OPTIONS = (
    "--output=json",
    "--only-categories=performance,accessibility",
    "--chrome-flags=--headless",
    "--no-enable-error-reporting",
    "--quiet",
)
"""What every run is given besides its address, its report's path, and its profile. Error reporting is off,
so Lighthouse sends nothing anywhere but to the page it measures."""

ADDRESS = re.compile(r"https://[A-Za-z0-9.-]+(?::[0-9]{1,5})?(?:[/?#][A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]*)?")
"""An https address with a host, written only in the characters an address may hold unescaped. None of them is
a space, a quotation mark, a backtick, or `|`, so an address can neither break out of the summary's code spans
nor start a line of the job's log."""

ERROR_CODE = re.compile(r"[A-Z][A-Z0-9_]*")
VERSION = re.compile(r"[0-9]+(?:\.[0-9]+){1,3}")
CHROME = re.compile(r"Chrome/([0-9]+)\.")
"""Chrome's major version, from the user agent in a report. Chrome reports only its major version there."""
COMMIT = re.compile(r"[0-9a-f]{40}")


class CouldNotMeasure(Exception):
    """A number the eval could not get. The message says why, in words a reader of the summary can act on."""


class Measure(NamedTuple):
    name: str
    higher_is_better: bool
    read: Callable[[dict], int | float]
    show: Callable[[int | float], str]


def _score(category: str) -> Callable[[dict], int]:
    return lambda report: round(report["categories"][category]["score"] * 100)


def _audit(audit: str) -> Callable[[dict], float]:
    return lambda report: report["audits"][audit]["numericValue"]


MEASURES = {
    "performance": Measure("Performance score", True, _score("performance"), str),
    "accessibility": Measure("Accessibility score", True, _score("accessibility"), str),
    "largest_contentful_paint": Measure(
        "Largest Contentful Paint",
        False,
        lambda report: round(_audit("largest-contentful-paint")(report) / 1000, 2),
        lambda seconds: f"{seconds:.2f} s",
    ),
    "cumulative_layout_shift": Measure(
        "Cumulative Layout Shift", False, lambda report: round(_audit("cumulative-layout-shift")(report), 3), "{:.3f}".format
    ),
    "transfer_size": Measure(
        "Total transfer size", False, lambda report: round(_audit("total-byte-weight")(report)), "{:,} bytes".format
    ),
    "requests": Measure(
        "Requests", False, lambda report: len(report["audits"]["network-requests"]["details"]["items"]), str
    ),
}
"""What the eval reports for each page on each profile, by the key limits.json and accepted.json use. A score is
out of 100, Largest Contentful Paint is in seconds, and the transfer size is in bytes as they crossed the
network, compressed."""


class Outcome(NamedTuple):
    passed: bool
    summary: str
    problems: list[str]
    results: dict | None


def evaluate(
    *,
    lighthouse: list[str],
    out: Path,
    limits: dict,
    accepted: dict,
    address: str = "",
    commit: str = "",
    run: str | None = None,
    data: Path = DATA,
    head_of_main: Callable[[], str],
    read_page: Callable[[str], str],
    pause: Callable[[float], None] = time.sleep,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> Outcome:
    """Measure each page, judge its numbers, and say what was found.

    With an `address`, that page alone is measured. Otherwise each of PAGES is measured on the preview. With a
    `commit`, the preview is measured as that commit's deploy: only while `head_of_main()` is that commit, which
    shows that its deploy uploaded its pages, and only once each page states that commit's newest board day.
    """
    try:
        pages = _pages(address)
    except CouldNotMeasure as error:
        return _not_measured(str(error))
    if commit:
        try:
            head = head_of_main()
            if head != commit:
                return Outcome(
                    True,
                    f"## Site eval\n\nNot measured. `main` has moved on from `{commit}`, whose deploy this run "
                    f"follows, to `{head}`. The run that follows the deploy of `{head}` measures the preview.\n",
                    [],
                    None,
                )
            stamp = _newest_board(data)
            for path, page in pages:
                _wait_until_served(path, page, stamp, commit, read_page, pause)
        except CouldNotMeasure as error:
            return _not_measured(str(error))

    out.mkdir(parents=True, exist_ok=True)
    measured = {}
    tools = {}
    for number, (path, page) in enumerate(pages, start=1):
        for profile in PROFILES:
            measured[path, profile] = _measure(lighthouse, page, profile, out / f"{number}-{profile}", tools)

    if commit:
        try:
            head = head_of_main()
        except CouldNotMeasure as error:
            return _not_measured(str(error))
        if head != commit:
            return Outcome(
                True,
                f"## Site eval\n\nNot judged. `main` moved on from `{commit}` to `{head}` while the preview was "
                f"measured, so the numbers may be of either commit's pages. The run that follows the deploy of "
                f"`{head}` measures the preview again.\n",
                [],
                None,
            )

    results = {
        "commit": commit or None,
        "measured_at": now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run": run,
        "lighthouse": tools.get("lighthouse"),
        "chrome": tools.get("chrome"),
        "runs": RUNS,
        "base": _base(pages[0][1]),
        "pages": {},
    }
    problems = []
    sections = []
    for (path, profile), found in measured.items():
        where = f"{profile.capitalize()}, `{path}`"
        heading = f"### `{path}` on {'a phone' if profile == 'phone' else 'a desktop'}"
        if isinstance(found, CouldNotMeasure):
            results["pages"].setdefault(path, {})[profile] = {"failure": str(found)}
            problems.append(f"{where}: could not be measured: {found}")
            sections.append(f"{heading}\n\nCould not be measured: {found}.\n")
            continue
        results["pages"].setdefault(path, {})[profile] = found
        rows = ["| Measure | This run | Runs | Accepted | Limit | Result |", "| --- | --- | --- | --- | --- | --- |"]
        for key, measure in MEASURES.items():
            value = found[key]["median"]
            runs = found[key]["runs"]
            limit = limits[profile][key]["limit"]
            was = accepted.get("pages", {}).get(path, {}).get(profile, {}).get(key, {}).get("median")
            if limit is None:
                result = "no limit"
            elif value >= limit if measure.higher_is_better else value <= limit:
                result = "pass"
            else:
                result = "**fail**"
                side = "under" if measure.higher_is_better else "over"
                problems.append(f"{where}: {measure.name} {measure.show(value)} is {side} its limit of {measure.show(limit)}")
            rows.append(
                f"| {measure.name} | {measure.show(value)} | {measure.show(min(runs))} to {measure.show(max(runs))} "
                f"| {'none' if was is None else measure.show(was)} "
                f"| {'none' if limit is None else ('at least ' if measure.higher_is_better else 'at most ') + measure.show(limit)} "
                f"| {result} |"
            )
        sections.append(heading + "\n\n" + "\n".join(rows) + "\n")

    return Outcome(not problems, _summary(pages, commit, address, results, accepted, sections, problems), problems, results)


def _pages(address: str) -> list[tuple[str, str]]:
    """The pages to measure, each as its path and its address."""
    if not address:
        return [(path, PREVIEW + path) for path in PAGES]
    if not ADDRESS.fullmatch(address):
        raise CouldNotMeasure("the address given is not an https address")
    parts = urlsplit(address)
    return [((parts.path or "/") + (f"?{parts.query}" if parts.query else ""), address)]


def _base(address: str) -> str:
    parts = urlsplit(address)
    return f"{parts.scheme}://{parts.netloc}"


def _not_measured(reason: str) -> Outcome:
    problem = f"{reason[0].upper()}{reason[1:]}, so nothing was measured"
    return Outcome(False, f"## Site eval\n\n**Failed:** {problem}.\n", [problem], None)


def _newest_board(data: Path) -> tuple[str, str]:
    """The board day and the publish time of the newest board day in `data`, which every page states in its
    <head>, as RisingRepos's data contract says."""
    try:
        day = json.loads((data / "boards" / "index.json").read_text(encoding="utf-8"))["board_days"][0]["board_day"]
        board = json.loads((data / "boards" / "days" / day / "daily.json").read_text(encoding="utf-8"))
        return day, board["published_at"]
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        raise CouldNotMeasure("the deployed commit's newest board day could not be read") from error


class _Stamp(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "meta" and attributes.get("name") in ("rr:board-date", "rr:published-at"):
            self.meta.setdefault(attributes["name"], attributes.get("content"))


def _states(html: str) -> tuple[str | None, str | None]:
    stamp = _Stamp()
    stamp.feed(html)
    stamp.close()
    return stamp.meta.get("rr:board-date"), stamp.meta.get("rr:published-at")


def _wait_until_served(path, page, stamp, commit, read_page, pause) -> None:
    for attempt in range(1, SERVED_TRIES + 1):
        try:
            if _states(read_page(page)) == stamp:
                return
        except OSError:
            pass  # read again, after a pause
        if attempt < SERVED_TRIES:
            pause(SERVED_PAUSE)
    day, published = stamp
    raise CouldNotMeasure(f"`{path}` does not state the newest board day of `{commit}`, {day} published at {published}")


def _measure(lighthouse: list[str], page: str, profile: str, stem: Path, tools: dict) -> dict | CouldNotMeasure:
    """The median and each run's value of every number, for one page on one profile, or why they could not be
    measured. The first run that fails ends the measurement."""
    runs = []
    for run in range(1, RUNS + 1):
        try:
            report = _run_lighthouse(lighthouse, page, profile, Path(f"{stem}-{run}.json"), Path(f"{stem}-{run}.log"))
            runs.append(_numbers(report))
        except CouldNotMeasure as error:
            return CouldNotMeasure(f"run {run} of {RUNS}: {error}")
        version = str(report.get("lighthouseVersion"))
        chrome = CHROME.search(str(report.get("environment", {}).get("hostUserAgent")))
        tools.setdefault("lighthouse", version if VERSION.fullmatch(version) else None)
        tools.setdefault("chrome", chrome.group(1) if chrome else None)
    return {
        key: {"median": statistics.median_low([numbers[key] for numbers in runs]), "runs": [numbers[key] for numbers in runs]}
        for key in MEASURES
    }


def _run_lighthouse(lighthouse: list[str], page: str, profile: str, report_path: Path, log_path: Path) -> dict:
    """One run of Lighthouse, and the report it wrote.

    What Lighthouse prints goes to `log_path`, never to the job's log: GitHub reads a line of the job's log that
    starts with `::` as a command, and Lighthouse prints what the measured page makes it print.
    """
    arguments = [*lighthouse, page, f"--output-path={report_path}", *OPTIONS, *PROFILES[profile]]
    with log_path.open("wb") as log:
        try:
            done = subprocess.run(arguments, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=RUN_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise CouldNotMeasure(f"Lighthouse did not finish within {RUN_TIMEOUT} seconds") from None
        except OSError:
            raise CouldNotMeasure("Lighthouse could not be started") from None
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        report = None
    error = report.get("runtimeError") if isinstance(report, dict) else None
    if isinstance(error, dict):
        code = str(error.get("code"))
        raise CouldNotMeasure(f"Lighthouse reported {code if ERROR_CODE.fullmatch(code) else 'an error'}")
    if done.returncode != 0:
        raise CouldNotMeasure(f"Lighthouse exited with status {done.returncode}")
    if not isinstance(report, dict):
        raise CouldNotMeasure("Lighthouse wrote no report")
    return report


def _numbers(report: dict) -> dict[str, int | float]:
    numbers = {}
    for key, measure in MEASURES.items():
        try:
            numbers[key] = measure.read(report)
        except (KeyError, IndexError, TypeError) as error:
            raise CouldNotMeasure(f"the report holds no {measure.name}") from error
    return numbers


def _summary(pages, commit, address, results, accepted, sections, problems) -> str:
    where = ", ".join(f"`{page}`" for _, page in pages)
    if commit:
        what = f"Measured {where} after the deploy of `{commit}`,"
    elif address:
        what = f"Measured {where}, the address given by hand,"
    else:
        what = f"Measured the preview as it stands, {where},"
    tools = f"with Lighthouse {results['lighthouse'] or '(version unknown)'} in Chrome {results['chrome'] or '(version unknown)'}."
    if not commit and not address:
        tools += " A pull request's own pages reach the preview only once it merges."
    if COMMIT.fullmatch(str(accepted.get("commit"))) and accepted.get("measured_at"):
        against = f"The accepted numbers were measured on {accepted['measured_at'][:10]}, at `{accepted['commit']}`."
    else:
        against = "No numbers are accepted yet."
    lines = [
        "## Site eval",
        "",
        f"{what} {tools} Each number is the median of {RUNS} runs. {against}",
        "",
        *sections,
    ]
    if problems:
        lines += [f"**Failed:** {len(problems)} {'number' if len(problems) == 1 else 'numbers'}.", ""]
        lines += [f"- {problem}" for problem in problems] + [""]
    return "\n".join(lines)


def head_of_main() -> str:
    """The commit at the head of this repository's main, read from GitHub. The repository is public, so git
    reads it without a credential."""
    repository = f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}"
    try:
        done = subprocess.run(
            ["git", "ls-remote", "--exit-code", repository, "refs/heads/main"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        done = None
    head = done.stdout.split()[0] if done and done.returncode == 0 and done.stdout.split() else ""
    if not COMMIT.fullmatch(head):
        raise CouldNotMeasure("the head of main could not be read")
    return head


def read_page(address: str) -> str:
    """The page at `address`, as the preview serves it."""
    request = urllib.request.Request(address, headers={"User-Agent": "rising-repos-site site eval"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read(10_000_000).decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(prog="python evals/site/measure.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, required=True, help="the folder to write results.json, the reports, and the logs into")
    options = parser.parse_args()

    run = None
    if os.environ.get("GITHUB_RUN_ID"):
        run = (
            f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/"
            f"{os.environ['GITHUB_RUN_ID']}/attempts/{os.environ['GITHUB_RUN_ATTEMPT']}"
        )
    accepted = HERE / "accepted.json"
    outcome = evaluate(
        lighthouse=shlex.split(os.environ["SITE_EVAL_LIGHTHOUSE"]),
        out=options.out,
        limits=json.loads((HERE / "limits.json").read_text(encoding="utf-8")),
        accepted=json.loads(accepted.read_text(encoding="utf-8")) if accepted.exists() else {},
        address=os.environ.get("SITE_EVAL_ADDRESS", ""),
        commit=os.environ.get("SITE_EVAL_COMMIT", ""),
        run=run,
        head_of_main=head_of_main,
        read_page=read_page,
    )

    if outcome.results is not None:
        options.out.mkdir(parents=True, exist_ok=True)
        (options.out / "results.json").write_text(json.dumps(outcome.results, indent=2) + "\n", encoding="utf-8", newline="\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8", newline="\n") as summary:
            summary.write(outcome.summary)
    print(outcome.summary)
    for problem in outcome.problems:
        # A workflow command's message escapes these three, so that no problem can end the line it is on.
        message = problem.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::error title=Site eval::{message}")
    return 0 if outcome.passed else 1


if __name__ == "__main__":
    sys.exit(main())
