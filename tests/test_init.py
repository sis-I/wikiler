"""Tests for init's agent-facing install surface.

`wiki init` is the only command allowed to scaffold. Beyond the directory
tree it installs the runtime rules as AGENTS.md and the four portable skills,
reading both from package data rather than the current working directory.
"""

import os
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path

from wikiler.cli import main

# Kept as a literal so the test is an independent oracle for the contract.
SKILL_NAMES = ("wiki-setup", "wiki-ingest", "wiki-query", "wiki-lint")


def _packaged_bytes(relative):
    return (files("wikiler") / relative).read_bytes()


class TestInitInstallsAgentFiles(unittest.TestCase):
    def test_init_installs_agents_and_skills_from_package(self):
        """Running init from an unrelated cwd reads files from the package."""
        old_cwd = Path.cwd()
        old_env = os.environ.pop("WIKI_VAULT", None)
        try:
            with tempfile.TemporaryDirectory() as tmp, \
                    tempfile.TemporaryDirectory() as elsewhere:
                vault = Path(tmp).resolve()
                os.chdir(elsewhere)
                try:
                    self.assertEqual(main(["--vault", str(vault), "init"]), 0)
                finally:
                    os.chdir(old_cwd)

                agents = vault / "AGENTS.md"
                self.assertTrue(agents.is_file())
                self.assertEqual(
                    agents.read_bytes(), _packaged_bytes("runtime_rules.md")
                )

                for name in SKILL_NAMES:
                    with self.subTest(skill=name):
                        installed = vault / ".agents" / "skills" / name / "SKILL.md"
                        self.assertTrue(installed.is_file())
                        self.assertEqual(
                            installed.read_bytes(),
                            _packaged_bytes(f".agents/skills/{name}/SKILL.md"),
                        )
        finally:
            if old_env is not None:
                os.environ["WIKI_VAULT"] = old_env

    def tearDown(self):
        os.chdir(Path(__file__).resolve().parents[1])


class TestInitPreservesEdits(unittest.TestCase):
    def test_reinit_keeps_edits_and_restores_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp).resolve()
            self.assertEqual(main(["--vault", str(vault), "init"]), 0)

            agents = vault / "AGENTS.md"
            agents.write_text("local rules edit\n", encoding="utf-8")
            edited_skill = (
                vault / ".agents" / "skills" / "wiki-lint" / "SKILL.md"
            )
            edited_skill.write_text("local skill edit\n", encoding="utf-8")
            removed_skill = (
                vault / ".agents" / "skills" / "wiki-query" / "SKILL.md"
            )
            removed_skill.unlink()

            self.assertEqual(main(["--vault", str(vault), "init"]), 0)

            self.assertEqual(agents.read_text(encoding="utf-8"), "local rules edit\n")
            self.assertEqual(
                edited_skill.read_text(encoding="utf-8"), "local skill edit\n"
            )
            self.assertEqual(
                removed_skill.read_bytes(),
                _packaged_bytes(".agents/skills/wiki-query/SKILL.md"),
            )
            log_text = (vault / "wiki" / "log.md").read_text(encoding="utf-8")
            self.assertEqual(log_text.count("setup | Vault initialized"), 1)


if __name__ == "__main__":
    unittest.main()
