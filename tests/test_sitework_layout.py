"""The layout report and the pictures.

What needs no browser is tested on small made-up files: the choice of pages from two folders of them, the values
a stylesheet newly uses, and the difference between two outlines. The browser's part is tested twice, on a made-up
page that is too wide for a phone. The command itself is tested with `sitework.shell.run` replaced, so that no
test makes a worktree of this repository or builds its pages.
"""

import contextlib
import io
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sitework import layout, shell


def write(folder: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text, encoding="utf-8", newline="\n")
    return folder


class FolderTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def sites(self, base: dict[str, str], head: dict[str, str]) -> tuple[Path, Path]:
        return write(self.folder / "base", base), write(self.folder / "head", head)


class TheChoice(FolderTest):
    def chosen(self, base: dict[str, str], head: dict[str, str]) -> list[tuple]:
        return [(page.kind, page.path, page.others, page.new) for page in layout.choose(*self.sites(base, head))]

    def test_a_page_whose_bytes_differ_is_chosen_and_one_that_is_the_same_is_not(self):
        base = {"index.html": "<p>one</p>", "baseline/index.html": "<p>same</p>"}
        head = {"index.html": "<p>two</p>", "baseline/index.html": "<p>same</p>"}
        self.assertEqual(self.chosen(base, head), [("The root", "index.html", 0, False)])

    def test_a_page_the_base_does_not_have_is_chosen_and_said_to_be_new(self):
        self.assertEqual(
            self.chosen({"index.html": "same"}, {"index.html": "same", "how-it-works/index.html": "new"}),
            [("How it works", "how-it-works/index.html", 0, True)],
        )

    def test_the_newest_board_day_stands_for_every_one_that_differs_and_the_rest_are_counted(self):
        days = ("2026-11-01", "2026-11-03", "2026-11-02", "2026-10-31")
        base = {f"days/{day}/index.html": "old" for day in days}
        head = {f"days/{day}/index.html": "old" if day == "2026-10-31" else "new" for day in days}
        self.assertEqual(self.chosen(base, head), [("A board day", "days/2026-11-03/index.html", 2, False)])

    def test_a_page_the_change_altered_in_its_own_markup_stands_for_its_kind_before_one_only_restyled(self):
        # On #28 the newest board day differed only in the stylesheet every page holds, and it was the page taken (#73).
        days = ("2026-11-21", "2026-11-22", "2026-11-23")
        base = {f"days/{day}/index.html": "<style>a{}</style><nav>Earlier</nav>" for day in days}
        head = {
            f"days/{day}/index.html": "<style>a{color:red}</style><nav>Earlier"
            + ("" if day == days[-1] else " <a>Latest</a>")
            + "</nav>"
            for day in days
        }
        (taken,) = layout.choose(*self.sites(base, head))
        self.assertEqual((taken.path, taken.others, taken.own), ("days/2026-11-22/index.html", 2, 2))

    def test_each_kind_of_page_is_told_by_its_address_and_they_come_in_the_order_a_reader_meets_them(self):
        in_order = [
            ("The root", "index.html"),
            ("A board day", "days/2026-11-03/index.html"),
            ("History", "days/index.html"),
            ("Baseline", "baseline/index.html"),
            ("Search", "search/index.html"),
            ("How it works", "how-it-works/index.html"),
            ("For agents", "for-agents/index.html"),
            ("The not-found page", "404.html"),
        ]
        chosen = self.chosen({}, {path: "new" for _, path in reversed(in_order)})
        self.assertEqual([(kind, path) for kind, path, _, _ in chosen], in_order)

    def test_a_page_of_a_kind_the_site_does_not_have_yet_is_chosen_once_for_its_folder(self):
        head = {"repos/a/index.html": "new", "repos/b/index.html": "new", "about.html": "new"}
        self.assertEqual(
            self.chosen({}, head),
            [("A page under /repos/", "repos/b/index.html", 1, True), ("The page /about.html", "about.html", 0, True)],
        )

    def test_a_file_that_is_not_a_page_is_never_chosen(self):
        base = {"index.html": "same", "days/2026-11-03/history.json": "{}", "static/fonts/OFL.txt": "a"}
        head = {"index.html": "same", "days/2026-11-03/history.json": "[]", "static/fonts/OFL.txt": "b"}
        self.assertEqual(self.chosen(base, head), [])

    def test_a_page_the_head_no_longer_has_is_named_as_gone(self):
        base, head = self.sites({"index.html": "same", "baseline/index.html": "old"}, {"index.html": "same"})
        self.assertEqual(layout.gone(base, head), ["baseline/index.html"])
        self.assertEqual(layout.choose(base, head), [])


