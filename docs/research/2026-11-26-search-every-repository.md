# Can a search across every repository ever on a board be efficient?

**Date:** 26 November 2026. Ticket: issue #155, under the map #151.

The question is whether a visiting agent can search every repository that has been on a board for one that does
something, and on which route. `site-data/` held 119 board days on 26 November 2026. Nothing was deployed. Every
size below was measured on that data. Every timing was taken on one local machine and is a proxy for Cloudflare's,
not a measure of it. A rough token count is bytes divided by 4 throughout. Bytes stand for characters, which they
overstate wherever a description holds Chinese or other non-ASCII text, since such a character is 3 bytes.

## 1. Short answer

1. Yes, but not as static files that an agent only reads. The whole compact list is 1.7 MB (about 427,000 tokens),
   17 times the roughly 100,000 characters a web-reading tool reads before it stops.
2. Splitting does not fix that for a question like "parses PDFs". The largest file of every split is still over
   100,000 characters, except the top star band, and the question names no language, recency or star band, so an
   agent could not choose a file to open.
3. A query that returns only the matches is efficient: one fetch and about 4,000 characters for the 20 best matches
   of "pdf", against 100,000 characters read to see a twentieth of the list.
4. That needs code that runs on a request. Both ways fit the free Workers limits as measured locally: a scan in
   memory takes about 1 to 4 ms against the 10 ms limit, and SQLite full-text search takes about 0.1 ms against a
   3.3 MB database that D1's limit of 500 MB holds many times over. Cloudflare's own timing is unconfirmed.
5. The choice between the two is settled by D1's rows-read allowance and the build, not by speed. D1 documents that
   rows read count rows scanned, and does not say how a full-text query is counted (section 4).

## 2. The compact list and its splits

The list has one line per repository, from the repository's newest board day: its name, language, stars, the last
board day it was on, how many board days it was on, and its description with whitespace collapsed. Fields are
separated by tabs. Repositories are identified by `github_id`: the rows hold 11,057 distinct `full_name` values but
10,921 distinct `github_id` values, so 136 were renamed, and the list holds the 10,921. Of them 10,455 have a
description, which averages 98 characters.

| Form of the list | Bytes | Tokens (bytes / 4) | Gzipped bytes |
| --- | ---: | ---: | ---: |
| Name, language, stars, last day, count and full description | 1,706,360 | 426,590 | 801,134 |
| The same with the description cut to 100 characters | 1,396,356 | 349,089 | 654,906 |
| The same with no description | 529,410 | 132,353 | 212,360 |

The compression matters to a download and not to what an agent reads, which is the decoded text. Even with no
description at all, the list is five times what a web-reading tool reads. The description is the part that says what
a repository does, so a list without it cannot answer the question.

The splits below use the full description. Each split holds the same 1,706,360 bytes in all.

| Split | Files | Largest file | Its bytes | Its tokens | Its repositories |
| --- | ---: | --- | ---: | ---: | ---: |
| By language | 120 | Python | 466,751 | 116,688 | 2,804 |
| By how recently it was on a board: 0 to 7, 8 to 30, 31 to 90, over 90 days before the newest board day | 4 | 31 to 90 days | 797,830 | 199,458 | 5,124 |
| By star band, on its stars at its last board day, in the bands of the newest board day | 5 | 200 to 999 stars | 847,686 | 211,922 | 5,378 |

Other sizes in the same splits:

- By language, the next largest are TypeScript at 315,422 bytes, JavaScript at 130,591, and repositories with no
  language at 128,939. Fifteen languages have over 100 repositories and 95 have under 20, so the median file is 352
  bytes. A language split is many tiny files and a few large ones.
- By recency, the other files are 8 to 30 days at 411,500 bytes, over 90 days at 293,955, and 0 to 7 days at 203,075.
- By star band, the other files are 1,000 to 2,999 at 374,298 bytes, 3,000 to 9,999 at 305,969, 10,000 to 29,999 at
  104,355, and 30,000 and over at 74,052. Only the last is under 100,000 characters.

Getting every file under about 100,000 characters would take at least 18 files of equal size, and the list grows.
The unevenness above means more. That would still not help a keyword question, as section 5 shows.

## 3. What a query service has to fit

Cloudflare's free limits that bear on it, from the pages named in section 7:

