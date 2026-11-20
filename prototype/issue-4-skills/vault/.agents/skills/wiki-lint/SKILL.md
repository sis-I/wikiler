---
name: wiki-lint
description: Mechanical structural scan of a Wikiler vault covering frontmatter, filenames, H1s, links, orphans, and index/log consistency. Use after ingests or before major queries.
---

Run `wiki lint [--json] [--fix]`. `--fix` applies only unambiguous mechanical repairs; `--json` prints findings as JSON.

Exit codes: `0` no errors, `1` lint errors present, `2` invalid usage.

Review the findings and resolve what the engine cannot decide: contradictions, stale claims, missing pages, cross-references. Re-run until structural errors are zero. The engine fixes form only, never meaning.

Vault rules live in `<vault>/AGENTS.md`.
