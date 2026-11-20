# First-run walkthrough (prototype)

Question: does a realistic first run need a fifth skill or a harness adapter?

## Walkthrough

1. User installs `wikiler`. Package data carries `runtime_rules.md` and the four
   `SKILL.md` files. No harness-specific install step.
2. User runs `wiki init --vault ./my-vault`. Per the decided contract this creates
   the usual `raw/`, `wiki/`, `output/`, `index.md`, `log.md`, plus
   `AGENTS.md` (copy of runtime rules) and `.agents/skills/wiki-*/SKILL.md`.
3. User opens a harness with `my-vault` as the working directory. OpenCode and Pi
   search `.agents/skills/`, find four skills, and advertise their descriptions.
   The `Use when ...` clauses are the triggers. No router is loaded.
4. User drops `raw/articles/foo.md` and says "process this". The harness selects
   `wiki-ingest` from the description. It runs `wiki ingest`, reads the manifest,
   fills the TODO sections itself, writes related pages, and runs `wiki sync`.
5. User asks "what is X?". The harness selects `wiki-query`, reads the candidates,
   and synthesizes the answer itself with wikilink citations. Optionally it writes
   a synthesis page and runs `wiki sync`.
6. User asks "check the wiki". The harness selects `wiki-lint`, reviews findings,
   and fixes meaning the engine cannot decide.

At no point does the harness need a harness-specific tool or a fifth skill. When
the user says "sync my wiki" there is no skill, but the command is in `AGENTS.md`
and in each skill's handoff, so the agent runs `wiki sync` directly. That matches
the release map, which keeps `sync` CLI-only.

## Edge cases pushed

- Harness opened at the parent of the vault: `.agents/skills/` is not searched
  downwards, so the skills are not found. Contract scope says the harness is
  opened on the vault. Worth stating in the README; not a reason for an adapter.
- Two skills could match "set up the wiki and ingest this file". The descriptions
  are distinct enough that the harness selects setup first, then ingest after
  init. Acceptable; the user can invoke either by ID explicitly.
- Re-init overwrite: should an existing `AGENTS.md` or skill be refreshed or
  preserved? Genuinely open. Captured in issue #6 rather than decided here.
- A routing skill would add a load step without adding a capability. Four skills
  with explicit triggers are smaller. Rejected.

## Verdict

The four skills, installed by `init` into `.agents/skills/`, are sufficient. No
fifth skill, no routing skill, no harness adapter. The only gap is engine work:
`init` must actually copy `runtime_rules.md` and install the skills. That is
issue #6.
