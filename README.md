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
# Initialize a vault
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

## Vault Layout

```
my-vault/
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

## License

MIT

## Python

`>=3.10`, no required runtime dependencies.
