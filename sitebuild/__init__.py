"""The site's generator: checks the data files against the data contract, then renders the site's pages."""

import base64
import hashlib
import json
import math
import re
import shutil
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import NamedTuple

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

from sitebuild import share
from sitebuild.contract import boards as read_boards

TEMPLATES = Path(__file__).parent / "templates"
STATIC = Path(__file__).parent / "static"
"""Files served as they are, under /static/. The type is inside each page, so the fonts' folder holds only
OFL.txt: the copyright notice and the SIL Open Font License, which the licence asks to travel with the fonts."""
DATA = Path(__file__).resolve().parent.parent / "site-data"

BOARD = "index.html"
DAYS = "days/index.html"
BOARD_DAY = "days/{board_day}/index.html"
HOW_IT_WORKS = "how-it-works/index.html"
FOR_AGENTS = "for-agents/index.html"
BASELINE = "baseline/index.html"
BASELINE_NAME = "Baseline"
"""The Baseline page's name, as the site's bar and the page's own strip show it: change it here to rename the page."""
NOT_FOUND = "404.html"
SHARE_IMAGE = "share.png"
"""A board day's share image, written beside its page (sitebuild/share.py)."""
SITE = "https://risingrepos.com"
"""The site's own address. A card and a canonical address name a page by its whole address, since what reads them,
a crawler or a search engine, reads them away from the page (#35). The preview's pages name the live site's too."""

PAGES = {
    BOARD: "latest.html",
    DAYS: "days.html",
    BOARD_DAY: "board.html",
    HOW_IT_WORKS: "how-it-works.html",
    FOR_AGENTS: "for-agents.html",
    BASELINE: "baseline.html",
    NOT_FOUND: "not-found.html",
}
"""Each page the build writes, by its path in the site, and the template in templates/ that renders it.

- `BOARD`, the site's root, is the newest board day's board. It is the one page that states its board day in the
  data contract's two meta tags, which latest.html adds to board.html, so whatever reads them reads the root.
- `DAYS` lists every board day, newest first.
- `BOARD_DAY` is written once for each board day in the index, the newest included, so that each board day keeps
  one address however many come after it.
- `HOW_IT_WORKS` says in a few plain sentences how the boards are ranked, for the formula `DESCRIBED_FORMULA`
  names, and what the site is set in.
- `BASELINE` draws each repository on the newest board by its baseline against its recent pace, and lists them.
- Every page links to the list, to Baseline, and to How it works from the site's bar.
- Cloudflare Pages answers an address that holds no page with `NOT_FOUND` and the status 404. A site with no
  404.html at its root is taken for a single-page app, and every such address gets the root page and the
  status 200.

page.html names the templates whose pages carry the notice of an old board: every one but not-found.html and
how-it-works.html, whose text the notice's hiding of an old board would hide.
"""

DESCRIBED_FORMULA = 2
"""The version of the scoring formula that how-it-works.html describes. Its page says so, and says plainly when the
newest board was ranked by another, so that a new formula in RisingRepos never leaves the page describing the wrong
one unnoticed."""

MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
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


def share_lines(board: dict) -> list[share.Line]:
    """The lines of a board day's share image: its board day in words, and the full names of its first three rows,
    in the file's order (B1)."""
    return share.layout(long_date(board["board_day"]), [row["full_name"] for row in board["rows"][:3]])


def long_date(day: str) -> str:
    """'2026-11-09' as '9 November 2026'."""
    value = date.fromisoformat(day)
    return f"{value.day} {MONTHS[value.month - 1]} {value.year}"


def new_means(since: str) -> str:
    """What New means on a board, back to the first board day `since`, in the words of the page's About this board and
    of the agent copy's header, so that the two say it from one place (#176)."""
    return (
        f"New means under a name on none of the boards before this one, back to the first on {long_date(since)}. "
        "A repository renamed or moved since counts as new, and its opened row still lists the boards it was on before."
    )


NEW_UNTOLD = (
    "What is new on this board cannot be told: the board before it held a star band back or listed no repository, "
    "so one missing from it may have been kept off."
)
"""What About this board says when New cannot be told, which the agent copy's header says too (#176)."""


def listed(items: list[str], last: str = "and") -> str:
    """['A'] as 'A', two joined by `last`, as 'A and B', and three as 'A, B, and C'."""
    if len(items) < 3:
        return f" {last} ".join(items)
    return ", ".join(items[:-1]) + f", {last} " + items[-1]


def long_dates(days: list[str]) -> str:
    """['2026-11-09'] as '9 November 2026', two days joined by 'and', and three as 'A, B, and C'."""
    return listed([long_date(day) for day in days])


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
    return f"{long_date(value.date().isoformat())} at {clock(moment)}"


