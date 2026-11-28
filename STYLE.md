# The style guide

What a new part of a page reaches for first, so that it reads as one with the
rest. Read it before a change that adds to a page or changes how one looks.

This is a guide, and not a rule. No change is stopped for departing from it.
A feature that needs a size, a colour, a shape, or a kind of control that is
not here takes it. It then says in its pull request what it added and why
what was here did not serve, and adds it to this guide in that pull request,
so that the next change finds it.

Two documents sit beside this one. The design note, in README.md under "The
design note", records what each part of a page is today, and why. Part 2 of
[STANDARDS.md](STANDARDS.md) holds what a page promises its reader. Those
promises hold for whatever a change adds, and this guide loosens none of
them. "What a part still has to do", below, names the ones a new part meets
first.

## What the look is for

A reader comes back each day to see what is rising. So a page is quick to
take in, quiet, and plain about what each thing on it does. The figures are
what the reader came for, and everything round them is a quiet logbook: paper
and ink, with colour kept for meaning. The dashed line of a repository's own
pace is the one mark that recurs, in a row, in an opened row, and on
Baseline.

A new part earns its place the same way. It says what it has to say in words
and figures first, and takes a colour, a box, or a drawing only where that
makes the words quicker to read.

## Start from what is there

Before writing a new rule in `sitebuild/templates/site.css`, find the part of
a page that already does the nearest job, and build from it.

| A new part needs | Start from | In the stylesheet |
| --- | --- | --- |
| A page's title and its opening line | The title block of History, Baseline, and How it works | `.head`, `.kind`, `h1`, `.lede` |
| A heading within a page | 20 px at 500 | `.figures h2`, `.month h2` |
| Something said about a whole board | A note above the rows: words on the raised surface, a rule in the ink at its left, its first sentence at 500 | `.notes` |
| A box that holds a chart or a row's detail | The card that holds Baseline's chart, or an opened row | `.card`, `.op` |
| A flow of steps, each with a way out | How it works' diagram: a spine in the third ink, a diamond for a check, a square for a step, an oval for the start and the end, a dashed edge for a way off, and a key along its foot (#214) | `.flow`, `.spine`, `.step`, `.box`, `.way`, `.off`, `.finish`, `.key` |
| A choice among a few | The filter's buttons, each with `aria-pressed` | `.segments button` |
| One action, such as undoing a view | The button under the line that says no row matches: the filter's size, with an edge | `.filtered-none button` |
| A choice among many | The filter's list of languages | `.toolbar select` |
| Words the reader types | The board's search, in the filter on a phone and in the day bar from 768 px up, and the field that finds a repository on Baseline's chart | `input[type="search"]` |
| A figure | Rising Mono with figures of one width | `.num` |
| A table of figures | Baseline's table | `.numbers` |
| A table of figures with more columns than a phone has room for | An opened row's table of the boards it was on: below 768 px each of its rows is stacked, and each figure is under its column's heading | `.more-days` |
| A quiet aside | A note under a chart or a table | `.note` |
| Words for a screen reader alone | | `.sr` |
| Anything that works only with the page's script | Hidden until the script has marked the root element | `.js-only` |

## The values in use

Read from the stylesheet on 22 November 2026. Each list is what the site uses
today, with the job each value does, so that a new part can pick by the job.

### Colour

A colour is a token on `:root`, picked by its job. The design note's table
gives each token's job and its contrast.

- Three hues carry meaning: the accent for what a repository gained and for
  the board's top, amber for what is new, and the red for a loss.
- The neutrals do the rest: `--text`, `--text-2`, and `--text-3` for three
  levels of text; `--bg`, `--surface`, and `--raised` for three levels of
  surface; `--line` and `--line-strong` for a rule or an edge.
- A link keeps the colour of the text round it, so that a colour always means
  one of the things above.
