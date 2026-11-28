# How well visiting agents use the site today: the baseline

**Date:** 26 and 27 November 2026. Ticket: #156, under the map #151.

This is the yardstick the map weighs every route against, and the one it measures the live work by. Five tasks a
person might give their agent were run against risingrepos.com, each by a fresh agent that could only fetch web pages,
and each answer was scored against the data files. The board was 26 November 2026's, with 304 rows.

## 1. Short answer

Of five tasks, one passed outright, one passed on a summary, one was right but could not be checked, and two failed.

- **A row's language is not in the page's text.** The language is an attribute of the row's markup, which a reading
  tool drops, so "rising repositories in Python" cannot be answered at all.
- **One read takes in about 40% of a board.** The reading tool gave each agent the first 39,967 of the root's 99,115
  characters word for word, ranks 1 to about 125, and a model's summary of the rest. The summary dropped rows and once
  invented an address that the page does not hold; when it was right, the agent could not tell. Only an agent that knew to ask for the page again at an offset read
  it all, and that took three fetches.
- **What a mark means is at the foot of the page.** New is defined in About this board, after the last row, so an
  agent reaches the definition only through the summary.
- **A repository's history is out of reach.** It is in no page's text, and the only route is to open each earlier
  board day, up to 119 pages.
- **The search and the filters run only in a browser.** Every agent read the rows by hand.

## 2. The tasks and their results

Each agent was Claude Code's `web-fetch` subagent on Sonnet, given only the request below and told to start at
`https://risingrepos.com/`, to fetch nothing but that site, and to report every fetch and the tool's note on it. The
right answers come from `truth.py` over `site-data/boards/days/`.

| # | The person's request | The right answer | Result | Fetches | Read word for word |
| --- | --- | --- | --- | ---: | ---: |
| 1 | "list today's top 5 rising GitHub repositories written in Python, with how many stars each gained" | Ranks 3, 7, 8, 9, and 14: SandAI-org/MAGI-2-preview, Jeomon/Windows-Use, zcyoung2000/douban-backup, openJiuwen-ai/jiuwenswarm, perixtar/Tech-OA-Interview-Questions | **Failed.** No row's language was in the text, and the filter needs a browser | 1 | 39,967 |
| 2 | "find me rising GitHub repositories that work with PDF files … List every one you can find on today's board" | The 5 rows whose name or description mentions PDF: ranks 43, 100, 131, 143, and 282 | **Passed.** All five, with sensible near matches, after reading the page in three parts by offset | 3 | 99,115 |
| 3 | "What exactly does New mean there?" | "New means under a name on none of the boards before this one, back to the first on 29 July 2026" | **Passed on a summary.** The words were right, but came from the summary, so the agent could not be sure of them | 2 | 44,442 |
| 4 | "has pallets/flask been on earlier boards before today? On how many, and what was its best rank?" | 17 earlier board days, the first on 3 August 2026, best rank 1 | **Failed.** It found 25 November, at rank 182, which is right, and stopped: the rest needs up to 119 fetches | 4 | 93,843 |
| 5 | "which repositories are ranked 280 to 285 on today's board?" | tensorflow/tensorflow, bitwize-music-studio/claude-ai-music-skills, happycola233/tchMaterial-parser, AdventDevInc/kudu, fzn0x/idx, paullarionov/claude-certified-architect | **Right, but unchecked.** All six came from the summary, never from the page's text | 4 | 129,335 |

The fourteen fetches read 406,702 characters word for word to answer five questions, and only two answers rest on
text the agent saw.

## 3. Measured without an agent

`measure_window.py` fetches the live pages, turns each into text with the head, styles, and scripts dropped, and
checks what falls inside a reading limit. Its conversion is an approximation: it gave 77,267 characters for a root the
real tool counted at 99,115, so its window counts read high and are not used above.

- The root was 352,637 bytes.
- Of the 286 rows whose markup carries a language, 27 name it anywhere in their text, and only because their
  description happens to.
- New is defined in the last 620 characters of the text this script makes of the root, after every row.
- How it works is 4,475 characters, and History 9,450: each is read whole in one fetch.

## 4. What the tool did

Claude Code's `web-fetch` subagent read the first 39,967 characters of a 99,115-character page word for word, then gave
a model's summary of the remaining 59,148, and said: "The verbatim page text stops here, 39967 of 99115 characters in;
re-fetching this URL returns the same split." An agent that asked again at an offset of 39,967 and then 79,934 read the
whole page. The tool's documentation says the subagent reads pages of up to about 48,000 characters in full (#153);
this page is twice that.

An agent cannot tell a right summary from a wrong one. One summary named jub0t/Concat, at +1,297, as the day's biggest
gain; it is, at rank 297, but the agent that read it could not check it and set it aside. Another gave the board's
previous-day link as `rising-repos.example`, an address the page does not hold.

## 5. Running it again

1. Pick the board day and a repository that has been on many earlier boards, and run
   `python truth.py <site-data/boards/days> <board day> <repository>` for the right answers.
2. Start five fresh agents with only a web-fetch tool, each with one request from the table, word for word, starting
   at `https://risingrepos.com/`, told to fetch nothing but that site and to report every fetch and the tool's note.
3. Score each as passed, passed on a summary, right but unchecked, or failed, and record its fetches and the characters
   it read word for word.
4. Run `python measure_window.py <out.json>` for the counts that need no agent.

A route that serves visiting agents well turns the two failures into passes, and the summaries into text the agent
reads itself, in fewer fetches.
