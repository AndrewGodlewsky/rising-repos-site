"""`new-tests`: show that each test a change adds fails on the commit before.

A test that passes with the feature and without it proves nothing (docs/workflow-plan.md, section 6, and D18
there, and standard C18). So each test the change adds, among the agents' tests and the owner's, is run on the
code as it was where the change began, and has to fail or error there.

One kind of test cannot fail there: the test of a criterion that keeps something as it was, such as "from 768
pixels up the table is as it was". On #27 no such test could be added, the criterion was measured by hand three
times, and nothing holds it since. On #28 and #29 it was folded into a test of something new to get past this
check (#52). So a plan marks such a criterion's proof with "stays the same:", and a test it names there has to
pass on the commit before. The mark cuts both ways, so that it says something exact: a test that is marked and
fails before is not a test of what stayed the same. Whether a marked test holds anything is the reviewer's to
show, by taking away the lines of the change that keep the thing as it was.
"""

import argparse
import contextlib
import sys
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

from sitework import altered, guard, rules, shell

RUN_ONE = """\
import os, sys, unittest
sys.path[:0] = [os.path.abspath(folder) for folder in sys.argv[2:]]
result = unittest.main(module=None, argv=sys.argv[:2], exit=False).result
passed = result.wasSuccessful() and result.testsRun and not result.skipped and not result.expectedFailures
sys.exit(0 if passed else 1)
"""
"""A program that runs the one test named by its first argument, with each folder after it put on the path first,
as `unittest discover -s` puts the folder it is given. It exits with 0 only when the test ran and passed. unittest's
own exit is 0 as well after a test that was skipped, and after one that failed as it was expected to, and neither
of those shows that what the test is about is so."""


def say(words: str) -> None:
    """Print words this workflow did not write: a plan's, or what a command printed. Where the output's encoding
    has no way to write one of their characters, as a pipe on Windows has none for an arrow, that character is
    shown by its number, and the command goes on."""
    encoding = sys.stdout.encoding or "utf-8"
    print(words.encode(encoding, "backslashreplace").decode(encoding))


def command(test: str) -> list[str]:
    """The command that runs the one test `test` from the top of a checkout, under the name the check's own runs
    of unittest import it by: an agents' test from its file's name, with the folder of the agents' tests on the
    path, and an owner's test as a module of its folder. A test of this module replaces it."""
    path, *names = test.split("::")
    module = PurePosixPath(path).with_suffix("").parts
    if path.startswith(altered.TESTS):
        return [sys.executable, "-c", RUN_ONE, ".".join((*module[1:], *names)), altered.TESTS]
    return [sys.executable, "-c", RUN_ONE, ".".join((*module, *names))]


def passes(test: str, checkout: Path | None = None) -> bool:
    """Whether the test passes when run in `checkout`, which is this repository when none is given. A test that
    was skipped did not pass."""
    try:
        shell.run(*command(test), cwd=checkout)
    except shell.Failed:
        return False
    return True


def added(base: str, head: str, files: dict[str, str]) -> list[str]:
    """Each test the change adds: one that `head` has, and `base` does not have under that file, class, and
    name. `files` is what the change did to each file of the tests."""
    new = []
    for path in sorted(files):
        if files[path] != "D" and altered.is_test_file(path):
            before = altered.tests_at(base, path)
            new += [test for test in altered.tests_at(head, path) if test not in before]
    return new


@contextlib.contextmanager
def before(base: str, head: str, files: dict[str, str]) -> Iterator[Path]:
    """A checkout of the code as `base` has it, with each file of the tests that the change added or altered as
    `head` has it. It is a worktree of this repository in a temporary folder, and is removed when the block ends,
    also when the block ends with an error. `head` is a commit's own name, since `HEAD` there is the checkout's."""
    folders = sorted({path.split("/")[0] for path, how in files.items() if how != "D"})
    with shell.worktree(base) as checkout:
        # Every other file of these folders is the same in both commits, so this copies what the change wrote.
        shell.git("checkout", head, "--", *folders, cwd=checkout)
        yield checkout


def kept_the_same(options: argparse.Namespace) -> set[str]:
    """The tests the feature's plan marks as holding what stays the same, or none when no plan was given or the
    issue has none. `criteria` reads a plan, and reads this module, so it is brought in here and not above."""
    from sitework import criteria

    if options.plan:
        plan = options.plan.read_text(encoding="utf-8")
    else:
        plan = criteria.plan_of(options.issue) if options.issue is not None else None
    return criteria.kept_the_same(plan) if plan else set()


def main(command: str, arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="Run each test a change adds on the code before the change. Exit 0 when each fails there, or "
        "when the change adds none, and 1 when one passes there.",
    )
    guard.add_change(parser)
    plan = parser.add_mutually_exclusive_group()
    plan.add_argument(
        "--issue",
        metavar="N",
        type=int,
        help='the feature\'s issue: a test its plan names in a row that begins "stays the same:" has to pass before',
    )
    plan.add_argument("--plan", metavar="FILE", type=Path, help="a file that holds the plan, in the place of --issue")
    options = parser.parse_args(arguments)
    kept = kept_the_same(options)
    base = guard.base_of(options)
    head = shell.git("rev-parse", "--verify", f"{options.head}^{{commit}}")
    files = guard.changed(base, head, altered.TESTS, rules.OWNERS_TESTS)
    new = added(base, head, files)
    if not new:
        print("the change adds no test")
        return 0
    proved_nothing = False
    with before(base, head, files) as checkout:
        for test in new:
            passed = passes(test, checkout)
            if test in kept and passed:
                print(f"passes before, as the plan says of what stays the same: {test}")
            elif test in kept:
                proved_nothing = True
                print(f"fails before, though the plan says it holds what stays the same: {test}")
            elif passed:
                proved_nothing = True
                print(f"passes before, so it proves nothing: {test}")
            else:
                print(f"fails before: {test}")
    return 1 if proved_nothing else 0
