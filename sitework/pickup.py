"""`pickup`: choose the issue this run works on, and with `--claim`, claim it.

It judges nothing and does not read what an issue asks for (docs/workflow-plan.md, section 3). It asks four
things in order: whether the site is healthy, whether an issue is in flight, whether a stopped issue has been
answered, and otherwise which approved idea is next. It prints one JSON object. It exits 0 when there is an issue
to work on, 3 when there is nothing to do, and 4 when the site is not healthy.

Without `--claim` it changes nothing on GitHub. An Orca automation runs it that way before each scheduled run, and
starts an agent only when it exits 0, so a run with nothing to do starts no agent. The agent then runs it with
`--claim`.
"""

import argparse
import functools
import json
import os
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from sitework import confirm, issue, rules, shell

NOTHING, UNHEALTHY = 3, 4
"""The exit codes when there is nothing to do, and when the site is not healthy."""

WORKFLOWS = {rules.IN_PROGRESS, rules.NEEDS_OWNER, rules.BLOCKED_ON_DATA}
"""The labels the workflow sets. An idea that carries one is not new."""

SLUG_WORDS = 5

FEATURES = "refs/heads/" + rules.BRANCH.partition("{")[0]
"""How git names every feature's branch begins, the branch that reverts one among them."""

RUNS = "sitework-runs"
"""The file under git's common directory that holds the checkout of each run that claimed an issue and may still be
at work, a line to a checkout. A run is known by where it works, and not by the branch that checkout is on, since
a run may leave its feature's branch once its issue is closed and still be looking back over itself."""

Comments = Callable[[int], list[dict]]
"""Gives the comments the owner's account wrote on an issue. A run reads an issue's comments once, however many
of its steps ask for them."""


class End(Exception):
    """The run ends with no issue to work on. Its message says why."""

    def __init__(self, code: int, why: str):
        super().__init__(why)
        self.code = code


class Taken(NamedTuple):
    """An issue to work on: the issue, how it is taken up, why, and the comments the owner's account wrote on
    it."""

    issue: dict
    take_up: str
    why: str
    said: list[dict]


def healthy() -> None:
    """End the run unless the newest deploy to main succeeded and the site eval that followed it passed. One
    that has not finished is not a failure: the next run looks again."""
    deploy = confirm.deploy_run()
    if deploy["status"] != "completed":
        raise End(NOTHING, f"The deploy of {deploy['headSha'][:7]} to main has not finished: {deploy['url']}")
    if deploy["conclusion"] != "success":
        raise unhealthy(f"The newest deploy to main ended in {deploy['conclusion']}: {deploy['url']}")
    measured = confirm.eval_after(deploy)
    if measured is None or measured["status"] != "completed":
        raise End(NOTHING, f"The site eval that follows the deploy of {deploy['headSha'][:7]} has not finished.")
    if measured["conclusion"] != "success":
        raise unhealthy(f"The site eval after the newest deploy ended in {measured['conclusion']}: {measured['url']}")


def unhealthy(why: str) -> End:
    """The end of a run that starts nothing because the site is not healthy. What is printed says why, and
    nothing is sent to the owner: the notice on Discord was dropped on 24 November 2026 (#53)."""
    return End(UNHEALTHY, why)


def common(name: str) -> Path:
    """A file under git's common directory, which is in no commit and which every worktree of the repository
    shares."""
    return Path(shell.git("rev-parse", "--path-format=absolute", "--git-common-dir")) / name


def at_work() -> list[str]:
    """Each run that an agent is still at work on, by the name of its checkout's folder. A run's checkout is one
    that claimed an issue, which `claim` wrote down, or one that is on a feature's branch. Orca says which agents
    are open in each. An agent that has finished its turn is `done` there. The agent that runs this command is
    left out, since it is the one asking.

    The labels alone do not say this. A run takes `in-progress` off its issue when it closes it, and then looks
    back over itself for some minutes more. Asked of the labels in those minutes, a check of the schedule would
    start the next issue beside a run that has not ended.

    A checkout that was written down and holds no agent at work is forgotten here, so that the file names only
    the runs that may still be going. The agent that asks counts for that, though it holds nothing up: a run
    that asked again would otherwise take its own checkout out of the file while it was still at work."""
    held, path = {}, ""
    for line in shell.git("worktree", "list", "--porcelain").splitlines():
        name, _, rest = line.partition(" ")
        if name == "worktree":
            path = rest
        elif name == "branch" and rest.startswith(FEATURES):
            held[same(path)] = f"{Path(path).name}, on {rest.removeprefix('refs/heads/')}"
    runs = common(RUNS)
    written = runs.read_text(encoding="utf-8").splitlines() if runs.is_file() else []
    for checkout in written:
        held.setdefault(same(checkout), Path(checkout).name)
    if not held:
        return []
    listed = json.loads(shell.run("orca", "worktree", "ps", "--json", "--limit", "1000"))["result"]["worktrees"]
    asking = os.environ.get("ORCA_AGENT_SESSION_ID")
    open_in = {same(worktree["path"]): [a for a in worktree["agents"] if a["state"] != "done"] for worktree in listed}
    busy = {checkout for checkout, agents in open_in.items() if any(a["orcaSessionId"] != asking for a in agents)}
    going = [checkout for checkout in written if open_in.get(same(checkout))]
    if going != written:
        runs.write_text("".join(f"{checkout}\n" for checkout in going), encoding="utf-8")
    return sorted(name for checkout, name in held.items() if checkout in busy)


