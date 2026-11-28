# Which crawlers feed which AI answers, and how a new site gets in

Research for issue #154, part of the planning effort in #151. Gathered on 2026-11-26. Each fact names its source by number in the list at the end. A fact that no primary source confirms is marked "unconfirmed:".

## Short answer

- No operator offers a form that submits a site to an AI answer. Each answer surface draws on a search index, and a site gets into the index by being crawlable and discoverable. Google's own page says a page needs to be indexed and eligible for a snippet, and nothing more [1].
- The practical entry points are a `sitemap.xml` with a `Sitemap:` line in `robots.txt`, a verified property in Google Search Console and in Bing Webmaster Tools, and IndexNow for Bing and the other engines that take it [2][3][5][6].
- Three operators run a crawler that exists to feed answers: OpenAI (`OAI-SearchBot`), Anthropic (`Claude-SearchBot`), and Perplexity (`PerplexityBot`) [7][8][9]. Allowing each in `robots.txt` is the only stated condition for appearing.
- Google and Microsoft draw their answers from the index their ordinary crawlers build, `Googlebot` and `bingbot`. Google-Extended does not govern Search or, as far as the page says, AI Overviews [10][1].
- Brave runs its own index and a crawler with no user-agent token of its own, so a site cannot single it out in `robots.txt` [11][12].
- Cloudflare's content signals (`search`, `ai-input`, `ai-train`) are preferences only. Cloudflare says the file does not stop a crawler, and its pages name no operator that honours the signals [13][14].
- This site has no `sitemap.xml` and a `robots.txt` with no rules, so today nothing tells any index that the site exists beyond links from elsewhere. That is the gap to close.

## Table, one row per answer surface

| Surface | Crawler (user-agent token) | Index the answers draw on | How a new site gets in | Controls |
| --- | --- | --- | --- | --- |
| Google AI Overviews and AI Mode | `Googlebot` is the control Google names for crawling [1]. Which fetcher feeds these features: unconfirmed:, the page names only Googlebot's robots.txt rules. | Google Search's index [1] | The page must be indexed and eligible for a snippet. No special files, schema, or AI text files are needed [1]. Sitemap submitted in Search Console, or a `Sitemap:` line in `robots.txt` [2][3]. Google offers no URL-submission route to AI features. | `noindex` removes the page from Search [15]. `nosnippet` and `max-snippet` also limit use as direct input to AI Overviews and AI Mode [15]. `data-nosnippet` excludes parts of a page from snippets; the page gives no AI detail for it [15]. `Google-Extended` does not affect inclusion in Search or ranking [10]. |
| Google Gemini grounding and training | `Google-Extended` is a robots.txt token only, with no user-agent string of its own; crawling uses existing Google agents [10] | Google Search's index, for grounding in Gemini Apps and Vertex AI [10] | Same as Google Search [10] | `Google-Extended` covers training of future Gemini models and grounding in Gemini Apps and Grounding with Google Search on Vertex AI [10]. Google says it will support an AIPREF training signal in early 2027 [10]. |
| ChatGPT search | `OAI-SearchBot` for search, `GPTBot` for training, `ChatGPT-User` for user-triggered fetches [7] | OpenAI says ChatGPT "sometimes partners with other search providers" and does not name them [16]. Which providers: unconfirmed:. | Allow `OAI-SearchBot` in `robots.txt`, and let the host or CDN permit OpenAI's published searchbot IP addresses [7][16]. A change can take about 24 hours to be seen [7]. OpenAI describes no submission route. | Opting out of `OAI-SearchBot` keeps a site out of ChatGPT search answers, though it can still appear as a navigational link [7]. Each setting is independent of the others [7]. `ChatGPT-User` is not used to decide search appearance, and robots.txt rules may not apply to it [7]. |
| Claude web search | `Claude-SearchBot` for search indexing, `Claude-User` for user-initiated fetches, `ClaudeBot` for training [8] | Unconfirmed:. Anthropic's pages that I read say "the search provider" and do not name it for the Claude apps or API [17][18]. Secondary reporting names Brave [19]. | Do not block `Claude-SearchBot`; Anthropic says blocking it "may reduce your site's visibility" in search results [8]. No submission route described. | Anthropic says its bots honour robots.txt, and supports `Crawl-delay` [8]. Blocking `Claude-User` stops retrieval in answer to a user query [8]. A rule naming `ClaudeBot` takes priority for training preferences [8]. Anthropic does not recommend blocking by IP address [8]. |
| Perplexity | `PerplexityBot` surfaces and links sites in results and is not used for foundation-model training; `Perplexity-User` fetches for a user's question [9] | Perplexity's own search results. Whether this is its own index: unconfirmed:, the pages I read do not describe the index. | Allow `PerplexityBot` in `robots.txt` and permit its published IP ranges [9]. No submission route described. | `Perplexity-User` "generally ignores robots.txt rules" because a user asked for the fetch [9]. Perplexity does not say whether it reads content signals: unconfirmed:. |
| Microsoft Copilot and Bing's AI summaries | `bingbot`. Microsoft's crawler help page could not be read in this session, so the token is unconfirmed: from a primary page here. | Bing's index. Microsoft says citations in Copilot and Bing's AI summaries are shown in the AI Performance report, which covers "select partner integrations" [20]. | Verify the site in Bing Webmaster Tools, submit a sitemap there or list it in `robots.txt`, and use IndexNow for changes [5][20]. Bing says freshness affects how fast updates reach search results and AI answers, and that no tool guarantees how content appears in AI answers [5]. | Bing says it respects the preferences a content owner sets in `robots.txt` and other supported controls [20]. Page-level citation counts "reflect how often pages are cited, not page importance, ranking, or placement" [20]. |
| Brave (Brave Search and its answers) | No distinct token. Brave "does not advertise a differentiated user agent" and follows Googlebot's limits: where Googlebot cannot crawl, Brave's bot will not [12] | Brave's own index, over 30 billion pages, which also takes data from opted-in browser users [11] | Be crawlable by Googlebot [12]. Brave has a page to submit a URL for re-fetching or report a missing page [12]. Whether it accepts a first submission of a new site: unconfirmed:, the page describes only re-fetching and removal. | `noindex` delists a page once Brave re-fetches it. `robots.txt` is not used to prevent indexing [12]. |

