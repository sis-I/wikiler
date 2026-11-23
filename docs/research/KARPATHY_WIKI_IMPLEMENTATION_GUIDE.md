# Karpathy LLM Wiki / Second Brain: Practical Implementation Guide

Status: Non-normative evidence

> Non-normative third-party evidence. This guide is a historical snapshot of
> external research about the Karpathy LLM Wiki idea and practitioner projects.
> It is not Wikiler behavior and it is not a specification. Every claim below
> is attributed to the named source, each source URL is listed in section 11,
> and all were accessed on 2026-11-16. These claims are illustrative only, not
> Wikiler behavior. Numeric figures are reported by their sources and were not
> independently verified. The link grammar, scale figures, popularity and page
> counts, tool counts, and repository names below have been corrected against
> the audited [research note](KARPATHY_LLM_WIKI_RESEARCH.md). For the normative
> how-to, see `docs/guides/LLM_WIKI_IMPLEMENTATION_GUIDE.md`.

Based on research across Karpathy's original post and gist, practitioner repos,
and Reddit, Medium, and DEV community experiences. Includes Garry Tan's gbrain
(33,140 stars as of 2026-11-16, reported by GitHub and not independently
verified), NicholasSpisak second-brain, frankchu91 mindbase, DimitrisLianos
LLM_Wiki_SecondBrain, and microsoft/llmwiki.

---

## 1. Original Source: Karpathy's Post and Gist

### The X Post

**URL:** https://x.com/karpathy/status/2039805659525644595
**Date:** April 2026
**Key quote:** *"Data ingest: I index source documents (articles, papers, repos,
datasets, images, etc.) into a raw/ directory, then I use LLM incrementally
compile a wiki, which is just a collection of markdown files..."*

### The Idea File (Gist)

**URL:** https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
**Raw:** https://gist.githubusercontent.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md

This is an *idea file*, not a specific implementation. It describes:

- The core idea: RAG re-derives knowledge on every query; the wiki compiles
  knowledge once and keeps it current.
- Three layers: raw sources, wiki, schema.
- Three operations: ingest, query, lint.
- Two special files: index.md, log.md.
- Optional CLI tools: qmd for search at scale.
- Tips: Obsidian Web Clipper, download images locally, Obsidian graph view,
  Marp, Dataview, git version control.

**Scale note:** the canonical gist says index.md is sufficient at about 100
sources and hundreds of pages. It does not give a word count. Beyond that
scale, the gist names qmd (hybrid BM25 plus vector search) as an optional local
search tool. Earlier coverage added a word count threshold that is not in the
gist, so it has been removed here.

---

## 2. Key Practitioners and Repos

All figures in this table were reported by their sources on 2026-11-16 and were
not independently verified. They are illustrative only, not Wikiler behavior.

| Practitioner | Repo | Stars | Type | Notes |
|---|---|---|---|---|
| **Garry Tan** (YC President and CEO) | `garrytan/gbrain` | 33,140 | Production agent brain | Runs his OpenClaw and Hermes agents: 155,795 pages, 24,589 people, 5,340 companies, 66 cron jobs. These counts are first-party claims from the project README and were not independently audited. MCP server and skills. Not a Karpathy-pattern purist: uses PGLite and Postgres plus pgvector under markdown. |
| **Nicholas Spisak** | `NicholasSpisak/second-brain` | Agent Skills | Agent skill for Claude Code, Codex, Cursor, and Gemini CLI | Four skills: onboarding, ingest, query, lint. Wizard-based setup. Generates CLAUDE.md and AGENTS.md. No repository license was detected; a reusable agent skill without a license is a distribution risk. |
| **Frank Chu** | `frankchu91/mindbase-llm-wiki` | MCP server and web UI | MCP server and local web app | `npx mindbase-app`. Free local Ollama models. Human-in-the-loop approval before writing. 49 MCP tools in the current server documentation. |
| **Dimitris Lianos** | `DimitrisLianos/LLM_Wiki_SecondBrain` | Fully local Python | Python CLI and web UI | Standard library only, no cloud APIs. arc42 and C4 docs. FTS5 search, no vector DB. |
| **Microsoft** | `microsoft/llmwiki` | VS Code extension and MCP | TypeScript monorepo | VS Code extension, `@llmwiki/core` MCP server. The reference calls itself a 14-tool reference but lists 18 tool headings, and it lists six lint categories. |
| **Green Dalii** | `GD4AI/obsidian-llm-wiki` | Obsidian plugin | Community plugin | Native Obsidian plugin, no terminal or Docker. The older `green-dalii/obsidian-llm-wiki` URL redirects to this canonical repository. |

