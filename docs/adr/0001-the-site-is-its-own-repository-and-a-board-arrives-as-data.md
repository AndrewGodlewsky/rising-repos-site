# The site is its own repository, and a board reaches it as data committed here

The site's pages live in this repository, and RisingRepos, which works out the
boards, holds none of them. Each day RisingRepos's publish commits a board
day's data file to `site-data/` on `main` here, and this repository's workflow
builds the pages from it and uploads them. Only what a board shows crosses, in
that one direction: the full record of star counts and scores behind it stays
with RisingRepos. This keeps the hosting credential in GitHub Actions, and
lets the site's build refuse a bad file before any page is written.

## Status

Accepted. RisingRepos's decision records 0004 and 0007 hold it. They turned
down building and uploading the pages from the machine that publishes,
keeping the data in object storage for the workflow to fetch, and having the
page fetch its data in the reader's browser.

## Consequences

- `site-data/` is RisingRepos's output. A change to the pages never edits it,
  and a feature that needs a figure the files do not carry asks RisingRepos
  for it ([0002](0002-risingrepos-owns-the-data-contract.md)).
- Every publish is a push to `main`, so it ends in a deploy
  ([0006](0006-every-push-to-main-is-a-production-deploy.md)), and it arrives
  whatever else is in flight.
- The daily push can change any file here but a workflow. So the job that
  holds the hosting credential runs nothing from this repository's files.
- This repository decides how a board looks and what a reader can do with it.
  RisingRepos decides what is on a board and how it is scored.

## Confirmed by

`tests/test_workflow.py::TheWorkflow::test_the_deploy_job_does_not_check_out_the_repository`,
`tests/test_workflow.py::TheWorkflow::test_the_build_job_references_no_secret`,
`tests/test_build.py::TheBuild::test_without_the_data_option_it_builds_from_the_repositorys_site_data`,
and
`tests/test_data.py::TheDataFiles::test_a_board_day_file_that_does_not_match_its_schema_fails_the_build_and_names_the_file`.