## What the controls do, and who honours them

- **Content signals.** `search` covers building an index and returning links and short excerpts, not AI summaries. `ai-input` covers feeding content to a model at answer time. `ai-train` covers training [13][14]. Cloudflare's own sample syntax is `Content-Signal: search=yes, ai-train=no` [14].
- **Cloudflare's defaults.** A free-plan zone with no `robots.txt` of its own gets only the commented policy, with no rules and no signals [14]. That matches this site's file.
- **Who honours them.** Cloudflare's pages say compliance is voluntary and "some companies might simply ignore them", and name no operator that honours the signals [13][14]. The OpenAI, Anthropic, Perplexity, Google, and Bing pages I read do not mention content signals: unconfirmed: for each of them. Google's AIPREF plan for 2027 is a separate mechanism [10].
- **robots.txt.** OpenAI, Anthropic, Perplexity, and Bing state that they honour it for their crawlers, with the user-triggered fetchers (`ChatGPT-User`, `Perplexity-User`) as the stated exceptions [7][8][9][20]. Anthropic says its user-initiated agent is also covered by its general policy [8].
- **Consequence for this site.** The site wants to be found, so it needs no `Disallow` rule. Leaving the Cloudflare notice alone is harmless, but it expresses no preference. A `Content-Signal: search=yes, ai-input=yes, ai-train=no` line would state one, with the limits above.

## Steps for a new site's owner

