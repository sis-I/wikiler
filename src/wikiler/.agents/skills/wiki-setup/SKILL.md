---
name: wiki-setup
description: Initialize a Wikiler vault: scaffold directory structure, write wiki/index.md and wiki/log.md, copy the runtime rules template into AGENTS.md. Model-invoked: the agent fires it when creating a new vault.
---

# wiki-setup: Portable Skill

## Purpose

Scaffold a new Wikiler vault directory structure and create the initial
`wiki/index.md` and `wiki/log.md`. Copies the packaged `runtime_rules.md`
into the vault as `AGENTS.md`.

## Contract

- **Input**: target vault path (from `--vault`, `WIKI_VAULT`, or cwd).
- **Output**: vault subdirectories, `wiki/index.md`, `wiki/log.md`,
  `AGENTS.md` (runtime rules copy).
- **Exit codes**: `0` success; `1` operational error; `2` invalid usage.
- **JSON**: not applicable (no `--json` flag).
- **Idempotent**: re-running does not duplicate index/log content or append
  another setup entry.

## Preconditions

- Target directory must not already be a vault (unless re-running init).
- Only `setup` may scaffold a vault; every other command refuses outside an
  initialized vault.

## Steps

1. Resolve target vault (`--vault` > `WIKI_VAULT` > cwd).
2. Create `raw/`, `raw/assets/`, `wiki/sources/`, `wiki/entities/`,
   `wiki/concepts/`, `wiki/synthesis/`, `wiki/queries/`, `output/`.
3. Write `wiki/index.md` with section headers (Sources, Entities, Concepts,
   Synthesis, Queries).
4. Write `wiki/log.md` with header and append `## [YYYY-MM-DD] setup |
   Vault initialized`.
5. Copy `runtime_rules.md` to vault root as `AGENTS.md`.
6. Return exit code 0.

## Notes

- `raw/` is created empty; the engine never populates it.
- The user's personal source files live under `raw/` and are human-owned.
- The packaged `runtime_rules.md` is the source of truth for the vault's
  `AGENTS.md`; CI checks for drift between the two.
