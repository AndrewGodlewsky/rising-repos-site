# Rising Repos — design plan

The site is an instrument, not a feed. It answers one question each morning:
which repositories gained faster than their own history predicts? Every choice
below is made to let a developer scan that answer in under a minute, trust it,
and see plainly when part of it is missing.

## 1. Tokens

### Colour

| token     | light     | dark      | used for                                              |
|-----------|-----------|-----------|-------------------------------------------------------|
| `--base`  | `#F4F6F8` | `#0F1418` | page background (cool graph-paper grey)               |
| `--surface` | `#FFFFFF` | `#161C22` | the day-strip blocks' hollow fill, `<details>` body  |
| `--ink`   | `#14181F` | `#E8ECEF` | text                                                  |
| `--muted` | `#66707A` | `#8A949C` | rank, facts line, footer, notes                       |
| `--rule`  | `#D9DEE3` | `#2A323A` | row separators, column rules, tag outlines            |
| `--rise`  | `#1F7A5A` | `#4CC38A` | THE accent: pace numerals, day-strip fill, focus ring |
| `--amber` | `#B9791B` | `#D9A441` | hold and partial-history disclosures ONLY             |

Contrast (checked by hand): muted on base 4.6:1, muted on surface 5.0:1, rise on
base 4.9:1 (and the pace numeral is large text), ink on base > 15:1. Light amber
on base is only 3.3:1, so **amber is never used for running text** — it is a
border, an underline or a square mark next to text set in ink or muted. Dark-mode
amber and rise both clear 8:1.

No cream, no terracotta, no gradients, no shadows.

### Type

Two stacks, two roles, nothing else:

- sans, for everything: `system-ui, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`
- mono, ONLY for repository names and commit SHAs:
  `ui-monospace, "Cascadia Mono", Consolas, Menlo, monospace`

Scale (rem): `0.8` tags, meta-marks · `0.9` facts line, notes, footer, archive
table · `1` body, descriptions · `1.25` board headings, page heading on day
pages · `1.6` wordmark · `2.6` the pace multiple (weight 300).

`font-variant-numeric: tabular-nums` on every number that sits in a column or a
row of siblings (rank, pace, stars, forks, archive table, day strip labels).
Body copy and descriptions are capped at `60ch`.

### Space and shape

Base unit 0.25 rem. Rows are separated by a 1 px `--rule` top border; boards by a
1 px left rule in the three-column layout. Tags are 1 px outlined pills, nothing
else is rounded. No shadows. No page-load animation; the only motion on the page
is `<details>` opening, which the browser does without CSS.

## 2. Wireframe

Wide (≥ 1100 px), the latest-day page `/`:

```
Rising Repos                                             Days   Source
Repositories gaining stars faster than their own history predicts.
Boards for Monday 21 September 2026 (published 05:10 UTC)

▪ ▪ ▫ ▪ ▪ ▪ ▪ ▪ ▪ ▫ ▪ ▪ ▪ ▪ ▪ ▪ ▪ ▪ ▪ ▪ ▪ ▪ ▪ ▪ ▪ ▪ ▪ ▪ ▪ █   ← day strip
        ¯                     ¯                                 ← amber underline = a held band that day
                                                              █ = this page's day

┃ (staleness banner, amber left border, only when the board is > 26 h old)

Daily  12 repositories    │ Weekly  4 repositories    │ Monthly  0 repositories
                          │                           │
┃ The crawl behind this   │  1  fastapi/fastapi       │ No repository yet has the
┃ board reached 208,246   │     description…          │ 182 valid nightly
┃ of 209,170 repositories │                           │ observations the monthly
┃ with 200 to 1k stars,   │     2.1×  its usual pace  │ board requires — this
┃ so that range is held.  │           +410 stars      │ board fills as data accrues.
┃ 200-1k: 208246/209170   │           above its trend │
                          │                           │
 1  astral-sh/uv          │     81,020 stars 3,910    │
    An extremely fast     │     forks Python          │
    Python package…       │     established           │
                          │     ▸ Security and        │
    3.4×  its usual pace  │       structure           │
          +1,240 stars    │                           │
          above its own   │  2  …                     │
          trend           │                           │
                          │                           │
    48,210 stars 1,320    │                           │
    forks Rust growing    │                           │
    3rd day on the board  │                           │
    RS 4.21               │                           │
    [provisional]         │                           │
    ▸ Security and        │                           │
      structure           │                           │
 2  …                     │                           │

Built 2026-09-22 05:12 UTC. RS is how rare a repository's excess above its own
trend is, in −log10 units within its star stratum; the board publishes RS ≥ 3.
Source
```

