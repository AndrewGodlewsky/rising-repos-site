"""`weigh`: say what a change adds to the pages, in bytes, before it and after it.

A page has little room left: `tests/test_page_weight.py` holds a page to PAGE_LIMIT bytes and the root of a long
board to WIRE_BUDGET gzipped, the first within about a tenth of its limit and the second within a few hundredths.
So a feature measures what it adds, for its plan's budget and for its pull request. Each stage of the runs on #27,
#28, and #29 wrote a script of its own for that, and the figures in a plan came from a script nobody else could run
again (#80). This is that script, once: it builds the site before the change and after it, with the same data, and
prints the heaviest page of each kind and the root as it travels.

It measures the boards the site has. The two limits are held on boards the tests make up, the longest of them
longer than any published, so this informs and judges nothing: the tests are what a change has to pass.
"""

import argparse
import gzip
import sys
import tempfile
from pathlib import Path

from sitework import layout, shell

PAGE_LIMIT = 550_000
WIRE_BUDGET = 155_000
"""The two limits of `tests/test_page_weight.py`, which `tests/test_sitework_weigh.py` holds to that file's own:
the most bytes a page may take, and the most the root of a long board may take gzipped."""

FILE_LIMIT = 20_000
"""Cloudflare Pages's file count cap for a single deployment, tracked here as the archive grows (#246)."""

ROOT_PAGE = "index.html"
GZIP_LEVEL = 6
"""The level the size test packs the root at. A server packs a little tighter."""


def inventory(site: Path) -> tuple[int, int]:
    """The total count of files in a built site and their combined size in bytes (#246)."""
    files = [path for path in site.rglob("*") if path.is_file()]
    return len(files), sum(path.stat().st_size for path in files)


def heaviest(site: Path) -> dict[str, tuple[str, int]]:
    """The heaviest page of each kind in a built site: its path and its bytes."""
    found: dict[str, tuple[str, int]] = {}
    for page in layout.pages(site):
        kind, size = layout.kind_of(page), (site / page).stat().st_size
        if size > found.get(kind, ("", -1))[1]:
            found[kind] = (page, size)
    return found


def packed(site: Path) -> int | None:
    """The root's bytes once gzipped, or None for a site with no root."""
    root = site / ROOT_PAGE
    return len(gzip.compress(root.read_bytes(), compresslevel=GZIP_LEVEL, mtime=0)) if root.is_file() else None


def change(before: int | None, after: int) -> str:
    """How a weight moved, with its sign, or that the page is new."""
    return "new" if before is None else "the same" if after == before else f"{after - before:+,}"


def report(base: Path, head: Path) -> str:
    """What the change added to the pages, from the site built before it and the site built after it. Each kind's
    page is the heaviest the head has, weighed in the base at the same address."""
    after = heaviest(head)
    kinds = [*layout.ORDER, *sorted(kind for kind in after if kind not in layout.ORDER)]
    lines = [
        "# The pages' weight",
        "",
        "The heaviest page of each kind, in bytes, before the change and after it.",
        "",
        "| Kind | Page | Before | After | Change | Room left |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for kind in kinds:
        if kind not in after:
            continue
        page, size = after[kind]
        was = (base / page).stat().st_size if (base / page).is_file() else None
        before = "-" if was is None else f"{was:,}"
        lines.append(
            f"| {kind} | `{layout.address(page)}` | {before} | {size:,} | {change(was, size)} | {PAGE_LIMIT - size:,} |"
        )
    was, now = packed(base), packed(head)
    if now is not None:
        before = "-" if was is None else f"{was:,}"
        lines += [
            "",
            f"The root gzipped at level {GZIP_LEVEL}: {before} before, {now:,} after ({change(was, now)}).",
        ]
    base_files, base_bytes = inventory(base)
    head_files, head_bytes = inventory(head)
    lines += [
        "",
        f"Built files: {base_files:,} before, {head_files:,} after ({change(base_files, head_files)}; "
        f"{FILE_LIMIT - head_files:,} below the {FILE_LIMIT:,}-file deployment cap); "
        f"total size {head_bytes:,} bytes ({change(base_bytes, head_bytes)}).",
    ]
    lines += [
        "",
        f"A page may take {PAGE_LIMIT:,} bytes, and the root of a 713-row board {WIRE_BUDGET:,} gzipped. "
        "`tests/test_page_weight.py` holds both on boards it makes up, which are longer than these, so the room "
        "left here is more than the room a change has. Markup added to a row is added once for every row.",
    ]
    return "\n".join(lines)


def main(command: str, arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="Build the site before a change and after it, and print the heaviest page of each kind and "
        "the root's gzipped weight, in bytes. It informs: it exits 1 only when a build fails.",
    )
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
            layout.build("base", options.base or shell.git("merge-base", "origin/main", "HEAD"), base)
            layout.build("head", options.head, head)
            said = report(base, head)
    except shell.Failed as error:
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    print(said)
    return 0
