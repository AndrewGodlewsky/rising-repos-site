"""Cross-board history, star bands, opened-row facts and history.json, and History's calendar (#252)."""

from datetime import date, timedelta
from typing import NamedTuple

from sitebuild.formatting import (
    day_name,
    figure,
    growth,
    licence_label,
    per_day,
    per_day_class,
    rounded,
    short_date,
    signed,
    times,
    why,
)

HISTORY_WINDOW = 30
"""How many board days the expanded row's chart covers, its own board included."""

ABOUT = ("license", "created_at", "pushed_at")
"""The facts the data contract gives each row since AndrewGodlewsky/RisingRepos#197, by its names: its licence as an
SPDX id, which the owner chose and the contract marks untrusted, when it was created, and when it was last pushed to.
The opened row shows them from the history file, as text."""

WINDOW = 14
"""How many board days the "Most often" order counts, its own board included: two weeks of boards."""

RAMP = (200, 275, 350)
"""The board days calendar's fixed ramp: a board of fewer rows than the first step
takes the first shade, and each step after takes the next. Fixed, so that a shade means the same count every month."""


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


def band_name(bands: list[Band], stars: int) -> str:
    """The name of the band in `bands` that `stars` falls in, as a row's facts give it."""
    return next(band.name for band in bands if band.below is None or stars < band.below)


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

    def listed_before(self, number: int, github_id: int) -> list[tuple[str, int]]:
        """Each board older than the one at `number` that listed the repository `github_id`, newest first, as its
        board day and the rank it gave: what the agent copy's earlier boards and an opened row's line of the boards
        before its table are both counted from (#221)."""
        return [
            (self.boards[at]["board_day"], self.by_id[at][github_id]["rank"])
            for at in range(number + 1, len(self.boards))
            if github_id in self.by_id[at]
        ]

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
    told.append(["Language", row.get("language") or "Not given"])
    if about:
        told.append(["Licence", licence_label(row.get("license"))])
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
    gained_stars, days = row["recent_stars"], row["recent_days"]
    reason = why(row)
    usual, own = figure(baseline, 2), times(days * baseline)
    sentence = (
        f"Over the 12 days before, its usual pace was {usual} stars a day. Over "
        f"{'the day kept' if days == 1 else 'the last 2 days'} it gained {figure(gained_stars, 0)}, where its own pace "
        f"would have given {own}" + (f": {reason['above']} above its own trend." if reason["above"] else ".")
    )
    return [baseline, gained_stars, days], [
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


def before_words(older: list[tuple[str, int]], start: str, best: int) -> str:
    """The line under an opened row's table of the boards it was on, for a repository that was also on `older`, the
    boards before the window's first board day `start`, newest first, as `History.listed_before` gives them: how many,
    the first, worded as the row's "First on a board" fact words it, and `best`, its best rank on any board up to the
    one shown (#221)."""
    first = day_name(older[-1][0])
    if len(older) == 1:
        said = f"And 1 board before {short_date(start)}, on {first}."
    else:
        said = f"And {len(older)} boards before {short_date(start)}, the first on {first}."
    return f"{said} Its best rank on any board: {best}."


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
    drawing, from `drawing_words`. A row whose repository was on a board older than the first of `days` gives
    `before`, the line under its table that says how many, the first, and its best rank on any board, from
    `before_words`, since the table lists those board days alone (#221). From a file that carries them (RisingRepos#193
    to #197), `stars` is its star count on each of the 31 days to the board day, oldest first, null where there is
    none, and `month` the words of its line, from `month_words`."""
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
        older = history.listed_before(span[0], row["github_id"])
        if older:
            best = min([rank for _, rank in older] + [seen[1] for seen in on])
            entry["before"] = before_words(older, days[0], best)
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
