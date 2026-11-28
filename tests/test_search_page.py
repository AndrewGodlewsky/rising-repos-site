"""The archive search page (`/search/`) and on-demand earlier-boards expansion in opened rows (#242)."""

import json
import unittest
from datetime import date, timedelta

from helpers import BuildTest, read_json, write_json

from sitebuild import SEARCH
from sitework.layout import chrome, published, served


class TheSearchPage(BuildTest):
    def test_search_page_makes_no_api_request_on_load_and_renders_results_safely_on_submit(self):
        """#242, ADR 0010: /search/ sends zero /api/ requests on initial load, fetches /api/search?format=json only on
        explicit submit, escapes hostile owner-written fields via textContent (P5, P6), paginates, and degrades
        gracefully offline or with scripts off."""
        self.build_pages()
        seen_urls: list[str] = []

        def mock_search(route):
            seen_urls.append(route.request.url)
            if "fail=1" in route.request.url or "q=offline" in route.request.url:
                route.abort()
                return
            page = 2 if "page=2" in route.request.url else 1
            payload = {
                "format": 1,
                "matches": 25,
                "page": page,
                "pages": 2,
                "repositories": [
                    {
                        "full_name": "octocat/Hello-World" if page == 1 else "octocat/Spoon-Knife",
                        "language": "Python",
                        "stars": 12345,
                        "last_board_day": "2026-11-09",
                        "last_rank": 3,
                        "description": "<img src=x onerror=alert(1)> Safe <b>description</b>",
                    }
                ],
            }
            route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

        with served(self.out) as site, chrome() as browser:
            # With scripts off, the page renders a clear noscript fallback with no /api/ links.
            no_js = browser.new_context(java_script_enabled=False, viewport={"width": 1440, "height": 900})
            plain = no_js.new_page()
            plain.goto(f"{site}/{SEARCH.removesuffix('index.html')}", wait_until="load")
            self.assertIn("Archive search needs scripts turned on.", plain.locator("main").inner_text())
            self.assertFalse(
                any("/api/" in href for href in plain.locator("a[href]").evaluate_all("a => a.map(x => x.href)"))
            )
            no_js.close()

            # With scripts on, initial load sends zero /api/ requests.
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.route("**/api/search*", mock_search)
            page.goto(f"{site}/{SEARCH.removesuffix('index.html')}", wait_until="load")
            self.assertEqual(seen_urls, [])

            # Submitting a search queries /api/search?q=pdf&format=json and renders safely.
            page.locator("#archive-q").fill("pdf")
            page.locator(".search-go").click()
            page.locator(".search-item").first.wait_for()
            self.assertEqual(len(seen_urls), 1)
            self.assertIn("/api/search?q=pdf&format=json", seen_urls[0])
            self.assertEqual(page.locator("#archive-results img, #archive-results b").count(), 0)
            self.assertIn("<img src=x onerror=alert(1)>", page.locator(".search-desc").first.inner_text())
            self.assertEqual(
                page.locator(".search-name").first.get_attribute("href"), "https://github.com/octocat/Hello-World"
            )
            self.assertEqual(page.locator(".search-seen a").first.get_attribute("href"), "/days/2026-11-09/")

            # Pagination fetches page 2.
            page.get_by_role("button", name="Next").click()
            page.wait_for_function("() => document.querySelector('.search-name').textContent === 'octocat/Spoon-Knife'")
            self.assertIn("page=2", seen_urls[-1])

            # Offline / failing API degrades cleanly.
            page.locator("#archive-q").fill("offline")
            page.locator(".search-go").click()
            page.wait_for_function(
                "() => document.getElementById('archive-status').textContent.includes('could not be reached')"
            )
            page.close()

    def test_an_opened_row_with_earlier_boards_fetches_and_renders_them_on_click(self):
        """#242: when an opened row has boards older than the 30-day window, clicking 'Show all earlier boards'
        fetches /api/repo/<owner>/<name>?format=json on demand and lists only the earlier board days."""
        newest = read_json(self.board_file())
        older_template = read_json(self.board_file("2026-11-08"))
        target = newest["rows"][0]
        start = date.fromisoformat("2026-11-09")
        entries = [{"board_day": "2026-11-09", "row_count": len(newest["rows"])}]
        for back in range(1, 35):
            day = (start - timedelta(days=back)).isoformat()
            rows = [{**target, "rank": 1}] if back == 33 else []
            write_json(
                self.board_file(day),
                {
                    **older_template,
                    "board_day": day,
                    "published_at": f"{day}T23:00:00Z",
                    "state": "rows" if rows else "empty",
                    "rows": rows,
                },
            )
            entries.append({"board_day": day, "row_count": len(rows)})
        write_json(self.index, {**read_json(self.index), "board_days": entries})
        self.build_pages()

        asked: list[str] = []
        fail_once = [True]

        def mock_repo(route):
            asked.append(route.request.url)
            if fail_once[0]:
                fail_once[0] = False
                route.abort()
                return
            payload = {
                "format": 1,
                "repository": {
                    "full_name": target["full_name"],
                    "history": [
                        {"board_day": "2026-10-07", "rank": 1},
                        {"board_day": "2026-11-09", "rank": 1},
                    ],
                },
            }
            route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

        with served(self.out) as site, chrome() as browser:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.clock.set_fixed_time(published(self.out))
            page.route("**/api/repo/**", mock_repo)
            page.goto(site, wait_until="load")
            row = page.locator("table.chart > tbody > tr").first
            row.locator("td.wy summary").click()
            row.locator("td.wy details[data-drawn]").wait_for()
            # Zero /api/ requests on opening the row itself.
            self.assertEqual(asked, [])
            button = row.locator("button.more-before")
            self.assertEqual(button.count(), 1)
            # First click fails -> graceful error note and retry button.
            button.click()
            row.locator(".more-before-err").wait_for()
            self.assertEqual(len(asked), 1)
            # Second click succeeds -> lists only boards older than the 30-day window and removes the button.
            button.click()
            row.locator(".earlier-list li").first.wait_for()
            self.assertEqual(row.locator("button.more-before").count(), 0)
            self.assertEqual(row.locator(".earlier-list a").all_text_contents(), ["2026-10-07"])
            self.assertEqual(row.locator(".earlier-list a").first.get_attribute("href"), "/days/2026-10-07/")
            page.close()


if __name__ == "__main__":
    unittest.main()
