"""Tests for the ingest command: scaffold source pages, never generate prose.

Ingest is mechanical: it creates one source page with valid frontmatter and
explicit TODO markers, lists the source's images, and reconciles the index and
log. Image downloading is opt-in: by default ingest performs no network I/O.
The agent reads the source and fills the page. Re-ingesting is safe: the body
is never touched.
"""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from wikiler.cli import main
from wikiler.page import parse_frontmatter, split_frontmatter_text
from wikiler.vault import vault_paths
from wikiler.commands.ingest import (
    TODO_SECTIONS,
    today,
    _slugify,
    _parse_frontmatter_local,
    _extract_title,
    _extract_tags,
    _render_image_entry,
)
from wikiler.images import ImageRef

TODO_LABELS = [heading for heading, _hint in TODO_SECTIONS]
CORE_TODO_LABELS = [label for label in TODO_LABELS if label != "Images"]


class TestToday(unittest.TestCase):
    def test_returns_iso_date(self):
        self.assertRegex(today(), r"^\d{4}-\d{2}-\d{2}$")


class TestSlugify(unittest.TestCase):
    def test_kebab_case(self):
        self.assertEqual(
            _slugify("The AI Agent Complexity Ratchet"),
            "the-ai-agent-complexity-ratchet",
        )

    def test_collapses_punctuation(self):
        self.assertEqual(_slugify("Hello, World!!"), "hello-world")

    def test_empty_falls_back(self):
        self.assertEqual(_slugify("!!!"), "source")


class TestFrontmatterParsing(unittest.TestCase):
    def test_parses_frontmatter_and_body(self):
        text = "---\ntitle: Hello\nauthor: X\ntags: [a, b]\n---\n\n# Body\n"
        fm, body = _parse_frontmatter_local(text)
        self.assertEqual(fm["title"], "Hello")
        self.assertEqual(fm["author"], "X")
        self.assertEqual(fm["tags"], "[a, b]")
        self.assertEqual(body, "\n# Body\n")

    def test_no_frontmatter(self):
        fm, body = _parse_frontmatter_local("# Just a title\n")
        self.assertEqual(fm, {})
        self.assertEqual(body, "# Just a title\n")


class TestTitleAndTags(unittest.TestCase):
    def test_title_from_frontmatter(self):
        self.assertEqual(_extract_title({"title": "Foo"}, "", "x.md"), "Foo")

    def test_title_from_h1(self):
        self.assertEqual(
            _extract_title({}, "# Hello World\n", "x.md"), "Hello World"
        )

    def test_title_from_filename(self):
        self.assertEqual(
            _extract_title({}, "", "my-article.md"), "My Article"
        )

    def test_tags_from_list(self):
        self.assertEqual(_extract_tags({"tags": "[x, y]"}), ["x", "y"])

    def test_tags_from_comma_string(self):
        self.assertEqual(_extract_tags({"tags": "a, b, c"}), ["a", "b", "c"])

    def test_tags_empty(self):
        self.assertEqual(_extract_tags({}), [])


