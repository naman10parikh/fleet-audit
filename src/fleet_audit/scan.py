"""Measure a repository's agent-native surfaces from what is committed, never from memory. It only reads.

For one clone it records the files that make a repository usable by coding agents (AGENTS.md, CLAUDE.md, GEMINI.md,
llms.txt, skills, sub-agents, hooks, an MCP server, a CLI, a Claude Code plugin, a Gemini CLI extension, an A2A
agent card, a self-improvement contract), its identity and memory files, the hygiene files of a mature project and
the shape of its README. With gh available it adds GitHub's facts (visibility, description, topics, stars).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .gitutil import default_ref, gh_available, gh_repo, github_slug, is_repo, out, show, tree

HOOK_EVENTS = r'"(?:SessionStart|SessionEnd|PreToolUse|PostToolUse|Stop|PreCompact|UserPromptSubmit|SubagentStop|Notification)"'


def first(files: list[str], *patterns: str) -> str:
    """The first file matching any pattern (regexes over the repository-relative path), or ''."""
    for pat in patterns:
        rx = re.compile(pat, re.I)
        for f in files:
            if rx.search(f):
                return f
    return ""


def count(files: list[str], pattern: str) -> int:
    rx = re.compile(pattern, re.I)
    return sum(1 for f in files if rx.search(f))


def licence_kind(text: str) -> str:
    if "MIT License" in text or "Permission is hereby granted" in text:
        return "MIT"
    if "Apache License" in text:
        return "Apache-2.0"
    if "Mozilla Public License" in text:
        return "MPL-2.0"
    if "GNU GENERAL PUBLIC LICENSE" in text.upper():
        return "GPL"
    return "other" if text.strip() else ""


def scan_clone(path: str | Path, head: bool = False, offline: bool = False) -> dict:
    """Every measured fact for one local clone. `head` reads the local HEAD instead of the remote's default branch."""
    path = Path(path).expanduser().resolve()
    if not is_repo(path):
        return {"name": path.name, "path": str(path), "error": "not a git repository"}
    ref = default_ref(path, head)
    files = tree(path, ref)
    readme_path = first(files, r"^readme\.md$")
    readme = show(path, ref, readme_path) if readme_path else ""
    lic_path = first(files, r"^licen[cs]e(\.md|\.txt)?$")
    pkg: dict = {}
    if "package.json" in files:
        try:
            pkg = json.loads(show(path, ref, "package.json") or "{}")
        except ValueError:
            pkg = {}
    pyproject = show(path, ref, "pyproject.toml") if "pyproject.toml" in files else ""
    settings = show(path, ref, ".claude/settings.json") if ".claude/settings.json" in files else ""
    plugin_hooks = show(path, ref, "hooks/hooks.json") if "hooks/hooks.json" in files else ""
    deps = json.dumps(pkg.get("dependencies", {})) + json.dumps(pkg.get("devDependencies", {}))
    slug = github_slug(path)
    row = {
        "name": slug[1] if slug else path.name,
        "owner": slug[0] if slug else "",
        "path": str(path),
        "ref": ref,
        "files": len(files),
        "local_changes": len([s for s in out(["git", "status", "--porcelain"], path).splitlines() if s.strip()]),
        "readme": {
            "bytes": len(readme.encode()),
            "quick_start": bool(re.search(r"^#{1,3} .*(install|quick ?start|get(ting)? started|usage|setup)", readme,
                                          re.I | re.M)),
            "agents_section": bool(re.search(r"coding agent|agents\.md|\bmcp\b", readme, re.I)),
            "license_section": bool(re.search(r"^#{1,3} .*licen[cs]e", readme, re.I | re.M)),
        },
        "license": licence_kind(show(path, ref, lic_path)[:600]) if lic_path else "",
        "surfaces": {
            "AGENTS.md": first(files, r"^agents\.md$"),
            "CLAUDE.md": first(files, r"^claude\.md$", r"^\.claude/claude\.md$"),
            "GEMINI.md": first(files, r"^gemini\.md$"),
            "llms.txt": first(files, r"^llms\.txt$", r"(^|/)public/llms\.txt$", r"^docs/llms\.txt$"),
            "cursor_rules": first(files, r"^\.cursor/rules/", r"^\.cursorrules$"),
            "copilot": first(files, r"^\.github/copilot-instructions\.md$"),
            "skills": count(files, r"(^|/)SKILL\.md$"),
            "subagents": count(files, r"^\.claude/agents/[^/]+\.md$"),
            "hooks": len(re.findall(HOOK_EVENTS, settings)),
            "plugin_hooks": len(re.findall(HOOK_EVENTS, plugin_hooks)),
            "mcp_config": first(files, r"^\.mcp\.json$"),
            "mcp_server": first(files, r"mcp[-_]?server\.(ts|js|mjs|py)$", r"(^|/)src/mcp/", r"(^|/)mcp/(server|index)\.",
                                r"^server\.json$") or ("dependency" if "@modelcontextprotocol/sdk" in deps
                                                       or "fastmcp" in pyproject or re.search(r'"mcp"', deps) else ""),
            "plugin_json": first(files, r"^\.claude-plugin/plugin\.json$"),
            "marketplace": first(files, r"^\.claude-plugin/marketplace\.json$"),
            "gemini_ext": first(files, r"^gemini-extension\.json$"),
            "a2a_card": first(files, r"\.well-known/agent(-card)?\.json$"),
            "dsip": first(files, r"(^|/)dsip\.json$"),
            "cli": "bin" if pkg.get("bin") else ("scripts" if "[project.scripts]" in pyproject else ""),
        },
        "identity": {
            "SOUL.md": first(files, r"(^|/)soul\.md$"),
            "BRAND.md": first(files, r"(^|/)brand\.md$"),
            "HEARTBEAT.md": first(files, r"(^|/)heartbeat\.md$"),
            "MEMORY.md": first(files, r"(^|/)memory\.md$"),
            "LEARNINGS.md": first(files, r"(^|/)learnings\.md$"),
        },
        "hygiene": {
            "SECURITY.md": first(files, r"^(\.github/)?security\.md$"),
            "CONTRIBUTING.md": first(files, r"^(\.github/)?contributing\.md$"),
            "CODE_OF_CONDUCT.md": first(files, r"^(\.github/)?code_of_conduct\.md$"),
            "workflows": count(files, r"^\.github/workflows/[^/]+\.ya?ml$"),
            "scheduled": any(re.search(r"^\s*(schedule|workflow_dispatch)\s*:", show(path, ref, f), re.M)
                             for f in files if re.match(r"^\.github/workflows/[^/]+\.ya?ml$", f)),
            "tests": count(files, r"(^|/)(tests?|__tests__|spec)/|\.(test|spec)\.(ts|tsx|js|mjs|py)$|(^|/)test_[^/]+\.py$"),
            "evals": count(files, r"(^|/)evals?/|(^|/)eval[^/]*\.(ts|js|mjs|py|sh)$"),
        },
        "github": {},
    }
    if slug and not offline:
        row["github"] = gh_repo(*slug)
    return row


def scan_owner(owner: str, clones: str | Path | None = None, offline: bool = False) -> list[dict]:
    """Every repository of a GitHub owner: a clone under `clones/<name>` is scanned in full; the rest get a root
    listing through the API."""
    if not gh_available():
        raise RuntimeError("scanning an owner needs gh (https://cli.github.com), signed in")
    raw = out(["gh", "repo", "list", owner, "--limit", "300", "--json", "name,visibility,isArchived,isFork"])
    if not raw:
        raise RuntimeError(f"gh repo list {owner} returned nothing: check `gh auth status`")
    rows = []
    for r in sorted(json.loads(raw), key=lambda r: r["name"].lower()):
        clone = Path(clones).expanduser() / r["name"] if clones else None
        if clone and is_repo(clone):
            rows.append(scan_clone(clone, offline=offline))
        else:
            listing = out(["gh", "api", f"repos/{owner}/{r['name']}/contents", "--jq", ".[].name"]).split()
            rows.append({"name": r["name"], "owner": owner, "path": "", "ref": "github-api", "root_files": listing,
                         "github": {"visibility": r["visibility"].lower(), "archived": r["isArchived"]},
                         "fork": r["isFork"]})
    return rows


def stamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
