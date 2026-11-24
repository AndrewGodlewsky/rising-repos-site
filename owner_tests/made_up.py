"""The boards the owner's tests build the site from, every row of them made up.

A scenario has to find on the site what it is about: a repository that is new and one that is not, a star band that
is held back, a board with no rows, text that a repository's owner wrote to break the page. The day's real boards
hold some of these and not others, and change every day, so this module writes a data folder of its own, laid out as
the data contract says, with the schemas the repository ships beside its own data. Nothing here is copied from a
real board: each owner's name starts with "made-up-", and each number is worked out below.

Three sets of boards come from here. `boards` is the site the browser is driven through. `largest_board` and
`long_board` are each one board day alone, for the two sizes the site promises.
"""

import json
import random
import shutil
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "site-data" / "contract"
"""The schemas of the data contract, as the repository ships them with its data. The build checks each data file
against the schema that comes with it, so the made-up folder carries a copy of these."""

STAR_BANDS = [
    {"least_stars": 200, "most_stars": 999},
    {"least_stars": 1000, "most_stars": 2999},
    {"least_stars": 3000, "most_stars": 9999},
    {"least_stars": 10000, "most_stars": 29999},
    {"least_stars": 30000, "most_stars": None},
]
"""Five star bands, lowest first, so that a board's filter offers several."""

NEWEST = date(2027, 3, 2)
"""The newest made-up board day. The others count back from it."""

MARKUP = (
    '<script>document.title="owned"</script><img src=x onerror="document.title=\'owned\'"> '
    "<a href=\"javascript:document.title='owned'\">a link</a> [another](https://made-up.invalid/) "
    'https://made-up.invalid/ </td></tr></table> & &amp; "quotes" <b>bold</b>'
)
"""A description written to break the page: a script, an image whose handler would run one, a link to a script, a
link as Markdown writes one, a bare address, the tags that would close the board's table, and the characters that
escaping has to carry. Were any of it read as markup, the page's title would change, a link would appear, or the rows
after it would fall out of the table."""

MARKUP_LANGUAGE = 'Go"><script>document.title=1</script>'
"""A language written to close the attribute it is put in, and to start a script after it. It is kept to 37
characters, since the list of languages is as wide as its longest: one of about 80 made that list wider than a
phone's screen before any row was opened, which would have failed the sentence about a phone for a cause of its own."""

UNBROKEN = ("NoSpaceAnywhereInThisDescriptionSoNothingLetsALineBreak" * 7)[:350]
"""A description of the most characters the contract allows, 350, with no place to break a line."""

BEYOND_ASCII = (
    "Text beyond ASCII: 日本語の説明, مرحبا بالعالم, an emoji 🚀, and a right-to-left override "
    "\u202egnp.exe\u202c before its end"
)
"""A description in several scripts, with the character that turns the direction of the text after it."""


@dataclass(frozen=True)
class Repository:
    """A made-up repository: what its owner wrote, and the numbers every row of it is worked out from. `stars` is its
    star count on the newest board day, and `usual` its baseline in stars a day: 1 or more gives a row a multiple,
    under 1 puts it on the floor, and under 0 is a repository that had been losing stars. `traits` name what else
    its rows carry: "day-left-out", a board day that lost too many stars to be believed, so that its recent pace keeps
    one day; "loss-on-the-day", a small loss on the board day itself; "no-day-before", no count for the day before
    the board day; and "young", no count for the first twelve of its 31 days."""

    github_id: int
    full_name: str
    description: str | None
    language: str | None
    stars: int
    usual: float
    licence: str | None = "MIT"
    traits: frozenset[str] = frozenset()


LONG_OWNER = "made-up-OwnerWhoseNameRunsOnAndOnAndOnn"
LONG_NAME = ("ARepositoryNameOfAHundredCharactersWithNoPlaceToBreakIt" * 2)[:100]
LONG_NAME_BEFORE = ("TheNameThisRepositoryHadBeforeItWasRenamedWhichWasLongToo" * 2)[:100]

