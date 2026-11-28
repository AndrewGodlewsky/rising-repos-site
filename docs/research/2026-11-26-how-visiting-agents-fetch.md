# How visiting agents fetch and read a page: what the primary sources say

**Date:** 26 November 2026. Ticket: #153, under the map in #151.

The question is how the visiting agents people use in November 2026 fetch and read a page: how much of it they read,
whether they see the `<head>`, whether they look for `/llms.txt`, whether they can read JSON or Markdown, whether they
can run code over what they fetch, whether they can use an MCP server their person has not added, and what
user-agent string they send. Every page below was fetched on 26 November 2026 and its text read for the point cited.
Nothing was installed, and no agent was run against the site. Where a point is marked "unconfirmed:", no primary
source read for this note states it. A "Here" sentence is my reading of the sources against this site.

## 1. Short answer

1. Reading limits are published for only two tools. Claude Code's WebFetch reads the first 100,000 characters of a page
   when Claude calls it, which matches the 100,000 of 107,563 characters measured on the root on 25 November 2026
   ([S1](#sources)). Gemini's URL context accepts up to 34 MB per URL ([S9](#sources)). The Claude API's web fetch tool
   truncates at an optional `max_content_tokens` and publishes no default ([S5](#sources)). Perplexity says only that
   content "may be truncated for longer pages" ([S11](#sources)). For ChatGPT and Cursor no limit is published.
2. Most of these tools hand the model converted text, not the page. Claude Code's WebFetch gives most pages to a
   second, smaller model that answers a question about them, so the main model usually never sees the page itself
   ([S1](#sources)). No source says whether a `<link rel="alternate">` or JSON-LD survives conversion in any tool.
3. Claude Code's WebFetch is the one tool whose documentation says it asks for Markdown: it sends a `User-Agent`
   beginning `Claude-User` and an `Accept` header that prefers Markdown over HTML ([S1](#sources)). No other tool's
   documentation says it sends `Accept: text/markdown`.
4. No vendor documentation read says its agent looks for `/llms.txt` on its own. Google says Google Search ignores it
   ([S14](#sources)). Claude Code's own documentation pages open with a line pointing agents to that site's
   `llms.txt` ([S1](#sources)), which shows that publishers use it and not that an agent looks for it unprompted.
5. The agents that fetch from the vendor's servers, not the person's machine, are bound to the address they are given.
   The Claude API's web fetch tool can fetch only a URL that already appeared in the conversation, and a URL Claude
   writes in its own output does not count ([S5](#sources)). URLs from earlier search or fetch results also count. Whether a link
   inside the text of a fetched page counts: unconfirmed.
6. Two agents can run code over a fetch. The Claude API's web fetch tool (version `web_fetch_20260209` and later) lets
   Claude write and run code to filter the fetched content before it enters context ([S5](#sources)). Claude Code can
   use `curl` through Bash when Bash is allowed ([S1](#sources)).
7. JSON is a supported content type for Gemini's URL context ([S9](#sources)). The Claude API's web fetch tool accepts
   only text, HTML, and PDF, and returns `unsupported_content_type` otherwise ([S5](#sources)). Perplexity's tool
   extracts "whatever text content the server returns" ([S11](#sources)).

## 2. The table

Each cell names its source in brackets, listed in section 3. "Unconfirmed:" marks a point no primary source read for this
note states.

| Agent | How much it reads | Sees the `<head>`? | Looks for `/llms.txt`? | JSON or Markdown; sends `Accept: text/markdown`? | Runs code over a fetch? | MCP server its person has not added? | User-agent string |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Claude Code, WebFetch** | First 100,000 characters when Claude calls it. A `web-fetch` subagent reads pages of up to about 48,000 characters in full. Claude can ask for the next part (v2.1.290 or later). Copy kept for 15 minutes [S1] | Unconfirmed: no source says whether the head survives the conversion to text. Most pages are read by a smaller model, which answers a question about the page [S1] | No source says it does. Unconfirmed [S1] | Yes to Markdown: it sends an `Accept` header that prefers Markdown over HTML so a server can return Markdown directly [S1]. JSON: unconfirmed | Not inside WebFetch. Claude can run `curl` through Bash if Bash is allowed [S1] | Unconfirmed that none are used. The documentation describes MCP servers as ones the person connects [S1] | Begins with `Claude-User` [S1]. The full string: unconfirmed |
| **Claude API, web fetch tool** | Truncates at the optional `max_content_tokens`; the example in the documentation shows 100000, and no default is stated. An average 10 kB page is about 2,500 tokens [S5] | Unconfirmed: the result is a text document with a title [S5] | No source says it does. Unconfirmed | Content types accepted: text, HTML, and PDF only [S5]. `Accept` header: unconfirmed | Yes: from `web_fetch_20260209` on, Claude writes and runs code to filter the fetch before it reaches context [S5] | No: the request must carry `mcp_servers` and a matching `mcp_toolset` [S6] | Unconfirmed: S5 does not state it. Anthropic names the bots `ClaudeBot`, `Claude-User`, and `Claude-SearchBot` and gives no full strings [S7] |
| **Claude.ai** | "Long articles are retrieved in full into the context window" [S8] | Unconfirmed | Unconfirmed | Unconfirmed | Unconfirmed for the web tools | Unconfirmed | Unconfirmed. `Claude-User` is described as supporting users who ask Claude questions [S7] |
| **Claude API, web search tool** | Returns results as encrypted content with a title, URL, and age; citations quote up to 150 characters [S10] | Unconfirmed | Unconfirmed | Unconfirmed | Yes: from `web_search_20260209`, Claude runs code to filter results [S10] | No: as for web fetch [S6] | Unconfirmed; see `Claude-SearchBot` [S7] |
| **ChatGPT** | Unconfirmed: no limit is published. The search tool's context is limited to 128k [S3]. The tool can open a page and search within it (`open_page`, `find_in_page`) [S3] | Unconfirmed | Unconfirmed | Unconfirmed | Unconfirmed | Unconfirmed | `ChatGPT-User/1.0` for user-initiated visits, with the `+https://openai.com/bot` suffix [S2]. The cloud browser (agent) signs its requests (RFC 9421) with `Signature-Agent: "https://chatgpt.com"`, and its user agent is not stated [S4] |
| **Perplexity** | Up to 10 URLs per call. "May be truncated for longer pages"; no threshold [S11] | Unconfirmed | Unconfirmed | Extracts "whatever text content the server returns"; PDFs and binaries may give limited content. Markdown output: unconfirmed. `Accept`: unconfirmed [S11] | Unconfirmed | Unconfirmed | `Perplexity-User/1.0` for user-requested fetches, which generally ignore `robots.txt` [S12] |
| **Gemini, URL context** | Up to 20 URLs per request; 34 MB per URL; fetched content counts as input tokens [S9] | Unconfirmed: the page does not cover it [S9] | Unconfirmed | JSON is a supported text type, as are HTML, plain text, XML, CSV, PDF, and images; Markdown is not named [S9]. `Accept`: unconfirmed | Unconfirmed | Unconfirmed | Not stated for URL context [S9]. Google's user-triggered fetchers page lists `Google-Agent` (agents on Google infrastructure acting on a request), `Google-GeminiNotebook`, and others, without tying `Google-Agent` to the URL context tool [S13] |
| **Codex** | Unconfirmed. Its search runs against an index OpenAI maintains by default and cached mode avoids fetching arbitrary pages live; live mode is a setting [S15] | Unconfirmed | Unconfirmed | Unconfirmed | Runs commands in a sandbox. Whether it fetches a page with them: unconfirmed [S15] | Unconfirmed that none are used. Servers are added by the person, with `codex mcp` [S16] | Unconfirmed |
| **Cursor** | Unconfirmed: no primary page found. Its `@Web` page says Cursor builds a query and gathers results as context [S17] | Unconfirmed | Unconfirmed | Unconfirmed | Unconfirmed | Unconfirmed | Unconfirmed |

## 3. What this means for the site

These are my inferences, and each is labelled by the fact it rests on.

- The root's text is 107,563 characters, and the only published limit for a coding agent is 100,000 ([S1]). So the
  last ranks fall outside a Claude Code read of the root, as the 25 November measurement saw. A shorter first page, or
  a small separate document of the board that a link names near the top, would keep every rank inside that limit.
- A link to a machine-readable page only helps if the agent is told or shown the address, because the Claude API tool
  fetches only URLs that appeared in the conversation ([S5]), and no source says any agent looks for `/llms.txt` or
  follows `<link rel="alternate">` unprompted. The root's visible text is therefore the most reliable place for it.
- Claude Code sends an `Accept` header that prefers Markdown, so a Markdown version served at the same address by
  content negotiation would be seen by that tool and by no other tool in this table ([S1]). Cloudflare documents the
  server side of that exchange and names no client ([S18]).

## 4. What stays unconfirmed

- Whether any agent keeps `<head>` content (a `<link rel="alternate">`, JSON-LD) after converting a page.
- Whether any agent fetches `/llms.txt` on its own.
- Any published read limit for ChatGPT, Claude.ai, Codex, and Cursor, and a truncation threshold for Perplexity.
- The full user-agent strings of Claude Code's WebFetch, the Claude API tools, and Claude.ai. Anthropic publishes
  tokens, not strings, and the Claude Code page gives only a prefix.
- Whether ChatGPT, Gemini, Perplexity, and Cursor can use an MCP server their person has not added. The sources read
  describe servers as added by the person, and none says a server can be added without them.
- Whether any tool other than Claude Code sends `Accept: text/markdown`.
- How Cursor fetches a page at all: the official `@Web` and `@Link` pages found describe search, not fetching.

Two search results were secondary and are not relied on above: a write-up of the Claude Code source reporting the
header string `text/markdown, text/html, */*`, and trade-press reports of Google's `llms.txt` position, which S14
supersedes. The Claude Code source itself was not read.

## Sources

Primary sources, each fetched on 26 November 2026.

- **S1.** Claude Code, tools reference: [WebFetch tool behavior](https://code.claude.com/docs/en/tools-reference),
  and its sections "Fix missing or outdated page content", "The web-fetch subagent", and "Identify WebFetch requests to
  your site". Also the same page's tool table for Bash and `curl`.
- **S2.** OpenAI, [crawlers and user agents](https://developers.openai.com/api/docs/bots): GPTBot,
  OAI-SearchBot, ChatGPT-User.
- **S3.** OpenAI, [web search guide](https://developers.openai.com/api/docs/guides/tools-web-search).
- **S4.** OpenAI Help, [article 11845367](https://help.openai.com/en/articles/11845367), titled "ChatGPT Work's Cloud
  browser allowlisting".
- **S5.** Anthropic, [web fetch tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool).
- **S6.** Anthropic, [MCP connector](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector): "Pass
  `mcp_servers` and a matching `mcp_toolset` in `tools` on each request."
- **S7.** Anthropic, [Does Anthropic crawl data from the web](https://privacy.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler).
- **S8.** Anthropic, [Enabling and using web search](https://support.claude.com/en/articles/10684626-enabling-and-using-web-search).
- **S9.** Google, [URL context](https://aistudio.google.com/docs/url-context) (moved from ai.google.dev).
- **S10.** Anthropic, [web search tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool).
- **S11.** Perplexity, [fetch_url tool](https://docs.perplexity.ai/docs/agent-api/tools/fetch-url-content).
- **S12.** Perplexity, [bots guide](https://docs.perplexity.ai/guides/bots).
- **S13.** Google, [user-triggered fetchers](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers).
- **S14.** Google, [AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide):
  "Google Search itself doesn't use them", of machine-readable files, AI text files, markup, and Markdown.
- **S15.** OpenAI, [Codex web search](https://learn.chatgpt.com/docs/web-search.md).
- **S16.** OpenAI, [Codex CLI](https://learn.chatgpt.com/docs/codex/cli), on MCP servers and `codex mcp`.
- **S17.** Cursor, [`@Web`](https://docs.cursor.com/context/@-symbols/@-web), read only as a search-result summary,
  because the fetch of Cursor's documentation redirected or returned 404.
- **S18.** Cloudflare, [Markdown for Agents](https://developers.cloudflare.com/fundamentals/reference/markdown-for-agents/):
  the origin's HTML is converted when the client sends `Accept: text/markdown`; the limit is 6 MiB of HTML. It names no
  client.
