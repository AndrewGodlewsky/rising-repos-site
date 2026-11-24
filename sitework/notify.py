"""`notify`: send the owner one message on Discord.

The workflow tells the owner when it stops for an answer, when a feature ships, and when the site is not healthy
(docs/workflow-plan.md, sections 3, 10, and 14). The webhook's address is a credential, since whoever holds it can
post to the owner's channel (STANDARDS.md, C6). So it is read from the environment or from the machine's
credential store, it is used in this one process and handed to no command, and it is never printed. An error is
named by its type alone, because an error's own words can repeat the address it was given.
"""

import argparse
import json
import os
import ssl
import urllib.request

VARIABLE = "RISINGREPOS_DISCORD_WEBHOOK_URL"
"""The environment variable that holds the webhook's address."""
SERVICE, ENTRY = "risingrepos", "discord-webhook-url"
"""Where the machine's credential store holds the address, which is read when the variable is unset."""

LONGEST = 1900
"""The characters of a message that are sent. What a longer message holds after them is left out."""
TIMEOUT = 30  # seconds that the request may take
AGENT = "rising-repos-site workflow"  # each request names its caller, as Discord asks
SUPPRESS_EMBEDS = 4  # the message flag that keeps Discord from showing a preview of each link

# The request goes out over HTTPS, through no proxy, and follows no redirect, so that the address reaches Discord
# and nothing else. An address of any other scheme is refused before anything is sent.
OPENER = urllib.request.OpenerDirector()
for handler in (
    urllib.request.HTTPSHandler(context=ssl.create_default_context()),
    urllib.request.HTTPDefaultErrorHandler(),
    urllib.request.HTTPErrorProcessor(),
    urllib.request.UnknownHandler(),
):
    OPENER.add_handler(handler)


def post(address: str, message: str) -> None:
    """Send `message` to the webhook at `address`, once. The message mentions nobody, whatever its text holds. A
    test replaces this function, so that no test sends a message."""
    body = {"content": message, "allowed_mentions": {"parse": []}, "flags": SUPPRESS_EMBEDS}
    request = urllib.request.Request(
        address,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": AGENT},
    )
    with OPENER.open(request, timeout=TIMEOUT):
        pass


def address() -> str | None:
    """The webhook's address: the variable's value, or what the credential store holds when the variable is
    unset. `keyring` is no dependency of this repository, so it is imported only when it is needed, and a machine
    without it raises ImportError here."""
    held = os.environ.get(VARIABLE)
    if held:
        return held
    import keyring

    return keyring.get_password(SERVICE, ENTRY)


def send(message: str) -> str:
    """Send the owner `message`, cut at LONGEST characters, and say `sent`, or `not sent:` and why. It raises
    nothing, so that a script which tells the owner as its last step is not failed by Discord."""
    try:
        where = address()
    except ImportError:
        return "not sent: no credential store"
    except Exception as error:  # its words could hold the webhook's address
        return f"not sent: {type(error).__name__}"
    if not where:
        return "not sent: no credential"
    try:
        post(where, message[:LONGEST])
    except Exception as error:  # its words could hold the webhook's address
        return f"not sent: {type(error).__name__}"
    return "sent"


def main(command: str, arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="Send the owner one message on Discord. Exit 0 when it was sent, and 1 when it was not.",
    )
    parser.add_argument("message", help="the message, of which the first 1,900 characters are sent")
    said = send(parser.parse_args(arguments).message)
    print(said)
    return 0 if said == "sent" else 1
