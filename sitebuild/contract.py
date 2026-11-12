"""Reading the data files that RisingRepos publishes into site-data/, as its data contract defines them.

The contract is RisingRepos's src/risingrepos/publishing/contract/README.md. Each file is checked against the
schema that is shipped with it, in site-data/contract/, before anything is built from it.
"""

import json
from pathlib import Path

import fastjsonschema

SCHEMA_VERSION_NEEDED = 1
"""The lowest `schema_version` the pages need. A file below it fails the build."""


class DataError(Exception):
    """A data file or a schema the pages cannot be built from. The message names the file."""


def latest_board(data: Path) -> dict:
    """The daily board of the latest board day: the first in the index, read and checked with the index."""
    index = _read(data / "boards" / "index.json", _validator(data / "contract" / "index.schema.json"))
    day = index["board_days"][0]["board_day"]
    path = data / "boards" / "days" / day / "daily.json"
    board = _read(path, _validator(data / "contract" / "daily.schema.json"))
    if board["board_day"] != day:
        raise DataError(f"{path} holds the board day {board['board_day']}, and its folder is {day}")
    return board


def _read(path: Path, validate) -> dict:
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


def _validator(path: Path):
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


def _refs(node):
    """Every `$ref` in a schema, wherever it is."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref":
                yield value
            yield from _refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _refs(item)


def _refuse(address: str):
    raise fastjsonschema.JsonSchemaDefinitionException(f"it refers to {address}, which is outside itself")


class _EveryScheme(dict):
    """fastjsonschema's `handlers`: it asks `scheme in handlers`, then calls `handlers[scheme](address)`, and
    fetches with urllib when no handler is given. This holds every scheme, and each one refuses."""

    def __contains__(self, scheme):
        return True

    def __getitem__(self, scheme):
        return _refuse


_NO_REMOTE_DOCUMENTS = _EveryScheme()


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise DataError(f"{path} cannot be read as JSON: {error}") from error
