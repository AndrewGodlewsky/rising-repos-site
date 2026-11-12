# rising-repos-site

The pages of [risingrepos.com](https://risingrepos.com), which lists the GitHub
repositories gaining stars faster than their own pace predicts. The RisingRepos
project works out which repositories those are and commits the data here. This
repository holds the pages: their templates, the generator that builds them,
and the workflow that uploads them to Cloudflare Pages.

## The rebuild and the preview

The site is being rebuilt, on this repository's `main`. Until it goes live, two
addresses serve two different sites:

| Address | Serves | Source |
| --- | --- | --- |
| <https://risingrepos.com> | The earlier site, from its Cloudflare deployment of 2026-10-16. No push to this repository changes it | The tag `legacy-site` |
| <https://preview.risingrepos.pages.dev> | The rebuilt site, uploaded on every push to `main` | `main` |

- Each push to `main` is uploaded to the Cloudflare Pages branch `preview`. The
  project's production branch is `main`, so the upload is a preview deployment.
- Every page built for the preview carries
  `<meta name="robots" content="noindex">`.
- Going live is one reviewed change, to the three workflows and to the site
  eval. In `.github/workflows/deploy.yml`, `PAGES_BRANCH: preview` becomes
  `PAGES_BRANCH: main`, and the same line drops the `noindex` tag. In
  `.github/workflows/stale-check.yml`, the address the check reads by default
  becomes `https://risingrepos.com/` (see "The stale check"). Without that
  part, the check would go on reading the preview, which no longer changes
  once boards are uploaded to production, and would post a false alarm every
  day. The site eval is pointed at the live address too: `PREVIEW` in
  `evals/site/measure.py`, with `evals/site/accepted.json` measured there, and
  the default `address` in `.github/workflows/site-eval.yml` (see "The site
  eval"). Otherwise the eval that follows each deploy waits for a board day the
  preview no longer shows, and fails.

## The first page

The site has one page so far: the latest daily board, as one ranked list. Each
row shows its rank, the repository's name linked to GitHub, its description,
its language, and its stars, in the order the data file gives them. The site
computes no score and no rank. The page states the board day and when it was
published, says so when the board is empty, and says the ranking is
provisional while the data file says the score is.

The build writes it as `index.html`, at the site's root, and writes `404.html`
beside it. Cloudflare Pages answers an address that holds no page with
`404.html` and the status 404. Without that file at the root, Pages takes the
site for a single-page app and answers every such address with the board and
the status 200. The not-found page states no board day.

What every page holds to, each checked by a test in `tests/`:

- **How it states its board day.** The board's `<head>` carries
  `<meta name="rr:board-date">` with the board day and
  `<meta name="rr:published-at">` with the file's `published_at`, once each,
  as the data contract says. The read-back after a publish and the checks of a
  stale site read them.
- **Owner-written text.** A repository's owner wrote its name, description, and
  language. Each is escaped where it is shown: Jinja2's autoescaping is on for
  every template, and no template marks a value as safe. None of them is made a
  link. A row's name links to `https://github.com/<full_name>`, and the data
  contract lets `full_name` hold only letters, digits, `-`, `_`, `.`, and one
  `/`.
- **No script.** The page carries none. Its Content-Security-Policy, in a
  `<meta>` tag, forbids every script and every request but the page itself.
- **Nothing from another site.** The page requests nothing from another
  address. Its type comes from the reader's own fonts, through font stacks, so
  no font file is fetched or committed. Its styles are in the page.
- **Its size.** A page, with its styles and scripts, stays within **320,000
  bytes**. Measured on 2026-11-12, without `--noindex`:

  | Board | The board's page | The not-found page |
  | --- | --- | --- |
  | The data contract's example, 5 rows | 9,953 bytes | 7,171 bytes |
  | 316 made-up rows, each description the longest the contract allows (350 characters) and holding characters that escaping lengthens | 265,010 bytes | 7,171 bytes |

  316 rows is the largest board the earlier site published. The limit was set
  from the largest page measured before
  [RisingRepos#71](https://github.com/AndrewGodlewsky/RisingRepos/issues/71)
  kept one design, 263,763 bytes, with a fifth more for what later slices add
  to a row, such as the stars gained that day. A row's markup is the same as it
  was then, so a longer board adds the same bytes per row. Compressed for
  transfer, the example's board page is about 3.5 KB.
  `tests/test_page_weight.py` holds the limit and builds the 316 rows.

### The design note

The site has one look. It was chosen in
[RisingRepos#71](https://github.com/AndrewGodlewsky/RisingRepos/issues/71),
from two designs built for this page, and the record of why is there. A ticket
that adds a page designs what it adds to this note, and a change to the look
changes this note in the same pull request.

**What the look is for.** People come back each day to see what is rising.
The page is quick to take in and easy to find one's way around, clean and
current, and pleasant to use. It has a character of its own rather than a
stock look, and it reads as made with care. Its affordances are plain: how a
thing on the page looks shows what it does, before anyone tries it. The look
was designed from nothing, and takes nothing from the earlier site.

**The idea.** The board is set like a record chart. A deep evergreen band at
the top carries the site's name and the board's date. Under it, each position
is set large beside its repository, below column headings that stay in view
while the list scrolls.

**Type.** Two roles, each in its own family, so that the two are plainly
different. No font file is fetched: each role is a stack of faces that
readers' systems already have, in `sitebuild/templates/site.css`.

| Role | What it sets | Stack | Where each named face is |
| --- | --- | --- | --- |
| Display: a DIN-style signage face | The site's name, the date, the ranks, the repository names, the star counts, a message's heading | `--display`: `Bahnschrift, "DIN Alternate", "Arial Narrow", "Nimbus Sans Narrow", "DejaVu Sans Condensed", sans-serif-condensed, sans-serif` | Bahnschrift: Windows 10 (version 1709 on) and 11. DIN Alternate: macOS and iOS. Arial Narrow: Microsoft Office on Windows, and macOS. Nimbus Sans Narrow: Linux, with Ghostscript's URW fonts (Debian's `fonts-urw-base35`, Fedora's `urw-base35-nimbus-sans-fonts`). DejaVu Sans Condensed: Linux (Fedora's `dejavu-sans-fonts`, Debian's `fonts-dejavu-extra`). `sans-serif-condensed`: Android's name for Roboto at its condensed width |
| The display role's cut for the date | The date, condensed | `--display-condensed`: the same stack with `"DIN Condensed"` in place of `"DIN Alternate"` | DIN Condensed: macOS and iOS. Bahnschrift narrows along its own width axis, under `font-stretch: condensed` |
| Text: the reader's own interface face | The descriptions, the owner, the language, the column headings, the band's sentences, the footer | `--text`: `system-ui`, then names for browsers older than it | `system-ui` is Segoe UI on Windows, San Francisco on Apple systems, and Roboto on Android |

Sizes, on a phone and then from 48rem (768 px) up: the date 2.25rem rising to
4rem; the ranks 1.75rem and 2.25rem, bold; the names 1.375rem and 1.625rem,
semibold; the star counts 1rem and 1.125rem, regular. The text is 1rem, with
the owner, the language, and the footer at 0.875rem and the column headings at
0.8125rem. The ranks and the star counts use tabular figures, so that their
digits line up down the column.

**Colour.** One idea: an evergreen field, white paper, and one green.

| Token | Value | Used for | Contrast |
| --- | --- | --- | --- |
| `--field` | `#0f3b2e` | The band, the theme colour, and the icon | |
| `--field-ink` | `#f2f7f4` | The site's name and the date, on the band | 11.50:1 on the band |
| `--field-muted` | `#b6cfc3` | The band's other text | 7.54:1 on the band |
| `--paper` | `#ffffff` | The page | |
| `--ink` | `#13201a` | The text and the star counts | 16.81:1 |
| `--muted` | `#50605a` | The owner, the language, the column headings, and the footer | 6.64:1 |
| `--green` | `#12704b` | The ranks, a link before it is visited, and the focus ring | 6.10:1 |
| `--visited` | `#551a8b` | A link once visited | 11.01:1, and 1.81:1 against `--green` |
| `--rule` | `#dae3de` | The line between rows | |

The contrast is against white unless the table says otherwise. The provisional
note on the band has a rule of `#7fcfa6` at its left. Every text colour meets
WCAG AA, 4.5:1, against its background, and `tests/test_colour.py` holds each
pair. On the paper, green marks the positions and the links, and nothing else.

**Spacing.** The content is at most 68rem wide, with 1rem at each side on a
phone and 2rem from 48rem up, which is the one breakpoint. A row has 1.125rem
above and below its content and a hairline between rows, and 0.375rem between
the name, the description, and the language. A description runs at most 35rem
wide, about 75 characters a line on a desktop. The band has 1rem above its
content and 1.25rem below. From 48rem up the site's line takes one line, and
the board's facts stand beside the date rather than under it, so that the band
stays short and the list starts high on the first screen.

**A row, in order of importance.**

1. The rank: the largest thing in the row, green, in the display face.
2. The repository's name: the link, large, in the display face.
3. The description, in the text face.
4. The total stars, at the right, in the display face at regular weight.
5. The owner, small and muted above the name and part of its link, and the
   language, small and muted under the description.

A row's position, name, and total stars line up on the name's baseline. The
owner is floated above the name, so the name's line is the first that sets the
cells' baseline.

**Links.**

| State | How it looks |
| --- | --- |
| At rest | Green, with a 2 px underline in the same green, offset 0.28em in the name's own size so that it clears the descenders |
| Visited | Violet, `#551a8b`, text and underline: the colour browsers give a visited link by default |
| Hover | The underline thickens to 3 px |
| Keyboard focus | A 2 px green ring, 4 px outside the link |

A repository's link holds the owner and the name, and only the name is
underlined. A browser lets a visited link change only its colours, so the
visited state is a change of colour. To see it in an automated browser, whose
fresh contexts record no visits, force the state on a link with the DevTools
protocol's `CSS.forcePseudoState` and `visited`.

**What a later page keeps.**

- The band at the top, with the site's line, and the page's title where the
  date is, in the display face. The band stays short: on a desktop, what the
  page is for starts on the first screen.
- The two roles in their families. No font file, and no third family.
- The colours in the table. A new text colour comes with a background that
  gives it 4.5:1, and a line in `tests/test_colour.py`.
- An underline means a link. A link looks like one before it is touched, and
  shows once it has been visited.
- Tabular figures for any number in a column.
- Column headings that stay in view, and a `scroll-padding-top` on the page
  that keeps a focused link clear of them.
- A page that reads at a phone's width (390 px) and a desktop's (1280 px), with
  five rows, with hundreds, and with none. The site does not follow the
  reader's dark mode yet.

The look is in `sitebuild/templates/site.css`, which
`sitebuild/templates/page.html` includes in every page. `page.html` also holds
the `<head>` and the band's first line. `board.html` and `not-found.html` fill
the rest of the band and the page below it. `PAGES` in `sitebuild/__init__.py`
lists each page the build writes, with its template.

## The data

The RisingRepos project defines the files a board day is published as, in its
data contract (`src/risingrepos/publishing/contract/README.md` there), and its
publish writes them here:

```text
site-data/
  boards/index.json                   every board day published, newest first
  boards/days/<board day>/daily.json  one board day's daily board
  contract/index.schema.json          the schemas the files follow, shipped
  contract/daily.schema.json          with them in the same commit
```

Until that publish writes its first board day
([RisingRepos#42](https://github.com/AndrewGodlewsky/RisingRepos/issues/42)),
`site-data/` holds the contract's example and schemas, copied byte for byte from
RisingRepos commit `03cce1680d211dad9adc229d0d13096b2473c47e`. The publish
replaces them.

The build reads the index and the latest board day, the first in the index, and
checks each against the schema shipped with it before it writes a page:

- A file that does not match its schema, or cannot be read, fails the build
  with a message that names the file, and no page is written.
- The pages need `schema_version` 1 or later, which `sitebuild/contract.py`
  states. A file below it fails the build.
- A field the pages do not read is ignored. RisingRepos adds a field to the
  schema and to the files in one publish, so the files still match.
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
A test holds the copy in `tests/fixtures/` to the bytes of the RisingRepos
commit above. A change to the contract reaches it, and that test, by a pull
request here.
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

**Two pushes close together.** Their builds run at the same time, and either
can finish first. Their uploads take turns, in the concurrency group
`cloudflare-pages-upload`, and just before it uploads, a run reads the head of
`main` with `git ls-remote`, which needs no credential because the repository
is public. If `main` has moved past the run's commit, the run uploads nothing
and says so in a notice in its log, and the newer push's run uploads its own
pages once its build passes. So the pages of an older push never replace those
of a newer one, whichever build finishes first. If the newer push's build
fails, neither push uploads, and the preview keeps the pages it had until a
push to `main` builds or the failed run is re-run. If `main` cannot be read,
the job fails and nothing is uploaded.

A pull request builds and does not deploy.

## Building locally

You need [uv](https://docs.astral.sh/uv/).

```sh
uv sync --locked                                     # the pinned dependencies, into .venv
uv run --locked python -m unittest discover -s tests # the tests
uv run --locked python -m sitebuild dist --noindex   # the pages, as the preview gets them
python -m http.server 8000 --bind 127.0.0.1 --directory dist  # then open http://127.0.0.1:8000/
```

The tests are the one command the workflow's build job runs too. They build
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

Each time a push to `main` reaches the preview,
`.github/workflows/site-eval.yml` runs Lighthouse on the first page, five times
on each of Lighthouse's phone and desktop profiles. It gives six numbers for
each: Lighthouse's performance score and accessibility score, the Largest
Contentful Paint, the Cumulative Layout Shift, the bytes the page took to
transfer, and the requests it made. It can also be started by hand for any https
address. [evals/site/README.md](evals/site/README.md) says how it measures, what
each number means, and how its limits were set.

**Reading the numbers.** A run's summary has a table for each page on each
profile. Each number is the median of the five runs, with the lowest and the
highest of them beside it, then the accepted number from
`evals/site/accepted.json` and the limit from `evals/site/limits.json`. A number
outside its limit, or one that could not be measured, fails the job and is
listed under the tables. A failed job holds nothing back: by the time it runs,
the pages are already on the preview.

**What a site change reports.** A pull request's own pages reach the preview
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
  preview as it stands.

## Layout

```text
sitebuild/          the generator: python -m sitebuild <folder> [--noindex] [--data <folder>]
  contract.py       reads the data files and checks each against its schema
  templates/        Jinja2 templates and the stylesheets they include, with autoescaping on for every one
site-data/          the data files RisingRepos publishes, and their schemas
evals/site/         the site eval, its limits, and its accepted numbers, which .github/workflows/site-eval.yml runs
tests/              the tests
  fixtures/         the data contract's example, which the tests build from
.github/workflows/  the workflows
  deploy.yml        the build job and the deploy job
  stale-check.yml   the daily check that the site is fresh
  site-eval.yml     the site eval
pyproject.toml      the dependencies, and the date uv resolves them as of
uv.lock             every package, pinned with its hashes
.python-version     3.14, for local builds. CI uses the exact version in deploy.yml
```

## The stale check

`.github/workflows/stale-check.yml` fetches the site's page once a day and
posts to Discord in three cases: the newest board has grown too old, the page
cannot be fetched, or the page gives no usable board day. Because GitHub runs
it, a stale site is still reported while the machine that publishes is
switched off. The age comes from the page's `rr:published-at`, the moment its
board day was first published (see "The first page"): the board counts as
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
| `address` | The page to read. Only an https address is taken: a host name in lower case, a port if any, and a path of letters, digits, and `. _ ~ / -`, in 200 characters at most | `https://preview.risingrepos.pages.dev/` |
| `max_age_hours` | The age in hours from which the newest board is too old: a whole number from 0 to 168. 0 makes any board too old, which forces an alarm | `26` |

A scheduled run takes the defaults, from `DEFAULT_ADDRESS` and
`DEFAULT_MAX_AGE_HOURS` at the top of the workflow. An input it does not take
fails the run, and nothing is read or posted. So does an empty
`DISCORD_WEBHOOK_URL`, even while the board is fresh, so that a missing secret
fails the next daily run and is not found first on the day an alarm is due.
At go-live
([RisingRepos#58](https://github.com/AndrewGodlewsky/RisingRepos/issues/58))
`DEFAULT_ADDRESS` and the input's default become `https://risingrepos.com/`.

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