def same(path: str) -> str:
    """A folder's path in one spelling, so that git's and Orca's can be compared."""
    return os.path.normcase(os.path.normpath(path))


def in_flight(opened: list[dict], comments: Comments) -> Taken | None:
    """The issue that carries `in-progress`, which a run began and did not end. No agent is at work on it, or
    `pickup` would have ended before it asked, so the run that asks takes it up again."""
    held = sorted((one for one in opened if rules.IN_PROGRESS in issue.labels(one)), key=lambda one: one["number"])
    if not held:
        return None
    said = comments(held[0]["number"])
    return Taken(held[0], "resume", "It is in progress, and no agent is at work on its branch.", said)


def answered(opened: list[dict], comments: Comments) -> Taken | None:
    """An approved issue that stopped and can go on: the owner removed `needs-owner` from it, or the field it
    waited for has arrived (docs/workflow-plan.md, sections 12 and 14)."""
    for one in sorted(opened, key=lambda one: one["number"]):
        marks = issue.labels(one)
        if rules.APPROVED not in marks:
            continue
        said = comments(one["number"])
        if rules.BLOCKED_ON_DATA in marks:
            waits = issue.of_kind(said, "waiting on data")
            field = issue.value(waits[-1]["body"], "Field") if waits else None
            if field and issue.arrived(field):
                return Taken(
                    one, "data arrived", f"The field {field} is in the daily schema and the newest board.", said
                )
        elif rules.NEEDS_OWNER not in marks:
            kinds = [kind for kind in (rules.kind_of(comment["body"]) for comment in said) if kind]
            if kinds and kinds[-1] == "stopped":
                return Taken(one, "answered", "It was stopped for the owner, who has removed needs-owner.", said)
    return None


def new_idea(opened: list[dict], owner: str, comments: Comments, pulls: list[dict]) -> Taken:
    """The approved idea that was approved earliest, of those nothing has been done on. The owner's account wrote
    it and put both labels on it, which keeps a stranger's issue out."""
    branches = [
        line.split("refs/heads/")[1] for line in shell.git("ls-remote", "--heads", "origin", "agent/*").splitlines()
    ]
    ideas = []
    for one in opened:
        number, marks = one["number"], set(issue.labels(one))
        start = issue.branch_start(number)
        if not {rules.IDEA, rules.APPROVED} <= marks or marks & WORKFLOWS or one["author"]["login"] != owner:
            continue
        if (
            issue.feature(pulls, number)
            or issue.revert(pulls, number)
            or any(name.startswith(start) for name in branches)
        ):
            continue
        said = comments(number)
        when = approved(number, owner)
        if when and not any(rules.kind_of(comment["body"]) for comment in said):
            ideas.append((when, number, one, said))
    if not ideas:
        raise End(NOTHING, "No issue is ready to be worked on.")
    when, _, one, said = min(ideas, key=lambda found: found[:2])
    return Taken(one, "new", f"It is the approved idea that was approved earliest, at {when}.", said)


def approved(number: int, owner: str) -> str | None:
    """When the owner's account approved the idea: the time `approved` was last put on it. None when another
    account put on that label or `site-idea`. The issue's timeline says who applied a label, and when."""
    events = shell.gh_json("api", f"{issue.REPOSITORY}/issues/{number}/timeline?per_page=100", "--paginate")
    last = {event["label"]["name"]: event for event in events if event.get("event") == "labeled"}
    for label in (rules.IDEA, rules.APPROVED):
        if label not in last or (last[label]["actor"] or {}).get("login") != owner:
            return None
    return last[rules.APPROVED]["created_at"]


def branch(taken: Taken) -> str:
    """The feature's branch: the one the issue's newest `picked up` comment names, so that an issue taken up
    again keeps its branch, and for a new idea one made from its number and the first words of its title."""
    picked = issue.of_kind(taken.said, "picked up")
    named = issue.value(picked[-1]["body"], "Branch") if picked else None
    words = re.findall(r"[a-z0-9]+", taken.issue["title"].lower())[:SLUG_WORDS]
    slug = "-".join(words)
    # An issue titled just "Revert" would get the slug of the branch that reverts a feature. The scripts would
    # then take the feature's own branch for the one that reverts it, and `ship --revert` merges that one with
    # no review. So that one slug is given a word before it, and no feature's branch has the revert's name.
    if slug == issue.REVERT:
        slug = f"idea-{slug}"
    return named or rules.BRANCH.format(issue=taken.issue["number"], slug=slug)


