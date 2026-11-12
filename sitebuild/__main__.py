"""Build the site's pages: python -m sitebuild <folder> [--noindex]"""

import argparse
import sys
from pathlib import Path

from sitebuild import build


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m sitebuild", description="Build the site's pages into a new folder.")
    parser.add_argument("out", type=Path, help="the folder to write the pages into. It must be new or empty")
    parser.add_argument(
        "--noindex",
        action="store_true",
        help="ask search engines not to index the pages, as every page built for the preview does",
    )
    options = parser.parse_args()
    try:
        build(options.out, noindex=options.noindex)
    except FileExistsError as error:
        print(f"sitebuild: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
