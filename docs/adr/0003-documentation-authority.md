# ADR-0003: Lock the documentation authority and correction policy

- Status: Accepted
- Date: 2026-11-22
- Deciders: sis-I

## Context

Issue #2 asked which documents become normative for Wikiler users, vault
agents, contributors, and maintainers; how the corrected implementation guide
differs from the original research interpretation; what caveats third-party
claims must carry; and what public documentation structure replaces the old
`.dev` guidance. The answer feeds the public engine release map in issue #5 and
depends on the repository topology and vault boundary decision in
pi-wiki-vault#27.

The research interpretation is faithful evidence about the source material, not
about Wikiler. The guide mixed Karpathy's proposal, an author's recommended
implementation, and this repository's own conventions. Without a recorded
authority rank, a later edit could silently promote third-party evidence into a
specification or demote a locked decision to a suggestion. `.dev/` was temporary
local guidance and had no place in the public tree.

## Decision

Ratify the corrected documentation set as the normative baseline for the first
release. Promise no breaking changes to the normative doc set through the 0.x
line. Any change requires an ADR and a version bump. The engine checks form
only; the agent decides meaning.

A normative document is the canonical source for its topic. It wins conflicts
with non-normative documents, changes only through an explicit recorded
decision, and is linked to rather than restated by other documents.

The global authority rank is:

1. ADRs, as decision records, immutable once accepted.
2. Scope-specific canonical specs: `src/wikiler/runtime_rules.md` and its vault
   copy `<vault>/AGENTS.md` for the vault contract and agent behavior; root
   `AGENTS.md` for engine contributor rules only.
3. Normative guides under `docs/guides/`.
4. `README.md` and CLI help.
5. `CHANGELOG.md` and release notes.
6. `docs/research/` and third-party material, non-normative evidence.

A per-audience start here index lives in `docs/AUTHORITY.md`, routing users,
vault agents, contributors, and maintainers according to the rank and the two
scope carve-outs above. Root `AGENTS.md` is a contributor document and is not a
skill reference target. The redundant local precedence rule in the compiling
guide is removed.

"Corrected" means both factual correction against the shipped engine and the
decisions locked in issues #26 and #27, and editorial clarification. Every
third-party claim, wherever it appears, carries attribution, a source URL, an
access date, and an explicit "illustrative only, not Wikiler behavior"
statement. Numeric claims additionally say they are reported by the source and
not independently verified. Claims that fail these rules do not enter normative
documents.

The permanent public structure retires `.dev/`: `docs/guides/` holds normative
how-to only, `docs/research/` holds evidence and third-party material,
`docs/plans/` holds internal implementation plans, `docs/adr/` holds immutable
decisions, `docs/agents/` holds contracts, and `docs/README.md` is the index.
Root `README.md` stays a short entry point. Temporary local notes never become
maintained public guidance.

A small form-only test mirrors the parity tests in issues #1 and #3. It asserts
that every public doc carries a status marker and that `AGENTS.md` points to
`docs/AUTHORITY.md`. It parses no prose meaning.

## Consequences

- A conflict is settled by walking the rank from top to bottom. An ADR beats a
  guide, a guide beats the changelog, and no research note overrides any of
  them.
- The vault contract and the contributor contract stay separate. A vault agent
  reads `<vault>/AGENTS.md`, never the repository root `AGENTS.md`.
- A change to a normative document needs an ADR and a version bump, not just a
  prose edit. The form-only test catches a missing status marker or a dropped
  pointer, not a change in meaning.
- Third-party material can be kept as evidence without becoming a promise
  about Wikiler. Its caveats travel with it.
- The compiling guide and the old plan file are deleted after their needed
  content is ported. Git history preserves them.

## Alternatives considered

- **Keep `.dev/` as the public guidance home.** Rejected: it was temporary
  local material and did not rank against the locked decision records.
- **Treat the research interpretation as normative.** Rejected: it is evidence
  about source material, not a description of the shipped engine.
- **Let each document decide its own precedence.** Rejected: local precedence
  rules drifted and produced conflicting claims, which is why the redundant
  rule in the compiling guide is removed.
- **Require the engine to parse prose for caveats.** Rejected: the engine
  checks form only. Caveat judgment belongs to the agent.
