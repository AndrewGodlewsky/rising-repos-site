"""`check`: run every check a change has to pass, the cheapest first, and stop at the first that fails.

No agent is in it, so it costs time and no tokens (docs/workflow-plan.md, section 6). The agent that builds runs
it on the machine before the pull request exists, with the issue, so that the plan's criteria are checked too,
and the guard lets through what the owner allowed for that issue, as it does when the ship script runs it.
The pull request's job and main's build job run it with `--suite`: a checkout there holds no history to read a
change from, and a push to main is not a feature.

A change that touches no guarded path is not run against the tests of what is guarded (`rules.OWN_TESTS`): it
cannot alter what they find, and they are a third of the time the agents' tests take. `--suite` runs every
test, and so does a change the owner let touch a guarded path.

A step that passes says so in one line. A step that fails shows what it printed.
"""

import argparse
import fnmatch
import functools
import sys
import time

from sitework import issue, newtests, rules, shell, ship

NAMED = "import sys, unittest; sys.path.insert(0, 'tests'); unittest.main(module=None)"
"""Runs the files of tests named after it as `unittest discover -s tests` runs them: each found in `tests` and
taken under its own name. Discovery can take a file in and cannot leave one out, so when some are left out the
rest are named."""


def the_rest() -> list[str]:
    """The files of the agents' tests but for those of what no feature changes, each as unittest names it. They
    are the files that discovery finds, less the ones a pattern of `rules.OWN_TESTS` names."""
    return sorted(
        path.stem
        for path in (shell.ROOT / "tests").glob("test*.py")
        if not any(fnmatch.fnmatch(f"tests/{path.name}", pattern) for pattern in rules.OWN_TESTS)
    )


def steps(
    number: int | None, suite: bool, allowed: list[str], rest: list[str] | None = None
) -> list[tuple[str, list[str]]]:
    """Each step's name and its command, in the order they run. The lint reads the code in a moment, the steps
    that read the change need only git, and the tests take minutes, so a fault is met by the cheapest step that
    can find it. A step of Python runs under the Python that runs this, which is the one `uv run` chose.

    `number` is the feature's issue, when one was given, and `allowed` the patterns of the guarded paths its owner
    let the change touch. The guard lets those through here as it does when the ship script runs it, so that a
    change the owner allowed can pass on the machine.

    `rest` is the files of the agents' tests to run when those of what no feature changes are left out, and
    None when every test runs."""
    python = [sys.executable, "-m"]
    code = [
        ("the lint", [*python, "ruff", "check", "."]),
        ("the format", [*python, "ruff", "format", "--check", "."]),
    ]
    every = ("the agents' tests", [*python, "unittest", "discover", "-s", "tests"])
    fewer = ("the agents' tests, but for the workflow's own", [sys.executable, "-c", NAMED, *(rest or [])])
    tests = [
        every if rest is None else fewer,
        ("the owner's tests", [*python, "unittest", "discover", "-s", "owner_tests", "-t", "."]),
    ]
    if suite:
        return [*code, *tests]
    change = [
        ("white space", ["git", "diff", "--check", "origin/main...HEAD"]),
        ("the guarded paths", [*python, "sitework", "guard", *(["--allow", *allowed] if allowed else [])]),
    ]
    of_issue = [] if number is None else ["--issue", str(number)]
    proofs = [("the new tests", [*python, "sitework", "new-tests", *of_issue])]
    if number is not None:
        proofs.append(("the criteria", [*python, "sitework", "criteria", *of_issue]))
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
    # The owner's comments are read once, before the first step, and only when there is an issue to read. They are
    # read on the lead and on each partner of its group, as the merge reads them (25 November 2026).
    allowed = []
    if options.issue is not None:
        owner = issue.owner()
        allowed = ship.allowed_for(options.issue, functools.cache(lambda number: issue.comments(number, owner)))
    # With nothing allowed, the guard's step, which comes before the tests, fails a change that touches a guarded
    # path. So the tests are reached only by a change that cannot alter the ones that are left out.
    rest = None if options.suite or allowed else the_rest()
    for name, step in steps(options.issue, options.suite, allowed, rest):
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
