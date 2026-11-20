"""Tests for the query command: ranked retrieval candidates, not answers."""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from wikiler.cli import main
from wikiler.vault import vault_paths
from wikiler.commands.query import (
    SNIPPET_LIMIT,
    _keywords,
    _find_relevant_pages,
    _snippet,
)


class TestKeywords(unittest.TestCase):
    def test_extracts_lowercase_tokens(self):
        self.assertEqual(_keywords("What is pstack?"), ["what", "pstack"])

    def test_drops_short_tokens(self):
        self.assertEqual(_keywords("a vs b of pstack"), ["pstack"])


class TestFindRelevantPages(unittest.TestCase):
    INDEX = """# Wiki Index

Content catalog, one line per page, categorized.

## Sources
- [[sources/pstack|Pstack Intro]]: a sampling profiler for Python.
- [[sources/py-spy-vs-pstack|Py-spy vs pstack]]: pstack compared with py-spy.
- [[sources/unrelated|Unrelated Topic]]: nothing to see here.

## Entities
- [[Pstack]]: short-form link (should be skipped)
"""

    def test_matches_keyword_against_index_entries(self):
        matched = _find_relevant_pages(self.INDEX, "pstack profiler")
        self.assertEqual(
            matched,
            [("sources/pstack", "Pstack Intro"),
             ("sources/py-spy-vs-pstack", "Py-spy vs pstack")],
        )

    def test_skips_short_form_links(self):
        matched = _find_relevant_pages(self.INDEX, "Pstack")
        targets = [t for t, _ in matched]
        self.assertNotIn("Pstack", targets)

    def test_returns_empty_when_nothing_matches(self):
        self.assertEqual(_find_relevant_pages(self.INDEX, "zzzznothing"), [])

    def test_deduplicates_repeated_matches(self):
        matched = _find_relevant_pages(self.INDEX, "pstack pstack")
        self.assertEqual(len(matched), 2)

    def test_ranks_pages_matching_more_keywords_first(self):
        index = """# Wiki Index
- [[sources/one|One]]: sampling profiler.
- [[sources/two|Two]]: sampling profiler for Python programs.
"""
        matched = _find_relevant_pages(index, "sampling profiler python")
        self.assertEqual(
            matched,
            [("sources/two", "Two"), ("sources/one", "One")],
        )

    def test_accepts_path_only_links(self):
        index = "# Wiki Index\n- [[sources/path-only]]: a sampling profiler.\n"
        self.assertEqual(
            _find_relevant_pages(index, "sampling profiler"),
            [("sources/path-only", "")],
        )

    def test_normalises_wiki_prefixed_targets(self):
        index = "# Wiki Index\n- [[wiki/sources/foo|Foo]]: a sampling profiler.\n"
        self.assertEqual(
            _find_relevant_pages(index, "sampling profiler"),
            [("sources/foo", "Foo")],
        )


class TestSnippet(unittest.TestCase):
    def test_returns_first_paragraph(self):
        text = "# Title\n\nThis is the first paragraph about pstack.\n\nSecond paragraph.\n"
        self.assertEqual(_snippet(text), "This is the first paragraph about pstack.")

    def test_skips_headings(self):
        text = "# Title\n\n## A Heading\n\nReal body text here about pstack tools.\n"
        self.assertEqual(_snippet(text), "Real body text here about pstack tools.")

    def test_skips_frontmatter(self):
        text = (
            "---\ntype: concept\ntitle: Pstack\n---\n\n"
            "# Pstack\n\nA sampling profiler for Python.\n"
        )
        self.assertEqual(_snippet(text), "A sampling profiler for Python.")

    def test_skips_source_metadata_and_todo_blocks(self):
        text = (
            "# Pstack Intro\n\n"
            "## Source metadata\n\n"
            "- **Source file:** pstack.md\n\n"
            "## Key claims\n\n"
            "<!-- TODO: agent — extract and phrase the key claims -->\n\n"
            "## Structured summary\n\n"
            "pstack samples stack traces of running Python processes.\n"
        )
        self.assertEqual(
            _snippet(text),
            "pstack samples stack traces of running Python processes.",
        )

    def test_skips_tables(self):
        text = (
            "# Title\n\n"
            "| Question | Answer |\n|---|---|\n| Why? | Because. |\n\n"
            "A real paragraph about pstack.\n"
        )
        self.assertEqual(_snippet(text), "A real paragraph about pstack.")

    def test_truncates_long_paragraphs(self):
        text = "# Title\n\n" + ("word " * 100).strip() + "\n"
        snippet = _snippet(text)
        self.assertLessEqual(len(snippet), SNIPPET_LIMIT + 1)  # + ellipsis
        self.assertTrue(snippet.endswith("…"))

    def test_empty_when_no_body(self):
        self.assertEqual(_snippet("# Title\n"), "")


