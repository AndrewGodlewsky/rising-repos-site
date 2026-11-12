"""The page's colours, read from the stylesheet of each built page: every text colour meets WCAG AA (4.5:1)
against the background it is set on, and a link that has been visited looks unlike one that has not."""

import re
import unittest

from helpers import BuildTest

TEXT_ON_BACKGROUND = {
    "--ink": "--paper",
    "--muted": "--paper",
    "--green": "--paper",
    "--visited": "--paper",
    "--field-ink": "--field",
    "--field-muted": "--field",
    "--field-visited": "--field",
}
"""Each colour the page sets text in, and the background it sets that text on. README.md's design note says
what each is for. A new text colour is added here with its background."""

VISITED_APART = 1.5
"""The least contrast between a visited link's colour and an unvisited one's. The colour changes hue as well,
from green to violet. The design before RisingRepos#71 changed only the underline, at 1.09:1, and a visited
row could not be told from one that was not."""


def luminance(colour: str) -> float:
    """WCAG 2's relative luminance of a colour written #rrggbb."""
    channels = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    red, green, blue = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(one: str, other: str) -> float:
    lighter, darker = sorted((luminance(one), luminance(other)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


class TheColours(BuildTest):
    def setUp(self):
        super().setUp()
        self.styles = {}
        for path, page in self.build_pages().items():
            (style,) = page.all("style")
            self.styles[path] = style.text()

    def tokens(self, style: str) -> dict[str, str]:
        return dict(re.findall(r"(--[a-z-]+):\s*(#[0-9a-f]{6});", style))

    def test_each_text_colour_meets_wcag_aa_against_its_background(self):
        for path, style in self.styles.items():
            tokens = self.tokens(style)
            for text, background in TEXT_ON_BACKGROUND.items():
                with self.subTest(path, text=text):
                    self.assertGreaterEqual(contrast(tokens[text], tokens[background]), 4.5)

    def test_the_page_sets_text_only_in_those_colours(self):
        for path, style in self.styles.items():
            with self.subTest(path):
                used = set(re.findall(r"(?<![\w-])color:\s*([^;}]+?)\s*[;}]", style))
                self.assertLessEqual(used, {f"var({token})" for token in TEXT_ON_BACKGROUND} | {"inherit", "currentColor"})

    def test_a_visited_link_differs_in_lightness_from_one_not_yet_visited(self):
        for path, style in self.styles.items():
            with self.subTest(path):
                tokens = self.tokens(style)
                self.assertGreaterEqual(contrast(tokens["--green"], tokens["--visited"]), VISITED_APART)
                self.assertRegex(style, r"a:visited\s*\{[^}]*color:\s*var\(--visited\)")

    def test_on_the_field_a_link_is_in_its_ink_and_once_visited_in_a_light_violet_apart_from_it(self):
        """The band and the strip under it are the field. RisingRepos#43 put links to other board days in the strip,
        and RisingRepos#111 made the site's name in the band a link."""
        for path, style in self.styles.items():
            with self.subTest(path):
                tokens = self.tokens(style)
                self.assertGreaterEqual(contrast(tokens["--field-ink"], tokens["--field-visited"]), VISITED_APART)
                self.assertIn(".band a, .strip a { color: var(--field-ink); }", style)
                self.assertIn(".band a:visited, .strip a:visited { color: var(--field-visited); }", style)
                self.assertRegex(style, r"\.site \.home, \.site \.home:visited \{[^}]*color: var\(--field-ink\);")

    def test_a_link_on_the_field_has_a_focus_ring_in_the_fields_ink(self):
        for path, style in self.styles.items():
            with self.subTest(path):
                self.assertIn(".band a:focus-visible, .strip a:focus-visible { outline-color: var(--field-ink); }", style)


class TheMeasure(unittest.TestCase):
    """The contrast measure above, against values WCAG's own definition gives."""

    def test_black_on_white_is_21_to_1_and_a_colour_on_itself_is_1_to_1(self):
        self.assertAlmostEqual(contrast("#000000", "#ffffff"), 21.0)
        self.assertAlmostEqual(contrast("#12704b", "#12704b"), 1.0)

    def test_the_order_of_the_two_colours_does_not_matter(self):
        self.assertAlmostEqual(contrast("#767676", "#ffffff"), contrast("#ffffff", "#767676"))
        self.assertAlmostEqual(round(contrast("#767676", "#ffffff"), 2), 4.54)


if __name__ == "__main__":
    unittest.main()
