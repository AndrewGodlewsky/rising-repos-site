"""Measure a compact list of every repository ever on a board, and its splits.

Usage: uv run --locked python -I measure.py <site-data/boards/days> <output directory>

It writes the compact list (all.tsv), each split (by language, recency, and
star band) and a SQLite file (repos.db) into the output directory, prints a
JSON report of sizes and timings, and shows what the "pdf" keyword finds.
The output directory is not committed. Sizes are bytes of UTF-8; a rough token
count is bytes divided by 4. Timings are local, a proxy for Cloudflare's.
"""

import datetime
import glob
import gzip
import json
import os
import re
import sqlite3
import sys
import time
from collections import defaultdict

days_dir, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

# One record per repository, from its newest board day. github_id is the
# identity, since a repository can be renamed.
repos = {}
first = {}
count = defaultdict(int)
board_days = sorted(glob.glob(os.path.join(days_dir, "*", "daily.json")))
latest_bands = None
for path in board_days:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    latest_bands = d["star_bands"]
    for r in d["rows"]:
        k = r["github_id"]
        first.setdefault(k, d["board_day"])
        count[k] += 1
        repos[k] = dict(r, last_day=d["board_day"])
newest = datetime.date.fromisoformat(max(r["last_day"] for r in repos.values()))


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def band(stars):
    for i, b in enumerate(latest_bands):
        if b["most_stars"] is None or stars <= b["most_stars"]:
            return i
    return len(latest_bands) - 1


def line(r, desc_max=None):
    desc = clean(r["description"])
    if desc_max and len(desc) > desc_max:
        desc = desc[: desc_max - 1] + "…"
    return "\t".join(
        [r["full_name"], r["language"] or "", str(r["stars"]), r["last_day"], str(count[r["github_id"]]), desc]
    )


def size(lines):
    b = ("\n".join(lines) + "\n").encode("utf-8")
    return len(b), len(gzip.compress(b, 6))


rows = sorted(repos.values(), key=lambda r: (r["last_day"], r["stars"]), reverse=True)
report = {
    "board_days": len(board_days),
    "repositories": len(rows),
    "with_description": sum(1 for r in rows if clean(r["description"])),
    "mean_description_chars": round(sum(len(clean(r["description"])) for r in rows) / len(rows), 1),
}

variants = {
    "full description": None,
    "description cut to 100 characters": 100,
    "no description (name, language, stars, last day, count)": 0,
}
report["flat"] = {}
for name, dm in variants.items():
    if dm == 0:
        ls = [line(dict(r, description=""), None) for r in rows]
    else:
        ls = [line(r, dm) for r in rows]
    report["flat"][name] = size(ls)
    if dm is None:
        with open(os.path.join(out, "all.tsv"), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(ls) + "\n")

# Splits use the full description.
splits = {
    "language": defaultdict(list),
    "recency (days since last on a board)": defaultdict(list),
    "star band (stars on last board day)": defaultdict(list),
}
labels = [f"{b['least_stars']}-{b['most_stars']}" if b["most_stars"] else f"{b['least_stars']}+" for b in latest_bands]
lang_counts = defaultdict(int)
for r in rows:
    lang_counts[r["language"] or "(none)"] += 1
for r in rows:
    ln = line(r)
    lang = r["language"] or "(none)"
    splits["language"][lang].append(ln)
    age = (newest - datetime.date.fromisoformat(r["last_day"])).days
    rb = "0-7" if age <= 7 else "8-30" if age <= 30 else "31-90" if age <= 90 else "91+"
    splits["recency (days since last on a board)"][rb].append(ln)
    splits["star band (stars on last board day)"][labels[band(r["stars"])]].append(ln)

