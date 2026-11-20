"""Tests for the sync verb: index reconciliation, frontmatter and log."""

import shutil
import tempfile
import unittest
from pathlib import Path

from wikiler.cli import main
from wikiler.commands.sync import sync_vault
from wikiler.page import parse_frontmatter, update_index

INDEX_TEMPLATE = """# Wiki Index

Content catalog — one line per page, categorized.

## Sources

## Entities

## Concepts

## Synthesis

## Queries
"""

LOG_TEMPLATE = "# Wiki Log\n\nAppend-only timeline.\n\n"

PAGE_TEMPLATE = """---
type: {type}
title: {title}
sources: []
created: {created}
updated: {updated}
tags: []
---

# {h1}
"""


class SyncTestCase(unittest.TestCase):
    def setUp(self):
        self.vault = Path(tempfile.mkdtemp()).resolve()
        (self.vault / "wiki" / "concepts").mkdir(parents=True)
        (self.vault / "wiki" / "entities").mkdir(parents=True)
        (self.vault / "wiki" / "sources").mkdir(parents=True)
        (self.vault / "wiki" / "synthesis").mkdir(parents=True)
        (self.vault / "wiki" / "queries").mkdir(parents=True)
        self.index_path = self.vault / "wiki" / "index.md"
        self.log_path = self.vault / "wiki" / "log.md"
        self.index_path.write_text(INDEX_TEMPLATE, encoding="utf-8")
        self.log_path.write_text(LOG_TEMPLATE, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.vault, ignore_errors=True)

    def write_page(self, rel, text):
        path = self.vault / "wiki" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def page(self, rel, **overrides):
        fields = dict(
            type="concept",
            title="Foo Page",
            created="2020-01-01",
            updated="2020-01-02",
            h1="Foo Page",
        )
        fields.update(overrides)
        return PAGE_TEMPLATE.format(**fields)

    def drop_key(self, text, key):
        return "\n".join(
            line for line in text.splitlines() if not line.startswith(f"{key}:")
        ) + "\n"


class TestSyncIndex(SyncTestCase):
    def test_appends_missing_index_entries(self):
        self.write_page("concepts/foo-page.md", self.page("concepts/foo-page.md"))

        result = sync_vault(self.vault, entry_date="2026-11-11")

        index = self.index_path.read_text(encoding="utf-8")
        self.assertIn("- [[concepts/foo-page|Foo Page]]", index)
        self.assertEqual(result.index_added, ["concepts/foo-page"])
        # The entry lands under its category section.
        self.assertLess(
            index.index("## Concepts"), index.index("[[concepts/foo-page|Foo Page]]")
        )

    def test_writes_no_index_change_when_every_page_is_listed(self):
        self.write_page("concepts/foo-page.md", self.page("concepts/foo-page.md"))
        update_index(self.vault)
        before = self.index_path.read_text(encoding="utf-8")

        result = sync_vault(self.vault, entry_date="2026-11-11")

        self.assertEqual(result.index_added, [])
        self.assertEqual(self.index_path.read_text(encoding="utf-8"), before)

    def test_recognises_non_canonical_index_link_forms(self):
        self.write_page("concepts/foo-page.md", self.page("concepts/foo-page.md"))
        self.index_path.write_text(
            INDEX_TEMPLATE + "\n- [[wiki/concepts/foo-page|Foo Page]]\n",
            encoding="utf-8",
        )

        result = sync_vault(self.vault, entry_date="2026-11-11")

        self.assertEqual(result.index_added, [])
        self.assertEqual(
            self.index_path.read_text(encoding="utf-8").count("concepts/foo-page"),
            1,
        )

    def test_reports_dangling_index_entries_without_deleting(self):
        self.index_path.write_text(
            INDEX_TEMPLATE + "\n- [[concepts/gone-page|Gone Page]]\n",
            encoding="utf-8",
        )

        result = sync_vault(self.vault, entry_date="2026-11-11")

        self.assertIn("concepts/gone-page", result.dangling)
        self.assertIn(
            "[[concepts/gone-page|Gone Page]]",
            self.index_path.read_text(encoding="utf-8"),
        )