def clock(moment: str) -> str:
    """'2026-11-10T00:41:07Z' as '00:41 UTC'."""
    return f"{datetime.fromisoformat(moment):%H:%M} UTC"


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
    Otherwise `recent` lists, newest first as the file does, the other days over which the ranking measures a recent
    pace, but for any the file names as a day the ranking lacked (`lacked_days`), whose own note states it. `earlier`
    is how many days the ranking reads only further back, and `oldest` and `newest` the span they fall in, so that the
    page words one day and many alike.
    """
    if "partial_days" not in board:
        return None
    days = board["partial_days"]
    lacked = {day["snapshot_day"] for day in board.get("unranked", [])}
    earlier = [day["snapshot_day"] for day in days if not day["recent"]]
    return {
        "recent": [
            day["snapshot_day"]
            for day in days
            if day["recent"] and day["snapshot_day"] != board["board_day"] and day["snapshot_day"] not in lacked
        ],
        "earlier": len(earlier),
        "oldest": min(earlier, default=None),
        "newest": max(earlier, default=None),
    }


def before_holds(board: dict) -> dict | None:
    """What the page of a file published before the data contract had a board's `state`, `holds`, `missed_stars`, and
    `unranked` (AndrewGodlewsky/RisingRepos#13) needs to word its recent partial days as it did before them: `own`,
    whether the board day was itself partial. Such a file does not say what a recent day did, so its page says what
    the day may have done.

    None for a file that has those fields, which come together: its page takes the notes of `holds` and `lacked_days`
    instead. Each board day is published again with them, and this and its one block in board.html can go once no
    file in site-data/ lacks them.
    """
    if "state" in board:
        return None
    return {"own": any(day["snapshot_day"] == board["board_day"] for day in board.get("partial_days", []))}


def lacked_days(board: dict) -> list[dict]:
    """Each day the board's ranking needed and lacked, as its file names it (`unranked`,
    AndrewGodlewsky/RisingRepos#13), with its `kind`, told once here for the notes in the band and for the message
    under a board with no row:

    - "missing": no snapshot was kept that day, so no repository could be ranked;
    - "unranked": its snapshot was partial and missed `repositories` that the ranking could otherwise have ranked;
    - "partial": its snapshot was partial but missed none of those.

    Empty for a file older than the field.
    """
    return [
        {
            "day": day["snapshot_day"],
            "repositories": day["repositories"],
            "kind": "missing" if day["status"] == "missing" else "unranked" if day["repositories"] else "partial",
        }
        for day in board.get("unranked", [])
    ]


def why_none(board: dict, lacked: list[dict]) -> str | None:
    """Why a board that lists no row lists none, as the message under it says, so that a board held back, or one whose
    ranking lacked a day, never reads as a day on which nothing rose (AndrewGodlewsky/RisingRepos#13): "held" when it
    holds a star band; otherwise "missing" or "unranked" when one of the days its ranking lacked (`lacked`, as
    `lacked_days` gives them) is of that kind, a missing day first; and "none" when nothing kept a repository off, as
    for a file older than those fields. None for a board that lists rows."""
    if board["rows"]:
        return None
    if board.get("state") == "held":
        return "held"
    kinds = {day["kind"] for day in lacked}
    return next((kind for kind in ("missing", "unranked") if kind in kinds), "none")


def star_run(run: dict) -> str:
    """A run of star counts as a file gives it, in words: 1,000 to 2,999; 30,000 or more, for a run with no most;
    and 281, for a run of one count."""
    least, most = run["least_stars"], run["most_stars"]
    if most is None:
        return f"{least:,} or more"
    return f"{least:,}" if most == least else f"{least:,} to {most:,}"


def holds(board: dict) -> dict | None:
    """What a board's page says about the star bands its board holds back (AndrewGodlewsky/RisingRepos#13): each
    band whose rows are left off, as `bands`, and each run of star counts the board day's own snapshot missed, as
    `missed`, which is why, both lowest first in words, as the file gives them.

    None when the board holds none, and when its file is older than the field: the page then says nothing of a
    hold. The site decides no hold. RisingRepos decides each from its record of the board day's snapshot, and the
    file names the bands and the counts.
    """
    if board.get("state") != "held":
        return None
    return {
        "bands": [star_run(band) for band in board["holds"]],
        "missed": [star_run(run) for run in board["missed_stars"]],
    }


def rounded(value: float, places: int) -> Decimal:
    """`value` to `places` decimal places, a half rounded up, as a reader rounds: 10.5 to none as 11, and 8.125 to
    two as 8.13. It rounds the number as JSON wrote it, not its nearest binary fraction, which may lie below it."""
    return Decimal(repr(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


MINUS = "\N{MINUS SIGN}"
"""What a figure below 0 is written with (AndrewGodlewsky/RisingRepos#199): the true minus, which the site's type
draws as wide as the plus and the figures, not the hyphen. A loss takes it, and so does a pace that was falling."""


def figure(value: float, places: int) -> str:
    """A number to at most `places` decimal places, with thousands parted by commas, no zero at the end, and the true
    minus below 0: 260.0 as '260', 30.1667 to two places as '30.17', 1285.909 to two places as '1,285.91', and -3.421
    to two places as '−3.42'. The sign is the rounded figure's, so one that rounds to 0 takes none: -0.004 to two
    places is '0'. Every figure the site writes, a gain's or a loss's among them, takes its sign here."""
    number = rounded(value, places)
    text = f"{abs(number) if number == 0 else number:,}".replace("-", MINUS)
    return text.rstrip("0").rstrip(".") if "." in text else text


def times(score: float) -> str:
    """A score as a multiple of a usual pace, without a cap: to one decimal place under 10, and a whole number from
    10, which needs no decimal to read. 8.63 as '8.6', 4.0 as '4', 9.96 as '10', and 1285.9 as '1,286'. Its places go
    by size, so a figure below 0 takes them as the same figure above 0 does: -12.34 as '−12'."""
    return figure(score, 1) if abs(rounded(score, 1)) < 10 else figure(score, 0)


def why(row: dict) -> dict:
    """Why a row's repository is on its board, in words, from the numbers its file gives the row as its score worked
    them out (AndrewGodlewsky/RisingRepos#49): `line` for the row, and `detail`, the score and the sum it came from,
    for the row's expanded view, with `gained`, the line's first half, and `above`, the stars above its own trend or
    None, which the opened row's drawing labels itself with. The site works out no score: it rounds what it shows, and
    tells from the numbers which of these the row is.

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
    written = figure(stars, 0)
    total = f"Score {figure(score, 2)} = {written} stars ÷ {span} ÷ {figure(divisor, 2)}"
    if baseline >= divisor:
        pace = f"{times(score)}× its usual pace"
        detail = f"That multiple is its score: {written} stars ÷ {span} ÷ its usual {figure(baseline, 2)} a day"
    elif baseline >= 0:
        pace = f"its usual pace was under {floor}"
        detail = f"{total}: its usual {figure(baseline, 2)} a day counts as {floor}"
    else:
        pace = "it had been losing stars"
        detail = f"{total}: it lost {figure(-baseline, 2)} a day before, which counts as {floor}"
    left_out = row["days_left_out"]
    # The excess is the stars above its own trend only when it covers every recent day and the pace was not falling.
    above = None if left_out or baseline < 0 else figure(row["excess"], 0)
    gained = f"{signed(written)} in {span}" if above is None else f"{signed(above)} above its own trend"
    if left_out == 1:
        detail += ". A recent day that lost too many stars to be believed is left out"
    elif left_out:
        detail += f". {left_out} recent days that lost too many stars to be believed are left out"
    return {"line": f"{gained} · {pace}", "detail": detail + ".", "gained": gained, "above": above}


def growth(row: dict) -> dict:
    """A row's growth, as the Baseline page's table and an opened row give it: the multiple the ranking itself uses,
    its recent pace over its baseline, in the file's own numbers, or, where the file gives no honest multiple, what it
    does give. `multiple` is the score written as a multiple ('130×') when the repository's baseline was at least the
    floor it was divided by; otherwise None, and `pace` is its score, its recent stars a day, since a baseline under
    the floor counts as the floor of 1, with `note` saying why. The site computes nothing: it rounds the score the
    file gives, as `times` and `figure` do."""
    score, baseline, divisor = row["score"], row["baseline"], row["divided_by"]
    if baseline >= divisor:
        return {"multiple": f"{times(score)}×", "pace": None, "note": None}
    return {
        "multiple": None,
        "pace": f"{figure(score, 1)} a day",
        "note": "baseline under 1 a day" if baseline >= 0 else "it had been losing stars",
    }


def signed(written: str) -> str:
    """A gain as the site writes it, from the figure `figure` or `times` wrote: a plus before a figure above 0, and a
    loss and 0 as the figure is, with its true minus or bare. A gain that rounds to 0 is '0', never '+0'."""
    return written if written == "0" or written.startswith(MINUS) else "+" + written


def gain_class(number: float | None) -> str:
    """The class a gain's cell takes beside its own (AndrewGodlewsky/RisingRepos#199): ' loss' for a loss, which the
    stylesheet sets in the red, and ' nil' for 0 or no count, which it sets in the second ink, since the green is for
    what a repository gained. Nothing for a gain."""
    if number is None or number == 0:
        return " nil"
    return " loss" if number < 0 else ""


def gained(row: dict) -> str:
    """The growth column when the board's file gives `gained_1_day` (RisingRepos#194): the stars the repository gained
    on the board day, as '+147', '0', or '−600' for a loss, and '–' when the file has no count for the day before."""
    gain = row.get("gained_1_day")
    if gain is None:
        return "–"
    return signed(figure(gain, 0))


def per_day(row: dict) -> str:
    """The growth column when the board's file has no `gained_1_day`: the stars a day the repository gained over its
    recent days, the board day and the day before, or the one of them the loss rule kept, as '+148'. The same unit on
    every row, which its total over the two days would not be when a day is left out. Whole from 10, to one place
    below, as `times` rounds: 295 in 2 days as '+148', and 13 in 2 days as '+6.5'. The contract does not bar a loss
    over the recent days, which is written as a loss is on the board day."""
    return signed(times(row["recent_stars"] / row["recent_days"]))


def per_day_class(row: dict) -> str:
    """The class of `per_day`'s cell, as `gain_class` gives it: a board's growth column, and an opened row's table."""
    return gain_class(row["recent_stars"] / row["recent_days"])


PACE_SCALE = (0.5, 5000)
"""The stars a day the row's small chart spans, bottom to top, on a log scale: the same for every row of every board,
so that two rows' charts compare. A pace under the bottom, a falling one among them, sits on the bottom."""


def own_pace(row: dict) -> dict:
    """A row's own pace against what it gained, small, as the worked example of How it works draws it: across the 14
    days, the dashed level of its usual pace, its baseline a day, as it would have gone on; over its recent days, the
    last two or the one the loss rule kept, the level of its recent pace; and the part between shaded. Both levels are
    stars a day on one log scale, `PACE_SCALE`, shared by every row, so the gap reads as its multiple and the height as
    its size. The file gives averages for the two windows, not a count for each day, so each is one level.

    The stylesheet draws it from `style`, two custom properties of the cell: `--u` and `--r`, how far down the box
    each level sits, from 0 to 1, and `--e`, where the recent run ends, when a day was left out. Two numbers cost a
    row about a sixth of what an SVG of the same drawing does. Its `text` gives the usual pace to two places, and the
    recent pace as the growth column writes stars a day, so an opened row's table of days says the same."""
    baseline, gained, days = row["baseline"], row["recent_stars"], row["recent_days"]
    low, high = (math.log10(value) for value in PACE_SCALE)

    def down(pace: float) -> str:
        at = (math.log10(min(max(pace, PACE_SCALE[0]), PACE_SCALE[1])) - low) / (high - low)
        return f"{0.05 + (1 - at) * 0.9:.2f}"

    style = f"--u:{down(baseline)};--r:{down(gained / days)}"
    if days != 2:
        style += f";--e:{(12 + days) / 14:.3f}"
    return {"style": style, "text": f"Usual {figure(baseline, 2)} a day, then {times(gained / days)} a day"}


HISTORY_WINDOW = 30
"""How many board days the expanded row's chart covers, its own board included."""


ABOUT = ("license", "created_at", "pushed_at")
"""The facts the data contract gives each row since AndrewGodlewsky/RisingRepos#197, by its names: its licence as an
SPDX id, which the owner chose and the contract marks untrusted, when it was created, and when it was last pushed to.
The opened row shows them from the history file, as text."""


def day_name(day: str) -> str:
    """A day as an opened row names it: '2026-11-09' as '9 Nov 2026'."""
    return f"{short_date(day)} {day[:4]}"


def band_name(bands: list[Band], stars: int) -> str:
    """The name of the band in `bands` that `stars` falls in, as a row's facts give it."""
    return next(band.name for band in bands if band.below is None or stars < band.below)


def facts(
    row: dict, on: list[list], days: list[str], first: str, was: str | None, about: bool, bands: list[Band]
) -> list:
    """An opened row's facts, each [term, value], or [term, value, 'loss'] for a gain that is a loss, which the
    stylesheet sets in the red: every one worded here, from the file, as the board words the same figures. `on` is the
    row's entries in its history and `days` the board days they are placed in; `first` is the first board that listed
    it and `was` its earlier name, as `History` finds them; `about` says whether the board gives a licence, creation, or
    last push for any row, and `bands` are the board's star bands."""
    told = []
    if "score" in row:
        grew = growth(row)
        told.append(["Multiple", grew["multiple"] or "None: " + grew["note"]])
    if "star_history" in row:
        for count, name in ((7, "gained_7_days"), (30, "gained_30_days")):
            gain = row.get(name)
            said = [f"Gained in {count} days", "Not known" if gain is None else signed(figure(gain, 0))]
            told.append([*said, "loss"] if gain is not None and gain < 0 else said)
    told.append(["Language", row.get("language") or "not given"])
    if about:
        told.append(["Licence", row.get("license") or "None given"])
    if bands:
        told.append(["Star band", band_name(bands, row["stars"])])
    for name, term in (("created_at", "Created"), ("pushed_at", "Last pushed")):
        if about and row.get(name):
            told.append([term, day_name(row[name][:10])])
    told.append(["First on a board", "This board" if first == days[-1] else day_name(first)])
    if was:
        told.append(["Listed before as", was])
    told.append([f"On the last {len(days)} boards", f"{len(on)} of {len(days)}"])
    told.append(["Best rank in them", str(min(entry[1] for entry in on))])
    return told


def drawing_words(row: dict) -> tuple[list, list[str]]:
    """What an opened row's drawing of its own pace against what it gained is drawn from and labelled with: the numbers
    its lines take, [its baseline a day, to two places, its recent stars, its recent days], and its words, [the label at
    the end of what it gained, the label at the end of its own pace, the label of its usual pace, and the whole of it
    in a sentence for a screen reader]. Its first label is the first half of the row's line, from `why`: a row whose
    recent pace kept one day, or that had been losing stars, is not above its own trend, so it gives what it gained.
    Every figure takes its sign as `figure` and `signed` give it."""
    baseline = float(rounded(row["baseline"], 2))
    gained, days = row["recent_stars"], row["recent_days"]
    reason = why(row)
    usual, own = figure(baseline, 2), times(days * baseline)
    sentence = (
        f"Over the 12 days before, its usual pace was {usual} stars a day. Over "
        f"{'the day kept' if days == 1 else 'the last 2 days'} it gained {figure(gained, 0)}, where its own pace "
        f"would have given {own}" + (f": {reason['above']} above its own trend." if reason["above"] else ".")
    )
    return [baseline, gained, days], [
        reason["gained"],
        f"At its own pace: {signed(own)}",
        f"Usual pace, {usual} a day",
        sentence,
    ]


def month_words(counts: list[int | None], day: str) -> list[str] | None:
    """The words of an opened row's line of its stars over the 31 days `counts` gives, to the board day `day`: [its
    first count and the day of it, its last count and the board day, and the whole of it in a sentence for a screen
    reader]. None when fewer than two days have a count, since there is no line to draw."""
    known = [count for count in counts if count is not None]
    if len(known) < 2:
        return None
    first = next(at for at, count in enumerate(counts) if count is not None)
    start = (date.fromisoformat(day) - timedelta(days=len(counts) - 1 - first)).isoformat()
    missing = len(counts) - len(known)
    uncounted = f", with {missing} {'day' if missing == 1 else 'days'} uncounted." if missing else "."
    return [
        f"{short_date(start)}: {counts[first]:,}",
        f"{short_date(day)}: {known[-1]:,}",
        f"From {counts[first]:,} stars on {day_name(start)} to {known[-1]:,} on {day_name(day)}{uncounted}",
    ]


def history_file(boards: list[dict], history: History, number: int) -> dict:
    """What a board's opened rows show beyond their line, as the file `days/<board day>/history.json`, which the
    board's script fetches from the site's own address when a reader first opens a row. Every word and figure the row
    shows is written here, as the board writes the same ones, and the script places it: it keeps numbers only where it
    draws a line.

    `days` are the last `HISTORY_WINDOW` board days, oldest first, ending with this one, for the addresses of their
    boards, and `dates` name each as [its short name, its long name]. `rows`, in the board's order, give in `on` one
    entry for each of those board days whose board listed the row: [the day's place in `days`, its rank, its total
    stars, its stars a day over its recent days, the class that colours those (AndrewGodlewsky/RisingRepos#199), and
    its multiple], each figure as the board writes it and '—' where that board gave none. A day it was off the board has
    no entry, so the strip leaves it quiet, never a zero. Each row gives its `facts`, as `facts` words them, and a row
    with a score gives `sum`, the sum behind its reason, and `pace` and `said`, the numbers and the words of its
    drawing, from `drawing_words`. From a file that carries them (RisingRepos#193 to #197), `stars` is its star count
    on each of the 31 days to the board day, oldest first, null where there is none, and `month` the words of its line,
    from `month_words`."""
    span = list(range(min(len(boards), number + HISTORY_WINDOW) - 1, number - 1, -1))  # oldest first
    days = [boards[at]["board_day"] for at in span]
    by_id = [history.by_id[at] for at in span]
    about = any(name in row for row in boards[number]["rows"] for name in ABOUT)
    bands = bands_of(boards[number])
    rows = []
    for row in boards[number]["rows"]:
        on = []
        for place, listed in enumerate(by_id):
            seen = listed.get(row["github_id"])
            if not seen:
                continue
            if "score" in seen:
                on.append(
                    [
                        place,
                        seen["rank"],
                        f"{seen['stars']:,}",
                        per_day(seen),
                        per_day_class(seen).strip(),
                        growth(seen)["multiple"] or "—",
                    ]
                )
            else:
                on.append([place, seen["rank"], f"{seen['stars']:,}", "—", "nil", "—"])
        first = boards[history.first[row["github_id"]]]["board_day"]
        entry = {"on": on, "facts": facts(row, on, days, first, history.was(number, row), about, bands)}
        if "score" in row:
            entry["sum"] = why(row)["detail"]
            entry["pace"], entry["said"] = drawing_words(row)
        if "star_history" in row:
            entry["stars"] = row["star_history"]
            month = month_words(row["star_history"], days[-1])
            if month:
                entry["month"] = month
        rows.append(entry)
    return {"days": days, "dates": [[short_date(day), day_name(day)] for day in days], "rows": rows}


MADE_LATE = 2
"""How many days after its board day, by the date in UTC, a board's publish time must fall for its page to say that
the board was made after its day. The daily job publishes a board on its day, or early on the next."""


def daily_job(board: dict) -> dict | None:
    """When the day's update that published a board began, and how long it took to publish it, from the file's
    `daily_job_started_at` (RisingRepos#51), as plain values: board.html words them.

    None when the file does not say: one published before the data contract had the field, or a board that no daily
    run published, whose field is null. The page then says nothing about the update. Otherwise `started` is the
    field, `same_day` whether it falls on the publish time's day in UTC, and `seconds` how long the update ran
    before the publish. A start after the publish time never reaches here: the contract gives the field as no later
    than `published_at`, to the second, and the build refuses a file that breaks that (`contract`), so `seconds` is
    never below 0.
    """
    started = board.get("daily_job_started_at")
    if not started:
        return None
    began, published = datetime.fromisoformat(started), datetime.fromisoformat(board["published_at"])
    return {
        "started": started,
        "same_day": began.date() == published.date(),
        "seconds": int((published - began).total_seconds()),
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


class Band(NamedTuple):
    """A star band as the board offers it: its number, lowest first; its `label` on its button, '1k–3k' or '30k+';
    the star count it stops `below`, None for the top band; the `word` that names it in the board's address,
    '1k-3k' or '30k-plus', which a reader may have shared, so it is made from the band's limits, not from its label;
    and its `name` in a row's facts, '1k–3k' or '30k or more'."""

    number: int
    label: str
    below: int | None
    word: str
    name: str


def bands_of(board: dict) -> list[Band]:
    """The star bands as the board's filter names them, from the file's `star_bands` (AndrewGodlewsky/RisingRepos#196,
    in the form `holds` uses: each band's `least_stars` and `most_stars`, lowest first). The contract has the site
    keep no limits of its own, so a file from before the field gives none, and its board has no band filter.

    Each band is worded from its own limits, the lowest too: the file's lowest band starts at the star floor, so it
    reads "200–1k", from its least to where the next begins, as every band but the top one does."""
    given = board.get("star_bands", [])

    def short(stars: int) -> str:
        return f"{stars // 1000}k" if stars % 1000 == 0 and stars >= 1000 else f"{stars:,}"

    bands = []
    for number, band in enumerate(given):
        below = None if band["most_stars"] is None else band["most_stars"] + 1
        least = short(band["least_stars"])
        if below is None:
            bands.append(Band(number, f"{least}+", below, f"{least}-plus", f"{least} or more"))
        else:
            label = f"{least}–{short(below)}"
            bands.append(Band(number, label, below, f"{least}-{short(below)}", label))
    return bands


def held_bands(board: dict, bands: list[Band]) -> set[int]:
    """The numbers of the bands in `bands` that the board holds back (`holds`, AndrewGodlewsky/RisingRepos#13), each
    matched by where it stops. A held band has no row on the board, so its filter would show nothing: the page keeps
    its button for the script, which tells a row's band from every band's limits, and hides it from the reader."""
    stops = {None if hold["most_stars"] is None else hold["most_stars"] + 1 for hold in board.get("holds", [])}
    return {band.number for band in bands if band.below in stops}


TOP = 10
"""How many rows at the head of a board take the accent, in the pace chart and at their rank in the list."""

LABELLED = 5
"""How many of those the pace chart names by rank beside their dot."""


def _ticks(low: float, high: float) -> list[float]:
    """The powers of ten from `low` to `high` inclusive, for a log axis: 1, 10, 100, 1000. Always at least one
    decade, so that a board whose rows all sit at one pace still has an axis."""
    first = int(math.floor(math.log10(low)))
    last = max(int(math.ceil(math.log10(high))), first + 1)
    return [10.0**power for power in range(first, last + 1)]


def pace_chart(rows: list[dict]) -> dict | None:
    """The board's one chart: every row placed by its usual pace (across) against its recent pace (up), both in stars
    a day on log scales, so that a row's score, recent pace ÷ usual pace, is how far above the diagonal of its own pace
    it sits. The diagonals of 3×, 10×, 100×, and 1,000× are drawn as guides.

    The site computes no score: the usual pace is the divisor the file gives (`divided_by`, the baseline or the floor
    of 1 star a day), and the recent pace is the file's score times that divisor, which is the file's recent stars over
    its recent days. Positions are percentages of the plot, so the page can stretch the chart to any shape and keep
    its dots round and its labels at their own size. None for a board with no rows, or rows without the numbers.
    """
    if not rows or "score" not in rows[0]:
        return None
    points = [(row["divided_by"], row["score"] * row["divided_by"]) for row in rows]
    xs, ys = _ticks(min(x for x, _ in points), max(x for x, _ in points)), _ticks(1, max(y for _, y in points))
    x0, x1, y0, y1 = math.log10(xs[0]), math.log10(xs[-1]), math.log10(ys[0]), math.log10(ys[-1])
    # A little room inside the frame, so that the dots at the floor and at the top clear the axes.
    x0, x1 = x0 - (x1 - x0) * 0.03, x1 + (x1 - x0) * 0.01

    def left(x: float) -> float:
        return round((math.log10(x) - x0) / (x1 - x0) * 100, 2)

    def top(y: float) -> float:
        return round((y1 - math.log10(y)) / (y1 - y0) * 100, 2)

    dots = [{"left": left(x), "top": top(y), "rank": row["rank"]} for row, (x, y) in zip(rows, points, strict=True)]
    # The labelled dots, by rank. Dots that sit close together share one label, "1, 2", placed at the first of them,
    # so that no label lands on another or drifts from its dot.
    labels: list[dict] = []
    for dot in dots[:LABELLED]:
        near = next(
            (label for label in labels if abs(label["left"] - dot["left"]) < 6 and abs(label["top"] - dot["top"]) < 6),
            None,
        )
        if near:
            near["text"] += f", {dot['rank']}"
        else:
            labels.append({"text": str(dot["rank"]), "left": dot["left"], "top": dot["top"]})
    guides = []
    for multiple in (1, 3, 10, 100, 1000):
        # The diagonal y = multiple · x, clipped to the plot: in log space, a line of slope 1.
        shift = math.log10(multiple)
        start, end = max(x0, y0 - shift), min(x1, y1 - shift)
        if start >= end:
            continue
        # On a phone, "own pace" is set beside its line, at a point 60% of the way along it, and not at the line's
        # end: there the 3× line leaves the chart too, and the two labels printed on top of each other (#34). The
        # area below and to the right of the line is the board's emptiest, since a row is there only when its recent
        # pace is under its usual one.
        beside = start + (end - start) * 0.6
        guides.append(
            {
                "multiple": multiple,
                "x1": left(10**start),
                "y1": top(10 ** (start + shift)),
                "x2": left(10**end),
                "y2": top(10 ** (end + shift)),
                "bx": left(10**beside),
                "by": top(10 ** (beside + shift)),
                "label": "own pace" if multiple == 1 else f"{multiple:,}×",
            }
        )
    return {
        # Every dot as one path, in the board's order, the top rows in their own: a zero-length stroke with a round
        # cap is a dot, placed to a tenth of a percent. One path costs about 12 bytes a row, where an element for each
        # dot cost several times that. baseline.js reads the dots back from these, in order.
        "lead": "".join(f"M{round(dot['left'], 1):g} {round(dot['top'], 1):g}h0" for dot in dots[:TOP]),
        "rest": "".join(f"M{round(dot['left'], 1):g} {round(dot['top'], 1):g}h0" for dot in dots[TOP:]),
        "count": len(dots),
        "labels": labels,
        "guides": guides,
        "xticks": [{"at": left(x), "text": f"{x:,.0f}"} for x in xs],
        "yticks": [{"at": top(y), "text": f"{y:,.0f}"} for y in ys],
        "floor": sum(1 for x, _ in points if x == 1),
    }


WINDOW = 14
"""How many board days the "Most often" order counts, its own board included: two weeks of boards."""

RAMP = (200, 275, 350)
"""The board days calendar's fixed ramp: a board of fewer rows than the first step
takes the first shade, and each step after takes the next. Fixed, so that a shade means the same count every month."""


def comparable(board: dict) -> bool:
    """Whether a board can stand as the board before when telling what is new: it listed its rows as usual. A held
    board left whole star bands off and an empty one listed nothing, so a repository missing from either may have been
    kept off rather than not rising, and the page does not guess which."""
    return board.get("state", "rows" if board["rows"] else "empty") == "rows"


class History:
    """What the boards say about each other, worked out once at build time from the lists the files hold. New goes by
    name: a repository whose name, in any case, was on no earlier board is new, so a renamed or transferred one is new
    under its new name. Everything else follows a repository by its GitHub id, which a rename or a transfer keeps, so
    its run, its return, and its history stay whole: specula-org/Specula, on boards from August, came back as
    specular-org/Specular, which is new and still lists its earlier boards. The site computes no score and no rank: it
    compares lists."""

    def __init__(self, boards: list[dict]):
        self.boards = boards  # newest first, as the index is
        self.by_id = [{row["github_id"]: row for row in board["rows"]} for board in boards]
        self.named = [{row["full_name"].lower() for row in board["rows"]} for board in boards]
        self.first: dict[int, int] = {}
        self.first_named: dict[str, int] = {}
        for number in range(len(boards) - 1, -1, -1):  # oldest first, so the first number kept is the oldest board
            for github_id in self.by_id[number]:
                self.first.setdefault(github_id, number)
            for row in boards[number]["rows"]:
                self.first_named.setdefault(row["full_name"].lower(), number)
        self._rows: dict[int, dict] = {}

    def was(self, number: int, row: dict) -> str | None:
        """The name that `row`, on the board at `number`, had on the latest earlier board that listed it under another,
        at any distance, when it has been renamed or moved since: what its opened row says it was listed as before."""
        github_id, name = row["github_id"], row["full_name"]
        earlier = (listed[github_id]["full_name"] for listed in self.by_id[number + 1 :] if github_id in listed)
        return next((was for was in earlier if was != name), None)

    def known(self, number: int) -> bool:
        """Whether what is new on the board at `number` can be told: there is a board before it, and it is
        comparable."""
        return number + 1 < len(self.boards) and comparable(self.boards[number + 1])

    def rows(self, number: int) -> dict:
        """For the board at `number`: each row's recent presence, in the board's order (`marks`); how many rows are
        new (`new`, None when that cannot be told); how many boards the window covers (`window`); and the first board
        day the site holds (`since`). A mark holds `on`, how many of those boards listed it, by which the board's
        "Most often in 14 boards" order sorts; and `status`: "new" when its name was on no earlier board, "still" when
        it was on the board before too, with `run` boards in a row, or "back" after a gap, with `last`, the board day it
        was last on. The status is None when it cannot be told."""
        if number in self._rows:
            return self._rows[number]
        span = list(range(min(len(self.boards), number + WINDOW) - 1, number - 1, -1))  # oldest first
        known = self.known(number)
        marks, new = [], 0
        for row in self.boards[number]["rows"]:
            github_id = row["github_id"]
            seen = [github_id in self.by_id[at] for at in span]
            mark = {"on": sum(seen), "status": None, "run": 0, "last": None}
            if known and self.first_named[row["full_name"].lower()] == number:
                mark["status"] = "new"
                new += 1
            elif number + 1 < len(self.boards) and github_id in self.by_id[number + 1]:
                run = 0
                while number + run < len(self.boards) and github_id in self.by_id[number + run]:
                    run += 1
                mark.update(status="still", run=run)
            elif known:
                # Back after a gap: last on a board by its GitHub id or, for a name another repository held, by name.
                name = row["full_name"].lower()
                last = next(
                    at
                    for at in range(number + 1, len(self.boards))
                    if github_id in self.by_id[at] or name in self.named[at]
                )
                mark.update(status="back", last=self.boards[last]["board_day"])
            marks.append(mark)
        result = {
            "marks": marks,
            "new": new if known else None,
            "window": len(span),
            "since": self.boards[-1]["board_day"],
        }
        self._rows[number] = result
        return result


def calendar(boards: list[dict], history: History) -> list[dict]:
    """The board days as month calendars, newest month first: each month's weeks from Monday, and each day a cell
    holding its board, its count of rows, its shade on the fixed `RAMP` (0 for a board with none), and how many of its
    rows were new (None when that cannot be told, and for a board with none, which has no row that could be new:
    #91); a cell with no count for a day between the first board and the newest that has none; and None outside
    them."""
    by_day = {board["board_day"]: number for number, board in enumerate(boards)}
    months = sorted({board["board_day"][:7] for board in boards}, reverse=True)
    oldest, newest = boards[-1]["board_day"], boards[0]["board_day"]
    result = []
    for month in months:
        year, number = (int(part) for part in month.split("-"))
        first = date(year, number, 1)
        following = date(year + number // 12, number % 12 + 1, 1)
        cells: list[dict | None] = [None] * first.weekday()
        day = first
        while day < following:
            iso = day.isoformat()
            if iso in by_day:
                at = by_day[iso]
                count = len(boards[at]["rows"])
                cells.append(
                    {
                        "day": iso,
                        "date": day.day,
                        "count": count,
                        "shade": (1 + sum(count >= step for step in RAMP)) if count else 0,
                        "new": history.rows(at)["new"] if count else None,
                        "newest": at == 0,
                    }
                )
            elif oldest <= iso <= newest:
                cells.append({"day": iso, "date": day.day, "count": None})
            else:
                cells.append(None)
            day = date.fromordinal(day.toordinal() + 1)
        cells += [None] * (-len(cells) % 7)
        result.append({"month": month, "weeks": [cells[at : at + 7] for at in range(0, len(cells), 7)]})
    return result


FONTS = Path(__file__).parent / "fonts"
# Modified versions of IBM Plex Sans and IBM Plex Mono, renamed by sitebuild/fonts/subset.py.
FACES = [
    ("Rising Sans", 400, "rising-sans-400"),
    ("Rising Sans", 500, "rising-sans-500"),
    ("Rising Mono", 400, "rising-mono-400"),
    ("Rising Mono", 500, "rising-mono-500"),
]


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


def build(out: Path, *, data: Path = DATA, noindex: bool) -> None:
    """Check the data files in `data`, then write the site's pages into `out`, a folder that does not exist yet
    or is empty. Nothing is written when a file fails its check.

    With `noindex`, every page asks search engines not to index it.
    """
    # crawl and agent_copy name the site's addresses and figures from this module, and repo_list reads agent_copy, so
    # they are read here and not at the top, where this module is not yet whole.
    from sitebuild import agent_copy, crawl, repo_list

    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise FileExistsError(f"{out} already exists and is not an empty folder. Build into a new one.")
    boards = read_boards(data)
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
    # fetch on first opening.
    for number, board in enumerate(boards):
        page = out / board_day_page(board["board_day"])
        page.with_name(SHARE_IMAGE).write_bytes(share.draw(share_lines(board)))
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
    # not wanted: its values are the build's own fixed words, and a repository's name is in none of them.
    plain = {**guide, "marks": [Markup(mark) for mark in guide["marks"]], "owner_line": Markup(guide["owner_line"])}
    llms = templates.get_template("llms.txt").render(**common, site=SITE, **{**guide, **plain})
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
    yield (
        DAYS,
        DAYS,
        {
            "boards": boards,
            "calendar": calendar(boards, history),
            "ramp": RAMP,
        },
    )
    yield HOW_IT_WORKS, HOW_IT_WORKS, {"described": DESCRIBED_FORMULA}
    yield FOR_AGENTS, FOR_AGENTS, {}
    yield BASELINE, BASELINE, {"board": boards[0], "chart": pace_chart(boards[0]["rows"])}
    yield NOT_FOUND, NOT_FOUND, {}


def _beside(boards: list[dict], number: int, history: History) -> dict:
    """What a board's page is given: the board, what it says about the bands it holds back, the days its ranking
    lacked, why it lists no row when it lists none, its partial days, which notes a file older than the holds takes,
    and the day's update, whether it was made after its day, and the board days before it and after it, when there
    are."""
    board = boards[number]
    lacked = lacked_days(board)
    bands = bands_of(board)
    return {
        "board": board,
        "held": holds(board),
        "lacked": lacked,
        "why_none": why_none(board, lacked),
        "partial": partial_days(board),
        "before_holds": before_holds(board),
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
