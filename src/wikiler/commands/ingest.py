"""ingest command: scaffold a source page from a raw source.

Ingest is mechanical. It reads a raw source under raw/, derives a title and
tags, and scaffolds exactly one page under wiki/sources/<slug>.md with valid
frontmatter and explicit TODO markers for the parts that require judgment:

- Key claims
- Structured summary
- Entities
- Concepts
- Images (only when the source references at least one image)

The agent reads the source, discusses it, and fills those sections. The engine
never writes a sentence about the source's content. Re-ingesting an existing
page leaves its body untouched (including text the agent authored), fills in
missing required frontmatter keys, keeps ``created``, and refreshes
``updated``.

Images are local-first. By default ingest performs no network I/O: it lists the
images the source already references under raw/assets/ (Obsidian ``![[asset]]``
embeds and ``raw/assets/...`` links) with their alt text or caption, and
reports remaining remote URLs as not downloaded. ``--download-images`` opts in
to fetching those URLs, for sources that never went through Obsidian. The
raw/ source file itself is never modified: it is human-owned and immutable.
All engine writes go under wiki/ and output/ (plus raw/assets/ for images
downloaded from external URLs).

Two flags shape the run. ``--json`` prints the manifest as one JSON object and
nothing else on stdout, so it can be piped. ``--force`` is destructive: it
rewrites an existing page's scaffold, discarding the agent-authored body and
restoring the TODO markers. ``created`` is preserved (the page existed
before), ``updated`` is refreshed.
"""

from pathlib import Path
import json
import re

from ..vault import resolve_target_vault, vault_paths, is_within_vault
from ..log import append_log_entry, today
from ..output import report_error
from ..page import (
    ISO_DATE_RE,
    log_has_entry,
    normalise_frontmatter,
    parse_frontmatter,
    quote_scalar,
    scalar_needs_quotes,
    update_index,
)
from ..images import find_images, download_images


def _slugify(text):
    """Convert a title to a kebab-case filename stem."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "source"


def _parse_frontmatter_local(text):
    """Parse YAML-ish frontmatter delimited by --- lines.

    Returns a (frontmatter_dict, body) tuple. When no frontmatter is present,
    returns ({}, text).
    """
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm_text = text[4:end]
    body = text[end + 5:]
    fm = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        fm[key] = val
    return fm, body


def _extract_title(fm, body, source_name):
    """Derive the page title: frontmatter title, then first H1, then filename."""
    if fm.get("title"):
        return fm["title"]
    match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return Path(source_name).stem.replace("-", " ").replace("_", " ").title()


def _extract_tags(fm):
    """Return a cleaned list of tags from frontmatter.

    Supports inline YAML sequences like [a, b], comma-separated strings, and
    real lists.
    """
    raw = fm.get("tags", [])
    if isinstance(raw, str):
        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            raw = raw[1:-1]
        raw = [t.strip() for t in raw.split(",") if t.strip()]
    tags = []
    for t in raw:
        t = str(t).strip().strip('"').strip("'")
        if t:
            tags.append(t)
    return tags


# ---------------------------------------------------------------------------
# Scaffold rendering
# ---------------------------------------------------------------------------

# Section heading and the TODO hint rendered under it. The Images section is
# conditional: a source without images gets no Images section and no marker.
TODO_SECTIONS = (
    ("Key claims", "extract and phrase the key claims"),
    ("Structured summary", "write the structured summary"),
    ("Entities", "decide which entities warrant pages"),
    ("Concepts", "decide which concepts warrant pages"),
    (
        "Images",
        "describe only images whose meaning the prose or caption does not "
        "already capture; skip decorative images",
    ),
)

TODO_RE = re.compile(r"<!-- TODO: agent — .+? -->")

IMAGES_SECTION = "Images"


def _render_flow_list(items):
    """Render a YAML flow list, quoting items YAML would misread."""
    rendered = []
    for item in items:
        item = str(item)
        if not item or "," in item or scalar_needs_quotes(item):
            rendered.append(quote_scalar(item))
        else:
            rendered.append(item)
    return "[" + ", ".join(rendered) + "]"


def _render_scaffold(title, source_name, tags, created, updated, images):
    """Render a source page scaffold: frontmatter plus TODO-marked sections.

    The Images section appears only when the source references an image. Each
    entry keeps the source's own alt text or caption, so the agent does not
    restate what is already written.
    """
    source_file = Path(source_name).name
    lines = [
        "---",
        "type: source",
        f"title: {quote_scalar(title)}",
        f"sources: {_render_flow_list([source_file])}",
        f"created: {created}",
        f"updated: {updated}",
        f"tags: {_render_flow_list(tags)}",
        "---",
        "",
        f"# {title}",
        "",
        "## Source metadata",
        "",
        f"- **Source file:** {source_file}",
        "",
    ]
    for heading, hint in TODO_SECTIONS:
        if heading == IMAGES_SECTION and not images:
            continue
        lines.append(f"## {heading}")
        lines.append("")
        lines.append(f"<!-- TODO: agent — {hint} -->")
        lines.append("")
        if heading == IMAGES_SECTION:
            for ref in images:
                lines.append(_render_image_entry(ref))
            lines.append("")
    return "\n".join(lines)


def _render_image_entry(ref):
    """Render one image entry with the source's alt text and caption."""
    alt = _markdown_safe(ref.alt)
    caption = ref.caption.strip()
    if caption == alt:
        caption = ""

    if ref.remote:
        entry = f"- {ref.target}"
        text = " — ".join(part for part in (alt, caption) if part)
        if text:
            entry += f" — {text}"
        entry += " (not downloaded; rerun with --download-images)"
        return entry

    alt_text = alt or Path(ref.target).name
    path = f"<{ref.target}>" if " " in ref.target else ref.target
    entry = f"- ![{alt_text}]({path})"
    if caption:
        entry += f" — {caption}"
    return entry


