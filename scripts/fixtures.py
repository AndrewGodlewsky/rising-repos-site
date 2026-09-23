#!/usr/bin/env python3
"""Fabricate a realistic boards tree for developing the site build.

    python scripts/fixtures.py <outdir> [--days 20] [--seed 7] [--age-hours 2]

Writes the full data contract the pipeline exports:

    <outdir>/manifest.json, daily.json, weekly.json, monthly.json   (latest day)
    <outdir>/index.json
    <outdir>/days/YYYY-MM-DD/{manifest,daily,weekly,monthly}.json   (every day)

then build against it with

    RR_BOARDS_DIR=<outdir> python build.py --deploy-kind watchdog

The tree is deterministic for a given seed. It plants, on purpose: held boards
with real-looking hold reasons, one day whose daily board is empty, one day whose
daily board is entirely held, a partial-history day, a link-suppressed row with a
deleted/dmca correction, a row suppressed by the security scan alone, rows with
null description/language/stars, and every badge the contract can carry.
Never commit the output into site-data/.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BOARD_TYPES = ("daily", "weekly", "monthly")
STRATA = ("200-1k", "1-3k", "3-10k", "10-30k", "30k+")
STRATUM_RANGE = {"200-1k": (200, 999), "1-3k": (1000, 2999), "3-10k": (3000, 9999),
                 "10-30k": (10000, 29999), "30k+": (30000, 180000)}
BANDS = ("emerging", "growing", "established")

REPOS = [
    ("astral-sh/uv", "An extremely fast Python package and project manager, written in Rust.", "Rust", "MIT", ["python", "packaging", "rust"]),
    ("astral-sh/ruff", "An extremely fast Python linter and code formatter, written in Rust.", "Rust", "MIT", ["python", "linter"]),
    ("fastapi/fastapi", "FastAPI framework, high performance, easy to learn, fast to code, ready for production", "Python", "MIT", ["api", "async", "python"]),
    ("BurntSushi/ripgrep", "ripgrep recursively searches directories for a regex pattern while respecting your gitignore", "Rust", "Unlicense", ["search", "cli"]),
    ("sharkdp/bat", "A cat(1) clone with wings.", "Rust", "Apache-2.0", ["cli", "terminal"]),
    ("charmbracelet/bubbletea", "A powerful little TUI framework", "Go", "MIT", ["tui", "go"]),
    ("tinygrad/tinygrad", "You like pytorch? You like micrograd? You love tinygrad!", "Python", "MIT", ["deep-learning"]),
    ("ggml-org/llama.cpp", "LLM inference in C/C++", "C++", "MIT", ["llm", "inference"]),
    ("zed-industries/zed", "Code at the speed of thought – Zed is a high-performance, multiplayer code editor from the creators of Atom and Tree-sitter.", "Rust", "GPL-3.0", ["editor"]),
    ("biomejs/biome", "A toolchain for web projects, aimed to provide functionalities to maintain them.", "Rust", "MIT", ["javascript", "formatter", "linter"]),
    ("oven-sh/bun", "Incredibly fast JavaScript runtime, bundler, test runner, and package manager – all in one", "Zig", "MIT", ["javascript", "runtime"]),
    ("denoland/deno", "A modern runtime for JavaScript and TypeScript.", "Rust", "MIT", ["javascript", "typescript", "runtime"]),
    ("helix-editor/helix", "A post-modern modal text editor.", "Rust", "MPL-2.0", ["editor", "modal"]),
    ("typst/typst", "A new markup-based typesetting system that is powerful and easy to learn.", "Rust", "Apache-2.0", ["typesetting", "latex"]),
    ("jqlang/jq", "Command-line JSON processor", "C", "MIT", ["json", "cli"]),
    ("junegunn/fzf", "A command-line fuzzy finder", "Go", "MIT", ["cli", "fuzzy-search"]),
    ("nushell/nushell", "A new type of shell", "Rust", "MIT", ["shell"]),
    ("pola-rs/polars", "Dataframes powered by a multithreaded, vectorized query engine, written in Rust", "Rust", "MIT", ["dataframe", "arrow"]),
    ("duckdb/duckdb", "DuckDB is an analytical in-process SQL database management system", "C++", "MIT", ["sql", "olap"]),
    ("sst/opencode", "AI coding agent, built for the terminal.", "TypeScript", "MIT", ["ai", "terminal"]),
    ("anomalyco/opencode", "The open source coding agent.", "TypeScript", "MIT", ["ai", "agent"]),
    ("modelcontextprotocol/servers", "Model Context Protocol Servers", "TypeScript", "MIT", ["mcp"]),
    ("ollama/ollama", "Get up and running with OpenAI gpt-oss, DeepSeek-R1, Gemma 3 and other models.", "Go", "MIT", ["llm", "local"]),
    ("HKUDS/LightRAG", "\"LightRAG: Simple and Fast Retrieval-Augmented Generation\"", "Python", "MIT", ["rag"]),
    ("microsoft/markitdown", "Python tool for converting files and office documents to Markdown.", "Python", "MIT", ["markdown", "conversion"]),
    ("unslothai/unsloth", "Fine-tuning & Reinforcement Learning for LLMs. 🦥 Train OpenAI gpt-oss, DeepSeek, Qwen3, Llama 4, Gemma 3, TTS 2x faster with 70% less VRAM.", "Python", "Apache-2.0", ["fine-tuning"]),
    ("browser-use/browser-use", "🌐 Make websites accessible for AI agents. Automate tasks online with ease.", "Python", "MIT", ["ai", "browser"]),
    ("stanfordnlp/dspy", "DSPy: The framework for programming—not prompting—language models", "Python", "MIT", ["llm"]),
    ("github/spec-kit", "💫 Toolkit to help you get started with Spec-Driven Development", "Python", "MIT", ["sdd"]),
    ("obra/superpowers", "Superpowers is a complete software development workflow for your coding agents", None, "MIT", []),
    ("mitchellh/ghostty", "👻 Ghostty is a fast, feature-rich, and cross-platform terminal emulator that uses platform-native UI and GPU acceleration.", "Zig", "MIT", ["terminal"]),
    ("sindresorhus/awesome", "😎 Awesome lists about all kinds of interesting topics", None, "CC0-1.0", ["awesome"]),
    ("tldr-pages/tldr", "📚 Collaborative cheatsheets for console commands", "Markdown", "CC-BY-4.0", ["documentation"]),
    ("localsend/localsend", "An open-source cross-platform alternative to AirDrop", "Dart", "Apache-2.0", ["flutter"]),
    ("immich-app/immich", "High performance self-hosted photo and video management solution.", "TypeScript", "AGPL-3.0", ["self-hosted", "photos"]),
    ("ClickHouse/ClickHouse", "ClickHouse® is a real-time analytics database management system", "C++", "Apache-2.0", ["olap"]),
    ("neondatabase/neon", "Neon: Serverless Postgres. We separated storage and compute to offer autoscaling, code-like database branching, and scale to zero.", "Rust", "Apache-2.0", ["postgres"]),
    ("tursodatabase/limbo", "Limbo is a project to build the modern evolution of SQLite.", "Rust", "MIT", ["sqlite"]),
    ("valkey-io/valkey", "A flexible distributed key-value database that is optimized for caching and other realtime workloads.", "C", "BSD-3-Clause", ["kv", "redis"]),
    ("karpathy/nanochat", "The best ChatGPT that $100 can buy.", "Python", "MIT", ["llm", "training"]),
    ("Textualize/textual", "The lean application framework for Python. Build sophisticated user interfaces with a simple Python API. Run your apps in the terminal and a web browser.", "Python", "MIT", ["tui"]),
    ("withastro/astro", "The web framework for content-driven websites. ⭐️ Star to support our work!", "TypeScript", "MIT", ["web"]),
    ("rolldown/rolldown", "Fast Rust bundler for JavaScript with Rollup-compatible API.", "Rust", "MIT", ["bundler"]),
    ("void-linux/void-packages", None, "Shell", None, []),
    ("nicbarker/clay", "High performance UI layout library in C.", "C", "Zlib", ["ui", "layout"]),
    ("dragonflydb/dragonfly", "A modern replacement for Redis and Memcached", "C++", "BSL-1.1", ["redis"]),
    ("aristocratos/btop", "A monitor of resources", "C++", "Apache-2.0", ["monitoring"]),
    ("ajeetdsouza/zoxide", "A smarter cd command. Supports all major shells.", "Rust", "MIT", ["cli"]),
    ("dandavison/delta", "A syntax-highlighting pager for git, diff, grep, and blame output", "Rust", "MIT", ["git"]),
    ("gitui-org/gitui", "Blazing 💥 fast terminal-ui for git written in rust 🦀", "Rust", "MIT", ["git", "tui"]),
    ("jesseduffield/lazygit", "simple terminal UI for git commands", "Go", "MIT", ["git", "tui"]),
    ("wez/wezterm", "A GPU-accelerated cross-platform terminal emulator and multiplexer written by @wez and implemented in Rust", "Rust", "MIT", ["terminal"]),
    ("atuinsh/atuin", "✨ Magical shell history", "Rust", "MIT", ["shell"]),
    ("eza-community/eza", "A modern alternative to ls", "Rust", "EUPL-1.2", ["cli"]),
    ("zellij-org/zellij", "A terminal workspace with batteries included", "Rust", "MIT", ["terminal"]),
    ("meilisearch/meilisearch", "A lightning-fast search engine API bringing AI-powered hybrid search to your sites and applications.", "Rust", "MIT", ["search"]),
    ("qdrant/qdrant", "Qdrant - High-performance, massive-scale Vector Database and Vector Search Engine for the next generation of AI.", "Rust", "Apache-2.0", ["vector-database"]),
    ("lancedb/lancedb", "Developer-friendly, embedded retrieval engine for multimodal AI. Search More; Manage Less.", "Rust", "Apache-2.0", ["vector-database"]),
    ("ratatui/ratatui", "A Rust crate for cooking up terminal user interfaces (TUIs) 👨‍🍳🐀", "Rust", "MIT", ["tui"]),
    ("crossbeam-rs/crossbeam", "Tools for concurrent programming in Rust", "Rust", "Apache-2.0", ["concurrency"]),
]

SUBSYSTEMS = ["Command Adapters", "Dependency Resolver", "Lockfile Writer", "Package Index Client",
              "Wheel Cache", "Virtual Environment Manager", "Query Planner", "Storage Engine",
              "Expression Compiler", "Terminal Renderer", "Event Loop", "Widget Tree",
              "Syntax Highlighter", "Tree-sitter Bindings", "Model Loader", "Tokenizer",
              "Sampling", "HTTP Server", "Auth Middleware", "Schema Validation", "Diff Engine"]
CORE = ["Resolver", "run()", "Config", "LockfileWriter", "QueryPlan", "Session", "App", "render()",
        "Tokenizer", "ModelLoader", "Router", "Store", "Document", "parse()", "Widget", "Backend"]

RANK_BADGES = ["provisional", "limited-history", "sustained", "unconfirmed-by-forks",
               "fork-history-insufficient", "category-withheld", "no-summary"]

ORDINAL_SUFFIX = {1: "st", 2: "nd", 3: "rd"}


def _sha(rng: random.Random) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(40))


def _security(rng: random.Random, kind: str) -> dict:
    if kind == "queued":
        return {"card": "not yet scanned — queued", "link_suppressed": False, "commit_sha": None}
    n = rng.choice([0, 0, 3, 12, 53, 112, 208, 475])
    parts = ["no findings" if n == 0 else f"{n} findings"]
    if rng.random() < 0.7:
        parts.append("1 check pending")
    na = rng.choice([0, 0, 1, 5])
    if na:
        parts.append(f"{na} check{'s' if na > 1 else ''} not applicable")
    return {"card": " · ".join(parts), "link_suppressed": kind == "suppressed",
            "commit_sha": _sha(rng)}


def _structure(rng: random.Random, language: str | None) -> dict:
    if language in (None, "Markdown"):
        return {"state": "empty(no_code)",
                "lines": ["Structure: no code to map — curated list / documentation repository"],
                "commit_sha": _sha(rng)}
    if rng.random() < 0.15:
        return {"state": "queued", "lines": ["Structure: not yet mapped — queued"], "commit_sha": None}
    n = rng.choice([1, 7, 23, 97, 150, 282, 823, 2400])
    subs = rng.sample(SUBSYSTEMS, 3)
    core = rng.sample(CORE, 3)
    return {"state": "done",
            "lines": [f"Structure: {n:,} subsystems — " + " · ".join(subs),
                      "Core: " + " · ".join(core)],
            "commit_sha": _sha(rng)}


def _hold_reason(rng: random.Random, held: list[str], day: str) -> str:
    totals = {"200-1k": 209170, "1-3k": 43800, "3-10k": 16555, "10-30k": 4388, "30k+": 611}
    parts = []
    for s in held:
        t = totals[s]
        if s == "30k+" and rng.random() < 0.5:
            parts.append(f"30k+: no coverage record for {day}")
        else:
            parts.append(f"{s}: {t - rng.randint(1, max(2, t // 150))}/{t} on {day}")
    return "; ".join(parts)


def _entry(rng: random.Random, rank: int, repo: tuple, day: date, streak: dict,
           plant: str | None = None, admitted: tuple = STRATA) -> dict:
    name, desc, lang, lic, topics = repo
    weights = {"200-1k": 5, "1-3k": 5, "3-10k": 4, "10-30k": 2, "30k+": 1}
    stratum = rng.choices(admitted, weights=[weights[s] for s in admitted])[0]
    lo, hi = STRATUM_RANGE[stratum]
    stars = rng.randint(lo, hi)
    band = rng.choices(BANDS, weights=[3, 3, 2])[0]
    rs = round(rng.uniform(3.0, 7.5), 3)
    pace = round(rng.choices([rng.uniform(1.4, 2.5), rng.uniform(2.5, 5), rng.uniform(5, 14)],
                             weights=[5, 3, 1])[0], 2)
    excess = round(stars * rng.uniform(0.004, 0.06) * (pace / 2), 1)
    final = round(rs * rng.uniform(0.8, 1.6), 3)
    badges = []
    if rng.random() < 0.25:
        badges.append("provisional")
    if rng.random() < 0.15:
        badges.append("limited-history")
    corroboration = round(rng.uniform(0.5, 1.0), 3)
    if corroboration < 0.65:
        badges.append(rng.choice(["unconfirmed-by-forks", "fork-history-insufficient"]))
    if rng.random() < 0.3:
        badges.append("category-withheld")
    if rng.random() < 0.6:
        badges.append("no-summary")
    consecutive = streak.get(name, 0) + 1
    streak[name] = consecutive
    if consecutive >= 3 and "sustained" not in badges:
        badges.append("sustained")
    corrections = []
    sec_kind = "scanned" if rng.random() < 0.85 else "queued"
    if plant == "dmca":
        corrections = [{"kind": "deleted/dmca", "detail": "repository returned 451 on the nightly re-resolve"}]
    elif plant == "security":
        sec_kind = "suppressed"
    elif plant == "nulls":
        desc, lang, stars = None, None, None
    pushed = datetime(day.year, day.month, day.day, rng.randint(0, 23), rng.randint(0, 59),
                      tzinfo=timezone.utc) - timedelta(days=rng.randint(0, 4))
    return {
        "repo_id": 100000 + (abs(hash(name)) % 900000),
        "rank": rank,
        "name": name,
        "description": desc,
        "language": lang,
        "topics": topics,
        "license": lic,
        "homepage": None if rng.random() < 0.6 else f"https://{name.split('/')[1].lower()}.dev",
        "stars": stars,
        "forks": None if stars is None else int(stars * rng.uniform(0.03, 0.12)),
        "pushed_at": pushed.isoformat(),
        "final_display": min(final, 8.0),
        "final_is_capped": final > 8.0,
        "rs": rs,
        "fork_corroboration": corroboration,
        "excess_above_trend": excess,
        "pace_multiple": pace,
        "stratum": stratum,
        "band": band,
        "consecutive_days": consecutive,
        "badges": badges,
        "summary": None,
        "link_suppressed": bool(corrections) or sec_kind == "suppressed",
        "corrections": corrections,
        "security": _security(rng, sec_kind),
        "structure": _structure(rng, lang),
    }


def build_day(rng: random.Random, day: date, i: int, n_days: int, streaks: dict,
              generated_at: datetime) -> tuple[dict, dict[str, dict]]:
    """One day's manifest + three board docs. `i` indexes the day (0 = oldest)."""
    d = day.isoformat()
    boards = {}
    manifest = {"day": d, "generated_at": generated_at.isoformat(), "boards": {}}
    for bt in BOARD_TYPES:
        # weekly/monthly need history: fewer rows early on, none on the first days
        base_n = {"daily": rng.randint(6, 14), "weekly": rng.randint(2, 7), "monthly": rng.randint(0, 4)}[bt]
        if bt == "weekly" and i < 2:
            base_n = 0
        if bt == "monthly" and i < 5:
            base_n = 0
        held: list[str] = []
        hold_reason = None
        # planted states, keyed on day index
        if bt == "daily" and i == n_days - 4:          # a real quiet night
            base_n = 0
        if bt == "daily" and i == 3:                    # everything held
            held = list(STRATA)
            base_n = 0
        elif bt == "daily" and i in (n_days - 6, n_days - 1):
            held = ["200-1k"]
        elif bt == "weekly" and i == n_days - 2:
            held = ["10-30k", "30k+"]
        if held:
            hold_reason = _hold_reason(rng, held, d)
        admitted = [s for s in STRATA if s not in held]
        rows = []
        pool = rng.sample(REPOS, min(len(REPOS), base_n + 3))
        rank = 0
        for repo in pool:
            if rank >= base_n:
                break
            plant = None
            if bt == "daily" and i == n_days - 1 and rank == 2:
                plant = "dmca"
            elif bt == "daily" and i == n_days - 1 and rank == 5:
                plant = "security"
            elif bt == "weekly" and i == n_days - 1 and rank == 1:
                plant = "nulls"
            rank += 1
            rows.append(_entry(rng, rank, repo, day, streaks.setdefault(bt, {}), plant,
                               tuple(admitted)))
        partial = (bt in ("weekly", "monthly")) and (n_days - 8 <= i <= n_days - 5)
        facets = {"band": {}}
        for r in rows:
            facets["band"][r["band"]] = facets["band"].get(r["band"], 0) + 1
        boards[bt] = {
            "board_type": bt, "day": d, "floor": 3.0,
            "strata_admitted": admitted, "strata_held": held,
            "hold_reason": hold_reason, "partial_history": partial,
            "rows": rows, "facets": facets,
        }
        manifest["boards"][bt] = {"rows": len(rows), "held": held, "partial_history": partial}
    # repos that dropped off the board lose their streak
    for bt in BOARD_TYPES:
        on_board = {r["name"] for r in boards[bt]["rows"]}
        for name in list(streaks.get(bt, {})):
            if name not in on_board:
                del streaks[bt][name]
    return manifest, boards


