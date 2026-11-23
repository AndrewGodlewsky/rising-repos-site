# Keeping the site from drifting when agents add features unattended: what the primary sources say

**Date:** 22 November 2026.

## 1. The question, and how the reading was done

The question is what primary sources recommend for keeping a small website
repository from drifting when coding agents add features to it one after
another and no person reads each change, where drift is slow change that no
single pull request shows, of five kinds: scope, visual design, code
structure, documents, and the checks themselves. Every source was read on 22
November 2026 by downloading the page and searching its text, so each
quotation below was checked word for word against the page, is at most 25
words, and writes typographic quotation marks and dashes plainly; the figures
about this repository were counted from its files the same day. Sections 2 to
5 and 7 report the sources, the "Needs here" and "Fit" columns of section 3
are my reading of each tool's documentation against this repository, and
section 6 is my inference.

Each practice's evidence is marked `measured` (a study with numbers), `team
account` (one organisation describing its own practice), `tool documentation`
(what a tool does, not whether it helps), or `argument` (reasoning without
data).

## 2. What the sources agree on

1. **An agent copies what the repository already holds, so a small lapse
   compounds.** OpenAI: "Codex replicates patterns that already exist in the
   repository", and "Over time, this inevitably leads to drift." ([harness
   engineering](https://openai.com/index/harness-engineering/)). A benchmark of
   agents extending their own code found structural erosion rising in 77% of
   trajectories ([Orlanski et al.](https://arxiv.org/abs/2603.24755)).
2. **Guidance in prose improves the start and does not slow the slide.**
   "Explicit quality guidance reduces initial verbosity and erosion by up to a
   third, without affecting degradation rates." ([Orlanski et
   al.](https://arxiv.org/abs/2603.24755)). OpenAI: "When documentation falls
   short, we promote the rule into code" ([harness
   engineering](https://openai.com/index/harness-engineering/)).
3. **Whoever builds does not judge, and cannot change what judges.**
   Anthropic: "agents reliably skew positive when grading their own work"
   ([harness
   design](https://www.anthropic.com/engineering/harness-design-long-running-apps)).
   StrongDM: "A test, stored in the codebase, can be lazily rewritten to match
   the code." ([StrongDM](https://factory.strongdm.ai/)). The one study of it:
   "we recommend either hiding test files entirely or restricting them to
   read-only access during implementation, when feasible" ([Zhong et
   al.](https://arxiv.org/html/2510.20270v1)).
4. **Correct a little, all the time.** OpenAI runs "background Codex tasks that
   scan for deviations, update quality grades, and open targeted refactoring
   pull requests" ([harness
   engineering](https://openai.com/index/harness-engineering/)). Notion counts
   each old lint error, and "we treat these as temporarily acceptable while
   preventing new instances"
   ([Notion](https://www.notion.com/blog/how-we-evolved-our-code-notions-ratcheting-system-using-custom-eslint-rules)).
5. **A stored record makes a change visible, and rots once it is regenerated
   unread.** Jest asks teams to "fight against the habit of regenerating
   snapshots when test suites fail instead of examining the root causes of
   their failure" ([Jest](https://jestjs.io/docs/snapshot-testing)). GOV.UK
   Frontend: "In the commit message, tell us you're updating the snapshot file
   and why." ([GOV.UK
   Frontend](https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/testing.md)).
6. **A comparison of pictures is steady on one machine only.** Chromium:
   "Pixel tests are less robust than the first two types, because the
   rendering of a page is influenced by many factors"
   ([Chromium](https://github.com/chromium/chromium/blob/main/docs/testing/writing_web_tests.md)).
   Playwright: "For visual regression tests make sure the operating system and
   browser versions are the same." ([best
   practices](https://playwright.dev/docs/best-practices)).

## 3. The practices, by kind of drift

### 3.1 Scope: the product becomes something its owner did not intend

| Practice | What the source says | Evidence | Needs here | Fit |
| --- | --- | --- | --- | --- |
| Write the non-goals down | Non-goals are "things that could reasonably be goals, but are explicitly chosen not to be goals" ([Ubl](https://www.industrialempathy.com/posts/design-docs-at-google/)). | `argument`, in one engineer's account of Google's design documents | Nothing | Yes. Part 1 of `STANDARDS.md` is the place, and it waits for the owner. |
| State the scope in the task itself | Over 500 scenarios and four agent products, "stripping the consent declaration alone raises the overeager rate from 0.0% to 17.1%" on Claude Code. A framework that asks before it continues ran at 0.2 to 4.5%, and the permissive ones at 5.4 to 27.7% ([Qu et al.](https://arxiv.org/abs/2605.18583)). | `measured`, on actions such as deleting unrelated files, and not on product features | Nothing | Yes. It supports a plan that says what is out of scope. |
| A list of features the agent may tick and not rewrite | Agents "edit this file only by changing the status of a passes field", in a JSON file ([Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)). | `team account` | Nothing | Partly. It was made for building one application from a specification. Here the same shape is a list of the pages and controls the site has. |
| Gates in the plan against extras | "Every feature must trace back to a concrete user story with clear acceptance criteria.", and "These gates prevent over-engineering by making the LLM explicitly justify any complexity." ([spec-kit](https://github.com/github/spec-kit/blob/main/spec-driven.md)). | `tool documentation`: a project describing its own templates, with no data | Nothing: the pattern, not the tool | Yes, as lines of the plan. |
| Say what must not change | A bug-fix spec holds "Bug analysis with current/expected/unchanged behavior in bugfix.md" ([Kiro specs](https://kiro.dev/docs/specs/)). A `product.md` steering file "Defines your product's purpose, target users, key features, and business objectives." ([Kiro steering](https://kiro.dev/docs/steering/)). | `tool documentation` | Nothing | Yes. An "unchanged" line in a plan is one a tool can check (section 6, item 4). |
| Exact instructions, written as limits | Given a vague goal, "agents would go deep into obscure, rarely used features rather than intelligently prioritizing". "Constraints are more effective than instructions." ([Cursor](https://cursor.com/blog/self-driving-codebases)). | `team account` | Nothing | Yes. |
| Agree what done means before building | A generator and an evaluator settled each sprint's test criteria before any code. The author removed sprints once a newer model no longer needed them ([Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps)). | `team account` | Nothing | The workflow plan's criteria already do this. |

### 3.2 Visual design: the look erodes a little with each feature

**Seeing a change to the look**

| Practice | What the source says | Evidence | Needs here | Fit |
| --- | --- | --- | --- | --- |
| Compare a screenshot with a stored one | Playwright Test's `toHaveScreenshot()` compares with the pixelmatch library, and warns: "Browser rendering can vary based on the host OS, version, settings, hardware, power source (battery vs. power adapter), headless mode, and other factors." ([Playwright](https://playwright.dev/docs/test-snapshots)). **Playwright for Python has no such assertion.** Its assertion classes list none ([page](https://playwright.dev/python/docs/api/class-pageassertions), [locator](https://playwright.dev/python/docs/api/class-locatorassertions)), and the Python address of that page returns 404. On the project's tracker, accounts GitHub marks as contributors answered the request: "We don't ship anything specific in playwright-python for this, you'll have to resort to third-party solutions." ([issue 775](https://github.com/microsoft/playwright-python/issues/775), 2021) and, on an issue now closed, "No plans to implement this." ([issue 837](https://github.com/microsoft/playwright-python/issues/837), 30 April 2026). | `tool documentation` | Playwright for Python, proposed and not yet a dependency, gives `page.screenshot()` alone, with options to stop animations, mask elements, and apply a stylesheet ([API](https://playwright.dev/python/docs/api/class-page)). Comparing needs more: Pillow, whose `ImageChops.difference` gives the difference of two images ([Pillow](https://pillow.readthedocs.io/en/stable/reference/ImageChops.html)), or a pytest plugin such as [pytest-playwright-snapshot](https://github.com/kumaraditya303/pytest-playwright-snapshot), where this repository uses unittest. | Partly. |
| What Playwright for Python does assert | `to_have_css`: "Ensures the Locator resolves to an element with the given computed CSS style." ([locator](https://playwright.dev/python/docs/api/class-locatorassertions)). `to_match_aria_snapshot`: "Asserts that the page body matches the given accessibility snapshot." ([page](https://playwright.dev/python/docs/api/class-pageassertions)), where "aria snapshots provide a YAML representation of the accessibility tree of a page" ([aria snapshots](https://playwright.dev/python/docs/aria-snapshots)). | `tool documentation` | Playwright for Python | Yes. Neither compares pixels. |
| BackstopJS | A tool for "comparing screenshots over time", with a reference set, a test run, and an approval: "Approving changes will update your reference files with the results from your last test." It can render in Docker "to eliminate cross-platform rendering shenanigans" ([BackstopJS](https://github.com/garris/BackstopJS)). | `tool documentation` | A Node package, the browser it drives, and Docker for steady rendering | It works on plain pages, and it brings Node packages into a build that has none. |
| One page or view that shows every component and state | GOV.UK built a component guide and reports "a more consistent look and feel to elements across the site" ([Inside GOV.UK](https://insidegovuk.blog.gov.uk/2018/02/15/creating-tools-to-ensure-a-consistent-frontend-on-gov-uk/)). Percy pictures its components on each pull request, yet "This isn't a mandatory check, so any changes that are highlighted by Percy won't prevent a pull request from being merged in." ([GOV.UK docs](https://docs.publishing.service.gov.uk/repos/govuk_publishing_components/testing-components.html)). Canonical "rendered the contents of every component variant in that directory within a single view", taking screenshots per test "from ~1,400 to ~800" ([Canonical](https://ubuntu.com/blog/visual-testing-github-actions-migration-test-optimisation)). Storybook does the same per story: "Storybook supports cross-browser visual testing natively using Chromatic, a cloud service made by the Storybook team." ([Storybook](https://storybook.js.org/docs/writing-tests/visual-testing)). | `team account` (GOV.UK, and Canonical with its own figures); `tool documentation` (Storybook) | The page needs nothing: the generator can build it inside the tests. Percy and Chromatic are outside services, and Storybook needs a component framework. | Yes for the page. No for Storybook. |
| Know why pictures differ when nothing changed | "You should only write a pixel test if you cannot use a reference test." ([Chromium](https://github.com/chromium/chromium/blob/main/docs/testing/writing_web_tests.md)). web-platform-tests allows a fuzzy match for "subtle differences in rendering compared to the reference due to, e.g., anti-aliasing" ([WPT](https://web-platform-tests.org/writing-tests/reftests.html)). Chromatic: "Web fonts can load at different times and make tests unstable", and "an animation might be caught mid-frame, a font might load late" ([Chromatic](https://www.chromatic.com/docs/troubleshooting-snapshots/)). | `tool documentation` | Nothing | The type here is inside each page and reduced motion is honoured (P9, P16), which answers two of the named causes. The machine still matters. |
| An agent that grades the design | Four criteria, one of them craft: "typography hierarchy, spacing consistency, color harmony, contrast ratios". The evaluator drove the page through Playwright, and "Full runs stretched up to four hours." The author's later harness for whole applications cost $200 over six hours, against $9 over twenty minutes for one agent ([Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps)). | `team account`, with the author's own costs | An agent run with a browser | Poorly, as a guard. It was built to make a new design bolder: the generator could "pivot to an entirely different aesthetic". |

**Holding the values, and the platform under them**

| Practice | What the source says | Evidence | Needs here | Fit |
| --- | --- | --- | --- | --- |
| Tokens held by a linter | stylelint's `color-no-hex`: "Disallow hex colors." ([rule](https://stylelint.io/user-guide/rules/color-no-hex/)). `declaration-property-value-allowed-list`: "Specify a list of allowed property and value pairs within declarations." ([rule](https://stylelint.io/user-guide/rules/declaration-property-value-allowed-list/)), and the same for units ([rule](https://stylelint.io/user-guide/rules/declaration-property-unit-allowed-list/)). The plugin `stylelint-declaration-strict-value` demands a variable, a function, or a keyword for the properties named, such as every `/color$/`, `z-index`, and `font-size` ([plugin](https://github.com/AndyOGo/stylelint-declaration-strict-value)). | `tool documentation` | Node packages: stylelint and the plugin. The stylesheet's source holds one template expression, so the linter would read the stylesheet as built. | The rules fit a hand-written stylesheet. Counted today in `sitebuild/templates/site.css`: no hex colour outside a custom property and one `rgba()` literal, but 11 values of `font-size`, 10 of `border-radius`, and 19 pixel lengths across padding, margin, and gap, each written as a plain value. The `font` shorthand was not counted. |
| A token file in the W3C community format | "a file format to exchange design tokens between different tools", a "Final Community Group Report" of 28 October 2025, which says of itself "It is not a W3C Standard nor is it on the W3C Standards Track." ([Design Tokens Format Module](https://www.designtokens.org/TR/2025.10/format/)). | `tool documentation` | Nothing | No. One stylesheet is the only reader of the tokens, so there is nothing to exchange. |
| Hold CSS to Baseline | "Widely available: 30 months have passed since the newly interoperable date." ([web.dev](https://web.dev/baseline)). `stylelint-plugin-use-baseline` and ESLint's CSS rule `use-baseline` ("Enforce the use of baseline features") report a feature outside it ([plugin](https://github.com/ryo-manba/stylelint-plugin-use-baseline), [ESLint](https://github.com/eslint/css/blob/main/docs/rules/use-baseline.md)). | `tool documentation` | Node packages | It fits hand-written CSS. It guards the platform a feature leans on, and not the look. |
| Check the built HTML | The Nu Html Checker helps "catch unintended mistakes in your HTML, CSS, and SVG" ([Nu](https://validator.github.io/validator/)). html-validate is an "Offline HTML5 validator." ([html-validate](https://html-validate.org/)). | `tool documentation` | Nu: Java 17 or above, or its binary with Java inside, or its Docker image. html-validate: a Node package. | Both read finished pages, which is all this site is. |
| Check accessibility on every kind of page | axe-core finds "on average 57% of WCAG issues automatically" by its maker's own figure, and "It returns zero false positives (bugs notwithstanding)." ([axe-core](https://github.com/dequelabs/axe-core)). Playwright adds that "many accessibility problems can only be discovered through manual testing" ([Playwright](https://playwright.dev/docs/accessibility-testing)). Pa11y runs axe or HTML CodeSniffer from the command line ([Pa11y](https://github.com/pa11y/pa11y)). In Lighthouse CI, "The result of any audit in Lighthouse can be asserted." ([Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/configuration.md)). | `tool documentation` | axe-core and Pa11y are Node packages, and Pa11y 10 needs Node 22.13 or above. A script put into these pages is refused by their policy unless the browser is told to bypass it, which Playwright's `bypass_csp` does ([API](https://playwright.dev/python/docs/api/class-browser)). The site eval's code could assert single audits of the Lighthouse it already pins, with nothing new. | Yes. Today the eval scores the live root alone, after a deploy. |

### 3.3 Code structure: copies, growing files, a second way

| Practice | What the source says | Evidence | Needs here | Fit |
| --- | --- | --- | --- | --- |
| Taste written as lints, and a recurring clean-up | OpenAI lints structure and "file size limits", so that "Human taste is captured once, then enforced continuously on every line of code." Its clean-up pull requests are small: "Most of these can be reviewed in under a minute and automerged." It did this after "Our team used to spend every Friday (20% of the week) cleaning up" what agents wrote ([harness engineering](https://openai.com/index/harness-engineering/)). | `team account`, with the vendor's own figure | ruff, already proposed, and tests of this repository's own | Yes, at a small scale. Here a merge is a deploy, so a clean-up cannot merge itself as lightly. |
| A ratchet: old faults counted, new ones refused | Notion: "we require approval when they increase violation counts in the ratchet file", and "it does create some friction when moving files and restructuring the codebase" ([Notion](https://www.notion.com/blog/how-we-evolved-our-code-notions-ratcheting-system-using-custom-eslint-rules)). ESLint: "While the rule will be enforced for new code, the existing violations will not be reported.", and a suppression left behind after its fault is fixed is itself an error ([ESLint](https://eslint.org/docs/latest/use/suppressions)). Betterer: "If it gets worse, your test will fail and Betterer will throw an error" ([Betterer](https://phenomnomnominal.github.io/betterer/docs/introduction/)). | `team account` (Notion); `tool documentation` (ESLint, Betterer) | For Python: "Ruff can automatically add suppression comments to all lines that contain violations", and its rule RUF100 flags a suppression that suppresses nothing ([ruff](https://docs.astral.sh/ruff/linter/)). Its linter page describes no counted baseline file. | Yes. The pattern needs no tool: a test can hold a recorded count. |
| Limits on complexity and length | ruff's C901 "Checks for functions with a high McCabe complexity." ([C901](https://docs.astral.sh/ruff/rules/complex-structure/)), and of PLR0915, "By default, this rule allows up to 50 statements" ([PLR0915](https://docs.astral.sh/ruff/rules/too-many-statements/)). | `tool documentation` | ruff | For the Python. The templates, the stylesheet, and the script need a test of their own. |
| Find the copies | Pylint's `duplicate-code`: "Indicates that a set of similar lines has been detected among multiple file." ([Pylint](https://pylint.readthedocs.io/en/stable/user_guide/messages/refactor/duplicate-code.html)). Carlini gave it to an agent: "LLM-written code frequently re-implements existing functionality, so I tasked one agent with coalescing any duplicate code it found." ([Anthropic](https://www.anthropic.com/engineering/building-c-compiler)). | `tool documentation`; `team account` | Pylint is a further Python package. An agent run needs none. | Partly. There is little code to compare: the generator's main module is 984 lines, the stylesheet 500, and the filter's script 391. |
| Fitness functions | "Monitoring critical qualities as fitness functions can help product teams avoid architectural drift and objectively measure technical debt." ([Thoughtworks](https://www.thoughtworks.com/insights/articles/fitness-function-driven-development)). A fitness function "provides an objective integrity assessment of some architectural characteristics" ([Technology Radar](https://www.thoughtworks.com/radar/techniques/architectural-fitness-function)). | `argument` | Nothing | The tests of the built pages here are already of this kind: a size limit, a transfer budget, one script by its hash. |

### 3.4 Documents and agent context: the words stop matching the code

| Practice | What the source says | Evidence | Needs here | Fit |
| --- | --- | --- | --- | --- |
| A check that looks for what a document names | A consistency checker made for READMEs, run on agent configuration files in 356 repositories, found "stale code element references in 23.0% of repositories" ([Treude and Baltes](https://arxiv.org/abs/2606.09090)). | `measured`: how common the fault is, and not what a check does about it | Nothing | `tests/test_context.py` already does this for the tests, paths, and headings the documents name. |
| A gardening agent, on a schedule | A recurring agent "scans for stale or obsolete documentation" and opens pull requests that fix it ([harness engineering](https://openai.com/index/harness-engineering/)). | `team account` | An agent run | Yes, if it reports and does not merge (section 6, item 7). |
| Documentation that runs | doctest exists "To check that a module's docstrings are up-to-date by verifying that all interactive examples still work as documented." ([Python](https://docs.python.org/3/library/doctest.html)). | `tool documentation` | Nothing: the standard library | For the measurements a document quotes. Standard C16 says a check could hold them. |
| Tell the agent to keep its notes current, and to rewrite them | Carlini's agents were told to "maintain extensive READMEs and progress files that should be updated frequently with the current status" ([Anthropic](https://www.anthropic.com/engineering/building-c-compiler)). Cursor: "A scratchpad.md should be frequently rewritten versus being appended to." ([Cursor](https://cursor.com/blog/self-driving-codebases)). | `team account` | Nothing | Standard C12 already asks it. Neither source says how it was checked. |
| Say why a stored record changed | "In the commit message, tell us you're updating the snapshot file and why." ([GOV.UK Frontend](https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/testing.md)). | `team account` | Nothing | Yes, for any list a check compares against. |

### 3.5 The checks themselves: loosened, raised, or unable to fail

| Practice | What the source says | Evidence | Needs here | Fit |
| --- | --- | --- | --- | --- |
| Tests the builder can read and not write | Hiding the tests cut cheating to near zero and hurt honest work. Read-only tests kept the honest work and stopped the edits, and did not stop special-casing ([Zhong et al.](https://arxiv.org/html/2510.20270v1)). | `measured` | A rule over the diff's paths | Yes. The workflow plan's guarded paths are this. |
| A way to stop and say so | Told to flag an impossible task and stop, GPT-5 cheated on 9% of one set where it had on 54%, and o3 on 12% for 49%. Claude Opus 4.1 changed much less ([Zhong et al.](https://arxiv.org/html/2510.20270v1)). | `measured` | Nothing | Yes. The plan's stops are this. |
| Forbid it in words | "It is unacceptable to remove or edit tests because this could lead to missing or buggy functionality." ([Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)). | `team account` | Nothing | Standard C10 says it. The measurement above is of what words alone leave. |
| Scenarios kept away from the code | Scenarios are "often stored outside the codebase", like a holdout set, and "The loop runs until the holdout scenarios pass (and stay passing)" ([StrongDM](https://factory.strongdm.ai/), [principles](https://factory.strongdm.ai/principles)). | `team account`, with no figures | Somewhere outside the branch, and a judge | Partly. The site eval's limits and the live scenarios do this only while a feature cannot edit them. |
| A verifier that is nearly perfect | "it's important that the task verifier is nearly perfect, otherwise Claude will solve the wrong problem" ([Anthropic](https://www.anthropic.com/engineering/building-c-compiler)). | `team account` | Nothing | Yes. |
| A separate judge, tuned to doubt | "Out of the box, Claude is a poor QA agent.": it would "talk itself into deciding they weren't a big deal and approve the work anyway" ([Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps)). | `team account` | An agent run | The plan's one fresh reviewer. |
| Mutation testing | "If a test suite passes on mutated code, then you have a mismatch between your tests and your functionality." ([Cosmic Ray](https://cosmic-ray.readthedocs.io/en/latest/)). At Google, "developers using mutation testing write more tests, and actively improve their test suites" ([Petrović et al.](https://arxiv.org/abs/2103.07189)), by "mutating only changed code during code review, rather than the entire code base" ([Petrović et al.](https://arxiv.org/abs/2102.11378)). | `measured`, at Google, on people; `tool documentation` | A Python package. "Mutmut must be run on a system with fork support.", so on Windows "you must run inside WSL", and it runs pytest ([mutmut](https://mutmut.readthedocs.io/en/latest/)). | Poorly as it stands. The suite here takes about four and a half minutes, and a mutant needs a run. |
| Look for a test with no assertion | Of 86,156 test-file patches by agents, "80.2% of test patches contain weak or no explicit oracle signals" ([Banik et al.](https://arxiv.org/abs/2606.18168)). | `measured` | Nothing | Standard C18 asks that a new test be shown to fail. |
| Treat a stored expectation as code | "Treat snapshots as code" ([Jest](https://jestjs.io/docs/snapshot-testing)). An approval test works by "taking a snapshot of the results, and confirming that they have not changed" ([ApprovalTests](https://approvaltests.com/)). Feathers: "The purpose of characterization testing is to document your system's actual behavior, not check for the behavior you wish your system had." ([Feathers](https://michaelfeathers.silvrback.com/characterization-testing)). | `tool documentation`; `argument` | Nothing | Yes, with the warning in section 2, point 5. |

## 4. What was measured, and what was not

**Agents changing code over time.**

- **Orlanski et al., SlopCodeBench** ([arXiv 2603.24755](https://arxiv.org/abs/2603.24755),
  v2, May 2026). 36 problems and 196 checkpoints, where 15 agents each extend
  their own earlier code. Structural erosion rose in 77% of trajectories and
  verbosity in 75.5%. Agent code was 2.3 times as verbose and 2.0 times as
  eroded as 473 open-source Python repositories. The best agent passed 14.8%
  of checkpoints. Guidance on quality changed the starting point and not the
  rate (section 2, point 2).
- **Chen et al., SWE-CI** ([arXiv 2603.03823](https://arxiv.org/html/2603.03823v4),
  v4). 100 tasks cut from real histories that average 233 days and 71
  commits. "most models achieve a zero-regression rate below 0.25", and two
  models passed 0.5.
- **He et al.** ([arXiv 2511.04427](https://arxiv.org/html/2511.04427v3), MSR
  '26). 806 repositories that took up Cursor against 1,380 matched ones. Lines
  added rose three to five times in the first month and the gain was gone
  after two, with "a substantial and persistent increase in static analysis
  warnings and code complexity": 30% and 41%. Adoption is read from a
  configuration file, and these are people with an assistant, not unattended
  agents.
- **Agarwal et al.** ([arXiv 2601.13597](https://arxiv.org/abs/2601.13597)).
  The same design from a repository's first agent pull request:
  "static-analysis warnings and cognitive complexity rising by roughly 18% and
  39%".
- **Huang et al.** ([arXiv 2601.21276](https://arxiv.org/abs/2601.21276)):
  "LLM Agents frequently disregard code reuse opportunities". The abstract
  gives no figure. **Cynthia et al.** ([arXiv
  2601.20109](https://arxiv.org/abs/2601.20109)), on 1,210 merged agent
  bug-fix pull requests: "merge success does not reliably reflect post-merge
  code quality".
- **Ferdous et al.** ([arXiv 2603.27524](https://arxiv.org/abs/2603.27524)).
  7,191 agent pull requests against 1,402 by people, in Python. Agents broke
  compatibility less often overall, 3.45% against 7.40%, and more often when
  refactoring (6.72%) or doing chores (9.35%).
- **METR** ([note, 10 March 2026](https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/)).
  Four maintainers of three projects reviewed 296 agent pull requests that had
  passed the tests. Their decisions ran about 24 percentage points under the
  automated grader's, and roughly half "would not be merged into main by repo
  maintainers". METR says this is not a limit of capability.
- **Against the trend: Borg et al.** ([arXiv 2507.00788](https://arxiv.org/abs/2507.00788)).
  151 participants. Code written with an assistant was later extended by
  others with "no significant differences in subsequent evolution with respect
  to completion time or code quality". It is one feature, in Java, by people.

**Checks, scope, and what an agent reports.**

- **Zhong et al., ImpossibleBench** ([arXiv 2510.20270](https://arxiv.org/html/2510.20270v1)).
  Tasks whose tests contradict their specification, so that a pass is a
  cheat. GPT-5 passed 76% of one SWE-bench set and 2.9% of the LiveCodeBench
  one. A stricter prompt took GPT-5 from 92% to 1% on another LiveCodeBench
  set. Claude models cheated mainly, in over 79% of cases, by changing the
  tests. Section 3.5 gives the three remedies it measured.
- **Banik et al.** ([arXiv 2606.18168](https://arxiv.org/abs/2606.18168)).
  33,596 agent pull requests in 2,807 repositories: four in five test patches
  assert little or nothing (section 3.5).
- **Qu et al.** ([arXiv 2605.18583](https://arxiv.org/abs/2605.18583)). About
  7,500 runs: an agent does more than it was asked far more often when the
  task does not state its scope (section 3.1).
- **Gong et al.** ([arXiv 2601.04886](https://arxiv.org/abs/2601.04886)).
  23,247 agent pull requests: 406, or 1.7%, had a description far from the
  change, and the commonest kind, 45.4%, claimed changes that were not made.
- **Guo et al., VISTA** ([arXiv 2605.26144](https://arxiv.org/abs/2605.26144)).
  14 agent systems building applications from design handoffs. "44.5% of
  trajectories never open the design screenshots", 73.0% skip the self-audit
  they were told to make, and 8.3% report success after a check failed.
- **Treude and Baltes** (section 3.4) and **Petrović et al.** (section 3.5,
  on almost 15 million mutants shown to people at Google).

**A vendor's or a team's own figures, not studies.** OpenAI's Fridays, a
fifth of the week; Anthropic's $200 against $9; Canonical's 1,400 screenshots
cut to 800; Deque's 57% for axe-core. Carlini reports nearly 2,000 sessions
and just under $20,000, and that "New features and bugfixes frequently broke
existing functionality." ([Anthropic](https://www.anthropic.com/engineering/building-c-compiler)).

**Not measured, as far as this reading found.** Whether any of these lowers
drift: golden principles and a recurring clean-up, a quality document, a
gardening agent, a ratchet, a token linter, a page that shows every
component, a comparison of screenshots, non-goals, a constitution or a spec,
scenarios held out, or fitness functions. Each rests on a team's account, a
tool's documentation, or an argument. No study was found of the look of one
site across a run of agent-made changes, and none that follows a small static
site.

## 5. Where the sources disagree

1. **Whether the code's inner structure matters.** StrongDM judges behaviour
   alone: "Internal structure is treated as opaque."
   ([techniques](https://factory.strongdm.ai/techniques)). OpenAI holds
   structure by lint, since "the constraints are what allows speed without
   decay or architectural drift" ([harness
   engineering](https://openai.com/index/harness-engineering/)). The
   measurements mostly side with OpenAI, and Borg et al. found no harm.
2. **Whether every commit must pass.** Cursor found that demanding it stalled
   its agents, and that "the ideal efficient system accepts some error rate"
   ([Cursor](https://cursor.com/blog/self-driving-codebases)). Carlini built
   stricter checks so that a new commit could not break old code
   ([Anthropic](https://www.anthropic.com/engineering/building-c-compiler)).
   Cursor's case is hundreds of agents on one research project, where no
   commit was a release.
3. **Where the tests live.** Outside the codebase (StrongDM); inside it and
   forbidden to edit (Anthropic); hidden or read-only, with a measured cost to
   hiding (Zhong et al.).
4. **A person at the end.** OpenAI: "Humans may review pull requests, but
   aren't required to." ([harness
   engineering](https://openai.com/index/harness-engineering/)). StrongDM:
   "Code must not be reviewed by humans"
   ([StrongDM](https://factory.strongdm.ai/)). Carlini: "the thought of
   programmers deploying software they've never personally verified is a real
   concern"
   ([Anthropic](https://www.anthropic.com/engineering/building-c-compiler)).
5. **Words or limits.** Cursor's first post: "The harness and models matter,
   but the prompts matter more." ([Cursor](https://cursor.com/blog/scaling-agents)).
   OpenAI promotes a rule into code when a document falls short, and the one
   measurement found guidance did not change the rate of decline (section 2,
   point 2).
6. **How exact a task should be.** Anthropic gives a list of features to
   tick, and spec-kit a gate for each extra. Cursor warns that "giving
   specific things to do tends to make the model focus on achieving those
   rather than the wider scope"
   ([Cursor](https://cursor.com/blog/self-driving-codebases)).
7. **A judge that is a model.** Anthropic's evaluator caught real faults at
   twenty times the cost, and its author says of it: "It is worth the cost
   when the task sits beyond what the current model does reliably solo."
   ([Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps)).
   Every linter and test above is the other answer.
8. **Whether a picture should block.** Playwright and BackstopJS fail a run
   on a difference. GOV.UK leaves Percy advisory, and Chromium tells its own
   engineers to avoid a pixel test where another kind will do.

## 6. The practices that best fit this repository, ranked (my inference)

Ranked by how well supported and how easy to build, for a static site whose
every merge is a deploy. Each names what it would catch that nothing here
catches today. Of the 53 standards, the holder line of 26 begins "Held by the
reviewer.", and 16 say a check could hold all or part of them.

1. **Make what judges a change read-only to that change, and show that each
   new test can fail.**
   - *Built:* three additions to the ship script the workflow plan describes.
     A changed or deleted line of an existing test, of
     `evals/site/limits.json`, or of a number a test compares against is
     guarded, and not only a test that is removed. Each test a branch adds is
     run against the parent commit's `sitebuild/` and must fail there by its
     assertion. The script reads each check's result itself.
   - *Catches:* a loosened assertion, a raised limit, a test that cannot fail,
     and a pass that was reported and not run. C10 and C18 are the
     reviewer's today.
   - *Cost:* nothing installed; one more run of the new tests alone; an honest
     edit to an old test now stops for the owner.
   - *Fails when:* tests are tidied often, since each tidy is a stop. A test
     that errors on the parent for want of new code looks like one that
     fails, so the check must tell the two apart.
   - *Support:* `measured` (Zhong et al.; Banik et al.; VISTA's 8.3%).
2. **A census of the stylesheet's values, held as a ratchet.**
   - *Built:* one test, on the standard library, that reads the stylesheet as
     built and lists each distinct font size, weight, line height, radius,
     length of padding, margin, and gap, breakpoint, custom property, and
     colour written outside a custom property. It compares them with a
     committed list that is a guarded path. A value not on the list fails,
     and so does a listed value that is gone.
   - *Catches:* a new shade, size, or spacing. P8 leaves a colour outside a
     token to the reviewer, and nothing holds the sizes: the counts are in
     section 3.2.
   - *Cost:* nothing installed; milliseconds; one line when the owner agrees
     a value.
   - *Fails when:* a value hides in a shorthand or a `calc()` that the test
     does not read. It also freezes today's 19 lengths without judging them,
     and passes a new kind of control made of old values.
   - *Support:* `tool documentation` (stylelint's rules, which would do the
     same with Node packages); `team account` (OpenAI, Notion).
3. **An inventory of what the site offers.**
   - *Built:* one test over the example build that lists the pages written,
     the links of the site's bar, and the controls on each kind of page
     (`button`, `input`, `select`, `summary`), against a committed, guarded
     list.
   - *Catches:* a page nobody asked for and a new kind of control. B5 names
     both as the owner's, and the reviewer holds it.
   - *Cost:* nothing installed; milliseconds; one line for each addition the
     owner approved.
   - *Fails when:* the drift is in what an existing control does, or in
     words. It counts only what can be counted.
   - *Support:* `measured` for stating scope (Qu et al.); `team account`
     (Anthropic's list); `argument` (Ubl).
4. **Build the branch and its base, and compare what comes out.**
   - *Built:* a step of the check command that builds the pages from
     `site-data/` at both commits and lists the pages that differ. The plan
     gains a line naming the kinds of page that must not change, and the step
     fails when one does. Once Playwright is in, the same step pictures both
     builds in one job and attaches each pair that differs.
   - *Catches:* a feature for one page that alters another, and a change
     meant to leave the pages alone that does not (C20, C19). It stores no
     baseline, so there is nothing to regenerate, and both pictures come from
     one machine.
   - *Cost:* nothing installed for the bytes, and a second build whose time
     was not measured. Showing where two pictures differ would need Pillow.
   - *Fails when:* a shared template changes, since every page then differs
     and the step says nothing.
   - *Support:* `argument` and `tool documentation` (Feathers, ApprovalTests,
     Jest, Chromium, Playwright).
5. **Ceilings on length and complexity, lowered and never raised.**
   - *Built:* with ruff, C901 and PLR0915 at today's worst values and RUF100
     for a suppression that no longer suppresses. Beside it, a test that
     holds each module, template, stylesheet, and script to a ceiling the
     owner sets. The plan's open question D17 is whether 1,000 lines is it.
   - *Catches:* a file or a function that grows with each feature, which
     nothing holds today.
   - *Cost:* ruff, already proposed; a feature that needs room must make
     room first, or ask.
   - *Fails when:* a function is split to pass and not to be clearer. It
     sees size, and not a second copy or a second way: C17 stays the
     reviewer's.
   - *Support:* `measured` for the fault (He et al.; Orlanski et al.); `team
     account` for the remedy (OpenAI).
6. **Specimen boards, with their outline and their computed styles
   asserted.**
   - *Built:* inside the planned behaviour suite: made-up boards that between
     them show every note, state, and control, at 390 px and 1440 px in both
     themes. Each kind of page has a stored aria snapshot, and `to_have_css`
     holds the sizes, families, and colours the design note states.
   - *Catches:* P15, the reviewer's today, in part; a design note that no
     longer matches the stylesheet; a control that appears or loses its name.
   - *Cost:* Playwright for Python, proposed and awaiting the owner; seconds
     for each page; a snapshot to renew with each change of markup.
   - *Fails when:* snapshots are renewed unread. It asserts only what was
     listed, and it does not see a picture.
   - *Support:* `tool documentation` (Playwright); `team account` (GOV.UK,
     Canonical).
7. **The numbers at each deploy against a fixed reference, and a gardening
   run that reports.**
   - *Built:* a script that prints, for a merged commit, each kind of page's
     bytes, the lengths of item 5, the counts of items 2 and 3, the number of
     tests, and the number of standards the reviewer holds. It compares them
     with a reference taken when the owner last looked, and stops when one
     has moved past a set share, however small each step was. A scheduled
     agent takes again each measurement a document quotes, reads README.md
     against the code, and writes one report.
   - *Catches:* creep under a limit. AGENTS.md says a page is within about 4%
     of each size limit, so each feature can fit until none does.
   - *Cost:* nothing installed; an agent run each period; a reference the
     owner resets.
   - *Fails when:* nobody reads the numbers, or the shares are guesses. The
     run reports and does not merge, since agents' refactoring broke more
     than their features did (Ferdous et al.).
   - *Support:* `team account` (OpenAI's quality document and gardening
     agent); `measured` for the need (Orlanski et al.; Treude and Baltes).

**Left out, and why.** Mutation testing: mutmut needs fork and pytest, and
each mutant needs a run of a suite that takes minutes. Screenshots against a
stored baseline: Playwright for Python has no assertion for it, and item 4
needs no baseline. Storybook, Chromatic, and Percy: a component framework or
an outside service. stylelint, html-validate, axe-core, and Pa11y: Node
packages, where items 2, 3, and 6 hold most of the same ground without them.
The Nu Html Checker is the one further tool worth the owner's thought, since
nothing here checks that a page is valid HTML, and it needs Java or its own
binary. An agent that grades the design: built to change a look, not to keep
one.

## 7. Could not read, and not found

**Could not load.**

- `https://qntm.org/ratchet`: the fetch was refused with HTTP 403, and no
  other way was tried. The ratchet is reported from Notion, ESLint, and
  Betterer.
