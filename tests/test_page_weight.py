"""Every page stays light: it carries no script but the site's own, requests nothing from another site, and stays
within its size limit. A board's opened rows read its history.json, which the page fetches once, on the first opening,
so that file is not part of the page's weight."""

import gzip
import random
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from helpers import ROOT, BuildTest, Page, read_json

from sitebuild import BOARD, board_day_page

SIZE_LIMIT = 500_000
"""The most bytes a page may take, uncompressed, with its styles, its script, and its type. Issue #39 in RisingRepos
set it at 320,000 from the largest page measured, the chart design's page of the largest board below at 263,763 bytes,
with a fifth more for what later slices add to a row. AndrewGodlewsky/RisingRepos#49 raised it to 410,000 for each
row's reason. AndrewGodlewsky/RisingRepos#199 raised it to 500,000, as decided there, for the redesign's type
inside each page, its filter and script, and each row's figures: the largest board below measured 479,955 bytes, and
the real board of the most rows, 475 on 12 August 2026, 476,623. Past about 500 real rows, a long board's later rows in
a second file is the next step. README.md gives the measurements."""

LARGEST_BOARD = 316
"""The most rows a daily board of the earlier site held (RisingRepos's data contract, under Size)."""

WIRE_ROWS = 713
"""The board length that the root's transfer size is tested at: 475 rows, the longest board formula 2 made over the
whole snapshot archive (12 August 2026), with half as many again for longer boards to come. The choice is recorded on
AndrewGodlewsky/RisingRepos#122."""

WIRE_BUDGET = 150_000
"""The most bytes the root of a `WIRE_ROWS` board may take gzipped. AndrewGodlewsky/RisingRepos#122 held it to the
site eval's transfer limit, 100,000. AndrewGodlewsky/RisingRepos#199 gave it its own, 150,000, as decided there: the
redesign's root of 713 rows measured 144,789 bytes with zlib 1.3.1, which the workflow's Python uses, and the type
takes about 28,000 of a page's gzipped bytes. The zlib-ng of Python 3.14 on Windows packs it to 141,600, so a size
measured there reads about 2% low. The eval's limit, in evals/site/limits.json, stays 100,000 for the real root it
measures: 80,871 bytes with zlib 1.3.1 for the 264 rows of 21 November 2026."""

EVAL_LIMITS = ROOT / "evals" / "site" / "limits.json"
"""The site eval's limits, read here rather than copied, so that a change there is a change here."""

LOADS = {"src", "srcset", "imagesrcset", "poster", "data", "background", "action", "formaction", "manifest", "ping"}
"""The attributes whose address a browser fetches, or sends something to, without following a link."""

CSS_ADDRESS = re.compile(r"""url\(\s*(['"]?)(.*?)\1\s*\)|@import\s+(['"])(.*?)\3""", re.IGNORECASE)


def requests(page: Page) -> list[str]:
    """Every address the page makes the browser fetch: everything but the links a reader follows."""
    found = []
    for element in page.all():
        for name, value in element.attrs.items():
            if value is None:
                continue
            if name in ("srcset", "imagesrcset"):
                found += [candidate.split()[0] for candidate in value.split(",") if candidate.strip()]
            elif name in LOADS or (element.tag == "link" and name == "href"):
                found.append(value)
            elif name == "style":
                found += css_addresses(value)
        if element.tag == "style":
            found += css_addresses(element.text())
        if element.tag == "meta" and (element.attrs.get("http-equiv") or "").lower() == "refresh":
            found.append((element.attrs.get("content") or "").partition("=")[2])
    return found


def css_addresses(css: str) -> list[str]:
    return [match.group(2) or match.group(4) for match in CSS_ADDRESS.finditer(css)]


def on_this_site(address: str) -> bool:
    parts = urlsplit(address.strip())
    return parts.scheme == "data" or not (parts.scheme or parts.netloc)


def page_weight(out: Path, path: str, page: Page) -> int:
    """The page's bytes, and those of each file on this site that it makes the browser fetch."""
    files = [address for address in requests(page) if not address.strip().startswith("data:")]
    folder = (out / path).parent
    return len(page.html.encode("utf-8")) + sum(
        ((out / address.lstrip("/")) if address.startswith("/") else (folder / address)).stat().st_size
        for address in files
    )


LONGEST_NUMBERS = {
    "baseline": -3.4166666666666665,
    "divided_by": 1.0,
    "recent_stars": 200,
    "recent_days": 1,
    "days_left_out": 1,
    "excess": 400.0,
    "score": 200.0,
}
"""The numbers of the row whose reason is the longest the site wrote for any of formula 2's 31,195 rows from 29 July
to 14 November 2026, 200 bytes (AndrewGodlewsky/RisingRepos#49): a repository that had been losing stars, and whose
recent pace keeps one day, whose expanded view writes its score out and says why a day is missing."""


