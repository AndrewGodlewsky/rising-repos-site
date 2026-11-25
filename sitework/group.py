"""`sort` and `release`: the ideas a run works together, and an idea sent back to wait for a run of its own.

On 25 November 2026 the owner asked that ideas which change the same part of the site be worked in one run, to
spend less time and fewer tokens on each: every run reads, reproduces, checks, reviews, deploys, and confirms what
it changes, and two ideas that change one part did all of that twice. A fresh agent judges which ideas go together
(docs/workflow/sort.md). These two commands record what it judged and claim or release the ideas, and judge
nothing themselves but what a script can: that an idea waits, that a group stays small, and that a partner is one.

The idea `pickup` claimed is the lead. Its branch, plan, pull request, and review are the group's, and every
script after the sort is given the lead's number. A partner carries a `joined` comment that names its lead, and
`issue.partners` reads the group from the two.
"""

import argparse
import functools
import sys
from pathlib import Path

from sitework import issue, pickup, rules, shell

MOST = 3
"""The most ideas a group holds, its lead among them, so that one pull request still holds the change and a
reviewer can read it in one sitting."""


class Refused(Exception):
    """The command changes nothing. Its message says why."""


def sort(lead: int, partners: list[int], text: str) -> list[str]:
    """Record the lead's partners, or that it has none, and claim each partner as `pickup` claims the lead. Every
    condition is asked before anything on GitHub changes, so a refusal leaves the issues as they were.

    A sort that GitHub cut short after the sort was posted is finished by running it again with the same
    partners: it claims those it had not, and posts nothing twice. Refused, it would leave an idea named in the
    group and never claimed, whose change would ship with the lead while it waited to be worked again."""
    owner = issue.owner()
    opened = pickup.open_issues()
    comments = functools.cache(lambda number: issue.comments(number, owner))
    led = next((one for one in opened if one["number"] == lead), None)
    if not led or rules.IN_PROGRESS not in issue.labels(led):
        raise Refused(f"#{lead} is not an issue a run has claimed, so it has no group to sort.")
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
    waits = {number for _, number, _, _ in pickup.ideas_waiting(opened, owner, comments, issue.pulls())}
    others = [f"#{number}" for number in claiming if number not in waits]
    if others:
        raise Refused(f"{', '.join(others)} is not an approved idea that waits for a run, so it cannot join #{lead}.")
    named = ", ".join(f"#{number}" for number in partners) or "none"
    done = [] if sorted_already else [issue.post(lead, "sorted", f"{rules.WITH}: {named}\n\n{text}")]
    for number in claiming:
        shell.gh("issue", "edit", str(number), "--add-label", rules.IN_PROGRESS, "--add-assignee", owner)
        done += [line for line in [issue.set_status(number, rules.WORKING)] if line]
        joined = f"{rules.LEAD}: #{lead}\n\nIt is worked in #{lead}'s run, on its branch and in its pull request."
        done.append(issue.post(number, "joined", joined))
    return done


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
        "sort": "Record which ideas go with the idea this run claimed, or that none does, and claim each of them.",
        "release": "Send a partner back from its group to wait for a run of its own.",
    }
    parser = argparse.ArgumentParser(prog=f"python -m sitework {command}", description=what[command])
    if command == "sort":
        parser.add_argument("lead", type=int, help="the idea this run claimed")
        parser.add_argument("--with", dest="partners", type=int, nargs="+", default=[], metavar="N", help="a partner")
    else:
        parser.add_argument("issue", type=int, help="the partner to send back")
    parser.add_argument("--file", type=Path, required=True, metavar="F", help="the file that holds why")
    options = parser.parse_args(arguments)
    text = options.file.read_text(encoding="utf-8").strip()
    try:
        done = sort(options.lead, options.partners, text) if command == "sort" else release(options.issue, text)
    except Refused as refused:
        print(f"{refused} Nothing was changed.", file=sys.stderr)
        return 1
    except shell.Failed as error:
        print(error, file=sys.stderr)
        return 1
    print("\n".join(done))
    return 0
