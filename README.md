# rising-repos-site

The static site at [risingrepos.com](https://risingrepos.com): a nightly
instrument that lists GitHub repositories gaining stars faster than their own
history predicts. The pipeline (in the wayfinder repo) exports board data into
`site-data/`; `build.py` renders it into `dist/`, verifies every page, and a
push to `main` deploys `dist/` to Cloudflare Pages.

There is no JavaScript, no external request and no dependency beyond Jinja2.
`DESIGN.md` holds the design plan (tokens, wireframe, the choices reviewed
against the brief).

## What the site renders

| page | from | shows |
|---|---|---|
| `/` | the root files in `site-data/boards/` | the latest board day: header, day strip, daily / weekly / monthly boards |
| `/days/` | `index.json` | every board day, newest first: rows per board, held star ranges, backfill marks |
| `/days/YYYY-MM-DD/` | `days/YYYY-MM-DD/` | that day's three boards, with previous / next day links |

Every page carries `<meta name="rr:board-date">` and `<meta name="rr:build-ts">`
(ISO 8601) for the staleness monitor. The latest page also applies the staleness
rule from the root manifest's `generated_at`: under 26 h **fresh**; 26 h to 7 d
**banner** (boards shown with a notice); over 7 d **dark** (no boards, a notice
and a link to the archive). A `--deploy-kind normal` build refuses anything but
fresh; the watchdog passes `--deploy-kind watchdog` to publish the stale state
on purpose.

Each row: rank, `owner/repo` (linked to GitHub unless `link_suppressed`), the
description, the **pace multiple** set large with "+N stars above its own trend"
beside it, then stars, forks, language, band, days on the board, RS, badges as
plain words, any correction as an amber note, and a `<details>` with the
security card line, the structure lines, the score and fork corroboration.

A board whose crawl was incomplete for a star range shows that range as **held**
in an amber-bordered disclosure with the exporter's `hold_reason`; a board with
no rows says why in one sentence. `partial_history` renders as a quiet note that
part of the lookback was backfilled.

## The data contract

```
site-data/boards/
  manifest.json                     {day, generated_at, boards{bt: {rows, held[], partial_history}}}
  daily.json weekly.json monthly.json   the LATEST day's boards
  index.json                        {"latest": "YYYY-MM-DD", "days": [{day, rows{bt:n}, held{bt:[...]}, partial_history{bt:bool}}, ...]}
  days/YYYY-MM-DD/                  manifest.json + the three board files for every board day
```

Board document: `board_type, day, floor, strata_admitted[], strata_held[],
hold_reason (str|null), partial_history (bool), rows[], facets{band{...}}`.

Row: `repo_id, rank, name ("owner/repo"|null), description, language, topics[],
license, homepage, stars, forks, pushed_at, final_display, final_is_capped, rs,
fork_corroboration, excess_above_trend, pace_multiple, stratum, band,
consecutive_days, badges[], summary, link_suppressed, corrections[{kind, detail}],
security{card, link_suppressed, commit_sha}, structure{state, lines[], commit_sha}`.

Badges `category-withheld` and `no-summary` never render. If `index.json` is
absent (exports before the history export existed) the build synthesises a
one-day index from `manifest.json` and serves that day's page from the root
files, so the site still builds.

## Building

```
pip install -r requirements.txt          # jinja2 + markupsafe, hash-pinned
python build.py --selfcheck              # proves every verify check can fail, then builds a fixture tree end to end
python build.py                          # site-data/boards -> dist/, normal deploy rules
python build.py --deploy-kind watchdog   # publish even if the data is stale or dark
```

`build.py` exits non-zero and prints the problems when any page fails
verification: an empty numeric slot, a `None`/`Undefined` in the output, an
internal link with no file in `dist/`, a row count that differs from the export,
a held star range without its disclosure, a missing meta tag, a directory index
with no cache rule in `_headers`, or an archive that omits a day. CI runs
`--selfcheck` first so a verifier that stopped being able to fail can never
green-light a deploy.

### Building against fixtures

Real data only arrives nightly; `scripts/fixtures.py` fabricates a full tree
(20 days by default, deterministic per seed) with held boards, an empty board,
an all-held board, a partial-history stretch, a link-suppressed row with a
correction, and null fields:

```
python scripts/fixtures.py /tmp/rr-fixtures            # --days 20 --seed 7 --age-hours 2
RR_BOARDS_DIR=/tmp/rr-fixtures python build.py --deploy-kind watchdog
python -m http.server 8000 --directory dist              # then open http://localhost:8000/
```

`--age-hours 30` yields the banner state, `--age-hours 200` the dark state.
`RR_BOARDS_DIR` points the build at any boards tree; the default is
`site-data/boards`. Never commit fixture output into `site-data/`.

## Cache policy

`static/_headers` is copied into `dist/` unchanged. Cloudflare's `/*.html` rule
does not match directory-index requests, so `/` and `/days/*` each have an
explicit `no-cache, must-revalidate` rule; the build refuses to ship a directory
index no rule covers.
