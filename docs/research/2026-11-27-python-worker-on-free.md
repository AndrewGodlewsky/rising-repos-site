# Can the query service run as a Python Worker on the free plan?

Issue #172. Researched on 26 November 2026 from Cloudflare's own documentation,
blog, and changelog. Nothing was installed and nothing was deployed. A fact
that no primary source confirms is marked "unconfirmed:".

## Short answer

A Python Worker is allowed on the Free plan and is generally available, but no
Cloudflare document says whether its start-up fits inside the Free plan's
10 ms of CPU for each request. Only a local trial can settle that. Until then,
a TypeScript Worker is the safe choice.

Pages Functions cannot be Python. Cloudflare's pages for them show JavaScript
only.

### Recommendation

1. Run the trial below before choosing. If a Python Worker serves a search
   across the full list within 10 ms of CPU, on a warm and on a cold isolate,
   build it in Python and keep one language.
2. If it does not, or the trial cannot be run, build a small TypeScript Worker
   and record in ADR 0003 that the query service is the one exception, and why.
3. Do not use Pages Functions for this. They add nothing a Worker lacks, and
   they cannot be Python.

### Pros and cons

| Choice | For | Against |
| --- | --- | --- |
| Python Worker | Keeps one language. Generally available. Memory snapshots are automatic. The generator's own search code could be reused. | The 10 ms fit is unmeasured. Runs on Pyodide (WebAssembly), so every request pays that interpreter's speed. Deploy needs `uv` and `pywrangler`, which are new to this repository. Cold start measured by Cloudflare at about one second for a small web stack. |
| TypeScript Worker | The most common Worker path. Native V8 speed. Plain `wrangler deploy`, which the repository already pins. | A second language, so ADR 0003 needs an exception. A second toolchain to test. |
| Pages Functions | Sits inside the existing Pages project and deploy. | JavaScript or TypeScript only. Share the same 100,000 requests a day. Advanced mode needs compiled JavaScript. Gains nothing over a Worker. |

## The facts, with sources

### Release stage and plans

- Python Workers are generally available. The blog post says "Today, Python
  Workers are now generally available (GA)", with a publication date of
  21 September 2026 (blog.cloudflare.com/python-workers-ga/). The changelog
  entry of 15 October 2026 repeats it: "Now that Python Workers are generally
  available" (developers.cloudflare.com/changelog/post/2026-10-15-phonellm-mini-workers-ai/).
- Plans: neither page states a plan restriction. The December 2025 post says
  "Our free tier offers 100,000 requests per day and 10ms CPU time per
  invocation" (blog.cloudflare.com/python-workers-advancements/). The Python
  overview page names only the `python_workers` compatibility flag as a
  requirement (developers.cloudflare.com/workers/languages/python/).
- unconfirmed: an explicit statement that Python Workers deploy on a Free
  account. The account's `python_workers: true` flag is not a test of it.

### Limits that apply

- Free plan: 10 ms of CPU time for each HTTP request, 128 MB of memory for each
  isolate, 1 second of start-up time, 50 subrequests, 64 MiB uncompressed
  bundle, 100,000 requests a day, 20,000 static files per Worker version at
  most 25 MiB each (developers.cloudflare.com/workers/platform/limits/ and
  /workers/platform/pricing/).
- CPU time "measures how long the CPU spends executing your Worker code", and
  waiting on `fetch()`, KV, or a database does not count (limits page).
- The limits page has no Python-specific entry.

### Start-up, memory snapshots, cold start

- At deploy time Cloudflare "executes the Worker entrypoint module and
  everything it imports at top level" and captures the WebAssembly memory. A
  request loads that snapshot "and use[s] it to bootstrap your Worker in an
  isolate" (developers.cloudflare.com/workers/languages/python/how-python-workers-work/).
- "Python Workers will automatically apply memory snapshots for free for every
  Python Worker." Cloudflare's benchmark of a Worker importing httpx, fastapi,
  and pydantic gave a mean cold start of 1.027 s, against about 10 s without
  snapshots (blog.cloudflare.com/python-workers-advancements/, a first-party
  benchmark).
- unconfirmed: how the snapshot load and the interpreter's start-up count
  against the 10 ms. The "how Python Workers work" page, the limits page, and
  the pricing page say nothing on it. A cold start of one second is wall time
  and may or may not be CPU time; no source separates them.
- Secondary and unofficial: a Cloudflare community thread reports occasional
  Free-plan CPU readings above 10 ms without an error. It is a user report,
  not documentation.

### Holding a 1.7 MB list

- Module-scope state is captured in the snapshot, since top-level code runs
  before it (how-python-workers-work page). That page does not itself say a
  loaded list is kept, and the examples page shows no module-level cache.
  unconfirmed: that a list built at import time survives into requests, and
  that a large object keeps the snapshot within limits.
- A Python Worker has only an in-memory filesystem that is lost when the
  isolate is destroyed (stdlib page).
- A bundled file can be read inside the handler with
  `Path(__file__).parent / "file.html"` (examples page).
