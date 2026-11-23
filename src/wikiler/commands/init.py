"""init command: scaffold vault structure and install agent-facing files."""

from importlib.resources import files

from ..vault import ensure_vault_structure, vault_paths
from ..log import append_log_entry

SKILL_NAMES = ("wiki-setup", "wiki-ingest", "wiki-query", "wiki-lint")


def _skill_relpath(name):
    """Return the vault-relative path of one installed skill."""
    return f".agents/skills/{name}/SKILL.md"

INDEX_TEMPLATE = """# Wiki Index

Content catalog, one line per page, categorized.

## Sources

## Entities

## Concepts

## Synthesis

## Queries

"""


def _install_if_missing(destination, source):
    """Write *source* package data to *destination* only when absent.

    Existing files are user-owned once installed, so re-init never overwrites
    edits to AGENTS.md or to a skill. To adopt newer package data, remove the
    file and re-run init.
    """
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())


def cmd_init(args):
    """Scaffold the target vault: subdirectories, index.md, log.md.

    Also installs AGENTS.md and the four portable skills from package data.
    Idempotent: re-running does not overwrite edited files or append another
    setup entry to log.md.
    """
    from ..vault import resolve_target_vault

    vault = resolve_target_vault(getattr(args, "vault", None))
    ensure_vault_structure(vault)

    package = files("wikiler")
    _install_if_missing(vault / "AGENTS.md", package / "runtime_rules.md")
    for name in SKILL_NAMES:
        relpath = _skill_relpath(name)
        _install_if_missing(vault / relpath, package / relpath)

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

