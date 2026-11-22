"""Contract tests for the agent-facing wiki rules.

AGENTS.md and docs/adr/ are prose, but they are the contract the engine and
the agent are held to. These tests fail if the contract loses a required
section, a verb, or the link grammar, so a docs edit cannot silently weaken
it.
"""

import unittest
from pathlib import Path

from wikiler import lint as lint_module
from wikiler import log as log_module
from wikiler import page as page_module
from wikiler.commands.init import INDEX_TEMPLATE

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_MD = REPO_ROOT / "src" / "wikiler" / "runtime_rules.md"
EXAMPLE_AGENTS_MD = REPO_ROOT / "examples" / "vault" / "AGENTS.md"
ADR_DIR = REPO_ROOT / "docs" / "adr"


class TestAgentConfig(unittest.TestCase):
    def setUp(self):
        self.text = AGENTS_MD.read_text(encoding="utf-8")

    def test_engine_and_agent_roles_section(self):
        self.assertIn("## Engine and agent roles", self.text)
        # The boundary is the point of the section: form vs meaning.
        self.assertIn("never decide", self.text)
        self.assertIn("TODO", self.text)

    def test_page_schema_is_documented(self):
        for field in ("type", "title", "sources", "created", "updated", "tags"):
            self.assertIn(field, self.text)
        self.assertIn("Title Case H1", self.text)
        self.assertIn("kebab-case", self.text)

    def test_raw_sources_immutable_but_assets_writable(self):
        self.assertIn("source files", self.text)
        self.assertIn("immutable", self.text)
        self.assertIn("raw/assets/", self.text)

    def test_link_grammar_has_canonical_and_migration_examples(self):
        self.assertIn("[[dir/slug|Page Title]]", self.text)
        self.assertIn("Canonical:", self.text)
        self.assertIn("Non-canonical, accepted for migration:", self.text)
        self.assertIn("(concept)", self.text)

    def test_wikilink_tiers_are_described_without_invalid_wording(self):
        self.assertIn("non-canonical, accepted for migration", self.text)
        self.assertNotIn("Invalid:", self.text)
        self.assertIn("`wiki/` prefix", self.text)
        self.assertIn("WARNING-level", self.text)
        self.assertIn("migration affordances", self.text)

    def test_command_reference_lists_every_verb(self):
        for command in (
            "wiki init",
            "wiki ingest <path> [--download-images] [--json] [--force]",
            "wiki query <question> [--json]",
            "wiki sync",
            "wiki lint [--json] [--fix]",
        ):
            self.assertIn(command, self.text)

    def test_image_downloads_are_opt_in(self):
        # Rule 6, Ingest step 3, and the command reference each carry the
        # opt-in split, so one doc edit cannot quietly drop a piece of it.
        self.assertIn(
            "6. Images are local-first and opt-in. `ingest` performs no "
            "network I/O",
            self.text,
        )
        self.assertIn("reported in the manifest as not downloaded", self.text)
        self.assertIn("skipping decorative images is fine", self.text)
        self.assertIn(
            "`--download-images` fetches the remaining remote URLs", self.text
        )

    def test_force_flag_is_documented_as_destructive(self):
        # The flag throws away agent-authored text, so the contract has to
        # say so before an agent reaches for it.
        self.assertIn("`--force` is destructive", self.text)
        self.assertIn("discarding", self.text)

    def test_log_operation_vocabulary(self):
        self.assertIn("setup | ingest | query | synthesis | sync | lint", self.text)

    def test_rules_split_structural_and_semantic_ownership(self):
        self.assertIn("structural invariants", self.text)
        self.assertIn("semantic invariants", self.text)
        self.assertIn("mechanical half", self.text)

    def test_operations_mark_ownership(self):
        for marker in ("[engine]", "[agent]", "[shared]"):
            self.assertIn(marker, self.text)

    def test_example_agents_is_a_byte_for_byte_copy(self):
        self.assertEqual(
            AGENTS_MD.read_bytes(),
            EXAMPLE_AGENTS_MD.read_bytes(),
            "examples/vault/AGENTS.md must match runtime_rules.md byte for byte",
        )

    def test_dash_rule_is_documented(self):
        self.assertIn("## Dash Rule", self.text)
        self.assertIn("em-dashes, en-dashes, or double hyphens", self.text)
        self.assertIn("technical syntax and are exempt", self.text)
        self.assertIn("vault documents or code comments", self.text)

    def test_normative_contract_states_all_ten_areas(self):
        self.assertIn("## Normative vault contract for 0.x", self.text)
        for area in (
            "1. **Directory layout:**",
            "2. **Frontmatter fields:**",
            "3. **Filename rules:**",
            "4. **Title Case H1:**",
            "5. **Wikilink grammar, two tiers:**",
            "6. **Source immutability:**",
            "7. **Index and log semantics:**",
            "8. **Raw asset rules:**",
            "9. **Engine and agent ownership:**",
            "10. **Scope of the promise:**",
        ):
            self.assertIn(area, self.text)

    def test_glossary_defines_twelve_vault_terms(self):
        glossary = REPO_ROOT / "GLOSSARY.md"
        self.assertTrue(glossary.is_file(), "root GLOSSARY.md must exist")
        text = glossary.read_text(encoding="utf-8")
        for term in (
            "vault",
            "page",
            "raw source",
            "source page",
            "entity",
            "concept",
            "synthesis",
            "query",
            "wikilink",
            "index",
            "log",
            "asset",
        ):
            self.assertIn(f"## {term}\n", text)
        self.assertNotIn("\u2014", text)
        self.assertNotIn("\u2013", text)

    def test_adr_0002_records_vault_contract_decision(self):
        adrs = sorted(ADR_DIR.glob("0002-*.md"))
        self.assertEqual(len(adrs), 1, "expected exactly one ADR-0002 file")
        text = adrs[0].read_text(encoding="utf-8")
        for field in ("Status: Accepted", "Date:", "Deciders:"):
            self.assertIn(field, text)
        for phrase in ("Ratify", "0.x", "canonical artifact"):
            self.assertIn(phrase, text)
        readme = (ADR_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("ADR-0002", readme)
        self.assertIn("0002-", readme)

    def test_adr_0001_records_sync_verb_decision(self):
        self.assertTrue(ADR_DIR.is_dir(), "docs/adr/ must exist")
        adrs = sorted(ADR_DIR.glob("0001-*.md"))
        self.assertEqual(len(adrs), 1, "expected exactly one ADR-0001 file")
        text = adrs[0].read_text(encoding="utf-8")
        self.assertIn("sync", text)
        self.assertIn("no new top-level verbs", text)


class TestLockedConstants(unittest.TestCase):
    """The machine-checkable half of the normative vault contract.

    Expected values come from the decision recorded on issue #3, not from the
    docs, so a prose edit cannot quietly change what the engine enforces.
    """

    def test_six_frontmatter_fields_are_locked(self):
        self.assertEqual(
            page_module.REQUIRED_FRONTMATTER_FIELDS,
            ["type", "title", "sources", "created", "updated", "tags"],
        )

    def test_five_page_types_are_locked(self):
        self.assertEqual(
            lint_module.VALID_TYPES,
            {"source", "entity", "concept", "synthesis", "query"},
        )

    def test_allowed_directories_and_types_are_locked(self):
        self.assertEqual(
            page_module.PAGE_DIRS,
            ("sources", "entities", "concepts", "synthesis", "queries"),
        )
        self.assertEqual(
            page_module.PAGE_TYPE_BY_DIR,
            {
                "sources": "source",
                "entities": "entity",
                "concepts": "concept",
                "synthesis": "synthesis",
                "queries": "query",
            },
        )

    def test_filename_regex_is_locked(self):
        self.assertEqual(
            lint_module.KEBAB_CASE_RE.pattern,
            r"^[a-z0-9]+(-[a-z0-9]+)*\.md$",
        )

    def test_log_vocabulary_is_locked(self):
        self.assertEqual(
            log_module.LOG_OPERATIONS,
            ("setup", "ingest", "query", "synthesis", "sync", "lint"),
        )

    def test_init_index_template_obeys_the_dash_rule(self):
        self.assertNotIn("\u2014", INDEX_TEMPLATE)
        self.assertNotIn("\u2013", INDEX_TEMPLATE)
        self.assertIn(
            "Content catalog, one line per page, categorized.", INDEX_TEMPLATE
        )


if __name__ == "__main__":
    unittest.main()
