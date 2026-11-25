"""`comment`, `stop`, and `close`: the workflow's comments and labels on an issue. Also the reading of an issue,
its comments, and its pull requests that the other scripts share, of the data on main that an issue can wait
for, and the deleting of a finished branch in this repository, which `ship` shares.

Agents act under the owner's account, so who wrote a comment does not tell the owner's words from an agent's
(docs/workflow-plan.md, D10). Each comment the workflow writes begins with a fixed first line
(`sitework.rules.first_line`), and a comment by the owner's account without one is the owner's own. The
repository is public and anyone can comment on its issues, so a comment by any other account counts for nothing
here, whatever its first line says. A pull request from a fork counts for nothing either, since anyone can open
one from a branch of any name.
"""

import argparse
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path

from sitework import rules, shell

REPOSITORY = "repos/{owner}/{repo}"
"""This repository in a path of GitHub's API. `gh api` fills in the two names itself."""

REVERT = "revert"
"""The slug of the branch that reverts a feature's merge. No feature's branch has it: `pickup.branch` gives the
one title that would make it another slug."""

PULL = "number,state,headRefName,headRefOid,isCrossRepository,mergeCommit,mergedAt"

SCHEMA = "site-data/contract/daily.schema.json"
INDEX = "site-data/boards/index.json"
BOARD = "site-data/boards/days/{day}/daily.json"
"""The daily schema, the list of board days, and a board day's file. `sitebuild.contract` reads the same three
from a folder. Here they are read as main holds them on origin, which the checkout this runs in may be behind."""

BEFORE_THE_WORDS = re.compile(r"(?:[\W_]+|\d+[.)])*")
"""What Markdown can put before the first word of a line: the marks of a heading, a quotation, a list, emphasis,
or code, a numbered list's number, and the spaces among them."""


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


def newest(said: list[dict]) -> dict | None:
    """The newest of the workflow's comments among the owner's account's, past any grade. Each run grades the
    ideas that wait, and a grade is no work begun on an idea (25 November 2026), so how far an issue came is read
    from the workflow's other comments."""
    done = [comment for comment in said if rules.kind_of(comment["body"]) not in (None, rules.GRADED)]
    return done[-1] if done else None


def grade(said: list[dict]) -> dict | None:
    """The idea's newest grade, by the lines of it a script reads: its complexity, its effort, the part of the
    site a reader sees it in, and the code it touches. None when it has no grade."""
    graded = of_kind(said, rules.GRADED)
    if not graded:
        return None
    return {name.lower(): value(graded[-1]["body"], name) for name in ("Complexity", "Effort", "Area", "Code")}


def named_with(said: list[dict]) -> list[int]:
    """The ideas the newest `sorted` comment names on its `With:` line, which a run's sort wrote on the idea the
    run claimed. None of them for `With: none`, or when no sort has been written."""
    sorts = of_kind(said, "sorted")
    named = value(sorts[-1]["body"], rules.WITH) if sorts else None
    return [int(found) for found in re.findall(r"#(\d+)", named or "")]


def partners(lead: int, comments: Callable[[int], list[dict]]) -> list[int]:
    """The ideas in the lead's group now: each that the lead's sort named, whose own newest comment of the
    workflow's is `joined`, or `stopped` with its lead, and names this lead. One sent back, stopped alone, or
    shipped has left. `comments` gives the comments the owner's account wrote on an issue, so a stranger's
    `sorted` comment names no partner, as a stranger's comment counts for nothing anywhere here."""
    found = []
    for number in named_with(comments(lead)):
        last = newest(comments(number))
        if (
            last
            and rules.kind_of(last["body"]) in ("joined", "stopped")
            and value(last["body"], rules.LEAD) == f"#{lead}"
        ):
            found.append(number)
    return found


def says_it_is_the_workflows(body: str) -> bool:
    """Whether a comment's first line says the workflow wrote it, however that line is written: with Markdown's
    marks and spaces before it, and in any case. The scripts write the line one way, and `sitework.rules.kind_of`
    knows that way alone. An agent that writes a comment by hand can miss it, with `Site workflow: Review`, with
    `**Site workflow: review**`, or with a kind the workflow does not have, and such a comment is still an
    agent's."""
    lines = body.strip().splitlines()
    first = lines[0] if lines else ""
    return first[BEFORE_THE_WORDS.match(first).end() :].lower().startswith(rules.FIRST_LINE.strip().lower())


