"""The list of every repository that has been on a board, `/repos.tsv`, for the query service (#177).

The service is a Rust Worker in another repository, which fetches this file when it starts and again every few minutes,
so that a new board day reaches its search with no deploy of the Worker (#175). The format is therefore a contract
between the two repositories: a change to a field, its order, or the opening lines raises `LIST_FORMAT`, and the Worker
is changed with it.
"""

from sitebuild.agent_copy import one_line

LIST_FORMAT = 1
"""The version of the list's layout, which its first line states."""

FIELDS = ("full_name", "language", "stars", "last_board_day", "last_rank", "history", "description")
"""The fields of each line, in order: the repository's name, language, and stars on the newest board it was on, that
board day, its rank that day, every board day it was on with its rank there (`2026-11-25:182,2026-11-26:221`), and its
description, last."""


def repo_list(boards: list[dict]) -> str:
    """The list's text for `boards`, newest first: its format line, its field line, and one line for each GitHub id on
    any board, which a rename or a transfer keeps, under the name, language, and stars of the newest board that listed
    it. A tab or a line break in a name, a language, or a description is made a space (P5). Walking oldest first, the
    last board a repository is on is the one whose figures are kept, and its history is already in order."""
    found: dict[int, dict] = {}
    for board in reversed(boards):
        for row in board["rows"]:
            found.setdefault(row["github_id"], {"days": []})["days"].append(f"{board['board_day']}:{row['rank']}")
            found[row["github_id"]].update(row=row, day=board["board_day"])
    lines = [f"# rising-repos list, format {LIST_FORMAT}", "\t".join(FIELDS)]
    for seen in found.values():
        row = seen["row"]
        lines.append(
            "\t".join(
                one_line(str(field))
                for field in (
                    row["full_name"],
                    row["language"] or "",
                    row["stars"],
                    seen["day"],
                    row["rank"],
                    ",".join(seen["days"]),
                    row["description"] or "",
                )
            )
        )
    return "\n".join(lines) + "\n"
