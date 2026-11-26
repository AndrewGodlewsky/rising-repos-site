"""What the workflow's scripts agree on: the labels, the stages of a run, the first line of each comment the
workflow writes, and the paths a feature leaves alone. One place owns each, so that two scripts never differ on
one."""

IDEA = "site-idea"
APPROVED = "approved"
IN_PROGRESS = "in-progress"
NEEDS_OWNER = "needs-owner"
BLOCKED_ON_DATA = "blocked-on-data"
"""The labels. The idea agent sets the first and the owner's approval the second. The workflow sets and clears the
other three, and never applies `approved`."""

FEEDBACK = "workflow feedback"
"""The label of an issue that holds what a run taught: how the run could have cost less, or what went wrong in
the workflow itself. `sitework feedback` files such an issue and puts this label on it. It is a label of its own,
and not one of the five above, so that the owner and the agent that mends the workflow can list what the runs
taught apart from the ideas for the site. `pickup` takes up only an issue that carries both `site-idea` and
`approved`, and a feedback issue is given neither, so it is never picked up as a feature."""

STAGES = ("shape", "build", "check", "review", "ship", "confirm", "mend")
"""The stages of a run that an issue can stop at, in the order a run meets them (docs/workflow-plan.md, section
14). `stop` takes one of them, and the digest tells a run's stages apart by them. A run meets `mend` only when
`confirm` failed because of the change, since the fault is mended once before the site is put back. It is a stage
of its own so that an issue whose mend failed stops at `mend`, and so that the digest shows what a mend cost
apart from what the feature cost."""

FIRST_LINE = "Site workflow: "
KINDS = (
    "picked up",
    "plan",
    "review",
    "stopped",
    "waiting on data",
    "shipped",
    "reverted",
    "graded",
    "sorted",
    "joined",
    "released",
)
"""Every comment the workflow writes begins with `Site workflow: ` and one of these. Agents act under the owner's
account, so the author of a comment does not tell the owner's words from an agent's: a comment by that account
without this first line is the owner's own.

The last four came on 25 November 2026, when the owner asked that each idea be graded and that ideas which change
the same part of the site be worked in one run. `graded` gives an idea's complexity and effort and why. `sorted`
names, on the idea a run claimed, the ideas that go with it, `joined` marks each of those, and `released` marks
one sent back to wait for a run of its own."""

POINTS = (1, 2, 3, 5, 8, 13)
"""The values a grade gives an idea's complexity and its effort: Fibonacci points, as estimates are made in
software work. The owner asked for them on 25 November 2026, in the place of Low, Medium, and High, so that a
group's size can be added up. An idea of 13 should be split."""

GRADED = "graded"
"""The kind of the comment that grades an idea. A grade is no work begun on the idea, so a script that asks how
far an issue came reads past it."""

COMMENTED = tuple(kind for kind in KINDS if kind not in ("sorted", "joined", "released"))
"""The kinds `sitework comment` posts. The other three go with a change of labels, which `sort` and `release`
make with them, so that a comment never says an idea is in a group when its labels say otherwise."""

LEAD, WITH = "Lead", "With"
"""The names of the lines that tie a group together: `With: #90, #91` on the idea a run claimed, or `With: none`,
and `Lead: #89` on each idea that joined it, was sent back from it, or was stopped with it."""

BACKLOG, WORKING = "Backlog", "In progress"
"""The statuses the scripts set on an issue, by the names GitHub gives them. GitHub shows an issue in progress
under its Active tab and one in the backlog under Open (25 November 2026)."""

BRANCH = "agent/{issue}-{slug}"
"""A feature's branch, made from origin/main."""

OWNERS_TESTS = "owner_tests/"
"""The owner's tests. A change may add to them, which is how the reviewer adds a test for something new, and may
change nothing that is there. `sitework.guard` holds a file of Python there by what it means, since a line that is
added can switch a test off, and any other file by its lines."""

ALLOWED = "Allowed:"
"""A line of the owner's own comment on an issue that begins with this word names the guarded paths the owner
lets that issue's change touch, as patterns with commas between them."""

GUARDED = {
    "a workflow": (".github/**",),
    "a dependency": ("pyproject.toml", "uv.lock", ".python-version", "uv.toml"),
    "the settings of the lint and the format": ("ruff.toml", ".ruff.toml", "*/ruff.toml", "*/.ruff.toml"),
    "how git reads and compares a file": (".gitattributes", "*/.gitattributes"),
    "a size limit": ("tests/test_page_weight.py",),
    "the site eval and its limits": ("evals/**",),
    "a check that holds the guards": (
        "tests/test_workflow.py",
        "tests/test_site_eval.py",
        "tests/test_site_eval_workflow.py",
        "tests/test_stale_check.py",
        "tests/test_tokens.py",
        "tests/test_context.py",
        "tests/test_runbook.py",
        "tests/test_sitework_*.py",
    ),
    "the type": ("sitebuild/fonts/**",),
    "the data RisingRepos publishes": ("site-data/**",),
    "the standards and the decision records": ("STANDARDS.md", "docs/adr/**"),
    "the workflow's own scripts and documents": (
        "sitework/**",
        "docs/workflow/**",
        "docs/workflow-plan.md",
        "AGENTS.md",
        "CLAUDE.md",
        ".claude/**",
    ),
}
"""The guarded paths: what judges a feature, which a feature's change leaves alone unless the owner allowed it.
Each reason a path is guarded, with the patterns of the paths it covers. A pattern is matched against the whole
path as `fnmatch` matches, so its `*` crosses a `/`. The owner's tests and the policy are guarded more narrowly
than a pattern can say, and have their own names. So has what a change adds at the top of the repository, which
no pattern can list, and `sitework.guard` names it.

A `ruff.toml` or a `.ruff.toml` holds the lint's and the format's settings in place of `pyproject.toml`, and a
`uv.toml` those that say how the dependencies are resolved. Ruff takes its settings for a file from the nearest
folder that holds some, and git takes a folder's `.gitattributes` for what is under it, so those two are guarded
in every folder and not at the top alone."""

OWN_TESTS = ("tests/test_sitework_*.py", "tests/test_stale_check.py")
"""The tests of what no feature changes: the workflow's own scripts, and the stale check. Each of these files
is guarded, and so is what it tests, so `sitework check` leaves them out for a change that touches no guarded
path. On 24 November 2026 that was 527 of the 838 agents' tests, and a third of the time they took. They are run
wherever every test is: by a pull request's job, on main, and for a change the owner let touch a guarded path.
`sitework ship` merges nothing whose job did not pass, which also holds the little of them a feature can
reach: the README that one of them reads, and the helpers that some of them import.

The eval's own tests are not among them, though the eval is guarded. They build real pages and measure
them, so a feature can make one fail, and it is better told so on the machine."""

POLICY_IN = "sitebuild/templates/**"
"""Where the policy that lets a page's script run is written: a `<meta>` of a template. That element's text is
guarded, and the rest of a template is not, since a feature may change a page's markup."""


def first_line(kind: str) -> str:
    """The first line of the workflow's comment of this kind."""
    if kind not in KINDS:
        raise ValueError(f"{kind!r} is not a kind of comment the workflow writes")
    return FIRST_LINE + kind


def kind_of(body: str) -> str | None:
    """Which of the workflow's comments this is, from its first line. None for a comment that is not the
    workflow's, which on an issue here is the owner's own."""
    lines = body.strip().splitlines()
    first = lines[0].strip() if lines else ""
    if first.startswith(FIRST_LINE) and first[len(FIRST_LINE) :] in KINDS:
        return first[len(FIRST_LINE) :]
    return None