- A repository's name on a board, which leaves the site for GitHub, carries
  a mark after its text: the type's upwards arrow, turned 45 degrees to point
  up and right, in the link's own colour, drawn by the stylesheet with empty
  text for a screen reader, so that it is no part of the link's name. It is
  the site's one link that does so: Baseline's table links each name to
  GitHub without it, in the same tab (#104).
- Whatever a colour says is said in words or in a sign as well: a loss has
  its minus, and New is a word.

Each token is set three times: once for light, and twice for dark, by the
browser's setting and by the reader's choice. A new token goes in all three.
`tests/test_colour.py` measures each text colour against each background it
is set on, so a new colour, or a new pairing of two, gets a line there.

### Type

Words are in `--sans` and figures in `--mono`, with figures of one width in
any column. There are two weights. 500 marks a name, a heading, or the first
sentence of a note, and everything else is 400.

| Size | What takes it |
| --- | --- |
| 11 px | A chart's ticks and the labels along its edge, and the YES and NO on How it works' branches, in Rising Mono |
| 12 px | The smallest labels: the count in a filter's button, the New mark, the name of a fact in an opened row, a stage of How it works' diagram |
| 13 px | The filter's buttons, a table's column headings, a quiet note, the colophon, the owner over a name in Baseline's table on a phone |
| 14 px | The second level of text: a description, the links of the two bars, the lines of About this board |
| 15 px | The body, and a small heading at 500 |
| 16 px | A repository's name, 17 px from 768 px up, and a check or a step of How it works' diagram |
| 18 px | A page's opening line, and "On the board" on How it works |
| 20 px | A heading within a page, and a board's date in the day bar, 28 px from 768 px up |
| 36 px | A page's title, 56 px from 768 px up |

The site's own words keep to the characters the two faces hold, which
`CHARACTERS` in `sitebuild/fonts/characters.py` names. A new symbol in a heading
or a label is drawn in the fallback face until the faces are cut again, and
that file's docstring says how.

### Space

- Between and round the parts of a page: 4, 8, 12, 16, 20, 24, 32, 40, and
  48 px.
- Inside a row or a control, where 4 px is too coarse: 2, 6, and 10 px.
- A page's content is at most 1,200 px wide, with 16 px at each side, and
  32 px from 768 px up (`.wrap`).
- Running text keeps a measure: 640 px for an opening line, a notice, or a
  note; 680 px for How it works' note on the type, and 62 characters in a box
  of its diagram; 760 px for the notes above the rows and About this board.

### Shape

- Corners: 4 px for the smallest things, such as a cell of an opened row's
  run of days; 6 px for a mark, such as New or a top-three rank; 8 px for a
  button or a cell of History; 10 px for a field or a group of buttons; 12 px
  for a box in the flow of a page, such as the notice of an old board or an
  opened row; 16 px for the card; and an oval, 28 px, for the end of How it
  works' diagram, whose start is round.
- A rule or an edge is 1 px in `--line`, and in `--line-strong` where it has
  to be seen.
- A cell that holds nothing says so by its edge, not by a fill: on History, a
  board with no repository has a dashed edge in `--line-strong` and no fill,
  and a day with no board is hatched in `--line` (#91).
- Depth is a surface and a line. Only the readout over Baseline's chart has a
  shadow.
- A button, the theme switch, and a link in the day bar are 32 px tall. A
  field is 38 px. A link in a board's foot, which a finger presses, is at
  least 44 px tall.

### Widths

The stylesheet is written for a phone first, and widens at 768 px and at
1,100 px. The day bar alone also narrows: below 390 px its parts sit closer,
and below 360 px it leaves out Latest, for which there is then no room (#28).
Below 768 px the filter's star bands are a grid of two or three columns, as
wide as the toolbar, so that no button is left alone on a line (#32). From
768 px up the board's search leaves the filter for the day bar, so that on a
window 1,200 px wide or more the filter keeps one row whatever languages a
board lists (#213).

### Movement

Movement answers the reader's own pointer or key, and is short: 120 to 160 ms
on `--ease`, for a colour, a background, or the turn of a row's chevron. The
one longer change is the wash on the row that a press on Baseline's chart
leads to, which fades over 400 ms. One rule at the end of the stylesheet turns
all of it off for a reader who asked for less motion.

## What a part still has to do

These are promises, in part 2 of [STANDARDS.md](STANDARDS.md), and not this
guide's to loosen. A new part meets them however it looks.

- P3: the page is whole with scripts off, so a part that needs the script is
  marked `js-only`, and what it shows is on the page without it.
- P7: its text meets 4.5:1 against what it is set on, in both themes.
- P11: nothing on the page moves after it is first drawn.
- P13: a drawing comes with its figures in words.
- P14: the keyboard reaches each control, and each shows its ring.
- P15: it reads at 390 px and at 1440 px.
- P16: it honours forced colours and reduced motion.

## When what is here does not serve

1. Take the nearest value in use, if one does the job.
2. If none does, add what the feature needs: a colour as a token, a size or
   a space as a plain value.
3. Say in the pull request what was added, and why what was here did not
   serve.
4. Add it to this guide, and to the design note when it is a new part of a
   page.

The stylesheet is what a page gets. Where this guide and the stylesheet
differ, the stylesheet is right, and this guide is corrected.