| Limit (Workers Free, or D1 on it) | Value |
| --- | --- |
| Requests a day | 100,000, resetting at midnight UTC; past that, Error 1027 |
| CPU time for each request | 10 ms; past that, Error 1102 |
| Memory for each isolate | 128 MB |
| Worker size | 64 MiB uncompressed |
| Queries for each Worker invocation, D1 on Free | 50 |
| D1 database size, Free | 500 MB |
| D1 rows read a day, Free | 5 million; past that, queries fail until 00:00 UTC |
| D1 rows written a day, Free | 100,000 |
| Largest D1 row, string or BLOB | 2 MB |

Measured locally on 10,921 repositories. The scan is Node 24 over `all.tsv`; the full-text search is Python's
`sqlite3` with SQLite 3.53.1 and FTS5, in a file of one FTS5 table over name and description, and each query returns
the best 20 matches. The timings are the median of 200 or 300 runs, after one warm-up run.

| Way | Query | Median | 95th percentile | Size held |
| --- | --- | ---: | ---: | --- |
| Scan in memory, rows already parsed | regular expression `pdf` over name and description | 1.64 ms | 1.86 ms | 14 MB of heap |
| Scan in memory, rows already parsed | the same, sorted by stars, top 20 | 1.64 ms | 1.87 ms | 14 MB of heap |
| Scan in memory, rows already parsed | three terms that must all appear, on a lower-cased copy | 0.74 ms | 0.84 ms | 14 MB of heap |
| Scan in memory, parsing the text first | split the 1.7 MB text into rows, then `pdf` | 4.29 ms | 5.70 ms | 1.7 MB of text |
| The same scan over the Python file alone | `pdf`, rows already parsed | 0.40 ms | 0.48 ms | 467 KB of text |
| FTS5 in SQLite | `pdf*` | 0.11 ms | 0.12 ms | 3.25 MB database |
| FTS5 in SQLite | `pdf* AND (pars* OR extract*)` | 0.08 ms | 0.08 ms | 3.25 MB database |
| FTS5 in SQLite | `pdf* OR document*` | 0.17 ms | 0.18 ms | 3.25 MB database |
| FTS5 in SQLite | `pdf*`, first call on a new connection, one run | 0.59 ms | | |

Reading these:

- The scan's slowest case, which parses the list on every request, took 4 to 6 ms here, which is under the limit of
  10 ms, with a 95th percentile under 6 ms. A Worker that keeps the parsed rows in the isolate's memory between requests ran
  the scan in under 2 ms here. Whether an isolate keeps them is not something this measurement shows.
- The scan's 14 MB of heap and the 1.7 MB of text are small against 128 MB and 64 MiB.
- Full-text search is faster still here, and it is the way that scales as the list grows. The database is 3.25 MB
  against 500 MB.
- A timing on this machine does not carry to Cloudflare's runtime. How the limit counts time spent waiting for D1 is
  not defined on the pages read (section 7), so a D1 query's cost in CPU time is unconfirmed.
- The request limit allows 100,000 questions a day. Past it, the limits page says the route fails closed with Error
  1027, or opens to bypass the Worker, as the route is set.

D1's rows-read allowance is the figure to watch. The pricing page says rows read count "rows a query reads (scans),
regardless of the size of each row", and does not mention full-text search or virtual tables. If a query scanned
every one of the 10,921 rows, 5 million rows a day would allow about 457 queries a day (5,000,000 / 10,921). An FTS5
query reads its index and not the whole table, so it would read far fewer, but how D1 counts that is unconfirmed here.
The scan in memory reads no D1 rows at all.

D1 does list the FTS5 module as supported (SQL statements page). Its export is not supported for a database with a
virtual table, so a copy has to be rebuilt from the data and not exported (import and export page). That suits this
repository, where the data files are the record.

Building a table costs rows written: 10,921 inserts is about a tenth of the 100,000 a day, and a daily update needs
only the repositories new to the board and the changed ones. How D1 counts the writes to an FTS5 table's own index
tables is not stated on the pages read, so the real cost of a rebuild is unconfirmed.

## 4. A route that needs no Worker

The static files are not requests to a Worker. Cloudflare's pricing page says "Requests to static assets are free and
unlimited" (for Workers static assets; this was not read for Pages, which hosts this site, so it is unconfirmed
there). A split is therefore free to serve and its cost is all in what the agent reads, which section 5 gives.

