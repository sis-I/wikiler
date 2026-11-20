"""Lint engine: health-check the wiki for structural faults.

Scans every wiki page plus the index and log, and reports findings grouped
by severity: errors -> warnings -> info.

Checks performed:
- frontmatter: every page must have valid YAML frontmatter with the
  required fields (type, title, sources, created, updated, tags)
- yaml: scalar values YAML would misread and unparseable flow lists
- dates: created/updated must be ISO dates, with created <= updated
- filenames: page files must be kebab-case
- h1: every page must have a Title Case H1, and only one H1
- title: frontmatter title and H1 must agree after a type suffix is stripped
- wikilinks: links in pages, index, and log must use the full
  [[dir/slug|Page Title]] form
- broken links: wikilink targets must resolve to an existing page
- sources: frontmatter sources must match a file under raw/
- orphans: pages with zero inbound links, counting links from the index

The linter judges form only. Contradictions, staleness, and coverage gaps
stay with the agent.
"""

from dataclasses import dataclass, field
from datetime import date as date_cls
from enum import Enum
from pathlib import Path
import re

from .log import append_log_entry, log_has_entry_on_date
from .page import (
    INDEX_LINK_RE,
    ISO_DATE_RE,
    PAGE_DIRS,
    PAGE_TYPE_BY_DIR,
    REQUIRED_FRONTMATTER_FIELDS,
    find_page_files,
    flow_list_error,
    frontmatter_key,
    index_target_rel,
    is_quoted,
    parse_frontmatter,
    scalar_needs_quotes,
    strip_yaml_comment,
)


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


SEVERITY_ORDER = (Severity.ERROR, Severity.WARNING, Severity.INFO)


@dataclass
class Finding:
    severity: Severity
    file: str  # path relative to vault root
    message: str
    line: int | None = None


@dataclass(frozen=True)
class PageIdentity:
    """Identity data used to resolve a wikilink to a page."""

    canonical: str
    path: Path
    title: str
    h1: str


@dataclass
class AliasMap:
    """Page aliases mapped to canonical page identifiers."""

    identities: dict[str, PageIdentity]
    aliases: dict[str, set[str]]

    def resolve(self, alias):
        """Return canonical identifiers for *alias*."""
        return self.aliases.get(alias.strip(), set())

    def resolve_link(self, target, display=None):
        """Resolve a link target, narrowed by its display text when present."""
        candidates = self.resolve(target)
        if display is None:
            return candidates
        display_candidates = self.resolve(display)
        if not display_candidates:
            return candidates
        narrowed = candidates & display_candidates
        if narrowed:
            return narrowed
        if len(candidates) == 1:
            return candidates
        return set()

    def identity(self, canonical):
        """Return the page identity for *canonical*."""
        return self.identities.get(canonical)


@dataclass(frozen=True)
class LinkRewrite:
    """One wikilink rewritten by lint fix."""

    file: str
    original: str
    replacement: str


@dataclass(frozen=True)
class IndexEntryRemoval:
    """One index entry removed because its target file was missing."""

    file: str
    target: str
    link: str


@dataclass
class FixResult:
    """Outcome of a lint fix run."""

    files_changed: list[str] = field(default_factory=list)
    links_rewritten: list[LinkRewrite] = field(default_factory=list)
    index_entries_removed: list[IndexEntryRemoval] = field(default_factory=list)
    log_written: bool = False
    log_entry: str | None = None

    @property
    def changed(self):
        return bool(self.links_rewritten or self.index_entries_removed)

    def record_file_changed(self, relative):
        """Record a changed file once, preserving repair order."""
        if relative not in self.files_changed:
            self.files_changed.append(relative)


@dataclass
class LintResult:
    findings: list[Finding] = field(default_factory=list)

    def add(self, severity, file, message, line=None):
        self.findings.append(Finding(severity, file, message, line))

    def by_severity(self, severity):
        return [f for f in self.findings if f.severity == severity]

    @property
    def errors(self):
        return self.by_severity(Severity.ERROR)

    @property
    def warnings(self):
        return self.by_severity(Severity.WARNING)

    @property
    def infos(self):
        return self.by_severity(Severity.INFO)

    @property
    def has_errors(self):
        return len(self.errors) > 0


# Frontmatter is delimited by lines that are exactly "---".
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

VALID_TYPES = {"source", "entity", "concept", "synthesis", "query"}

