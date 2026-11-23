# RisingRepos owns the data contract, and the site shows only what a file gives

The data files are the one place where the two repositories meet, and
RisingRepos defines them: a schema for each kind of file, a rule for its
version, and an example. Every publish ships the schemas beside the data, in
the same commit, and the build checks each file against the schema that came
with it before it writes a page. The site reads the fields and adds no
ranking of its own. It computes no score and no rank, takes the star bands
from the file and keeps no band limits of its own, and leaves out a fact the
file does not give, where it could have guessed one.

## Status

Accepted. RisingRepos's decision record 0013 holds it. It turned down the site
owning the schemas, because a field is written before it is read, and each
repository keeping its own copy, because copies drift apart.

## Consequences

- RisingRepos adds a field first, to the schema and to the files together. The
  site ignores a field it does not read, and begins to read it in a change of
  its own. A field is removed in the opposite order.
- A page reads a field that older files lack as optional: a file without it
  builds, and its page shows what it showed before the field.
- What the site does work out, it works out at build time by comparing the
  lists the files hold: which repositories are New, and which boards a
  repository was on.
- Every test but one builds from the tests' own copy of the contract's
  example, and one test holds that copy to the bytes of a named RisingRepos
  commit. A change to the contract reaches the copy by a pull request here.
- A schema is code to the validator, which would fetch whatever a schema
  refers to. So the build refuses a schema that refers outside itself, and
  never fetches a reference.

## Confirmed by

`tests/test_reasons.py::TheReason::test_the_page_works_out_no_score_and_shows_the_numbers_its_file_gives`,
`tests/test_data.py::TheDataFiles::test_a_field_the_pages_do_not_read_added_to_a_row_and_to_the_schema_is_ignored`,
`tests/test_data.py::TheDataFiles::test_a_board_day_file_from_before_the_fields_for_the_redesign_builds_and_changes_only_what_reads_them`,
and
`tests/test_data.py::TheSchemas::test_a_schema_never_makes_the_build_fetch_a_reference`.
