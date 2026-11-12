"""The site eval: Lighthouse's measure of the site's pages, for their speed, their weight, and their accessibility.

It runs Lighthouse on each page, on a phone profile and a desktop profile, RUNS times each, and takes the
median of each number. It judges each median against its limit in limits.json, writes a summary that sets the
numbers beside the accepted ones in accepted.json, and fails when a number is outside its limit or could not be
measured. README.md says what each number means. .github/workflows/site-eval.yml runs it from the
repository's top folder, with the site's locked dependencies:

    uv run --locked python -m evals.site.measure --out <folder>

It reads these from its environment, which the workflow sets:

    SITE_EVAL_LIGHTHOUSE  the command that runs Lighthouse, pinned to one version
    SITE_EVAL_ADDRESS     an https address to measure in place of the preview's pages, or nothing
    SITE_EVAL_COMMIT      the commit whose deploy to the preview is measured, or nothing
    GITHUB_STEP_SUMMARY   the file the summary is added to, when it runs in a workflow

Into <folder> it writes results.json, in the shape accepted.json has, and each run's report and log. After a
deploy it reads the newest board with sitebuild.contract, as the build does, so it waits for the stamp the build
put on each page.
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
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlsplit

from sitebuild import contract

HERE = Path(__file__).resolve().parent
DATA = HERE.parent.parent / "site-data"

PREVIEW = "https://preview.risingrepos.pages.dev"
PAGES = ("/",)
"""The pages measured on the preview, by their path. A change that adds a page to the site adds it here."""

RUNS = 5
"""Lighthouse runs for each page on each profile. Lighthouse's documentation on variability says that the
median of five runs is about twice as stable as one run. The median is always one of the runs' values: were
the runs ever even in number, it would be the lower of the middle two."""

RUN_TIMEOUT = 180
"""Seconds one Lighthouse run may take. A run of the first page takes under half a minute."""

SERVED_TRIES = 10
SERVED_PAUSE = 15
"""After a deploy, how many times the eval reads each page, SERVED_PAUSE seconds apart, before it gives up
waiting for the preview to state the deployed commit's newest board day."""

PROFILES = {"phone": (), "desktop": ("--preset=desktop",)}
"""Lighthouse's own two profiles. With no preset it emulates a mid-range phone on a slow 4G connection, and
`--preset=desktop` a desktop on a wired one. Both simulate the slow CPU and connection from one fast load,
which removes much of the variation a real network brings."""

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
"""Chrome's major version, from the user agent in a report, which holds no other part of it."""
COMMIT = re.compile(r"[0-9a-f]{40}")


class CouldNotMeasure(Exception):
    """A number the eval could not get. The message says why, in words a reader of the summary can act on."""


class Measure(NamedTuple):
    name: str
    higher_is_better: bool
    read: Callable[[dict], int | float]
    show: Callable[[int | float], str]

    def within(self, value: int | float, limit: int | float) -> bool:
        return value >= limit if self.higher_is_better else value <= limit


def _score(report: dict, category: str) -> int:
    return round(report["categories"][category]["score"] * 100)


def _audit(report: dict, audit: str) -> float:
    return report["audits"][audit]["numericValue"]