# Minor words that may stay lowercase in Title Case (not first/last word).
MINOR_WORDS = {
    "a", "an", "the", "and", "or", "but", "for", "nor", "on", "at", "to",
    "from", "by", "with", "in", "is", "of", "vs", "vs.", "&", "via", "per",
}

# Page files use kebab-case; index.md and log.md are exempt because they are
# not page files at all.
KEBAB_CASE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.md$")

# Type suffixes the wiki tolerates on a title or H1, e.g. "Foo (concept)".
TYPE_SUFFIX_RE = re.compile(
    r"\s+\((?:entity|concept|source|synthesis)\)\s*$", re.IGNORECASE
)

# Specialist files in wiki/ that participate in link scanning but are not
# page files subject to frontmatter/H1/filename checks.
SPECIAL_LINK_FILES = ("index.md", "log.md")


def extract_wikilinks(text):
    """Return list of (raw, target, display) for each [[...]] wikilink."""
    links = []
    for m in WIKILINK_RE.finditer(text):
        raw = m.group(1)
        if "|" in raw:
            target, _, display = raw.partition("|")
        else:
            target, display = raw, raw
        links.append((raw, target.strip(), display.strip()))
    return links


def _strip_type_suffix(text):
    """Strip a trailing parenthetical type suffix like ' (concept)'."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()


def _strip_allowed_type_suffix(text):
    """Strip only the type suffixes the wiki allows on titles and H1s."""
    return TYPE_SUFFIX_RE.sub("", text).strip()


def _normalise_title(text):
    """Collapse whitespace so title/H1 comparison ignores formatting."""
    return " ".join(text.split())


def _frontmatter_lines(text):
    """Return ``(line_number, key, raw_value)`` for top-level frontmatter keys.

    ``line_number`` is 1-based within the whole file. Nested lines, comments,
    and a missing closing delimiter produce no entries; the missing
    frontmatter itself is reported by the caller.
    """
    lines = text.splitlines()
    if not lines or not re.fullmatch(r"---[ \t]*", lines[0]):
        return []
    entries = []
    for end in range(1, len(lines)):
        if not re.fullmatch(r"---[ \t]*", lines[end]):
            continue
        for idx in range(1, end):
            line = lines[idx]
            key = frontmatter_key(line)
            if key is None:
                continue
            entries.append((idx + 1, key, line.partition(":")[2].strip()))
        return entries
    return []


def _key_line(entries, key):
    """Return the 1-based line of *key* in frontmatter entries, or None."""
    for line_no, entry_key, _value in entries:
        if entry_key == key:
            return line_no
    return None


def _h1_lines(lines):
    """Return ``(line_number, text)`` for every body H1 outside fenced code."""
    start = 0
    if lines and re.fullmatch(r"---[ \t]*", lines[0]):
        for idx in range(1, len(lines)):
            if re.fullmatch(r"---[ \t]*", lines[idx]):
                start = idx + 1
                break

    h1s = []
    fence = None
    for idx in range(start, len(lines)):
        line = lines[idx]
        stripped = line.lstrip()
        fence_match = re.match(r"(`{3,}|~{3,})", stripped)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker[0]
            elif marker[0] == fence:
                fence = None
            continue
        if fence is None and line.startswith("# "):
            h1s.append((idx + 1, line[2:].strip()))
    return h1s


def _special_link_files(vault):
    """Return existing wiki/index.md and wiki/log.md paths."""
    files = []
    wiki_dir = Path(vault) / "wiki"
    for name in SPECIAL_LINK_FILES:
        path = wiki_dir / name
        if path.is_file():
            files.append(path)
    return files


def _raw_source_names(vault):
    """Return ``(relative_paths, filenames)`` for files under raw/."""
    raw_dir = Path(vault) / "raw"
    rel_paths = set()
    names = set()
    if not raw_dir.is_dir():
        return rel_paths, names
    for path in raw_dir.rglob("*"):
        if path.is_file():
            names.add(path.name)
            rel_paths.add(str(path.relative_to(raw_dir)))
    return rel_paths, names


def _raw_source_exists(entry, raw_paths, raw_names):
    """True when *entry* names a file under raw/.

    Accepts both a path relative to raw/ and the filename-only convention the
    wiki uses, so moving a source between raw/ subdirectories does not break
    the check.
    """
    entry = entry.strip()
    if not entry:
        return False
    if entry in raw_paths:
        return True
    return Path(entry).name in raw_names


def _is_wiki_target(entry, stem_index, path_index):
    """True when a frontmatter sources entry names a wiki page."""
    target = entry.strip()
    if not target:
        return False
    if "/" in target:
        candidate = target[:-3] if target.endswith(".md") else target
        if candidate.startswith("wiki/"):
            candidate = candidate[len("wiki/"):]
        return candidate in path_index
    stem = target[:-3] if target.endswith(".md") else target
    return stem in stem_index


def result_to_dict(result):
    """Serialise a LintResult into the ``lint --json`` shape."""
    findings = []
    for severity in SEVERITY_ORDER:
        for finding in result.by_severity(severity):
            findings.append({
                "severity": finding.severity.value,
                "file": finding.file,
                "line": finding.line,
                "message": finding.message,
            })
    return {
        "command": "lint",
        "summary": {
            "errors": len(result.errors),
            "warnings": len(result.warnings),
            "info": len(result.infos),
        },
        "findings": findings,
    }


def is_title_case(text):
    """Return True if text reads as Title Case.

    Each significant word should start with an uppercase letter. All-caps
    tokens (acronyms) and tokens starting with a digit or symbol are OK.
    Minor words may stay lowercase when not first or last. A trailing
    parenthetical type suffix (e.g. ' (concept)') is ignored.
    """
    text = _strip_type_suffix(text)
    words = text.split()
    if not words:
        return True
    for i, word in enumerate(words):
        core = word.lstrip("(").lstrip("[").rstrip(")").rstrip("]").rstrip(":,.;")
        if not core:
            continue
        # All-caps acronym, or starts with digit/symbol -> OK.
        if core.isupper() or not core[0].isalpha():
            continue
        # First or last word must start uppercase.
        if i == 0 or i == len(words) - 1:
            if not core[0].isupper():
                return False
            continue
        # Middle word: must start uppercase unless it's a minor word.
        if core[0].isupper():
            continue
        if core.lower() in MINOR_WORDS:
            continue
        return False
    return True


def build_alias_map(vault):
    """Build a map from page identity aliases to canonical page paths."""
    identities = {}
    aliases = {}

    def add_alias(alias, canonical):
        alias = alias.strip()
        if alias:
            aliases.setdefault(alias, set()).add(canonical)

    for page_path in find_page_files(vault):
        text = page_path.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(text) or {}
        h1_lines = _h1_lines(text.splitlines())
        title = frontmatter.get("title", "")
        if not isinstance(title, str):
            title = ""
        h1 = h1_lines[0][1] if h1_lines else ""
        canonical = str(page_path.relative_to(Path(vault) / "wiki"))[:-3]
        page_type = PAGE_TYPE_BY_DIR.get(page_path.parent.name, "")
        identity = PageIdentity(
            canonical,
            page_path,
            title.strip(),
            h1,
        )
        identities[canonical] = identity

        add_alias(canonical, canonical)
        add_alias(page_path.stem, canonical)
        add_alias(title, canonical)
        add_alias(_strip_allowed_type_suffix(title), canonical)
        add_alias(h1, canonical)
        add_alias(_strip_allowed_type_suffix(h1), canonical)
        title_base = _strip_allowed_type_suffix(title)
        if title_base and page_type in {"entity", "concept", "source", "synthesis"}:
            add_alias(f"{title_base} ({page_type})", canonical)

    return AliasMap(identities, aliases)


def find_wiki_pages(vault):
    """Return (stem_index, path_index) for all .md pages under wiki/.

    stem_index maps page stem -> Path (for bare filename links like
    [[llm-wiki|...]]). path_index maps relative path without '.md' -> Path
    (for path-prefixed links like [[wiki/entities/pi-durable|...]]).
    """
    stem_index = {}
    path_index = {}
    wiki_dir = vault / "wiki"
    if not wiki_dir.exists():
        return stem_index, path_index
    for path in wiki_dir.rglob("*.md"):
        stem = path.stem
        stem_index.setdefault(stem, path)
        rel_no_ext = str(path.relative_to(wiki_dir))[:-3]  # drop .md
        path_index.setdefault(rel_no_ext, path)
    return stem_index, path_index


def lint_vault(vault):
    """Run all lint checks against the vault and return a LintResult."""
    vault = Path(vault)
    result = LintResult()
    stem_index, path_index = find_wiki_pages(vault)  # for link resolution
    alias_map = build_alias_map(vault)
    page_files = find_page_files(vault)  # pages subject to frontmatter/H1 checks
    special_files = _special_link_files(vault)
    link_files = page_files + special_files

    # The log is an append-only historical record: scan it for link *form*,
    # but never resolve its links or count them as inbound. Rewriting history
    # is not a mechanical repair. The index is current, so its links resolve
    # and count as inbound: a page listed in the index is not an orphan.
    index_files = [p for p in special_files if p.name == "index.md"]
    resolution_files = page_files + index_files

    # Build inbound-link map: target page path (relative to vault) -> set of
    # source files. Keyed by path (not stem) so duplicate stems in different
    # directories are tracked individually.
    inbound = {str(p.relative_to(vault)): set() for p in page_files}
    file_links = {}  # file path -> list of (raw, target, display)

    # Map each stem to all pages that share it, to detect duplicate stems
    # across directories (e.g. pi-durable in both sources/ and entities/).
    stem_to_paths: dict[str, list[Path]] = {}
    for path in page_files:
        stem_to_paths.setdefault(path.stem, []).append(path)

    def _is_ambiguous_bare_stem(target):
        """True if target is a bare stem shared by multiple pages."""
        if "/" in target:
            return False
        paths = stem_to_paths.get(target)
        return paths is not None and len(paths) > 1

    def _resolve_target(target):
        """Resolve a wikilink target to a page Path, or None if unknown.

        Path-prefixed links accept both [[entities/pi-durable|...]] and
        [[wiki/entities/pi-durable|...]] (the leading "wiki/" is optional).
        A bare stem only resolves when it is unique; a duplicated bare stem
        returns None so the caller can flag it as ambiguous.
        """
        # Path-prefixed link (contains a directory separator).
        if "/" in target:
            candidate = target
            if candidate.startswith("wiki/"):
                candidate = candidate[len("wiki/"):]
            if candidate in path_index:
                return path_index[candidate]
            return None
        # Bare stem link: resolve only when the stem is unique.
        if target not in stem_index:
            return None
        paths = stem_to_paths[target]
        if len(paths) > 1:
            return None  # ambiguous; the caller flags it separately
        return paths[0]

    # Link resolution across pages and the index.
    for link_path in resolution_files:
        text = link_path.read_text(encoding="utf-8")
        rel = str(link_path.relative_to(vault))
        links = extract_wikilinks(text)
        file_links[link_path] = links
        for _raw, target, _display in links:
            _target_text, display_separator, _display_text = _raw.partition("|")
            resolved = _resolve_target(target)
            if resolved is None:
                candidates = alias_map.resolve_link(
                    target,
                    _display_text if display_separator else None,
                )
                target_candidates = alias_map.resolve(target)
                if len(candidates) == 1:
                    canonical = next(iter(candidates))
                    identity = alias_map.identity(canonical)
                    suggestion = ""
                    if identity is not None:
                        suggestion = (
                            f"; did you mean [[{canonical}|{identity.title}]]"
                        )
                        display = _display_text if display_separator else target
                        _report_display_mismatch(
                            result,
                            rel,
                            _raw,
                            display,
                            identity,
                        )
                    result.add(
                        Severity.ERROR, rel,
                        f"broken link [[{_raw}]] target '{target}.md' not found"
                        f"{suggestion}",
                    )
                elif _is_ambiguous_bare_stem(target):
                    result.add(
                        Severity.ERROR, rel,
                        f"ambiguous link [[{_raw}]] target stem '{target}' is "
                        f"duplicated across directories; use a path-prefixed "
                        f"form like [[entities/{target}|...]] or "
                        f"[[sources/{target}|...]]",
                    )
                elif len(target_candidates) > 1:
                    possible = ", ".join(sorted(target_candidates))
                    result.add(
                        Severity.ERROR, rel,
                        f"ambiguous link [[{_raw}]] target '{target}' matches "
                        f"multiple pages: {possible}",
                    )
                else:
                    result.add(
                        Severity.ERROR, rel,
                        f"broken link [[{_raw}]] target '{target}.md' not found",
                    )
            else:
                resolved_rel = str(resolved.relative_to(vault))
                if resolved_rel in inbound:
                    inbound[resolved_rel].add(rel)
                identity = alias_map.identity(
                    str(resolved.relative_to(vault / "wiki"))[:-3]
                )
                if identity is not None and display_separator:
                    _report_display_mismatch(
                        result,
                        rel,
                        _raw,
                        _display_text,
                        identity,
                    )

    # Wikilink form check. Short-form links were not resolved above.
    for link_path in link_files:
        rel = str(link_path.relative_to(vault))
        if link_path not in file_links:
            file_links[link_path] = extract_wikilinks(
                link_path.read_text(encoding="utf-8")
            )
        for raw, _target, _display in file_links[link_path]:
            if "|" not in raw:
                result.add(
                    Severity.WARNING, rel,
                    f"short-form wikilink [[{raw}]] (use [[filename|Page Title]])",
                )

    # Check each page file.
    raw_paths, raw_names = _raw_source_names(vault)
    for page_path in page_files:
        text = page_path.read_text(encoding="utf-8")
        rel = str(page_path.relative_to(vault))
        lines = text.splitlines()

        # 1. Filename must be kebab-case. index.md and log.md are not page
        #    files, so they are exempt by construction.
        if not KEBAB_CASE_RE.fullmatch(page_path.name):
            result.add(
                Severity.ERROR, rel,
                f"filename '{page_path.name}' is not kebab-case "
                f"(expected lower-case words separated by hyphens)",
            )

        # 2. Frontmatter validation.
        fm = parse_frontmatter(text)
        entries = _frontmatter_lines(text)
        if fm is None:
            result.add(Severity.ERROR, rel, "missing YAML frontmatter block")
        else:
            missing = [f for f in REQUIRED_FRONTMATTER_FIELDS if f not in fm]
            if missing:
                result.add(
                    Severity.ERROR, rel,
                    "frontmatter missing required fields: " + ", ".join(missing),
                )
            # Validate type value.
            if "type" in fm and fm["type"] not in VALID_TYPES:
                result.add(
                    Severity.ERROR, rel,
                    f"invalid frontmatter type '{fm['type']}' (expected one of "
                    + ", ".join(sorted(VALID_TYPES)) + ")",
                )
            # Validate sources is a list.
            if "sources" in fm and not isinstance(fm["sources"], list):
                result.add(
                    Severity.ERROR, rel,
                    "frontmatter 'sources' must be a list",
                )
            # Validate tags is a list.
            if "tags" in fm and not isinstance(fm["tags"], list):
                result.add(
                    Severity.ERROR, rel,
                    "frontmatter 'tags' must be a list",
                )

            # 3. YAML validity: flag values YAML would misread. Quoted values
            #    and block scalars are already safe; flow lists must parse.
            for line_no, key, raw in entries:
                if not raw or raw in ("|", ">", "|-", ">-", "|+", ">+"):
                    continue
                commentless = strip_yaml_comment(raw)
                if is_quoted(commentless):
                    # A quoted scalar, optionally followed by a comment, is
                    # safe: YAML reads the quoted value.
                    continue
                if raw.startswith("["):
                    problem = flow_list_error(commentless)
                    if problem:
                        result.add(
                            Severity.ERROR, rel,
                            f"frontmatter '{key}' flow list would not parse: "
                            f"{problem}",
                            line=line_no,
                        )
                    continue
                if scalar_needs_quotes(raw):
                    result.add(
                        Severity.ERROR, rel,
                        f"unquoted YAML scalar for '{key}' would be misread: "
                        f"{raw!r} (quote it)",
                        line=line_no,
                    )

            # 4. Dates: ISO form and chronological order.
            parsed_dates = {}
            for field in ("created", "updated"):
                if field not in fm:
                    continue
                value = fm[field]
                valid = isinstance(value, str) and ISO_DATE_RE.fullmatch(value)
                if valid:
                    try:
                        parsed_dates[field] = date_cls.fromisoformat(value)
                    except ValueError:
                        valid = False
                if not valid:
                    result.add(
                        Severity.ERROR, rel,
                        f"frontmatter '{field}' must be an ISO date "
                        f"(YYYY-MM-DD), got {value!r}",
                        line=_key_line(entries, field),
                    )
            if "created" in parsed_dates and "updated" in parsed_dates:
                if parsed_dates["created"] > parsed_dates["updated"]:
                    result.add(
                        Severity.ERROR, rel,
                        "frontmatter 'created' is after 'updated'",
                        line=_key_line(entries, "created"),
                    )

            # 5. Every declared source must exist under raw/. Synthesis pages
            #    may name wiki pages instead, because they derive from them.
            if isinstance(fm.get("sources"), list):
                for entry in fm["sources"]:
                    if not isinstance(entry, str):
                        continue
                    if fm.get("type") == "synthesis" and \
                            _is_wiki_target(entry, stem_index, path_index):
                        continue
                    if not _raw_source_exists(entry, raw_paths, raw_names):
                        result.add(
                            Severity.WARNING, rel,
                            f"frontmatter sources entry {entry!r} has no "
                            f"matching file under raw/",
                            line=_key_line(entries, "sources"),
                        )

        # 6. H1 checks: one Title Case H1, and only one H1.
        h1s = _h1_lines(lines)
        if not h1s:
            result.add(Severity.ERROR, rel, "missing Title Case H1 (# Title)")
        else:
            h1_line, h1_text = h1s[0]
            if not is_title_case(h1_text):
                result.add(
                    Severity.WARNING, rel,
                    f"H1 is not Title Case: {h1_text!r}", line=h1_line,
                )
            if len(h1s) > 1:
                result.add(
                    Severity.WARNING, rel,
                    f"multiple H1 headings (first at line {h1_line}, "
                    f"another at line {h1s[1][0]})",
                    line=h1s[1][0],
                )

            # 7. Frontmatter title must agree with the H1, ignoring a
            #    trailing type suffix such as ' (concept)'.
            title = fm.get("title") if fm else None
            if isinstance(title, str) and title.strip():
                compare_title = _normalise_title(
                    _strip_allowed_type_suffix(title)
                )
                compare_h1 = _normalise_title(
                    _strip_allowed_type_suffix(h1_text)
                )
                if compare_title != compare_h1:
                    result.add(
                        Severity.WARNING, rel,
                        f"frontmatter title {title!r} does not match H1 "
                        f"{h1_text!r}",
                        line=h1_line,
                    )

    # Orphan detection.
    # A page is an orphan if it has zero inbound links from a page or the
    # index. Log links are historical and do not count (see above).
    for page_path in page_files:
        rel = str(page_path.relative_to(vault))
        stem = page_path.stem
        if stem in ("index", "log"):
            continue
        if not inbound[rel]:
            result.add(Severity.INFO, rel, "orphan page (zero inbound links)")

    return result


def _comparable_title(text):
    """Return a title normalized for suffix-insensitive comparison."""
    return _normalise_title(_strip_allowed_type_suffix(text))


def _display_matches_title(display, identity):
    """True when *display* names *identity* after type suffix stripping."""
    return _comparable_title(display) == _comparable_title(identity.title)


def _report_display_mismatch(result, file, raw, display, identity):
    """Report display text that contradicts the resolved page title."""
    if _display_matches_title(display, identity):
        return
    result.add(
        Severity.WARNING,
        file,
        f"link [[{raw}]] display text {display!r} does not match target "
        f"title {identity.title!r}",
    )


def _rewrite_links(text, alias_map, file, result):
    """Rewrite unambiguous links in *text* and record each change."""
    def replace_link(match):
        original = match.group(0)
        raw = match.group(1)
        target_text, separator, display_text = raw.partition("|")
        target = target_text.strip()
        candidates = alias_map.resolve_link(
            target,
            display_text if separator else None,
        )
        if len(candidates) != 1:
            return original

        canonical = next(iter(candidates))
        identity = alias_map.identity(canonical)
        if identity is None:
            return original

        if separator:
            if not _display_matches_title(display_text, identity):
                return original
            display = display_text
        elif target == identity.path.stem or "/" in target:
            display = identity.title
        else:
            if not _display_matches_title(target, identity):
                return original
            display = target

        replacement = f"[[{canonical}|{display}]]"
        if replacement != original:
            result.links_rewritten.append(
                LinkRewrite(file, original, replacement)
            )
        return replacement

    return WIKILINK_RE.sub(replace_link, text)


def _remove_dangling_index_entries(vault, result):
    """Remove index entries whose target page file is missing."""
    index_path = Path(vault) / "wiki" / "index.md"
    if not index_path.is_file():
        return

    content = index_path.read_text(encoding="utf-8")
    prefixes = tuple(f"{directory}/" for directory in PAGE_DIRS) + ("wiki/",)
    kept_lines = []

    for line in content.splitlines(keepends=True):
        dangling_matches = []
        for match in INDEX_LINK_RE.finditer(line):
            target = match.group(1).strip()
            if not target.startswith(prefixes):
                continue
            relative = index_target_rel(target)
            if (Path(vault) / "wiki" / f"{relative}.md").is_file():
                continue
            dangling_matches.append(match)
            result.index_entries_removed.append(
                IndexEntryRemoval(
                    "wiki/index.md",
                    target,
                    match.group(0),
                )
            )

        if not dangling_matches:
            kept_lines.append(line)
            continue
        if len(dangling_matches) == len(list(INDEX_LINK_RE.finditer(line))):
            continue
        cleaned = line
        for match in reversed(dangling_matches):
            cleaned = cleaned[:match.start()] + cleaned[match.end():]
        kept_lines.append(cleaned)

    if result.index_entries_removed:
        index_path.write_text("".join(kept_lines), encoding="utf-8")
        result.record_file_changed("wiki/index.md")


def fix_vault(vault, entry_date=None):
    """Apply automated fixes to the wiki and log the operation.

    Rewrites only links that resolve unambiguously. It removes dangling
    index entries and appends one dated log entry when work was done.
    """
    vault = Path(vault)
    page_files = find_page_files(vault)
    alias_map = build_alias_map(vault)
    result = FixResult()
    fix_files = list(page_files)
    index_path = vault / "wiki" / "index.md"
    if index_path.is_file():
        fix_files.append(index_path)

    for page_path in fix_files:
        text = page_path.read_text(encoding="utf-8")
        relative = str(page_path.relative_to(vault))
        new_text = _rewrite_links(text, alias_map, relative, result)
        if new_text != text:
            page_path.write_text(new_text, encoding="utf-8")
            result.record_file_changed(relative)

    _remove_dangling_index_entries(vault, result)
    if result.changed and not log_has_entry_on_date(
        vault,
        "lint",
        entry_date,
    ):
        result.log_entry = append_log_entry(
            vault,
            "lint",
            "Automated fixes applied",
            entry_date,
        )
        result.log_written = True
        result.record_file_changed("wiki/log.md")
    return result


def fix_result_to_dict(result):
    """Serialise a FixResult into a JSON-friendly mapping."""
    return {
        "files_changed": result.files_changed,
        "links_rewritten": [
            {
                "file": rewrite.file,
                "original": rewrite.original,
                "replacement": rewrite.replacement,
            }
            for rewrite in result.links_rewritten
        ],
        "index_entries_removed": [
            {
                "file": removal.file,
                "target": removal.target,
                "link": removal.link,
            }
            for removal in result.index_entries_removed
        ],
        "log_written": result.log_written,
        "log_entry": result.log_entry,
    }


def format_fix_result(result):
    """Format a FixResult as a human-readable repair report."""
    if not result.changed:
        return "No fixes applied."

    lines = ["Files changed:"]
    for relative in result.files_changed:
        lines.append(f"  {relative}")

    if result.links_rewritten:
        lines.append("Links rewritten:")
        for rewrite in result.links_rewritten:
            lines.append(
                f"  {rewrite.file}: {rewrite.original} -> "
                f"{rewrite.replacement}"
            )

    if result.index_entries_removed:
        lines.append("Index entries removed:")
        for removal in result.index_entries_removed:
            lines.append(f"  {removal.file}: {removal.link}")

    if result.log_written:
        lines.append(f"Log entry: {result.log_entry}")

    return "\n".join(lines)


def format_result(result):
    """Format a LintResult as a human-readable report string."""
    lines = []
    lines.append("Wiki Lint Report")
    lines.append("=" * 40)
    for severity in SEVERITY_ORDER:
        findings = result.by_severity(severity)
        if not findings:
            continue
        label = severity.value.upper()
        lines.append("")
        lines.append(f"{label} ({len(findings)}):")
        lines.append("-" * (len(label) + 5))
        for f in findings:
            loc = f.file
            if f.line is not None:
                loc += f":{f.line}"
            lines.append(f"  {loc}: {f.message}")
    lines.append("")
    total = len(result.findings)
    if result.has_errors:
        lines.append(f"Lint FAILED: {total} finding(s), including {len(result.errors)} error(s).")
    elif total:
        lines.append(f"Lint passed with {total} warning(s)/info(s), no errors.")
    else:
        lines.append("Lint passed: no issues found.")
    lines.append("")
    return "\n".join(lines)
