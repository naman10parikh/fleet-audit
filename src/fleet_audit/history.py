"""The history plan before a repository goes public: rewrite a scratch copy, then prove it clean. It pushes nothing.

Going public publishes every commit, so the history must pass the same scrub as the tree. For each repository this
clones a bare mirror into a scratch folder and runs git filter-repo there to
  1. drop every internal working note named in the facts file's "internal_files" from every commit;
  2. replace every pattern from your patterns file, in files and in commit messages (each pattern's replacement, or
     [removed]), plus any extra [regex, replacement] pairs in the facts file's "history_replace";
then scrubs the rewritten mirror. Pushing that history is a force-push, so it is left to a person.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .gitutil import run
from .scrub import patterns, python_regex, scrub


def paths_in_history(mirror: Path) -> set[str]:
    return set(run(["git", "log", "--all", "--format=", "--name-only"], mirror).stdout.split("\n")) - {""}


def plan(source: str, patterns_file: str | Path, out_dir: str | Path, facts: dict | None = None) -> dict:
    """`source` is anything git can clone (owner/name through gh, a URL, or a local path)."""
    if not shutil.which("git-filter-repo"):
        return {"source": source, "error": "git filter-repo is not installed (pip install git-filter-repo)"}
    facts = facts or {}
    name = Path(source.rstrip("/")).name.removesuffix(".git")
    base = Path(out_dir).expanduser()
    base.mkdir(parents=True, exist_ok=True)
    mirror = base / f"{name}.git"
    if mirror.exists():
        return {"source": source, "error": f"a mirror already exists at {mirror}; choose another --out folder"}
    local = Path(source).expanduser()
    if local.exists():
        r = run(["git", "clone", "--mirror", "--quiet", str(local), str(mirror)])
    elif source.startswith(("http://", "https://", "git@", "ssh://")):
        r = run(["git", "clone", "--mirror", "--quiet", source, str(mirror)])
    else:  # owner/name, through gh and its credentials
        r = run(["gh", "repo", "clone", source, str(mirror), "--", "--mirror", "--quiet"])
    if r.returncode:
        return {"source": source, "error": "clone failed: " + r.stderr.strip()[:200]}
    count = lambda: int(run(["git", "rev-list", "--all", "--count"], mirror).stdout.strip() or 0)  # noqa: E731
    before = count()
    internal = [p.rstrip("/") for p in facts.get("internal_files", [])]
    seen = paths_in_history(mirror)
    dropped = sorted(p for p in internal if p in seen or any(s.startswith(p + "/") for s in seen))
    lines = [f"regex:{python_regex(p.regex, p.case_sensitive)}==>{p.replacement}" for p in patterns(patterns_file)]
    lines += [f"regex:{pat}==>{rep}" for pat, rep in facts.get("history_replace", [])]
    expressions = base / f"{name}.replace.txt"
    expressions.write_text("\n".join(lines) + "\n")
    args = ["git", "filter-repo", "--force", "--replace-text", str(expressions), "--replace-message", str(expressions)]
    if dropped:
        listing = base / f"{name}.paths.txt"
        listing.write_text("\n".join(dropped) + "\n")
        args += ["--invert-paths", "--paths-from-file", str(listing)]
    r = run(args, mirror)
    if r.returncode:
        return {"source": source, "error": "filter-repo failed: " + r.stderr.strip()[-300:]}
    after = scrub(mirror, patterns_file)
    return {"source": source, "mirror": str(mirror), "commits_before": before, "commits_after": count(),
            "internal_dropped": dropped, "internal_not_in_history": sorted(set(internal) - set(dropped)),
            "after": {k: after.get(k) for k in ("tree", "history_commits", "message_commits", "secrets", "clean")}}
