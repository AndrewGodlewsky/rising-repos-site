# The site eval

**The question:** is the site's page fast, light, and accessible?

It measures the preview's pages with
[Lighthouse](https://github.com/GoogleChrome/lighthouse) from GitHub's runners,
so nothing runs on anyone's own machine, and it keeps the numbers. A test in
`tests/` answers pass or fail on every push. This eval answers with numbers
instead, because it needs the network and a deployed page.

| File | What it holds |
| --- | --- |
| `measure.py` | The code: it runs Lighthouse, takes the medians, judges them against the limits, and writes the summary and `results.json` |
| `limits.json` | The limit for each number on each profile, and the reason for it |
| `accepted.json` | The last accepted numbers, with the commit whose pages they measured, the run that measured them, and its date |
| [`.github/workflows/site-eval.yml`](../../.github/workflows/site-eval.yml) | The workflow that runs it |

## What it runs on, and when

| The workflow runs | It measures | Its summary says |
| --- | --- | --- |
| After each run of `Build and deploy` for a push to `main` that succeeded | Each page in `PAGES` in `measure.py` on the preview, <https://preview.risingrepos.pages.dev>. Today that is the first page, `/` | `Measured … after the deploy of <commit>` |
| By hand, for an https address | That one page | `… the address given by hand` |
| On a pull request that changes the workflow or this folder | The preview as it stands, with the pull request's code and limits | `Measured the preview as it stands` |

To start it by hand, open the workflow under Actions and choose **Run
workflow**, or run:

```sh
gh workflow run site-eval.yml --repo AndrewGodlewsky/rising-repos-site --ref main -f address=https://risingrepos.com/
```

The address must be `https://` with a host, written in the characters an address
may hold unescaped. Anything else is refused and nothing is measured. In the
job, `python evals/site/measure.py --out <folder>` runs the eval. It reads
Lighthouse's command, the address, and the deployed commit from its environment,
as its docstring says.

**After a deploy, how it knows what it measures.** A run that follows `Build and
deploy` measures the preview only while that run's commit is still the head of
`main`. The deploy job uploads only the head of `main`, so a successful run
whose commit is still the head uploaded its pages. A deploy that failed is not
measured at all. Each page must then state, in its `rr:board-date` and
`rr:published-at` tags, the newest board day in that commit's `site-data/`. The
eval reads the page up to ten times, fifteen seconds apart, before it gives up
and fails. If `main` moves on before the measurement starts, nothing is
measured, and the run that follows the newer deploy measures instead. If it
moves on during the measurement, the numbers are not judged. A newer deploy's
measurement cancels an older one that is still running.

## How it measures

Lighthouse **13.5.0** runs in Chrome from the runner image, on two profiles that
Lighthouse defines:

- **Phone**, its default: a mid-range phone with a CPU four times slower than
  the runner's, on a slow 4G connection (150 ms round trip, about 1.6 Mbit/s).
- **Desktop**, its `--preset=desktop`: a desktop on a wired connection (40 ms,
  about 10 Mbit/s).

The slow CPU and connection are simulated from one fast page load. Lighthouse's
documentation on variability says that simulating them removes much of the
variation a real network brings. Each page is measured five times on each
profile, one run after another, each in a new Chrome. Every number in the
summary is the median of the five, and the summary gives the lowest and highest
of the five beside it. The same documentation says the median of five runs is
about twice as stable as one run.

| Number | What it means | Better |
| --- | --- | --- |
| Performance score | Lighthouse's score out of 100, from five measures of the load, weighted | Higher |
| Accessibility score | The share of Lighthouse's accessibility checks (axe-core) that the page passes, weighted, out of 100 | Higher |
| Largest Contentful Paint | Seconds until the largest text block or image in view is painted. Google calls 2.5 s or less good | Lower |
| Cumulative Layout Shift | How much content in view moves after it is shown, in the load's largest burst of movement. Google calls 0.1 or less good | Lower |
| Total transfer size | The bytes of every request the load made, as they crossed the network: compressed | Lower |
| Requests | How many requests the load made | Lower |

A run that Lighthouse could not finish, or whose report lacks a number, fails
the eval and the summary says which run and why. What Lighthouse prints goes to
a log file in the run's artifact, never to the job's log, because GitHub reads a
log line that starts with `::` as a command.

Lighthouse sends nothing anywhere but to the page it measures: error reporting
is turned off.

## The pass mark

`limits.json` holds a limit for each number on each profile, and the reason for
each. A median outside its limit fails the job. The job reports and does not
gate anything: by the time it runs, the deploy has happened. The limits were set
from the first measurement, on 2026-11-12, by the agent that built this eval
([RisingRepos#74](https://github.com/AndrewGodlewsky/RisingRepos/issues/74)).
Whether the live address meets them is checked when the site goes live
([RisingRepos#58](https://github.com/AndrewGodlewsky/RisingRepos/issues/58)).

## Reading a run

Open the run under Actions. Its summary has a table for each page on each
profile:

| Column | What it shows |
| --- | --- |
| This run | The median of the five runs |
| Runs | The lowest and the highest of the five |
| Accepted | The median in `accepted.json`, for the same page and profile |
| Limit | `at least` for a score, `at most` for the rest |
| Result | `pass`, `**fail**`, or `no limit` |

Below the tables, each number that failed or could not be measured is listed,
and the same lines are on the run's page as errors. The artifact `site-eval`
keeps `results.json` and every report and log for 90 days. A report opens in the
[Lighthouse viewer](https://googlechrome.github.io/lighthouse/viewer/), which
shows why a score is what it is.

## Changing the accepted numbers or a limit

The page's numbers move for reasons that are not faults: the first page's design
changes, and the number of rows on a board day moves with the score and from day
to day. So the accepted numbers and the limits change, each in a pull request
that says why:

- **The accepted numbers.** Copy `results.json` from the run's `site-eval`
  artifact over `accepted.json`. A run that followed a deploy records its
  commit. A run on a pull request measured the preview as it stood, so fill in
  `commit` with the commit whose deploy the preview was serving, and say in the
  pull request how that was known. The pull request names the run, its commit,
  and its date, and the reviewers see the old and the new numbers in the diff.
- **A limit.** Change it in `limits.json` with its new reason. A limit is never
  moved only to make a failed run pass: either the page is fixed, or the pull
  request says why the new number is right for the page.

## Changing the pinned version of Lighthouse

Lighthouse's version and the date npm resolves its packages as of are in
`SITE_EVAL_LIGHTHOUSE` in the workflow, and change together. In an empty folder,
run

```sh
npm install --package-lock-only --ignore-scripts --before=<date> lighthouse@<version>
```

which writes a `package-lock.json` and installs nothing. Check that file with
RisingRepos's `scripts/run_limits/check_downloads.py`, as
[the main README](../../README.md#changing-a-pinned-version) says. On 2026-11-12, 13.6.0 failed the check:
its tree holds versions of `glob` and `minimatch` with known vulnerabilities,
which no version in that tree's ranges fixes. 13.5.0 with `--before=2026-10-29`
passed: 113 packages, none failed. Lighthouse needs Node 22.19 or later, and the
runner image's Node is newer.

## What it does not measure

- Real visitors. Every number is from a simulated load on GitHub's runner.
- Pages other than those in `PAGES`. A change that adds a page to the site adds
  it there.
- A pull request's own pages. They reach the preview only when it merges, so the
  run after its deploy is the first to measure them.
