"""`stage` and `digest`: mark in a run's record where each stage begins, and make a digest of the run from it.

Reading a whole run costs about what the run cost, so no agent reads one. An agent's record of its run holds every
call it made and the tokens of every message, so this reads the record of each agent that took part and writes
about a page: where the tokens went, which tools and files were used most, how long the whole suite took, which
checks failed, and where the run stopped. The look back reads that page, and opens a record itself only where the
page points at waste (docs/workflow-plan.md, section 18).

A run finds its own records with `--this-run`, so that no agent has to know where they are kept: the session's
record, and beside it the record of each fresh agent the session started.

The digest is pushed with the run's notes, which are public. So it names a file by its path in the repository,
counts a file outside it without naming it, and takes nothing else from a record but the names of its tools, of
the tests a check chose, of the step the check stopped at, and of a fresh agent's own file: no command, no word
of an agent's, and no folder of the machine the run was made on.
"""

import argparse
import io
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sitework import rules, shell
from sitework.issue import REPOSITORY

STAGES = (*rules.STAGES, "look back")
"""The stages a run marks, in the order it meets them: each one an issue can stop at, and the look back, which
comes after the last of them."""

PICK_UP = "pick up"
"""What the first record holds before its first stage: the choice of the issue, and the claim on it."""

KINDS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
"""The four kinds of token a message is charged for, as the record names them."""

FIGURES = "## Figures"
FIGURES_HEADING = (
    "| Issue | Shape and build | Review | Look back | Every stage | Stopped | Hours from approval to close |"
)
FIGURES_RULE = "| --- | ---: | ---: | ---: | ---: | --- | ---: |"
"""The heading of a feature's figures and the two rows above its own. They never change, so that `notes` can add
the row beneath them to a table that holds a row for every feature. So a mend has no column of its own here: its
tokens are in `Every stage`, and the table of tokens by stage is where they are told apart."""

SUITE = ("unittest discover -s tests", "sitework check")
"""The two checks that run the whole suite, as `check_names` names them. A run of `unittest discover -s tests`
that chooses a part of it, with `-p` or `-k`, has a longer name, and is not one."""

SITEWORK = r"-m\s+sitework\s+"
"""How every command of the workflow is run. A command is read as a call only in this form, so that a sentence
which names one is not taken for it."""
STAGE_CALL = re.compile(SITEWORK + r"stage\s+[\"']?(" + "|".join(name.replace(" ", r"\s+") for name in STAGES) + r")\b")
SITEWORK_CHECK = re.compile(SITEWORK + r"(check|guard|new-tests|criteria|ship|confirm)\b")
STOP = re.compile(SITEWORK + r"stop\b([^&|;\n]*)")
STEP = re.compile(r"^([A-Za-z' ]+): failed after [\d.]+ s\s*$", re.MULTILINE)
"""The line `sitework check` prints for the step it stopped at. A step's name is plain words, so a line that
holds anything else, such as a path, is not read as one."""
UNITTEST = re.compile(r"-m\s+unittest\b((?:[^&|;\n]|&\d)*)")
RUFF = re.compile(r"\bruff\s+(check|format)\b")
WRITTEN = re.compile(r"<<-?\s*([\"']?)(\w+)\1[^\n]*\n.*?^\s*\2\s*$", re.DOTALL | re.MULTILINE)
"""A file's text given to a command in the shell, from the word that opens it to the same word on a line of its
own. It is what a command writes, and not what it runs."""
REDIRECT = re.compile(r"\d*>>?\s*(?:&\d|\S+)|<\s*\S+")
QUIET = {"-v", "--verbose", "-q", "--quiet", "-f", "--failfast", "-b", "--buffer", "-c", "--catch"}
"""The options of unittest that change what it prints or when it gives up, and not which tests it runs."""
CHOOSES = {"-s", "--start-directory", "-p", "--pattern", "-k", "-t", "--top-level-directory"}
"""The options of unittest that choose its tests, each followed by its value."""
NAMEABLE = re.compile(r"[\w.*?\[\]-]+")
"""A value that can be written in the digest: the name of a test or a pattern for one, with no part of a path."""
ENDED = re.compile(r"<task-id>([^<]+)</task-id>")
STATUS = re.compile(r"<status>([^<]+)</status>")

CONFIG, SESSION = "CLAUDE_CONFIG_DIR", "CLAUDE_CODE_SESSION_ID"
"""The two variables Claude Code gives a session: the folder it keeps its records in, and the session's name."""

