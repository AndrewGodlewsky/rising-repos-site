"""What a visiting agent's reading window holds of the live site, measured without an agent.

Fetches the live pages, turns each into text the way a web-reading tool does (the page's styles, scripts, and head
dropped, each block on its own line), and checks which answers fall inside the two reading limits Claude Code
publishes: 100,000 characters for WebFetch and about 48,000 for its web-fetch subagent. The conversion is an
approximation of a real tool's, which no vendor publishes.

Usage: python measure_window.py <output.json>
"""

import html
import json
import re
import sys
import urllib.request

SITE = "https://risingrepos.com"
LIMITS = {"webfetch": 100_000, "web_fetch_subagent": 48_000}
BLOCK = re.compile(r"</?(p|div|li|tr|h[1-6]|section|header|footer|main|nav|table|tbody|thead|details|summary|dt|dd|br)\b[^>]*>", re.I)


def fetch(path):
    request = urllib.request.Request(SITE + path, headers={"User-Agent": "rising-repos-site baseline"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def as_text(page):
    body = re.sub(r"<head>.*?</head>", "", page, flags=re.S | re.I)
    body = re.sub(r"<(style|script)\b[^>]*>.*?</\1>", "", body, flags=re.S | re.I)
    body = BLOCK.sub("\n", body)
    body = re.sub(r"<[^>]+>", " ", body)
    body = html.unescape(body)
    lines = [" ".join(line.split()) for line in body.split("\n")]
    return "\n".join(line for line in lines if line)


def rows_of(page):
    """Each row of the board, as the markup gives it: rank, name, language attribute, and the row's own text."""
    rows = []
    for match in re.finditer(r"<tr role=row data-o=\d+([^>]*)>(.*?)</tr>", page, flags=re.S):
        attributes, inner = match.group(1), match.group(2)
        language = re.search(r'data-l=(?:"([^"]*)"|([^\s>]+))', attributes)
        name = re.search(r'href="https://github\.com/([^"]+)"', inner)
        rank = re.search(r'<td class="?rk[^>]*>(\d+)</td>', inner)
        rows.append(
            {
                "rank": int(rank.group(1)) if rank else None,
                "name": name.group(1) if name else None,
                "language": (language.group(1) or language.group(2)) if language else None,
                "text": as_text(inner),
            }
        )
    return rows


def in_window(row, window):
    """A row is in the window when the text a reader gets of it, "More on owner/name", is."""
    return bool(row["name"]) and f"More on {row['name']}" in window


def main(out):
    root = fetch("/")
    text = as_text(root)
    rows = rows_of(root)
    report = {"board": re.search(r"<title>([^<]*)", root).group(1), "page_bytes": len(root.encode()), "text_characters": len(text), "rows": len(rows)}

    for name, limit in LIMITS.items():
        window = text[:limit]
        seen = [row for row in rows if in_window(row, window)]
        report[name] = {"limit": limit, "rows_in_window": len(seen), "rows_cut_off": len(rows) - len(seen), "last_rank_in_window": max((row["rank"] or 0 for row in seen), default=0)}

    # A rising repository in one language: is a row's language anywhere in the text an agent reads?
    shown = sum(1 for row in rows if row["language"] and row["language"] in row["text"])
    report["language_shown_in_row_text"] = {"rows_with_a_language": sum(1 for row in rows if row["language"]), "rows_whose_text_names_it": shown}

    # A rising repository that does something: the rows whose name or description mention PDF.
    pdf = [row for row in rows if re.search("pdf", row["text"], re.I)]
    report["pdf_rows"] = {name: sum(1 for row in pdf if in_window(row, text[:limit])) for name, limit in LIMITS.items()}
    report["pdf_rows"]["on_the_board"] = len(pdf)

    # What New means: where the page defines it.
    at = text.find("New means")
    if at < 0:
        at = next((m.start() for m in re.finditer(r"\bNew\b[^.\n]{0,40}\bfirst\b", text)), -1)
    report["new_is_defined_at_character"] = at
    report["new_definition_in_window"] = {name: 0 <= at < limit for name, limit in LIMITS.items()}

    # How a board is ranked: the page that says so, whole within one read?
    how = as_text(fetch("/how-it-works/"))
    report["how_it_works_text_characters"] = len(how)

    # A repository's place on earlier boards: what the root's text says of it, and where the rest lives.
    report["history_in_page_text"] = bool(re.search(r"on \d+ of the last \d+ boards|boards? before", text))
    days = as_text(fetch("/days/"))
    report["history_page_text_characters"] = len(days)

    json.dump(report, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(report, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
