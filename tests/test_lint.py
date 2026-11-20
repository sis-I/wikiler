"""Tests for the wiki lint engine."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from wikiler.lint import (
    Severity,
    Finding,
    LintResult,
    parse_frontmatter,
    extract_wikilinks,
    is_title_case,
    lint_vault,
    format_result,
    find_wiki_pages,
    find_page_files,
    result_to_dict,
)
from wikiler.vault import ensure_vault_structure, vault_paths
from wikiler.log import append_log_entry


class TestParseFrontmatter(unittest.TestCase):
    def test_missing_frontmatter(self):
        self.assertIsNone(parse_frontmatter("# Just a title\n\nbody\n"))

    def test_valid_frontmatter(self):
        text = """---
type: source
title: My Page
sources: [a.md, b.md]
created: 2026-10-29
updated: 2026-10-29
tags: [tag1, tag2]
---

# My Page

body
"""
        fm = parse_frontmatter(text)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["type"], "source")
        self.assertEqual(fm["title"], "My Page")
        self.assertEqual(fm["sources"], ["a.md", "b.md"])
        self.assertEqual(fm["created"], "2026-10-29")
        self.assertEqual(fm["tags"], ["tag1", "tag2"])

    def test_empty_list_frontmatter(self):
        text = """---
type: concept
title: X
sources: []
created: 2026-10-29
updated: 2026-10-29
tags: []
---

# X
"""
        fm = parse_frontmatter(text)
        self.assertEqual(fm["sources"], [])
        self.assertEqual(fm["tags"], [])

    def test_flow_list_with_quoted_comma(self):
        text = """---
type: concept
title: X
sources: [a.md, "b, c.md", d.md]
created: 2026-10-29
updated: 2026-10-29
tags: []
---

# X
"""
        fm = parse_frontmatter(text)
        self.assertEqual(fm["sources"], ["a.md", "b, c.md", "d.md"])

    def test_inline_comment_is_stripped(self):
        text = """---
type: concept
title: Foo
sources: [] # none yet
created: 2026-10-29
updated: 2026-10-29
tags: []
---

# Foo
"""
        fm = parse_frontmatter(text)
        self.assertEqual(fm["sources"], [])
        self.assertEqual(fm["title"], "Foo")

    def test_quoted_values(self):
        text = """---
type: entity
title: "My Entity"
tags: ["a", "b"]
created: 2026-10-29
updated: 2026-10-29
sources: []
---