### Garry Tan's gbrain: Notable Distinctions

Gbrain is Garry Tan's production brain, not a pure Karpathy clone, but it
shares DNA. These are third-party claims, attributed to the project sources in
section 11 and accessed on 2026-11-16. They are illustrative only, not Wikiler
behavior.

- **Karpathy's pattern**: ingest sources you manually add, LLM compiles wiki,
  browse in Obsidian.
- **Gbrain**: operational brain that auto-enriches from meetings, email, tweets,
  calendar, and contacts: continuous ingestion, not manual drops.
- **Architecture**: markdown wiki as the human and LLM interface, plus a
  database layer using PGLite or Postgres with pgvector for identity
  resolution, a fact store, and a relationship graph.
- **Two-layer pages**: compiled truth above a separator, rewritten on new
  evidence, with an append-only timeline below it.
- **MECE directories**: every piece of knowledge has one primary home
  directory with a resolver README.md.
- **Scale**: the project README reports 155,795 pages, 24,589 people, and
  5,340 companies. These are first-party claims and were not independently
  audited. The gist's own guidance is about 100 sources and hundreds of pages.
- **Install**: `bun install -g github:garrytan/gbrain`, then `gbrain setup
  claude-code` or `gbrain setup codex`.
- **Not distributed on npm** (shadow package warning).

Read the full schema:
https://github.com/garrytan/gbrain/blob/master/docs/GBRAIN_RECOMMENDED_SCHEMA.md

---

## 3. Practitioner Experiences: What Worked, What Did Not

These experiences are anecdotes from named third-party posts, attributed with
URLs in section 11 and accessed on 2026-11-16. They are illustrative only, not
Wikiler behavior, and do not support universal claims.

### Positive Experiences

**Reddit r/AI_Agents: "Spent a weekend actually understanding and building
Karpathy's LLM Wiki"**

- Weekend was enough to get a basic version working with Claude and Obsidian.
- About 80 articles and PDFs ingested, with a working wiki by Sunday night.
- "It genuinely felt like magic."
- No embeddings and no vector DB were needed at the scale they reported.
- The LLM handled its own indexing through summary files.
- The bottleneck was consistency, not retrieval.

**Reddit r/LocalLLaMA: u/Astro-Han**

- Built a Claude Code skill file doing the compile, query, and lint loop from
  the gist.
- `npx add-skill Astro-Han/karpathy-llm-wiki`.
- The linting step kept the wiki consistent as new sources arrived.

**Reddit r/ObsidianMD: u/Dementiy (running for a quarter)**

- What held: wiki as a reading layer, with pages regenerated from notes that
  stayed useful.
- Asking for a current picture of a topic assembled it from what was actually
  there.
- What broke: static wiki pages generated once and then left to rot.
- Derived on demand pages do not rot.

**OpenAIToolsHub: Six months in with Obsidian and Claude**

- Pitfall: forgetting to lint after big ingest weeks.
- Six to eight articles dumped over a weekend with lint skipped led to orphan
  pages and contradictions.
- Cost: about a week of confusion about the current view.
- Lesson: the lint protocol is not optional.

### Negative and Cautionary Experiences

**Reddit r/LLM: "We built Karpathy's LLM Wiki: the LLM read it, understood it,
and ignored it anyway"**

- Built for supply chain AI with over 200 pages and Wikipedia-style linking.
- The agent read the wiki before every query but still ignored wiki guidance.
- A column name `FINAL_REASON` was louder than four wiki pages saying not to
  rely on it.
- Lesson: wiki guidance must be enforced in system prompts and tool
  definitions, not just read passively.

**DEV Community: "The Lint Ran Every Week. The Dead-Link Count Never Went
Down."**

- Weekly lint ran but recovered nothing.
- Dead links and orphans accumulated despite linting.
- Lesson: lint needs enforcement and follow-through, not just reporting.

**Medium: "I Tried to Build Karpathy LLM WIKI. Here's Where It Broke Down for
Me."**

- Maintenance overhead slowly exceeded perceived value.
- Usage dropped to zero gradually, not dramatically.
- The inputs could not be maintained.

**Reddit r/ObsidianMD: u/UnderneathTheBottle6**

- The pattern of ingest, generate, synthesize, and hoard cheapened the
  material produced.
