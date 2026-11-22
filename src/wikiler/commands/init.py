"""init command: scaffold vault structure and initial index.md / log.md."""

from pathlib import Path

from ..vault import ensure_vault_structure, vault_paths
from ..log import append_log_entry

INDEX_TEMPLATE = """# Wiki Index

Content catalog, one line per page, categorized.

## Sources

## Entities

## Concepts

## Synthesis

## Queries

"""


def cmd_init(args):
    """Scaffold the target vault: subdirectories, index.md, log.md.

    Idempotent: re-running does not duplicate index.md content or append
    another setup entry to log.md.
    """
    from ..vault import resolve_target_vault

    vault = resolve_target_vault(getattr(args, "vault", None))
    ensure_vault_structure(vault)

    paths = vault_paths(vault)
    index_path = paths["index"]
    log_path = paths["log"]

    if not index_path.exists():
        index_path.write_text(INDEX_TEMPLATE, encoding="utf-8")

    log_is_new = not log_path.exists()
    if log_is_new:
        log_path.write_text("# Wiki Log\n\nAppend-only timeline.\n\n", encoding="utf-8")
        append_log_entry(vault, "setup", "Vault initialized")
    return 0


def register(subparsers):
    parser = subparsers.add_parser("init", help="Scaffold vault structure")
    parser.set_defaults(func=cmd_init)

