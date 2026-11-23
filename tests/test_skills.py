"""Contract tests for the four portable wiki skills.

The skills are the agent-facing surface of the wiki CLI. These tests hold the
portable contract steady: minimal frontmatter, a discovery trigger in each
description, a short body with one vault-rules pointer, and byte-identical
copies at the repo root and inside the installed package.
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_SKILLS = REPO_ROOT / ".agents" / "skills"
PACKAGED_SKILLS = REPO_ROOT / "src" / "wikiler" / ".agents" / "skills"
# Kept as a literal so the test is an independent oracle for the contract.
SKILL_NAMES = ("wiki-setup", "wiki-ingest", "wiki-query", "wiki-lint")
FORBIDDEN_FRONTMATTER = {"license", "compatibility", "metadata", "allowed-tools"}


def _iter_skill_paths():
    """Yield (base, name, SKILL.md path) for both installed copies."""
    for base in (ROOT_SKILLS, PACKAGED_SKILLS):
        for name in SKILL_NAMES:
            yield base, name, base / name / "SKILL.md"


def _split_frontmatter(text):
    """Return (frontmatter_lines, body_text) from a SKILL.md document."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError("SKILL.md must start with a --- frontmatter fence")
    end = next(
        (i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if end is None:
        raise AssertionError("SKILL.md frontmatter fence is never closed")
    return lines[1:end], "\n".join(lines[end + 1:])


class TestSkillFrontmatter(unittest.TestCase):
    def test_each_skill_has_minimal_frontmatter_and_trigger(self):
        for base, name, path in _iter_skill_paths():
            with self.subTest(base=str(base), skill=name):
                self.assertTrue(path.is_file(), f"missing {path}")
                frontmatter, body = _split_frontmatter(
                    path.read_text(encoding="utf-8")
                )
                keys = {
                    line.split(":", 1)[0].strip()
                    for line in frontmatter
                    if ":" in line
                }
                self.assertEqual(keys, {"name", "description"})
                self.assertFalse(keys & FORBIDDEN_FRONTMATTER)

                description = " ".join(
                    line.split(":", 1)[1].strip()
                    for line in frontmatter
                    if line.startswith("description:")
                )
                self.assertIn("Use when", description)

                skill_name = " ".join(
                    line.split(":", 1)[1].strip()
                    for line in frontmatter
                    if line.startswith("name:")
                )
                self.assertEqual(skill_name, name)

                self.assertLess(len(body.splitlines()), 500)
                self.assertEqual(body.count("<vault>/AGENTS.md"), 1)
                self.assertNotIn("disable-model-invocation", body)
                self.assertNotIn("autoinvoke", body)

    def test_no_references_directories(self):
        for base, name, _ in _iter_skill_paths():
            with self.subTest(base=str(base), skill=name):
                self.assertFalse((base / name / "references").exists())


class TestSkillCopiesIdentical(unittest.TestCase):
    def test_repo_root_and_packaged_skills_are_byte_identical(self):
        for name in SKILL_NAMES:
            with self.subTest(skill=name):
                root = (ROOT_SKILLS / name / "SKILL.md").read_bytes()
                packaged = (PACKAGED_SKILLS / name / "SKILL.md").read_bytes()
                self.assertEqual(root, packaged)

    def test_dash_rule_in_skill_prose(self):
        # Em dashes and en dashes are banned as punctuation in repo prose.
        # CLI flags such as --json are technical syntax and are exempt.
        for name in SKILL_NAMES:
            with self.subTest(skill=name):
                text = (ROOT_SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
                self.assertNotIn("\u2014", text)
                self.assertNotIn("\u2013", text)


if __name__ == "__main__":
    unittest.main()
