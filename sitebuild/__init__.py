"""The site's generator: checks the data files against the data contract, then renders the site's pages.

Public helpers for paths, formatting, cross-board history, and charts live in their own modules (`paths`,
`formatting`, `history`, `charts`) and are re-exported here so existing callers and tests keep one entry point (#252).
"""

import base64
import hashlib
import json
import re
import shutil
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from functools import cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

from sitebuild import agent_copy, crawl, repo_list, share
from sitebuild.charts import LABELLED, TOP, _ticks, pace_chart
from sitebuild.contract import boards as read_boards
from sitebuild.formatting import (
    MADE_LATE,
    MINUS,
    MONTHS,
    NEW_UNTOLD,
    PACE_SCALE,
    WEEKDAYS,
    clock,
    daily_job,
    day_in_month,
    day_name,
    figure,
    gain_class,
    gained,
    growth,
    holds,
    lacked_days,
    licence_label,
    listed,
    long_date,
    long_dates,
    made_late,
    month_name,
    new_means,
    own_pace,
    partial_days,
    per_day,
    per_day_class,
    repositories,
    rounded,
    short_date,
    signed,
    star_run,
    times,
    took,
    utc_time,
    why,
    why_none,
)
from sitebuild.history import (
    ABOUT,
    HISTORY_WINDOW,
    RAMP,
    WINDOW,
    Band,
    History,
    band_name,
    bands_of,
    before_words,
    calendar,
    comparable,
    drawing_words,
    facts,
    held_bands,
    history_file,
    month_words,
)
from sitebuild.paths import (
    BASELINE,
    BASELINE_NAME,
    BOARD,
    BOARD_DAY,
    DATA,
    DAYS,
    DESCRIBED_FORMULA,
    FOR_AGENTS,
    HOW_IT_WORKS,
    NOT_FOUND,
    PAGES,
    SHARE_IMAGE,
    SITE,
    STATIC,
    TEMPLATES,
    address,
    board_day_page,
    day_address,
)

__all__ = [
    "ABOUT",
    "BASELINE",
    "BASELINE_NAME",
    "BOARD",
    "BOARD_DAY",
    "DATA",
    "DAYS",
    "DESCRIBED_FORMULA",
    "FACES",
    "FONTS",
    "FOR_AGENTS",
    "HISTORY_WINDOW",
    "HOW_IT_WORKS",
    "LABELLED",
    "MADE_LATE",
    "MINUS",
    "MONTHS",
    "NEW_UNTOLD",
    "NOT_FOUND",
    "PACE_SCALE",
    "PAGES",
    "RAMP",
    "SHARE_IMAGE",
    "SITE",
    "STATIC",
    "TEMPLATES",
    "TOP",
    "WEEKDAYS",
    "WINDOW",
    "Band",
    "History",
    "_ticks",
    "address",
    "band_name",
    "bands_of",
    "before_words",
    "board_day_page",
    "build",
    "calendar",
    "clock",
    "comparable",
    "daily_job",
    "day_address",
    "day_in_month",
    "day_name",
    "drawing_words",
    "environment",
    "facts",
    "figure",
    "font_faces",
    "gain_class",
    "gained",
    "growth",
    "held_bands",
    "history_file",
    "holds",
    "lacked_days",
    "licence_label",
    "listed",
    "long_date",
    "long_dates",
    "made_late",
    "month_name",
    "month_words",
    "new_means",
    "own_pace",
    "pace_chart",
    "partial_days",
    "per_day",
    "per_day_class",
    "repositories",
    "rounded",
    "script_hash",
    "share_lines",
    "short_date",
    "signed",
    "star_run",
    "times",
    "took",
    "unquoted",
    "utc_time",
    "why",
    "why_none",
]


def share_lines(board: dict) -> list[share.Line]:
    """The lines of a board day's share image: its board day in words, and the full names of its first three rows,
    in the file's order (B1)."""
    return share.layout(long_date(board["board_day"]), [row["full_name"] for row in board["rows"][:3]])


FONTS = Path(__file__).parent / "fonts"
# Modified versions of IBM Plex Sans and IBM Plex Mono, renamed by sitebuild/fonts/subset.py.
FACES = [
    ("Rising Sans", 400, "rising-sans-400"),
    ("Rising Sans", 500, "rising-sans-500"),
    ("Rising Mono", 400, "rising-mono-400"),
    ("Rising Mono", 500, "rising-mono-500"),
]


