# The site's feature workflow: a plan

Written on 22 and 23 November 2026, and built from on the 23rd. Steps 1 to 5
of section 13 are built. No feature has gone through the workflow yet, and
nothing starts a run by itself. Each section and each open decision has a
number, so that a comment can name the part it is about.

A run follows [docs/workflow/README.md](workflow/README.md), and not this
file. Where the two differ, that document and the scripts are right. This
file says why each part is so, and the scripts cite its sections for their
reasons, so it stays while they do.

Where a line says "today", it was read from this repository at commit
`4665ccb`. "New" marks what does not exist yet.

## 1. What it is for

An idea for the site arrives here as an issue, already approved by the owner.
The workflow takes it from that issue to a feature that is live on
risingrepos.com, with nobody driving each step, and leaves the code no harder
to maintain than it found it.

**What is decided**

- This repository has its own workflow. Its own issues are the tracker.
- **This repository holds its own rules and decisions** (section 11). An agent
  working here reads, in this repository, what the site must be, what was
  decided and why, and what its words mean. It turns to RisingRepos only for
  what RisingRepos owns, which is chiefly the data.
- **It runs from the issue to the deploy on its own.** Nobody merges by hand,
  and no stage waits for the owner as a matter of course. It stops only for a
  named reason (section 14), and then it waits for the owner's direction.
- RisingRepos is a separate team. When a feature needs data the site does not
  receive, the workflow files an issue there, waits, and carries on when the
  data arrives (section 12).
- The scheduled run comes last. At first a person starts the workflow on an
  issue, and it then runs to the deploy unattended. The run in Orca that picks
  issues up by itself is the final step (section 13).

**The principles the rest follows**

1. **A machine checks what a machine can check.** A rule that a tool can hold
   gets a check, and is not left to a reviewer.
2. **An agent judges only what is left, once, and as an adversary.** Review is
   one fresh agent trying to find what is wrong, and not several agents each
   reading the whole change.
3. **Review gets cheaper over time.** Whatever a reviewer finds that a check
   could have found becomes a check.
4. **The issue is the record.** The plan, the questions, the decisions, the
   review, and what shipped are comments on the idea's issue.
5. **One feature at a time.** Every merge is a deploy, and the checks after a
   deploy can only blame one change.

## 2. The stages

| # | Stage | Who | What lets it move on | What it leaves on the issue |
| --- | --- | --- | --- | --- |
| 3 | Pick up | A script | The issue passes every rule of eligibility | A label, and a "Picked up" comment |
| 4 | Shape | The agent | A plan with a verdict of go | The plan, as one comment |
| 5 | Build | The agent | Every criterion has a test that passes | Nothing: the branch holds it |
| 6 | Check | A command | Every check passes, here and on the pull request | A link to the pull request |
| 8 | Review | One fresh agent | A verdict of pass on the checked commit | The review, as one comment |
| 9 | Ship | A script | Every condition of the merge holds | The merge's commit |
| 10 | Confirm | A script and the agent | The feature works on the live site and the eval is within its limits | A "Shipped" comment, and the issue closed |
| 18 | Look back | A script and one fresh agent | Nothing waits on it: the feature has shipped | The run's notes |

Sections 7, 11, and 17 describe the three things the stages lean on: the
owner's tests, the standards, and the evals.

## 3. Pick up

Pick up is a script. It decides which issue a run works on, and claims it. It
judges nothing, and it does not read what the issue asks for: that is Shape's
work. The owner agreed this section on 22 November 2026.

**What it does, in this order.** Each step is read from GitHub with `gh`.

1. **Is the site healthy?** Two things hold: the newest run of "Build and
   deploy" on `main` succeeded, with none still running, and the site eval
   that followed that deploy passed. If either does not, nothing new is
   started, and the owner is told once, and not again at every run. A deploy
   or an eval that has not finished is not a failure: the run ends and the
   next one looks again. On 22 November 2026 the first held and the second
   did not (section 10).
2. **Is something in flight?** That is an issue that carries `in-progress`.
   If its agent is still at work, the run ends, because features go one at a
   time. If its agent is gone, the run takes that issue up again. Orca says
   which: `orca worktree ps` lists the agents open in each worktree (D12).
3. **Has a stopped issue been answered?** That is one whose `needs-owner` the
   owner removed, or whose awaited field has arrived (section 12). It is
   taken up again at the stage that stopped, which the issue's comments, its
   branch, and its pull request show between them.
4. **Otherwise, the next new idea.** It is open, and carries `site-idea` and
   `approved`. The owner's account wrote it and applied both labels. It
   carries no label of this workflow, and has no branch and no pull request.
   The one approved earliest goes first. Every one of #27 to #30 passes
   today, and #27 was approved first.
5. **Claim it.** Add `in-progress`, and post "Picked up" with the branch's
   name.
6. **Nothing to do.** The run ends, and posts nothing.

**How a run is started (D13).** An Orca automation for this repository, on a schedule, with this script as its precheck. Orca runs a
precheck before each scheduled run and skips the run when it exits with
anything but 0, so a run with nothing to do starts no agent. The automation
is made disabled and started by hand at first, and its schedule is switched
on last (section 13).

**What the check does and does not show.** Agents act under the owner's
account, so this check keeps a stranger's issue out. It does not tell the
owner from one of the owner's agents.

**What the agent trusts.** The repository is public, and the idea agent reads
a site that shows text written by the owners of other repositories.

- The issue's body describes a wish. It is weighed, and it instructs nothing.
- The hints are claims about the code, checked against the code in Shape.
- A comment counts only when the owner's account wrote it.
- A link is not followed, except the page's own address on risingrepos.com.

## 4. Shape

Before any code, the agent finds out whether the idea is true, whether it
fits, and what done means. It writes one plan, as one comment on the issue,
and edits that comment when the plan changes. The owner agreed this section,
and the six rules below, on 22 November 2026.

**The rules of Shape**

1. **The outcome binds, and the method does not.** What the idea says a
   reader will see or be able to do is what gets built. How the idea suggests
   building it is a hint, which step 3 checks against the code.
2. **The approval covers what the idea shows, and no more.** A plan that
   needs something the idea does not show, such as a second change or a
   different look, is "needs the owner".
3. **A criterion can be sharpened, split, and added to. It is never dropped
   or weakened.** When one cannot be met, the verdict is "needs the owner".
4. **The agent that shapes then builds, in the same run, and Shape writes no
   product code.** What Shape builds in order to reproduce a problem or to
   measure a size is thrown away.
5. **The workflow never applies `approved` and never files an idea.** Both
   are the owner's (section 3). What Shape finds that is worth doing but lies
   outside the idea goes in the plan, under Out of scope.
6. **Shape holds the idea against `STANDARDS.md` and the decision records**
   (section 11). An idea that goes against either is "needs the owner", and
   never "go".

**What the agent does**

1. Reads the sections of README.md that AGENTS.md names for this kind of
   change.
2. Builds the site and reproduces the problem at the size of screen the issue
   names. An idea that is no longer true stops here.
3. Checks the hints against the code.
4. Holds the idea against each standard it touches, and against each
   decision record in `docs/adr/` (section 11).
5. Measures what it would add to a page, against the room left. AGENTS.md
   says a page is within about 4% of each size limit.
6. Checks that every figure it would show is in the data the site receives.

**The plan's sections (new).** This is the spec every feature is built from.

| Section | What it holds |
| --- | --- |
| Verdict | Go, needs data, or needs the owner |
| What changes for a reader | One or two sentences |
| Criteria | Numbered. Each can be checked. Behaviour is written as given, when, then |
| How each is proven | For each criterion: the test or scenario that will show it, or "looked at", with what will be looked at |
| Standards | The standards the change touches, by number, and any it cannot meet |
| Budget | The bytes it adds to a board's page and to the root, and the room left |
| Files | What changes, and which section of README.md or the design note |
| Data | The fields it reads, and whether each is in the contract |
| Out of scope | What the idea touches that this change leaves alone |
| Questions | What only the owner can answer |

