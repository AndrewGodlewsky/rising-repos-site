"""A stand-in for Lighthouse, which the site eval's tests run in its place.

It takes the arguments Lighthouse takes and answers from a plan that the test writes, so that a test decides
what each run reports. The plan is the JSON file named by FAKE_LIGHTHOUSE_PLAN:

    {"phone": [<answer>, ...], "desktop": [<answer>, ...]}

A run is on the desktop profile when it is given --preset=desktop, and on the phone profile otherwise. Each
run takes the next answer of its profile, and the last answer once they run out. An answer is an object with
any of these:

    "report"  the report to write to --output-path, as JSON
    "exit"    the exit status (0 when left out)
    "print"   text to print, as Lighthouse prints its progress
    "sleep"   seconds to wait before answering, for a run that takes too long

Each run's arguments are added, one JSON line per run, to the file named by FAKE_LIGHTHOUSE_CALLS.
"""

import json
import os
import sys
import time
from pathlib import Path


def main(arguments: list[str]) -> int:
    calls = Path(os.environ["FAKE_LIGHTHOUSE_CALLS"])
    with calls.open("a", encoding="utf-8", newline="\n") as log:
        log.write(json.dumps(arguments) + "\n")
    profile = "desktop" if "--preset=desktop" in arguments else "phone"
    earlier = sum(
        1
        for line in calls.read_text(encoding="utf-8").splitlines()
        if ("--preset=desktop" in json.loads(line)) == (profile == "desktop")
    )
    answers = json.loads(Path(os.environ["FAKE_LIGHTHOUSE_PLAN"]).read_text(encoding="utf-8"))[profile]
    answer = answers[min(earlier, len(answers)) - 1]
    time.sleep(answer.get("sleep", 0))
    if "print" in answer:
        print(answer["print"])
    if "report" in answer:
        (output,) = [
            argument.removeprefix("--output-path=") for argument in arguments if argument.startswith("--output-path=")
        ]
        Path(output).write_text(json.dumps(answer["report"]), encoding="utf-8")
    return answer.get("exit", 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
