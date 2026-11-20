#!/usr/bin/env bash
# Throwaway inspection of the prototype contract. Not a test suite.
set -eu
root="$(cd "$(dirname "$0")" && pwd)"
for skill in wiki-setup wiki-ingest wiki-query wiki-lint; do
  file="$root/vault/.agents/skills/$skill/SKILL.md"
  echo "=== $skill ==="
  sed -n '1,3p' "$file"
  echo "body lines: $(awk 'NR>4 && NF{n++} END{print n+0}' "$file")"
  echo "AGENTS pointer: $(grep -c 'AGENTS.md' "$file")"
  echo
done
echo "Harness discovery path: vault/.agents/skills/"
echo "Skills found: $(find "$root/vault/.agents/skills" -name SKILL.md | wc -l | tr -d ' ')"
