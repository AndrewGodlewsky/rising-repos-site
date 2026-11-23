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
import ast
import re
from fnmatch import fnmatchcase
from pathlib import Path

from sitework import rules, shell

POLICY = "the policy that lets a page's script run"
OWNERS = "the owner's tests, which a change adds to and takes nothing from"

AT_THE_TOP = "a new file or folder at the top of the repository, which the checks are run from"
"""Why a path is guarded that a change adds outside every folder the repository had. Each check is run from the
top of the repository, and Python reads the folder it is run from ahead of its own modules, so a `fnmatch.py` or
a `unittest/` there is run in place of the real one. A tool's settings are read from there as well."""

COMMENT = re.compile(r"\{#.*?#\}", re.DOTALL)
"""A template comment, from its `{#` to the first `#}` after it, as the build reads one. The build leaves it out
of the page, so nothing it holds is on a page."""

META = re.compile(r"<meta\b(?:\{%.*?%\}|\{\{.*?\}\}|[^>])*+>", re.DOTALL | re.IGNORECASE)
"""A `<meta>` element as a template writes it, once the template's comments are left out. What a template tag or
expression holds is passed over whole, so that a `>` inside one does not end the element early."""


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
    not its value, and a change to the script leaves the text as it was.

    The template's comments are left out before the elements are looked for. An element put inside a comment
    reads as it did and is on no page, so a change that hid the policy there would otherwise be read as no
    change to it."""
    written = COMMENT.sub("", template)
    return [element for element in META.findall(written) if "content-security-policy" in element.lower()]


def lost_lines(base: str, head: str, repository: Path | None = None) -> set[str]:
    """Each of the owner's tests that the change took a line from. A reworded line is one taken and one added.
    Git counts no lines in a file that is not text, so one of those that changed is taken to have lost some.
    This is the rule for a file among them that is not Python, as the list of their sentences is not. A line
    added to a file of Python can take a test away, so `more_than_added` reads one of those."""
    counted = shell.git("diff", "--numstat", "--no-renames", "-z", base, head, "--", rules.OWNERS_TESTS, cwd=repository)
    records = [record.split("\t", 2) for record in counted.split("\0")[:-1]]
    return {path for _, lost, path in records if lost != "0"}


def is_words(statement: ast.stmt) -> bool:
    """Whether a statement is a string and nothing more: a docstring where it comes first, and elsewhere the words
    this repository writes under a constant to say what it is. It does nothing when it is run."""
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )


def bound(statement: ast.stmt) -> set[str]:
    """Each name a statement gives a meaning where it stands: a function's or a class's own name, each name an
    import brings in, and each name that is assigned to. A statement that holds others, as an `if` does, is read
    with them, since what they bind is bound where it stands."""
    if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return {statement.name}
    # An assignment is read for the names it is to. Its value binds none here, though a comprehension in it has
    # names of its own.
    if isinstance(statement, ast.Assign):
        stored = statement.targets
    elif isinstance(statement, ast.AnnAssign | ast.AugAssign):
        stored = [statement.target]
    else:
        stored = [statement]
    names = set()
    for node in (node for part in stored for node in ast.walk(part)):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, ast.alias):
            names.add(node.asname or node.name.partition(".")[0])
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
    return names


def called(statement: ast.stmt, inside: str) -> str:
    """How a reason names a statement the file had: by each name it binds, with its class's name before a
    member's, or by the line it began on when it binds none."""
    names = sorted(bound(statement))
    return " and ".join(f"`{inside}{name}`" for name in names) if names else f"what was on line {statement.lineno}"


def mark(statement: ast.stmt, top: bool) -> str:
    """What has to be as it was for a statement to be one the file had: all of it, as `ast.dump` writes it, which
    holds a function's decorators and its body, and in which a comment and a line's layout do not show. A class at
    the top of a file is told by its name, its decorators, and its bases alone, since a change may add a member to
    it. Its members are then compared one by one."""
    if top and isinstance(statement, ast.ClassDef):
        return ast.dump(ast.ClassDef(**{**dict(ast.iter_fields(statement)), "body": []}))
    return ast.dump(statement)


RUNS_THE_FILE = ast.dump(ast.parse('if __name__ == "__main__":\n    unittest.main()').body[0])
"""The two lines each file of the owner's tests ends with, which run its tests when the file is run as a program.
They do nothing when the file is imported, which is how every check reads it, so a new file may end with them as
the others do."""


