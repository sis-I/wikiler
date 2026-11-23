"""Packaging tests for the portable skill contract.

The skills and runtime rules must ship as package data so a fresh
`pip install wikiler` plus `wiki init` installs them into a new vault.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# Kept as a literal so the test is an independent oracle for the contract.
SKILL_NAMES = ("wiki-setup", "wiki-ingest", "wiki-query", "wiki-lint")


class TestPackagedData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp()
        cls.wheel_dir = Path(cls._tmp) / "wheels"
        cls.wheel_dir.mkdir()
        # Build from a copy so pip's build/ directory never lands in the repo.
        source = Path(cls._tmp) / "source"
        source.mkdir()
        for name in ("pyproject.toml", "README.md", "LICENSE"):
            shutil.copy2(REPO_ROOT / name, source / name)
        shutil.copytree(
            REPO_ROOT / "src",
            source / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        subprocess.run(
            [
                sys.executable, "-m", "pip", "wheel", str(source),
                "--no-deps", "--wheel-dir", str(cls.wheel_dir), "--quiet",
            ],
            check=True,
            capture_output=True,
        )
        wheels = list(cls.wheel_dir.glob("*.whl"))
        if len(wheels) != 1:
            raise AssertionError(f"expected one wheel, found {wheels}")
        cls.wheel = wheels[0]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_wheel_contains_runtime_rules_and_skills(self):
        # Issue #6 asks for a wheel *or* sdist; the wheel half is covered here.
        expected = {"wikiler/runtime_rules.md"} | {
            f"wikiler/.agents/skills/{name}/SKILL.md" for name in SKILL_NAMES
        }
        with zipfile.ZipFile(self.wheel) as archive:
            names = set(archive.namelist())
        self.assertTrue(expected <= names, f"missing from wheel: {expected - names}")

    def test_installed_wheel_init_installs_agent_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "site"
            vault = Path(tmp) / "vault"
            elsewhere = Path(tmp) / "elsewhere"
            elsewhere.mkdir()
            subprocess.run(
                [
                    sys.executable, "-m", "pip", "install", "--no-deps",
                    "--target", str(target), str(self.wheel), "--quiet",
                ],
                check=True,
                capture_output=True,
            )

            env = dict(os.environ)
            env.pop("WIKI_VAULT", None)
            env["PYTHONPATH"] = str(target)
            script = (
                "from wikiler.cli import main; "
                f"raise SystemExit(main(['--vault', {str(vault)!r}, 'init']))"
            )
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=elsewhere,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            self.assertTrue((vault / "AGENTS.md").is_file())
            for name in SKILL_NAMES:
                with self.subTest(skill=name):
                    installed = (
                        vault / ".agents" / "skills" / name / "SKILL.md"
                    )
                    self.assertTrue(installed.is_file())


if __name__ == "__main__":
    unittest.main()
