"""The scrub gate a repository passes before it is made public: patterns over the tree, the history and the commit
messages, and secrets by gitleaks, because going public publishes every commit.

The patterns come from a file you name and keep out of every repository (scrub-patterns.example.txt shows the
format). Results name a pattern by its number (p1, p2, ...) and never print the matched text, so a report can be
shared without repeating what it found. One pattern per line:

  regex                 case-insensitive Perl-style regex
  CS regex              case-sensitive
  regex==>replacement   what the history plan writes instead of a match (default: [removed])
  # comment             ignored
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .gitutil import default_ref, is_repo, run

LOCKFILES = [":!*.lock", ":!pnpm-lock.yaml", ":!package-lock.json"]
POSIX = {"[:space:]": r"\s", "[:digit:]": "0-9", "[:alpha:]": "A-Za-z", "[:alnum:]": "A-Za-z0-9", "[:upper:]": "A-Z",
         "[:lower:]": "a-z"}


@dataclass
class Pattern:
    regex: str
    case_sensitive: bool
    replacement: str = "[removed]"


def patterns(file: str | Path) -> list[Pattern]:
    path = Path(file).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"no patterns file at {path}")
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cs = line.startswith("CS ")
        body = line[3:] if cs else line
        regex, _, repl = body.rpartition("==>") if "==>" in body else (body, "", "")
        out.append(Pattern(regex, cs, repl or "[removed]"))
    return out


def ere(pat: str) -> str:
    """`git log -G` reads POSIX extended regexes. macOS uses BSD regex, which has no \\b, \\d, \\s or \\w, so a
    pattern using them would never match there; translate them. Other platforms take them as they are."""
    if sys.platform != "darwin":
        return pat
    pat = re.sub(r"\\b(?=[\w(\[])", "[[:<:]]", pat)
    pat = re.sub(r"(?<=[\w)\]+*?}])\\b", "[[:>:]]", pat)
    return pat.replace(r"\d", "[0-9]").replace(r"\s", "[[:space:]]").replace(r"\w", "[[:alnum:]_]")


def python_regex(pat: str, cs: bool) -> str:
    """The same pattern for Python's re (commit messages here, git filter-repo in the history plan): POSIX classes
    become Python ones, and a case-insensitive pattern gets (?i)."""
    for k, v in POSIX.items():
        pat = pat.replace(k, v)
    if "[:" in pat:
        raise ValueError("a scrub pattern uses a POSIX class this tool cannot translate")
    return pat if cs or pat.startswith("(?i)") else "(?i)" + pat


def messages(path: Path) -> list[str]:
    """Every commit message on every ref: going public publishes them too."""
    text = run(["git", "log", "--all", "--format=%B%x1e"], path).stdout
    return [m for m in text.split("\x1e") if m.strip()]


def gitleaks(path: Path, ref: str) -> dict:
    """Secrets over the whole history, redacted. The repository's own .gitleaks.toml (read from the ref, so a bare
    mirror works too) is honoured."""
    if not shutil.which("gitleaks"):
        return {"secrets": None, "secret_rules": [], "gitleaks": "not installed"}
    own = run(["git", "show", f"{ref}:.gitleaks.toml"], path)
    with tempfile.TemporaryDirectory() as tmp:
        extra = []
        if own.returncode == 0:
            cfg = Path(tmp) / "gitleaks.toml"
            cfg.write_text(own.stdout)
            extra = ["--config", str(cfg)]
        report = Path(tmp) / "report.json"
        r = run(["gitleaks", "git", "--no-banner", "--redact", "-f", "json", "-r", str(report), *extra, str(path)])
        if "unknown command" in (r.stderr + r.stdout):
            run(["gitleaks", "detect", "--no-banner", "--redact", "-f", "json", "-r", str(report), "-s", str(path),
                 "--log-opts=--all", *extra])
        try:
            leaks = json.loads(report.read_text() or "[]") if report.exists() else []
        except ValueError:
            leaks = []
    return {"secrets": len(leaks), "secret_rules": sorted({f'{x.get("RuleID")}:{x.get("File")}' for x in leaks})[:40]}


def scrub(path: str | Path, patterns_file: str | Path, head: bool = False, tree_only: bool = False,
          skip_leaks: bool = False) -> dict:
    """Scrub a clone or a bare mirror. `head` checks the local HEAD (before a push); `tree_only` checks only the
    files (seconds); `skip_leaks` skips gitleaks."""
    path = Path(path).expanduser().resolve()
    if not is_repo(path):
        return {"name": path.name, "error": "not a git repository"}
    ref = default_ref(path, head)
    tree, history, subjects = {}, {}, {}
    msgs = [] if tree_only else messages(path)
    for i, p in enumerate(patterns(patterns_file), 1):
        flags = ["-I", "-c", "-P"] + ([] if p.case_sensitive else ["-i"])  # Perl regexes: \b and \d work everywhere
        hits = run(["git", "grep", *flags, p.regex, ref, "--", ".", *LOCKFILES], path).stdout.splitlines()
        files = {h.split(":", 2)[1]: int(h.rsplit(":", 1)[1]) for h in hits if h.count(":") >= 2}
        if files:
            tree[f"p{i}"] = files
        if tree_only:
            continue
        log = ["git", "log", "--all", "--format=%h", "-E", f"-G{ere(p.regex)}"]
        n = len(run(log + ([] if p.case_sensitive else ["--regexp-ignore-case"]), path).stdout.split())
        if n:
            history[f"p{i}"] = n
        rx = re.compile(python_regex(p.regex, p.case_sensitive))
        m = sum(1 for msg in msgs if rx.search(msg))
        if m:
            subjects[f"p{i}"] = m
    result = {"name": path.name, "ref": ref, "tree": tree}
    if tree_only:
        return result | {"tree_only": True, "clean": not tree}
    result |= {"history_commits": history, "message_commits": subjects}
    leaks = {"secrets": None, "secret_rules": [], "gitleaks": "skipped"} if skip_leaks else gitleaks(path, ref)
    result |= leaks
    result["clean"] = not tree and not history and not subjects and not leaks["secrets"]
    return result


def line(r: dict) -> str:
    """One line per repository, with pattern numbers and counts only."""
    if "error" in r:
        return f'{r["name"]:<22} {r["error"]}'
    tree = " ".join(f"{k}:{sum(v.values())}" for k, v in r["tree"].items()) or "0"
    if r.get("tree_only"):
        return f'{r["name"]:<22} {"CLEAN" if r["clean"] else "DIRTY"} tree {tree}'
    hist = " ".join(f"{k}:{v}" for k, v in r["history_commits"].items()) or "0"
    if r["message_commits"]:
        hist += " msg " + " ".join(f"{k}:{v}" for k, v in r["message_commits"].items())
    secrets = r.get("gitleaks") or r["secrets"]
    return (f'{r["name"]:<22} {"CLEAN" if r["clean"] else "DIRTY":<6} tree {tree:<20} history {hist:<20} '
            f"secrets {secrets}")
