"""`sort` and `release`: the ideas a run works together, and an idea sent back to wait for a run of its own.

On 25 November 2026 the owner asked that ideas which change the same part of the site be worked in one run, to
spend less time and fewer tokens on each: every run reads, reproduces, checks, reviews, deploys, and confirms what
it changes, and two ideas that change one part did all of that twice. A fresh agent judges which ideas go together
(docs/workflow/sort.md). These two commands record what it judged and claim or release the ideas, and judge
nothing themselves but what a script can: that an idea waits, that a group stays small, and that a partner is one.

The group's idea approved earliest is its lead: the idea `pickup` claimed, or, when the sort chose a group
elsewhere in the queue, that group's, to which the claim is handed. Its branch, plan, pull request, and review are
the group's, and every script after the sort is given the lead's number. A partner carries a `joined` comment that
names its lead, and `issue.partners` reads the group from the two.
"""

import argparse
import functools
import re
import sys
from pathlib import Path

from sitework import issue, pickup, rules, shell

MOST = 3
"""The most ideas a group holds, its lead among them, so that one pull request still holds the change and a
reviewer can read it in one sitting."""

MOST_EFFORT = 13
"""The most points of effort a group's ideas add up to. The owner let ideas of different sizes go together on 25
November 2026, so long as they are close in the code, and this keeps the group one pull request."""

HANDED = "handed over from #{claimed}"
"""How the `picked up` comment of a lead the sort chose begins its `Taken up:` line. A handover that GitHub cut
short is known by it when the sort is run again."""


class Refused(Exception):
    """The command changes nothing. Its message says why."""


def sort(claimed: int, partners: list[int], text: str, lead: int | None = None) -> list[str]:
    """Record the lead's partners, or that it has none, and claim each partner as `pickup` claims the lead. Every
    condition is asked before anything on GitHub changes, so a refusal leaves the issues as they were. The last two
    lines it gives name the lead and its branch, which the run makes after the sort.

    The sort chooses from the whole queue (25 November 2026). When the group it chose is led by an idea other than
    the one `pickup` claimed, the claim is handed over: the lead is claimed first, the group is recorded, and the
    claimed idea is sent back last to wait for the next run, so that a step GitHub refuses leaves no idea that a
    run has let go of and no other has taken.

    Every idea of the group has a grade in points, and their effort adds up to `MOST_EFFORT` at most.

    A sort that GitHub cut short is finished by running it again with the same arguments: it claims what it had
    not, and posts nothing twice. Refused, it would leave an idea named in the group and never claimed, whose
    change would ship with the lead while it waited to be worked again."""
    owner = issue.owner()
    opened = pickup.open_issues()
    comments = functools.cache(lambda number: issue.comments(number, owner))
    lead = claimed if lead is None else lead
    handing = lead != claimed
    led = next((one for one in opened if one["number"] == lead), None)
    lead_held = bool(led) and rules.IN_PROGRESS in issue.labels(led)
    last = issue.newest(comments(lead))
    # A handover GitHub cut short is known by the lead: in progress, and its newest comment the `picked up` of
    # this very handover, or none at all when GitHub took the lead's labels and refused the comment.
    taken_up = str(issue.value(last["body"], "Taken up")) if last and rules.kind_of(last["body"]) == "picked up" else ""
    handed = handing and lead_held and re.match(rf"{re.escape(HANDED.format(claimed=claimed))}\b", taken_up) is not None
    half_claimed = handing and lead_held and last is None
    held = next((one for one in opened if one["number"] == claimed), None)
    if not handed and (not held or rules.IN_PROGRESS not in issue.labels(held)):
        raise Refused(f"#{claimed} is not an issue a run has claimed, so it has no group to sort.")
    pulls = issue.pulls()
    if handing and not handed:
        if issue.of_kind(comments(claimed), "sorted"):
            raise Refused(f"#{claimed} is sorted already, and its group goes with it. It cannot be passed over now.")
        branches = shell.git("ls-remote", "--heads", "origin", "agent/*")
        if f"refs/heads/{issue.branch_start(claimed)}" in branches or issue.feature(pulls, claimed):
            raise Refused(f"#{claimed} has a branch or a pull request, so sent back it could never wait again.")
        if not partners:
            raise Refused("A group elsewhere in the queue goes first only when it is a group: name its partners.")
    waits = {number for _, number, _, _ in pickup.ideas_waiting(opened, owner, comments, pulls)}
    if handing and not handed and not half_claimed and lead not in waits:
        raise Refused(f"#{lead} is not an approved idea that waits for a run, so it cannot lead the group.")
    if handing and not handed:
        approved = {number: pickup.approved(number, owner) or "" for number in [lead, *partners]}
        if any(approved[number] < approved[lead] for number in partners):
            raise Refused(f"#{lead} is not the idea of the group approved earliest, which leads it.")
    sorted_already = bool(issue.of_kind(comments(lead), "sorted"))
    if sorted_already and issue.named_with(comments(lead)) != partners:
        raise Refused(
            f"#{lead} is sorted already, with other partners. Run it again only with the same ones, to finish it."
        )
    if lead in partners or len(set(partners)) != len(partners):
        raise Refused("A partner is named twice, or is the lead itself.")
    if len(partners) > MOST - 1:
        raise Refused(f"A group holds at most {MOST} ideas, its lead among them.")
    joined = set(issue.partners(lead, comments)) if sorted_already else set()
    claiming = [number for number in partners if number not in joined]
    others = [f"#{number}" for number in claiming if number not in waits]
    if others:
        raise Refused(f"{', '.join(others)} is not an approved idea that waits for a run, so it cannot join #{lead}.")
    grades = {number: issue.grade(comments(number)) for number in [lead, *partners]}
    ungraded = [f"#{number}" for number, grade in grades.items() if grade is None]
    if ungraded:
        raise Refused(f"{', '.join(ungraded)} has no grade in points: grade it first.")
    effort = sum(grade["effort"] for grade in grades.values())
    if effort > MOST_EFFORT:
        raise Refused(f"The group's effort adds up to {effort} points, and a group holds at most {MOST_EFFORT}.")
    done = []
    if handing and not handed:
        branch = pickup.branch(pickup.Taken(led, "new", "", comments(lead)))
        shell.gh("issue", "edit", str(lead), "--add-label", rules.IN_PROGRESS, "--add-assignee", owner)
        done += [line for line in [issue.set_status(lead, rules.WORKING)] if line]
        taken = f"{HANDED.format(claimed=claimed)}. A group led by #{lead} went before it."
        done.append(issue.post(lead, "picked up", f"Branch: {branch}\nTaken up: {taken}"))
        comments.cache_clear()
    named = ", ".join(f"#{number}" for number in partners) or "none"
    if not sorted_already:
        done.append(issue.post(lead, "sorted", f"{rules.WITH}: {named}\n\n{text}"))
    for number in claiming:
        shell.gh("issue", "edit", str(number), "--add-label", rules.IN_PROGRESS, "--add-assignee", owner)
        done += [line for line in [issue.set_status(number, rules.WORKING)] if line]
        joined = f"{rules.LEAD}: #{lead}\n\nIt is worked in #{lead}'s run, on its branch and in its pull request."
        done.append(issue.post(number, "joined", joined))
    if handing and rules.kind_of((issue.newest(comments(claimed)) or {"body": ""})["body"]) != "released":
        why = f"A group led by #{lead} went first, so this idea waits for the next run."
        done += issue.send_back(claimed, lead, why)
    branch = pickup.branch(pickup.Taken(led or held, "new", "", issue.comments(lead, owner)))
    return [*done, f"{rules.LEAD}: #{lead}", f"Branch: {branch}"]


