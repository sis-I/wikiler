"""Vault path resolution, marker detection, and structure scaffolding.

The engine never writes to raw/ directly; raw/ is human-owned and immutable.
All engine writes go under wiki/ and output/ of the target vault.

Only `init` may scaffold a vault. Other commands resolve the target, check
for a vault marker, and refuse (without writing anything) when it is absent.
"""

from pathlib import Path
import os

VAULT_SUBDIRS = [
    "raw",
    "raw/assets",
    "wiki",
    "wiki/sources",
    "wiki/entities",
    "wiki/concepts",
    "wiki/synthesis",
    "wiki/queries",
    "output",
]

# Files whose presence marks a directory as an initialized vault. `init`
# creates both; either one is enough to recognise a vault.
VAULT_MARKERS = ("wiki/index.md", "wiki/log.md")

NOT_A_VAULT_FMT = "error: not a wiki vault: {path} (run wiki init first)"


def resolve_target_vault(explicit=None):
    """Resolve the target vault path.

    Precedence: explicit argument > WIKI_VAULT env var > current working dir.
    Returns an absolute, resolved Path.
    """
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get("WIKI_VAULT")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def vault_paths(vault):
    """Return a dict of key vault paths for the given vault root."""
    v = Path(vault)
    return {
        "root": v,
        "raw": v / "raw",
        "raw_assets": v / "raw" / "assets",
        "wiki": v / "wiki",
        "wiki_sources": v / "wiki" / "sources",
        "wiki_entities": v / "wiki" / "entities",
        "wiki_concepts": v / "wiki" / "concepts",
        "wiki_synthesis": v / "wiki" / "synthesis",
        "wiki_queries": v / "wiki" / "queries",
        "output": v / "output",
        "index": v / "wiki" / "index.md",
        "log": v / "wiki" / "log.md",
    }


def ensure_vault_structure(vault):
    """Create all required vault subdirectories. Idempotent.

    Only `init` may call this: every other command must refuse to run
    outside an existing vault rather than scaffold one as a side effect.
    Does not create index.md or log.md; those are created by the init command.
    raw/ is created as an empty directory but never populated by the engine.
    """
    v = Path(vault)
    for rel in VAULT_SUBDIRS:
        (v / rel).mkdir(parents=True, exist_ok=True)
    return v


def is_vault(vault):
    """Return True when *vault* contains an init marker (index.md or log.md).

    A directory tree alone is not a vault: only `init` may scaffold, so the
    markers prove the directory was initialized rather than invented by a
    stray command run.
    """
    v = Path(vault)
    return any((v / rel).is_file() for rel in VAULT_MARKERS)


def refusal_for_command(command, vault):
    """Return a refusal message if *command* may not run in *vault*.

    `init` is the only command allowed to scaffold a vault. Every other
    command (including future ones such as `sync`) refuses unless a vault
    marker is present, so it can never create raw/, wiki/, or output/ as a
    side effect. Returns None when the command may proceed.
    """
    if command == "init" or is_vault(vault):
        return None
    return NOT_A_VAULT_FMT.format(path=Path(vault).resolve())


def is_within_vault(path, vault):
    """Return True if path resolves to a location inside the vault root.

    Safety guard: the engine must never write outside the target vault.
    """
    p = Path(path).resolve()
    v = Path(vault).resolve()
    try:
        p.relative_to(v)
        return True
    except ValueError:
        return False
