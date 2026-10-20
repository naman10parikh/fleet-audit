#!/usr/bin/env python3
"""A Claude Code PreToolUse hook: before a `git push`, scrub the repository's tree with your patterns file, and
block the push when a pattern matches.

The patterns file is $FLEET_AUDIT_PATTERNS, else .fleet-audit/scrub-patterns.txt inside the repository (keep that
folder out of git). With no patterns file, the push goes ahead. A match exits 2 with the pattern numbers and the
file names, never the matched text; that blocks the command and tells the agent what to fix. It changes no file.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

if {"-h", "--help"} & set(sys.argv[1:]):
    print(__doc__)
    raise SystemExit(0)

try:
    from fleet_audit.scrub import scrub
except ImportError:  # running from a clone or the plugin folder: use the source beside this file
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from fleet_audit.scrub import scrub

PUSH = re.compile(r"(^|[;&|(\s])git(\s+-C\s+\S+)?\s+push\b")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if payload.get("tool_name", "Bash") != "Bash" or not PUSH.search(command):
        return 0
    cwd = Path(payload.get("cwd") or os.getcwd())
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True).stdout.strip()
    if not top:
        return 0
    patterns = Path(os.environ.get("FLEET_AUDIT_PATTERNS") or Path(top) / ".fleet-audit" / "scrub-patterns.txt")
    if not patterns.expanduser().is_file():
        return 0
    result = scrub(top, patterns, head=True, tree_only=True)
    if result.get("clean", True):
        return 0
    hits = "; ".join(f"{k} in {', '.join(sorted(v))}" for k, v in result["tree"].items())
    print(f"fleet-audit blocked this push: the committed tree matches scrub patterns ({hits}). Remove those lines, "
          "commit, and push again. The matched text is not shown.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