class TheStylesheet(unittest.TestCase):
    BASE = """
        {# The page's inks. A note that names color: #123456 is no rule. #}
        :root { --text: #1b1a16; --line: rgba(27, 26, 22, 0.1); }
        body { margin: 0; color: var(--text); font: 400 15px/1.6 var(--sans); }
        /* padding: 99px; */
        a:hover { color: #1B1A16; }
        @media (min-width: 700px) { .row { padding: 4px 8px; border-radius: 6px; gap: 12px; } }
        .tag { font-size: 12px; font-weight: 500; margin-top: 6px; }
    """

    def new(self, added: str) -> list[str]:
        return layout.new_values(self.BASE, self.BASE + added)

    def test_a_stylesheet_that_uses_nothing_new_gives_nothing(self):
        self.assertEqual(layout.new_values(self.BASE, self.BASE), [])
        self.assertEqual(self.new(".more { color: #1b1a16; padding: 8px 4px; font-size: 15px; font-weight: 400; }"), [])

    def test_a_value_that_only_a_note_names_is_not_in_use(self):
        self.assertEqual(
            self.new(".x { color: #123456; padding: 99px; }"),
            ["- colour `#123456`, in `.x`", "- space `99px`, in `.x`"],
        )

    def test_read_stylesheet_reads_partials_under_css_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            code = write(
                Path(folder),
                {
                    layout.STYLESHEET: '{% include "css/part.css" %}\n',
                    "sitebuild/templates/css/part.css": ".x { color: #abcdef; }\n",
                },
            )
            self.assertIn("#abcdef", layout.read_stylesheet(code))

    def test_a_new_colour_size_weight_space_and_radius_are_each_listed_with_the_rule_that_uses_them(self):
        added = ".badge { color: #B45309; font-size: 13px; font-weight: 600; margin-left: 10px; border-radius: 3px; }"
        self.assertEqual(
            self.new(added),
            [
                "- colour `#b45309`, in `.badge`",
                "- font size `13px`, in `.badge`",
                "- font weight `600`, in `.badge`",
                "- space `10px`, in `.badge`",
                "- corner radius `3px`, in `.badge`",
            ],
        )

    def test_a_colour_is_found_wherever_it_is_written(self):
        added = ":root { --new: rgba(214, 140, 40, 0.18); } .a { border: 1px solid #abc; box-shadow: 0 1px #00000014; }"
        self.assertEqual(
            self.new(added),
            [
                "- colour `rgba(214, 140, 40, 0.18)`, in `:root`",
                "- colour `#abc`, in `.a`",
                "- colour `#00000014`, in `.a`",
            ],
        )

    def test_the_font_shorthand_gives_its_weight_and_its_size(self):
        self.assertEqual(
            self.new(".count { font: 700 17px/1.2 var(--mono); }"),
            ["- font size `17px`, in `.count`", "- font weight `700`, in `.count`"],
        )

    def test_each_side_of_a_space_is_a_value_of_its_own_and_one_in_use_is_not_new(self):
        self.assertEqual(
            self.new(".pad { padding: 4px 9px 12px; row-gap: 14px; margin: 0 auto; }"),
            ["- space `9px`, in `.pad`", "- space `14px`, in `.pad`", "- space `auto`, in `.pad`"],
        )

    def test_a_value_used_twice_is_listed_once_with_the_first_rule_and_how_many_more(self):
        self.assertEqual(
            self.new(".a { gap: 5px; } .b { padding: 5px; } .c { margin: 5px; }"),
            ["- space `5px`, in `.a` and 2 more"],
        )

    def test_a_selector_a_media_query_and_a_property_that_only_sounds_alike_are_not_values(self):
        added = "a:focus-visible { outline-offset: 2px; } @media (max-width: 480px) { .x { line-gap-override: 3%; } }"
        self.assertEqual(self.new(added), [])


