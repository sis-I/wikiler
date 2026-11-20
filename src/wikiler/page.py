"""Shared page helpers: frontmatter parse/render, index sync, log dedupe.

These are mechanical writing helpers owned by the engine and imported by
lint, ingest, and query.  The linter still owns linting; this module owns
writing.  Having one implementation of each helper keeps the frontmatter
schema, the index format, and the log dedupe rule from drifting across
commands.
"""

from dataclasses import dataclass, field
from pathlib import Path
import json
import re

from .log import read_log, today

# Frontmatter is delimited by lines that are exactly "---".
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
FRONTMATTER_OPEN_RE = re.compile(r"^---[ \t]*\n")
FRONTMATTER_CLOSE_RE = re.compile(r"^---[ \t]*$", re.MULTILINE)

# Dates written to frontmatter, e.g. 2026-11-13.
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Characters that start a YAML indicator when they begin a scalar value.
YAML_INDICATORS = "-?:,[]{}#&*!|>'\"%@`"

# Index links with a path target, e.g. [[concepts/foo|Foo]].
INDEX_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")

# Wiki subdirectories that contain pages, and the page type each holds.
PAGE_DIRS = ("sources", "entities", "concepts", "synthesis", "queries")
PAGE_TYPE_BY_DIR = {
    "sources": "source",
    "entities": "entity",
    "concepts": "concept",
    "synthesis": "synthesis",
    "queries": "query",
}

# Frontmatter fields, in canonical render order.
REQUIRED_FRONTMATTER_FIELDS = ["type", "title", "sources", "created", "updated", "tags"]


def is_quoted(value):
    """Return True when *value* is wrapped in matching YAML quotes."""
    return (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in ("'", '"')
    )


def _split_flow_items(inner):
    """Split a bracketless flow list, respecting quoted commas.

    Raises ``ValueError`` for an unterminated quoted item.
    """
    items = []
    buf = []
    quote = None
    escaped = False
    for ch in inner:
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\" and quote == '"':
                escaped = True
            elif ch == quote:
                quote = None
            buf.append(ch)
        elif ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif ch == ",":
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if quote:
        raise ValueError("flow list has an unterminated quoted item")
    items.append("".join(buf))
    return items


def _unquote_flow_item(item):
    item = item.strip()
    return item[1:-1] if is_quoted(item) else item


def _parse_flow_list(value):
    """Parse a YAML flow list like [a, b, c] into a list of strings."""
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [_unquote_flow_item(item) for item in _split_flow_items(inner)]


def strip_yaml_comment(value):
    """Remove a trailing YAML comment that is outside quotes."""
    quote = None
    escaped = False
    for i, ch in enumerate(value):
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\" and quote == '"':
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or value[i - 1].isspace()):
            return value[:i].rstrip()
    return value


def flow_list_error(value):
    """Return a message when a flow list would not parse, else None.

    Validates the shape the wiki schema relies on: one bracketed list, with
    no empty items, no unterminated quotes, and no unquoted item that YAML
    would read as a mapping.
    """
    if not value.endswith("]"):
        return "flow list is not closed with ']'"
    inner = value[1:-1]
    if not inner.strip():
        return None
    try:
        items = _split_flow_items(inner)
    except ValueError as exc:
        return str(exc)
    if any(not item.strip() for item in items):
        return "flow list has an empty item"
    for item in items:
        stripped = item.strip()
        if not is_quoted(stripped) and ": " in stripped:
            return f"flow list item {stripped!r} would parse as a mapping"
    return None


