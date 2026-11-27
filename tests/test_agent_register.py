"""The register that keeps the agent route in step with the pages (#179).

What a reader sees, a visiting agent can get too, or the register says why it cannot. These build the example's boards
and read what the build wrote, and hold the register to it.
"""

import json
import re
import shutil

from helpers import BuildTest

from sitebuild import PAGES
from sitebuild.agent_register import REGISTER

COUNTERPART = re.compile(r"(agent copy|query service|llms\.txt): (\S.*)|none: (\S.*)")


class TheRegister(BuildTest):
    def seen(self) -> dict[str, set[str]]:
        """What the example's pages show a reader, as it builds with the day's gain and the reasons, and then without
        each, since a board's columns differ with what its file gives."""
        columns, filters = set(), set()
        for dropped in ((), ("gained_1_day", "gained_7_days", "gained_30_days", "star_history"), ("score",)):
            if dropped:
                self.drop_row_fields(*dropped)
            for page in self.build_pages().values():
                columns |= {th.text() for th in page.all("th") if th.attrs.get("scope") == "col"}
                filters |= {
                    element.attrs["id"]
                    for element in page.all()
                    if "id" in element.attrs and (element.tag in ("select", "input") or "segments" in element.classes())
                }
            shutil.rmtree(self.out)
        return {"column": columns, "filter": filters}

    def test_every_column_filter_and_page_the_build_writes_is_in_the_register(self):
        seen = self.seen() | {"page": set(PAGES)}
        missing = [
            f"{kind} {name!r}" for kind, names in seen.items() for name in sorted(names) if name not in REGISTER[kind]
        ]
        self.assertEqual(missing, [], f"not in sitebuild/agent_register.py, for a visiting agent: {missing}")

    def test_each_agent_copy_field_the_register_names_is_in_the_agent_copy(self):
        self.build_pages()
        copy = json.loads((self.out / "latest.json").read_text(encoding="utf-8"))
        fields = set(copy["rows"][0])
        llms = (self.out / "llms.txt").read_text(encoding="utf-8")
        sections = set(re.findall(r"^## (.+)$", llms, re.MULTILINE))
        # The query service answers from its own repository, so its parameters are those /llms.txt documents (#180):
        # the register can name no parameter that a visiting agent is not told of.
        search = llms.split("## Search every repository\n", 1)[1].split("\n## ", 1)[0]
        parameters = set(re.findall(r"\b([a-z]+)=", search))
        known = {"agent copy": fields, "llms.txt": sections, "query service": parameters}
        for kind, entries in REGISTER.items():
            for name, counterpart in entries.items():
                found = COUNTERPART.fullmatch(counterpart)
                if found and found.group(1):
                    with self.subTest(f"{kind} {name}"):
                        for named in found.group(2).split(", "):
                            self.assertIn(named, known[found.group(1)], counterpart)

    def test_the_boards_search_and_language_and_baselines_find_have_their_counterparts_in_the_query_service(self):
        # #180 moved them there once the service was live: it searches every repository ever on a board.
        filters = REGISTER["filter"]
        self.assertEqual(
            (filters["q"], filters["language"], filters["find"]),
            ("query service: q", "query service: lang", "query service: q"),
        )

    def test_every_register_entry_names_a_counterpart_or_a_reason(self):
        self.assertEqual(list(REGISTER), ["column", "filter", "page"])
        for kind, entries in REGISTER.items():
            for name, counterpart in entries.items():
                with self.subTest(f"{kind} {name}"):
                    self.assertRegex(counterpart, COUNTERPART)
