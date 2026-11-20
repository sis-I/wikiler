# PROTOTYPE: issue #4 portable skill contract

THROWAWAY. This is not production code and must not merge into main. The validated
decision is posted on issue #4; the implementation lives in issue #6.

## Question

What is the smallest portable contract for `wiki-setup`, `wiki-ingest`,
`wiki-query`, and `wiki-lint` when operating Wikiler vaults, and does a realistic
first run need a fifth skill or a harness adapter?

## Verdict

Four skills are enough. Each description carries a `Use when ...` trigger, so a
harness can select the right one without a router. `wiki init` installs them into
`<vault>/.agents/skills/`, which OpenCode and Pi already search. No harness adapter
and no fifth skill are needed. `sync` stays CLI-only, reached from `AGENTS.md` and
from each skill's handoff.

## Run

From the repository root:

```
bash prototype/issue-4-skills/check.sh
```

It prints each skill's frontmatter and body size so you can see the contract's
state. No install, no network, no persistence.

## Layout

```
prototype/issue-4-skills/
├── README.md                # this file
├── check.sh                 # one-command inspection of the four skills
├── first-run.md             # walkthrough, edge cases, verdict
└── vault/
    ├── AGENTS.md            # stand-in for the packaged runtime_rules.md copy
    └── .agents/skills/
        ├── wiki-setup/SKILL.md
        ├── wiki-ingest/SKILL.md
        ├── wiki-query/SKILL.md
        └── wiki-lint/SKILL.md
```
