"""The site eval's workflow measures the preview after each deploy, and an address by hand, holding no secret.

It runs code that the daily data push can change, as the build job does, so it holds nothing that code could
misuse: no secret, no environment, and a token that can only read the repository. Each test below names one
thing the workflow has to guarantee.
"""

import re
import unittest
from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
FULL_SHA = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")
SECRET = re.compile(r"\bsecrets\b")
EXPRESSION = re.compile(r"\$\{\{")


def load(name: str) -> dict:
    workflow = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    workflow["on"] = workflow.pop(True)  # YAML 1.1 reads the key `on` as true
    return workflow


def step_using(job: dict, action: str) -> dict:
    (step,) = [step for step in job["steps"] if step.get("uses", "").startswith(action + "@")]
    return step


def step_named(job: dict, name: str) -> dict:
    (step,) = [step for step in job["steps"] if step.get("name") == name]
    return step


class TheSiteEvalWorkflow(unittest.TestCase):
    def setUp(self):
        self.text = (WORKFLOWS / "site-eval.yml").read_text(encoding="utf-8")
        self.workflow = load("site-eval.yml")
        self.deploy = load("deploy.yml")
        (self.job,) = self.workflow["jobs"].values()
        self.measure = step_named(self.job, "Measure")

    def test_it_runs_after_each_deploy_by_hand_and_on_a_pull_request_that_changes_the_eval(self):
        self.assertEqual(set(self.workflow["on"]), {"workflow_run", "workflow_dispatch", "pull_request"})
        self.assertEqual(
            self.workflow["on"]["workflow_run"],
            {"workflows": [self.deploy["name"]], "types": ["completed"], "branches": ["main"]},
        )
        self.assertEqual(self.workflow["on"]["pull_request"], {"paths": [".github/workflows/site-eval.yml", "evals/site/**"]})

    def test_after_a_deploy_it_measures_only_a_push_to_main_whose_run_succeeded(self):
        self.assertEqual(
            self.job["if"],
            "github.event_name != 'workflow_run' || "
            "(github.event.workflow_run.event == 'push' && github.event.workflow_run.conclusion == 'success')",
        )
        # The deployed commit is checked out, so the eval reads that commit's newest board day, and is told which
        # commit it is, so it measures only while that commit is the head of main.
        self.assertEqual(step_using(self.job, "actions/checkout")["with"]["ref"], "${{ github.event.workflow_run.head_sha }}")
        self.assertEqual(self.measure["env"]["SITE_EVAL_COMMIT"], "${{ github.event.workflow_run.head_sha }}")

    def test_it_holds_no_secret_and_cannot_reach_the_deploy_environment(self):
        self.assertIsNone(SECRET.search(self.text))
        self.assertNotIn("environment", self.job)
        self.assertEqual(self.workflow["permissions"], {})
        self.assertEqual(self.job["permissions"], {"contents": "read"})
        self.assertIs(step_using(self.job, "actions/checkout")["with"]["persist-credentials"], False)

    def test_the_address_given_by_hand_reaches_the_eval_only_through_its_environment(self):
        self.assertEqual(
            self.workflow["on"]["workflow_dispatch"]["inputs"]["address"],
            {
                "description": "The https address of the page to measure",
                "required": True,
                "default": "https://preview.risingrepos.pages.dev/",
                "type": "string",
            },
        )
        self.assertEqual(self.measure["env"]["SITE_EVAL_ADDRESS"], "${{ inputs.address }}")
        for step in self.job["steps"]:
            with self.subTest(step.get("name") or step.get("uses")):
                self.assertIsNone(EXPRESSION.search(step.get("run", "")))

    def test_lighthouse_is_pinned_to_one_version_and_none_of_its_packages_runs_an_install_script(self):
        self.assertRegex(
            self.measure["env"]["SITE_EVAL_LIGHTHOUSE"],
            r"^npm exec --yes --ignore-scripts --before=\d{4}-\d{2}-\d{2} --package=lighthouse@\d+\.\d+\.\d+ -- lighthouse$",
        )

    def test_the_eval_runs_on_the_python_and_the_uv_the_build_job_uses(self):
        build = self.deploy["jobs"]["build"]
        self.assertEqual(self.job["runs-on"], build["runs-on"])
        self.assertEqual(self.job["env"]["UV_PYTHON"], build["env"]["UV_PYTHON"])
        self.assertEqual(step_using(self.job, "astral-sh/setup-uv"), step_using(build, "astral-sh/setup-uv"))
        self.assertEqual(self.measure["run"], 'uv run --no-project python evals/site/measure.py --out "$RUNNER_TEMP/site-eval"\n')

    def test_it_keeps_each_runs_numbers_and_reports_as_an_artifact_even_when_it_fails(self):
        upload = step_using(self.job, "actions/upload-artifact")
        self.assertEqual(upload["if"], "always()")
        self.assertEqual(upload["with"]["path"], "${{ runner.temp }}/site-eval")

    def test_it_stops_within_its_timeout_and_a_newer_deploys_measurement_replaces_an_older_ones(self):
        self.assertLessEqual(self.job["timeout-minutes"], 30)
        self.assertEqual(
            self.job["concurrency"],
            {
                "group": "${{ github.event_name == 'workflow_run' && 'site-eval-preview' || format('site-eval-{0}', github.run_id) }}",
                "cancel-in-progress": True,
            },
        )

    def test_every_action_is_pinned_to_a_full_commit_sha(self):
        for step in self.job["steps"]:
            if "uses" in step:
                self.assertRegex(step["uses"], FULL_SHA)


if __name__ == "__main__":
    unittest.main()
