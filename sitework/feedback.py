"""`feedback`: file what a run taught as issues, and push nothing into the repository.

The look back says how a run could have cost less and what went wrong in the workflow itself
(docs/workflow-plan.md, section 18). Each thing it says is an issue here, so that the owner and another agent can
mend one and close it by itself. A run files one issue for the run as a whole, which holds its digest, and one for
each fault or saving that can be mended alone. A finding that an open issue already holds is added to that issue
as a comment, so that a fault seen in three runs is one issue and not three.

The issue for the run as a whole is a record: it holds the digest, and nothing to mend. So it is closed as soon
as it is filed, and the open issues that carry the label are the ones with something to do. The owner chose that on
25 November 2026, when three of the fifteen open issues were records of runs. A closed issue keeps its digest and
can be searched and linked as an open one can.

An issue is filed with the label `sitework.rules.FEEDBACK` and with no other. `pickup` takes up only an issue that
carries both `site-idea` and `approved`, so none of these is ever built as a feature.

Nothing here commits or pushes. What a run taught was a folder of notes on main until 24 November 2026. A push to
main is a deploy, so that folder needed an exception in the deploy workflow, and two scripts had to know that its
commits had no deploy of their own. An issue needs neither.
"""

import argparse
import codecs
import io
import sys
from pathlib import Path

from sitework import issue, rules, shell

FROM = "From the run on #{run}."
"""The last line of a filed issue's body. It names the feature's issue that the run worked on, so that GitHub
links the two and a reader of either finds the other."""

SEEN_AGAIN = "Seen again in the run on #{run}."
"""The first line of the comment that adds a finding to an issue, for the same reason."""


def read_text(path: Path) -> str:
    """A file's words, whichever of the encodings a shell on Windows writes with `>` it is in, and with the ends
    of its lines as git keeps them."""
    written = path.read_bytes()
    wide = written.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE))
    return written.decode("utf-16" if wide else "utf-8-sig").replace("\r\n", "\n")


def one_line(title: str) -> str:
    """A new issue's title, without the white space at its ends. `feedback list` prints an issue as one line, its
    number and then its title, and the look back reads those lines to see what is already filed. What follows a
    line break in a title would be read there as an issue of its own, and an empty title tells that reader
    nothing, so both are refused while the command's line is read, before anything is asked of GitHub."""
    lines = title.strip().splitlines()
    if len(lines) != 1:
        raise argparse.ArgumentTypeError("a title is one line with words in it")
    return lines[0]


def filed() -> list[dict]:
    """Every open issue that carries the label, oldest first. An issue takes its number when it is opened, so the
    lowest number is the oldest. GitHub gives 30 issues unless it is asked for more."""
    asked = ("--label", rules.FEEDBACK, "--state", "open", "--limit", "1000", "--json", "number,title")
    return sorted(shell.gh_json("issue", "list", *asked), key=lambda there: there["number"])


def show(options: argparse.Namespace) -> int:
    """Print what is already filed, so that the look back adds to an issue and does not file a second one for the
    same fault."""
    found = filed()
    for there in found:
        print(f"#{there['number']} {there['title']}")
    if not found:
        print(f"No open issue carries `{rules.FEEDBACK}`.")
    return 0


def file(options: argparse.Namespace) -> int:
    """Open a new issue with the label, and print its address. Its body is the file's words, then the digest when
    one is given, as `sitework digest` printed it, then the line that names the run. Both files are read before
    GitHub is asked anything, so that a file which cannot be read opens no issue."""
    parts = [read_text(options.file).strip()]
    if options.digest:
        parts.append(read_text(options.digest).strip())
    body = "\n\n".join([*parts, FROM.format(run=options.run)]) + "\n"
    labelled = ("--title", options.title, "--label", rules.FEEDBACK)
    address = shell.gh("issue", "create", *labelled, "--body-file", "-", stdin=body)
    print(address)
    if options.digest:
        # The issue that holds a digest is the run's record, and is closed once it is filed.
        shell.gh("issue", "close", address.rstrip("/").rpartition("/")[2])
    return 0


def add(options: argparse.Namespace) -> int:
    """Add a finding that was seen again to the issue it is filed in, as a comment, and print the comment's
    address. The issue has to be open and to carry the label. A number is easily a wrong one, and without the
    check a finding about the workflow would land on a feature's issue, where the next run of that feature would
    read it as the owner's own words, since agents act under the owner's account."""
    words = read_text(options.file).strip()
    there = issue.read(options.issue)
    if there["state"] != "OPEN":
        why = "is closed"
    elif rules.FEEDBACK not in issue.labels(there):
        why = f"does not carry `{rules.FEEDBACK}`"
    else:
        body = f"{SEEN_AGAIN.format(run=options.run)}\n\n{words}\n"
        print(shell.gh("issue", "comment", str(options.issue), "--body-file", "-", stdin=body))
        return 0
    print(
        f"feedback: #{options.issue} {why}, so nothing was added to it. `feedback list` prints each issue a "
        "finding can be added to, and `feedback file` opens a new one.",
        file=sys.stderr,
    )
    return 1


def main(command: str, arguments: list[str]) -> int:
    prog = f"python -m sitework {command}"
    parser = argparse.ArgumentParser(
        prog=prog,
        description=f"File what a run taught as issues that carry the label `{rules.FEEDBACK}`. Nothing is pushed "
        "into the repository.",
    )
    forms = parser.add_subparsers(dest="form", required=True, metavar="{list,file,add}")
    forms.add_parser(
        "list",
        help="print each open issue that carries the label",
        description=f"Print each open issue that carries the label `{rules.FEEDBACK}` as `#<number> <title>`, "
        "oldest first, so that a finding which is already filed is added to its issue and not filed again.",
    )
    filing = forms.add_parser(
        "file",
        help="open a new issue with the label",
        description=f"Open a new issue that carries the label `{rules.FEEDBACK}`, and print its address. Its body "
        "is the file's words, then the digest when one is given, then a last line that names the run.",
    )
    filing.add_argument("--run", type=int, required=True, metavar="N", help="the number of the feature's issue")
    filing.add_argument("--title", type=one_line, required=True, metavar="T", help="the new issue's title, one line")
    filing.add_argument("--file", type=Path, required=True, metavar="F", help="the file that holds the issue's words")
    filing.add_argument(
        "--digest",
        type=Path,
        metavar="D",
        help="what `sitework digest` printed, for the issue of the run as a whole, which is closed once it is filed",
    )
    adding = forms.add_parser(
        "add",
        help="add a finding that was seen again to its issue",
        description="Add a finding that was seen again to the issue it is filed in, as a comment that begins by "
        f"naming the run, and print the comment's address. An issue that is closed, or that does not carry the "
        f"label `{rules.FEEDBACK}`, is refused and left as it is.",
    )
    adding.add_argument("issue", type=int, metavar="ISSUE", help="the number of the open issue the finding is in")
    adding.add_argument("--run", type=int, required=True, metavar="N", help="the number of the feature's issue")
    adding.add_argument("--file", type=Path, required=True, metavar="F", help="the file that holds the finding")
    options = parser.parse_args(arguments)
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")  # a title may hold a letter the console's own encoding lacks
    try:
        return {"list": show, "file": file, "add": add}[options.form](options)
    except (OSError, UnicodeError) as error:
        print(f"feedback: a file could not be read, so nothing was asked of GitHub: {error}", file=sys.stderr)
        return 1
    except shell.Failed as error:
        print(f"feedback: {error}", file=sys.stderr)
        return 1