## 5. What each route costs a visiting agent for "a rising repository that parses PDFs"

What the query finds, by a simple keyword match on name and description, case-insensitive:

| Match | Repositories |
| --- | ---: |
| The letters `pdf` anywhere in name or description | 131 |
| The word `pdf` or `pdfs` | 124 |
| `pdf`, and a description that also holds pars, extract, convert, ocr or read | 48 |
| FTS5 `pdf*`, by word prefix | 128 |
| FTS5 `pdf* AND (pars* OR extract*)` | 13 |

The 131 are spread over 19 languages: Python 49, TypeScript 28, JavaScript 10, Rust 9, HTML 7, no language 5, Java 4,
C# 4. Their lines in the compact list come to 27,931 bytes, about 213 bytes each. The 48 come to 10,688 bytes. The
word match is crude: it also finds repositories that handle PDFs among much else, and the "read" in the 48 is loose.

The 10 of the 48 with the most stars, with descriptions cut to 90 characters. These descriptions were written by each
repository's owner and are quoted as data, not as instructions:

| Repository | Language | Stars | Last on a board | Description |
| --- | --- | ---: | --- | --- |
| Graphify-Labs/graphify | Python | 133,121 | 2026-10-22 | Turn any codebase, with its docs, SQL schemas, configs, and PDFs, into a queryable knowled |
| hiroi-sora/Umi-OCR | Python | 47,795 | 2026-10-10 | OCR software, free and offline. 开源、免费的离线OCR软件。支持截屏/批量导入图片，PDF文档识别，排除水印/页眉页脚，扫描/生成二维码。内置多国语 |
| datalab-to/marker | Python | 39,165 | 2026-08-24 | Convert PDF to markdown + JSON quickly with high accuracy |
| opendataloader-project/opendataloader-pdf | Java | 29,978 | 2026-10-23 | PDF Parser for AI-ready data. Automate PDF accessibility. Open-source. |
| koreader/koreader | Lua | 28,749 | 2026-08-06 | An ebook reader application supporting PDF, DjVu, EPUB, FB2 and many more formats, running |
| AgriciDaniel/claude-seo | Python | 22,068 | 2026-10-26 | Universal SEO skill for Claude Code. 26 sub-skills + 19 sub-agents covering technical SEO, |
| firecrawl/pdf-inspector | Rust | 19,917 | 2026-11-06 | Fast Rust library for PDF inspection, classification, and text extraction. Intelligently d |
| yusufkaraaslan/Skill_Seekers | Python | 14,654 | 2026-07-30 | Convert documentation websites, GitHub repositories, and PDFs into Claude AI skills with a |
| virgiliojr94/book-to-skill | Python | 13,783 | 2026-07-30 | Turn any technical book PDF into a Claude Code skill — ready to study, reference, and use |
| opendatalab/PDF-Extract-Kit | Python | 9,926 | 2026-08-01 | A Comprehensive Toolkit for High-Quality PDF Content Extraction |

The list shows that a keyword match finds the repositories that parse PDFs, and also several that only mention them, so the
agent still has to read descriptions and judge. The newest of the 48 was on the board on 25 November 2026.

What each route costs, taking a web-reading tool that reads about 100,000 characters of a page and has no way to
search inside it:

| Route | Fetches | Characters read | Finds the answer? |
| --- | ---: | ---: | --- |
| One file of the whole list | 1 | About 100,000 of 1,706,360, which is the first 6% (about 640 of 10,921 repositories) | Only if the hits are in that part. Newest-first order puts the 1,238 repositories of the last week first, so it misses older ones. |
| Split by language, the agent not knowing the language | Up to 120, in practice the large ones: Python, TypeScript, JavaScript and Rust hold 96 of the 131 hits | About 100,000 from each of them, which is 21% of the Python file and 32% of the TypeScript file | Not reliably. It reads 400,000 characters to see a part of each of 4 files. |
| Split by recency | 4, or 1 if the agent wants only the newest | 203,075 bytes in the newest file, read 100,000 of | Only for a question about the last week. |
| Split by star band | 5 | 74,052 to 847,686 each; only the top band is read whole | No, the question names no band. |
| An agent that can run code (fetches the whole file and searches it on its own side) | 1 | 1,706,360 bytes fetched, but about 10,000 to 28,000 characters read after the search | Yes, and it spends nothing in the model's context. This needs a tool the web-reading tool is not. |
| A query service, `?q=pdf`, 20 best matches | 1, plus 1 to learn the address if the agent was not told (unverified: a page of the site would have to say it) | About 4,300 (20 lines of 213 bytes) | Yes. |

