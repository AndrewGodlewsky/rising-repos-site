"""`guard`: name each guarded path a change touches.

A feature must not change what judges it: a workflow, a dependency, a limit, the policy, the type, the standards,
the owner's tests, or this workflow's own scripts (docs/workflow-plan.md, section 9, and D18 there). The paths are
`sitework.rules.GUARDED`. A change that has to touch one waits for the owner, who names it on the issue.

The ship script runs the copy of this module that is on main, taken out into a temporary folder, against the
repository being worked on, since a branch could otherwise loosen the guard it is held to. So this module works
from any folder, and imports nothing of the workflow but its rules and its shell. The commands that read a change
as this one does take from here how a change is named and read, since this module can take nothing from them.
"""

import argparse
import re
from fnmatch import fnmatchcase
from pathlib import Path

from sitework import rules, shell

POLICY = "the policy that lets a page's script run"
OWNERS = "the owner's tests, which a change adds to and takes nothing from"

META = re.compile(r"<meta\b(?:\{#.*?#\}|\{%.*?%\}|\{\{.*?\}\}|[^>])*+>", re.DOTALL | re.IGNORECASE)
"""A `<meta>` element as a template writes it. What a template tag, expression, or comment holds is passed over
whole, so that a `>` inside one does not end the element early."""


def add_change(parser: argparse.ArgumentParser) -> None:
    """Give a command the two options that name the change it reads."""
    parser.add_argument(
        "--base", metavar="REF", help="the commit the change began from (default: where the head left origin/main)"
    )
    parser.add_argument("--head", metavar="REF", default="HEAD", help="the commit the change ends at (default: HEAD)")


def base_of(options: argparse.Namespace, repository: Path | None = None) -> str:
    """The commit the change began from: the one given, or the newest that origin/main and the head share. What
    main gained after the branch left it is then no part of the branch's change."""
    return options.base or shell.git("merge-base", "origin/main", options.head, cwd=repository)


def changed(base: str, head: str, *paths: str, repository: Path | None = None) -> dict[str, str]:
    """Each path that differs between the two commits, of those under `paths` when any is given, with git's
    letter for how: A for a file the change added, M for one it altered, and D for one it removed. A renamed file
    is one removed and one added, so that both of its names are read."""
    printed = shell.git("diff", "--name-status", "--no-renames", "-z", base, head, "--", *paths, cwd=repository)
    fields = printed.split("\0")[:-1]
    return dict(zip(fields[1::2], fields[::2], strict=True))


def read(ref: str, path: str, repository: Path | None = None) -> str:
    """The file as the commit has it, or nothing when the commit has no such file."""
    return shell.git("show", f"{ref}:{path}", cwd=repository, check=False)


def policy(template: str) -> list[str]:
    """The policy's own text in a template: each `<meta>` that states a Content-Security-Policy, as written. The
    script's hash is worked out when a page is built (`sitebuild.script_hash`), so the text holds its name and
    not its value, and a change to the script leaves the text as it was."""
    return [element for element in META.findall(template) if "content-security-policy" in element.lower()]


def lost_lines(base: str, head: str, repository: Path | None = None) -> set[str]:
    """Each of the owner's tests that the change took a line from. A reworded line is one taken and one added.
    Git counts no lines in a file that is not text, so one of those that changed is taken to have lost some."""
    counted = shell.git("diff", "--numstat", "--no-renames", "-z", base, head, "--", rules.OWNERS_TESTS, cwd=repository)
    records = [record.split("\t", 2) for record in counted.split("\0")[:-1]]
    return {path for _, lost, path in records if lost != "0"}


def touched(base: str, head: str, repository: Path | None = None) -> dict[str, str]:
    """Each guarded path the change touches, with why it is guarded."""
    paths = changed(base, head, repository=repository)
    found = {}
    for why, patterns in rules.GUARDED.items():
        for path in paths:
            if any(fnmatchcase(path, pattern) for pattern in patterns):
                found.setdefault(path, why)
    for path in paths:
        if fnmatchcase(path, rules.POLICY_IN):
            before, after = (policy(read(ref, path, repository)) for ref in (base, head))
            if before != after:
                found[path] = POLICY
    owners = {path: how for path, how in paths.items() if path.startswith(rules.OWNERS_TESTS)}
    if owners:
        lost = lost_lines(base, head, repository)
        for path, how in owners.items():
            if how == "D":
                found[path] = f"{OWNERS}: this file was removed or renamed"
            elif path in lost:
                found[path] = f"{OWNERS}: this file lost a line"
    return found


def main(command: str, arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="Name each guarded path a change touches. Exit 0 when there is none, and 1 when there is one.",
    )
    add_change(parser)
    parser.add_argument(
        "--allow",
        metavar="PATTERN",
        nargs="+",
        action="extend",
        default=[],
        help="a pattern of the paths the owner let this change touch, matched as fnmatch matches",
    )
    parser.add_argument("--repository", metavar="PATH", type=Path, help="where git runs (default: this repository)")
    options = parser.parse_args(arguments)
    found = touched(base_of(options, options.repository), options.head, options.repository)
    named = {
        path: why for path, why in found.items() if not any(fnmatchcase(path, allowed) for allowed in options.allow)
    }
    for path, why in sorted(named.items()):
        print(f"{path}: {why}")
    return 1 if named else 0