# My Entity
"""
        fm = parse_frontmatter(text)
        self.assertEqual(fm["title"], "My Entity")
        self.assertEqual(fm["tags"], ["a", "b"])


class TestExtractWikilinks(unittest.TestCase):
    def test_full_form(self):
        text = "See [[llm-wiki|LLM Wiki (concept)]] for details."
        links = extract_wikilinks(text)
        self.assertEqual(links, [("llm-wiki|LLM Wiki (concept)", "llm-wiki", "LLM Wiki (concept)")])

    def test_short_form(self):
        text = "See [[LLM Wiki]] for details."
        links = extract_wikilinks(text)
        self.assertEqual(links, [("LLM Wiki", "LLM Wiki", "LLM Wiki")])

    def test_multiple_links(self):
        text = "See [[a|A]] and [[b|B]]."
        links = extract_wikilinks(text)
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0], ("a|A", "a", "A"))
        self.assertEqual(links[1], ("b|B", "b", "B"))

    def test_no_links(self):
        self.assertEqual(extract_wikilinks("No links here."), [])


class TestIsTitleCase(unittest.TestCase):
    def test_title_case_ok(self):
        self.assertTrue(is_title_case("LLM Wiki"))
        self.assertTrue(is_title_case("The Complete Guide"))
        self.assertTrue(is_title_case("90% Test Coverage"))
        self.assertTrue(is_title_case("Build the Lever"))
        self.assertTrue(is_title_case("/architect (concept)"))

    def test_not_title_case(self):
        self.assertFalse(is_title_case("llm wiki"))  # all lowercase
        self.assertFalse(is_title_case("LLM wiki"))  # lowercase second word
        self.assertFalse(is_title_case("llm Wiki"))  # lowercase first word
        self.assertFalse(is_title_case("poteto"))  # lowercase first word
        self.assertFalse(is_title_case("what is codemode"))  # lowercase middle


class TestLintResult(unittest.TestCase):
    def test_by_severity(self):
        result = LintResult()
        result.add(Severity.ERROR, "a.md", "err1")
        result.add(Severity.WARNING, "b.md", "warn1")
        result.add(Severity.INFO, "c.md", "info1")
        result.add(Severity.ERROR, "d.md", "err2")
        self.assertEqual(len(result.errors), 2)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(len(result.infos), 1)
        self.assertTrue(result.has_errors)

    def test_no_errors(self):
        result = LintResult()
        result.add(Severity.INFO, "a.md", "info1")
        self.assertFalse(result.has_errors)


class TestLintVault(unittest.TestCase):
    def _make_page(self, vault, rel, content):
        vault = Path(vault)
        path = vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _make_clean_page(self, vault, rel, title, ptype="concept"):
        fm = (
            f"---\n"
            f"type: {ptype}\n"
            f"title: {title}\n"
            f"sources: []\n"
            f"created: 2026-10-29\n"
            f"updated: 2026-10-29\n"
            f"tags: []\n"
            f"---\n\n"
            f"# {title}\n\n"
            f"body\n"
        )
        return self._make_page(vault, rel, fm)

    def test_empty_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            result = lint_vault(tmp)
            self.assertEqual(len(result.findings), 0)

    def test_missing_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self._make_page(tmp, "wiki/concepts/nofm.md", "# No Frontmatter\n\nbody\n")
            result = lint_vault(tmp)
            errors = [f for f in result.errors if "frontmatter" in f.message]
            self.assertTrue(any("missing YAML frontmatter" in f.message for f in errors))

    def test_missing_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "created: 2026-10-29\n"
                "---\n\n"
                "# Incomplete\n\nbody\n"
            )
            self._make_page(tmp, "wiki/concepts/incomplete.md", content)
            result = lint_vault(tmp)
            missing = [f for f in result.errors if "missing required fields" in f.message]
            self.assertTrue(len(missing) >= 1)

    def test_invalid_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: not-a-type\n"
                "title: Bad Type\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Bad Type\n\nbody\n"
            )
            self._make_page(tmp, "wiki/concepts/badtype.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any("invalid frontmatter type" in f.message for f in result.errors))

    def test_h1_title_case_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self._make_clean_page(tmp, "wiki/concepts/lower.md", "all lowercase title")
            result = lint_vault(tmp)
            self.assertTrue(any("not Title Case" in f.message for f in result.warnings))

    def test_h1_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: No H1\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "Just body, no H1.\n"
            )
            self._make_page(tmp, "wiki/concepts/noh1.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any("missing Title Case H1" in f.message for f in result.errors))

    def test_short_form_wikilink_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: With Link\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# With Link\n\n"
                "See [[Some Page]] for details.\n"
            )
            self._make_page(tmp, "wiki/concepts/withlink.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any("short-form wikilink" in f.message for f in result.warnings))

    def test_full_form_wikilink_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            # Create the target page first
            self._make_clean_page(tmp, "wiki/concepts/some-page.md", "Some Page")
            content = (
                "---\n"
                "type: concept\n"
                "title: With Link\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# With Link\n\n"
                "See [[some-page|Some Page]] for details.\n"
            )
            self._make_page(tmp, "wiki/concepts/withlink.md", content)
            result = lint_vault(tmp)
            broken = [f for f in result.errors if "broken link" in f.message]
            short = [f for f in result.warnings if "short-form" in f.message]
            self.assertEqual(len(broken), 0)
            self.assertEqual(len(short), 0)

    def test_path_prefixed_link_without_wiki_prefix_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            # Duplicate stem 'pi-durable' in two directories
            self._make_clean_page(tmp, "wiki/entities/pi-durable.md", "Pi Durable")
            self._make_clean_page(tmp, "wiki/sources/pi-durable.md", "Pi Durable")
            content = (
                "---\n"
                "type: concept\n"
                "title: Linker\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Linker\n\n"
                "See [[entities/pi-durable|Pi Durable]] for details.\n"
            )
            self._make_page(tmp, "wiki/concepts/linker.md", content)
            result = lint_vault(tmp)
            broken = [f for f in result.errors if "broken link" in f.message]
            ambiguous = [f for f in result.errors if "ambiguous" in f.message]
            self.assertEqual(len(broken), 0)
            self.assertEqual(len(ambiguous), 0)

    def test_path_prefixed_link_with_wiki_prefix_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self._make_clean_page(tmp, "wiki/entities/pi-durable.md", "Pi Durable")
            self._make_clean_page(tmp, "wiki/sources/pi-durable.md", "Pi Durable")
            content = (
                "---\n"
                "type: concept\n"
                "title: Linker\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Linker\n\n"
                "See [[wiki/entities/pi-durable|Pi Durable]] for details.\n"
            )
            self._make_page(tmp, "wiki/concepts/linker.md", content)
            result = lint_vault(tmp)
            broken = [f for f in result.errors if "broken link" in f.message]
            ambiguous = [f for f in result.errors if "ambiguous" in f.message]
            self.assertEqual(len(broken), 0)
            self.assertEqual(len(ambiguous), 0)

    def test_ambiguous_bare_stem_duplicate_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            # Duplicate stem 'pi-durable' in two directories
            self._make_clean_page(tmp, "wiki/entities/pi-durable.md", "Pi Durable")
            self._make_clean_page(tmp, "wiki/sources/pi-durable.md", "Pi Durable")
            content = (
                "---\n"
                "type: concept\n"
                "title: Linker\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Linker\n\n"
                "See [[pi-durable|Pi Durable]] for details.\n"
            )
            self._make_page(tmp, "wiki/concepts/linker.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any("ambiguous link" in f.message for f in result.errors))
            self.assertTrue(any("duplicated across directories" in f.message for f in result.errors))

    def test_broken_link_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Broken\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Broken\n\n"
                "See [[nonexistent-page|Nonexistent]] for details.\n"
            )
            self._make_page(tmp, "wiki/concepts/broken.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any("broken link" in f.message for f in result.errors))

    def test_ambiguous_stem_uses_typed_display_for_suggestion(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self._make_clean_page(
                tmp,
                "wiki/entities/pi-durable.md",
                "Pi Durable",
                ptype="entity",
            )
            self._make_clean_page(
                tmp,
                "wiki/sources/pi-durable.md",
                "Pi Durable",
                ptype="source",
            )
            content = (
                "---\n"
                "type: concept\n"
                "title: Linker\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Linker\n\n"
                "See [[pi-durable|Pi Durable (entity)]] for details.\n"
            )
            self._make_page(tmp, "wiki/concepts/linker.md", content)

            result = lint_vault(tmp)

            errors = [f for f in result.errors if "link" in f.message]
            self.assertEqual(len(errors), 1)
            self.assertIn(
                "did you mean [[entities/pi-durable|Pi Durable]]",
                errors[0].message,
            )

    def test_ambiguous_title_alias_reports_all_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self._make_clean_page(
                tmp,
                "wiki/entities/shared-one.md",
                "Shared Title",
                ptype="entity",
            )
            self._make_clean_page(
                tmp,
                "wiki/sources/shared-two.md",
                "Shared Title",
                ptype="source",
            )
            content = (
                "---\n"
                "type: concept\n"
                "title: Linker\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Linker\n\n"
                "See [[Shared Title]] for details.\n"
            )
            self._make_page(tmp, "wiki/concepts/linker.md", content)

            result = lint_vault(tmp)

            errors = [f for f in result.errors if "ambiguous link" in f.message]
            self.assertEqual(len(errors), 1)
            self.assertIn("matches multiple pages", errors[0].message)
            self.assertIn("entities/shared-one", errors[0].message)
            self.assertIn("sources/shared-two", errors[0].message)

    def test_broken_link_suggests_unique_title_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self._make_clean_page(tmp, "wiki/concepts/foo.md", "Foo")
            content = (
                "---\n"
                "type: concept\n"
                "title: Broken\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Broken\n\n"
                "See [[Foo]] for details.\n"
            )
            self._make_page(tmp, "wiki/concepts/broken.md", content)

            result = lint_vault(tmp)

            broken = [f for f in result.errors if "broken link" in f.message]
            self.assertEqual(len(broken), 1)
            self.assertIn(
                "did you mean [[concepts/foo|Foo]]",
                broken[0].message,
            )

    def test_orphan_page_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            # A page with no inbound links
            self._make_clean_page(tmp, "wiki/concepts/orphan.md", "Orphan Page")
            result = lint_vault(tmp)
            self.assertTrue(any("orphan page" in f.message for f in result.infos))

    def test_not_orphan_when_linked(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            # Two pages that link to each other - neither is an orphan.
            content_a = (
                "---\n"
                "type: concept\n"
                "title: Page A\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Page A\n\n"
                "See [[page-b|Page B]] for details.\n"
            )
            content_b = (
                "---\n"
                "type: concept\n"
                "title: Page B\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Page B\n\n"
                "See [[page-a|Page A]] for details.\n"
            )
            self._make_page(tmp, "wiki/concepts/page-a.md", content_a)
            self._make_page(tmp, "wiki/concepts/page-b.md", content_b)
            result = lint_vault(tmp)
            orphans = [f for f in result.infos if "orphan page" in f.message]
            self.assertEqual(len(orphans), 0)

    def test_index_short_form_link_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self._make_page(tmp, "wiki/index.md", "# Index\n\n- [[Some Page]]\n")
            result = lint_vault(tmp)
            warnings = [
                f for f in result.warnings
                if f.file == "wiki/index.md" and "short-form" in f.message
            ]
            self.assertEqual(len(warnings), 1)

    def test_log_short_form_link_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self._make_page(tmp, "wiki/log.md", "# Log\n\n- [[GBrain (entity)]]\n")
            result = lint_vault(tmp)
            warnings = [
                f for f in result.warnings
                if f.file == "wiki/log.md" and "short-form" in f.message
            ]
            self.assertEqual(len(warnings), 1)

    def test_log_links_are_form_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self._make_clean_page(tmp, "wiki/concepts/orphan.md", "Orphan Page")
            self._make_page(
                tmp, "wiki/log.md",
                "# Log\n\n## [2026-10-29] lint | Old\n\n"
                "- [[missing-page]]\n"
                "- [[concepts/orphan|Orphan Page]]\n",
            )
            result = lint_vault(tmp)
            self.assertFalse(any(
                f.file == "wiki/log.md" and "broken link" in f.message
                for f in result.errors
            ))
            # Log links are history, not inbound references.
            self.assertTrue(any(
                "orphan page" in f.message for f in result.infos
            ))
            self.assertTrue(any(
                f.file == "wiki/log.md" and "short-form" in f.message
                for f in result.warnings
            ))

    def test_index_link_prevents_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self._make_clean_page(tmp, "wiki/concepts/orphan.md", "Orphan Page")
            self._make_page(
                tmp, "wiki/index.md",
                "# Index\n\n- [[concepts/orphan|Orphan Page]]\n",
            )
            result = lint_vault(tmp)
            orphans = [f for f in result.infos if "orphan page" in f.message]
            self.assertEqual(orphans, [])

    def test_non_kebab_filename_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self._make_clean_page(tmp, "wiki/concepts/Bad Name.md", "Bad Name")
            result = lint_vault(tmp)
            self.assertTrue(any(
                "not kebab-case" in f.message for f in result.errors
            ))

    def test_index_and_log_exempt_from_kebab_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self._make_page(tmp, "wiki/index.md", "# Index\n")
            self._make_page(tmp, "wiki/log.md", "# Log\n")
            result = lint_vault(tmp)
            self.assertFalse(any(
                "not kebab-case" in f.message for f in result.errors
            ))

    def test_unquoted_colon_scalar_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Foo: Bar\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Foo: Bar\n"
            )
            self._make_page(tmp, "wiki/concepts/colon.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any(
                "would be misread" in f.message and f.line == 3
                for f in result.errors
            ))

    def test_quoted_colon_scalar_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: \"Foo: Bar\"\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Foo: Bar\n"
            )
            self._make_page(tmp, "wiki/concepts/quoted-colon.md", content)
            result = lint_vault(tmp)
            self.assertFalse(any(
                "would be misread" in f.message for f in result.errors
            ))

    def test_valid_flow_list_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Flow\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: [a, \"b, c\", d]\n"
                "---\n\n"
                "# Flow\n"
            )
            self._make_page(tmp, "wiki/concepts/flow.md", content)
            result = lint_vault(tmp)
            self.assertFalse(any(
                "flow list would not parse" in f.message
                for f in result.errors
            ))

    def test_leading_indicator_scalar_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: - Foo\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# - Foo\n"
            )
            self._make_page(tmp, "wiki/concepts/leading.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any(
                "would be misread" in f.message for f in result.errors
            ))

    def test_flow_list_with_trailing_comment_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Comment\n"
                "sources: [] # none yet\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Comment\n"
            )
            self._make_page(tmp, "wiki/concepts/comment-flow.md", content)
            result = lint_vault(tmp)
            self.assertFalse(any(
                "flow list" in f.message or "'sources' must be a list" in f.message
                for f in result.errors
            ))

    def test_quoted_scalar_with_trailing_comment_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: \"Foo: Bar\" # quoted\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Foo: Bar\n"
            )
            self._make_page(tmp, "wiki/concepts/quoted-comment.md", content)
            result = lint_vault(tmp)
            self.assertFalse(any(
                "would be misread" in f.message for f in result.errors
            ))

    def test_comment_indicator_scalar_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Foo # Bar\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Foo # Bar\n"
            )
            self._make_page(tmp, "wiki/concepts/comment.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any(
                "would be misread" in f.message for f in result.errors
            ))

    def test_unclosed_flow_list_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Flow\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: [a, b\n"
                "---\n\n"
                "# Flow\n"
            )
            self._make_page(tmp, "wiki/concepts/flow.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any(
                "flow list would not parse" in f.message
                for f in result.errors
            ))

    def test_unterminated_quoted_flow_item_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Flow\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                'tags: ["a]\n'
                "---\n\n"
                "# Flow\n"
            )
            self._make_page(tmp, "wiki/concepts/flow.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any(
                "flow list would not parse" in f.message
                for f in result.errors
            ))

    def test_empty_flow_list_item_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Flow\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: [a, , b]\n"
                "---\n\n"
                "# Flow\n"
            )
            self._make_page(tmp, "wiki/concepts/flow.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any(
                "flow list would not parse" in f.message
                for f in result.errors
            ))

    def test_bad_iso_date_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Bad Date\n"
                "sources: []\n"
                "created: 2026-1-1\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Bad Date\n"
            )
            self._make_page(tmp, "wiki/concepts/baddate.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any(
                "'created' must be an ISO date" in f.message
                for f in result.errors
            ))

    def test_created_after_updated_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Backwards\n"
                "sources: []\n"
                "created: 2026-10-30\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Backwards\n"
            )
            self._make_page(tmp, "wiki/concepts/backwards.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any(
                "created' is after 'updated" in f.message
                for f in result.errors
            ))

    def test_title_h1_type_suffix_is_tolerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Foo\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Foo (concept)\n"
            )
            self._make_page(tmp, "wiki/concepts/foo.md", content)
            result = lint_vault(tmp)
            self.assertFalse(any(
                "does not match H1" in f.message for f in result.warnings
            ))

    def test_title_h1_mismatch_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Foo\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Bar\n"
            )
            self._make_page(tmp, "wiki/concepts/foo.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any(
                "does not match H1" in f.message for f in result.warnings
            ))

    def test_frontmatter_comment_is_not_an_h1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Comment\n"
                "# this is a frontmatter comment\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Comment\n"
            )
            self._make_page(tmp, "wiki/concepts/comment-heading.md", content)
            result = lint_vault(tmp)
            self.assertFalse(any(
                "multiple H1" in f.message for f in result.warnings
            ))

    def test_duplicate_h1_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Two Heads\n"
                "sources: []\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Two Heads\n\n"
                "body\n\n"
                "# Another Heading\n"
            )
            self._make_page(tmp, "wiki/concepts/two-heads.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any(
                "multiple H1" in f.message for f in result.warnings
            ))

    def test_missing_raw_source_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            content = (
                "---\n"
                "type: concept\n"
                "title: Missing Source\n"
                "sources: [missing.md]\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Missing Source\n"
            )
            self._make_page(tmp, "wiki/concepts/missing-source.md", content)
            result = lint_vault(tmp)
            self.assertTrue(any(
                "has no matching file under raw/" in f.message
                for f in result.warnings
            ))

    def test_existing_raw_source_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self._make_page(tmp, "raw/articles/foo.md", "# Foo\n")
            content = (
                "---\n"
                "type: concept\n"
                "title: Has Source\n"
                "sources: [foo.md]\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Has Source\n"
            )
            self._make_page(tmp, "wiki/concepts/has-source.md", content)
            result = lint_vault(tmp)
            self.assertFalse(any(
                "has no matching file under raw/" in f.message
                for f in result.warnings
            ))

    def test_synthesis_wiki_source_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            self._make_clean_page(tmp, "wiki/concepts/foo.md", "Foo")
            content = (
                "---\n"
                "type: synthesis\n"
                "title: Synthesis\n"
                "sources: [foo.md]\n"
                "created: 2026-10-29\n"
                "updated: 2026-10-29\n"
                "tags: []\n"
                "---\n\n"
                "# Synthesis\n"
            )
            self._make_page(tmp, "wiki/synthesis/synthesis.md", content)
            result = lint_vault(tmp)
            self.assertFalse(any(
                "has no matching file under raw/" in f.message
                for f in result.warnings
            ))

    def test_severity_ordering_in_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_vault_structure(tmp)
            # Create a page with an error (missing frontmatter)
            self._make_page(tmp, "wiki/concepts/nofm.md", "# No Frontmatter\n\nbody\n")
            result = lint_vault(tmp)
            report = format_result(result)
            # Errors should appear before warnings before info
            err_idx = report.find("ERROR")
            warn_idx = report.find("WARNING")
            info_idx = report.find("INFO")
            self.assertTrue(err_idx < warn_idx or warn_idx == -1)
            self.assertTrue(warn_idx < info_idx or info_idx == -1)


class TestResultToDict(unittest.TestCase):
    def test_shape(self):
        result = LintResult()
        result.add(Severity.ERROR, "wiki/a.md", "err", line=3)
        result.add(Severity.WARNING, "wiki/b.md", "warn")
        result.add(Severity.INFO, "wiki/c.md", "info")
        data = result_to_dict(result)
        self.assertEqual(data["command"], "lint")
        self.assertEqual(
            data["summary"], {"errors": 1, "warnings": 1, "info": 1}
        )
        self.assertEqual(len(data["findings"]), 3)
        self.assertEqual(
            data["findings"][0],
            {
                "severity": "error",
                "file": "wiki/a.md",
                "line": 3,
                "message": "err",
            },
        )


class TestLintCLI(unittest.TestCase):
    def test_lint_returns_zero_for_clean_vault(self):
        from wikiler.cli import main
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main(["--vault", tmp, "init"]), 0)
            rc = main(["--vault", tmp, "lint"])
            self.assertEqual(rc, 0)

    def test_lint_returns_nonzero_for_errors(self):
        from wikiler.cli import main
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main(["--vault", tmp, "init"]), 0)
            self._make_page_helper(tmp, "wiki/concepts/nofm.md", "# No Frontmatter\n\nbody\n")
            rc = main(["--vault", tmp, "lint"])
            self.assertNotEqual(rc, 0)

    def test_lint_json_emits_summary_and_findings(self):
        from wikiler.cli import main
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main(["--vault", tmp, "init"]), 0)
            self._make_page_helper(
                tmp, "wiki/concepts/nofm.md", "# No Frontmatter\n\nbody\n"
            )
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["--vault", tmp, "lint", "--json"])
            self.assertEqual(rc, 1)
            data = json.loads(buf.getvalue())
            self.assertEqual(data["command"], "lint")
            self.assertGreaterEqual(data["summary"]["errors"], 1)
            self.assertTrue(data["findings"])
            for finding in data["findings"]:
                self.assertEqual(
                    set(finding), {"severity", "file", "line", "message"}
                )

    def test_lint_json_clean_vault_exits_zero(self):
        from wikiler.cli import main
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main(["--vault", tmp, "init"]), 0)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["--vault", tmp, "lint", "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertEqual(
                data["summary"], {"errors": 0, "warnings": 0, "info": 0}
            )

    def _make_page_helper(self, vault, rel, content):
        vault = Path(vault)
        path = vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