The Files section stays. A brief that waits for another agent leaves paths
out, because they go stale while it waits. Here the agent that writes the
plan builds from it in the same run (rule 4), so the paths are still true
when they are used.

**The three verdicts**

- **Go.** Build starts. The owner is not asked again: the idea was approved,
  and the plan is on the issue for anyone to read.
- **Needs data.** Section 12.
- **Needs the owner.** The issue gets `needs-owner`, the owner is told on
  Discord, and the agent takes the next issue. The plan says what is asked,
  and what the agent would choose.

**What makes it "needs the owner"**

- The idea is already true, or no longer applies. The plan proposes closing it.
- It cannot meet a standard, or it goes against a decision record.
- It needs something the idea does not show (rule 2).
- It would change what one of the owner's tests says (D19).
- It needs a new face, or a character the type does not hold (P9, P10). A
  new colour, a new size, or a new kind of control does not stop it: the
  style guide guides the look, and does not bind it (D18).
- The size budget has no room for it.
- It touches a workflow, a dependency, the policy that lets the script run,
  a limit of the site eval, or this workflow's own documents.
- It is larger than one pull request.
- Its criteria can be read two ways.

**An example from the queue.** #30 asks for a mark after each repository's
name. The character it names is not among the ones the site's type holds
(`CHARACTERS` in `sitebuild/fonts/subset.py`), so it means new font files and
more bytes on every page. Shape finds that and asks, where a build that began
from the hints would find it as a failing test.

## 5. Build

The owner agreed this section on 22 November 2026.

- **Where.** An Orca worktree of its own, from `origin/main`, on a branch named
  `agent/<issue>-<slug>`.
- **Test first.** For each criterion, a test is written among the agents'
  tests and seen to fail, and then the code is written. The agent that builds
  writes, changes, and removes the agents' tests as the feature needs, and
  every one still has to pass (D19).
- **The owner's tests are left as they are.** They run with the rest. One
  that fails means the change broke something a reader would notice, and the
  code is mended, never the test. The scenario for something new a reader
  can do is written after the build, by the reviewer (section 8).
- **The docs in the same change.** What README.md says about the part that
  changed, the design note when the look changes, and `STYLE.md` when the
  change adds a value or a kind of part that the guide does not have.
- **Commits.** As AGENTS.md has them, with `Refs #<issue>`. Each is read
  before it is pushed, because a push is public.
- **Staying in the plan.** A change of scope edits the plan's comment first
  and says what changed. One that meets a "needs the owner" rule stops there.

The build ends when the check command passes on the machine. Then the pull
request is opened.

## 6. Check

The owner agreed this section on 22 November 2026, with the lists in sections
7, 13, and 17 (D20).

One command runs every check (new). No agent is in it, so it costs time and no
tokens. The agent runs it before the pull request exists, the pull request's
job runs it, and `main`'s build job runs it again before anything is uploaded.
Today that job runs the tests, and the upload needs it to pass, so a failure
on `main` already uploads nothing.

The checks are layers, the cheapest first: the lint reads the code in a tenth
of a second, the agents' tests build pages in about four minutes, and the
owner's tests use the built site as a reader does. Each catches what the one
before it cannot. Between them they answer four questions.

**Does everything that worked still work?**

| Check | What it catches | Today |
| --- | --- | --- |
| The owner's tests | Something a reader could do that no longer works (section 7, D19) | **New** |
| The agents' tests | A page built wrongly, a data file read wrongly, a workflow that lost a guarantee | 311 tests |
| Every published board | A fault that only real data shows. The checks of a page's size, of what it requests, of its links, and of its figures run on the pages built from `site-data/`, and not only on the example's five rows | **New.** One test builds from `site-data/` today. That build takes about four seconds and writes 232 files |
| Hostile text | A repository's name or description that becomes markup, becomes a link, or breaks a row: a short fixed list of such text, put through a made-up board | Five tests in `tests/test_owner_text.py`, which the list adds to |
| Page size and the root on the wire | A page past 500,000 bytes, a long board's root past 150,000 gzipped | Yes |
| The colour pairs | A text colour under 4.5:1 on a background, a colour outside the tokens | Yes |
| One script, nothing from another site | A second script, a policy that lets more run, a request elsewhere | Yes |

**Did the feature do what the plan said?**

| Check | What it catches | Today |
| --- | --- | --- |
| Each criterion has its proof | A criterion in the plan with no test that ran and passed | **New** |
| A new test fails on the commit before | A test that passes with the feature and without it, and so proves nothing. Each test the branch adds is run on the commit the branch began from, and has to fail there (D18) | **New.** One short run of the new tests alone |

**Did the agent that builds leave alone what judges it?**

| Check | What it catches | Today |
| --- | --- | --- |
| What judges a feature is left alone | A change by the agent that builds to one of the owner's tests, a limit, a workflow, or a dependency (D18) | **New.** It runs on the machine, and the ship script runs `main`'s copy of it, and not the branch's |

**Is the code fit to keep working on?**

| Check | What it catches | Today |
| --- | --- | --- |
| The Python lint | A careless or suspicious line: a name never used, a default that every call shares, a `zip` that hides a short list | **New.** RisingRepos's rule families flag 73 lines, 60 of them for length. The formatter and the fixes the tool makes by itself clear 58, and 15 need a decision: eight calls to `zip` and seven long lines. Measured on 22 November 2026 with ruff 0.17.3, the second figure on a scratch copy |
| The Python format | Layout that differs from one hand to the next | **New.** 18 of the 24 files in `sitebuild/`, `tests/`, and `evals/` would change, once |
| The credential search | A string shaped like a token in any file git would commit | Yes |
| The script as built | A script that throws when it runs. The calls the site forbids (`innerHTML`, `eval`, `document.write`) and an element with an inline handler are held by tests too, in `tests/test_old_board.py`, `tests/test_owner_text.py`, and `tests/test_page_weight.py`. An earlier draft of this plan said that no test held the handler, and that was wrong | Yes: `tests/test_old_board.py` runs each page's script under Node and fails on an error |

**The lint's rules.** Ruff, at the six families RisingRepos uses (B, E, F, I,
UP, and W) and 120 columns. Two of the families find faults and the rest keep
the code uniform. No family that puts a ceiling on a function's or a file's
size is on: how code is shaped is guided, and not ruled (D17). The tests keep
to the same line length as the rest. Ruff is a new development dependency,
which the owner agreed (D3).

**Where each runs.** On the machine, on the pull request, and on `main`,
except where a row says otherwise. The owner's tests run on the live site as
well, after the deploy (section 10).

**Left out, and why**

- An audit of accessibility on every page before a deploy. The owner's tests
  find each control by its name, so a control that loses its name fails one,
  and the site eval scores the live root after each deploy.
- Pictures before and after. They decide nothing, so they are no check. They
  are taken for the owner, who gets them in the "Shipped" note, and the
  reviewer reads none (section 8, D4).
- A comparison of two builds byte for byte, of two pictures, or of the
  stylesheet's values against a list. The owner turned these down: the look
  is guided, and what matters is what the site does (D18).
- Mutation testing. Each changed copy of the code needs a run of a suite that
  takes four minutes.
- A linter for the page's script. Its source files are templates, so a tool
  would have to read the script as built, and the tests already run that.
- A linter for the templates. A name that is misspelt already fails the
  build, which is strict about names it does not know.
- A tool that checks links. The owner's tests hold the links within the site,
  and a link to a repository fails for reasons outside it.
