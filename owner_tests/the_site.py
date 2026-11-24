"""The site the owner's tests are run against, and the one browser they drive it with.

With nothing set, the site is built here: the made-up boards of `made_up` are written to a temporary folder, the
build's public command makes the pages from them, and a server on 127.0.0.1 hands them out as the site's host does.
With the environment variable SITE set to an address, such as https://risingrepos.com, nothing is built, and the
browser reads that site instead.

Either way there is one site and one browser for the whole run, opened when the first scenario asks and closed when
Python exits, so that the suite can be run whole, by one file, or by one test.
"""

import atexit
import contextlib
import os
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import Browser, sync_playwright

from owner_tests import made_up

LIVE = os.environ.get("SITE", "").strip().rstrip("/")
"""The address of the site to read, from the environment variable SITE, or nothing when the site is built here."""


def build(out: Path, data: Path) -> subprocess.CompletedProcess:
    """Run `python -m sitebuild <out> --data <data>` from the repository, as anyone who builds the site does. The
    owner's tests reach the generator through this command alone, so that they hold whatever is behind it."""
    return subprocess.run(
        [sys.executable, "-m", "sitebuild", str(out), "--data", str(data)],
        cwd=made_up.ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


def built(folder: Path, boards: list[dict]) -> Path:
    """The pages built from `boards`, in a new folder under `folder`, which holds their data beside them."""
    made_up.write(folder / "site-data", boards)
    result = build(folder / "dist", folder / "site-data")
    if result.returncode != 0:
        raise RuntimeError(f"the build of the made-up boards failed: {result.stderr}")
    return folder / "dist"


class _Pages(SimpleHTTPRequestHandler):
    """Hands out the built pages as the site's host does: a folder's index.html at the folder's address, and the
    built 404.html, with the status 404, at an address that holds no page."""

    def send_error(self, code, message=None, explain=None):
        if code != 404:
            super().send_error(code, message, explain)
            return
        page = (Path(self.directory) / "404.html").read_bytes()
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(page)

    def list_directory(self, path):
        """Nothing: a folder with no index.html holds no page, and its address is answered as any other that holds
        none."""
        self.send_error(404)

    def log_message(self, format, *args):
        """Nothing: a line for each request would bury the tests' own report."""


@dataclass(frozen=True)
class Site:
    """Where the site is, the browser that reads it, and, for a site built here, the boards it was built from,
    newest first, and the folder its pages are in. A site that was not built here has neither."""

    address: str
    browser: Browser
    boards: list[dict] | None = None
    pages: Path | None = None


_closing = contextlib.ExitStack()
_site: Site | None = None


def opened() -> Site:
    """The site and the browser, opened on the first call and shared by every scenario after it."""
    global _site
    if _site is None:
        atexit.register(_closing.close)
        _site = _open()
    return _site


def _open() -> Site:
    # Chrome is the one the machine already has, so that no browser is downloaded.
    playwright = sync_playwright().start()
    _closing.callback(playwright.stop)
    browser = playwright.chromium.launch(channel="chrome", headless=True)
    _closing.callback(browser.close)
    if LIVE:
        return Site(LIVE, browser)
    folder = Path(_closing.enter_context(tempfile.TemporaryDirectory()))
    boards = made_up.boards()
    pages = built(folder, boards)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Pages, directory=str(pages)))
    _closing.callback(server.server_close)
    _closing.callback(server.shutdown)
    # A daemon thread, so that Python does not wait for it before it runs what closes the server.
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return Site(f"http://127.0.0.1:{server.server_port}", browser, boards, pages)
