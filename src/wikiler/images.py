"""Image discovery and opt-in downloading for ingest.

Ingest is local-first. By default it performs no network I/O: it discovers the
images a source already references as local assets (``raw/assets/...`` paths
and Obsidian ``![[asset]]`` embeds), and reports any remaining remote URLs as
not downloaded. Fetching remote URLs is opt-in through ``--download-images``,
for sources that never went through the Obsidian attachment hotkey.

Discovery copies the alt text or caption the source already carries. It never
invents a description: choosing which images matter is the agent's job.
"""

from dataclasses import dataclass, replace
from pathlib import Path
import re
import urllib.error
import urllib.request
from urllib.parse import parse_qs, unquote, urlsplit

# Local attachments live here, relative to the vault root.
ASSET_DIR = "raw/assets"

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")

# A caption is the short, plain paragraph immediately after an image. Longer
# text is article prose; structural lines are not captions.
CAPTION_MAX_CHARS = 160
_CAPTION_BLOCK_PREFIXES = (
    "#", ">", "|", "```", "~~~", "**", "- ", "* ", "+ ", "![", "[", "<", "---",
)

# Obsidian embeds: ![[asset]] or ![[asset|alt]] (an alias may be a pixel width).
OBSIDIAN_EMBED_RE = re.compile(r"!\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")

# Markdown images: ![alt](target), with optional <angle brackets> for paths
# containing spaces.
MARKDOWN_IMAGE_RE = re.compile(
    r"!\[([^\]]*)\]\(\s*(?:<([^>]+)>|([^)\n]+))\s*\)"
)

# Bare URLs are only remote images when they look like one.
BARE_URL_RE = re.compile(r"https?://\S+")


@dataclass(frozen=True)
class ImageRef:
    """One image referenced by a source.

    ``target`` is a vault-relative local path (``raw/assets/x.png``) or a
    remote URL. ``alt`` and ``caption`` hold the source's own text verbatim so
    the agent does not have to restate what is already written.
    """

    target: str
    remote: bool
    alt: str = ""
    caption: str = ""


def extract_image_urls(text):
    """Return the remote image URLs found in *text*, in first-seen order."""
    return [ref.target for ref in find_images(text) if ref.remote]


def find_images(text):
    """Return the images *text* references, local and remote, deduplicated.

    Local references win no network access and are never downloaded here.
    Duplicate references collapse to one entry; alt text and captions are
    merged so the first non-empty value is kept.
    """
    lines = text.splitlines()
    ordered = []
    positions = {}

    for line_no, line in enumerate(lines):
        for ref in _refs_on_line(line):
            if not ref.caption:
                ref = replace(ref, caption=_caption_after(lines, line_no))
            key = (ref.remote, ref.target)
            if key in positions:
                existing = ordered[positions[key]]
                ordered[positions[key]] = replace(
                    existing,
                    alt=existing.alt or ref.alt,
                    caption=existing.caption or ref.caption,
                )
            else:
                positions[key] = len(ordered)
                ordered.append(ref)
    return ordered


def download_images(images, dest_dir):
    """Fetch remote refs into *dest_dir*, returning refs with local targets.

    Local refs pass through untouched. A ref whose download fails stays
    remote, so the manifest can still report it as not downloaded.
    """
    dest_dir = Path(dest_dir)
    seen_urls = set()
    resolved = []
    for ref in images:
        if not ref.remote:
            resolved.append(ref)
            continue
        local_name = _download_image(ref.target, dest_dir, seen_urls)
        if local_name is None:
            resolved.append(ref)
        else:
            resolved.append(
                replace(
                    ref,
                    target=f"{ASSET_DIR}/{local_name}",
                    remote=False,
                )
            )
    return resolved


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------


def _refs_on_line(line):
    """Return the image refs on one line, merging the regex passes."""
    refs = []

    for match in OBSIDIAN_EMBED_RE.finditer(line):
        alt = (match.group(2) or "").strip()
        if _is_width_alias(alt):
            alt = ""
        target = _obsidian_target(match.group(1))
        if target:
            refs.append(ImageRef(target=target, remote=False, alt=alt))

    for match in MARKDOWN_IMAGE_RE.finditer(line):
        alt = match.group(1).strip()
        target = (match.group(2) or match.group(3) or "").strip()
        target = _strip_optional_title(target)
        ref = _markdown_target(target, alt)
        if ref:
            refs.append(ref)

    # Bare URLs that look like images (markdown targets are deduplicated).
    for match in BARE_URL_RE.finditer(line):
        url = match.group(0).rstrip(".,;:)")
        if _looks_like_image_url(url):
            refs.append(ImageRef(target=url, remote=True))

    return refs