class TestSyncFrontmatter(SyncTestCase):
    def test_quotes_unquoted_colon_values(self):
        self.write_page(
            "concepts/foo-page.md",
            self.page("concepts/foo-page.md", title="Foo: Bar", h1="Foo: Bar"),
        )

        sync_vault(self.vault, entry_date="2026-11-11")

        text = (self.vault / "wiki/concepts/foo-page.md").read_text(encoding="utf-8")
        self.assertIn('title: "Foo: Bar"', text)
        self.assertEqual(parse_frontmatter(text)["title"], "Foo: Bar")

    def test_quotes_indicator_and_comment_values(self):
        self.write_page(
            "concepts/foo-page.md",
            self.page(
                "concepts/foo-page.md",
                title="*Emphasis Page",
                h1="*Emphasis Page",
            ),
        )
        self.write_page(
            "concepts/bar-page.md",
            self.page("concepts/bar-page.md", title="Bar #note", h1="Bar #note"),
        )

        sync_vault(self.vault, entry_date="2026-11-11")

        foo = (self.vault / "wiki/concepts/foo-page.md").read_text(encoding="utf-8")
        bar = (self.vault / "wiki/concepts/bar-page.md").read_text(encoding="utf-8")
        self.assertIn('title: "*Emphasis Page"', foo)
        self.assertIn('title: "Bar #note"', bar)

    def test_preserves_unknown_frontmatter_keys_and_order(self):
        text = self.page("concepts/foo-page.md").replace(
            "tags: []", "tags: []\nowner: agent\nreview: pending"
        )
        self.write_page("concepts/foo-page.md", text)

        sync_vault(self.vault, entry_date="2026-11-11")

        result = (self.vault / "wiki/concepts/foo-page.md").read_text(encoding="utf-8")
        self.assertIn("owner: agent", result)
        self.assertIn("review: pending", result)
        self.assertLess(result.index("owner: agent"), result.index("review: pending"))

    def test_sets_created_only_when_absent(self):
        text = self.drop_key(self.page("concepts/foo-page.md"), "created")
        self.write_page("concepts/foo-page.md", text)

        sync_vault(self.vault, entry_date="2026-11-11")
        after_first = (self.vault / "wiki/concepts/foo-page.md").read_text(encoding="utf-8")
        self.assertIn("created: 2026-11-11", after_first)

        # A later change must not reset created.
        after_first = after_first.replace("title: Foo Page", 'title: "Foo: Page"')
        (self.vault / "wiki/concepts/foo-page.md").write_text(
            after_first, encoding="utf-8"
        )
        sync_vault(self.vault, entry_date="2026-11-12")
        after_second = (self.vault / "wiki/concepts/foo-page.md").read_text(encoding="utf-8")
        self.assertIn("created: 2026-11-11", after_second)

    def test_refreshes_updated_only_when_the_page_changed(self):
        self.write_page(
            "concepts/foo-page.md",
            self.page("concepts/foo-page.md", title="Foo: Bar", h1="Foo: Bar"),
        )

        sync_vault(self.vault, entry_date="2026-11-11")
        changed = (self.vault / "wiki/concepts/foo-page.md").read_text(encoding="utf-8")
        self.assertIn("created: 2020-01-01", changed)
        self.assertIn("updated: 2026-11-11", changed)

        # Nothing left to normalise: updated must stay put.
        sync_vault(self.vault, entry_date="2026-11-12")
        unchanged = (self.vault / "wiki/concepts/foo-page.md").read_text(encoding="utf-8")
        self.assertEqual(unchanged, changed)

    def test_adds_missing_required_keys_without_inventing_content(self):
        text = self.drop_key(self.page("concepts/foo-page.md"), "sources")
        self.write_page("concepts/foo-page.md", text)

        sync_vault(self.vault, entry_date="2026-11-11")

        normalised = (self.vault / "wiki/concepts/foo-page.md").read_text(
            encoding="utf-8"
        )
        fm = parse_frontmatter(normalised)
        self.assertEqual(fm["sources"], [])
        self.assertEqual(fm["type"], "concept")
        self.assertEqual(fm["title"], "Foo Page")

    def test_adds_frontmatter_to_a_page_that_has_none(self):
        self.write_page("concepts/foo-page.md", "# Foo Page\n\nBody text.\n")

        sync_vault(self.vault, entry_date="2026-11-11")

        normalised = (self.vault / "wiki/concepts/foo-page.md").read_text(
            encoding="utf-8"
        )
        fm = parse_frontmatter(normalised)
        self.assertEqual(fm["type"], "concept")
        self.assertEqual(fm["title"], "Foo Page")
        self.assertEqual(fm["created"], "2026-11-11")
        self.assertIn("Body text.", normalised)

    def test_derives_a_missing_type_from_the_page_directory(self):
        text = self.drop_key(
            self.page("entities/foo-page.md", type="entity", title="Foo Page"),
            "type",
        )
        self.write_page("entities/foo-page.md", text)

        sync_vault(self.vault, entry_date="2026-11-11")

        normalised = (self.vault / "wiki/entities/foo-page.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("type: entity", normalised)

    def test_quotes_a_missing_title_derived_from_the_h1(self):
        text = self.page("concepts/foo-page.md", title="Placeholder", h1="Foo: Bar")
        text = self.drop_key(text, "title")
        self.write_page("concepts/foo-page.md", text)

        sync_vault(self.vault, entry_date="2026-11-11")

        normalised = (self.vault / "wiki/concepts/foo-page.md").read_text(
            encoding="utf-8"
        )
        self.assertIn('title: "Foo: Bar"', normalised)
        self.assertEqual(parse_frontmatter(normalised)["title"], "Foo: Bar")

    def test_preserves_body_with_trailing_space_on_closing_delimiter(self):
        text = self.page("concepts/foo-page.md")
        prose = "\nSee: a # note here.\n"
        text = text.replace("\n---\n\n# Foo Page", " \n--- \n\n# Foo Page" + prose)
        self.write_page("concepts/foo-page.md", text)

        sync_vault(self.vault, entry_date="2026-11-11")

        after = (self.vault / "wiki/concepts/foo-page.md").read_text(encoding="utf-8")
        self.assertIn("See: a # note here.", after)
        self.assertNotIn('See: a "', after)

    def test_does_not_touch_page_body(self):
        prose = "A sentinel paragraph that must survive verbatim.\n"
        self.write_page(
            "concepts/foo-page.md",
            self.page("concepts/foo-page.md").replace(
                "# Foo Page", "# Foo Page\n\n" + prose
            ),
        )
        page_path = self.vault / "wiki/concepts/foo-page.md"
        before = page_path.read_text(encoding="utf-8")

        sync_vault(self.vault, entry_date="2026-11-11")

        after = page_path.read_text(encoding="utf-8")
        self.assertEqual(after.split("---\n", 2)[2], before.split("---\n", 2)[2])


class TestSyncLog(SyncTestCase):
    def test_appends_one_sync_entry_when_something_changed(self):
        self.write_page("concepts/foo-page.md", self.page("concepts/foo-page.md"))

        sync_vault(self.vault, entry_date="2026-11-11")

        log = self.log_path.read_text(encoding="utf-8")
        self.assertIn("## [2026-11-11] sync |", log)
        self.assertEqual(log.count("sync |"), 1)

    def test_no_log_entry_when_nothing_changed(self):
        self.write_page("concepts/foo-page.md", self.page("concepts/foo-page.md"))
        sync_vault(self.vault, entry_date="2026-11-11")
        before = self.log_path.read_text(encoding="utf-8")

        result = sync_vault(self.vault, entry_date="2026-11-11")

        self.assertFalse(result.log_written)
        self.assertEqual(self.log_path.read_text(encoding="utf-8"), before)

    def test_second_run_reports_nothing_changed(self):
        self.write_page("concepts/foo-page.md", self.page("concepts/foo-page.md"))
        sync_vault(self.vault, entry_date="2026-11-11")

        result = sync_vault(self.vault, entry_date="2026-11-11")

        self.assertEqual(result.pages_changed, [])
        self.assertEqual(result.index_added, [])
        self.assertFalse(result.log_written)

    def test_appends_at_most_one_entry_per_day(self):
        self.write_page("concepts/foo-page.md", self.page("concepts/foo-page.md"))
        sync_vault(self.vault, entry_date="2026-11-11")
        # A later change on the same day must not append a second entry.
        self.write_page("entities/bar-page.md", self.page(
            "entities/bar-page.md", type="entity", title="Bar Page", h1="Bar Page",
        ))
        result = sync_vault(self.vault, entry_date="2026-11-11")

        self.assertTrue(result.pages_changed or result.index_added)
        self.assertFalse(result.log_written)
        log = self.log_path.read_text(encoding="utf-8")
        self.assertEqual(log.count("sync |"), 1)


class TestSyncCli(SyncTestCase):
    def test_sync_refuses_outside_vault(self):
        outside = Path(tempfile.mkdtemp()).resolve()
        try:
            rc = main(["--vault", str(outside), "sync"])
            self.assertEqual(rc, 1)
            self.assertEqual(list(outside.rglob("*")), [])
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_sync_exits_zero_when_nothing_to_do(self):
        rc = main(["--vault", str(self.vault), "sync"])
        self.assertEqual(rc, 0)

    def test_sync_exits_zero_after_work(self):
        self.write_page("concepts/foo-page.md", self.page("concepts/foo-page.md"))
        rc = main(["--vault", str(self.vault), "sync"])
        self.assertEqual(rc, 0)
        self.assertIn("sync |", self.log_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
