"""`ship`: merge a feature's pull request once every condition of the merge holds.

No person takes part in a merge, and a merge is a deploy, so this script is the gate (docs/workflow-plan.md,
section 9). It prints a line for each condition, `holds:` or `fails:`, and merges only when every one holds. It
merges exactly the commit it judged: GitHub refuses the merge when the pull request's head is no longer that
commit. With `--revert` it merges the pull request that reverts the feature, which no reviewer reads, so that a
broken page does not stay live while a question waits.
"""

import argparse
import re
import sys
import tarfile
import tempfile
from collections.abc import Iterator
from pathlib import Path

from sitework import issue, rules, shell

SCRIPTS = __package__
"""The folder of the workflow's scripts, which is also the name they are run by."""

COMMIT = re.compile(r"[0-9a-f]{7,40}")


def checks(rollup: list[dict], head: str) -> tuple[bool, str]:
    """Every check of the pull request passed for its head, and there is at least one. A check that was skipped
    is neither: the deploy job is skipped on every pull request. One that gives no conclusion has not passed,
    whatever else it says."""
    results = [
        (check.get("name") or check["__typename"], check.get("conclusion") or "no conclusion yet") for check in rollup
    ]
    passed = [name for name, result in results if result == "SUCCESS"]
    others = [f"{name} ({result.lower()})" for name, result in results if result not in ("SUCCESS", "SKIPPED")]
    if others:
        return False, f"a check of the pull request has not passed for {head[:7]}: {', '.join(others)}"
    if not passed:
        return False, f"no check of the pull request passed for {head[:7]}"
    return True, f"every check of the pull request passed for {head[:7]}: {', '.join(passed)}"


def reviewed(said: list[dict], head: str) -> tuple[bool, str]:
    """The newest review passed the head, or a commit that carries the same change, so that a branch brought up
    to main does not need a second review."""
    reviews = issue.of_kind(said, "review")
    if not reviews:
        return False, "the issue has no review comment"
    verdict, commit = (issue.value(reviews[-1]["body"], name) for name in ("Verdict", "Commit"))
    if verdict != "pass":
        return False, f"the newest review's verdict is {verdict or 'not given'}, and not pass"
    if not commit or not COMMIT.fullmatch(commit):
        return False, "the newest review passed, and names no commit"
    if head.startswith(commit):
        return True, f"the newest review passed {head[:7]}"
    if patch_id(commit) == patch_id(head):
        return True, f"the newest review passed {commit[:7]}, and {head[:7]} carries the same change"
    return False, f"the newest review passed {commit[:7]}, and {head[:7]} carries another change"


def patch_id(commit: str) -> str:
    """What names a commit's change whatever it is based on: git's patch id of the diff from where the commit left
    main. White space is kept, because in Python a line's indentation is part of what it means, and the ids git
    gives without it are the same for a line moved into or out of a block."""
    base = shell.git("merge-base", "origin/main", commit)
    diff = shell.git("diff", "--full-index", base, commit)
    return shell.run("git", "patch-id", "--verbatim", stdin=diff + "\n").split(" ")[0]


def approved(the_issue: dict) -> tuple[bool, str]:
    """The issue is open, and the owner has not withdrawn the approval."""
    number = the_issue["number"]
    if the_issue["state"] != "OPEN":
        return False, f"#{number} is {the_issue['state'].lower()}, and not open"
    if rules.APPROVED not in issue.labels(the_issue):
        return False, f"#{number} no longer carries {rules.APPROVED}"
    return True, f"#{number} is open and carries {rules.APPROVED}"


def allowed(said: list[dict]) -> list[str]:
    """The patterns of the guarded paths the owner lets this issue's change touch: those on each line of the
    owner's own comments that begins `Allowed:`, with commas between them."""
    lines = [line.strip() for comment in issue.owners_own(said) for line in comment["body"].splitlines()]
    named = [line[len(rules.ALLOWED) :].split(",") for line in lines if line.startswith(rules.ALLOWED)]
    return [pattern.strip() for patterns in named for pattern in patterns if pattern.strip()]


