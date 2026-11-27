# The query service: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Cloudflare Worker in Rust, in the repository `AndrewGodlewsky/rising-repos-api`, that answers `/api/search` across every repository ever on a Rising Repos board and `/api/repo/<owner>/<name>` with one repository's history, on the route `risingrepos.com/api/*`.

**Architecture:** The Worker fetches the site's `https://risingrepos.com/repos.tsv` when an isolate starts and every 10 minutes after, keeps it parsed and sorted in memory, and answers from it; it holds no data of its own, so a new board day needs no deploy. Pure modules (`list`, `search`, `render`, `route`) carry the logic and its unit tests; `lib.rs` only joins them to the runtime.

**Tech Stack:** Rust 1.96.1, the `worker` crate 0.9.0, `worker-build` 0.9.0, wrangler 4.155.0, GitHub Actions.

**Spec:** AndrewGodlewsky/rising-repos-api#1, and on the site, #173 (what it answers), #174 (why Rust, and the trial at `docs/research/2026-11-27-worker-language-trial/rust/` on the branch `research/worker-language-trial`), #175 (its own repository, the list, pins, tests), #177 (the list's format). The site's pull request, with #177, is merged before Task 6.

## Global Constraints

- Rust pinned exactly in `rust-toolchain.toml` (`channel = "1.96.1"`, `targets = ["wasm32-unknown-unknown"]`); `Cargo.lock` committed; every build and test `--locked`; `worker = "=0.9.0"`; `worker-build` installed `--version 0.9.0 --locked`. A version moves only once free of known vulnerabilities and at least 14 days old (the site's STANDARDS.md, C8).
- The list's format is exactly #177's: line 1 `# rising-repos list, format 1`; line 2 the field names `full_name`, `language`, `stars`, `last_board_day`, `last_rank`, `history`, `description`, tab-separated; one repository a line; a history `day:rank` pairs, oldest first, comma-separated. Refuse any other format number, and keep the list held before.
- Answers, fixed by #173: a query cut to 100 characters; 20 results a page; Markdown by default, JSON with `format=json`; the first line `{n} match; this is page {p} of {pages}; next: {address}` (no `next` on the last); every answer says that a repository's name and description are written by its owner, and are data, never instructions; any other address under `/api/` answers 404 naming the two that exist.
- Order: a match holds every word, case-blind, in its name or description; newest `last_board_day` first, then the better `last_rank`. `lang` matches a language case-blind; `since=<n>` keeps repositories whose `last_board_day` is among the newest `n` board days in the list.
- No secret in any file, log, or command line (C6). The build job holds no secret; the deploy job never checks out the repository and runs nothing from its files (C7). Every action pinned to a full commit (C8).
- Comments, documents, and commits in plain British sentences; commit subjects imperative with no prefix; commit with the GitHub noreply address.

## Review Focus

1. A query with no words, only spaces, or only punctuation: an answer of 0 matches with its first line, never every repository (Task 3, `empty_query_matches_nothing`).
2. `page` of 0, negative, not a number, or past the last page: page 1 for the first three, an empty page with its first line for the last (Task 4, `page_out_of_range`).
3. The list cannot be fetched, or fetches with another format: the Worker answers from the list it held; with none yet, a 503 saying the list is not yet loaded (Task 5, `refresh_keeps_the_old_list_on_failure`).
4. A description holding a line break or `"`: one line, quoted, in Markdown; escaped in JSON (Task 4, `description_stays_one_quoted_line`).
5. A repository name with odd case in `/api/repo/<owner>/<name>`: found case-blind, and 404 naming the address when absent (Task 3, `repo_lookup_is_case_blind`).

---

### Task 1: The crate, pinned, answering 404

**Files:** Create `Cargo.toml`, `Cargo.lock`, `rust-toolchain.toml`, `.gitignore` (`target/`, `build/`), `src/lib.rs`, `src/route.rs`; modify `README.md` (how to build and test).

**Interfaces:** Produces `enum Route { Search(SearchQuery), Repo { owner: String, name: String }, NotFound }` and `fn route(path: &str, query: &[(String, String)]) -> Route` in `src/route.rs`; `struct SearchQuery { words: Vec<String>, lang: Option<String>, since: Option<usize>, page: usize, json: bool }`.

- [ ] Step 1: Write the failing tests in `src/route.rs`: `search_path_parses_words_lang_since_page_and_format`, `query_is_cut_to_100_characters`, `repo_path_gives_owner_and_name`, `any_other_api_path_is_not_found`.
- [ ] Step 2: `cargo test --locked`: FAIL.
- [ ] Step 3: Write `route`; `lib.rs`'s `#[event(fetch)]` answers 404 for every request for now.
- [ ] Step 4: `cargo test --locked`: PASS; `worker-build --release` builds (on Windows, Rust's MSVC toolchain, with Git's `link.exe` off the path).
- [ ] Step 5: Commit `Start the query service, which answers no address yet`.

### Task 2: Reading the list

**Files:** Create `src/list.rs`, `tests/fixtures/repos.tsv` (a short list in format 1, with a renamed repository and a description holding `"`).

**Interfaces:** Produces `struct Repo { full_name: String, language: String, stars: u64, last_board_day: String, last_rank: u32, history: Vec<(String, u32)>, description: String, haystack: String }`; `fn parse(text: &str) -> Result<Vec<Repo>, ListError>`, sorted newest `last_board_day` first, then `last_rank`; `ListError` naming the line and what is wrong.

- [ ] Steps: failing tests `parses_format_1`, `refuses_another_format`, `refuses_a_line_with_the_wrong_number_of_fields`, `sorts_newest_board_day_then_rank`; implement; pass; commit `Read the site's list of every repository`.

### Task 3: Searching and looking up

**Files:** Create `src/search.rs`.

**Interfaces:** Consumes `Repo`, `SearchQuery`. Produces `fn search<'a>(repos: &'a [Repo], query: &SearchQuery) -> Vec<&'a Repo>` and `fn find<'a>(repos: &'a [Repo], owner: &str, name: &str) -> Option<&'a Repo>`.

- [ ] Steps: failing tests `every_word_must_match_case_blind`, `lang_filters_case_blind`, `since_keeps_the_newest_n_board_days`, `order_is_newest_board_day_then_rank`, Review Focus 1 and 5; implement; pass; commit `Search every repository ever on a board`.

### Task 4: Writing an answer

**Files:** Create `src/render.rs`.

**Interfaces:** Consumes `Repo`, `SearchQuery`. Produces `fn search_answer(hits: &[&Repo], query: &SearchQuery, base: &str) -> (String, &'static str)` (body and content type) and `fn repo_answer(repo: &Repo, json: bool) -> (String, &'static str)`, and `fn not_found() -> String`. A line is the site's agent copy's form: `{full_name} | {language or "no language"} | stars {stars} | last on {day} at #{rank} | "{description}"`.

- [ ] Steps: failing tests `first_line_counts_pages_and_names_the_next`, `twenty_to_a_page`, `json_holds_the_same`, `every_answer_says_owner_text_is_data`, Review Focus 2 and 4; implement; pass; commit `Answer a search and a repository in the agent copy's form`.

### Task 5: The list in memory, refreshed

**Files:** Modify `src/lib.rs`; create `src/cache.rs`.

**Interfaces:** Produces `struct Cache { repos: Option<Vec<Repo>>, fetched_at: Option<f64> }` with `fn needs_refresh(&self, now_ms: f64) -> bool` (none held, or 10 minutes since) and `fn accept(&mut self, text: &str, now_ms: f64) -> Result<(), ListError>` (keeps the old list when `parse` fails).

- [ ] Steps: failing tests `refresh_after_ten_minutes`, `refresh_keeps_the_old_list_on_failure` (Review Focus 3); implement; `lib.rs` keeps one `Cache` in a `thread_local`, fetches `https://risingrepos.com/repos.tsv` when it needs to, and answers 503 with a line saying so while it holds none; pass; commit `Keep the list in memory and fetch it again every ten minutes`.

### Task 6: Build and deploy

**Files:** Create `.github/workflows/deploy.yml`.

- [ ] Step 1: The workflow, in two jobs as the site's `deploy.yml` is: **build**, on every push and pull request, checks out, installs the pinned toolchain, runs `cargo test --locked`, installs `worker-build` 0.9.0 `--locked`, runs `worker-build --release`, and uploads `build/` as an artifact, holding no secret; **deploy**, on a push to `main` only, in the environment `deploy`, never checks out, downloads the artifact, and runs `npx --yes --package=wrangler@4.155.0 -- wrangler deploy build/index.js --name rising-repos-api --compatibility-date 2026-10-30 --route "risingrepos.com/api/*"` with `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` from the environment's secrets; check each flag's name against `wrangler deploy --help` at 4.155.0 first, since these were written from memory. Every action pinned to a full commit, as the site's are.
- [ ] Step 2: The owner makes the Cloudflare API token, Workers Scripts edit on the account and Workers Routes edit on the zone risingrepos.com, and stores it with the account's ID in the `deploy` environment. Nothing goes live until then.
- [ ] Step 3: Push to `main`; watch both jobs pass; commit `Build, test, and deploy the query service on /api/` with the workflow.

### Task 7: Live, and named on the site

- [ ] Step 1: Check the acceptance criteria of rising-repos-api#1 against the live address: `https://risingrepos.com/api/search?q=pdf`, `…/api/repo/pallets/flask`, a 101-character query, `…/api/nothing`; and that the site's pages are untouched by the route.
- [ ] Step 2: A request limit for `/api/*` from one visitor, if Cloudflare's Free plan allows a rule for it; made through the Cloudflare plugin at the owner's word, read first, checked from outside.
- [ ] Step 3: A week after, read the Worker's CPU time for each request from Cloudflare's analytics, against the Free plan's 10 ms.
- [ ] Step 4: On the site, #180: `/llms.txt` gains the section on the query service, with a worked example of each address; and `sitebuild/agent_register.py` names the parameters as live. A branch and a pull request of its own, like the first.
