"""`comment`, `stop`, and `close`: the workflow's comments and labels on an issue. Also the reading of an issue,
its comments, and its pull requests that the other scripts share.

Agents act under the owner's account, so who wrote a comment does not tell the owner's words from an agent's
(docs/workflow-plan.md, D10). Each comment the workflow writes begins with a fixed first line
(`sitework.rules.first_line`), and a comment by the owner's account without one is the owner's own. The
repository is public and anyone can comment on its issues, so a comment by any other account counts for nothing
here, whatever its first line says. A pull request from a fork counts for nothing either, since anyone can open
one from a branch of any name.
"""

import argparse
import json
import sys
from pathlib import Path

from sitework import notify, rules, shell

REPOSITORY = "repos/{owner}/{repo}"
"""This repository in a path of GitHub's API. `gh api` fills in the two names itself."""

REVERT = "revert"
"""The slug of the branch that reverts a feature's merge. No feature's branch has it."""

PULL = "number,state,headRefName,headRefOid,isCrossRepository,mergeCommit,mergedAt"


def owner() -> str:
    """The account that owns the repository."""
    return shell.gh_json("repo", "view", "--json", "owner")["owner"]["login"]


def read(number: int) -> dict:
    """The issue: its title, its state, its labels, its author, and its address."""
    return shell.gh_json("issue", "view", str(number), "--json", "number,title,state,labels,author,url")


def labels(issue: dict) -> list[str]:
    return [label["name"] for label in issue["labels"]]


def comments(number: int, owner: str) -> list[dict]:
    """The comments on the issue that the owner's account wrote, oldest first."""
    every = shell.gh_json("api", f"{REPOSITORY}/issues/{number}/comments?per_page=100", "--paginate")
    return [comment for comment in every if comment["user"]["login"] == owner]


def of_kind(comments: list[dict], kind: str) -> list[dict]:
    """The workflow's comments of one kind among the owner's account's, oldest first."""
    return [comment for comment in comments if rules.kind_of(comment["body"]) == kind]


def owners_own(comments: list[dict]) -> list[dict]:
    """The owner's own comments among the owner's account's: those the workflow did not write."""
    return [comment for comment in comments if rules.kind_of(comment["body"]) is None]


def value(body: str, name: str) -> str | None:
    """What a comment gives for `name`: the rest of its first line that begins `<name>: `. This is how a comment
    holds what a script reads back from it, such as `Verdict: pass`."""
    start = f"{name}: "
    for line in body.splitlines():
        if line.strip().startswith(start):
            return line.strip()[len(start) :].strip()
    return None


def post(number: int, kind: str, text: str) -> str:
    """Post the workflow's comment of this kind on the issue, and say what was done. A plan is rewritten as the
    owner's answers come in, so the plan comment that is already there is edited in place: an issue then holds
    one plan, and a script that reads the plan reads the current one."""
    body = f"{rules.first_line(kind)}\n\n{text.strip()}\n"
    if kind == "plan":
        there = of_kind(comments(number, owner()), kind)
        if there:
            path = f"{REPOSITORY}/issues/comments/{there[-1]['id']}"
            shell.gh("api", "--method", "PATCH", path, "--input", "-", stdin=json.dumps({"body": body}))
            return f"edited the {kind} comment: {there[-1]['html_url']}"
    return f"posted the {kind} comment: {shell.gh('issue', 'comment', str(number), '--body-file', '-', stdin=body)}"


def pulls(state: str = "all") -> list[dict]:
    """Every pull request into main in this state, oldest first. One into another branch is none of the
    workflow's: its merge would deploy nothing."""
    found = shell.gh_json("pr", "list", "--state", state, "--base", "main", "--limit", "1000", "--json", PULL)
    return sorted(found, key=lambda pull: pull["number"])


def branch_start(number: int) -> str:
    """How the name of every branch of the issue begins."""
    return rules.BRANCH.format(issue=number, slug="")


def feature(pulls: list[dict], number: int) -> list[dict]:
    """The feature's pull requests among `pulls`: those from this repository's own branches `agent/<number>-...`,
    but for the branch that reverts it."""
    start = branch_start(number)
    return [
        pull
        for pull in pulls
        if pull["headRefName"].startswith(start)
        and pull["headRefName"] != start + REVERT
        and not pull["isCrossRepository"]
    ]