- A spelling checker. The ones looked at default to American spelling.

`docs/research/2026-11-22-other-kinds-of-testing.md` holds what was read for
this list, and section 13 says when each new check is built.

**A check that fails some of the time is a fault.** It is fixed or removed,
and never run again until it passes. One of the agents' tests is mended by the
agent that builds. One of the owner's tests is not that agent's to change, so
the feature stops for the owner (section 14).

**Before a merge.** The check must have passed on the pull request for the
exact commit that is merged. The ship script (section 9) refuses otherwise.

## 7. The owner's tests in a browser (new)

The owner agreed this section on 22 November 2026 (D19, D20). The list of
sentences in D19 still waits for the owner to read it.

**What exists today.** The page's script is run under Node against stand-ins
for the page, with no fetch and no timers (`tests/run_page_script.js`), and
those tests cover the notice of an old board and the theme. No test presses a
filter, sorts, searches, opens a row, or moves over the Baseline chart: the
filter's script is otherwise checked by reading its text. All four issues in
the queue change something in that untested part.

**What the suite is.** Scenarios that drive a real browser through the built
site and say what a reader would see. Each is one given, when, then. They are
most of the owner's tests (D19): one plain sentence each, in a folder that a
feature's change leaves alone. D19 holds the whole draft list.

**The first scenarios**

| Scenario | It shows |
| --- | --- |
| Pressing New shows only new repositories, and says how many | The filter, and its count |
| Choosing a star band, a language, or an order changes the rows | Each control |
| Typing in the search narrows the rows, and no match says so | The search |
| A filtered board's address, opened again, shows the same filter | The address holds the state |
| Opening a row shows its reason, then the rest once the history arrives | An opened row, and the one fetch |
| A row opened on a phone has nothing past the edge | The layout |
| The theme switch changes the theme, and the choice is kept | The theme |
| Moving over the Baseline chart names the nearest repository | The readout |
| The keyboard reaches every control, and each shows its ring | Focus |
| With scripts off, every row is listed and no control shows | The page is whole without the script |
| The page asks nothing of another site, and the browser refuses nothing | The policy |
| The day bar leads to the board before, the board after, and the newest | Moving between days |
| When a board day's history does not arrive, an opened row still shows its reason | The one fetch, failing |
| With the reader's clock 26 hours past the publish time, the page says how old the newest board is, and a week past it, no board is shown | The notice of an old board, in a real browser |

**Failure and time.** The last two rows test what depends on something
outside the page, which no test of a built page reaches. Playwright for
Python can fail a request (`route.abort()`), take the browser offline
(`set_offline`), and fix what the page's clock says
(`page.clock.set_fixed_time`, since version 1.45). Its documentation shows no
way to delay a request, so no scenario leans on one.

**Two rules for writing one**

- A scenario names no repository and no board day. It takes "the first row"
  or "a language the filter offers". So the same scenario runs on the made-up
  board the tests build and on the live site.
- A feature that adds something a reader can do gets a scenario of its own.
  The reviewer writes it (section 8), which neither shaped the feature nor
  built it, and it is the one run against the live site after the deploy.

**Where it runs.** Against the pages built on the machine, served at
127.0.0.1. On the pull request, the same. After a deploy, against
risingrepos.com, reading only.

**The tool.** Playwright for Python, driving the Chrome that the machine and
GitHub's runner already have, so that no browser is downloaded. It is a new
development dependency, which the owner agreed (D2).

**Other browsers, later.** Firefox and WebKit are Playwright's own builds, and
take a few hundred megabytes to install. The scenarios run in Chrome alone
until the workflow has carried some features (section 13, step 9).

**Not Gherkin.** The criteria are written as given, when, then in the plan,
and each test's name is that sentence. A second language for the same
sentence is one more thing to keep in step.

## 8. Review

The owner agreed this section on 23 November 2026.

One fresh agent that did not write the change, started once the check has
passed. It is the one place after the build where an agent's judgement is
used: the check has already decided whatever a script can.

**What it is given.** The plan, the diff, the check's results, the list of
existing tests the change altered or removed, which a script makes, and the
layout report (below). It is not given the author's reasoning, and it is not
given pictures.

**What it is for.** To find what is wrong. It does not run again what the
check ran.

- A case the tests miss. It may build the site and try to break it.
- A criterion met in its words and not in its meaning.
- A standard that only judgement can hold, bent: above all, whether a new
  part reads as one with the rest (`STYLE.md`).
- Code that will be hard to change, or that solves more than the plan asked.
- Anything in the diff that the plan does not account for.
- One of the agents' tests changed or removed so that the change passes, and
  not because what the page does has changed. The agent that builds may
  change those tests (D19), so this is where a loosened one is caught.

**It writes the owner's test for something new** (D19). When the feature adds
something a reader can do, the reviewer writes the sentence and its test among
the owner's tests, from the plan and the built site. It is already a separate
agent with both in hand, so a third agent would read the same things again. A
feature it cannot write a passing test for does not do what the idea showed,
and that is a finding. The check then runs again with the new test in it,
which has to fail on the commit before, as any new test does (section 6). The
reviewer adds to the owner's tests and changes nothing that is there.

**The layout report, in place of pictures.** The owner chose that a reviewer
reads no pictures, since each one costs tokens. A script writes a short report
in words for each page the change altered, at a phone's width and at a
desktop's: what reaches past the edge of the screen or is cut off; the outline
of the changed part as a reader meets it, with each heading and the name of
each control; and the values the change added to the stylesheet that were not
in use before, for the reviewer to hold against `STYLE.md`. It informs, and
nothing fails on it (D18). The pictures are still taken, since a script takes
them for nothing, and they go to the owner in the "Shipped" note (D4). A look
the owner dislikes becomes an idea like any other. The report is not built,
and was not tried.

**What it writes.** One comment on the issue. A verdict, pass or changes
needed, for a named commit. Then its findings, numbered, each with its file
and line, and each saying two things: whether it blocks, and whether a check
could have found it.

**How many times.** One review. After fixes, the same reviewer reads the
changes since, and nothing else. A change that still does not pass goes to
`needs-owner`.

**Security.** No second reviewer: the owner chose that the standards and the
pointers to them carry this. Standards P1, P2, P5, P21, and P22 hold what a
page may run, request, and trust, and C5 to C9 what the repository keeps, and
AGENTS.md sends a change to them. When the diff touches
`sitebuild/contract.py` or `sitebuild/templates/page.html`, the reviewer's
brief names those standards. A change to a workflow, a dependency, a limit of
the eval, or the page's policy already stops for the owner (section 9).

**What a finding becomes.** A finding that a check could have found becomes a
test among the agents' tests, in the same pull request. Where it needs one of
the owner's tests changed, or a change to the check, it becomes an issue for
the owner, since a feature changes neither.

**What it costs.** No cap is set (D6). The tokens the build used and the
tokens the review used are written in the "Shipped" note, and the look back
(section 18) says where either could have been less.

## 9. Ship

A script merges, and it refuses unless every one of these holds:

- The check passed on the pull request, for the head commit.
- The review's verdict is pass, and names that same commit.
- The branch merges into `main` as it is now. If `main` moved, the check has
  run on the result.
- The issue is still open, and still carries `approved`.
- The diff touches no guarded path (below) that the owner's answer on the
  issue does not cover.

It merges that exact commit, as one merge commit named for the issue. The
workflow that exists today then builds and uploads it. No person takes part.

**The guarded paths.** A feature's diff should not change what judges it. So
the script stops (section 14) when the diff changes a workflow, a dependency,
a size limit or a limit of the site eval, the policy beyond the script's
hash, the type, the standards, the look back's notes, or this workflow's own
scripts and documents, or removes a check, unless a comment of the owner's on
the issue allows that path. Shape asks that question before any code is
written, so a stop here means the build left its plan. Each is told from the
diff's paths.