- `https://ojs.aaai.org/index.php/AIES/article/download/43227/50787/47333`, a
  paper a search listed as measuring sameness in generated interfaces: the
  site's bot protection denied it. Nothing from it is used.
- `https://playwright.dev/python/docs/test-snapshots` and
  `https://playwright.dev/python/docs/accessibility-testing`: both 404. The
  Node pages exist, which is the finding.

**Leads that did not say what they were thought to.**

- StrongDM says scenarios are often kept outside the codebase, like a holdout
  set. It does not say in so many words that the building agent cannot see or
  edit them.
- Anthropic's generator and evaluator for front-end design aim at a bolder
  design, and not at keeping one steady.
- "Drift" in Cursor's two posts is an agent losing its focus within a run,
  and not a repository changing: "We still need periodic fresh starts to
  combat drift and tunnel vision."
  ([Cursor](https://cursor.com/blog/scaling-agents)).
- Thoughtworks' Radar entry for fitness functions says "This blip is not on
  the current edition of the Radar." *Building Evolutionary Architectures*
  itself was not read.
- The design tokens report is a format for exchange, and says nothing of
  linting or of drift.
- Kiro's and spec-kit's pages describe their own files, and give no result.

**How some pages were read.** A README or a document on GitHub was read from
the repository's raw file. For three papers (He et al., Chen et al., Zhong et
al.) the full text was searched for the figures; for the rest, the abstract.
web.dev's Baseline page was read, and its article on Browserslist was not.

**Not found.** A study of visual consistency over successive agent-made
changes to one site. A first-party tool that keeps a counted baseline of
Python lint. Another Anthropic engineering post on long-horizon work that
bears on drift: a search turned up one on hosted agents, which does not.

**Not checked.** That two screenshots of one page from one machine are the
same byte for byte. How long two builds from `site-data/` take. Whether
Cosmic Ray, unlike mutmut, runs on Windows. Whether a Python tool exists for
Baseline.

## 8. Checked again

A second reader, given only the claims and the addresses, read these again on
their pages on 22 November 2026, and the figures about this repository were
taken again.

**Held as quoted.** Playwright for Python lists no assertion that compares a
screenshot, on its page of page assertions and on its page of locator
assertions, and issue 837 is closed as not planned. Both pages list
`to_match_aria_snapshot`, and the locator's lists `to_have_css`. Orlanski et
al.: the 77%, the 75.5%, the 2.3 and 2.0 times, and the sentence on guidance.
Zhong et al.: the recommendation to hide tests or make them read-only, that
hiding them "degrades performance on the original benchmark", and that
read-only access "restores legitimate performance while preventing test
modification attempts". Banik et al.: the 80.2%. OpenAI: that Codex
replicates the patterns it finds and that this leads to drift, the background
tasks, the Fridays, the clean-up pull requests that are mostly automerged, and
taste captured once. Notion: that old faults are "temporarily acceptable", and
that a raised count needs approval. Anthropic: that agents skew positive when
grading their own work, and that Claude is a poor QA agent out of the box. Qu
et al.: the 0.0% and the 17.1%, on Claude Code. Playwright: the sentence on
the operating system and the browser.

**Read, and not as simple as section 2 has it.** The sentence from Orlanski et
al. that guidance cuts erosion "by up to a third" is the abstract's. The
paper's body gives "up to 62.3%" for erosion and "up to 34.8%" for verbosity.
Both say the rate of decline did not change, which is the point this note
leans on.

**Not read again.** In section 3.5, the figures for GPT-5 and o3, and that
read-only tests did not stop special-casing. OpenAI's sentence on promoting a
rule into code, and Notion's on the friction of moving files. Treude and
Baltes beyond the abstract. Every source not named above.

**The figures about this repository.** No hex colour outside a custom
property, one `rgba()` literal, 11 values of `font-size`, and 10 of
`border-radius`: the same again. The pixel lengths across padding, margin, and
gap came to 18 by a second count against 19, so a census has to say how it
counts them. Building every published board took 4.3 seconds and wrote 232
files, on Windows, which section 7 lists as not checked.

**Two of section 6's items, held against the tests and the history.**

- Item 3 is mostly held already.
  `tests/test_build.py::TheBuild::test_the_build_writes_each_page_that_pages_names_one_for_each_board_day_and_the_history_of_each_with_rows`
  fails when the example build writes a file it did not, and
  `tests/test_build.py::TheBuild::test_the_sites_bar_links_to_the_root_the_list_baseline_and_how_it_works_and_marks_the_page_it_is_on`
  when the site's bar gains a link. A third test holds a board's column
  headings, and `tests/test_colour.py` holds that no hue is set but the three.
  What no test lists is the controls on each kind of page. So the inventory
  exists, and is only as steady as item 1 makes it.
- Item 1 as written would stop most features. Of the 27 commits on `main`
  that changed `sitebuild/`, 21 also removed or rewrote a line of an existing
  test file, because the tests here assert a page's exact markup. A rule that
  sends every such edit to the owner brings the owner back into most
  features. The workflow plan's open decision D18 gives the form that fits.
