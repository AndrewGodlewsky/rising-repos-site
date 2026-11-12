"""The deploy workflow keeps the build apart from the upload.

The daily data push can change any file in this repository except a workflow.
So nothing it can change may run in the job that holds the Cloudflare
credential. Each test below names one thing the workflow has to guarantee.
"""

import re
import unittest

import yaml

from helpers import SECRET, load_workflow

FULL_SHA = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")


def actions(job: dict) -> set[str]:
    return {step["uses"].split("@")[0] for step in job["steps"] if "uses" in step}


def step_using(job: dict, action: str) -> dict:
    (step,) = [step for step in job["steps"] if step.get("uses", "").startswith(action + "@")]
    return step


def step_named(job: dict, name: str) -> dict:
    (step,) = [step for step in job["steps"] if step.get("name") == name]
    return step


class TheWorkflow(unittest.TestCase):
    def setUp(self):
        self.workflow = load_workflow("deploy.yml")
        self.build = self.workflow["jobs"]["build"]
        self.deploy = self.workflow["jobs"]["deploy"]

    def test_it_has_a_build_job_and_a_deploy_job_and_nothing_else(self):
        self.assertEqual(set(self.workflow["jobs"]), {"build", "deploy"})
        self.assertEqual(self.deploy["needs"], "build")

    def test_no_job_gets_a_permission_it_does_not_ask_for(self):
        self.assertEqual(self.workflow["permissions"], {})

    def test_the_build_job_can_only_read_the_repository(self):
        self.assertEqual(self.build["permissions"], {"contents": "read"})
        self.assertIs(step_using(self.build, "actions/checkout")["with"]["persist-credentials"], False)

    def test_the_build_job_references_no_secret(self):
        self.assertIsNone(SECRET.search(yaml.safe_dump(self.build)))
        self.assertNotIn("environment", self.build)

    def test_the_build_job_hands_its_output_to_the_deploy_job_as_an_artifact(self):
        upload = step_using(self.build, "actions/upload-artifact")["with"]
        download = step_using(self.deploy, "actions/download-artifact")["with"]
        self.assertEqual(upload["path"], "dist")
        self.assertEqual(download["name"], upload["name"])

    def test_the_deploy_job_does_not_check_out_the_repository(self):
        self.assertEqual(actions(self.deploy), {"actions/download-artifact"})

    def test_the_deploy_job_runs_a_wrangler_whose_version_is_pinned_in_this_file(self):
        command = step_named(self.deploy, "Upload to Cloudflare Pages")["run"]
        self.assertRegex(command, r"--package=wrangler@\d+\.\d+\.\d+ ")
        self.assertRegex(command, r"--before=\d{4}-\d{2}-\d{2} ")
        self.assertIn("--ignore-scripts", command)

    def test_the_deploy_job_uploads_only_static_files(self):
        steps = [step.get("name") for step in self.deploy["steps"]]
        check = step_named(self.deploy, "Refuse code that would run on Cloudflare")["run"]
        self.assertIn("site/_worker.js", check)
        self.assertLess(steps.index("Refuse code that would run on Cloudflare"), steps.index("Upload to Cloudflare Pages"))

    def test_the_cloudflare_credential_comes_from_the_deploy_environment_and_only_the_deploy_job_has_it(self):
        self.assertEqual(self.deploy["environment"], "deploy")
        self.assertEqual(self.deploy["permissions"], {})
        upload = step_named(self.deploy, "Upload to Cloudflare Pages")
        self.assertEqual(
            {name: value for name, value in upload["env"].items() if SECRET.search(value)},
            {
                "CLOUDFLARE_API_TOKEN": "${{ secrets.CLOUDFLARE_API_TOKEN }}",
                "CLOUDFLARE_ACCOUNT_ID": "${{ secrets.CLOUDFLARE_ACCOUNT_ID }}",
            },
        )
        others = [step for step in self.deploy["steps"] if step is not upload]
        self.assertIsNone(SECRET.search(yaml.safe_dump(others)))
        self.assertIsNone(SECRET.search(yaml.safe_dump(self.workflow.get("env", {}))))

    def test_a_push_to_main_deploys_and_a_pull_request_only_builds(self):
        self.assertEqual(self.workflow["on"]["push"], {"branches": ["main"]})
        self.assertIn("pull_request", self.workflow["on"])
        self.assertEqual(set(self.workflow["on"]), {"push", "pull_request"})
        self.assertEqual(self.deploy["if"], "github.event_name == 'push' && github.ref == 'refs/heads/main'")
        self.assertNotIn("if", self.build)

    def test_uploads_go_to_the_preview_until_go_live(self):
        self.assertEqual(self.workflow["env"]["PAGES_BRANCH"], "preview")
        command = step_named(self.deploy, "Upload to Cloudflare Pages")["run"]
        self.assertIn('--project-name=risingrepos --branch="$PAGES_BRANCH"', command)

    def test_of_two_pushes_to_main_the_older_ones_pages_are_never_uploaded_after_the_newer_ones(self):
        # The builds of two pushes run at once, and either can finish first. Their uploads take turns, and
        # each run uploads only while its commit is still the head of main. So the run of an older push that
        # comes to its turn after a newer push leaves the upload to the newer push's run.
        self.assertEqual(self.deploy["concurrency"], {"group": "cloudflare-pages-upload", "cancel-in-progress": False})
        steps = [step.get("name") for step in self.deploy["steps"]]
        self.assertEqual(steps.index("Upload only the newest push") + 1, steps.index("Upload to Cloudflare Pages"))
        newest = step_named(self.deploy, "Upload only the newest push")
        # The whole script, because a one-word change in either branch (newest=true where main has moved on)
        # uploads every push again.
        self.assertEqual(
            newest["run"],
            'line=$(git ls-remote --exit-code "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY" refs/heads/main)\n'
            "head=${line%%[[:space:]]*}\n"
            'if [ "$head" = "$GITHUB_SHA" ]; then\n'
            '  echo "newest=true" >> "$GITHUB_OUTPUT"\n'
            "else\n"
            '  echo "::notice::Not uploaded: main has moved on to $head from this run\'s $GITHUB_SHA.'
            ' The run for $head uploads once its build passes."\n'
            '  echo "newest=false" >> "$GITHUB_OUTPUT"\n'
            "fi\n",
        )
        upload = step_named(self.deploy, "Upload to Cloudflare Pages")
        self.assertEqual(upload["if"], f"steps.{newest['id']}.outputs.newest == 'true'")

    def test_pages_built_for_an_upload_that_is_not_production_ask_not_to_be_indexed(self):
        command = step_named(self.build, "Build the pages")["run"]
        self.assertIn('if [ "$PAGES_BRANCH" = main ]', command)
        self.assertRegex(command, r"else\s+uv run --locked python -m sitebuild dist --noindex\s+fi")

    def test_every_action_is_pinned_to_a_full_commit_sha(self):
        for job in self.workflow["jobs"].values():
            for step in job["steps"]:
                if "uses" in step:
                    self.assertRegex(step["uses"], FULL_SHA)


if __name__ == "__main__":
    unittest.main()
