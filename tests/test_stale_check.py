"""The stale check posts to Discord when the site's newest board is too old.

`.github/workflows/stale-check.yml` holds the Discord webhook, and reads a page that the daily data push can
change, as it can change any file in this repository but a workflow. So its job checks out nothing and runs only
the script written in the workflow file, and nothing it reads from the page reaches a shell, a command line, or
its output. The tests in `TheWorkflow` read the workflow file. The tests in `TheCheck` take the script out of it
and run it as the job does, against a stand-in for the site and a stand-in for Discord: each an HTTPS server on
127.0.0.1 with a made-up certificate that only the script these tests run trusts.

A board's publish time is set some hours before the moment a test runs, an hour or more away from the limit, so
that what a test sees does not depend on when it runs.
"""

import ast
import html
import http.server
import json
import os
import re
import secrets
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from helpers import ROOT

WORKFLOW = ROOT / ".github" / "workflows" / "stale-check.yml"
SECRET = re.compile(r"\bsecrets\b")
RUN = "https://github.com/AndrewGodlewsky/rising-repos-site/actions/runs/123456789"
"""The run's address in each alarm, from the GITHUB_ variables each test gives the script."""

# A made-up certificate and its key, for the address 127.0.0.1 only, valid until 2126. They guard nothing. The
# stand-ins serve HTTPS with them, and only the script these tests run is told to trust the certificate.
CERTIFICATE = """\
-----BEGIN CERTIFICATE-----
MIIBtzCCAV2gAwIBAgIUQalNfoE5Ot4d6/XLL/Dm89a2/MAwCgYIKoZIzj0EAwIw
FDESMBAGA1UEAwwJMTI3LjAuMC4xMCAXDTI2MTExMjE2MzQxOVoYDzIxMjYxMDE5
MTYzNDE5WjAUMRIwEAYDVQQDDAkxMjcuMC4wLjEwWTATBgcqhkjOPQIBBggqhkjO
PQMBBwNCAAQ5fs0836p7QJD95srmdJy8aOstOvUkffpq/iqUaB/+GT4+LxIsk7ne
ZMXS7xYRVU3BTkgkP/tgOnGm+kYD81wBo4GKMIGHMB0GA1UdDgQWBBRZluYmVpgm
tlqQ/66OOIYk1dTqpTAfBgNVHSMEGDAWgBRZluYmVpgmtlqQ/66OOIYk1dTqpTAP
BgNVHREECDAGhwR/AAABMA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgKE
MBMGA1UdJQQMMAoGCCsGAQUFBwMBMAoGCCqGSM49BAMCA0gAMEUCID5oUzE8yN/l
CwsRXpozLCbmJ8x6IJvSqLDfAOumC4zEAiEA6fJL15bJr7uC092Ff8zZeeMkgV1d
5tKLKYxuTWUgKjY=
-----END CERTIFICATE-----
"""
KEY = """\
-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgNZfyp3NMqpFZIsV7
iEHPc+3AlCpeyijpmGFP2yKdmQKhRANCAAQ5fs0836p7QJD95srmdJy8aOstOvUk
ffpq/iqUaB/+GT4+LxIsk7neZMXS7xYRVU3BTkgkP/tgOnGm+kYD81wB
-----END PRIVATE KEY-----
"""


def load() -> dict:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    workflow["on"] = workflow.pop(True)  # YAML 1.1 reads the key `on` as true
    return workflow


def the_step(workflow: dict) -> dict:
    (step,) = workflow["jobs"]["check"]["steps"]
    return step


def hours_ago(hours: float) -> str:
    """A publish time `hours` before now, written as the page writes one."""
    return (datetime.now(UTC) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def page(board_day: str | None = "2026-11-09", published_at: str | None = None, *, head: str = "") -> bytes:
    """A page whose head states a board day as the site's pages do. A tag whose value is None is left out."""
    tags = "".join(
        f'<meta name="{name}" content="{html.escape(value)}">'
        for name, value in (("rr:board-date", board_day), ("rr:published-at", published_at))
        if value is not None
    )
    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8">{tags}{head}<title>A stand-in</title></head>'
        "<body><p>A board.</p></body></html>"
    ).encode()


