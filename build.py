#!/usr/bin/env python3
"""Rising Repos site build — every board day (wayfinder tickets #10, #13).

Reads the boards tree the pipeline exports (default `site-data/boards/`,
override with the `RR_BOARDS_DIR` environment variable to build against a
fixture tree from `scripts/fixtures.py`):

    manifest.json, daily.json, weekly.json, monthly.json   the latest day
    index.json                                             every day, ascending
    days/YYYY-MM-DD/{manifest,daily,weekly,monthly}.json   every board day

and renders into `dist/`:

    index.html                 the latest day
    days/index.html            the archive: every day with rows, holds, marks
    days/YYYY-MM-DD/index.html one page per board day
    _headers                   Cloudflare's cache policy, copied from static/

then verifies EVERY page. A non-zero exit blocks the deploy (J §7 step 4).
`--selfcheck` proves each verify check can fail on a planted error, then builds
a fixture tree end to end; CI runs it before the real build so a vacuous
verifier can never green-light a deploy.

If `index.json` has not been exported yet (the pipeline before ticket #28
shipped only the latest day) the build synthesises a one-day index from
`manifest.json` and serves that day's page from the root files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
DEFAULT_BOARDS_DIR = ROOT / "site-data" / "boards"
BOARD_TYPES = ("daily", "weekly", "monthly")
STRATA = ("200-1k", "1-3k", "3-10k", "10-30k", "30k+")
STRIP_DAYS = 30
SITE = "https://risingrepos.com"

# I §8.1 / REVIEW D8. Hours, never day buckets: the board for UTC day D always
# publishes during UTC day D+1, so any date comparison misfires every night.
FRESH_BELOW_HOURS = 26
DARK_ABOVE_HOURS = 7 * 24

EMPTY_REASONS = {
    "daily": "No repository cleared the RS ≥ 3 floor {night} — "
             "a quiet night is a real result, not a broken page.",
    "weekly": "No repository yet clears the weekly board's bar of 112 valid "
              "nightly observations — this board fills as data accrues.",
    "monthly": "No repository yet has the 182 valid nightly observations the "
               "monthly board requires — this board fills as data accrues.",
}
ALL_HELD_REASON = ("Every star range was held {night} — the crawl behind this "
                   "board was incomplete, so publishing would be a guess.")

# The exporter's own vocabulary (rising/board.py LINK_SUPPRESSED_KINDS).
LINK_SUPPRESSED_KINDS = {"deleted/dmca", "confirmed-malware", "deleted", "dmca"}
HIDDEN_BADGES = {"category-withheld", "no-summary"}
BADGE_WORDS = {
    "provisional": "provisional",
    "limited-history": "limited history",
    "sustained": "sustained",
    "unconfirmed-by-forks": "not confirmed by forks",
    "fork-history-insufficient": "fork history too short",
}
STRATUM_WORDS = {"200-1k": "200 to 1k", "1-3k": "1k to 3k", "3-10k": "3k to 10k",
                 "10-30k": "10k to 30k", "30k+": "30k or more"}


def staleness(board_ts: datetime, now: datetime) -> tuple[str, float]:
    """THE staleness rule (I7/I §8.1) — one function, all causes, computed once."""
    hours = (now - board_ts).total_seconds() / 3600
    if hours < FRESH_BELOW_HOURS:
        return "fresh", hours
    if hours <= DARK_ABOVE_HOURS:
        return "banner", hours
    return "dark", hours


# --- loading -----------------------------------------------------------------


def boards_dir() -> Path:
    return Path(os.environ.get("RR_BOARDS_DIR") or DEFAULT_BOARDS_DIR)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_index(bdir: Path) -> dict:
    """index.json, or a one-day index synthesised from the root manifest."""
    if (bdir / "index.json").exists():
        idx = _read(bdir / "index.json")
        idx["days"] = sorted(idx["days"], key=lambda d: d["day"])
        return idx
    man = _read(bdir / "manifest.json")
    return {"latest": man["day"], "days": [{
        "day": man["day"],
        "rows": {bt: v["rows"] for bt, v in man["boards"].items()},
        "held": {bt: v.get("held", []) for bt, v in man["boards"].items()},
        "partial_history": {bt: bool(v.get("partial_history"))
                            for bt, v in man["boards"].items()},
    }]}


def day_dir(bdir: Path, day: str, latest: str) -> Path:
    d = bdir / "days" / day
    if d.exists():
        return d
    if day == latest:
        return bdir
    raise FileNotFoundError(f"index lists {day} but {d} does not exist")


def load_day(d: Path) -> tuple[dict, list[dict]]:
    manifest = _read(d / "manifest.json")
    boards = []
    for bt in BOARD_TYPES:
        doc = _read(d / f"{bt}.json")
        doc.setdefault("partial_history", False)
        doc.setdefault("hold_reason", None)
        boards.append(doc)
    return manifest, boards


# --- presentation ------------------------------------------------------------


def long_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%A} {d.day} {d:%B} {d.year}"


def short_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {d:%B}"


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def strata_words(strata: list[str]) -> str:
    words = [STRATUM_WORDS.get(s, s) for s in sorted(strata, key=lambda s: STRATA.index(s) if s in STRATA else 99)]
    if len(words) <= 1:
        return "".join(words)
    return ", ".join(words[:-1]) + " and " + words[-1]


def thousands(n) -> str:
    return f"{int(n):,}"


def prepare_row(r: dict) -> dict:
    """Derive the words the template prints; never invent data."""
    r = dict(r)
    name = r.get("name")
    r["display_name"] = name or f"repository {r['repo_id']}"
    r["href"] = None if (r.get("link_suppressed") or not name) else f"https://github.com/{name}"
    r["pace_text"] = f"{float(r['pace_multiple']):.1f}×"
    r["excess_text"] = f"+{round(float(r['excess_above_trend'])):,}"
    n = int(r.get("consecutive_days") or 1)
    r["days_words"] = f"{ordinal(n)} day on the board" if n > 1 else ""
    r["tags"] = [BADGE_WORDS.get(b, b.replace("-", " ")) for b in (r.get("badges") or [])
                 if b not in HIDDEN_BADGES]
    notes = []
    for c in r.get("corrections") or []:
        kind = c.get("kind") or "correction"
        if kind in LINK_SUPPRESSED_KINDS:
            notes.append(f"Listed as {kind} — link removed")
        elif c.get("detail"):
            notes.append(f"Listed as {kind}: {c['detail']}")
        else:
            notes.append(f"Listed as {kind}")
    sec = r.get("security") or {}
    if sec.get("link_suppressed") and not any(
            (c.get("kind") in LINK_SUPPRESSED_KINDS) for c in (r.get("corrections") or [])):
        notes.append("Link removed after the security scan")
    elif r.get("link_suppressed") and not notes and name:
        notes.append("Link removed")
    r["notes"] = notes
    r["security"] = {"card": sec.get("card") or "not yet scanned — queued",
                     "link_suppressed": bool(sec.get("link_suppressed")),
                     "commit_sha": sec.get("commit_sha")}
    st = r.get("structure") or {}
    r["structure"] = {"state": st.get("state") or "queued",
                      "lines": list(st.get("lines") or ["Structure: not yet mapped — queued"]),
                      "commit_sha": st.get("commit_sha")}
    r["description"] = (r.get("description") or "").strip() or None
    return r


def prepare_board(doc: dict, night: str) -> dict:
    b = dict(doc)
    b["rows"] = [prepare_row(r) for r in doc["rows"]]
    b["held_words"] = strata_words(doc["strata_held"])
    b["day_words"] = night
    reason = EMPTY_REASONS[doc["board_type"]]
    if doc["strata_held"] and not doc["rows"]:
        reason = ALL_HELD_REASON
    b["empty_reason"] = reason.format(night=night)
    return b


def strip_for(index: dict, current: str) -> list[dict]:
    """The last STRIP_DAYS calendar days ending at the latest day — or at the
    current page's day when that lies outside the window."""
    by_day = {d["day"]: d for d in index["days"]}
    latest = date.fromisoformat(index["latest"])
    cur = date.fromisoformat(current)
    end = latest if (latest - cur).days < STRIP_DAYS else cur
    max_rows = max((sum(d["rows"].values()) for d in index["days"]), default=0)
    out = []
    for i in range(STRIP_DAYS - 1, -1, -1):
        day = (end - timedelta(days=i)).isoformat()
        d = by_day.get(day)
        if d is None:
            out.append({"day": day, "href": None, "level": 0, "held": False,
                        "title": f"{long_date(day)}: no boards", "short": short_date(day)})
            continue
        rows = sum(d["rows"].values())
        level = 0 if rows == 0 or max_rows == 0 else min(4, 1 + int(3 * rows / max_rows))
        held = [f"{strata_words(v)} ({bt})" for bt, v in d["held"].items() if v]
        partial = [bt for bt, v in d.get("partial_history", {}).items() if v]
        title = f"{long_date(day)}: {rows} {'repository' if rows == 1 else 'repositories'}"
        if held:
            title += "; held " + ", ".join(held)
        if partial:
            title += "; part of the " + " and ".join(partial) + " lookback is backfilled"
        out.append({"day": day, "href": f"/days/{day}/", "level": level, "held": bool(held),
                    "title": title, "short": short_date(day)})
    return out


