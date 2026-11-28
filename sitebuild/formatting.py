"""Dates, figures, signs, board notes, reasons, and row paces, worded once for every page and agent copy (#252)."""

import math
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

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

NEW_UNTOLD = (
    "What is new on this board cannot be told: the board before it held a star band back or listed no repository, "
    "so one missing from it may have been kept off."
)
"""What About this board says when New cannot be told, which the agent copy's header says too (#176)."""

MINUS = "\N{MINUS SIGN}"
"""What a figure below 0 is written with (AndrewGodlewsky/RisingRepos#199): the true minus, which the site's type
draws as wide as the plus and the figures, not the hyphen. A loss takes it, and so does a pace that was falling."""

PACE_SCALE = (0.5, 5000)
"""The stars a day the row's small chart spans, bottom to top, on a log scale: the same for every row of every board,
so that two rows' charts compare. A pace under the bottom, a falling one among them, sits on the bottom."""

MADE_LATE = 2
"""How many days after its board day, by the date in UTC, a board's publish time must fall for its page to say that
the board was made after its day. The daily job publishes a board on its day, or early on the next."""


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


def day_name(day: str) -> str:
    """A day as an opened row names it: '2026-11-09' as '9 Nov 2026'."""
    return f"{short_date(day)} {day[:4]}"


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


def signed(written: str) -> str:
    """A gain as the site writes it, from the figure `figure` or `times` wrote: a plus before a figure above 0, and a
    loss and 0 as the figure is, with its true minus or bare. A gain that rounds to 0 is '0', never '+0'."""
    return written if written == "0" or written.startswith(MINUS) else "+" + written


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
    gained_text = f"{signed(written)} in {span}" if above is None else f"{signed(above)} above its own trend"
    if left_out == 1:
        detail += ". A recent day that lost too many stars to be believed is left out"
    elif left_out:
        detail += f". {left_out} recent days that lost too many stars to be believed are left out"
    return {"line": f"{gained_text} · {pace}", "detail": detail + ".", "gained": gained_text, "above": above}


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


def own_pace(row: dict) -> dict:
    """A row's own pace against what it gained, small, as How it works once drew it (#214): across the 14
    days, the dashed level of its usual pace, its baseline a day, as it would have gone on; over its recent days, the
    last two or the one the loss rule kept, the level of its recent pace; and the part between shaded. Both levels are
    stars a day on one log scale, `PACE_SCALE`, shared by every row, so the gap reads as its multiple and the height as
    its size. The file gives averages for the two windows, not a count for each day, so each is one level.

    The stylesheet draws it from `style`, two custom properties of the cell: `--u` and `--r`, how far down the box
    each level sits, from 0 to 1, and `--e`, where the recent run ends, when a day was left out. Two numbers cost a
    row about a sixth of what an SVG of the same drawing does. Its `text` gives the usual pace to two places, and the
    recent pace as the growth column writes stars a day, so an opened row's table of days says the same."""
    baseline, gained_stars, days = row["baseline"], row["recent_stars"], row["recent_days"]
    low, high = (math.log10(value) for value in PACE_SCALE)

    def down(pace: float) -> str:
        at = (math.log10(min(max(pace, PACE_SCALE[0]), PACE_SCALE[1])) - low) / (high - low)
        return f"{0.05 + (1 - at) * 0.9:.2f}"

    style = f"--u:{down(baseline)};--r:{down(gained_stars / days)}"
    if days != 2:
        style += f";--e:{(12 + days) / 14:.3f}"
    return {
        "style": style,
        "text": f"Usual {figure(baseline, 2)} a day, then {times(gained_stars / days)} a day",
        "multiple": growth(row)["multiple"] if "score" in row else None,
    }


def licence_label(value: str | None) -> str:
    """A repository's licence as an opened row's facts show it (#239): GitHub's SPDX id as given, plain prose for
    GitHub's `NOASSERTION` sentinel (a licence file GitHub could not identify), and 'None given' when absent."""
    if not value:
        return "None given"
    if value == "NOASSERTION":
        return "Other (not identified)"
    return value


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
