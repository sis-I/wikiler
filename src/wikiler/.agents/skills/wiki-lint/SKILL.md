---
name: wiki-lint
description: Mechanical structural scan of a Wikiler vault. Checks frontmatter, filenames, H1 form, link form and resolution, orphans, and index/log consistency. Reports findings by severity; --fix applies unambiguous repairs only.
---

# wiki-lint: Portable Skill

## Purpose

Scan every wiki page plus the index and log, and report findings grouped by
severity: errors → warnings → info. Checks frontmatter, filenames, H1 form,
link form and resolution, orphans, and index/log consistency.

## Contract

- **Input**: none (operates on the target vault).
- **Output**: structural findings report (human-readable or JSON).
- **Exit codes**: `0` no errors; `1` lint errors present; `2` invalid usage.
- **JSON**: `--json` prints findings as JSON.
- **Fix**: `--fix` applies only unambiguous mechanical repairs (link
  rewrites, dangling index entry removal).

## Flags

- `--fix`: apply automated fixes to unambiguous issues only.
- `--json`: emit findings as JSON.

## Preconditions

- Target must be an initialized vault.

## Steps

1. Resolve target vault; refuse if not a vault.
2. Build alias map from all page titles, H1s, and stems.
3. Check each page: filename kebab-case, frontmatter fields, YAML validity,
   dates, H1 Title Case, title/H1 agreement, source existence under `raw/`.
4. Check each wikilink: full `[[dir/slug|Page Title]]` form, target
   resolution, display text match.
5. Check index: entries resolve to existing files; dangling entries reported.
6. Check orphans: pages with zero inbound links (index links count; log
   links do not).
7. Report findings by severity. Under `--fix`, rewrite unambiguous links and
   remove dangling index entries.
8. Append a dated `lint` log entry only when fixes were applied.

## Notes

- The linter judges form only. Contradictions, staleness, and coverage gaps
  stay with the agent.
- Log links are scanned for form but never resolved or counted as inbound:
  rewriting history is not a mechanical repair.
- Aim to lint after every 10 ingests, monthly, and before major queries.
