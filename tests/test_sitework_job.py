"""`job` waits for a pull request's own job in one call, and says how it ended (#62).

No test reaches GitHub or waits. `sitework.shell.run` is replaced by a stand-in that answers each command from
what the test gives it, in the shapes `gh` answers in, and the sleep between two looks by one that only counts.
"""

import contextlib
import io
import json
import unittest
from unittest import mock

from sitework import job, shell

HEAD = "a" * 40
OLDER = "c" * 40
VIEW = "gh pr view"
RUN = "https://github.com/the-owner/the-site/actions/runs/45489207264/job/138811544305"


class InTurn:
    """Answers given one at each asking, and the last of them from then on."""

    def __init__(self, *answers):
        self.answers = list(answers)

    def next(self):
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]


class Shell:
    """Stands in for `sitework.shell.run`. A command is answered by the answer whose words it begins with, the
    longest of them when several do, and a command with no answer fails the test. An answer that is not text is
    given as the JSON `gh` would print."""

    def __init__(self, answers: dict):
        self.answers = answers
        self.ran = []

    def __call__(self, *command, cwd=None, check=True, stdin=None):
        line = " ".join(command)
        self.ran.append(line)
        starts = [start for start in self.answers if line.startswith(start)]
        if not starts:
            raise AssertionError(f"the test gave no answer for: {line}")
        answer = self.answers[max(starts, key=len)]
        if isinstance(answer, InTurn):
            answer = answer.next()
        return answer if isinstance(answer, str) else json.dumps(answer)


def check(name: str, conclusion: str) -> dict:
    """One check of a pull request, as `gh pr view` gives it. One with no conclusion is queued or running."""
    return {
        "__typename": "CheckRun",
        "conclusion": conclusion,
        "detailsUrl": RUN,
        "name": name,
        "status": "COMPLETED" if conclusion else "IN_PROGRESS",
        "workflowName": "Build and deploy",
    }


def pull(*checks: dict, head: str = HEAD) -> dict:
    return {"number": 77, "headRefOid": head, "statusCheckRollup": list(checks)}


class Job(unittest.TestCase):
    """A test with the stand-in in place, the checkout on the head of pull request #77, and that head's job
    passed, so that each test changes the one answer it is about."""

    def setUp(self):
        self.answers = {
            VIEW: pull(check("build", "SUCCESS"), check("deploy", "SKIPPED")),
            "git rev-parse HEAD": HEAD,
        }
        self.shell = Shell(self.answers)
        self.enterContext(mock.patch.object(shell, "run", self.shell))
        self.slept = []
        self.enterContext(mock.patch.object(job, "sleep", self.slept.append))

    def run_command(self, *arguments: str) -> tuple[int, dict | None, str]:
        """Run `job`, and give its exit code, the JSON object it printed, and everything it printed."""
        printed, progress = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(progress):
            code = job.main("job", list(arguments))
        text = printed.getvalue()
        return code, json.loads(text) if text.lstrip().startswith("{") else None, text + progress.getvalue()

    def test_a_job_that_passed_exits_0_and_names_each_check_that_was_not_skipped(self):
        code, report, _ = self.run_command()
        self.assertEqual(code, 0)
        self.assertEqual((report["pull"], report["commit"], report["result"]), (77, HEAD, "passed"))
        self.assertEqual(report["checks"], [{"name": "build", "result": "success", "run": 45489207264, "url": RUN}])
        self.assertEqual(self.slept, [])

    def test_a_job_that_github_has_not_listed_yet_is_waited_for_and_does_not_end_the_wait(self):
        # Asked just after a push, GitHub reports no check at all, and `gh pr checks --watch` ended there.
        self.answers[VIEW] = InTurn(pull(), pull(check("build", "")), pull(check("build", "SUCCESS")))
        code, report, _ = self.run_command()
        self.assertEqual((code, report["result"]), (0, "passed"))
        self.assertEqual(self.slept, [20, 20])

    def test_a_job_that_failed_exits_1_and_gives_the_run_to_read_or_to_run_again(self):
        self.answers[VIEW] = pull(check("build", "FAILURE"), check("deploy", "SKIPPED"))
        code, report, _ = self.run_command()
        self.assertEqual((code, report["result"]), (1, "failed"))
        self.assertEqual(report["checks"][0]["run"], 45489207264)
        self.assertIn("build (failure)", report["why"])

    def test_a_job_that_has_not_ended_after_20_minutes_exits_1_and_says_it_has_not_finished(self):
        self.answers[VIEW] = pull(check("build", ""))
        code, report, _ = self.run_command()
        self.assertEqual((code, report["result"]), (1, "not finished"))
        self.assertEqual(sum(self.slept), 20 * 60)

    def test_a_checkout_whose_commit_was_not_pushed_is_told_to_push_and_no_job_is_waited_for(self):
        # The pull request's head is the commit before, whose job passed, and that says nothing of this commit.
        self.answers[VIEW] = pull(check("build", "SUCCESS"), head=OLDER)
        code, report, printed = self.run_command()
        self.assertEqual((code, report), (1, None))
        self.assertIn("Push first", printed)
        self.assertEqual(self.slept, [])

    def test_a_pull_request_named_by_its_number_is_judged_by_its_own_head_whatever_the_checkout_is_on(self):
        self.answers[f"{VIEW} 77"] = pull(check("build", "SUCCESS"), head=OLDER)
        code, report, _ = self.run_command("77")
        self.assertEqual((code, report["commit"]), (0, OLDER))


if __name__ == "__main__":
    unittest.main()