def guarded(base: str, head: str, patterns: list[str]) -> tuple[bool, str]:
    """`guard` passes, as main's copy of it reads the change. The branch's own copy could have been loosened by
    the change it judges, so the scripts are taken out of main into a temporary folder and run from there. Until
    main holds the scripts, the copy the head holds is all there is."""
    on_main = bool(shell.git("ls-tree", "--name-only", "origin/main", SCRIPTS))
    whose = "main's copy of guard" if on_main else f"the branch's copy of guard, since main has no {SCRIPTS}/ yet,"
    with tempfile.TemporaryDirectory() as folder:
        archive, copy = Path(folder) / "scripts.tar", Path(folder) / "copy"
        shell.git("archive", f"--output={archive}", "origin/main" if on_main else head, SCRIPTS)
        with tarfile.open(archive) as held:
            held.extractall(copy, filter="data")
        change = ["--repository", str(shell.ROOT), "--base", base, "--head", head]
        allow = ["--allow", *patterns] if patterns else []
        try:
            shell.run(sys.executable, "-m", SCRIPTS, "guard", *change, *allow, cwd=copy)
        except shell.Failed as error:
            return False, f"{whose} does not pass the change:\n{error}"
    return True, f"{whose} finds no guarded path that the owner has not allowed"


def checkout(head: str) -> tuple[bool, str]:
    """The checkout this runs in holds the pull request's head, and nothing in it has changed since. `new-tests`
    and `criteria` run in it, and `criteria` runs the plan's tests as they are on disk. In a checkout that is
    behind a commit the reviewer pushed, or whose files were edited, the two would judge something other than the
    commit that is merged."""
    at = shell.git("rev-parse", "HEAD")
    if at != head:
        return False, f"the checkout is at {at[:7]}, and not at the pull request's head, {head[:7]}"
    differs = shell.git("status", "--porcelain")
    if differs:
        return False, f"the checkout's working tree is not clean:\n{differs}"
    return True, f"the checkout is at {head[:7]}, and its working tree is clean"


def passes(name: str, *arguments: str) -> tuple[bool, str]:
    """Another of the workflow's commands exits 0 for this change."""
    try:
        shell.run(sys.executable, "-m", SCRIPTS, name, *arguments)
    except shell.Failed as error:
        return False, f"`{name}` does not pass:\n{error}"
    return True, f"`{name}` passes"


def ship(number: int, reverting: bool) -> int:
    opened = issue.pulls("open")
    ours = issue.revert(opened, number) if reverting else issue.feature(opened, number)
    if len(ours) != 1:
        what = "that revert it" if reverting else "of its own"
        print(f"fails: #{number} has {len(ours)} open pull requests {what}, and a merge needs exactly one")
        return 1
    pull = str(ours[0]["number"])
    read = shell.gh_json("pr", "view", pull, "--json", "headRefOid,statusCheckRollup")
    head = read["headRefOid"]
    shell.git("fetch", "origin")
    main = shell.git("rev-parse", "origin/main")
    base = shell.git("merge-base", "origin/main", head)
    the_issue = issue.read(number)
    said = issue.comments(number, issue.owner())

    def conditions() -> Iterator[tuple[bool, str]]:
        yield checks(read["statusCheckRollup"], head)
        if not reverting:
            yield reviewed(said, head)
        contains = "contains" if base == main else "does not contain"
        yield base == main, f"{head[:7]} {contains} the head of main, {main[:7]}"
        yield approved(the_issue)
        yield guarded(base, head, allowed(said))
        if not reverting:
            yield checkout(head)
            yield passes("new-tests", "--base", base, "--head", head)
            yield passes("criteria", "--issue", str(number))

    every = True
    for holds, what in conditions():
        print(f"{'holds' if holds else 'fails'}: {what}", flush=True)
        every = every and holds
    if not every:
        print("Nothing was merged.")
        return 1
    of = "the revert of " if reverting else ""
    subject = f"Merge {of}#{number}: {the_issue['title']}"
    shell.gh(
        "pr", "merge", pull, "--merge", "--match-head-commit", head, "--subject", subject, "--body", f"Refs #{number}"
    )
    # GitHub has merged by now, so a merge commit it has not named yet is no failure: `confirm` reads it again.
    merge = shell.gh_json("pr", "view", pull, "--json", "mergeCommit")["mergeCommit"]
    print(merge["oid"] if merge else "It is merged, and GitHub has not named the merge commit yet.")
    return 0


def main(command: str, arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="Merge the issue's pull request once every condition of the merge holds. Exit 0 when it merged, "
        "and 1 when a condition fails, having merged nothing.",
    )
    parser.add_argument("issue", type=int, help="the issue's number")
    parser.add_argument("--revert", action="store_true", help="merge the pull request that reverts the feature")
    options = parser.parse_args(arguments)
    try:
        return ship(options.issue, options.revert)
    except shell.Failed as error:
        print(error, file=sys.stderr)
        return 1
