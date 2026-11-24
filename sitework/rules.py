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

STAGES = ("shape", "build", "check", "review", "ship", "confirm", "mend")
"""The stages of a run that an issue can stop at, in the order a run meets them (docs/workflow-plan.md, section
14). `stop` takes one of them, and the digest tells a run's stages apart by them. A run meets `mend` only when
`confirm` failed because of the change, since the fault is mended once before the site is put back. It is a stage
of its own so that an issue whose mend failed stops at `mend`, and so that the digest shows what a mend cost
apart from what the feature cost."""

FIRST_LINE = "Site workflow: "
KINDS = ("picked up", "plan", "review", "stopped", "waiting on data", "shipped", "reverted")
"""Every comment the workflow writes begins with `Site workflow: ` and one of these. Agents act under the owner's
account, so the author of a comment does not tell the owner's words from an agent's: a comment by that account
without this first line is the owner's own."""

BRANCH = "agent/{issue}-{slug}"
"""A feature's branch, made from origin/main."""

OWNERS_TESTS = "owner_tests/"
"""The owner's tests. A change may add to them, which is how the reviewer adds a test for something new, and may
change nothing that is there. `sitework.guard` holds a file of Python there by what it means, since a line that is
added can switch a test off, and any other file by its lines."""

NOTES = "docs/workflow-notes/"
"""The look back's notes. A push to main that changes nothing else deploys nothing."""

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
    "the look back's notes": (NOTES + "**",),
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