def owners_own(comments: list[dict]) -> list[dict]:
    """The owner's own comments among the owner's account's: those whose first line does not say the workflow
    wrote them. The owner's own words can allow a guarded path and answer a stop, so a comment that only nearly
    begins as the workflow's do is left out here too, though it is none of the workflow's kinds."""
    return [comment for comment in comments if not says_it_is_the_workflows(comment["body"])]


def value(body: str, name: str) -> str | None:
    """What a comment gives for `name`: the rest of its first line that begins `<name>: `. This is how a comment
    holds what a script reads back from it, such as `Verdict: pass`."""
    start = f"{name}: "
    for line in body.splitlines():
        if line.strip().startswith(start):
            return line.strip()[len(start) :].strip()
    return None


def arrived(field: str) -> bool:
    """Whether `field` is now a key somewhere in the daily schema and in the newest board day's file. `pickup`
    asks it of the field an issue waits for, and `stop` asks it before an issue is made to wait. Both ask here,
    so that a field one of them finds is a field the other finds."""
    shell.git("fetch", "origin", "main")
    if not holds(on_main(SCHEMA), field):
        return False
    newest = max(day["board_day"] for day in on_main(INDEX)["board_days"])
    return holds(on_main(BOARD.format(day=newest)), field)


def on_main(path: str):
    return json.loads(shell.git("show", f"origin/main:{path}"))


def holds(value, key: str) -> bool:
    """Whether `key` is a key of this JSON value, or of any object inside it."""
    if isinstance(value, dict):
        return key in value or any(holds(inner, key) for inner in value.values())
    if isinstance(value, list):
        return any(holds(inner, key) for inner in value)
    return False


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


def can_be_of(pull: dict, number: int) -> bool:
    """Whether a pull request can be the issue's at all: it is from one of this repository's own branches, and
    it was opened after the issue. An issue and a pull request take their numbers from one sequence here, and a
    pull request is opened after its issue, so one whose number is not higher than the issue's is older than the
    issue. The name of the branch alone does not tell, because the repository's first pull requests are on
    branches named for the numbers of issues in RisingRepos, such as `agent/38-preview-site`, and this
    repository's own issues reach those numbers in time."""
    return pull["number"] > number and not pull["isCrossRepository"]


def feature(pulls: list[dict], number: int) -> list[dict]:
    """The feature's pull requests among `pulls`: those from this repository's own branches `agent/<number>-...`
    that were opened after the issue, but for the branch that reverts it."""
    start = branch_start(number)
    return [
        pull
        for pull in pulls
        if pull["headRefName"].startswith(start) and pull["headRefName"] != start + REVERT and can_be_of(pull, number)
    ]


def revert(pulls: list[dict], number: int) -> list[dict]:
    """The pull requests among `pulls` that revert the feature's merge."""
    branch = branch_start(number) + REVERT
    return [pull for pull in pulls if pull["headRefName"] == branch and can_be_of(pull, number)]


def merged(number: int) -> dict | None:
    """The feature's pull request that merged, the newest when a feature was merged more than once. None when
    none has."""
    found = feature(pulls("merged"), number)
    return max(found, key=lambda pull: pull["mergedAt"]) if found else None


def reverted(number: int) -> dict | None:
    """The pull request that reverts the feature and merged, the newest when a feature was reverted more than
    once. None when none has. `merged` leaves it out, so this is how the merge that put the site back is found."""
    found = revert(pulls("merged"), number)
    return max(found, key=lambda pull: pull["mergedAt"]) if found else None


def standing(number: int) -> list[dict]:
    """The feature's merged pull requests that no merged revert has undone, newest first: those that merged after
    the newest merged pull request that reverts the feature, or every one of them when no revert has merged.

    A feature can have more than one merge on main. A fault seen on the live site is mended once before the site
    is put back, and the mend is a second pull request of the same issue, so a mend that failed too leaves two
    merges to undo. A feature that was reverted can also be landed again later, and the merge its revert undid is
    not undone a second time. `ship --revert` merges a revert only when it holds the revert of every merge that
    stood, so a merged revert left none of the merges before it standing.

    The merged pull requests are asked for once, so that the feature's merges and its reverts are read from one
    answer."""
    return standing_among(pulls("merged"), number)