def facts(taken: Taken, pulls: list[dict]) -> dict:
    """What the issue, its comments, and its pull requests show of how far the feature came, for the agent to
    find the stage to carry on from.

    The newest pull request alone does not say whether a mend was tried, or whether the site was put back.
    `standing` is how many of the feature's merges are on main with no revert after them: one is the feature,
    and two the feature and its mend, so that a run taken up again never mends a second time. `reverted` is
    whether the feature was merged and nothing of it stands, which is a site that was put back."""
    plans, reviews = issue.of_kind(taken.said, "plan"), issue.of_kind(taken.said, "review")
    ours = issue.feature(pulls, taken.issue["number"])
    newest = ours[-1] if ours else None
    standing = issue.standing_among(pulls, taken.issue["number"])
    return {
        "labels": issue.labels(taken.issue),
        "plan": {"exists": bool(plans), "verdict": plan_verdict(plans[-1]["body"]) if plans else None},
        "pull_request": {"number": newest["number"], "state": newest["state"]} if newest else None,
        "review": {name.lower(): issue.value(reviews[-1]["body"], name) for name in ("Verdict", "Commit")}
        if reviews
        else None,
        "merged": bool(newest and newest["state"] == "MERGED"),
        "standing": len(standing),
        "reverted": not standing and any(pull["state"] == "MERGED" for pull in ours),
    }


def plan_verdict(body: str) -> str | None:
    """A plan's verdict: the first line with words after its `## Verdict` heading."""
    lines = [line.strip() for line in body.splitlines()]
    after = lines[lines.index("## Verdict") + 1 :] if "## Verdict" in lines else []
    return next((line for line in after if line), None)


def claim(taken: Taken, branch: str, owner: str) -> None:
    """Claim the issue: it carries `in-progress`, it is assigned to the owner, it no longer waits on data, and a
    `picked up` comment names its branch.

    The issues assigned to the owner are then the ones a run is at work on, which is how the owner sees at a
    glance what is being worked on. A stop takes the issue off that list again (`issue.stop`), and a close
    leaves the closed issue with the owner's name on it. An issue that is assigned already stays so."""
    number = taken.issue["number"]
    labels = [] if rules.IN_PROGRESS in issue.labels(taken.issue) else ["--add-label", rules.IN_PROGRESS]
    if taken.take_up == "data arrived":
        labels += ["--remove-label", rules.BLOCKED_ON_DATA]
    shell.gh("issue", "edit", str(number), *labels, "--add-assignee", owner)
    issue.post(number, "picked up", f"Branch: {branch}\nTaken up: {taken.take_up}. {taken.why}")
    # The run is written down by the checkout it works in, so that a later look finds it for as long as its agent
    # is at work there, whatever branch the checkout is on by then.
    runs = common(RUNS)
    written = runs.read_text(encoding="utf-8").splitlines() if runs.is_file() else []
    if not any(same(checkout) == same(str(shell.ROOT)) for checkout in written):
        runs.write_text("".join(f"{checkout}\n" for checkout in [*written, str(shell.ROOT)]), encoding="utf-8")


def pickup(claiming: bool) -> tuple[int, dict]:
    """The exit code, and the JSON object to print.

    Whether the site is healthy is asked before anything new is started, and before an issue in flight that
    is not yet on the site is carried on. A feature that is live is taken up again whatever the site's health:
    the fault may be its own, and the run that mends it or puts the site back is this one. Asked first of all,
    a feature that broke the site eval and lost its run would have kept every later run from starting.

    Before any of that, nothing starts while a run is still at work: features go one at a time, and the next
    waits until the one before has wholly ended, its look back with it."""
    try:
        busy = at_work()
        if busy:
            raise End(NOTHING, f"A run is still at work in {'; '.join(busy)}. Nothing starts until it has ended.")
        owner = issue.owner()
        opened = shell.gh_json(
            "issue", "list", "--state", "open", "--limit", "1000", "--json", "number,title,labels,author"
        )
        pulls = issue.pulls()
        comments = functools.cache(lambda number: issue.comments(number, owner))
        taken = in_flight(opened, comments)
        if not (taken and issue.standing_among(pulls, taken.issue["number"])):
            healthy()
            taken = taken or answered(opened, comments) or new_idea(opened, owner, comments, pulls)
    except End as end:
        return end.code, {"why": str(end)}
    answer = {
        "issue": taken.issue["number"],
        "title": taken.issue["title"],
        "branch": branch(taken),
        "take_up": taken.take_up,
        "why": taken.why,
        "facts": facts(taken, pulls),
    }
    if claiming:
        claim(taken, answer["branch"], owner)
    return 0, answer


def main(command: str, arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="Choose the issue this run works on. Exit 0 with an issue to work on, 3 with nothing to do, and 4 "
        "when the site is not healthy.",
    )
    parser.add_argument("--claim", action="store_true", help="claim the issue: add in-progress and post picked up")
    options = parser.parse_args(arguments)
    try:
        code, answer = pickup(options.claim)
    except shell.Failed as error:
        print(error, file=sys.stderr)
        return 1
    print(json.dumps(answer, indent=2))
    return code
