"""`notes`: push a run's notes to main, in a commit that holds nothing else.

The notes of a run are files in this repository: one for the run, named for its issue, and one row in a table
that holds a row for every feature (docs/workflow-plan.md, section 18). They reach main after the feature has,
straight from this script and through no pull request. Three things make that safe.

The commit is made in a temporary worktree of `origin/main`, so that the agent's own tree, with whatever it holds,
is left as it is and none of it rides along.

The script refuses a commit that touches any path outside the notes' folder, and pushes nothing. A push to main
of anything else is a deploy, and the deploy workflow leaves out that folder alone.

The script waits for the deploy of the commit beneath its own before it pushes, and pushes only when that deploy
ended in success. A run of the deploy workflow uploads its pages only while its commit is still the head of main,
and a commit of notes starts no run. So notes pushed on top of a commit whose run has yet to reach its upload
would make that run find main moved on and upload nothing, with no later run to upload those pages: a board day
could be left off the site until the next one. A run that failed is the same hazard, since running it again is
how its pages get uploaded, and it could no longer upload them from beneath the notes.
"""

import argparse
import codecs
import re
import sys
import time
from pathlib import Path

from sitework import confirm, rules, shell
from sitework.digest import FIGURES, FIGURES_HEADING, FIGURES_RULE

RUN = rules.NOTES + "runs/{issue}.md"
FEATURES = rules.NOTES + "features.md"
SUBJECT = "Add the notes of the run on #{issue}"

FEATURES_OPENING = f"""# The figures of every feature

One row for each run of the site's feature workflow, added with the run's notes by `python -m sitework notes`.
A figure in tokens is the sum of the four kinds a message is charged for, and `runs/` holds each run's digest.

{FIGURES_HEADING}
{FIGURES_RULE}
"""

DEPLOY = "deploy.yml"
"""The workflow whose run uploads a commit's pages."""
WAIT = 20
LOOKS = 61
"""The deploy's run is looked at every 20 seconds for 20 minutes, which is 61 looks. A build and its upload take
a few minutes, and GitHub takes some seconds after a push to make the run at all."""


class Refused(Exception):
    """The notes cannot be pushed as they were given. The message says why."""


def wait(seconds: int) -> None:
    """The pause between two looks at the deploy's run, as a name of its own so that a test can replace it."""
    time.sleep(seconds)


def read_text(path: Path) -> str:
    """A file's words, whichever of the encodings a shell on Windows writes with `>` it is in, and with the ends
    of its lines as git keeps them."""
    written = path.read_bytes()
    wide = written.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE))
    return written.decode("utf-16" if wide else "utf-8-sig").replace("\r\n", "\n")


def figures_row(digest: str, issue: int) -> str:
    """The feature's row from the digest's table of figures. A digest without the table, or one made for another
    issue or for none, is refused, so that the table of every feature never gets a row that names no feature."""
    lines = [line.strip() for line in digest.partition(FIGURES)[2].splitlines() if line.strip()]
    if lines[:2] != [FIGURES_HEADING, FIGURES_RULE] or len(lines) < 3 or not lines[2].startswith("|"):
        raise Refused(f"the digest has no table under `{FIGURES}` with the heading row `sitework digest` writes")
    if lines[2].split("|")[1].strip() != f"#{issue}":
        raise Refused(f"the digest's figures are not those of #{issue}: make it with `--issue {issue}`")
    return lines[2]


def with_row(features: str | None, row: str) -> str:
    """The table of every feature with `row` under its last row. `features` is the file as it stands, or None
    when there is none yet. A row that is already there is not added again, so that the same notes pushed twice
    change nothing the second time."""
    lines = (features or FEATURES_OPENING).splitlines()
    if row in lines:
        return features
    last = max((number for number, line in enumerate(lines) if line.startswith("|")), default=None)
    if last is None:
        lines += ["", FIGURES_HEADING, FIGURES_RULE]
        last = len(lines) - 1
    return "\n".join([*lines[: last + 1], row, *lines[last + 1 :]]) + "\n"


def outside(paths: list[str]) -> list[str]:
    """Each of `paths` that is not in the notes' folder."""
    return [path for path in paths if not path.startswith(rules.NOTES)]


def write_notes(tree: Path, issue: int, notes: str, digest: str, row: str) -> None:
    """Write the run's file and the feature's row into a checkout. The run's file is a heading, the notes, and
    the digest with each of its headings one level down, so that the file has one title."""
    run = tree / RUN.format(issue=issue)
    run.parent.mkdir(parents=True, exist_ok=True)
    lowered = re.sub(r"(?m)^#", "##", digest.strip())
    run.write_text(f"# The run on #{issue}\n\n{notes.strip()}\n\n{lowered}\n", encoding="utf-8", newline="\n")
    features = tree / FEATURES
    table = with_row(features.read_text(encoding="utf-8") if features.exists() else None, row)
    features.write_text(table, encoding="utf-8", newline="\n")


