"""Shared logging helpers for the wiki log (wiki/log.md).

Every engine operation appends an entry of the form:

    ## [YYYY-MM-DD] op | title

The log is append-only; the engine only ever appends, never rewrites.
"""

from datetime import date
from pathlib import Path

from .vault import vault_paths

LOG_ENTRY_FMT = "## [{date}] {op} | {title}"

# The closed vocabulary of log operation names, locked by the normative vault
# contract. The engine emits setup, ingest, sync, and lint; query and
# synthesis entries are authored by the agent.
LOG_OPERATIONS = ("setup", "ingest", "query", "synthesis", "sync", "lint")


def today():
    """Return today's date as an ISO string (YYYY-MM-DD)."""
    return date.today().isoformat()


def format_log_entry(op, title, entry_date=None):
    """Format a single log entry line without a trailing newline."""
    d = entry_date or today()
    return LOG_ENTRY_FMT.format(date=d, op=op, title=title)


def append_log_entry(vault, op, title, entry_date=None):
    """Append an entry to wiki/log.md, creating the file if missing.

    Returns the entry string that was appended.
    """
    paths = vault_paths(vault)
    log_path = paths["log"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = format_log_entry(op, title, entry_date)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry + "\n")
    return entry


def log_has_entry_on_date(vault, op, entry_date=None):
    """Return True if wiki/log.md already has an *op* entry for the date.

    Used to keep date-scoped operations at most once per day: the log is a
    timeline, not a journal of every invocation.
    """
    d = entry_date or today()
    prefix = f"## [{d}] {op} |"
    return any(line.startswith(prefix) for line in read_log(vault).splitlines())


def read_log(vault):
    """Return the full contents of wiki/log.md, or empty string if missing."""
    paths = vault_paths(vault)
    log_path = paths["log"]
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8")
