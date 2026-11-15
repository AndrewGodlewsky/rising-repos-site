"""The site's generator: checks the data files against the data contract, then renders the site's pages."""

import base64
import hashlib
from collections.abc import Iterator
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from itertools import groupby
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from sitebuild.contract import boards as read_boards

TEMPLATES = Path(__file__).parent / "templates"
DATA = Path(__file__).resolve().parent.parent / "site-data"

BOARD = "index.html"
DAYS = "days/index.html"
BOARD_DAY = "days/{board_day}/index.html"
HOW_IT_WORKS = "how-it-works/index.html"
NOT_FOUND = "404.html"

PAGES = {
    BOARD: "latest.html",
    DAYS: "days.html",
    BOARD_DAY: "board.html",
    HOW_IT_WORKS: "how-it-works.html",
    NOT_FOUND: "not-found.html",
}
"""Each page the build writes, by its path in the site, and the template in templates/ that renders it.

- `BOARD`, the site's root, is the newest board day's board. It is the one page that states its board day in the
  data contract's two meta tags, which latest.html adds to board.html, so whatever reads them reads the root.
- `DAYS` lists every board day, newest first.
- `BOARD_DAY` is written once for each board day in the index, the newest included, so that each board day keeps
  one address however many come after it.
- `HOW_IT_WORKS` says in a few plain sentences how the boards are ranked, for the formula `DESCRIBED_FORMULA`
  names. Every page links to it from the site's line.
- Cloudflare Pages answers an address that holds no page with `NOT_FOUND` and the status 404. A site with no
  404.html at its root is taken for a single-page app, and every such address gets the root page and the
  status 200.

page.html names the templates whose pages carry the notice of an old board: every one but not-found.html and
how-it-works.html, whose text the notice's hiding of an old board would hide.
"""

SCRIPT = "old-board.js"
"""The site's one script, in templates/: the notice of an old board (AndrewGodlewsky/RisingRepos#56). old-board.html
puts its text in the page, and the build puts the hash of that text in the page's Content-Security-Policy, which lets
this script run and no other."""

DESCRIBED_FORMULA = 2
"""The version of the scoring formula that how-it-works.html describes. Its page says so, and says plainly when the
newest board was ranked by another, so that a new formula in RisingRepos never leaves the page describing the wrong
one unnoticed."""

MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def board_day_page(day: str) -> str:
    """The path of a board day's own page: '2026-11-09' as 'days/2026-11-09/index.html'."""
    return BOARD_DAY.format(board_day=day)


def address(path: str) -> str:
    """A page's address on the site, from its path: 'days/index.html' as '/days/'."""
    return "/" + path.removesuffix("index.html")


def day_address(day: str) -> str:
    """The address of a board day's page: '2026-11-09' as '/days/2026-11-09/'."""
    return address(board_day_page(day))


def long_date(day: str) -> str:
    """'2026-11-09' as '9 November 2026'."""
    value = date.fromisoformat(day)
    return f"{value.day} {MONTHS[value.month - 1]} {value.year}"


def long_dates(days: list[str]) -> str:
    """['2026-11-09'] as '9 November 2026', two days joined by 'and', and three as 'A, B, and C'."""
    dates = [long_date(day) for day in days]
    if len(dates) < 3:
        return " and ".join(dates)
    return ", ".join(dates[:-1]) + ", and " + dates[-1]


def short_date(day: str) -> str:
    """'2026-11-09' as '9 Nov'."""
    value = date.fromisoformat(day)
    return f"{value.day} {MONTHS[value.month - 1][:3]}"


def day_in_month(day: str) -> str:
    """'2026-11-09' as 'Monday 9 November'."""
    value = date.fromisoformat(day)
    return f"{WEEKDAYS[value.weekday()]} {value.day} {MONTHS[value.month - 1]}"


def month_name(month: str) -> str:
    """'2026-11' as 'November 2026'."""
    year, number = month.split("-")
    return f"{MONTHS[int(number) - 1]} {year}"


def utc_time(moment: str) -> str:
    """'2026-11-10T00:41:07Z' as '10 November 2026 at 00:41 UTC'."""
    value = datetime.fromisoformat(moment)
    return f"{long_date(value.date().isoformat())} at {value:%H:%M} UTC"


def repositories(count: int) -> str:
    """5 as '5 repositories', 1 as '1 repository', and 0 as 'No repositories'."""
    if count == 0:
        return "No repositories"
    return "1 repository" if count == 1 else f"{count:,} repositories"


