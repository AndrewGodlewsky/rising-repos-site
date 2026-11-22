"""Make the four font files the pages carry from the files in source/, so that they can be made again.

Each page holds these files inside its stylesheet as data: URIs (sitebuild/__init__.py, `font_faces`), so they are
cut to what the site writes: printable ASCII, the no-break space, and the site's own other characters, CHARACTERS
below, with kerning and the standard ligatures kept and the hinting dropped. A letter outside them, such as an
accented letter in owner-written text, is drawn in the fallback face that site.css matches to their metrics.

The licence. The source files are IBM Plex Sans and IBM Plex Mono, Copyright 2017 IBM Corp. with Reserved
Font Name "Plex", under the SIL Open Font License 1.1 (sitebuild/static/fonts/OFL.txt, published with the site). A
subset is a Modified Version under the licence (its FAQ, 2.6), and condition 3 bars a Modified Version from the
Reserved Font Name, and condition 4 from the copyright holder's name as promotion. So this script renames what it
makes, RENAMED below: every name record that names the family or the face, IDs 1, 2, 3, 4, 6, 16, 17, 18, 21, and 22
where present, after which no such record holds "Plex" or "IBM", and sets the vendor code in OS/2 from IBM's
"IBM " to "NONE". It keeps the copyright (ID 0), the version (5), the licence's description and address (13,
14) as IBM wrote them, restoring 13 in IBM's words where the sources lacked it, and the records from 256 on that the
STAT table names its axes by. It writes a description (10) that says the font is a modified version of IBM Plex, as
acknowledgement. It drops the other records, the trademark among them, and, as fontTools does by default, the
Macintosh platform's copies of those it keeps. It checks every table for the
old name after renaming and stops if one holds it.

The sources in source/ are Latin cuts of IBM Plex Sans 3.201 and IBM Plex Mono 2.3 from the Fontsource packaging,
the files the site's design was drawn in, renamed once by this script's `--rename-sources` step, outlines
untouched. IBM's own release files (github.com/IBM/plex, Sans 3.006 and Mono 2.005 on 21 November 2026) are another
build, whose outlines, some widths, and vertical metrics differ, so the site keeps these.

It needs fontTools and brotli, which the build does not, so it runs in an environment of its own that uv makes for the
run and installs nothing into: from the repository's root,
`uv run --no-project --with fonttools==4.63.0 --with brotli==1.2.1 python sitebuild/fonts/subset.py`, which makes the
files in fonts/ byte for byte. Those two versions were checked on 22 November 2026 under the rule in README.md
("Changing a pinned version"), with RisingRepos's `scripts/run_limits/check_downloads.py`: no known vulnerability on
osv.dev, and published at least 14 days before. A change to either is checked the same way first.
"""

import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
# Beyond ASCII: no-break space, middle dot, », ×, ÷, en dash, em dash, ellipsis, ‹, ›, the up arrow, and the minus
# sign, which a loss is written with, as wide as the plus and the figures.
CHARACTERS = "U+0020-007E,U+00A0,U+00B7,U+00BB,U+00D7,U+00F7,U+2013,U+2014,U+2026,U+2039,U+203A,U+2191,U+2212"
# What each file is made from, in source/, and the family it is renamed to.
FILES = {
    "rising-sans-400": ("rising-sans-latin-400.woff2", "IBM Plex Sans", "Rising Sans"),
    "rising-sans-500": ("rising-sans-latin-500.woff2", "IBM Plex Sans", "Rising Sans"),
    "rising-mono-400": ("rising-mono-latin-400.woff2", "IBM Plex Mono", "Rising Mono"),
    "rising-mono-500": ("rising-mono-latin-500.woff2", "IBM Plex Mono", "Rising Mono"),
}
# The sources as they came, from the Fontsource packaging of IBM Plex (Sans 3.201, Mono 2.3): Latin cuts, so
# modified versions already, under the reserved name until `--rename-sources` renamed them.
CAME_AS = {
    "rising-sans-latin-400.woff2": "ibm-plex-sans-latin-400.woff2",
    "rising-sans-latin-500.woff2": "ibm-plex-sans-latin-500.woff2",
    "rising-mono-latin-400.woff2": "ibm-plex-mono-latin-400.woff2",
    "rising-mono-latin-500.woff2": "ibm-plex-mono-latin-500.woff2",
}
RENAMED = {1, 2, 3, 4, 6, 16, 17, 18, 21, 22}
KEPT = {0, 5, 13, 14}
DESCRIPTION = 10
LICENCE = 13
# Record 13 as IBM writes it in its own release files (github.com/IBM/plex), restored where the sources lacked it.
LICENCE_TEXT = ("This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available "
                "with a FAQ at: http://scripts.sil.org/OFL")
