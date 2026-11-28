# Standards

What the site, a page, and a change are each held to. A standard is a rule
that holds for every change. A decision and its reasons are a record in
[docs/adr/](docs/adr/README.md), how each part works is in
[README.md](README.md), and the words are in [GLOSSARY.md](GLOSSARY.md).

**Reading one.** Each standard has a number, the rule, and its reason. Its
last line says what holds it: a test that fails when it is broken, a limit of
the site eval, or the reviewer. "A check could hold this" marks a standard
that a tool could hold and none does yet. `tests/test_context.py` fails when a
standard names no holder, or names a test or a limit that does not exist.

**Using them**

- **Planning a change.** Read Part 1, and hold the idea against every
  standard it touches. An idea that goes against a standard, or against a
  decision record, is the owner's to decide.
- **Building.** Hold to every standard the change touches. Tests hold most of
  Part 2, so run them.
- **Reviewing.** Judge the change by the standards that name the reviewer,
  and leave the others to the checks that hold them.

## Part 1. What belongs on the site

The owner adds to this part. So far it holds only what this repository had
already written down.

**B1. The site shows what the data file gives.** It computes no score and no
rank, takes the star bands from the file and keeps no band limits of its own,
and leaves out a fact the file does not give, where it could have guessed
one. The ranking is RisingRepos's, and a figure made up here could disagree
with the board
([0002](docs/adr/0002-risingrepos-owns-the-data-contract.md)).

Held by
`tests/test_reasons.py::TheReason::test_the_page_works_out_no_score_and_shows_the_numbers_its_file_gives`,
`tests/test_build.py::TheBands::test_bands_the_file_changes_are_the_bands_the_board_offers`,
and the reviewer.

**B2. A feature that needs a figure the files do not carry waits for
RisingRepos to add it.** A page reads only the fields the data contract
names, and a field reaches the files before a page reads it.

Held by
`tests/test_data.py::TheDataFiles::test_a_field_added_to_a_row_but_not_to_the_schema_fails_the_build`
and the reviewer.

**B3. What a reader needs in order not to misread a board is said in words,
in the open.** An earlier board, a provisional ranking, a hold, unranked
repositories, an old newest board, and an empty board each say what they are.
None is left to a colour or a mark alone, so that it reads the same to a
screen reader, and so that a board held back, or one that lacked a day, never
reads as a day on which nothing rose.

Held by
`tests/test_build.py::TheBoardDays::test_an_earlier_boards_page_says_so_and_links_to_the_newest`,
`tests/test_build.py::TheBuild::test_the_board_says_its_ranking_is_provisional_while_the_file_says_so_and_names_no_score`,
`tests/test_held.py::HeldBands::test_a_held_board_says_which_band_it_holds_back_and_which_star_counts_its_own_snapshot_missed`,
`tests/test_held.py::UnrankedRepositories::test_a_day_the_ranking_needed_that_was_partial_says_how_many_repositories_could_not_be_ranked`,
`tests/test_held.py::UnrankedRepositories::test_an_empty_board_two_days_after_a_missing_day_says_no_repository_could_be_ranked_not_that_none_rose`,
`tests/test_build.py::TheBuild::test_a_board_that_is_empty_says_so_and_states_its_board_day_the_same_way`,
`tests/test_old_board.py::TheNotice::test_from_26_hours_the_page_says_how_old_the_newest_board_is_in_hours_and_then_in_days`,
and the reviewer, for whatever a change newly shows.

**B4. A page is for a reader who comes back each day.** It is quick to take
in and easy to find one's way around, and how a thing on it looks shows what
it does, before anyone tries it.

Held by the reviewer.

**B5. The site has one look, and a new part starts from it.** The style
guide ([STYLE.md](STYLE.md)) says what a new part of a page reaches for, and
the design note records what each part is. Both guide, and neither binds: the
owner chose on 22 November 2026 that the look is guided and not ruled. A
feature that needs a size, a colour, or a kind of control they do not have
adds it, says so in its pull request, and adds it to the guide and the note
in that pull request. What a page promises, in part 2, holds for whatever is
added.