def revert(pulls: list[dict], number: int) -> list[dict]:
    """The pull requests among `pulls` that revert the feature's merge."""
    branch = branch_start(number) + REVERT
    return [pull for pull in pulls if pull["headRefName"] == branch and not pull["isCrossRepository"]]


def merged(number: int) -> dict | None:
    """The feature's pull request that merged, the newest when a feature was merged more than once. None when
    none has."""
    found = feature(pulls("merged"), number)
    return max(found, key=lambda pull: pull["mergedAt"]) if found else None


def tell(issue: dict, what: str) -> None:
    """Tell the owner on Discord what became of the issue. A message that cannot be sent is a warning, and fails
    nothing: what was done on the issue is done, and the issue itself says it."""
    said = notify.send(f"{rules.FIRST_LINE}#{issue['number']} {what}. {issue['title']}\n{issue['url']}")
    if said != "sent":
        print(f"warning: the owner was not told on Discord ({said})")


def comment(options: argparse.Namespace, text: str) -> int:
    print(post(options.issue, options.kind, text))
    return 0


def stop(options: argparse.Namespace, text: str) -> int:
    """Stop the issue for the owner, or for data it waits on (docs/workflow-plan.md, sections 12 and 14)."""
    number = str(options.issue)
    if options.data is not None:
        waiting = f"Waiting on RisingRepos#{options.data}.\nField: {options.field}\n\n{text}"
        print(post(options.issue, "waiting on data", waiting))
        shell.gh("issue", "edit", number, "--remove-label", rules.IN_PROGRESS, "--add-label", rules.BLOCKED_ON_DATA)
        return 0
    issue = read(options.issue)
    print(post(options.issue, "stopped", f"Stage: {options.stage}\n\n{text}"))
    shell.gh("issue", "edit", number, "--remove-label", rules.IN_PROGRESS, "--add-label", rules.NEEDS_OWNER)
    tell(issue, f"stopped at {options.stage} and waits for your answer")
    return 0


def close(options: argparse.Namespace, text: str) -> int:
    """Post what shipped, close the issue, and remove its branch (docs/workflow-plan.md, section 10)."""
    number = str(options.issue)
    pull = merged(options.issue)
    if pull is None:
        print(f"#{number} has no pull request that merged, so nothing shipped and nothing was changed.")
        return 1
    issue = read(options.issue)
    print(post(options.issue, "shipped", text))
    shell.gh("issue", "close", number)
    shell.gh("issue", "edit", number, "--remove-label", rules.IN_PROGRESS)
    if shell.git("ls-remote", "origin", f"refs/heads/{pull['headRefName']}"):
        shell.git("push", "origin", "--delete", pull["headRefName"])
    tell(issue, "shipped")
    return 0


def main(command: str, arguments: list[str]) -> int:
    what = {
        "comment": "Post one of the workflow's comments on an issue. A plan that is already there is edited in place.",
        "stop": "Stop an issue for the owner, or with --data for a field it waits on.",
        "close": "Post what shipped, close the issue, and remove its branch from origin.",
    }
    parser = argparse.ArgumentParser(prog=f"python -m sitework {command}", description=what[command])
    parser.add_argument("issue", type=int, help="the issue's number")
    if command == "comment":
        parser.add_argument("kind", choices=rules.KINDS, help="which of the workflow's comments this is")
    if command == "stop":
        why = parser.add_mutually_exclusive_group(required=True)
        why.add_argument("--stage", type=str.lower, choices=rules.STAGES, help="the stage that stops for the owner")
        why.add_argument("--data", type=int, metavar="N", help="the RisingRepos issue that will bring the field")
        parser.add_argument("--field", metavar="NAME", help="with --data, the field the issue waits for")
    parser.add_argument("--file", type=Path, required=True, metavar="F", help="the file that holds the comment's text")
    options = parser.parse_args(arguments)
    if command == "stop" and (options.data is None) != (options.field is None):
        parser.error("--data and --field are given together")
    text = options.file.read_text(encoding="utf-8")
    try:
        return {"comment": comment, "stop": stop, "close": close}[command](options, text)
    except shell.Failed as error:
        print(error, file=sys.stderr)
        return 1
