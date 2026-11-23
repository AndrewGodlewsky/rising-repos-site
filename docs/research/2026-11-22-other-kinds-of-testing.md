# Other kinds of testing for the site, and evals of the agent workflow: what the primary sources say

**Date:** 22 November 2026.

The question is which kinds of testing, beyond those the project already knows, are worth having on a small static
site that agents change unattended, and what first-party sources say about evaluating an agentic coding workflow.
Every page linked was downloaded on 22 November 2026 and its text searched, so each quotation was checked against
its page; a quotation leaves out a README's markup characters. Nothing was installed and no test was run. Each
"Here" sentence is my reading of the sources against this repository, and section 4 is my inference.

## 1. Summary

1. Failure and time scenarios in the planned browser tests (E) test function that nothing on the known list reaches.
2. Property-based tests suit the wording functions and third-party text (A, B), and are deterministic in CI by default.
3. A type checker (C), actionlint and zizmor (D), and `node --check` (I) cost seconds and no model tokens.
4. `uv audit` exists as a preview feature and GitHub lists uv for Dependabot; pip-audit does not read `uv.lock` (G).
5. For evals of the workflow, Anthropic advises deterministic graders, tasks from real failures, and reading transcripts.

## 2. The candidates

What each tool needs, and what its own documentation says about Windows:

