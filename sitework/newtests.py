"""`new-tests`: show that each test a change adds fails on the commit before.

A test that passes with the feature and without it proves nothing (docs/workflow-plan.md, section 6, and D18
there, and standard C18). So each test the change adds, among the agents' tests and the owner's, is run on the
code as it was where the change began, and has to fail or error there.
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
unittest.main(module=None, argv=sys.argv[:2])
"""
"""A program that runs the one test named by its first argument, with each folder after it put on the path first,
as `unittest discover -s` puts the folder it is given."""


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
    """Whether the test passes when run in `checkout`, which is this repository when none is given."""
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


def main(command: str, arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="Run each test a change adds on the code before the change. Exit 0 when each fails there, or "
        "when the change adds none, and 1 when one passes there.",
    )
    guard.add_change(parser)
    options = parser.parse_args(arguments)
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
            if passes(test, checkout):
                proved_nothing = True
                print(f"passes before, so it proves nothing: {test}")
            else:
                print(f"fails before: {test}")
    return 1 if proved_nothing else 0
