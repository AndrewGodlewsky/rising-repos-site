"""The owner's tests: what a reader can do on the site and what the site promises that reader, one plain sentence to
a test. README.md, in this folder, lists the sentences and says how the folder may change.

Run them from the repository with `python -m unittest discover -s owner_tests -t .`. They build the site from made-up
boards and drive it in a browser. With the environment variable SITE set to a site's address they read that site
instead, and the scenarios that need the made-up boards are left out here, by the loader.
"""

import sys
import unittest
from collections.abc import Iterator
from pathlib import Path

from owner_tests import the_site


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    """Every scenario in the folder's test files, as unittest's discovery asks a package for them. Against a live
    site, a scenario marked as needing the made-up boards is left out, and the run says how many were."""
    folder = Path(__file__).parent
    found = unittest.TestSuite(
        loader.loadTestsFromName(f"{__name__}.{file.stem}") for file in sorted(folder.glob(pattern or "test*.py"))
    )
    if not the_site.LIVE:
        return found
    scenarios = list(_each(found))
    kept = [scenario for scenario in scenarios if not _needs_made_up_boards(scenario)]
    print(
        f"owner_tests: reading {the_site.LIVE}, so {len(scenarios) - len(kept)} scenarios that need the made-up "
        f"boards are left out, and {len(kept)} run.",
        file=sys.stderr,
    )
    return unittest.TestSuite(kept)


def _each(suite: unittest.TestSuite) -> Iterator[unittest.TestCase]:
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from _each(test)
        else:
            yield test


def _needs_made_up_boards(scenario: unittest.TestCase) -> bool:
    method = getattr(scenario, scenario.id().rpartition(".")[2], None)
    return getattr(method, "needs_made_up_boards", False)
