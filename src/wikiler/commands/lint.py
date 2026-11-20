"""lint command: health-check the wiki for structural faults."""

import json

from ..lint import (
    format_fix_result,
    format_result,
    fix_result_to_dict,
    fix_vault,
    lint_vault,
    result_to_dict,
)
from ..vault import resolve_target_vault


def cmd_lint(args):
    vault = resolve_target_vault(getattr(args, "vault", None))
    fix_result = None
    if args.fix:
        fix_result = fix_vault(vault)

    result = lint_vault(vault)
    if args.json:
        data = result_to_dict(result)
        if fix_result is not None:
            data["fixes"] = fix_result_to_dict(fix_result)
        print(json.dumps(data, indent=2))
    else:
        if fix_result is not None:
            print(format_fix_result(fix_result))
        print(format_result(result))
    return 1 if result.has_errors else 0


def register(subparsers):
    parser = subparsers.add_parser("lint", help="Lint the wiki")
    parser.add_argument("--fix", action="store_true", help="Apply automated fixes")
    parser.add_argument("--json", action="store_true", help="Emit findings as JSON")
    parser.set_defaults(func=cmd_lint)