def parse_frontmatter(text):
    """Parse YAML frontmatter from markdown text.

    Returns a dict of fields, or None if no frontmatter block is present.
    This is a small parser tuned to the wiki frontmatter format (scalar
    values and flow lists), not a full YAML parser.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    result = {}
    for line in m.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = strip_yaml_comment(value.strip())
        if value.startswith("[") and value.endswith("]"):
            try:
                result[key] = _parse_flow_list(value)
            except ValueError:
                # Keep the raw text so the linter can report the fault
                # instead of crashing on malformed input.
                result[key] = value
        elif (value.startswith('"') and value.endswith('"')) or \
             (value.startswith("'") and value.endswith("'")):
            result[key] = value[1:-1]
        else:
            result[key] = value
    return result


def scalar_needs_quotes(value):
    """Return True when YAML would misread *value* as a non-string scalar.

    Covers the cases the wiki schema actually sees: an indicator character
    in the first position, a mapping indicator (``: ``), and a comment
    indicator (`` #``).
    """
    if not value:
        return False
    if value[0] in YAML_INDICATORS:
        return True
    return ": " in value or " #" in value


def quote_scalar(value):
    """Return *value* as a double-quoted YAML scalar (JSON strings are YAML)."""
    return json.dumps(str(value), ensure_ascii=False)


def frontmatter_key(line):
    """Return the top-level key of a frontmatter line, or None."""
    if not line or line[0].isspace() or ":" not in line:
        return None
    key = line.partition(":")[0].strip()
    return key if re.fullmatch(r"[A-Za-z0-9_-]+", key) else None


def _set_frontmatter_key(lines, key, value):
    """Set *key* to *value* in place."""
    for i, line in enumerate(lines):
        if frontmatter_key(line) == key:
            lines[i] = f"{key}: {value}"
            return


def split_frontmatter_text(text):
    """Split text into (opening delimiter, block, body) preserving the body.

    ``FRONTMATTER_RE`` also swallows blank lines after the closing ``---``,
    so rebuilding from its match would drop them. This helper locates the
    exact closing delimiter line and returns the body untouched.

    Returns None when *text* has no frontmatter block.
    """
    opening = FRONTMATTER_OPEN_RE.match(text)
    if not opening:
        return None
    open_end = opening.end()
    closing = FRONTMATTER_CLOSE_RE.search(text, open_end)
    if not closing:
        return None
    block = text[open_end:closing.start()]
    if block.endswith("\n"):
        block = block[:-1]
    body_start = closing.end()
    if body_start < len(text) and text[body_start] == "\n":
        body_start += 1
    return text[:open_end], block, text[body_start:]


def normalise_frontmatter(text, page_type=None, fallback_title=None,
                          page_date=None, touch_updated=False):
    """Normalise a page's frontmatter without touching its body.

    Quotes scalars YAML would misread, ensures the required keys exist, and
    applies the ``created``/``updated`` contract: ``created`` is only filled
    in when absent; ``updated`` moves to *page_date* only when another line
    in the page changed, or when *touch_updated* is set (an operation that
    touched the page even though only its dates changed). Unknown keys and
    their order are preserved.

    Returns ``(new_text, changed)``. When nothing needed changing the
    original *text* is returned unchanged.
    """
    split = split_frontmatter_text(text)
    if split is None:
        # No block yet: add one, keeping the body verbatim after a blank line.
        opening, block, body = "---\n", "", "\n" + text
    else:
        opening, block, body = split
    lines = block.splitlines()

    date_str = page_date or today()

    present = set()
    other_changed = False
    created_added = False
    updated_missing = "updated" not in {
        frontmatter_key(line) for line in lines
    }

    new_lines = []
    for line in lines:
        key = frontmatter_key(line)
        if key is None:
            new_lines.append(line)
            continue
        present.add(key)
        raw = line.partition(":")[2].strip()
        value = strip_yaml_comment(raw)
        new_line = line
        is_list = value.startswith("[") and value.endswith("]")
        is_block = value in ("|", ">")
        if not (is_list or is_block or is_quoted(value)):
            if scalar_needs_quotes(raw):
                new_line = f"{key}: {quote_scalar(raw)}"
                other_changed = True
        new_lines.append(new_line)

    defaults = {
        "type": page_type or "source",
        "title": fallback_title or "Untitled",
        "sources": "[]",
        "created": date_str,
        "updated": date_str,
        "tags": "[]",
    }
    for field_name in REQUIRED_FRONTMATTER_FIELDS:
        if field_name in present:
            continue
        insert_at = 0
        for i, line in enumerate(new_lines):
            key = frontmatter_key(line)
            if key in REQUIRED_FRONTMATTER_FIELDS and \
                    REQUIRED_FRONTMATTER_FIELDS.index(key) < \
                    REQUIRED_FRONTMATTER_FIELDS.index(field_name):
                insert_at = i + 1
        default = defaults[field_name]
        if field_name in ("sources", "tags"):
            rendered = default  # empty flow list
        elif scalar_needs_quotes(default):
            rendered = quote_scalar(default)
        else:
            rendered = default
        new_lines.insert(insert_at, f"{field_name}: {rendered}")
        present.add(field_name)
        if field_name == "created":
            created_added = True
        elif field_name != "updated":
            other_changed = True

    if not updated_missing and (other_changed or created_added or touch_updated):
        _set_frontmatter_key(new_lines, "updated", date_str)

    new_text = opening + "\n".join(new_lines) + "\n---\n" + body
    return new_text, new_text != text


def find_page_files(vault):
    """Return list of Paths for wiki pages in the page subdirectories."""
    files = []
    wiki_dir = Path(vault) / "wiki"
    if not wiki_dir.exists():
        return files
    for sub in PAGE_DIRS:
        subdir = wiki_dir / sub
        if subdir.is_dir():
            files.extend(sorted(subdir.glob("*.md")))
    return files


@dataclass
class IndexUpdate:
    """Outcome of an index reconciliation."""

    added: list[str] = field(default_factory=list)  # dir/slug
    dangling: list[str] = field(default_factory=list)  # dir/slug targets


def index_target_rel(target):
    """Normalise an index link target to wiki-relative ``dir/slug`` form."""
    return target[len("wiki/"):] if target.startswith("wiki/") else target


def find_dangling_index_entries(vault, content=None):
    """Return index targets whose page file no longer exists.

    Only path-prefixed targets (``dir/slug`` or ``wiki/dir/slug``) count as
    index entries; title-style links are lint's business. Entries are never
    deleted here: `sync` reports them and `lint --fix` owns removal.
    """
    index_path = Path(vault) / "wiki" / "index.md"
    if content is None:
        if not index_path.exists():
            return []
        content = index_path.read_text(encoding="utf-8")

    wiki_dir = Path(vault) / "wiki"
    prefixes = tuple(f"{d}/" for d in PAGE_DIRS) + ("wiki/",)
    dangling = []
    for line in content.splitlines():
        for match in INDEX_LINK_RE.finditer(line):
            target = match.group(1).strip()
            if not target.startswith(prefixes):
                continue
            rel = index_target_rel(target)
            if not (wiki_dir / f"{rel}.md").is_file() and target not in dangling:
                dangling.append(target)
    return dangling


def update_index(vault):
    """Ensure all wiki pages are present in wiki/index.md.

    Writes only when an entry was appended, so a fully indexed vault is
    left byte-for-byte unchanged. Returns an :class:`IndexUpdate` naming
    the entries added and any dangling entries found.
    """
    index_path = Path(vault) / "wiki" / "index.md"
    if not index_path.exists():
        index_path.write_text("# Index\n", encoding="utf-8")

    content = index_path.read_text(encoding="utf-8")
    page_files = find_page_files(vault)

    result = IndexUpdate()
    new_lines = content.splitlines()

    # Any path-prefixed link form counts as listed: [[dir/slug|Title]],
    # [[dir/slug]], and [[wiki/dir/slug|Title]] all name the same page.
    prefixes = tuple(f"{d}/" for d in PAGE_DIRS)
    indexed = set()
    for match in INDEX_LINK_RE.finditer(content):
        target = match.group(1).strip()
        if target.startswith(prefixes) or target.startswith("wiki/"):
            indexed.add(index_target_rel(target))

    for page_path in page_files:
        rel_path = page_path.relative_to(Path(vault) / "wiki")
        rel_no_ext = str(rel_path)[:-3]

        if rel_no_ext in indexed:
            continue

        fm = parse_frontmatter(page_path.read_text(encoding="utf-8"))
        title = fm.get("title") if fm else page_path.stem.replace("-", " ").title()
        entry = f"- [[{rel_no_ext}|{title}]]"

        # Find appropriate section or just append
        category = rel_path.parts[0].capitalize()
        section_header = f"## {category}"

        sec_idx = -1
        for i, line in enumerate(new_lines):
            if line.strip() == section_header:
                sec_idx = i
                break

        if sec_idx != -1:
            new_lines.insert(sec_idx + 1, entry)
        else:
            new_lines.append(f"\n{section_header}")
            new_lines.append(entry)
        result.added.append(rel_no_ext)

    if result.added:
        written = "\n".join(new_lines) + "\n"
        index_path.write_text(written, encoding="utf-8")
        result.dangling = find_dangling_index_entries(vault, written)
    else:
        result.dangling = find_dangling_index_entries(vault, content)
    return result


def log_has_entry(vault, op, title):
    """Return True if wiki/log.md already contains an entry for *op* | *title*.

    The log is append-only: existing entries are never rewritten.  Callers use
    this to skip appending a duplicate entry, which keeps re-runs (e.g.
    re-ingesting the same source) idempotent.
    """
    marker = f"{op} | {title}"
    return any(marker in line for line in read_log(vault).splitlines())