def deploy_runs(commit: str) -> list[dict]:
    """Each run of the deploy workflow that GitHub holds for the push of `commit` to main, with its status, how
    it ended, and when it was made. Only a push counts, as in `confirm.deploy_run`: a pull request from a fork's
    own main also names main as its branch, and its run uploads nothing. Counted here, a stranger's run could
    hold the notes back, or stand in for a deploy that failed."""
    return shell.gh_json(
        "run",
        "list",
        "--workflow",
        DEPLOY,
        "--branch",
        "main",
        "--event",
        "push",
        "--commit",
        commit,
        "--json",
        "status,conclusion,databaseId,createdAt",
    )


def deploy_end(commit: str) -> str | None:
    """Wait until every run of the deploy workflow for `commit` has ended, and give how the newest of them ended,
    in GitHub's word for it: `success`, `failure`, `cancelled`, and so on. None when they had not ended in time.
    No run at all is waited for like one in progress, since GitHub makes a run some seconds after the push. The
    newest run is the one that counts, since a run made later for the same commit is a second try at its deploy."""
    for look in range(LOOKS):
        if look:
            wait(WAIT)
        runs = deploy_runs(commit)
        if runs and all(run["status"] == "completed" for run in runs):
            return max(runs, key=lambda run: run["createdAt"])["conclusion"]
    return None


def push(issue: int, notes: str, digest: str, row: str) -> int:
    """Make the commit on the head of main and push it. When main moved between the fetch and the push, do the
    whole of it once more on the new head: the wait for that head's deploy, and the commit, made again from the
    files as they now stand, since the push that moved main may have added a row of its own."""
    for _ in range(2):
        shell.git("fetch", "--quiet", "origin", "main")
        head = shell.git("rev-parse", "origin/main")
        # The head itself may be a commit of notes, which no run was made for. `confirm` finds the commit beneath
        # it that a run was made for, and it is asked here so that both scripts follow the same one.
        deploying = confirm.deploy_commit(head)
        ended = deploy_end(deploying)
        if ended != "success":
            why = (
                f"had not ended after {WAIT * (LOOKS - 1) // 60} minutes, so nothing is pushed: notes pushed on "
                "top of it would keep its pages from being uploaded."
                if ended is None
                else f"ended as {ended}, so nothing is pushed: that commit's pages are not live, and notes pushed "
                "on top of it would stop a re-run of its deploy from uploading them."
            )
            print(f"notes: the deploy of {deploying[:7]} {why}", file=sys.stderr)
            return 1
        with shell.worktree(head) as tree:
            write_notes(tree, issue, notes, digest, row)
            shell.git("add", "--all", cwd=tree)
            if not shell.git("status", "--porcelain", cwd=tree):
                print(f"The notes of the run on #{issue} are already on main.")
                return 0
            shell.git("commit", "--quiet", "--message", SUBJECT.format(issue=issue), cwd=tree)
            stray = outside(shell.git("diff", "--name-only", head, "HEAD", cwd=tree).splitlines())
            if stray:
                print(
                    f"notes: refused, and nothing is pushed. The commit touches paths outside {rules.NOTES}: "
                    + ", ".join(stray),
                    file=sys.stderr,
                )
                return 1
            made = shell.git("rev-parse", "HEAD", cwd=tree)
            try:
                shell.git("push", "--quiet", "origin", "HEAD:main", cwd=tree)
            except shell.Failed:
                shell.git("fetch", "--quiet", "origin", "main")
                if shell.git("rev-parse", "origin/main") == head:
                    raise  # main stood still, so the push was refused for a reason a second try would not change
                continue
        print(f"Pushed the notes of the run on #{issue} to main as {made[:7]}.")
        return 0
    print("notes: main moved before each of two pushes, so nothing is pushed. Run it again.", file=sys.stderr)
    return 1


def main(command: str, arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="Push a run's notes to main, in a commit that holds nothing else, once the deploy beneath it "
        "has ended in success.",
    )
    parser.add_argument("issue", type=int, help="the number of the run's issue")
    parser.add_argument("--digest", type=Path, required=True, metavar="FILE", help="what `sitework digest` printed")
    parser.add_argument("--notes", type=Path, required=True, metavar="FILE", help="the look back's lines")
    options = parser.parse_args(arguments)
    try:
        digest, notes = read_text(options.digest), read_text(options.notes)
        row = figures_row(digest, options.issue)
        return push(options.issue, notes, digest, row)
    except (OSError, UnicodeError, Refused, shell.Failed) as error:
        print(f"notes: {error}", file=sys.stderr)
        return 1
