"""Tests for the shared wiki log helpers."""

import os
import tempfile
import unittest
from pathlib import Path

from wikiler.log import (
    today,
    format_log_entry,
    append_log_entry,
    read_log,
)
from wikiler.vault import vault_paths


class TestFormatLogEntry(unittest.TestCase):
    def test_format_matches_contract(self):
        entry = format_log_entry("ingest", "GBrain", entry_date="2026-10-29")
        self.assertEqual(entry, "## [2026-10-29] ingest | GBrain")

    def test_uses_today_when_no_date(self):
        entry = format_log_entry("lint", "Wiki health check")
        self.assertTrue(entry.startswith("## [" + today() + "] lint | Wiki health check"))


class TestAppendLogEntry(unittest.TestCase):
    def test_appends_entry_and_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            append_log_entry(vault, "ingest", "LLM Wiki", entry_date="2026-10-29")
            log_path = vault_paths(vault)["log"]
            self.assertTrue(log_path.exists())
            contents = log_path.read_text(encoding="utf-8")
            self.assertIn("## [2026-10-29] ingest | LLM Wiki", contents)

    def test_append_only_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            append_log_entry(vault, "ingest", "First", entry_date="2026-10-01")
            append_log_entry(vault, "lint", "Second", entry_date="2026-10-02")
            contents = read_log(vault)
            self.assertIn("## [2026-10-01] ingest | First", contents)
            self.assertIn("## [2026-10-02] lint | Second", contents)
            # First entry still present (append-only)
            first_idx = contents.index("## [2026-10-01]")
            second_idx = contents.index("## [2026-10-02]")
            self.assertLess(first_idx, second_idx)

    def test_read_log_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            self.assertEqual(read_log(vault), "")
