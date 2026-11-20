# Implementation Plan: Make `wiki-engine` a Mechanical Helper for the LLM Agent

Status: in progress. Tickets #10, #13 to #19 landed; #20 to #22 open (2026-11-13)
Repo: `/Users/sis/Projects/pi-wiki-vault`
Target code: `engine/wiki_engine/`
Target docs: `AGENTS.md`

Provenance: written 2026-11-10, sharpened by a grill round the same day (§0.1), then split into
tickets on the GitHub issue tracker. The T-numbers used below map to issues:

| Plan ref | Issue | State |
|---|---|---|
| T0 docs contract | #10 | closed |
| T1 vault guard | #13 | closed |
| T2 shared helpers | #14 | closed |
| T3 `sync` | #15 | closed |
| T4 `ingest` scaffold-only | #16 | closed |
| T5 `query` retrieval-only | #17 | closed |
| T6 lint checks | #18 | closed |
| T4b `ingest --json/--force` | #19 | closed |
| T7 scoped `--fix` | #20 | open |
| T8 wikilink migration | #21 | open |
| T9 end-to-end | #22 | open |

This document is the design record, not the work queue. Where it disagrees with an issue, the
issue's acceptance criteria win; where it disagrees with `AGENTS.md`, `AGENTS.md` wins.

---

## 0. Context for the implementing session

`AGENTS.md` defines `ingest`, `query`, and `lint` as **agent workflows**: the LLM reads
sources, discusses takeaways with the user, writes summaries, decides which entities and
concepts matter, synthesizes cited answers, and judges contradictions.

`engine/wiki_engine/` is a Python CLI (`wiki-engine`) that currently attempts to do those
semantic tasks with regex heuristics. That is the wrong boundary. The intended architecture is:

- **Agent (LLM):** all judgment — reading, summarizing, deciding, synthesizing, semantic lint.
- **Engine (Python CLI):** all mechanics — scaffolding, validation, link resolution, index/log
  sync, safe mechanical repairs.

The engine must **never invent content**. When it cannot decide something deterministically, it
emits a TODO marker or a suggestion on stdout.

Decisions (amended 2026-11-10 after the grill round — see §0.1):