@cache
def font_faces() -> Markup:
    """The four faces' @font-face rules, each file inside the page as a data: URI, so a page is one request
    and no font file is fetched or published. The files are sitebuild/fonts/subset.py's, cut to the site's own
    characters.

    A face inside the page is still ready a few milliseconds after the page is first drawn. Each face holds its
    text back until then, with `font-display: block`, and is not drawn in the fallback first. Drawn there and
    then again in its own face, a name near the end of its line took another number of lines, and every row under
    it moved."""
    rules = []
    for family, weight, name in FACES:
        data = base64.b64encode((FONTS / f"{name}.woff2").read_bytes()).decode("ascii")
        rules.append(
            f'@font-face {{ font-family: "{family}"; src: url(data:font/woff2;base64,{data}) format("woff2"); '
            f"font-weight: {weight}; font-display: block; }}"
        )
    return Markup("\n".join(rules))


TAG = re.compile(r"<[a-z][^<>]*>")
BARE = re.compile(r'(\s[a-z][a-z-]*)="([A-Za-z0-9_.:-]+)"(?!/)')  # not before "/>", which would join the value


def unquoted(page: str) -> str:
    """The page with the quotes taken off each attribute value in <body> that needs none: a value of
    letters, digits, and _ . : - only, which HTML reads the same with or without quotes, so the page's elements are
    exactly as before. Only the tags change, never text, and the head, with its policy, style, and script, is left as
    written. Each row repeats its attributes, so this cuts about 16 KB from a 274-row board, if only some 300 bytes
    gzipped."""
    head, body = page.split("<body>", 1)
    return head + "<body>" + TAG.sub(lambda tag: BARE.sub(r"\1=\2", tag.group(0)), body)


def script_hash(text: str) -> str:
    """How a Content-Security-Policy names an inline script of exactly `text`: 'sha256-' and its digest in base64."""
    return "sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")


def environment() -> Environment:
    """The templates, as the build renders them: every value escaped, an undefined name an error, and a line that
    holds only a tag or a comment left out whole. The notes on the stylesheet and the scripts are Jinja comments, so
    they stay in the templates and no page carries them."""
    return Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


@cache
def _render_environment() -> Environment:
    """The configured Jinja2 environment, cached across builds in the same process so repeated builds in the test
    suite do not recompile every template (#253)."""
    templates = environment()
    templates.filters.update(
        long_date=long_date,
        new_means=new_means,
        long_dates=long_dates,
        short_date=short_date,
        day_in_month=day_in_month,
        month_name=month_name,
        utc_time=utc_time,
        clock=clock,
        took=took,
        listed=listed,
        thousands="{:,}".format,
        repositories=repositories,
        day_address=day_address,
        why=why,
        growth=growth,
        per_day=per_day,
        gained=gained,
        gained_class=lambda row: gain_class(row.get("gained_1_day")),
        per_day_class=per_day_class,
        own_pace=own_pace,
        baseline_figure=lambda value: figure(value, 2),
        script_hash=lambda text: script_hash(str(text)),
    )
    return templates


