"""The site's pages, addresses, and folder paths, kept apart so generator modules import them without cycles (#252)."""

from pathlib import Path

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
SEARCH = "search/index.html"
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
    SEARCH: "search.html",
    NOT_FOUND: "not-found.html",
}
"""Each page the build writes, by its path in the site, and the template in templates/ that renders it.

- `BOARD`, the site's root, is the newest board day's board. It is the one page that states its board day in the
  data contract's two meta tags, which latest.html adds to board.html, so whatever reads them reads the root.
- `DAYS` lists every board day, newest first.
- `BOARD_DAY` is written once for each board day in the index, the newest included, so that each board day keeps
  one address however many come after it.
- `HOW_IT_WORKS` draws how the boards are ranked as one flow diagram of the checks a repository goes through, for
  the formula `DESCRIBED_FORMULA` names, with the newest board's star bands, and says what the site is set in (#214).
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
one unnoticed. That notice is all a new formula sets off: the page's flow diagram is this version's, written by hand
from RisingRepos's src/risingrepos/scoring.py and src/risingrepos/boards.py, since a board day's file brings none of
the formula's rules. So when RisingRepos raises the version, the diagram is redrawn from that code and this raised in
the same change (AGENTS.md, "How it works is written for one formula", #214)."""


def board_day_page(day: str) -> str:
    """The path of a board day's own page: '2026-11-09' as 'days/2026-11-09/index.html'."""
    return BOARD_DAY.format(board_day=day)


def address(path: str) -> str:
    """A page's address on the site, from its path: 'days/index.html' as '/days/'."""
    return "/" + path.removesuffix("index.html")


def day_address(day: str) -> str:
    """The address of a board day's page: '2026-11-09' as '/days/2026-11-09/'."""
    return address(board_day_page(day))
