"""What the build writes for crawlers and feed readers: the sitemap, robots.txt (#170), and the Atom feed (#243)."""

import re
from xml.sax.saxutils import escape

from sitebuild.formatting import gained, long_date, per_day, repositories
from sitebuild.paths import BASELINE, DAYS, FOR_AGENTS, HOW_IT_WORKS, SEARCH, SITE, address, day_address

SITEMAP_SCHEMA = "http://www.sitemaps.org/schemas/sitemap/0.9"
ATOM_SCHEMA = "http://www.w3.org/2005/Atom"
FEED_DAYS = 30
"""How many newest board days `/feed.xml` lists (#243)."""
FEED_TOP = 10
"""How many leading repositories each board day's Atom entry summarises."""
XML_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
"""Characters disallowed by XML 1.0, stripped from owner-written text before XML escaping (P5, #243)."""


def xml_text(text: str) -> str:
    """`text` with XML 1.0 illegal characters removed and markup characters escaped."""
    return escape(XML_ILLEGAL.sub("", text))


def sitemap(boards: list[dict]) -> str:
    """The sitemap of sitemaps.org's schema 0.9, with one entry for each page that holds a board or tells of the
    site, by its whole address with the closing slash, since that is the address the site answers 200 at.

    A board day's entry carries the time its file was published, which is when its page last changed. The root,
    History, and Baseline show the newest board, so they carry its time. Search, How it works, and For agents carry
    none: their text changes only with the site, and a `lastmod` that the build made up would tell a crawler nothing
    true (#170, #242). `boards` is newest first, as the data's index lists them.
    """
    newest = boards[0]["published_at"]
    entries = [(address(""), newest), (address(DAYS), newest), (address(BASELINE), newest)]
    entries += [(address(SEARCH), None), (address(HOW_IT_WORKS), None), (address(FOR_AGENTS), None)]
    entries += [(day_address(board["board_day"]), board["published_at"]) for board in boards]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<urlset xmlns="{SITEMAP_SCHEMA}">',
    ]
    for path, modified in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(SITE + path)}</loc>")
        if modified:
            lines.append(f"    <lastmod>{escape(modified)}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def atom_feed(boards: list[dict]) -> str:
    """A static Atom 1.0 feed at `/feed.xml` of the newest `FEED_DAYS` board days (#243).

    Every figure is worded by `sitebuild.formatting` so the feed agrees with the boards (P20), and owner-written
    text is stripped of XML 1.0 illegal control characters and XML-escaped (P5). `boards` is newest first.
    """
    newest = boards[0]["published_at"]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<feed xmlns="{ATOM_SCHEMA}">',
        f"  <id>{escape(SITE + '/')}</id>",
        "  <title>Rising Repos</title>",
        "  <subtitle>GitHub repositories gaining stars faster than their own pace predicts, "
        "on a new board each day.</subtitle>",
        f'  <link href="{escape(SITE + "/")}" rel="alternate" type="text/html"/>',
        f'  <link href="{escape(SITE + "/feed.xml")}" rel="self" type="application/atom+xml"/>',
        f"  <updated>{escape(newest)}</updated>",
    ]
    for board in boards[:FEED_DAYS]:
        day = board["board_day"]
        rows = board["rows"]
        url = SITE + day_address(day)
        gains = bool(rows) and "gained_1_day" in rows[0]
        explained = bool(rows) and "score" in rows[0]
        summary_lines = [f"{repositories(len(rows))} on the board for {long_date(day)}."]
        if rows:
            summary_lines.append("")
            for row in rows[:FEED_TOP]:
                parts = [f"{row['rank']}. {row['full_name']}"]
                if explained:
                    parts.append(f"{gained(row)} on the day" if gains else f"{per_day(row)} a day")
                parts.append(f"{row['stars']:,} stars")
                if row.get("language"):
                    parts.append(row["language"])
                summary_lines.append(" · ".join(parts))
        summary = "\n".join(summary_lines)
        lines += [
            "  <entry>",
            f"    <id>{escape(url)}</id>",
            f"    <title>{xml_text(f'Rising Repos: {long_date(day)} ({repositories(len(rows))})')}</title>",
            f'    <link href="{escape(url)}" rel="alternate" type="text/html"/>',
            f"    <updated>{escape(board['published_at'])}</updated>",
            f'    <summary type="text">{xml_text(summary)}</summary>',
            "  </entry>",
        ]
    lines.append("</feed>")
    return "\n".join(lines) + "\n"


def robots(*, noindex: bool) -> str:
    """The site's robots.txt. Cloudflare Pages serves a managed one, with a signal the owner did not choose, for a
    site that has none, so the site states its own (#170).

    A crawler may fetch every page, and two signals say what it may do with the text: it may build a search index
    (`search=yes`) and may answer from the pages (`ai-input=yes`). Neither says anything of training, so the file
    makes no claim there. The sitemap is named.

    A build with `noindex`, the preview's, invites no crawler and names no sitemap, as its pages ask search engines
    not to index them.
    """
    if noindex:
        return "User-agent: *\nDisallow: /\n"
    return f"User-agent: *\nContent-Signal: search=yes, ai-input=yes\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n"
