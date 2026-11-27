"""The list of every repository, `/repos.tsv`, which the query service in another repository fetches (#177).

Its format is a contract with that service, so these hold it: the two opening lines, the seven fields of every line,
each repository once by its GitHub id, and each history in order. They build boards written for each case."""

import unittest

from helpers import BuildTest, read_json, write_json

from sitebuild.repo_list import FIELDS, LIST_FORMAT, repo_list

NEWEST, OLDER, OLDEST = "2026-11-09", "2026-11-08", "2026-11-07"


class TheRepositoryList(BuildTest):
    def listed(self) -> list[list[str]]:
        """The built list's lines after the two opening ones, each split into its fields."""
        self.build_pages()
        text = (self.out / "repos.tsv").read_text(encoding="utf-8")
        return [line.split("\t") for line in text.split("\n")[2:] if line]

    def add_board(self, day: str, rows: list[dict]) -> None:
        """Write a board day `day`, in the index, with `rows` for its rows, made from the newest board's first row."""
        board = {**read_json(self.board_file(NEWEST)), "board_day": day, "rows": rows}
        index = read_json(self.index)
        kept = [entry for entry in index["board_days"] if entry["board_day"] != day]
        entry = {"board_day": day, "row_count": len(rows)}
        index["board_days"] = sorted([*kept, entry], key=lambda e: e["board_day"], reverse=True)
        write_json(self.index, index)
        self.write_board(board)

    def row(self, rank: int, github_id: int, name: str, **changes) -> dict:
        template = read_json(self.board_file(NEWEST))["rows"][0]
        return {**template, "rank": rank, "github_id": github_id, "full_name": name, **changes}

    def test_the_list_opens_with_its_format_and_its_fields(self):
        self.build_pages()
        lines = (self.out / "repos.tsv").read_text(encoding="utf-8").split("\n")
        self.assertEqual(lines[0], f"# rising-repos list, format {LIST_FORMAT}")
        self.assertEqual(lines[0], "# rising-repos list, format 1")
        self.assertEqual(lines[1], "\t".join(FIELDS))

    def test_every_repository_ever_on_a_board_is_listed_once(self):
        newest = read_json(self.board_file(NEWEST))["rows"]
        gone = self.row(1, 700_001, "example/gone-by-the-newest-board")
        renamed = self.row(2, newest[0]["github_id"], "example/the-old-name")
        self.add_board(OLDEST, [gone, renamed])
        ids = {row["github_id"] for row in newest} | {gone["github_id"]}
        names = [fields[0] for fields in self.listed()]
        self.assertEqual(len(names), len(ids))
        self.assertEqual(len(set(names)), len(names))
        self.assertIn("example/gone-by-the-newest-board", names)
        self.assertIn(newest[0]["full_name"], names)
        self.assertNotIn("example/the-old-name", names)

    def test_each_line_has_seven_fields_and_no_tab_or_line_break_inside_one(self):
        messy = self.row(1, 700_002, "example/messy", description="one\ttwo\nthree\r\nfour", language=None)
        self.add_board(OLDEST, [messy])
        lines = self.listed()
        self.assertTrue(lines)
        self.assertTrue(all(len(fields) == len(FIELDS) for fields in lines), lines)
        line = next(fields for fields in lines if fields[0] == "example/messy")
        self.assertEqual(line[1], "")
        self.assertEqual(line[-1], "one two three  four")

    def test_a_history_lists_every_board_day_with_its_rank_oldest_first(self):
        first = self.row(3, 700_003, "example/steady")
        second = self.row(1, 700_003, "example/steady")
        self.add_board(OLDEST, [first])
        self.add_board(OLDER, [second])
        line = next(fields for fields in self.listed() if fields[0] == "example/steady")
        self.assertEqual(line[5], f"{OLDEST}:3,{OLDER}:1")

    def test_a_repository_is_listed_under_its_newest_name_with_its_newest_board_figures(self):
        old = self.row(4, 700_004, "example/before", stars=10, language="C")
        new = self.row(2, 700_004, "example/after", stars=99, language="Rust")
        self.add_board(OLDEST, [old])
        self.add_board(OLDER, [new])
        lines = [fields for fields in self.listed() if fields[0].startswith("example/") and "700" not in fields[0]]
        line = next(fields for fields in lines if fields[0] == "example/after")
        self.assertEqual(line[1:5], ["Rust", "99", OLDER, "2"])
        self.assertEqual(line[5], f"{OLDEST}:4,{OLDER}:2")
        self.assertNotIn("example/before", [fields[0] for fields in lines])


class TheListOfNoBoards(unittest.TestCase):
    def test_no_board_makes_a_list_of_its_two_opening_lines(self):
        self.assertEqual(repo_list([]), "# rising-repos list, format 1\n" + "\t".join(FIELDS) + "\n")


if __name__ == "__main__":
    unittest.main()