- Hoarding without distillation loses value.

---

## 4. Practical Implementation: Folder Structure

This tree is a third-party recommendation, illustrative only, not Wikiler
behavior. Wikiler's locked layout is in `docs/guides/LLM_WIKI_IMPLEMENTATION_GUIDE.md`.

```
your-vault/
├── CLAUDE.md              # Agent config (Claude Code) or AGENTS.md (Codex)
├── log.md                 # Vault-level setup log (optional)
├── raw/                   # Layer 1, immutable source of truth (human-owned)
│   ├── assets/            # Downloaded images from clipped articles
│   ├── papers/
│   ├── articles/
│   └── <source files>     # Articles, papers, PDFs, images, data files
├── wiki/                  # Layer 2, LLM-owned knowledge base
│   ├── index.md           # Content catalog (one line per page, categorized)
│   ├── log.md             # Append-only timeline (## [YYYY-MM-DD] op | title)
│   ├── sources/           # One summary page per ingested source
│   ├── entities/          # People, orgs, products, tools
│   ├── concepts/          # Ideas, frameworks, theories, patterns
│   ├── synthesis/         # Comparisons, analyses, cross-cutting themes
│   └── queries/           # Saved query results (optional)
├── output/                # Reports, query results, generated artifacts
└── assets/                # Vault-level assets
```

**Naming conventions in the source guide:**

- Filenames: kebab-case plus `.md`, for example `article-title-here.md`.
- H1 titles: Title Case, for example `# Article Title Here`.
- Internal links: `[[dir/slug|Page Title]]`, the corrected Wikiler form. The
  original guide used `[[Page Title]]`; the handoff from the vault contract
  decision is to use the path-qualified form.
- Frontmatter on every wiki page:

  ```yaml
  ---
  type: source | entity | concept | synthesis | query
  title: Page Title
  sources: [source-filename-1.md, source-filename-2.md]
  created: YYYY-MM-DD
  updated: YYYY-MM-DD
  tags: [tag1, tag2]
  ---
  ```

---

## 5. Schema File: CLAUDE.md and AGENTS.md Template

This is described by the source as the single source of truth that makes the
LLM a disciplined wiki maintainer. It is third-party guidance, illustrative
only, not Wikiler behavior. A vault using Wikiler takes its contract from the
installed `AGENTS.md`.

### Recommended Sections

1. **Architecture**: three directories, wiki subdirectories, two special
   files (index.md, log.md).
2. **Page format**: YAML frontmatter and wikilink syntax rules.
3. **Naming**: kebab-case filenames, Title Case H1, `[[dir/slug|Page Title]]`
   links.
4. **Operations**: step-by-step ingest, query, and lint workflows.
5. **Rules**: eight to ten hard rules, such as never modify raw and always
   update index and log.
6. **Lint frequency**: after every 10 ingests, monthly minimum, before major
   queries.
7. **Image handling**: download to `raw/assets/`, reference from wiki, describe
   in text.
8. **Optional tools**: summarize, qmd, agent-browser.

### Example: Ingest Operation (from the gist plus NicholasSpisak)

```
When the user adds a file to raw/ and asks you to process it:

1. Read the source completely
2. Discuss key takeaways with the user
3. Create a source summary page in wiki/sources/ with title, source metadata,
   key claims, structured summary
4. Identify all entities and concepts mentioned:
   - If a wiki page exists: update it with new info, noting the source
   - If no wiki page exists: create one in the appropriate subdirectory
5. Add canonical wikilinks [[dir/slug|Page Title]] between related pages
6. Update wiki/index.md with any new pages
7. Append to wiki/log.md: ## [YYYY-MM-DD] ingest | Source Title

A single source may touch 10 to 15 wiki pages. That is normal.
```

### Example: Query Operation

```
When the user asks a question:

1. Read wiki/index.md to find relevant pages
2. Read the relevant wiki pages
3. Synthesize an answer with canonical wikilink citations
4. If the answer produces a valuable artifact, offer to save it as a new page
   in wiki/synthesis/
5. If you save a new page, update index and log
```

### Example: Lint Operation

```
Scan for:
- Contradictions between pages
- Stale claims superseded by newer sources
- Orphan pages (no inbound links)
- Important concepts mentioned but lacking their own page
- Missing cross-references
- Data gaps fillable with web search

Report findings by severity and offer to fix.
Log: ## [YYYY-MM-DD] lint | Summary of findings
```

---