def may_be_added(statement: ast.stmt) -> bool:
    """Whether a change may add a statement at the top of one of the owner's tests: an import of names, a
    function, a class, an assignment to a name, a docstring, or the two lines that run the file as a program. Any
    other is code that runs when the file is imported, where it can change what the folder's other files hold, as
    an assignment to an attribute of one of their classes does."""
    if isinstance(statement, ast.Import | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return True
    if isinstance(statement, ast.ImportFrom):
        # An import of every name a module has does not say which names it binds, and one may be a name the file had.
        return all(alias.name != "*" for alias in statement.names)
    if isinstance(statement, ast.Assign):
        return all(isinstance(target, ast.Name) for target in statement.targets)
    if isinstance(statement, ast.AnnAssign):
        return isinstance(statement.target, ast.Name)
    return is_words(statement) or ast.dump(statement) == RUNS_THE_FILE


def one_by_one(body: list[ast.stmt]) -> list[ast.stmt]:
    """The statements of a file or of a class that a change is held to: all but a docstring that comes first,
    which may change, since a new sentence can change what a file's docstring lists. An import of several names
    is read as an import of each, on the line that name is on. The lint wants the names a file takes from one
    module in one import, so a new test that needs another helper adds its name to an import the file had, and
    that has to read as a name added and not as an import changed."""
    statements = []
    for statement in body[1:] if body and is_words(body[0]) else body:
        if isinstance(statement, ast.Import | ast.ImportFrom):
            fields = dict(ast.iter_fields(statement))
            statements += [
                type(statement)(**{**fields, "names": [name]}, lineno=name.lineno) for name in statement.names
            ]
        else:
            statements.append(statement)
    return statements


def beyond_adding(was: list[ast.stmt], now: list[ast.stmt], inside: str = "") -> str | None:
    """What a change did, that is more than adding, to the statements at the top of one of the owner's tests, or
    to the members of a class there when `inside` is that class's name and a dot. None when it only added.

    The statements the file had have to be there still, each as it was and in the order they were in, with the
    new ones anywhere among them."""
    was, now = one_by_one(was), one_by_one(now)
    marks = [mark(statement, not inside) for statement in was]
    kept, added = 0, []
    for statement in now:
        if kept < len(was) and mark(statement, not inside) == marks[kept]:
            if not inside and isinstance(statement, ast.ClassDef):
                if what := beyond_adding(was[kept].body, statement.body, f"{statement.name}."):
                    return what
            kept += 1
        else:
            added.append(statement)
    if kept < len(was):
        return f"this file changed, moved, or lost {called(was[kept], inside)}"
    names = set().union(*map(bound, was))
    for statement in added:
        # Whichever of two definitions comes later takes the other's place, so a new one of a name the file had
        # is a change to what the file had.
        if again := sorted(bound(statement) & names):
            return f"this file defines `{inside}{again[0]}` a second time"
        if not inside and not may_be_added(statement):
            return (
                f"this file gained a statement on line {statement.lineno} that is not an import of names, a "
                "function, a class, an assignment to a name, or a docstring"
            )
    return None


def more_than_added(was: str, now: str) -> str | None:
    """What a change did to one of the owner's tests in Python that is more than adding to it, in words, or None
    when it only added. `was` is the file's text where the change began, which is empty for a new file, and `now`
    is its text where the change ends.

    The file is read for what it means and not for its lines, since a line that is added can take a test away:
    a `return` or a skip at the head of a test, a second definition of a helper under the first, a statement at
    the top of a new file that changes the others when the file is imported. A file that cannot be read, which a
    file nested too deep for Python is as well, is one whose meaning cannot be held, and is named."""
    try:
        return beyond_adding(ast.parse(was).body, ast.parse(now).body)
    except SyntaxError, RecursionError:
        return "this file cannot be read as Python, before the change or after it"


def new_at_the_top(base: str, paths: dict[str, str], repository: Path | None = None) -> list[str]:
    """Each path the change adds at the top of the repository: a file there, or a file under a folder there that
    the commit the change began from does not have. A file added inside a folder that commit has is none of
    them, and neither is a change to a file that was at the top already."""
    folders = shell.git("ls-tree", "-d", "--name-only", "-z", base, cwd=repository).split("\0")[:-1]
    return [
        path for path, how in paths.items() if how == "A" and ("/" not in path or path.split("/")[0] not in folders)
    ]


def touched(base: str, head: str, repository: Path | None = None) -> dict[str, str]:
    """Each guarded path the change touches, with why it is guarded."""
    paths = changed(base, head, repository=repository)
    found = {}
    for why, patterns in rules.GUARDED.items():
        for path in paths:
            if any(fnmatchcase(path, pattern) for pattern in patterns):
                found.setdefault(path, why)
    for path in new_at_the_top(base, paths, repository):
        found.setdefault(path, AT_THE_TOP)
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
                what = "this file was removed or renamed"
            elif path.endswith(".py"):
                what = more_than_added(read(base, path, repository), read(head, path, repository))
            else:
                what = "this file lost a line" if path in lost else None
            if what:
                found[path] = f"{OWNERS}: {what}"
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
