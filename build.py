#!/usr/bin/env python3
"""Walking-skeleton site build — wayfinder ticket #6.

Reads `site-data/snapshot.json` (pushed by scripts/skeleton-collect.py, #5),
renders one board-ish page into `dist/`, then verifies it. Non-zero exit blocks
the deploy (J §7 step 4).

ponytail: one file, one template, one page. Ticket #13 (full site build-out)
replaces all of it — do not grow this into the real build.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
SNAPSHOT = ROOT / "site-data" / "snapshot.json"
LEAD_COUNT = 10  # I2: lead-and-index — the top ten get full treatment

# I §8.1 / REVIEW D8. Hours, never day buckets: the board for UTC day D always
# publishes during UTC day D+1, so any date comparison misfires every night.
FRESH_BELOW_HOURS = 26
DARK_ABOVE_HOURS = 7 * 24


def staleness(board_ts: datetime, now: datetime) -> tuple[str, float]:
    """THE staleness rule (I7/I §8.1) — one function, all causes, computed once.

    A held day, a missed deploy and a CI failure are indistinguishable to a
    visitor, so they must render identically. Returns (state, age_hours).
    """
    hours = (now - board_ts).total_seconds() / 3600
    if hours < FRESH_BELOW_HOURS:
        return "fresh", hours
    if hours <= DARK_ABOVE_HOURS:
        return "banner", hours
    return "dark", hours


def render(data: dict, now: datetime) -> str:
    board_ts = datetime.fromisoformat(data["generated_at"])
    # ponytail: the skeleton has no run.json yet, so `generated_at` stands in as
    # the board timestamp. #7/#8 introduce run.json; repoint this one line then.
    state, age_hours = staleness(board_ts, now)

    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        undefined=StrictUndefined,  # I1
        autoescape=True,
    )
    repos = data["repos"] if state != "dark" else []
    return env.get_template("index.html").render(
        repos=repos,
        lead=repos[:LEAD_COUNT],
        rest=repos[LEAD_COUNT:],
        state=state,
        age_days=int(age_hours // 24),
        board_date=board_ts.date().isoformat(),
        board_ts=board_ts.strftime("%Y-%m-%d %H:%M UTC"),
        build_ts=now.replace(microsecond=0).isoformat(),
        matched=data["matched"],
    )


# --- verify (I §9, blocking gate) -------------------------------------------

INTERNAL_HREF = re.compile(r'href="(/[^"#?]*)')
EMPTY_SLOT = re.compile(r'class="num"[^>]*>\s*</')


def check_links(html: str, dist: Path) -> list[str]:
    """I §9.3 — every internal link resolves to a file that exists."""
    bad = []
    for href in INTERNAL_HREF.findall(html):
        target = dist / href.lstrip("/")
        if href.endswith("/"):
            target = target / "index.html"
        if not target.exists():
            bad.append(href)
    return bad


def verify(html: str, data: dict, state: str, dist: Path) -> list[str]:
    """Subset of I §9 that applies to a one-page skeleton.

    ponytail: skipped 9.1 page count, 9.4 chart geometry, 9.5 run.json row
    count, 9.6 dual rank labels, 9.8 JS-disabled parse — none have subjects yet
    (one page, no charts, no run.json, no all-time rank, no JS). #13 adds them.
    """
    problems = []
    if EMPTY_SLOT.search(html):
        problems.append("empty value slot in a class=num element (I §9.2)")
    if ">None<" in html or "Undefined" in html:
        problems.append("unrendered None/Undefined reached the output")
    for href in check_links(html, dist):
        problems.append(f"broken internal link: {href} (I §9.3)")
    # I §9.7 — the staleness contract: static board date plus both meta tags.
    for tag in ("rr:board-date", "rr:build-ts"):
        m = re.search(rf'name="{tag}" content="([^"]+)"', html)
        if not m:
            problems.append(f"missing meta tag {tag} (I §9.7)")
        elif not _parseable(m.group(1)):
            problems.append(f"meta tag {tag} is not parseable: {m.group(1)}")
    expected = 0 if state == "dark" else len(data["repos"])
    got = html.count('<li class="repo')
    if got != expected:
        problems.append(f"board row count {got} != {expected} repos in snapshot")
    # J §12.5 — `_headers` must reach the upload root, or the whole cache policy
    # silently reverts to Cloudflare's defaults with a green build.
    if not (dist / "_headers").exists():
        problems.append("_headers missing from the upload root (J §12.5)")
    # ponytail: J §12.1 (run.json age), §12.3 (domain config survived) and §12.4
    # (file count/size) have no subject yet — no run.json, domain bound at the
    # Pages project not by a CNAME file, one page and no assets. #17 adds them.
    return problems


def assert_deploy_kind(state: str, kind: str) -> list[str]:
    """J §12.2 — the staleness function's output must match the deploy kind.

    A normal publish must never quietly ship stale data. A watchdog deploy ships
    the stale state on purpose, so `banner`/`dark` is its job, not a failure.
    """
    if kind == "normal" and state != "fresh":
        return [
            f"normal deploy with board data in state '{state}', not 'fresh' "
            f"(J §12.2) — re-run as a watchdog deploy to publish the stale state"
        ]
    return []


def _parseable(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


# --- self-check --------------------------------------------------------------


def selfcheck() -> None:
    """The one runnable check: staleness boundaries, and that the link checker
    actually fails on a planted broken link (I §9.3 names the vacuous pass as a
    known trap)."""
    t0 = datetime(2026, 8, 7, 0, 0, tzinfo=timezone.utc)
    cases = [
        (timedelta(hours=0), "fresh"),
        (timedelta(hours=25, minutes=59), "fresh"),
        (timedelta(hours=26), "banner"),
        (timedelta(days=7), "banner"),
        (timedelta(days=7, seconds=1), "dark"),
    ]
    for delta, want in cases:
        got, _ = staleness(t0, t0 + delta)
        assert got == want, f"staleness({delta}) = {got}, want {want}"

    assert check_links('<a href="/nope/">x</a>', DIST) == ["/nope/"], (
        "link checker passed a planted broken link — it is vacuous"
    )
    assert check_links("<a href=\"https://github.com/a/b\">x</a>", DIST) == []

    assert verify('<span class="num"></span>', {"repos": []}, "dark", DIST), (
        "verify passed an empty value slot"
    )

    # J §12.2 both ways: normal blocks on stale, watchdog is meant to ship it.
    assert assert_deploy_kind("banner", "normal"), "normal deploy shipped stale data"
    assert assert_deploy_kind("dark", "normal"), "normal deploy shipped dark data"
    assert not assert_deploy_kind("banner", "watchdog")
    assert not assert_deploy_kind("dark", "watchdog")
    assert not assert_deploy_kind("fresh", "normal")
    print("selfcheck ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument(
        "--deploy-kind",
        choices=("normal", "watchdog"),
        default="normal",
        help="normal blocks on stale data; watchdog publishes the stale state",
    )
    args = ap.parse_args()
    if args.selfcheck:
        selfcheck()
        return 0

    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    state, age_hours = staleness(datetime.fromisoformat(data["generated_at"]), now)
    html = render(data, now)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    (DIST / "index.html").write_text(html, encoding="utf-8")
    shutil.copy(ROOT / "static" / "_headers", DIST / "_headers")

    problems = verify(html, data, state, DIST)
    problems += assert_deploy_kind(state, args.deploy_kind)
    if problems:
        print("VERIFY FAILED — deploy blocked (J §7 step 4):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(
        f"built dist/index.html — {len(data['repos'])} repos, "
        f"board {age_hours:.1f} h old, state '{state}', {args.deploy_kind} deploy"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
