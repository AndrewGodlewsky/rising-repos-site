"""`layout-report` and `pictures`: say in words how the pages a change altered are laid out, and take their pictures.

A reviewer reads no pictures, since each one costs tokens, so the report says what a picture would show
(docs/workflow-plan.md, section 8): what reaches past the right edge of a phone's screen and of a desktop's, how
the outline a reader meets changed, and which values the stylesheet newly uses, for the reviewer to hold against
STYLE.md. It informs, and nothing fails on it. The pictures are still taken, for the owner, who gets them when a
feature ships.

Both build the pages before the change and after it, from the same data, so that only the code differs. The pages
the change altered are the files whose bytes differ, and the new ones. Most pages are board days from one
template, so one page of each kind is looked at, and the rest of its kind are counted.

What needs a browser is kept apart from what does not: the choice of pages, the stylesheet's new values, and the
difference between two outlines are plain functions of files and text.
"""

import argparse
import contextlib
import difflib
import functools
import http.server
import io
import re
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

from sitebuild import BASELINE, BOARD, BOARD_DAY, DAYS, FOR_AGENTS, HOW_IT_WORKS, NOT_FOUND
from sitework import shell

STYLESHEET = "sitebuild/templates/site.css"

SCREENS = {390: 844, 1440: 900}
"""The two screens a page is looked at on, each width with its height: a phone's and a desktop's."""

KINDS = {
    BOARD: "The root",
    DAYS: "History",
    BASELINE: "Baseline",
    HOW_IT_WORKS: "How it works",
    FOR_AGENTS: "For agents",
    NOT_FOUND: "The not-found page",
}
BOARD_DAYS = "A board day"
BOARD_DAY_PAGE = re.compile(re.escape(BOARD_DAY).replace(re.escape("{board_day}"), "[^/]+"))
ORDER = ["The root", BOARD_DAYS, "History", "Baseline", "How it works", "For agents", "The not-found page"]
"""The kinds of page the site has, in the order a reader comes to them."""

NO_PAGE = "No page differs between the base and the head."

OUTLINE_LINES = 40
"""How many lines of an outline, or of the difference between two, the report gives before it cuts."""


@dataclass(frozen=True)
class Chosen:
    """The one page of its kind that the report looks at."""

    kind: str
    path: str
    new: bool
    """The base has no such page."""
    others: int
    """How many other pages of the kind differ too."""
    own: int = 0
    """How many of the kind's pages that differ do so in their own markup, when not all of them do."""


SHARED = re.compile(
    r"<style\b.*?</style>|<script\b.*?</script>|<meta\b[^>]*http-equiv[^>]*>", re.DOTALL | re.IGNORECASE
)
"""What every page of the site holds alike: its styles, its script, and the policy that names the script's hash. A
change to the stylesheet alters these in every page, whatever else it alters."""


def own_markup(page: Path) -> str:
    """A page without what every page holds alike."""
    return SHARED.sub("", page.read_text(encoding="utf-8", errors="replace"))


def kind_of(path: str) -> str:
    """Which kind of page a file of the built site is. A page of a kind the site does not have yet is named by its
    folder, so that a feature which adds many pages from one template has one of them looked at."""
    if path in KINDS:
        return KINDS[path]
    if BOARD_DAY_PAGE.fullmatch(path):
        return BOARD_DAYS
    folder, _, rest = path.partition("/")
    return f"A page under /{folder}/" if rest else f"The page /{path}"


def pages(site: Path) -> list[str]:
    return sorted(path.relative_to(site).as_posix() for path in site.rglob("*.html"))


def choose(base: Path, head: Path) -> list[Chosen]:
    """One page of each kind the change altered, from the two built sites. Of a kind's pages it takes the last
    by name, which for board days is the newest, among those the change altered in their own markup.

    Every page holds the stylesheet, so a change to it alters the bytes of every page. On #28 the change put a
    link into the day bar of each earlier board, and the newest board's bar holds no such link: the report took
    the newest board day, said its outline was the same, and showed nothing of what the change made, and three
    agents wrote scripts of their own to see it (#73). So a page that differs only in what every page holds
    alike stands for its kind only when no page of the kind differs in more."""
    differing: dict[str, list[tuple[str, bool]]] = {}
    for page in pages(head):
        new = not (base / page).is_file()
        if new or (base / page).read_bytes() != (head / page).read_bytes():
            differing.setdefault(kind_of(page), []).append((page, new))
    order = [*ORDER, *sorted(kind for kind in differing if kind not in ORDER)]
    chosen = []
    for kind in order:
        found = differing.get(kind)
        if not found:
            continue
        # One page of a kind is the one to take, so the pages are read again only where there is a choice.
        own = [
            (page, new)
            for page, new in (found if len(found) > 1 else [])
            if new or own_markup(base / page) != own_markup(head / page)
        ]
        some = 0 < len(own) < len(found)
        chosen.append(Chosen(kind, *(own if some else found)[-1], others=len(found) - 1, own=len(own) if some else 0))
    return chosen