TIMELINE = '.[] | select(.event == "labeled" or .event == "closed") | [.event, .label.name // "", .created_at] | @tsv'
"""What is kept of an issue's timeline: each label put on it and each close, as a line of three fields."""


@dataclass
class Call:
    """One tool call of a run, and what the record holds of its result."""

    stage: str
    tool: str
    given: dict
    at: datetime
    failed: bool | None = None
    """None while the record holds no result for the call."""
    ended: datetime | None = None
    background: str = ""
    """What the record calls a command that was left to run in the background. Its result line comes at once and
    says only that it started, so its end is the notice that names it."""
    step: str = ""
    """The step a failed run of `sitework check` stopped at, when the record holds what the run printed."""

    @property
    def command(self) -> str:
        return shell_command(self.given)


@dataclass
class Run:
    """What the records of one run hold, gathered once for every part of the digest."""

    records: int = 0
    tokens: dict[str, list[int]] = field(default_factory=dict)
    """Each stage's tokens in the four kinds, in the order the run first met the stages."""
    messages: int = 0
    calls: list[Call] = field(default_factory=list)
    roots: list[str] = field(default_factory=list)
    """Each folder that is the repository: this checkout, and the folder each record's agent was started in."""
    times: list[datetime] = field(default_factory=list)
    agents: list[tuple[str, str, int]] = field(default_factory=list)
    """Each fresh agent: its record's name, the stage it began in, and its tokens of every kind together."""


class NoRecord(Exception):
    """The run's own record cannot be found. The message says which of the two leads to it is missing, and names
    no folder."""


def when(text: str) -> datetime:
    return datetime.fromisoformat(text).astimezone(UTC)


def plain(path: str) -> str:
    return path.replace("\\", "/").rstrip("/")


def tool_calls(line: dict) -> list[dict]:
    """The tool calls in one line of an agent's message."""
    content = line["message"].get("content")
    blocks = content if isinstance(content, list) else []
    return [block for block in blocks if isinstance(block, dict) and block.get("type") == "tool_use"]


def shell_command(given: dict) -> str:
    """The shell command a tool call was given, without the text of any file it writes, or nothing for a call of
    a tool that runs no command."""
    command = given.get("command")
    return WRITTEN.sub("", command) if isinstance(command, str) else ""


def stage_begun(block: dict) -> str | None:
    """The stage a tool call begins, when it is `sitework stage <name>`."""
    called = STAGE_CALL.search(shell_command(block.get("input", {})))
    return " ".join(called[1].split()) if called else None


def first_stage(lines: list[dict]) -> str | None:
    for line in lines:
        if line.get("type") == "assistant":
            for block in tool_calls(line):
                if begun := stage_begun(block):
                    return begun
    return None


def started(record: Path) -> str:
    """When a record's first line was written, as the record writes a time."""
    with record.open(encoding="utf-8") as lines:
        return next((json.loads(line).get("timestamp", "") for line in lines if line.strip()), "")


def this_run() -> list[Path]:
    """The records of the run this is called from: its session's, and then the record of each fresh agent the
    session started, oldest first, so that an agent is read after the one that started it. Claude Code gives a
    session the folder it keeps its records in and the session's own name, and keeps the session's record in one
    folder under `projects`. That folder's name is Claude Code's to choose, so it is found by the record it
    holds, and is never worked out from the folder the agent works in."""
    unset = [name for name in (CONFIG, SESSION) if not os.environ.get(name)]
    if unset:
        raise NoRecord(f"{' and '.join(unset)} {'is' if len(unset) == 1 else 'are'} not set, so this run has no record")
    session = sorted(Path(os.environ[CONFIG], "projects").glob(f"*/{os.environ[SESSION]}.jsonl"))
    if not session:
        raise NoRecord(f"no folder under `projects` in {CONFIG} holds the record of the session {SESSION} names")
    agents = session[0].with_suffix("").glob("subagents/agent-*.jsonl")
    return [session[0], *sorted(agents, key=lambda record: (started(record), record.name))]


def stage_of_start(record: Path, calls: dict[str, Call]) -> str | None:
    """The stage a fresh agent was started in: the stage of the call that started it. Claude Code keeps a file
    beside an agent's record that names that call. Nothing else is read from the file, since what it says of the
    agent's task is the words of the agent that started it, and the digest is public. None for a record with no
    such file, or one started by a call that no record read so far holds."""
    beside = record.with_suffix(".meta.json")
    start = calls.get(json.loads(beside.read_text(encoding="utf-8")).get("toolUseId")) if beside.is_file() else None
    return start.stage if start else None


