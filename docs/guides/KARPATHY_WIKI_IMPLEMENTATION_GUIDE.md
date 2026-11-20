# Karpathy LLM Wiki / Second Brain — Practical Implementation Guide

Based on research across Karpathy's original post/gist, practitioner repos, and Reddit/Medium/DEV community experiences. Includes Garry Tan's gbrain (31K+ stars), NicholasSpisak second-brain, frankchu91 mindbase, DimitrisLianos LLM_Wiki_SecondBrain, and microsoft/llmwiki.

---

## 1. Original Source — Karpathy's Post and Gist

### The X Post
**URL:** https://x.com/karpathy/status/2039805659525644595  
**Date:** April 2026  
**Key quote:** *"Data ingest: I index source documents (articles, papers, repos, datasets, images, etc.) into a raw/ directory, then I use LLM incrementally compile a wiki, which is just a collection of markdown files..."*

### The Idea File (Gist)
**URL:** https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f  
**Raw:** https://gist.githubusercontent.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md

This is an *idea file*, not a specific implementation. It describes:

- The core idea: RAG re-derives knowledge on every query; the wiki compiles knowledge once and keeps it current
- Three layers: raw sources, wiki, schema
- Three operations: ingest, query, lint
- Two special files: index.md, log.md
- Optional CLI tools (qmd for search at scale)
- Tips: Obsidian Web Clipper, download images locally, Obsidian graph view, Marp, Dataview, git version control

**Scale limit:** index.md is sufficient for ~100 sources / ~400K words. Beyond that, add qmd (hybrid BM25 + vector search).

---

## 2. Key Practitioners and Repos

| Practitioner | Repo | Stars | Type | Notes |
|---|---|---|---|---|
| **Garry Tan** (YC President/CEO) | `garrytan/gbrain` | ~31K | Production agent brain | Runs his OpenClaw/Hermes agents: 155,795 pages, 24,589 people, 5,340 companies, 66 cron jobs. MCP server + skills. Not Karpathy-pattern purist — uses PGLite/Postgres + pgvector under markdown. |
| **Nicholas Spisak** | `NicholasSpisak/second-brain` | Agent Skills | Agent skill (Claude Code, Codex, Cursor, Gemini CLI) | Four skills: onboarding, ingest, query, lint. Wizard-based setup. Generates CLAUDE.md/AGENTS.md. |
| **Frank Chu** | `frankchu91/mindbase-llm-wiki` | MCP server + web UI | MCP server + local web app | `npx mindbase-app`. Free local Ollama models. Human-in-the-loop approval before writing. 48 MCP tools. |
| **Dimitris Lianos** | `DimitrisLianos/LLM_Wiki_SecondBrain` | Fully local Python | Python CLI + web UI | Standard library only (no cloud APIs). arc42 + C4 docs. FTS5 search, no vector DB. |
| **Microsoft** | `microsoft/llmwiki` | VS Code extension + MCP | TypeScript monorepo | VS Code extension, @llmwiki/core MCP server, 14 MCP tools, 7 lint checks. |
| **Green Dalii** | `green-dalii/obsidian-llm-wiki` | Obsidian plugin | Community plugin | Native Obsidian plugin, no terminal/Docker. |

### Garry Tan's gbrain — Notable Distinctions

Gbrain is Garry Tan's production brain, not a pure Karpathy clone, but it shares DNA:

- **Karpathy's pattern**: ingest sources you manually add → LLM compiles wiki → browse in Obsidian
- **Gbrain**: operational brain that auto-enriches from meetings, email, tweets, calendar, contacts — continuous ingestion, not manual drops
- **Architecture**: markdown wiki (human/LLM interface) + database layer (PGLite/Postgres + pgvector) for identity resolution, fact store, relationship graph
- **Two-layer pages**: compiled truth (above line, rewritten on new evidence) + timeline (below line, append-only)
- **MECE directories**: every piece of knowledge has exactly one primary home directory with a resolver README.md
- **Scale**: 155,795 pages, 24,589 people, 5,340 companies — far beyond Karpathy's ~400K word limit
- **Install**: `bun install -g github:garrytan/gbrain` then `gbrain setup claude-code` or `codex`
- **Not distributed on npm** (shadow package warning)

Read the full schema: https://github.com/garrytan/gbrain/blob/master/docs/GBRAIN_RECOMMENDED_SCHEMA.md

---

## 3. Practitioner Experiences — What Worked, What Didn't