def gone(base: Path, head: Path) -> list[str]:
    """Each page the base has and the head does not."""
    return [page for page in pages(base) if not (head / page).is_file()]


def address(path: str) -> str:
    """A page's address on the site, from its file."""
    return "/" + path.removesuffix("index.html")


FAMILIES = ("colour", "font size", "font weight", "space", "corner radius")
"""What the style guide gives values for, and so what a new value is listed under."""

NOT_STYLES = re.compile(r"\{#.*?#\}|/\*.*?\*/|\{\{.*?\}\}|\{%.*?%\}", re.DOTALL)
"""A note of the template or of the stylesheet, and anything the build puts in: none of it is a rule."""
PART = re.compile(r"([^{};]*)([{};])")
COLOUR = re.compile(r"#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\([^()]*\)")
SPACE = re.compile(r"(padding|margin)(-[a-z-]+)?|(row-|column-)?gap")
RADIUS = re.compile(r"border-([a-z-]+-)?radius")


def sides(value: str) -> list[str]:
    """The values of a shorthand, apart: split at white space and at a radius's slash, outside any brackets."""
    found, depth, word = [], 0, ""
    for letter in value:
        depth += (letter == "(") - (letter == ")")
        if depth == 0 and (letter.isspace() or letter == "/"):
            found += [word] if word else []
            word = ""
        else:
            word += letter
    return found + ([word] if word else [])


def uses(name: str, value: str):
    """Each value one declaration uses, with the family it belongs to."""
    for colour in COLOUR.findall(value.lower()):
        yield "colour", colour
    if name == "font-size":
        yield "font size", value
    elif name == "font-weight":
        yield "font weight", value
    elif name == "font":
        # The shorthand: its size is the first word with a unit, and any weight is a word before it.
        words = value.split()
        size = next((number for number, word in enumerate(words) if re.match(r"[\d.]+[a-z%]", word)), None)
        if size is not None:
            yield "font size", words[size].partition("/")[0]
            for word in words[:size]:
                if word.isdigit() or word in ("bold", "bolder", "lighter"):
                    yield "font weight", word
    elif SPACE.fullmatch(name):
        for side in sides(value):
            yield "space", side
    elif RADIUS.fullmatch(name):
        for side in sides(value):
            yield "corner radius", side


def values(stylesheet: str) -> dict[str, dict[str, list[str]]]:
    """Every value the stylesheet uses, by family, each with the rules that use it, in the order they come."""
    found = {family: {} for family in FAMILIES}
    rule = ""
    for text, end in PART.findall(NOT_STYLES.sub(" ", stylesheet)):
        if end == "{":
            rule = " ".join(text.split())
        elif ":" in text:
            name, _, value = text.partition(":")
            for family, used in uses(name.strip().lower(), value.replace("!important", "").strip()):
                found[family].setdefault(used, []).append(rule)
    return found


def new_values(base: str, head: str) -> list[str]:
    """A line for each value the head's stylesheet uses that the base's did not: its family, and where it is."""
    before, after = values(base), values(head)
    lines = []
    for family in FAMILIES:
        for value, rules in after[family].items():
            if value not in before[family]:
                more = f" and {len(rules) - 1} more" if len(rules) > 1 else ""
                lines.append(f"- {family} `{value}`, in `{rules[0]}`{more}")
    return lines


def cut(lines: list[str], limit: int, what: str) -> list[str]:
    return lines if len(lines) <= limit else [*lines[:limit], f"... and {len(lines) - limit} more lines of {what}."]


