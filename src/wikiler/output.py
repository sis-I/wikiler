"""Output routing: keep stdout clean for consumers that pipe it.

A command that emits JSON owns stdout: the payload is the only thing that
lands there. Errors and refusals go to stderr in JSON mode, so a consumer can
pipe stdout straight into a JSON parser.
"""

import sys


def report_error(message, as_json=False):
    """Print an error message and return the exit code (1).

    In JSON mode the message goes to stderr, so stdout stays a single JSON
    object. Otherwise it goes to stdout, where a human reads it.
    """
    print(message, file=sys.stderr if as_json else sys.stdout)
    return 1
