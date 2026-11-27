# The site eval

**What it asks:** does the site's first page load quickly, stay small, and pass
Lighthouse's accessibility checks?

It measures the live site's pages with
[Lighthouse](https://github.com/GoogleChrome/lighthouse) from GitHub's runners,
so nothing runs on anyone's own machine, and it keeps the numbers. A test in
`tests/` answers pass or fail on every push. This eval answers with numbers
instead, because it needs the network and a deployed page.

| File | What it holds |
| --- | --- |
| `measure.py` | The code: it runs Lighthouse, takes the medians, judges them against the limits, and writes the summary and `results.json` |
| `limits.json` | The limit for each number on each profile, and the reason for it |
| `accepted.json` | The numbers accepted most recently, with the commit whose pages they measured, the run that measured them, and its date |
| [`.github/workflows/site-eval.yml`](../../.github/workflows/site-eval.yml) | The workflow that runs it |

## What it runs on, and when

| The workflow runs | It measures | Its summary says |
| --- | --- | --- |
| After each run of `Build and deploy` for a push to `main` that succeeded | Each page in `PAGES` in `measure.py` on the live site, <https://risingrepos.com>, the address `DEPLOYED_SITE` in `measure.py` holds. Today that is the first page, `/` | `Measured … after the deploy of <commit>` |
| By hand, for an https address | That one page | `… the address given by hand` |
| On a pull request that changes the workflow or this folder | The live site as it stands, with the pull request's code and limits | `Measured the site as it stands` |

To start it by hand, open the workflow under Actions and choose **Run
workflow**, or run:

```sh
gh workflow run site-eval.yml --repo AndrewGodlewsky/rising-repos-site --ref main -f address=https://risingrepos.com/
```

The address must be `https://` with a host, written in the characters an address
may hold unescaped, apart from `'`, which is written `%27`. Anything else is
refused and nothing is measured. In the job,
`uv run --locked python -m evals.site.measure --out <folder>` runs the eval,
with the packages the build job installs from `uv.lock`. It reads
Lighthouse's command, the address, and the deployed commit from its environment,
as its docstring says.

**After a deploy, how it knows what it measures.** A run that follows `Build and
deploy` measures the site only while that run's commit is still the head of
`main`. The deploy job uploads only the head of `main`, so a successful run
whose commit is still the head uploaded its pages. A deploy that failed is not
measured at all. Each page must then state, in its `rr:board-date` and
`rr:published-at` tags, the newest board day in that commit's `site-data/`,
which the eval reads with `sitebuild/contract.py`, as the build does. The
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
about twice as stable as one run. An eval's first run is often its slowest,
while the runner is still busy, and the median sets it aside.

| Number | What it means | Better |
| --- | --- | --- |
| Performance score | Lighthouse's score out of 100, from five measures of the load, weighted | Higher |
| Accessibility score | The share of Lighthouse's accessibility checks (axe-core) that the page passes, weighted, out of 100 | Higher |
| Largest Contentful Paint | Seconds until the largest text block or image in view is painted. Google calls 2.5 s or less good | Lower |
| Cumulative Layout Shift | How much content in view moves after it is shown, in the load's largest burst of movement. Google calls 0.1 or less good | Lower |
| Total transfer size | The bytes of every request the load made, as they crossed the network: compressed | Lower |
| Requests | How many requests the page sent. One that the page's own content security policy refused is not counted, nor a `data:` address, whose bytes the page holds itself, and the summary says what it left out: see [Requests the page never sent](#requests-the-page-never-sent) | Lower |

A run that Lighthouse could not finish, or whose report lacks a number, fails
the eval and the summary says which run and why. What Lighthouse prints goes to
a log file in the run's artifact, never to the job's log, because GitHub reads a
log line that starts with `::` as a command.

Lighthouse sends nothing anywhere but to the page it measures: error reporting
is turned off.

**Why Lighthouse runs in the job.** Google's PageSpeed Insights runs Lighthouse
on Google's side, so the job would install nothing. On 2026-11-12 it refused a
request made without a key: such requests share a daily quota, and that quota
was zero. A key is a secret, and this job holds none. So Lighthouse runs in the
job, at a pinned version, in the Chrome that the runner image ships.

## Requests the page never sent

**What the host added at risingrepos.com.** Cloudflare serves the live site,
and until 26 November 2026 it put two scripts at the end of each page it handed
to a browser: the module script of its Web Analytics, from
`static.cloudflareinsights.com`, and an inline script for its bot check, which
would load more from `/cdn-cgi/challenge-platform/`. The built pages hold
neither, and every run on the preview counted one request, the page. The page's
content security policy, in its `<meta>` tag, lets only the page's own script
run, by its hash. So Chrome refused both: the inline script never ran, and the
module script was never fetched. On 26 November 2026 the owner turned both off
in the zone's settings, and since then the live pages are served exactly as
built. The owner's test of sentence 26 no longer passes over a refusal on the
live site, so a script the host puts back fails it (#146). The rule below stays,
for any request the policy refuses.

**What the first measurement there found.**
[Run 44019660473](https://github.com/AndrewGodlewsky/rising-repos-site/actions/runs/44019660473),
after the deploy of `0519dab` on 2026-11-17, failed on Requests alone: 2 on
both profiles, against a limit of 1. Each of its ten reports has two rows in
`network-requests`: the page, and the analytics script with status -1, no
protocol, and 0 bytes. Every other number was within its limit. Those reports
held the two categories and nothing else, so nothing in them said why the
script had no answer.

**Why the row alone does not settle it.** In Lighthouse 13.5.0 a request's row
keeps the values it starts with until an answer comes, and records no reason
when the request ends without one. A request the policy refused, and one that
failed on the network (a name that does not resolve, a connection refused or
reset), give the same row. The second kind was sent, and the page depends on
it.

**How the eval tells them apart.** Each run also asks Lighthouse for its
`inspector-issues` audit, which names each address that Chrome says the page's
content security policy blocked. The eval drops a row from Requests only if
each of these is true:

- that audit lists the row's exact address;
- the row has status -1, a transfer size of 0, and a resource size of 0;
- the address is an https address that the summary can print.

A failure on the network is never listed by the audit, and a request that broke
only a report-only policy was still sent, so its row has an answer: both count.
So does every other row, including one that lacks a field or holds one of an
unexpected kind. When the audit is missing, failed, or holds something else,
nothing is dropped. An audit asked for with `--only-audits` beside
`--only-categories` goes into the report and into neither category, so neither
score changes. Under each table the summary names every request it did not
count, in which runs, and for what reason. The reports in the artifact keep the
whole rows.

**The page's own type.** Since
[AndrewGodlewsky/RisingRepos#199](https://github.com/AndrewGodlewsky/RisingRepos/issues/199)
the site's four faces are inside each page, as `data:` addresses in its
stylesheet. Lighthouse lists each as a row of `network-requests`, with the
protocol `data` and the font's bytes as its transfer size, though no request
for it left the browser. Its own total transfer size leaves such addresses
out for that reason. So does the eval's Requests: it drops every row whose
address has the scheme `data`, and the summary counts them under each table.
A row that opens on a reader's click fetches its board day's `history.json`,
which a load that clicks nothing never asks for.

**What it found once it asked.**
[Run 44025134536](https://github.com/AndrewGodlewsky/rising-repos-site/actions/runs/44025134536),
on the pull request that brought in this rule, measured the live site on
2026-11-17. In all ten reports the audit listed the analytics script's exact
address, so Requests was 1 on both profiles, and the summary named the script
under each table. Its other numbers were close to those of the run before.

## The pass mark

`limits.json` holds a limit for each number on each profile, and the reason for
each. A median outside its limit fails the job. A failed job holds nothing back:
by the time it runs, the pages are already live. The limits were set from the
first measurement, of the preview on 2026-11-12, by the agent that built this
eval ([RisingRepos#74](https://github.com/AndrewGodlewsky/RisingRepos/issues/74)).
Since go-live the eval measures risingrepos.com against those same limits, and
[RisingRepos#58](https://github.com/AndrewGodlewsky/RisingRepos/issues/58)
records its first run there, which failed on its count of requests, as
[Requests the page never sent](#requests-the-page-never-sent) explains.
`accepted.json` still holds that measurement of the preview. Only its `base`
moved to the live address, together with `DEPLOYED_SITE`, which a test keeps it
equal to. [RisingRepos#113](https://github.com/AndrewGodlewsky/RisingRepos/issues/113)
replaces its numbers from a run on the live site.

## Reading a run

Open the run under Actions. Its summary has a table for each page on each
profile:

| Column | What it shows |
| --- | --- |
| This run | The median of the five runs |
| Runs | The lowest and the highest of the five |
| Accepted | The median in `accepted.json`, for the same page and profile |
| Limit | `at least` for a score, `at most` for the rest |
| Result | `pass` or `**fail**` |

Under a table, a list names each request that Requests did not count, with the
runs concerned and the reason. Below the tables, each number that failed or
could not be measured is listed, and the same lines are on the run's page as
errors. The artifact `site-eval` keeps `results.json` and every report and log
for 90 days. A report opens in the
[Lighthouse viewer](https://googlechrome.github.io/lighthouse/viewer/), which
shows why a score is what it is.

## Changing the accepted numbers or a limit

The page's numbers move for reasons that are not faults: the first page's design
changes, and the number of rows on a board day moves with the score and from day
to day. So the accepted numbers and the limits change, each in a pull request
that gives the reason:

- **The accepted numbers.** Copy `results.json` from the run's `site-eval`
  artifact over `accepted.json`. A run that followed a deploy records its
  commit. A run on a pull request measured the site as it stood, so fill in
  `commit` with the commit whose deploy the site was serving, and say in the
  pull request how that was known. The pull request names the run, its commit,
  and its date, and its diff sets the earlier numbers beside the new ones.
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
RisingRepos's `scripts/run_limits/check_downloads.py`, as [the main
README](../../README.md#changing-a-pinned-version) says. On 2026-11-12, 13.6.0
failed the check: its tree holds versions of `glob` and `minimatch` with known
vulnerabilities, which no version in that tree's ranges fixes. 13.5.0 with
`--before=2026-10-29` passed: 113 packages, none failed. Lighthouse needs Node
22.19 or later, and the runner image's Node is newer.

A new version can also change how `inspector-issues` writes its items, which
`_requests` in `measure.py` reads. If it does, the eval drops nothing from
Requests, and a request the page's policy refused fails the eval again, until
the code reads the new form.

## What it does not measure

- Real visitors. Every number is from a simulated load on GitHub's runner.
- Pages other than those in `PAGES`. A change that adds a page to the site adds
  it there.
- A pull request's own pages. They reach the site only when it merges, so the
  run after its deploy is the first to measure them.
