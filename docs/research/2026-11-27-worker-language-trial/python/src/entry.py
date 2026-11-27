"""PROTOTYPE, throw away: does a search over every repository ever on a board fit a Python Worker? (#174)"""

import re
from urllib.parse import parse_qs, urlparse

from repos_data import DATA
from workers import Response, WorkerEntrypoint

# Built once, when the Worker starts (and so in Cloudflare's memory snapshot): one tuple a repository, with a
# lower-cased copy of its name and description to match against.
ROWS = []
for line in DATA.split("\n"):
    name, language, stars, day, rank, description = line.split("\t")
    ROWS.append((name, language, int(stars), day, int(rank), description, (name + " " + description).lower()))
ROWS.sort(key=lambda row: (row[3], -row[4]), reverse=True)  # once, at start: newest board day first, then better rank
STARTED_WITH = len(ROWS)
CALLS = 0

def search(words, language, page):
    # The full scan, as the Rust and JavaScript trials do it, so that the three compare.
    hits = [row for row in ROWS if all(word in row[6] for word in words) and (not language or row[1].lower() == language)]
    start = (page - 1) * 20
    return len(hits), hits[start : start + 20]


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        global CALLS
        CALLS += 1
        query = parse_qs(urlparse(request.url).query)
        if "ping" in query:  # the baseline: the same request and reply, with no search
            return Response("pong\n", headers={"x-calls": str(CALLS), "x-rows": str(STARTED_WITH)})
        words = (query.get("q", [""])[0].lower())[:100].split()
        language = query.get("lang", [""])[0].lower()
        page = int(query.get("page", ["1"])[0])
        total, hits = search(words, language, page)
        lines = [f"{total} match; page {page}."]
        lines += [f"{row[0]} | {row[1] or 'no language'} | stars {row[2]} | last on {row[3]} at #{row[4]} | \"{row[5]}\"" for row in hits]
        return Response("\n".join(lines) + "\n", headers={"x-calls": str(CALLS), "x-rows": str(STARTED_WITH)})
