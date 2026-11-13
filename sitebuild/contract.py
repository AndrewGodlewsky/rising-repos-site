"""Reading the data files that RisingRepos publishes into site-data/, as its data contract defines them.

The contract is RisingRepos's src/risingrepos/publishing/contract/README.md. Each file is checked against the
schema that is shipped with it, in site-data/contract/, before anything is built from it.
"""

import json
from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path
from typing import NoReturn

import fastjsonschema

SCHEMA_VERSION_NEEDED = 1
"""The lowest `schema_version` the pages need. A file below it fails the build."""


class DataError(Exception):
    """A data file or a schema the pages cannot be built from. The message names the file."""


def boards(data: Path) -> list[dict]:
    """The daily board of every board day in the index, newest first, each read and checked with the index.

    The index names every board day a single time, newest first, and the pages rely on that order: the latest
    page shows the first, and each board day's page links to the board days beside it. Each entry's `row_count`
    must be the number of rows in its board day's file (RisingRepos#115). The pages count a board's rows from the
    file, which they read anyway, so the check is what holds the index's count true for whatever else reads it.
    """
    path = data / "boards" / "index.json"
    index = _read(path, _validator(data / "contract" / "index.schema.json"))
    days = [entry["board_day"] for entry in index["board_days"]]
    for day in days:
        try:
            date.fromisoformat(day)
        except ValueError:
            raise DataError(f"{path} lists {day!r}, which is not a date") from None
    for newer, older in zip(days, days[1:]):
        if newer <= older:
            raise DataError(f"{path} lists {newer} before {older}: it must list each board day once, newest first")
    validate = _validator(data / "contract" / "daily.schema.json")
    boards = []
    for entry in index["board_days"]:
        if "row_count" not in entry:  # only where the schema shipped with the index does not require it
            raise DataError(f"{path} lists {entry['board_day']} without its row_count")
        board = _board(data, entry["board_day"], validate)
        if entry["row_count"] != len(board["rows"]):
            raise DataError(
                f"{path} gives {entry['board_day']} {entry['row_count']} rows, "
                f"and its file holds {len(board['rows'])}"
            )
        boards.append(board)
    return boards


def latest_board(data: Path) -> dict:
    """The daily board of the newest board day, the one the site's root shows. It is the first of `boards`, so it
    fails wherever the build would. The site eval reads it to know which board day the preview should state."""
    return boards(data)[0]


def _board(data: Path, day: str, validate: Callable[[object], object]) -> dict:
    path = data / "boards" / "days" / day / "daily.json"
    board = _read(path, validate)
    if board["board_day"] != day:
        raise DataError(f"{path} holds the board day {board['board_day']}, and its folder is {day}")
    return board


def _read(path: Path, validate: Callable[[object], object]) -> dict:
    """The data file at `path`, once it matches its schema and is in a version the pages read."""
    value = _load(path)
    try:
        validate(value)
    except fastjsonschema.JsonSchemaValueException as error:
        raise DataError(f"{path} does not match its schema: {error.message}") from error
    version = value.get("schema_version") if isinstance(value, dict) else None
    if not isinstance(version, int) or version < SCHEMA_VERSION_NEEDED:
        raise DataError(
            f"{path} is in version {version} of the data contract, "
            f"and the pages need version {SCHEMA_VERSION_NEEDED} or later"
        )
    return value


def _validator(path: Path) -> Callable[[object], object]:
    """Compile the schema at `path`, which may refer only within itself.

    fastjsonschema turns a schema into Python and fetches any remote document a `$ref` resolves to. The
    schema arrives with the data, so a `$ref` that does not start with '#' is refused before compiling, and
    the compiler is given a handler for every kind of address that refuses to fetch it: a reference that
    starts with '#' still resolves to a remote document under some `$id`s.
    """
    schema = _load(path)
    outside = [ref for ref in _refs(schema) if not (isinstance(ref, str) and ref.startswith("#"))]
    if outside:
        raise DataError(f"{path} refers to {outside[0]!r}, outside itself. A schema may refer only within itself")
    try:
        return fastjsonschema.compile(schema, handlers=_NO_REMOTE_DOCUMENTS)
    except fastjsonschema.JsonSchemaDefinitionException as error:
        raise DataError(f"{path} is not a schema the build can use: {error}") from error


def _refs(node: object) -> Iterator[object]:
    """Every `$ref` in a schema, wherever it is."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref":
                yield value
            yield from _refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _refs(item)


def _refuse(address: str) -> NoReturn:
    raise fastjsonschema.JsonSchemaDefinitionException(f"it refers to {address}, which is outside itself")


class _EveryScheme(dict):
    """fastjsonschema's `handlers`: it asks `scheme in handlers`, then calls `handlers[scheme](address)`, and
    fetches with urllib when no handler is given. This holds every scheme, and each one refuses."""

    def __contains__(self, scheme):
        return True

    def __getitem__(self, scheme):
        return _refuse


_NO_REMOTE_DOCUMENTS = _EveryScheme()


def _load(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise DataError(f"{path} cannot be read as JSON: {error}") from error
