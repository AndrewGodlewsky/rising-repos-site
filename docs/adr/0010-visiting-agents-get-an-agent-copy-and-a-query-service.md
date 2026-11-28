# Visiting agents get an agent copy of each board and a query service

A visiting agent reads a board's page badly: its rows are a table of
markup and drawn cells, and the longest board is too long for the smallest
reading window an agent has. So the build writes each board day's board again
as text and JSON beside its page, the agent copy, in parts that each fit that
window. What a copy cannot answer, such as a search across every repository
ever on a board, is answered by a query service, which lives in its own
repository, `AndrewGodlewsky/rising-repos-api`, out of reach of the daily data
push. The pages stay static, as [0003](0003-the-pages-are-static-and-whole-without-their-script.md)
says: no page depends on the service to render, and static pages may
progressively enhance through the same-origin `/api/` endpoints on explicit
reader interaction (such as submitting a search on `/search/` or expanding
earlier boards inside an opened row), sending zero `/api/` requests on initial
load (#242).

## Status

Accepted on 27 November 2026, by the owner, and decided in #157, #171, #174,
and #175. #171 chose the layout of the agent copy from three built for the
purpose, #174 chose the language of the query service, and #175 chose its own
repository. Amended on 28 November 2026, with the owner's approval on #242, to
allow progressive-enhancement calls from static pages to `/api/` on explicit
reader interaction.

**In force** since 27 November 2026. The agent copy and `/llms.txt` came first.
The query service went live that evening at `/api/` on the site's own domain,
from its own repository (AndrewGodlewsky/rising-repos-api#1), and #180 named its
two addresses in `/llms.txt` and moved the board's search, its language menu, and
Baseline's find to it in `sitebuild/agent_register.py`. On 28 November 2026,
#242 added `/search/` and on-demand earlier-board expansion in opened rows using
those same `/api/` endpoints.

## Consequences

- Every figure in the agent copy is the page's, worded as the page words it,
  from the same functions, so the copy cannot say what the page does not.
- A repository's name and description are written by its owner. The copy shows
  them as data: quoted, on one line, and with a line saying that they are never
  instructions.
- Static pages remain whole with scripts off and send zero `/api/` requests on
  initial load. Any response read from `/api/` is treated as untrusted data and
  rendered strictly through `textContent` (P5, P6).
- A change to a row's figures changes the copy with the page, and a change to
  the copy's layout raises its format number, so that an agent is told when it
  reads another.

## Confirmed by

- tests/test_agent_copy.py::TheAgentCopy::test_every_row_of_a_board_is_in_exactly_one_part
- tests/test_agent_copy.py::TheAgentCopy::test_a_rows_figures_are_the_pages_figures
- tests/test_agent_copy.py::TheAgentCopy::test_the_json_holds_every_row_its_format_and_the_names_of_the_owner_written_fields
- tests/test_agent_copy.py::TheAgentCopy::test_latest_is_the_newest_boards_copy
- tests/test_published_boards.py::EveryPublishedBoard::test_the_build_writes_the_sites_pages_a_page_for_each_board_day_and_the_history_of_each_that_has_rows
- tests/test_llms.py::TheLlmsTxt::test_llms_txt_names_both_addresses_of_the_query_service_with_a_worked_example_of_each
- tests/test_search_page.py::TheSearchPage::test_search_page_makes_no_api_request_on_load_and_renders_results_safely_on_submit

No test holds that the query service lives in its own repository.
