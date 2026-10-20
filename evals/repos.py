"""Fixture repositories for the evals and the tests, built fresh in a temporary folder on every run.

bare      a README and nothing else: almost every check is missing
complete  every surface the standard asks for: no check is missing
leaky     a planted email shape in the tree, a home path only in history, and an email shape in a commit message

The planted strings are assembled at run time, so this file never holds them whole.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMAIL = "@".join(["jane.doe", "example.org"])  # an email shape, never a real address
HOME_PATH = "/".join(["", "home", "jane", "project", "build.sh"])
IDENTITY = ["-c", "user.name=fixture", "-c", "user.email=" + "@".join(["fixture", "example.invalid"])]


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *IDENTITY, *args], cwd=repo, check=True, capture_output=True)


def commit_all(repo: Path, files: dict[str, str], message: str) -> None:
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


def init(root: Path, name: str) -> Path:
    repo = root / name
    repo.mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    return repo


def bare(root: Path) -> Path:
    repo = init(root, "bare")
    commit_all(repo, {"README.md": "# bare\n\nA small tool.\n"}, "first")
    return repo


def complete(root: Path) -> Path:
    repo = init(root, "complete")
    skill = "---\nname: {0}\ndescription: Use when {0} is needed.\n---\n\n# {0}\n\n## Steps\n1. Do it.\n\n## Output\nA report.\n"
    agent = "---\nname: {0}\ndescription: The {0} persona.\ntools: Read\n---\n\nYou are {0}.\n"
    readme = "# complete\n\nA tool that does one job well.\n\n## Quick start\n\n```bash\ncomplete --help\n```\n\n" + (
        "It reads a folder and writes a report. " * 60) + "\n"
    files = {
        "README.md": readme, "AGENTS.md": "# AGENTS.md\n", "CLAUDE.md": "@AGENTS.md\n", "GEMINI.md": "@AGENTS.md\n",
        "llms.txt": "# complete\n\n> A tool.\n\n- [AGENTS.md](AGENTS.md)\n",
        "LICENSE": "MIT License\n\nPermission is hereby granted, free of charge\n",
        "SECURITY.md": "# Security\n", "CONTRIBUTING.md": "# Contributing\n", "CODE_OF_CONDUCT.md": "# Conduct\n",
        "identity/SOUL.md": "# Complete\n", "memory/MEMORY.md": "# Memory\n", "memory/LEARNINGS.md": "# Learnings\n",
        ".claude/settings.json": json.dumps({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": []}]}}),
        "src/complete/mcp_server.py": "print('server')\n",
        "pyproject.toml": '[project]\nname = "complete"\nversion = "0.2.0"\n\n[project.scripts]\ncomplete = "complete:main"\n',
        ".claude-plugin/plugin.json": "{}\n", ".claude-plugin/marketplace.json": "{}\n", "gemini-extension.json": "{}\n",
        ".well-known/agent-card.json": "{}\n", "dsip.json": "{}\n", ".mcp.json": '{"mcpServers": {}}\n',
        ".github/workflows/ci.yml": "name: ci\non:\n  push:\n  pull_request:\njobs: {}\n",
        ".github/workflows/loop.yml": "name: loop\non:\n  schedule:\n    - cron: '0 6 * * *'\n  workflow_dispatch:\njobs: {}\n",
    }
    for s in ("one", "two", "three"):
        files[f"skills/{s}/SKILL.md"] = skill.format(s)
    for a in ("author", "critic"):
        files[f".claude/agents/{a}.md"] = agent.format(a)
    commit_all(repo, files, "everything")
    return repo


def leaky(root: Path) -> Path:
    repo = init(root, "leaky")
    commit_all(repo, {"notes.txt": f"contact {EMAIL}\n", "build.sh": f"cd {HOME_PATH}\n"}, "first draft")
    commit_all(repo, {"build.sh": "cd ./project\n"}, f"tidy paths, thanks {EMAIL}")
    return repo


def patterns_file(root: Path) -> Path:
    """The shipped example patterns, copied outside the fixture repositories, as a user would."""
    target = root / "patterns.txt"
    target.write_text((ROOT / "scrub-patterns.example.txt").read_text())
    return target
