"""The build reads the data files only as RisingRepos's data contract (version 1) defines them, and checks
each one against the schema that is shipped with it."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import EXAMPLE, BuildTest, read_json, write_json

import sitebuild
from sitebuild import BOARD
from sitebuild.contract import SCHEMA_VERSION_NEEDED, DataError

COPIED = {
    "contract/daily.schema.json": "4cf53ad662ae30326701501f4d26403bb7acb4421a46dc194a0a1f0e5d159e71",
    "contract/index.schema.json": "e2f3f9467a029962f69c10d9560a710a4aeb0eefa690a537faf75641d6898815",
    "boards/index.json": "e748551f487ba07f4bfa048eba037fe9e19209eddcd28b84a24c5bca9e6ae523",
    "boards/days/2026-11-09/daily.json": "6cfa2a2ba8ec13a717c9757d6c027af31acd87b03e3574949c2ec7d99fe2eaab",
    "boards/days/2026-11-08/daily.json": "a2620bcad1c3340204f1dfcf08f42ee5dc4cc9d65f6f07497f3de75862f32dcd",
}
"""The SHA-256 of each file the example copies, by its path under site-data/: the schemas and the example in
RisingRepos's src/risingrepos/publishing/contract/ at 81ba0820c50f736c8b25c2ff0058dadad4dcab05, which gave each
board day in the index its row count (RisingRepos#43). A change to the contract reaches this copy by a pull
request here that changes these too."""


class TheExample(unittest.TestCase):
    def test_the_tests_build_from_the_contracts_example_and_schemas_byte_for_byte(self):
        files = sorted(path.relative_to(EXAMPLE).as_posix() for path in EXAMPLE.rglob("*") if path.is_file())
        self.assertEqual(files, sorted(COPIED))
        for name, digest in COPIED.items():
            with self.subTest(name):
                self.assertEqual(hashlib.sha256((EXAMPLE / name).read_bytes()).hexdigest(), digest)


class TheDataFiles(BuildTest):
    def test_an_index_that_does_not_match_its_schema_fails_the_build_and_names_the_file(self):
        write_json(self.index, {"schema_version": 1, "board_days": []})
        self.assertBuildFails(str(self.index), "board_days")

    def test_a_board_day_file_that_does_not_match_its_schema_fails_the_build_and_names_the_file(self):
        board = read_json(self.board_file())
        board["rows"][1]["stars"] = "many"
        write_json(self.board_file(), board)
        self.assertBuildFails(str(self.board_file()), "stars")

    def test_a_file_that_is_not_json_fails_the_build_and_names_the_file(self):
        self.board_file().write_text("{", encoding="utf-8")
        self.assertBuildFails(str(self.board_file()))

    def test_a_missing_board_day_file_fails_the_build_and_names_it(self):
        self.board_file().unlink()
        self.assertBuildFails(str(self.board_file()))

    def test_a_board_day_file_whose_board_day_is_not_its_folders_fails_the_build(self):
        board = read_json(self.board_file())
        write_json(self.board_file(), {**board, "board_day": "2026-11-07"})
        self.assertBuildFails(str(self.board_file()), "2026-11-07", "2026-11-09")

    def test_the_build_states_the_lowest_schema_version_its_pages_need_and_fails_on_a_file_below_it(self):
        self.assertEqual(SCHEMA_VERSION_NEEDED, 1)
        below = SCHEMA_VERSION_NEEDED - 1
        schema = read_json(self.daily_schema)
        schema["properties"]["schema_version"]["const"] = below
        write_json(self.daily_schema, schema)
        write_json(self.board_file(), {**read_json(self.board_file()), "schema_version": below})
        self.assertBuildFails(str(self.board_file()), f"version {below}", f"version {SCHEMA_VERSION_NEEDED}")

    def test_a_field_the_pages_do_not_read_added_to_a_row_and_to_the_schema_is_ignored(self):
        # As RisingRepos adds a field: to the schema it ships, as a required field, and to every file.
        schema = read_json(self.daily_schema)
        row = schema["properties"]["rows"]["items"]
        row["properties"]["forks"] = {"description": "A field the pages do not read.", "type": "integer"}
        row["required"].append("forks")
        write_json(self.daily_schema, schema)
        board = read_json(self.board_file())
        for row in board["rows"]:
            row["forks"] = 31337
        write_json(self.board_file(), board)
        pages = self.build_pages()
        self.assertEqual(len(pages[BOARD].rows()), len(board["rows"]))
        for path, page in pages.items():
            with self.subTest(path):
                self.assertNotIn("31337", page.html)
                self.assertNotIn("forks", page.html)

    def test_every_board_days_file_is_checked_and_an_older_one_that_does_not_match_fails_the_build(self):
        board = read_json(self.board_file("2026-11-08"))
        write_json(self.board_file("2026-11-08"), {**board, "score_provisional": "yes"})
        self.assertBuildFails(str(self.board_file("2026-11-08")), "score_provisional")

    def test_a_board_day_in_the_index_without_its_file_fails_the_build_and_names_the_file(self):
        self.board_file("2026-11-08").unlink()
        self.assertBuildFails(str(self.board_file("2026-11-08")))

    def test_an_index_that_does_not_list_each_board_day_once_newest_first_fails_the_build(self):
        # A board day listed twice with two row counts: the schema's uniqueItems compares whole entries.
        for days in (["2026-11-08", "2026-11-09"], ["2026-11-09", "2026-11-09", "2026-11-08"]):
            with self.subTest(days):
                entries = [{"board_day": day, "row_count": count} for count, day in enumerate(days)]
                write_json(self.index, {"schema_version": 1, "board_days": entries})
                self.assertBuildFails(str(self.index), "newest first")

    def test_an_index_that_lists_a_day_that_is_not_a_date_fails_the_build(self):
        index = read_json(self.index)
        write_json(self.index, {**index, "board_days": [*index["board_days"], {"board_day": "2026-02-30", "row_count": 0}]})
        self.assertBuildFails(str(self.index), "'2026-02-30', which is not a date")

    def test_an_index_from_before_row_count_still_builds_because_the_pages_count_each_boards_own_rows(self):
        # As site-data/ held it before RisingRepos#43: the schema and the index without row_count.
        schema = read_json(self.index_schema)
        entry = schema["properties"]["board_days"]["items"]
        del entry["properties"]["row_count"]
        entry["required"].remove("row_count")
        write_json(self.index_schema, schema)
        index = read_json(self.index)
        write_json(self.index, {**index, "board_days": [{"board_day": entry["board_day"]} for entry in index["board_days"]]})
        pages = self.build_pages()
        self.assertEqual(len(pages[BOARD].rows()), len(read_json(self.board_file())["rows"]))

    def test_the_pages_do_not_read_row_count_and_count_each_boards_rows_from_its_file(self):
        index = read_json(self.index)
        write_json(self.index, {**index, "board_days": [{**entry, "row_count": 31337} for entry in index["board_days"]]})
        for path, page in self.build_pages().items():
            with self.subTest(path):
                self.assertNotIn("31,337", page.html)
                self.assertNotIn("31337", page.html)

    def test_a_field_added_to_a_row_but_not_to_the_schema_fails_the_build(self):
        board = read_json(self.board_file())
        board["rows"][0]["homepage"] = "https://example.com/"
        write_json(self.board_file(), board)
        self.assertBuildFails(str(self.board_file()), "homepage")


class TheSchemas(BuildTest):
    """A schema is code to fastjsonschema, and it arrives with the data. It may refer only within itself."""

    def test_a_schema_with_a_ref_that_does_not_start_with_a_hash_fails_the_build_and_names_the_schema(self):
        for ref in ("https://example.invalid/row.schema.json", "row.schema.json", "file:///row.schema.json"):
            for schema in (self.daily_schema, self.index_schema):
                with self.subTest(ref=ref, schema=schema.name):
                    original = schema.read_bytes()
                    value = read_json(schema)
                    value["definitions"] = {"elsewhere": {"$ref": ref}}
                    write_json(schema, value)
                    # Refused by the build's own check, before fastjsonschema compiles anything.
                    self.assertBuildFails(str(schema), repr(ref), "A schema may refer only within itself")
                    schema.write_bytes(original)

    def test_a_schema_never_makes_the_build_fetch_a_reference(self):
        # Every $ref starts with '#', but the $id's fragment keeps the schema itself out of fastjsonschema's store
        # of known documents, so it resolves the reference as a remote document: with urllib, unless the build
        # passes handlers that refuse it.
        value = read_json(self.daily_schema)
        value["$id"] = "https://example.invalid/daily.schema.json#board"
        value["definitions"] = {"stars": {"type": "integer", "minimum": 0}}
        value["properties"]["rows"]["items"]["properties"]["stars"] = {"$ref": "#/definitions/stars"}
        write_json(self.daily_schema, value)
        out = Path(self.enterContext(tempfile.TemporaryDirectory())) / "dist"
        with mock.patch("urllib.request.urlopen") as urlopen:
            with self.assertRaises(DataError) as refused:
                sitebuild.build(out, data=self.data, noindex=False)
        urlopen.assert_not_called()
        self.assertIn(str(self.daily_schema), str(refused.exception))
        self.assertIn("https://example.invalid/daily.schema.json", str(refused.exception))


if __name__ == "__main__":
    unittest.main()
