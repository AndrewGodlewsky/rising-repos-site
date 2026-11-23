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

from sitework import confirm, issue, notify, rules, shell

NOTHING, UNHEALTHY = 3, 4
"""The exit codes when there is nothing to do, and when the site is not healthy."""

WORKFLOWS = {rules.IN_PROGRESS, rules.NEEDS_OWNER, rules.BLOCKED_ON_DATA}
"""The labels the workflow sets. An idea that carries one is not new."""

TOLD = "sitework-told"
"""The file under git's common directory that holds the run the owner was last told of. There it is in no commit,
and every worktree of the repository shares it."""

SLUG_WORDS = 5

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
        raise unhealthy(deploy, f"The newest deploy to main ended in {deploy['conclusion']}: {deploy['url']}")
    measured = confirm.eval_after(deploy)
    if measured is None or measured["status"] != "completed":
        raise End(NOTHING, f"The site eval that follows the deploy of {deploy['headSha'][:7]} has not finished.")
    if measured["conclusion"] != "success":
        raise unhealthy(
            measured, f"The site eval after the newest deploy ended in {measured['conclusion']}: {measured['url']}"
        )


def unhealthy(run: dict, why: str) -> End:
    """Tell the owner of a run that failed, once for that run and not again at every run, and give the end of
    this run. A message that could not be sent is not remembered, so the next run sends it."""
    told = Path(shell.git("rev-parse", "--path-format=absolute", "--git-common-dir")) / TOLD
    this = str(run["databaseId"])
    if not (told.is_file() and told.read_text(encoding="utf-8").strip() == this):
        if notify.send(f"{rules.FIRST_LINE}nothing new starts, because the site is not healthy. {why}") == "sent":
            told.write_text(this + "\n", encoding="utf-8")
    return End(UNHEALTHY, why)


def agent_at_work(number: int) -> bool:
    """Whether an agent is at work in the worktree whose branch is the issue's. Git says which worktree holds the
    branch, and Orca which agents are open in it. An agent that has finished its turn is `done` there. The agent
    that runs this command is left out, since it is the one asking."""
    start = "refs/heads/" + issue.branch_start(number)
    held, path = set(), ""
    for line in shell.git("worktree", "list", "--porcelain").splitlines():
        name, _, rest = line.partition(" ")
        if name == "worktree":
            path = rest
        elif name == "branch" and rest.startswith(start):
            held.add(same(path))
    if not held:
        return False
    listed = json.loads(shell.run("orca", "worktree", "ps", "--json", "--limit", "1000"))["result"]["worktrees"]
    asking = os.environ.get("ORCA_AGENT_SESSION_ID")
    return any(
        agent["state"] != "done" and agent["orcaSessionId"] != asking
        for worktree in listed
        if same(worktree["path"]) in held
        for agent in worktree["agents"]
    )


def same(path: str) -> str:
    """A folder's path in one spelling, so that git's and Orca's can be compared."""
    return os.path.normcase(os.path.normpath(path))


def in_flight(opened: list[dict], comments: Comments) -> Taken | None:
    """The issue that carries `in-progress`, when its agent is gone. The run ends when its agent is at work,
    because features go one at a time."""
    held = sorted((one for one in opened if rules.IN_PROGRESS in issue.labels(one)), key=lambda one: one["number"])
    for one in held:
        if agent_at_work(one["number"]):
            raise End(NOTHING, f"#{one['number']} is in progress, and an agent is at work on its branch.")
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
    """What the issue, its comments, and its pull request show of how far the feature came, for the agent to
    find the stage to carry on from."""
    plans, reviews = issue.of_kind(taken.said, "plan"), issue.of_kind(taken.said, "review")
    ours = issue.feature(pulls, taken.issue["number"])
    newest = ours[-1] if ours else None
    return {
        "labels": issue.labels(taken.issue),
        "plan": {"exists": bool(plans), "verdict": plan_verdict(plans[-1]["body"]) if plans else None},
        "pull_request": {"number": newest["number"], "state": newest["state"]} if newest else None,
        "review": {name.lower(): issue.value(reviews[-1]["body"], name) for name in ("Verdict", "Commit")}
        if reviews
        else None,
        "merged": bool(newest and newest["state"] == "MERGED"),
    }


def plan_verdict(body: str) -> str | None:
    """A plan's verdict: the first line with words after its `## Verdict` heading."""
    lines = [line.strip() for line in body.splitlines()]
    after = lines[lines.index("## Verdict") + 1 :] if "## Verdict" in lines else []
    return next((line for line in after if line), None)


def claim(taken: Taken, branch: str) -> None:
    """Claim the issue: it carries `in-progress`, it no longer waits on data, and a `picked up` comment names its
    branch."""
    number = taken.issue["number"]
    labels = [] if rules.IN_PROGRESS in issue.labels(taken.issue) else ["--add-label", rules.IN_PROGRESS]
    if taken.take_up == "data arrived":
        labels += ["--remove-label", rules.BLOCKED_ON_DATA]
    if labels:
        shell.gh("issue", "edit", str(number), *labels)
    issue.post(number, "picked up", f"Branch: {branch}\nTaken up: {taken.take_up}. {taken.why}")


def pickup(claiming: bool) -> tuple[int, dict]:
    """The exit code, and the JSON object to print."""
    try:
        healthy()
        owner = issue.owner()
        opened = shell.gh_json(
            "issue", "list", "--state", "open", "--limit", "1000", "--json", "number,title,labels,author"
        )
        pulls = issue.pulls()
        comments = functools.cache(lambda number: issue.comments(number, owner))
        taken = in_flight(opened, comments) or answered(opened, comments) or new_idea(opened, owner, comments, pulls)
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
        claim(taken, answer["branch"])
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
