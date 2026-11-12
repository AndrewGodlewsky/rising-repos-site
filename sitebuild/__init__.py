"""The site's generator: checks the data files against the data contract, then renders the first page."""

from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from sitebuild.contract import latest_board

TEMPLATES = Path(__file__).parent / "templates"
DATA = Path(__file__).resolve().parent.parent / "site-data"

DESIGNS = (
    "register",
    "chart",
)
"""The designs of the first page, each a template and a stylesheet of that name in templates/. The first is
built at the site's root, and each other one under /<name>/. Issue #71 in RisingRepos keeps one."""

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
    """Check the data files in `data`, then write every design of the first page into `out`, a folder that does
    not exist yet or is empty. Nothing is written when a file fails its check.

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
    pages = {name: templates.get_template(f"{name}.html").render(board=board, noindex=noindex) for name in DESIGNS}
    for name, page in pages.items():
        folder = out if name == DESIGNS[0] else out / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(page, encoding="utf-8", newline="\n")