### Positive Experiences

**Reddit r/AI_Agents — "Spent a weekend actually understanding and building Karpathy's LLM Wiki"**

- Weekend was enough to get a basic version working with Claude + Obsidian
- ~80 articles/PDFs ingested, working wiki by Sunday night
- "It genuinely felt like magic"
- No embeddings, no vector DB needed at ~400K words scale
- LLM handles its own indexing through summary files
- Bottleneck is consistency, not retrieval

**Reddit r/LocalLLaMA — u/Astro-Han**

- Built a Claude Code skill file doing compile/query/lint loop from the gist
- `npx add-skill Astro-Han/karpathy-llm-wiki`
- Linting step is what keeps the wiki consistent as new sources come in

**Reddit r/ObsidianMD — u/Dementiy (running for a quarter)**

- What held: wiki as a reading layer — pages regenerated from notes stay useful
- Ask for current picture of a topic, it assembles from what's actually there
- What broke: static wiki pages generated once and kept rot over time
- Derived-on-demand pages can't rot

**OpenAIToolsHub — Six months in with Obsidian + Claude**

- Pitfall: forgetting to lint after big ingest weeks
- Dumped 6–8 articles over a weekend, skipped lint, ended up with orphan pages and contradictions
- Cost: ~1 week of confusion about "what's the current view?"
- Lesson: lint protocol isn't optional

### Negative / Cautionary Experiences

**Reddit r/LLM — "We built Karpathy's LLM Wiki — the LLM read it, understood it, and ignored it anyway"**

- Built for supply chain AI with 200+ pages, Wikipedia-style linking
- Agent reads wiki before every query but still ignores wiki guidance
- A column name "FINAL_REASON" was louder than four wiki pages saying "don't rely on this"
- Lesson: wiki guidance must be enforced in system prompts/tool definitions, not just read passively

**DEV Community — "The Lint Ran Every Week. The Dead-Link Count Never Went Down."**

- Weekly lint ran but recovered nothing
- Dead links and orphans accumulated despite linting
- Lesson: lint needs enforcement/follow-through, not just reporting

**Medium — "I Tried to Build Karpathy LLM WIKI. Here's Where It Broke Down for Me."**

- Maintenance overhead slowly exceeded perceived value
- Usage dropped to zero gradually, not dramatically
- Couldn't maintain the inputs

**Reddit r/ObsidianMD — u/UnderneathTheBottle6**

- Pattern "ingest → generate/synthesize → hoard" cheapened the material produced
- Hoarding without distillation loses value

---

## 4. Practical Implementation — Folder Structure

```
your-vault/
├── CLAUDE.md              # Agent config (Claude Code) or AGENTS.md (Codex)
├── log.md                 # Vault-level setup log (optional)
├── raw/                   # Layer 1 — IMMUTABLE source of truth (human-owned)
│   ├── assets/            # Downloaded images from clipped articles
│   ├── papers/
│   ├── articles/
│   └── <source files>     # Articles, papers, PDFs, images, data files
├── wiki/                  # Layer 2 — LLM-owned knowledge base
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

**Naming conventions:**

- Filenames: kebab-case + `.md` (e.g., `article-title-here.md`)
- H1 titles: Title Case (e.g., `# Article Title Here`)
- Internal links: `[[Page Title]]` (wikilinks using Title Case, not filename)
- Frontmatter on every wiki page:

  ```yaml
  ---
  type: source \| entity \| concept \| synthesis \| query
  title: Page Title
  sources: [source-filename-1.md, source-filename-2.md]
  created: YYYY-MM-DD
  updated: YYYY-MM-DD
  tags: [tag1, tag2]
  ---
  ```

---

## 5. Schema File — CLAUDE.md / AGENTS.md Template

This is the **single source of truth** that makes the LLM a disciplined wiki maintainer. Co-evolve with your LLM as you learn what works.

### Recommended Sections

1. **Architecture** — three directories, wiki subdirectories, two special files (index.md, log.md)
2. **Page format** — YAML frontmatter + wikilink syntax rules
3. **Naming** — kebab-case filenames, Title Case H1, `[[Page Title]]` links
4. **Operations** — step-by-step ingest, query, lint workflows
5. **Rules** — 8-10 hard rules (never modify raw, always update index/log, etc.)
6. **Lint frequency** — after every 10 ingests, monthly minimum, before major queries
7. **Image handling** — download to `raw/assets/`, reference from wiki, describe in text
8. **Optional tools** — summarize, qmd, agent-browser

