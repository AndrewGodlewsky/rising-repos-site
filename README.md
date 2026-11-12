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
- Going live is one reviewed change to `.github/workflows/deploy.yml`:
  `PAGES_BRANCH: preview` becomes `PAGES_BRANCH: main`. The same line drops the
  `noindex` tag.

## The first page

The site has one page so far: the latest daily board, as one ranked list. Each
row shows its rank, the repository's name linked to GitHub, its description,
its language, and its stars, in the order the data file gives them. The site
computes no score and no rank. The page states the board day and when it was
published, says so when the board is empty, and says the score is provisional
while the data file says it is.

It is built in two designs, each a whole first page on its own, until
[RisingRepos#71](https://github.com/AndrewGodlewsky/RisingRepos/issues/71) keeps
one:

| Design | On the preview |
| --- | --- |
| The register | <https://preview.risingrepos.pages.dev/> |
| The chart | <https://preview.risingrepos.pages.dev/chart/> |

What every page holds to, each checked by a test in `tests/`:

- **How it states its board day.** Its `<head>` carries
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

  | Board | The register | The chart |
  | --- | --- | --- |
  | The data contract's example, 5 rows | 7,885 bytes | 8,706 bytes |
  | 316 made-up rows, each description the longest the contract allows (350 characters) and holding characters that escaping lengthens | 256,722 bytes | 263,763 bytes |

  316 rows is the largest board the earlier site published. The limit is the
  largest page measured with a fifth more, for what later slices add to a row,
  such as the stars gained that day. Compressed for transfer, the example's
  pages are about 3 KB. `tests/test_page_weight.py` holds the limit and builds
  the 316 rows.

### The design note

The aims: a page that is easy to find one's way around, clean and current,
simple and pleasant to use, with a character of its own rather than a stock
look, and with clear affordances, so that a visitor can tell what each thing on
the page does by looking at it. The look was designed from nothing, and takes
nothing from the earlier site.

What both designs share: each name looks like a link before it is touched,
underlined in the link's own colour, and shows when it has been visited. Ranks
and star counts use tabular figures so that their digits line up. Every text
colour meets WCAG AA against its background. The page reads at a phone's width
(390 px) and a desktop's (1280 px), with five rows, with hundreds, and with an
empty board. Neither design follows the reader's dark mode yet.

| | The register | The chart |
| --- | --- | --- |
| The idea | A quiet reference list. The board's facts sit in a column of their own and stay in view on a desktop while the list scrolls | A record chart. The date is set large on a deep green band, and each position is set large beside its repository |
| Type | One geometric humanist family, from a font stack: Avenir Next where Apple systems have it, Corbel where Windows has it, otherwise the system's own | A condensed signage face for the date, the positions, the names, and the stars, from a font stack: Bahnschrift where Windows has it, DIN where Apple systems have it, otherwise a condensed sans. The text is in the system's interface face |
| Colour | Ink `#172033` and link blue `#2346c8` on white, with a cool tint `#eef2f7` behind the facts | Evergreen `#0f3b2e` behind the date, green `#12704b` for the positions and the names' underlines, on white |
| A row | A list item: the rank small in the margin, `owner/name` as one link, the description and the language under it, and the stars to the right | A table row under column headings that stay in view: the position large, the owner above the name, the description and the language under them, and the stars in their own column |

Each design is a template and a stylesheet of the same name in
`sitebuild/templates/`, and one line of `DESIGNS` in `sitebuild/__init__.py`.
The first design in `DESIGNS` is built at the site's root, and each other one
under `/<name>/`. Removing a design is deleting its template, its stylesheet,
and its line. What both designs share, the page's `<head>`, is
`sitebuild/templates/page.html`.

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
(see "The data"), write only to temporary folders, and read no network.
They include the search that RisingRepos's regression command makes, for a
file git would commit that holds a string shaped like a GitHub token or a
Discord webhook address: `tests/test_tokens.py` fails on one and names the
file, never the value.

The generator reads `site-data/`, or the folder given with `--data <folder>`.
It refuses an output folder that already holds files, so remove `dist` before
building again. The local server answers this machine only, and stops with
Ctrl+C.

## Layout

```text
sitebuild/          the generator: python -m sitebuild <folder> [--noindex] [--data <folder>]
  contract.py       reads the data files and checks each against its schema
  templates/        Jinja2 templates and the stylesheets they include, with autoescaping on for every one
site-data/          the data files RisingRepos publishes, and their schemas
tests/              the tests
  fixtures/         the data contract's example, which the tests build from
.github/workflows/  deploy.yml: the build job and the deploy job. stale-check.yml: the daily check that the site is fresh
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