MEASURES = {
    "performance": Measure("Performance score", True, lambda report: _score(report, "performance"), str),
    "accessibility": Measure("Accessibility score", True, lambda report: _score(report, "accessibility"), str),
    "largest_contentful_paint": Measure(
        "Largest Contentful Paint",
        False,
        lambda report: round(_audit(report, "largest-contentful-paint") / 1000, 2),
        lambda seconds: f"{seconds:.2f} s",
    ),
    "cumulative_layout_shift": Measure(
        "Cumulative Layout Shift",
        False,
        lambda report: round(_audit(report, "cumulative-layout-shift"), 3),
        "{:.3f}".format,
    ),
    "transfer_size": Measure(
        "Total transfer size", False, lambda report: round(_audit(report, "total-byte-weight")), "{:,} bytes".format
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


class Measured(NamedTuple):
    """One page measured on one profile: each number's median and its value in every run, and the versions of
    the tools that measured it."""

    numbers: dict[str, dict]
    lighthouse: str | None
    chrome: str | None


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
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Outcome:
    """Measure each page, judge its numbers, and say what was found.

    With an `address`, that page alone is measured. Otherwise each of PAGES is measured on the preview. With a
    `commit`, the preview is measured as that commit's deploy: only while `head_of_main()` is that commit, which
    shows that its deploy uploaded its pages, and only once each page states that commit's newest board day.
    """
    try:
        pages = _pages(address)
        if commit:
            head = head_of_main()
            if head != commit:
                return _superseded(
                    f"Not measured. `main` has moved on from `{commit}`, whose deploy this run follows, to `{head}`. "
                    f"The run that follows the deploy of `{head}` measures the preview."
                )
            stamp = _board_stamp(data)
            for path, page in pages:
                _wait_until_served(path, page, stamp, commit, read_page, pause)
    except CouldNotMeasure as error:
        return _failed(f"{error}, so nothing was measured")

    out.mkdir(parents=True, exist_ok=True)
    measured = {
        (path, profile): _measure(lighthouse, page, profile, out / f"{number}-{profile}")
        for number, (path, page) in enumerate(pages, start=1)
        for profile in PROFILES
    }
    if commit:
        try:
            head = head_of_main()
        except CouldNotMeasure as error:
            return _failed(f"{error} after the measurement, so the numbers were not judged")
        if head != commit:
            return _superseded(
                f"Not judged. `main` moved on from `{commit}` to `{head}` while the preview was measured, so the "
                f"numbers may be of either commit's pages. The run that follows the deploy of `{head}` measures the "
                f"preview again."
            )

    made = [found for found in measured.values() if isinstance(found, Measured)]
    results = {
        "commit": commit or None,
        "measured_at": now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run": run,
        "lighthouse": made[0].lighthouse if made else None,
        "chrome": made[0].chrome if made else None,
        "runs": RUNS,
        "base": _base(pages[0][1]),
        "pages": {},
    }
    sections, problems = [], []
    for (path, profile), found in measured.items():
        was = accepted.get("pages", {}).get(path, {}).get(profile, {})
        section, found_problems = _section(path, profile, found, limits[profile], was)
        sections.append(section)
        problems += found_problems
        numbers = found.numbers if isinstance(found, Measured) else {"failure": str(found)}
        results["pages"].setdefault(path, {})[profile] = numbers
    lines = ["## Site eval", "", _opening(pages, commit, address, results, accepted), "", *sections]
    if problems:
        lines += ["**Failed:**", "", *(f"- {problem}" for problem in problems), ""]
    return Outcome(not problems, "\n".join(lines), problems, results)


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


def _superseded(text: str) -> Outcome:
    """Nothing judged, because a newer deploy's run measures the preview instead. That fails nothing."""
    return Outcome(True, f"## Site eval\n\n{text}\n", [], None)


def _failed(problem: str) -> Outcome:
    """Nothing judged, because the eval could not make its measurement or tell whose pages it measured. That
    fails the eval."""
    problem = problem[0].upper() + problem[1:]
    return Outcome(False, f"## Site eval\n\n**Failed:** {problem}.\n", [problem], None)


def _board_stamp(data: Path) -> tuple[str, str]:
    """The board day and the publish time that the build states in each page's <head>, taken from the board
    that the build reads from `data`."""
    try:
        board = contract.latest_board(data)
    except contract.DataError as error:
        raise CouldNotMeasure("the deployed commit's newest board day could not be read") from error
    return board["board_day"], board["published_at"]


class _Stamp(HTMLParser):
    """Reads the board day and the publish time that a page states in its <meta> tags."""

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


def _wait_until_served(
    path: str,
    page: str,
    stamp: tuple[str, str],
    commit: str,
    read_page: Callable[[str], str],
    pause: Callable[[float], None],
) -> None:
    """Return once `page` states the board day and publish time in `stamp`, or fail after SERVED_TRIES reads."""
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


def _measure(lighthouse: list[str], page: str, profile: str, stem: Path) -> Measured | CouldNotMeasure:
    """`page` measured RUNS times on `profile`, or why it could not be. The first run that fails ends it."""
    runs = []
    for run in range(1, RUNS + 1):
        try:
            report = _run_lighthouse(lighthouse, page, profile, Path(f"{stem}-{run}.json"), Path(f"{stem}-{run}.log"))
            runs.append(_numbers(report))
        except CouldNotMeasure as error:
            return CouldNotMeasure(f"run {run} of {RUNS}: {error}")
    values = {key: [numbers[key] for numbers in runs] for key in MEASURES}
    # Every run uses the same Lighthouse and the same Chrome, so the last report names them for all.
    version = str(report.get("lighthouseVersion"))
    environment = report.get("environment")
    chrome = CHROME.search(str(environment.get("hostUserAgent"))) if isinstance(environment, dict) else None
    return Measured(
        {key: {"median": statistics.median_low(each), "runs": each} for key, each in values.items()},
        version if VERSION.fullmatch(version) else None,
        chrome.group(1) if chrome else None,
    )


def _run_lighthouse(lighthouse: list[str], page: str, profile: str, report_path: Path, log_path: Path) -> dict:
    """One run of Lighthouse, and the report it wrote.

    What Lighthouse prints goes to `log_path`, never to the job's log: GitHub reads a line of the job's log that
    starts with `::` as a command, and Lighthouse prints what the measured page makes it print.
    """
    arguments = [*lighthouse, page, f"--output-path={report_path}", *OPTIONS, *PROFILES[profile]]
    with log_path.open("wb") as log:
        try:
            done = subprocess.run(
                arguments, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=RUN_TIMEOUT
            )
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


def _section(
    path: str, profile: str, found: Measured | CouldNotMeasure, limits: dict, was: dict
) -> tuple[str, list[str]]:
    """The summary's section for one page on one profile, and a problem for each number outside its limit.
    `limits` are the profile's, and `was` the page's accepted numbers on the profile."""
    where = f"{profile.capitalize()}, `{path}`"
    heading = f"### `{path}` on a {profile}"
    if isinstance(found, CouldNotMeasure):
        return f"{heading}\n\nCould not be measured: {found}.\n", [f"{where}: could not be measured: {found}"]
    rows = ["| Measure | This run | Runs | Accepted | Limit | Result |", "| --- | --- | --- | --- | --- | --- |"]
    problems = []
    for key, measure in MEASURES.items():
        value, runs = found.numbers[key]["median"], found.numbers[key]["runs"]
        accepted = was.get(key, {}).get("median")
        limit = limits[key]["limit"]
        bound = (
            "none"
            if limit is None
            else f"{'at least' if measure.higher_is_better else 'at most'} {measure.show(limit)}"
        )
        if limit is None:
            result = "no limit"
        elif measure.within(value, limit):
            result = "pass"
        else:
            result = "**fail**"
            side = "under" if measure.higher_is_better else "over"
            problems.append(
                f"{where}: {measure.name} {measure.show(value)} is {side} its limit of {measure.show(limit)}"
            )
        rows.append(
            f"| {measure.name} | {measure.show(value)} | {measure.show(min(runs))} to {measure.show(max(runs))} "
            f"| {'none' if accepted is None else measure.show(accepted)} | {bound} | {result} |"
        )
    return heading + "\n\n" + "\n".join(rows) + "\n", problems


def _opening(pages: list[tuple[str, str]], commit: str, address: str, results: dict, accepted: dict) -> str:
    """The summary's first paragraph: what was measured, with what, and against which accepted numbers."""
    where = ", ".join(f"`{page}`" for _, page in pages)
    if commit:
        what = f"Measured {where} after the deploy of `{commit}`,"
    elif address:
        what = f"Measured {where}, the address given by hand,"
    else:
        what = f"Measured the preview as it stands, {where},"
    lighthouse, chrome = results["lighthouse"] or "(version unknown)", results["chrome"] or "(version unknown)"
    tools = f"with Lighthouse {lighthouse} in Chrome {chrome}."
    if not commit and not address:
        tools += " A pull request's own pages reach the preview only once it merges."
    if COMMIT.fullmatch(str(accepted.get("commit"))) and accepted.get("measured_at"):
        against = f"The accepted numbers were measured on {accepted['measured_at'][:10]}, at `{accepted['commit']}`."
    else:
        against = "No numbers are accepted yet."
    return f"{what} {tools} Each number is the median of {RUNS} runs. {against}"


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
    parser = argparse.ArgumentParser(prog="python -m evals.site.measure", description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--out", type=Path, required=True, help="the folder to write results.json, the reports, and the logs into"
    )
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
        (options.out / "results.json").write_text(
            json.dumps(outcome.results, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
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