Narrow (< 1100 px): the same, stacked daily → weekly → monthly, with a
three-link in-page nav under the day strip ("Daily 12", "Weekly 4",
"Monthly 0"). At 360 px the pace block keeps its 2.6 rem numeral; the words wrap
beside it.

`/days/YYYY-MM-DD/`: identical, except the heading reads "Boards for <date>" at
1.25 rem under the wordmark, the day strip emphasises that day, and a nav line
above the boards gives "Previous day 19 September" and "Next day 21 September"
as plain links. No staleness banner — an archive page is dated by its heading.

`/days/`: the wordmark, "Every board day", then one table:

```
Day                       Daily   Weekly   Monthly   Notes
Monday 21 September 2026     12        4         0   ▪ held 200 to 1k (daily)
Sunday 20 September 2026      9        3         1
Saturday 19 September 2026    0        0         0   part of the lookback is backfilled
…
```

Day cells link to the day page; the amber square marks a held band, in text.

## 3. The row, element by element

```
 rank   name (mono, link unless link_suppressed)
        description, one or two lines, ≤ 60ch
        PACE   its usual pace
        2.6rem +N stars above its own trend
        stars  forks  language  band  "3rd day on the board"  RS n.nn   (0.9 rem, muted, spaced not dotted)
        [tag] [tag]                                                      (only non-suppressed badges, plain words)
        ┃ Listed as deleted/dmca — link removed                          (corrections only)
        ▸ Security and structure
            <card line>
            <structure line 1>
            <structure line 2>
            Score 4.80, fork corroboration 0.92, compared within the 1-3k star stratum. Scanned at <sha>.
```

Badge words: provisional → "provisional"; limited-history → "limited history";
sustained → "sustained"; unconfirmed-by-forks → "not confirmed by forks";
fork-history-insufficient → "fork history too short". `category-withheld` and
`no-summary` never render.

## 4. Review against the direction — what I changed after writing this down

- First draft had a "score / stars / band" `<dl>` with middle dots between items,
  carried over from the current page. That is exactly the meta-chain the
  direction bans; the facts line is now sibling spans separated by space.
- First draft set the hold text itself in amber. Light amber fails AA for running
  text, so the disclosure is ink text with an amber left border, and the archive
  table uses an amber square before muted text.
- First draft kept the radio band filter. Across three columns a global filter
  hides rows unevenly and the radios must live outside `<main>` for the sibling
  selector; band is instead a plain word on the facts line and the filter is
  dropped.
- Nav links were "Days →" and "Previous day ←". Arrows removed.
- The archive table's "Notes" column first said "HELD" in small caps. Now
  sentence case: "held 200 to 1k (daily)".
- Day-strip blocks had a hover scale transition. Removed; there is no motion
  besides `<details>`.
- The `<details>` summary was styled as a button-like pill. It is now plain text
  with the browser's disclosure marker, since it is the only interactive control
  in a row and a pill would compete with the tags.

## 4b. Second look, after rendering the fixture tree in a browser

- The pace block aligned the numeral and the two small lines on a shared
  baseline, so "its usual pace" floated above the numeral's middle and
  "+N stars" hung below it. The words are now vertically centred on the numeral
  and read as one unit at 1440 px and at 390 px.
- In the archive table the amber square mark inherited the note's
  `display: block` and sat on its own line. Scoped the rule to direct children.
- The page requested `/favicon.ico` and got a 404 — the only console error. An
  inline empty `data:` icon keeps the page at zero failed requests.
- Kept: the 30-block strip wraps to two rows at phone width and still reads,
  the in-page board nav appears only when the columns stack, and the
  `<details>` disclosure opens without any styling of its own.

## 5. Things deliberately not built

- No per-repo pages: `site-data/repos/*.json` is out of scope for these three
  page kinds; the security card and structure lines already ride the row.
- No JavaScript at all.
- No band filter (see §4).
- No sparkline of the repo's trajectory: the data contract carries no series.
