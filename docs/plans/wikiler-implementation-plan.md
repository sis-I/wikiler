# Wikiler Implementation Plan

Status: Plan, below normative guides

GitHub Issues are the decision records for this project. ADRs capture the hard
to reverse trade-offs. This plan is an internal work queue, not a source of
authority: it ranks below the normative guides in `docs/guides/` and must not
be used to settle a question that an issue or ADR already answers. For the
authority rank, see `docs/AUTHORITY.md`.

## Provenance

Derived from the newer compiling guide, which marked its final verification
tickets closed, and rewritten in current repository terms: distribution and
import package `wikiler`, console command `wiki`, and code under
`src/wikiler/`. The older helper refactor plan is retired; git history keeps
it. Where this plan disagrees with an issue, the issue wins. Where it
disagrees with a normative guide, the guide wins.

## Completed foundation

The mechanical helper work is closed. The original plan references T0 through
T9, all landed, and map to earlier repository issues:

| Plan ref | Area | State |
|---|---|---|
| T0 | Documentation contract | Closed |
| T1 | Vault resolution guard | Closed |
| T2 | Shared frontmatter and index helpers | Closed |
| T3 | `sync` verb | Closed |
| T4 | Scaffold-only `ingest` | Closed |
| T5 | Retrieval-only `query` | Closed |
| T6 | Mechanical lint checks and `--json` | Closed |
| T4b | `ingest --json` and `--force` | Closed |
| T7 | Scoped `--fix` | Closed |
| T8 | Canonical wikilink migration | Closed |
| T9 | End-to-end scaffold workflow | Closed |

The locked shape that came out of that work:

- Five verbs: `init`, `ingest`, `query`, `lint`, `sync`.
- `ingest` writes a scaffold with `<!-- TODO: agent -->` markers and no prose.
- `query` ranks candidates and never answers or saves.
- `lint` checks form, reports by severity, and repairs only unambiguous cases
  under `--fix`.
- `sync` is the single mechanical reconciler for index, frontmatter, and log.
- Non-init commands refuse to run outside an initialized vault.
- The engine never creates a vault implicitly and never decides meaning.

The implementation detail lives in `src/wikiler/`: `cli.py`, `vault.py`,
`page.py`, `lint.py`, `log.py`, `output.py`, `images.py`, `runtime_rules.md`,
and `commands/`.

## Remaining work from the release map

Issue #5 closed the decision map and handed implementation to four tickets.
This section tracks those tickets only. No new decision is made here.

| Ticket | Scope | State |
|---|---|---|
| #6 | Portable skill contract: four skills with `name` and `description` frontmatter and `Use when` triggers, byte parity between repo-root and packaged copies, and refresh on delete and re-init | Landed |
| #7 | Documentation authority structure and correction policy from issue #2 | Current ticket |
| #8 | Normative vault contract: ADR-0002, twelve vault terms, contract updates, regenerated example rules, parity tests | Landed |
| #9 | Sanitized example vault acceptance contract: fixture, pytest acceptance module, init topic dirs, CI, README pointer and Obsidian section | Landed |

### Ticket #7 checklist

- [x] ADR-0003 and the ADR index entry
- [x] `docs/AUTHORITY.md` rank table and audience map
- [x] `docs/README.md` index
- [x] Root `AGENTS.md` points to the authority index and matches the locked rank
- [x] Sole normative implementation guide, linked to the research note
- [x] Detailed getting started walkthrough, linked from the root README
- [x] Karpathy guide moved to research with a non-normative banner
- [x] Historical research note banner, contents otherwise unchanged
- [x] Compiling guide and old plan retired after porting content
- [x] New plan rewritten in current repo terms
- [x] Five documentation terms added to the root glossary
- [x] Five corrections applied to the moved guide
- [x] Form-only anti-drift test
- [x] Full test suite green

## Out of scope after this plan

These were considered in issue #5 and are explicitly not scheduled:

- Pi extensions, OpenCode plugins, and an MCP server.
- `qmd`, hybrid BM25 and vector retrieval, or a database sidecar.
- Redesigning the five CLI verbs or adding a fifth skill.
- Publishing the maintainer's personal or private main vault.
- A hosted service, dashboard, or multi-user synchronization.

## Definition of done

- Every path in the issue #2 document status table exists with its stated
  role.
- The five corrections are applied and private repository residue is gone from
  the public guides, plan, authority index, docs index, and root rules.
- The anti-drift test asserts form only and never parses prose meaning.
- The full test suite is green.
- No engine behavior, version, CLI, or vault schema changed in this work.
