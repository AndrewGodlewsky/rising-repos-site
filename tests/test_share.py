"""What a link to the site shows when it is shared (#35): the card tags in each page's head, the canonical address,
each kind of page's own description, and the share image each board day has beside its page, which the card shows.

The image's drawing is looked at. What it says, and where each line of it sits, is its layout, which the tests read.
"""

from io import BytesIO

from helpers import BuildTest, read_json
from PIL import Image

from sitebuild import BASELINE, BOARD, DAYS, FOR_AGENTS, HOW_IT_WORKS, NOT_FOUND, board_day_page, share_lines
from sitebuild.share import HEIGHT, WIDTH

NEWEST, OLDER = "2026-11-09", "2026-11-08"
"""The example's two board days, newest first. The older lists no row."""

SITE = "https://risingrepos.com"

CARD = ("og:title", "og:description", "og:site_name", "og:image")


def card(page) -> dict[str, list[str]]:
    """Each Open Graph property the page's head states, with every value it is given."""
    found = {}
    for element in page.all("meta"):
        if element.attrs.get("property"):
            found.setdefault(element.attrs["property"], []).append(element.attrs.get("content"))
    return found


def canonicals(page) -> list[str]:
    return [
        element.attrs.get("href")
        for element in page.all("link")
        if "canonical" in (element.attrs.get("rel") or "").lower().split()
    ]


def share_image(day: str) -> str:
    return board_day_page(day).replace("index.html", "share.png")


def overlap(one: tuple, other: tuple) -> bool:
    return one[0] < other[2] and other[0] < one[2] and one[1] < other[3] and other[1] < one[3]


class TheCard(BuildTest):
    def test_every_page_carries_the_card_tags_once_each_and_names_its_image_on_risingrepos_com(self):
        pages = self.build_pages()
        self.assertEqual(
            set(pages),
            {BOARD, DAYS, HOW_IT_WORKS, FOR_AGENTS, BASELINE, NOT_FOUND, board_day_page(NEWEST), board_day_page(OLDER)},
        )
        for path, page in pages.items():
            with self.subTest(path):
                tags = card(page)
                for name in CARD:
                    self.assertEqual(len(tags.get(name, [])), 1, name)
                self.assertEqual(tags["og:site_name"], ["Rising Repos"])
                self.assertEqual(tags["og:title"], [page.one("title").text()])
                self.assertEqual(page.meta("twitter:card"), ["summary_large_image"])
                self.assertTrue(tags["og:image"][0].startswith(SITE + "/"), tags["og:image"])


class TheCanonical(BuildTest):
    def test_the_root_and_the_newest_board_days_page_declare_the_same_canonical_the_board_days_own(self):
        pages = self.build_pages()
        own = f"{SITE}/days/{NEWEST}/"
        for path in (BOARD, board_day_page(NEWEST)):
            with self.subTest(path):
                self.assertEqual(canonicals(pages[path]), [own])
                self.assertEqual(card(pages[path])["og:url"], [own])

    def test_every_other_page_declares_its_own_address_and_the_not_found_page_none(self):
        pages = self.build_pages()
        for path, own in (
            (board_day_page(OLDER), f"{SITE}/days/{OLDER}/"),
            (DAYS, f"{SITE}/days/"),
            (BASELINE, f"{SITE}/baseline/"),
            (HOW_IT_WORKS, f"{SITE}/how-it-works/"),
            (FOR_AGENTS, f"{SITE}/for-agents/"),
        ):
            with self.subTest(path):
                self.assertEqual(canonicals(pages[path]), [own])
                self.assertEqual(card(pages[path])["og:url"], [own])
        self.assertEqual(canonicals(pages[NOT_FOUND]), [])
        self.assertNotIn("og:url", card(pages[NOT_FOUND]))


