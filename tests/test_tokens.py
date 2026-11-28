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

TOKEN_SHAPE = (
    r"gh[pousr]_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|discord(app)?\.com/api/webhooks/[0-9]"
    r"|-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"
    r"|A(KIA|SIA)[0-9A-Z]{16}"
    r"|xox[baprs]-[0-9A-Za-z-]{10,}"
    r"|hooks\.slack\.com/services/"
    r"|sk-(ant|proj)-[A-Za-z0-9_-]{20,}"
)
"""How a credential or secret starts, read alike by Python and by `git grep -E` (#250). Written as a pattern, it
matches nothing itself."""

PRIVATE_SHAPE = (
    r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+"
    r"|/(Users|home)/[A-Za-z0-9._-]+/"
    r"|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)
"""Local home-directory paths and email addresses that must not reach a public repository (STANDARDS.md C5, #251)."""

ALLOWED_EMAIL_DOMAINS = (
    "users.noreply.github.com",
    "example.com",
    "example.org",
    "example.net",
    "example.invalid",
    "ibm.com",
    "sil.org",
)
"""Email domains that are public, RFC 2606 reserved, or placeholder rather than personal."""

LOCAL_TEST_KEY_FILES = {"tests/test_stale_check.py"}
"""Files that carry a documented made-up PEM key for a 127.0.0.1 stand-in HTTPS server alone."""

NON_PEM_TOKEN_SHAPE = (
    r"gh[pousr]_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|discord(app)?\.com/api/webhooks/[0-9]"
    r"|A(KIA|SIA)[0-9A-Z]{16}"
    r"|xox[baprs]-[0-9A-Za-z-]{10,}"
    r"|hooks\.slack\.com/services/"
    r"|sk-(ant|proj)-[A-Za-z0-9_-]{20,}"
)


def token_shaped_files(root: Path) -> list[str]:
    """The files git would commit under `root` that hold a string shaped like a credential: each staged file,
    and each tracked or new file in the working tree. A file git ignores is not read."""
    import re

    found = set()
    for where in ("--cached", "--untracked"):
        command = ["git", "grep", where, "--files-with-matches", "-z", "--extended-regexp", "-e", TOKEN_SHAPE]
        result = subprocess.run(command, cwd=root, capture_output=True, timeout=60)
        if result.returncode not in (0, 1):  # 1 means that nothing matched
            raise RuntimeError(
                f"`git grep {where}` exited {result.returncode}: {result.stderr.decode(errors='replace')}"
            )
        found.update(name for name in result.stdout.decode("utf-8", errors="replace").split("\0") if name)
    non_pem = re.compile(NON_PEM_TOKEN_SHAPE)
    kept = []
    for name in sorted(found):
        if name in LOCAL_TEST_KEY_FILES:
            text = (root / name).read_text(encoding="utf-8", errors="replace")
            if not non_pem.search(text):
                continue
        kept.append(name)
    return kept


def private_files(root: Path) -> list[str]:
    """Non-data files git would commit under `root` that hold a local home-directory path or a personal email
    address (STANDARDS.md C5, #251). `site-data/` holds owner-written repository descriptions and is excluded."""
    import re

    home = re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+|/(?:Users|home)/[A-Za-z0-9._-]+/")
    email = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
    candidates = set()
    for where in ("--cached", "--untracked"):
        command = [
            "git",
            "grep",
            where,
            "--files-with-matches",
            "-z",
            "--extended-regexp",
            "-e",
            PRIVATE_SHAPE,
            "--",
            ":(exclude)site-data/**",
            ":(exclude)*.lock",
            ":(exclude)sitebuild/static/fonts/OFL.txt",
        ]
        result = subprocess.run(command, cwd=root, capture_output=True, timeout=60)
        if result.returncode not in (0, 1):
            raise RuntimeError(
                f"`git grep {where}` exited {result.returncode}: {result.stderr.decode(errors='replace')}"
            )
        candidates.update(name for name in result.stdout.decode("utf-8", errors="replace").split("\0") if name)
    found = []
    for name in sorted(candidates):
        if name == "tests/test_tokens.py":
            continue
        text = (root / name).read_text(encoding="utf-8", errors="replace")
        has_home = bool(home.search(text))
        has_email = any(
            not any(domain.lower() == ok or domain.lower().endswith("." + ok) for ok in ALLOWED_EMAIL_DOMAINS)
            for domain in email.findall(text)
        )
        if has_home or has_email:
            found.append(name)
    return found


class TheRepository(unittest.TestCase):
    def test_no_file_git_would_commit_holds_a_string_shaped_like_a_credential(self):
        self.assertEqual(token_shaped_files(ROOT), [])

    def test_no_file_git_would_commit_holds_a_local_home_path_or_personal_email(self):
        self.assertEqual(private_files(ROOT), [])


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
            "pem.txt": "-----BEGIN " + "RSA PRIVATE KEY-----",
            "aws.txt": "AK" + "IA" + "0123456789ABCDEF",
            "slack.txt": "xo" + "xb-1234567890-abcdef",
            "ai.txt": "sk-" + "ant-" + "a" * 24,
        }
        for name, value in made_up.items():
            (self.root / name).write_text(f"value = {value}\n", encoding="utf-8")
        subprocess.run(["git", "add", "classic.txt"], cwd=self.root, check=True, timeout=60)
        self.assertEqual(token_shaped_files(self.root), sorted(made_up))

    def test_it_finds_local_home_paths_and_personal_emails_and_allows_noreply(self):
        (self.root / "win.txt").write_text("C:\\" + "Users\\alice\\repo\n", encoding="utf-8")
        (self.root / "mac.txt").write_text("/" + "Users/alice/repo\n", encoding="utf-8")
        (self.root / "mail.txt").write_text("alice" + "@personal-domain.test\n", encoding="utf-8")
        (self.root / "ok.txt").write_text("123+alice" + "@users.noreply.github.com\n", encoding="utf-8")
        self.assertEqual(private_files(self.root), ["mac.txt", "mail.txt", "win.txt"])

    def test_it_reads_no_file_git_ignores(self):
        (self.root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        (self.root / "ignored.txt").write_text("gh" + "o_" + "z" * 36 + "\n", encoding="utf-8")
        self.assertEqual(token_shaped_files(self.root), [])


if __name__ == "__main__":
    unittest.main()
