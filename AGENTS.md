# Wikiler: Engine Contributor Rules

## Identity

- Repository and distribution name: `wikiler`
- Python import package: `wikiler`
- Console entry point: `wiki`
- Portable skill prefix: `wiki` (skills: `wiki-setup`, `wiki-ingest`, `wiki-query`, `wiki-lint`)
- License: MIT
- Python: `>=3.10`, no required runtime dependencies
- Packaging: root `src/` layout, PyPI + GitHub Releases
- Version: `0.1.0` (SemVer `0.x`, interfaces may change)

`Wikiler` is short for `wiki compiler`. It is not an acronym.

## Engine and Agent Roles

The engine is the mechanical half; the agent is the judgment half. Neither side does the other's job.

- **Agent (LLM):** judgment. Read and discuss sources, write summaries, claims, and definitions, choose which entities and concepts matter, synthesize cited answers, and judge contradictions, staleness, coverage gaps, and emphasis.
- **Engine (`wikiler`):** mechanics. Scaffold pages, validate frontmatter, filenames, H1 form, and links, resolve retrieval candidates, maintain `wiki/index.md` and `wiki/log.md`, and apply safe mechanical repairs.
- **Boundary:** the engine may reject or repair *form*; it must never decide *meaning*. Anything it cannot determine deterministically is emitted as a suggestion or `<!-- TODO -->` marker for the agent to resolve.

If a rule below can be checked mechanically, `wiki lint` owns it. If it requires reading for sense, the agent owns it.

## Repository Layout

```
wikiler/
├── pyproject.toml            # package metadata, [project.scripts] wiki = "wikiler.cli:main"
├── src/
│   └── wikiler/
│       ├── __init__.py       # __version__, public API exports
│       ├── cli.py            # verb dispatch (init, ingest, query, lint, sync)
│       ├── vault.py          # path resolution, vault markers, boundary guards
│       ├── page.py           # frontmatter YAML, H1 Title Case, wikilink grammar
│       ├── lint.py           # mechanical scan by severity, unambiguous --fix only
│       ├── log.py            # append-only dated log entries
│       ├── output.py         # error reporting, JSON vs human streams
│       ├── images.py         # local asset listing + opt-in remote download
│       ├── .agents/
│       │   └── skills/
│       │       └── wiki-*/SKILL.md  # packaged skills installed by init
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── init.py
│       │   ├── ingest.py
│       │   ├── query.py
│       │   ├── lint.py
│       │   └── sync.py
│       └── runtime_rules.md  # packaged AGENTS.md template copied into new vaults
├── tests/                    # engine test suite (sdist only, not wheel)
├── .agents/
│   └── skills/
│       ├── wiki-setup/SKILL.md
│       ├── wiki-ingest/SKILL.md
│       ├── wiki-query/SKILL.md
│       └── wiki-lint/SKILL.md
├── examples/
│   └── vault/                # sanitized fixture vault for CI acceptance
├── docs/
│   ├── adr/                  # architecture decision records
│   ├── agents/               # agent contracts (issue tracker, triage labels, domain)
│   ├── guides/               # corrected implementation guide
│   └── research/             # Karpathy evidence base
├── LICENSE                   # MIT
├── AGENTS.md                 # this file: rules for engine contributors
├── CHANGELOG.md
└── README.md
```

## Vault Boundary

The `wikiler` package installs into the user's Python environment. The engine resolves the target vault from `--vault`, `WIKI_VAULT`, or cwd.