def write_tree(outdir: Path, n_days: int, seed: int, age_hours: float, end: date | None = None) -> dict:
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    latest_gen = now - timedelta(hours=age_hours)
    end = end or (latest_gen.date() - timedelta(days=1))   # the board for day D publishes on D+1
    days = [end - timedelta(days=n_days - 1 - i) for i in range(n_days)]
    streaks: dict = {}
    index = []
    outdir.mkdir(parents=True, exist_ok=True)
    for i, day in enumerate(days):
        gen = latest_gen - timedelta(days=n_days - 1 - i)
        man, boards = build_day(rng, day, i, n_days, streaks, gen)
        ddir = outdir / "days" / day.isoformat()
        ddir.mkdir(parents=True, exist_ok=True)
        _dump(ddir / "manifest.json", man)
        for bt, doc in boards.items():
            _dump(ddir / f"{bt}.json", doc)
        if i == n_days - 1:
            _dump(outdir / "manifest.json", man)
            for bt, doc in boards.items():
                _dump(outdir / f"{bt}.json", doc)
        index.append({"day": day.isoformat(),
                      "rows": {bt: v["rows"] for bt, v in man["boards"].items()},
                      "held": {bt: v["held"] for bt, v in man["boards"].items()},
                      "partial_history": {bt: v["partial_history"] for bt, v in man["boards"].items()}})
    idx = {"latest": days[-1].isoformat(), "days": index}
    _dump(outdir / "index.json", idx)
    return idx


def _dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--days", type=int, default=20)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--age-hours", type=float, default=2.0,
                    help="how old the latest board is (2 = fresh, 30 = banner, 200 = dark)")
    args = ap.parse_args()
    idx = write_tree(args.outdir, args.days, args.seed, args.age_hours)
    rows = sum(sum(d["rows"].values()) for d in idx["days"])
    print(f"wrote {len(idx['days'])} days, {rows} rows, latest {idx['latest']} -> {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
