"""What every scenario of the owner's tests starts from: a reader with a browser, and the handles a reader has on a
page.

A scenario finds a thing as a reader would: by what it is and what it is called (the button named New, the board's
table, a link), by the words on the screen, or by the address in the bar. It names a tag only where the browser gives
the thing no role to find it by: a row's disclosure, a link in the part of an opened row that a screen reader is not
read, the dots of a drawing, and the tags in a page's head. It names no class and no id, so that a page's markup can
change round it and leave it standing.

A scenario names no repository and no board day either. It takes the first row, or a language the filter offers, so
that it reads a live site as it reads the made-up one.
"""

import re
import unittest
from datetime import date, datetime, timedelta
from urllib.parse import urljoin

from playwright.sync_api import Locator, Page, Response, expect

from owner_tests import the_site

PHONE = 390
DESKTOP = 1440
"""The two widths a reader's screen is taken to have, in pixels."""

WAIT = 10_000
"""How long, in milliseconds, a scenario waits for the page to show what it expects before it fails. A live site
answers more slowly than the server on this machine."""

expect.set_options(timeout=WAIT)

REASON = re.compile(r"·.*(usual pace|losing stars)")
"""The line an opened row starts with: what the repository gained, a dot, and how that stands against its usual
pace."""

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def needs_made_up_boards(test):
    """Mark a scenario that only the made-up boards can give its start: a board that holds a band back, the file a
    page was built from, a build that fails. Against a live site the loader leaves such a scenario out."""
    test.needs_made_up_boards = True
    return test


def the_day(words: str) -> date:
    """The day a page names in words, "2 Mar 2027" or "2 March 2027", wherever in `words` it stands."""
    day, month, year = re.search(r"(\d{1,2}) ([A-Z][a-z]{2})[a-z]* (\d{4})", words).groups()
    return date(int(year), MONTHS.index(month) + 1, int(day))


def number(figure: str) -> int | None:
    """The whole number a figure on the page gives, below nothing when a minus leads it, or None for a dash that
    stands where the page has no count."""
    digits = re.sub(r"\D", "", figure)
    if not digits:
        return None
    return -int(digits) if figure.strip()[0] in "−-" else int(digits)


def heading(page: Page) -> Locator:
    """The page's heading."""
    return page.get_by_role("heading", level=1)


def board(page: Page) -> Locator:
    """The board: the first table of the page's main part. An opened row holds a table of its own, after it. On
    Baseline it is that page's table, which lists the newest board's repositories too."""
    return page.get_by_role("main").get_by_role("table").first


def rows(page: Page) -> Locator:
    """The board's rows that are shown, in the order shown: each row whose header is a link to a repository, which
    reads owner/name. The row of headings has none, and a row of the table inside an opened row is headed by a date."""
    return board(page).get_by_role("row").filter(has=_repository(page.get_by_role("rowheader")))


def rows_that_open(page: Page) -> Locator:
    """The rows shown that a reader can open. A board's rows are, and the rows of Baseline's table are not."""
    return rows(page).filter(has=page.locator("summary"))


def names(page: Page) -> list[str]:
    """The name of each row shown, in the order shown."""
    return [name.strip() for name in _repository(board(page).get_by_role("rowheader")).all_inner_texts()]


def _repository(header: Locator) -> Locator:
    return header.get_by_role("link").filter(has_text="/")


def column(page: Page, heading: str) -> list[str]:
    """What each row shown says under the column whose heading starts with `heading`, in the order shown, read
    while no row is opened. A row's cells stand in the order of the headings, but for its name, which is the row's
    header and no cell."""
    table = board(page)
    headings = [" ".join(words.split()) for words in table.get_by_role("columnheader").all_inner_texts()]
    (at,) = [place for place, words in enumerate(headings) if words.startswith(heading)]
    if at > headings.index("Repository"):
        at -= 1
    cells = table.get_by_role("cell").all_inner_texts()
    return [" ".join(cell.split()) for cell in cells[at :: len(headings) - 1]]


def new_names(page: Page) -> list[str]:
    """The name of each row shown that the board marks New: the word stands beside the name, in the row's header."""
    headers = board(page).get_by_role("rowheader").all_inner_texts()
    return [name for name, header in zip(names(page), headers, strict=True) if header.split()[1:] == ["New"]]


def opener(row: Locator) -> Locator:
    """The control that opens a row. It is the summary of a disclosure, which has no role to be found by."""
    return row.locator("summary").first


