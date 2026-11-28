# Boards over 500 rows split their later rows into a second file

Every board day currently renders all of its rows into one self-contained HTML
document held under 550,000 bytes uncompressed (`SIZE_LIMIT`) and 155,000 bytes
gzipped at 713 rows (`WIRE_BUDGET`), following #184. The longest published board
so far (12 August 2026, 475 rows) already exceeds 500,000 bytes uncompressed.
Once real published boards exceed roughly 500 rows, or when the heaviest page
crosses 525,000 bytes, raising `SIZE_LIMIT` again would degrade first-paint
speed on slow phones and crowd the 100,000-byte live transfer limit. Instead,
the next scaling step is to keep the leading rows (ranks 1–200) in the initial
HTML document and write the remaining rows into a sibling static JSON or HTML
fragment (`more-rows.json` or `rows-2.html`, beside `history.json`), loaded on
demand or linked plainly for readers with scripts off (#246, RisingRepos#64).

## Status

Not yet in force. Recorded on 28 November 2026 in #246 as the planned next step
once real boards approach the 550,000-byte page cap raised in #184. Until that
threshold is reached, every board stays a single HTML document.

## Considered options

- **Raise `SIZE_LIMIT` and `WIRE_BUDGET` again:** delays the problem while
  pushing initial transfer size and phone LCP closer to the site eval limits.
- **Paginate boards into separate `/days/<day>/page-2/` URLs only:** breaks
  in-page filtering, sorting, and searching across the full board unless the
  client fetches the other pages anyway.
- **Keep ranks 1–200 inline and split the tail into a sibling static file:**
  keeps the initial HTML fast and small, preserves a complete no-JS path via a
  plain link to the continuation page, and lets the board's script fetch the
  tail on demand (or when a filter/search is used) under the existing
  `connect-src 'self'` policy.

## Consequences

- `sitework weigh` reports both per-page byte weight and total built file count
  against Cloudflare Pages's 20,000-file deployment cap so headroom is visible
  on every pull request.
- When split boards are introduced, the agent copy (`board.md` / `board.json`)
  and `history.json` continue to cover the whole board day unchanged.
- Splitting later rows requires updating the no-JS fallback, filter counts, and
  `owner_tests/` expectations only for boards above the split threshold, so
  shorter boards remain untouched.

## Confirmed by

- tests/test_page_weight.py::PageWeight::test_each_page_of_the_largest_board_published_is_within_the_size_limit
- tests/test_page_weight.py::PageWeight::test_a_long_boards_root_stays_within_its_transfer_budget_once_gzipped
- tests/test_sitework_weigh.py::TheWeights::test_the_report_counts_built_files_against_the_deployment_cap_and_total_bytes

## Reopen when

Reopen if a published board day exceeds 525,000 bytes uncompressed, if a real
board exceeds 500 rows, or if Cloudflare Pages's 20,000-file deployment cap
approaches 80% utilisation (16,000 files).