- Only `init` may scaffold a vault. Every other command refuses to run outside an initialized vault.
- The engine writes only under `wiki/` and `output/` of the target vault, except that `init` writes `<vault>/AGENTS.md` and installs the four skills under `<vault>/.agents/skills/`. `raw/` is human-owned and immutable; the engine may write only downloaded assets to `raw/assets/`.
- The user's personal main vault stays outside the public project. Its final location is a human decision; the public project never moves, renames, or touches it.
- Migration of the personal vault is governed by [the private migration ticket](https://github.com/sis-I/pi-wiki-vault/issues/33), not by this document.

## Vault Rules (for agents operating a vault)

The packaged `src/wikiler/runtime_rules.md` is the single source of truth for vault operator rules. It is copied into every new vault as `AGENTS.md` by `wiki init`. Engine contributors should not edit vault rules here; edit `runtime_rules.md` instead.

The root `AGENTS.md` (this file) governs engine development only.

## Special Files

- `wiki/index.md`: Content catalog, one line per page, categorized. Reconcile with `wiki sync`; do not hand-edit.
- `wiki/log.md`: Append-only timeline, entries like `## [YYYY-MM-DD] op | title`. Reconcile with `wiki sync`; do not hand-edit.
- Log operation names: `setup | ingest | query | synthesis | sync | lint`.

## Commands

```
wiki init
wiki ingest <path> [--download-images] [--json] [--force]
wiki query <question> [--json]
wiki sync
wiki lint [--json] [--fix]
```

- `init` scaffolds the vault (subdirectories, index.md, log.md), copies the runtime rules to `AGENTS.md`, and installs the four portable skills under `.agents/skills/`. Existing `AGENTS.md` and skills are preserved; remove a file and re-run `init` to refresh it from the package.
- `ingest` scaffolds a source page from a raw source. Local-first: no network I/O by default.
- `query` retrieves candidate pages; never synthesizes an answer.
- `lint` scans for structural faults; `--fix` repairs unambiguous issues only.
- `sync` reconciles index, frontmatter, and log; never edits a page body.

## Rules for Engine Contributors

1. `raw/` source files are immutable. The engine may write only downloaded assets to `raw/assets/`; it must never rewrite, move, or delete anything else under `raw/`.
2. When pages are added or changed, run `wiki sync` to reconcile `wiki/index.md` and `wiki/log.md`. Never hand-edit either file.
3. The engine guarantees valid YAML, the required frontmatter fields (`type`, `title`, `sources`, `created`, `updated`, `tags`), and `created`/`updated` semantics. `created` is set once and preserved; `updated` changes on edit.
4. Use the link grammar `[[dir/slug|Page Title]]`, where `dir` is one of `sources | entities | concepts | synthesis | queries`.
5. Use kebab-case filenames.
6. Images are local-first and opt-in. `--download-images` opts in to fetching remote URLs.
7. `wiki lint` is the mechanical half of the health check. Cadence is agent-managed, not engine-enforced.
8. The engine enforces structural invariants; the agent enforces semantic invariants.
9. One source at a time; stay involved, read summaries, guide emphasis.
10. Treat wiki pages as derived-on-demand: regenerate when sources change, do not let them rot.

## Development

Run from the repository root:

```
pip install -e .
wiki init --vault /path/to/vault
wiki ingest --vault /path/to/vault articles/foo.md
wiki lint --vault /path/to/vault
wiki sync --vault /path/to/vault
```

Run tests:

```
cd /path/to/repo
pip install pytest
python -m pytest tests/
```

The test suite runs against temporary vault directories, never the user's real vault.

## Documentation Authority

- `docs/adr/`: Architecture decision records (numbered, immutable once accepted).
- `docs/agents/`: Agent contracts (issue-tracker.md, triage-labels.md, domain.md).
- `docs/guides/`: Corrected implementation guide.
- `docs/research/`: Evidence base (Karpathy research note).

## Agent Skills

- `docs/agents/issue-tracker.md`: GitHub Issues for `sis-I/wikiler`.
- `docs/agents/triage-labels.md`: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.
- `docs/agents/domain.md`: Single-context domain structure.
- Repo-root `.agents/skills/wiki-*/SKILL.md` and packaged `src/wikiler/.agents/skills/wiki-*/SKILL.md` are byte-identical. `init` installs the packaged copies into new vaults.

## Dash Rule

Never use em-dashes, en-dashes, or double hyphens as punctuation in repo documents or code comments. Replace with a comma, colon, period, conjugation, or by restructuring the sentence. CLI flags such as `--vault` and `--json` are technical syntax and are exempt.