def release(number: int, text: str) -> list[str]:
    """Send a partner back to wait for a run of its own: it leaves the group, is no longer in progress or the
    owner's, and goes back to the backlog with its grade. Shape sends one back that does not fit the group after
    all, and a later stage one that alone keeps the group from going on (docs/workflow/README.md, "Shape" and
    "Build")."""
    owner = issue.owner()
    last = issue.newest(issue.comments(number, owner))
    lead = issue.lead_of(last)
    if not lead or rules.kind_of(last["body"]) not in ("joined", "stopped"):
        raise Refused(f"#{number} is in no group, so there is nothing to send it back from.")
    return issue.send_back(number, int(lead.lstrip("#")), text)


def main(command: str, arguments: list[str]) -> int:
    what = {
        "sort": "Record the group this run works, the idea it claimed alone or with partners, or with --lead a "
        "group elsewhere in the queue, to which the claim is handed and the claimed idea sent back to wait. Claim "
        "every idea of the group, and print its lead and branch last.",
        "release": "Send a partner back from its group to wait for a run of its own.",
    }
    parser = argparse.ArgumentParser(prog=f"python -m sitework {command}", description=what[command])
    if command == "sort":
        parser.add_argument("claimed", type=int, help="the idea this run claimed")
        parser.add_argument("--lead", type=int, metavar="N", help="the group's lead, when it is not the claimed idea")
        parser.add_argument("--with", dest="partners", type=int, nargs="+", default=[], metavar="N", help="a partner")
    else:
        parser.add_argument("issue", type=int, help="the partner to send back")
    parser.add_argument("--file", type=Path, required=True, metavar="F", help="the file that holds why")
    options = parser.parse_args(arguments)
    text = options.file.read_text(encoding="utf-8").strip()
    try:
        if command == "sort":
            done = sort(options.claimed, options.partners, text, options.lead)
        else:
            done = release(options.issue, text)
    except Refused as refused:
        print(f"{refused} Nothing was changed.", file=sys.stderr)
        return 1
    except shell.Failed as error:
        print(error, file=sys.stderr)
        return 1
    print("\n".join(done))
    return 0
