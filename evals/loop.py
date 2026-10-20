#!/usr/bin/env python3
"""fleet-audit's improvement loop: run the evals, audit this repository with its own checks, scrub its own tree with
the shipped example patterns, and write proposals.

  python3 evals/loop.py [--out proposals/latest.md]

It never edits a file outside the proposals and never commits: a person reads the proposals and makes every change.
  1. the evals (evals/run.py): a failure becomes a proposal to fix the regression, and the loop exits 1;
  2. the self-audit (`fleet-audit check .`): every missing check becomes a proposal, with its fix;
  3. the self-scrub (the example patterns over this tree): any match becomes a proposal.
With GITHUB_OUTPUT set, it writes propose=true or propose=false for the workflow that opens the issue.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fleet_audit.checks import checks  # noqa: E402
from fleet_audit.scan import scan_clone  # noqa: E402
from fleet_audit.scrub import scrub  # noqa: E402


def evals() -> tuple[bool, dict]:
    proc = subprocess.run([sys.executable, str(ROOT / "evals" / "run.py"), "--json"], capture_output=True, text=True,
                          env={**os.environ, "FLEET_AUDIT_RUNLOG": "off"}, timeout=600)
    try:
        return proc.returncode == 0, json.loads(proc.stdout)
    except ValueError:
        return False, {"passed": 0, "failed": 1, "results": [{"eval": "run.py", "ok": False, "detail": proc.stderr[-300:]}]}


def main() -> int:
    args = sys.argv[1:]
    if {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    out = Path(args[args.index("--out") + 1]) if "--out" in args else ROOT / "proposals" / "latest.md"
    ok, report = evals()
    own = checks(scan_clone(ROOT, head=True, offline=True))
    tree = scrub(ROOT, ROOT / "scrub-patterns.example.txt", head=True, tree_only=True)["tree"]
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# fleet-audit improvement loop", "", f"Run {stamp}. Evals: {report['passed']} passed, "
             f"{report['failed']} failed.", ""]
    n = 0
    for r in report["results"]:
        if not r["ok"]:
            n += 1
            lines += [f"## {n}. Fix the regression in `{r['eval']}`", "", f"The eval failed: {r['detail']}", "",
                      "Reproduce with `python3 evals/run.py`, fix the cause, and add a test that would have caught it.", ""]
    for c in own:
        if c.status == "fail":
            n += 1
            lines += [f"## {n}. This repository misses its own check: {c.label}", "", c.fix, ""]
    for pat, files in tree.items():
        n += 1
        lines += [f"## {n}. The tree matches example pattern {pat}", "", f"In: {', '.join(sorted(files))}. Remove the "
                  "match, or assemble a test string at run time so the file never holds it whole.", ""]
    if not n:
        lines += ["Nothing to propose: every eval passes, every check this repository can decide passes, and its tree "
                  "matches no example pattern.", ""]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"evals {'pass' if ok else 'FAIL'}; {n} proposal(s) written to {out}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write(f"propose={'true' if n else 'false'}\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
