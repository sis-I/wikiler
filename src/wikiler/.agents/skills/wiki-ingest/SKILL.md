---
name: wiki-ingest
description: Scaffold a source page from a raw source file under raw/. Derives title and tags, writes wiki/sources/<slug>.md with frontmatter and TODO markers for the agent to fill. Local-first: no network I/O by default.
---

# wiki-ingest: Portable Skill

## Purpose

Read a raw source under `raw/`, derive a title and tags, and scaffold exactly
one page under `wiki/sources/<slug>.md` with valid frontmatter and explicit
`<!-- TODO: agent -->` markers for the parts that require judgment.

## Contract

- **Input**: source path within `raw/` (e.g. `articles/my-article.md`).
- **Output**: `wiki/sources/<slug>.md` scaffold; updated `wiki/index.md`;
  appended `wiki/log.md` entry (idempotent).
- **Exit codes**: `0` success; `1` operational error (source not found,
  not a vault); `2` invalid usage.
- **JSON**: `--json` prints the scaffold manifest as one JSON object on
  stdout; errors go to stderr.
- **Idempotent**: re-running leaves the agent-authored body untouched and
  does not duplicate the log entry.

## Flags

- `--download-images`: fetch remote image URLs into `raw/assets/` (opt-in;
  default lists local assets only, no network I/O).
- `--force`: destructive rewrite of an existing page's scaffold, discarding
  the agent-authored body and restoring TODO markers. Preserves `created`,
  refreshes `updated`.
- `--json`: emit the manifest as JSON, nothing else on stdout.

## Preconditions

- Target must be an initialized vault.
- Source file must exist under `raw/`.

## Steps

1. Resolve target vault; refuse if not a vault.
2. Read the raw source; derive title (frontmatter → H1 → filename) and tags.
3. Discover images (local-first; no network by default).
4. If new or `--force`: render scaffold with TODO-marked sections (Key
   claims, Structured summary, Entities, Concepts, Images when present).
5. If existing and not `--force`: normalise frontmatter only; never rewrite
   the agent-authored body.
6. Run `sync` to update `index.md` and `log.md`.
7. Print manifest (human or JSON).

## Notes

- The engine never writes a sentence about the source's content.
- The agent fills TODO sections after the scaffold is written.
- `raw/` source files are immutable; only `raw/assets/` may receive
  downloaded images.
