# Working in rising-repos-site

The pages of risingrepos.com: a Python generator (`sitebuild/`) with Jinja2
templates, one stylesheet, and one script, the data it renders (`site-data/`),
and the workflows that test, deploy, and watch the site.
[README.md](README.md) is the full account of each part and why it is so. The
table under "Read before you act" names the section to read for the part you
are changing.

## What a push does

- A push to `main` is a production deploy. The build job checks and builds the
  pages, and the deploy job uploads them to risingrepos.com
  (`.github/workflows/deploy.yml`).
- A push to any other branch runs no workflow. A pull request runs the checks
  and the build, keeps a picture of each kind of page it altered, and deploys
  nothing. One that changes the site eval also runs the eval, against the live
  site. No branch gets a preview deployment: look at other work by building it
  locally.
- The repository is public, and a push is public at once. Pushed history is
  never rewritten, so read each commit, with `git log -p origin/main..HEAD`,
  before it is pushed, and each PR body, review, and comment before it is
  posted.

## How work is tracked here

This repository runs its own feature work, and its own issues are the tracker.

- An idea for the site is an issue here labelled `site-idea`, and the owner
  approves one with `approved`.
  [docs/workflow/README.md](docs/workflow/README.md) is how an approved idea
  goes from its issue to the live site, stage by stage, with nobody driving
  each step. Follow it for any issue that carries both labels.
- A feature is delivered on a branch named `agent/<issue>-<slug>`, through a
  PR. Its commits and its PR cite the issue here: `Refs #<n>`. Ideas worked
  together are delivered on the branch of the one the run took up, the lead,
  and their commits and PR cite each of them.
- A feature leaves alone what judges it: a workflow, a dependency, a limit,
  the standards, the owner's tests, and the feature workflow's own scripts and
  documents. That document lists them under "The guarded paths". A change to
  one of them is not a feature. The owner directs it, and no run of the
  feature workflow carries it.

## RisingRepos, which owns the data

The site is one part of the RisingRepos project. Its repository,
`AndrewGodlewsky/RisingRepos`, is private. This repository holds its own
rules and decisions, and turns to that one only for what it owns, which is
chiefly the data. A path below written `RisingRepos: <path>` is in a checkout
of it.

- `site-data/` is RisingRepos's output. Its publishing job commits each board
  day straight to `main` here, as `Publish board day <date>`. A change to the
  data contract (`site-data/contract/` and `sitebuild/contract.py`) lands in
  both repositories, in an order that keeps each one working (RisingRepos:
  `docs/adr/0004-the-site-stays-in-its-own-repository.md`).
- A feature that needs a figure the site does not receive files an issue
  there, and waits for the data (docs/workflow/README.md, under "Shape").
- Because RisingRepos is private and this repository is public, what is
  written here, in a file, a commit, a PR, a review, or a comment, names a
  RisingRepos issue by its number and says what it decided in other words. It
  quotes neither the issue nor its owner, and holds no path on anyone's
  machine and no personal e-mail address. Commit with your GitHub noreply
  address. The publishing job commits under its own.
- Name the domain in the words [GLOSSARY.md](GLOSSARY.md) defines (board,
  board day, star band, hold, publish). They are RisingRepos's words, defined
  here in this repository's own wording.

## Build and test

```sh
uv sync --locked                                      # the pinned dependencies, into .venv
uv run --locked python -m sitework check              # every check a change has to pass, the cheapest first
uv run --locked python -m unittest discover -s tests  # the agents' tests alone. They need Node on the PATH, and Chrome
uv run --locked python -m unittest discover -s owner_tests -t .  # the owner's tests alone, in the machine's Chrome
uv run --locked ruff format .                         # lay the Python out as the format check asks
uv run --locked coverage run -m unittest discover -s tests  # the agents' tests, noting each line and branch they ran
uv run --locked coverage combine                      # gather what each Python a test started noted
uv run --locked coverage report                       # which lines and branches of sitebuild/ and sitework/ no test ran
uv run --locked python -m sitebuild dist              # the pages; it refuses a dist/ that already holds files
python -m http.server 8000 --bind 127.0.0.1 --directory dist  # then open http://127.0.0.1:8000/
```

The build job runs `python -m sitework check --suite`: the lint, the format,
and both kinds of tests. So the check command is what a PR has to pass. Run
it before each commit.

