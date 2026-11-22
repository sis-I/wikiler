"""Tests for the CLI dispatcher: subcommand routing and vault resolution."""

import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from wikiler.cli import build_parser, main
from wikiler.vault import vault_paths
from wikiler.log import read_log


class TestBuildParser(unittest.TestCase):
    def test_subcommands_registered(self):
        parser = build_parser()
        cases = [
            ("init", ["--vault", "/tmp/x", "init"]),
            ("query", ["--vault", "/tmp/x", "query", "q"]),
            ("lint", ["--vault", "/tmp/x", "lint"]),
            ("ingest", ["--vault", "/tmp/x", "ingest", "some/source.md"]),
            ("sync", ["--vault", "/tmp/x", "sync"]),
        ]
        for expected_cmd, args in cases:
            ns = parser.parse_args(args)
            self.assertEqual(ns.command, expected_cmd)
            self.assertTrue(hasattr(ns, "func"))

    def test_ingest_requires_source(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["--vault", "/tmp/x", "ingest"])

    def test_query_requires_question(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["--vault", "/tmp/x", "query"])

    def test_query_json_flag_parsed(self):
        parser = build_parser()
        ns = parser.parse_args(["--vault", "/tmp/x", "query", "q", "--json"])
        self.assertTrue(ns.json)

    def test_lint_json_flag_parsed(self):
        parser = build_parser()
        ns = parser.parse_args(["--vault", "/tmp/x", "lint", "--json"])
        self.assertTrue(ns.json)

    def test_lint_fix_flag_parsed(self):
        parser = build_parser()
        ns = parser.parse_args(["--vault", "/tmp/x", "lint", "--fix"])
        self.assertTrue(ns.fix)

    def test_ingest_download_images_flag_is_opt_in(self):
        parser = build_parser()
        ns = parser.parse_args(["--vault", "/tmp/x", "ingest", "some/source.md"])
        self.assertFalse(ns.download_images)
        ns = parser.parse_args(
            ["--vault", "/tmp/x", "ingest", "some/source.md", "--download-images"]
        )
        self.assertTrue(ns.download_images)

    def test_ingest_json_and_force_flags_are_parsed(self):
        parser = build_parser()
        ns = parser.parse_args(
            ["--vault", "/tmp/x", "ingest", "some/source.md", "--json", "--force"]
        )
        self.assertTrue(ns.json)
        self.assertTrue(ns.force)

    def test_ingest_help_marks_force_as_destructive(self):
        parser = build_parser()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit):
            parser.parse_args(["ingest", "--help"])
        help_text = buf.getvalue()
        self.assertIn("--force", help_text)
        self.assertIn("destructive", help_text.lower())
        self.assertIn("discard", help_text.lower())

    def test_query_save_flag_removed(self):
        parser = build_parser()
        with contextlib.redirect_stderr(io.StringIO()), \
                self.assertRaises(SystemExit):
            parser.parse_args(["--vault", "/tmp/x", "query", "q", "--save"])

    def test_vault_argument_parsed(self):
        parser = build_parser()
        ns = parser.parse_args(["--vault", "/some/vault", "init"])
        self.assertEqual(ns.vault, "/some/vault")

    def test_short_vault_flag(self):
        parser = build_parser()
        ns = parser.parse_args(["-v", "/some/vault", "init"])
        self.assertEqual(ns.vault, "/some/vault")


