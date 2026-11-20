import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from wikiler.cli import main
from wikiler.lint import fix_vault, lint_vault
from wikiler.vault import ensure_vault_structure


class TestLintFix(unittest.TestCase):
    def setUp(self):
        self.vault = Path(tempfile.mkdtemp()).resolve()
        ensure_vault_structure(self.vault)
        self.wiki_dir = self.vault / "wiki"
        self.concepts_dir = self.wiki_dir / "concepts"

    def tearDown(self):
        shutil.rmtree(self.vault, ignore_errors=True)

    def write_page(
        self,
        relative,
        title,
        h1=None,
        page_type="concept",
        extra_frontmatter="",
        body="",
    ):
        path = self.vault / "wiki" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        heading = h1 or title
        extra = f"{extra_frontmatter}\n" if extra_frontmatter else ""
        text = (
            "---\n"
            f"type: {page_type}\n"
            f"title: {title}\n"
            "sources: []\n"
            "created: 2023-01-01\n"
            "updated: 2023-01-01\n"
            "tags: []\n"
            f"{extra}"
            "---\n"
            f"# {heading}\n"
            f"{body}"
        )
        path.write_text(text, encoding="utf-8")
        return path

    def write_markers(self):
        index_path = self.wiki_dir / "index.md"
        index_path.write_text("# Index\n", encoding="utf-8")
        log_path = self.wiki_dir / "log.md"
        log_path.write_text("# Log\n", encoding="utf-8")
        return index_path, log_path

    def run_cli(self, *arguments):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            return_code = main([
                "--vault",
                str(self.vault),
                "lint",
                *arguments,
            ])
        return return_code, output.getvalue()

    def test_fix_short_form_wikilink(self):
        target = self.write_page("concepts/target-page.md", "Target Page")
        linker = self.write_page(
            "concepts/linker.md",
            "Linker",
            body="See [[target-page]]",
        )

        fix_vault(self.vault)

        content = linker.read_text(encoding="utf-8")
        self.assertIn("[[concepts/target-page|Target Page]]", content)
        self.assertTrue(target.is_file())

    def test_fix_rewrites_title_style_link_and_preserves_display(self):
        self.write_page(
            "concepts/foo.md",
            "Foo",
            h1="Foo (concept)",
        )
        linker = self.write_page(
            "concepts/linker.md",
            "Linker",
            body="See [[Foo (concept)]]",
        )

        fix_vault(self.vault)

        content = linker.read_text(encoding="utf-8")
        self.assertIn("[[concepts/foo|Foo (concept)]]", content)

    def test_fix_preserves_frontmatter_and_existing_display_verbatim(self):
        self.write_page("concepts/foo.md", "Foo")
        linker = self.write_page(
            "concepts/linker.md",
            "Linker",
            extra_frontmatter="owner: agent\nreview: pending",
            body="See [[foo|Foo (concept)]]",
        )
        before = linker.read_text(encoding="utf-8")
        before_frontmatter = before.split("---\n", 2)[1]

        fix_vault(self.vault)

        after = linker.read_text(encoding="utf-8")
        self.assertEqual(after.split("---\n", 2)[1], before_frontmatter)
        self.assertIn("owner: agent", after)
        self.assertIn("review: pending", after)
        self.assertIn("[[concepts/foo|Foo (concept)]]", after)

    def test_fix_uses_display_type_to_resolve_duplicate_stems(self):
        self.write_page(
            "entities/pi-durable.md",
            "Pi Durable",
            h1="Pi Durable (entity)",
            page_type="entity",
        )
        self.write_page(
            "sources/pi-durable.md",
            "Pi Durable",
            page_type="source",
        )
        linker = self.write_page(
            "concepts/linker.md",
            "Linker",
            body=(
                "Entity: [[pi-durable|Pi Durable (entity)]]\n"
                "Source: [[pi-durable|Pi Durable (source)]]"
            ),
        )

        fix_vault(self.vault)

        content = linker.read_text(encoding="utf-8")
        self.assertIn(
            "[[entities/pi-durable|Pi Durable (entity)]]",
            content,
        )
        self.assertIn(
            "[[sources/pi-durable|Pi Durable (source)]]",
            content,
        )

    def test_fix_leaves_contradictory_display_untouched_and_reports_it(self):
        self.write_page("concepts/foo.md", "Foo")
        linker = self.write_page(
            "concepts/linker.md",
            "Linker",
            body="See [[foo|Wrong Title]]",
        )

        fix_vault(self.vault)

        content = linker.read_text(encoding="utf-8")
        self.assertIn("[[foo|Wrong Title]]", content)
        result = lint_vault(self.vault)
        self.assertTrue(any(
            "display text" in finding.message
            and "does not match" in finding.message
            for finding in result.warnings
        ))

    def test_fix_rewrites_unambiguous_link_in_index(self):
        self.write_page("concepts/foo.md", "Foo")
        index_path = self.wiki_dir / "index.md"
        index_path.write_text("# Index\n\n- [[Foo]]\n", encoding="utf-8")

        result = fix_vault(self.vault)

        self.assertIn(
            "- [[concepts/foo|Foo]]",
            index_path.read_text(encoding="utf-8"),
        )
        self.assertIn("wiki/index.md", result.files_changed)

    def test_fix_leaves_unmatched_link_untouched_and_reports_it(self):
        linker = self.write_page(
            "concepts/linker.md",
            "Linker",
            body="See [[Missing Page]]",
        )

        fix_vault(self.vault)

        content = linker.read_text(encoding="utf-8")
        self.assertIn("[[Missing Page]]", content)
        result = lint_vault(self.vault)
        self.assertTrue(any(
            "broken link" in finding.message
            for finding in result.errors
        ))

    def test_fix_removes_and_reports_dangling_index_entry(self):
        self.write_page("concepts/kept.md", "Kept")
        index_path = self.wiki_dir / "index.md"
        index_path.write_text(
            "# Index\n\n"
            "- [[concepts/kept|Kept]]\n"
            "- [[concepts/gone|Gone]]\n",
            encoding="utf-8",
        )

        result = fix_vault(self.vault)

        index = index_path.read_text(encoding="utf-8")
        self.assertIn("[[concepts/kept|Kept]]", index)
        self.assertNotIn("[[concepts/gone|Gone]]", index)
        self.assertEqual(
            [entry.target for entry in result.index_entries_removed],
            ["concepts/gone"],
        )

    def test_fix_logs_only_when_changed_and_at_most_once_per_day(self):
        self.write_page("concepts/foo.md", "Foo")
        self.write_page(
            "concepts/linker.md",
            "Linker",
            body="See [[foo]]",
        )

        first = fix_vault(self.vault, entry_date="2026-11-11")

        self.assertTrue(first.log_written)
        log_path = self.wiki_dir / "log.md"
        self.assertEqual(log_path.read_text(encoding="utf-8").count("lint |"), 1)

        second = fix_vault(self.vault, entry_date="2026-11-11")

        self.assertFalse(second.changed)
        self.assertFalse(second.log_written)
        self.assertEqual(log_path.read_text(encoding="utf-8").count("lint |"), 1)

        self.write_page("concepts/bar.md", "Bar")
        self.write_page(
            "concepts/second-linker.md",
            "Second Linker",
            body="See [[bar]]",
        )

        third = fix_vault(self.vault, entry_date="2026-11-11")

        self.assertTrue(third.changed)
        self.assertFalse(third.log_written)
        self.assertEqual(log_path.read_text(encoding="utf-8").count("lint |"), 1)

    def test_cli_reports_changed_files_and_rewritten_links(self):
        self.write_page("concepts/foo.md", "Foo")
        self.write_page(
            "concepts/linker.md",
            "Linker",
            body="See [[foo]]",
        )
        self.write_markers()

        return_code, report = self.run_cli("--fix")

        self.assertEqual(return_code, 0)
        self.assertIn("Files changed:", report)
        self.assertIn("wiki/concepts/linker.md", report)
        self.assertIn("Links rewritten:", report)
        self.assertIn("[[foo]]", report)
        self.assertIn("[[concepts/foo|Foo]]", report)

    def test_cli_json_reports_fixes(self):
        self.write_page("concepts/foo.md", "Foo")
        self.write_page(
            "concepts/linker.md",
            "Linker",
            body="See [[foo]]",
        )
        self.write_markers()

        return_code, output = self.run_cli("--fix", "--json")

        data = json.loads(output)
        self.assertEqual(return_code, 0)
        self.assertIn("wiki/concepts/linker.md", data["fixes"]["files_changed"])
        self.assertEqual(
            data["fixes"]["links_rewritten"][0]["original"],
            "[[foo]]",
        )
        self.assertEqual(
            data["fixes"]["links_rewritten"][0]["replacement"],
            "[[concepts/foo|Foo]]",
        )

    def test_second_cli_fix_on_clean_wiki_changes_nothing(self):
        target = self.write_page("concepts/foo.md", "Foo")
        linker = self.write_page(
            "concepts/linker.md",
            "Linker",
            body="See [[foo]]",
        )
        index_path, log_path = self.write_markers()

        first_return_code, _first_output = self.run_cli("--fix")
        before = {
            path: path.read_bytes()
            for path in (index_path, log_path, linker, target)
        }

        second_return_code, second_output = self.run_cli("--fix")

        self.assertEqual(first_return_code, 0)
        self.assertEqual(second_return_code, 0)
        self.assertIn("No fixes applied.", second_output)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_fix_does_not_add_missing_index_entry(self):
        self.write_page("concepts/new-page.md", "New Page")
        index_path = self.wiki_dir / "index.md"
        index_path.write_text("# Index\n\n## Concepts\n", encoding="utf-8")

        fix_vault(self.vault)

        index_content = index_path.read_text(encoding="utf-8")
        self.assertNotIn("[[concepts/new-page|New Page]]", index_content)

    def test_fix_does_not_log_when_nothing_changed(self):
        log_path = self.wiki_dir / "log.md"
        if log_path.exists():
            log_path.unlink()

        fix_vault(self.vault)

        self.assertFalse(log_path.exists())


if __name__ == "__main__":
    unittest.main()