REPOSITORIES = {
    # The three whose owners wrote the worst they could. The first was renamed, so its opened row gives the name it
    # was listed under before. Both names are long, an owner of 39 characters and a repository of 100, and neither
    # repository's name has a place to break a line.
    "long": Repository(910001, f"{LONG_OWNER}/{LONG_NAME}", UNBROKEN, "Jupyter Notebook", 41870, 12.5, "Apache-2.0"),
    "long-before": Repository(
        910001, f"{LONG_OWNER}/{LONG_NAME_BEFORE}", UNBROKEN, "Jupyter Notebook", 41870, 12.5, "Apache-2.0"
    ),
    "markup": Repository(910002, "made-up-mallory/markup-in-everything", MARKUP, MARKUP_LANGUAGE, 482, 1.5, None),
    "beyond-ascii": Repository(
        910003, "made-up-nadia/text-beyond-ascii", BEYOND_ASCII, "Rust", 4207, 7.5, "NOASSERTION"
    ),
    # The rest, plain: several star bands, several languages, and each shape a row's numbers can take.
    "harbour": Repository(
        910004, "made-up-amber/harbour-lights", "A made-up tool that maps harbours.", "Python", 13250, 12.5
    ),
    "kiln": Repository(910005, "made-up-birch/kiln-notes", "Made-up notes on firing a kiln.", "TypeScript", 5120, 4.75),
    "ferry": Repository(
        910006, "made-up-cedar/ferry-timetable", "A made-up ferry timetable.", "Go", 1840, 2.25, "GPL-3.0"
    ),
    "lantern": Repository(910007, "made-up-dune/lantern", "A made-up lantern for dark terminals.", "Python", 640, 0.25),
    "quarry": Repository(910008, "made-up-ember/quarry-maps", "Made-up maps of old quarries.", "C++", 7300, 3.0),
    "orchard": Repository(910009, "made-up-fjord/orchard", None, None, 260, 0.5, None, frozenset({"young"})),
    "tideline": Repository(
        910010, "made-up-grove/tideline", "A made-up reader of tide tables.", "TypeScript", 2210, -0.5
    ),
    "glacier": Repository(
        910011,
        "made-up-heath/glacier-watch",
        "A made-up watch on glaciers.",
        "Rust",
        36400,
        20.0,
        "MIT",
        frozenset({"day-left-out"}),
    ),
    "saltmarsh": Repository(
        910012, "made-up-isle/saltmarsh", "A made-up survey of salt marshes.", "Python", 18900, 9.0
    ),
    "millrace": Repository(
        910013,
        "made-up-juniper/millrace",
        "A made-up model of a mill race.",
        "Go",
        1310,
        1.0833333333333333,
        "MIT",
        frozenset({"no-day-before"}),
    ),
    "weathervane": Repository(
        910014,
        "made-up-kestrel/weathervane",
        "A made-up weather vane.",
        "TypeScript",
        3480,
        2.0,
        "MIT",
        frozenset({"loss-on-the-day"}),
    ),
    "causeway": Repository(910015, "made-up-larch/causeway", "A made-up causeway planner.", "Python", 870, 1.25),
    "lighthouse": Repository(910016, "made-up-moss/lighthouse-keeper", "A made-up keeper's log.", "Rust", 52300, 30.0),
    "towpath": Repository(910017, "made-up-nettle/towpath", "A made-up walk along a towpath.", "Go", 2740, 1.75),
    "windbreak": Repository(910018, "made-up-osier/windbreak", "A made-up windbreak.", "C++", 6150, 5.5),
    "footbridge": Repository(910019, "made-up-pine/footbridge", "A made-up footbridge.", "TypeScript", 530, 0.75),
    "drystone": Repository(910020, "made-up-quince/drystone", "A made-up dry stone wall.", "Python", 11400, 6.25),
    "sluice": Repository(910021, "made-up-rowan/sluice-gate", "A made-up sluice gate.", "Go", 1570, 1.5),
    "hedgerow": Repository(910022, "made-up-sorrel/hedgerow", "A made-up hedgerow count.", "Python", 410, 0.0),
}
"""Every made-up repository the browser's site lists, by a short name the boards below use. No test names one: a
scenario takes the first row, or finds the row that holds a text above."""