def standing_among(every: list[dict], number: int) -> list[dict]:
    """What `standing` gives, read from pull requests that are already in hand, of any state. `pickup` has
    every pull request before it asks, and asks GitHub no second time. GitHub writes each moment as UTC in one
    form, so they compare as text."""
    merged = [pull for pull in every if pull["state"] == "MERGED"]
    undone = max((pull["mergedAt"] for pull in revert(merged, number)), default="")
    stands = [pull for pull in feature(merged, number) if pull["mergedAt"] > undone]
    return sorted(stands, key=lambda pull: pull["mergedAt"], reverse=True)


def one_line(error: shell.Failed) -> str:
    """The command that failed and what it printed, as one line."""
    return " ".join(str(error).split())


def main_holds(branch: str) -> bool:
    """Whether main holds every commit of this local branch. Main is fetched first, so that the answer is of
    GitHub's main and not of what this machine last saw. Git answers by how it exits, with 0 for yes and 1 for
    no. Any other exit is a command that failed, and it is raised as one, so that it is never read as a no."""
    shell.git("fetch", "origin", "main")
    try:
        shell.git("merge-base", "--is-ancestor", branch, "origin/main")
    except shell.Failed as error:
        if error.code != 1:
            raise
        return False
    return True


def delete_local(branch: str) -> str | None:
    """Delete the branch in this repository once main holds its work, and give the one line to print when the
    branch is left instead. A local branch that is not there is nothing to delete, and nothing is said of it.

    The owner asked on 24 November 2026 that a finished run leave no branch lying about, on GitHub or here.
    `close` asks this for a feature's branch, and `ship --revert` for the branch of a revert that has merged.

    The branch is deleted only when main holds its every commit. One that holds a commit main does not has work
    that reached no pull request, and a script does not throw work away. `git branch -d` would not ask that: it
    holds a branch against the branch it follows, or against what the checkout is on when it follows none, and
    neither is main as GitHub has it. So main is asked here, and the delete is then forced.

    Git refuses to delete the branch a checkout is on, so a checkout on this one leaves it first with
    `git switch --detach`, which stays at the same commit and keeps every file as it is.

    No failure leaves here. The issue is closed or the merge is made by the time a branch is removed, and
    neither is undone for a branch. So a step that git refuses, as it refuses to delete a branch that another
    worktree is on, is a line to print as well."""
    left = f"The local branch {branch} is left"
    try:
        if not shell.git("branch", "--list", branch):
            return None
        if not main_holds(branch):
            work = "work that reached no pull request is not thrown away by a script"
            return f"{left}: it holds a commit that main does not, and {work}."
        if shell.git("branch", "--show-current") == branch:
            shell.git("switch", "--detach")
        shell.git("branch", "-D", branch)
    except shell.Failed as error:
        return f"{left}, since git refused a step of deleting it: {one_line(error)}"
    return None


def comment(options: argparse.Namespace, text: str) -> int:
    print(post(options.issue, options.kind, text))
    return 0


def set_status(number: int | str, name: str) -> str | None:
    """Set the issue's status, which decides the tab GitHub shows it under, and give the one line to print when
    GitHub refused. None when it was set.

    The owner reads what a run is at work on from GitHub's Active tab, which shows the statuses Todo, In
    progress, and In review (25 November 2026). Assigning an issue moves it from Backlog to Todo by itself, and
    taking the owner off it moves nothing back, so the scripts set the status they mean. The statuses are a
    preview of GitHub's, and a status is a thing to see and no condition of anything, so a refusal is told and
    no command fails for it."""
    try:
        shell.gh("api", "--method", "PATCH", f"{REPOSITORY}/issues/{number}", "-f", f"status={name}")
    except shell.Failed as error:
        return f"#{number} was not set to {name}, since GitHub refused it: {one_line(error)}"
    return None