def build(out: Path, *, data: Path = DATA, noindex: bool, share_images: bool = True) -> None:
    """Check the data files in `data`, then write the site's pages into `out`, a folder that does not exist yet
    or is empty. Nothing is written when a file fails its check.

    With `noindex`, every page asks search engines not to index it. With `share_images` false, each board day's
    `share.png` is skipped, which lets tools that read only the HTML pages run faster (#253).
    """
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise FileExistsError(f"{out} already exists and is not an empty folder. Build into a new one.")
    boards = read_boards(data)
    templates = _render_environment()
    common = {
        "newest": boards[0],
        "days_address": address(DAYS),
        "how_address": address(HOW_IT_WORKS),
        "agents_address": address(FOR_AGENTS),
        "new_untold": NEW_UNTOLD,
        "noindex": noindex,
        "baseline_address": address(BASELINE),
        "baseline_name": BASELINE_NAME,
        "top": TOP,
        "font_faces": font_faces(),
    }
    history = History(boards)
    guide = agent_copy.guide(boards, history)
    # Each template is told its own name, which page.html reads to decide whether the page carries the notice.
    pages = {
        written: templates.get_template(PAGES[page]).render(
            **context, **common, **guide, site=SITE, **_card(written, page, context, boards[0]), template=PAGES[page]
        )
        for written, page, context in _pages(boards, history)
    }
    for path, page in pages.items():
        (out / path).parent.mkdir(parents=True, exist_ok=True)
        (out / path).write_text(unquoted(page), encoding="utf-8", newline="\n")
    shutil.copytree(STATIC, out / "static")
    # Each board day's share image, which a link's card shows, and its history of its rows, which its expanded rows
    # fetch on first opening. Share images are drawn in parallel because Pillow releases the GIL while encoding PNGs
    # (#253); layouts are computed upfront so the cached FreeType font objects stay on the main thread.
    if share_images:
        planned = [(out / board_day_page(board["board_day"]), share.render(share_lines(board))) for board in boards]

        def write_share(item: tuple[Path, object]) -> None:
            page, image = item
            page.with_name(SHARE_IMAGE).write_bytes(share.encode(image))

        with ThreadPoolExecutor() as pool:
            list(pool.map(write_share, planned))
    for number, board in enumerate(boards):
        if board["rows"]:
            (out / board_day_page(board["board_day"])).with_name("history.json").write_text(
                json.dumps(history_file(boards, history, number), separators=(",", ":")), encoding="utf-8"
            )
    # What a crawler reads: the sitemap, and the site's own robots.txt (#170).
    (out / "sitemap.xml").write_text(crawl.sitemap(boards), encoding="utf-8", newline="\n")
    (out / "robots.txt").write_text(crawl.robots(noindex=noindex), encoding="utf-8", newline="\n")
    # What a visiting agent reads: each board again, as text and as JSON (#176).
    for path, text in agent_copy.copies(boards, history).items():
        (out / path).write_text(text, encoding="utf-8", newline="\n")
    # What the query service reads: every repository that has been on a board, with its history (#177).
    (out / "repos.tsv").write_text(repo_list.repo_list(boards), encoding="utf-8", newline="\n")
    # What a visiting agent finds first, and what tells it the above is there (#178).
    # The file is plain text, so the templates' escaping, which would turn each apostrophe into an entity, is
    # not wanted: every value of the guide is the build's own fixed words, and no repository's owner wrote any of
    # them. A template may not switch the escaping off (P5), so each value is marked as safe for this one render.
    plain = {
        key: [Markup(v) for v in value] if isinstance(value, list) else Markup(value) for key, value in guide.items()
    }
    llms = templates.get_template("llms.txt").render(**common, site=SITE, **plain)
    (out / "llms.txt").write_text(llms, encoding="utf-8", newline="\n")


def _card(written: str, page: str, context: dict, newest: dict) -> dict:
    """What a page's card and canonical address name, by the page's kind, and never by whether it is given a board:
    Baseline is given the newest. The root's canonical address is the newest board day's own page, which shows the
    same board, and the page for an address that holds none has no address of its own. A board day's page names its
    own share image, and every other page the newest board day's."""
    day = context["board"]["board_day"] if page in (BOARD, BOARD_DAY) else newest["board_day"]
    own = {BOARD: day_address(day), NOT_FOUND: None}.get(page, address(written))
    return {
        "canonical": own and SITE + own,
        "share_image": SITE + day_address(day) + SHARE_IMAGE,
        "share_size": (share.WIDTH, share.HEIGHT),
    }


def _pages(boards: list[dict], history: History) -> Iterator[tuple[str, str, dict]]:
    """Each page the build writes: its path in the site, its entry in `PAGES`, and what its template is given."""
    yield BOARD, BOARD, _beside(boards, 0, history)
    for number, board in enumerate(boards):
        yield board_day_page(board["board_day"]), BOARD_DAY, _beside(boards, number, history)
    cal = calendar(boards, history)
    yield (
        DAYS,
        DAYS,
        {
            "boards": boards,
            "calendar": cal,
            "years": sorted({month["month"][:4] for month in cal}, reverse=True),
            "ramp": RAMP,
        },
    )
    yield HOW_IT_WORKS, HOW_IT_WORKS, {"described": DESCRIBED_FORMULA, "bands": bands_of(boards[0])}
    yield FOR_AGENTS, FOR_AGENTS, {}
    yield BASELINE, BASELINE, {"board": boards[0], "chart": pace_chart(boards[0]["rows"])}
    yield NOT_FOUND, NOT_FOUND, {}


def _beside(boards: list[dict], number: int, history: History) -> dict:
    """What a board's page is given: the board, what it says about the bands it holds back, the days its ranking
    lacked, why it lists no row when it lists none, its partial days, the day's update, whether it was made after its
    day, and the board days before it and after it, when there are."""
    board = boards[number]
    lacked = lacked_days(board)
    bands = bands_of(board)
    return {
        "board": board,
        "held": holds(board),
        "lacked": lacked,
        "why_none": why_none(board, lacked),
        "partial": partial_days(board),
        "job": daily_job(board),
        "late": made_late(board),
        "before": boards[number + 1] if number + 1 < len(boards) else None,
        "after": boards[number - 1] if number > 0 else None,
        "history_address": day_address(board["board_day"]) + "history.json",
        "languages": sorted({row["language"] for row in board["rows"] if row.get("language")}, key=str.casefold),
        "history": history.rows(number),
        "bands": bands,
        "held_bands": held_bands(board, bands),
    }
