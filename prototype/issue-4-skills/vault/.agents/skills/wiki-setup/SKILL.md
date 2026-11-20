---
name: wiki-setup
description: Initialize a new Wikiler vault with directories, index, log, AGENTS.md, and the four portable skills. Use when creating or initializing a vault, or when the user asks to set up a wiki.
---

Run `wiki init --vault <path>`. Vault resolution is `--vault` > `WIKI_VAULT` > cwd. Only `init` may create a vault; every other command refuses outside one.

Exit codes: `0` success, `1` operational error, `2` invalid usage. No `--json` flag. Re-running is idempotent. `init` installs `AGENTS.md` and the four skills under `.agents/skills/`.

Vault rules live in `<vault>/AGENTS.md`. Read them before any other wiki operation.
