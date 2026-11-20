"""Tests for vault path resolution and structure scaffolding."""

import os
import tempfile
import unittest
from pathlib import Path

from wikiler.vault import (
    resolve_target_vault,
    vault_paths,
    ensure_vault_structure,
    is_within_vault,
    is_vault,
    refusal_for_command,
    VAULT_SUBDIRS,
)


class TestResolveTargetVault(unittest.TestCase):
    def test_explicit_argument_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = resolve_target_vault(tmp)
            self.assertEqual(result, Path(tmp).resolve())

    def test_env_var_used_when_no_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("WIKI_VAULT")
            os.environ["WIKI_VAULT"] = tmp
            try:
                result = resolve_target_vault()
                self.assertEqual(result, Path(tmp).resolve())
            finally:
                if old is None:
                    os.environ.pop("WIKI_VAULT", None)
                else:
                    os.environ["WIKI_VAULT"] = old

    def test_defaults_to_cwd(self):
        old = os.environ.get("WIKI_VAULT")
        cwd = os.getcwd()
        try:
            if "WIKI_VAULT" in os.environ:
                del os.environ["WIKI_VAULT"]
            result = resolve_target_vault()
            self.assertEqual(result, Path(cwd).resolve())
        finally:
            if old is not None:
                os.environ["WIKI_VAULT"] = old


class TestVaultPaths(unittest.TestCase):
    def test_returns_expected_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolved = Path(tmp).resolve()
            paths = vault_paths(resolved)
            expected = {
                "root", "raw", "raw_assets", "wiki", "wiki_sources",
                "wiki_entities", "wiki_concepts", "wiki_synthesis",
                "wiki_queries", "output", "index", "log",
            }
            self.assertEqual(set(paths.keys()), expected)
            self.assertEqual(paths["root"], Path(tmp).resolve())
            self.assertEqual(paths["index"], Path(tmp).resolve() / "wiki" / "index.md")
            self.assertEqual(paths["log"], Path(tmp).resolve() / "wiki" / "log.md")


class TestEnsureVaultStructure(unittest.TestCase):
    def test_creates_all_subdirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault_structure(tmp)
            self.assertTrue(vault.exists())
            for rel in VAULT_SUBDIRS:
                self.assertTrue((vault / rel).exists(), f"missing {rel}")
            # raw exists but is empty (engine never populates it)
            self.assertTrue((vault / "raw").is_dir())

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            ensure_vault_structure(tmp)  # second call should not raise
            for rel in VAULT_SUBDIRS:
                self.assertTrue((Path(tmp) / rel).exists())


class TestIsVault(unittest.TestCase):
    def test_empty_directory_is_not_a_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(is_vault(tmp))

    def test_scaffolded_dirs_without_markers_are_not_a_vault(self):
        # A bare directory tree is not enough: init must have created a marker.
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self.assertFalse(is_vault(tmp))

    def test_index_marker_identifies_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp).resolve()
            (vault / "wiki").mkdir()
            (vault / "wiki" / "index.md").write_text("# Wiki Index\n", encoding="utf-8")
            self.assertTrue(is_vault(vault))

    def test_log_marker_identifies_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp).resolve()
            (vault / "wiki").mkdir()
            (vault / "wiki" / "log.md").write_text("# Wiki Log\n", encoding="utf-8")
            self.assertTrue(is_vault(vault))


class TestRefusalForCommand(unittest.TestCase):
    def test_init_allowed_in_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(refusal_for_command("init", tmp))

    def test_non_init_commands_refuse_in_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp).resolve()
            expected = (
                f"error: not a wiki vault: {vault} "
                "(run wiki init first)"
            )
            for command in ("ingest", "query", "lint", "sync"):
                with self.subTest(command=command):
                    self.assertEqual(refusal_for_command(command, vault), expected)

    def test_non_init_commands_allowed_in_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp).resolve()
            (vault / "wiki").mkdir()
            (vault / "wiki" / "index.md").write_text("# Wiki Index\n", encoding="utf-8")
            for command in ("ingest", "query", "lint", "sync"):
                with self.subTest(command=command):
                    self.assertIsNone(refusal_for_command(command, vault))


class TestIsWithinVault(unittest.TestCase):
    def test_inside_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.assertTrue(is_within_vault(base / "wiki" / "index.md", base))
            self.assertTrue(is_within_vault(base / "raw" / "assets" / "x.jpg", base))

    def test_outside_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            outside = base.parent / "outside.md"
            self.assertFalse(is_within_vault(outside, base))
