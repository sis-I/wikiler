# Karpathy LLM Wiki Research

## Scope

This note answers three questions:

1. What did Andrej Karpathy's LLM Wiki idea actually propose?
2. How do the implementations cited in `docs/guides/KARPATHY_WIKI_IMPLEMENTATION_GUIDE.md` compare?
3. Which guide claims are supported, overstated, contradicted, or unresolved?

The research snapshot was taken on 2026-11-16. Repository popularity figures are included only to identify the referenced projects. They are volatile and are not evidence of architectural quality.

The canonical source for Karpathy's proposal is the gist at https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f. The raw file is at https://gist.githubusercontent.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md.

## Executive findings

1. Karpathy's gist is an abstract idea file, not an implementation specification. It explicitly leaves directory layout, page format, schema conventions, and tooling to the user.
2. The guide mixes three different things together: Karpathy's proposal, the guide author's recommended implementation, and this repository's stricter `wiki-engine` conventions.
3. The canonical gist gives a scale statement of about 100 sources and hundreds of pages. It does not give a 400,000 word threshold.
4. The guide's `[[Page Title]]` link recommendation is not stated in Karpathy's gist. The current repository's `[[dir/slug|Page Title]]` grammar is a stronger local convention motivated by ambiguous bare stems.
5. The strongest precedent for this repository's agent integration is a portable Agent Skill backed by a CLI. A second-brain project already packages the ingest, query, and lint workflows this way.
6. MCP is a credible later integration surface, but copying the tool counts of larger products would be premature. A small stable tool contract should precede a larger MCP surface.
7. The guide's practitioner anecdotes are useful hypotheses about maintenance failure modes. They are not general evidence and should not be presented as such.

## 1. What Karpathy proposed

### Canonical source

Karpathy's gist describes the LLM Wiki pattern. The related X post is titled "LLM Knowledge Bases" and is dated April 2, 2026 by X's oEmbed response at https://publish.twitter.com/oembed?url=https://twitter.com/karpathy/status/2039805659525644595.

The gist itself does not state a publication date inside the document. It identifies itself as an idea file designed to be copied into an LLM agent.

### Explicit proposal

The following elements come directly from the gist:

- **Persistent compilation.** RAG retrieves source fragments and re-derives an answer for each question. The wiki instead becomes a persistent, interlinked artifact that is updated as sources arrive.
- **Three conceptual layers.**
  - Raw sources are curated, immutable source material.
  - The wiki contains LLM-generated Markdown pages that the LLM owns and maintains.
  - The schema is an agent configuration document that defines structure and workflows.
- **Three operations.**
  - Ingest reads a new source, discusses it with the user, writes a summary, updates related pages, and records the operation.
  - Query searches the wiki, synthesizes a cited answer, and can file valuable answers back into the wiki.
  - Lint checks for contradictions, stale claims, orphans, missing concepts, missing cross-references, and research gaps.
- **Two special files.**
  - `index.md` is a content catalog organized by category.
  - `log.md` is an append-only timeline of operations.
- **Human and LLM roles.** The human curates sources, directs analysis, asks questions, and interprets meaning. The LLM performs the mechanical and editorial work of maintaining the wiki.
- **Moderate-scale retrieval.** The gist says that reading `index.md` works at roughly 100 sources and hundreds of pages.
- **Optional search.** The gist names `qmd` as an optional local hybrid search engine with a CLI and an MCP server. It points to https://github.com/tobi/qmd.
- **Tooling tips.** The gist mentions Obsidian Web Clipper, local image downloads, Obsidian graph view, Marp, Dataview, and Git version control.

The gist's closing note is decisive for interpreting the guide:

> This document is intentionally abstract. It describes the idea, not a specific implementation.

### What Karpathy did not specify

The gist does not prescribe any of the following:

- The `wiki/sources`, `wiki/entities`, `wiki/concepts`, `wiki/synthesis`, and `wiki/queries` directory split.
- The YAML fields `type`, `title`, `sources`, `created`, `updated`, and `tags`.
- A filename convention.
- A wikilink grammar.
- A 400,000 word scale threshold.
- A Python engine, an MCP server, an Obsidian plugin, or a VS Code extension.
- A particular agent harness.

These are implementation decisions. They can be excellent decisions, but they should not be attributed to Karpathy.

## 2. Referenced implementations

### Repository metadata snapshot

The following counts came from GitHub's repository API on 2026-11-16:

