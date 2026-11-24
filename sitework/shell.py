"""How the workflow's scripts run git and GitHub's CLI.

Every script reaches both through `run`, and through nothing else. A test replaces `run` with a stand-in that
answers from a list, so that no test reaches GitHub, pushes, or merges.

A script that needs a checkout of its own makes it with `worktree`, which is the one place that makes one.
"""

import contextlib
import json
import os
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Failed(Exception):
    """A command exited with something other than 0. Its message is the command and what it printed, and `code` is
    what it exited with."""

    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


def run(
    *command: str,
    cwd: Path | None = None,
    check: bool = True,
    stdin: str | Path | None = None,
    env: dict[str, str] | None = None,
) -> str:
    """Run `command` in `cwd`, which is the repository when none is given, and give what it printed, without the
    white space at its ends. A command that fails raises `Failed`, unless `check` is false. `env` adds to the
    environment the command gets.

    What a command prints is read as UTF-8, which is what git and gh write. A Python that is piped writes the
    machine's own encoding on Windows unless it is told otherwise, so each command is told, and a byte that is
    still not UTF-8 is replaced and never stops the script that reads it.

    `stdin` is what the command reads as its standard input. Text is written to it as UTF-8, with each line's end
    as the machine writes one. A file is handed to the command as it is, so that the command reads the file's own
    bytes: that is how what one command wrote reaches another with no byte replaced and no line's end rewritten
    on the way."""
    with contextlib.ExitStack() as opened:
        reads = {"stdin": opened.enter_context(stdin.open("rb"))} if isinstance(stdin, Path) else {"input": stdin}
        done = subprocess.run(
            command,
            cwd=cwd or ROOT,
            **reads,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PYTHONUTF8": "1", **(env or {})},
        )
    if check and done.returncode != 0:
        raise Failed(
            f"{' '.join(command)}: exit {done.returncode}\n{done.stdout}{done.stderr}".strip(), done.returncode
        )
    return done.stdout.strip()


def git(*arguments: str, cwd: Path | None = None, check: bool = True) -> str:
    return run("git", *arguments, cwd=cwd, check=check)


def gh(*arguments: str, stdin: str | None = None, check: bool = True) -> str:
    return run("gh", *arguments, stdin=stdin, check=check)


def gh_json(*arguments: str):
    """What a `gh` command that was asked for JSON printed, read."""
    return json.loads(gh(*arguments))


@contextlib.contextmanager
def worktree(start: str, *options: str) -> Iterator[Path]:
    """A checkout of `start` in a temporary folder, as a worktree of this repository, for the length of a block.

    A script that commits, or that runs the code of another commit, does it there and never in the folder the
    agent works in. That folder may hold a feature's branch and work that is not committed, and a script that
    switched its branch or wrote into it would lose or change what the agent has. So the agent's own tree is left
    as it is, and nothing in it rides along in what the script commits.

    `options` are `git worktree add`'s own. With none the checkout is on no branch, which is all that reading a
    commit needs. The worktree is removed when the block ends, also when the block ends with an error."""
    with tempfile.TemporaryDirectory() as folder:
        tree = Path(folder) / "tree"
        git("worktree", "add", *(options or ("--detach",)), str(tree), start)
        try:
            yield tree
        finally:
            git("worktree", "remove", "--force", str(tree))
