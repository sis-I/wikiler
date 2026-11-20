# Changelog

## [0.1.0] 2026-11-20

### Added
- Initial public release of `wikiler` (formerly `wiki-engine`)
- Five CLI verbs: `init`, `ingest`, `query`, `lint`, `sync`
- `src/wikiler/` package layout with conventional root `src/`
- Packaged `runtime_rules.md` template copied into new vaults as `AGENTS.md`
- Four portable skills: `wiki-setup`, `wiki-ingest`, `wiki-query`, `wiki-lint`
- Sanitized example vault at `examples/vault/` for CI acceptance checks
- MIT license, Python >= 3.10, no required runtime dependencies
- PyPI and GitHub Release distribution

### Changed
- Console command renamed from `wiki-engine` to `wiki`
- Python import package renamed from `wiki_engine` to `wikiler`
- Distribution renamed from `wiki-engine` to `wikiler`
- Engine moved from `engine/wiki_engine/` to `src/wikiler/`
- Tests moved from `engine/tests/` to `tests/`
- Vault rules moved from root `AGENTS.md` to `src/wikiler/runtime_rules.md`
- Root `AGENTS.md` now covers engine contributor rules only

### Removed
- None

### Deprecated
- None

### Fixed
- None

### Security
- None
