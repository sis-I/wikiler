"""Tests for image discovery: local assets first, remote downloads opt-in.

Discovery is mechanical. It classifies each image the source references as
local (already under raw/assets/) or remote, copies the alt text or caption the
source already carries, and never touches the network.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from wikiler.images import (
    ImageRef,
    extract_image_urls,
    find_images,
    _download_image,
    _image_filename,
)


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


class TestFindImages(unittest.TestCase):
    def test_no_images(self):
        self.assertEqual(find_images("# Title\n\nProse only.\n"), [])

    def test_obsidian_embed_is_a_local_asset(self):
        refs = find_images("![[Image 5.jpg]]\n")
        self.assertEqual(
            [(ref.target, ref.remote) for ref in refs],
            [("raw/assets/Image 5.jpg", False)],
        )

    def test_obsidian_alias_becomes_alt_text(self):
        refs = find_images("![[Image 6.jpg|Grok Bot]]\n")
        self.assertEqual(refs[0].alt, "Grok Bot")

    def test_obsidian_width_alias_is_not_alt_text(self):
        self.assertEqual(find_images("![[Image 6.jpg|300]]\n")[0].alt, "")

    def test_obsidian_path_stays_vault_relative(self):
        refs = find_images("![[raw/assets/Image 5.jpg]]\n")
        self.assertEqual(refs[0].target, "raw/assets/Image 5.jpg")

    def test_markdown_raw_assets_link_is_local(self):
        refs = find_images("![screenshot](raw/assets/shot.png)\n")
        self.assertEqual(refs[0].target, "raw/assets/shot.png")
        self.assertFalse(refs[0].remote)
        self.assertEqual(refs[0].alt, "screenshot")

    def test_markdown_raw_assets_link_with_spaces_is_local(self):
        refs = find_images("![x](raw/assets/Image 7.jpg)\n")
        self.assertEqual(refs[0].target, "raw/assets/Image 7.jpg")

    def test_markdown_angle_bracket_path_is_local(self):
        refs = find_images("![x](<raw/assets/Image 7.jpg>)\n")
        self.assertEqual(refs[0].target, "raw/assets/Image 7.jpg")

    def test_markdown_link_title_is_not_part_of_the_path(self):
        refs = find_images('![x](raw/assets/shot.png "A title")\n')
        self.assertEqual(refs[0].target, "raw/assets/shot.png")

    def test_markdown_non_image_local_link_is_ignored(self):
        self.assertEqual(find_images("![doc](raw/assets/spec.pdf)\n"), [])

    def test_pdf_embed_is_not_an_image(self):
        self.assertEqual(find_images("![[paper.pdf]]\n"), [])

    def test_note_embed_is_not_an_image(self):
        self.assertEqual(find_images("![[Meeting Notes]]\n"), [])

    def test_markdown_remote_image_is_remote(self):
        refs = find_images("![diagram](https://example.com/diagram.png)\n")
        self.assertEqual(refs[0].target, "https://example.com/diagram.png")
        self.assertTrue(refs[0].remote)
        self.assertEqual(refs[0].alt, "diagram")

    def test_bare_image_url_is_remote(self):
        refs = find_images("See https://example.com/photo.jpg for details\n")
        self.assertEqual(refs[0].target, "https://example.com/photo.jpg")
        self.assertTrue(refs[0].remote)

    def test_non_image_url_is_ignored(self):
        self.assertEqual(find_images("See https://example.com/page.html\n"), [])

    def test_caption_follows_the_image(self):
        text = (
            "![[Image 7.jpg|Image]]\n"
            "\n"
            "Ending the month of August with 2,462 PRs in production\n"
            "\n"
            "# Next Heading\n"
        )
        self.assertEqual(
            find_images(text)[0].caption,
            "Ending the month of August with 2,462 PRs in production",
        )

    def test_long_prose_is_not_a_caption(self):
        text = "![x](https://example.com/a.png)\n\n" + ("word " * 60) + "\n"
        self.assertEqual(find_images(text)[0].caption, "")

    def test_heading_is_not_a_caption(self):
        text = "![x](https://example.com/a.png)\n\n## Section\n"
        self.assertEqual(find_images(text)[0].caption, "")

    def test_lead_in_ending_in_a_colon_is_not_a_caption(self):
        text = (
            "![[Image 11.jpg|Image]]\n"
            "\n"
            "When planning, two of the most common mistakes I see are:\n"
            "\n"
            "1. Accepting the agent's first design.\n"
        )
        self.assertEqual(find_images(text)[0].caption, "")

    def test_bold_subheading_is_not_a_caption(self):
        text = "![[Image 12.jpg|Image]]\n\n**Architecting bigger changes**\n"
        self.assertEqual(find_images(text)[0].caption, "")

    def test_duplicate_references_are_listed_once(self):
        text = (
            "![[Image 6.jpg|Grok Bot]]\n"
            "\n"
            "![[Image 6.jpg|Grok Bot]]\n"
        )
        self.assertEqual(len(find_images(text)), 1)

    def test_duplicate_keeps_the_first_caption(self):
        text = (
            "![[Image 6.jpg]]\n"
            "\n"
            "First caption\n"
            "\n"
            "![[Image 6.jpg]]\n"
            "\n"
            "Second caption\n"
        )
        self.assertEqual(find_images(text)[0].caption, "First caption")


class TestImageFilename(unittest.TestCase):
    def test_uses_last_path_segment(self):
        self.assertEqual(
            _image_filename("https://example.com/path/pic.png?w=10"), "pic.png"
        )

    def test_uses_format_query_parameter_for_the_extension(self):
        self.assertEqual(
            _image_filename(
                "https://pbs.twimg.com/media/HIGAeAZXoAAbGms?format=jpg&name=large"
            ),
            "HIGAeAZXoAAbGms.jpg",
        )

    def test_sanitises_unsafe_characters(self):
        self.assertEqual(
            _image_filename("https://example.com/a%20b.png"), "a_b.png"
        )


class TestImageRef(unittest.TestCase):
    def test_dataclass_fields(self):
        ref = ImageRef(target="raw/assets/x.png", remote=False, alt="x")
        self.assertEqual(ref.caption, "")


class TestImageUrls(unittest.TestCase):
    def test_extract_image_urls_markdown(self):
        text = "![alt](https://example.com/image.jpg) and ![alt2](http://example.com/pic.png)"
        urls = extract_image_urls(text)
        self.assertIn("https://example.com/image.jpg", urls)
        self.assertIn("http://example.com/pic.png", urls)

    def test_extract_image_urls_bare(self):
        text = "See https://example.com/photo.jpg for details"
        urls = extract_image_urls(text)
        self.assertIn("https://example.com/photo.jpg", urls)

    def test_extract_image_urls_ignores_local_assets(self):
        text = "![x](raw/assets/pic.png)"
        self.assertEqual(extract_image_urls(text), [])


class TestImageDownloadContentType(unittest.TestCase):
    """Image downloads must inspect Content-Type before the response closes."""

    def _download(self, url, response, dest):
        with mock.patch(
            "wikiler.images.urllib.request.urlopen",
            return_value=response,
        ):
            return _download_image(url, dest, set())

    def test_reads_content_type_while_response_is_open(self):
        response = _FakeResponse(b"img-bytes", "image/png")
        with tempfile.TemporaryDirectory() as tmp:
            name = self._download(
                "https://example.com/pic.png", response, Path(tmp)
            )
            self.assertEqual(name, "pic.png")
            self.assertEqual((Path(tmp) / name).read_bytes(), b"img-bytes")
            self.assertTrue(response.closed)

    def test_rejects_non_image_content_type(self):
        response = _FakeResponse(b"<html></html>", "text/html")
        with tempfile.TemporaryDirectory() as tmp:
            name = self._download(
                "https://example.com/page.html", response, Path(tmp)
            )
            self.assertIsNone(name)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_accepts_octet_stream_when_url_names_an_image(self):
        response = _FakeResponse(b"img-bytes", "application/octet-stream")
        with tempfile.TemporaryDirectory() as tmp:
            name = self._download(
                "https://pbs.twimg.com/media/HIGAeAZXoAAbGms?format=jpg",
                response,
                Path(tmp),
            )
            self.assertEqual(name, "HIGAeAZXoAAbGms.jpg")


if __name__ == "__main__":
    unittest.main()