- `garrytan/gbrain`: 33,140 stars, MIT license, created 2026-04-05. Source: https://github.com/garrytan/gbrain.
- `NicholasSpisak/second-brain`: 779 stars, no repository license detected, created 2026-04-06. Source: https://github.com/NicholasSpisak/second-brain.
- `frankchu91/mindbase-llm-wiki`: 137 stars, MIT license, created 2026-04-26. Source: https://github.com/frankchu91/mindbase-llm-wiki.
- `DimitrisLianos/LLM_Wiki_SecondBrain`: 18 stars, MIT license, created 2026-04-10. Source: https://github.com/DimitrisLianos/LLM_Wiki_SecondBrain.
- `microsoft/llmwiki`: 116 stars, MIT license, created 2026-04-09. Source: https://github.com/microsoft/llmwiki.
- `GD4AI/obsidian-llm-wiki`: 796 stars, Apache-2.0 license, created 2026-04-26. The older `green-dalii/obsidian-llm-wiki` URL redirects to this canonical repository. Source: https://github.com/GD4AI/obsidian-llm-wiki.

### Architecture comparison

#### garrytan/gbrain

- Product shape: production agent brain with a CLI, skills, and an MCP server.
- Storage: Markdown remains the human and LLM interface. PGLite is the default local engine, with PostgreSQL and pgvector available as a production option. Source: https://github.com/garrytan/gbrain/blob/master/docs/ENGINES.md.
- Retrieval: vector, lexical, and graph retrieval. Source: https://github.com/garrytan/gbrain/blob/master/docs/architecture/RETRIEVAL.md.
- Page model: compiled truth above a horizontal-rule separator, followed by an append-only timeline. Source: https://github.com/garrytan/gbrain/blob/master/docs/GBRAIN_RECOMMENDED_SCHEMA.md.
- Scale: the README reports 155,795 pages, 24,589 people, and 5,340 companies. These are first-party claims rather than independently audited measurements.
- Important distinction: continuous enrichment from meetings, email, calendars, and other feeds is a later architecture. It is not the manual source-drop pattern in Karpathy's gist.

#### NicholasSpisak/second-brain

- Product shape: four portable Agent Skills for setup, ingest, query, and lint.
- Distribution: `npx skills add NicholasSpisak/second-brain`.
- Vault contract: `raw/`, `wiki/`, `output/`, and a generated agent configuration file.
- Retrieval: `index.md` at small scale, with optional `qmd` as the wiki grows.
- Setup: an idempotent wizard that does not overwrite an existing vault.
- Source: https://github.com/NicholasSpisak/second-brain.

This is the closest precedent for a professional `wiki-engine` agent integration. It keeps the agent workflow portable and delegates mechanical behavior to scripts rather than embedding it in one harness extension.

#### frankchu91/mindbase-llm-wiki

- Product shape: local MCP server and web application.
- Tool surface: 49 MCP tools in the current server documentation. Source: https://github.com/frankchu91/mindbase-llm-wiki/blob/main/apps/mcp/README.md.
- Write safety: the product asks before applying a write plan and distinguishes human-written from agent-written content.
- Local behavior: plain Markdown storage, local indexes, and optional local Ollama models.
- Scale: semantic and graph-aware retrieval sit on top of a local file store.
- Source: https://github.com/frankchu91/mindbase-llm-wiki.

The useful lesson is the explicit write boundary and provenance. The broad 49-tool surface is not a target for `wiki-engine` at its current stage.

#### DimitrisLianos/LLM_Wiki_SecondBrain

- Product shape: fully local Python implementation with an optional web interface.
- Storage and retrieval: SQLite FTS5, a wikilink graph, and reciprocal rank fusion. A documented decision rejects a vector database.
- Runtime: a standard-library Python core, with an optional LLM runtime and web stack.
- Source: https://github.com/DimitrisLianos/LLM_Wiki_SecondBrain.

This project demonstrates that a local, dependency-light engine can support richer retrieval without adopting a large service architecture.

#### microsoft/llmwiki

- Product shape: TypeScript monorepo with a VS Code extension, an MCP server, and a Copilot plugin.
- Storage: a `.wiki/` root rather than this repository's `wiki/` root.
- Tool documentation: the current reference calls itself a 14-tool reference but lists 18 tool headings. It also lists six lint categories. Source: https://github.com/microsoft/llmwiki/blob/main/docs/mcp-tools.md.
- Quality practice: the repository has tests and CI that check builds, types, and generated plugin output.
- Source: https://github.com/microsoft/llmwiki.