def _history(repository: Repository, stars: int, recent: int, one_day: bool) -> list[int | None]:
    """A row's star count on each of the 31 days to its board day, oldest first, ending in `stars`: its usual pace up
    to the recent days, then `recent` stars over them. With `one_day`, the board day lost more stars than the formula
    takes for real, so the recent pace is the day before alone."""
    if one_day:
        before = stars + max(600, stars // 25)
        start = before - recent
    else:
        on_the_day = -12 if "loss-on-the-day" in repository.traits else round(recent * 0.55)
        before = stars - on_the_day
        start = stars - recent
    counts: list[int | None] = [max(start - round(repository.usual * (28 - day)), 0) for day in range(28)]
    counts += [start, before, stars]
    if "young" in repository.traits:
        counts[:12] = [None] * 12
    if "no-day-before" in repository.traits:
        counts[29] = None
    return counts


def _gained(counts: list[int | None], days: int) -> int | None:
    """The stars gained over the last `days` days of `counts`, or None when the day they are counted from has no
    count, as the contract gives each of a row's three gains."""
    return None if counts[30 - days] is None else counts[30] - counts[30 - days]


def _row(repository: Repository, rank: int, score: float, stars: int, board_day: date) -> dict:
    """A row of `repository` at `rank`, with a score as near `score` as whole stars allow, worked out as the contract
    describes each field: the score is the recent stars over the recent days, over what they are divided by, and the
    gains are read back from the star history."""
    one_day = "day-left-out" in repository.traits
    days = 1 if one_day else 2
    divided_by = max(repository.usual, 1.0)
    recent = max(round(score * divided_by * days), 1)
    counts = _history(repository, stars, recent, one_day)
    return {
        "rank": rank,
        "github_id": repository.github_id,
        "full_name": repository.full_name,
        "description": repository.description,
        "language": repository.language,
        "license": repository.licence,
        "created_at": "2027-01-20T09:00:00Z" if "young" in repository.traits else "2023-06-14T08:15:00Z",
        "pushed_at": f"{board_day.isoformat()}T18:47:03Z",
        "stars": stars,
        "score": recent / days / divided_by,
        "recent_stars": recent,
        "recent_days": days,
        "days_left_out": 2 - days,
        "baseline": repository.usual,
        "divided_by": divided_by,
        "excess": (recent / days - max(repository.usual, 0.0)) * 2,
        "star_history": counts,
        "gained_1_day": _gained(counts, 1),
        "gained_7_days": _gained(counts, 7),
        "gained_30_days": _gained(counts, 30),
    }


def _board(days_before: int, listed: str = "", **said) -> dict:
    """The board of the day `days_before` the newest, listing the repositories `listed` names, in rank order. Each
    row's score is four fifths of the one above it, from 60, so the ranks are in the order of the scores, and each
    repository has three stars fewer for each day before the newest. `said` gives whatever the file says beyond its
    rows: its state, its holds, a provisional ranking, the days its ranking lacked."""
    day = NEWEST - timedelta(days=days_before)
    after = day + timedelta(days=1)
    rows = [
        _row(REPOSITORIES[name], rank, 60 * 0.8 ** (rank - 1), REPOSITORIES[name].stars - 3 * days_before, day)
        for rank, name in enumerate(listed.split(), start=1)
    ]
    return {
        "schema_version": 1,
        "board_day": day.isoformat(),
        "published_at": f"{after.isoformat()}T00:41:07Z",
        "daily_job_started_at": f"{after.isoformat()}T00:28:44Z",
        "score_provisional": False,
        "formula_version": 2,
        "partial_days": [],
        "state": "rows" if rows else "empty",
        "star_bands": STAR_BANDS,
        "holds": [],
        "missed_stars": [],
        "unranked": [],
        "rows": rows,
        **said,
    }


def _day(days_before: int) -> str:
    return (NEWEST - timedelta(days=days_before)).isoformat()


def boards() -> list[dict]:
    """The boards of the site the browser is driven through, newest first, as the index lists them. Nine board days
    over ten days, so that History has a day with no board, and over two months.

    - The newest: fourteen rows in all five star bands and seven languages, six of them new, the rest on the board
      before too or back after a gap, with a row for each shape a row's numbers take.
    - The board before it, which lists its rows as usual, so that what is new on the newest can be told.
    - A board whose ranking is provisional.
    - A board that holds the second star band back, and lists rows from the others.
    - A board whose ranking lacked a day, so that some repositories could not be ranked.
    - A day with no board.
    - Three boards with no rows: one on which nothing rose, one that holds a band back, and one whose ranking had no
      snapshot of a day it needs.
    - The first board.
    """
    return [
        _board(
            0,
            "long markup beyond-ascii harbour kiln ferry lantern quarry orchard tideline glacier saltmarsh millrace"
            " weathervane",
        ),
        _board(1, "harbour kiln beyond-ascii ferry glacier weathervane causeway lighthouse towpath windbreak"),
        _board(
            2, "long-before harbour kiln beyond-ascii glacier causeway lighthouse footbridge", score_provisional=True
        ),
        _board(
            3,
            "harbour kiln saltmarsh causeway footbridge drystone",
            state="held",
            holds=[STAR_BANDS[1]],
            missed_stars=[{"least_stars": 2006, "most_stars": 2051}],
            partial_days=[{"snapshot_day": _day(3), "recent": True}],
        ),
        _board(
            4,
            "harbour kiln quarry long-before causeway towpath drystone sluice",
            unranked=[{"snapshot_day": _day(6), "status": "partial", "repositories": 1847}],
            partial_days=[{"snapshot_day": _day(6), "recent": True}],
        ),
        # Five days before the newest there is no board.
        _board(6),
        _board(
            7,
            state="held",
            holds=[STAR_BANDS[0]],
            missed_stars=[{"least_stars": 412, "most_stars": 440}],
            partial_days=[{"snapshot_day": _day(7), "recent": True}],
        ),
        _board(8, unranked=[{"snapshot_day": _day(10), "status": "missing", "repositories": 0}]),
        _board(9, "harbour ferry quarry lighthouse sluice hedgerow"),
    ]


LARGEST_BOARD = 316
"""The most rows a daily board of the earlier site held, which a page's size has been measured at since."""

LONG_BOARD = 713
"""The length the root's size on the wire is promised at: half as many rows again as the longest board the formula
in use has made, 475."""


def largest_board() -> list[dict]:
    """One board day of `LARGEST_BOARD` rows, each as long as the contract lets a row be: a description of 350
    characters holding the ones that escaping lengthens, a long name, and the numbers of a repository that had been
    losing stars and whose recent pace keeps one day, which the site words at the greatest length."""
    description = ("A made-up row of the largest board, with <markup> & characters escaping lengthens. " * 5)[
        :349
    ] + "…"
    repositories = [
        Repository(
            920000 + rank,
            f"made-up-example/a-made-up-repository-of-the-largest-board-{rank:03d}",
            description,
            "Jupyter Notebook",
            123456 + rank,
            -3.4166666666666665,
            ("MIT", "Apache-2.0", None, "GPL-3.0", "NOASSERTION")[rank % 5],
            frozenset({"day-left-out"}),
        )
        for rank in range(1, LARGEST_BOARD + 1)
    ]
    rows = [_row(repository, rank, 200.0, repository.stars, NEWEST) for rank, repository in enumerate(repositories, 1)]
    return [{**_board(0), "state": "rows", "rows": rows}]


def long_board() -> list[dict]:
    """One board day of `LONG_BOARD` rows of about the length a real row has, from a seeded generator, so that every
    run builds the same page. Each name is four random words and each description 105 characters of them, which pack
    less tightly than a real description's prose, so the size errs on the heavy side. So does the order: the rows are
    ranked as they are drawn, not by their scores as a real board's are, and neighbours that differ more pack less
    tightly. Three baselines in four are a star a day or more, a fifth are under one, and the rest below nothing; the
    scores have a median near 8; and a row has a recent day left out one time in about 1,250. That is drawn as
    tests/test_page_weight.py draws its own long board, to the spread it records of the formula's real rows."""
    draw = random.Random(LONG_BOARD)
    letters = "abcdefghijklmnopqrstuvwxyz"

    def word() -> str:
        return "".join(draw.choice(letters) for _ in range(draw.randint(2, 9)))

    def text(length: int) -> str:
        words: list[str] = []
        while len(" ".join(words)) < length:
            words.append(word())
        return " ".join(words)[: length - 1].rstrip().capitalize() + "."

    def usual() -> float:
        kind = draw.random()
        if kind < 0.75:
            return max(round(10 ** abs(draw.gauss(0, 0.95)) * 12), 12) / 12
        return draw.randint(0, 11) / 12 if kind < 0.963 else -draw.randint(1, 72) / 12

    rows = []
    for rank in range(1, LONG_BOARD + 1):
        score = 3 * 10 ** abs(draw.gauss(0, 0.6))
        pace = usual()
        repository = Repository(
            930000 + rank,
            f"made-up-{word()}/{word()}-{word()}-{word()}",
            text(105),
            draw.choice(["Python", "TypeScript", "Go", "Rust", "C++", "Java", "Shell", None]),
            # A repository holds at least the stars it has just gained, so that no day of its history is below nothing.
            draw.randrange(1000, 250_000) + round(score * max(pace, 1.0) * 2),
            pace,
            ("MIT", "Apache-2.0", None, "GPL-3.0", "NOASSERTION")[rank % 5],
            frozenset({"day-left-out"}) if draw.random() < 0.0008 else frozenset(),
        )
        rows.append(_row(repository, rank, score, repository.stars, NEWEST))
    return [{**_board(0), "state": "rows", "rows": rows}]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def board_file(folder: Path, board_day: str) -> Path:
    """Where the data contract puts a board day's file under the data folder `folder`."""
    return folder / "boards" / "days" / board_day / "daily.json"


def write(folder: Path, listed: list[dict]) -> None:
    """Write `listed`, boards newest first, into the new folder `folder` as the data contract lays a data folder out:
    the two schemas, the index with each board day's count of rows, and each board day's file in its own folder."""
    shutil.copytree(CONTRACT, folder / "contract")
    index = [{"board_day": board["board_day"], "row_count": len(board["rows"])} for board in listed]
    write_json(folder / "boards" / "index.json", {"schema_version": 1, "board_days": index})
    for board in listed:
        write_json(board_file(folder, board["board_day"]), board)