class TestQueryE2E(unittest.TestCase):
    def _setup(self):
        old = os.environ.get("WIKI_VAULT")
        if "WIKI_VAULT" in os.environ:
            del os.environ["WIKI_VAULT"]
        tmp = tempfile.mkdtemp()
        return tmp, old

    def _teardown(self, tmp, old):
        shutil.rmtree(tmp, ignore_errors=True)
        if old is None:
            os.environ.pop("WIKI_VAULT", None)
        else:
            os.environ["WIKI_VAULT"] = old

    def _run(self, tmp, argv, capture=False):
        argv_full = ["--vault", tmp] + argv
        if capture:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(argv_full)
            return rc, buf.getvalue()
        return main(argv_full), ""

    def _seed(self, tmp, authored_body=None):
        """Init, ingest one source, and optionally author a paragraph."""
        self.assertEqual(main(["--vault", tmp, "init"]), 0)
        vault = Path(tmp).resolve()
        raw_dir = vault / "raw"
        source = raw_dir / "pstack.md"
        source.write_text(
            "# Pstack Intro\n\n"
            "pstack is a sampling profiler for Python programs.\n",
            encoding="utf-8",
        )
        self.assertEqual(main(["--vault", tmp, "ingest", "pstack.md"]), 0)

        page = vault / "wiki" / "sources" / "pstack-intro.md"
        if authored_body is not None:
            text = page.read_text(encoding="utf-8")
            text = text.replace(
                "<!-- TODO: agent — extract and phrase the key claims -->",
                authored_body,
            )
            page.write_text(text, encoding="utf-8")
        return vault, source, page

    def test_query_uninitialized_vault_errors(self):
        tmp, old = self._setup()
        try:
            rc, out = self._run(tmp, ["query", "pstack"], capture=True)
            self.assertNotEqual(rc, 0)
            self.assertIn("not a wiki vault", out)
            self.assertIn("run wiki init first", out)
        finally:
            self._teardown(tmp, old)

    def test_query_missing_index_errors(self):
        tmp, old = self._setup()
        try:
            self.assertEqual(main(["--vault", tmp, "init"]), 0)
            (Path(tmp) / "wiki" / "index.md").unlink()
            rc, out = self._run(tmp, ["query", "pstack"], capture=True)
            self.assertEqual(rc, 1)
            self.assertIn("wiki/index.md not found", out)
        finally:
            self._teardown(tmp, old)

    def test_query_no_matches_returns_zero(self):
        tmp, old = self._setup()
        try:
            self.assertEqual(main(["--vault", tmp, "init"]), 0)
            rc, out = self._run(tmp, ["query", "zzzznothing"], capture=True)
            self.assertEqual(rc, 0)
            self.assertIn("No wiki pages matched", out)
        finally:
            self._teardown(tmp, old)

    def test_query_prints_ranked_candidates_with_snippets(self):
        tmp, old = self._setup()
        try:
            body = "pstack captures stack traces of running Python processes."
            vault, source, _page = self._seed(tmp, authored_body=body)
            original = source.read_text(encoding="utf-8")

            rc, out = self._run(tmp, ["query", "pstack profiler"], capture=True)

            self.assertEqual(rc, 0)
            self.assertIn("[[sources/pstack-intro|Pstack Intro]]", out)
            self.assertIn("path: wiki/sources/pstack-intro.md", out)
            self.assertIn(f"snippet: {body}", out)

            # Retrieval only: no answer, no offer to save, no synthesis page.
            self.assertNotIn("Cited:", out)
            self.assertNotIn("saved synthesis artifact", out)
            self.assertEqual(
                list((vault / "wiki" / "synthesis").glob("*.md")), []
            )

            # raw/ untouched.
            self.assertEqual(source.read_text(encoding="utf-8"), original)
        finally:
            self._teardown(tmp, old)

    def test_query_json_returns_matches_with_snippets(self):
        tmp, old = self._setup()
        try:
            body = "pstack captures stack traces of running Python processes."
            _vault, _source, _page = self._seed(tmp, authored_body=body)

            rc, out = self._run(
                tmp, ["query", "pstack profiler", "--json"], capture=True
            )

            self.assertEqual(rc, 0)
            payload = json.loads(out)
            self.assertEqual(payload["question"], "pstack profiler")
            self.assertEqual(len(payload["matches"]), 1)
            match = payload["matches"][0]
            self.assertEqual(
                set(match), {"target", "title", "path", "snippet"}
            )
            self.assertEqual(match["target"], "sources/pstack-intro")
            self.assertEqual(match["title"], "Pstack Intro")
            self.assertEqual(match["path"], "wiki/sources/pstack-intro.md")
            self.assertEqual(match["snippet"], body)
        finally:
            self._teardown(tmp, old)

    def test_query_json_no_matches_returns_empty_list(self):
        tmp, old = self._setup()
        try:
            self.assertEqual(main(["--vault", tmp, "init"]), 0)
            rc, out = self._run(
                tmp, ["query", "zzzznothing", "--json"], capture=True
            )
            self.assertEqual(rc, 0)
            self.assertEqual(
                json.loads(out), {"question": "zzzznothing", "matches": []}
            )
        finally:
            self._teardown(tmp, old)

    def test_query_scaffold_page_prints_empty_snippet_field(self):
        tmp, old = self._setup()
        try:
            # No authored body: every scaffold block is skipped.
            self._seed(tmp)
            rc, out = self._run(tmp, ["query", "pstack"], capture=True)
            self.assertEqual(rc, 0)
            self.assertTrue(
                any(line.strip() == "snippet:" for line in out.splitlines())
            )
        finally:
            self._teardown(tmp, old)

    def test_query_resolves_title_for_path_only_wiki_prefixed_entry(self):
        tmp, old = self._setup()
        try:
            vault, _source, _page = self._seed(tmp, authored_body="pstack body.")
            index_path = vault / "wiki" / "index.md"
            index = index_path.read_text(encoding="utf-8")
            index = index.replace(
                "[[sources/pstack-intro|Pstack Intro]]",
                "[[wiki/sources/pstack-intro]]",
            )
            index_path.write_text(index, encoding="utf-8")

            rc, out = self._run(tmp, ["query", "pstack", "--json"], capture=True)

            self.assertEqual(rc, 0)
            match = json.loads(out)["matches"][0]
            self.assertEqual(match["target"], "sources/pstack-intro")
            self.assertEqual(match["title"], "Pstack Intro")
            self.assertEqual(match["path"], "wiki/sources/pstack-intro.md")
        finally:
            self._teardown(tmp, old)

    def test_query_does_not_touch_index_or_log(self):
        tmp, old = self._setup()
        try:
            vault, _source, _page = self._seed(tmp, authored_body="pstack body.")
            paths = vault_paths(vault)
            index_before = paths["index"].read_text(encoding="utf-8")
            log_before = paths["log"].read_text(encoding="utf-8")

            self._run(tmp, ["query", "pstack"], capture=True)

            self.assertEqual(
                paths["index"].read_text(encoding="utf-8"), index_before
            )
            self.assertEqual(paths["log"].read_text(encoding="utf-8"), log_before)
        finally:
            self._teardown(tmp, old)


if __name__ == "__main__":
    unittest.main()