class TheOutline(unittest.TestCase):
    BASE = "\n".join(
        ['- heading "Rising Repos" [level=1]', '- link "History"', '- heading "About this board" [level=2]']
        + [f'- paragraph: "Fact {number}"' for number in range(1, 9)]
    )

    def test_outlines_that_are_the_same_give_nothing(self):
        self.assertEqual(layout.outline_diff(self.BASE, self.BASE), [])

    def test_only_the_lines_that_changed_and_their_neighbours_are_given(self):
        head = self.BASE.replace('"Fact 6"', '"Fact six"')
        self.assertEqual(
            layout.outline_diff(self.BASE, head)[1:],
            [
                '   - paragraph: "Fact 4"',
                '   - paragraph: "Fact 5"',
                '-  - paragraph: "Fact 6"',
                '+  - paragraph: "Fact six"',
                '   - paragraph: "Fact 7"',
                '   - paragraph: "Fact 8"',
            ],
        )

    def test_each_part_says_which_heading_a_reader_has_passed_when_they_meet_it(self):
        head = self.BASE.replace('"Fact 6"', '"Fact six"')
        self.assertEqual(
            layout.outline_diff(self.BASE, head)[0], '@@ line 9, under heading "About this board" [level=2] @@'
        )
        first = layout.outline_diff(self.BASE, self.BASE.replace("Rising Repos", "Rising"))[0]
        self.assertEqual(first, "@@ line 1 @@")

    def test_a_long_difference_is_cut_and_says_how_many_lines_it_left_out(self):
        head = "\n".join(f'- paragraph: "New {number}"' for number in range(100))
        cut = layout.outline_diff(self.BASE, head, limit=10)
        self.assertEqual(len(cut), 11)
        whole = layout.outline_diff(self.BASE, head, limit=None)
        self.assertEqual(cut[-1], f"... and {len(whole) - 10} more lines of the difference.")


def seen(outline: str = "", wide: int = 390, past: int = 0, first: tuple = ()) -> layout.Seen:
    return layout.Seen(outline=outline, wide=wide, screen=390, past=past, first=list(first))


