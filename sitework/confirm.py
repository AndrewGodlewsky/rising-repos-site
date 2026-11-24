"""`confirm`: see that a merged feature is live, works, and left the site within its limits. Also the reading of
the two workflows' runs, which `pickup` shares to judge whether the site is healthy.

Every merge is a deploy (docs/adr/0006), so a merge is not the end of a feature: its pages have to be uploaded,
the owner's tests have to pass on the live site, and the site eval that follows the deploy has to pass
(docs/workflow-plan.md, section 10). This script reads each of the three and judges none of them. When one fails
because of the change, the agent mends the fault once, and the mend's merge is followed here as the feature's
was. When the mend fails too, or cannot be made, the agent puts the site back with `revert` before it asks the
owner anything. The revert's merge is a deploy as well, so `--revert` reads the same three for it: the feature's
own deploy and eval say nothing of whether the site was put back.

Progress goes to the error stream, so that what is printed is the one JSON object.
"""

import argparse
import json
import sys
import time

from sitework import issue, rules, shell

DEPLOY = "Build and deploy"
EVAL = "Site eval"
JOB, UPLOAD = "deploy", "Upload to Cloudflare Pages"
"""The two workflows, and the job and the step that upload the pages, by the names .github/workflows/deploy.yml
and site-eval.yml give them."""

RUN = "databaseId,headSha,status,conclusion,createdAt,updatedAt,url"

UNMEASURED = ("cancelled", "skipped")
"""How a run of the eval ends when it did not measure the site. The eval's workflow cancels a running eval when
the eval of the next deploy starts, and skips its one job after a deploy that failed. Neither says anything
against the pages."""

WAIT = 20
LOOKS = 60
"""A run is looked at every 20 seconds, 60 times, which is 20 minutes."""
LIVE_WAIT = 60
LIVE_TRIES = 11
"""The owner's tests are tried once, and then once a minute for 10 minutes: a cache can serve the old page for a
while after a deploy."""

sleep = time.sleep
"""The wait between two looks. A test replaces it, so that no test waits."""


def deploy_run(commit: str | None = None) -> dict | None:
    """The run of "Build and deploy" for the push of `commit` to main, or with no commit the newest run for any
    push to main. None when there is none yet. Only a push counts: a pull request from a fork's own main also
    names main as its branch."""
    pushes = ["--workflow", DEPLOY, "--branch", "main", "--event", "push"]
    which = ["--commit", commit] if commit else []
    runs = shell.gh_json("run", "list", *pushes, *which, "--limit", "1", "--json", RUN)
    return runs[0] if runs else None


def eval_after(deploy: dict) -> dict | None:
    """The run of "Site eval" that followed a deploy's run: the first one made for the deploy's commit once that
    run had finished. None when there is none yet. The eval's workflow starts a run when a deploy's run completes,
    and a run of the eval does not name the run it follows, so it is told by its commit and by when it was made."""
    followed = ["--workflow", EVAL, "--event", "workflow_run", "--commit", deploy["headSha"]]
    runs = shell.gh_json("run", "list", *followed, "--limit", "20", "--json", RUN)
    after = [run for run in runs if run["createdAt"] >= deploy["updatedAt"]]
    return min(after, key=lambda run: run["createdAt"]) if after else None


def uploaded(run: dict) -> bool:
    """Whether a deploy's run uploaded its pages. Its deploy job uploads only while its commit is the head of
    main, and leaves the step out when a newer push has arrived."""
    jobs = shell.gh_json("run", "view", str(run["databaseId"]), "--json", "jobs")["jobs"]
    steps = [step for job in jobs if job["name"] == JOB for step in job["steps"] if step["name"] == UPLOAD]
    return any(step["conclusion"] == "success" for step in steps)


def say(progress: str) -> None:
    print(progress, file=sys.stderr, flush=True)


def deployed(merge: str) -> tuple[dict, dict | None]:
    """Wait for the deploy that uploads the merge, and give its result with its run. When the merge's own run left
    the upload to a newer push, the run that uploads the merge is the one for the newer head of main, which
    holds the merge because main is never rewritten. Every push to main starts a run, so the head always has one
    to wait for. The head is asked of GitHub itself, because the checkout's own `origin/main` is as old as its
    last fetch: a head read from it could be the merge, and the deploy would then be said not to have uploaded."""
    commit = merge
    for _ in range(LOOKS):
        run = deploy_run(commit)
        if run is None or run["status"] != "completed":
            say(f"The deploy of {commit[:7]} has not finished.")
            sleep(WAIT)
            continue
        report = {"run": run["databaseId"], "commit": commit, "result": run["conclusion"]}
        if run["conclusion"] != "success":
            return report, run
        if uploaded(run):
            say(f"The deploy of {commit[:7]} uploaded its pages: {run['url']}")
            return report, run
        head = shell.git("ls-remote", "origin", "refs/heads/main").split("\t")[0]
        if head == commit:
            return report | {"result": "not uploaded"}, run
        say(f"The deploy of {commit[:7]} left its upload to a newer push, so the run for {head[:7]} is followed.")
        commit = head
    return {"run": None, "commit": commit, "result": "not finished"}, None


