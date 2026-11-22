# ADR-0002: Lock the normative vault contract

- Status: Accepted
- Date: 2026-11-22
- Deciders: sis-I

## Context

Issue #3 asked which directory layout, frontmatter fields, filename rules,
Title Case H1 rules, wikilink grammar, source immutability rules, index and
log semantics, raw asset rules, and engine and agent ownership boundaries
form the normative vault contract for the first release. The answer feeds the
public engine release map in issue #5 and depends on the repository topology
and vault boundary decision in pi-wiki-vault#27.

The engine and the agent split work along a form and meaning boundary. That
split was implemented and documented, but it was not explicitly frozen.
Without a decision, a later release could tighten a warning into an error,
move the canonical artifact, or change the vault contract in a patch release.

## Decision

Ratify the current implemented and documented behavior as the normative
baseline for the first release. Do not tighten warning-level checks into
errors. Promise no breaking changes to the vault contract through the 0.x
line; any change requires an ADR and a version bump.

`src/wikiler/runtime_rules.md` is the one living normative spec. The example
vault `AGENTS.md`, the packaged skills, and the root `AGENTS.md` are derived
from it or checked against it. There is no JSON Schema for 0.1.0. The engine
checks form; the agent decides meaning.

The locked areas are: directory layout; six frontmatter fields and five
`type` values; kebab-case page filenames with `index.md` and `log.md` exempt;
the exact Title Case H1 algorithm and suffix regex; the two-tier wikilink
grammar; source immutability; index and log semantics; local-first opt-in
raw assets; engine and agent ownership boundaries; and the scope of the
promise. `src/wikiler/runtime_rules.md` states each area in full.

## Consequences

- A warning stays a warning. `lint --fix` remains the only automatic repair
  path for non-canonical link forms.
- Contributors edit the vault contract in one place and regenerate the
  example vault copy. Anti-drift tests assert machine-checkable constants and
  guard prose copies by string assertions, without parsing prose.
- The no-breaking-change promise covers the vault contract only. CLI JSON
  output shape and exit codes are explicitly out of scope and remain an open
  decision for issue #5.
- A contract change needs an ADR and a version bump, not just a docs edit.

## Alternatives considered

- **Tighten warning-level checks into errors.** Rejected: it breaks existing
  migration paths and changes the engine and agent boundary in a patch.
- **Introduce a JSON Schema for 0.1.0.** Rejected: two sources of truth would
  drift, and the engine has no runtime dependency for schema validation.
- **Treat bare stems and `wiki/` prefixed links as invalid.** Rejected: the
  engine tolerates them as migration affordances, so prose and code must
  agree on the wording "non-canonical, accepted for migration".
- **Promise stability for CLI JSON output and exit codes too.** Rejected:
  that surface is not settled and is routed to issue #5.