| Tool | Must be installed | Windows, per its documentation |
| --- | --- | --- |
| Hypothesis 6.170 | Python package `hypothesis` | "known to work and regularly tested on macOS, Windows, Linux, and Emscripten" ([compatibility](https://hypothesis.readthedocs.io/en/latest/compatibility.html)) |
| Big List of Naughty Strings | Nothing: a data file, `blns.json`, to copy | Not applicable |
| mypy 2.4.1 | Python package; "Mypy requires Python 3.10 or later to run." ([getting started](https://mypy.readthedocs.io/en/stable/getting_started.html)) | Not stated on the pages read |
| Pyright | Node. The PyPI package is community-maintained and "will automatically install node (which Pyright requires)" ([installation](https://github.com/microsoft/pyright/blob/main/docs/installation.md)) | Not stated on the pages read |
| ty 0.0.108 | Python package `ty`, or `uvx ty`, or a standalone installer that "does not require Python at all" ([README](https://github.com/astral-sh/ty/blob/main/README.md)) | Yes: a PowerShell installer ([installation](https://docs.astral.sh/ty/installation/)) |
| actionlint | Standalone binary; shellcheck and pyflakes are optional extras | Yes: Chocolatey, Scoop, winget, and binaries for "Windows (i386, x86_64, arm64)" ([install](https://github.com/rhysd/actionlint/blob/main/docs/install.md)) |
| zizmor | Standalone binary, also on PyPI (`pip install zizmor`, `uvx zizmor`) | Not named; wheels are "provided on a best-effort basis" ([installation](https://docs.zizmor.sh/installation/)) |
| Playwright for Python | Python package `playwright`, then `playwright install` for the browsers | "Windows 11+, Windows Server 2019+ or Windows Subsystem for Linux (WSL)." ([intro](https://playwright.dev/python/docs/intro)) |
| pip-audit | Python package `pip-audit` | Not stated in the README |
| `uv audit` | Nothing new: uv 0.11.6, installed here, answers `uv help audit` | uv already runs here |
| ESLint | Node package; "you must have Node.js (^20.19.0, ^22.13.0, or >=24) installed" ([getting started](https://eslint.org/docs/latest/use/getting-started)) | Not stated on the page read |
| Biome | Node package, or "the standalone installer, which does not require Node.js" ([getting started](https://biomejs.dev/guides/getting-started/)) | Yes: a PowerShell install line on the same page |
| djLint | Python package ("needs Python 3.11 or newer") or npm package ([getting started](https://djlint.com/docs/getting-started/)) | Named for the npm builds only: "Windows on x64, x86 and Arm64" |
| lychee | Standalone binary | Yes: "We provide binaries for Linux, macOS, and Windows for every release." ([README](https://github.com/lycheeverse/lychee/blob/master/README.md)) |
| LinkChecker | Python package; "Python 3.10 or later is needed." ([README](https://github.com/linkchecker/linkchecker/blob/master/README.rst)) | Not stated in the README |
| htmltest | Standalone binary | Yes: a Windows binary release ([README](https://github.com/wjdp/htmltest/blob/master/README.md)) |
| CSP Evaluator | Node package `csp_evaluator`, a library with no command-line program in its README | Not stated |
| HTTP Observatory | Node package, run as `npx @mdn/mdn-http-observatory <host>` | Not stated |
| Vale | Standalone binary | "Vale is cross-platform (Windows, macOS, and Linux)" ([docs](https://vale.sh/docs)) |
| codespell | Python package `codespell` | Not stated in the README |
| cspell | Node package; "CSpell needs Node 22 and above." ([README](https://github.com/streetsidesoftware/cspell/blob/main/packages/cspell/README.md)) | Not stated in the README |

### A. Property-based testing with Hypothesis

- **What it is.** "Hypothesis is the property-based testing library for Python. With Hypothesis, you write tests
  which should pass for all inputs in whatever range you describe, and let Hypothesis randomly choose which of those
  inputs to check - including edge cases you might not have thought about."
  ([index](https://hypothesis.readthedocs.io/en/latest/index.html)). A test is a method under `@given(st.integers())`.
- **Under `unittest`.** "unittest works out of the box with Hypothesis.", though "unittest.TestCase.subTest() is a
  no-op under Hypothesis" ([compatibility](https://hypothesis.readthedocs.io/en/latest/compatibility.html)).
- **Shrinking and replay.** A failing input is reduced before it is reported: "Examples from this strategy shrink
  towards shorter strings" ([strategies](https://hypothesis.readthedocs.io/en/latest/reference/strategies.html)).
  "When a test fails, Hypothesis automatically saves the failure so it can be replayed later.", under `.hypothesis/`,
  yet "If you want to ensure an input is run every time, use @example."
  ([replaying failures](https://hypothesis.readthedocs.io/en/latest/tutorial/replaying-failures.html)).
- **In CI, and cost.** "If the CI environment variable is set to any value, the ci profile is active by default." It
  sets `derandomize=True`, `deadline=None` and `database=None`, so "every run will test the same set of test cases
  until you update Hypothesis, Python, or the test function". Off CI, runs are random and "The default deadline is
  200 milliseconds." "The default max examples is 100.", so a property costs about a hundred calls of its body
  ([API](https://hypothesis.readthedocs.io/en/latest/reference/api.html)).
- **Here.** The functions that word numbers, dates and sentences get rules in place of examples (never raises, the
  noun agrees with the number), tried on inputs nobody listed. A failure found locally needs an `@example` to stay.

### B. Hostile and odd text through the generator

- **Hypothesis `text()`.** "The default alphabet strategy can generate the full unicode range but excludes surrogate
  characters because they are invalid in the UTF-8 encoding." (strategies page, above). The page names combining
  characters; null bytes and emoji lie inside that range, though it does not name them (my inference).
- **Big List of Naughty Strings.** "The Big List of Naughty Strings is an evolving list of strings which have a high
  probability of causing issues when used as user-input data. This is intended for use in helping both automated and
  manual QA testing" ([README](https://github.com/minimaxir/big-list-of-naughty-strings/blob/master/README.md)).
- **Here.** A test builds a page with such text in a row and holds what must stay true: the text appears escaped,
  the page parses, the script's hash still matches the policy. The list gives named cases; random text finds others.

### C. Static type checking

- **What it adds to a linter.** "Mypy will type check your code statically: this means that it will check for errors
  without ever running your code, just like a linter." It reads only what is annotated: "By default, mypy will not
  type check dynamically typed functions." ([getting started](https://mypy.readthedocs.io/en/stable/getting_started.html)).
- **Pyright**: "Pyright is a full-featured, standards-based static type checker for Python."
  ([README](https://github.com/microsoft/pyright/blob/main/README.md)). It runs on Node.
- **ty**: "An extremely fast Python type checker and language server, written in Rust." On maturity: "ty is currently
  in beta." and "ty does not yet have a stable API; breaking changes, including changes to diagnostics, may occur
  between any two versions." ([README](https://github.com/astral-sh/ty/blob/main/README.md)).
- **Here.** It catches a `None` or a string reaching a function that words a number, and a renamed field, on paths
  no test runs. Its worth follows how much of `sitebuild/` is annotated, which was not measured.

### D. Linting the workflows

- **actionlint**: "actionlint is a static checker for GitHub Actions workflow files." It lists a "Strong type check
  for ${{ }} expressions", "Security checks; script injection by untrusted inputs, hard-coded credentials", and
  "runner label validation, cron syntax validation". "Basically all you need to do is run the actionlint command in
  your repository." ([README](https://github.com/rhysd/actionlint/blob/main/README.md)).
- **zizmor**: "zizmor is a static analysis tool for your CI/CD. It can find and fix security issues in common CI/CD
  setups, including GitHub Actions, Dependabot, and pre-commit." ([home](https://docs.zizmor.sh/)). Its audits
  include `template-injection`, `excessive-permissions` and `unpinned-uses` ([audits](https://docs.zizmor.sh/audits/)).
- **Here.** The workflows deploy the site and hold its credentials, and no page test reads them. actionlint catches
  the workflow that would not run, zizmor the one that runs unsafely.

### E. Failure and time scenarios in Playwright for Python

- **Failing a request.** "You can abort requests using page.route() and route.abort()." A handler can pass, answer
  or fail a request: "route.fulfill() answers it without touching the network, and route.abort() fails it."
  ([network](https://playwright.dev/python/docs/network)). The pages read hold no example of delaying a request.
- **Offline.** `browser_context.set_offline(offline)`: "Whether to emulate network being offline for the browser
  context.", "Added before v1.9" ([BrowserContext](https://playwright.dev/python/docs/api/class-browsercontext)).
- **Time.** `page.clock.set_fixed_time(...)`: "Makes Date.now and new Date() return fixed fake time at all times,
  keeps all the timers running.", "Added in: v1.45" ([Clock](https://playwright.dev/python/docs/api/class-clock)).
- **Here.** All three are in the Python binding. They reach the two behaviours that depend on something outside the
  page: the notice computed from the reader's clock, and an opened row whose `history.json` fails to arrive.

### F. A few browser checks against the live site, on a schedule

- GitHub: "The schedule event can be delayed during periods of high loads of GitHub Actions workflow runs. High load
  times include the start of every hour. If the load is sufficiently high enough, some queued jobs may be dropped."
  "Scheduled workflows will only run on the default branch." "In a public repository, scheduled workflows are
  automatically disabled when no repository activity has occurred in 60 days."
  ([events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)).
- **Here.** The browser tests, pointed at the live address, check what only the host can break, such as the policy
  as served. The 60-day rule would switch the watcher off once the repository goes quiet (my inference).

### G. Auditing dependencies for known vulnerabilities

- **pip-audit**: "pip-audit is a tool for scanning Python environments for packages with known vulnerabilities." Of
  lock files: "At the moment, only pyproject.toml and pylock.*.toml are supported." Its README does not mention uv
  ([README](https://github.com/pypa/pip-audit/blob/main/README.md)); `uv export` can write a `pylock.toml`.
- **uv** has its own command: "Dependencies are audited for known vulnerabilities, as well as 'adverse' statuses such
  as deprecation and quarantine." and "Auditing requires network access and cannot be performed in offline mode."
  ([uv CLI](https://docs.astral.sh/uv/reference/cli/)). It is listed as the preview feature `audit-command`
  ([preview features](https://docs.astral.sh/uv/concepts/preview/)).
- **Dependabot**: its table has a row for uv, supported version "v0.11", with version updates and security updates
  both marked "Supported"; the page does not name `uv.lock` in words
  ([supported ecosystems](https://docs.github.com/en/code-security/dependabot/ecosystems-supported-by-dependabot/supported-ecosystems-and-repositories)).
- **Here.** This guards the build, not what the reader sees, and a new advisory fails a run that changed nothing.

### I to N, briefly

- **I. Plain JavaScript.** ESLint needs a Node package in the project; Biome has an installer that needs no Node.
  `node --check` needs nothing: "Syntax check the script without executing." ([Node CLI](https://nodejs.org/api/cli.html)).
  It finds a script that does not parse, and no logic error. `tests/test_old_board.py` already runs a script under Node.
- **J. Jinja templates.** "djLint reads HTML and the template syntax inside it, with profiles for Django, Jinja, Twig,
  Nunjucks, Handlebars, Liquid, Go templates and more." ([README](https://github.com/djlint/djLint/blob/master/README.md)).
  curlylint calls itself "Experimental HTML templates linting" ([README](https://github.com/thibaudcolas/curlylint/blob/main/README.md)).
  The build already uses `StrictUndefined` (`sitebuild/__init__.py`), so a misspelt name fails it without a linter.
- **K. Link checking.** "lychee is a fast, asynchronous link checker which detects broken URLs and mail addresses in
  local files and websites." htmltest checks "Whether internal links work / are valid." and "Whether internal hashes
  work." LinkChecker warns "The version in the Python Package Index may be old" (READMEs in the table). The internal
  links and anchors of `dist/` are worth holding; the links to repositories are slow and fail for outside reasons.
- **L. Other browsers.** "Playwright can run tests on Chromium, WebKit and Firefox browsers", after `playwright
  install webkit` or `firefox`; "These browsers will take a few hundred megabytes of disk space when installed". Both
  are Playwright's own builds ([browsers](https://playwright.dev/python/docs/browsers)).
- **M. The policy and the headers.** "CSP Evaluator allows developers and security experts to check if a Content
  Security Policy (CSP) serves as a strong mitigation against cross-site scripting attacks."; it is a library, so CI
  would need a small Node script ([README](https://github.com/google/csp-evaluator/blob/master/README.md)). "HTTP
  Observatory is a service that checks web sites for security-relevant headers.", has a command line, and scans a
  live host, so it fits after a deploy ([README](https://github.com/mdn/mdn-http-observatory/blob/main/README.md)).
- **N. Prose and spelling.** In Vale, "By default, spelling includes a custom, open-source dictionary for American
  English." ([spelling](https://vale.sh/docs/checks/spelling)), so British spelling needs a dictionary supplied.
  codespell "does not check for word membership in a complete dictionary, but instead looks for a set of common
  misspellings." ([README](https://github.com/codespell-project/codespell/blob/main/README.rst)). cspell can hold
  British spelling: `"language": "en-GB"` "tells cspell to use British English instead of US English"
  ([README](https://github.com/streetsidesoftware/cspell/blob/main/packages/cspell/README.md)).

## 3. Evals of the workflow itself

From Anthropic's [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) (9 January 2026), unless marked.

| Grader | Good at | Bad at |
| --- | --- | --- |
| Code-based | "Fast", "Cheap", "Objective", "Reproducible", "Easy to debug" | "Brittle to valid variations that don’t match expected patterns exactly", "Lacking in nuance" |
| Model-based | "Flexible", "Scalable", "Captures nuance", "Handles open-ended tasks" | "Non-deterministic", "More expensive than code", "Requires calibration with human graders for accuracy" |
| Human | "Gold standard quality", "Used to calibrate model-based graders" | "Expensive", "Slow" |

- **Which grader.** Code-based methods include "Binary tests (fail-to-pass, pass-to-pass)" and "Static analysis
  (lint, type, security)". "We recommend choosing deterministic graders where possible, LLM graders where necessary
  or for additional flexibility, and using human graders judiciously for additional validation."
- **Capability and regression.** Capability evals "should start at a low pass rate, targeting tasks the agent
  struggles with and giving teams a hill to climb." Regression evals "should have a nearly 100% pass rate.", and a
  capability eval that is passed can become "a regression suite that is run continuously to catch any drift".
- **Start small, from real failures.** "In reality, 20-50 simple tasks drawn from real failures is a great start."
- **Grade the outcome.** "grade what the agent produced, not the path it took".
- **Read transcripts.** "As a rule, we do not take eval scores at face value until someone digs into the details of
  the eval and reads some transcripts."
- **Metrics for coding agents.** The example tracks `n_turns`, `n_toolcalls` and `n_total_tokens`. "pass@k measures
  the likelihood that an agent gets at least one correct solution in k attempts."; "pass^k measures the probability
  that all k trials succeed."
- **OpenAI** agrees: "Log everything: Log as you develop so you can mine your logs for good eval cases."
  ([evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)).

**Here (my inference).** Running an eval means running the agent, which spends tokens; grading need not. The
token-free part is to keep, for each change the workflow delivers, the outcome figures CI already produces: whether
the tests passed on the first push, how many pushes it took, whether the Lighthouse run after the deploy passed, and
whether a later change had to repair it. A repaired change is the "real failure" to turn into a test.

## 4. The five most valuable additions (my inference)

Ranked for an owner who cares whether a feature broke something that worked more than how a page looks, dislikes
tight constraints, and wants checks that spend no model tokens.

1. **Failure and time scenarios in the browser tests (E).** They test the stale notice and the failed fetch, which
   no test of a built page can, and need nothing beyond the Playwright already planned.
2. **Property-based tests of the wording functions and of hostile text (A, B).** A property states what must always
   hold and fixes no value, so it is a loose constraint, and it tries inputs no agent thought to list.
3. **A type checker over `sitebuild/` (C).** It finds a wrong call on a path no test runs, in seconds. mypy is the
   settled choice; ty is quicker to adopt beside uv but calls itself beta.
4. **actionlint and zizmor on the workflows (D).** The workflows are the one part of the repository no test reads,
   and they deploy. Each tool is one binary and one command.
5. **A few browser checks of the live site after a deploy (F).** They reuse item 1's tests against what the host
   serves. Tie them to the deploy first; a schedule adds less, for the reasons GitHub gives.

Next would be `uv audit` on a schedule (G), `node --check` on the built script (I), and a link check of `dist/` (K).

## 5. Could not read, and not checked

**Could not read.** Hypothesis's glossary and its page on how many times a test runs: the two addresses tried
returned "not found" and an empty page. Pyright's documentation site was not fetched; its `docs/installation.md` was
read from the repository. GitHub's page of dependency graph ecosystems loaded, and a search of its text found
`poetry.lock` and no mention of uv, so whether Dependabot alerts, as distinct from updates, read `uv.lock` is open.
OpenAI's guide to agent evals and MDN's Observatory FAQ were downloaded and not read.

**Not checked.** No tool was installed or run, so every "Here" sentence is a reading of documentation, not a result.
Also open: whether mypy, Pyright, ty and Hypothesis support Python 3.14; how long a property takes on this code;
whether ruff checks any types (the note assumes not); whether the files in `sitebuild/templates/*.js` hold template
syntax, which decides whether `node --check` can read the source or only the built script; whether the policy is
sent as a header or written in the page; whether `uv audit` prints a preview warning when run; whether a scheduled
run counts as "repository activity"; whether a route handler can delay a request; and the upkeep of htmltest,
curlylint, LinkChecker and CSP Evaluator.

## 6. Checked again

A second reader, given only the claims and the addresses, read these again on their pages on 22 November 2026, and
the points this note left open about the repository were looked at in it.

**Held as quoted.** Playwright for Python: aborting a request, `set_offline`, and `set_fixed_time` with its version.
The network page shows no way to delay a request. Hypothesis: the `ci` profile and its three settings, the default
deadline and number of examples, that `unittest` works, that `subTest()` is a no-op "because it interacts poorly with
Hypothesis generating hundreds of inputs at a time", and that it is "supported and tested on CPython and PyPy 3.11+".
GitHub: both sentences on scheduled workflows. ty: that it is in beta, with no stable API. actionlint and zizmor:
what each is, and that zizmor "is available on PyPI". Anthropic: the five quotations on graders, on 20 to 50 tasks,
on grading what was produced, on the two pass rates, and on reading transcripts. mypy: both sentences.

**Looked at in the repository.**

- The files in `sitebuild/templates/*.js` do hold template syntax: `node --check` stops at the first character of
  `filters.js`. So a syntax check has to read the script as built. `tests/test_old_board.py` already fails when the
  built script throws under Node.
- The policy is written in each page, in `sitebuild/templates/page.html`, and is not sent as a header.
- 72 of the 75 functions in `sitebuild/` have every type written. mypy ran over `sitebuild/` on Python 3.14 in about
  five seconds, brought in for that run alone, and reported seven things: three for other packages whose types it
  could not find, and four where an annotation is looser than the code's use of it. None is a fault in what a page
  shows.
- `uv help audit` describes the command on uv 0.11.6. No audit was run.
- `tests/` calls `self.subTest` 105 times. That matters to A only inside a test Hypothesis runs.

**Corrected.** Sections 2 D and 4 say that no test reads the workflows. Three files of tests do:
`tests/test_workflow.py`, `tests/test_site_eval_workflow.py`, and `tests/test_stale_check.py` hold what this
repository decided each workflow must do. They are not a general audit of a workflow, which is what actionlint and
zizmor are.
