# Working in rising-repos-site

The pages of risingrepos.com: a Python generator (`sitebuild/`) with Jinja2
templates, one stylesheet, and one script, the data it renders (`site-data/`),
and the workflows that test, deploy, and watch the site.
[README.md](README.md) is the full account of each part and why it is so. The
table under "Read before you act" names the section to read for the part you
are changing.

## What a push does

- A push to `main` is a production deploy. The build job tests and builds the
  pages, and the deploy job uploads them to risingrepos.com
  (`.github/workflows/deploy.yml`).
- A push to any other branch runs no workflow. A pull request runs the tests and
  the build, and deploys nothing. One that changes the site eval also runs the
  eval, against the live site. No branch gets a preview deployment: look at
  other work by building it locally.
- The repository is public, and a push is public at once. Pushed history is
  never rewritten, so read each commit, with `git log -p origin/main..HEAD`,
  before it is pushed, and each PR body, review, and comment before it is
  posted.

## The project this repository serves

The site is one part of the RisingRepos project. Its repository,
`AndrewGodlewsky/RisingRepos`, is private, and holds the issues, the project's
own decisions, and the agent process for both repositories. Read its
`AGENTS.md` before starting a task here. A path below written
`RisingRepos: <path>` is in a checkout of it.

- Site work is tracked by an issue in RisingRepos and delivered here, on a
  branch named `agent/<issue>-<slug>`, through a PR. The procedure is
  RisingRepos: `docs/agents/git-workflow.md`, "Work in the site repository".
- Commits and PRs here cite that tracker in full:
  `Refs AndrewGodlewsky/RisingRepos#<n>`.
- Because RisingRepos is private and this repository is public, what is
  written here, in a file, a commit, a PR, a review, or a comment, names a
  RisingRepos issue by its number and says what it decided in other words. It
  quotes neither the issue nor its owner, and holds no path on anyone's
  machine and no personal e-mail address. Commit with your GitHub noreply
  address. The publishing job commits under its own.
- `site-data/` is RisingRepos's output. Its publishing job commits each board
  day straight to `main` here, as `Publish board day <date>`. A change to the
  data contract (`site-data/contract/` and `sitebuild/contract.py`) lands in
  both repositories, in an order that keeps each one working (RisingRepos:
  `docs/adr/0004-the-site-stays-in-its-own-repository.md`).
- Name the domain in the words [GLOSSARY.md](GLOSSARY.md) defines (board,
  board day, star band, hold, publish). They are RisingRepos's words, defined
  here in this repository's own wording.

## Build and test

```sh
uv sync --locked                                      # the pinned dependencies, into .venv
uv run --locked python -m unittest discover -s tests  # every test: about 4½ minutes, and needs Node on the PATH
uv run --locked python -m sitebuild dist              # the pages; it refuses a dist/ that already holds files
python -m http.server 8000 --bind 127.0.0.1 --directory dist  # then open http://127.0.0.1:8000/
```

The test command is the one the build job runs, so it is the check a PR has to
pass. Run the whole suite before each commit.

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
| Edit a workflow | The comment at the top of that workflow, then README.md, "The workflow". A workflow is a security surface (RisingRepos: `docs/agents/review.md`, "Security surfaces") |
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
  to a board's row is multiplied by every row, so measure before and after. A
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