1. Verbs: `init`, `ingest`, `query`, `lint`, **plus `sync`**. (Original "no new top-level
   verbs" is lifted; see §0.1 Q2.)
2. `ingest` becomes scaffold-only; `query` becomes retrieval-only; `lint` stays mechanical.
3. Add flags, not commands: `--json`, `--force`. **`--save` and `--extract` are dropped.**
4. Docs-first: update `AGENTS.md` before changing code.

## 0.1 Decisions from the grill round (2026-11-10)

Four decisions settled before implementation. They override any conflicting text below.

**Q1 — `lint --fix` keeps rewriting links, scoped.** The title/stem→path alias map is built
anyway, because `lint` messages need it ("did you mean `[[concepts/foo|Foo]]`" instead of
"target not found"). Given the map, rewriting is cheap. `--fix` rewrites a link only when the
target resolves uniquely **and** the existing display text matches the target's title after
`_strip_type_suffix`; everything else is reported, never touched. The one-time migration of
226 findings runs through `--fix` as §6 describes.

> Note: `fix_vault` already exists (`lint.py:359`) and handles bare links, `update_index`, and
> logging. This is an extension, not a greenfield build.

**Q2 — New verb `sync`; `query --save` deleted.** Strip `--save` down and it writes frontmatter,
calls `update_index`, and appends a log entry. The first belongs to the agent's editor; the last
two are mechanics. Verbs become `init | ingest | query | lint | sync`. `sync` reconciles
`index.md`, normalises frontmatter quoting, and appends a date-deduped log entry. The agent
writes `wiki/synthesis/<slug>.md` with its own tools, then runs `sync`. This also makes Rule 2
of `AGENTS.md` enforceable by one obvious command. ADR-worthy; see §12.

**Q3 — Add an end-to-end verification ticket.** Mechanical checks do not show that
scaffold-plus-TODOs beats the old auto-generated pages. Final ticket: take one unclipped
article, run the full loop by hand (ingest → agent fills TODOs → sync → lint), and record what
the scaffold did and did not give you. This must land before the pattern is used on real ingests.

**Q4 — `ingest --extract` dropped.** Advisory regex candidates for an agent that reads the
source in full anyway. Anchors entity choices and preserves ~80 lines the plan otherwise
deletes. Re-add only if missed entities show up across real ingests, and define "candidate"
first.

---

## 1. Non-goals

- Do not add an LLM client, API calls, or embeddings to the engine.
- Do not change the three-layer layout (`raw/`, `wiki/`, `output/`).
- Do not re-write the 8 existing source summaries, 19 entity pages, or 63 concept pages.
- Do not build a semantic contradiction detector in Python; that stays with the agent.

---

## 2. Baseline (measured before starting)

Running `engine/.venv/bin/wiki-engine --vault . lint` against the repo reports:

- **121 errors** — almost all broken/short-form title links such as `[[GBrain (entity)]]`
  and `[[Foo (concept)]]` instead of `[[entities/gbrain|GBrain (entity)]]`.
- **105 warnings** — the same links reported as short-form wikilinks.
- **26 info** — orphan pages. Many are false positives because inbound links from
  `wiki/index.md` are not counted.

Known bugs / hazards found during investigation:

- Running `wiki-engine` from `engine/` silently created `engine/wiki`, `engine/raw`,
  `engine/output` and linted an empty vault ("clean"). Vault resolution must never scaffold
  into the cwd.
- `lint --fix` appends a log entry on every run (not idempotent).
- `_add_source_to_frontmatter` drops unknown frontmatter keys and resets `created`.
- `download_images` reads `resp.headers` after its `with` block closes.
- `pyproject.toml` says `requires-python = ">=3.9"` but the code uses PEP 604 unions
  (`int | None`, `list[Finding]`), which need 3.10+.

Expected end state: `wiki-engine --vault . lint` returns **0 errors**.

---

## 3. Phase 1 — AGENTS.md (do this first, get review)

File: `AGENTS.md`

### 3.1 Add a section `## Engine and agent roles`

Suggested text:

```markdown
## Engine and agent roles

- **Agent (LLM):** judgment. Read and discuss sources, write summaries/claims/definitions,
  choose which entities and concepts matter, synthesize cited answers, judge contradictions,
  staleness, coverage gaps, and emphasis.
- **Engine (`wiki-engine`):** mechanics. Scaffold pages, validate frontmatter/links/filenames/H1,
  resolve retrieval candidates, maintain `index.md`/`log.md`, and apply safe link/index repairs.
- **Boundary:** the engine may reject or repair *form*; it must never decide *meaning*.
  Anything it cannot determine deterministically is emitted as a suggestion or `<!-- TODO -->`
  for the agent.
```

### 3.2 Amend the numbered Rules

- **Rule 1:** `raw/` **source files** are immutable. The engine may write only downloaded
  assets to `raw/assets/`; it must never rewrite, move, or delete anything else under `raw/`.
  (Resolves the current contradiction between Rule 1 and Rule 6.)
- **Rule 3:** engine owns valid YAML (quoting), required fields, and `created`/`updated`;
  agent owns a Title Case H1. `created` is set once and preserved; `updated` changes on edit.
- **Rule 4:** state the accepted grammar explicitly:
  `[[dir/slug|Page Title]]` where `dir` is one of
  `sources|entities|concepts|synthesis|queries`. Title-style links such as
  `[[Foo (concept)]]` and bare stems are invalid.
- **Rule 8:** engine enforces structural invariants (lint); agent enforces semantic invariants
  (contradictions, stale claims, missing pages).
- **Rule 7:** record that `wiki-engine lint` is the mechanical half; the agent runs it and
  reviews the report. Cadence tracking is a later enhancement (see §10).

### 3.3 Update the Operations sections with per-step ownership

For each operation, mark steps as `[engine]`, `[agent]`, or `[shared]`:

- **Ingest:** `[engine]` scaffold source page, sync index/log, download images.
  `[agent]` read source, discuss takeaways, write Key claims / Structured summary, choose and
  author entity/concept pages, cross-link.
- **Query:** `[engine]` read index and return ranked candidate pages.
  `[agent]` read pages, synthesize the cited answer, decide whether to save.
  `[shared]` the agent writes `wiki/synthesis/<slug>.md` itself, then `sync` reconciles
  `index.md`/`log.md`.
- **Lint:** `[engine]` mechanical scan and safe `--fix`.
  `[agent]` semantic scan, severity triage, and approval of semantic fixes.

### 3.4 Add a short command reference and log vocabulary

```
wiki-engine init
wiki-engine ingest <path> [--json] [--force]
wiki-engine query <question> [--json]
wiki-engine sync
wiki-engine lint [--json] [--fix]
```

Log operation names: `setup | ingest | query | synthesis | sync | lint`.

Commit Phase 1 separately so the contract can be reviewed before code changes.

---

## 4. Phase 2 — Refactor the engine

### 4.1 `engine/wiki_engine/commands/ingest.py` — scaffold only

**Delete** these semantic helpers (approx. lines 114–167 and 170–737):

- `_first_sentence`, `_paragraphs`, `_clean_markdown`
- `_extract_key_claims`, `_build_structured_summary`
- `_extract_capitalized_phrases`, `_classify_candidate`, `extract_entities_and_concepts`
- `_render_entity_page`, `_render_concept_page`, `_build_definition`
- `_existing_page_path`, `_add_related_link`, `_add_source_to_frontmatter`
- `_create_entity_page`, `_create_concept_page`, `_ensure_entity_page`, `_ensure_concept_page`
- `_render_page` (replace with a scaffold renderer)

**Keep and reuse:** `today`, `_slugify`, `_parse_frontmatter_local`, `_extract_title`,
`_extract_tags`, `extract_image_urls`, `_image_filename`, `_download_image`,
`download_images`.

**New `ingest` behavior:**

1. Resolve vault and validate the source is a file inside `raw/` (keep the current guard).
2. Parse leading frontmatter for `title` and `tags`; fall back to first H1, then filename.
3. Slugify the title into `wiki/sources/<slug>.md`.
4. **If the page does not exist**, write a scaffold:

```markdown
---
type: source
title: "<title>"          # always double-quoted; use json.dumps for escaping
sources: ["<source-filename>"]
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [tag1, tag2]
---

# <Page Title>

## Source metadata

- **Source file:** <source-filename>

## Key claims

<!-- TODO: agent — extract and phrase the key claims -->

## Structured summary

<!-- TODO: agent — write the structured summary -->

## Entities

<!-- TODO: agent — decide which entities warrant pages -->

## Concepts

<!-- TODO: agent — decide which concepts warrant pages -->

## Images

<!-- TODO: agent — describe each image in text; engine-downloaded files below -->
```

   Add downloaded image lines only if `download_images` returned any.
5. **If the page exists**, do **not** touch the body and do not overwrite TODOs the agent has
   replaced. Only: ensure required frontmatter keys exist, refresh `updated`, and set
   `created` only when absent. Add a `--force` flag to rewrite the scaffold.
6. Always run `update_index(vault)` and append an idempotent
   `## [YYYY-MM-DD] ingest | <title>` entry.
7. Print a manifest, for example:

```
ingested raw/articles/foo.md -> wiki/sources/foo.md (created)
  TODO: Key claims, Structured summary, Entities, Concepts
  images: 2 downloaded to raw/assets/
```

**`--extract` — dropped (Q4, §0.1).** Do not carry the capitalized-phrase heuristic forward in
any form. It is deleted along with the other semantic helpers.

**`--json`:** emit the manifest as JSON (`source`, `page`, `created`, `todos`, `images`).

**Frontmatter writing rule:** always quote scalar values with `json.dumps(str(value))`
(JSON strings are valid YAML). Flow lists keep `[a, b]` form but quote items that contain
`:`/`,`/`#`. Never emit an unquoted title containing `:`.

### 4.2 `engine/wiki_engine/commands/query.py` — retrieval only

**Delete:** `_synthesize`, `_page_summary`, `_first_sentence`, `_strip_frontmatter`,
`_extract_h1`, `_title_case` (no title fallback is needed any more; delete `_title_case` too).

**New behavior for `query <question>`:**

1. Read `wiki/index.md` (keep the existing error when missing).
2. Match candidate entries by keyword (reuse `_keywords`, `INDEX_ENTRY_RE`,
   `_find_relevant_pages`). Keep the existing rule that only path-prefixed links are candidates.
3. For each match, read the page and compute a short snippet (first non-heading paragraph,
   truncated to ~200 chars). This is retrieval metadata, not synthesis.
4. Print a human-readable candidate list, or `--json`:

```json
{"question": "...", "matches": [
  {"target": "concepts/foo", "title": "Foo", "path": "wiki/concepts/foo.md", "snippet": "..."}
]}
```

1. Never generate an answer, never auto-save, never print "I found N pages that answer…".
   Exit 0 with no matches, as today.

**`--save <file|->` — dropped (Q2, §0.1).** DELETE the flag and the code that derives a title
from the question or `sources` from anything. Remove the old behavior where `--save` persisted an
engine-generated answer. The agent writes `wiki/synthesis/<slug>.md` itself and runs
`wiki-engine sync` (see §4.6).

### 4.3 `engine/wiki_engine/lint.py` — harden the mechanical checks

Keep: frontmatter parsing, wikilink extraction, path/stem resolution, ambiguity detection,
broken-link detection, orphan detection, severity grouping, `format_result`.

**Add checks:**

1. **Scan `wiki/index.md` and `wiki/log.md` too** (at least for link form). They are
   currently invisible, which is why the repo reports clean while `index.md` has bare links.
2. **Orphan inbound links:** count links from `index.md` as inbound. A page listed in the
   index is not an orphan.
3. **Kebab-case filenames:** every page file must match `^[a-z0-9]+(-[a-z0-9]+)*\.md$`
   (error). Allow `index.md` and `log.md`.
4. **YAML validity (stdlib):**
   - values must be quoted when they contain `:`, start with `[`/`{`/`*`/`&`/`!`/`|`/`>`,
     or contain `#`;
   - flow lists must parse with the existing `_parse_flow_list`;
   - `created`/`updated` must match `^\d{4}-\d{2}-\d{2}$`;
   - `created <= updated`.
5. **Title consistency:** frontmatter `title` and H1 should match after stripping a trailing
   `(entity|concept|source|synthesis)` suffix (warning, not error).
6. **Duplicate H1:** more than one `#` line is a warning.
7. **Sources exist:** every entry in frontmatter `sources` must exist somewhere under `raw/`
   (warning; allow the current filename-only convention). Skip for `type: synthesis` if the
   entry is a wiki target.
8. Add `--json` output:

```json
{"command": "lint",
 "summary": {"errors": 0, "warnings": 0, "info": 0},
 "findings": [{"severity": "error", "file": "wiki/...", "line": 12, "message": "..."}]}
```

**`--fix` becomes strictly mechanical and safe:**

- Build an alias map — **shared with the lint messages**, so a broken link reports
  `did you mean [[concepts/foo|Foo]]` instead of a bare "target not found":
  - canonical `dir/stem`
  - unique bare `stem`
  - exact frontmatter `title`
  - H1 text, plus H1 with a trailing type suffix stripped
- Rewrite a link to `[[dir/stem|Display]]` only when **both** hold:
  1. the target resolves **uniquely** through that map; and
  2. the existing display text, if any, equals the target's frontmatter title after
     `_strip_type_suffix` — in which case keep the existing display text verbatim.
  For a bare/title target with no display text, use the frontmatter title as display.
- Leave ambiguous or non-matching targets untouched and report them individually.
  (This is what resolves the 22 `pi-durable` cases: their display text names the type.)
- Preserve unknown frontmatter fields: edit only the lines that change (`sources`, `updated`,
  `created`) instead of re-rendering the whole block.
- Reconcile `index.md`: append missing pages; optionally remove entries whose target file no
  longer exists (only under `--fix`, and report each removal).
- Log `## [YYYY-MM-DD] lint | Automated fixes applied` **only if something changed**, and
  dedupe by date (add `log_has_entry_on_date` or inline check).
- Print a summary of files changed and links rewritten.

### 4.4 `engine/wiki_engine/vault.py` / `cli.py` — vault safety

- Split `ensure_vault_structure`:
  - `init` calls it (scaffolding is allowed).
  - Other commands must **not** scaffold. In `cli.main`, before dispatch:
    - resolve the vault;
    - if a marker is missing (`wiki/index.md` or `wiki/log.md`), print
      `error: not a wiki vault: <path> (run wiki-engine init first)` and return 1;
    - never create directories as a side effect of `ingest`/`query`/`lint`.
- When `--vault` is omitted and cwd is not a vault, refuse rather than scaffolding cwd.
- Remove the now-unused `ensure_vault_structure` call from `cli.main`.
- Keep `is_within_vault`.

### 4.5 Small mechanical fixes

- Fix `download_images`/`_download_image` to read `Content-Type` **inside** the `with` block.
- Set `requires-python = ">=3.10"` in `engine/pyproject.toml`, then refresh `uv.lock`
  (`cd engine && uv lock`), because the code uses PEP 604 unions.
- Remove duplicate `import re` and the mid-file imports at the bottom of `lint.py`; move
  `from datetime import date` and `from .log import append_log_entry` to the top.

### 4.6 `engine/wiki_engine/commands/sync.py` — new verb (Q2, §0.1)

`wiki-engine sync` is the durable mechanic that `query --save` and `lint --fix` were both
smuggling. It never edits page bodies and never invents content.

1. Resolve the vault through the marker guard from §4.4 (refuse outside a vault).
2. **Index reconciliation** — reuse `update_index(vault)`:
   - append entries for pages present on disk but absent from `wiki/index.md`;
   - report entries whose target file no longer exists (do not delete them here; that stays
     behind `lint --fix`, per §4.3);
   - write only if the file actually changed.
3. **Frontmatter normalisation** — for each page, edit only lines that change:
   - quote scalar values per the rule in §4.1;
   - ensure required keys exist;
   - set `created` only when absent, refresh `updated` only when another line changed;
   - preserve all unknown keys and their order.
4. **Log** — append `## [YYYY-MM-DD] sync | <n> page(s) updated, <m> index entr(y|ies) added`
   only if something changed, deduped by date.
5. Print a summary of files changed; `--json` is **not** required for v1.
6. Exit 0 on nothing-to-do.

`sync` shares the frontmatter-writing helper with `ingest` and the index helper with `lint`
— one implementation, three callers.

---

## 5. Tests

Run with `cd engine && uv run pytest` (or `.venv/bin/pytest`).

### 5.1 `tests/test_ingest.py`

- Keep tests for `_slugify`, `_parse_frontmatter_local`, `_extract_title`, `_extract_tags`,
  and `extract_image_urls`.
- **Delete** tests for `_extract_key_claims`, `_build_structured_summary`,
  `extract_entities_and_concepts`, `_classify_candidate`, and the entity/concept page creation
  E2E tests.
- Update the main E2E test to assert:
  - the page has valid frontmatter and the `<!-- TODO: agent -->` markers;
  - the source body text is **not** copied into the page;
  - no entity/concept pages are created by default;
  - `raw/` is unchanged.
- Add:
  - `test_ingest_does_not_overwrite_agent_body`: ingest, append authored text, re-ingest,
    assert the authored text survives and `created` is unchanged.
  - `test_ingest_extract_prints_candidates_only` — **dropped with `--extract` (Q4, §0.1).**
  - `test_ingest_json_manifest`.
  - `test_ingest_quotes_titles_with_colons`.

### 5.2 `tests/test_query.py`

- Keep `_keywords`, `_find_relevant_pages`, and the no-match/uninitialized-vault tests.
- Delete `_synthesize` tests.
- Add:
  - `test_query_json_returns_matches_with_snippets`;
  - `test_query_does_not_generate_answer` (output contains no "Cited:" synthesis block);
  - `test_query_save_*` — **all dropped with `--save` (Q2, §0.1).** Replacements live in §5.7.

### 5.3 `tests/test_lint.py`

- Keep existing frontmatter/link/title-case/orphan tests, updating the orphan expectation so
  index links count as inbound.
- Add tests for: index.md link scanning, kebab-case filenames, unquoted colon values, bad
  dates, `created > updated`, title/H1 mismatch, duplicate H1, missing raw source.

### 5.4 `tests/test_lint_fix.py`

- Keep the short-form rewrite test but expect `[[dir/stem|Title]]`.
- Add:
  - title-style link rewrite (`[[Foo (concept)]]` → `[[concepts/foo|Foo (concept)]]`);
  - unknown frontmatter fields preserved;
  - log entry not duplicated on a second no-op `--fix`;
  - ambiguous targets left untouched.

### 5.5 `tests/test_cli.py`

- Keep the subcommand registration test, updated to **five** verbs (`init`, `ingest`, `query`,
  `lint`, `sync`).
- Add flag-parsing tests for `ingest --json/--force`, `query --json`, and `lint --json/--fix`.
- Add a test asserting `--save` and `--extract` are rejected as unknown arguments (they are
  removed, not silently ignored).
- Add `test_non_init_commands_refuse_non_vault_cwd`: run in a temp dir with no
  `wiki/index.md`, assert return code 1 and that no directories were created.

### 5.6 `tests/test_vault.py`

- Add tests for marker detection and the refusal path.

### 5.7 `tests/test_sync.py` — new (Q2, §0.1)

- `test_sync_appends_missing_index_entries`;
- `test_sync_is_idempotent` (second run changes nothing, logs nothing);
- `test_sync_preserves_unknown_frontmatter`;
- `test_sync_sets_created_once_and_refreshes_updated_only_on_change`;
- `test_sync_quotes_unquoted_colon_values`;
- `test_sync_reports_dangling_index_entries_without_deleting`;
- `test_sync_refuses_outside_vault`.

---

## 6. Phase 3 — Migrate the existing wiki (after Phase 2 passes tests)

Do **not** re-run `ingest` over existing sources as a migration mechanism. The existing pages
are agent-authored and richer than any scaffold.

1. Back up with a commit first (or work in a worktree).
2. Run `engine/.venv/bin/wiki-engine --vault . lint --json > tmp/lint-before.json`.
3. Run `engine/.venv/bin/wiki-engine --vault . lint --fix`.
   This rewrites title-style and bare links through the alias map, syncs the index, and logs
   the operation.
4. Review the remaining errors in `tmp/lint-after.json`. Expect genuinely missing pages to
   remain (for example links to pages that were never created). Hand those to the agent to
   resolve; do not auto-create stubs.
5. Keep the `(entity)`/`(concept)` H1 suffixes. The linter tolerates them and the pages are
   internally consistent.
6. Run `lint` again until errors are zero. Then:
   `## [YYYY-MM-DD] lint | Mechanical migration to file-path wikilinks`.

Expected: 121 errors → 0, 105 warnings → 0 (or only genuine issues), 26 info → far fewer.

---

## 7. Phase 4 — Verification checklist

- [ ] `cd engine && uv run pytest` — all green.
- [ ] `engine/.venv/bin/wiki-engine --vault . lint` — 0 errors.
- [ ] `engine/.venv/bin/wiki-engine --vault . lint --json | jq .summary` — sane counts.
- [ ] Dry run in `tmp/`: `init` a scratch vault, copy one raw article, run `ingest`, confirm
      the page contains TODO markers and none of the article's prose.
- [ ] Re-run `ingest` after appending authored text; confirm the text survives and `created`
      is unchanged.
- [ ] `git status --short` — no changes under `raw/` except intentionally downloaded assets.
- [ ] Run `wiki-engine` from `engine/` with no `--vault`; confirm it refuses instead of
      creating `engine/wiki`, `engine/raw`, `engine/output`.
- [ ] `wiki-engine sync` twice: second run reports nothing changed and appends no log entry.
- [ ] **End-to-end (Q3, §0.1):** pick one unclipped article, `ingest` it, have the agent fill
      every TODO, `sync`, `lint` clean. Record what the scaffold did and did not give you.
- [ ] `git log --oneline` — one commit per ticket, tests landing with their change.

---

## 8. File-by-file change map

| File | Change |
|---|---|
| `AGENTS.md` | Engine/agent roles section; Rules 1, 3, 4, 7, 8; operations ownership; command reference |
| `engine/wiki_engine/cli.py` | Vault marker guard; stop calling `ensure_vault_structure` for non-init |
| `engine/wiki_engine/vault.py` | Marker helper; clarify `ensure_vault_structure` is init-only |
| `engine/wiki_engine/commands/ingest.py` | Delete semantic generation; scaffold-only; `--json`, `--force` |
| `engine/wiki_engine/commands/query.py` | Delete `_synthesize` and `--save`; retrieval + `--json` |
| `engine/wiki_engine/commands/sync.py` | **New verb** (Q2): index reconciliation, frontmatter normalisation, dated log entry |
| `engine/wiki_engine/lint.py` | New checks; `--json`; alias map shared with messages; `--fix` scoped to unambiguous rewrites; imports cleanup |
| `engine/wiki_engine/log.py` | Add date-scoped dedupe helper |
| `engine/pyproject.toml` | `requires-python = ">=3.10"` |
| `engine/uv.lock` | Refresh after pyproject change |
| `engine/tests/*.py` | As described in §5, plus new `test_sync.py` |

---

## 9. Suggested commit sequence

1. `docs: define engine vs agent responsibilities` — T0, the contract
2. `chore(engine): guard vault resolution, require 3.10, fix image headers and imports` — T1,
   pure prefactor, no behaviour change
3. `feat(engine): add sync verb` — T2, lands the index/log/frontmatter helpers that everything
   else calls
4. `refactor(engine): make ingest scaffold-only` — T3
5. `refactor(engine): make query retrieval-only` — T4
6. `fix(engine): harden mechanical lint checks and add --json` — T5
7. `fix(engine): scope --fix to unambiguous alias rewrites` — T6
8. `fix(wiki): mechanically migrate links to file-path wikilinks` — T7
9. `test: end-to-end scaffold workflow on one article` — T8

Tests land with their ticket, never as a separate cleanup commit. (The earlier sequence put the
whole suite after three engine commits, which inverts TDD.)

---

## 10. Deferred / optional (do not block this work)

- Lint cadence tracking (every 10 ingests, monthly, before major queries) via a small state
  file under `wiki/` or by counting log entries. Note it in AGENTS.md as agent-managed.
- Fuzzy/semantic retrieval beyond keyword matching (see `qmd`).
- Real YAML parser (PyYAML) instead of the stdlib checks, if the custom checks prove brittle.
- `output/` rendering for query reports.

---

## 11. Definition of done

- AGENTS.md names the engine as a mechanical helper and the agent as the reasoning layer.
- `ingest` cannot write prose; it only scaffolds, syncs, and reports.
- `query` cannot fabricate an answer or a page; `--save` no longer exists.
- `sync` is the single mechanism for index/log/frontmatter reconciliation.
- `lint` validates structure, not meaning, and fixes only unambiguous mechanical issues.
- The engine never creates a vault implicitly.
- The existing wiki lints clean after the mechanical link migration.
- One real article has gone through the full scaffold→agent→sync→lint loop and is documented.
- All tests pass.

## 12. Documentation debt this creates

- `docs/agents/domain.md` points at `docs/adr/`, which does not exist. Q2 (adding `sync`,
  lifting "no new top-level verbs") is a hard-to-reverse decision worth an ADR-0001. Create the
  directory as part of T0 and record it there.
- `AGENTS.md` Rule 2 ("always update `index.md` and `log.md`") becomes `wiki-engine sync`; say
  so explicitly rather than leaving the agent to infer it.