def live() -> dict:
    """Run the owner's tests against the live site, until they pass or the tries run out."""
    # The live address has one owner, the eval, where RUNBOOK.md's table and tests/test_runbook.py hold it. It is
    # imported here and not above because the eval's module brings the generator with it, which `pickup` has no
    # use for when it reads the runs through this module.
    from evals.site.measure import DEPLOYED_SITE

    folder = rules.OWNERS_TESTS.rstrip("/")
    for tries in range(1, LIVE_TRIES + 1):
        try:
            # The address goes to this one command, so that nothing run later reads the live site by mistake.
            shell.run(
                sys.executable, "-m", "unittest", "discover", "-s", folder, "-t", ".", env={"SITE": DEPLOYED_SITE}
            )
        except shell.Failed as error:
            failure = error
        else:
            say(f"The owner's tests pass on {DEPLOYED_SITE}.")
            return {"result": "passed", "tries": tries}
        if tries < LIVE_TRIES:
            say(f"The owner's tests do not pass on {DEPLOYED_SITE} yet. Try {tries} of {LIVE_TRIES}.")
            sleep(LIVE_WAIT)
    say(f"The owner's tests fail on {DEPLOYED_SITE}:\n{failure}")
    return {"result": "failed", "tries": LIVE_TRIES}


def measured(deploy: dict) -> dict:
    """Wait for the site eval that followed the deploy's run, and give its result with the run that was read.

    An eval that did not measure the site is not read as a failure of the change: a revert would then take out
    a feature that did nothing wrong. Such an eval was most often cancelled for the eval of a newer deploy, whose
    pages hold the merge as well, because main is never rewritten. So the eval of the newest deploy to main is
    waited for in its place, as `deployed` follows a newer push. When the newest deploy is the one already
    followed, no other eval measures these pages, and the result is how this one ended."""
    run = None
    for _ in range(LOOKS):
        run = eval_after(deploy)
        if run and run["status"] == "completed":
            newest = deploy_run() if run["conclusion"] in UNMEASURED else None
            if newest is None or newest["databaseId"] == deploy["databaseId"]:
                say(f"The site eval that followed the deploy of {deploy['headSha'][:7]} finished: {run['url']}")
                return {"run": run["databaseId"], "result": run["conclusion"]}
            say(
                f"The site eval that followed the deploy of {deploy['headSha'][:7]} ended as {run['conclusion']} "
                f"and measured nothing ({run['url']}), so the eval that follows the newest deploy to main, of "
                f"{newest['headSha'][:7]}, is read in its place."
            )
            deploy = newest
            continue
        say(f"The site eval that follows the deploy of {deploy['headSha'][:7]} has not finished.")
        sleep(WAIT)
    return {"run": run["databaseId"] if run else None, "result": "not finished"}


def confirm(number: int, reverting: bool = False) -> int:
    """Follow the merge of the feature's pull request, or with `reverting` the merge of the pull request that
    reverts it, through the three steps. `issue.merged` never gives a revert, so without the choice a second
    `confirm` would follow the feature's merge again: a revert whose own deploy failed would read as confirmed,
    and one that mended the site would read as failed.

    Without `reverting` the merge that is followed is the feature's newest, which after a mend is the mend's.
    With it, the revert has to be of what stands. A feature can be reverted and landed again, so its newest
    merged revert may be older than its newest merge, and that revert's deploy says nothing of whether the site
    was put back from the merge that is on main now. So the newest merged revert is followed only when no merge
    of the feature stands after it."""
    if reverting and issue.standing(number):
        print(f"#{number}'s newest merge has no merged pull request that reverts it, so there is nothing to confirm.")
        return 1
    pull = issue.reverted(number) if reverting else issue.merged(number)
    if pull is None:
        what = "merged pull request that reverts it" if reverting else "pull request that merged"
        print(f"#{number} has no {what}, so there is nothing to confirm.")
        return 1
    merge = pull["mergeCommit"]["oid"]
    deploy, run = deployed(merge)
    report = {
        "issue": number,
        "merge": merge,
        "deploy": deploy,
        "live": {"result": "not run"},
        "eval": {"run": None, "result": "not run"},
    }
    if deploy["result"] == "success":
        report["live"] = live()
        report["eval"] = measured(run)
    wanted = {"deploy": "success", "live": "passed", "eval": "success"}
    report["failed"] = [step for step, result in wanted.items() if report[step]["result"] != result]
    print(json.dumps(report, indent=2))
    return 1 if report["failed"] else 0


def main(command: str, arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="See that a merged feature was uploaded, passes the owner's tests on the live site, and passed "
        "the site eval. Exit 0 when all three hold, and 1 when one does not.",
    )
    parser.add_argument("issue", type=int, help="the issue's number")
    parser.add_argument(
        "--revert", action="store_true", help="follow the merge of the pull request that reverts the feature"
    )
    options = parser.parse_args(arguments)
    try:
        return confirm(options.issue, options.revert)
    except shell.Failed as error:
        print(error, file=sys.stderr)
        return 1
