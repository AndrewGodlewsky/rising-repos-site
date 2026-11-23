# The Rising Repos site

The pages of risingrepos.com: one board a day of the GitHub repositories that
are gaining stars faster than their own pace predicts. RisingRepos, a separate
project, works out each board. This repository shows it.

These are the words this repository uses, in its pages, its code, its tests,
and its documents. Write an issue, a plan, a comment, or a name in them.
`tests/test_context.py` holds each term to a use somewhere in those files.

## Language

### What a board says

**Rising**:
Gaining stars faster than the repository's own baseline predicts, over the
last one or two days.
_Avoid_: trending (GitHub's own list), hot, spiking

**Board**:
One ranked list of the rising repositories for one board day. A board has
rows and holds nothing, or is empty, or is held, whether or not it still lists
rows of the other star bands.
_Avoid_: leaderboard, feed

**Board day**:
The day a board is for: the day whose star counts it ranks.
_Avoid_: date on its own (a board can be published days after its board day)

**Newest board**:
The board of the latest board day published, which the root shows. It can be
days old.
_Avoid_: today's board, current board

**Earlier board**:
Any board that is not the newest.
_Avoid_: old board (said of the newest once it has aged), archived board

**Old**:
Said of the newest board from 26 hours after its publish time.
_Avoid_: outdated, expired

**Row**:
One repository's line on a board.
_Avoid_: entry, item, card

**Rank**:
A row's place on its board, counted from 1 at the top. The data file gives
the order.
_Avoid_: score, position

**Score**:
The number RisingRepos's formula gives a repository for a board day: its
recent pace as a multiple of its baseline, or of the floor when its baseline
is under that. A board is ranked by it, highest first, and the site works out
none.
_Avoid_: rank, rating

**Baseline**:
A repository's own settled pace, in stars a day, which a rise is measured
against. A page words it as "its usual pace" and "its own trend". It is also
the name of the page that charts each repository on the newest board by it.
_Avoid_: average, trend line

**Recent pace**:
The stars a day a repository gained over the two days that end on the board
day, or over one of them when the loss rule left the other out.
_Avoid_: momentum, velocity

**Floor**:
The least a baseline counts as when a score divides by it: 1 star a day.
_Avoid_: minimum, clamp, star floor (the fewest stars a repository needs to
be followed at all, where the lowest star band starts)

**Excess**:
The stars a repository gained above its baseline over the recent days. A page
words it as "above its own trend".
_Avoid_: surplus, gain (every star gained, not only those above the baseline)

**Gain**:
The stars a repository gained over a run of days that ends on the board day.
A row carries its gain over 1, 7, and 30 days. It is 0 when it gained none,
below 0 for a loss, and not known when the day it is measured from has no
count.
_Avoid_: delta, change

**Loss**:
A gain below 0.
_Avoid_: drop, decline

**Loss rule**:
The formula's rule that takes a day on which a repository lost too many stars
to be believed as bad data, and leaves that day out of both paces. No gain is
ever left out.
_Avoid_: filter, outlier rule

**Star band**:
One of the ranges of star counts that group repositories of like size. Each
board day's file states them, and the site keeps no limits of its own.
_Avoid_: bucket, tier, size class

**Hold**:
Leaving a star band off a board because the board day's own snapshot missed
star counts in it, and saying so on the board. A board with a hold is held.
_Avoid_: hide, suppress, skip

**Unranked**:
Said of a repository that could not be ranked for a board day, because a day
its score needs is partial or missing. The file gives how many there were, and
not which. It is not a hold.
_Avoid_: held, dropped

**Snapshot**:
What RisingRepos recorded on one day: the star count of each repository it
follows.
_Avoid_: reading, sample

**Partial day**:
A day whose snapshot holds only part of the repositories RisingRepos follows.
_Avoid_: short day, degraded day

**Missing day**:
A day with no snapshot at all.
_Avoid_: hole

**Star history**:
A repository's star counts day by day, up to the board day. A day with no
count is a gap, never 0.
_Avoid_: trend, sparkline

**Formula version**:
The number of the formula that ranked a board: a whole number that goes up by
one when the formula changes.
_Avoid_: algorithm version, model

**Provisional ranking**:
A board's ranking while its data file says the score is provisional.
_Avoid_: beta, draft

**New**:
Said of a repository whose name was on none of the boards before this one. It
cannot be told on a board that follows one with a hold or with no rows.
_Avoid_: first-time, fresh, debut

### Getting a board onto the site

**Publish**:
RisingRepos making a board day visible on the site, by committing its data
file here.
_Avoid_: deploy (the upload of the pages), export, release

**Deploy**:
Uploading the built pages to risingrepos.com, which every push to `main`
causes. A publish ends in a deploy, and a deploy of a change to the pages
publishes no board day.
_Avoid_: publish, release

**Publish time**:
When a board day was first published. Publishing it again keeps it, so it says
how old the board is.
_Avoid_: build time, updated at

**Data contract**:
The files that carry board days from RisingRepos to the site, their schemas,
and the rule for changing them. RisingRepos owns it.
_Avoid_: API, feed, export format

**Daily job**:
RisingRepos's daily run, which ends in a publish. A page calls it "the day's
update".
_Avoid_: cron, pipeline

**Preview**:
The address that showed this site before it went live. Nothing is uploaded
there now.
_Avoid_: staging, beta

### Parts of a page

**Root**:
The page at `/`, which shows the newest board. It alone carries the data
contract's two tags, which state its board day and its publish time.
_Avoid_: home page, index, landing page

**History**:
The page that lists every board day, as month calendars.
_Avoid_: archive, calendar

**How it works**:
The page that says in plain sentences how a board is ranked.
_Avoid_: about, FAQ, methodology

**Site's bar**:
The bar at the top of every page: the mark and the name, the links to History,
Baseline, and How it works, and the theme switch.
_Avoid_: header, navbar

**Day bar**:
The bar under the site's bar that stays in view: the board day before, the
board's date, and the board day after.
_Avoid_: pager, date picker

**Notes above the rows**:
What changes how a board reads, said in words above its rows: an earlier
board, a provisional ranking, a hold, and unranked repositories.
_Avoid_: banner, alert, warning

**Filter**:
The controls over the rows, which show only once the script runs: All or New,
the star bands, the language, the order, and a search.
_Avoid_: toolbar, facets

**Opened row**:
A row opened on what lies behind its line: first its reason, and with the
script its sum, its facts, and the boards it was on.
_Avoid_: expanded row, detail panel, drawer, modal

**Reason**:
The line a row opens on, which says in figures why the repository is on the
board.
_Avoid_: explanation, tooltip

**Sum**:
The sentence in an opened row that shows the arithmetic behind its score.
_Avoid_: formula (the rule that ranks every row), breakdown

**About this board**:
A board's plain facts, under its rows: its count, its publish time, the day's
update, what New means on it, and the formula that ranked it.
_Avoid_: footer, metadata

**Colophon**:
The line at the foot of every page that says what the site is, and that it is
not affiliated with GitHub.
_Avoid_: footer, disclaimer

**Notice of an old board**:
What a page shows, by the reader's own clock, once the newest board is old.
_Avoid_: stale banner, warning

**Design note**:
The record of the site's one look, and of what each part of a page is, kept in
README.md.
_Avoid_: design system, style guide (the guide to what a new part reaches
for)

**Style guide**:
The guide to what a new part of a page reaches for first: the parts to start
from and the values in use, kept in STYLE.md. It guides, and does not bind.
_Avoid_: design note (the record of what each part is), design system, rules

### How a feature is made

**Idea**:
A change proposed for the site, as an issue here labelled `site-idea`. The
owner approves one, and only then is it built.
_Avoid_: ticket, task, request

**Feature workflow**:
The stages that take an approved idea from its issue to a feature live on
the site, with nobody driving each step: docs/workflow/README.md.
_Avoid_: pipeline, workflow on its own (a workflow is one of GitHub's, in
.github/workflows/)

**Run**:
One agent's pass through the feature workflow for one idea, from picking the
issue up to the look back.
_Avoid_: job (a job belongs to a workflow of GitHub's), session

**Owner's tests**:
The plain sentences about what a reader can do on the site and what the site
promises, each held by a test that drives the built site in a browser. A
feature may add to them and takes nothing from them.
_Avoid_: acceptance tests, end-to-end tests

**Agents' tests**:
Every other test: the ones that hold a page's exact markup and how each part
is built. An agent changes them as a feature needs.
_Avoid_: unit tests

**Check**:
The one command that runs everything a change has to pass: the lint, the
format, the guarded paths, and both kinds of tests.
_Avoid_: CI, pipeline

**Guarded path**:
A file that judges a feature, and that a feature therefore leaves alone: a
workflow, a limit, the standards, the owner's tests, the feature workflow's
own scripts.
_Avoid_: protected file, locked file

**Stop**:
A run handing its issue to the owner with a question, for one of the named
reasons, and going on to the next issue.
_Avoid_: block, failure, escalation

**Look back**:
The last stage of a run: a script digests the run's record, and a fresh
agent notes how the run could have cost less or done better.
_Avoid_: retrospective, post-mortem

### People

**Reader**:
Someone reading the site.
_Avoid_: user, customer

**Repository's owner**:
Whoever controls a repository on a board, and wrote its name, its description,
its language, and its licence.
_Avoid_: author, maintainer

**Owner-written text**:
What a repository's owner wrote, which the site does not trust: it is shown as
text, and never made a link.
_Avoid_: user content, untrusted input

### Watching the site

**Stale check**:
The check GitHub runs once a day, which reads the root and raises an alarm
when the newest board is old, the page cannot be fetched, or the page states
no usable board day.
_Avoid_: health check, monitor, watchdog

**Alarm**:
The message the stale check posts to Discord.
_Avoid_: alert, notification

**Site eval**:
The measurement of the live root after each deploy: six numbers on a phone
profile and on a desktop one, each held to a limit.
_Avoid_: benchmark, performance test, audit
