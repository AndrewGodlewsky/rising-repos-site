"""`python -m sitework <command>`: hand the rest of the line to the command's module.

A module is imported only when its command is asked for, so that a command which needs nothing but git still runs
where a browser, or GitHub's CLI, is missing.
"""

import importlib
import sys

COMMANDS = {
    "pickup": ("sitework.pickup", "Choose the issue this run works on, and claim it"),
    "comment": ("sitework.issue", "Post one of the workflow's comments on an issue, or edit the one that is there"),
    "stop": ("sitework.issue", "Stop an issue for the owner, or for data it waits on"),
    "close": ("sitework.issue", "Post what shipped, close the issue, and remove its branch"),
    "check": ("sitework.check", "Run every check a change has to pass"),
    "guard": ("sitework.guard", "Name each guarded path a change touches"),
    "new-tests": ("sitework.newtests", "Show that each test a change adds fails on the commit before"),
    "criteria": ("sitework.criteria", "Show that each criterion of the plan has a proof that passes"),
    "altered-tests": ("sitework.altered", "List the existing tests a change altered or removed"),
    "layout-report": ("sitework.layout", "Describe in words how the pages a change altered are laid out"),
    "pictures": ("sitework.layout", "Take a picture of each page a change altered, for the owner"),
    "job": ("sitework.job", "Wait for a pull request's own job, and say how it ended"),
    "ship": ("sitework.ship", "Merge a pull request once every condition of the merge holds"),
    "confirm": ("sitework.confirm", "See that a merged feature is live, works, and left the site within its limits"),
    "revert": ("sitework.revert", "Put the site back by reverting every merge of a feature that stands"),
    "stage": ("sitework.digest", "Mark in the run's record that a stage begins"),
    "digest": ("sitework.digest", "Make a one-page digest of a run from its record"),
    "feedback": ("sitework.feedback", "File what a run taught as issues, or add to one that is already open"),
    "notify": ("sitework.notify", "Send the owner one message on Discord"),
}
"""Each command, the module that holds it, and what it does. A module's `main` takes the command's name and the
arguments after it, and gives the exit code."""


def usage() -> str:
    width = max(len(name) for name in COMMANDS)
    lines = [f"  {name.ljust(width)}  {what}" for name, (_, what) in COMMANDS.items()]
    return "usage: python -m sitework <command> [arguments]\n\n" + "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in COMMANDS:
        print(usage())
        return 2
    module, _ = COMMANDS[argv[1]]
    return importlib.import_module(module).main(argv[1], argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
