"""`revert`: put the site back by reverting a feature's merge.

When the live check or the site eval fails because of a change, the site is put back first and the owner is
asked second, so that a broken page does not stay live while a question waits (docs/workflow-plan.md,
section 10). This script makes the revert and opens its pull request. The agent then waits for the pull
request's check and runs `ship <issue> --revert`, which merges it without a review.

The revert is made in a temporary worktree from origin/main, so that the agent's own tree, which may hold the
feature's branch and work that is not committed, is left as it is.
"""

import argparse
import sys

from sitework import issue, shell


def revert(number: int) -> int:
    pull = issue.merged(number)
    if pull is None:
        print(f"#{number} has no pull request that merged, so there is nothing to revert.")
        return 1
    merge = pull["mergeCommit"]["oid"]
    title = issue.read(number)["title"]
    branch = issue.branch_start(number) + issue.REVERT
    shell.git("fetch", "origin")
    # The branch follows nothing: made from origin/main with git's defaults, it would name main as where its
    # pushes go.
    with shell.worktree("origin/main", "--no-track", "-B", branch) as tree:
        shell.git("revert", "-m", "1", "--no-edit", merge, cwd=tree)
        shell.git("push", "origin", branch, cwd=tree)
    words = ["--title", f"Revert #{number}: {title}", "--body", f"Refs #{number}"]
    opened = shell.gh("pr", "create", "--base", "main", "--head", branch, *words)
    # `gh pr create` prints the new pull request's address, which ends in its number.
    print(opened.rstrip("/").rsplit("/", 1)[-1])
    return 0


def main(command: str, arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="Revert the merge of the issue's pull request on a branch of its own, and open the pull request "
        "that puts the site back. Print that pull request's number.",
    )
    parser.add_argument("issue", type=int, help="the issue's number")
    options = parser.parse_args(arguments)
    try:
        return revert(options.issue)
    except shell.Failed as error:
        print(error, file=sys.stderr)
        return 1