The coverage report is there to be read, and nothing requires a share of
it: no check, no job, and no pull request is held to a number (#49). A line
that no test ran is worth a look. A line that ran was not thereby checked.

Without `--suite`, a change that touches no guarded path is not run against
the tests of the workflow's own scripts and of the stale check: no such
change can alter what they find. The build job runs every test.

## The two kinds of tests

- **The agents' tests**, in `tests/`, hold a page's exact markup and how each
  part is built. Write, change, and remove them as a change needs. Every one
  still has to pass.
- **The owner's tests**, in `owner_tests/`, are plain sentences about what a
  reader can do on the site, driven through a real browser.
  [owner_tests/README.md](owner_tests/README.md) lists them. A change may add
  to that folder and changes nothing that is there. One that fails means a reader
  lost something: mend the code, never the test.

## A new test earns its place

A test is kept for the fault it catches. Before you add one to the agents'
tests, show three things (#48, #51):

- **It names the behaviour.** Its name is the sentence of the issue or the
  plan that it holds, and the value it expects comes from that sentence,
  never from a run of the new code.
- **It can fail.** Take away the one condition it is about, see it fail for
  that reason, and put the condition back. Take the condition away, and do
  not only turn it round: most tests notice a condition that was turned
  round, and only the test that holds a refusal notices one that is gone.
  `sitework new-tests` asks a different question, whether the test fails on
  the commit before, and stays.
- **No test already there fails with it.** While the condition is away, run
  the tests the file had. If one of them fails too, the fault is held
  already: add nothing, or give that test the name that says so.

No number is set on the tests. A test that restates the code, by expecting
whatever the code gave or by checking that a call was made as it is
written, catches nothing and is not added.

## Before you start a branch

Fetch from GitHub first, every time, and start the branch from the newest
`origin/main`, so that the work begins from what is on GitHub and not from
what this machine last saw. The publishing job pushes a board day to `main`
each day, so a copy that was current yesterday is behind today. Before taking
up a branch that already exists, pull it.

## When a piece of work is done

Commit it and push its branch, without waiting to be asked, so that finished
work does not sit on one machine alone. Run the whole suite first, and read
each commit before it is pushed, since a push is public at once. The work goes
to its own branch and never straight to `main`: a push there is a deploy, and
work reaches `main` through a pull request.

## Read before you act

| Before you | Read |
| --- | --- |
| Plan a change, or review one | [STANDARDS.md](STANDARDS.md): every standard the change touches. Each says whether a test or the reviewer holds it |
| Build against how the site is made, or wonder why it is made so | The record in [docs/adr/](docs/adr/README.md). A change that goes against a record waits for the owner |
| Name a thing in an issue, a comment, or the code: a board, a row, a part of a page | [GLOSSARY.md](GLOSSARY.md) |
| Change how a page looks: its markup, `site.css`, a colour, a size, a face | [STYLE.md](STYLE.md), the style guide, for what a new part reaches for. It guides, and does not bind. Then README.md, "The design note". A change to the look rewrites the note in the same PR, and `tests/test_colour.py` holds every colour pair the note lists |
| Change what a page says or shows, what its script does, or add a page | README.md, "The pages" |
| Show text a repository's owner wrote, or read a value from the address or the browser's storage | [STANDARDS.md](STANDARDS.md), P5, P21, and P22: that text and those values are not trusted. P1 and P2 hold what a page may run and request |
| Change how the data files are read or checked | README.md, "The data" |
| Take an approved idea from its issue to the live site | [docs/workflow/README.md](docs/workflow/README.md), and nothing here replaces it |
| Edit a workflow | The comment at the top of that workflow, then README.md, "The workflow". A workflow is a guarded path, which a feature leaves alone, and [STANDARDS.md](STANDARDS.md), C7 and C8, hold what its jobs may run |
| Add or change a line of a workflow or of the eval's code that names risingrepos.com or the preview, or sets the Pages branch | RUNBOOK.md, "The lines the switch changes". `tests/test_runbook.py` holds that table to the files |
| Change the site eval or its limits | [evals/site/README.md](evals/site/README.md) |
| Change the stale check | README.md, "The stale check" |
| Move a pinned version: a Python package, uv, an action, wrangler, or Lighthouse | README.md, "Changing a pinned version" |
| Touch the type: a face, a character the site's own text newly uses, a font file | The docstring of `sitebuild/fonts/subset.py`, then README.md, "The design note", under "Type" |
| Handle a credential: the Cloudflare token or the Discord webhook | [STANDARDS.md](STANDARDS.md), C6, for the rule. RisingRepos: `docs/agents/secrets.md` for how a value is stored, handed to a command, and checked |

## Where a change most often goes wrong

- **A page has little room left.** `tests/test_page_weight.py` holds a page to
  500,000 bytes and the root of a 713-row board to 150,000 gzipped, and both
  are within about 4% of their limits. README.md, "The pages", under "Its
  size" and "The root on the wire", gives the last measurements. Markup added
  to a board's row is multiplied by every row, so measure before and after:
  `python -m sitework weigh` prints both. A
  gzipped size measured on Windows reads about 2% lower than the workflow's.
- **The page requests nothing.** Its styles, its one script, its icon, and its
  type are inside it, and its Content-Security-Policy allows that script by
  the hash of its text. A second script, an inline event handler, or a request
  to another site is refused by the browser. The policy lets a board with rows
  fetch from the site's own address, which the script uses for the board day's
  `history.json` alone. A change that breaks this fails
  `tests/test_page_weight.py` or the policy's tests in
  `tests/test_old_board.py`.
- **The type is a renamed cut of IBM Plex.** The licence reserves the name
  "Plex" to the original, so the files here are Rising Sans and Rising Mono.
  Commit a font file only under a `rising-` name, made by
  `sitebuild/fonts/subset.py`.
- **A page is whole with scripts off.** The script adds the filters, the sort,
  the search, and an opened row's detail to a board that already lists every
  row. Check a change to a board with scripts off as well as on.

## How this repository is written

- Comments, docstrings, docs, and commit bodies are plain, complete sentences
  that say why, and cite the issue that decided the point. Match the file you
  are in.
- A commit subject is one plain sentence in the imperative, with no type
  prefix: "Count only the requests the page sent in the site eval".
- Prose uses British spelling: colour, practise.
- [STANDARDS.md](STANDARDS.md), part 3, holds these three rules and the rest
  that a change to the code or the words is held to.
