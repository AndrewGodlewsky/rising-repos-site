# The owner's tests

What a reader can do on risingrepos.com, and what the site promises that
reader: one plain sentence each, and one test to a sentence. The sentences are
the owner's, and so the folder is theirs to read and approve. Every other test
is in `tests/`, and is an agent's to write, change, and remove as a feature
needs. `docs/workflow-plan.md`, under D19, is where the two kinds were decided.

A test here drives the site from outside, as a reader does. It builds the
pages with the build's public command, hands them out from this machine, and
reads them in Chrome. It finds a thing by what it is and what it is called
(the button named New, the board's table, a link), by the words on the screen,
or by the address in the bar, and names no class and no id. A feature can
change a page's markup round a test and leave it standing. A test that fails
has found something a reader would notice.

## The rule

- A feature's change may add to this folder, and changes nothing that is
  here. `python -m sitework guard` holds this.
- When a feature adds something a reader can do, the reviewer adds a sentence
  and its test for it, and changes none that is here. The agent that builds a
  feature does not write here.
- The owner reads what was added.
- A feature that fails one of these tests mends its code. A feature that is
  meant to change what a sentence says waits for the owner.

**What that means for a file of Python.** A line that is added can take a
test away: a `return` at the head of a test, a skip, a second definition of
a helper under the first. So the guard reads such a file for what it means,
and not for its lines.

- Each statement at the top of a file, and each member of a class there,
  stays as it was and where it was, with its decorators and its body. A
  comment, a line's layout, and the docstring that begins a file or a class
  may change.
- What a change adds has a name the file, or the class, did not have, since
  a second definition would take the first one's place. At the top of a file
  it adds only an import of names, a function, a class, an assignment to a
  name, a docstring, or the two lines that run the file as a program. A name
  may be added to an import the file has.
- The made-up boards stay as they are too, since every other sentence is
  tested on them. A new scenario that needs a board of another kind makes
  one under a new name. One that needs the boards here changed waits for
  the owner, who allows it on the issue.

In a file that is not Python, as this one is not, a change may add lines and
may take none away. So this file gives no count of the tests: a file that is
only added to cannot keep one true (#54). A run's last lines say how many ran.

No rule of this kind is whole: a statement that is allowed can still run
code when its file is read. So the reviewer reads what a change added here,
and the owner reads it after.

## The sentences

Each sentence is followed by the name of the test that holds it. The test's
docstring starts with the sentence's number and says how it is checked. A
sentence marked *made-up boards* needs something only those boards can give
it, and is left out of a run against a live site.

### A board (`test_a_board.py`)

1. The root shows the newest board, with every repository its file lists, in
   the file's order. *Made-up boards.*
   `test_the_root_shows_the_newest_board_with_every_repository_its_file_lists_in_the_files_order`
2. Every board day that was published has a page at its own address.
   *Made-up boards.*
   `test_every_board_day_that_was_published_has_a_page_at_its_own_address`
3. A row gives its rank, its name as a link to the repository on GitHub, the
   stars it gained on the day, and its total stars.
   `test_a_row_gives_its_rank_its_name_linked_to_github_the_stars_it_gained_on_the_day_and_its_total_stars`
4. A row opens on the reason it is on the board, with scripts on or off.
   `test_a_row_opens_on_the_reason_it_is_on_the_board_with_scripts_on_or_off`
5. A board says above its rows when it is an earlier board, when its ranking
   is provisional, when a star band is held back, and when repositories could
   not be ranked. *Made-up boards.*
   `test_a_board_says_above_its_rows_when_it_is_earlier_provisional_holds_a_band_back_or_could_not_rank_some`
6. A board with no rows says why. *Made-up boards.*
   `test_a_board_with_no_rows_says_why`

### Getting about (`test_getting_about.py`)

7. Every page has the site's bar, and each link in it leads to a page that is
   there.
   `test_every_page_has_the_sites_bar_and_each_link_in_it_leads_to_a_page_that_is_there`
8. The day bar leads to the board day before and to the one after.
   `test_the_day_bar_leads_to_the_board_day_before_and_to_the_one_after`
9. History lists every board day, and each leads to its board.
   *Made-up boards.*
   `test_history_lists_every_board_day_and_each_leads_to_its_board`
10. No link within the site leads to a page the build did not write.
    *Made-up boards.*
    `test_no_link_within_the_site_leads_to_a_page_the_build_did_not_write`

### The filter and an opened row, in a browser (`test_the_filter_and_an_opened_row.py`)

11. New shows only the repositories that are new, and says how many.
    `test_new_shows_only_the_repositories_that_are_new_and_says_how_many`
12. A star band's button shows only that band's repositories.
    `test_a_star_bands_button_shows_only_that_bands_repositories`
13. Choosing a language shows only that language's repositories.
    `test_choosing_a_language_shows_only_that_languages_repositories`
14. Each order puts the rows in that order.
    `test_each_order_puts_the_rows_in_that_order`
15. A search shows only the rows whose name or description holds it, and says
    so when none does.
    `test_a_search_shows_only_the_rows_whose_name_or_description_holds_it_and_says_so_when_none_does`
16. A filtered board's address, opened again, shows the same rows.
    `test_a_filtered_boards_address_opened_again_shows_the_same_rows`

    It does not claim that two or more filters chosen together give the
    same rows again, or anything of a board on which no row matches. Each of
    its four addresses holds one filter, or a language with an order. #41 is
    to test the filters together, and #33 is the idea for a board that
    matches nothing.
17. An opened row shows its sum, its facts, and the boards it was on, once the
    history arrives.
    `test_an_opened_row_shows_its_sum_its_facts_and_the_boards_it_was_on_once_the_history_arrives`

    It does not claim anything of a history that arrives late or not at
    all, where the row says "The rest of this row could not be loaded.", or
    that the history is asked for once however many rows are opened. #42 is
    to test those.

### The other pages (`test_the_other_pages.py`)

18. Baseline draws and lists every repository of the newest board.
    `test_baseline_draws_and_lists_every_repository_of_the_newest_board`
19. Moving over Baseline's chart names the nearest repository.
    `test_moving_over_baselines_chart_names_the_nearest_repository`

    It does not claim a tap on a phone or finding a repository by its name,
    which sentences 36 and 37 hold since #29, or that the chart's labels do
    not print over each other, which is the idea #34. It moves a mouse's
    pointer over the chart on a desktop.
20. How it works names the formula that ranked the newest board.
    `test_how_it_works_names_the_formula_that_ranked_the_newest_board`

### For every reader (`test_for_every_reader.py`)

21. With scripts off, every row is listed, and no control shows that would do
    nothing.
    `test_with_scripts_off_every_row_is_listed_and_no_control_shows_that_would_do_nothing`
22. The theme switch turns the page light or dark, and the choice is kept.
    `test_the_theme_switch_turns_the_page_light_or_dark_and_the_choice_is_kept`
23. On a phone, nothing reaches past the edge of the screen, with a row
    opened.
    `test_on_a_phone_nothing_reaches_past_the_edge_of_the_screen_with_a_row_opened`

    It does not claim anything of Baseline's page, or of how the star-band
    filter wraps on a phone. It opens the first row of the newest board on a
    screen 390 pixels wide, and holds that nothing is past either edge. #32
    is the idea for the filter's wrap, and #34 for Baseline's labels.
24. The keyboard reaches every control, and each shows its ring.
    `test_the_keyboard_reaches_every_control_and_each_shows_its_ring`
25. Every text colour meets 4.5:1 against what it is set on, in both themes.
    `test_every_text_colour_meets_4_5_to_1_against_what_it_is_set_on_in_both_themes`

### What the site promises (`test_what_the_site_promises.py`)

26. A page asks nothing of another site, and its browser refuses nothing.
    `test_a_page_asks_nothing_of_another_site_and_its_browser_refuses_nothing`
    On the live site the host adds two scripts of its own to each page, and
    the page's policy refuses both. That refusal is the promise kept, so the
    test passes over those two there, and nothing else.
27. A page runs one script, and no other.
    `test_a_page_runs_one_script_and_no_other`
28. What a repository's owner wrote is shown as text, and is never a link.
    *Made-up boards.*
    `test_what_a_repositorys_owner_wrote_is_shown_as_text_and_is_never_a_link`
29. No page is over 500,000 bytes, and the root of a long board is under
    150,000 on the wire. *Made-up boards.*
    `test_no_page_is_over_500000_bytes_and_the_root_of_a_long_board_is_under_150000_on_the_wire`
30. A newest board that is 26 hours old says so, and after a week the boards
    are not shown.
    `test_a_newest_board_that_is_26_hours_old_says_so_and_after_a_week_the_boards_are_not_shown`
31. The root states its board day and its publish time in the data contract's
    two tags.
    `test_the_root_states_its_board_day_and_its_publish_time_in_the_data_contracts_two_tags`
32. A data file that breaks the data contract fails the build.
    *Made-up boards.*
    `test_a_data_file_that_breaks_the_data_contract_fails_the_build`

Sentences 29 and 32 are about the build and its files, and are tested through
the build command and what it writes, and not through the browser.

### On the live site, after each deploy

33. The site eval's six numbers are within their limits.

Sentence 33 has no test here. The site eval is that test: it measures the
live site after each deploy, and `evals/site/` holds it and its limits.

### An opened row, on a phone (`test_an_opened_row_on_a_phone.py`)

34. On a phone, each board an opened row was on gives every figure under its
    heading, and none is cut.
    `test_on_a_phone_each_board_an_opened_row_was_on_gives_every_figure_under_its_heading_and_none_is_cut`

Sentence 34 came with #27, and reads a live site as it reads the made-up one.

### The way to the newest board, on a phone (`test_the_way_to_the_newest_on_a_phone.py`)

35. On a phone, an earlier board's day bar leads to the newest board, with
    scripts on or off.
    `test_on_a_phone_an_earlier_boards_day_bar_leads_to_the_newest_board_with_scripts_on_or_off`

Sentence 35 came with #28, and reads a live site as it reads the made-up one.

### Choosing a dot of Baseline's chart (`test_choosing_a_dot_of_baseline.py`)

36. On a phone, a tap on a dot of Baseline's chart names its repository, with
    its rank and figures as the table gives them, until a tap away from every
    dot.
    `test_on_a_phone_a_tap_on_a_dot_of_baselines_chart_names_its_repository_as_the_table_does_until_a_tap_away`
37. Typing part of a repository's name in Baseline's "Find a repository"
    names the first by rank whose name holds it, and says so when none does.
    `test_typing_part_of_a_repositorys_name_in_baselines_find_field_names_the_first_by_rank_that_holds_it`

Sentences 36 and 37 came with #29, and read a live site as they read the
made-up one.

### A row's name on GitHub (`test_a_rows_name_on_github.py`)

38. A row's name opens its repository on GitHub in a new tab, and the board
    stays in its own, with scripts on or off.
    `test_a_rows_name_opens_its_repository_on_github_in_a_new_tab_and_the_board_stays_with_scripts_on_or_off`

    It does not claim anything of the mark drawn after the name, which the
    agents' tests hold, or of Baseline's table, whose names still open GitHub
    in the same tab. GitHub answers with a stand-in, so the test asks nothing
    of it.

Sentence 38 came with #30, and reads a live site as it reads the made-up one.

### A history that cannot be had (`test_a_history_that_cannot_be_had.py`)

39. An opened row whose history cannot be had still shows its reason, and
    says the rest could not be loaded.
    `test_an_opened_row_whose_history_cannot_be_had_still_shows_its_reason_and_says_the_rest_could_not_be_loaded`

Sentence 39 came with #42. It keeps the history from the reader's own browser,
so it reads a live site as it reads the made-up one, and asks nothing of the
site but what a reader with a fault on the way would ask.

### A view that matches nothing (`test_a_view_that_matches_nothing.py`)

40. A view that leaves no row says what is chosen, and its button "Clear
    search and filters" shows every row of the board in the order chosen,
    until Back returns that view.
    `test_a_view_that_leaves_no_row_says_what_is_chosen_and_clear_search_and_filters_shows_all_rows_until_back`

Sentence 40 came with #33, and reads a live site as it reads the made-up one.

## How to run them

From the repository, with the pinned dependencies in place (`uv sync
--locked`) and Google Chrome on the machine:

```sh
uv run --locked python -m unittest discover -s owner_tests -t .
```

The run builds one site from the made-up boards, into a temporary folder,
serves it from 127.0.0.1 on a free port, and opens one browser for every
test. It takes about 40 seconds.

One file, or one test, runs by its name:

```sh
uv run --locked python -m unittest owner_tests.test_a_board
uv run --locked python -m unittest owner_tests.test_a_board.ABoard.test_a_board_with_no_rows_says_why
```

### Against a live site

With the environment variable `SITE` set to a site's address, the run builds
nothing and reads that site:

```sh
SITE=https://risingrepos.com uv run --locked python -m unittest discover -s owner_tests -t .
```

In PowerShell:

```powershell
$env:SITE = "https://risingrepos.com"
uv run --locked python -m unittest discover -s owner_tests -t .
Remove-Item Env:SITE
```

The loader leaves out the nine scenarios marked *made-up boards* above, and
the run's first line says how many it left out and how many run. The others
name no repository and no board day: each takes the first row, or a language
the filter offers, so it reads whatever board the site shows that day. Every
one of them only reads. A scenario that the day's board gives nothing to start
from, such as a board with no new row, is skipped, and says what was missing.
The run takes about 75 seconds.

## What is in the folder

| File | What it holds |
| --- | --- |
| `made_up.py` | The made-up boards, and the files they are written to. Nothing here is copied from `site-data/` |
| `the_site.py` | The one site and the one browser of a run: built and served here, or the address `SITE` names |
| `scenario.py` | What every test starts from: a reader with a browser, and the handles a reader has on a page |
| `test_*.py` | The tests, one file for each group of sentences above |
| `__init__.py` | The loader, which leaves out what a live site cannot be asked |

The folder imports nothing from `tests/` or `sitework/`, and reaches the
generator only through `python -m sitebuild <out> --data <folder>`, so that it
holds whatever is behind that command.

## Adding a sentence

- Write the sentence in the list above, under the next number, and name its
  test after it. The test's docstring starts with that number.
- Find things as `scenario.py` does: by role and name, by the words on the
  screen, by the address. Name a tag only where the browser gives a thing no
  role, and say so where you do.
- Wait with `expect(...)`, and never for a fixed time.
- Name no repository and no board day. If the scenario cannot start from
  whatever board a live site shows, mark it `@needs_made_up_boards`, and add
  what it needs to `made_up.py` under a new name, as the rule above asks.
- Against a live site a scenario only reads.