def set_aside(number: str, label: str) -> None:
    """Mark an issue that a run has stopped work on: `label` in the place of `in-progress`, the issue off the
    list of those assigned to the owner, which holds what a run is at work on (`pickup.claim` puts an issue on
    it), and the issue back in the backlog, so that GitHub shows it under Open and not under Active. The label
    says what the issue waits for."""
    shell.gh(
        "issue", "edit", number, "--remove-label", rules.IN_PROGRESS, "--add-label", label, "--remove-assignee", owner()
    )
    refused = set_status(number, rules.BACKLOG)
    if refused:
        print(refused)


def stop(options: argparse.Namespace, text: str) -> int:
    """Stop the issue for the owner, or for data it waits on (docs/workflow-plan.md, sections 12 and 14).

    Nothing is sent to the owner. The comment and the label are the notice: on 24 November 2026 the owner dropped
    the message on Discord that a stop and a close used to send, which three runs in a row had not been able to
    send (#53).

    An issue that waits on data is taken up again when its field has arrived, and a field has arrived when its
    name is a key anywhere in the daily schema and the newest board day's file. A name that is there already,
    as `description` is, would have arrived before the issue ever waited: every run would take the issue up, find
    nothing new, and stop it again. So such a name is refused here, before anything on GitHub changes."""
    number = str(options.issue)
    if options.data is not None:
        if arrived(options.field):
            print(
                f"#{number} is not stopped, and nothing was changed. `{options.field}` is already a name in the "
                "daily schema and in the newest board day's file, so the next run would take the issue up again "
                "with nothing new to read. Give a more exact name, which is in neither of them yet."
            )
            return 1
        waiting = f"Waiting on RisingRepos#{options.data}.\nField: {options.field}\n\n{text}"
        print(post(options.issue, "waiting on data", waiting))
        set_aside(number, rules.BLOCKED_ON_DATA)
        return 0
    print(post(options.issue, "stopped", f"Stage: {options.stage}\n\n{text}"))
    set_aside(number, rules.NEEDS_OWNER)
    return 0


def close(options: argparse.Namespace, text: str) -> int:
    """Post what shipped, close the issue, and remove its branch, on GitHub and in this repository
    (docs/workflow-plan.md, section 10).

    A feature has shipped only while a merge of it stands on main. One whose every merge was reverted is not on
    the site, and its issue waits for the owner, so nothing is posted and nothing is closed for it. The merged
    pull requests are asked for a second time only to say which of the two a refusal is.

    The local branch goes after the one on GitHub, and only as `delete_local` allows. A local branch that is left
    is one printed line and still a close that exits 0: a run that read it as a failure would run the command
    again, and post the note a second time."""
    number = str(options.issue)
    stands = standing(options.issue)
    if not stands:
        if merged(options.issue) is None:
            print(f"#{number} has no pull request that merged, so nothing shipped and nothing was changed.")
        else:
            print(
                f"Every merge of #{number} was reverted, so none of it is on the site: nothing shipped and nothing "
                "was changed."
            )
        return 1
    pull = stands[0]
    print(post(options.issue, "shipped", text))
    shell.gh("issue", "close", number)
    shell.gh("issue", "edit", number, "--remove-label", rules.IN_PROGRESS)
    if shell.git("ls-remote", "origin", f"refs/heads/{pull['headRefName']}"):
        shell.git("push", "origin", "--delete", pull["headRefName"])
    left = delete_local(pull["headRefName"])
    if left:
        print(left)
    return 0


def main(command: str, arguments: list[str]) -> int:
    what = {
        "comment": "Post one of the workflow's comments on an issue. The command writes the comment's first line, "
        "`Site workflow: <kind>`, itself, so the file holds only what follows it. A plan that is already there is "
        "edited in place.",
        "stop": "Stop an issue for the owner, or with --data for a field it waits on.",
        "close": "Post what shipped, close the issue, and remove its branch from origin and from this repository.",
    }
    parser = argparse.ArgumentParser(prog=f"python -m sitework {command}", description=what[command])
    parser.add_argument("issue", type=int, help="the issue's number")
    if command == "comment":
        parser.add_argument("kind", choices=rules.COMMENTED, help="which of the workflow's comments this is")
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
