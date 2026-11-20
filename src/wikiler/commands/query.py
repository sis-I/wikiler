"""query command: retrieve candidate pages for a question.

Query is retrieval, not synthesis. It reads wiki/index.md, matches entries
against the question's keywords, then reads each matched page and attaches a
short snippet. The ranked candidate list is the answer: the agent reads those
pages and writes the cited synthesis itself, then saves it with its own tools
and runs ``wiki sync``.

No prose about the wiki's contents is generated here, and nothing is saved.
raw/ is never touched: query only reads the wiki.
"""

import json
import re

from ..page import index_target_rel, parse_frontmatter, split_frontmatter_text
from ..vault import resolve_target_vault, vault_paths


def _keywords(question):
    """Return lowercase keyword tokens (length >= 3) from the question."""
    tokens = re.findall(r"[a-z0-9]+", question.lower())
    return [t for t in tokens if len(t) >= 3]


# Matches index entries like:  - [[sources/foo|Foo Title]]
INDEX_ENTRY_RE = re.compile(r"^\s*-\s*\[\[([^\]]+)\]\]")

# How long a retrieval snippet may grow before it is truncated.
SNIPPET_LIMIT = 200


def _find_relevant_pages(index_text, question):
    """Scan wiki/index.md for entries relevant to the question.

    Returns a list of (target, title) pairs where *target* is the path
    relative to wiki/ (e.g. "sources/foo") and *title* is the display title
    (empty for a path-only link; the page's own title fills that in later).
    Results are ranked by how many distinct keywords each entry matches;
    ties keep index order. Only path-prefixed links are candidates: a
    `wiki/dir/slug` target is normalised to `dir/slug`, and a title-style
    link such as `[[Foo]]` is skipped.
    """
    keywords = _keywords(question)
    matched = []
    seen = set()
    for line in index_text.splitlines():
        m = INDEX_ENTRY_RE.match(line)
        if not m:
            continue
        target, _separator, display = m.group(1).partition("|")
        target = index_target_rel(target.strip())
        display = display.strip()
        if "/" not in target:
            continue  # only path-prefixed links resolve to a page
        haystack = (target + " " + display + " " + line).lower()
        score = len({keyword for keyword in keywords if keyword in haystack})
        if score and target not in seen:
            seen.add(target)
            matched.append((score, target, display))
    matched.sort(key=lambda item: -item[0])  # stable: ties keep index order
    return [(target, display) for _score, target, display in matched]


def _clean_inline(text):
    """Reduce a markdown paragraph to plain inline text."""
    text = re.sub(r"^[-*+]\s+", "", text)  # list marker
    text = re.sub(r"^#{1,6}\s*", "", text)  # stray heading marker
    text = re.sub(r"\*\*|__", "", text)  # bold
    text = re.sub(r"\[\[([^\]]*\|)?([^\]]*)\]\]", r"\2", text)  # wikilink -> display
    return " ".join(text.split())


def _snippet(text, limit=SNIPPET_LIMIT):
    """Return the first non-heading paragraph of a page, truncated.

    Frontmatter, headings, tables, source-metadata bullets, and TODO comment
    blocks are skipped: they carry no signal about what the page says. When a
    paragraph is longer than *limit* characters it is cut at a word boundary
    and given an ellipsis.
    """
    split = split_frontmatter_text(text)
    body = split[2] if split else text

    for block in re.split(r"\n\s*\n", body):
        clean = " ".join(line.strip() for line in block.strip().splitlines())
        if not clean or clean.startswith("#"):
            continue
        if clean.startswith("|"):
            continue  # table row, not a paragraph
        if clean.startswith("<!--") and clean.endswith("-->"):
            continue
        if clean.startswith("- **"):
            continue
        clean = _clean_inline(clean)
        if not clean:
            continue
        if len(clean) > limit:
            cut = clean[:limit].rsplit(" ", 1)[0] or clean[:limit]
            return cut.rstrip() + "…"
        return clean
    return ""


def _page_title(text):
    """Return a page's frontmatter title, then H1, for a path-only index link."""
    fm = parse_frontmatter(text)
    if fm and fm.get("title"):
        return fm["title"]
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _candidate(vault, page_path, target, title):
    """Build one retrieval match: target, title, vault-relative path, snippet."""
    text = page_path.read_text(encoding="utf-8") if page_path.is_file() else ""
    return {
        "target": target,
        "title": title or _page_title(text),
        "path": page_path.relative_to(vault).as_posix(),
        "snippet": _snippet(text),
    }


def _format_matches(question, matches):
    """Render the ranked candidate list for humans."""
    lines = [f"Query: {question}", f"Candidates ({len(matches)}):", ""]
    for index, match in enumerate(matches, 1):
        lines.append(f"{index}. [[{match['target']}|{match['title']}]]")
        lines.append(f"   path: {match['path']}")
        lines.append(f"   snippet: {match['snippet']}")
        if index != len(matches):
            lines.append("")
    return "\n".join(lines)


def cmd_query(args):
    """Retrieve candidate pages for a question; never answer it."""
    vault = resolve_target_vault(getattr(args, "vault", None))
    question = getattr(args, "question", None)
    as_json = getattr(args, "json", False)
    paths = vault_paths(vault)
    index_path = paths["index"]

    if not index_path.exists():
        print(
            "error: wiki/index.md not found; run `wiki init` and "
            "ingest sources before querying."
        )
        return 1

    index_text = index_path.read_text(encoding="utf-8")
    matched = _find_relevant_pages(index_text, question)
    matches = []
    for target, title in matched:
        page_path = paths["wiki"] / f"{target}.md"
        matches.append(_candidate(vault, page_path, target, title))

    if as_json:
        print(json.dumps(
            {"question": question, "matches": matches},
            ensure_ascii=False,
        ))
        return 0

    if not matches:
        print(f"No wiki pages matched the question: {question}")
        print("Tip: ingest sources into raw/ first, then re-run this query.")
        return 0

    print(_format_matches(question, matches))
    return 0


def register(subparsers):
    parser = subparsers.add_parser(
        "query", help="Retrieve candidate pages for a question"
    )
    parser.add_argument("question", help="Question to retrieve candidate pages for")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the question and ranked matches as JSON",
    )
    parser.set_defaults(func=cmd_query)
