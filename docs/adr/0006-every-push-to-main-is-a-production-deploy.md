# Every push to main is a production deploy, and there is no preview

The site is developed on `main`, and each push to `main` is built and uploaded
to risingrepos.com. No branch gets a preview: a pull request runs the checks
and the build and uploads nothing, so other work is looked at by building it
locally. One branch keeps the scheduled checks, which GitHub runs only from
the default branch, watching the pages a reader gets, and keeps every change
a small one.

One push to `main` builds and uploads nothing: a push that changes only
`docs/workflow-notes/`, the notes the feature workflow keeps of its runs. No
page is made from that folder, so its pages would be the ones already live.
The owner chose on 23 November 2026 that the notes are kept here and that a
push of them deploys nothing.

## Status

Accepted. RisingRepos's decision record 0009 holds it. It turned down a
long-lived branch merged at the end, and a second hosting project. Until
go-live (RisingRepos#58) each upload went to a preview address. Since then
nothing is uploaded there.

## Consequences

- A merge is a release. Nothing is uploaded unless the checks pass on that
  push: the deploy job waits for the build job.
- The workflow leaves out the notes' folder by name, and nothing else. A list
  of the files that do make a page would be the other way to write it, and a
  file left off such a list would be a change that should have deployed and
  did not, with nothing to say so.
- A run uploads its pages only while its commit is the head of `main`. So the
  notes are pushed only once the run of the newest commit that changes a page
  has finished: pushed sooner, they would leave that run's pages unuploaded.
- The site eval and the stale check measure the live site after the fact, and
  hold nothing back. By the time the eval runs, the pages are live.
- A page taken out of the repository can go on being served at its exact
  address for up to a week. So nothing is put on the site in the expectation
  that it can be withdrawn quickly.
- `RUNBOOK.md` says how risingrepos.com can be returned to the earlier site.

## Confirmed by

`tests/test_workflow.py::TheWorkflow::test_a_push_to_main_deploys_and_a_pull_request_only_builds`,
`tests/test_workflow.py::TheWorkflow::test_a_push_that_changes_only_the_workflows_notes_starts_no_run_and_nothing_else_is_left_out`,
`tests/test_workflow.py::TheWorkflow::test_it_has_a_build_job_and_a_deploy_job_and_nothing_else`,
and
`tests/test_workflow.py::TheWorkflow::test_uploads_go_to_the_production_branch_since_go_live`.
