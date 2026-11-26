"""A board day's share image: the picture a link's card shows when the board day's address, or the root's, is
shared on Discord or X (#35). It says the board day in words and the full names of the board's first three rows,
in the site's own faces and colours, and is written beside the board day's page as share.png.

The image is laid out first, as lines of text, each with its face, size, place, and colour, and drawn from that
layout after. So what it says and where each line sits are read by the tests, and the drawing is looked at.

Pillow reads the site's WOFF2 faces as they are, through its own FreeType. Its builds for Windows have no raqm, so
every face is opened with the basic layout engine, and a name is laid out alike on the machine and on the build job.
"""

from dataclasses import dataclass
from functools import cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1200, 630
"""The size both cards draw a large image at without cropping it: 1.91 to 1."""

MARGIN = 80
NAME_X = 152
"""Where a row's name starts, after its rank in the margin's column."""
ROWS_TOP, ROWS_BOTTOM = 236, HEIGHT - 56
"""The band the rows are laid out in, under the heading."""

LARGEST, SMALLEST = 56, 16
"""The size a row's name is drawn at when the three fit, and the least it is shrunk to. A name of GitHub's longest,
an owner of 39 characters and a repository's name of 100, takes two lines at 16, so three such fit."""

BREAKS = "/-_."
"""The characters a name is wrapped after where it can be. Elsewhere it is wrapped at any character."""

# The light theme's colours, from site.css: the page, the ink, the second ink, and the evergreen pen.
BACKGROUND, TEXT, TEXT_2, ACCENT = "#f7f6f2", "#1b1a16", "#55524a", "#12704b"

FONTS = Path(__file__).parent / "fonts"
SANS, SANS_MEDIUM, MONO, MONO_MEDIUM = "rising-sans-400", "rising-sans-500", "rising-mono-400", "rising-mono-500"

EMPTY = "No repository is on this board."
"""What an empty board's image says, in its page's own words."""


@cache
def font(face: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONTS / f"{face}.woff2", size, layout_engine=ImageFont.Layout.BASIC)


@dataclass(frozen=True)
class Line:
    """One line of the image's text, drawn with its top left at (x, y). `rank` is the rank of the row it belongs
    to, or None for the heading; `is_rank` is true of the rank's own figure, beside the name's first line."""

    text: str
    face: str
    size: int
    x: int
    y: int
    fill: str
    rank: int | None = None
    is_rank: bool = False

    def box(self) -> tuple[int, int, int, int]:
        """The box the line's ink takes in the image: left, top, right, bottom."""
        left, top, right, bottom = font(self.face, self.size).getbbox(self.text, anchor="la")
        return (self.x + int(left), self.y + int(top), self.x + int(right), self.y + int(bottom))


def layout(day: str, names: list[str]) -> list[Line]:
    """The image's lines for a board day, given as the site writes it ("9 November 2026"), and the full names of
    its first three rows, in the file's order. An empty board says so in words, as its page does (B3)."""
    lines = [
        Line("Rising Repos", SANS_MEDIUM, 40, MARGIN, 64, ACCENT),
        Line(f"The daily board for {day}", SANS, 52, MARGIN, 124, TEXT),
    ]
    if not names:
        return [*lines, Line(EMPTY, SANS, 44, MARGIN, ROWS_TOP, TEXT_2)]
    for size in range(LARGEST, SMALLEST - 1, -2):
        rows = _rows(names, size)
        if max(line.box()[3] for line in rows) <= ROWS_BOTTOM:
            return lines + rows
    raise ValueError(f"the names do not fit the image at {SMALLEST} px: {names}")


def _rows(names: list[str], size: int) -> list[Line]:
    """Each name under the one before, at `size`, wrapped to the room beside the ranks."""
    height, gap = round(size * 1.25), round(size * 0.45)
    lines, y = [], ROWS_TOP
    for rank, name in enumerate(names, 1):
        lines.append(Line(str(rank), MONO_MEDIUM, size, MARGIN, y, ACCENT, rank, is_rank=True))
        for part in wrapped(name, font(MONO, size), WIDTH - MARGIN - NAME_X):
            lines.append(Line(part, MONO, size, NAME_X, y, TEXT, rank))
            y += height
        y += gap
    return lines


def wrapped(name: str, face: ImageFont.FreeTypeFont, room: int) -> list[str]:
    """`name` in lines no wider than `room`, each broken after a `/`, `-`, `_`, or `.` where one falls in the
    second half of the line, and at the last character that fits where none does."""
    lines, rest = [], name
    while face.getlength(rest) > room:
        fits = len(rest) - 1
        while fits > 1 and face.getlength(rest[:fits]) > room:
            fits -= 1
        after = [place + 1 for place in range(fits // 2, fits) if rest[place] in BREAKS]
        cut = after[-1] if after else fits
        lines.append(rest[:cut])
        rest = rest[cut:]
    return [*lines, rest]


def draw(lines: list[Line]) -> bytes:
    """The image, as the bytes of a PNG."""
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    pen = ImageDraw.Draw(image)
    for line in lines:
        pen.text((line.x, line.y), line.text, font=font(line.face, line.size), fill=line.fill, anchor="la")
    written = BytesIO()
    image.save(written, "PNG", optimize=True)
    return written.getvalue()