OLD = ("Plex", "IBM")


def options() -> subset.Options:
    chosen = subset.Options()
    chosen.layout_features = ["kern", "liga"]
    chosen.hinting = False
    chosen.flavor = "woff2"
    chosen.name_IDs = ["*"]  # every record, so that 13 and 14 survive; rename() then keeps only what it means to
    return chosen


def rename(font: TTFont, old: str, new: str) -> None:
    """Give the font the family `new` in place of `old`, as the module's docstring says."""
    table = font["name"]
    # Kept besides: the records from 256 on, which STAT names its axes and values by ("Weight", "Regular", ...).
    table.names = [record for record in table.names if record.nameID in RENAMED | KEPT or
                   (record.nameID >= 256 and not any(word in record.toUnicode() for word in OLD))]
    if not table.getName(LICENCE, 3, 1, 0x409):  # the Fontsource cuts dropped it: IBM's own words, from its files
        table.setName(LICENCE_TEXT, LICENCE, 3, 1, 0x409)
    postscript = new.replace(" ", "")
    version = font["head"].fontRevision
    for record in table.names:
        if record.nameID not in RENAMED:
            continue
        text = record.toUnicode().replace(old, new).replace(old.replace(" ", ""), postscript)
        if record.nameID == 3:  # the unique ID, "version;vendor;PostScript name" in IBM's files
            text = f"{version:.3f};RisingRepos;{table.getDebugName(6).replace(old.replace(' ', ''), postscript)}"
        record.string = text
    font["OS/2"].achVendID = "NONE"  # IBM's registered vendor code ("IBM "): the modified font is not IBM's
    table.setName(f"A modified version of {old} by IBM Corp., under the SIL Open Font License 1.1: cut to the "
                  f"characters of risingrepos.com, unhinted, and renamed, as the licence asks of a modified version.",
                  DESCRIPTION, 3, 1, 0x409)
    for record in table.names:
        if record.nameID in RENAMED and any(word in record.toUnicode() for word in OLD):
            raise SystemExit(f"name record {record.nameID} still says {record.toUnicode()!r}")


def old_name_left(path: Path) -> list[str]:
    """Each table of the saved font, other than the kept name records, that still holds the old name."""
    font = TTFont(path)
    found = []
    for tag in font.keys():
        if tag in ("GlyphOrder", "name"):
            continue
        data = font.getTableData(tag)
        if any(word.encode("ascii") in data or word.encode("utf-16-be") in data for word in OLD):
            found.append(tag)
    return found


def main(source: Path, out: Path) -> None:
    unicodes = subset.parse_unicodes(CHARACTERS)
    for name, (file, old, new) in FILES.items():
        chosen = options()
        font = subset.load_font(str(source / file), chosen)
        cutter = subset.Subsetter(chosen)
        cutter.populate(unicodes=unicodes)
        cutter.subset(font)
        rename(font, old, new)
        path = out / f"{name}.woff2"
        subset.save_font(font, str(path), chosen)
        left = old_name_left(path)
        if left:
            raise SystemExit(f"{path.name}: the old name is still in {left}")
        print(name, path.stat().st_size, "bytes")


def rename_sources(came: Path, source: Path) -> None:
    """Rename the sources as they came (CAME_AS) into source/, outlines untouched: a step run once."""
    for name, (_, old, new) in FILES.items():
        file = FILES[name][0]
        font = TTFont(came / CAME_AS[file])
        rename(font, old, new)
        font.save(source / file)
        left = old_name_left(source / file)
        if left:
            raise SystemExit(f"{file}: the old name is still in {left}")
        print(file, (source / file).stat().st_size, "bytes")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--rename-sources"]:  # python sitebuild/fonts/subset.py --rename-sources <folder as they came>
        rename_sources(Path(sys.argv[2]), HERE / "source")
    else:  # optional: another source folder and output folder, for comparing builds
        main(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "source", Path(sys.argv[2]) if len(sys.argv) > 2 else HERE)
