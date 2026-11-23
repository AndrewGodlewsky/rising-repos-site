# Every push to main is a production deploy, and there is no preview

The site is developed on `main`, and each push to `main` is built and uploaded
to risingrepos.com. No branch gets a preview: a pull request runs the tests
and the build and uploads nothing, so other work is looked at by building it
locally. One branch keeps the scheduled checks, which GitHub runs only from
the default branch, watching the pages a reader gets, and keeps every change
a small one.

## Status

Accepted. RisingRepos's decision record 0009 holds it. It turned down a
long-lived branch merged at the end, and a second hosting project. Until
go-live (RisingRepos#58) each upload went to a preview address. Since then
nothing is uploaded there.

## Consequences

- A merge is a release. Nothing is uploaded unless the tests pass on that
  push: the deploy job waits for the build job.
- The site eval and the stale check measure the live site after the fact, and
  hold nothing back. By the time the eval runs, the pages are live.
- A page taken out of the repository can go on being served at its exact
  address for up to a week. So nothing is put on the site in the expectation
  that it can be withdrawn quickly.
- `RUNBOOK.md` says how risingrepos.com can be returned to the earlier site.

## Confirmed by

`tests/test_workflow.py::TheWorkflow::test_a_push_to_main_deploys_and_a_pull_request_only_builds`,
`tests/test_workflow.py::TheWorkflow::test_it_has_a_build_job_and_a_deploy_job_and_nothing_else`,
and
`tests/test_workflow.py::TheWorkflow::test_uploads_go_to_the_production_branch_since_go_live`.
