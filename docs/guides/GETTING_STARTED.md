# Getting Started

Status: Normative

This walkthrough goes from a fresh install to a linted vault. It is the
detailed companion to the root `README.md`. The rules behind each step are in
[LLM_WIKI_IMPLEMENTATION_GUIDE.md](LLM_WIKI_IMPLEMENTATION_GUIDE.md), the sole
normative how-to. A committed example lives in `examples/vault/`; the test
suite copies it to a temporary directory before exercising the verbs, so it is
safe to read but not to use as your own vault.

## 1. Install

```
pip install wikiler
```

Or, from a source checkout:

```
pip install -e .
```

This installs the `wiki` console command. Wikiler needs Python 3.10 or newer
and has no required runtime dependencies.

## 2. Set up Obsidian for sources

Wikiler reads plain Markdown, so Obsidian can be the editor for `raw/`.

1. Install Obsidian and open the vault root as an Obsidian vault.
2. Install the Web Clipper plugin. In its settings, set **Folder** to
   `raw/<topic>/`, for example `raw/articles/`.
3. Set **Default location for new attachments** to `raw/assets` under
   Settings, Files and links.
4. When a saved note references remote images, run **Download attachments for
   current file** from the Command palette. That command has no default
   keybinding, so assign a hotkey only if you want one.

The engine performs no network I/O on ingest. It lists local assets found
under `raw/assets/` and reports remote URLs as not downloaded. Pass
`--download-images` only for a source that never went through Obsidian.

## 3. Create a vault

```
wiki init --vault /path/to/my-vault
```

Only `init` may create a vault. Every other command refuses to run outside an
initialized one. `init` creates:

```
my-vault/
├── AGENTS.md             # vault agent contract, preserved on re-run
├── .agents/
│   └── skills/
│       ├── wiki-setup/SKILL.md
│       ├── wiki-ingest/SKILL.md
│       ├── wiki-query/SKILL.md
│       └── wiki-lint/SKILL.md
├── raw/
│   ├── articles/
│   ├── papers/
│   ├── repos/
│   ├── datasets/
│   └── assets/          # downloaded images, opt-in
├── wiki/
│   ├── sources/
│   ├── entities/
│   ├── concepts/
│   ├── synthesis/
│   ├── queries/
│   ├── index.md
│   └── log.md
└── output/
```

The vault `AGENTS.md` is copied from the packaged runtime rules and is the
single contract for agents operating the vault. The four skills are discovered
from their descriptions. `sync` stays CLI-only, so there is no fifth skill.
Re-running `init` preserves edited files. To refresh one, delete it and run
`init` again.

## 4. Ingest one source

Clip an article into `raw/articles/`, then run:

```
wiki ingest --vault /path/to/my-vault articles/my-article.md
```

The engine writes `wiki/sources/my-article.md` with frontmatter and `<!-- TODO:
agent -->` markers. It does not copy the source prose into the page, invent
claims, or create entity and concept pages. It records the ingest in
`wiki/log.md` and adds the new page to `wiki/index.md`.

For a machine-readable manifest:

```
wiki ingest --vault /path/to/my-vault articles/my-article.md --json
```

To see which images were found, read the manifest. Adding `--download-images`
fetches remote URLs into `raw/assets/`; without it, they are reported as not
downloaded.

## 5. Author the pages

Read the source completely and discuss the takeaways before writing. Fill each
scaffold section:

- Source metadata: the source filename and any image descriptions the prose
  does not already carry. Skipping decorative images is fine.
- Key claims and structured summary: in your own words, grounded in the
  source. The engine never writes prose.
- Entities and concepts: decide which warrant their own pages. Update an
  existing page or create a new one under `wiki/entities/` or
  `wiki/concepts/` with the six required frontmatter fields and a Title Case
  H1.

A single source may touch 10 to 15 wiki pages. That is normal. Link related
pages with the canonical grammar:

```
[[dir/slug|Page Title]]
```

The `dir` is one of `sources`, `entities`, `concepts`, `synthesis`, or
`queries`. Use kebab-case filenames. Never hand-edit `wiki/index.md` or
`wiki/log.md`.

## 6. Reconcile with sync

```
wiki sync --vault /path/to/my-vault
```

`sync` appends index entries for pages on disk, normalises frontmatter
quoting, and appends a dated log entry only when something changed. It never
edits a page body. Run it after authoring or editing pages. A second run with
nothing to do writes nothing, including no new log entry.

## 7. Query the vault

```
wiki query --vault /path/to/my-vault "what is X?"
```

The engine reads `wiki/index.md`, ranks candidate pages, and prints a short
snippet for each. It does not answer the question. Read the candidates and
synthesise a cited answer with canonical wikilinks. If the answer produces a
valuable artifact, write `wiki/synthesis/<slug>.md` yourself and run `sync`.

Use `--json` to get the ranked candidates as a single JSON object:

```
wiki query --vault /path/to/my-vault "what is X?" --json
```

## 8. Lint the structure

```
wiki lint --vault /path/to/my-vault
```

The engine reports structural findings by severity: errors, warnings, and
info. `--fix` applies only repairs it can resolve unambiguously, such as
rewriting a non-canonical link to the canonical form. `--json` prints findings
as JSON.

Review the report yourself. The engine cannot judge contradictions, stale
claims, important concepts with no page, missing cross-references, or research
gaps. Fix those, then re-run lint until structural errors are zero. Aim to
lint after every 10 ingests, monthly, and before major queries. The cadence is
agent-managed, not engine-enforced.

## 9. Check your work

A healthy first vault has these properties:

- Every page has the six frontmatter fields and exactly one Title Case H1.
- All wikilinks use `[[dir/slug|Page Title]]`.
- Every page is listed in `wiki/index.md`, and the log has one `setup` entry
  plus an `ingest` entry for the source.
- `wiki lint` reports zero findings at every severity.
- A second `wiki sync` changes nothing and logs nothing.
- Nothing under `raw/` changed except an image you chose to download.

## 10. Keep the vault current

One source at a time. Stay involved, read the scaffold summaries, and guide
emphasis. Treat pages as derived on demand: when a source changes, regenerate
what depends on it instead of letting the prose rot.

The replacement policy for local files matters on re-ingest. `wiki ingest`
leaves an authored body alone. `--force` restores the scaffold and discards
your text. It preserves `created` and refreshes `updated`. Use it only when
you mean to start that page over.
