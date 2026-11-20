---
name: wiki-query
description: Retrieve candidate wiki pages for a question. Reads wiki/index.md, matches entries by keyword, reads each matched page, and returns a ranked list with snippets. Retrieval only: never synthesizes an answer or writes to the wiki.
---

# wiki-query: Portable Skill

## Purpose

Read `wiki/index.md`, match entries against the question's keywords, read
each matched page, and attach a short snippet. The ranked candidate list is
the output: the agent reads those pages and writes the cited synthesis
itself.

## Contract

- **Input**: question string.
- **Output**: ranked list of candidate pages with path and snippet (human or
  JSON).
- **Exit codes**: `0` success (including no matches); `1` operational error
  (not a vault, no index); `2` invalid usage.
- **JSON**: `--json` prints `{"question": ..., "matches": [...]}` on stdout.

## Flags

- `--json`: emit the question and ranked matches as JSON.

## Preconditions

- Target must be an initialized vault.
- `wiki/index.md` must exist (run `init` and ingest sources first).

## Steps

1. Resolve target vault; refuse if not a vault.
2. Read `wiki/index.md`; match entries by keyword overlap with the question.
3. Rank by distinct keyword count (ties keep index order).
4. Read each matched page; extract the first non-heading paragraph as a
   snippet (truncated at 200 characters).
5. Print the ranked list (human-readable or JSON).

## Notes

- Query is retrieval only; it never synthesizes an answer.
- Query never writes to `raw/` or any wiki page.
- The agent writes `wiki/synthesis/<slug>.md` with its own tools, then runs
  `wiki sync`.
