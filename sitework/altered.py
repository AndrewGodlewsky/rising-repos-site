"""`altered-tests`: list the existing tests a change altered or removed.

The agent that builds a feature changes and removes the agents' tests as the feature needs, so nothing stops
here. The reviewer reads this list, to catch a test that was loosened so that a change passes
(docs/workflow-plan.md, sections 5 and 9). The owner's tests are not listed: the guard names a change to one.
"""

import argparse
import ast
from pathlib import PurePosixPath

from sitework import guard

TESTS = "tests/"
"""The agents' tests, written as `sitework.rules.OWNERS_TESTS` writes the owner's."""


def is_test_file(path: str) -> bool:
    """Whether unittest would read tests from this file."""
    name = PurePosixPath(path).name
    return name.startswith("test_") and name.endswith(".py")


def tests_at(ref: str, path: str) -> dict[str, str]:
    """Each test the file holds as the commit has it: a `test_*` method of a class at the top of the file. A test
    is named as `<path>::<class>::<method>`, and comes with its code as `ast.dump` writes it, in which a comment,
    a line's layout, and where the method stands in the file do not show. A commit without the file holds none."""
    found = {}
    for node in ast.parse(guard.read(ref, path)).body:
        if isinstance(node, ast.ClassDef):
            for method in node.body:
                if isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef) and method.name.startswith("test_"):
                    found[f"{path}::{node.name}::{method.name}"] = ast.dump(method)
    return found


def main(command: str, arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="List each of the agents' tests that a change altered or removed. It informs, and exits 0.",
    )
    guard.add_change(parser)
    options = parser.parse_args(arguments)
    base = guard.base_of(options)
    lines = []
    for path in sorted(guard.changed(base, options.head, TESTS)):
        if is_test_file(path):
            after = tests_at(options.head, path)
            for test, code in tests_at(base, path).items():
                if test not in after:
                    lines.append(f"removed: {test}")
                elif after[test] != code:
                    lines.append(f"altered: {test}")
    print("\n".join(lines) or "no existing test was altered or removed")
    return 0
