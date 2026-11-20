# Wikiler Vault Rules: Runtime Agent Contract

This document is the packaged runtime rules template. It is copied into every
new vault by `wiki init` and is the single source of truth for agents
operating a Wikiler vault. The repository-level `AGENTS.md` (for engine
contributors) is a separate document.

## Engine and agent roles

The engine is the mechanical half; the agent is the judgment half. Neither
side does the other's job.

- **Agent (LLM):** judgment. Read and discuss sources, write summaries,
  claims, and definitions, choose which entities and concepts matter,
  synthesize cited answers, and judge contradictions, staleness, coverage
  gaps, and emphasis.
- **Engine (`wikiler`):** mechanics. Scaffold pages, validate frontmatter,
  filenames, H1 form, and links, resolve retrieval candidates, maintain
  `wiki/index.md` and `wiki/log.md`, and apply safe mechanical repairs.
- **Boundary:** the engine may reject or repair *form*; it must never decide
  *meaning*. Anything it cannot determine deterministically is emitted as a
  suggestion or `<!-- TODO -->` marker for the agent to resolve.

If a rule below can be checked mechanically, `wiki lint` owns it. If it
requires reading for sense, the agent owns it.

## Architecture: Three Layers

- `raw/`: Layer 1, human-owned source of truth. Organized by topic:
  `articles/`, `papers/`, `repos/`, `datasets/`, plus `assets/` for
  downloaded images. `raw/` source files are immutable: the engine may write
  only downloaded assets to `raw/assets/` and must never rewrite, move, or
  delete anything else under `raw/`.
- `wiki/`: Layer 2, LLM-owned knowledge base. Contains `sources/`,
  `entities/`, `concepts/`, `synthesis/`, `queries/`, plus `index.md` and
  `log.md`.
- `output/`: Reports, query results, generated artifacts.

## Special Files

- `wiki/index.md`: Content catalog, one line per page, categorized.
  Reconcile with `wiki sync`; do not hand-edit.
- `wiki/log.md`: Append-only timeline, entries like
  `## [YYYY-MM-DD] op | title`. Reconcile with `wiki sync`; do not
  hand-edit.
- Log operation names: `setup | ingest | query | synthesis | sync | lint`.

## Page Format

Every wiki page uses YAML frontmatter plus a Title Case H1:

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

- `type`: one of `source`, `entity`, `concept`, `synthesis`, `query`.
- `title`: the page title; matches the H1 once a trailing type suffix is
  ignored.
- `sources`: source filenames this page derives from.
- `created`: set once, on creation, and preserved thereafter.
- `updated`: refreshed whenever the page changes.
- `tags`: free-form retrieval tags.

Ownership:

- **Engine** guarantees valid YAML, the required fields, and
  `created`/`updated` semantics.
- **Agent** owns the Title Case H1 (e.g. `# LLM Inference Optimization`).
- **Both** keep filenames kebab-case + `.md` (e.g.
  `llm-inference-optimization.md`). The engine rejects other names; the
  agent must not create them.

## Links

Use file-path wikilinks only:

`[[dir/slug|Page Title]]`, where `dir` is one of `sources | entities |
concepts | synthesis | queries`.

- Valid: `[[concepts/llm-inference-optimization|LLM Inference Optimization]]`
- Invalid: `[[LLM Inference Optimization]]` (title link),
  `[[llm-inference-optimization]]` (bare stem),
  `[[Foo (concept)]]` (title with type suffix).

The display title may keep the type suffix used by the page, for example
`[[entities/gbrain|GBrain (entity)]]`; the target must always be a path.

## Operations

Every step is marked with its owner: `[engine]`, `[agent]`, or `[shared]`.

### Setup (init)

1. `[engine]` `wiki init` scaffolds `raw/`, `raw/assets/`,
   `wiki/sources/`, `wiki/entities/`, `wiki/concepts/`,
   `wiki/synthesis/`, `wiki/queries/`, `output/`, `wiki/index.md`, and
   `wiki/log.md`. It logs the operation as `setup`.
2. `[agent]` Never run another command against a directory that is not a
   vault. `init` is the only command that creates one.

### Ingest (drop source → scaffold → author pages)

When the user adds a file to `raw/` and asks to process it:

1. `[engine]` `wiki ingest <path>` reads a source under `raw/`, writes a
   scaffold to `wiki/sources/<slug>.md` with frontmatter and `<!-- TODO:
   agent -->` markers, and lists the source's images with the alt text or
   caption the source already carries. It performs no network I/O: local
   `raw/assets/` links and Obsidian `![[asset]]` embeds are listed as local,
   and remaining remote URLs are reported in the manifest as not downloaded.
   Pass `--download-images` for a source that never went through Obsidian;
   it fetches those URLs into `raw/assets/`. Re-running it leaves an
   authored body untouched; `--force` discards it and starts the scaffold
   over.
2. `[agent]` Read the source completely and discuss key takeaways with the
   user.
3. `[agent]` Fill the scaffold: source metadata, key claims, structured
   summary, and image descriptions. Describe only images whose meaning the
   prose or caption does not already capture; skipping decorative images is
   fine. Write the prose; the engine never does.
4. `[agent]` Identify all entities and concepts mentioned:
   - If a wiki page exists: update it with new info, noting the source.
   - If no wiki page exists: create one in the appropriate subdirectory
     with the required frontmatter and H1.
