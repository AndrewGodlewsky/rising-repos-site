"""Build the site's pages: python -m sitebuild <folder> [--noindex] [--data <folder>]"""

import argparse
import sys
from pathlib import Path

from sitebuild import DATA, build
from sitebuild.contract import DataError


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m sitebuild", description="Build the site's pages into a new folder."
    )
    parser.add_argument("out", type=Path, help="the folder to write the pages into. It must be new or empty")
    parser.add_argument(
        "--noindex",
        action="store_true",
        help="ask search engines not to index the pages, as every page built for the preview does",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DATA,
        help="the folder of data files, laid out as the data contract says (default: this repository's site-data)",
    )
    parser.add_argument(
        "--no-share-images",
        action="store_true",
        help="leave out each board day's share.png, for checks that weigh or read the HTML pages alone (#253)",
    )
    options = parser.parse_args()
    try:
        build(options.out, data=options.data, noindex=options.noindex, share_images=not options.no_share_images)
    except (FileExistsError, DataError) as error:
        print(f"sitebuild: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
