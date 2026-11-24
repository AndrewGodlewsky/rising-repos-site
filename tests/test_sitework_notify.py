"""`notify` sends the owner one message on Discord, and never prints the webhook's address.

No test sends a message. Each replaces `sitework.notify.post`, the one function that reaches Discord, or the
opener it posts through, and the credential store is a stand-in. Each made-up address is put together when the
test runs, so that no file holds one whole (tests/test_tokens.py).
"""

import contextlib
import io
import json
import os
import sys
import types
import unittest
import urllib.error
from unittest import mock

from sitework import notify

ADDRESS = "https://discord" + ".com/api/webhooks/" + "1234/made-up"


class Notify(unittest.TestCase):
    def setUp(self):
        self.enterContext(mock.patch.dict(os.environ))
        os.environ.pop(notify.VARIABLE, None)
        self.posted = []
        self.enterContext(
            mock.patch.object(notify, "post", lambda address, message: self.posted.append((address, message)))
        )

    def store(self, held: str | None) -> list:
        """Put a credential store that holds `held` in the place of the `keyring` package, and give the list of
        what it is asked for."""
        asked = []

        def get_password(service, entry):
            asked.append((service, entry))
            return held

        self.enterContext(mock.patch.dict(sys.modules, {"keyring": types.SimpleNamespace(get_password=get_password)}))
        return asked

    def no_store(self) -> None:
        """Leave the machine without the `keyring` package: Python refuses to import a module named as None."""
        self.enterContext(mock.patch.dict(sys.modules, {"keyring": None}))

    def run_command(self, message: str) -> tuple[int, str]:
        """Run `notify`, and give its exit code and everything it printed, to either stream."""
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            code = notify.main("notify", [message])
        return code, printed.getvalue()

    def test_it_posts_the_message_to_the_address_in_the_environment_and_prints_sent(self):
        os.environ[notify.VARIABLE] = ADDRESS
        self.assertEqual(self.run_command("The site eval failed."), (0, "sent\n"))
        self.assertEqual(self.posted, [(ADDRESS, "The site eval failed.")])

    def test_it_cuts_a_message_at_1900_characters(self):
        os.environ[notify.VARIABLE] = ADDRESS
        self.run_command("a" * 1900 + "b" * 50)
        self.assertEqual(self.posted, [(ADDRESS, "a" * 1900)])

    def test_with_the_variable_unset_it_reads_the_address_from_the_credential_store(self):
        asked = self.store(ADDRESS)
        self.assertEqual(self.run_command("Shipped."), (0, "sent\n"))
        self.assertEqual(asked, [("risingrepos", "discord-webhook-url")])
        self.assertEqual(self.posted, [(ADDRESS, "Shipped.")])

    def test_with_the_variable_set_the_credential_store_is_never_imported(self):
        os.environ[notify.VARIABLE] = ADDRESS
        self.no_store()
        self.assertEqual(self.run_command("Shipped."), (0, "sent\n"))

    def test_without_the_keyring_package_it_prints_that_there_is_no_credential_store_and_exits_1(self):
        self.no_store()
        self.assertEqual(self.run_command("Shipped."), (1, "not sent: no credential store\n"))
        self.assertEqual(self.posted, [])

    def test_a_store_that_holds_no_address_sends_nothing_and_exits_1(self):
        self.store(None)
        self.assertEqual(self.run_command("Shipped."), (1, "not sent: no credential\n"))
        self.assertEqual(self.posted, [])

    def test_a_failed_post_is_named_by_its_type_and_its_words_are_never_printed(self):
        os.environ[notify.VARIABLE] = ADDRESS

        def refuse(address, message):
            raise ValueError(f"could not reach {address}")

        self.enterContext(mock.patch.object(notify, "post", refuse))
        self.assertEqual(self.run_command("Shipped."), (1, "not sent: ValueError\n"))

    def test_a_store_that_fails_is_named_by_its_type_and_its_words_are_never_printed(self):
        def get_password(service, entry):
            raise RuntimeError(f"the store is locked, and held {ADDRESS}")

        self.enterContext(mock.patch.dict(sys.modules, {"keyring": types.SimpleNamespace(get_password=get_password)}))
        self.assertEqual(self.run_command("Shipped."), (1, "not sent: RuntimeError\n"))


class Post(unittest.TestCase):
    """`post` itself, through an opener that keeps the request and sends nothing."""

    def test_it_sends_the_message_as_json_that_mentions_nobody(self):
        sent = []

        class Opener:
            def open(self, request, timeout):
                sent.append(request)
                return contextlib.nullcontext()

        with mock.patch.object(notify, "OPENER", Opener()):
            notify.post(ADDRESS, "Stopped at check: @everyone")
        (request,) = sent
        self.assertEqual((request.full_url, request.get_method()), (ADDRESS, "POST"))
        self.assertEqual(request.get_header("Content-type"), "application/json")
        body = json.loads(request.data)
        self.assertEqual(body["content"], "Stopped at check: @everyone")
        self.assertEqual(body["allowed_mentions"], {"parse": []})

    def test_an_address_that_is_not_https_is_refused_before_anything_is_sent(self):
        with self.assertRaises(urllib.error.URLError) as refused:
            notify.post("http://127.0.0.1:9/made-up", "Shipped.")
        self.assertIn("unknown url type", str(refused.exception.reason))


if __name__ == "__main__":
    unittest.main()