def archive_rows(index: dict) -> list[dict]:
    out = []
    for d in reversed(index["days"]):
        rows = {bt: int(d["rows"].get(bt, 0)) for bt in BOARD_TYPES}
        holds = [f"held {strata_words(v)} ({bt})" for bt, v in d["held"].items() if v]
        partial = [bt for bt in BOARD_TYPES if d.get("partial_history", {}).get(bt)]
        out.append({"day": d["day"], "href": f"/days/{d['day']}/", "long": long_date(d["day"]),
                    "rows": rows, "hold_notes": holds, "partial": partial,
                    "empty_all": sum(rows.values()) == 0 and not holds})
    return out


# --- render ------------------------------------------------------------------


def make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        undefined=StrictUndefined,  # I1
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["thousands"] = thousands
    return env


def _human_ts(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def render_boards_page(env: Environment, *, path: str, page_kind: str, manifest: dict,
                       boards: list[dict], index: dict, state: str | None, age_hours: float,
                       now: datetime, prev: dict | None = None, nxt: dict | None = None) -> str:
    day = manifest["day"]
    night = "last night" if page_kind == "latest" else "that night"
    prepared = [prepare_board(b, night) for b in boards]
    gen = datetime.fromisoformat(manifest["generated_at"])
    return env.get_template("boards.html").render(
        path=path, page_kind=page_kind,
        boards=prepared if state != "dark" else [],
        state=state, age_days=int(age_hours // 24),
        board_date=day, day_long=long_date(day),
        generated_at=gen.isoformat(), published_human=_human_ts(gen),
        strip=strip_for(index, day), prev=prev, next=nxt,
        build_ts=now.replace(microsecond=0).isoformat(), build_ts_human=_human_ts(now),
    )


def render_days_page(env: Environment, index: dict, now: datetime) -> str:
    return env.get_template("days.html").render(
        path="/days/", latest=index["latest"], days=archive_rows(index),
        strip=strip_for(index, index["latest"]),
        board_date=index["latest"],
        build_ts=now.replace(microsecond=0).isoformat(), build_ts_human=_human_ts(now),
    )


# --- verify (I §9, blocking gate) -------------------------------------------

INTERNAL_HREF = re.compile(r'href="(/[^"#?]*)')
EMPTY_SLOT = re.compile(r'class="[^"]*\bnum\b[^"]*"[^>]*>\s*</')
ROW_MARK = '<li class="repo"'


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


def check_headers(headers: str, index_paths: list[str]) -> list[str]:
    """J §5 — every directory index that ships has a cache rule. `/*.html`
    does NOT match a directory request, measured on the live edge (#3)."""
    rules = [ln.strip() for ln in headers.splitlines()
             if ln.strip() and not ln.startswith((" ", "\t", "#"))]

    def covered(p: str) -> bool:
        for r in rules:
            if r == p:
                return True
            if r.endswith("*") and p.startswith(r[:-1]):
                return True
        return False

    return [p for p in index_paths if not covered(p)]


def check_archive(html: str, index: dict) -> list[str]:
    """The archive must link every day the index lists."""
    return [d["day"] for d in index["days"] if f'href="/days/{d["day"]}/"' not in html]


def verify_page(html: str, boards: list[dict], state: str | None, dist: Path) -> list[str]:
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
    got = html.count(ROW_MARK)
    if got != expected:
        problems.append(f"board row count {got} != {expected} rows exported")
    # G §9.2: a held stratum must be DISCLOSED, or the correct fallback is a
    # full hold — an undisclosed hold is the failure the breaker exists for.
    if state != "dark":
        for b in boards:
            if b["strata_held"] and b["rows"] and f'id="disclosure-{b["board_type"]}"' not in html:
                problems.append(f"{b['board_type']}: held strata undisclosed")
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


# --- build -------------------------------------------------------------------


def build(bdir: Path, dist: Path, now: datetime, deploy_kind: str) -> tuple[list[str], dict]:
    """Render every page into `dist`, then verify all of them. Returns
    (problems, summary)."""
    env = make_env()
    index = load_index(bdir)
    latest = index["latest"]
    root_manifest, root_boards = load_day(day_dir(bdir, latest, latest))
    state, age_hours = staleness(datetime.fromisoformat(root_manifest["generated_at"]), now)

    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True)
    shutil.copy(ROOT / "static" / "_headers", dist / "_headers")

    pages: list[tuple[str, str, list[dict], str | None]] = []   # (path, html, boards, state)

    html = render_boards_page(env, path="/", page_kind="latest", manifest=root_manifest,
                              boards=root_boards, index=index, state=state,
                              age_hours=age_hours, now=now)
    pages.append(("/", html, root_boards, state))

    days = [d["day"] for d in index["days"]]
    for i, day in enumerate(days):
        manifest, boards = load_day(day_dir(bdir, day, latest))
        if manifest["day"] != day:
            raise ValueError(f"days/{day}/manifest.json says day {manifest['day']}")
        prev = ({"href": f"/days/{days[i-1]}/", "label": short_date(days[i-1])} if i > 0 else None)
        nxt = ({"href": f"/days/{days[i+1]}/", "label": short_date(days[i+1])} if i + 1 < len(days) else None)
        html = render_boards_page(env, path=f"/days/{day}/", page_kind="day", manifest=manifest,
                                  boards=boards, index=index, state=None, age_hours=0.0,
                                  now=now, prev=prev, nxt=nxt)
        pages.append((f"/days/{day}/", html, boards, None))

    archive_html = render_days_page(env, index, now)
    pages.append(("/days/", archive_html, [], None))

    for path, html, _, _ in pages:
        out = dist / path.lstrip("/") / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")

    problems = []
    for path, html, boards, st in pages:
        problems += [f"{path}: {p}" for p in verify_page(html, boards, st, dist)]
    problems += [f"/days/: archive does not list {d}" for d in check_archive(archive_html, index)]
    if not (dist / "_headers").exists():
        problems.append("_headers missing from the upload root (J §12.5)")
    else:
        for p in check_headers((dist / "_headers").read_text(encoding="utf-8"),
                               [path for path, *_ in pages]):
            problems.append(f"{p}: directory index shipped without a cache rule in _headers (J §5)")
    problems += assert_deploy_kind(state, deploy_kind)
    summary = {"pages": len(pages), "days": len(days), "latest": latest, "state": state,
               "age_hours": age_hours, "rows": sum(len(b["rows"]) for b in root_boards)}
    return problems, summary


# --- self-check --------------------------------------------------------------


def selfcheck() -> None:
    t0 = datetime(2026, 8, 7, 0, 0, tzinfo=timezone.utc)
    for delta, want in [(timedelta(hours=0), "fresh"), (timedelta(hours=25, minutes=59), "fresh"),
                        (timedelta(hours=26), "banner"), (timedelta(days=7), "banner"),
                        (timedelta(days=7, seconds=1), "dark")]:
        got, _ = staleness(t0, t0 + delta)
        assert got == want, f"staleness({delta}) = {got}, want {want}"

    with tempfile.TemporaryDirectory() as tmp:
        dist = Path(tmp) / "dist"
        (dist / "days" / "2026-01-01").mkdir(parents=True)
        (dist / "days" / "2026-01-01" / "index.html").write_text("x")
        assert check_links('<a href="/nope/">x</a>', dist) == ["/nope/"], (
            "link checker passed a planted broken link — it is vacuous")
        assert check_links('<a href="/days/2026-01-01/">x</a><a href="https://github.com/a/b">x</a>'
                           '<a href="#daily">x</a>', dist) == []

        good_meta = ('<meta name="rr:board-date" content="2026-08-15">'
                     '<meta name="rr:build-ts" content="2026-08-15T05:00:00+00:00">')
        assert any("empty value slot" in p for p in
                   verify_page(good_meta + '<span class="rank num"></span>', [], "fresh", dist)), (
            "verify passed an empty value slot")
        assert any("None" in p for p in verify_page(good_meta + "<b>None</b>", [], "fresh", dist))
        assert any("meta tag" in p for p in verify_page('<li class="repo"', [{"strata_held": [], "rows": [1], "board_type": "daily"}], "fresh", dist))

        # an undisclosed held stratum must fail verification (G §9.2)
        fake = [{"board_type": "daily", "strata_held": ["30k+"], "rows": [{"x": 1}]}]
        assert any("undisclosed" in p for p in
                   verify_page(good_meta + ROW_MARK + ">", fake, "fresh", dist)), (
            "verify passed an undisclosed held stratum")
        assert not any("undisclosed" in p for p in
                       verify_page(good_meta + ROW_MARK + '><p id="disclosure-daily">', fake, "fresh", dist))
        # row count must match the export exactly, both ways
        assert any("row count" in p for p in verify_page(good_meta, fake, "fresh", dist))
        assert any("row count" in p for p in verify_page(good_meta + ROW_MARK + ROW_MARK, fake, "fresh", dist))
        # a dark page shows no rows at all
        assert any("row count" in p for p in verify_page(good_meta + ROW_MARK, fake, "dark", dist))

    assert check_headers("/\n  Cache-Control: x\n/*.html\n  Cache-Control: x\n", ["/", "/days/", "/days/2026-01-01/"]) == [
        "/days/", "/days/2026-01-01/"], "headers check passed a directory index with no rule"
    assert check_headers("/\n  Cache-Control: x\n/days/*\n  Cache-Control: x\n", ["/", "/days/", "/days/2026-01-01/"]) == []
    assert check_headers("# /days/*\n", ["/days/"]) == ["/days/"], "a commented-out rule counted"

    idx = {"latest": "2026-01-02", "days": [{"day": "2026-01-01"}, {"day": "2026-01-02"}]}
    assert check_archive('<a href="/days/2026-01-02/">', idx) == ["2026-01-01"], (
        "archive check passed a missing day")
    assert check_archive('<a href="/days/2026-01-01/"><a href="/days/2026-01-02/">', idx) == []

    assert assert_deploy_kind("banner", "normal"), "normal deploy shipped stale data"
    assert assert_deploy_kind("dark", "normal"), "normal deploy shipped dark data"
    assert not assert_deploy_kind("banner", "watchdog")
    assert not assert_deploy_kind("dark", "watchdog")
    assert not assert_deploy_kind("fresh", "normal")

    assert ordinal(1) == "1st" and ordinal(2) == "2nd" and ordinal(3) == "3rd"
    assert ordinal(11) == "11th" and ordinal(12) == "12th" and ordinal(21) == "21st" and ordinal(112) == "112th"
    assert strata_words(["10-30k", "200-1k"]) == "200 to 1k and 10k to 30k"
    r = prepare_row({"repo_id": 1, "name": "a/b", "pace_multiple": 3.44, "excess_above_trend": 1239.6,
                     "consecutive_days": 3, "badges": ["provisional", "no-summary"], "link_suppressed": True,
                     "corrections": [{"kind": "deleted/dmca", "detail": "451"}],
                     "security": {"card": "c", "link_suppressed": False, "commit_sha": None}, "structure": {}})
    assert r["href"] is None and r["pace_text"] == "3.4×" and r["excess_text"] == "+1,240"
    assert r["tags"] == ["provisional"] and r["days_words"] == "3rd day on the board"
    assert r["notes"] == ["Listed as deleted/dmca — link removed"]

    # end to end: a fixture tree must build clean, in every staleness state
    sys.path.insert(0, str(ROOT / "scripts"))
    import fixtures  # noqa: E402  (scripts/fixtures.py)
    for age, want_state, kind in ((2, "fresh", "normal"), (30, "banner", "watchdog"), (200, "dark", "watchdog")):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / "boards"
            fixtures.write_tree(bdir, 12, 3, age)
            dist = Path(tmp) / "dist"
            problems, summary = build(bdir, dist, datetime.now(timezone.utc), kind)
            assert not problems, f"fixture build (age {age} h) failed verify: {problems}"
            assert summary["state"] == want_state, (summary, want_state)
            assert (dist / "index.html").exists() and (dist / "days" / "index.html").exists()
            assert (dist / "days" / summary["latest"] / "index.html").exists()
            assert summary["pages"] == 12 + 2
            if want_state == "dark":
                assert ROW_MARK not in (dist / "index.html").read_text(encoding="utf-8")
            # and the verifier catches a page whose hold disclosure went missing
            problems_after = verify_page(
                (dist / "index.html").read_text(encoding="utf-8").replace('id="disclosure-', 'id="x-'),
                [prepare_board(b, "x") for b in load_day(bdir)[1]], summary["state"], dist)
            if want_state != "dark" and any(b["strata_held"] and b["rows"] for b in load_day(bdir)[1]):
                assert any("undisclosed" in p for p in problems_after), "rendered page lost its disclosure check"
            # a stale-data normal deploy is refused
            problems, _ = build(bdir, dist, datetime.now(timezone.utc), "normal")
            assert bool(problems) == (want_state != "fresh")
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

    problems, s = build(boards_dir(), DIST, datetime.now(timezone.utc), args.deploy_kind)
    if problems:
        print("VERIFY FAILED — deploy blocked (J §7 step 4):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(
        f"built {s['pages']} pages into dist/ — latest {s['latest']} with {s['rows']} board rows, "
        f"{s['days']} archive days, board {s['age_hours']:.1f} h old, state '{s['state']}', "
        f"{args.deploy_kind} deploy"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
