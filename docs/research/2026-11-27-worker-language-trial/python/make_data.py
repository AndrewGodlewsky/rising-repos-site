"""PROTOTYPE, throw away: write src/repos_data.py, the compact list of every repository that has been on a board, as one
Python string the Worker parses when it starts. Usage: python make_data.py <site-data/boards/days> <out .py>"""

import json
import sys
from pathlib import Path

days = Path(sys.argv[1])
latest = {}
for path in sorted(days.glob("*/daily.json")):
    day = path.parent.name
    for row in json.loads(path.read_text(encoding="utf-8"))["rows"]:
        latest[row["github_id"]] = (row["full_name"], row.get("language") or "", row["stars"], day, row["rank"], (row.get("description") or "").replace("\t", " ").replace("\n", " "))
lines = ["\t".join(str(field) for field in record) for record in latest.values()]
text = "\n".join(lines)
Path(sys.argv[2]).write_text("DATA = " + repr(text) + "\n", encoding="utf-8")
print(f"{len(lines)} repositories, {len(text.encode()):,} bytes of list")