class VaultTestCase(unittest.TestCase):
    """A freshly initialized scratch vault, with WIKI_VAULT cleared."""

    def setUp(self):
        self._old_env = os.environ.get("WIKI_VAULT")
        os.environ.pop("WIKI_VAULT", None)
        self.tmp = tempfile.mkdtemp()
        self.vault = Path(self.tmp).resolve()
        self.assertEqual(main(["--vault", self.tmp, "init"]), 0)
        self.paths = vault_paths(self.vault)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        if self._old_env is None:
            os.environ.pop("WIKI_VAULT", None)
        else:
            os.environ["WIKI_VAULT"] = self._old_env

    def write_source(self, name, text):
        source = self.paths["raw"] / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(text, encoding="utf-8")
        return source

    def ingest(self, name="article.md", *flags):
        """Run ingest, returning (returncode, stdout)."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["--vault", self.tmp, "ingest", name, *flags])
        return rc, buf.getvalue()

    def ingest_json(self, name="article.md", *flags):
        """Run ingest with --json, returning (returncode, stdout, stderr)."""
        out_buf = io.StringIO()
        err_buf = io.StringIO()
        with contextlib.redirect_stdout(out_buf), \
                contextlib.redirect_stderr(err_buf):
            rc = main(["--vault", self.tmp, "ingest", name, "--json", *flags])
        return rc, out_buf.getvalue(), err_buf.getvalue()

    def page(self, slug="article"):
        return self.paths["wiki_sources"] / f"{slug}.md"


def _body(text):
    """Return the body after the frontmatter block, byte for byte."""
    split = split_frontmatter_text(text)
    return text if split is None else split[2]


class TestScaffoldIngest(VaultTestCase):
    def test_creates_exactly_one_page_with_four_todo_markers(self):
        self.write_source(
            "article.md",
            "---\n"
            "title: Temp Article\n"
            "author: Test Author\n"
            "tags: [test, example]\n"
            "---\n\n"
            "# Temp Article\n\n"
            "This is the first paragraph with an important claim about AI.\n",
        )

        rc, _ = self.ingest()
        self.assertEqual(rc, 0)

        pages = list(self.paths["wiki_sources"].glob("*.md"))
        self.assertEqual([p.name for p in pages], ["temp-article.md"])

        content = self.page("temp-article").read_text(encoding="utf-8")
        fm = parse_frontmatter(content)
        self.assertEqual(fm["type"], "source")
        self.assertEqual(fm["title"], "Temp Article")
        self.assertEqual(fm["sources"], ["article.md"])
        self.assertEqual(fm["tags"], ["test", "example"])
        self.assertRegex(fm["created"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(fm["updated"], r"^\d{4}-\d{2}-\d{2}$")

        self.assertEqual(content.count("<!-- TODO: agent"), 4)
        for label in CORE_TODO_LABELS:
            self.assertIn(f"## {label}", content)
        self.assertNotIn("## Images", content)

    def test_does_not_copy_source_prose(self):
        self.write_source(
            "article.md",
            "# Temp Article\n\n"
            "This sentence is the source's prose and must not be copied.\n",
        )

        self.assertEqual(self.ingest()[0], 0)

        content = self.page("temp-article").read_text(encoding="utf-8")
        self.assertNotIn("must not be copied", content)
        self.assertNotIn("source's prose", content)

    def test_creates_no_entity_or_concept_pages(self):
        self.write_source(
            "article.md",
            "# Test Source\n\n"
            "Garry Tan built GBrain with Claude Code using the Lossless "
            "Migration Pattern.\n",
        )

        self.assertEqual(self.ingest()[0], 0)

        self.assertEqual(list(self.paths["wiki_entities"].glob("*.md")), [])
        self.assertEqual(list(self.paths["wiki_concepts"].glob("*.md")), [])

    def test_quotes_titles_containing_colons(self):
        self.write_source(
            "article.md",
            "---\ntitle: Foo: Bar\n---\n\n# Foo: Bar\n\nBody.\n",
        )

        self.assertEqual(self.ingest()[0], 0)

        content = self.page("foo-bar").read_text(encoding="utf-8")
        self.assertIn('title: "Foo: Bar"', content)
        self.assertEqual(parse_frontmatter(content)["title"], "Foo: Bar")

    def test_quotes_tags_yaml_would_misread(self):
        self.write_source(
            "article.md",
            "---\ntitle: Tags\ntags: [#nlp, -x, plain]\n---\n\n# Tags\n\nBody.\n",
        )

        self.assertEqual(self.ingest()[0], 0)

        content = self.page("tags").read_text(encoding="utf-8")
        self.assertIn('tags: ["#nlp", "-x", plain]', content)

    def test_derives_title_from_h1_when_no_frontmatter(self):
        source = self.write_source(
            "no-fm.md", "# Derived Title\n\nSome body text here.\n"
        )
        original = source.read_text(encoding="utf-8")

        self.assertEqual(self.ingest("no-fm.md")[0], 0)

        page = self.page("derived-title")
        self.assertTrue(page.exists())
        fm = parse_frontmatter(page.read_text(encoding="utf-8"))
        self.assertEqual(fm["title"], "Derived Title")
        self.assertEqual(fm["sources"], ["no-fm.md"])
        self.assertEqual(fm["tags"], [])
        self.assertEqual(source.read_text(encoding="utf-8"), original)

    def test_missing_source_returns_nonzero(self):
        rc, out = self.ingest("does-not-exist.md")
        self.assertNotEqual(rc, 0)
        self.assertIn("error:", out)

    def test_rejects_source_outside_raw(self):
        outside = self.vault / "outside.md"
        outside.write_text("# Outside\n\nNot a raw source.\n", encoding="utf-8")

        rc, out = self.ingest("../outside.md")

        self.assertNotEqual(rc, 0)
        self.assertIn("raw/", out)
        self.assertEqual(list(self.paths["wiki_sources"].glob("*.md")), [])
        self.assertTrue(outside.exists())

    def test_raw_source_is_untouched(self):
        content = "# Immutable\n\nGarry Tan built GBrain.\n"
        source = self.write_source("immutable.md", content)

        self.assertEqual(self.ingest("immutable.md")[0], 0)

        self.assertEqual(source.read_text(encoding="utf-8"), content)
        raw_files = [p for p in self.paths["raw"].rglob("*") if p.is_file()]
        self.assertEqual([p.name for p in raw_files], ["immutable.md"])

    def test_manifest_names_source_page_state_todos_and_images(self):
        self.write_source("article.md", "# Temp Article\n\nBody.\n")

        rc, out = self.ingest()

        self.assertEqual(rc, 0)
        self.assertIn("ingested article.md", out)
        self.assertIn("wiki/sources/temp-article.md", out)
        self.assertIn("(created)", out)
        self.assertIn("TODO: " + ", ".join(CORE_TODO_LABELS), out)
        self.assertNotIn("Images", out)
        self.assertRegex(out, r"images: 0\b")


class TestJsonManifest(VaultTestCase):
    def test_json_prints_one_object_naming_the_manifest_fields(self):
        self.write_source("article.md", "# Temp Article\n\nBody.\n")

        rc, out, err = self.ingest_json("article.md")

        self.assertEqual(rc, 0)
        self.assertEqual(err, "")
        # One object, nothing else: stdout stays pipeable.
        self.assertEqual(len(out.strip().splitlines()), 1)
        manifest = json.loads(out)
        self.assertEqual(manifest["source"], "raw/article.md")
        self.assertEqual(manifest["page"], "wiki/sources/temp-article.md")
        self.assertEqual(manifest["title"], "Temp Article")
        self.assertIs(manifest["created"], True)
        self.assertEqual(manifest["todos"], CORE_TODO_LABELS)
        self.assertEqual(manifest["images"], 0)

    def test_json_manifest_counts_the_source_images(self):
        self.write_source(
            "article.md",
            "# Temp Article\n\n"
            "![shot](https://example.com/shot.png)\n\n"
            "![local](raw/assets/local.png)\n",
        )

        rc, out, _err = self.ingest_json("article.md")

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["images"], 2)

    def test_json_manifest_round_trips_a_title_with_a_colon(self):
        self.write_source(
            "article.md", "---\ntitle: Foo: Bar\n---\n\n# Foo: Bar\n\nBody.\n"
        )

        rc, out, _err = self.ingest_json("article.md")

        self.assertEqual(rc, 0)
        manifest = json.loads(out)
        self.assertEqual(manifest["title"], "Foo: Bar")
        fm = parse_frontmatter(self.page("foo-bar").read_text(encoding="utf-8"))
        self.assertEqual(fm["title"], manifest["title"])

    def test_json_errors_go_to_stderr_so_stdout_stays_empty(self):
        rc, out, err = self.ingest_json("does-not-exist.md")

        self.assertNotEqual(rc, 0)
        self.assertEqual(out, "")
        self.assertIn("error:", err)


class TestForceIngest(VaultTestCase):
    def setUp(self):
        super().setUp()
        self.write_source("dup.md", "# Dup\n\nBody one.\n")
        self.assertEqual(self.ingest("dup.md")[0], 0)

    def test_force_discards_the_authored_body(self):
        page = self.page("dup")
        authored = "Agent-authored analysis that must not survive.\n"
        page.write_text(
            page.read_text(encoding="utf-8") + "\n" + authored, encoding="utf-8"
        )

        rc, _out = self.ingest("dup.md", "--force")

        self.assertEqual(rc, 0)
        text = page.read_text(encoding="utf-8")
        self.assertNotIn(authored, text)
        self.assertIn("<!-- TODO: agent", text)

    def test_force_preserves_created_and_refreshes_updated(self):
        page = self.page("dup")
        text = page.read_text(encoding="utf-8")
        page.write_text(
            text.replace(f"created: {today()}", "created: 2020-01-01"),
            encoding="utf-8",
        )

        self.assertEqual(self.ingest("dup.md", "--force")[0], 0)

        fm = parse_frontmatter(page.read_text(encoding="utf-8"))
        self.assertEqual(fm["created"], "2020-01-01")
        self.assertEqual(fm["updated"], today())

    def test_force_on_a_page_that_does_not_exist_creates_it(self):
        self.write_source("fresh.md", "# Fresh\n\nBody.\n")

        rc, out = self.ingest("fresh.md", "--force")

        self.assertEqual(rc, 0)
        self.assertIn("(created)", out)
        self.assertTrue(self.page("fresh").exists())

    def test_force_manifest_state_says_rewritten(self):
        rc, out = self.ingest("dup.md", "--force")

        self.assertEqual(rc, 0)
        self.assertIn("(rewritten)", out)

    def test_json_and_force_work_together(self):
        page = self.page("dup")
        page.write_text(
            page.read_text(encoding="utf-8") + "\nAgent text.\n", encoding="utf-8"
        )

        rc, out, err = self.ingest_json("dup.md", "--force")

        self.assertEqual(rc, 0)
        self.assertEqual(err, "")
        manifest = json.loads(out)
        self.assertIs(manifest["created"], False)
        self.assertEqual(manifest["todos"], CORE_TODO_LABELS)
        self.assertNotIn("Agent text.", page.read_text(encoding="utf-8"))


class TestReingest(VaultTestCase):
    def setUp(self):
        super().setUp()
        self.write_source("dup.md", "# Dup\n\nBody one.\n")
        self.assertEqual(self.ingest("dup.md")[0], 0)

    def test_reingest_leaves_body_byte_identical(self):
        before = self.page("dup").read_text(encoding="utf-8")

        self.assertEqual(self.ingest("dup.md")[0], 0)

        after = self.page("dup").read_text(encoding="utf-8")
        self.assertEqual(_body(after), _body(before))

    def test_reingest_keeps_agent_authored_text(self):
        page = self.page("dup")
        authored = "Agent-authored analysis that must survive.\n"
        text = page.read_text(encoding="utf-8")
        page.write_text(text + "\n" + authored, encoding="utf-8")

        self.assertEqual(self.ingest("dup.md")[0], 0)

        self.assertIn(authored, page.read_text(encoding="utf-8"))

    def test_reingest_preserves_created_and_refreshes_updated(self):
        page = self.page("dup")
        text = page.read_text(encoding="utf-8")
        text = text.replace(
            f"created: {today()}", "created: 2020-01-01"
        ).replace(f"updated: {today()}", "updated: 2020-01-01")
        page.write_text(text, encoding="utf-8")

        self.assertEqual(self.ingest("dup.md")[0], 0)

        fm = parse_frontmatter(page.read_text(encoding="utf-8"))
        self.assertEqual(fm["created"], "2020-01-01")
        self.assertEqual(fm["updated"], today())

    def test_reingest_fills_in_missing_required_keys(self):
        page = self.page("dup")
        text = page.read_text(encoding="utf-8")
        text = "\n".join(
            line for line in text.splitlines() if not line.startswith("tags:")
        ) + "\n"
        page.write_text(text, encoding="utf-8")
        body_before = _body(text)

        self.assertEqual(self.ingest("dup.md")[0], 0)

        new_text = page.read_text(encoding="utf-8")
        fm = parse_frontmatter(new_text)
        self.assertEqual(fm["tags"], [])
        self.assertEqual(_body(new_text), body_before)

    def test_manifest_lists_only_the_todos_still_open(self):
        page = self.page("dup")
        text = page.read_text(encoding="utf-8")
        text = text.replace(
            "<!-- TODO: agent — write the structured summary -->",
            "The agent's summary.",
        )
        page.write_text(text, encoding="utf-8")

        rc, out = self.ingest("dup.md")

        self.assertEqual(rc, 0)
        self.assertIn("TODO: Key claims, Entities, Concepts", out)
        self.assertNotIn("Structured summary", out)

    def test_reingest_does_not_duplicate_index_or_log_entries(self):
        self.assertEqual(self.ingest("dup.md")[0], 0)

        index = self.paths["index"].read_text(encoding="utf-8")
        log = self.paths["log"].read_text(encoding="utf-8")
        self.assertEqual(len(list(self.paths["wiki_sources"].glob("*.md"))), 1)
        self.assertEqual(index.count("[[sources/dup|Dup]]"), 1)
        self.assertEqual(log.count("ingest | Dup"), 1)

    def test_reingest_does_not_duplicate_images(self):
        source = self.write_source(
            "img.md",
            "# Img\n\n![alt](https://example.com/pic.png)\n",
        )
        response = _FakeResponse(b"img-bytes", "image/png")
        with mock.patch(
            "wikiler.images.urllib.request.urlopen",
            return_value=response,
        ) as urlopen:
            self.assertEqual(self.ingest("img.md", "--download-images")[0], 0)
            self.assertEqual(self.ingest("img.md", "--download-images")[0], 0)

        assets = sorted(p.name for p in self.paths["raw_assets"].iterdir())
        self.assertEqual(assets, ["pic.png"])
        # The second ingest reused the asset instead of downloading it again.
        self.assertEqual(urlopen.call_count, 1)
        self.assertEqual(source.read_text(encoding="utf-8").count("https://"), 1)


class _FakeResponse:
    """A urlopen response that fails if headers are read after closing."""

    def __init__(self, data, content_type):
        self._data = data
        self._content_type = content_type
        self.closed = False
        self.headers = self  # acts as the headers mapping

    def read(self):
        return self._data

    def get(self, key, default=None):
        if key == "Content-Type":
            if self.closed:
                raise AssertionError(
                    "Content-Type read after the response was closed"
                )
            return self._content_type
        return default

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.closed = True
        return False


class TestImageIngest(VaultTestCase):
    def test_default_ingest_performs_no_network_io(self):
        self.write_source(
            "remote.md",
            "# Remote\n\n![screenshot](https://example.com/shot.png)\n",
        )

        with mock.patch(
            "wikiler.images.urllib.request.urlopen",
            side_effect=AssertionError("default ingest must not touch the network"),
        ):
            rc, out = self.ingest("remote.md")

        self.assertEqual(rc, 0)
        self.assertEqual(list(self.paths["raw_assets"].iterdir()), [])
        self.assertIn("remote not downloaded", out)
        self.assertIn("--download-images", out)

        content = self.page("remote").read_text(encoding="utf-8")
        self.assertIn("## Images", content)
        self.assertIn(
            "https://example.com/shot.png — screenshot "
            "(not downloaded; rerun with --download-images)",
            content,
        )

    def test_lists_local_assets_and_obsidian_embeds_without_network(self):
        (self.paths["raw_assets"] / "Image 7.jpg").write_bytes(b"local")
        (self.paths["raw_assets"] / "shot.png").write_bytes(b"local")
        self.write_source(
            "local.md",
            "# Local\n\n"
            "![screenshot](raw/assets/shot.png)\n\n"
            "![[Image 7.jpg|Image]]\n"
            "\n"
            "Ending the month of August with 2,462 PRs in production\n",
        )

        with mock.patch(
            "wikiler.images.urllib.request.urlopen",
            side_effect=AssertionError("local assets need no network"),
        ):
            rc, out = self.ingest("local.md")

        self.assertEqual(rc, 0)
        self.assertRegex(out, r"images: 2 local\b")
        self.assertNotIn("not downloaded", out)

        content = self.page("local").read_text(encoding="utf-8")
        self.assertIn("![screenshot](raw/assets/shot.png)", content)
        self.assertIn("![Image](<raw/assets/Image 7.jpg>)", content)
        self.assertIn(
            "— Ending the month of August with 2,462 PRs in production", content
        )

    def test_download_images_flag_fetches_and_lists_local_paths(self):
        self.write_source(
            "flag.md",
            "# Flag\n\n![screenshot](https://example.com/shot.png)\n",
        )
        response = _FakeResponse(b"shot-bytes", "image/png")

        with mock.patch(
            "wikiler.images.urllib.request.urlopen",
            return_value=response,
        ):
            rc, out = self.ingest("flag.md", "--download-images")

        self.assertEqual(rc, 0)
        asset = self.paths["raw_assets"] / "shot.png"
        self.assertEqual(asset.read_bytes(), b"shot-bytes")
        self.assertRegex(out, r"images: 1 local\b")
        self.assertNotIn("not downloaded", out)

        content = self.page("flag").read_text(encoding="utf-8")
        self.assertIn("![screenshot](raw/assets/shot.png)", content)
        self.assertNotIn("https://example.com/shot.png", content)

    def test_download_flag_names_files_from_the_url(self):
        self.write_source(
            "tw.md",
            "# Tw\n\n"
            "![Image](https://pbs.twimg.com/media/HIGAeAZXoAAbGms"
            "?format=jpg&name=large)\n",
        )
        response = _FakeResponse(b"tw-bytes", "image/jpeg")

        with mock.patch(
            "wikiler.images.urllib.request.urlopen",
            return_value=response,
        ):
            self.assertEqual(self.ingest("tw.md", "--download-images")[0], 0)

        self.assertTrue(
            (self.paths["raw_assets"] / "HIGAeAZXoAAbGms.jpg").is_file()
        )
        self.assertIn(
            "HIGAeAZXoAAbGms.jpg",
            self.page("tw").read_text(encoding="utf-8"),
        )

    def test_non_image_embeds_do_not_trigger_an_images_section(self):
        self.write_source(
            "docs.md",
            "# Docs\n\n![[paper.pdf]]\n\n![[Meeting Notes]]\n\n"
            "![spec](raw/assets/spec.pdf)\n",
        )

        rc, out = self.ingest("docs.md")

        self.assertEqual(rc, 0)
        self.assertRegex(out, r"images: 0\b")
        self.assertNotIn("Images", out)
        content = self.page("docs").read_text(encoding="utf-8")
        self.assertNotIn("## Images", content)
        self.assertNotIn("TODO: agent — describe", content)

    def test_reingest_with_download_leaves_authored_body_byte_identical(self):
        self.write_source(
            "again.md",
            "# Again\n\n![shot](https://example.com/shot.png)\n",
        )
        self.assertEqual(self.ingest("again.md")[0], 0)
        page = self.page("again")
        page.write_text(
            page.read_text(encoding="utf-8") + "\nAgent-authored analysis.\n",
            encoding="utf-8",
        )
        before = _body(page.read_text(encoding="utf-8"))

        response = _FakeResponse(b"shot-bytes", "image/png")
        with mock.patch(
            "wikiler.images.urllib.request.urlopen",
            return_value=response,
        ):
            self.assertEqual(self.ingest("again.md", "--download-images")[0], 0)

        self.assertTrue((self.paths["raw_assets"] / "shot.png").is_file())
        self.assertEqual(_body(page.read_text(encoding="utf-8")), before)


class TestImageEntries(unittest.TestCase):
    def test_remote_entry_reports_not_downloaded_once(self):
        ref = ImageRef(
            target="https://example.com/shot.png",
            remote=True,
            alt="A screenshot",
            caption="A screenshot",
        )
        entry = _render_image_entry(ref)
        self.assertEqual(entry.count("A screenshot"), 1)
        self.assertIn("not downloaded", entry)

    def test_local_entry_uses_alt_text_and_caption(self):
        ref = ImageRef(
            target="raw/assets/Image 7.jpg",
            remote=False,
            alt="Image",
            caption="Ending the month with 2,462 PRs",
        )
        self.assertEqual(
            _render_image_entry(ref),
            "- ![Image](<raw/assets/Image 7.jpg>)"
            " — Ending the month with 2,462 PRs",
        )

    def test_local_entry_falls_back_to_the_filename(self):
        ref = ImageRef(target="raw/assets/shot.png", remote=False)
        self.assertEqual(
            _render_image_entry(ref), "- ![shot.png](raw/assets/shot.png)"
        )


class TestIngestIndexAndLogUpdates(VaultTestCase):
    def test_ingest_indexes_page_with_file_path_link(self):
        self.write_source("tech-article.md", "# Tech Article\n\nBody.\n")

        self.assertEqual(self.ingest("tech-article.md")[0], 0)

        index = self.paths["index"].read_text(encoding="utf-8")
        self.assertIn("## Sources", index)
        self.assertIn("[[sources/tech-article|Tech Article]]", index)
        # No entity/concept pages were created, so only the empty index
        # sections init wrote remain.
        entries = [line for line in index.splitlines() if line.startswith("- [[")]
        self.assertEqual(entries, ["- [[sources/tech-article|Tech Article]]"])

    def test_ingest_appends_ingest_entry_to_log(self):
        self.write_source("log-article.md", "# Log Article\n\nBody.\n")

        self.assertEqual(self.ingest("log-article.md")[0], 0)

        log = self.paths["log"].read_text(encoding="utf-8")
        self.assertRegex(log, r"## \[\d{4}-\d{2}-\d{2}\] ingest \| Log Article")


if __name__ == "__main__":
    unittest.main()