def reason(row: Locator) -> Locator:
    """The reason a row is on the board, which shows once the row is opened."""
    return row.get_by_text(REASON).first


def open_row(row: Locator) -> None:
    """Open a row, and wait until it shows its reason."""
    opener(row).click()
    expect(reason(row)).to_be_visible()


def boards_it_was_on(row: Locator) -> Locator:
    """The table an opened row holds, of the boards it was on, which shows once the history has arrived."""
    return row.get_by_role("table")


def open_rows(shown: Locator) -> None:
    """Open each of the rows `shown`, and wait until the last shows what the history gives it. Each is opened from
    the keyboard, with Enter on its disclosure: over the hundreds of rows of a real board that is several times as
    quick as the pointer, which waits for the page to stop moving before each press. The disclosures are found
    once, and not once for each row, for the same reason."""
    for disclosure in shown.locator("summary").element_handles():
        disclosure.press("Enter")
    expect(boards_it_was_on(shown.last)).to_be_visible()


def facts(row: Locator) -> dict[str, str]:
    """An opened row's facts, each term with what the row gives for it."""
    terms = row.get_by_role("term").all_inner_texts()
    given = row.get_by_role("definition").all_inner_texts()
    return dict(zip(terms, given, strict=True))


def day_bar(page: Page) -> Locator:
    """The bar under the site's own, which holds the board days on either side of a board's."""
    return page.get_by_role("navigation", name="Board days", exact=True)


def address_of(link: Locator) -> str:
    """Where a link leads, in full."""
    return urljoin(link.page.url, link.get_attribute("href"))


class Scenario(unittest.TestCase):
    """A scenario: a reader, a browser, and the site. Each reader is a new one, who has chosen no theme and has
    visited nothing."""

    site: the_site.Site

    @classmethod
    def setUpClass(cls):
        cls.site = the_site.opened()

    def setUp(self):
        marked = getattr(getattr(self, self._testMethodName), "needs_made_up_boards", False)
        if marked and self.site.boards is None:
            # The loader leaves these out. This is for one of them asked for by name.
            self.skipTest("the scenario needs the made-up boards, and SITE names a site that was not built from them")

    def reader(
        self, *, width: int = DESKTOP, scripts: bool = True, dark: bool = False, clock: datetime | None = None
    ) -> Page:
        """A new reader's browser: `width` pixels wide, with scripts on or off, set to the dark theme or the light,
        and with its clock reading `clock`.

        With no clock given, a reader of the made-up site has one that reads an hour after the newest board was
        published, since those boards are dated once and for all, and the notice of an old board goes by the reader's
        clock. A reader of a live site has the clock of the machine."""
        context = self.site.browser.new_context(
            viewport={"width": width, "height": 900},
            java_script_enabled=scripts,
            color_scheme="dark" if dark else "light",
        )
        self.addCleanup(context.close)
        context.set_default_timeout(WAIT)
        context.set_default_navigation_timeout(3 * WAIT)
        if clock is None and self.site.boards:
            clock = datetime.fromisoformat(self.site.boards[0]["published_at"]) + timedelta(hours=1)
        if clock and scripts:
            context.clock.set_fixed_time(clock)
        return context.new_page()

    def visit(self, page: Page, path: str = "/") -> Response:
        """Take the reader to the site's address `path`, and give what the site answered."""
        return page.goto(self.site.address + path)

    def given(self, there: object, missing: str) -> None:
        """Hold a scenario to what it starts from: a board that tells which rows are new, a language to choose. The
        made-up boards have every such thing, so its absence there is a failure. A live board may lack one on a given
        day, and then the scenario is skipped, with what was missing."""
        if there:
            return
        if self.site.boards is None:
            self.skipTest(f"the site gives the scenario nothing to start from today: {missing}")
        self.fail(missing)

    def each_kind_of_page(self, page: Page) -> list[str]:
        """The address of a page of each kind, as a reader comes to them from the root: the root, each page the
        site's bar leads to, the board before the newest, and an address that holds no page."""
        self.visit(page)
        bar = page.get_by_role("banner").get_by_role("link")
        places = [address_of(bar.nth(at)) for at in range(bar.count())]
        before = day_bar(page).get_by_role("link", name=re.compile("^The board before"))
        if before.count():
            places.append(address_of(before))
        places.append(f"{self.site.address}/no-page-is-at-this-address/")
        return list(dict.fromkeys(places))