The owner's tests are guarded more closely: a change may add lines to their
folder, which is how the reviewer adds a test, and may take none away. An
agents' test that a change removed stops nothing here: the agent that builds
may remove one (section 5), and it is on the list the reviewer reads
(section 8).

**What a review of the gates changed.** On 23 November 2026, before any
feature ran, one fresh agent read the scripts as an adversary. The scripts
now differ from this section and the next in these ways:

- The owner's tests are held by what a file of Python means, and not by its
  lines. A `return` or a skip added to a test takes it away and removes no
  line.
- A new file or folder at the top of the repository is guarded, with the
  settings of the lint and how git reads a file, since Python and each tool
  read the folder a check is run from.
- The merge of a revert is held to being exactly the revert of the feature's
  merge, in the guard's place. The guard would refuse the revert of a
  feature whose reviewer added one of the owner's tests, and the broken page
  would stay live.
- Nothing merges when `main` moved while the conditions were judged, when
  the plan was edited after the review, or when the review names its commit
  by fewer than its 40 digits. Two changes are the same only when git's
  patch id of their bytes is.
- A pull request is an issue's only when its number is the higher one. The
  repository's first pull requests are on branches numbered for RisingRepos's
  issues, and this repository's own issues reach those numbers in time.
- A test that was skipped proves no criterion.
- After a revert, Confirm follows the revert's own deploy. An eval that was
  cancelled measured nothing, and is no failure of the change.

Some of its findings were narrowed and not closed, and four things are left
as they are. A run acts with the owner's own access to GitHub, so the
scripts hold an agent that follows them, and nothing here holds one that
does not: a rule on GitHub's side for `main` would. An eval that `main`
moved past ends as a pass without measuring, and Confirm cannot tell that
from a pass. A statement the owner's tests may gain can still run code when
its file is read, which the reviewer and the owner read for. And nothing
ties a criterion's proof to the change: a plan can name a test that `main`
already had, and it is the reviewer who reads for a criterion met in its
words alone.

## 10. Confirm

1. **The deploy.** Wait for the run of "Build and deploy" for the merge, and
   see that its upload ran and was not left to a newer push.
2. **The feature, live.** Run the feature's own scenarios, and a short pass of
   the suite, against risingrepos.com. Cloudflare can serve a cached page for
   a while after a deploy, so this tries again for a set time before it fails.
3. **The eval.** Read the site eval that follows the deploy. Each number is
   within its limit.
4. **Close.** Post "Shipped" on the issue: the pull request, the merge's
   commit, the pictures, the eval's numbers, and the figures of the four evals for this feature
   (section 17). Close the issue,
   delete the branch and the worktree, and tell the owner on Discord.
5. **Look back.** Section 18. Nothing waits on it.

**When one of these fails because of the change,** the run mends it. The
owner decided this on 23 November 2026: a feature may deploy and be found
wanting a few minutes later, and the run then tries to put it right by
itself, in fewer steps than the feature had. A mend is a second pull request
of the same issue. The plan stands and nothing is shaped again, the check
runs, the reviewer reads the mend alone, and the ship script merges it on
the conditions it holds a feature to. The fault stays live meanwhile.

When the mend fails on the live site too, or its cause cannot be found, the
site is put back: the agent opens a pull request that reverts every merge
of the feature, which the check must pass and no reviewer reads, and the
ship script merges it. Then the run stops (section 14), and says what it
saw. Until that day this section had the site put back first and the owner
asked second (D5).

A run can end in the middle of this. So the script that picks an issue up
says how many of the feature's merges stand on `main` and whether it was
reverted, and takes a feature that is live up again whatever the site's
health, though section 3 has the health asked first of all: the fault may be
the feature's own, and no other run would mend it.

Two parts of this are an agent's reading, and not the owner's words: that
one mend is tried and no more, and that a board no reader can read is put
back at once, with no mend tried while it is down.