def _is_width_alias(alias):
    """True when an Obsidian alias is a pixel width (``300`` or ``300x200``)."""
    return bool(re.fullmatch(r"\d+(?:x\d+)?", alias.strip()))


def _obsidian_target(raw):
    """Resolve an Obsidian embed target to a vault-relative asset path.

    Returns ``""`` for embeds that are not images (notes, PDFs, audio).
    """
    target = _clean_local_path(raw)
    if not target:
        return ""
    if "/" not in target:
        target = f"{ASSET_DIR}/{target}"
    return target if _is_image_path(target) else ""


def _markdown_target(raw, alt):
    """Classify a markdown image target as local, remote, or unknown."""
    target = raw.strip()
    if target.startswith(("http://", "https://")):
        return ImageRef(target=target, remote=True, alt=alt)
    local = _clean_local_path(target)
    if local.startswith(f"{ASSET_DIR}/") and _is_image_path(local):
        return ImageRef(target=local, remote=False, alt=alt)
    return None


def _is_image_path(path):
    """True when a local path names a file with an image extension."""
    return path.lower().endswith(IMAGE_EXTENSIONS)


def _strip_optional_title(target):
    """Drop a markdown link title: ``raw/assets/x.png "Title"``."""
    return re.split(r"\s+(?=[\"'])", target, maxsplit=1)[0].strip()


def _clean_local_path(raw):
    """Normalise a vault-relative path: drop leading ``./``, ``/``."""
    target = unquote(raw.strip()).replace("\\", "/")
    while target.startswith("./"):
        target = target[2:]
    return target.lstrip("/")


def _looks_like_image_url(url):
    """True when a bare URL names an image by extension or ``format`` query."""
    parts = urlsplit(url)
    if parts.path.lower().endswith(IMAGE_EXTENSIONS):
        return True
    fmt = parse_qs(parts.query).get("format", [""])[0].lower()
    return f".{fmt}" in IMAGE_EXTENSIONS


def _caption_after(lines, line_no):
    """Return the source's caption for an image on *line_no*, or ``""``.

    Mechanically accepts only the next non-empty line when it reads as a short
    plain paragraph. Headings, lists, links, longer prose, and lead-ins ending
    in a colon are article structure, not captions, so they are left alone.
    """
    for line in lines[line_no + 1:]:
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith(_CAPTION_BLOCK_PREFIXES):
            return ""
        if candidate.endswith(":"):
            return ""
        if re.match(r"^\d+[.)]\s", candidate):
            return ""
        if len(candidate) > CAPTION_MAX_CHARS:
            return ""
        return candidate
    return ""


# ---------------------------------------------------------------------------
# Downloading (opt-in)
# ---------------------------------------------------------------------------


def _image_filename(url):
    """Derive a clean filename for an image URL.

    Uses the URL's last path segment; when that has no extension, the
    ``format`` query parameter (e.g. Twitter's ``?format=jpg``) supplies it.
    """
    parts = urlsplit(url)
    name = unquote(parts.path.rsplit("/", 1)[-1])
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name).strip("._") or "image"
    if "." not in name:
        fmt = parse_qs(parts.query).get("format", [""])[0].lower()
        if f".{fmt}" in IMAGE_EXTENSIONS:
            name = f"{name}.{fmt}"
    return name


def _download_image(url, dest_dir, seen_urls):
    """Download *url* to *dest_dir*. Returns the local filename or None.

    *seen_urls* is a set of already-downloaded URLs (to avoid re-downloads
    within one run). A file already present on disk is reused, so re-ingesting
    a source never duplicates its assets and a previously failed download can
    be retried.
    """
    if url in seen_urls:
        return None
    seen_urls.add(url)

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / _image_filename(url)
    if dest.exists():
        return dest.name

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "wikiler/0.1 (ingest)"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            # Read the headers while the response is still open; the object is
            # not usable after the `with` block exits.
            ctype = resp.headers.get("Content-Type", "")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return None

    content_type = ctype.split(";")[0].strip().lower()
    # Verify it looks like an image by content-type if available.
    if content_type and not content_type.startswith("image/"):
        # Still accept when the URL itself names an image (extension or
        # ``format`` query), even if the server mislabels the content type.
        if not _looks_like_image_url(url):
            return None

    dest.write_bytes(data)
    return dest.name