### Example: Ingest Operation (from Karpathy's gist + NicholasSpisak)

```
When the user adds a file to raw/ and asks you to process it:

1. Read the source completely
2. Discuss key takeaways with the user
3. Create a source summary page in wiki/sources/ with title, source metadata, key claims, structured summary
4. Identify all entities and concepts mentioned:
   - If a wiki page exists: update it with new info, noting the source
   - If no wiki page exists: create one in the appropriate subdirectory
5. Add [[wikilinks]] between all related pages
6. Update wiki/index.md with any new pages
7. Append to wiki/log.md: ## [YYYY-MM-DD] ingest | Source Title

A single source may touch 10-15 wiki pages. That is normal.
```

### Example: Query Operation

```
When the user asks a question:

1. Read wiki/index.md to find relevant pages
2. Read the relevant wiki pages
3. Synthesize an answer with [[wikilink]] citations to wiki pages
4. If the answer produces a valuable artifact (comparison, analysis, new connection), offer to save it as a new page in wiki/synthesis/
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

## 6. Operations — The Ingest/Query/Lint Cycle

### Ingest (drop source → create/update wiki pages)

**Flow:**

1. User drops source into `raw/`
2. LLM reads source, discusses takeaways with user
3. LLM writes summary page in `wiki/sources/`
4. LLM creates/updates entity and concept pages (10-15 pages per source is normal)
5. LLM adds `[[wikilinks]]` between related pages
6. LLM updates `wiki/index.md`
7. LLM appends to `wiki/log.md`

**Tips from practitioners:**

- Ingest one source at a time, stay involved — read summaries, guide emphasis
- Batch-ingest many sources at once with less supervision (document in schema)
- Download images locally (Obsidian Web Clipper + "Download attachments" hotkey)
- LLMs can't read inline images in one pass — read text first, then view images separately

### Query (read index → synthesize with citations)

**Flow:**

1. LLM reads `wiki/index.md` first to find relevant pages
2. LLM drills into matched pages
3. LLM synthesizes answer with `[[wikilink]]` citations
4. Valuable artifacts (comparisons, analyses) get saved as `wiki/synthesis/` pages
5. Update index and log for new pages

**Scale note:** `index.md` + keyword search works up to ~100 pages. Beyond that, add `qmd` (hybrid BM25 + vector search, local, on-device).

### Lint (health check for contradictions/orphans/stale claims)

**Flow:**

1. Scan all wiki pages + index
2. Check: broken links, orphan pages, index completeness, stale entries, missing pages, frontmatter validation
3. Report by severity (errors → warnings → info)
4. Offer fixes
5. Log the lint pass

**Practitioner warnings:**

- Lint is not optional — skipping leads to contradictions and orphan pages
- Weekly lint that only reports without fixing recovers nothing
- Run lint after every 10 ingests or monthly minimum

---

## 7. Tooling Recommendations

| Tool | Purpose | Install | When to add |
|---|---|---|---|
| **Obsidian** | Frontend / graph view / reading wiki | obsidian.md | Day 1 |
| **Obsidian Web Clipper** | Save web articles as markdown to `raw/` | Chrome extension | Day 1 |
| **qmd** | Local hybrid search (BM25 + vector) for wiki | `npm i -g @tobilu/qmd` | When wiki > ~100 pages |
| **summarize** | Summarize links, files, media from CLI | `npm i -g @steipete/summarize` | Optional |
| **agent-browser** | Browser automation for web research | `npm i -g agent-browser` | Optional |

---

## 8. How to Create an Agent Skill from This

If you want to package this as an installable agent skill (like NicholasSpisak's second-brain), structure it like this:

```
your-skill/
├── SKILL.md              # Skill manifest (name, description, allowed-tools)
├── references/
│   ├── wiki-schema.md    # Canonical wiki rules (single source of truth)
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

**SKILL.md pattern** (from NicholasSpisak):

```markdown
---
name: second-brain
description: >
  Set up a new Obsidian knowledge base with the LLM Wiki pattern.
allowed-tools: Bash Read Write Glob Grep
---
# Second Brain — Onboarding Wizard

## Wizard Flow
Guide user through 5 steps, one question at a time:
1. Vault name (default: second-brain)
2. Vault location (default: ~/Documents/)
3. Domain / topic
4. Agent config (auto-detect agent, generate CLAUDE.md/AGENTS.md)
5. Optional CLI tools (summarize, qmd, agent-browser)

## Post-Wizard: Scaffold the Vault
1. Create directory structure (raw/, wiki/, output/, CLAUDE.md)
2. Generate agent config files from templates
3. Update wiki/log.md with setup entry
4. Install CLI tools if selected
5. Print summary with next steps
```