class _Answer(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self._answer()

    def do_POST(self):
        self._answer()

    def _answer(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.server.requests.append((self.command, dict(self.headers), body))
        status, content, headers = self.server.answer
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):  # the stand-ins print nothing
        pass


class StandIn:
    """An HTTPS server on 127.0.0.1 that gives every request one answer, which `answer` sets: a status, a body,
    and any other headers. It keeps each request in `requests`, as its method, its headers, and its body."""

    def __init__(self, test: unittest.TestCase, tls: Path, status: int, content: bytes = b""):
        self._server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Answer)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(tls / "certificate.pem", tls / "key.pem")
        self._server.socket = context.wrap_socket(self._server.socket, server_side=True)
        self.answer(status, content)
        self._server.requests = []
        self.address = f"https://127.0.0.1:{self._server.server_address[1]}/"
        # A short poll, so that each test's shutdown does not wait half a second for the server to notice it.
        thread = threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        test.addCleanup(thread.join)
        test.addCleanup(self._server.server_close)
        test.addCleanup(self._server.shutdown)

    @property
    def requests(self) -> list[tuple[str, dict, bytes]]:
        return self._server.requests

    def answer(self, status: int, content: bytes = b"", **headers: str) -> None:
        self._server.answer = (status, content, headers)


class TheWorkflow(unittest.TestCase):
    def setUp(self):
        self.workflow = load()
        self.job = self.workflow["jobs"]["check"]
        self.step = the_step(self.workflow)

    def test_only_its_schedule_and_a_start_by_hand_can_run_it(self):
        # No pull request can start it, so no change that is not yet on main runs where the webhook is.
        self.assertEqual(set(self.workflow["on"]), {"schedule", "workflow_dispatch"})

    def test_it_runs_once_a_day_after_a_board_due_by_8pm_eastern_has_passed_26_hours(self):
        (entry,) = self.workflow["on"]["schedule"]
        minute, hour, *days = entry["cron"].split()
        self.assertEqual(days, ["*", "*", "*"])
        self.assertRegex(minute, r"^[0-9]+$")
        self.assertRegex(hour, r"^[0-9]+$")
        # Not on the hour, when GitHub delays scheduled runs most, and drops some.
        self.assertNotEqual(int(minute), 0)
        # 8:00 pm in US Eastern daylight time (UTC-4) and standard time (UTC-5), 26 hours on, is 02:00 and 03:00
        # UTC the night after. The check runs once a day after both.
        for behind_utc in (4, 5):
            stale = (20 + behind_utc + 26) % 24
            self.assertGreater(int(hour) * 60 + int(minute), stale * 60)

    def test_its_token_has_no_permission(self):
        # The job reads nothing from this repository, so its token needs no permission, contents: read included.
        self.assertEqual(self.workflow["permissions"], {})
        self.assertNotIn("permissions", self.job)

    def test_it_checks_out_nothing_uses_no_action_and_runs_only_the_script_in_this_file(self):
        self.assertEqual(set(self.workflow["jobs"]), {"check"})
        self.assertEqual(len(self.job["steps"]), 1)
        self.assertNotIn("uses", self.step)
        # The runner image's own Python, isolated from the environment's PYTHON variables and from the folder it
        # runs in.
        self.assertEqual(self.step["shell"], "python3 -I {0}")

    def test_it_has_a_time_limit_and_no_deployment_environment(self):
        self.assertLessEqual(self.job["timeout-minutes"], 10)
        self.assertNotIn("environment", self.job)
        self.assertEqual(self.job["runs-on"], "ubuntu-24.04")

    def test_the_webhook_reaches_only_the_step_that_posts_through_its_environment(self):
        self.assertEqual(
            {name: value for name, value in self.step["env"].items() if SECRET.search(value)},
            {"DISCORD_WEBHOOK_URL": "${{ secrets.DISCORD_WEBHOOK_URL }}"},
        )
        rest = dict(self.workflow, jobs={"check": dict(self.job, steps=[dict(self.step, env={})])})
        self.assertIsNone(SECRET.search(yaml.safe_dump(rest)))

    def test_no_expression_is_written_into_the_script(self):
        # GitHub replaces each ${{ }} in a run: block before the script runs, so a value put there becomes code.
        # The inputs and the secret reach the script through its environment instead.
        self.assertNotIn("${{", self.step["run"])
        self.assertEqual(self.step["env"]["CHECK_ADDRESS"], "${{ inputs.address }}")
        self.assertEqual(self.step["env"]["CHECK_MAX_AGE_HOURS"], "${{ inputs.max_age_hours }}")

    def test_a_run_by_hand_is_offered_the_defaults_a_scheduled_run_takes(self):
        inputs = self.workflow["on"]["workflow_dispatch"]["inputs"]
        self.assertEqual(set(inputs), {"address", "max_age_hours"})
        self.assertEqual(inputs["address"]["default"], self.workflow["env"]["DEFAULT_ADDRESS"])
        self.assertEqual(inputs["max_age_hours"]["default"], self.workflow["env"]["DEFAULT_MAX_AGE_HOURS"])

    def test_it_reads_the_preview_until_go_live_and_the_site_is_fresh_for_26_hours(self):
        self.assertEqual(self.workflow["env"]["DEFAULT_ADDRESS"], "https://preview.risingrepos.pages.dev/")
        self.assertEqual(self.workflow["env"]["DEFAULT_MAX_AGE_HOURS"], "26")

    def test_the_script_keeps_to_the_grammar_of_python_3_12_which_the_runner_image_has(self):
        # The tests run the script with this repository's Python, and the job with ubuntu-24.04's own python3,
        # which is 3.12. This shows only that 3.12 can parse it, not that every library call it makes is in 3.12.
        ast.parse(self.step["run"], feature_version=(3, 12))


