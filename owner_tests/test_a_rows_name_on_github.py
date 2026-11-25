"""A row's name, which leads to its repository on GitHub. Sentence 38 of the owner's tests."""

import unittest

from playwright.sync_api import expect

from owner_tests.scenario import Scenario, board, names

GITHUB = "https://github.com/"


class ARowsNameOnGitHub(Scenario):
    def test_a_rows_name_opens_its_repository_on_github_in_a_new_tab_and_the_board_stays_with_scripts_on_or_off(self):
        """Sentence 38. With scripts on and then off, the reader follows the first row's name, by a click and then by
        Enter on it. The repository's page on GitHub opens in a tab of its own, which has no hold on the board's tab,
        and the board's tab stays on the board, with every row it listed. The link is found by its role and the name
        it reads, owner/name. GitHub answers with a stand-in, so that nothing is asked of it and a run against a live
        site only reads."""
        for scripts in (True, False):
            for how in ("click", "Enter"):
                with self.subTest(scripts=scripts, how=how):
                    page = self.reader(scripts=scripts)
                    page.context.route(
                        GITHUB + "**",
                        lambda route: route.fulfill(content_type="text/html", body="<title>GitHub stand-in</title>"),
                    )
                    self.visit(page)
                    listed = names(page)
                    self.given(listed, "the newest board lists no repository")
                    there = page.url
                    link = board(page).get_by_role("link", name=listed[0], exact=True)
                    with page.context.expect_page() as opening:
                        if how == "click":
                            link.click()
                        else:
                            link.press("Enter")
                    tab = opening.value
                    expect(tab).to_have_url(GITHUB + listed[0])
                    self.assertTrue(tab.evaluate("() => window.opener === null"))
                    self.assertEqual(page.url, there)
                    self.assertEqual(names(page), listed)


if __name__ == "__main__":
    unittest.main()
