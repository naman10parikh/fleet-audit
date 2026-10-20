"""Dispatch: send a plain-language task to the skill and the command that does it.

Deterministic keyword routing on word boundaries. The best-scoring route wins; ties go to the earlier route; no
match falls back to auditing, since that is the first step of every job here.
"""

from __future__ import annotations

import re

ROUTES = [
    {"route": "scrub", "skill": "scrub-before-public",
     "command": "fleet-audit scrub <path> --patterns <file>",
     "keys": ["scrub", "secret", "secrets", "leak", "personal", "email", "home path", "confidential", "before public",
              "go public", "make it public", "publish"],
     "why": "Patterns over the tree, the history and the commit messages, and secrets by gitleaks."},
    {"route": "history", "skill": "scrub-before-public",
     "command": "fleet-audit history <owner/name> --patterns <file> --out <scratch>",
     "keys": ["history", "rewrite", "filter-repo", "old commits", "force-push", "internal notes"],
     "why": "Rewrite a scratch mirror and prove it clean; pushing stays with a person."},
    {"route": "fix", "skill": "fix-with-the-kit",
     "command": "fleet-audit kit <path> --facts <facts.json> --owner <owner> --author <name> --dry-run",
     "keys": ["fix", "kit", "add the missing", "write the missing", "readme blocks", "license", "plugin",
              "marketplace", "agent card", "gemini extension", "scaffold"],
     "why": "Write the missing standard files and the README blocks; a dry run first."},
    {"route": "report", "skill": "audit-a-repo",
     "command": "fleet-audit report <path> ... --out readiness.md",
     "keys": ["report", "summary", "markdown", "table", "every repository", "all my repos", "fleet"],
     "why": "One Markdown page over many repositories."},
    {"route": "audit", "skill": "audit-a-repo",
     "command": "fleet-audit check <path>",
     "keys": ["audit", "check", "scan", "ready", "readiness", "missing", "surfaces", "agent-native", "what is missing"],
     "why": "Measure the surfaces and run the checks, with the fix for each gap."},
]


def route(task: str) -> dict:
    """The route for a task: {route, skill, command, why, score}."""
    text = re.sub(r"\s+", " ", task.lower())
    best, best_score = ROUTES[-1], 0
    for r in ROUTES:
        score = sum(1 for k in r["keys"] if re.search(r"\b" + re.escape(k) + r"\b", text))
        if score > best_score:
            best, best_score = r, score
    return {k: best[k] for k in ("route", "skill", "command", "why")} | {"score": best_score}