class TestMainDispatcher(unittest.TestCase):
    def _run(self, argv):
        """Run main against a fresh temp vault; return (rc, vault_path).

        Uses mkdtemp so the vault persists after _run returns (unlike
        TemporaryDirectory, which deletes on context exit).
        """
        old = os.environ.get("WIKI_VAULT")
        try:
            if "WIKI_VAULT" in os.environ:
                del os.environ["WIKI_VAULT"]
            tmp = tempfile.mkdtemp()
            # global options precede the subcommand in argparse
            argv_full = ["--vault", tmp] + argv
            rc = main(argv_full)
            return rc, tmp
        finally:
            if old is not None:
                os.environ["WIKI_VAULT"] = old

    def _cleanup(self, tmp):
        shutil.rmtree(tmp, ignore_errors=True)

    def test_init_creates_structure_and_log_entry(self):
        rc, tmp = self._run(["init"])
        try:
            self.assertEqual(rc, 0)
            vault = Path(tmp).resolve()
            paths = vault_paths(vault)
            self.assertTrue(paths["root"].exists())
            self.assertTrue(paths["raw"].exists())
            self.assertTrue((paths["wiki"] / "sources").exists())
            self.assertTrue((paths["wiki"] / "entities").exists())
            self.assertTrue((paths["wiki"] / "concepts").exists())
            self.assertTrue((paths["wiki"] / "synthesis").exists())
            self.assertTrue((paths["wiki"] / "queries").exists())
            self.assertTrue(paths["output"].exists())
            self.assertTrue(paths["index"].exists())
            self.assertTrue(paths["log"].exists())
            log_contents = read_log(vault)
            self.assertIn("## [", log_contents)
            self.assertIn("setup | Vault initialized", log_contents)
        finally:
            self._cleanup(tmp)

    def test_init_creates_topic_directories(self):
        rc, tmp = self._run(["init"])
        try:
            self.assertEqual(rc, 0)
            raw = Path(tmp) / "raw"
            for topic in ("articles", "papers", "repos", "datasets"):
                with self.subTest(topic=topic):
                    self.assertTrue(
                        (raw / topic).is_dir(),
                        f"init must create raw/{topic}/",
                    )
            self.assertTrue((raw / "assets").is_dir())
        finally:
            self._cleanup(tmp)

    def test_init_idempotent(self):
        rc, tmp = self._run(["init"])
        try:
            self.assertEqual(rc, 0)
            index_path = Path(tmp) / "wiki" / "index.md"
            index_first = index_path.read_text(encoding="utf-8")
            # Re-run init against the same vault: should not duplicate entries.
            rc2 = main(["--vault", tmp, "init"])
            self.assertEqual(rc2, 0)
            log_contents = read_log(tmp)
            # setup entry appears exactly once (idempotent init)
            self.assertEqual(log_contents.count("setup | Vault initialized"), 1)
            # index.md content is unchanged by the re-run
            self.assertEqual(index_path.read_text(encoding="utf-8"), index_first)
        finally:
            self._cleanup(tmp)

    def test_other_commands_return_zero(self):
        old = os.environ.get("WIKI_VAULT")
        try:
            if "WIKI_VAULT" in os.environ:
                del os.environ["WIKI_VAULT"]
            tmp = tempfile.mkdtemp()
            try:
                self.assertEqual(main(["--vault", tmp, "init"]), 0)
                # ingest needs a real raw source to read.
                article = Path(tmp) / "raw" / "articles" / "x.md"
                article.parent.mkdir(parents=True, exist_ok=True)
                article.write_text("# X\n", encoding="utf-8")
                self.assertEqual(main(["--vault", tmp, "ingest", "articles/x.md"]), 0)
                self.assertEqual(main(["--vault", tmp, "query", "what is pstack?"]), 0)
                self.assertEqual(main(["--vault", tmp, "lint"]), 0)
                self.assertEqual(main(["--vault", tmp, "sync"]), 0)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        finally:
            if old is not None:
                os.environ["WIKI_VAULT"] = old

    def test_env_var_resolves_vault(self):
        old = os.environ.get("WIKI_VAULT")
        try:
            tmp = tempfile.mkdtemp()
            os.environ["WIKI_VAULT"] = tmp
            try:
                rc = main(["init"])
                self.assertEqual(rc, 0)
                self.assertTrue(Path(tmp, "wiki", "index.md").exists())
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        finally:
            if old is None:
                os.environ.pop("WIKI_VAULT", None)
            else:
                os.environ["WIKI_VAULT"] = old

    def test_engine_leaves_raw_untouched(self):
        rc, tmp = self._run(["init"])
        try:
            self.assertEqual(rc, 0)
            raw_dir = Path(tmp) / "raw"
            self.assertTrue(raw_dir.is_dir())
            # raw/ is scaffolded (raw/assets exists as an empty dir) but the engine
            # never adds source files or images to raw/ — raw/ is human-owned
            regular_files = [p for p in raw_dir.rglob("*") if p.is_file()]
            self.assertEqual(regular_files, [])
        finally:
            self._cleanup(tmp)


class TestNonVaultRefusal(unittest.TestCase):
    """Non-init commands must refuse outside a vault and write nothing."""

    def setUp(self):
        self._old_cwd = Path.cwd()
        self._old_env = os.environ.get("WIKI_VAULT")
        os.environ.pop("WIKI_VAULT", None)

    def tearDown(self):
        os.chdir(self._old_cwd)
        if self._old_env is None:
            os.environ.pop("WIKI_VAULT", None)
        else:
            os.environ["WIKI_VAULT"] = self._old_env

    def _run(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(argv)
        return rc, buf.getvalue()

    def test_commands_refuse_and_create_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp).resolve()
            cases = [
                ["ingest", "article.md"],
                ["query", "what is pstack?"],
                ["lint"],
                ["lint", "--fix"],
            ]
            for argv in cases:
                with self.subTest(argv=argv):
                    rc, out = self._run(["--vault", str(vault)] + argv)
                    self.assertEqual(rc, 1)
                    self.assertIn(
                        f"error: not a wiki vault: {vault}", out
                    )
                    self.assertIn("run wiki init first", out)
                    # No directories or files at any depth.
                    self.assertEqual(list(vault.rglob("*")), [])

    def test_cwd_non_vault_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp).resolve()
            os.chdir(vault)
            rc, out = self._run(["lint"])
            self.assertEqual(rc, 1)
            self.assertIn("not a wiki vault", out)
            self.assertEqual(list(vault.rglob("*")), [])

    def test_explicit_non_vault_does_not_fall_back_to_cwd(self):
        with tempfile.TemporaryDirectory() as cwd_tmp, \
                tempfile.TemporaryDirectory() as other_tmp:
            cwd_vault = Path(cwd_tmp).resolve()
            other = Path(other_tmp).resolve()
            self.assertEqual(main(["--vault", str(cwd_vault), "init"]), 0)
            os.chdir(cwd_vault)
            # If --vault fell back to cwd, lint would succeed against cwd_vault.
            rc, out = self._run(["--vault", str(other), "lint"])
            self.assertEqual(rc, 1)
            self.assertIn(f"not a wiki vault: {other}", out)

    def test_json_mode_refusal_goes_to_stderr(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp).resolve()
            out_buf = io.StringIO()
            err_buf = io.StringIO()
            with contextlib.redirect_stdout(out_buf), \
                    contextlib.redirect_stderr(err_buf):
                rc = main(
                    ["--vault", str(vault), "ingest", "article.md", "--json"]
                )
            self.assertEqual(rc, 1)
            self.assertEqual(out_buf.getvalue(), "")
            self.assertIn("not a wiki vault", err_buf.getvalue())


if __name__ == "__main__":
    unittest.main()
