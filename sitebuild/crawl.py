"""What the build writes for a crawler: the sitemap and the site's own robots.txt (#170)."""

from xml.sax.saxutils import escape

from sitebuild.paths import BASELINE, DAYS, FOR_AGENTS, HOW_IT_WORKS, SITE, address, day_address

SITEMAP_SCHEMA = "http://www.sitemaps.org/schemas/sitemap/0.9"


def sitemap(boards: list[dict]) -> str:
    """The sitemap of sitemaps.org's schema 0.9, with one entry for each page that holds a board or tells of the
    site, by its whole address with the closing slash, since that is the address the site answers 200 at.

    A board day's entry carries the time its file was published, which is when its page last changed. The root,
    History, and Baseline show the newest board, so they carry its time. How it works carries none: its text changes
    only with the site, and a `lastmod` that the build made up would tell a crawler nothing true (#170).
    `boards` is newest first, as the data's index lists them.
    """
    newest = boards[0]["published_at"]
    entries = [(address(""), newest), (address(DAYS), newest), (address(BASELINE), newest)]
    entries += [(address(HOW_IT_WORKS), None), (address(FOR_AGENTS), None)]
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
