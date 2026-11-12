"""The site's generator: checks the data files against the data contract, then renders the site's pages."""

from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from sitebuild.contract import latest_board

TEMPLATES = Path(__file__).parent / "templates"
DATA = Path(__file__).resolve().parent.parent / "site-data"

BOARD = "index.html"
NOT_FOUND = "404.html"

PAGES = {
    BOARD: "board.html",
    NOT_FOUND: "not-found.html",
}
"""Each page the build writes, by its path in the site, and the template in templates/ that renders it.

- `BOARD`, the site's root, is the board.
- Cloudflare Pages answers an address that holds no page with `NOT_FOUND` and the status 404. A site with no
  404.html at its root is taken for a single-page app, and every such address gets the root page and the
  status 200.
"""

MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def long_date(day: str) -> str:
    """'2026-11-09' as '9 November 2026'."""
    value = date.fromisoformat(day)
    return f"{value.day} {MONTHS[value.month - 1]} {value.year}"


def utc_time(moment: str) -> str:
    """'2026-11-10T00:41:07Z' as '10 November 2026 at 00:41 UTC'."""
    value = datetime.fromisoformat(moment)
    return f"{long_date(value.date().isoformat())} at {value:%H:%M} UTC"


def repositories(count: int) -> str:
    """5 as '5 repositories', 1 as '1 repository', and 0 as 'No repositories'."""
    if count == 0:
        return "No repositories"
    return "1 repository" if count == 1 else f"{count:,} repositories"


def build(out: Path, *, data: Path = DATA, noindex: bool) -> None:
    """Check the data files in `data`, then write the site's pages into `out`, a folder that does not exist yet
    or is empty. Nothing is written when a file fails its check.

    With `noindex`, every page asks search engines not to index it.
    """
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise FileExistsError(f"{out} already exists and is not an empty folder. Build into a new one.")
    board = latest_board(data)
    templates = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    templates.filters.update(long_date=long_date, utc_time=utc_time, thousands="{:,}".format, repositories=repositories)
    pages = {path: templates.get_template(name).render(board=board, noindex=noindex) for path, name in PAGES.items()}
    out.mkdir(parents=True, exist_ok=True)
    for path, page in pages.items():
        (out / path).write_text(page, encoding="utf-8", newline="\n")