def read_run(records: list[Path]) -> Run:
    """Read each record once. The first is the record of the agent that ran the feature. Each one after it is a
    fresh agent's. What it did before its first stage call belongs to that stage. When it made no such call, it
    belongs to the stage the agent was started in, so that the reviewer's tokens are the review's, or, when
    nothing says which call started it, to a stage named by its file."""
    run = Run(records=len(records), roots=[plain(str(shell.ROOT))])
    counted: dict[str, tuple[str, list[int], int]] = {}
    calls: dict[str, Call] = {}
    began = {}
    for number, record in enumerate(records):
        with record.open(encoding="utf-8") as text:
            lines = [json.loads(line) for line in text if line.strip()]
        stage = PICK_UP if number == 0 else first_stage(lines) or stage_of_start(record, calls) or record.stem
        began[number] = stage
        started_in = next((line["cwd"] for line in lines if isinstance(line.get("cwd"), str)), None)
        if started_in and plain(started_in) not in run.roots:
            run.roots.append(plain(started_in))
        for line in lines:
            kind = line.get("type")
            if kind == "assistant":
                at = when(line["timestamp"])
                run.times.append(at)
                for block in tool_calls(line):
                    stage = stage_begun(block) or stage
                    calls[block["id"]] = Call(stage, block["name"], block.get("input", {}), at)
                # One message is written as several lines, each with the whole message's tokens, so it is
                # counted once, and in the stage its last line was in: the line with a stage call may not be
                # its first.
                message = line["message"]
                counted[message["id"]] = (stage, [message["usage"].get(kind_, 0) for kind_ in KINDS], number)
            elif kind == "user" and isinstance(line["message"].get("content"), list):
                kept = line.get("toolUseResult")
                for block in line["message"]["content"]:
                    call = calls.get(block.get("tool_use_id")) if block.get("type") == "tool_result" else None
                    if call:
                        call.failed = bool(block.get("is_error"))
                        call.ended = when(line["timestamp"])
                        call.background = kept.get("backgroundTaskId", "") if isinstance(kept, dict) else ""
                        stopped = STEP.search(printed(block)) if SUITE[1] in check_names(call.command) else None
                        call.step = stopped[1] if stopped else ""
            elif kind == "queue-operation" and line.get("operation") == "enqueue":
                notice = line.get("content") if isinstance(line.get("content"), str) else ""
                named, status = ENDED.search(notice), STATUS.search(notice)
                for call in calls.values():
                    if named and status and call.background == named[1]:
                        call.background, call.ended = "", when(line["timestamp"])
                        call.failed = status[1] != "completed"
    used = Counter()
    for stage, tokens, number in counted.values():
        total = run.tokens.setdefault(stage, [0, 0, 0, 0])
        run.tokens[stage] = [had + more for had, more in zip(total, tokens, strict=True)]
        used[number] += sum(tokens)
    run.agents = [(record.stem, began[number], used[number]) for number, record in enumerate(records) if number]
    run.messages = len(counted)
    run.calls = list(calls.values())
    return run


def printed(block: dict) -> str:
    """What a command printed, from a result the record keeps as text or as a list of parts."""
    content = block.get("content")
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content if isinstance(content, str) else ""


def in_repository(path: str, roots: list[str]) -> str | None:
    """`path` as the repository names it, or None for a file outside the repository. A drive's letter is written
    in either case, so the folders are compared without regard to it."""
    path = plain(path)
    for root in roots:
        if path.casefold().startswith(root.casefold() + "/"):
            name = path[len(root) + 1 :]
            return None if ".." in name.split("/") else name
    return None


def lines_of(name: str) -> str:
    """How many lines the file has in this checkout, or a dash when the checkout holds no such file."""
    path = shell.ROOT / name
    return f"{len(path.read_bytes().splitlines()):,}" if path.is_file() else "-"


def check_names(command: str) -> list[str]:
    """Each check a shell command runs. A check is named by the words that choose its tests and by nothing else
    of the command: a run of unittest by `discover`, the options in `CHOOSES` with their values, and the tests it
    names, up to the first word that is none of those. So the name holds no folder, and no words of the agent's."""
    names = [f"sitework {name}" for name in SITEWORK_CHECK.findall(command)]
    for arguments in UNITTEST.findall(command):
        words = [word.strip("\"'") for word in REDIRECT.sub(" ", arguments).split()]
        name, value_of = ["unittest"], None
        for word in words:
            if value_of:
                name += [word] if NAMEABLE.fullmatch(word) else []
                value_of = None
            elif word in CHOOSES:
                name.append(word)
                value_of = word
            elif word == "discover" or re.fullmatch(r"tests?[\w.]*", word):
                name.append(word)
            elif word not in QUIET:
                break
        names.append(" ".join(name))
    names += [f"ruff {name}" for name in RUFF.findall(command)]
    return list(dict.fromkeys(names))