class TheCheck(unittest.TestCase):
    def setUp(self):
        temporary = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.folder = temporary / "run"
        self.folder.mkdir()
        self.tls = temporary / "tls"
        self.tls.mkdir()
        (self.tls / "certificate.pem").write_text(CERTIFICATE, encoding="ascii", newline="\n")
        (self.tls / "key.pem").write_text(KEY, encoding="ascii", newline="\n")
        workflow = load()
        step = the_step(workflow)
        self.script = temporary / "stale-check.py"
        self.script.write_text(step["run"], encoding="utf-8", newline="\n")
        self.shell = step["shell"].split()
        self.default_hours = workflow["env"]["DEFAULT_MAX_AGE_HOURS"]
        self.site = StandIn(self, self.tls, 200, page(published_at=hours_ago(2)))
        self.discord = StandIn(self, self.tls, 204)
        # A made-up webhook address, put together here so that no file holds one.
        self.token = secrets.token_urlsafe(48)
        self.webhook = f"{self.discord.address}api/webhooks/{secrets.randbelow(10**18)}/{self.token}"

    def check(self, address: str | None = None, hours: str = "", **environment: str) -> subprocess.CompletedProcess:
        """Run the script as the job does, with the inputs `address` (the stand-in site by default) and `hours`
        (empty, so the workflow's default age limit, by default). `environment` sets or replaces any other variable."""
        given = {
            "CHECK_ADDRESS": self.site.address if address is None else address,
            "CHECK_MAX_AGE_HOURS": hours,
            "DEFAULT_ADDRESS": "",
            "DEFAULT_MAX_AGE_HOURS": self.default_hours,
            "DISCORD_WEBHOOK_URL": self.webhook,
            "GITHUB_EVENT_NAME": "schedule",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_REPOSITORY": "AndrewGodlewsky/rising-repos-site",
            "GITHUB_RUN_ID": "123456789",
            "SSL_CERT_FILE": str(self.tls / "certificate.pem"),
        }
        given.update(environment)
        ours = ("CHECK_", "DEFAULT_", "DISCORD_", "GITHUB_", "SSL_CERT_")
        inherited = {name: value for name, value in os.environ.items() if not name.startswith(ours)}
        command = [{"python3": sys.executable, "{0}": str(self.script)}.get(word, word) for word in self.shell]
        result = subprocess.run(
            command,
            env=inherited | given,
            cwd=self.folder,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        output = result.stdout + result.stderr
        self.assertNotIn(self.token, output, "the webhook's address is in the run's output")
        for _, _, body in self.discord.requests:
            self.assertNotIn(self.token, body.decode("utf-8", errors="replace"))
        return result

    def alarm(self) -> dict:
        """The one message Discord was sent, as the JSON it was sent as."""
        self.assertEqual(len(self.discord.requests), 1, "a run posts one message at most")
        ((method, headers, body),) = self.discord.requests
        self.assertEqual(method, "POST")
        self.assertEqual(headers["Content-Type"], "application/json")
        return json.loads(body)

    def assertPostsNothing(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.discord.requests, [])

    def test_a_fresh_board_posts_nothing(self):
        for hours in (0, 2, 25):
            with self.subTest(hours_old=hours):
                self.site.answer(200, page(published_at=hours_ago(hours)))
                result = self.check()
                self.assertPostsNothing(result)
                self.assertIn("Fresh. Board day 2026-11-09 was published", result.stdout)
                self.assertIn("Nothing was posted.", result.stdout)

    def test_a_board_26_hours_old_or_more_posts_one_alarm_with_its_age_and_where_to_look(self):
        published_at = hours_ago(30)
        self.site.answer(200, page(published_at=published_at))
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        alarm = self.alarm()
        self.assertEqual(
            alarm["content"].splitlines(),
            [
                "Rising Repos site check: the newest board is too old. Board day 2026-11-09 was published "
                f"30.0 hours ago, at {published_at}, and the limit is 26 hours.",
                f"Address read: {self.site.address}",
                "Check first: whether the daily job ran and published its board. If it did, whether the site's "
                "latest Build and deploy run passed.",
                f"Run: {RUN}",
            ],
        )
        # The log shows the message as it was sent, and Discord's answer.
        self.assertIn(alarm["content"], result.stdout)
        self.assertIn("Discord answered HTTP 204.", result.stdout)

    def test_the_alarm_mentions_nobody_and_shows_no_preview_of_its_links(self):
        self.site.answer(200, page(published_at=hours_ago(30)))
        self.check()
        alarm = self.alarm()
        self.assertEqual(alarm["allowed_mentions"], {"parse": []})
        self.assertEqual(alarm["flags"], 4)  # SUPPRESS_EMBEDS
        self.assertEqual(set(alarm), {"content", "allowed_mentions", "flags"})

    def test_a_page_that_cannot_be_read_posts_one_alarm_that_says_why(self):
        self.site.answer(404, b"<p>Not here</p>")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            self.alarm()["content"].splitlines(),
            [
                "Rising Repos site check: the page could not be read: it answered HTTP 404.",
                f"Address read: {self.site.address}",
                "Check first: whether the address opens in a browser. If it does not, the site's latest Build and "
                "deploy run, then Cloudflare Pages.",
                f"Run: {RUN}",
            ],
        )

    def test_a_page_whose_server_cannot_be_reached_posts_an_alarm_that_names_the_failure_by_its_kind(self):
        result = self.check(address="https://127.0.0.1:1/")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "the page could not be read: the request failed with ConnectionRefusedError.",
            self.alarm()["content"],
        )

    def test_a_page_that_states_no_usable_board_day_posts_one_alarm(self):
        fresh = hours_ago(2)
        pages = {
            "neither tag": page(None, None),
            "no board day": page(None, fresh),
            "no publish time": page("2026-11-09", None),
            "a tag twice": page(published_at=fresh, head='<meta name="rr:board-date" content="2026-11-09">'),
            "a tag with no content": page("", fresh),
            "a board day that is no date": page("2026-13-45", fresh),
            "a publish time that is no time": page(published_at="2026-11-12T24:00:00Z"),
            "a publish time more than ten minutes ahead": page(published_at=hours_ago(-1)),
        }
        for case, content in pages.items():
            with self.subTest(case):
                self.discord.requests.clear()
                self.site.answer(200, content)
                result = self.check()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(
                    self.alarm()["content"].splitlines(),
                    [
                        "Rising Repos site check: the page was read, and it states no usable board day.",
                        f"Address read: {self.site.address}",
                        "Check first: the site's latest Build and deploy run, and whether the page's head still "
                        "carries rr:board-date and rr:published-at once each.",
                        f"Run: {RUN}",
                    ],
                )

    def test_a_hostile_tag_changes_nothing_but_the_no_usable_board_day_result(self):
        self.site.answer(200, page(None, None))
        self.check()
        expected = self.alarm()["content"]
        hostile = {
            "shell": "2026-11-09$(touch pwned)`touch pwned`;touch pwned",
            "markup": '2026-11-09"><script>alert("pwned")</script>',
            "a mention": "@everyone 2026-11-09 pwned <@&123>",
            "a workflow command on the next line": "2026-11-09\n::add-mask::pwned\n::error::pwned",
            "digits beyond ASCII": "２０２６-11-09",
            "a very long value": "2026-11-09" + "pwned" * 50_000,
        }
        fresh = hours_ago(2)
        for case, value in hostile.items():
            # In rr:published-at the value's board day becomes a fresh publish time, so that only the rest of the
            # value is wrong.
            for tag, content in (
                ("rr:board-date", page(value, fresh)),
                ("rr:published-at", page("2026-11-09", value.replace("2026-11-09", fresh))),
            ):
                with self.subTest(case, tag=tag):
                    self.discord.requests.clear()
                    self.site.answer(200, content)
                    result = self.check()
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(self.alarm()["content"], expected)
                    self.assertNotIn("pwned", result.stdout + result.stderr)
                    self.assertEqual(list(self.folder.iterdir()), [], "the run wrote a file")

    def test_a_run_started_by_hand_says_so_first(self):
        self.site.answer(200, page(published_at=hours_ago(30)))
        for case, environment, by_hand in (
            ("by the schedule", {}, False),
            ("by hand", {"GITHUB_EVENT_NAME": "workflow_dispatch"}, True),
            ("a scheduled run run again by hand", {"GITHUB_RUN_ATTEMPT": "2"}, True),
        ):
            with self.subTest(case):
                self.discord.requests.clear()
                self.check(**environment)
                first = self.alarm()["content"].splitlines()[0]
                self.assertEqual(first == "Started by hand, not by the daily schedule.", by_hand, first)

    def test_a_run_by_hand_forces_an_alarm_with_a_short_limit(self):
        self.site.answer(200, page(published_at=hours_ago(2)))
        result = self.check(hours="1", GITHUB_EVENT_NAME="workflow_dispatch")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        content = self.alarm()["content"]
        self.assertIn("the newest board is too old. Board day 2026-11-09 was published 2.0 hours ago", content)
        self.assertIn("and the limit is 1 hours.", content)

    def test_a_limit_of_0_makes_any_board_too_old(self):
        self.site.answer(200, page(published_at=hours_ago(0)))
        self.check(hours="0")
        self.assertIn("and the limit is 0 hours.", self.alarm()["content"])

    def test_a_scheduled_run_takes_the_defaults(self):
        self.site.answer(200, page(published_at=hours_ago(27)))
        self.check(address="", DEFAULT_ADDRESS=self.site.address)
        self.assertEqual(len(self.site.requests), 1)
        self.assertIn("and the limit is 26 hours.", self.alarm()["content"])

    def test_a_redirect_is_followed_only_to_an_https_address(self):
        moved = StandIn(self, self.tls, 200, page(published_at=hours_ago(30)))
        port = moved.address.split(":")[2].rstrip("/")
        for case, location, found in (
            ("to https", moved.address, "the newest board is too old"),
            ("to http", f"http://127.0.0.1:{port}/", "the page could not be read: the request failed with URLError."),
        ):
            with self.subTest(case):
                self.discord.requests.clear()
                self.site.answer(302, Location=location)
                self.check()
                self.assertIn(found, self.alarm()["content"])

    def test_no_proxy_is_used(self):
        # Nothing listens at the proxy's address, so a read through it would fail.
        self.assertPostsNothing(self.check(HTTPS_PROXY="http://127.0.0.1:1"))

    def test_the_page_is_read_without_a_cache_and_names_the_check(self):
        self.check()
        ((method, headers, _),) = self.site.requests
        self.assertEqual(method, "GET")
        self.assertEqual(headers["Cache-Control"], "no-cache")
        self.assertEqual(headers["User-Agent"], "rising-repos-site stale check")

    def test_an_address_that_is_not_https_is_refused_and_nothing_is_read_or_posted(self):
        port = self.site.address.split(":")[2].rstrip("/")
        for address in (
            f"http://127.0.0.1:{port}/",
            "file:///etc/passwd",
            f"https://user:pwned@127.0.0.1:{port}/",
            f"https://127.0.0.1:{port}/?pwned",
            f"https://127.0.0.1:{port}/$(touch pwned)",
            f"https://127.0.0.1:{port}/" + "a" * 200,
            "",
        ):
            with self.subTest(address=address[:60]):
                result = self.check(address=address)
                self.assertEqual(result.returncode, 1)
                self.assertIn("::error::The address to read is not one this check takes", result.stdout)
                self.assertNotIn("pwned", result.stdout + result.stderr)
                self.assertEqual(self.site.requests, [])
                self.assertEqual(self.discord.requests, [])

    def test_a_limit_that_is_not_a_whole_number_of_hours_from_0_to_168_is_refused(self):
        for hours in ("-1", "169", "1.5", " 26", "26\n", "２６"):
            with self.subTest(hours=hours):
                result = self.check(hours=hours)
                self.assertEqual(result.returncode, 1)
                self.assertIn("::error::The age limit is not a whole number of hours from 0 to 168.", result.stdout)
                self.assertEqual(self.site.requests, [])
                self.assertEqual(self.discord.requests, [])
        self.check(hours="168")
        self.assertEqual(len(self.site.requests), 1)

    def test_the_webhook_address_is_in_no_output_when_discord_refuses_the_alarm(self):
        self.site.answer(200, page(published_at=hours_ago(30)))
        for status in (404, 429, 500):
            with self.subTest(status=status):
                self.discord.requests.clear()
                self.discord.answer(status, json.dumps({"message": self.token}).encode())
                result = self.check()
                self.assertEqual(result.returncode, 1)
                self.assertIn(f"::error::Discord refused the alarm: it answered HTTP {status}.", result.stdout)
                self.assertEqual(len(self.discord.requests), 1, "a refused alarm is not sent again")

    def test_the_webhook_address_is_in_no_output_when_the_alarm_cannot_be_sent(self):
        self.site.answer(200, page(published_at=hours_ago(30)))
        for case, webhook, kind in (
            ("nothing listens", f"https://127.0.0.1:1/api/webhooks/1/{self.token}", "ConnectionRefusedError"),
            ("not https", f"http://127.0.0.1:1/api/webhooks/1/{self.token}", "URLError"),
            ("a port that is no number", f"https://127.0.0.1:{self.token}/", "InvalidURL"),
            ("no address at all", f"not an address {self.token}", "ValueError"),
        ):
            with self.subTest(case):
                result = self.check(DISCORD_WEBHOOK_URL=webhook)
                self.assertEqual(result.returncode, 1)
                self.assertIn(f"::error::The alarm was not sent: the request failed with {kind}.", result.stdout)

    def test_a_webhook_that_is_not_set_fails_the_run(self):
        self.site.answer(200, page(published_at=hours_ago(30)))
        result = self.check(DISCORD_WEBHOOK_URL="")
        self.assertEqual(result.returncode, 1)
        self.assertIn("::error::The alarm was not sent: the secret DISCORD_WEBHOOK_URL is empty.", result.stdout)


if __name__ == "__main__":
    unittest.main()