def _markdown_safe(text):
    """Keep alt text from breaking the surrounding markdown image syntax."""
    return text.replace("[", "(").replace("]", ")").replace("\n", " ").strip()


def _image_summary(images):
    """Summarise discovered images for the manifest line."""
    local = sum(1 for ref in images if not ref.remote)
    remote = len(images) - local
    line = f"images: {local} local"
    if remote:
        line += (
            f", {remote} remote not downloaded "
            f"(rerun with --download-images)"
        )
    return line


def _remaining_todos(text):
    """Return the scaffold sections whose TODO marker is still present.

    Keyed on the section heading rather than the hint prose, so rewording a
    hint cannot silently drop a section from the manifest.
    """
    open_sections = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            open_sections.setdefault(current, False)
        elif current and TODO_RE.search(line):
            open_sections[current] = True
    return [heading for heading, _hint in TODO_SECTIONS if open_sections.get(heading)]


def _vault_relative(vault, path):
    """Return *path* as a vault-relative POSIX path.

    Falls back to the absolute path when the target sits outside the vault,
    so the manifest still names the file that was written.
    """
    root = Path(vault).resolve()
    try:
        return Path(path).resolve().relative_to(root).as_posix()
    except ValueError:
        return Path(path).as_posix()


# ---------------------------------------------------------------------------
# Top-level ingest command
# ---------------------------------------------------------------------------

def cmd_ingest(args):
    """Scaffold one source page from a raw source and sync index/log."""
    vault = resolve_target_vault(getattr(args, "vault", None))
    source = getattr(args, "source", None)
    as_json = getattr(args, "json", False)
    force = getattr(args, "force", False)
    paths = vault_paths(vault)

    raw_source = paths["raw"] / source
    if not raw_source.exists():
        return report_error(f"error: source not found: {raw_source}", as_json)
    if not raw_source.is_file():
        return report_error(f"error: not a file: {raw_source}", as_json)
    if not is_within_vault(raw_source, paths["raw"]):
        return report_error(f"error: source must be within raw/: {source}", as_json)

    raw_text = raw_source.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter_local(raw_text)
    title = _extract_title(fm, body, source)
    tags = _extract_tags(fm)
    date = today()

    paths["wiki_sources"].mkdir(parents=True, exist_ok=True)
    target = paths["wiki_sources"] / f"{_slugify(title)}.md"
    is_new = not target.exists()

    # Images are local-first. Discovery is read-only and never touches the
    # network; only --download-images fetches remaining remote URLs. Downloads
    # are idempotent, and an existing page's body is never rewritten, so only a
    # newly scaffolded page lists the images.
    images = find_images(raw_text)
    if args.download_images:
        images = download_images(images, paths["raw_assets"])

    if is_new or force:
        # A forced ingest starts the scaffold over: the agent-authored body
        # is discarded and the TODO markers come back. `created` stays as it
        # was, because the page existed before this run; `updated` moves.
        created_date = date
        if not is_new:
            existing_fm = parse_frontmatter(target.read_text(encoding="utf-8"))
            existing_created = (existing_fm or {}).get("created", "")
            if ISO_DATE_RE.match(existing_created):
                created_date = existing_created
        target.write_text(
            _render_scaffold(title, source, tags, created_date, date, images),
            encoding="utf-8",
        )
    else:
        # The body is the agent's: never rewrite it, never overwrite a
        # resolved TODO. Only frontmatter mechanics are ours.
        text = target.read_text(encoding="utf-8")
        new_text, _changed = normalise_frontmatter(
            text,
            page_type="source",
            fallback_title=title,
            page_date=date,
            touch_updated=True,
        )
        if new_text != text:
            target.write_text(new_text, encoding="utf-8")

    update_index(vault)

    # Idempotent: the log is append-only, so re-ingesting the same source
    # must not append a duplicate entry.
    if not log_has_entry(vault, "ingest", title):
        append_log_entry(vault, "ingest", title)

    page_text = target.read_text(encoding="utf-8")
    todos = _remaining_todos(page_text)
    manifest = {
        "source": _vault_relative(vault, raw_source),
        "page": _vault_relative(vault, target),
        "title": title,
        "created": is_new,
        "todos": todos,
        "images": len(images),
    }
    if as_json:
        print(json.dumps(manifest, ensure_ascii=False))
        return 0

    state = "created" if is_new else ("rewritten" if force else "updated")
    page_rel = target.relative_to(vault)
    print(f"ingested {source} -> {page_rel} ({state})")
    if todos:
        print(f"  TODO: {', '.join(todos)}")
    print(f"  {_image_summary(images)}")
    return 0


def register(subparsers):
    parser = subparsers.add_parser(
        "ingest", help="Scaffold a source page from a raw source"
    )
    parser.add_argument("source", help="Path to source file within raw/")
    parser.add_argument(
        "--download-images",
        action="store_true",
        help=(
            "Fetch remote image URLs into raw/assets/ (default: list local "
            "assets only, no network I/O)"
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the scaffold manifest as JSON, and nothing else on stdout",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Destructive: rewrite an existing page's scaffold, discarding the "
            "agent-authored body"
        ),
    )
    parser.set_defaults(func=cmd_ingest)
