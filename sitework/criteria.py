"""`criteria`: show that each criterion of a feature's plan has a proof that passed.

A plan is the workflow's comment on the issue, in Markdown. Its section "Criteria" is a numbered list, and its
section "How each is proven" is a table with a row for each criterion: the criterion's number, and its proof. A
proof is one test or more, each named in backticks as `tests/test_x.py::Class::test_name`, or the words
"looked at:" and what will be looked at, for what no test can show. A criterion with no test that ran and passed
is what this command catches (docs/workflow-plan.md, section 6).

A row that begins "stays the same:" is the proof of a criterion that keeps something as it was. Its tests are
judged here as any others are. `new-tests` reads the mark, and lets such a test pass on the commit before (#52).
"""

import argparse
import re
from pathlib import Path

from sitework import altered, issue, newtests, rules

CRITERIA = "Criteria"
PROOFS = "How each is proven"
"""The headings of the two sections of a plan that are read here."""

CRITERION = re.compile(r"(\d+)[.)]\s")
"""A criterion: a line of the list that begins with its number. A line set in from the margin carries on the
criterion above it."""

ROW = re.compile(r"\|\s*(\d+)\s*\|(.*)\|$")
"""A row of the table: a criterion's number, and its proof. The table's heading has no number, and is passed over."""

TEST = re.compile(rf"`((?:{altered.TESTS}|{rules.OWNERS_TESTS})[^`\s:]+\.py::\w+::\w+)`")
"""A test a proof names: one of the agents' or of the owner's, by its file, its class, and its name."""

LOOKED_AT = re.compile(r"looked at:\s*(\S.*)", re.IGNORECASE)
"""The proof of what no test can show, which has to say what will be looked at. A row may begin with a capital."""


STAYS = re.compile(r"stays the same:", re.IGNORECASE)
"""How the proof begins of a criterion that keeps something as it was."""


def kept_the_same(plan: str) -> set[str]:
    """Each test the plan names in a row that begins "stays the same:". Such a test holds what the change must
    leave as it was, so it passes on the commit before, where every other new test has to fail."""
    rows = [row for line in section(plan, PROOFS) if (row := ROW.match(line.strip()))]
    return {test for row in rows if STAYS.match(row[2].strip()) for test in TEST.findall(row[2])}


def plan_of(number: int) -> str | None:
    """The plan of an issue: the newest of the workflow's plans that the owner's account posted on it, or None when
    there is none. The repository is public, so a comment by any other account counts for nothing here, whatever
    its first line says: a stranger's plan, with nothing but things looked at for proofs, would pass any change."""
    plans = issue.of_kind(issue.comments(number, issue.owner()), "plan")
    return plans[-1]["body"] if plans else None


def section(plan: str, heading: str) -> list[str]:
    """The lines of the plan under `## <heading>`, as far as the next heading of that level."""
    lines, inside = [], False
    for line in plan.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip() == heading
        elif inside:
            lines.append(line)
    return lines


def judged(proof: str | None, passed: dict[str, bool]) -> tuple[bool, str]:
    """Whether a criterion is proven by its row of the table, and the words that say how, or say what is wrong.
    A test it names has to be at HEAD, and to pass when run in this repository. `passed` holds how each test that
    has been run ended, so that a test which proves two criteria runs once."""
    if proof is None:
        return False, "no row of the table says how it is proven"
    tests = TEST.findall(proof)
    for test in tests:
        if test not in altered.tests_at("HEAD", test.split("::")[0]):
            return False, f"{test} is not at HEAD"
        if test not in passed:
            passed[test] = newtests.passes(test)
        if not passed[test]:
            return False, f"{test} fails"
    if tests:
        return True, "proven by " + ", ".join(tests)
    if looked_at := LOOKED_AT.search(proof):
        return True, looked_at[0].strip()
    return False, "its row names no test, and nothing that was looked at"


def main(command: str, arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="Show that each criterion of a feature's plan has a proof that passed. Exit 0 when every one "
        "is proven, and 1 otherwise.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--plan", metavar="FILE", type=Path, help="a file that holds the plan")
    source.add_argument("--issue", metavar="N", type=int, help="the issue whose newest plan is read")
    options = parser.parse_args(arguments)
    plan = options.plan.read_text(encoding="utf-8") if options.plan else plan_of(options.issue)
    if plan is None:
        print(f'issue {options.issue} has no comment that begins "{rules.first_line("plan")}"')
        return 1
    criteria = [int(criterion[1]) for line in section(plan, CRITERIA) if (criterion := CRITERION.match(line))]
    if not criteria:
        print(f'the plan has no numbered criterion under "## {CRITERIA}"')
        return 1
    rows = [row for line in section(plan, PROOFS) if (row := ROW.match(line.strip()))]
    proofs = {int(row[1]): row[2] for row in rows}
    passed: dict[str, bool] = {}
    every = True
    for number in criteria:
        proven, words = judged(proofs.get(number), passed)
        every = every and proven
        newtests.say(f"{number}: {words}" if proven else f"{number}: not proven: {words}")
    return 0 if every else 1