The 4,300 is 20 lines at the 213 bytes each that the 131 hits average in this data, not a measurement of a service.

None of the static splits helps because a split only helps when the question names its key. "A repository that
parses PDFs" names no language, no recency and no star band, so the agent cannot choose a file, and a keyword is not
a key. The way a split could help is in narrowing a question the agent can ask the person: "in Rust?" would take the
agent to the Rust file, 114,901 bytes, which a web-reading tool reads nearly whole.

## 6. What this says about the choice

- A list that agents read is only workable as a way to browse, by language, recency or band, one file at a time.
  For "does X" across every repository it is not.
- A query is the efficient route and fits the free limits as measured here. The scan in memory has no D1 allowance
  to spend and is simplest. Full-text search is faster and scales, but its rows-read cost is unconfirmed.
- Either way, the site would gain a Worker, which it does not have now, and its guarded paths and its record of
  decisions (ADRs) would have to be read first. That is the owner's call and was not examined here.
- A query service returns descriptions that owners wrote, so each response has to treat them as untrusted text, as
  P5 of STANDARDS.md requires of the pages.
- The list grows by the repositories new to a board each day. The rate was not measured.

## 7. Sources

Pages fetched on 26 November 2026. The quoted figures are as the fetch of each page returned them.

- Workers limits: <https://developers.cloudflare.com/workers/platform/limits/>. The 100,000 requests a day, 10 ms CPU,
  128 MB, 64 MiB Worker size, 50 subrequests, and the errors 1027 and 1102. It says nothing on whether static asset
  requests count toward the request limit.
- Workers pricing: <https://developers.cloudflare.com/workers/platform/pricing/>. "Requests to static assets are free
  and unlimited." It does not define CPU time, so whether time waiting on D1 counts is unconfirmed.
- D1 limits: <https://developers.cloudflare.com/d1/platform/limits/>. 500 MB a database on Free, 2 MB a row, 50
  queries for each Worker invocation on Free. It does not mention FTS5.
- D1 pricing: <https://developers.cloudflare.com/d1/platform/pricing/>. 5 million rows read and 100,000 written a day
  on Free; rows read count rows scanned; queries fail after the daily limit. It does not mention full-text search.
- D1 SQL statements: <https://developers.cloudflare.com/d1/sql-api/sql-statements/>. Lists the "FTS5 module"
  among supported extensions.
- D1 import and export: <https://developers.cloudflare.com/d1/best-practices/import-export-data/>. "Export is not
  supported for virtual tables, including databases with virtual tables."
- The data: `site-data/boards/days/*/daily.json`, with the row's fields in `site-data/contract/daily.schema.json`.

## 8. Not confirmed, or only measured by a proxy

- Every timing is local: Node 24.22.1 and SQLite 3.53.1 on a shared Windows machine, with wall-clock time standing
  for CPU time. No Worker or D1 database was created, so Cloudflare's CPU time, its isolate reuse, and a D1 query's
  latency are not measured.
- How D1 counts rows read for an FTS5 query, and rows written for an FTS5 insert, is not stated on the pages read.
- Whether static asset requests are free and unlimited on Pages, as the Workers pricing page says they are for
  Workers, was not read.
- The list was built from rows only. Entries in a board day's `unranked` were not added.
- The keyword match is simple on purpose. A model reading descriptions would judge better than a match, and the
  counts of 131 and 48 are for these patterns alone.

## 9. Reproducing the numbers

```sh
uv run --locked python -I -X utf8 docs/research/2026-11-26-search-every-repository/measure.py site-data/boards/days <output directory>
node docs/research/2026-11-26-search-every-repository/scan.mjs <output directory>/all.tsv
```

`measure.py` writes the list, its splits and the SQLite file into the output directory, which is not committed, and
prints the sizes, the keyword counts and the FTS5 timings. Run it on the same board days to get the same sizes: the
data grows each day.