report["splits"] = {}
for sname, groups in splits.items():
    sizes = {k: size(v) + (len(v),) for k, v in groups.items()}
    big = max(sizes.items(), key=lambda kv: kv[1][0])
    # Language split with the small languages merged into one file.
    entry = {
        "files": len(groups),
        "total_bytes": sum(s[0] for s in sizes.values()),
        "largest": [big[0], big[1][0], big[1][1], big[1][2]],
        "sizes": {k: list(v) for k, v in sorted(sizes.items(), key=lambda kv: -kv[1][0])[:12]},
    }
    if sname == "language":
        entry["languages_with_over_100_repositories"] = sum(1 for n in lang_counts.values() if n > 100)
        entry["languages_with_under_20_repositories"] = sum(1 for n in lang_counts.values() if n < 20)
        entry["median_file_bytes"] = sorted(s[0] for s in sizes.values())[len(sizes) // 2]
    report["splits"][sname] = entry
    d = os.path.join(out, sname.split(" ")[0])
    os.makedirs(d, exist_ok=True)
    for k, v in groups.items():
        safe = re.sub(r"[^A-Za-z0-9+_-]", "_", k)
        with open(os.path.join(d, safe + ".tsv"), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(v) + "\n")

# The "pdf" question, by a simple keyword match on name and description.
pdf = re.compile(r"pdf", re.I)
hits = [r for r in rows if pdf.search(r["full_name"] + " " + (r["description"] or ""))]
pdf_word = re.compile(r"\bpdfs?\b", re.I)
hits_word = [r for r in rows if pdf_word.search(r["full_name"] + " " + (r["description"] or ""))]
parse = re.compile(r"pars|extract|convert|ocr|read", re.I)
hits_parse = [r for r in hits if parse.search(r["description"] or "")]
report["pdf"] = {
    "substring_pdf": len(hits),
    "word_pdf": len(hits_word),
    "pdf_and_parse_extract_convert_ocr_read": len(hits_parse),
    "hit_lines_bytes": size([line(r) for r in hits])[0],
    "hit_lines_parse_bytes": size([line(r) for r in hits_parse])[0],
    "by_language_of_hits": dict(
        sorted(
            (
                (k, sum(1 for r in hits if (r["language"] or "(none)") == k))
                for k in {r["language"] or "(none)" for r in hits}
            ),
            key=lambda kv: -kv[1],
        )[:8]
    ),
    "hits_in_languages": len({r["language"] for r in hits}),
}
with open(os.path.join(out, "pdf-hits.tsv"), "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(line(r) for r in hits_parse) + "\n")
report["pdf"]["top_parse_hits"] = [
    [r["full_name"], r["language"], r["stars"], r["last_day"], clean(r["description"])[:90]]
    for r in sorted(hits_parse, key=lambda r: -r["stars"])[:10]
]
report["pdf"]["newest_parse_hits"] = [
    [r["full_name"], r["last_day"]] for r in sorted(hits_parse, key=lambda r: r["last_day"], reverse=True)[:5]
]

# SQLite FTS5, as D1 would hold it.
db_path = os.path.join(out, "repos.db")
if os.path.exists(db_path):
    os.remove(db_path)
con = sqlite3.connect(db_path)
con.execute(
    "create virtual table repo using fts5(full_name, description, language unindexed, stars unindexed, "
    "last_day unindexed, tokenize='unicode61')"
)
con.executemany(
    "insert into repo values (?,?,?,?,?)",
    [(r["full_name"], clean(r["description"]), r["language"] or "", r["stars"], r["last_day"]) for r in rows],
)
con.commit()
con.execute("insert into repo(repo) values('optimize')")
con.commit()
con.execute("vacuum")
con.close()
report["sqlite"] = {
    "fts5_db_bytes": os.path.getsize(db_path),
    "fts5_db_gzip_bytes": len(gzip.compress(open(db_path, "rb").read(), 6)),
}
con = sqlite3.connect(db_path)


def timeit(fn, n=200):
    fn()
    t = []
    for _ in range(n):
        s = time.perf_counter()
        fn()
        t.append((time.perf_counter() - s) * 1000)
    t.sort()
    return {"median_ms": round(t[n // 2], 3), "p95_ms": round(t[int(n * 0.95)], 3)}


queries = {
    "pdf (prefix)": "pdf*",
    "pdf AND (parse OR parser OR parsing OR extract*)": "pdf* AND (pars* OR extract*)",
    "pdf OR document (two terms)": "pdf* OR document*",
}
report["sqlite"]["timings"] = {}
report["sqlite"]["rows_matched"] = {}
for name, q in queries.items():
    sql = "select full_name, language, stars, last_day, description from repo where repo match ? order by rank limit 20"
    report["sqlite"]["timings"][name] = timeit(lambda sql=sql, q=q: con.execute(sql, (q,)).fetchall())
    report["sqlite"]["rows_matched"][name] = con.execute(
        "select count(*) from repo where repo match ?", (q,)
    ).fetchone()[0]
report["sqlite"]["timings"]["first call, cold connection (single run)"] = None
con.close()
s = time.perf_counter()
c2 = sqlite3.connect(db_path)
c2.execute("select full_name from repo where repo match 'pdf*' order by rank limit 20").fetchall()
report["sqlite"]["timings"]["first call, cold connection (single run)"] = round((time.perf_counter() - s) * 1000, 3)
# Pages of a plain table scan, a proxy for rows read when FTS is not used.
report["sqlite"]["table_rows"] = c2.execute("select count(*) from repo").fetchone()[0]
c2.close()

print(json.dumps(report, indent=1, ensure_ascii=False))
