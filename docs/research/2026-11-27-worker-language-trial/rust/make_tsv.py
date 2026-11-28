"""PROTOTYPE, throw away: write repos.tsv, every repository ever on a board, one line each, for the Rust and
JavaScript trial Workers (#174). The same list as the Python trial's.

Usage: python make_tsv.py <site-data/boards/days> <out .tsv>"""

import json
import sys
from pathlib import Path

latest = {}
for path in sorted(Path(sys.argv[1]).glob("*/daily.json")):
    day = path.parent.name
    for row in json.loads(path.read_text(encoding="utf-8"))["rows"]:
        latest[row["github_id"]] = (
            row["full_name"],
            row.get("language") or "",
            row["stars"],
            day,
            row["rank"],
            (row.get("description") or "").replace("\t", " ").replace("\n", " "),
        )
text = "\n".join("\t".join(str(field) for field in record) for record in latest.values())
Path(sys.argv[2]).write_text(text, encoding="utf-8", newline="\n")
print(f"{len(latest)} repositories, {len(text.encode()):,} bytes")