1. Publish a `sitemap.xml` of every page, with an honest `lastmod` per page, and add a `Sitemap:` line to `robots.txt` [3][5].
2. Allow the answer crawlers in `robots.txt`, or leave no rule that blocks them: `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, `Googlebot`, `bingbot` [1][7][8][9]. Check that Cloudflare's bot settings do not block them, and that OpenAI's and Perplexity's published IP ranges are let through [7][9][16].
3. Verify the site in Google Search Console and submit the sitemap there [2].
4. Verify the site in Bing Webmaster Tools and submit the sitemap there [5][20]. Importing a site from Search Console is reported only by secondary coverage: unconfirmed:.
5. Set up IndexNow: host a key file at the site root and send changed URLs to one participating engine, which shares them with the others [6][21]. Google does not take part in IndexNow as far as the pages I read say: unconfirmed:.
6. Keep every page indexable and snippet-eligible: no `noindex`, no `nosnippet`, no `max-snippet:0` [1][15].
7. If a page is missing from Brave, use Brave's submit page [12].
8. Decide whether to state content signals. Treat them as a statement of preference, not a control [13][14].
9. Watch Bing's AI Performance report for citations. Google, OpenAI, Anthropic, and Perplexity offer no equivalent report in the pages read: unconfirmed:.

## What stays unconfirmed

- Which index Claude's search uses. Anthropic's pages read here do not name it. A 2025 report that Anthropic listed Brave Search as a subprocessor is secondary [19].
- Which search providers ChatGPT search partners with [16].
- Which Google fetcher supplies AI Overviews and AI Mode, and whether `Google-Extended` has any effect on them. Google's page on `Google-Extended` does not mention either feature [10].
- Whether Perplexity runs its own index.
- Whether any answer operator reads Cloudflare's content signals.
- The `bingbot` token and Microsoft's crawler documentation, because Microsoft's crawler help page returned no body text when fetched.
- Whether Brave accepts a first submission of a new site.
- Whether Google supports IndexNow.

## Sources

Primary sources were read on 2026-11-26 through a page-fetch tool that summarises each page, so quotations are the tool's extracts and not the full page text. Source 19 is secondary and stands alone for nothing in this note.

1. Google Search Central, "AI features and your website": https://developers.google.com/search/docs/appearance/ai-features
2. Google Search Console Help, "Build and submit a sitemap": https://support.google.com/webmasters/answer/7451001
3. Google Search Central, "Sitemaps overview": https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview
4. Not used.
5. Bing Webmaster blog, "Keeping Content Discoverable with Sitemaps in AI Powered Search", July 2025: https://blogs.bing.com/webmaster/July-2025/Keeping-Content-Discoverable-with-Sitemaps-in-AI-Powered-Search
6. IndexNow documentation: https://www.indexnow.org/documentation
7. OpenAI, "Overview of OpenAI crawlers": https://developers.openai.com/api/docs/bots
8. Anthropic Help Center, "Does Anthropic crawl data from the web, and how can site owners block the crawler?": https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler
9. Perplexity docs, "Perplexity crawlers": https://docs.perplexity.ai/guides/bots
10. Google Search Central, "Google's common crawlers": https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers
11. Brave, "Brave Search API: what sets it apart": https://brave.com/search/api/guides/what-sets-brave-search-api-apart/
12. Brave Search help, "Brave Search crawler": https://search.brave.com/help/brave-search-crawler
13. Cloudflare docs, "Managed robots.txt" and the Content Signals Policy: https://developers.cloudflare.com/bots/additional-configurations/managed-robots-txt/
14. Cloudflare blog, "Content Signals Policy": https://blog.cloudflare.com/content-signals-policy/
15. Google Search Central, "Robots meta tag and X-Robots-Tag": https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag
16. OpenAI Help Center, "ChatGPT search": https://help.openai.com/en/articles/9237897-chatgpt-search
17. Claude API docs, "Web search tool": https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool
18. Claude for Government, "Security and data handling", section "Web search and web fetch" (says "the search provider" without naming it): https://claude.com/docs/government/security/security-and-data-handling.md
19. Secondary: TechCrunch, "Anthropic appears to be using Brave to power web search for its Claude chatbot", 21 March 2025: https://techcrunch.com/2025/03/21/anthropic-appears-to-be-using-brave-to-power-web-searches-for-its-claude-chatbot/ (found in a search; not fetched)
20. Bing Webmaster blog, "Introducing AI Performance in Bing Webmaster Tools Public Preview", February 2026: https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview
21. Bing, "IndexNow": https://www.bing.com/indexnow
