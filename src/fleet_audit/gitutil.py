"""Small helpers around git and gh. They read; the only writes are the kit's and the history plan's scratch mirror."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


def run(cmd: list[str], cwd: str | Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def out(cmd: list[str], cwd: str | Path | None = None) -> str:
    r = run(cmd, cwd)
    return r.stdout if r.returncode == 0 else ""


def is_repo(path: Path) -> bool:
    return (path / ".git").exists() or (path / "HEAD").exists()


def default_ref(path: Path, head: bool = False) -> str:
    """HEAD when asked (the local state before a push), else the remote's default branch when known, else HEAD."""
    if head:
        return "HEAD"
    remote = out(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], path).strip()
    return remote or "HEAD"


def tree(path: Path, ref: str) -> list[str]:
    return [line for line in out(["git", "ls-tree", "-r", "--name-only", ref], path).splitlines() if line]


def show(path: Path, ref: str, file: str) -> str:
    return out(["git", "show", f"{ref}:{file}"], path)


def github_slug(path: Path) -> tuple[str, str] | None:
    """(owner, name) from the origin remote, when it points at github.com."""
    url = out(["git", "remote", "get-url", "origin"], path).strip()
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    return (m.group(1), m.group(2)) if m else None


def gh_available() -> bool:
    return shutil.which("gh") is not None


def gh_repo(owner: str, name: str) -> dict:
    """GitHub's facts for one repository, or {} when gh is missing or the lookup fails."""
    if not gh_available():
        return {}
    fields = "visibility,description,repositoryTopics,stargazerCount,defaultBranchRef,isArchived"
    raw = out(["gh", "repo", "view", f"{owner}/{name}", "--json", fields])
    if not raw:
        return {}
    r = json.loads(raw)
    return {"visibility": (r.get("visibility") or "").lower(), "description": r.get("description") or "",
            "topics": [t["name"] for t in (r.get("repositoryTopics") or [])], "stars": r.get("stargazerCount", 0),
            "branch": (r.get("defaultBranchRef") or {}).get("name") or "", "archived": r.get("isArchived", False)}
