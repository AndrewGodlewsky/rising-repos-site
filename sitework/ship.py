"""`ship`: merge a feature's pull request once every condition of the merge holds.

No person takes part in a merge, and a merge is a deploy, so this script is the gate (docs/workflow-plan.md,
section 9). It prints a line for each condition, `holds:` or `fails:`, and merges only when every one holds. It
merges exactly the commit it judged: GitHub refuses the merge when the pull request's head is no longer that
commit. GitHub holds a merge to nothing of main, so the script reads main once more just before it merges, and
merges nothing when main has moved since the conditions were judged. With `--revert` it merges the pull request
that reverts the feature, which no reviewer reads, so that a broken page does not stay live while a question
waits. That pull request has to hold exactly the revert of every merge of the feature that stands on main, which
is two merges when a mend of the feature was merged as well, and nothing else. Once it has merged, its branch is
deleted on GitHub and in this repository, since nothing else removes that branch.
"""

import argparse
import functools
import re
import sys
import tarfile
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path

from sitework import issue, rules, shell

SCRIPTS = __package__
"""The folder of the workflow's scripts, which is also the name they are run by."""

COMMIT = re.compile(r"[0-9a-f]{40}")
"""A commit by its whole name. A review names the commit it passed this way and no shorter, because a head whose
name begins with a few given digits can be made on purpose, and would then count as the commit that was read."""


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
    to main does not need a second review.

    The review also has to be of the plan as it now is. The plan is one comment that is edited in place, and
    `criteria` holds the change to whatever it says today, so a plan edited after the review could turn a proof
    into something only looked at, and the review would still read as a pass. GitHub writes both moments as UTC
    in one form, so they compare as text."""
    reviews = issue.of_kind(said, "review")
    if not reviews:
        return False, "the issue has no review comment"
    verdict, commit = (issue.value(reviews[-1]["body"], name) for name in ("Verdict", "Commit"))
    if verdict != "pass":
        return False, f"the newest review's verdict is {verdict or 'not given'}, and not pass"
    plans = issue.of_kind(said, "plan")
    if plans and plans[-1]["updated_at"] > reviews[-1]["created_at"]:
        return False, "the plan was edited after the newest review, which passed the plan as it was before"
    if not commit or not COMMIT.fullmatch(commit):
        return False, "the newest review passed, and names no commit by all of its 40 hex digits"
    if commit == head:
        return True, f"the newest review passed {head[:7]}"
    if patch_id(commit) == patch_id(head):
        return True, f"the newest review passed {commit[:7]}, and {head[:7]} carries the same change"
    return False, f"the newest review passed {commit[:7]}, and {head[:7]} carries another change"


def patch_id(commit: str) -> str:
    """What names a commit's change whatever it is based on: git's patch id of the diff from where the commit left
    main. White space is kept, because in Python a line's indentation is part of what it means, and the ids git
    gives without it are the same for a line moved into or out of a block.

    Git writes the diff to a file and reads it back from that file, so the diff is never text in between. Read
    as text, a byte that is not UTF-8 is replaced and a line's end is rewritten, and two changes that differ only
    there would share one id. A file that is not text is in the diff as well, with the whole names of what it
    held before and after, so that a change to one is part of the id too."""
    base = shell.git("merge-base", "origin/main", commit)
    with tempfile.TemporaryDirectory() as folder:
        diff = Path(folder) / "change.diff"
        shell.git("diff", "--full-index", "--binary", f"--output={diff}", base, commit)
        return shell.run("git", "patch-id", "--verbatim", stdin=diff).split(" ")[0]


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
    owner's own comments that begins `Allowed:`, with commas between them.

    The patterns reach `guard` as the words after `--allow`, where one that begins with a dash would be read as
    an option of the command and not as a pattern. Such a pattern is left out, and allows nothing."""
    lines = [line.strip() for comment in issue.owners_own(said) for line in comment["body"].splitlines()]
    named = [line[len(rules.ALLOWED) :].split(",") for line in lines if line.startswith(rules.ALLOWED)]
    patterns = [pattern.strip() for found in named for pattern in found]
    return [pattern for pattern in patterns if pattern and not pattern.startswith("-")]