## 6. Operations: The Ingest, Query, Lint Cycle

### Ingest (drop source, create and update pages)

**Flow:**

1. User drops source into `raw/`.
2. LLM reads source and discusses takeaways with user.
3. LLM writes summary page in `wiki/sources/`.
4. LLM creates and updates entity and concept pages (10 to 15 pages per source
   is normal).
5. LLM adds canonical wikilinks `[[dir/slug|Page Title]]` between related
   pages.
6. LLM updates `wiki/index.md`.
7. LLM appends to `wiki/log.md`.

**Tips from practitioners:**

- Ingest one source at a time, stay involved, read summaries, and guide
  emphasis.
- Batch-ingest many sources at once with less supervision, documented in the
  schema.
- Download images locally using Obsidian Web Clipper and the Download
  attachments command.
- LLMs cannot read inline images in one pass; read text first, then view
  images separately.

### Query (read index, synthesize with citations)

**Flow:**

1. LLM reads `wiki/index.md` first to find relevant pages.
2. LLM drills into matched pages.
3. LLM synthesizes an answer with canonical wikilink citations.
4. Valuable artifacts, such as comparisons and analyses, get saved as
   `wiki/synthesis/` pages.
5. Update index and log for new pages.

**Scale note:** the canonical gist says reading `index.md` works at about 100
sources and hundreds of pages. The gist names qmd (local hybrid BM25 plus
vector search) as the optional next step, not a fixed page count.

### Lint (health check for contradictions, orphans, stale claims)

**Flow:**

1. Scan all wiki pages and index.
2. Check broken links, orphan pages, index completeness, stale entries, missing
   pages, and frontmatter validation.
3. Report by severity: errors, warnings, info.
4. Offer fixes.
5. Log the lint pass.

**Practitioner warnings:**

- Lint is not optional; skipping leads to contradictions and orphan pages.
- Weekly lint that only reports without fixing recovers nothing.
- Run lint after every 10 ingests, monthly at minimum.

---

## 7. Tooling Recommendations

| Tool | Purpose | Install | When to add |
|---|---|---|---|
| **Obsidian** | Frontend, graph view, reading wiki | obsidian.md | Day 1 |
| **Obsidian Web Clipper** | Save web articles as markdown to `raw/` | Chrome extension | Day 1 |
| **qmd** | Local hybrid search (BM25 plus vector) for wiki | `npm i -g @tobilu/qmd` | Beyond about 100 sources and hundreds of pages |
| **summarize** | Summarize links, files, media from CLI | `npm i -g @steipete/summarize` | Optional |
| **agent-browser** | Browser automation for web research | `npm i -g agent-browser` | Optional |

---

## 8. How to Create an Agent Skill from This

If you want to package this as an installable agent skill, such as
NicholasSpisak's second-brain, structure it like this. This is third-party
guidance, illustrative only, not Wikiler behavior:

```
your-skill/
├── SKILL.md              # Skill manifest (name, description, allowed-tools)
├── references/
│   ├── wiki-schema.md    # Canonical wiki rules
│   ├── agent-configs/
│   │   ├── claude-code.md    # CLAUDE.md template
│   │   ├── codex.md          # AGENTS.md template
│   │   ├── cursor.md         # .cursor/rules/*.mdc template
│   │   └── gemini.md         # GEMINI.md template
│   └── tooling.md        # CLI tool details and install commands
├── scripts/
│   └── onboarding.sh     # Vault scaffolding script
└── tests/
    └── test_onboarding.sh
```

**SKILL.md pattern (from NicholasSpisak):**

```markdown
---
name: second-brain
description: >
  Set up a new Obsidian knowledge base with the LLM Wiki pattern.
allowed-tools: Bash Read Write Glob Grep
---
# Second Brain: Onboarding Wizard

## Wizard Flow
Guide user through 5 steps, one question at a time:
1. Vault name (default: second-brain)
2. Vault location (default: ~/Documents/)
3. Domain or topic
4. Agent config (auto-detect agent, generate CLAUDE.md and AGENTS.md)
5. Optional CLI tools (summarize, qmd, agent-browser)

## Post-Wizard: Scaffold the Vault
1. Create directory structure (raw/, wiki/, output/, CLAUDE.md)
2. Generate agent config files from templates
3. Update wiki/log.md with setup entry
4. Install CLI tools if selected
5. Print summary with next steps
```

**Agent detection logic:**

