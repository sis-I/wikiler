# Wikiler

A local-first knowledge compiler that turns personal research and engineering sources into an interlinked, source-grounded wiki, with an LLM agent for judgment and a deterministic engine for structure.

## What it is

Wikiler (short for "wiki compiler") is a Python CLI engine for maintaining a personal knowledge wiki following the Karpathy LLM Wiki pattern. Sources live under `raw/`; the agent compiles them into interlinked markdown pages under `wiki/`. The engine handles mechanics (scaffolding, validation, index/log sync); the agent handles judgment (summaries, claims, entity/concept decisions, synthesis).

## Install

```
pip install wikiler
```

Or from source:

```
pip install -e .
```

This installs the `wiki` console command.

## Quick Start

```
# Initialize a vault; installs AGENTS.md and four skills under .agents/skills/
wiki init --vault /path/to/my-vault

# Ingest a source
wiki ingest --vault /path/to/my-vault articles/my-article.md

# Fill the TODO sections in wiki/sources/my-article.md, then:
wiki sync --vault /path/to/my-vault

# Query the wiki
wiki query --vault /path/to/my-vault "what is X?"

# Lint the wiki structure
wiki lint --vault /path/to/my-vault
```

## Example Vault

A committed, fully authored vault lives in `examples/vault/`. It is both a readable example and a CI acceptance target: the test suite copies it into a temporary directory before exercising every verb, so the fixture itself is never written to. All of its content is invented, with no real names, private paths, or remote URLs.

## Obsidian

Wikiler reads plain Markdown, so Obsidian can be used as the editor for `raw/` sources.

1. Install Obsidian and open the vault root as an Obsidian vault.
2. Install the Web Clipper plugin. In its settings, set **Folder** to `raw/<topic>/`, for example `raw/articles/`.
3. Set **Default location for new attachments** to `raw/assets` under Settings, Files and links.
4. When a saved note references remote images, run **Download attachments for current file** from the Command palette to save them locally. That command has no default keybinding, so assign a hotkey only if you want one.

Then run `wiki ingest` on the source. Ingest performs no network I/O by default: it lists local assets found under `raw/assets/` and reports remote URLs as not downloaded. Pass `--download-images` to fetch those URLs as a fallback for sources that never went through Obsidian.

## Vault Layout

```
my-vault/
├── AGENTS.md             # runtime rules (installed by init, preserved on re-run)
├── .agents/
│   └── skills/
│       ├── wiki-setup/SKILL.md
│       ├── wiki-ingest/SKILL.md
│       ├── wiki-query/SKILL.md
│       └── wiki-lint/SKILL.md
├── raw/
│   ├── articles/
│   ├── papers/
│   ├── repos/
│   ├── datasets/
│   └── assets/          # downloaded images (opt-in)
├── wiki/
│   ├── sources/
│   ├── entities/
│   ├── concepts/
│   ├── synthesis/
│   ├── queries/
│   ├── index.md
│   └── log.md
└── output/
```

## Commands

| Command | Purpose |
|---|---|
| `wiki init` | Scaffold vault structure |
| `wiki ingest <path>` | Scaffold a source page from `raw/<path>` |
| `wiki query <question>` | Retrieve candidate pages |
| `wiki sync` | Reconcile index, frontmatter, log |
| `wiki lint [--fix]` | Structural health check |

## Portable skills

`wiki init` installs `AGENTS.md` and four skills into `<vault>/.agents/skills/`:
`wiki-setup`, `wiki-ingest`, `wiki-query`, and `wiki-lint`. A harness opened on
the vault discovers them from the `Use when` clause in each description. `sync`
stays CLI-only. Re-running `init` preserves edited `AGENTS.md` and skill files;
delete a file and re-run `init` to refresh it from the installed package.

## Documentation

- `docs/guides/GETTING_STARTED.md`: detailed walkthrough from a fresh install to a linted vault.
- `docs/guides/LLM_WIKI_IMPLEMENTATION_GUIDE.md`: the normative implementation how-to.
- `docs/AUTHORITY.md`: which documents are normative and where each audience starts.
- `docs/README.md`: index of the docs tree.

## License

MIT

## Python

`>=3.10`, no required runtime dependencies.
