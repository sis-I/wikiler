---
name: wiki-ingest
description: Scaffold a source page from a raw file under raw/ with frontmatter and TODO markers. Use when a source is added to raw/ and the user asks to process or ingest it.
---

Run `wiki ingest <path> [--download-images] [--json] [--force]`. Images are local-first; `--download-images` is the only opt-in to network access. `--force` discards an authored body and restores TODO markers.

Exit codes: `0` success, `1` operational error (not a vault, source missing), `2` invalid usage. `--json` prints the scaffold manifest as one object on stdout.

After the scaffold: read the source in full, fill every `<!-- TODO: agent -->` section, identify related entities and concepts, add `[[dir/slug|Page Title]]` links, then run `wiki sync`.

Vault rules live in `<vault>/AGENTS.md`.
