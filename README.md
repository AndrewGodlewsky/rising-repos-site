# rising-repos-site

The pages of [risingrepos.com](https://risingrepos.com), which lists the GitHub
repositories gaining stars faster than their own pace predicts. The RisingRepos
project works out which repositories those are and commits the data here. This
repository holds the pages: their templates, the generator that builds them,
and the workflow that uploads them to Cloudflare Pages, `deploy.yml`.

## The live site and the preview

What this repository's `main` builds is live at risingrepos.com. It took the
place of the earlier site, kept under the tag `legacy-site`, during an
unattended run of the RisingRepos project in November 2026. The record of
that switch is on
[AndrewGodlewsky/RisingRepos#58](https://github.com/AndrewGodlewsky/RisingRepos/issues/58).

| Address | Serves | Source |
| --- | --- | --- |
| <https://risingrepos.com> | This site, uploaded again on every push to `main` | `main` |
| <https://preview.risingrepos.pages.dev> | The last upload made before go-live. No push reaches it now | `main` as it stood before go-live |

- Each push to `main` is uploaded to the Cloudflare Pages branch `main`. That
  is the project's production branch, so every upload is a production
  deployment, and the newest one is what risingrepos.com serves.
- A production build leaves `<meta name="robots" content="noindex">` out of
  its pages. Only a build made with `--noindex`, as each upload to the preview
  was, puts it in.
- Going live was one reviewed change, to the three workflows and to the site
  eval. [RUNBOOK.md](RUNBOOK.md) gives the checks made before it, every line
  it moved and why, what is looked at once it is made, and how risingrepos.com
  can be returned to the earlier site. `tests/test_runbook.py` holds the
  runbook's list of those lines to the files.

## The pages

A daily board is one ranked list. Each row shows its rank, the repository's
name linked to GitHub, its description, the stars it gained on the board day,
a small drawing of that pace against its own, and its total stars, in the
order the data file gives them. Its chevron opens it on the reason it is on the
board, which a reader can set against its stars, and, once the page's script
has the board day's `history.json`, on its score and the sum behind it, its
facts, and its last 30 board days (see "A row" and "An opened row" in the
design note). The site computes no score and no rank: it words and rounds the
numbers the file gives.

Above the rows, a board's page says what changes how it reads: that it is an
earlier board, that its ranking is provisional while the data file says the
score is, which star bands it holds back, and how many repositories could not
be ranked, and why. At its foot, About this board gives its plain facts: how
many repositories and when it was published, when the day's update began and
how long that took, that a board put out days late came after its day, what
New means on it, the formula that ranked it, and the days of incomplete
snapshots that its ranking leaned on. Each comes from the data file, only when
the file says so. Opened once the newest board is 26 hours old, every page but
the not-found page and How it works says how old it is, without a new build,
and from 7 days old it shows no board (see "The notice of an old board" in the
design note). The build writes these pages, which `PAGES` in
`sitebuild/__init__.py` lists:

| Address | Page |
| --- | --- |
| `/` | The newest board day's board |
| `/days/` | History: every board day as month calendars, newest first, each day with its count of repositories |
| `/days/<board day>/` | Each board day's board, the newest included, so that a board day keeps one address |
| `/days/<board day>/history.json` | What an opened row of that board shows beyond its line, for each board with rows, fetched on the first opening |
| `/baseline/` | Baseline: each repository on the newest board, placed by its baseline against its recent pace, with every one in a table |
| `/how-it-works/` | How a board is ranked, in a few plain sentences, with the worked example drawn, and what the site is set in |
| `/static/fonts/OFL.txt` | The fonts' licence and IBM's copyright notice, which the licence asks to travel with them |
| Any other | `404.html`, the page for an address that holds none, which links to `/` and to `/days/` and states no board day |

Each board's page links to the board day before it and the board day after
it, and the site's bar on every page links to History, Baseline, and How it
works. The addresses are the earlier site's, so a link to one of its board
days still leads to that board day on the live site. Each build writes every
page again: from the 115 board days in `site-data/` on 21 November 2026, 120
pages, 111 history files, and the licence, in about 10 seconds.

What every page holds to, each checked by a test in `tests/`:

- **How it states its board day.** The root's `<head>` carries
  `<meta name="rr:board-date">` with the board day and
  `<meta name="rr:published-at">` with the file's `published_at`, once each,
  as the data contract says. No other page carries either, so the read-back
  after a publish and the checks of a stale site, which read them, read the
  root. The pages that carry the notice of an old board, the root among them,
  also give the newest board's day, written out as the page writes dates, and
  its publish time in the notice's `data-newest-board-day` and
  `data-newest-published-at`, which only the notice's script reads.
- **Owner-written text.** A repository's owner wrote its name, description,
  language, and the licence file GitHub names its licence from. Each is escaped
  where the page shows it: Jinja2's autoescaping is on for every template, and
  no template marks a value as safe. The language is also a row's `data-l` and
  an option of the language filter, each one attribute value or one option's
  text. `history.json` holds a licence and an earlier name as JSON strings, and
  the script writes every value it reads from the file as text
  (`textContent`), into elements of a fixed set of tags. None of them is made
  a link. A row's name links to `https://github.com/<full_name>`, and the data
  contract lets `full_name` hold only letters, digits, `-`, `_`, `.`, and one
  `/`.
- **One script, the site's own.** Every page carries one script,
  `sitebuild/templates/site.js`, written in the page, made of the parts it
  uses: the theme, on every page; the notice of an old board, on every board
  day's page, the root among them, History, and Baseline; a board's filters
  and opened rows, on a board with rows; and the chart's readout, on Baseline.
  The Content-Security-Policy, in a `<meta>` tag, lets that one script run, by
  the SHA-256 of its exact text, which the build works out each time. It
  forbids every request but the page itself, and on a board with rows, a
  fetch from the site's own address, for `history.json`. No page lets scripts
  run through `'unsafe-inline'`, and no element has an event-handler
  attribute. With scripts turned off a page is whole: the board lists every
  row, a row opens on its reason line, and no control shows that would do
  nothing.
- **Nothing from another site.** The page requests nothing from another
  address. Its type is inside it: the four faces are `data:` addresses in its
  stylesheet, so no font file is fetched or published. Its styles, its script,
  and its icon are in the page too. The script stores one thing in the
  browser, the reader's choice of theme, under `theme` in `localStorage`, and
  sends nothing anywhere.
- **Its size.** A page, with its styles, its script, and its type, stays
  within **500,000 bytes**. Measured on 2026-11-21, without `--noindex`:

  | Board | A board's page | History | Baseline | How it works | The not-found page |
  | --- | --- | --- | --- | --- | --- |
  | The data contract's example, 5 rows | 98,971 bytes | 73,639 bytes | 78,653 bytes | 74,574 bytes | 69,538 bytes |
  | 316 made-up rows, each description the longest the contract allows (350 characters) and holding characters that escaping lengthens, and each row's reason the longest the site has written, 200 bytes | 482,638 bytes | | | | |
  | `site-data/` on 2026-11-21: the root, 264 rows, and the longest board, 12 August 2026, 475 rows | 310,553 and 480,324 bytes | 105,363 bytes | 137,958 bytes | | |

  The four faces are 34,964 bytes of every page. The script is 1,264 bytes
  where it is the theme alone, 2,948 with the notice of an old board, and
  21,975 on a board with rows, with its filters and opened rows. A made-up row
  above is 1,226 bytes of markup, and a row of `typical_rows` in the test
  about 800. What an opened row shows beyond its line is in `history.json`,
  not in the page: 222,708 bytes for the longest history in `site-data/`, 20
  August 2026. The notes on the stylesheet and the
  scripts are Jinja comments, which no page carries: as CSS and JS comments
  they took 9,531 bytes of a board's page.
  [AndrewGodlewsky/RisingRepos#199](https://github.com/AndrewGodlewsky/RisingRepos/issues/199)
  raised the limit from 410,000, which the 316 made-up rows had reached at
  381,378 bytes. Past about 500 real rows, a long board's later rows in a
  second file is the next step.
  [RisingRepos#64](https://github.com/AndrewGodlewsky/RisingRepos/issues/64)
  is where the limits that a longer board meets are weighed.
- **The root on the wire.** The site eval gives the root a budget of 100,000
  transferred bytes in each of its two profiles, phone and desktop
  (see `evals/site/limits.json`), and the root of 21 November 2026, 264 rows,
  takes 81,993 bytes gzipped at level 6. A test in
  `tests/test_page_weight.py` fills the newest board with 713 invented rows,
  gzips the built root at level 6, and checks the result against 150,000
  bytes, a budget of its own since
  [AndrewGodlewsky/RisingRepos#199](https://github.com/AndrewGodlewsky/RisingRepos/issues/199).
  On 2026-11-21 it came to 145,779 bytes with zlib 1.3.1, which the workflow's
  Python uses, and 142,657 with the zlib-ng that Python 3.14 uses on Windows,
  so a size measured on Windows reads about 2% low. The type takes about
  28,000 of those bytes. Before the notes on the stylesheet and the scripts
  became Jinja comments the root came to 149,615. Each invented row carries
  105 characters of description in random letters, which pack worse than a
  real description's words, so the test errs on the heavy side. Its numbers
  are drawn to the spread of formula 2's rows to 14 November 2026, which
  `typical_numbers` in the test gives. The count is formula 2's longest board
  so far, 475 rows, raised by half for boards still to come
  ([AndrewGodlewsky/RisingRepos#122](https://github.com/AndrewGodlewsky/RisingRepos/issues/122)).

### The design note

The site has one look. It was chosen in
[AndrewGodlewsky/RisingRepos#199](https://github.com/AndrewGodlewsky/RisingRepos/issues/199),
from three redesigns built for it, and the record of why is there. It took the
place of the look chosen in
[RisingRepos#71](https://github.com/AndrewGodlewsky/RisingRepos/issues/71).
A ticket that adds a page designs what it adds to this note, and a change to
the look changes this note in the same pull request.

**What the look is for.** People come back each day to see what is rising.
The page is quick to take in and easy to find one's way around, clean and
current, and pleasant to use. It has a character of its own rather than a
stock look, and it reads as made with care. Its affordances are plain: how a
thing on the page looks shows what it does, before anyone tries it.

**The idea.** The definition of a rising repository is a fact about two
paces, so the site draws it. Every repository on a board is a point: its usual
pace across, its pace over the last two days up, both on log scales, and "N×
its usual pace" is a family of parallel diagonals. How far above the dashed
diagonal of its own pace a repository sits is its score. Around that, the
chrome is a quiet logbook: warm paper and graphite ink in the light theme,
graphite paper and light ink in the dark, one evergreen pen, amber kept for
what is new, and a deep red kept for a loss. The dashed line of a
repository's own pace is the one recurring mark: in the site's mark, in each
row's small drawing, in an opened row's drawing, on Baseline, and in How it
works' worked example.

**Type.** Two families, Rising Sans and Rising Mono, at 400 and 500, inside
each page. They are IBM Plex Sans and IBM Plex Mono, by IBM Corp., under the
SIL Open Font License 1.1, cut to the characters the site's own text uses and
renamed, as the licence asks of a modified version. `sitebuild/fonts/subset.py`
makes them from the files in `sitebuild/fonts/source/`, and How it works names
them under "The type" and links to the licence. Text an owner wrote, in any
script, falls back to the reader's own faces. Until a face is in, the text is
set in "Rising Sans fallback": Arial, Liberation Sans, or Arimo, with its size
and line metrics matched to Rising Sans, so that nothing moves when the face
arrives.

| Role | Family | Where |
| --- | --- | --- |
| Text | Rising Sans, `--sans` | Everything that is words: the names, the descriptions, the bars, the notes, the headings |
| Figures | Rising Mono, `--mono`, with tabular figures | The ranks, the day's gain, the total stars, the counts on History, the chart's ticks and labels, the figures of an opened row |

The body is 15 px, the description 14 px, a repository's name 16 px (17 px from
768 px up) at 500, and its owner 14 px. A page's title is 36 px, and 56 px from
768 px up. A board's date, its title, is 20 px in the day bar, and 28 px from
768 px up.

**Colour.** Each colour has one job. The tokens are on `:root` in
`sitebuild/templates/site.css`; the dark theme sets them again.

| Token | Light | Dark | Its job |
| --- | --- | --- | --- |
| `--bg` | `#f7f6f2` | `#121311` | The page, and the browser's own bar (`theme-color`) |
| `--surface` | `#ffffff` | `#181a17` | A control, a card, an opened row, the notice of an old board |
| `--raised` | `#efeee8` | `#22241f` | A note above the rows, and a control under the pointer |
| `--text` | `#1b1a16` | `#ecebe5` | The text: 16.10:1 on the page, 15.60:1 in the dark |
| `--text-2` | `#55524a` | `#b0ada3` | The descriptions, the owner, the bars' links, a gain of 0 or a day with no count where a gain is green: 7.21:1, 8.30:1 |
| `--text-3` | `#6b675d` | `#939087` | The quietest text: the ranks past the top ten, the headings over the figures, a visited repository: 5.22:1, 5.84:1 |
| `--accent` | `#12704b` | `#5cc896` | Evergreen: what a repository gained, the top ten ranks, a pressed filter, the focus ring, a link under the pointer: 5.64:1, 9.01:1 |
| `--on-accent` | `#ffffff` | `#0f1a14` | A top-three rank on the accent: 6.10:1, 8.62:1 |
| `--new` | `#8a4b08` | `#f0b45e` | Amber: the New mark, the New filter: 6.79:1 on a control, 9.50:1 |
| `--loss` | `#a8201a` | `#f07a6e` | Deep red: a loss, and nothing else, written with the true minus, in the growth column and in an opened row's gains over 7 and 30 days and its table of days: 6.73:1, 6.84:1 |
| `--shade-1` to `--shade-4` | `#eef2ee` to `#9fcbb0` | `#1b221d` to `#285e42` | History's ramp, by a board's count of repositories |

The tints, `--accent-soft`, `--gain-soft`, and `--new-soft`, are the accent and
amber at 8% to 20%, and `--line`, `--line-strong`, and `--dot` the ink at 10%
to 32%. Every text colour meets WCAG AA, 4.5:1, against each background it is
set on, tints included, as the browser paints them; the lines and the focus
ring that carry meaning meet 3:1; and `tests/test_colour.py` holds each pair,
in both themes. The lowest is `--text-3` on a row under the pointer, 4.66:1. A
visited repository dims from the ink to `--text-3`, 3.09:1 apart, so a reader
who comes back each day sees which ones they have opened. No colour but the
three hues and the neutrals is set, and the test holds that too.

**The theme.** The site follows the browser's own setting, light or dark. The
switch at the right of the site's bar turns it the other way, and the choice
is kept in this browser, under `theme` in `localStorage`. A press that comes
back to the browser's own setting clears the kept choice, so the site follows
the browser again, with no third state on the switch. The theme's script runs
in the `<head>`, so a kept choice applies before the page is first drawn.
Without the script the switch is not shown and the site follows the browser.

**The site's bar.** On every page: the mark and "Rising Repos", which links to
the newest board; History, Baseline, and How it works, the one the page is
marked `aria-current`; and the theme switch. On a phone the three links take a
line of their own under the name. Baseline's name is `BASELINE_NAME` in
`sitebuild/__init__.py`, so that renaming the page is one change.

**The day bar.** Under the site's bar, a bar that stays at the top of the
screen while the page scrolls: the board day before, with an arrow before it;
the board's date, which is the page's `<h1>`; and the board day after, with an
arrow after it. An earlier board's bar also leads to the newest, from 768 px
up. Where there is no board day before, it says "First board". Each date is
short, "8 Nov", and a screen reader hears "The board before" or "The board
after" first, and "The daily board for" before the date. History's,
Baseline's, and How it works' bars lead back to the newest board instead. The
bar is 52 px tall, and 64 px from 768 px up, and `scroll-padding-top` clears
it, and the column headings under it on a desktop.

**The notes above the rows.** What changes how a board reads is said in the
open, above its rows: an earlier board, a provisional ranking, a star band
held back, and repositories that could not be ranked. Each is words on the
raised surface, with a rule in the ink at its left and its first sentence at
500, so it reads the same to a screen reader. The kinds are kept apart, since
each says something different about the rows:

- **A star band held back.** When the board day's own snapshot missed some
  star counts, RisingRepos leaves off every row of each star band they fall
  in, rather than rank a band from part of its repositories. The note counts
  the bands, "One star band is held back.", and names the star counts the
  snapshot missed and each band held, as the file gives them.
- **Repositories that could not be ranked.** When a day the ranking needs is
  partial or missing, the file says how many repositories it kept from the
  ranking, and the note starts with that count: "2,183 repositories could not
  be ranked." A missing day's starts "No repository could be ranked."
- **The partial days the ranking drew on** are plain facts, in About this
  board: a recent day that the file does not name as one the ranking lacked
  ([AndrewGodlewsky/RisingRepos#137](https://github.com/AndrewGodlewsky/RisingRepos/issues/137)),
  a partial day that kept none from it, and the days read only further back,
  with their count and the span they fall in, so that a single day and several
  dozen are worded alike.

A board whose file predates these fields
([AndrewGodlewsky/RisingRepos#13](https://github.com/AndrewGodlewsky/RisingRepos/issues/13))
says of its partial days what it did before them, in a note above the rows.
The generator gives those older notes one function and one block of the
board's template, set apart from the path a newer file takes, so that both can
be deleted once every board day has been published again with the fields.

When a board lists no row, its message says why, so that a board held back,
or one whose ranking lacked a day, never reads as a day on which nothing rose:
"No repository is on this board" for a held board, "No repository could be
ranked on this day" two days after a missing day, "No repository that could
be ranked made the board on this day" after a partial one, and "No repository
made the board on this day" otherwise. About this board carries the board's
state from the file, `rows`, `empty`, or `held`, in its `data-state`, for a
reader of the page rather than of its words. The site decides none of this.

**The filter.** Over the rows, where the page's script runs: All or New, each
with its count; the star bands, from the file's `star_bands`; the language; the
order (by rank, most stars gained, most often on the last 14 boards, fewest
stars first, most stars first); and a search of the names and the
descriptions. A band the board holds back has no row, so its button is
hidden. A file from before `star_bands` gives no bands, and its board no band
filter: the contract has the site keep no limits of its own. The filter says
how many rows it shows, to a screen reader, and when none match, says so. Its
state is in the address (`?show=new&band=1k-3k&lang=Rust&sort=gained&q=…`),
so a filtered board can be linked to. The controls are marked `js-only`, which
the stylesheet shows only once the script has marked the root element, in the
`<head>`, so they are in place from the first frame and move nothing, and
without the script the page shows the whole board and no control.

**New.** A repository is New when its name, in any case, was on none of the
boards before this one, back to the first; a renamed or moved repository is
New under its new name, and its opened row still lists the boards it was on
before, which follow it by its GitHub id. New is not told when the board
before held a band back or listed nothing, since a repository missing from it
may have been kept off, and About this board says so. `History` in
`sitebuild/__init__.py` works it out at build time by comparing lists: the
site computes no score and no rank.

**A row.** On a phone a row is stacked: the rank and the name on the first
line; the description at the row's full width, cut to one line; then the day's
gain with "on the day" after it, the drawing of its pace, and the total stars
at the right; and the chevron under the rank. From 768 px up a row has five
columns, under headings that stay in view under the day bar: the rank, 48 px;
the name with the description under it; the day's gain, 112 px; its pace,
120 px; and the total stars, 96 px. The top three ranks are set on the accent,
the top ten in it, and the rest in `--text-3`. A New repository has an amber
"New" after its name. The owner and the name are one run of text,
`owner/name`, so that a search of the page finds a row by it. The table, its
rows, and its cells name their roles (`role="table"`, `row`, `columnheader`,
`rowheader`, and `cell`), because some browsers stop telling assistive
technology that a table is one once its parts' display changes, as a stacked
row's does, and every cell keeps its column's heading, the description's and
the reason's for a screen reader only. A file older than the rows' numbers
gives no row a reason, and the board then shows the language in their place.

The day's gain is `gained_1_day`, signed: "+147" in the accent, "0" in
`--text-2`, "−600" for a loss in `--loss`, with the true minus, which the
site's type draws as wide as the plus, and "–" in `--text-2` when the file has
no count for the day before. A file from before the field gives the stars a
day over the recent days instead, "+148", as the board did before. The
drawing is the row's own pace against what it gained, on one log scale for
every row, so that two rows compare: the dashed level of its usual pace, the
level of its last two days, and the part between in the accent. A screen
reader hears it in words: "Usual 0.25 a day, then 48 a day".

**An opened row.** The chevron is a `<details>` whose `<summary>` is named "More
on" the repository, so a click, a tap, or the keyboard opens it with no
script, on its reason line:

| The row | Its line | The sum, once opened |
| --- | --- | --- |
| Its usual pace was at least the floor of 1 star a day | `+266 above its own trend · 60× its usual pace` | `That multiple is its score: 270 stars ÷ 2 days ÷ its usual 2.25 a day.` |
| Its usual pace was under the floor | `+157 above its own trend · its usual pace was under 1 star a day` | `Score 79 = 158 stars ÷ 2 days ÷ 1: its usual 0.58 a day counts as 1 star a day.` |
| It had been losing stars | `+87 in 2 days · it had been losing stars` | `Score 43.5 = 87 stars ÷ 2 days ÷ 1: it lost 4.04 a day before, which counts as 1 star a day.` |
| The loss rule left a recent day out | `+487 in 1 day · 16× its usual pace` | `That multiple is its score: 487 stars ÷ 1 day ÷ its usual 31.08 a day. A recent day that lost too many stars to be believed is left out.` |

`why` in `sitebuild/__init__.py` words both from the numbers the file gives
the row ([AndrewGodlewsky/RisingRepos#49](https://github.com/AndrewGodlewsky/RisingRepos/issues/49)).
A multiple of the floor is no multiple of the repository's own pace, so a row
under the floor gives none, and a row that had been losing stars, or whose
recent pace keeps one day, gives the stars it gained. A multiple has no cap:
a row can say `1,286× its usual pace`. It takes one decimal place under 10 and
none from 10. Every number is rounded half up, as a reader rounds, and parts
its thousands with commas.

With the script, the first opening of a row fetches the board day's
`history.json` once, and every row of the board then opens on the rest: the
sum; its facts (its multiple, its gains over 7 and 30 days, its language, its
licence, its star band, when it was created and last pushed to, its first
board, a name it was listed under before, how many of the last boards it was
on, and its best rank on them); a drawing of its stars day by day over the
last 14 days against the dashed line of its usual pace, with the part of the
two recent days above its own trend shaded; its stars over the last 30 days, from `star_history`, with a gap where a day has no count; its
last 30 board days, each a link to that board, carrying its rank there; and a
table of the boards it was on. Each part says what it is in a caption, for a
screen reader. A row's figures are worded as its line words them, so the two
never disagree, and a fact the file does not give is left out, never guessed.

**About this board, and the foot.** Under the rows, About this board gives the
board's plain facts in `--text-2`, each a line: its count of repositories and
when it was published, in UTC; when the day's update began and how long it
ran, in words ("The day's update began at 22:35 UTC and took 12 minutes to
publish this board."), with the date when it began on an earlier day; "This
board was made after its day", for a board put out two days or more after its
day; what New means on it, or that it cannot be told; "Ranked by formula
version 2.", with a link to How it works; the partial days its ranking drew
on; and a link to Baseline. Each reads its field
([RisingRepos#51](https://github.com/AndrewGodlewsky/RisingRepos/issues/51),
[RisingRepos#47](https://github.com/AndrewGodlewsky/RisingRepos/issues/47)),
and a file without the field gets no line: the page does not guess.
`daily_job` gives the template plain values, and `board.html` words them in
one place. A file whose start comes after its publish fails the build (see
"The data"). Then the foot: "End of the daily board for" its date, the board
days before and after again, and "Back to the top". An empty board has both.
At the foot of every page, the colophon says what the site is and that it is
not affiliated with GitHub.

**An earlier board.** A board day's page that is not the newest says so first,
above its rows, and links to the newest. Only the root states a board day in
the data contract's tags
([RisingRepos#43](https://github.com/AndrewGodlewsky/RisingRepos/issues/43)).

**History.** At `/days/`, every board day as month calendars, newest month
first and Monday first, two months a row from 1,100 px up. Each board day is a
cell that links to its board, with its count of repositories, how many of them
were new (from 768 px up, where the cell has room; a screen reader hears it at
any width), and a shade on a fixed ramp by that count, the same every month:
under 200, 200 to 274, 275 to 349, and 350 or more. The newest is outlined in
the accent and marked `aria-current="date"`. A day between the first board and
the newest that has no board is hatched, and a screen reader hears "no board".

**Baseline.** At `/baseline/`, the newest board's chart: each repository a dot,
placed by its baseline, the stars a day it gained over the twelve days before,
across, against its recent pace, up, both on log scales, with the diagonals of
its own pace, dashed, and of 3×, 10×, 100×, and 1,000×. The top ten are in the
accent, and the first five are labelled with their ranks. With the script,
the dot nearest the pointer names its repository, its rank, and its growth in
a readout, and a click on it goes to its line in the table. Under the chart,
the table gives every repository in words, so the chart holds nothing a
screen reader cannot reach. `pace_chart` in `sitebuild/__init__.py` places the
dots from the file's own numbers: the usual pace is the divisor the file
gives, and the recent pace its recent stars over its recent days.

**How it works.** The page says in a few plain sentences how the formula that
`DESCRIBED_FORMULA` in `sitebuild/__init__.py` names ranks a board: the two
recent days against the twelve before them, the floor, who makes the board and
when a star band is held back from it, what must hold before a repository has
a score, and that no gain is set aside. Its worked example is drawn: twelve
days at a usual 30 stars a day, then 520 stars in two days, with the part above
the dashed line of its own pace marked as "+460 above its own trend". It names
the formula under its title, and when the newest board was ranked by another,
it says so first. It carries no notice of an old board, which would hide its
text. Under "The type", it names the fonts and links to their licence.

**Links and focus.** A link in running text is underlined in a quiet line,
which takes the accent under the pointer. A repository's link underlines only
the name. A browser lets a visited link change only its colours, so the
visited state is a change of colour. To see it in an automated browser, whose
fresh contexts record no visits, force the state on a link with the DevTools
protocol's `CSS.forcePseudoState` and `visited`. Every control, link, and
`<summary>` shows a 2 px ring in the accent when the keyboard reaches it.

**Forced colours and motion.** In forced colours, the drawings made of
backgrounds take system colours, Baseline's legend keeps the page's, as its
chart's dots do, and History's cells, which lose their shades, keep an edge,
the newest one's in the highlight. With reduced motion, nothing transitions.

**The notice of an old board.** A page is built only when something is
pushed here, so when the publishing stops, no build runs to say so, and the
newest board goes on looking current
([AndrewGodlewsky/RisingRepos#56](https://github.com/AndrewGodlewsky/RisingRepos/issues/56)).
So every board day's page, the root among them, History, and Baseline carry
the notice's part of the page's script, `sitebuild/templates/old-board.js`,
which works out each time the page is opened how long ago the newest board
was published, by the reader's own clock. Every one of those pages measures
from the newest board, so an earlier board day's page says the same as the
root.

| The newest board's age | What the page shows |
| --- | --- |
| Younger than 26 hours, or a clock set behind its publish time | Nothing new: the page exactly as it was built |
| 26 hours or more, but less than 7 days | A notice under the site's bar: "**The newest board is 3 days old.** It is the board for 10 November 2026. A board is due every day, and none has come out since." |
| 7 days or more | The notice reads "**No board is shown: the newest is 10 days old.** It is the board for 3 November 2026. When a week passes with no new board, the site stops showing its boards, so that an old ranking is not taken for a current one.", and what `<main>` holds is hidden |

- 26 hours exactly counts as old, as it does for the stale check (see "The
  stale check"). The age is in whole hours under two days, and in whole days
  from then on. The build writes the board day into the notice with the same
  filter as every other date on the page, so the script works out only the
  age.
- The notice is a box on the surface, up to 640 px wide, with its first
  sentence at 500, between the site's bar and the day bar. It is words, not a
  colour or a badge, so it reads the same to a screen reader.
- **Nothing moves.** The page's one script is in the `<head>`, and the notice
  right after the site's bar, so the script runs before the browser has read
  the notice, the day bar, or the board. It watches for the notice as the page
  is read, and a notice it shows pushes down nothing already painted. From 7
  days it sets `data-withheld` on `<html>`, and the stylesheet hides what
  `<main>` holds, which has not been read yet either. `<main>` itself stays,
  so the page keeps its main landmark. On a fresh page the hidden notice takes
  no room.
- **With scripts turned off**, or in a browser that refuses the script, the
  page is the fresh page: the notice stays hidden, and the built page holds
  none of its words, so nothing on it would be false on a fresh day.
- **What it touches.** It reads the notice's two `data-` attributes and the
  clock. It writes only its own words, the board day as the build wrote it,
  and the numbers it works out, as text (`textContent`), shows the notice, and
  sets the one attribute on the root. It reads nothing an owner wrote and
  makes no request. A publish time that is not in the exact shape the page
  writes it, or that names no real moment, leaves the page as built.
- **Which pages.** One line near the top of `sitebuild/templates/page.html`
  names the templates whose pages carry the notice. To keep the notice to the
  root alone, make that list `("latest.html",)`.
- **Its tests.** `tests/test_old_board.py` takes the script's text from a
  built page and runs it under Node, through `tests/run_page_script.js`, with
  the clock passed in, and with the page's elements found only once the
  script has run, as a script in the `<head>` meets them. It runs it on every
  page that carries it: a second short of 26 hours and at 26 exactly, a second
  short of 7 days and at 7 exactly, at 10 and 400 days, with the clock set
  behind the publish time, and with malformed publish times. It runs the
  theme's part too: a kept choice, a press, and a press back to the browser's
  own setting. It also checks that the policy names the hash of the script's
  exact text, so a script whose text no longer matches its hash fails the
  tests rather than being refused by readers' browsers.

**What a later page keeps.**

- The site's bar, and a bar of its own under it for the page's place, which on
  a board is the day bar with the date as its heading.
- Rising Sans for words and Rising Mono for figures, inside the page. No font
  file, and no third family.
- The colours in the table, each with its one job: the accent for what a
  repository gained and the board's top, amber for what is new, the red for a
  loss, the neutrals for the rest. A new text colour comes with a background
  that gives it 4.5:1, in both themes, and a line in `tests/test_colour.py`.
- An underline means a link, and a visited repository dims.
- Tabular figures for any number in a column.
- A drawing comes with its figures in words, for a screen reader.
- A page that reads at a phone's width (390 px) and a desktop's (1440 px), in
  both themes, with five rows, with hundreds, and with none, and that is whole
  with scripts off.

The look is in `sitebuild/templates/site.css`, which
`sitebuild/templates/page.html` includes in every page. `page.html` also holds
the `<head>` with the page's one script, `site.js`, the site's bar, the
notice of an old board's place, which `old-board.html` holds, the place of the
page's own bar, and the colophon. `board.html`, `days.html`, `baseline.html`,
`how-it-works.html`, and `not-found.html` fill the rest. `latest.html` is
`board.html` with the data contract's two tags in its `<head>`, for the root,
and `nav.html` holds the links between board days that the day bar and a
board's foot share. The script's parts are `theme.js`, `old-board.js`,
`filters.js`, and `baseline.js`. `PAGES` in `sitebuild/__init__.py` lists each
page the build writes, with its template.

## The data

The RisingRepos project defines the files a board day is published as, in its
data contract (`src/risingrepos/publishing/contract/README.md` there), and its
publish writes them here:

```text
site-data/
  boards/index.json                   every board day published, newest first, with its row count
  boards/days/<board day>/daily.json  one board day's daily board
  contract/index.schema.json          the schemas the files follow, shipped
  contract/daily.schema.json          with them in the same commit
```

The publish wrote its first board days here on 2026-11-12
([RisingRepos#42](https://github.com/AndrewGodlewsky/RisingRepos/issues/42)),
and `site-data/` holds what it last wrote. A publish can write a range of board
days in one commit
([RisingRepos#43](https://github.com/AndrewGodlewsky/RisingRepos/issues/43)).

The build reads the index and every board day it lists, and checks each file
against the schema shipped with it before it writes a page:

- A file that does not match its schema, or cannot be read, fails the build
  with a message that names the file, and no page is written. So does a board
  day in the index whose file is missing or names another board day.
- The index must list each board day once, newest first, since the pages link
  each board day to the ones beside it in that order. An index that does not
  fails the build. The schema's `uniqueItems` alone would let one board day in
  twice with two row counts.
- The index's `row_count` for each board day must be the number of rows in
  that board day's file. A count that differs stops the build, and its message
  gives the board day, the count in the index, and the rows in the file. An
  entry with no count stops it too
  ([RisingRepos#115](https://github.com/AndrewGodlewsky/RisingRepos/issues/115)).
  The pages count a board's rows from its file, so the check is what keeps the
  index's count true for anything else that reads it.
- The pages need `schema_version` 1 or later, which `sitebuild/contract.py`
  states. A file below it fails the build.
- A field the pages do not read is ignored. RisingRepos adds a field to the
  schema and to the files in one publish, so the files still match.
- `partial_days`, which RisingRepos added to each board day's file for
  RisingRepos#45, is read when a file has it and not required when it does not:
  `site-data/` holds files from before the field until a publish writes every
  board day again, and they build as before, with no note on partial days. A
  site built before the pages read the field builds the newer files too: they
  match the schema shipped with them, and the field is one it ignores.
- `daily_job_started_at`, added for RisingRepos#51, is read the same way: a
  file without it, or with null in it, builds with no line on the update. A
  file whose start comes after its own `published_at`, compared to the second
  as both are written, fails the build and is named: the contract gives the
  start as no later than the publish, which a schema cannot say of two fields
  (AndrewGodlewsky/RisingRepos#133).
- `state`, `holds`, `missed_stars`, and `unranked`
  (AndrewGodlewsky/RisingRepos#13) are optional to the pages the same way: a
  board whose file lacks them names no state and no hold, and says of its
  partial days what it said before them.
- `formula_version` (RisingRepos#47) is optional to the pages in the same
  way, and a file that lacks it gets no line naming the formula.
- The seven figures behind a row's score (AndrewGodlewsky/RisingRepos#49),
  `baseline`, `divided_by`, `excess`, `recent_days`, `recent_stars`,
  `days_left_out`, and `score` itself, are optional the same way: a board whose rows lack them builds with no reason on any row.
  A site built before the pages read them builds the newer files too.
- The fields that RisingRepos added for the site's redesign
  (AndrewGodlewsky/RisingRepos#192) are read since the redesign
  (AndrewGodlewsky/RisingRepos#199): `star_bands`
  (AndrewGodlewsky/RisingRepos#196), the bands a board's filter offers; in each
  row `gained_1_day` (AndrewGodlewsky/RisingRepos#194), the growth column; and
  `star_history` (AndrewGodlewsky/RisingRepos#193), `gained_7_days` and
  `gained_30_days` (AndrewGodlewsky/RisingRepos#194 and #195), and `license`,
  `created_at`, and `pushed_at` (AndrewGodlewsky/RisingRepos#197), which the
  board day's `history.json` gives an opened row. They are optional the same
  way: a file without them builds, its growth column gives the stars a day, its
  board has no band filter, since the contract has the site keep no limits of
  its own, and its opened rows show none of them. A test in
  `tests/test_data.py` shows that only that board's pages change. The contract
  marks `license` untrusted, as it does a description, since the repository's
  owner chose the file GitHub names it from: the page writes it as text.
- The schemas are checked with fastjsonschema, the validator that RisingRepos's
  ADR 0013 chose, at the version RisingRepos's `pyproject.toml` pins. It turns
  a schema into Python, and it fetches whatever document a `$ref` points to
  elsewhere. A schema arrives with the data, so the build refuses one that
  holds a `$ref` that does not start with `#`, and compiles every schema with
  handlers that refuse to fetch anything. A `$ref` that starts with `#` can
  still point elsewhere under some `$id`s, and the handlers refuse that too.
  The build never fetches a reference.

The tests build from their own copy of the contract's example, in
`tests/fixtures/contract-example/`, so that the day's data does not change what
they check. Two tests read the day's files all the same. One builds from
`site-data/`, to show that the build reads it when no folder is given, so a
day's files that fail their schema fail the tests as well as the build. The
token search (below) reads every file git would commit, `site-data/` included,
so a day's file that holds a string shaped like a credential fails the tests.
A test holds the copy in `tests/fixtures/` to the bytes of the contract in
RisingRepos commit `0fd590ccbb8fb9087cfd4cdabf1f09fa6ce948c9`, whose schema
says when the daily job that published a board day began, numbers the formula
that ranked it, gives each row its score and the figures behind it, and gives
the board's state, the star bands it holds back, and the days its ranking
lacked. It also carries the fields added for the redesign (above). Its newest
board is held and its older one empty, so the tests
render both.
A change to the contract
reaches it, and that test, by a pull request here.
`.gitattributes` keeps git from changing the line endings of either copy.

## The workflow

`.github/workflows/deploy.yml` has two jobs. The daily data push can change any
file in this repository except a workflow, so nothing it can change runs in the
job that holds the Cloudflare credential.

| Job | Runs on | What it does | What it can reach |
| --- | --- | --- | --- |
| `build` | Every pull request, and every push to `main` | Checks out the repository, installs what `uv.lock` pins, runs the tests, builds the pages into `dist`, and uploads them as the artifact `site` | Read access to the repository. No secret |
| `deploy` | A push to `main`, once `build` has passed | Downloads the artifact, refuses it if it holds a `_worker.js`, leaves the upload to a newer push if `main` has moved on, and uploads it with wrangler | The `deploy` environment's `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, which GitHub gives only to `main`. It never checks out the repository, so it runs nothing from its files |

The deploy job runs wrangler with
`npm exec --ignore-scripts --before=<date> --package=wrangler@<version>`. The
version is pinned in the workflow, npm resolves every package that wrangler
pulls in as the registry stood on that date, and no package's install script
runs. Node is the runner image's own. Every action in the workflow is pinned to
a full commit SHA. `tests/test_workflow.py` checks each of these.

**Pushes close together.** However many there are, their builds run at the
same time and can finish in any order. Their uploads take turns, in the
concurrency group `cloudflare-pages-upload`, and just before it uploads, a run
reads the head of `main` with `git ls-remote`, which needs no credential
because the repository is public. If `main` has moved past the run's commit,
the run uploads nothing and says so in a notice in its log. The group has
`queue: max`, so each deploy job that arrives waits for its turn, and none is
cancelled to make room for another. Without it, GitHub would let only one wait
and cancel it when the next arrived, and the one cancelled could be the newest
push's, leaving nothing to upload it. So the newest push's run gets its turn,
finds `main` at its commit, and uploads its pages once its build passes, and
the pages of an older push never replace those of a newer one, whichever build
finishes first. If the newest push's build fails, nothing uploads it, and
risingrepos.com keeps the pages it had until a push to `main` builds or the
failed run is re-run. If `main` cannot be read, the job fails and nothing is uploaded.
GitHub keeps at most 100 jobs waiting in a group and cancels one that arrives
when the group is full, which would take more than 100 pushes during one
upload.

A pull request builds and does not deploy.

## Building locally

You need [uv](https://docs.astral.sh/uv/), and [Node](https://nodejs.org/)
on the `PATH` for the tests of the page's script. They install nothing for it,
and fail without it. `deploy.yml`'s build job uses the Node that GitHub's
runner image already has.

```sh
uv sync --locked                                     # the pinned dependencies, into .venv
uv run --locked python -m unittest discover -s tests # the tests
uv run --locked python -m sitebuild dist             # the pages, as risingrepos.com gets them
python -m http.server 8000 --bind 127.0.0.1 --directory dist  # then open http://127.0.0.1:8000/
```

The tests are the one command that `deploy.yml`'s build job runs too. They build
from `tests/fixtures/`, but for the one test that builds from `site-data/`
(see "The data"), write only to temporary folders, and reach no other machine:
the stale check's tests talk only to servers of their own on 127.0.0.1 (see
"The stale check").
They include the search that RisingRepos's regression command makes, for a
file git would commit that holds a string shaped like a GitHub token or a
Discord webhook address: `tests/test_tokens.py` fails on one and names the
file, never the value.

The generator reads `site-data/`, or the folder given with `--data <folder>`.
It refuses an output folder that already holds files, so remove `dist` before
building again. The local server answers this machine only, and stops with
Ctrl+C.

## The site eval

Each time a push to `main` reaches risingrepos.com,
`.github/workflows/site-eval.yml` runs Lighthouse on the first page, five times
on each of Lighthouse's phone and desktop profiles. It gives six numbers for
each: Lighthouse's performance score and accessibility score, the Largest
Contentful Paint, the Cumulative Layout Shift, the bytes the page took to
transfer, and the requests it sent. It can also be started by hand for any https
address. [evals/site/README.md](evals/site/README.md) says how it measures, what
each number means, and how its limits were set.

**Reading the numbers.** A run's summary has a table for each page on each
profile. Each number is the median of the five runs, with the lowest and the
highest of them beside it, then the accepted number from
`evals/site/accepted.json` and the limit from `evals/site/limits.json`. A number
outside its limit, or one that could not be measured, fails the job and is
listed under the tables. A failed job holds nothing back: by the time it runs,
the pages are already live.

**What a site change reports.** A pull request's own pages reach the site
only when it merges, so:

- The evidence on its tracking issue gives the numbers before it: the last run
  on `main` that followed a deploy.
- The run that follows its deploy gives the numbers after it, and the change's
  tracking issue links that run. A number that got worse is fixed in a later
  change, or the tracking issue says why it is right.
- A change that moves the numbers on purpose, such as a new design or a larger
  board, replaces `evals/site/accepted.json`, and a limit where one no longer
  fits, in a pull request that gives the reason.
- A change to the eval itself is measured on its own pull request, against the
  live site as it stands.

## Layout

```text
sitebuild/          the generator: python -m sitebuild <folder> [--noindex] [--data <folder>]
  contract.py       reads the data files and checks each against its schema
  templates/        Jinja2 templates, the stylesheet, and the parts of the page's one script, with autoescaping on for every one
  fonts/            Rising Sans and Rising Mono, which the build puts inside each page; subset.py cuts them from IBM Plex's files in source/
  static/           files served as they are, under /static/: the fonts' licence
site-data/          the data files RisingRepos publishes, and their schemas
evals/site/         the site eval, its limits, and its accepted numbers, which .github/workflows/site-eval.yml runs
tests/              the tests
  fixtures/         the data contract's example, which the tests build from
  run_page_script.js  runs a built page's script under Node, with the clock passed in, for test_old_board.py
.github/workflows/  the workflows
  deploy.yml        the build job and the deploy job
  stale-check.yml   the daily check that the site is fresh
  site-eval.yml     the site eval
RUNBOOK.md          going live, and going back
pyproject.toml      the dependencies, and the date uv resolves them as of
uv.lock             every package, pinned with its hashes
.python-version     3.14, for local builds. deploy.yml's build job takes the exact version named in deploy.yml, and stale-check.yml the python3 that its runner has
```

## The stale check

`.github/workflows/stale-check.yml` fetches the site's page once a day and
posts to Discord in three cases: the newest board has grown too old, the page
cannot be fetched, or the page gives no usable board day. Because GitHub runs
it, a stale site is still reported while the machine that publishes is
switched off. The age comes from the page's `rr:published-at`, the moment its
board day was first published (see "The pages"): the board counts as
fresh for 26 hours from then, and as too old after that. The age is a number
of hours since that moment, and the calendar date plays no part in it.

**When it runs.** At 04:41 UTC every day. The daily publish aims to have a
day's board on the site by 8:00 pm New York time: 00:00 UTC while daylight
time is in force, 01:00 UTC otherwise. A board that made it is 26 hours old by
02:00 or 03:00 UTC the night after. The check runs after both, so a missed day
is reported that same night (11:41 pm in New York in winter, 12:41 am in
summer), as long as the board before it was up by 9:41 pm in winter or
10:41 pm in summer. It runs at 41 minutes past the hour because GitHub delays
scheduled runs most, and drops some, at the start of an hour.

**At most one alarm a day.** The schedule starts it once a day, and a run
posts at most one message, so a stale board day is reported at most once a
day. The check keeps no record and can write nothing anywhere, so this is the
whole rule. What it gives up:

- When GitHub drops the day's run, that day has no alarm. The next day's run
  reports the board, a day older.
- A board that goes stale just after the check is reported by the next day's
  check, up to a day later.
- When a board was published later than the times above and the next day is
  missed, the miss is reported a day late.

A run started by hand posts as well, and so does a scheduled run that is run
again by hand. Each of those says in its first line that it was started by
hand.

**What a message says.** Which of the three it found. For a board that is too
old, its board day, how many hours ago it was published, and the limit. Then
the address it read, what to check first, and a link to the run. It mentions
nobody (`allowed_mentions` is empty), and Discord shows no preview of its
links. The run's log shows the message as it was sent, then Discord's answer
as an HTTP status: 204 when Discord took it. A board that is fresh posts
nothing, and the log says how old it is.

**Running it by hand.** From the Actions tab, or with
`gh workflow run stale-check.yml --repo AndrewGodlewsky/rising-repos-site`
and `-f <input>=<value>` for each input to change:

| Input | What it is | Default |
| --- | --- | --- |
| `address` | The page to read. Only an https address is taken: a host name in lower case, a port if any, and a path of letters, digits, and `. _ ~ / -`, in 200 characters at most | `https://risingrepos.com/` |
| `max_age_hours` | The age in hours from which the newest board is too old: a whole number from 0 to 168. 0 makes any board too old, which forces an alarm | `26` |

A scheduled run takes the defaults, from `DEFAULT_ADDRESS` and
`DEFAULT_MAX_AGE_HOURS` at the top of the workflow. An input it does not take
fails the run, and nothing is read or posted. So does an empty
`DISCORD_WEBHOOK_URL`, even while the board is fresh, so that a missing secret
fails the next daily run and is not found first on the day an alarm is due.
`DEFAULT_ADDRESS` and the input's default have been `https://risingrepos.com/`
since go-live
([RisingRepos#58](https://github.com/AndrewGodlewsky/RisingRepos/issues/58)).
Before it, both named the preview.

**What the job can reach, and what it reads.** Its token has no permission
(`permissions: {}`): it reads nothing from this repository. It holds one
secret, `DISCORD_WEBHOOK_URL`, in the environment of its one step, and no
deployment environment's secrets. No pull request starts it. It checks out
nothing and uses no action. All it runs is the script written in the workflow
file, with the runner image's own `python3 -I`. None of this repository's other
files, which the daily data push can change, is ever run beside the webhook.

The page is the one thing it reads, and the daily data push can change it, so
the script trusts nothing on it:

- It reads at most 4,000,000 bytes, over HTTPS only and through no proxy. A
  redirect to an address that is not https fails, and no file is opened.
- It takes the content of `rr:board-date` and `rr:published-at` only when the
  page carries each once, and uses a value only when it has the exact shape
  the data contract gives it: `YYYY-MM-DD`, and `YYYY-MM-DDTHH:MM:SSZ` in UTC,
  no more than ten minutes ahead of the runner's clock.
- A value that fails is reported as "states no usable board day", and is never
  repeated. Nothing read from the page reaches a shell, a command line, the
  log, or a file that GitHub reads back, and the message is made only of
  checked values.
- An error is named by its HTTP status or by the name of its type, never in
  its own words, which could repeat the webhook's address. The script never
  prints that address.

What the check cannot guard against: whoever can change the page can make it
state a fresh board. The check reports what the page states.

`tests/test_stale_check.py` reads the workflow for each of the above, and runs
the script as the job does against a stand-in for the site and a stand-in for
Discord. Both are HTTPS servers on 127.0.0.1, so the tests read no network
beyond the machine, with a made-up certificate that only the script under test
is told to trust. GitHub starts a scheduled or manual run only once the
workflow is on `main`, so the check's first real runs come after the change
that adds it is merged.

GitHub switches off the schedule of a public repository's workflow once the
repository has gone 60 days without activity. The data pushed here each day
counts as activity, so the schedule stays on.

## Changing a pinned version

Each download is checked before it is used, under the RisingRepos project's
rule: no known vulnerability on [osv.dev](https://osv.dev), and published at
least 14 days earlier.

- **Python packages.** Move `exclude-newer` in `pyproject.toml` forward, run
  `uv lock`, and check `uv.lock` with RisingRepos's
  `scripts/run_limits/check_downloads.py` before running `uv sync`. Lock with
  the uv version that `deploy.yml` names, so that the lock file's format is the
  one the build job reads. fastjsonschema is pinned to one version in
  `pyproject.toml`, because RisingRepos checks the same files with the same
  version, and the two move together.
- **wrangler.** In an empty folder, run
  `npm install --package-lock-only --ignore-scripts --before=<date> wrangler@<version>`,
  which writes a `package-lock.json` and installs nothing. Check that file the
  same way, then change the version and `--before` together in `deploy.yml`.
- **An action, uv, or Python.** Take a release at least 14 days old, look it
  up on osv.dev, and pin an action to the commit its release tag points at.
