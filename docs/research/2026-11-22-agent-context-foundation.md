# A context foundation for unattended coding agents: what the primary sources say

**Date:** 22 November 2026.

**Question.** What do primary sources recommend for the documents and checks
that hold a repository's judgement and standards, so that coding agents carrying
an issue to a deployed change without a person watching stay on track and do not
break the repository? "Context foundation" means agent instruction files, coding
standards, architecture decision records (ADRs), a glossary, architecture or
design documents, and rules enforced by tooling rather than by prose.

**Method.** Every source was read on 22 November 2026: web pages through a fetch
tool that returns a model-made digest, with each quotation requested verbatim in
a second pass, and Matt Pocock's skills from an installed copy whose skill names
match the [upstream repository](https://github.com/mattpocock/skills). Studies
were found by searching for measured effects of context files, ADRs, glossaries
and linter feedback on coding agents. Sections 1 to 7 report the sources;
section 8 is my own inference.

## 1. What the sources agree on

1. **Keep the always-loaded file short, and limit it to what the agent cannot
   find by itself.** Claude Code: "Only write down what Claude can't find by
   reading the repo, or what it would otherwise spend time rediscovering every
   session" ([best practices](https://code.claude.com/docs/en/best-practices)).
   OpenAI keeps "A short AGENTS.md (roughly 100 lines)" ([harness
   engineering](https://openai.com/index/harness-engineering/)). Pocock's
   `retro` skill: these files "should be used incredibly sparingly, usually only
   for navigation pointers to other files". The one controlled study of content
   agrees: files should "only contain specific additional instructions beyond
   what is already available in the codebase" ([Gloaguen et
   al.](https://arxiv.org/html/2602.11988)).
2. **Make the entry file a map, and load detail only when a task needs it.**
   OpenAI treats AGENTS.md "as the table of contents" for `docs/` ([harness
   engineering](https://openai.com/index/harness-engineering/)); Agent Skills
   load metadata always and the rest on demand ([Skills
   overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview));
   Claude Code, Codex and Copilot support per-directory or path-scoped files
   (section 4).
3. **Give the agent a pass-or-fail check, and put rules without exceptions into
   tooling.** Claude Code: "If something has to happen every time, make it a
   hook, a deny rule, or a managed setting" ([best
   practices](https://code.claude.com/docs/en/best-practices)). OpenAI enforces
   architecture "mechanically via custom linters ... and structural tests"
   ([harness engineering](https://openai.com/index/harness-engineering/)).
   Codex: "reserve formatting and lint checks for CI" ([Codex
   AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)).
   Pocock's `retro`: "Default to building the check over writing the rule."
4. **Write instructions concretely enough to verify.** "Use 2-space indentation"
   rather than "Format code properly" ([Claude
   memory](https://code.claude.com/docs/en/memory)); "Most agent files fail
   because they're too vague" ([GitHub
   blog](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/));
   principles must be "declarative and testable"
   ([spec-kit](https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/constitution.md)).
5. **Record decisions and their reasons inside the repository.** Nygard kept
   ADRs in the repository
   ([Nygard](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions)).
   OpenAI: "anything it can't access in-context while running effectively
   doesn't exist" ([harness
   engineering](https://openai.com/index/harness-engineering/)). A census found
   74.0% of directives in instruction files give no reason
   ([Zarzycki](https://arxiv.org/abs/2610.31715)).
6. **Grow the files from observed failures.** Claude Code adds a line when
   "Claude makes the same mistake a second time"
   ([memory](https://code.claude.com/docs/en/memory)); GitHub: "Start simple.
   Test it. Add detail when your agent makes mistakes" ([GitHub
   blog](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/));
   Pocock's `domain-modeling`: "Create files lazily: only when you have
   something to write."
7. **The files rot unless something keeps them true.** OpenAI's one big manual
   "rots instantly", so it runs a "doc-gardening" agent and CI checks ([harness
   engineering](https://openai.com/index/harness-engineering/)); Claude Code has
   `/doctor prompt-audit` for references to missing files and contradictions
   ([memory](https://code.claude.com/docs/en/memory)); Pocock's
   `writing-for-agents` calls the default fate "sediment".

## 2. The recommended documents

| Document | What it is for | Who recommends it | What goes in, what stays out | How it is kept true |
| --- | --- | --- | --- | --- |
| Agent instruction file (`AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`) | What every session loads: how to check work, and what the code does not say. | [agents.md](https://agents.md/); [Claude](https://code.claude.com/docs/en/memory); [Codex](https://learn.chatgpt.com/docs/agent-configuration/agents-md); [Copilot](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions); [OpenAI](https://openai.com/index/harness-engineering/) | In: exact test, lint and build commands; misleading places in the code; decisions not in the repo; "Anything you've had to correct twice already" ([Claude](https://code.claude.com/docs/en/best-practices)). Out: what the agent finds by reading; procedures (to skills) and part-of-repo rules (to scoped rules) ([Claude](https://code.claude.com/docs/en/memory)); task-specific content ([Copilot](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions)). Layout is disputed (section 6). | "Treat AGENTS.md as living documentation" ([agents.md](https://agents.md/)); `/doctor prompt-audit` ([Claude](https://code.claude.com/docs/en/memory)); CI that checks docs are "up to date, cross-linked, and structured correctly" ([OpenAI](https://openai.com/index/harness-engineering/)). |
| Path-scoped or nested files (`.claude/rules/` with `paths:`, `.github/instructions/*.instructions.md` with `applyTo`, nested `AGENTS.md`) | Rules for one part of the tree, loaded only there. | [Claude](https://code.claude.com/docs/en/memory); [Copilot](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions); [Codex](https://learn.chatgpt.com/docs/agent-configuration/agents-md) | One topic per file, named for it ([Claude](https://code.claude.com/docs/en/memory)); topics such as security in their own files ([GitHub](https://github.blog/ai-and-ml/github-copilot/unlocking-the-full-power-of-copilot-code-review-master-your-instructions-files/)). | Same audit as the root file ([Claude](https://code.claude.com/docs/en/memory)). |
| Skills (`.claude/skills/<name>/SKILL.md`) | Procedures that load only when relevant, so a long one does not weigh on unrelated tasks as it would in CLAUDE.md ([Claude](https://code.claude.com/docs/en/best-practices)). | [Claude](https://code.claude.com/docs/en/best-practices); [Skills guide](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | Body under 500 lines; references one level deep; scripts for deterministic steps; no time-sensitive facts; one term per concept. | Evaluate first, watch a fresh agent use it, refine. |
| Coding standards (`CODING_STANDARDS.md`, or a section of the instruction file) | What a change is judged against. | Pocock `code-review`, `retro`; [agents.md](https://agents.md/); [Copilot](https://docs.github.com/en/copilot/tutorials/coding-agent/get-the-best-results) | Pocock: judgement calls only, mechanical rules become checks, and the file is "read during review, not implementation". GitHub: short imperative rules with good and bad examples ([GitHub](https://github.blog/ai-and-ml/github-copilot/unlocking-the-full-power-of-copilot-code-review-master-your-instructions-files/)). | Pocock `retro`: add or clarify a rule when review misses a mistake; move mechanical ones into a linter, hook or CI job. |
| ADRs (`docs/adr/0001-slug.md`; MADR: `docs/decisions/NNNN-title.md`) | Why a structure or constraint exists, so it is neither blindly kept nor blindly reversed. | [Nygard](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions); [adr.github.io](https://adr.github.io/); [MADR](https://adr.github.io/madr/); Pocock `domain-modeling` | Nygard: title, context, decision, status, consequences; "one or two pages". MADR: optional "Confirmation" of how compliance is checked. Pocock: "An ADR can be a single paragraph", only for decisions that are hard to reverse, surprising, and a real trade-off. | Numbers never reused; reversed decisions stay, marked superseded ([Nygard](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions)); agents flag conflicts instead of overriding (Pocock domain.md). |
| Glossary (`GLOSSARY.md`, or `GLOSSARY-MAP.md` for several contexts) | One word per domain concept, used in issues, code and tests. | Pocock `domain-modeling`; consistent terms in the [Skills guide](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | One or two sentences a term, synonyms to avoid, project terms only; "It is a glossary and nothing else". | Updated inline when a term is resolved. |
| Architecture and design docs (`docs/ARCHITECTURE.md`, `DESIGN.md`, `SECURITY.md`, a quality score) | The system of record the map points to. | [OpenAI](https://openai.com/index/harness-engineering/) | Indexed design docs with a verification status; a quality grade per domain and layer; execution plans with decision logs, all checked in. | Doc-gardening agent; CI validation. |
| Constitution (`.specify/memory/constitution.md`) | Governing principles every plan is checked against. | [spec-kit](https://github.com/github/spec-kit/blob/main/spec-driven.md) | Named principles, each a non-negotiable rule with rationale, using MUST or SHOULD; a governance section ([command](https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/constitution.md)). | Semantic version and amendment dates; plan gates that require exceptions to be justified. |
| Per-task spec or agent brief (`SPEC.md`, an issue comment, an execution plan) | The definition of done for one unattended run. | [Claude](https://code.claude.com/docs/en/best-practices); [Copilot](https://docs.github.com/en/copilot/tutorials/coding-agent/get-the-best-results); Pocock `triage`, `to-spec`, `to-tickets` | Current and desired behaviour, testable acceptance criteria, an out-of-scope list (AGENT-BRIEF.md). File paths are disputed (section 6). | Written to survive renames while it waits (AGENT-BRIEF.md). |
| Rejected requests (`.out-of-scope/<concept>.md`) | Stops a rejected feature returning. | Pocock `triage` (OUT-OF-SCOPE.md) | One file per concept, a durable reason; rejected enhancements only. | Appended on each repeat request; deleted if the decision changes. |
| Progress file and feature list | Continuity across sessions on long work. | [Anthropic harness](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | JSON, which the model is less likely to overwrite than Markdown; "It is unacceptable to remove or edit tests". | Each session reads git log and the progress file first. |

## 3. Tooling instead of prose

What the sources say should be a check:

- **Rules with no exceptions** go in hooks, deny rules or managed settings,
  because "`CLAUDE.md` is for guidelines, and Claude is allowed to decide a
  guideline doesn't apply". Examples: a `Stop` hook running the typecheck, a
  `PostToolUse` hook running the formatter, a `PreToolUse` hook blocking edits
  under `migrations/`. The signal: "If you keep adding emphasis to a `CLAUDE.md`
  line and Claude still misses it, that's a sign the line belongs in a hook"
  ([best practices](https://code.claude.com/docs/en/best-practices)).
- **Architecture and taste.** OpenAI lints layer dependency directions,
  structured logging, type naming and file sizes, and writes the messages "to
  inject remediation instructions into agent context" ([harness
  engineering](https://openai.com/index/harness-engineering/)).
- **The documentation itself.** "Dedicated linters and CI jobs validate that the
  knowledge base is up to date, cross-linked, and structured correctly"
  ([harness engineering](https://openai.com/index/harness-engineering/)).
- **Mechanical rules in general.** Pocock's `retro`: "a fixed syntactic pattern,
  a banned API, an import shape, a file-location rule" gets a deterministic
  check, "full stop", and a repository with no hook or CI job running its checks
  is itself a finding. His `code-review` tells the reviewer to "skip anything
  tooling already enforces".
- **Decision compliance.** MADR's "Confirmation" suggests "a design/code review
  or a test with a library such as ArchUnit"
  ([MADR](https://adr.github.io/madr/)); spec-kit gates its plan template on the
  constitution
  ([spec-driven.md](https://github.com/github/spec-kit/blob/main/spec-driven.md)).
- **Done, for an unattended run.** Claude Code asks whether the run knows what
  done looks like, can check its work, is limited in what it touches, has a cap,
  and has someone who signs off ([best
  practices](https://code.claude.com/docs/en/best-practices)). Anthropic's
  agents marked features done after unit tests or `curl`, and did better when
  told to test end to end in a browser ([Anthropic
  harness](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)).
- **Tools that resist misuse.** "Poka-yoke your tools" ([building effective
  agents](https://www.anthropic.com/engineering/building-effective-agents));
  prefer scripts for deterministic steps, with specific error messages ([Skills
  guide](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)).

What stays prose: guidelines with exceptions ("Prefer named exports" stays in
CLAUDE.md, [best practices](https://code.claude.com/docs/en/best-practices));
judgement calls such as cross-file consistency (Pocock `retro`); non-standard
practices and their reasons ([Gloaguen et
al.](https://arxiv.org/html/2602.11988)). Claude Code adds "Whatever the scope,
keep the enforced set small", since every hook misfires sometimes and needs
upkeep. Both Anthropic and GitHub say the prose layer is not enforcement:
CLAUDE.md files "aren't enforced configuration"
([memory](https://code.claude.com/docs/en/memory)); "Copilot code review is
non-deterministic"
([GitHub](https://github.blog/ai-and-ml/github-copilot/unlocking-the-full-power-of-copilot-code-review-master-your-instructions-files/)).

## 4. How to arrange it for an agent

**Size, as each source states it.** These are vendor guidance, not measured
thresholds.

| Source | Limit or guidance |
| --- | --- |
| Claude Code ([memory](https://code.claude.com/docs/en/memory)) | Under 200 lines per CLAUDE.md; on-demand files cut off past 40,000 characters on a 200K window; `@` imports "don't reduce its context cost". |
| Codex ([AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)) | All instruction files together capped at "32 KiB by default"; one file per directory. |
| OpenAI's repository ([harness](https://openai.com/index/harness-engineering/)) | About 100 lines in AGENTS.md; the rest in `docs/`. |
| Copilot | No general limit ([docs](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions)); code review's 4,000-character cap: "That limit has now been removed" ([changelog, 12 June 2026](https://github.blog/changelog/2026-06-12-copilot-code-review-new-configurations-and-controls/)); files past about 1,000 lines may behave inconsistently ([GitHub](https://github.blog/ai-and-ml/github-copilot/unlocking-the-full-power-of-copilot-code-review-master-your-instructions-files/)). |
| Agent Skills ([overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)) | About 100 tokens of metadata per skill always loaded; body "Under 5k tokens" and under 500 lines; bundled files free until read. |

**One file or an index.** OpenAI's single large AGENTS.md failed: context is
scarce, "Too much guidance becomes non-guidance", it rotted, and a blob resists
mechanical checks; a short map into `docs/` replaced it ([harness
engineering](https://openai.com/index/harness-engineering/)). Anthropic
describes the same hybrid in Claude Code: CLAUDE.md files "are naively dropped
into context up front", and glob and grep fetch the rest "just in time"
([context
engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).
Pocock's `writing-for-agents`: "inline what every branch needs, and push behind
a pointer what only some branches reach"; a pointer's wording, not its target,
decides whether the agent follows it.

**Depth.** Keep references one level deep from the entry file, since Claude may
only preview a file reached through a second reference, and give reference files
over 100 lines a contents list ([Skills
guide](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)).

**How each tool merges nested files.**

- Claude Code concatenates CLAUDE.md files from the root down; subdirectory
  files load when Claude touches a file there; `paths:` rules load for matching
  files. By default it reads `AGENTS.md` only when no `CLAUDE.md` is on the
  path. A `CLAUDE.md` holding `@AGENTS.md` is the documented way to share one
  file; one that only tells Claude in words to read it means "Claude sees
  `AGENTS.md` only if it decides to open the file"
  ([memory](https://code.claude.com/docs/en/memory)).
- Codex: "Files closer to your current directory override earlier guidance
  because they appear later in the combined prompt" ([Codex
  AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)).
  agents.md: "The closest AGENTS.md to the edited file wins"
  ([agents.md](https://agents.md/)). Copilot: "the nearest AGENTS.md file in the
  directory tree will take precedence"
  ([Copilot](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions)).
- Contradictions are not resolved for you: Claude "may pick one arbitrarily"
  ([memory](https://code.claude.com/docs/en/memory)).

## 5. What has been measured

**Controlled studies of agent outcomes.**

- **Gloaguen et al., "Evaluating AGENTS.md"** ([arXiv
  2602.11988](https://arxiv.org/abs/2602.11988), v3 September 2026;
  [HTML](https://arxiv.org/html/2602.11988)). *Sample:* SWE-bench Lite (300
  tasks, 11 Python repositories, LLM-generated files) and CTXbench (138
  instances, 12 repositories with developer-committed files); Claude Code with
  Sonnet-4.5, Codex with GPT-5.2 and GPT-5.1 mini, Qwen Code. *Results:*
  LLM-generated files lowered success by about 0.5% and 2% (not significant) and
  raised cost by about 20% and 23% (significant). Developer-written files raised
  success by 2.4% (p = 21%, not significant), helped every agent except Claude
  Code, cost up to 19% more, and beat LLM-generated files significantly (p =
  3.8%). Agents obeyed the files: `uv` was used about 1.6 times per instance
  when named, under 0.01 when not. Overviews did not get agents to the right
  files sooner: "context files are not effective at providing a repository
  overview". "We observe no clear dependency between the success rate or the
  per-instance cost and the context file length." *Advice:* omit LLM-generated
  files for now; write only what the README and code do not say.
- **Lulla et al., "On the Impact of AGENTS.md Files on the Efficiency of AI
  Coding Agents"** ([arXiv 2601.20404](https://arxiv.org/html/2601.20404), JAWs
  2026). 124 small merged pull requests from 10 repositories, each run with and
  without the root AGENTS.md on Codex (gpt-5.2-codex). Median time fell 28.64%
  and median output tokens 16.58% (Wilcoxon, p < 0.05); median total tokens rose
  1.29%. Correctness was not measured.
- **McMillan, "Instruction Adherence in Coding Agent Configuration Files"**
  ([arXiv 2605.10039](https://arxiv.org/abs/2605.10039), May 2026). 1,650 Claude
  Code sessions, 16,050 function-level observations, two TypeScript codebases.
  For size, position, file architecture and contradictions in adjacent files:
  "None of the four structural variables or three two-way interactions produces
  a detectable contrast after multiple-testing correction". The largest effect
  was drift within a session: about 5.6% lower odds of compliance per further
  function (odds ratio 0.944), found during analysis, not pre-specified.
- **Shepard and Albrecht, "Probe-and-Refine Tuning of Repository Guidance"**
  ([arXiv 2606.20512](https://arxiv.org/abs/2606.20512)). SWE-bench Verified,
  four trials, Qwen3.5-35B-A3B: resolve rate 33.0% with guidance refined against
  synthetic bug-fix probes, 28.3% with the static guidance it started from,
  25.5% with none (p < 0.001). The gain came from reaching the right file more
  often; per-patch precision did not change; the method degraded on a smaller
  model.
- **Polandra et al.** ([arXiv 2610.21421](https://arxiv.org/abs/2610.21421))
  varied five instruction categories while two models rebuilt five Python
  libraries; functional correctness was limited under every combination. The
  task is far from issue-to-deploy work.
- **Adjacent: Blyth et al., "Static Analysis as a Feedback Loop"** ([arXiv
  2508.14419](https://arxiv.org/abs/2508.14419)). GPT-4o with Bandit and Pylint
  findings fed back for up to ten rounds: security issues fell from over 40% to
  13%, readability violations from over 80% to 11%. A prompting loop, not an
  agent in a repository.

**Observational studies**, which describe files and measure no outcome: 253
CLAUDE.md files are dominated by commands, implementation notes and architecture
([2509.14744](https://arxiv.org/abs/2509.14744)); 2,303 context files grow
"through frequent, small additions", and only 14.8% mention security
([2511.12884](https://arxiv.org/abs/2511.12884)); across 22,854 repositories
about four in five instruction sets are edited after creation
([2610.31715](https://arxiv.org/abs/2610.31715)).

**Not measurement.** GitHub's "lessons from over 2,500 repositories" reports no
outcome data, and it studies custom agent persona files in `.github/agents/`,
not root AGENTS.md files ([GitHub
blog](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/)).
OpenAI's harness post is one team's uncontrolled account; Anthropic's harness
post and Nygard's three-month report are the same kind of evidence. No study was
found that measures ADRs, a glossary or a coding-standards file, or that
compares a prose rule with the same rule enforced by a linter in an agent's
loop.

## 6. Where the sources disagree

1. **Layout and architecture in the instruction file.** Claude Code lists
   "Describe your architecture and file layout in `CLAUDE.md`" as advice to stop
   following ([best practices](https://code.claude.com/docs/en/best-practices)),
   yet its memory page still lists "project layout" among the facts to keep
   ([memory](https://code.claude.com/docs/en/memory)). GitHub asks for
   repository structure
   ([Copilot](https://docs.github.com/en/copilot/tutorials/coding-agent/get-the-best-results)).
   The measurement sides with leaving overviews out ([Gloaguen et
   al.](https://arxiv.org/html/2602.11988)).
2. **Whether length lowers adherence.** Claude Code says longer files "reduce
   adherence" ([memory](https://code.claude.com/docs/en/memory)); both studies
   that tested length found no detectable effect
   ([McMillan](https://arxiv.org/abs/2605.10039); [Gloaguen et
   al.](https://arxiv.org/html/2602.11988)). Length still costs tokens.
3. **Generating the file with a model.** Claude Code's `/init` and Copilot's
   docs offer to generate one; Gloaguen et al. advise against LLM-generated
   files; Shepard and Albrecht found probe-tuned guidance helped, so the method
   may be what matters.
4. **Emphasis.** Claude Code: emphasis "mostly makes Claude over-apply the rule"
   ([best practices](https://code.claude.com/docs/en/best-practices)).
   Anthropic's Skills guide shows "MUST filter" recommended over "always
   filter"; spec-kit marks test-first "NON-NEGOTIABLE".
5. **A person on the merge.** Claude Code: "have a person approve the result at
   the end", and protect `main` with a branch rule the task cannot bypass ([best
   practices](https://code.claude.com/docs/en/best-practices)). OpenAI: "Humans
   may review pull requests, but aren't required to" ([harness
   engineering](https://openai.com/index/harness-engineering/)). OpenAI's "This
   would be irresponsible in a low-throughput environment" is said of something
   else: of running with "minimal blocking merge gates", where a test that
   fails now and then gets a follow-up run and does not block. It cautions
   against loose gates where changes are few, not against leaving a person out.
6. **How much to enforce.** OpenAI encodes opinionated "golden principles" as
   mechanical rules; Claude Code says most guidelines have exceptions the model
   judges better, and forty hooks probably means preferences; Pocock defaults to
   a check for anything mechanical. Part of the gap is scope: harness hooks
   versus CI lints.
7. **Who applies standards.** Pocock's `retro` gives them to the review agent,
   "not the implementation agent". Claude Code tells a reviewer to "skip style",
   since "A reviewer that's asked to find problems will always find *something*"
   ([best practices](https://code.claude.com/docs/en/best-practices)).
8. **File paths in a task.** Pocock: "Don't reference file paths: they go stale"
   (`triage`, AGENT-BRIEF.md). GitHub wants "Directions about which files need
   to be changed"
   ([Copilot](https://docs.github.com/en/copilot/tutorials/coding-agent/get-the-best-results)).
9. **ADR size.** Nygard: "one or two pages". Pocock: one to three sentences, and
   only when all three of his tests pass.
10. **Fixed or living, up front or lazy.** Spec-kit: "The constitution's power
    lies in its immutability", written "once per project" before features
    ([spec-kit](https://github.com/github/spec-kit)). agents.md: "Treat
    AGENTS.md as living documentation". Pocock creates the glossary and ADR
    folder only when needed and tells agents to "proceed silently" when they are
    absent (domain.md).

## 7. What Matt Pocock's skills expect of a repository

One practitioner's recommendations, cited by skill and file name.

- **`CLAUDE.md` or `AGENTS.md` with an `## Agent skills` block**
  (`setup-matt-pocock-skills`, SKILL.md): one line each for the issue tracker,
  triage labels and domain docs, pointing into `docs/agents/`. Edit whichever
  file exists; "Never create `AGENTS.md` when `CLAUDE.md` already exists (or
  vice versa)". `writing-for-agents` (SKILL.md): a pointer's wording decides
  when it fires; every always-loaded word costs "context load"; keep one meaning
  in one place; a restatement of config is a stale-prone "cache"; delete
  "no-ops"; state the behaviour wanted rather than the one banned.
- **`docs/agents/issue-tracker.md`, `triage-labels.md`, `domain.md`**
  (`setup-matt-pocock-skills` and its seed files): how to read and write issues,
  the five states (`needs-triage`, `needs-info`, `ready-for-agent`,
  `ready-for-human`, `wontfix`), and the rule to read the glossary and relevant
  ADRs before exploring code.
- **`GLOSSARY.md`, or `GLOSSARY-MAP.md` for several contexts**
  (`domain-modeling`, SKILL.md and GLOSSARY-FORMAT.md): one or two sentences per
  term with `_Avoid_` synonyms, project-specific terms only, no implementation
  detail, updated inline. `tdd`, `diagnosing-bugs`, `to-spec`, `to-tickets` and
  `triage` use its words in titles and test names.
- **`docs/adr/0001-slug.md`** (`domain-modeling`, ADR-FORMAT.md): one to three
  sentences, with optional status, options and consequences, written only when a
  decision is hard to reverse, surprising without context, and a real trade-off.
  `improve-codebase-architecture` offers one when a refactor is rejected for a
  reason a future review would need.
- **`CODING_STANDARDS.md` and `CONTRIBUTING.md`** (`code-review`, `retro`): the
  Standards reviewer reads them plus a baseline of twelve Fowler smells, and
  "The repo overrides" the baseline. Judgement calls only; read at review.
- **`.out-of-scope/<concept>.md`** (`triage`, OUT-OF-SCOPE.md): one file per
  rejected concept, with a durable reason and a list of prior requests, matched
  by concept rather than keyword.
- **Outside the repository:** agent briefs on issues (`triage`, AGENT-BRIEF.md)
  with current and desired behaviour, key interfaces, testable acceptance
  criteria and an out-of-scope list; specs and tickets (`to-spec`, `to-tickets`)
  sized "to fit in a single fresh context window"; tests through public
  interfaces, with no tautological tests (`tdd`, tests.md).

## 8. What this suggests for a small static-site repository (my inference, not the sources')

The repository in the brief already follows the pattern most sources converge
on: a short AGENTS.md that routes to README sections, tests that hold some
documented rules to the code (the page-weight, colour and runbook tests
AGENTS.md names), and one test command shared with the build job. In the order I
would add things:

1. **A check that keeps the map true.** A standard-library test that fails when
   a path or README heading named in AGENTS.md no longer exists, as the runbook
   test already does for its table. It applies OpenAI's "cross-linked" check and
   Claude Code's audit for missing references; a stale pointer misleads an
   unattended agent more than a missing document does.
2. **The checks as the merge gate.** With no person merging, required status
   checks on `main` for the test and build jobs satisfy both OpenAI's reliance
   on mechanical gates and Claude Code's call for a branch rule the agent cannot
   bypass. Whether to keep a person on the merge is the owner's call; the
   sources split (section 6, point 5).
3. **Prose rules into tests before any standards file.** Read the README's
   design note and AGENTS.md's list of common failures for rules of fixed shape
   that no test holds yet, and test them with failure messages that say how to
   fix the fault. A third-party linter would be a new dependency for the owner
   to approve.
4. **The site's decisions where the agent can read them.** They live in a
   private repository an unattended agent may not have checked out. A
   `docs/adr/` here in Pocock's short form, keeping superseded records as Nygard
   does, restating only site decisions that pass Pocock's three tests, and
   naming the test that confirms each (MADR's "Confirmation"), would close that
   gap. The cost is duplication, so each record should say which repository owns
   the decision and cite the tracker issue by number, as the repository's rules
   already require.
5. **A site-scoped `GLOSSARY.md`, if the domain words are to be public**,
   limited to terms the pages, code and tests use, so an agent without the
   private checkout names things correctly.
6. **Last, a short `CODING_STANDARDS.md`,** only if a judgement-call rule
   appears that no test can hold.
7. **Throughout:** keep AGENTS.md a map well under 200 lines and 32 KiB, with no
   repository overview; reach the README by section rather than importing it;
   keep `.out-of-scope/` beside the tracker, which the owner has since decided
   is this repository's own issues; and after
   changing the foundation, rerun a few past issues with and without the change
   rather than assume it helped.

## 9. Could not read, and not found

- **Abstract only:** arXiv [2605.10039](https://arxiv.org/abs/2605.10039),
  [2606.20512](https://arxiv.org/abs/2606.20512),
  [2610.21421](https://arxiv.org/abs/2610.21421),
  [2511.12884](https://arxiv.org/abs/2511.12884),
  [2509.14744](https://arxiv.org/abs/2509.14744),
  [2610.31715](https://arxiv.org/abs/2610.31715),
  [2508.14419](https://arxiv.org/abs/2508.14419). The ETH paper's HTML was read
  to character 100,000 of 102,647;
  [2601.20404](https://arxiv.org/html/2601.20404) was read in full.
- **Did not cover the point:** the [spec-kit
  README](https://github.com/github/spec-kit) does not describe the constitution
  file (that came from
  [spec-driven.md](https://github.com/github/spec-kit/blob/main/spec-driven.md)
  and the [command
  template](https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/constitution.md));
  [adr.github.io](https://adr.github.io/) and its [practices
  page](https://adr.github.io/ad-practices/) are link lists whose linked
  articles were not read; the [agents.md
  repository](https://github.com/agentsmd/agents.md) README holds only a sample
  file.
- **Redirect:** the Codex guide on developers.openai.com now lives at
  [learn.chatgpt.com](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
  which was read.
- **Seen in search results only, not cited for any finding:** studies of Cursor
  rules ([2512.18925](https://arxiv.org/abs/2512.18925v1),
  [2606.12231](https://arxiv.org/pdf/2606.12231)) and of LLM-written ADRs
  ([2604.03826](https://arxiv.org/html/2604.03826)).
- **Not found:** a measurement of ADRs, glossaries or coding-standards files on
  agent results; a controlled comparison of prose rules with linter-enforced
  ones in an agent's loop; any study of unattended issue-to-deploy pipelines
  without a human merge.

## 10. Checked again

On 22 November 2026 a second reader, which had not seen this file, read five of
the pages again and looked for twenty of the statements above: arXiv 2602.11988
and 2601.20404, OpenAI's harness post, and Claude Code's best-practices and
memory pages. Each statement was on its page, some in other words. One
correction came of it, made in section 6, point 5: the sentence about a
low-throughput environment is about merge gates, not about review by a person.
A second correction, in section 8, point 7, follows a decision of the owner's
and not a source. The other sources were not read again.