def failed_checks(calls: list[Call]) -> list[str]:
    """A line for each time a check began to fail: how many tries it took to pass, or that it did not, and each
    step that `sitework check` stopped at on the way."""
    failing: dict[str, dict] = {}
    found = []
    for call in calls:
        name = " and ".join(check_names(call.command))
        if not name or call.failed is None or call.background:
            continue
        if call.failed and name not in failing:
            failing[name] = {"name": name, "stage": call.stage, "failed": 0, "passed": False, "steps": []}
            found.append(failing[name])
        if call.failed:
            failing[name]["failed"] += 1
            if call.step and call.step not in failing[name]["steps"]:
                failing[name]["steps"].append(call.step)
        elif name in failing:
            failing.pop(name)["passed"] = True
    lines = []
    for check in found:
        at = "at " + ", then at ".join(check["steps"]) if check["steps"] else ""
        if check["passed"]:
            outcome = f"{'failed ' + at + ', and ' if at else ''}passed on try {check['failed'] + 1}"
        else:
            times = "1 time" if check["failed"] == 1 else f"{check['failed']} times"
            outcome = f"failed {times}{', ' + at if at else ''}, and did not pass in the record"
        lines.append(f"- `{check['name']}`, in {check['stage']}: {outcome}.")
    return lines


def took(call: Call) -> list[str]:
    """How long one run of the whole suite took, and how it ended, as far as the record shows."""
    if call.failed is None or call.background:
        return [call.stage, "-", "no result"]
    seconds = round((call.ended - call.at).total_seconds())
    result = "passed" if not call.failed else f"failed at {call.step}" if call.step else "failed"
    return [call.stage, f"{seconds // 60}m {seconds % 60:02}s", result]


def hours_to_close(issue: int) -> float | None:
    """The hours from the idea's approval to the close of its issue, asked of GitHub. The approval is the last
    time the label was put on before the close, so that an idea approved twice is timed from the approval that
    led to this run. None for an issue that was never approved, or is still open."""
    timeline = shell.gh("api", "--paginate", f"{REPOSITORY}/issues/{issue}/timeline", "--jq", TIMELINE)
    events = [line.split("\t") for line in timeline.splitlines() if line.strip()]
    closes = [when(at) for event, _, at in events if event == "closed"]
    if not closes:
        return None
    approvals = [
        when(at)
        for event, label, at in events
        if (event, label) == ("labeled", rules.APPROVED) and when(at) <= max(closes)
    ]
    return (max(closes) - max(approvals)).total_seconds() / 3600 if approvals else None


def table(heading: list[str], rows: list[list[str]], numbers_from: int = 1) -> list[str]:
    """A Markdown table whose columns from `numbers_from` on are numbers, set to the right."""
    rule = ["---" if number < numbers_from else "---:" for number in range(len(heading))]
    return ["| " + " | ".join(row) + " |" for row in (heading, rule, *rows)]