def outline_diff(base: str, head: str, limit: int | None = OUTLINE_LINES) -> list[str]:
    """How the head's outline differs from the base's: each changed part with two lines either side, under a line
    that gives its place in the head's outline and the heading a reader has passed when they come to it. An
    outline's own lines begin with a dash, so a line taken out or put in is marked two spaces clear of it. With
    no limit it is given whole."""
    before, after = base.splitlines(), head.splitlines()
    lines = []
    for part in difflib.SequenceMatcher(None, before, after, autojunk=False).get_grouped_opcodes(2):
        first = next(start for change, _, _, start, _ in part if change != "equal")
        passed = next((line.strip() for line in reversed(after[:first]) if line.strip().startswith("- heading ")), "")
        lines.append(f"@@ line {first + 1}{', under ' + passed[2:] if passed else ''} @@")
        for change, from_, to, start, end in part:
            if change == "equal":
                lines += ["   " + line for line in before[from_:to]]
            else:
                lines += ["-  " + line for line in before[from_:to]] + ["+  " + line for line in after[start:end]]
    return cut(lines, limit, "the difference") if limit else lines


PAST_THE_EDGE = """() => {
  const screen = document.documentElement.clientWidth;
  const past = (element) => element.getBoundingClientRect().right > screen + 0.5;
  const shown = (element) => {
    if (getComputedStyle(element).visibility === "hidden") return false;
    let { left, top, right, bottom } = element.getBoundingClientRect();
    for (let around = element.parentElement; around !== document.documentElement; around = around.parentElement) {
      const style = getComputedStyle(around);
      if (style.overflowX === "visible" && style.overflowY === "visible" && style.clipPath === "none") continue;
      const box = around.getBoundingClientRect();
      [left, top] = [Math.max(left, box.left), Math.max(top, box.top)];
      [right, bottom] = [Math.min(right, box.right), Math.min(bottom, box.bottom)];
    }
    return right - left > 1 && bottom - top > 1;
  };
  const found = [...document.body.querySelectorAll("*")].filter((element) =>
    past(element) && (element.parentElement === document.body || !past(element.parentElement)) && shown(element));
  return {
    wide: document.documentElement.scrollWidth,
    screen: screen,
    past: found.length,
    first: found.slice(0, 5).map((element) => ({
      tag: [element.tagName.toLowerCase(), ...element.classList].join("."),
      right: Math.round(element.getBoundingClientRect().right),
      text: (element.innerText || element.getAttribute("aria-label") || "").trim().replace(/\\s+/g, " ").slice(0, 60),
    })),
  };
}"""
"""Run in a page: how wide the page is against its screen, and the elements whose right edge is past the screen's.
Of those, only the outermost are kept, since everything inside an element that is past the edge is past it too.
One of which nothing can be seen is left out: the words kept for a screen reader sit in a box one pixel wide that
hides what overflows it, and no picture would show them. `shown` cuts an element's box by every box around it
that hides its overflow, and keeps the element when more than a pixel of it is left."""


@dataclass
class Seen:
    """What the browser shows of one page on one screen."""

    outline: str
    wide: int
    screen: int
    past: int
    first: list[dict]

    @property
    def scrolls(self) -> bool:
        return self.wide > self.screen


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *arguments):
        """Say nothing: the report is what this command prints."""


@contextlib.contextmanager
def served(site: Path):
    """Serve a built site from this machine alone, on a port that is free, and give its address."""
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(site))) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            yield f"http://127.0.0.1:{server.server_address[1]}"
        finally:
            server.shutdown()


