"""Every page stays light: it carries no script, requests nothing from another site, and stays within its
size limit."""

import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from helpers import BuildTest, Page, read_json, write_json

from sitebuild import BOARD, board_day_page

SIZE_LIMIT = 320_000
"""The most bytes a page may take, uncompressed, with its styles and scripts. Issue #39 in RisingRepos set it
from the largest page measured, the chart design's page of the largest board below at 263,763 bytes, with a
fifth more for what later slices add to a row. README.md gives the measurements."""

LARGEST_BOARD = 316
"""The most rows a daily board of the earlier site held (RisingRepos's data contract, under Size)."""

LOADS = {"src", "srcset", "imagesrcset", "poster", "data", "background", "action", "formaction", "manifest", "ping"}
"""The attributes whose address a browser fetches, or sends something to, without following a link."""

CSS_ADDRESS = re.compile(r"""url\(\s*(['"]?)(.*?)\1\s*\)|@import\s+(['"])(.*?)\3""", re.IGNORECASE)


def requests(page: Page) -> list[str]:
    """Every address the page makes the browser fetch: everything but the links a reader follows."""
    found = []
    for element in page.all():
        for name, value in element.attrs.items():
            if value is None:
                continue
            if name in ("srcset", "imagesrcset"):
                found += [candidate.split()[0] for candidate in value.split(",") if candidate.strip()]
            elif name in LOADS or (element.tag == "link" and name == "href"):
                found.append(value)
            elif name == "style":
                found += css_addresses(value)
        if element.tag == "style":
            found += css_addresses(element.text())
        if element.tag == "meta" and (element.attrs.get("http-equiv") or "").lower() == "refresh":
            found.append((element.attrs.get("content") or "").partition("=")[2])
    return found


def css_addresses(css: str) -> list[str]:
    return [match.group(2) or match.group(4) for match in CSS_ADDRESS.finditer(css)]


def on_this_site(address: str) -> bool:
    parts = urlsplit(address.strip())
    return parts.scheme == "data" or not (parts.scheme or parts.netloc)


def page_weight(out: Path, path: str, page: Page) -> int:
    """The page's bytes, and those of each file on this site that it makes the browser fetch."""
    files = [address for address in requests(page) if not address.strip().startswith("data:")]
    folder = (out / path).parent
    return len(page.html.encode("utf-8")) + sum(
        ((out / address.lstrip("/")) if address.startswith("/") else (folder / address)).stat().st_size
        for address in files
    )


def made_up_rows(count: int) -> list[dict]:
    """Rows as long as the contract lets a row be in practice: a description of the most characters it may hold,
    with characters that escaping makes longer."""
    description = ("A made-up row of the largest board, with <markup> & characters escaping lengthens. " * 5)[:349]
    return [
        {
            "rank": rank,
            "github_id": 900000000 + rank,
            "full_name": f"rising-repos-example/a-made-up-repository-of-the-largest-board-{rank:03d}",
            "description": description + "…",
            "language": "Jupyter Notebook",
            "stars": 123456 + rank,
        }
        for rank in range(1, count + 1)
    ]


class PageWeight(BuildTest):
    def test_no_page_carries_a_script_and_each_page_forbids_one(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertEqual(page.all("script"), [])
                attributes = [(name, value or "") for element in page.all() for name, value in element.attrs.items()]
                self.assertEqual([name for name, _ in attributes if name.startswith("on")], [])
                self.assertEqual([value for _, value in attributes if value.strip().lower().startswith("javascript:")], [])
                (policy,) = [
                    element.attrs["content"]
                    for element in page.all("meta")
                    if element.attrs.get("http-equiv") == "Content-Security-Policy"
                ]
                self.assertTrue(policy.startswith("default-src 'none';"), policy)
                self.assertNotIn("script-src", policy)

    def test_no_page_requests_anything_from_another_site(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertEqual([address for address in requests(page) if not on_this_site(address)], [])

    def test_each_page_of_the_example_is_within_the_size_limit(self):
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertLessEqual(page_weight(self.out, path, page), SIZE_LIMIT)

    def test_each_page_of_the_largest_board_published_is_within_the_size_limit(self):
        board = read_json(self.board_file())
        write_json(self.board_file(), {**board, "rows": made_up_rows(LARGEST_BOARD)})
        pages = self.build_pages()
        self.assertEqual(len(pages[BOARD].rows()), LARGEST_BOARD)
        self.assertEqual(len(pages[board_day_page("2026-11-09")].rows()), LARGEST_BOARD)
        for path, page in pages.items():
            with self.subTest(path):
                self.assertLessEqual(page_weight(self.out, path, page), SIZE_LIMIT)


class TheChecks(unittest.TestCase):
    """The two checks above, on pages written to break them, since the built pages give them nothing to find."""

    def test_the_check_for_requests_finds_each_address_on_another_site_and_no_link(self):
        page = Page(
            '<html><head><link rel="preconnect" href="https://fonts.example">'
            "<style>@font-face { src: url(https://fonts.example/a.woff2) } @import 'https://cdn.example/x.css';</style>"
            '</head><body><img srcset="https://img.example/a.png 2x, b.png 1x"><a href="https://github.com/o/n">o/n</a>'
            "</body></html>"
        )
        self.assertEqual(
            [address for address in requests(page) if not on_this_site(address)],
            ["https://fonts.example", "https://fonts.example/a.woff2", "https://cdn.example/x.css", "https://img.example/a.png"],
        )

    def test_the_size_counts_each_file_on_this_site_that_a_page_loads(self):
        out = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (out / "day").mkdir()
        (out / "site.css").write_bytes(b"a" * 100)
        (out / "day" / "day.css").write_bytes(b"b" * 50)
        html = (
            '<html><head><link rel="stylesheet" href="/site.css"><link rel="stylesheet" href="day.css">'
            '<link rel="icon" href="data:,"></head><body></body></html>'
        )
        self.assertEqual(page_weight(out, "day/index.html", Page(html)), len(html) + 150)


if __name__ == "__main__":
    unittest.main()