- A static-assets binding is configured with `directory` and `binding =
  "ASSETS"`, and `env.ASSETS.fetch` returns an asset
  (developers.cloudflare.com/workers/static-assets/binding/). Asset requests
  are "free and unlimited" (static-assets billing page). unconfirmed: whether a
  fetch through the binding from a Worker counts as a subrequest, and whether `env.ASSETS` is reachable from a Python Worker; the
  Python basics page says only that `self.env` exposes bindings, and its
  example reads a variable.
- KV: 100,000 reads a day on Free (pricing page). KV reads do not count as CPU
  time. unconfirmed: the value size limit; this research did not fetch it.

### Pages Functions

- Functions "run on the Cloudflare network with Cloudflare Workers"
  (developers.cloudflare.com/pages/functions/). The get-started and routing
  pages show `.js` files only. Advanced mode needs a `_worker.js` in Module
  Worker syntax, and "We do not read `_worker.ts`"
  (developers.cloudflare.com/pages/functions/advanced-mode/).
- No Cloudflare page lists Python for Pages Functions. unconfirmed: that none
  can be, since the absence of a mention is not a statement.
- Functions requests are billed as Workers requests and share the
  100,000 requests a day (developers.cloudflare.com/pages/functions/pricing/).

### Putting a Worker on a path beside the Pages site

- A route is set in the Wrangler configuration as `{ "pattern":
  "example.com/api/*", "zone_name": "example.com" }`. The host needs a proxied
  DNS record. The only wildcard is `*`. The more specific pattern wins.
  The Free plan allows 1,000 routes for each zone
  (developers.cloudflare.com/workers/configuration/routing/routes/ and the
  limits page).
- The routes page says that when a route and a Custom Domain are both set on a
  hostname, the route takes precedence. unconfirmed: that this covers a Pages
  project's custom domain, since the page never mentions Pages and no Pages
  page was found on it. The trial of this step is a deploy, so it cannot be
  done offline.

### Deploying

- Python: `uv run pywrangler deploy`. Dependencies are bundled
  automatically (developers.cloudflare.com/workers/languages/python/ and
  /packages/). Pywrangler "calls out to `wrangler` when developing locally or
  deploying", needs `uv` and `npm`, and vendors packages into
  `python_modules` (blog.cloudflare.com/python-workers-advancements/).
  The packages page's example sets `requires-python = ">=3.13"`. Python 3.14
  is the default for a compatibility date of 2026-09-08 or later
  (developers.cloudflare.com/changelog/post/2026-09-08-python-workers-314/,
  as summarised by a search result; the post itself was not opened).
- A Worker with no packages: unconfirmed whether plain `wrangler deploy`
  suffices. No fetched page says it does, and the documentation always shows
  `pywrangler`.
- A changelog entry of 17 November 2026 says Python Workers with vendored
  packages "now deploy correctly" under the new `cf` command
  (developers.cloudflare.com/changelog/post/2026-11-17-release-candidate/), so
  this tooling is still moving.
- GitHub Actions: Cloudflare's page uses `cloudflare/wrangler-action@v4` with
  the secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, a token with
  the "Edit Cloudflare Workers" permission, and zone resources limited to what
  is needed (developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/).
  That page does not mention Python. A Python deploy step would also need
  `uv`, Node, and `uv run pywrangler deploy` in place of the action's plain
  deploy. Routes also need the token to reach the zone. The repository's
  workflow rules (STANDARDS.md, C6 to C8) govern the token and the pinned
  versions.

## What a local trial would measure

Nothing needs deploying for the first four.

1. Build a Python Worker with `uv run pywrangler dev` that loads the 1.7 MB
   list at import time and answers one search from a query string over all
   10,921 records.
2. Cold and warm time: start the dev server fresh, then send the same request
   twenty times, noting the first. Record wall time for each, with `curl -w
   '%{time_total}'`.
3. CPU time: run the Worker under `wrangler dev` with the Worker's log or
   `--inspector-port` and Chrome's profiler, or the CPU time the dev output
   reports where it does. Read the total for the first request and the median
   of later ones. The local runtime is workerd, the same engine, though not
   Cloudflare's machines, so treat the result as a guide and not a guarantee.
   Pass is under about 5 ms for a warm request and under 10 ms for the first.
4. Memory: note the process's resident memory with the list loaded against the
   128 MB limit. Unverified expectation: the Python objects for 10,921 records take more memory than the 1.7 MB file.
5. Whether the list survives: add a counter set at import time and returned in
   the reply. If it differs between requests the module state is not kept.
6. Where the list comes from: repeat steps 2 to 3 with the list read from a
   bundled file, from an `env.ASSETS.fetch`, and from KV (only a local
   simulation of KV is possible). Check each can be reached from Python.
7. Repeat the same search in a TypeScript Worker as the baseline.
8. Last, one real step: deploy an empty Python Worker and a route on a
   throwaway hostname in a scratch zone, to check the route beats the Pages
   custom domain and that Free accepts the deploy. This needs the owner's
   account and so is not part of this research.