def partial_days(board: dict) -> dict | None:
    """What a board's page says about the partial snapshot days its ranking read: days on which the collector's
    snapshot missed some repositories (RisingRepos#45).

    None when the board's file does not say, as a file published before the data contract had `partial_days`
    does not. The page then says nothing about partial days: it neither names one nor says there was none.
    Otherwise `own` is whether the board day is itself one, `recent` lists the other days over which the ranking
    measures a recent pace, and `earlier` the days it reads only further back, each newest first, as the file
    lists them.
    """
    if "partial_days" not in board:
        return None
    days = board["partial_days"]
    return {
        "own": any(day["snapshot_day"] == board["board_day"] for day in days),
        "recent": [day["snapshot_day"] for day in days if day["recent"] and day["snapshot_day"] != board["board_day"]],
        "earlier": [day["snapshot_day"] for day in days if not day["recent"]],
    }


def rounded(value: float, places: int) -> Decimal:
    """`value` to `places` decimal places, a half rounded up, as a reader rounds: 10.5 to none as 11, and 8.125 to
    two as 8.13. It rounds the number as JSON wrote it, not its nearest binary fraction, which may lie below it."""
    return Decimal(repr(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def figure(value: float, places: int) -> str:
    """A number to at most `places` decimal places, with thousands parted by commas and no zero at the end:
    260.0 as '260', 30.1667 to two places as '30.17', and 1285.909 to two places as '1,285.91'."""
    text = f"{rounded(value, places):,}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def times(score: float) -> str:
    """A score as a multiple of a usual pace, without a cap: to one decimal place under 10, and a whole number from
    10, which needs no decimal to read. 8.63 as '8.6', 4.0 as '4', 9.96 as '10', and 1285.9 as '1,286'."""
    return figure(score, 1) if rounded(score, 1) < 10 else figure(score, 0)


def why(row: dict) -> dict:
    """Why a row's repository is on its board, in words, from the numbers its file gives the row as its score worked
    them out (AndrewGodlewsky/RisingRepos#49): `line` for the row, and `detail`, the score and the sum it came from,
    for the row's expanded view. The site works out no score: it rounds what it shows, and tells from the numbers
    which of these the row is.

    - Its usual pace, its baseline, was no lower than the divisor its recent pace took: the line gives the stars it
      gained above that pace and its score as a multiple of it, and the detail names that multiple as the score and
      gives its sum without writing the score a second time. Each figure costs the root's transfer budget about 2.5
      bytes a row gzipped, and a row that wrote it twice took the site eval's 713-row test over 100,000 bytes.
    - Its usual pace was under that, the floor, and at least nothing: a multiple of the floor is no multiple of the
      repository's own pace, so the line says the pace was under the floor and gives no multiple.
    - It had been losing stars: the line gives the stars it gained, since its gain above a falling pace is not what
      the excess counts.
    - The loss rule left a recent day out: the line gives the stars of the days kept, since the excess is measured
      as if over every recent day, and the detail says that a day was left out.

    A row of a file published before the data contract had the numbers has none, and board.html then asks for no
    reason.
    """
    score, stars, days, baseline, divisor = (
        row[name] for name in ("score", "recent_stars", "recent_days", "baseline", "divided_by")
    )
    span = "1 day" if days == 1 else f"{days} days"
    floor = f"{figure(divisor, 2)} star{'' if divisor == 1 else 's'} a day"
    total = f"Score {figure(score, 2)} = {stars:,} stars ÷ {span} ÷ {figure(divisor, 2)}"
    if baseline >= divisor:
        pace = f"{times(score)}× its usual pace"
        detail = f"That multiple is its score: {stars:,} stars ÷ {span} ÷ its usual {figure(baseline, 2)} a day"
    elif baseline >= 0:
        pace = f"its usual pace was under {floor}"
        detail = f"{total}: its usual {figure(baseline, 2)} a day counts as {floor}"
    else:
        pace = "it had been losing stars"
        detail = f"{total}: it lost {figure(-baseline, 2)} a day before, which counts as {floor}"
    left_out = row["days_left_out"]
    # The excess is the stars above its own trend only when it covers every recent day and the pace was not falling.
    if left_out or baseline < 0:
        gained = f"+{stars:,} in {span}"
    else:
        gained = f"+{figure(row['excess'], 0)} above its own trend"
    if left_out == 1:
        detail += ". A recent day that lost too many stars to be believed is left out"
    elif left_out:
        detail += f". {left_out} recent days that lost too many stars to be believed are left out"
    return {"line": f"{gained} · {pace}", "detail": detail + "."}


MADE_LATE = 2
"""How many days after its board day, by the date in UTC, a board's publish time must fall for its page to say that
the board was made after its day. The daily job publishes a board on its day, or early on the next."""


def daily_job(board: dict) -> dict | None:
    """When the day's update that published a board began, and how long it took to publish it, from the file's
    `daily_job_started_at` (RisingRepos#51).

    None when the file does not say: one published before the data contract had the field, or a board that no daily
    run published, whose field is null, or one whose update would have begun after its publish time. The page then
    says nothing about the update. Otherwise `started` is the field, `same_day` whether it falls on the publish
    time's day in UTC, `began` the time it began, with its date when it is not the same day, and `took` how long it
    took, in words.
    """
    started = board.get("daily_job_started_at")
    if not started:
        return None
    began, published = datetime.fromisoformat(started), datetime.fromisoformat(board["published_at"])
    if began > published:
        return None
    same_day = began.date() == published.date()
    return {
        "started": started,
        "same_day": same_day,
        "began": f"{began:%H:%M} UTC" if same_day else utc_time(started),
        "took": took(int((published - began).total_seconds())),
    }


def took(seconds: int) -> str:
    """59 seconds as 'less than a minute', 60 as '1 minute', 125 minutes as '2 hours and 5 minutes'."""
    hours, minutes = divmod(seconds // 60, 60)
    if not hours:
        if not minutes:
            return "less than a minute"
        return "1 minute" if minutes == 1 else f"{minutes} minutes"
    spent = "1 hour" if hours == 1 else f"{hours} hours"
    if not minutes:
        return spent
    return f"{spent} and " + ("1 minute" if minutes == 1 else f"{minutes} minutes")


def made_late(board: dict) -> bool:
    """Whether a board was published `MADE_LATE` days or more after its board day, as the boards made from the
    archive's earlier days were."""
    published = datetime.fromisoformat(board["published_at"]).date()
    return (published - date.fromisoformat(board["board_day"])).days >= MADE_LATE


def script_hash(text: str) -> str:
    """How a Content-Security-Policy names an inline script of exactly `text`: 'sha256-' and its digest in base64."""
    return "sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")


def build(out: Path, *, data: Path = DATA, noindex: bool) -> None:
    """Check the data files in `data`, then write the site's pages into `out`, a folder that does not exist yet
    or is empty. Nothing is written when a file fails its check.

    With `noindex`, every page asks search engines not to index it.
    """
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise FileExistsError(f"{out} already exists and is not an empty folder. Build into a new one.")
    boards = read_boards(data)
    templates = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    templates.filters.update(
        long_date=long_date,
        long_dates=long_dates,
        short_date=short_date,
        day_in_month=day_in_month,
        month_name=month_name,
        utc_time=utc_time,
        thousands="{:,}".format,
        repositories=repositories,
        day_address=day_address,
        why=why,
    )
    common = {
        "newest": boards[0],
        "days_address": address(DAYS),
        "how_address": address(HOW_IT_WORKS),
        "noindex": noindex,
        "script_hash": script_hash(templates.get_template(SCRIPT).render()),
    }
    # Each template is told its own name, which page.html reads to decide whether the page carries the notice.
    pages = {
        written: templates.get_template(PAGES[page]).render(**context, **common, template=PAGES[page])
        for written, page, context in _pages(boards)
    }
    for path, page in pages.items():
        (out / path).parent.mkdir(parents=True, exist_ok=True)
        (out / path).write_text(page, encoding="utf-8", newline="\n")


def _pages(boards: list[dict]) -> Iterator[tuple[str, str, dict]]:
    """Each page the build writes: its path in the site, its entry in `PAGES`, and what its template is given."""
    yield BOARD, BOARD, _beside(boards, 0)
    for number, board in enumerate(boards):
        yield board_day_page(board["board_day"]), BOARD_DAY, _beside(boards, number)
    by_month = groupby(boards, key=lambda board: board["board_day"][:7])  # newest first, as the index is
    yield DAYS, DAYS, {"boards": boards, "months": [(month, list(days)) for month, days in by_month]}
    yield HOW_IT_WORKS, HOW_IT_WORKS, {"described": DESCRIBED_FORMULA}
    yield NOT_FOUND, NOT_FOUND, {}


def _beside(boards: list[dict], number: int) -> dict:
    """What a board's page is given: the board, what it says about partial days and about the day's update, whether
    it was made after its day, and the board days before it and after it, when there are."""
    return {
        "board": boards[number],
        "partial": partial_days(boards[number]),
        "job": daily_job(boards[number]),
        "late": made_late(boards[number]),
        "before": boards[number + 1] if number + 1 < len(boards) else None,
        "after": boards[number - 1] if number > 0 else None,
    }