This is the strongest product engineering precedent in the reference set, but it also shows why an MCP-first product creates a larger maintenance surface.

#### GD4AI/obsidian-llm-wiki

- Product shape: native Obsidian community plugin with no separate terminal application.
- Retrieval: personalized PageRank and BM25F over the wikilink graph, without a vector database.
- Models: supports local and hosted providers, including local model servers.
- Source: https://github.com/GD4AI/obsidian-llm-wiki.

This product avoids the need for a separate agent harness by moving the workflow into Obsidian. That is valuable for users who want a single application, but it does not remove the need for a portable agent contract in this repository.

## 3. Audit of the implementation guide

### Karpathy's proposal

- **Verified:** the guide correctly identifies the gist as an abstract idea file with three layers, three operations, and two special files.
- **Verified:** the `qmd` recommendation is supported by Karpathy's gist and the upstream project at https://github.com/tobi/qmd.
- **Overstated:** the guide combines about 100 sources with about 400,000 words. The canonical gist says about 100 sources and hundreds of pages. It does not mention 400,000 words.
- **Misattributed:** the guide's exact folder tree, frontmatter schema, filename rules, and title-style wikilinks are presented as Karpathy conventions. They are not in the gist.
- **Local divergence:** this repository deliberately requires path-qualified wikilinks. That convention is stricter than the guide and should be documented as a `wiki-engine` design decision.

### Practitioner repositories

- **Directionally verified:** the guide's gbrain popularity figure was an understatement at the time of research. Popularity remains volatile and is not a quality measure.
- **Verified as a first-party claim:** gbrain's page, person, and company counts appear in its README. They were not independently audited.
- **Verified:** second-brain provides four Agent Skills and an idempotent onboarding wizard.
- **Verified with correction:** MindBase currently documents 49 MCP tools, not 48.
- **Verified with correction:** the Microsoft reference lists six lint categories, not seven. Its stated tool count is internally inconsistent because the title says 14 while the document enumerates 18 headings.
- **Verified:** the Obsidian project is a native plugin with local and hosted model support.
- **New professional finding:** second-brain has no repository license detected. A reusable agent skill without a license is a distribution risk, even if its code is publicly readable.

### Practitioner experiences

The Reddit, DEV Community, Medium, and blog experiences in the guide are anecdotal. They are useful prompts for product questions, especially these:

- Does lint lead to repair, or only reporting?
- Does the workflow remain valuable after the initial novelty?
- Does the agent actually follow the vault schema?
- Do generated pages stay current as sources change?
- Does synthesis prevent the vault from becoming a summary warehouse?

They should be labeled as anecdotes and should not support universal claims about the pattern.

### The MindBase post discrepancy

MindBase's README points to X status `1911080091498963196`, while the guide points to `2039805659525644595`. The latter has a working X oEmbed response and is the April 2, 2026 "LLM Knowledge Bases" post. The former currently returns not found through X oEmbed and predates the LLM Wiki announcement. The guide's status is the canonical one for this effort.

## 4. Implications for this repository

### Preserve the engine and agent boundary

Karpathy's three layers are conceptual ownership boundaries. They do not require separate source repositories. The current implementation adds a useful product boundary:

- The engine owns deterministic structure, validation, indexing, and reconciliation.
- The agent owns meaning, claims, synthesis, and page selection.
- The vault owns human-curated sources and derived content.

This repository has already made that boundary clearer than most examples in the guide. The new work should preserve it rather than collapse engine behavior back into prompts.

### Make engine and vault separation explicit

A professional layout should let the engine operate on any vault without importing personal content or Obsidian state into the package. The repository can still track a default vault for demonstration, but it should distinguish:

- Product code and public documentation.
- A sanitized example vault.
- User-specific source material, assets, and editor state.

The exact repository boundary remains a product decision. It should not be presented as a requirement from Karpathy.

### Start with one portable Agent Skill

Both Pi and OpenCode support the shared Agent Skills format and discover project skills under `.agents/skills/`.

- Agent Skills specification: https://agentskills.io/specification.
- Pi skills documentation: https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md.
- OpenCode skills documentation: https://opencode.ai/docs/skills/.

A single `wiki-engine` skill can describe the shared workflow and route to ingest, query, lint, or sync. It can point to stable CLI commands and structured JSON output. This gives Pi and OpenCode one source of truth without maintaining two harness adapters.

### Defer native extensions and plugins