Held by the reviewer, who judges whether a new part reads as one with the
rest, and not whether its values are on a list.

**B6. An address keeps what it holds.** A board day keeps one address, and an
address of the earlier site still leads to its board day. Nothing is put on
the site in the expectation that it can be withdrawn quickly, because a page
taken out can go on being served for up to a week
([0006](docs/adr/0006-every-push-to-main-is-a-production-deploy.md)).

Held by
`tests/test_build.py::TheBoardDays::test_each_board_day_has_a_page_of_its_own_with_its_board_and_the_newest_has_the_roots_board`,
`tests/test_build.py::TheBoardDays::test_each_board_links_to_the_board_day_before_it_and_after_it_in_the_day_bar_and_the_foot`,
which writes a board day's address out, and the reviewer, for what is put on
the site.

**B7. Every page says what the site is, and that it is not affiliated with
GitHub.**

Held by
`tests/test_build.py::TheBuild::test_each_page_says_in_its_colophon_that_there_is_a_new_board_each_day`.

**B8. The site keeps nothing about a reader.** The script stores two things
in the browser, the reader's choice of theme and, on a board, the reader's
choice of the cards (#227), and sends nothing anywhere
([0004](docs/adr/0004-a-page-holds-everything-it-needs.md)).

Held by
`tests/test_old_board.py::TheNotice::test_the_script_reads_only_what_it_needs_and_writes_only_the_notices_text_and_the_roots_attributes`,
`tests/test_old_board.py::TheView::test_the_script_keeps_cards_under_a_key_of_its_own_and_nothing_but_that_and_the_theme`,
and the reviewer.

## Part 2. What a page promises

**P1. One script runs on a page, the site's own, allowed by the hash of its
exact text.** No page lets a script run through `'unsafe-inline'`, and no
element has an event-handler attribute
([0004](docs/adr/0004-a-page-holds-everything-it-needs.md)). No data enters
the script's text: a page's script is its parts exactly as they are shipped,
and no part holds a template's expression.

Held by
`tests/test_page_weight.py::PageWeight::test_no_page_carries_a_script_but_the_sites_own_and_each_page_forbids_every_other`,
which also fails on an event-handler attribute,
`tests/test_old_board.py::ThePolicy::test_each_page_carries_one_script_the_sites_own_parts_that_it_uses_and_no_other`,
`tests/test_old_board.py::ThePolicy::test_the_policy_lets_the_script_run_by_the_hash_of_its_exact_text`,
and
`tests/test_old_board.py::ThePolicy::test_a_script_changed_without_its_hash_in_the_policy_fails_the_check`.

**P2. A page requests nothing from another site.** Its styles, its script,
its icon, and its type are inside it.

Held by
`tests/test_page_weight.py::PageWeight::test_no_page_requests_anything_from_another_site`,
`tests/test_old_board.py::ThePolicy::test_the_policy_is_otherwise_as_it_was_and_only_a_board_with_rows_may_fetch_from_its_own_address`,
which refuses a file fetched from the site's own address too,
`tests/test_build.py::TheType::test_each_page_holds_the_four_faces_as_data_and_no_font_file_is_published`,
`tests/test_build.py::TheBuild::test_each_pages_theme_colour_is_its_background_in_each_scheme_and_its_icon_is_inside_it`,
and the site eval's limit on `requests`, on the live root.

**P3. A page is whole with scripts off.** The board lists every row, a row
opens on its reason, and no control shows that would do nothing
([0003](docs/adr/0003-the-pages-are-static-and-whole-without-their-script.md)).
A control that needs the script is one the stylesheet shows only once the
script has marked the page. A change to a board is looked at with scripts off
as well as on.

Held by
`tests/test_old_board.py::WithoutScripts::test_with_scripts_off_a_boards_page_holds_its_rows_and_its_publish_time_and_no_notice`,
`tests/test_old_board.py::WithoutScripts::test_with_scripts_off_the_list_holds_every_board_day_and_no_notice`,
`tests/test_reasons.py::TheReason::test_the_line_opens_without_a_script_and_from_the_keyboard`,
`tests/test_old_board.py::TheTheme::test_every_page_carries_the_switch_for_the_script_to_show_and_the_stylesheet_hides_it_without_the_script`,
for the theme switch, and the reviewer, for the filter's controls, for a new
control, and for the look with scripts off. A check could hold the controls.

**P4. A page stays within 550,000 bytes, and the root of a 713-row board
within 155,000 gzipped.** The owner raised both on 27 November 2026, from
500,000 and 150,000, to make room for the features then waiting, which use
much of it (#184): README.md, "The pages", gives the last measurements.
Markup added to a board's row is multiplied by every row, so it is measured
before and after. A gzipped size measured on Windows reads about 2% low. No
page carries a note written for whoever reads the stylesheet or the script,
and no file a page ships or fetches carries a value that nothing reads. A
field a page newly shows goes into the made-up rows the size tests measure,
at its longest, so that their worst case stays the worst. Every page built from
`site-data/` is also held to the 550,000-byte limit (#251).

Held by
`tests/test_page_weight.py::PageWeight::test_each_page_of_the_example_is_within_the_size_limit`,
`tests/test_page_weight.py::PageWeight::test_each_page_of_the_largest_board_published_is_within_the_size_limit`,
`tests/test_page_weight.py::PageWeight::test_a_long_boards_root_stays_within_its_transfer_budget_once_gzipped`,
`tests/test_page_weight.py::PageWeight::test_no_page_carries_the_notes_on_its_stylesheet_or_its_script`,
`tests/test_published_boards.py::EveryPublishedBoard::test_no_page_is_over_the_size_limit`,
the site eval's limit on `transfer_size`, on the live root, and the reviewer,
for the measuring before and after, for a value that nothing reads, and for the
made-up rows.

**P5. Owner-written text is shown as text.** It is escaped wherever a page
shows it, no template marks a value as safe, and the script writes what it
reads from a file as text. None of it is made a link: a repository's name
links to its own address on GitHub, which the build makes from the name. A
field added later that holds an address an owner wrote is made a link only
when that address is `http` or `https`.

Held by
`tests/test_owner_text.py::OwnerWrittenText::test_markup_in_a_description_appears_as_text`,
`tests/test_owner_text.py::OwnerWrittenText::test_no_owner_written_value_is_made_a_link_and_each_name_links_to_its_repository_on_github`,
`tests/test_owner_text.py::OwnerWrittenLanguage::test_markup_in_a_language_stays_one_attribute_value_and_one_options_text`,
`tests/test_owner_text.py::TheHistoryFile::test_the_history_file_holds_owner_text_as_strings_and_the_script_writes_text_alone`,
`tests/test_build.py::TheTemplates::test_no_template_turns_escaping_off_or_marks_a_value_as_safe`,
and the reviewer, for a field that holds an address, and for a link the
script would make from a value of the file.

**P6. The script writes text, and words no figure of the file's.** The build
words and rounds every figure a row shows, in the page and in `history.json`,
so that a row and its opened row never disagree, and the script places them.
What the script writes of its own is fixed captions and headings, a count of
what it lists, the age of the newest board, and how many rows a filter shows.
It writes with `textContent`, into elements of a fixed set of tags, and never
through `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, or
`eval`. The tests that run an opened row and the readout of Baseline's chart,
and the owner's tests that run the filter, hold where those parts put what
they write. None of them holds that the script wrote it as text.

Held by
`tests/test_old_board.py::TheNotice::test_the_script_reads_only_what_it_needs_and_writes_only_the_notices_text_and_the_roots_attributes`,
`tests/test_owner_text.py::TheHistoryFile::test_the_history_file_holds_owner_text_as_strings_and_the_script_writes_text_alone`,
`tests/test_owner_text.py::TheHistoryFile::test_no_script_template_uses_an_unsafe_dom_sink_or_eval`,
and the reviewer, for a figure the script would word and for the set of tags.

**P7. Every text colour meets 4.5:1 against each background it is set on, in
both themes.** A line or a ring that carries meaning meets 3:1. A new text
colour comes with a background that gives it 4.5:1, and with a line in
`tests/test_colour.py`.

Held by
`tests/test_colour.py::TheColours::test_each_text_colour_meets_wcag_aa_against_each_background_it_is_set_on_in_both_themes`,
`tests/test_colour.py::TheColours::test_the_lines_that_carry_meaning_and_the_focus_ring_meet_3_to_1_in_both_themes`,
`tests/test_colour.py::TheColours::test_the_page_sets_text_only_in_those_colours`,
and the reviewer, for a colour set on a background that the test's list does
not pair it with.

**P8. Each colour has one job, and no hue is set but the three.** The accent
is for what a repository gained and for the board's top, amber for what is
new, and the red for a loss and nothing else. The neutrals do the rest.

Held by
`tests/test_colour.py::TheColours::test_the_three_hues_each_have_one_job_and_no_other_hue_is_set`
and
`tests/test_colour.py::TheColours::test_the_page_sets_text_only_in_those_colours`,
for the hues the tokens hold and the colours text is set in, and the
reviewer, for where each colour is used, and for a colour written outside a
token.

**P9. Words are set in Rising Sans and figures in Rising Mono, inside the
page.** A number in a column takes tabular figures. No font file is fetched or
published, and there is no third family
([0005](docs/adr/0005-the-type-is-a-renamed-cut-of-ibm-plex.md)).

Held by
`tests/test_build.py::TheType::test_the_text_takes_rising_sans_and_every_figure_rising_mono_with_figures_of_one_width`,
for a board's three columns of figures,
`tests/test_build.py::TheType::test_each_page_holds_the_four_faces_as_data_and_no_font_file_is_published`,
and the reviewer, for a column or a family that a change adds.

**P10. The site's own text keeps to the characters its type holds.**
`CHARACTERS` in `sitebuild/fonts/characters.py` names them. A character outside
them is drawn in the fallback face, and adding one means cutting the faces
again, which is a change to the look (B5).

Held by
`tests/test_build.py::TheType::test_the_sites_own_text_keeps_to_the_characters_its_type_holds`.

**P11. Nothing on a page moves after it is first drawn.** The script is in
the `<head>`, a control that needs it is in place from the first frame, no
text is drawn until its face is in, the fallback face is matched to the
type's measures, and a notice that appears pushes down nothing already
painted.

Held by
`tests/test_old_board.py::WithoutScripts::test_the_script_is_in_the_head_and_the_notice_before_everything_it_could_move`,
`tests/test_old_board.py::TheNotice::test_the_notice_is_filled_the_moment_the_parser_reaches_it_when_the_script_runs_before_it`,
`tests/test_old_board.py::TheTheme::test_a_kept_choice_is_set_on_the_root_before_the_page_is_parsed_and_nothing_else_is`,
`tests/test_build.py::TheType::test_no_text_is_drawn_in_the_fallback_face_and_then_moved_when_its_own_face_is_in`,
the site eval's limit on `cumulative_layout_shift`, on the live root, and the
reviewer, for the fallback face and for anything a change adds that arrives
late.

**P12. A figure below 0 takes the true minus, and only a loss takes the
red.** A gain takes a plus only above 0. A number is rounded half up, as a
reader rounds, and parts its thousands with commas.

Held by
`tests/test_build.py::TheSigns::test_a_figure_takes_the_sign_of_what_it_rounds_to_and_a_gain_a_plus_only_above_0`,
`tests/test_build.py::TheSigns::test_no_page_and_no_opened_row_writes_a_figure_with_the_hyphen_or_a_plus_beside_a_minus`,
`tests/test_build.py::TheGrowthColumn::test_a_loss_is_in_the_red_and_a_gain_of_0_or_no_count_in_the_second_ink`,
and
`tests/test_reasons.py::TheNumbers::test_a_number_is_rounded_half_up_as_a_reader_rounds_it_and_parts_its_thousands`.

**P13. A drawing comes with its figures in words.** A screen reader hears
what a drawing shows, and a chart holds nothing that a screen reader cannot
reach in a table beside it.

Held by
`tests/test_history.py::TheHistoryFile::test_each_row_gives_its_facts_its_sum_and_the_words_and_numbers_of_its_drawings_from_the_file`,
`tests/test_build.py::TheBaseline::test_it_draws_and_lists_every_row_of_the_newest_board_in_its_order`,
`tests/test_history.py::TheHistoryFile::test_the_rows_own_pace_cell_and_its_opened_table_write_its_paces_alike`,
`tests/test_history.py::TheHistoryFile::test_a_row_gives_the_words_of_its_line_of_stars_over_a_month_and_none_without_two_counts`,
and the reviewer, for a new drawing, for the worked example of How it works,
and for what the script places in an opened row.

**P14. Every control, link, and `<summary>` shows a ring when the keyboard
reaches it, and a row opens from the keyboard.** A link the script takes out
of the keyboard's path is one the page gives again in a table beside it.

Held by
`tests/test_reasons.py::TheReason::test_the_line_opens_without_a_script_and_from_the_keyboard`,
for a row,
`tests/test_colour.py::TheColours::test_the_lines_that_carry_meaning_and_the_focus_ring_meet_3_to_1_in_both_themes`,
for the ring's contrast, and the reviewer, for the rest. A check could hold
this.

**P15. A page reads at a phone's width, 390 px, and at a desktop's, 1440 px,
in both themes, with five rows, with hundreds, and with none.**

Held by the reviewer. A check could hold this.

**P16. A page honours forced colours and reduced motion.** In forced colours
a drawing made of backgrounds takes system colours, and with reduced motion
nothing transitions.

Held by the reviewer.

**P17. Only the root carries the data contract's two tags.** It states its
board day and its publish time in them, once each, and no other page carries
either.
The check that follows a publish and the stale check read them, so they read
the root.

Held by
`tests/test_build.py::TheBuild::test_the_root_states_its_board_day_and_publish_time_in_the_contracts_two_meta_tags_once_each`
and
`tests/test_build.py::TheBuild::test_no_page_but_the_root_states_a_board_day_so_whatever_reads_the_tags_reads_the_root`.

**P18. A page reads a field that older files lack as optional.** A file
without the field builds, and its page shows what it showed before the field.
`site-data/` can hold files from before a field, until a publish writes every
board day again.

Held by
`tests/test_data.py::TheDataFiles::test_a_board_day_file_from_before_the_fields_for_the_redesign_builds_and_changes_only_what_reads_them`,
`tests/test_reasons.py::TheReason::test_a_board_whose_file_predates_the_rows_numbers_builds_and_gives_no_row_a_reason`,
`tests/test_build.py::TheBuild::test_a_board_whose_file_predates_the_formula_number_builds_and_names_no_formula`,
`tests/test_build.py::TheBuild::test_a_board_whose_file_predates_partial_days_builds_and_says_nothing_about_them`,
`tests/test_build.py::TheBuild::test_a_board_whose_file_predates_the_update_field_builds_and_says_nothing_about_an_update`,
`tests/test_held.py::RecentPartialDays::test_a_board_whose_file_predates_the_fields_names_no_state_and_no_hold`,
and the reviewer, for a field a change newly reads.

**P19. A data file that is wrong fails the build, with a message that names
it, and no page is written.** A page built from a bad file would be live
before anyone read it.

Held by
`tests/test_data.py::TheDataFiles::test_a_board_day_file_that_does_not_match_its_schema_fails_the_build_and_names_the_file`
and
`tests/test_data.py::TheDataFiles::test_an_index_whose_row_count_differs_from_its_board_days_file_fails_the_build_and_names_both`.

**P20. A figure reads the same in every place a page shows it.** A row, its
opened row, a drawing's words, and what a screen reader hears round one
figure one way and give it one sign. A review of the redesign found 13,444
rows that wrote one pace two ways (#26).

Held by
`tests/test_history.py::TheHistoryFile::test_the_rows_own_pace_cell_and_its_opened_table_write_its_paces_alike`,
`tests/test_build.py::TheGrowthColumn::test_an_opened_row_writes_and_marks_a_gain_as_the_board_does`,
and the reviewer, for a figure a change newly shows.

**P21. What the script writes into the address is a word the build wrote in
an attribute, and never a label read back out of its words.** A filter's
state is in the address, so a label read back would change every address a
reader has shared on the day the label was reworded. The script may read a
row's own text, its stars, its gain, and the words a search looks through,
where an attribute on every row would cost bytes that the root's budget
cannot spare (P4).

Held by the reviewer.

**P22. A value from the address or from the browser's storage only chooses
among values the page already holds.** The script compares it with them. It
never writes it into the page, and never looks anything up by it unguarded.

Held by the reviewer. A check could hold part of this.

**P23. What a reader sees, a visiting agent can get too.** Every column,
filter, and page of the site has its counterpart in the agent route, the
agent copy of each board, `/llms.txt`, and the query service, or a written
reason that it has none. They are listed in `sitebuild/agent_register.py`. A
reader who gains a way to see the board that an agent cannot follow has the
better site, and the agents that visit it would otherwise be the last to
learn of it (#160, #179).

Held by
`tests/test_agent_register.py::TheRegister::test_every_column_filter_and_page_the_build_writes_is_in_the_register`
and
`tests/test_agent_register.py::TheRegister::test_each_agent_copy_field_the_register_names_is_in_the_agent_copy`.

## Part 3. How the code and the words are written

**C1. A comment, a docstring, a document, and a commit's body are plain,
complete sentences that say why.** Each cites the issue that decided its
point, and matches the file it is in.

Held by the reviewer.

**C2. A commit's subject is one plain sentence in the imperative, with no
type prefix.** "Count only the requests the page sent in the site eval" is
one.

Held by the reviewer. A check could hold this.

**C3. Prose uses British spelling.**

Held by the reviewer.

**C4. The domain is named in the glossary's words, and a name means one thing
within a file.** A change that brings in a new term adds it to GLOSSARY.md.

Held by the reviewer.

**C5. Nothing private is written here.** A file, a commit, a pull request, a
review, or a comment names a RisingRepos issue by its number and says in its
own words what was decided there. It quotes neither the issue nor the owner,
and holds no path on anyone's machine and no personal e-mail address
([0007](docs/adr/0007-the-repository-is-public-and-holds-nothing-private.md)).

Held by
`tests/test_tokens.py::TheRepository::test_no_file_git_would_commit_holds_a_local_home_path_or_personal_email`,
for local home-directory paths and personal e-mail addresses (#251), and the
reviewer, for anything private in a commit, issue, pull request, or comment.

**C6. A credential's value is in no file, commit, issue, comment, log, or
command's arguments.** Only its name is. A value that reached any of those is
compromised, however briefly it was there: stop, and tell the owner which
credential and where, without repeating it.

Held by
`tests/test_tokens.py::TheRepository::test_no_file_git_would_commit_holds_a_string_shaped_like_a_credential`,
for GitHub tokens, Discord webhooks, PEM private keys, AWS keys, Slack tokens
and webhooks, and AI provider key prefixes in a file git would commit (#250),
and the reviewer, for any other credential and any other place.

**C7. The job that holds a credential runs nothing from this repository's
files.** The daily push can change any file here but a workflow, so a job
that runs the repository's code holds no secret, and no job gets a permission
it does not ask for.

Held by
`tests/test_workflow.py::TheWorkflow::test_the_deploy_job_does_not_check_out_the_repository`,
`tests/test_workflow.py::TheWorkflow::test_the_build_job_references_no_secret`,
`tests/test_workflow.py::TheWorkflow::test_the_cloudflare_credential_comes_from_the_deploy_environment_and_only_the_deploy_job_has_it`,
`tests/test_workflow.py::TheWorkflow::test_no_job_gets_a_permission_it_does_not_ask_for`,
`tests/test_stale_check.py::TheWorkflow::test_it_checks_out_nothing_uses_no_action_and_runs_only_the_script_in_this_file`,
`tests/test_site_eval_workflow.py::TheSiteEvalWorkflow::test_it_holds_no_secret_and_has_no_way_to_the_deploy_environment`,
and the reviewer, for a step that would run a file the build handed on.

**C8. Every download is pinned, and checked before it is used.** An action is
pinned to a full commit, and a package to a version. A pinned version moves
only as README.md, "Changing a pinned version", says: no known vulnerability,
and published at least 14 days earlier. A command written in a document that
installs or downloads something names exact versions, checked the same way,
and installs nothing into anyone's own tools.

Held by
`tests/test_workflow.py::TheWorkflow::test_every_action_is_pinned_to_a_full_commit_sha`,
`tests/test_workflow.py::TheWorkflow::test_the_deploy_job_runs_a_wrangler_whose_version_is_pinned_in_this_file`,
`tests/test_site_eval_workflow.py::TheSiteEvalWorkflow::test_every_action_is_pinned_to_a_full_commit_sha`,
`tests/test_site_eval_workflow.py::TheSiteEvalWorkflow::test_lighthouse_is_pinned_to_one_version_and_none_of_its_packages_runs_an_install_script`,
and the reviewer, for the check of a new version, for the versions of uv and
of Python that a workflow names, and for a command written in a document.

**C9. A dependency is added only once the owner has agreed to it.** The
build of a public site keeps the fewest outside packages
([0003](docs/adr/0003-the-pages-are-static-and-whole-without-their-script.md)).

Held by the reviewer.

**C10. A feature leaves the guards as they are.** The guards are what judges
a feature: a workflow, a pinned version, the policy that lets the script run,
a limit of the site eval, a limit or an assertion of a test, the owner's
tests, these standards, and the feature workflow's own scripts and documents.
`GUARDED` in `sitework/rules.py` lists their paths, and
`python -m sitework guard` names each one a change touches. A change that has
to move one says so, and waits for the owner, who allows it on the issue. A
test is never skipped or loosened so that a change passes, and one is removed
only when another test holds what it held.

Held by
`tests/test_sitework_guard.py::TheGuard::test_every_guarded_path_is_named_with_why_it_is_guarded`,
`tests/test_sitework_guard.py::TheGuard::test_a_change_to_the_policy_is_named`,
`tests/test_sitework_guard.py::TheGuard::test_one_of_the_owners_tests_that_changed_moved_or_lost_a_statement_is_named`,
`tests/test_sitework_guard.py::TheGuard::test_a_return_added_to_one_of_the_owners_tests_is_named`,
`tests/test_sitework_guard.py::TheGuard::test_a_file_or_a_folder_that_a_change_adds_at_the_top_of_the_repository_is_named`,
`tests/test_sitework_guard.py::TheGuard::test_a_path_the_owner_allowed_is_not_named_and_the_rest_still_are`,
for the paths the guard names, and the reviewer, for one of the agents' tests
that a change loosened or removed.

**C11. A test is named as the sentence it proves, and proves it on what the
build writes.** A test of one case builds from the tests' own copy of the
data contract's example, so that the day's data does not change what it
checks. Two build from `site-data/`: the one that shows the build reads it
when no folder is given, and `tests/test_published_boards.py`, whose checks
any row passes whatever its data (C19). The tests write only to temporary
folders, and reach no other machine.

Held by the reviewer.

**C12. A document changes in the same pull request as what it describes.**
README.md is the full account of each part, the design note of the look, and
RUNBOOK.md of the lines that going live changed.

Held by
`tests/test_runbook.py::TheRunbook::test_every_line_of_a_workflow_or_the_eval_that_names_an_address_is_in_its_table`,
for the runbook, and the reviewer, for the rest.

**C13. A decision recorded as the owner's is one the owner made.** The record
says when, and names the issue here where it was made, if there is one.
Anything else is labelled as an agent's reading.

Held by the reviewer.

**C14. A pull request holds one change, and reaches only what its issue
describes.** Every merge is a deploy, and the checks that follow a deploy can
blame only one change when only one went in
([0006](docs/adr/0006-every-push-to-main-is-a-production-deploy.md)).

Held by the reviewer.

**C15. A font file is committed only under a `rising-` name, made by
`sitebuild/fonts/subset.py`.** The licence reserves the name "Plex" to the
original ([0005](docs/adr/0005-the-type-is-a-renamed-cut-of-ibm-plex.md)).
The command in that script's docstring makes the files again, byte for byte.

Held by the reviewer. A check could hold this.

**C16. A document says only what the code and the built pages do.** A
sentence in README.md, a docstring, or a limit's stated reason that says more
than the code does is wrong. A measurement is taken again in every file that
quotes it: README.md and `evals/site/limits.json` each give the root's size.

Held by the reviewer. A check could hold the measurements.

**C17. One place owns each calculation, each phrase, and each choice.** A
second copy of a helper that already has a home is not written. A choice made
in the build is read by the templates and the script, and is not made again
in each.

Held by the reviewer.

**C18. A new test is shown to fail.** It goes red when the change it covers
is taken out, its check is as wide as what its name claims, and its data
holds a case where right code and wrong code differ. A review of the redesign
took one line of a fix out and saw every test still pass (#26).
`python -m sitework new-tests` runs each test a change adds on the code as it
was before the change, and passes only when each one fails there.

Held by
`tests/test_sitework_new_tests.py::TheNewTests::test_a_new_test_that_passes_on_the_code_before_proves_nothing_whatever_the_others_do`,
for the first of these, and the reviewer, for the other two.

**C19. A change to a row's words or figures is tried on every published
board, and not only on the example.** The example has five rows. The reviews
of the redesign found what the tests had missed by running every row in
`site-data/` (#26). `tests/test_published_boards.py` builds from `site-data/`
and holds every page and every row to what the other tests hold of the
example. A check of a row's new word or figure is added there, written so
that any row passes it whatever its data.

Held by
`tests/test_published_boards.py::EveryPublishedBoard::test_each_board_lists_its_files_rows_in_order_with_the_rank_name_description_language_and_stars_of_each`,
`tests/test_published_boards.py::EveryPublishedBoard::test_each_row_writes_its_usual_pace_and_its_recent_pace_one_way_in_its_cell_and_in_its_opened_view`,
`tests/test_published_boards.py::EveryPublishedBoard::test_no_page_and_no_opened_row_shows_a_templates_marks_or_a_value_that_was_never_filled_in`,
for what a row shows today, and the reviewer, for whether a change to a row
added its check there.

**C20. A change that is meant to leave the pages alone is shown to.** The
build before it and the build after it are the same, byte for byte. Two
builds of one commit always are.

Held by the reviewer. A check could hold this.

**C21. A check is cited only for what it measured.** On a pull request the
site eval measures the live site, and not the pull request's pages. A result
that was not run, or not read, is reported as that.

Held by the reviewer.

**C22. No guard, fallback, or assertion is written for a case that cannot
happen.**

Held by the reviewer.

**C23. A change leaves no whitespace error.** `git diff --check` prints
nothing. `python -m sitework check` runs it on a branch's change, before the
tests.

Held by
`tests/test_sitework_check.py::TheCheck::test_it_runs_every_check_of_a_change_the_cheapest_first`.

## Changing them

- **Add a standard** when a review finds what these did not say, or when a
  judgement made while building should hold for later work. Add it in the
  change that showed the need.
- **Give it a check** as soon as a tool can hold it, and name the check on
  its last line. A standard that a check can hold is not left to the
  reviewer.
- **Remove one** that no longer changes what anyone does.
- **A number is never used twice.** A new standard takes the next number of
  its part, and a removed one leaves a gap.
