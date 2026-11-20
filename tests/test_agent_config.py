"""Contract tests for the agent-facing wiki rules.

AGENTS.md and docs/adr/ are prose, but they are the contract the engine and
the agent are held to. These tests fail if the contract loses a required
section, a verb, or the link grammar, so a docs edit cannot silently weaken
it.
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_MD = REPO_ROOT / "src" / "wikiler" / "runtime_rules.md"
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

    def test_link_grammar_has_valid_and_invalid_examples(self):
        self.assertIn("[[dir/slug|Page Title]]", self.text)
        self.assertIn("Valid:", self.text)
        self.assertIn("Invalid:", self.text)
        self.assertIn("(concept)", self.text)

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

    def test_adr_0001_records_sync_verb_decision(self):
        self.assertTrue(ADR_DIR.is_dir(), "docs/adr/ must exist")
        adrs = sorted(ADR_DIR.glob("0001-*.md"))
        self.assertEqual(len(adrs), 1, "expected exactly one ADR-0001 file")
        text = adrs[0].read_text(encoding="utf-8")
        self.assertIn("sync", text)
        self.assertIn("no new top-level verbs", text)


if __name__ == "__main__":
    unittest.main()