def allowed_for(number: int, comments: Callable[[int], list[dict]]) -> list[str]:
    """The patterns the owner allowed for the change of this issue's run: on the lead and on each partner, whose
    work is in the same change (25 November 2026). `check` asks it on the machine, and the merge asks it, so that
    the two never differ on what the guard lets through."""
    group = issue.partners(number, comments)
    return allowed([*comments(number), *(comment for partner in group for comment in comments(partner))])


def guarded(base: str, head: str, patterns: list[str]) -> tuple[bool, str]:
    """`guard` passes, as main's copy of it reads the change. The branch's own copy could have been loosened by
    the change it judges, so the scripts are taken out of main into a temporary folder and run from there. A main
    that holds no scripts has no guard to ask, and the condition fails there: the copy the head holds is never
    run, since that would let a branch be judged by its own guard."""
    if not shell.git("ls-tree", "--name-only", "origin/main", SCRIPTS):
        return False, f"main holds no guard to read the change, since it has no {SCRIPTS}/"
    with tempfile.TemporaryDirectory() as folder:
        archive, copy = Path(folder) / "scripts.tar", Path(folder) / "copy"
        shell.git("archive", f"--output={archive}", "origin/main", SCRIPTS)
        with tarfile.open(archive) as held:
            held.extractall(copy, filter="data")
        change = ["--repository", str(shell.ROOT), "--base", base, "--head", head]
        allow = ["--allow", *patterns] if patterns else []
        try:
            shell.run(sys.executable, "-m", SCRIPTS, "guard", *change, *allow, cwd=copy)
        except shell.Failed as error:
            return False, f"main's copy of guard does not pass the change:\n{error}"
    return True, "main's copy of guard finds no guarded path that the owner has not allowed"


def reverts(number: int, main: str, head: str) -> tuple[bool, str]:
    """The pull request holds exactly what reverting every merge of the feature that stands gives on the head of
    main, and nothing else. No reviewer reads a revert, so without this the lane would merge whatever was pushed
    to the branch a revert is expected on.

    A feature whose mend failed has two merges that stand, its own and the mend's, and the site is put back only
    when both are undone: a pull request that reverts the mend alone leaves the broken feature live, and does not
    hold. A merge that an earlier revert undid does not stand, so a feature that was landed a second time is not
    held to undoing its first merge again. Git reverts the merges in the order they are given, and they are given
    newest first, because a later merge was made on top of an earlier one.

    This stands where `guard` does for a feature, and `guard` is not run on a revert. Each merge that is undone
    passed `guard`, so undoing exactly those merges takes nothing from what judges a feature. And `guard` would
    refuse the revert of a feature whose reviewer added one of the owner's tests, since the revert takes those
    lines out again, and the broken page would stay live for it.

    The revert is made in a worktree of its own and is never committed: the tree git would commit is all that
    the pull request's tree is held against."""
    merges = [pull["mergeCommit"]["oid"] for pull in issue.standing(number)]
    if not merges:
        none = f"#{number} has no merged pull request that a revert has not undone"
        return False, f"{none}, so there is nothing for {head[:7]} to revert"
    named = f"{'merge' if len(merges) == 1 else 'merges'}, {' and '.join(merge[:7] for merge in merges)}"
    revert = f"the revert of #{number}'s {named}, on the head of main, {main[:7]}"
    with shell.worktree(main) as tree:
        try:
            shell.git("revert", "-m", "1", "--no-commit", *merges, cwd=tree)
        except shell.Failed as error:
            return False, f"{revert}, cannot be made, so there is nothing to hold {head[:7]} against:\n{error}"
        reverted = shell.git("write-tree", cwd=tree)
    if shell.git("rev-parse", f"{head}^{{tree}}") != reverted:
        return False, f"{head[:7]} holds something other than {revert}"
    return True, f"{head[:7]} holds exactly {revert}"


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


