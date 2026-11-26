"""The shaded gain in an opened row's drawing. Sentence 41 of the owner's tests."""

import re
import unittest

from playwright.sync_api import expect

from owner_tests.scenario import Scenario, open_row, rows_that_open

DRAWING = "Its own pace against what it gained"
"""The caption that names an opened row's drawing of its own pace against what it gained."""

OPENED = 5
"""How many of the board's first rows are opened and their drawings read."""

MARKS = """figure => Array.from(figure.querySelectorAll('path')).map(mark => {
  const style = getComputedStyle(mark);
  return {
    d: mark.getAttribute('d') || '',
    filled: style.fill !== 'none',
    stroked: style.stroke !== 'none',
    dashed: style.strokeDasharray !== 'none',
    width: parseFloat(style.strokeWidth),
    length: mark.getTotalLength(),
  };
})"""
"""Each mark of a drawing, as the browser draws it: its outline, whether it is filled, whether it is stroked, whether
the stroke is dashed, how wide the stroke is, and how long its outline is. The marks of a drawing have no role, so
they are found by their tag, `path`."""

COMMAND = re.compile(r"[MLHVZ]|-?\d+(?:\.\d+)?(?:e-?\d+)?")

NEAR = 1e-6
"""Two points of a drawing's box, 100 across and 100 down, that are this near are one point."""


def runs(d: str) -> list[list[tuple[float, float]]]:
    """The points an outline passes through, as a run for each time the pen is lifted. A closed run ends at its
    first point again."""
    tokens, found, point, at = COMMAND.findall(d), [], (0.0, 0.0), 0
    while at < len(tokens):
        command = tokens[at]
        if command == "Z":
            found[-1].append(found[-1][0])
            at += 1
            continue
        if command == "H":
            point, at = (float(tokens[at + 1]), point[1]), at + 2
        elif command == "V":
            point, at = (point[0], float(tokens[at + 1])), at + 2
        else:
            point, at = (float(tokens[at + 1]), float(tokens[at + 2])), at + 3
        if command == "M":
            found.append([])
        found[-1].append(point)
    return found


def one(first: tuple[float, float], second: tuple[float, float]) -> bool:
    return abs(first[0] - second[0]) < NEAR and abs(first[1] - second[1]) < NEAR


class TheShadedGain(Scenario):
    def test_the_shaded_gain_in_an_opened_rows_drawing_follows_the_line_of_what_it_gained_through_each_recent_day(
        self,
    ):
        """Sentence 41. Each of the board's first five rows is opened, and its drawing of its own pace against what
        it gained is read, by its caption. The shaded gain is the drawing's one filled shape that closes on itself.
        The line of what it gained is its boldest solid line that has a length: the dashed line is its own pace, and
        the dot at the line's end has no length. Every point of the line over the days the shading spans, from its
        left edge to its right, is a corner of the shading's outline, and they come one after another, in the
        line's order, so that the shading's edge is the line itself there and leaves none of it unshaded. At least
        one of the drawings has to hold a day between the first and the last of the shaded ones, since only then
        could the shading cut across the line."""
        page = self.reader()
        self.visit(page)
        shown = rows_that_open(page)
        self.given(shown.count(), "the newest board lists no row that opens")
        middle = 0
        for at in range(min(OPENED, shown.count())):
            row = shown.nth(at)
            open_row(row)
            drawing = row.get_by_role("figure", name=DRAWING, exact=True)
            expect(drawing).to_be_visible()
            marks = drawing.evaluate(MARKS)
            (shaded,) = [mark for mark in marks if mark["filled"] and mark["d"].rstrip().endswith("Z")]
            solid = [
                mark
                for mark in marks
                if mark["stroked"] and not mark["dashed"] and mark["length"] > 0 and mark is not shaded
            ]
            line = max(solid, key=lambda mark: mark["width"])
            (outline,) = runs(shaded["d"])
            corners = [
                point for point in outline if not any(one(point, kept) for kept in outline[: outline.index(point)])
            ]
            left, right = min(x for x, _ in outline), max(x for x, _ in outline)
            under = [point for run in runs(line["d"]) for point in run if left - NEAR <= point[0] <= right + NEAR]
            with self.subTest(row=at):
                self.assertGreaterEqual(len(under), 2, (shaded["d"], line["d"]))
                starts = [place for place, corner in enumerate(corners) if one(corner, under[0])]
                self.assertTrue(starts, f"the shading {shaded['d']} does not start at the line {line['d']}")
                followed = corners[starts[0] : starts[0] + len(under)]
                self.assertEqual(len(followed), len(under), (shaded["d"], line["d"]))
                for corner, point in zip(followed, under, strict=True):
                    self.assertTrue(one(corner, point), f"the shading {shaded['d']} leaves the line {line['d']}")
            middle += len(under) > 2
        self.given(middle, "no drawing of the first rows holds a day between the first and the last shaded ones")


if __name__ == "__main__":
    unittest.main()