class TheImage(BuildTest):
    def test_each_board_day_with_rows_has_a_1200_by_630_png_beside_its_page_which_its_page_names(self):
        pages = self.build_pages()
        with Image.open(BytesIO((self.out / share_image(NEWEST)).read_bytes())) as image:
            self.assertEqual((image.format, image.size), ("PNG", (1200, 630)))
        newest = f"{SITE}/{share_image(NEWEST)}"
        for path, named in (
            (BOARD, newest),
            (board_day_page(NEWEST), newest),
            (board_day_page(OLDER), f"{SITE}/{share_image(OLDER)}"),
            (DAYS, newest),
            (BASELINE, newest),
            (HOW_IT_WORKS, newest),
            (FOR_AGENTS, newest),
            (NOT_FOUND, newest),
        ):
            with self.subTest(path):
                tags = card(pages[path])
                self.assertEqual(tags["og:image"], [named])
                self.assertEqual((tags["og:image:width"], tags["og:image:height"]), (["1200"], ["630"]))
        # What the image says: the board day in words, and the first three rows' names in the file's order.
        board = read_json(self.board_file(NEWEST))
        lines = share_lines(board)
        self.assertIn("9 November 2026", " ".join(line.text for line in lines if line.rank is None))
        names = ["".join(line.text for line in lines if line.rank == rank and not line.is_rank) for rank in (1, 2, 3)]
        self.assertEqual(names, [row["full_name"] for row in board["rows"][:3]])
        self.assertEqual([line.text for line in lines if line.is_rank], ["1", "2", "3"])

    def test_a_board_with_no_rows_has_an_image_that_says_it_lists_no_repository(self):
        self.build_pages()
        with Image.open(BytesIO((self.out / share_image(OLDER)).read_bytes())) as image:
            self.assertEqual((image.format, image.size), ("PNG", (1200, 630)))
        empty = share_lines(read_json(self.board_file(OLDER)))
        self.assertEqual([line.rank for line in empty if line.rank is not None], [])
        self.assertIn("No repository is on this board.", [line.text for line in empty])
        # A board of two rows shows those two, and no place for a third.
        board = read_json(self.board_file(NEWEST))
        two = share_lines({**board, "rows": board["rows"][:2]})
        self.assertEqual([line.text for line in two if line.is_rank], ["1", "2"])
        self.assertNotIn("No repository is on this board.", [line.text for line in two])

    def test_a_name_too_long_for_one_line_is_drawn_whole_inside_the_image_and_no_line_overlaps_another(self):
        """As long as the second row of 26 October 2026, 106 characters, and longer: GitHub allows an owner of 39
        characters and a repository's name of 100."""
        board = read_json(self.board_file(NEWEST))
        long_names = [
            "a" * 39 + "/" + "b" * 100,
            "some-organisation/" + "a-very-long-repository-name-that-goes-on-" * 2 + "and_on.and_on",
            "x" * 39 + "/" + "y" * 100,
        ]
        rows = [{**row, "full_name": name} for row, name in zip(board["rows"], long_names, strict=False)]
        lines = share_lines({**board, "rows": rows})
        for rank, name in enumerate(long_names, 1):
            self.assertEqual("".join(line.text for line in lines if line.rank == rank and not line.is_rank), name)
        boxes = [line.box() for line in lines]
        for box in boxes:
            self.assertTrue(0 <= box[0] and 0 <= box[1] and box[2] <= WIDTH and box[3] <= HEIGHT, box)
        for one in range(len(boxes)):
            for other in range(one + 1, len(boxes)):
                self.assertFalse(overlap(boxes[one], boxes[other]), (lines[one].text, lines[other].text))


class TheDescriptions(BuildTest):
    def test_each_kind_of_page_has_a_description_of_its_own_and_a_board_days_names_its_day(self):
        pages = self.build_pages()
        described = {}
        for path, page in pages.items():
            (description,) = page.meta("description")
            self.assertEqual(card(page)["og:description"], [description], path)
            described[path] = description
        kinds = {
            "root": [described[BOARD]],
            "board day": [described[board_day_page(NEWEST)], described[board_day_page(OLDER)]],
            "history": [described[DAYS]],
            "baseline": [described[BASELINE]],
            "how it works": [described[HOW_IT_WORKS]],
        }
        for kind, descriptions in kinds.items():
            for other, theirs in kinds.items():
                if other != kind:
                    self.assertFalse(set(descriptions) & set(theirs), (kind, other))
            self.assertNotIn(described[NOT_FOUND], descriptions, kind)
        self.assertIn("9 November 2026", described[board_day_page(NEWEST)])
        self.assertIn("8 November 2026", described[board_day_page(OLDER)])
        self.assertEqual(
            described[NOT_FOUND],
            "GitHub repositories gaining stars faster than their own pace predicts, on a new board each day.",
        )
