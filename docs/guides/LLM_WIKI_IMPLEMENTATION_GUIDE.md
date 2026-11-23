# LLM Wiki Implementation Guide

Status: Normative

This is the sole normative implementation how-to for Wikiler. It describes the
shipped engine and the decisions locked in `docs/adr/`. It is derived from
audited material and checked against the engine and ADR-0002 and ADR-0003.
The [getting started walkthrough](GETTING_STARTED.md) is the task-by-task
companion for a first vault.

## Authority and evidence

The engine checks form; the agent decides meaning. When this guide and a
non-normative document disagree, this guide wins. The ranked table is in
`docs/AUTHORITY.md`.

This guide is corrected, which means two things. Claims about Wikiler are
checked against the shipped engine and the locked decisions. Claims inherited
from source material are clarified where the original was ambiguous. The
[research note](../research/KARPATHY_LLM_WIKI_RESEARCH.md) is the evidence base
for the second category and is non-normative. The third-party
[implementation guide](../research/KARPATHY_WIKI_IMPLEMENTATION_GUIDE.md) is
evidence only, not a specification of Wikiler.

Third-party claims are kept out of normative instructions. Where source
material is referenced, it is attributed, dated, and marked as illustrative
only, not Wikiler behavior:

| Source claim | Attribution | Source URL | Access date | Status |
|---|---|---|---|---|
| The LLM Wiki idea is an abstract idea file with three layers, three operations, and two special files | Andrej Karpathy, LLM Wiki gist | https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f | 2026-11-16 | Illustrative only, not Wikiler behavior |
| Portable skills provide setup, ingest, query, and lint workflows | NicholasSpisak, second-brain | https://github.com/NicholasSpisak/second-brain | 2026-11-16 | Illustrative only, not Wikiler behavior |

Numeric claims about third-party projects are reported by their sources and
were not independently verified. They belong in research, not here.

## Architecture

A vault has three layers:

- `raw/`: human-owned, immutable source material, organised by topic under
  `articles/`, `papers/`, `repos/`, `datasets/`, with downloaded images in
  `raw/assets/`.
- `wiki/`: agent-authored knowledge pages under `sources/`, `entities/`,
  `concepts/`, `synthesis/`, and `queries/`, plus `index.md` and `log.md`.
- `output/`: reports and generated artifacts. No CLI verb writes here.

Engine writes stay under `wiki/` and `output/`. The one exception is `init`,
which writes `<vault>/AGENTS.md` and installs four skills under
`<vault>/.agents/skills/`.

Vault resolution order is `--vault`, then `WIKI_VAULT`, then the current
directory. Only `init` creates a vault. Every other command refuses to run
outside one.

## Setup

```
wiki init --vault /path/to/my-vault
```

`init` scaffolds the directories, `wiki/index.md`, and `wiki/log.md`, copies
the packaged runtime rules to `AGENTS.md`, and installs the four skills. It
never overwrites an existing `AGENTS.md` or skill. To refresh a file, delete it
and re-run `init` after upgrading the package.

The vault-level `AGENTS.md` is the agent contract. The repository root
`AGENTS.md` covers engine contributors and is not a vault skill or reference
target.

## Page format

Every wiki page carries YAML frontmatter and one Title Case H1:

```yaml
---
type: source | entity | concept | synthesis | query
title: Page Title
sources: [source-filename.md]
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [tag1, tag2]
---
```

- `type` is one of the five values above.
- `title` matches the H1 once a trailing type suffix is ignored.
- `sources` lists the raw source filenames the page derives from.
- `created` is set once and preserved. `updated` changes on edit.
- `tags` are free-form retrieval tags.

The engine guarantees valid YAML, the six required fields, and the date
semantics. The agent authors the Title Case H1. Filenames are kebab-case `.md`;
`index.md` and `log.md` are exempt.

## Links

Author file-path wikilinks only:

```
[[dir/slug|Page Title]]
```

Here `dir` is one of `sources`, `entities`, `concepts`, `synthesis`, or
`queries`. For example:

```
[[concepts/llm-inference-optimization|LLM Inference Optimization]]
```

The display title may keep a type suffix.

Bare stems, title links, and links with a `wiki/` prefix are non-canonical but
accepted for migration. The engine reports them as warnings and repairs them
under `lint --fix`. Agents must author canonical links.

## Operations

### Ingest

```
wiki ingest --vault /path/to/my-vault articles/my-article.md
```

The engine writes a scaffold at `wiki/sources/<slug>.md` with `<!-- TODO:
agent -->` markers and reports the source's images. It performs no network I/O
by default: local `raw/assets/` references are listed, and remote URLs are
reported as not downloaded. `--download-images` opts in to fetching them.

The agent then reads the source, discusses takeaways, fills the scaffold,
decides which entities and concepts warrant pages, and adds canonical
wikilinks. Re-running `ingest` leaves an authored body untouched. `--force`
discards it and is destructive.

### Query

```
wiki query --vault /path/to/my-vault "what is X?"
```

The engine returns ranked candidate pages with short snippets. It never
answers and never saves a page. The agent reads the candidates, synthesises a
cited answer with wikilinks, and offers to save valuable artifacts under
`wiki/synthesis/`.

### Sync

```
wiki sync --vault /path/to/my-vault
```

The engine reconciles `wiki/index.md` and `wiki/log.md` with the pages on
disk, normalises frontmatter quoting, and appends a dated log entry only when
something changed. It never edits a page body. It is idempotent: a no-op run
writes nothing. The agent runs `sync` after authoring or editing pages.

### Lint

```
wiki lint --vault /path/to/my-vault [--json] [--fix]
```

The engine scans frontmatter, filenames, H1 form, link form and resolution,
orphans, and index and log consistency. It reports findings by severity and
repairs only unambiguous issues under `--fix`. The agent reviews the report and
handles meaning: contradictions, stale claims, missing concepts, missing
cross-references, and research gaps. Aim to lint after every 10 ingests,
monthly, and before major queries. The cadence is agent-managed.

## Command reference

```
wiki init
wiki ingest <path> [--download-images] [--json] [--force]
wiki query <question> [--json]
wiki sync
wiki lint [--json] [--fix]
```

The log vocabulary is `setup | ingest | query | synthesis | sync | lint`.

## Rules

1. Raw source files are immutable. The engine may write only downloaded
   assets under `raw/assets/`.
2. Run `wiki sync` after changing pages. Never hand-edit `index.md` or
   `log.md`.
3. The engine enforces structural invariants; the agent enforces semantic
   invariants.
4. Author canonical wikilinks and kebab-case filenames.
5. One source at a time; stay involved and guide emphasis.
6. Treat pages as derived on demand and regenerate them when sources change.

## Dash Rule

Never use em-dashes, en-dashes, or double hyphens as punctuation in vault
documents or code comments. Replace them with a comma, colon, period,
conjugation, or a restructured sentence. CLI flags and frontmatter delimiters
are technical syntax and are exempt.