def delete_branch(branch: str) -> list[str]:
    """Delete the branch of a revert that has merged, on GitHub and in this repository, and give a line to print
    for each of the two that still has it.

    The owner asked on 24 November 2026 that a finished run leave no branch lying about, and nothing else removes
    this one: `close` deletes a feature's branch, and it is not run for a feature that was put back. A feature's
    own branch is not deleted here, because a mend is made on it.

    The merge is made by the time this runs, and it is not undone for a branch. So a branch that is already gone
    is no error, and a delete that is refused is a line to print and no failure. The branch in this repository
    goes as `issue.delete_local` has it, which also leaves one that holds a commit main does not."""
    on_github = None
    try:
        if shell.git("ls-remote", "origin", f"refs/heads/{branch}"):
            shell.git("push", "origin", "--delete", branch)
    except shell.Failed as error:
        on_github = f"The branch {branch} is left on GitHub, since git did not delete it: {issue.one_line(error)}"
    return [left for left in (on_github, issue.delete_local(branch)) if left]


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
    # A revert turns on no comment: it needs no review, and nothing the owner allowed is asked about. It undoes the
    # lead's merges, which hold its partners' work, so it asks nothing of the partners either.
    owner = None if reverting else issue.owner()
    comments = functools.cache(lambda one: issue.comments(one, owner))
    said = [] if reverting else comments(number)
    group = [] if reverting else issue.partners(number, comments)

    def conditions() -> Iterator[tuple[bool, str]]:
        yield checks(read["statusCheckRollup"], head)
        if not reverting:
            yield reviewed(said, head)
        contains = "contains" if base == main else "does not contain"
        yield base == main, f"{head[:7]} {contains} the head of main, {main[:7]}"
        yield approved(the_issue)
        if reverting:
            yield reverts(number, main, head)
            return
        # A partner's work is in this pull request, so the merge holds each partner to what holds the lead
        # (25 November 2026). One the owner closed or withdrew is sent back, and its part taken out, before a merge.
        for partner in group:
            holds, what = approved(issue.read(partner))
            back = f": send it back with `sitework release {partner}` and take its part out of the branch"
            yield holds, what if holds else what + back
        yield guarded(base, head, allowed_for(number, comments))
        yield checkout(head)
        yield passes("new-tests", "--base", base, "--head", head, "--issue", str(number))
        yield passes("criteria", "--issue", str(number))

    every = True
    for holds, what in conditions():
        print(f"{'holds' if holds else 'fails'}: {what}", flush=True)
        every = every and holds
    if not every:
        print("Nothing was merged.")
        return 1
    # The conditions take a while to judge, and a board day is pushed to main every day. GitHub holds a merge to
    # the pull request's head and to nothing of main, so main is read from GitHub once more, as late as it can
    # be. A push in the moment between this and the merge is still not seen.
    now = shell.git("ls-remote", "origin", "refs/heads/main").split("\t")[0]
    if now != main:
        moved = f"main moved from {main[:7]} to {now[:7] or 'no commit'} while the conditions were judged"
        print(f"fails: {moved}, so none of them saw what a merge would now be made onto. Run it again.")
        print("Nothing was merged.")
        return 1
    of = "the revert of " if reverting else ""
    subject = f"Merge {of}#{number}: {the_issue['title']}"
    shell.gh(
        "pr", "merge", pull, "--merge", "--match-head-commit", head, "--subject", subject, "--body", f"Refs #{number}"
    )
    if reverting:
        # The branch goes before the merge commit is read, so that the commit stays the last line printed.
        for left in delete_branch(ours[0]["headRefName"]):
            print(left)
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
    parser.add_argument(
        "--revert", action="store_true", help="merge the pull request that reverts the feature, and delete its branch"
    )
    options = parser.parse_args(arguments)
    try:
        return ship(options.issue, options.revert)
    except shell.Failed as error:
        print(error, file=sys.stderr)
        return 1