@contextlib.contextmanager
def chrome():
    """The Chrome this machine already has, with no window. Playwright is imported here, so that the parts of
    this module that need no browser can be used where there is none."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        try:
            yield browser
        finally:
            browser.close()


def published(site: Path) -> str | None:
    """When the newest board of a built site was published, as its root says, or None for a site that does not
    say. A page counts its board's age from the reader's clock, shows a notice from 26 hours, and shows no board
    from seven days, so a page is looked at with the clock set to this time: the report is then the same on
    whichever day it is made, and never describes a page with its board hidden."""
    root = site / BOARD
    text = root.read_text(encoding="utf-8") if root.is_file() else ""
    said = re.search(r'data-newest-published-at="?([0-9T:Z-]+)', text)
    return said[1] if said else None


def opened(browser, address: str, width: int, clock: str | None):
    """A page, loaded on a screen `width` pixels wide, with its type in place."""
    page = browser.new_page(viewport={"width": width, "height": SCREENS[width]})
    if clock:
        page.clock.set_fixed_time(clock)
    page.goto(address, wait_until="load")
    page.evaluate("document.fonts.ready.then(() => true)")
    return page


def look(browser, address: str, width: int, clock: str | None) -> Seen:
    page = opened(browser, address, width, clock)
    seen = Seen(outline=page.locator("body").aria_snapshot(), **page.evaluate(PAST_THE_EDGE))
    page.close()
    return seen


def count(number: int, one: str, many: str) -> str:
    return f"1 {one}" if number == 1 else f"{number} {many}"


def edge(seen: Seen, before: Seen | None) -> list[str]:
    """What reaches past the right edge of the screen at the head, and whether it did at the base."""
    if not seen.scrolls and not seen.past:
        was = ""
        if before and (before.scrolls or before.past):
            was = f" At the base, {count(before.past, 'element', 'elements')} reached past it."
        return ["Nothing reaches past the right edge, and the page does not scroll sideways." + was]
    then = ""
    if before:
        then = ", as it did at the base" if before.scrolls else ", and at the base it did not"
    lines = [
        f"The page scrolls sideways: it is {seen.wide} pixels wide on a screen of {seen.screen}{then}."
        if seen.scrolls
        else "The page does not scroll sideways, so what is past the edge is cut off or scrolls inside its own box."
    ]
    if seen.past:
        reach = count(seen.past, "element reaches", "elements reach")
        was = f" ({before.past} at the base)" if before else ""
        lines += ["", f"{reach} past the right edge{was}. The first:", ""]
        for element in seen.first:
            text = f': "{element["text"]}"' if element["text"] else ""
            lines.append(f"- `{element['tag']}`, to {element['right']} pixels{text}")
    return lines


def fenced(lines: list[str], language: str = "") -> list[str]:
    return ["", f"```{language}", *lines, "```"]


def outline(seen: Seen, before: Seen | None, said: dict, page: str, width: int) -> list[str]:
    """How the outline changed, for one page on one screen. `said` holds each change already given and where, so
    that a change is printed once: the root and the newest board day hold the same board, and most changes read
    the same on both screens. Two changes are the same when their lines are, wherever in the outline they fall."""
    if before is None:
        whole, what = seen.outline.splitlines(), "the outline"
        opening, same = "The outline, which the base does not have:", "is as it is"
    else:
        whole, what = outline_diff(before.outline, seen.outline, limit=None), "the difference"
        opening, same = "The outline, from the base to the head:", "changed as it did"
        if not whole:
            return ["The outline is the same at the base and at the head."]
    change = (before is None, *(line for line in whole if not line.startswith("@@")))
    if change in said:
        there, at = said[change]
        return [f"The outline {same} {'' if there == page else f'on `{there}` '}at {at} pixels wide."]
    said[change] = (page, width)
    return [opening, *fenced(cut(whole, OUTLINE_LINES, what), "" if before is None else "diff")]


def report(base: Path, head: Path, base_stylesheet: str, head_stylesheet: str) -> str:
    """The layout report of a change, from the site built before it and the site built after it."""
    chosen, removed = choose(base, head), gone(base, head)
    if not chosen and not removed:
        return NO_PAGE
    clock = published(head)
    differing = sum(1 + page.others for page in chosen)
    lines = [
        "# Layout report",
        "",
        f"{count(differing, 'page differs', 'pages differ')} between the base and the head. One page of each kind is "
        f"described below, as Chrome lays it out with scripts on, at {' and at '.join(map(str, SCREENS))} pixels wide.",
    ]
    if clock:
        lines += [
            f"The browser's clock is set to {clock}, when the newest board was published, so that no page shows "
            "the notice of an old board."
        ]
    said = {}
    with served(base) as old, served(head) as new, chrome() as browser:
        for page in chosen:
            others = count(page.others, "other page of its kind differs", "other pages of its kind differ")
            lines += ["", f"## {page.kind}, `{address(page.path)}`", ""]
            lines += [
                ("New: the base has no such page." if page.new else "It differs from the base's.")
                + (f" {others} too." if page.others else "")
                + (
                    f" This is the last by name of the {page.own} that differ in their own markup: the rest differ "
                    "only in the styles and the script that every page holds."
                    if page.own
                    else ""
                )
            ]
            for width in SCREENS:
                before = None if page.new else look(browser, old + address(page.path), width, clock)
                seen = look(browser, new + address(page.path), width, clock)
                lines += ["", f"### At {width} pixels wide", "", *edge(seen, before)]
                lines += ["", *outline(seen, before, said, address(page.path), width)]
    if removed:
        lines += ["", "## Pages the head no longer has", "", *(f"- `{address(page)}`" for page in removed)]
    added = new_values(base_stylesheet, head_stylesheet)
    lines += ["", "## The stylesheet's new values", ""]
    if added:
        lines += [f"Each is a value `{STYLESHEET}` uses at the head and did not at the base, to hold against STYLE.md."]
        lines += ["", *added]
    else:
        families = f"{', '.join(FAMILIES[:-1])}, or {FAMILIES[-1]}"
        lines += [f"`{STYLESHEET}` uses no {families} at the head that it did not at the base."]
    return "\n".join(lines)


def take_pictures(head: Path, chosen: list[Chosen], out: Path) -> list[Path]:
    """Write a picture of the whole of each chosen page, as the head lays it out on each screen, and give the
    files. A file is named for its page's address and its screen's width."""
    out.mkdir(parents=True, exist_ok=True)
    clock = published(head)
    written = []
    with served(head) as site, chrome() as browser:
        for chosen_page in chosen:
            name = chosen_page.path.removesuffix("index.html").removesuffix(".html").strip("/").replace("/", "-")
            for width in SCREENS:
                page = opened(browser, site + address(chosen_page.path), width, clock)
                written.append(out / f"{name or 'root'}-{width}.png")
                page.screenshot(path=written[-1], full_page=True)
                page.close()
    return written


def read_stylesheet(code: Path) -> str:
    """The stylesheet text of `code`: `site.css` together with any partials under `sitebuild/templates/css/` (#252)."""
    main_css = (code / STYLESHEET).read_text(encoding="utf-8")
    partials = code / Path(STYLESHEET).parent / "css"
    if not partials.is_dir():
        return main_css
    return "\n".join([main_css, *(path.read_text(encoding="utf-8") for path in sorted(partials.glob("*.css")))])


def build(which: str, commit: str | None, out: Path) -> str:
    """Build the pages of `commit` into `out`, from a temporary worktree of it, or of this checkout as it stands
    when no commit is named. Either way the data is this checkout's, so that two builds differ only by their
    code. It gives the stylesheet the pages were built with."""
    with shell.worktree(commit) if commit else contextlib.nullcontext(shell.ROOT) as code:
        cli = code / "sitebuild" / "__main__.py"
        options = (
            ["--no-share-images"] if cli.is_file() and "--no-share-images" in cli.read_text(encoding="utf-8") else []
        )
        try:
            shell.run(
                sys.executable,
                "-m",
                "sitebuild",
                str(out),
                "--data",
                str(shell.ROOT / "site-data"),
                *options,
                cwd=code,
            )
        except shell.Failed as error:
            raise shell.Failed(f"the build of the {which} failed.\n{error}") from error
        return read_stylesheet(code)


def main(command: str, arguments: list[str]) -> int:
    what = {
        "layout-report": "Describe in words how the pages a change altered are laid out. It informs: it exits 1 "
        "only when a build fails.",
        "pictures": "Take a picture of each page a change altered, at a phone's width and at a desktop's.",
    }
    parser = argparse.ArgumentParser(prog=f"python -m sitework {command}", description=what[command])
    if command == "pictures":
        parser.add_argument("--out", type=Path, required=True, metavar="DIR", help="the folder the pictures go into")
    parser.add_argument(
        "--base", metavar="REF", help="the commit before the change (default: the merge base of origin/main and HEAD)"
    )
    parser.add_argument(
        "--head",
        metavar="REF",
        help="the commit with the change (default: this checkout as it stands: HEAD, and what is not yet committed)",
    )
    options = parser.parse_args(arguments)
    try:
        with tempfile.TemporaryDirectory() as folder:
            base, head = Path(folder) / "base", Path(folder) / "head"
            base_stylesheet = build("base", options.base or shell.git("merge-base", "origin/main", "HEAD"), base)
            head_stylesheet = build("head", options.head, head)
            if command == "pictures":
                chosen = choose(base, head)
                said = "\n".join(str(path) for path in take_pictures(head, chosen, options.out)) if chosen else NO_PAGE
            else:
                said = report(base, head, base_stylesheet, head_stylesheet)
    except shell.Failed as error:
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")  # a page's words hold letters the console's own encoding lacks
    print(said)
    return 0
