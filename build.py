#!/usr/bin/env python3
"""Rising Repos site build — real boards (wayfinder ticket #10).

Reads `site-data/boards/{daily,weekly,monthly}.json` + `manifest.json`
(exported and pushed by the pipeline's board stage), renders the board
page into `dist/`, then verifies it. Non-zero exit blocks the deploy
(J §7 step 4). The skeleton's staleness function, deploy-kind gate and
non-vacuous verify harness survive unchanged — #13 (full site build-out)
adds every further page and surface.
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
BOARDS_DIR = ROOT / "site-data" / "boards"
BOARD_TYPES = ("daily", "weekly", "monthly")

# I §8.1 / REVIEW D8. Hours, never day buckets: the board for UTC day D always
# publishes during UTC day D+1, so any date comparison misfires every night.
FRESH_BELOW_HOURS = 26
DARK_ABOVE_HOURS = 7 * 24

EMPTY_REASONS = {
    "daily": "No repository cleared the RS ≥ 3 floor tonight — "
             "a quiet night is a real result, not a broken page.",
    "weekly": "No repository yet clears the weekly board's bar of 112 valid "
              "nightly observations — this board fills as data accrues.",
    "monthly": "No repository yet has the 182 valid nightly observations the "
               "monthly board requires — this board fills as data accrues.",
}


def staleness(board_ts: datetime, now: datetime) -> tuple[str, float]:
    """THE staleness rule (I7/I §8.1) — one function, all causes, computed once."""
    hours = (now - board_ts).total_seconds() / 3600
    if hours < FRESH_BELOW_HOURS:
        return "fresh", hours
    if hours <= DARK_ABOVE_HOURS:
        return "banner", hours
    return "dark", hours


def load_boards() -> tuple[dict, list[dict]]:
    manifest = json.loads((BOARDS_DIR / "manifest.json").read_text(encoding="utf-8"))
    boards = []
    for bt in BOARD_TYPES:
        doc = json.loads((BOARDS_DIR / f"{bt}.json").read_text(encoding="utf-8"))
        doc["empty_reason"] = EMPTY_REASONS[bt]
        if doc["strata_held"] and not doc["rows"]:
            doc["empty_reason"] = ("Every star range was held tonight — the "
                                   "crawl behind this board was incomplete, "
                                   "so publishing would be a guess.")
        boards.append(doc)
    return manifest, boards


def render(manifest: dict, boards: list[dict], now: datetime) -> str:
    board_ts = datetime.fromisoformat(manifest["generated_at"])
    state, age_hours = staleness(board_ts, now)
    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        undefined=StrictUndefined,  # I1
        autoescape=True,
    )
    facet_n = {"emerging": 0, "growing": 0, "established": 0}
    for b in boards:
        for k, v in b.get("facets", {}).get("band", {}).items():
            facet_n[k] = facet_n.get(k, 0) + v
    return env.get_template("index.html").render(
        boards=boards if state != "dark" else [],
        facet_n=facet_n,
        state=state,
        age_days=int(age_hours // 24),
        board_date=manifest["day"],
        board_ts=board_ts.strftime("%Y-%m-%d %H:%M UTC"),
        build_ts=now.replace(microsecond=0).isoformat(),
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


def verify(html: str, boards: list[dict], state: str, dist: Path) -> list[str]:
    problems = []
    if EMPTY_SLOT.search(html):
        problems.append("empty value slot in a class=num element (I §9.2)")
    if ">None<" in html or "Undefined" in html:
        problems.append("unrendered None/Undefined reached the output")
    for href in check_links(html, dist):
        problems.append(f"broken internal link: {href} (I §9.3)")
    for tag in ("rr:board-date", "rr:build-ts"):
        m = re.search(rf'name="{tag}" content="([^"]+)"', html)
        if not m:
            problems.append(f"missing meta tag {tag} (I §9.7)")
        elif not _parseable(m.group(1)):
            problems.append(f"meta tag {tag} is not parseable: {m.group(1)}")
    expected = 0 if state == "dark" else sum(len(b["rows"]) for b in boards)
    got = html.count('<li class="repo')
    if got != expected:
        problems.append(f"board row count {got} != {expected} rows exported")
    # G §9.2: a held stratum must be DISCLOSED, or the correct fallback is a
    # full hold — an undisclosed hold is the failure the breaker exists for.
    if state != "dark":
        for b in boards:
            if b["strata_held"] and b["rows"] and "disclosure" not in html:
                problems.append(f"{b['board_type']}: held strata undisclosed")
    if not (dist / "_headers").exists():
        problems.append("_headers missing from the upload root (J §12.5)")
    return problems


def assert_deploy_kind(state: str, kind: str) -> list[str]:
    """J §12.2 — a normal publish must never quietly ship stale data."""
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

    assert verify('<span class="num"></span>', [], "dark", DIST), (
        "verify passed an empty value slot"
    )
    # an undisclosed held stratum must fail verification (G §9.2)
    fake = [{"board_type": "daily", "strata_held": ["30k+"],
             "rows": [{"x": 1}]}]
    html_no_disc = ('<li class="repo x">'
                    '<meta name="rr:board-date" content="2026-08-15">'
                    '<meta name="rr:build-ts" content="2026-08-15">')
    assert any("undisclosed" in p for p in
               verify(html_no_disc, fake, "fresh", DIST)), (
        "verify passed an undisclosed held stratum"
    )

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

    manifest, boards = load_boards()
    now = datetime.now(timezone.utc)
    state, age_hours = staleness(
        datetime.fromisoformat(manifest["generated_at"]), now)
    html = render(manifest, boards, now)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    (DIST / "index.html").write_text(html, encoding="utf-8")
    shutil.copy(ROOT / "static" / "_headers", DIST / "_headers")

    problems = verify(html, boards, state, DIST)
    problems += assert_deploy_kind(state, args.deploy_kind)
    if problems:
        print("VERIFY FAILED — deploy blocked (J §7 step 4):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    rows = sum(len(b["rows"]) for b in boards)
    print(
        f"built dist/index.html — {rows} board rows, board {age_hours:.1f} h "
        f"old, state '{state}', {args.deploy_kind} deploy"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
