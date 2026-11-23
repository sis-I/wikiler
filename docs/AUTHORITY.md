# Documentation Authority

Status: Normative, living

This file is the global authority index. It states which kind of document wins
a conflict and where each audience starts. The decision behind it is
[ADR-0003](adr/0003-documentation-authority.md), which is immutable once
accepted. This file is living: it routes readers, it does not re-decide the
rank. For a walk through the tree, see [docs/README.md](README.md).

## Global rank

A document at a lower rank never overrides one at a higher rank. A normative
document is the canonical source for its topic: it wins conflicts with
non-normative documents, changes only through an explicit recorded decision,
and is linked to rather than restated by other documents.

| Rank | Document set | Authority |
|---|---|---|
| 1 | `docs/adr/` | Decision records, immutable once accepted |
| 2 | `src/wikiler/runtime_rules.md` and its vault copy `<vault>/AGENTS.md` | Scope-specific canonical spec for the vault contract and agent behavior |
| 2 | Root `AGENTS.md` | Scope-specific canonical spec for engine contributor rules only |
| 3 | `docs/guides/` | Normative guides and how-tos |
| 4 | `README.md` and CLI help | Public entry point and command reference |
| 5 | `CHANGELOG.md` and release notes | Record of what shipped |
| 6 | `docs/research/` and all third-party material | Non-normative evidence |

Two scope carve-outs matter when reading rank 2. The packaged
`src/wikiler/runtime_rules.md`, copied into a vault as `AGENTS.md`, owns the
vault contract and the behavior of agents operating a vault. The root
`AGENTS.md` owns engine contributor rules only and is not a skill reference
target. Neither document may be used outside its scope.

`docs/plans/` is internal work planning and ranks below normative guides.
`docs/agents/` holds repository agent contracts. `.dev/` is permanently
retired and is not a source of public guidance.

## Start here by audience

| Audience | Start here | Then read |
|---|---|---|
| Wikiler user | Root `README.md` quick start | `docs/guides/GETTING_STARTED.md` for the full walkthrough, then `docs/guides/LLM_WIKI_IMPLEMENTATION_GUIDE.md` and CLI help |
| Vault agent | `<vault>/AGENTS.md`, installed from `src/wikiler/runtime_rules.md`, and the four `wiki` skills under `<vault>/.agents/skills/` | `docs/adr/0002-normative-vault-contract.md` for the locked vault contract |
| Engine contributor | Root `AGENTS.md` | `docs/adr/`, then `docs/plans/wikiler-implementation-plan.md`, then `docs/README.md` |
| Maintainer | `docs/adr/` | This file, `docs/README.md`, `CHANGELOG.md`, and release notes |

A vault agent never uses the repository root `AGENTS.md` as its operating
contract. A contributor never edits vault rules in that file; the source of
truth is `src/wikiler/runtime_rules.md`.

## Correction policy

"Corrected" means both factual correction against the shipped engine and the
decisions locked in issues #26 and #27, and editorial clarification. The
research interpretation is faithful evidence about the source material, not
about Wikiler.

Every third-party claim, wherever it appears, carries attribution, a source
URL, an access date, and an explicit "illustrative only, not Wikiler behavior"
statement. Numeric claims additionally say they are reported by the source and
not independently verified. Claims that fail these rules do not enter normative
documents. `docs/research/` keeps such material with the caveats attached, and
`docs/guides/LLM_WIKI_IMPLEMENTATION_GUIDE.md` is the sole normative how-to.

The terms normative, corrected guide, third-party claim, caveat, and status
marker are defined in the root `GLOSSARY.md`. The status marker itself is a
form-only convention: every public document under `docs/` carries a
`Status: <value>` line that a mechanical check can find without reading prose.
