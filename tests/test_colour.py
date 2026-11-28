"""The page's colours, read from the stylesheet of each built page, in both themes: every text colour meets WCAG AA
(4.5:1) against each background it is set on, the lines and the focus ring that carry meaning meet 3:1, and a
repository that has been visited looks unlike one that has not.

README.md's design note gives each colour's job and each pair below. A tint is a colour with an alpha, painted over
what is under it, so a pair with a tint is measured against the colour the browser paints."""

import colorsys
import re
import unittest

from helpers import BuildTest

TEXT = ("--text", "--text-2", "--text-3")
"""The three neutral inks, each set on every surface a page has."""

SURFACES = ("--bg", "--surface", "--raised", "row hover")
"""The page, a card or control, a raised note or hovered control, and a board's row under the pointer: the soft
accent painted over the page."""

TEXT_ON_BACKGROUND = [
    *[(text, surface) for text in TEXT for surface in SURFACES],
    *[("--accent", surface) for surface in SURFACES],
    *[("--loss", surface) for surface in SURFACES],
    ("--accent", "--gain-soft over --surface"),
    ("--new", "--surface"),
    ("--new", "--new-soft over --bg"),
    ("--new", "--new-soft over --surface"),
    ("--new", "--new-soft over row hover"),
    ("--on-accent", "--accent"),
    *[("--text", f"--shade-{step}") for step in range(1, 5)],
]
"""Each text colour the page sets, and each background it sets that text on:

- the inks, and the accent (a gain, a rank of the top ten, a link under the pointer), on every surface;
- the red, for a loss: in the growth column on the page and on a row under the pointer, and in an opened row's
  facts and table of days on its card;
- the accent on its own tint over a control: a filter that is pressed;
- amber, for New: the New button's count, and the New mark and a pressed New button on amber's tint;
- the ink on the accent: a top-three rank, and a top-ten day of the 30-day strip;
- the ink on each step of History's ramp, and of the strip's days on a board, which take the third.

A new text colour is added here with each background it is set on."""

LINES_ON_BACKGROUND = [
    ("--accent", "--bg"),
    ("--accent", "--surface"),
    ("--text-3", "--surface"),
    ("--text-3", "--bg"),
]
"""What carries meaning without being text, each at WCAG's 3:1 for a graphic: the focus ring and what the board gained
in its drawings, in the accent, and the dashed line of a repository's own pace, in the third ink, on a card; and How it
works's spine, its arrows, and each branch, which carry the flow's direction, in the third ink on the page (#214)."""

INKS = {f"var({token})" for token in (*TEXT, "--accent", "--new", "--loss", "--on-accent")}

VISITED_APART = 1.5
"""The least contrast between a visited repository's name and one not yet visited. A visited repository dims from
the ink to the third ink. The design before RisingRepos#71 changed only the underline, at 1.09:1, and a visited row
could not be told from one that was not."""


def rgb(colour: str) -> tuple[tuple[float, float, float], float]:
    """A colour written #rrggbb, or rgba(r, g, b, a), as its channels and its alpha."""
    if colour.startswith("#"):
        return tuple(int(colour[i : i + 2], 16) for i in (1, 3, 5)), 1.0
    *channels, alpha = (float(part) for part in colour.removeprefix("rgba(").removesuffix(")").split(","))
    return tuple(channels), alpha


def painted(top: str, under: str) -> str:
    """The colour the browser paints for `top` over the opaque colour `under`."""
    (channels, alpha), (base, _) = rgb(top), rgb(under)
    return "#" + "".join(
        f"{round(alpha * one + (1 - alpha) * two):02x}" for one, two in zip(channels, base, strict=True)
    )


