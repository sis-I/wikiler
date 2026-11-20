"""Command-line interface: argument parsing and command dispatcher.

Routes init, ingest, query, lint, sync subcommands. Resolves the target vault
from --vault, WIKI_VAULT, or cwd. Only `init` may scaffold a vault; every
other command refuses to run outside an initialized vault.
"""

import argparse
import sys

from .vault import resolve_target_vault, refusal_for_command
from .output import report_error
from . import log

from .commands import init as cmd_init
from .commands import ingest as cmd_ingest
from .commands import query as cmd_query
from .commands import lint as cmd_lint
from .commands import sync as cmd_sync

COMMAND_MODULES = (cmd_init, cmd_ingest, cmd_query, cmd_lint, cmd_sync)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="wiki",
        description="LLM Wiki engine: ingest, query, lint, sync a compiling wiki.",
    )
    parser.add_argument(
        "--vault",
        "-v",
        default=None,
        help="Target vault path (default: WIKI_VAULT env var or cwd)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for mod in COMMAND_MODULES:
        mod.register(sub)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    vault = resolve_target_vault(getattr(args, "vault", None))
    refusal = refusal_for_command(args.command, vault)
    if refusal:
        # In JSON mode the refusal goes to stderr, so stdout carries the
        # JSON payload and nothing else.
        return report_error(refusal, getattr(args, "json", False))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
