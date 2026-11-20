"""sync command: reconcile index.md, frontmatter quoting, and log.md.

`sync` is the durable mechanic behind AGENTS.md Rule 2. It never edits a
page body and never invents content. It:

- appends an index entry for every page on disk that lacks one;
- reports (but does not delete) index entries whose target file is gone;
- quotes scalar frontmatter values YAML would misread, ensures the required
  keys exist, sets ``created`` only when absent, and refreshes ``updated``
  only when another line in that page changed;
- appends one dated ``sync`` log entry when something changed, at most once
  per day.

It is idempotent: a second run with nothing to do writes nothing and logs
nothing.
"""

from dataclasses import dataclass, field
from pathlib import Path
import re

from ..log import append_log_entry, log_has_entry_on_date, today
from ..page import (
    FRONTMATTER_RE,
    PAGE_TYPE_BY_DIR,
    find_page_files,
    index_target_rel,
    normalise_frontmatter,
    update_index,
)
from ..vault import resolve_target_vault


@dataclass
class SyncResult:
    """Outcome of a sync run."""

    pages_changed: list[str] = field(default_factory=list)  # wiki-relative
    index_added: list[str] = field(default_factory=list)  # dir/slug
    dangling: list[str] = field(default_factory=list)  # dir/slug
    log_written: bool = False
    log_entry: str | None = None
    log_date: str | None = None

    @property
    def changed(self):
        return bool(self.pages_changed or self.index_added)


def _page_title(text, page_path):
    """Return the H1 (preferred) or a humanised stem as the title fallback."""
    body = text
    match = FRONTMATTER_RE.match(text)
    if match:
        body = text[match.end():]
    h1 = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if h1:
        return h1.group(1).strip()
    return page_path.stem.replace("-", " ").title()


def _plural(count, singular, plural):
    return f"{count} {singular if count == 1 else plural}"


def _summary(result):
    """One-line count of what a sync run changed."""
    return (
        f"{_plural(len(result.pages_changed), 'page', 'pages')} updated, "
        f"{_plural(len(result.index_added), 'index entry', 'index entries')} added"
    )


def sync_vault(vault, entry_date=None):
    """Reconcile index, frontmatter, and log for *vault*. Returns SyncResult."""
    vault = Path(vault)
    date_str = entry_date or today()
    result = SyncResult(log_date=date_str)

    for page_path in find_page_files(vault):
        text = page_path.read_text(encoding="utf-8")
        new_text, changed = normalise_frontmatter(
            text,
            page_type=PAGE_TYPE_BY_DIR.get(page_path.parent.name, "source"),
            fallback_title=_page_title(text, page_path),
            page_date=date_str,
        )
        if changed:
            page_path.write_text(new_text, encoding="utf-8")
            result.pages_changed.append(
                str(page_path.relative_to(vault / "wiki"))
            )

    index_update = update_index(vault)
    result.index_added = index_update.added
    result.dangling = index_update.dangling

    if result.changed and not log_has_entry_on_date(vault, "sync", date_str):
        result.log_entry = append_log_entry(vault, "sync", _summary(result), date_str)
        result.log_written = True

    return result


def _format_result(result):
    lines = []
    if result.changed:
        lines.append(f"sync: {_summary(result)}")
        for rel in result.pages_changed:
            lines.append(f"  updated wiki/{rel}")
        for rel in result.index_added:
            lines.append(f"  index + {rel}")
    else:
        lines.append("sync: nothing to do")

    for target in result.dangling:
        rel = index_target_rel(target)
        lines.append(
            f"warning: index entry [[{target}]] points to missing file "
            f"wiki/{rel}.md (left in place)"
        )

    if result.log_written:
        lines.append(f"log: {result.log_entry}")
    elif result.changed:
        lines.append(
            f"log: already has a sync entry for {result.log_date} (not duplicated)"
        )
    return "\n".join(lines)


def cmd_sync(args):
    vault = resolve_target_vault(getattr(args, "vault", None))
    result = sync_vault(vault)
    print(_format_result(result))
    return 0


def register(subparsers):
    parser = subparsers.add_parser(
        "sync", help="Reconcile index.md, frontmatter, and log.md"
    )
    parser.set_defaults(func=cmd_sync)
