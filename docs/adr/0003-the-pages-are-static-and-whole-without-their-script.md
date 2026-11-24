# The pages are static, built by a Python generator, and whole without their script

A Python program reads the data files and writes every page from Jinja2
templates. A page may carry a small script written for this site, with no
framework and no code of anyone else's, and it reads correctly with scripts
turned off: the script adds to a page that is already whole. This keeps one
language across the two repositories, and the fewest outside packages in the
build of a public site.

## Status

Accepted. RisingRepos's decision record 0010 holds it. The strongest
alternative was a JavaScript framework that renders static pages. It was
turned down because it brings a second language and a large tree of packages,
and because a board is one ranked list, which a short script can filter and
order in the page.

## Consequences

- The styles and the script are written by hand.
- The script adds the filter, an opened row's detail, the theme switch, the
  notice of an old board, and the readout of Baseline's chart. Without it a
  page lists every row, a row opens on its reason, and no control shows that
  would do nothing.
- The build words and rounds every figure a row shows. The script places
  them, and words no figure of the file's itself.

## Confirmed by

`tests/test_old_board.py::WithoutScripts::test_with_scripts_off_a_boards_page_holds_its_rows_and_its_publish_time_and_no_notice`,
`tests/test_reasons.py::TheReason::test_the_line_opens_without_a_script_and_from_the_keyboard`,
and
`tests/test_old_board.py::TheTheme::test_every_page_carries_the_switch_for_the_script_to_show_and_the_stylesheet_hides_it_without_the_script`,
for the theme switch. No test holds that the filter's controls are hidden
without the script: the reviewer does (STANDARDS.md, P3).

## Reopen when

A view needs more in the browser than filtering and ordering rows that are
already on the page, such as a search across board days. The generator is
cheap to replace: the data contract and the published files do not depend on
it.