def render(run: Run, issue: int | None = None, hours: float | None = None) -> str:
    """The digest of a run, as Markdown."""
    tokens = {stage: [*kinds, sum(kinds)] for stage, kinds in run.tokens.items()}
    total = [sum(column) for column in zip(*tokens.values(), strict=True)] if tokens else [0] * 5
    stops = [call for call in run.calls if STOP.search(call.command)]
    suite = [call for call in run.calls if set(SUITE) & set(check_names(call.command))]
    reads = [in_repository(call.given.get("file_path") or "", run.roots) for call in run.calls if call.tool == "Read"]
    most_read = Counter(name for name in reads if name).most_common(10)
    tools = Counter(call.tool for call in run.calls).most_common()

    def all_of(*stages: str) -> str:
        return f"{sum(tokens[stage][-1] for stage in stages if stage in tokens):,}"

    span = f", from {min(run.times):%Y-%m-%d %H:%M} to {max(run.times):%Y-%m-%d %H:%M} UTC" if run.times else ""
    records = "1 record" if run.records == 1 else f"{run.records} records"
    lines = [
        f"# Digest of the run on #{issue}" if issue else "# Digest of a run",
        "",
        f"Made from {records}: {run.messages:,} messages and {len(run.calls):,} tool calls{span}.",
        "",
        "## Tokens by stage",
        "",
        *table(
            ["Stage", "Input", "Output", "Cache written", "Cache read", "All"],
            [[stage, *(f"{count:,}" for count in counts)] for stage, counts in [*tokens.items(), ("Total", total)]],
        ),
        "",
        "## Fresh agents",
        "",
        *(
            table(["Record", "Began in", "All"], [[name, stage, f"{used:,}"] for name, stage, used in run.agents], 2)
            if run.agents
            else ["None was started."]
        ),
        "",
        "## Tools",
        "",
        ", ".join(f"{tool} {count:,}" for tool, count in tools) + "." if tools else "None was called.",
        "",
        "## Files read most often",
        "",
        *table(["File", "Reads", "Lines"], [[name, f"{count:,}", lines_of(name)] for name, count in most_read]),
        "",
        f"{reads.count(None):,} reads were of files outside the repository, which are not named.",
        "",
        "## The whole suite",
        "",
    ]
    if suite:
        lines += [f"It ran {len(suite)} times." if len(suite) > 1 else "It ran once.", ""]
        lines += table(["Stage", "Took", "Result"], [took(call) for call in suite], numbers_from=3)
    else:
        lines += ["It did not run."]
    lines += ["", "## Checks that failed", "", *(failed_checks(run.calls) or ["None."])]
    lines += ["", "## Stops", ""]
    for call in stops:
        # `sitework stop` is given `--data` when the issue waits for a field, and stops for the owner otherwise.
        waits_for = "data" if "--data" in STOP.search(call.command)[1].split() else "the owner"
        lines += [f"- in {call.stage}, at {call.at:%Y-%m-%d %H:%M} UTC, for {waits_for}."]
    lines += [] if stops else ["None."]
    figures = [
        f"#{issue}" if issue else "-",
        all_of("shape", "build"),
        all_of("review"),
        all_of("look back"),
        f"{total[-1]:,}",
        "yes" if stops else "no",
        "-" if hours is None else f"{hours:.1f}",
    ]
    lines += ["", FIGURES, "", FIGURES_HEADING, FIGURES_RULE, "| " + " | ".join(figures) + " |", ""]
    lines += ["A figure in tokens is the sum of the four kinds. Every stage includes the pick up."]
    return "\n".join(lines)


def digest(records: list[Path], issue: int | None = None) -> str:
    """The digest of the run these records hold. With an issue, it asks GitHub for the hours the idea took."""
    return render(read_run(records), issue, hours_to_close(issue) if issue else None)


def begin_stage(command: str, arguments: list[str]) -> int:
    """Print the stage's name, so that the call and its place are in the run's record. It does nothing else."""
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        description="Mark in the run's record that a stage begins. The digest reads the mark, and nothing else does.",
    )
    parser.add_argument("name", nargs="+", help="the stage: " + ", ".join(STAGES))
    name = " ".join(parser.parse_args(arguments).name)
    if name not in STAGES:
        parser.error(f"{name!r} is not a stage. The stages are: {', '.join(STAGES)}")
    print(f"stage: {name}")
    return 0


def main(command: str, arguments: list[str]) -> int:
    if command == "stage":
        return begin_stage(command, arguments)
    parser = argparse.ArgumentParser(
        prog=f"python -m sitework {command}",
        usage="%(prog)s [-h] [--issue N] (--this-run | RECORD [RECORD ...])",
        description="Make a one-page digest of a run from its record, as Markdown on standard output. Give "
        "--this-run or the records, and not both.",
    )
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument(
        "--this-run",
        action="store_true",
        help=f"read the records of the run this is called from: its session's, then each fresh agent's. They are "
        f"found from {CONFIG} and {SESSION}",
    )
    which.add_argument(
        "records",
        nargs="*",
        type=Path,
        default=[],
        metavar="RECORD",
        help="the record of each agent that took part, the one that ran the feature first",
    )
    parser.add_argument(
        "--issue",
        type=int,
        metavar="N",
        help="the run's issue: its number goes in the figures, with its hours from approval to close",
    )
    options = parser.parse_args(arguments)
    try:
        run = read_run(this_run() if options.this_run else options.records)
    except NoRecord as error:
        print(f"digest: {error}.", file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError) as error:
        print(f"digest: a record could not be read: {error}", file=sys.stderr)
        return 1
    hours, unanswered = None, None
    if options.issue:
        try:
            hours = hours_to_close(options.issue)
        except shell.Failed as error:
            unanswered = error
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")  # a file's name may hold a letter the console's encoding lacks
    print(render(run, options.issue, hours))
    if unanswered:
        print(
            f"digest: GitHub did not give the issue's timeline, so the hours are left out.\n{unanswered}",
            file=sys.stderr,
        )
        return 1
    return 0
