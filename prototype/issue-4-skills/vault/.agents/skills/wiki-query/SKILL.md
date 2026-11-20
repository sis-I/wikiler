---
name: wiki-query
description: Retrieve candidate wiki pages for a question with short snippets. Use when the user asks a question about the vault. Returns candidates only, never an answer.
---

Run `wiki query <question> [--json]`. `--json` prints `{"question": ..., "matches": [...]}`.

Exit codes: `0` success (including no matches), `1` operational error, `2` invalid usage.

Read the candidate pages, then synthesize the answer yourself with file-path wikilink citations. If the answer is worth keeping, write `wiki/synthesis/<slug>.md` with your own tools and run `wiki sync`. The engine never fabricates an answer or saves a page for you.

Vault rules live in `<vault>/AGENTS.md`.