Pi extensions can register custom tools and commands. Source: https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/extensions.md.

OpenCode plugins can add tools, commands, hooks, and agents. Source: https://opencode.ai/docs/plugins/.

Those surfaces are useful when native tool calls, interactive setup, or richer rendering remove real friction. They are not required for the first portable workflow. Maintaining both a Pi extension and an OpenCode plugin would duplicate product logic unless both call a stable shared service.

### Treat MCP as a later protocol surface

MindBase, Microsoft `llmwiki`, and `qmd` all demonstrate that MCP can expose a local wiki. The current CLI already has a natural five-operation contract:

- `init`
- `ingest`
- `query`
- `lint`
- `sync`

A future MCP server should expose that contract rather than reproduce 18 or 49 overlapping tools. MCP should follow a stable CLI and JSON contract, not lead the product design.

### Correct the guide's authority

The guide should remain, but it should be labeled as a secondary implementation guide. It should link to the research note and distinguish:

1. Direct statements from Karpathy.
2. Claims about external projects.
3. Anecdotal practitioner experiences.
4. This repository's chosen conventions.

The 400,000 word threshold should be removed or attributed to secondary coverage. The guide's title-style link syntax should either be reconciled with the repository's path-qualified syntax or clearly labeled as an alternative convention.

## 5. Recommended first professional release

The research supports this release shape:

1. An installable `wiki-engine` Python package with a documented CLI.
2. A repository layout that clearly separates engine code, public documentation, and a sanitized example vault.
3. A root README with quick start, architecture, safety guarantees, and vault creation instructions.
4. CI for tests, packaging checks, and supported Python versions.
5. Complete package metadata, a license, a changelog, and a release process.
6. One portable Agent Skill under `.agents/skills/wiki-engine/`.
7. A corrected implementation guide linked to the primary research note.
8. Optional Pi and OpenCode native adapters only after a demonstrated need.
9. Optional MCP support only after the CLI and JSON contracts are stable.

This shape captures the strongest validated ideas from the reference projects without importing their full operational complexity.

## Open decisions

These decisions remain for the repository owner:

1. Should this repository be public, private, or split between a public engine and a private content vault?
2. Should the tracked default vault contain real research material, a sanitized example, or both?
3. Should the first Agent Skill be one routing skill or separate skills for setup, ingest, query, and lint?
4. What compatibility promise should the CLI and JSON output provide?
5. Should the existing GitHub repository be renamed to `wiki-engine`?

## Primary sources

- Karpathy gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f.
- Karpathy gist raw: https://gist.githubusercontent.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md.
- Karpathy X post metadata: https://publish.twitter.com/oembed?url=https://twitter.com/karpathy/status/2039805659525644595.
- garrytan/gbrain: https://github.com/garrytan/gbrain.
- gbrain engines: https://github.com/garrytan/gbrain/blob/master/docs/ENGINES.md.
- gbrain retrieval: https://github.com/garrytan/gbrain/blob/master/docs/architecture/RETRIEVAL.md.
- gbrain schema: https://github.com/garrytan/gbrain/blob/master/docs/GBRAIN_RECOMMENDED_SCHEMA.md.
- NicholasSpisak/second-brain: https://github.com/NicholasSpisak/second-brain.
- frankchu91/mindbase-llm-wiki: https://github.com/frankchu91/mindbase-llm-wiki.
- MindBase MCP reference: https://github.com/frankchu91/mindbase-llm-wiki/blob/main/apps/mcp/README.md.
- DimitrisLianos/LLM_Wiki_SecondBrain: https://github.com/DimitrisLianos/LLM_Wiki_SecondBrain.
- microsoft/llmwiki: https://github.com/microsoft/llmwiki.
- Microsoft MCP reference: https://github.com/microsoft/llmwiki/blob/main/docs/mcp-tools.md.
- GD4AI/obsidian-llm-wiki: https://github.com/GD4AI/obsidian-llm-wiki.
- qmd: https://github.com/tobi/qmd.
- Agent Skills specification: https://agentskills.io/specification.
- Pi skills documentation: https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md.
- Pi extensions documentation: https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/extensions.md.
- OpenCode skills documentation: https://opencode.ai/docs/skills/.
- OpenCode plugins documentation: https://opencode.ai/docs/plugins/.
- Audited guide: `docs/guides/KARPATHY_WIKI_IMPLEMENTATION_GUIDE.md`.
- Repository architecture decision: `docs/adr/0001-sync-verb.md`.