LICENSES = ["MIT", "Apache-2.0", None, "GPL-3.0", "NOASSERTION"]


def with_redesign_fields(row: dict) -> dict:
    """`row` with the fields that AndrewGodlewsky/RisingRepos#193 to #197 added to a row: the star history of a
    repository that gained its recent pace on each of the 31 days, as far as its stars allow, the gains that history
    gives, a license, and when the repository was created and last pushed to. The page shows the day's gain; the rest
    is in the board day's history.json. They are worked out from the row, not drawn, so a seeded generator draws the
    rows it drew before them."""
    per_day = min(row["recent_stars"] // row["recent_days"], row["stars"] // 31)
    history = [row["stars"] - per_day * (30 - day) for day in range(31)]
    return {
        **row,
        "license": LICENSES[row["rank"] % len(LICENSES)],
        "created_at": "2024-03-01T09:30:00Z",
        "pushed_at": "2026-11-09T18:47:03Z",
        "star_history": history,
        "gained_1_day": history[30] - history[29],
        "gained_7_days": history[30] - history[23],
        "gained_30_days": history[30] - history[0],
    }


def made_up_rows(count: int) -> list[dict]:
    """Rows as long as the contract lets a row be in practice: a description of the most characters it may hold,
    with characters that escaping makes longer, and the numbers whose reason is the longest the site has written."""
    description = ("A made-up row of the largest board, with <markup> & characters escaping lengthens. " * 5)[:349]
    return [
        with_redesign_fields(
            {
                "rank": rank,
                "github_id": 900000000 + rank,
                "full_name": f"rising-repos-example/a-made-up-repository-of-the-largest-board-{rank:03d}",
                "description": description + "…",
                "language": "Jupyter Notebook",
                "stars": 123456 + rank,
                **LONGEST_NUMBERS,
            }
        )
        for rank in range(1, count + 1)
    ]


def typical_numbers(draw: random.Random) -> dict:
    """A rising row's numbers as formula 2 works them out, drawn at random to the spread its 31,195 rows from 29 July
    to 14 November 2026 had (AndrewGodlewsky/RisingRepos#49). Three in four had a baseline of a star a day or more, at
    a median of 4.7, 30 at the 90th percentile, and 199 at the 99th; a fifth one under it; one in 27 one below
    nothing; and one in 1,250 a recent day left out. Their scores had a median of 6.9, 24.5 at the 90th percentile,
    and 102 at the 99th. Each baseline is a whole number of stars over 12 days, which leaves the long decimals the
    files carry."""
    kind = draw.random()
    if kind < 0.75:
        baseline = max(round(10 ** abs(draw.gauss(0, 0.95)) * 12), 12) / 12
    elif kind < 0.963:
        baseline = draw.randint(0, 11) / 12
    else:
        baseline = -draw.randint(1, 72) / 12
    divided_by = max(baseline, 1.0)
    left_out = int(draw.random() < 0.0008)
    days = 2 - left_out
    recent_stars = round(3 * 10 ** abs(draw.gauss(0, 0.6)) * divided_by * days)
    pace = recent_stars / days
    return {
        "baseline": baseline,
        "divided_by": divided_by,
        "recent_stars": recent_stars,
        "recent_days": days,
        "days_left_out": left_out,
        "excess": (pace - max(baseline, 0)) * 2,
        "score": recent_stars / days / divided_by,
    }


def typical_rows(count: int) -> list[dict]:
    """Rows of about the length that formula 2's rows have, from a seeded generator, so every run builds the same
    page. Each description is 105 characters, about the mean among those rows that have one, and the names and words
    are random letters, which gzip packs less tightly than the prose of a real description."""
    draw = random.Random(47)
    letters = "abcdefghijklmnopqrstuvwxyz"
    languages = ["Python", "TypeScript", "Go", "Rust", "C++", "Java", "Shell", None]

    def word() -> str:
        return "".join(draw.choice(letters) for _ in range(draw.randint(2, 9)))

    def text(length: int) -> str:
        words = []
        while len(" ".join(words)) < length:
            words.append(word())
        return " ".join(words)[: length - 1].rstrip().capitalize() + "."

    return [
        with_redesign_fields(
            {
                "rank": rank,
                "github_id": 700000000 + rank,
                "full_name": f"{word()}-{word()}/{word()}-{word()}",
                "description": text(105),
                "language": draw.choice(languages),
                "stars": draw.randrange(200, 250_000),
                **typical_numbers(draw),
            }
        )
        for rank in range(1, count + 1)
    ]


class PageWeight(BuildTest):
    def test_no_page_carries_a_script_but_the_sites_own_and_each_page_forbids_every_other(self):
        """The site's one script is site.js, inline, and the policy lets it run by its hash alone.
        tests/test_old_board.py checks the hash, and which parts of it each page carries."""
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertLessEqual(len(page.all("script")), 1)
                self.assertEqual([script.attrs for script in page.all("script")], [{}] * len(page.all("script")))
                attributes = [(name, value or "") for element in page.all() for name, value in element.attrs.items()]
                self.assertEqual([name for name, _ in attributes if name.startswith("on")], [])
                self.assertEqual(
                    [value for _, value in attributes if value.strip().lower().startswith("javascript:")], []
                )
                self.assertTrue(page.policy().startswith("default-src 'none';"), page.policy())
                if page.all("script"):
                    (source,) = page.directives()["script-src"]  # one source: the script's hash
                    self.assertRegex(source, r"^'sha256-[A-Za-z0-9+/]{43}='$")
                else:
                    self.assertNotIn("script-src", page.directives())

    def test_no_page_carries_the_notes_on_its_stylesheet_or_its_script(self):
        """They are Jinja comments, which the build leaves out (AndrewGodlewsky/RisingRepos#199): as CSS and JS
        comments they took 9,531 bytes of a board's page, and 4,044 of the long board's root gzipped below."""
        for path, page in self.build_pages().items():
            with self.subTest(path):
                (style,) = page.all("style")
                self.assertNotIn("/*", "".join(style.children))
                for script in page.all("script"):
                    self.assertNotRegex(
                        "".join(script.children), r"(?m)^\s*//|\s//\s"
                    )  # a note on its own line or after code
                self.assertNotIn("{#", page.html)

    def test_no_page_requests_anything_from_another_site(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertEqual([address for address in requests(page) if not on_this_site(address)], [])

    def test_each_page_of_the_example_is_within_the_size_limit(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertLessEqual(page_weight(self.out, path, page), SIZE_LIMIT)

    def test_each_page_of_the_largest_board_published_is_within_the_size_limit(self):
        board = read_json(self.board_file())
        self.write_board({**board, "rows": made_up_rows(LARGEST_BOARD)})
        pages = self.build_pages()
        self.assertEqual(len(pages[BOARD].rows()), LARGEST_BOARD)
        self.assertEqual(len(pages[board_day_page("2026-11-09")].rows()), LARGEST_BOARD)
        for path, page in pages.items():
            with self.subTest(path):
                self.assertLessEqual(page_weight(self.out, path, page), SIZE_LIMIT)

    def test_a_long_boards_root_stays_within_its_transfer_budget_once_gzipped(self):
        """AndrewGodlewsky/RisingRepos#122 and #199. gzip at level 6 packs it a little less tightly than the server
        does. The budget is above the eval's own limit, which a root of the real board meets."""
        limits = read_json(EVAL_LIMITS)
        self.assertGreaterEqual(
            WIRE_BUDGET, max(limits[profile]["transfer_size"]["limit"] for profile in ("phone", "desktop"))
        )
        board = read_json(self.board_file())
        self.write_board({**board, "rows": typical_rows(WIRE_ROWS)})
        pages = self.build_pages()
        self.assertEqual(len(pages[BOARD].rows()), WIRE_ROWS)
        packed = gzip.compress((self.out / BOARD).read_bytes(), compresslevel=6, mtime=0)
        self.assertLess(len(packed), WIRE_BUDGET)


class TheChecks(unittest.TestCase):
    """The two checks above, on pages written to break them, since the built pages give them nothing to find."""

    def test_the_check_for_requests_finds_each_address_on_another_site_and_no_link(self):
        page = Page(
            '<html><head><link rel="preconnect" href="https://fonts.example">'
            "<style>@font-face { src: url(https://fonts.example/a.woff2) } @import 'https://cdn.example/x.css';</style>"
            '</head><body><img srcset="https://img.example/a.png 2x, b.png 1x"><a href="https://github.com/o/n">o/n</a>'
            "</body></html>"
        )
        self.assertEqual(
            [address for address in requests(page) if not on_this_site(address)],
            [
                "https://fonts.example",
                "https://fonts.example/a.woff2",
                "https://cdn.example/x.css",
                "https://img.example/a.png",
            ],
        )

    def test_the_size_counts_each_file_on_this_site_that_a_page_loads(self):
        out = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (out / "day").mkdir()
        (out / "site.css").write_bytes(b"a" * 100)
        (out / "day" / "day.css").write_bytes(b"b" * 50)
        html = (
            '<html><head><link rel="stylesheet" href="/site.css"><link rel="stylesheet" href="day.css">'
            '<link rel="icon" href="data:,"></head><body></body></html>'
        )
        self.assertEqual(page_weight(out, "day/index.html", Page(html)), len(html) + 150)


if __name__ == "__main__":
    unittest.main()