- Claude Code: CLAUDE.md
- Codex: AGENTS.md
- Cursor: `.cursor/rules/*.mdc`
- Gemini CLI: GEMINI.md

---

## 9. Pitfalls and Lessons Learned (from practitioners)

| Pitfall | Evidence | Mitigation |
|---|---|---|
| Skipping lint after big ingest weeks | OpenAIToolsHub: 3 orphan pages and 1 contradiction after a month of skipping | Make lint mandatory after every 10 ingests |
| Lint only reports, does not fix | DEV Community: weekly lint recovered nothing | Lint must offer and apply fixes, not just report |
| LLM reads wiki but ignores guidance | Reddit r/LLM: `FINAL_REASON` column louder than wiki pages | Enforce wiki guidance in system prompts and tool definitions, not just passive reading |
| Static wiki pages rot | Reddit r/ObsidianMD, u/Dementiy: pages generated once and left to rot | Treat wiki pages as derived on demand and regenerate when sources change |
| Maintenance overhead exceeds value | Medium: usage dropped to zero gradually | Start small, automate ingest, keep human curation light |
| Messy sources (scanned PDFs, unloadable sites) | Reddit r/AI_Agents: week 2 cracks | Invest in a source cleaning pipeline early |
| Hoarding without distillation | Reddit r/ObsidianMD: ingest, generate, hoard cheapens material | Save synthesis artifacts back to wiki, do not just accumulate summaries |

---

## 10. Quick Start Checklist

- [X] Create vault folder with `raw/`, `wiki/` with subdirs, and `output/`.
- [X] Write `CLAUDE.md` (Claude Code) or `AGENTS.md` (Codex) using the schema
  template.
- [X] Initialize git in vault root.
- [X] Install Obsidian and open the vault folder.
- [X] Install Obsidian Web Clipper and configure it to save to `raw/`.
- [X] Set the Obsidian attachment folder to `raw/assets/` and bind the
  Download attachments command if wanted.
- [X] Perform first ingest: clip an article to `raw/` and run the ingest
  operation.
- [ ] Run query: ask a question and verify citations point to wiki pages.
- [ ] Run lint: health-check the wiki.
- [ ] Beyond about 100 sources and hundreds of pages, install qmd for search.

---

## 11. Source Links

All URLs below were accessed on 2026-11-16. Every third-party claim in this
guide is attributed to one of these sources, is illustrative only, not Wikiler
behavior, and carries figures reported by the source and not independently
verified.

**Primary sources:**

- Karpathy X post: https://x.com/karpathy/status/2039805659525644595
- Karpathy gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Karpathy gist raw: https://gist.githubusercontent.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md

**Practitioner repos:**

- Garry Tan gbrain: https://github.com/garrytan/gbrain (33,140 stars as of
  2026-11-16, reported by GitHub, not independently verified)
- gbrain schema: https://github.com/garrytan/gbrain/blob/master/docs/GBRAIN_RECOMMENDED_SCHEMA.md
- NicholasSpisak second-brain: https://github.com/NicholasSpisak/second-brain
- frankchu91 mindbase: https://github.com/frankchu91/mindbase-llm-wiki
- DimitrisLianos LLM_Wiki_SecondBrain: https://github.com/DimitrisLianos/LLM_Wiki_SecondBrain
- microsoft/llmwiki: https://github.com/microsoft/llmwiki
- GD4AI obsidian-llm-wiki: https://github.com/GD4AI/obsidian-llm-wiki
  (canonical; the older `green-dalii/obsidian-llm-wiki` URL redirects here)

**Practitioner experiences:**

- Reddit r/AI_Agents (weekend build): https://www.reddit.com/r/AI_Agents/comments/1sqg5ew/
- Reddit r/AI_Agents (month in): https://www.reddit.com/r/AI_Agents/comments/1tqvsds/
- Reddit r/ObsidianMD (quarter in): https://www.reddit.com/r/ObsidianMD/comments/1vcgr8z/
- Reddit r/LocalLLaMA: https://www.reddit.com/r/LocalLLaMA/comments/1sclfs6/
- OpenAIToolsHub (six months): https://www.openaitoolshub.org/en/blog/karpathy-llm-wiki
- DEV Community (lint failure): https://dev.to/michaeltuszynski/the-lint-ran-every-week-the-dead-link-count-never-went-down-22m1
- Medium (broke down): https://medium.com/@theo-james/i-tried-to-build-karpathy-llm-wiki-heres-where-it-broke-down-for-me-9c3eef65af21
