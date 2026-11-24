"""`job`: wait for a pull request's own job, and say how it ended.

A run pushes a commit and then has to know whether the pull request's job passed on it, before it asks for the
review, before the reviewer writes its verdict, and before `ship`. Waiting with `gh pr checks --watch` ended at
once with "no checks reported" when it was asked before GitHub had listed the job, and a wait left in the
background brought a message that only read the whole context again (#62). So this waits in one call, in the
foreground, as `confirm` waits for the deploy: it looks until every check of the head has ended, and a head with
no check yet is one whose checks have not been listed.

It judges by the rule `ship` merges by, which is `ship.checks`, so that a job this calls passed is one `ship`
takes. It prints one JSON object, and its progress goes to the error stream.

The job runs every test, the workflow's own among them, in about four minutes, where the machine's check takes
seven to thirteen (#74). So a commit that adds only a test is better waited for here than checked again on the
machine (#61).
"""

import argparse
import json
import re
import sys
import time

from sitework import shell, ship

WAIT = 20
LOOKS = 60
"""The job is looked at every 20 seconds, 60 times, which is 20 minutes. The build job gives up after 10."""

RUN = re.compile(r"/actions/runs/(\d+)")
"""The number of a workflow's run in the address of one of its jobs, which is what `gh run rerun` takes."""

sleep = time.sleep
"""The wait between two looks. A test replaces it, so that no test waits."""


def say(progress: str) -> None:
    print(progress, file=sys.stderr, flush=True)


def ended(rollup: list[dict]) -> bool:
    """Whether every check has ended, and there is at least one. A check that is queued or running gives no
    conclusion yet."""
    return bool(rollup) and all(check.get("conclusion") for check in rollup)


def report(pull: dict) -> dict:
    """What is printed of a pull request whose checks have ended: each check that was not skipped, with how it
    ended and the run to read or to run again."""
    head = pull["headRefOid"]
    passed, why = ship.checks(pull["statusCheckRollup"], head)
    checks = []
    for check in pull["statusCheckRollup"]:
        result = check["conclusion"].lower()
        if result == "skipped":
            continue
        run = RUN.search(check.get("detailsUrl") or "")
        checks.append(
            {
                "name": check.get("name") or check["__typename"],
                "result": result,
                "run": int(run[1]) if run else None,
                "url": check.get("detailsUrl"),
            }
        )
    return {
        "pull": pull["number"],
        "commit": head,
        "result": "passed" if passed else "failed",
        "why": why,
        "checks": checks,
    }


def job(number: int | None) -> int:
    """Wait for the checks of the pull request's head, and exit 0 when every one passed.

    With no number the pull request is the one of the branch the checkout is on, and its head on GitHub has to be
    the checkout's own commit: a commit that was not pushed has no job, and the job of the commit before it says
    nothing of this one."""
    which = [str(number)] if number else []
    pull = None
    for _ in range(LOOKS):
        pull = shell.gh_json("pr", "view", *which, "--json", "number,headRefOid,statusCheckRollup")
        head = pull["headRefOid"]
        if not number and shell.git("rev-parse", "HEAD") != head:
            print(
                f"The head of pull request #{pull['number']} on GitHub is {head[:7]}, and the checkout is on "
                "another commit. Push first: the job of another commit says nothing of this one."
            )
            return 1
        if ended(pull["statusCheckRollup"]):
            said = report(pull)
            print(json.dumps(said, indent=2))
            return 0 if said["result"] == "passed" else 1
        say(f"The job of pull request #{pull['number']} has not ended for {head[:7]}.")
        sleep(WAIT)
    print(json.dumps({"pull": pull["number"], "commit": pull["headRefOid"], "result": "not finished"}, indent=2))
    return 1


def main(command: str, arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="Wait for a pull request's own job, for up to 20 minutes, and print how each check ended as "
        "one JSON object. Exit 0 when every check passed, and 1 when one failed or none has ended. Run it in the "
        "foreground, once, after the push.",
    )
    parser.add_argument(
        "pull",
        nargs="?",
        type=int,
        help="the pull request's number. With none, the pull request of the branch the checkout is on",
    )
    try:
        return job(parser.parse_args(arguments).pull)
    except shell.Failed as error:
        print(error, file=sys.stderr)
        return 1
