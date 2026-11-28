"""A throwaway prototype of a card view for a board's rows: three designs, for the owner to click through and choose.

PROTOTYPE ONLY. Nothing here is built, deployed, or run by a check. It builds the site from site-data/ into a folder
of the system's temporary directory, copies the root page to /cards-prototype/ with its Content-Security-Policy taken
out and the prototype's stylesheet and script added, and serves that folder on this machine alone. The bar at the foot
of the page, or the left and right arrow keys, switch between the designs, and each design's own switch turns the
board between its list and its cards.

Every design lays out the rows the page already holds, by the stylesheet, and adds no markup to a row, so that any of
them fits the page's size limit. The one exception is design C's copy of each row's reason line, which the script
makes here and which the real page would show from the markup it already has.

Run it from the repository's root, then open the address it prints:

    uv run --locked python docs/research/2026-11-28-card-view-prototype/make_card_view_prototype.py
"""

import functools
import http.server
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path(tempfile.gettempdir()) / "rising-repos-cards-prototype"


def build() -> None:
    """Build the whole site, so that the prototype's links and an opened row's history.json resolve."""
    if OUT.exists():
        shutil.rmtree(OUT)
    subprocess.run([sys.executable, "-m", "sitebuild", str(OUT)], check=True)


def prototype_page() -> bytes:
    """The root page with the prototype's stylesheet and script, read afresh on each request so an edit shows on a
    reload."""
    page = (OUT / "index.html").read_text(encoding="utf-8")
    page = re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>', "", page, count=1)
    css = (HERE / "prototype.css").read_text(encoding="utf-8")
    js = (HERE / "prototype.js").read_text(encoding="utf-8")
    page = page.replace("</head>", f"<style>{css}</style>\n</head>", 1)
    end = page.rfind("</body>")
    script = f"<script>{js}</script>\n"
    page = page[:end] + script + page[end:] if end >= 0 else page + script
    return page.encode("utf-8")


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.split("?")[0] in ("/cards-prototype", "/cards-prototype/", "/cards-prototype/index.html"):
            body = prototype_page()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, *args: object) -> None:
        pass


def serve() -> None:
    handler = functools.partial(Handler, directory=str(OUT))
    for port in range(8000, 8011):
        try:
            server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
        except OSError:
            continue
        print(f"Serving the prototype at http://127.0.0.1:{port}/cards-prototype/ (Ctrl+C stops it)", flush=True)
        server.serve_forever()
    sys.exit("No port from 8000 to 8010 was free.")


if __name__ == "__main__":
    build()
    serve()
