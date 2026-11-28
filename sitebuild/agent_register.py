"""What a reader can see on the site, set against what a visiting agent can get instead (#179, decided in #160).

A column, a filter, and a page are each built for a reader. A later change that gives readers a new one is reminded, by
`tests/test_agent_register.py`, to give a visiting agent its counterpart in the agent route, or to write why it has
none. The route is each board's agent copy (#176), `/llms.txt` (#178), and the query service (#173), which answers at
/api/ from its own repository, AndrewGodlewsky/rising-repos-api, live since 27 November 2026. A filter that searches or
narrows the repositories has its counterpart in the service, which does the same across every repository ever on a
board, by a parameter that `/llms.txt` documents (#180).
"""

PACE_FIGURES = "agent copy: pace"

REGISTER: dict[str, dict[str, str]] = {
    "column": {
        "Rank": "agent copy: rank",
        "Repository": "agent copy: full_name",
        "Description": "agent copy: description",
        "More: why it is on the board": (
            "none: the reason is the row's own figures, which the agent copy's line gives as gained, stars, and pace"
        ),
        "Language": "agent copy: language",
        "Stars gained on the board day": "agent copy: growth",
        "Stars a day over the last 2 days": "agent copy: growth",
        "Against its own pace the last 14 days": PACE_FIGURES,
        "Total stars": "agent copy: stars",
        "Baseline, a day": PACE_FIGURES,
        "Recent, a day": PACE_FIGURES,
        "Growth": (
            "none: the multiple is the score that orders the board, and the agent copy gives the two paces it divides"
        ),
    },
    "filter": {
        "kinds": "agent copy: new",
        "bands": "agent copy: stars",
        "language": "query service: lang",
        "sort": (
            "none: the agent copy lists the rows in rank order with each row's gain, stars, and earlier boards, which"
            " an agent orders by itself"
        ),
        "q": "query service: q",
        "day-q": "query service: q",
        "find": "query service: q",
    },
    "page": {
        "index.html": "llms.txt: Boards as text",
        "days/index.html": "llms.txt: Boards as text",
        "days/{board_day}/index.html": "llms.txt: Boards as text",
        "how-it-works/index.html": "llms.txt: More",
        "for-agents/index.html": "llms.txt: More",
        "baseline/index.html": "none: its figures are the pace that each row of the agent copy gives",
        "404.html": "none: it answers an address that holds no page, and holds nothing to read",
    },
}
"""What a reader sees, by its kind, each with its counterpart for an agent: `agent copy: <field>` of a row of a board's
JSON, or `agent copy: <field>, <field>` for a control that reads two, `query service: <parameter>` for a parameter of
its search that `/llms.txt` names, `llms.txt: <section>`, or `none: <reason>`. A column is named by its heading, a
filter by the `id` of its control, and a page by its path in `PAGES`."""
