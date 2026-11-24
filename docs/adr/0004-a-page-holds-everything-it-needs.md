# A page holds everything it needs, and asks no other site for anything

Each page carries its styles, its one script, its icon, and its type inside
it, and requests nothing from another address. Its Content-Security-Policy
lets that one script run, by the hash of its exact text, and forbids every
request but the page itself and, on a board with rows, a fetch of that board
day's `history.json` from the site's own address. So no code of anyone else's
runs on a page, and the browser refuses a second script, an inline event
handler, or a request to another site.

## Status

Accepted. No single record holds it. Its reasons are written in three places:

- No third-party code runs on a public site (RisingRepos's decision record
  0010).
- A second request is something new that the page depends on, so the site
  eval allows one request, the page itself (`evals/site/limits.json`).
- Type inside the page, with a fallback face matched to its measures, is what
  keeps the layout from shifting (`evals/site/limits.json`, since
  RisingRepos#199 put the type inside the page).

## Consequences

- The type costs bytes on every page, and a page has little room left
  (README.md, "The pages", gives the sizes and the limits).
- An image, a web font, an embed, or an analytics script from another address
  cannot be added without reopening this. The host adds an analytics script
  to each live page, and the page's own policy refuses it.
- The script stores one thing in the browser, the reader's choice of theme,
  and sends nothing anywhere.

## Confirmed by

`tests/test_page_weight.py::PageWeight::test_no_page_requests_anything_from_another_site`,
`tests/test_page_weight.py::PageWeight::test_no_page_carries_a_script_but_the_sites_own_and_each_page_forbids_every_other`,
`tests/test_old_board.py::ThePolicy::test_the_policy_lets_the_script_run_by_the_hash_of_its_exact_text`,
and
`tests/test_old_board.py::ThePolicy::test_the_policy_is_otherwise_as_it_was_and_only_a_board_with_rows_may_fetch_from_its_own_address`.