def luminance(colour: str) -> float:
    """WCAG 2's relative luminance of an opaque colour."""
    channels, alpha = rgb(colour)
    assert alpha == 1.0, colour
    red, green, blue = [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (v / 255 for v in channels)
    ]
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(one: str, other: str) -> float:
    lighter, darker = sorted((luminance(one), luminance(other)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


TOKEN = re.compile(r"(--[a-z0-9-]+):\s*(#[0-9a-f]{6}|rgba\([^)]*\));")


class TheColours(BuildTest):
    def setUp(self):
        super().setUp()
        self.styles = {}
        for path, page in self.build_pages().items():
            (style,) = page.all("style")
            self.styles[path] = style.text()

    def themes(self, style: str) -> dict[str, dict[str, str]]:
        """Each theme's tokens: the light ones in :root, and the dark ones, which the browser's dark setting and a
        reader's choice of dark each set, laid over them."""
        light = dict(TOKEN.findall(style.split("@media (prefers-color-scheme: dark)")[0]))
        by_setting = re.search(r':root:not\(\[data-theme="light"\]\) \{([^}]*)\}', style).group(1)
        by_choice = re.search(r':root\[data-theme="dark"\] \{([^}]*)\}', style).group(1)
        return {
            "light": light,
            "dark": {**light, **dict(TOKEN.findall(by_setting))},
            "chosen dark": {**light, **dict(TOKEN.findall(by_choice))},
        }

    def colour(self, tokens: dict[str, str], name: str) -> str:
        """A background as the browser paints it: a token, a tint over another background, or a hovered row."""
        if name == "row hover":
            return painted(tokens["--accent-soft"], tokens["--bg"])
        if " over " in name:
            top, under = name.split(" over ")
            return painted(tokens[top], self.colour(tokens, under))
        return tokens[name]

    def test_the_dark_theme_is_the_same_by_the_browsers_setting_and_by_the_readers_choice(self):
        for path, style in self.styles.items():
            with self.subTest(path):
                themes = self.themes(style)
                self.assertEqual(themes["dark"], themes["chosen dark"])
                self.assertNotEqual(themes["dark"], themes["light"])

    def test_each_text_colour_meets_wcag_aa_against_each_background_it_is_set_on_in_both_themes(self):
        for path, style in self.styles.items():
            for theme, tokens in self.themes(style).items():
                for text, background in TEXT_ON_BACKGROUND:
                    with self.subTest(path, theme=theme, text=text, background=background):
                        self.assertGreaterEqual(contrast(tokens[text], self.colour(tokens, background)), 4.5)

    def test_the_lines_that_carry_meaning_and_the_focus_ring_meet_3_to_1_in_both_themes(self):
        for path, style in self.styles.items():
            for theme, tokens in self.themes(style).items():
                for line, background in LINES_ON_BACKGROUND:
                    with self.subTest(path, theme=theme, line=line, background=background):
                        self.assertGreaterEqual(contrast(tokens[line], tokens[background]), 3.0)
            with self.subTest(path, ring=True):
                self.assertIn(
                    "a:focus-visible, button:focus-visible, select:focus-visible, summary:focus-visible, "
                    ".plot svg:focus-visible { outline: 2px solid var(--accent);",
                    style,
                )
                self.assertRegex(style, r'input\[type="search"\]:focus-visible \{ outline: 2px solid var\(--accent\);')

    def test_the_page_sets_text_only_in_those_colours(self):
        for path, style in self.styles.items():
            with self.subTest(path):
                used = set(re.findall(r"(?<![\w-])color:\s*([^;}]+?)\s*[;}]", style))
                self.assertLessEqual(used, INKS | {"inherit", "currentColor"})
                self.assertLessEqual({text for text, _ in TEXT_ON_BACKGROUND}, {ink[4:-1] for ink in INKS})

    def test_a_visited_repository_dims_from_the_ink_to_the_third_ink(self):
        """A reader who comes back each day sees which repositories they have already opened."""
        for path, style in self.styles.items():
            with self.subTest(path):
                self.assertIn(".re a:visited, .re a:visited .ow { color: var(--text-3); }", style)
                for theme, tokens in self.themes(style).items():
                    self.assertGreaterEqual(contrast(tokens["--text"], tokens["--text-3"]), VISITED_APART, theme)

    def test_the_three_hues_each_have_one_job_and_no_other_hue_is_set(self):
        """Evergreen for what a repository gained and the board's top, with History's ramp in its steps; amber for
        new; a deep red for a loss and nothing else; and the neutral ramp for everything else
        (AndrewGodlewsky/RisingRepos#199). A neutral is warm or cool by a few points, so a colour counts as a hue once
        its channels lie more than 24 apart."""
        greens = {"--accent", "--accent-soft", "--gain-soft", "--shade-3", "--shade-4"}
        faint = {
            "--shade-1",
            "--shade-2",
        }  # the ramp's two lightest steps, each a faint green or a neutral by this test
        ambers = {"--new", "--new-soft"}
        reds = {"--loss"}
        for path, style in self.styles.items():
            for theme, tokens in self.themes(style).items():
                with self.subTest(path, theme=theme):
                    hues = {name: self.hue(value) for name, value in tokens.items() if self.hue(value) is not None}
                    self.assertLessEqual(set(hues), greens | faint | ambers | reds)
                    self.assertLessEqual(greens | ambers | reds, set(hues))
                    for name in set(hues) - ambers - reds:
                        self.assertTrue(130 <= hues[name] <= 170, (name, hues[name]))
                    for name in ambers:
                        self.assertTrue(25 <= hues[name] <= 45, (name, hues[name]))
                    for name in reds:
                        self.assertTrue(hues[name] <= 15 or hues[name] >= 345, (name, hues[name]))

    @staticmethod
    def hue(colour: str) -> float | None:
        """The colour's hue in degrees, or None for a neutral, whose channels lie within 24 of each other."""
        (red, green, blue), _ = rgb(colour)
        if max(red, green, blue) - min(red, green, blue) <= 24:
            return None
        hue, _, _ = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)
        return hue * 360


class TheMeasure(unittest.TestCase):
    """The contrast measure above, against values WCAG's own definition gives."""

    def test_black_on_white_is_21_to_1_and_a_colour_on_itself_is_1_to_1(self):
        self.assertAlmostEqual(contrast("#000000", "#ffffff"), 21.0)
        self.assertAlmostEqual(contrast("#12704b", "#12704b"), 1.0)

    def test_the_order_of_the_two_colours_does_not_matter(self):
        self.assertAlmostEqual(contrast("#767676", "#ffffff"), contrast("#ffffff", "#767676"))
        self.assertAlmostEqual(round(contrast("#767676", "#ffffff"), 2), 4.54)

    def test_a_tint_is_measured_as_the_browser_paints_it_over_what_is_under_it(self):
        self.assertEqual(painted("rgba(0, 0, 0, 0.5)", "#ffffff"), "#808080")
        self.assertEqual(painted("rgba(18, 112, 75, 1)", "#ffffff"), "#12704b")
        self.assertEqual(painted("#12704b", "#ffffff"), "#12704b")


if __name__ == "__main__":
    unittest.main()
