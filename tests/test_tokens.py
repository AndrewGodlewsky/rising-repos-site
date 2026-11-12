"""No file git would commit holds a string shaped like a credential.

The repository is public. The search is RisingRepos's, from its regression command: the pattern is
`config.TOKEN_SHAPE` there, and docs/agents/secrets.md there gives the same one. It knows only how a GitHub
token and a Discord webhook address start.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT

TOKEN_SHAPE = r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|discord(app)?\.com/api/webhooks/[0-9]"
"""How a GitHub token or a Discord webhook address starts, read alike by Python and by `git grep -E`. Written
as a pattern, it matches nothing itself."""


def token_shaped_files(root: Path) -> list[str]:
    """The files git would commit under `root` that hold a string shaped like a credential: each staged file,
    and each tracked or new file in the working tree. A file git ignores is not read."""
    found = set()
    for where in ("--cached", "--untracked"):
        command = ["git", "grep", where, "--files-with-matches", "-z", "--extended-regexp", "-e", TOKEN_SHAPE]
        result = subprocess.run(command, cwd=root, capture_output=True, timeout=60)
        if result.returncode not in (0, 1):  # 1 means that nothing matched
            raise RuntimeError(f"`git grep {where}` exited {result.returncode}: {result.stderr.decode(errors='replace')}")
        found.update(name for name in result.stdout.decode("utf-8", errors="replace").split("\0") if name)
    return sorted(found)


class TheRepository(unittest.TestCase):
    def test_no_file_git_would_commit_holds_a_string_shaped_like_a_credential(self):
        self.assertEqual(token_shaped_files(ROOT), [])


class TheSearch(unittest.TestCase):
    """The search, on a repository of its own in a temporary folder. Each made-up credential is put together
    when the test runs, so that no file holds one whole."""

    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        subprocess.run(["git", "init", "--quiet"], cwd=self.root, check=True, timeout=60)
        (self.root / "clean.txt").write_text("nothing here\n", encoding="utf-8")

    def test_it_finds_each_shape_in_a_new_file_and_in_a_staged_one(self):
        made_up = {
            "classic.txt": "gh" + "p_" + "a1B2" * 9,
            "fine-grained.txt": "github" + "_pat_" + "11ABC_" + "x" * 30,
            "webhook.txt": "https://discord" + ".com/api/webhooks/" + "1234/abc",
        }
        for name, value in made_up.items():
            (self.root / name).write_text(f"value = {value}\n", encoding="utf-8")
        subprocess.run(["git", "add", "classic.txt"], cwd=self.root, check=True, timeout=60)
        self.assertEqual(token_shaped_files(self.root), sorted(made_up))

    def test_it_reads_no_file_git_ignores(self):
        (self.root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        (self.root / "ignored.txt").write_text("gh" + "o_" + "z" * 36 + "\n", encoding="utf-8")
        self.assertEqual(token_shaped_files(self.root), [])


if __name__ == "__main__":
    unittest.main()
