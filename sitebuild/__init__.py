"""The site's generator: checks the data files against the data contract, then renders the site's pages."""

from collections.abc import Iterator
from datetime import date, datetime
from itertools import groupby
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from sitebuild.contract import boards as read_boards

TEMPLATES = Path(__file__).parent / "templates"
DATA = Path(__file__).resolve().parent.parent / "site-data"

BOARD = "index.html"
DAYS = "days/index.html"
BOARD_DAY = "days/{board_day}/index.html"
NOT_FOUND = "404.html"

PAGES = {
    BOARD: "latest.html",
    DAYS: "days.html",
    BOARD_DAY: "board.html",
    NOT_FOUND: "not-found.html",
}
"""Each page the build writes, by its path in the site, and the template in templates/ that renders it.

- `BOARD`, the site's root, is the newest board day's board. It is the one page that states its board day in the
  data contract's two meta tags, which latest.html adds to board.html, so whatever reads them reads the root.
- `DAYS` lists every board day, newest first.
- `BOARD_DAY` is written once for each board day in the index, the newest included, so that each board day keeps
  one address however many come after it.
- Cloudflare Pages answers an address that holds no page with `NOT_FOUND` and the status 404. A site with no
  404.html at its root is taken for a single-page app, and every such address gets the root page and the
  status 200.
"""

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
    )
    common = {"newest": boards[0], "days_address": address(DAYS), "noindex": noindex}
    pages = {
        written: templates.get_template(PAGES[page]).render(**context, **common)
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
    yield NOT_FOUND, NOT_FOUND, {}


def _beside(boards: list[dict], number: int) -> dict:
    """What a board's page is given: the board, what it says about partial days, and the board days before it and
    after it, when there are."""
    return {
        "board": boards[number],
        "partial": partial_days(boards[number]),
        "before": boards[number + 1] if number + 1 < len(boards) else None,
        "after": boards[number - 1] if number > 0 else None,
    }