class TheWords(unittest.TestCase):
    """What the report says of one page on one screen, from what the browser gave."""

    TABLE = {"tag": "table.chart", "right": 600, "text": "1 owner/name"}

    def test_a_page_that_fits_says_so_in_one_line_and_says_when_the_base_did_not(self):
        fits = "Nothing reaches past the right edge, and the page does not scroll sideways."
        self.assertEqual(layout.edge(seen(), seen()), [fits])
        self.assertEqual(layout.edge(seen(), None), [fits])
        self.assertEqual(
            layout.edge(seen(), seen(wide=600, past=2)), [fits + " At the base, 2 elements reached past it."]
        )

    def test_what_is_past_the_edge_of_a_page_that_does_not_scroll_is_cut_off_or_scrolls_in_a_box_of_its_own(self):
        lines = layout.edge(seen(past=1, first=[self.TABLE]), seen(past=1))
        self.assertEqual(
            [line for line in lines if line],
            [
                "The page does not scroll sideways, so what is past the edge is cut off or scrolls inside its own box.",
                "1 element reaches past the right edge (1 at the base). The first:",
                '- `table.chart`, to 600 pixels: "1 owner/name"',
            ],
        )

    def test_an_element_with_no_words_is_named_by_its_tag_alone(self):
        drawing = {"tag": "svg.pace", "right": 412, "text": ""}
        self.assertEqual(layout.edge(seen(wide=412, past=3, first=[drawing]), None)[-1], "- `svg.pace`, to 412 pixels")

    def test_a_change_to_the_outline_is_printed_once_and_then_named_by_where_it_was_given(self):
        base = "\n".join(f"- paragraph: Row {number}" for number in range(8))
        head = base.replace("Row 5", "Row five")
        said = {}
        first = layout.outline(seen(head), seen(base), said, "/", 390)
        self.assertEqual(first[0], "The outline, from the base to the head:")
        self.assertIn("+  - paragraph: Row five", first)
        self.assertEqual(
            layout.outline(seen(head), seen(base), said, "/", 1440),
            ["The outline changed as it did at 390 pixels wide."],
        )
        lower = layout.outline(seen("- banner\n" + head), seen("- banner\n" + base), said, "/days/2026-11-03/", 390)
        self.assertEqual(lower, ["The outline changed as it did on `/` at 390 pixels wide."])
        other = layout.outline(seen(base.replace("Row 2", "Row two")), seen(base), said, "/days/2026-11-03/", 1440)
        self.assertEqual(other[0], "The outline, from the base to the head:")

    def test_an_outline_that_did_not_change_says_so(self):
        self.assertEqual(
            layout.outline(seen("- main"), seen("- main"), {}, "/", 390),
            ["The outline is the same at the base and at the head."],
        )

    def test_the_outline_of_a_new_page_is_given_itself_and_cut_when_it_is_long(self):
        new = "\n".join(f"- paragraph: Row {number}" for number in range(layout.OUTLINE_LINES + 5))
        said = {}
        lines = layout.outline(seen(new), None, said, "/about.html", 390)
        self.assertEqual(lines[0], "The outline, which the base does not have:")
        self.assertEqual(lines[-2], "... and 5 more lines of the outline.")
        self.assertEqual(
            layout.outline(seen(new), None, said, "/about.html", 1440),
            ["The outline is as it is at 390 pixels wide."],
        )


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>A made-up page</title><style>body {{ margin: 0; }} table {{ width: 600px; }}
.sr {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }}
.box {{ width: 200px; overflow-x: auto; }} .box p {{ width: 900px; }}</style></head>
<body><main><h1>A made-up board</h1><p>One line of words.</p>
<span class="sr"><time>Words kept for a screen reader, in a box a pixel wide, that run well past the edge</time></span>
{more}</main></body></html>
"""
WIDE = '<h2>The wide part</h2><table class="chart wide"><tr><td>A table that is 600 pixels wide</td></tr></table>'
BOXED = '<div class="box"><p>A line 900 pixels wide in a box of 200</p></div>'


class TheBrowser(FolderTest):
    """The part that needs Chrome, on a page that fits a phone at the base and is too wide for one at the head."""

    def test_what_reaches_past_a_phones_edge_is_named_and_the_change_to_the_outline_is_given(self):
        base, head = self.sites({"index.html": PAGE.format(more="")}, {"index.html": PAGE.format(more=WIDE)})
        report = layout.report(base, head, "", "")
        phone, desktop = report.split("### At 390 pixels wide")[1].split("### At 1440 pixels wide")
        self.assertIn("The page scrolls sideways: it is 600 pixels wide", phone)
        self.assertIn("at the base it did not", phone)
        self.assertIn("1 element reaches past the right edge (0 at the base). The first:", phone)
        self.assertIn('`table.chart.wide`, to 600 pixels: "A table that is 600 pixels wide"', phone)
        self.assertIn('+    - heading "The wide part" [level=2]', phone)
        self.assertIn('under heading "A made-up board" [level=1]', phone)
        self.assertIn("Nothing reaches past the right edge, and the page does not scroll sideways.", desktop)
        self.assertIn("The outline changed as it did at 390 pixels wide.", desktop)
        self.assertIn("## The root, `/`", report)

    def test_a_page_is_seen_at_the_moment_its_newest_board_was_published_whatever_the_day_is(self):
        aged = (
            '<p id="old-board" data-newest-published-at=2026-11-02T10:00:00Z>The board is <span id="age"></span></p>'
            '<script>document.getElementById("age").textContent ='
            ' Math.floor((Date.now() - Date.parse("2026-11-02T10:00:00Z")) / 3600000) + " hours old";</script>'
        )
        base, head = self.sites({}, {"index.html": PAGE.format(more=aged)})
        report = layout.report(base, head, "", "")
        self.assertIn("The board is 0 hours old", report)
        self.assertIn("The browser's clock is set to 2026-11-02T10:00:00Z", report)

    def test_words_kept_for_a_screen_reader_are_not_past_the_edge_and_a_line_wider_than_its_box_is(self):
        base, head = self.sites({"index.html": PAGE.format(more="")}, {"index.html": PAGE.format(more=BOXED)})
        phone = layout.report(base, head, "", "").split("### At 390 pixels wide")[1].split("### At 1440")[0]
        self.assertIn("The page does not scroll sideways, so what is past the edge is cut off or scrolls", phone)
        self.assertIn("1 element reaches past the right edge (0 at the base). The first:", phone)
        self.assertIn('- `p`, to 900 pixels: "A line 900 pixels wide in a box of 200"', phone)
        self.assertNotIn("`time`", phone)

    def test_a_picture_of_each_chosen_page_is_written_at_each_width_and_named_for_both(self):
        pages = {"index.html": PAGE.format(more=""), "days/2026-11-03/index.html": PAGE.format(more="")}
        base, head = self.sites({}, pages)
        written = layout.take_pictures(head, layout.choose(base, head), self.folder / "pictures")
        self.assertEqual(
            [path.name for path in written],
            ["root-390.png", "root-1440.png", "days-2026-11-03-390.png", "days-2026-11-03-1440.png"],
        )
        for path in written:
            header = path.read_bytes()[:24]
            self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n", path.name)
            wide = struct.unpack(">I", header[16:20])[0]
            self.assertEqual(wide, int(path.stem.rpartition("-")[2]), path.name)


class Stand:
    """A stand-in for `sitework.shell.run`: it keeps each command, makes the folder a worktree would, and writes
    the pages a build would."""

    def __init__(self, pages: dict[str, dict[str, str]], failing: str = ""):
        self.pages, self.failing, self.commands = pages, failing, []

    def __call__(self, *command: str, cwd: Path | None = None, **more) -> str:
        self.commands.append((command, cwd))
        if command[:2] == ("git", "merge-base"):
            return "b" * 40
        if command[:3] == ("git", "worktree", "add"):
            write(
                Path(command[4]),
                {
                    layout.STYLESHEET: f".at {{ color: #{command[5][:6]}; }}",
                    "sitebuild/__main__.py": "--no-share-images",
                },
            )
        if command[1:3] == ("-m", "sitebuild"):
            which = "head" if cwd == shell.ROOT else "base"
            if which == self.failing:
                raise shell.Failed("python -m sitebuild: exit 1\nsitebuild: the data is not as the contract says")
            write(Path(command[3]), self.pages[which])
        return ""


class TheCommand(FolderTest):
    def setUp(self):
        super().setUp()
        self.root = write(
            self.folder / "checkout",
            {layout.STYLESHEET: ".at { color: #bbbbbb; }", "sitebuild/__main__.py": "--no-share-images"},
        )
        self.enterContext(mock.patch.object(shell, "ROOT", self.root))

    def main(self, stand: Stand, command: str = "layout-report", *arguments: str) -> tuple[int, str, str]:
        printed, complained = io.StringIO(), io.StringIO()
        with mock.patch.object(shell, "run", stand):
            with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(complained):
                code = layout.main(command, list(arguments))
        return code, printed.getvalue(), complained.getvalue()

    def test_when_no_page_differs_it_says_so_in_one_line(self):
        same = {"index.html": "<p>same</p>"}
        code, printed, _ = self.main(Stand({"base": same, "head": same}))
        self.assertEqual((code, len(printed.strip().splitlines())), (0, 1))
        self.assertIn("No page differs", printed)

    def test_the_base_is_built_from_a_worktree_and_the_head_from_this_checkout_with_the_same_data(self):
        same = {"index.html": "<p>same</p>"}
        stand = Stand({"base": same, "head": same})
        self.main(stand)
        commands = [command for command, _ in stand.commands]
        self.assertEqual(commands[0], ("git", "merge-base", "origin/main", "HEAD"))
        self.assertEqual(commands[1][:4] + commands[1][5:], ("git", "worktree", "add", "--detach", "b" * 40))
        builds = [(command, cwd) for command, cwd in stand.commands if command[1:3] == ("-m", "sitebuild")]
        self.assertEqual([cwd for _, cwd in builds], [Path(commands[1][4]), self.root])
        for command, _ in builds:
            self.assertEqual(command[0], sys.executable)
            self.assertEqual(command[4:], ("--data", str(self.root / "site-data"), "--no-share-images"))
        self.assertIn(("git", "worktree", "remove", "--force", commands[1][4]), commands)

    def test_a_base_and_a_head_that_are_named_are_each_built_from_a_worktree_of_their_own(self):
        same = {"index.html": "<p>same</p>"}
        stand = Stand({"base": same, "head": same})
        code, _, _ = self.main(stand, "layout-report", "--base", "aaaaaa1", "--head", "cccccc2")
        added = [command[5] for command, _ in stand.commands if command[:3] == ("git", "worktree", "add")]
        self.assertEqual((code, added), (0, ["aaaaaa1", "cccccc2"]))
        self.assertNotIn(self.root, [cwd for command, cwd in stand.commands if command[1:3] == ("-m", "sitebuild")])

    def test_a_build_that_fails_exits_1_and_says_which_and_why(self):
        same = {"index.html": "<p>same</p>"}
        for failing in ("base", "head"):
            code, printed, complained = self.main(Stand({"base": same, "head": same}, failing=failing))
            self.assertEqual((code, printed), (1, ""))
            self.assertIn("the data is not as the contract says", complained)
            self.assertIn(f"the {failing}", complained)

    def test_pictures_of_a_change_that_altered_no_page_writes_none_and_says_so(self):
        same = {"index.html": "<p>same</p>"}
        out = self.folder / "pictures"
        code, printed, _ = self.main(Stand({"base": same, "head": same}), "pictures", "--out", str(out))
        self.assertEqual(code, 0)
        self.assertIn("No page differs", printed)
        self.assertFalse(out.exists() and any(out.iterdir()))


if __name__ == "__main__":
    unittest.main()
