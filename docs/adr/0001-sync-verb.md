# ADR-0001: Add `sync` as a Top-Level Verb

- Status: Accepted
- Date: 2026-11-10
- Deciders: sis-I

## Context

`AGENTS.md` Rule 2 requires `wiki/index.md` and `wiki/log.md` to stay current whenever pages are added or changed, but no command did only that. The mechanics were buried in `ingest` and `lint --fix`, so a catalog update also scaffolded pages or rewrote links. `query --save` similarly bundled answer synthesis, page writing, and index/log updates into one flag.

An earlier design rule said the CLI should add no new top-level verbs. That rule produced flags carrying whole operations (`query --save`) and split one mechanic (index/log reconciliation) across two unrelated commands. It protected a surface count, not a boundary.

## Decision

Add `sync` as the fifth top-level verb. The verb set is `init | ingest | query | lint | sync`.

`wiki-engine sync` reconciles the index, normalises frontmatter quoting, and appends a dated log entry only when something changed. It never edits a page body and never invents content.

Consequences of the same decision:

- `query --save` is deleted. The agent writes `wiki/synthesis/<slug>.md` with its own tools and runs `sync`.
- Routine index reconciliation moves to `sync`. Lint fix mode keeps unambiguous link repairs, removes dangling index entries under its fix flag, and logs only when it changes something.
- The "no new top-level verbs" rule is lifted. A verb is justified when it names one mechanic the agent must be able to invoke on its own.
- Rule 2 becomes enforceable by a single command instead of agent discipline.

## Consequences

- Five verbs, each mapping to one job: `init` scaffolds, `ingest` scaffolds a source page, `query` retrieves candidates, `lint` validates structure, `sync` reconciles index/frontmatter/log.
- `sync` must be idempotent and refuse to run outside a vault. A no-op run writes nothing and logs nothing.
- The agent's write path is explicit: author the page, then `sync`. There is no engine-generated answer or page to trust.
- Adding a verb now requires an ADR and a named mechanic; the default is still a flag on an existing verb.

## Alternatives considered

- **Keep `query --save`.** Rejected: it made retrieval produce prose, which is the agent's job, and it hid index/log work behind an unrelated command.
- **Keep routine index additions and unconditional logging inside `ingest` and lint fix mode.** Rejected: editing a page or saving a synthesis then required running a command that did unrelated work.
- **Add a flag such as `ingest --sync` or `lint --index`.** Rejected: the mechanic is not specific to either command, and flags that carry whole operations are how the original rule went wrong.
