"""`check`: run every check a change has to pass, the cheapest first, and stop at the first that fails.

No agent is in it, so it costs time and no tokens (docs/workflow-plan.md, section 6). The agent that builds runs
it on the machine before the pull request exists, with the issue, so that the plan's criteria are checked too,
and the guard lets through what the owner allowed for that issue, as it does when the ship script runs it.
The pull request's job and main's build job run it with `--suite`: a checkout there holds no history to read a
change from, and a push to main is not a feature.

A step that passes says so in one line. A step that fails shows what it printed.
"""

import argparse
import sys
import time

from sitework import issue, newtests, shell, ship


def steps(number: int | None, suite: bool, allowed: list[str]) -> list[tuple[str, list[str]]]:
    """Each step's name and its command, in the order they run. The lint reads the code in a moment, the steps
    that read the change need only git, and the tests take minutes, so a fault is met by the cheapest step that
    can find it. A step of Python runs under the Python that runs this, which is the one `uv run` chose.

    `number` is the feature's issue, when one was given, and `allowed` the patterns of the guarded paths its owner
    let the change touch. The guard lets those through here as it does when the ship script runs it, so that a
    change the owner allowed can pass on the machine."""
    python = [sys.executable, "-m"]
    code = [
        ("the lint", [*python, "ruff", "check", "."]),
        ("the format", [*python, "ruff", "format", "--check", "."]),
    ]
    tests = [
        ("the agents' tests", [*python, "unittest", "discover", "-s", "tests"]),
        ("the owner's tests", [*python, "unittest", "discover", "-s", "owner_tests", "-t", "."]),
    ]
    if suite:
        return [*code, *tests]
    change = [
        ("white space", ["git", "diff", "--check", "origin/main...HEAD"]),
        ("the guarded paths", [*python, "sitework", "guard", *(["--allow", *allowed] if allowed else [])]),
    ]
    proofs = [("the new tests", [*python, "sitework", "new-tests"])]
    if number is not None:
        proofs.append(("the criteria", [*python, "sitework", "criteria", "--issue", str(number)]))
    return [*code, *change, *tests, *proofs]


def main(command: str, arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="Run every check a change has to pass, the cheapest first, and stop at the first that fails. "
        "Exit 0 when every step passes, and 1 otherwise.",
    )
    which = parser.add_mutually_exclusive_group()
    which.add_argument(
        "--issue",
        metavar="N",
        type=int,
        help="the feature's issue: the guard lets through what its owner allowed, and its plan's criteria are "
        "checked last",
    )
    which.add_argument(
        "--suite",
        action="store_true",
        help="run the lint, the format, and the two sets of tests alone, which is every step that needs no history",
    )
    options = parser.parse_args(arguments)
    # The owner's comments are read once, before the first step, and only when there is an issue to read.
    allowed = [] if options.issue is None else ship.allowed(issue.comments(options.issue, issue.owner()))
    for name, step in steps(options.issue, options.suite, allowed):
        print(f"{name}: started", flush=True)
        began = time.monotonic()
        try:
            shell.run(*step)
        except shell.Failed as failure:
            print(f"{name}: failed after {time.monotonic() - began:.1f} s")
            newtests.say(str(failure))
            return 1
        print(f"{name}: passed in {time.monotonic() - began:.1f} s", flush=True)
    return 0