**What has to be true first.** The site eval has to pass, or it cannot tell a
feature that slowed the page from one that did not. After the redesign it
failed on the phone's Largest Contentful Paint: 2.05 s, 2.05 s, and 2.11 s in
the three evals of 22 November 2026, against a limit of 2.00 s. The owner had
accepted a higher limit (RisingRepos#210), and step 1 of section 13 set it to
2.5 s, which is Google's line for a good paint.

The third of those evals failed on the desktop too, at 0.62 s against 0.60 s.
The first measured exactly 0.60 s, and the board had fewer rows on the third
than on the first, 252 against 264, so the figure did not rise with the
board: it sits at its limit, and the runner's noise carries it over. The
owner raised that limit to 0.9 s on 23 November 2026: the highest median
since the redesign with two fifths more, which is how the old limit was set.

The eval that followed the board of 23 November 2026 failed on a third
number, the phone's Cumulative Layout Shift, at 0.033 against 0.010. The
page drew its text in the fallback face and drew it again in its own a few
milliseconds later, and that board's fifth name took one line in the first
and two in the second. No limit was moved for it. The faces now hold their
text back until they are in, and the same board measures 0.0003
(README.md, "The design note", under "Type", which says what is left).

## 11. The standards and the rest of the context (new)

Agreed on 22 November 2026 (D14 to D16), and written that day: `STANDARDS.md`
with 53 standards, nine records in `docs/adr/`, `GLOSSARY.md` with 53 terms,
`tests/test_context.py`, which holds those three and AGENTS.md to the
files, and `STYLE.md`, the style guide. The first part of the standards still waits for the owner's own do's
and don'ts. AGENTS.md has pointers to the three and is otherwise as it was,
until step 5 of section 13. The reading behind this section is in
`docs/research/2026-11-22-agent-context-foundation.md`.

**Where a judgement is put.** At the strongest place that can hold it:

1. **A check that fails.** It stops a wrong change, whatever the agent read.
2. **A standard.** The plan is held against it at Shape, and the reviewer
   judges by it at Review.
3. **A decision record.** It tells Shape what is settled, and why, so that a
   feature does not reopen it by accident.

The first is a hard guard. The other two are soft ones: they guide an agent
and do not stop it. They act earliest, at Shape, before any code is written,
which is the cheapest place to turn a wrong idea round.

**What is added, in this order**

| File | What it holds | How it is kept true |
| --- | --- | --- |
| `STANDARDS.md` | The do's and don'ts of the site and of its code | Each standard names the check that holds it, or says that the reviewer does. A test fails when a check it names does not exist |
| `docs/adr/` | What was decided, why, and, where a condition was recorded, what would reopen it. Short records, and only for a choice that is hard to undo, would surprise a newcomer, and gave something up | Each record names the check that confirms it, and the same test looks for that check |
| `GLOSSARY.md` | The site's words, in this repository's own wording | It holds only words that the pages, the code, the tests, or the documents use |
| `STYLE.md` | What a new part of a page reaches for first: the parts to start from, and the values in use with the job each does. A guide, and not a rule (D18) | By hand. It gives the day its values were read, and the stylesheet is right where the two differ |
| `AGENTS.md` | Stays a map to the files above and to the workflow's documents. Rewritten last (section 13, step 5) | A test that every path and every README heading it names exists |
| `.out-of-scope/` | An idea the owner turned down, with the reason, so that it is not filed again | Made when the first idea is turned down, and not before |

An idea that goes against a decision record is never "go" at Shape. It is
"needs the owner" (section 4).

**`STANDARDS.md`** has three parts: what belongs on the site, which Shape
reads; what a page promises; and how the code and the words are written.
Each standard has a number, the rule, why, and how it is held: by a named
check, or by the reviewer. A standard that a check can hold is not left to
the reviewer. The standards the reviewer holds are the whole of the
reviewer's brief (section 8), so each one that becomes a check makes the
review smaller.

Most of the site's rules exist already, in README.md's prose and in the
tests. Writing those standards is mostly numbering them and saying which
check holds each.

| Kind | Examples | Held by |
| --- | --- | --- |
| What a page promises | Whole with scripts off. One script. Nothing from another site. Within its size | Tests today |
| The look | Each colour has one job. Two families of type. Tabular figures in a column. A drawing has its figures in words | The colour test today. The rest: the reviewer, until a check is written |
| Access | 4.5:1 for text. Every control reached by the keyboard, with a ring. Reads at 390 px and at 1440 px | The colour test today. The suite, new |
| Text an owner wrote | Escaped wherever it is shown, and never made a link | Tests today |
| The script | Writes only text. No `innerHTML`, no `eval`. Stores nothing but the theme | Tests today, on the script's text and on the notice as it runs. No test runs the filter or an opened row: the suite, new |
| The Python | The lint and the format. No value marked safe in a template | New, and a test today |
| The tests | Named as the sentence they prove. Test what the build writes. None skipped or loosened | The reviewer |
| The words | Plain, whole sentences that say why. British spelling. The domain's terms | The reviewer |
| A change | One feature. Its docs with it. No dependency without the owner | The paths' rule, and the reviewer |

**Where the standards come from.** They are not written afresh by an agent.
One study found a context file that a model wrote to be slightly worse than
none (the research file, section 5). They come from three places:

- the rules that README.md and AGENTS.md already state;
- what reviewers found on the pull requests already merged here, which is
  where judgement was really exercised: the twelve reviews of #25 and #26
  (#31 had none). Each quotation a standard rests on was looked up in the
  review it came from;
- the owner's own judgement of what belongs on the site and what does not.
  Nothing else can supply it, and it is most of the first part. It is still
  to come.

**What the earlier reviews taught, beyond the standards.** Two things bear on
the sections that follow:

- The reviewers found most of what the tests had missed by running every row
  in `site-data/`, where the tests build from an example of five rows. One
  review found 13,444 rows that wrote a pace two ways. Standard C19 says so,
  and a check that does it belongs in section 6.
- A fix made between two rounds of review brought in a fault of its own: a
  test added with a fix still passed with the fix taken out, and only the
  next round saw it. So the second look of section 8 runs the checks on the
  fix again, and does not only read it.

The standards that end "A check could hold this" are the list that section 6
draws its new checks from.

**What stays in RisingRepos.** AGENTS.md today sends an agent to the private
repository for seven things. Each is either brought here or left there:

| Today, AGENTS.md says | It becomes |
| --- | --- |
| Read RisingRepos's `AGENTS.md` before a task here | Dropped. This repository's own files are enough |
| Site work is tracked there, on a branch named there, by a procedure there | This repository's workflow documents (section 13, step 5) |
| A commit and a pull request cite an issue there | They cite the issue here |
| The domain's words are defined there | `GLOSSARY.md` here (D15) |
| A workflow is a security surface, as a document there says | A standard here, and the guarded paths (section 9) |
| A credential is handled as a document there says | The rules for the two credentials this repository uses, as a standard here. That document is read first (section 16) |
| `site-data/` and the data contract are RisingRepos's | Stays a pointer. The data is theirs (section 12) |

Two things do not change. The rule that nothing here quotes the private
repository stays, and becomes a standard. And the places where README.md, a
test, or a comment names a RisingRepos issue as where a point was decided
stay as they are: AGENTS.md has each say, in its own words, what was
decided. They were not each read to confirm that.

**What is left out**

- A document that gives an overview of the code. The same study found that
  an overview did not help an agent, and README.md is the full account
  already.
- The three files that the `mattpocock/skills` setup writes under
  `docs/agents/`. They tell those skills where the tracker and the labels
  are, and the workflow's own documents say that here. Its ideas are taken:
  the glossary, the short decision record, standards read at review, and the
  record of ideas turned down.

**How the context is itself judged.** By the first features (section 13,
step 6). Where an agent goes wrong for want of a rule, the rule is added.
Where a rule was never needed, it is a candidate to remove. No study was
found that measures what a decision record, a glossary, or a standards file
does for an agent, so this is the only evidence there will be.

## 12. Work that needs RisingRepos

- **Asking.** The agent files an issue in RisingRepos that says what the page
  needs to show, which field would carry it, and which issue here waits on it.
- **Waiting.** The issue here gets `blocked-on-data` and a comment that names
  the RisingRepos issue by its number. The agent takes the next issue.
- **Resuming.** Each run looks at the blocked issues. One whose field is now
  in `site-data/contract/daily.schema.json`, and in the newest board day's
  file, loses the label and goes back to Shape, since the plan may be stale.
- **The line between the two.** RisingRepos's publish goes on writing
  `site-data/`. The code that reads a new field, and the tests' copy of the
  contract's example, belong to this workflow. Today RisingRepos's own
  procedure has its agents open pull requests here, so its documents change
  too, and that change is decided there (D7).

## 13. What is built, and in what order

The owner agreed the order of the checks and the evals in it on 22 November
2026 (D20).

**Before the first feature**

1. **The eval is made green.** The phone's limit is raised to 2.5 s, as
   accepted, and the desktop's to 0.9 s, as the owner decided on 23 November
   2026. The layout shift that the board of that day showed is mended
   (section 10).
2. **The context and the check command.** `STANDARDS.md`, the first decision
   records, `GLOSSARY.md`, the test that holds them to the files, and
   `STYLE.md` (section 11). Then the one command; the lint and the format,
   with the one tidy change they needed first; the checks run on every
   published board; the list of hostile text; and the pull request's job
   (section 6).
3. **The owner's tests** (D19): their folder, the first scenarios in a real
   browser with the failure and clock cases (section 7), and the pictures.
   The owner reads the list first. Standard C10 and the glossary are brought
   into line in the same change.
4. **The ship script, the live check, and the revert**, with the three checks
   of a feature's own work: that what judges it was left alone, that each new
   test fails on the commit before, and that each criterion has its proof
   (section 6). They come before any feature, because the first feature
   already merges with nobody watching. With them, the one line that keeps a
   push of the look back's notes from deploying (section 18), with its test,
   and with decision record 0006, AGENTS.md, and README.md reworded to match.
5. **The workflow's documents.** The stages, the plan's sections, the stops,
   the labels, the reviewer's brief, and AGENTS.md rewritten to say this
   repository tracks its own work, with the test that holds it to the files.
   With them, the two scripts the reviewer reads from, which list the tests a
   change altered and write the layout report (section 8), and the script
   that makes a run's digest, which gives the four evals their figures
   (section 17), with the look back's brief (section 18).

**The features**

6. **The first features.** #27 to #30 go through it one at a time. A person
   starts each run, and it then goes to the deploy unattended. What each one
   teaches changes the documents.
7. **The scheduled run in Orca**, which takes over starting them.

**After the first few features**

8. **A type checker** over `sitebuild/`, where 72 of the 75 functions already
   state every type and nothing checks them: it finds a wrong kind of value
   on a path no test runs. mypy ran there in about five seconds and reported
   seven things, none a fault in what a page shows. It is a new development
   dependency when it is added.

**Later, as each earns its place**

9. The regression set for the workflow's judgement (section 17). The owner's
   tests in other browsers (section 7). An audit of the dependencies for
   known faults, which `uv audit` does with nothing new installed. Lint for
   the workflows, with actionlint and zizmor, run when a workflow changes,
   since a feature cannot change one. Test cases a tool generates, with
   Hypothesis, if running every published board leaves the functions that
   word a figure thinly tried.

Steps 1 to 5, 8, and 9 build the workflow or change what judges a feature,
so the workflow cannot carry them: the owner directs those. Steps 1 to 5
were built together on one branch on 23 November 2026, and reach `main` in
one pull request, since each leans on the others: the pull request's job
runs the check command, which runs the owner's tests.

## 14. Stops, and labels

The workflow goes on by itself until one of these is true. Nothing else stops
it, and a stop is never a matter of course.

| Stage | A reason to stop |
| --- | --- |
| Pick up | The site is not healthy (section 3). No issue is stopped by it: nothing new starts, and the owner is told once |
| Shape | One of the reasons in section 4: the idea is no longer true, it cannot meet a standard, it needs a new face or a character the type does not hold, it would change what one of the owner's tests says, the budget has no room, it touches a guarded path, it is larger than one pull request, or its criteria can be read two ways |
| Build | A criterion cannot be met as the plan has it. The work has to leave the plan in a way Shape would have stopped for |
| Check | A check fails and the only way past it is to loosen the check. Two different attempts at a failing check have not passed it |
| Review | The verdict is still "changes needed" after the one recheck |
| Ship | A condition of the merge does not hold and the agent cannot make it hold inside the plan |
| Mend | The one mend of a feature that failed on the live site did not put it right, or a reader cannot read the board. The site is put back first |
| Any | A security control refused an action. The agent does not look for a way round it |

**What a stop does**

1. The work is pushed, so nothing is lost.
2. One comment on the issue says the stage, what was seen, what was tried,
   the question for the owner, and what the agent would choose.
3. The issue swaps `in-progress` for `needs-owner`, and the owner is told on
   Discord.
4. The agent takes the next eligible issue. A stopped issue holds nothing up.

**How it starts again.** The owner answers on the issue and removes
`needs-owner`. The next run reads the answer and carries on from the stage
that stopped, with no merge and no approval asked of the owner beyond that
answer. A branch that waited is brought up to `main` and checked again first.
How a run tells the owner's answer from an agent's comment, when both come
from one account, is D10.

| Label | Means | Who sets it | Who clears it |
| --- | --- | --- | --- |
| `site-idea` | Proposed by the daily site review | The idea agent | Nobody |
| `approved` | The owner approved the idea | The owner's approval on Discord | The owner, to withdraw it |
| `in-progress` | The workflow holds it | Pick up | Confirm, or a move to one of the two below |
| `needs-owner` | A question is waiting, in the plan's comment | Any stage | The owner, by answering and removing it |
| `blocked-on-data` | Waiting on a RisingRepos issue | Shape | A run that finds the field has arrived |

A closed issue either shipped, and says so in its last comment, or was
withdrawn by the owner.

## 15. Decisions still open

**What the build starts from.** On 23 November 2026 the owner had a
recommendation on each open decision before them, and told the build to
start. None was answered one by one, so each is taken as recommended and
stays the owner's to change:

- D4: the pull request's job keeps the pictures, and the "Shipped" note
  links them.
- D5: answered since, on 23 November 2026 (below).
- D7: RisingRepos's agents change nothing here but `site-data/`. That part
  is decided in RisingRepos, and nothing here enforces it.
- D10: the owner answers a stop with a comment on the issue and removes
  `needs-owner`. Every comment the workflow writes begins with a fixed first
  line, and a comment without one is the owner's.
- D11: the list of stops in section 14 stands as written, and is judged by
  the third eval once four features have gone through.
- Section 9 stops on a line taken from the owner's tests or a check removed,
  and not on an agents' test removed.

- **D1. Settled on 22 November 2026: there is no switch.** The workflow merges
  and deploys by itself from the first feature, and the owner merges nothing.
  It stops only for a reason in section 14.
- **D2. Settled on 22 November 2026: Playwright for Python**, as a
  development dependency, drives the owner's tests (section 7). The
  alternative was to keep testing the script under Node, which cannot press
  a control.
- **D3. Settled on 22 November 2026: the lint and the format, with ruff**, at
  the six rule families RisingRepos uses and 120 columns, with no family that
  sets a ceiling on size (section 6). It needs one commit first, which is
  nearly all the tool's own work. An earlier draft said that many of the
  tests' names pass 120 columns and asked whether the limit should spare
  them. That was wrong: one name does, measured on 22 November 2026, and the
  long lines are code, which the formatter wraps.
- **D4. Where pictures are kept.** Settled in part on 23 November 2026: the
  reviewer reads none (section 8), and they go to the owner in the "Shipped"
  note. Still proposed: sent to Discord, and kept as the pull request job's
  artifact, with a link on the issue. Whether an agent can place a picture
  inside an issue's comment was not checked.
- **D5. Settled on 23 November 2026: a feature that fails on the live site is
  mended first.** The owner is content for a feature to deploy and be
  verified a few minutes later, and for the run to try to put a fault right
  by itself, in fewer steps (section 10). The site is put back only when the
  one mend fails, or when no reader can read the board. The plan had the
  agent revert first and ask second.
- **D6. Settled on 23 November 2026: no cap on what a run or a review may
  cost.** The owner wants the workflow made cheaper by going over each run,
  and not by a limit: the "Shipped" note gives the tokens of each stage, and
  the look back (section 18) says what could have been spared.
- **D7. RisingRepos's agents change nothing here but `site-data/`.**
- **D8. Settled with D1: the plan needs no second approval** when its verdict
  is go (section 4).
- **D9. Settled on 23 November 2026, with Review: the review's findings go on
  the issue**, and the pull request holds
  the diff, the check, and a link.
- **D10. How the owner answers a stop.** Proposed: the owner comments on the
  issue and removes `needs-owner`, and every comment an agent writes begins
  with a fixed first line, so that a run never takes its own words for the
  owner's. The alternative is to answer on Discord, where ideas are approved
  already, and have that same route write the answer onto the issue.
- **D12. Settled on 22 November 2026: a claim is dead when Orca lists no open
  agent in the issue's worktree** (section 3). `orca worktree ps` was run that
  day and listed the session at work in its worktree as an agent that was
  working, with how long ago it was last active. A timer is not needed.
- **D13. Settled on 22 November 2026: an Orca automation, and not an Orca
  bot** (section 3). A bot's advantage is starting on an event, such as a
  label being applied. Orca's guide says an owner's own actions on GitHub do
  not start a bot's rule, and the labels here are applied under the owner's
  account. A bot also needs a GitHub connector and Orca's cloud to hear
  events. That reading of the guide was not tried.
- **D14. Settled on 22 November 2026: the context this repository gets** is
  the set in section 11, in that order.
- **D15. Settled on 22 November 2026: the site's words are defined here**, in
  a `GLOSSARY.md` that is public with the rest of this repository, and in
  this repository's own wording.
- **D16. Settled on 22 November 2026: this repository holds its own rules and
  decisions**, and points to RisingRepos only for what RisingRepos owns
  (section 11). The owner means to supply much of what belongs on the site
  and what does not.
- **D17. Settled on 22 November 2026: no check holds a module or a function
  to a size.** The reviews of the redesign applied a line of 1,000 lines,
  from RisingRepos's rules for a review, and did not block on it.
  `sitebuild/__init__.py` is 984 lines. The owner chose that how code is
  shaped is guided and not ruled, as the look is, so the lint turns on no
  family that sets a ceiling (section 6), and no standard gives a number.
- **D18. Settled on 22 November 2026: which guards against drift are built.** The research is
  `docs/research/2026-11-22-keeping-the-site-from-drifting.md`, and its
  section 8 holds what was checked again. Four were proposed, and the owner
  answered on 22 November 2026.
  1. *Holding the stylesheet's values to a list: turned down.* The look is
     guided, and not ruled. `STYLE.md` was written that day as a guide to
     what a new part reaches for, standard B5 was reworded to match, and a
     new colour or kind of control no longer sends an idea to the owner
     (section 4).
  2. *A feature cannot change what judges it: agreed.* The evals, and the
     tests that matter most, are the owner's to read and approve. Which tests
     those are is D19.
  3. *Each new test is run on the commit before, and has to fail there:
     agreed.* It is part of Check (section 6), and costs one short run of the
     new tests alone.
  4. *Building the pages at both commits and comparing them: turned down.*
     It holds a change to a page's bytes, and what the owner cares about is
     what the site does: whether a feature broke something that worked. D19
     is where that is held.
  Of the three that waited for their part of the workflow: no ceiling on
  length is set (D17), a scheduled run that reports comes with the Orca run
  at the end, and the made-up boards are now the owner's tests (D19). An inventory of pages and links is not proposed, because two
  tests of the build already hold it.
- **D19. Settled on 22 November 2026: there are two kinds of tests.** The
  owner wants a small set of plain, fundamental tests that are theirs to
  read and approve, and leaves the detailed ones to the agents.
  - *The owner's tests* say what a reader can do on the site, and what the
    site promises that reader: one plain sentence each, and about thirty in
    all. They drive the built site from outside, as a reader does, and name
    no markup, so that a feature changes the page round them and leaves them
    standing. Most are the scenarios of section 7, which need a real browser.
    They live in one folder, with the site eval's limits and the size limits
    beside them, and a feature's change may not touch that folder. A script
    read from `main`, and not from the branch, checks that.
  - *The agents' tests* are every other test: the 311 in `tests/` today,
    which assert a page's exact markup. An agent writes, changes, and removes
    them as a feature needs, and every one still has to pass. Of the 27
    commits on `main` that changed `sitebuild/`, 21 rewrote a line of one, so
    closing them to a feature would stop most features.
  - *A feature that fails one of the owner's tests* has broken something a
    reader would notice, and mends its code. A feature that is meant to
    change what one says stops for the owner.
  - *A feature that adds something a reader can do* gets a sentence, and its
    test, among the owner's tests. A separate agent writes them, which
    neither shaped the feature nor built it. So the folder is closed to the
    agent that builds, and that separate agent adds to it and changes
    nothing that is there. The feature does not wait for the owner, who reads
    what was added afterwards: the owner was asked whether that reading was
    right, and answered that it made sense. It is the reviewer, once the check has
    passed (section 8), as the owner agreed on 23 November 2026.
  - Sections 4, 5, 7, 9, and 14 say this now. Standard C10 and the glossary
    name the two kinds once the owner's tests exist (section 13, step 3),
    since a standard says only what is there. Section 9 stops a change
    that takes a line from the owner's tests, and not one that removes an
    agents' test.

  The first draft of the owner's list, which the owner reads before the
  folder is closed. No test drives a browser today
  (section 7), so 11 to 17, 19, 23, and 24 are checked by no test as a reader
  would meet them.

  *A board*
  1. The root shows the newest board, with every repository its file lists,
     in the file's order.
  2. Every board day that was published has a page at its own address.
  3. A row gives its rank, its name as a link to the repository on GitHub,
     the stars it gained on the day, and its total stars.
  4. A row opens on the reason it is on the board, with scripts on or off.
  5. A board says above its rows when it is an earlier board, when its
     ranking is provisional, when a star band is held back, and when
     repositories could not be ranked.
  6. A board with no rows says why.

  *Getting about*
  7. Every page has the site's bar, and each link in it leads to a page that
     is there.
  8. The day bar leads to the board day before and to the one after.
  9. History lists every board day, and each leads to its board.
  10. No link within the site leads to a page the build did not write.

  *The filter and an opened row, in a browser*
  11. New shows only the repositories that are new, and says how many.
  12. A star band's button shows only that band's repositories.
  13. Choosing a language shows only that language's repositories.
  14. Each order puts the rows in that order.
  15. A search shows only the rows whose name or description holds it, and
      says so when none does.
  16. A filtered board's address, opened again, shows the same rows.
  17. An opened row shows its sum, its facts, and the boards it was on, once
      the history arrives.

  *The other pages*
  18. Baseline draws and lists every repository of the newest board.
  19. Moving over Baseline's chart names the nearest repository.
  20. How it works names the formula that ranked the newest board.

  *For every reader*
  21. With scripts off, every row is listed, and no control shows that would
      do nothing.
  22. The theme switch turns the page light or dark, and the choice is kept.
  23. On a phone, nothing reaches past the edge of the screen, with a row
      opened.
  24. The keyboard reaches every control, and each shows its ring.
  25. Every text colour meets 4.5:1 against what it is set on, in both
      themes.

  *What the site promises*
  26. A page asks nothing of another site, and its browser refuses nothing.
  27. A page runs one script, and no other.
  28. What a repository's owner wrote is shown as text, and is never a link.
  29. No page is over 500,000 bytes, and the root of a long board is under
      150,000 on the wire.
  30. A newest board that is 26 hours old says so, and after a week the
      boards are not shown.
  31. The root states its board day and its publish time in the data
      contract's two tags.
  32. A data file that breaks the data contract fails the build.

  *On the live site, after each deploy*
  33. The site eval's six numbers are within their limits.
- **D20. Settled on 22 November 2026: the tests, the lint, and the evals,
  and the order they are built in.** The owner asked first how testing and
  evals are done well, read the lists that answer gave, and agreed them.
  Section 6 holds the checks and what was left out, section 7 the owner's
  tests in a browser, section 13 the order, and section 17 the evals. Two new
  development dependencies come before the first feature, ruff and
  Playwright, and a type checker after the first few. The reading behind the
  lists is `docs/research/2026-11-22-other-kinds-of-testing.md`.
- **D21. Settled on 23 November 2026: the look back's notes are files in this
  repository, and a push of them deploys nothing.** The owner said both. An
  issue, and a place outside the repository, were proposed first and turned
  down. Section 18 says where the files are and how a push of them is kept
  from deploying, which is not so today.
- **D11. Whether the list of stops in section 14 is the right one.** Each
  entry is a judgement about what counts as a real reason. A list that is too
  long brings the owner back into every feature, and one that is too short
  lets a change through that weakens the checks.

## 16. Not checked

- That Playwright drives the runner's own Chrome with no browser download.
- Whether a built script that does not parse is reported as the error that
  `tests/test_old_board.py` looks for. A script that throws when it runs is.
- Anything about the owner's tests that only running them shows: how long
  they take, and that failing a request and fixing the clock behave on this
  site as Playwright's documentation says. None was run.
- Whether mypy's seven findings clear with settings and looser annotations
  alone. Three are for other packages whose types it could not find.
- Whether GitHub can itself refuse a merge whose check has not passed without
  also refusing the daily data push, which goes straight to `main` under the
  owner's account.
- What Orca offers for a scheduled run. That is step 7, and is looked at then.
- Whether the idea agent can attach its screenshots to the issue. Its links
  today are to Discord, and the issues say those expire.
- Whether the standards say all that this repository needs of RisingRepos's
  documents on security surfaces and on credentials. Both were read on 22
  November 2026, and standards C6 to C10 are what was taken from them. A
  change to a security surface gets no reviewer of its own (section 8).
- That each test a standard or a record names proves what the line says,
  as the lines stand now. `tests/test_context.py` shows only that the test
  exists. A second reader read each test's body on 22 November 2026: of 78
  lines, 57 held as written and 21 claimed more than their test proves. Each
  of the 21 was reworded, or given the test that does hold it, and that
  reading was not made again afterwards.
- Three things that reading found in the site itself, which no change here
  has touched. README.md says the script writes no figure of its own in an
  opened row, and the script writes fixed captions and one count there. No
  test holds that the filter's controls are hidden with scripts off, and no
  test measures the size of a page built from the published boards, whose
  longest has more rows than the test's made-up board. And Baseline may
  write a recent pace of 10 or more to one decimal place where a board
  writes it whole, which was read from the code and not seen on a page.
- That a reviewer judges a change to the look as well from the layout
  report as from pictures. The report is not built. The first features that
  change the look will show it, and the owner sees the pictures either way.
- That a push which changes only the notes' folder starts no run of the
  deploy workflow. It is read from GitHub's documentation, and was not tried
  here.
- What a look back costs. One session's record was read by a script on 23
  November 2026, which is all that shows the digest can be made.

## 17. The evals

The owner agreed a longer list on 22 November 2026 (D20), and asked on 23
November for a few that matter most. These are the four.

A test has one right answer, and passes or fails. An eval is a measurement,
held to a limit or watched from one feature to the next. Each of the four
answers one question the owner has of the workflow.

**1. Is the site still fast, accessible, and within its size? (exists)**

Measured on the live root after every deploy, on a phone profile and on a
desktop one, as the median of the eval's runs. Each number has a limit in
`evals/site/limits.json`, and a number past its limit fails the eval.

| Number | Phone | Desktop |
| --- | --- | --- |
| Performance score | 95 or more | 95 or more |
| Accessibility score | 100 | 100 |
| Largest Contentful Paint | 2.5 seconds or less | 0.6 seconds or less |
| Cumulative layout shift | 0.01 or less | 0.01 or less |
| Bytes transferred | 100,000 or fewer | 100,000 or fewer |
| Requests | 1 | 1 |

With them, the room left under the two size limits that the check holds,
since each feature fits until one does not: the longest board's page against
500,000 bytes, and the root of a 713-row board, gzipped, against 150,000.
README.md gives the last measurements: 476,623 bytes on 21 November 2026, and
144,789 on 22 November.

The phone's limit for Largest Contentful Paint was 2.0 seconds until step 1
of section 13 raised it. The desktop's was 0.6 seconds until the owner raised
it to 0.9 on 23 November 2026 (section 10).

**2. Did the feature break anything? (new)**

- The owner's tests, run on the live site right after the deploy: how many
  pass, of how many. Anything short of all of them puts the site back
  (section 10).
- Escapes: a feature that shipped and was later reverted, or needed a second
  change to repair it. The aim is none. This is the truest measure of whether
  the checks before a deploy are enough, and each escape becomes a test.

The owner's tests run after the deploy, and not on a schedule: GitHub says a
scheduled run can be delayed or dropped under load, and that a public
repository's scheduled workflows are disabled after 60 days without activity.

**3. Did it run without the owner? (new)**

Of the ideas picked up, how many reached the live site with no stop. For each
that stopped, the stage it stopped at and the reason. No target is set at
first: the list of stops (section 14) is judged by this number.

**4. What did it cost? (new)**

The tokens from pick-up to the "Shipped" note, by stage: Shape and Build
together, Review, and the look back. With them, the hours from the idea's
approval to the live site. No cap is set (D6). The number is watched from one
feature to the next, and the look back says what would have made it smaller.

**Where the figures are kept.** A script gathers evals 2 to 4 from each run's
record, so they cost almost no tokens. They are written in the "Shipped" note
and in the run's file of notes, and one row for each feature is added to a
table in `docs/workflow-notes/` (section 18), so that a change over ten
features can be seen at a glance.

**How an eval is graded.** Anthropic's account of evals for agents
([Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents))
gives four rules that these follow.

- By a script where one can: "We recommend choosing deterministic graders
  where possible, LLM graders where necessary or for additional flexibility".
- By what was made: "it's often better to grade what the agent produced, not
  the path it took." A feature is judged by the owner's tests and the checks.
- From real failures: "In reality, 20-50 simple tasks drawn from real
  failures is a great start."
- With a look at the run itself: "As a rule, we do not take eval scores at
  face value until someone digs into the details of the eval and reads some
  transcripts." The look back is that look.

**Kept for later.** A set of past ideas whose right outcome is known, run
again when the standards or the workflow's instructions change, to show a
reworded line that changed what an agent decides. It costs tokens, and it is
built from escapes, so it waits for some.

**Left out.** A fault planted for the reviewer to find, which the count of
escapes answers more cheaply. Measuring how fast the site loads for its real
readers, which would need analytics: the site keeps nothing about a reader
and requests nothing from another site (standards B8 and P2). The stale check
is not counted here: it watches the data's freshness daily, and exists.

## 18. The look back (new)

The owner asked for this on 23 November 2026: when a feature is done, an
agent looks over the whole run and writes down how it could have gone better.
It is how the workflow gets cheaper, since no cap is set on what a run may
cost (D6).

**The three questions** the owner set for it

1. How could the run have been more efficient?
2. What was used that was not needed?
3. What could have been used that would have saved tokens, or given a better
   outcome?

**A script reads the run first.** Reading a whole run costs about what the
run cost, so no agent reads one whole. An agent's record of its run holds
every call it made and the tokens of every message, so a script makes a
digest of about a page: the tokens of each stage; each tool, and how often it
was called; the files read most often, and how long each is; how many times
the whole suite ran, and how long that took; each check that failed, and how
many tries it took to pass; and each stop. The digest gives the evals their
figures as well (section 17).

On 23 November 2026 a script read the record of the session that wrote this
plan: 577 messages, each with its count of tokens, and 623 calls. This plan
was read 19 times and the whole suite run four times, which is the kind of
thing the digest is for.

**Then one fresh agent** reads the digest, the plan, the review, and the
"Shipped" note, and opens the record itself only where the digest points at
waste. It answers the three questions in fifteen lines or fewer. Each line
says what it saw, and what to do differently.

**Where the notes go.** Into this repository, as the owner chose (D21):

- `docs/workflow-notes/runs/`, one file for each run, named for its issue,
  which holds the digest and the fifteen lines. One file a run means that two
  runs never change the same file.
- `docs/workflow-notes/LESSONS.md`, the short list a run reads at its start.

They are public, like everything here, so the digest names a file by its path
in the repository and holds nothing of the machine it ran on (standard C5). A
feature's change leaves the folder alone (section 9).

**A push of the notes deploys nothing.** That is not so today. The deploy
workflow starts on every push to `main`, whatever the push changes, and
`tests/test_workflow.py` holds exactly that. So a notes file pushed by itself
would build and upload the same pages again, and run the site eval again. The
workflow gets one more line, which leaves out the notes' folder: GitHub's
rule is "When all the path names match patterns in `paths-ignore`, the
workflow will not run." The line names that folder and nothing else. A list
of the files that do make a page would be the other way to write it, and a
file left off such a list would be a change that should have deployed and did
not, with nothing to say so. The test, decision record 0006, AGENTS.md, and
README.md change with the line (section 13, step 4).

**When it runs, and how the notes reach `main`.** After Confirm, in a commit
of its own that holds the notes and nothing else, as the owner agreed on 23
November 2026. The script that pushes it
refuses a commit that touches any other path. The notes could ride in the
feature's own branch instead, but the look back would then have to run
before the merge: it would not see the deploy or the live check, and the
notes of a run that stopped would never reach `main`. A run that stops gets
its look back too, since those are the runs with the most to teach.

**What the notes change.** A note is not an instruction to the next run.
Every few features the owner and an agent go over the notes and change the
workflow's documents, which a feature cannot change (section 9). What a run
reads at its start is a short list of the lessons that have held, which is
rewritten and never only added to, so that it stays short.

**What it costs** is in the digest of the next run, like any stage's.