**Agent detection logic:**

- Claude Code → CLAUDE.md
- Codex → AGENTS.md
- Cursor → `.cursor/rules/*.mdc`
- Gemini CLI → GEMINI.md

---

## 9. Pitfalls and Lessons Learned (from practitioners)

| Pitfall | Evidence | Mitigation |
|---|---|---|
| Skipping lint after big ingest weeks | OpenAIToolsHub: 3 orphan pages + 1 contradiction after month of skipping | Make lint mandatory after every 10 ingests |
| Lint only reports, doesn't fix | DEV Community: weekly lint recovered nothing | Lint must offer and apply fixes, not just report |
| LLM reads wiki but ignores guidance | Reddit r/LLM: "FINAL_REASON" column louder than wiki pages | Enforce wiki guidance in system prompts/tool definitions, not just passive reading |
| Static wiki pages rot | Reddit r/ObsidianMD (u/Dementiy): pages generated once and kept rot | Treat wiki pages as derived-on-demand, regenerate when sources change |
| Maintenance overhead exceeds value | Medium: usage dropped to zero gradually | Start small, automate ingest, keep human curation light |
| Messy sources (scanned PDFs, unloadable sites) | Reddit r/AI_Agents: Week 2 cracks | Invest in source cleaning pipeline early |
| Hoarding without distillation | Reddit r/ObsidianMD: "ingest→generate→hoard" cheapens material | Save synthesis artifacts back to wiki, don't just accumulate summaries |

---

## 10. Quick Start Checklist

- [X] Create vault folder with `raw/`, `wiki/` (with subdirs), `output/`
- [X] Write `CLAUDE.md` (Claude Code) or `AGENTS.md` (Codex) using the schema template
- [X] Initialize git in vault root
- [X] Install Obsidian, open vault folder
- [X] Install Obsidian Web Clipper, configure to save to `raw/`
- [X] Set Obsidian attachment folder to `raw/assets/`, bind "Download attachments" hotkey
- [X] Perform first ingest: clip an article to `raw/`, run ingest operation
- [ ] Run query: ask a question, verify citations point to wiki pages
- [ ] Run lint: health-check the wiki
- [ ] When wiki > ~100 pages, install `qmd` for search

---

## 11. Source Links

**Primary sources:**

- Karpathy X post: https://x.com/karpathy/status/2039805659525644595
- Karpathy gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Karpathy gist raw: https://gist.githubusercontent.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md

**Practitioner repos:**

- Garry Tan gbrain: https://github.com/garrytan/gbrain (31K+ stars)
- gbrain schema: https://github.com/garrytan/gbrain/blob/master/docs/GBRAIN_RECOMMENDED_SCHEMA.md
- NicholasSpisak second-brain: https://github.com/nicholasspisak/second-brain
- frankchu91 mindbase: https://github.com/frankchu91/mindbase-llm-wiki
- DimitrisLianos LLM_Wiki_SecondBrain: https://github.com/DimitrisLianos/LLM_Wiki_SecondBrain
- microsoft/llmwiki: https://github.com/microsoft/llmwiki
- green-dalii obsidian-llm-wiki: https://github.com/green-dalii/obsidian-llm-wiki

**Practitioner experiences:**

- Reddit r/AI_Agents (weekend build): https://www.reddit.com/r/AI_Agents/comments/1sqg5ew/
- Reddit r/AI_Agents (month in): https://www.reddit.com/r/AI_Agents/comments/1tqvsds/
- Reddit r/ObsidianMD (quarter in): https://www.reddit.com/r/ObsidianMD/comments/1vcgr8z/
- Reddit r/LocalLLaMA: https://www.reddit.com/r/LocalLLaMA/comments/1sclfs6/
- OpenAIToolsHub (six months): https://www.openaitoolshub.org/en/blog/karpathy-llm-wiki
- DEV Community (lint failure): https://dev.to/michaeltuszynski/the-lint-ran-every-week-the-dead-link-count-never-went-down-22m1
- Medium (broke down): https://medium.com/@theo-james/i-tried-to-build-karpathy-llm-wiki-heres-where-it-broke-down-for-me-9c3eef65af21
