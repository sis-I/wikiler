"""Form-only anti-drift checks for the public documentation authority structure.

The expected values below come from the decision recorded on issue #2 and the
acceptance checks on issue #7, not from the docs they check. These tests assert
form only: a marker line, a pointer, path presence, and string absence. They
never parse prose meaning or claim that a statement is correct.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
ROOT_AGENTS = REPO_ROOT / "AGENTS.md"

STATUS_LINE = re.compile(r"^[ \t]*(?:-[ \t]+)?Status:[ \t]*\S", re.MULTILINE)

# The document status table from issue #2, plus the two root files it names.
EXPECTED_PATHS = (
    "docs/adr/0003-documentation-authority.md",
    "docs/AUTHORITY.md",
    "docs/README.md",
    "docs/guides/LLM_WIKI_IMPLEMENTATION_GUIDE.md",
    "docs/guides/GETTING_STARTED.md",
    "docs/research/KARPATHY_WIKI_IMPLEMENTATION_GUIDE.md",
    "docs/research/KARPATHY_LLM_WIKI_RESEARCH.md",
    "docs/plans/wikiler-implementation-plan.md",
    "GLOSSARY.md",
    "AGENTS.md",
)

RETIRED_PATHS = (
    "docs/guides/COMPILING_WIKI_IMPLEMENTATION_GUIDE.md",
    "docs/guides/KARPATHY_WIKI_IMPLEMENTATION_GUIDE.md",
    "docs/plans/wiki-engine-helper-refactor.md",
)

# Scopes named by the acceptance checks. The historical research note and the
# CHANGELOG are exempt, as is any other path outside this tuple.
RESIDUE_SCOPES = (
    DOCS / "guides",
    DOCS / "plans",
    DOCS / "AUTHORITY.md",
    DOCS / "README.md",
    ROOT_AGENTS,
)
FORBIDDEN_RESIDUE = (
    "/Users/",
    "wiki-engine",
    "engine/wiki_engine/",
    "engine/.venv/bin/",
)


def _residue_files():
    for scope in RESIDUE_SCOPES:
        if scope.is_dir():
            yield from sorted(scope.rglob("*.md"))
        else:
            yield scope


class TestDocumentationAuthorityForm(unittest.TestCase):
    def test_every_public_doc_carries_a_status_marker(self):
        docs = sorted(DOCS.rglob("*.md"))
        self.assertTrue(docs, "docs/ must contain public Markdown documents")
        for path in docs:
            with self.subTest(doc=path.relative_to(REPO_ROOT)):
                text = path.read_text(encoding="utf-8")
                self.assertIsNotNone(
                    STATUS_LINE.search(text),
                    f"{path} is missing a 'Status: <value>' marker line",
                )

    def test_root_agents_points_to_authority_index(self):
        text = ROOT_AGENTS.read_text(encoding="utf-8")
        self.assertIn("docs/AUTHORITY.md", text)

    def test_status_table_paths_exist_and_retired_paths_are_gone(self):
        for relative in EXPECTED_PATHS:
            with self.subTest(path=relative):
                self.assertTrue(
                    (REPO_ROOT / relative).is_file(), f"missing {relative}"
                )
        for relative in RETIRED_PATHS:
            with self.subTest(path=relative):
                self.assertFalse(
                    (REPO_ROOT / relative).exists(), f"retired path remains: {relative}"
                )

    def test_no_private_repo_residue_in_public_docs(self):
        for path in _residue_files():
            text = path.read_text(encoding="utf-8")
            for residue in FORBIDDEN_RESIDUE:
                with self.subTest(doc=path.relative_to(REPO_ROOT), residue=residue):
                    self.assertNotIn(residue, text)


if __name__ == "__main__":
    unittest.main()