5. `[agent]` Add file-path wikilinks between all related pages.
6. `[shared]` The agent writes the pages, then `wiki sync` reconciles
   `wiki/index.md` and `wiki/log.md`. The engine records the ingest
   operation when it scaffolds.

A single source may touch 10 to 15 wiki pages. That is normal.

### Query (retrieve → synthesize)

When the user asks a question:

1. `[engine]` `wiki query <question>` reads `wiki/index.md`, matches
   candidate pages, and prints a ranked list with a short snippet from each.
   It does not answer.
2. `[agent]` Read the candidate pages and synthesize the answer with
   file-path wikilink citations.
3. `[agent]` If the answer produces a valuable artifact (comparison,
   analysis, new connection), offer to save it.
4. `[shared]` The agent writes `wiki/synthesis/<slug>.md`;
   `wiki sync` registers it in `index.md` and `log.md`.

The engine never fabricates an answer and never saves a page on the agent's
behalf.

### Sync (reconcile index, frontmatter, log)

`wiki sync` reconciles `index.md` and `log.md` with the pages on disk. It
is the durable mechanic behind Rule 2; `ingest` also updates them for the
source it scaffolds. `sync` never edits a page body and never invents
content.

1. `[engine]` Append an index entry for every page on disk that lacks one.
2. `[engine]` Normalise frontmatter quoting, ensure the required keys exist,
   set `created` once, and refresh `updated` only when a page changed.
3. `[engine]` Append a dated log entry only when something changed.
4. `[agent]` Run `sync` after writing or editing pages.

It must be idempotent: a second run with nothing to do writes nothing and
logs nothing.

### Lint (mechanical scan → agent review)

`wiki lint` is the mechanical half. It checks frontmatter, filenames,
H1 form, link form and resolution, orphans, and index/log consistency.
Under `--fix` it repairs only what it can resolve unambiguously.

1. `[agent]` Run `wiki lint [--json] [--fix]`.
2. `[engine]` The scan reports structural findings by severity (errors
   → warnings → info) and applies only unambiguous repairs under `--fix`.
3. `[agent]` Review the report. Fix what the engine cannot decide:
   contradictions between pages, stale claims superseded by newer sources,
   important concepts lacking a page, missing cross-references, and data
   gaps fillable with web search.
4. `[shared]` The agent approves or performs semantic fixes and re-runs
   lint until structural errors are zero.

Aim to lint after every 10 ingests, monthly, and before major queries.
Cadence tracking is deferred; it is agent-managed, not engine-enforced.

## Command Reference

Run from the engine workspace with `--vault <path>`, or set `WIKI_VAULT`.
This reference is the contract; a missing command is an engine gap, not a
licence to hand-edit `index.md` or `log.md`.

```
wiki init
wiki ingest <path> [--download-images] [--json] [--force]
wiki query <question> [--json]
wiki sync
wiki lint [--json] [--fix]
```

- `ingest` performs no network I/O by default: it lists local
  `raw/assets/` images and reports remote URLs as not downloaded.
  `--download-images` fetches the remaining remote URLs into
  `raw/assets/`, naming files from the URL.
- `ingest --json` prints the scaffold manifest as one JSON object and
  nothing else on stdout. `--force` is destructive: it rewrites an
  existing scaffold, discarding the agent-authored body and restoring the
  TODO markers. It preserves `created` and refreshes `updated`.
- `query --json` prints the ranked candidates as JSON.
- `lint --json` prints findings as JSON; `--fix` applies only unambiguous
  mechanical repairs.

## Rules

1. `raw/` source files are immutable. The engine may write only downloaded
   assets to `raw/assets/`; it must never rewrite, move, or delete anything
   else under `raw/`.
2. When pages are added or changed, run `wiki sync` to reconcile
   `wiki/index.md` and `wiki/log.md`. Never hand-edit either file.
3. The engine guarantees valid YAML, the required frontmatter fields
   (`type`, `title`, `sources`, `created`, `updated`, `tags`), and
   `created`/`updated` semantics. The agent authors the Title Case H1; the
   engine validates that an H1 exists and is Title Case. `created` is set
   once and preserved; `updated` changes on edit.
4. Use the link grammar `[[dir/slug|Page Title]]`, where `dir` is one of
   `sources | entities | concepts | synthesis | queries`. Valid:
   `[[concepts/llm-inference-optimization|LLM Inference Optimization]]`.
   Invalid: `[[llm-inference-optimization]]` (bare stem),
   `[[LLM Inference Optimization]]` (title link),
   `[[Foo (concept)]]` (title with type suffix).
5. Use kebab-case filenames.
6. Images are local-first and opt-in. `ingest` performs no network I/O: it
   lists the images the source already references in `raw/assets/` (saved by
   the Obsidian hotkey) and reports remaining remote URLs as not downloaded.
   Pass `--download-images` only for sources that never went through Obsidian.
   Reference images from wiki pages, and describe only those whose meaning
   the prose or caption does not already carry; skipping decorative images is fine.
7. `wiki lint` is the mechanical half of the health check; the agent
   runs it and reviews the report. Cadence (every 10 ingests, monthly,
   before major queries) is agent-managed; tracking is deferred, not
   engine-enforced.
8. The engine enforces structural invariants (frontmatter, filenames, H1
   form, link form and resolution, orphans, index/log reconciliation); the
   agent enforces semantic invariants (contradictions, stale claims,
   coverage gaps, emphasis).
9. One source at a time; stay involved, read summaries, guide emphasis.
10. Treat wiki pages as derived-on-demand: regenerate when sources change,
    do not let them rot.
