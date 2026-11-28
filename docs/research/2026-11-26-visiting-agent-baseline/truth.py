"""The right answers to the baseline's five tasks, from the data files, so that a visiting agent's answer can be scored.

Usage: python truth.py <site-data/boards/days folder> <board day> <repository for the history task>
"""

import json
import re
import sys
from pathlib import Path


def main(days_dir, board_day, repository):
    days = Path(days_dir)
    today = json.loads((days / board_day / "daily.json").read_text(encoding="utf-8"))
    rows = today["rows"]
    answers = {"board_day": board_day, "rows": len(rows)}

    # 1. Today's top five rising repositories written in Python.
    answers["top_python"] = [(row["rank"], row["full_name"]) for row in rows if row.get("language") == "Python"][:5]

    # 2. Rising repositories that work with PDF files, by name or description.
    answers["pdf"] = [
        (row["rank"], row["full_name"]) for row in rows if re.search("pdf", row["full_name"] + " " + (row.get("description") or ""), re.I)
    ]

    # 3. What New means is the page's own sentence, which the build writes; it is checked against the live page.
    answers["new_means_starts"] = "New means under a name on none of the boards before this one"

    # 4. A repository's earlier boards: how many, the first, and its best rank.
    earlier = []
    for path in sorted(days.glob("*/daily.json")):
        if path.parent.name >= board_day:
            continue
        for row in json.loads(path.read_text(encoding="utf-8"))["rows"]:
            if row["full_name"] == repository:
                earlier.append((path.parent.name, row["rank"]))
    answers["history"] = {
        "repository": repository,
        "earlier_boards": len(earlier),
        "first": earlier[0][0] if earlier else None,
        "best_rank": min((rank for _, rank in earlier), default=None),
    }

    # 5. The repositories ranked 280 to 285.
    answers["ranks_280_285"] = [(row["rank"], row["full_name"]) for row in rows if 280 <= row["rank"] <= 285]

    print(json.dumps(answers, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:4])
