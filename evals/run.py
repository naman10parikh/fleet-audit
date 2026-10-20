#!/usr/bin/env python3
"""fleet-audit's evals: golden tasks on fixture repositories, each one pass or fail.

  python3 evals/run.py          run every eval; exit 1 on any failure
  python3 evals/run.py --json   print the results as JSON

The fixture repositories are built fresh in a temporary folder (evals/repos.py): a bare one, a complete one and a
leaky one. The tasks: detection precision and recall over the surfaces; the exact checks a bare repository misses;
nothing missing on a complete one; a list needing only its own checks; the scrub finding the tree, history and
message hits by number without ever printing the matched text; the kit writing exactly what is missing, a second
run writing nothing, and a dry run writing nothing; the report; and an MCP round trip whose kit tool is a dry run
unless asked.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))
os.environ.setdefault("FLEET_AUDIT_RUNLOG", "off")

import repos  # noqa: E402
from fleet_audit.checks import checks  # noqa: E402
from fleet_audit.kit import kit  # noqa: E402
from fleet_audit.report import report  # noqa: E402
from fleet_audit.scan import scan_clone  # noqa: E402
from fleet_audit.scrub import line, scrub  # noqa: E402

BARE_MISSING = {"AGENTS.md", "llms.txt", "licence", "SECURITY.md", "CONTRIBUTING.md", "README with a quick start",
                "SOUL.md", "CLAUDE.md", "GEMINI.md", "3+ skills", "2+ sub-agents", "a hook", "MCP server", "CLI",
                "plugin.json", "marketplace", "Gemini extension", "agent card", "dsip.json", "CI", "scheduled loop",
                "memory"}
KIT_FIXES = {"licence", "SECURITY.md", "CONTRIBUTING.md", "plugin.json", "marketplace", "Gemini extension", "agent card"}
FACTS = {"name": "bare", "kind": "tool", "one_liner": "A small tool.", "runtime": "python", "cli_bin": "bare",
         "mcp_bin": "bare-mcp", "skills": [{"path": "skills/one/SKILL.md", "what": "When one is needed."}],
         "components": {"Identity": {"grade": "🟡", "where": "README.md:1"}}, "dsip_level": "L0", "year": 2026}


def missing(scan: dict, kind: str | None = None) -> set[str]:
    return {c.label for c in checks(scan, kind=kind) if c.status == "fail"}


def detection(tmp: Path) -> list[tuple[str, bool, str]]:
    full, empty = scan_clone(repos.complete(tmp), offline=True), scan_clone(repos.bare(tmp), offline=True)
    keys = [k for k in full["surfaces"] if k not in ("cursor_rules", "copilot", "plugin_hooks")]
    tp = sum(1 for k in keys if full["surfaces"][k])
    fp = sum(1 for k in keys if empty["surfaces"][k])
    fn = len(keys) - tp
    precision, recall = tp / ((tp + fp) or 1), tp / ((tp + fn) or 1)
    out = [("detect-surfaces", precision == 1.0 and recall == 1.0,
            f"precision {precision:.2f} recall {recall:.2f} over {len(keys)} surfaces")]
    got = missing(empty)
    out.append(("golden-bare-misses-exactly", got == BARE_MISSING,
                "as expected" if got == BARE_MISSING else f"extra {sorted(got - BARE_MISSING)}, absent "
                f"{sorted(BARE_MISSING - got)}"))
    out.append(("golden-complete-misses-nothing", not missing(full), ", ".join(sorted(missing(full))) or "0 missing"))
    as_list = missing(empty, kind="list")
    out.append(("golden-list-kind", as_list == BARE_MISSING & {"AGENTS.md", "llms.txt", "licence", "SECURITY.md",
                                                               "CONTRIBUTING.md", "README with a quick start"},
                f"{len(checks(empty, kind='list'))} checks, missing {sorted(as_list)}"))
    return out


def scrubbing(tmp: Path) -> list[tuple[str, bool, str]]:
    repo, pats = repos.leaky(tmp), repos.patterns_file(tmp)
    r = scrub(repo, pats)
    printed = line(r) + json.dumps(r)
    secret_free = repos.EMAIL not in printed and repos.HOME_PATH not in printed and "jane" not in printed
    return [
        ("golden-scrub-tree", r["tree"] == {"p1": {"notes.txt": 1}}, f"tree {r['tree']}"),
        ("golden-scrub-history", r["history_commits"].get("p1", 0) >= 1 and r["history_commits"].get("p2", 0) >= 1,
         f"history {r['history_commits']}"),
        ("golden-scrub-messages", r["message_commits"] == {"p1": 1}, f"messages {r['message_commits']}"),
        ("scrub-never-prints-matches", secret_free, "no matched text in the output" if secret_free else "LEAKED"),
        ("golden-scrub-tree-only", scrub(repo, pats, tree_only=True)["clean"] is False, "tree-only finds p1"),
    ]


def kitting(tmp: Path) -> list[tuple[str, bool, str]]:
    repo = repos.bare(tmp / "kit")
    before = missing(scan_clone(repo, offline=True))
    dry = kit(repo, FACTS, "someone", "Some One", dry_run=True)
    untouched = not subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True).stdout
    wrote = kit(repo, FACTS, "someone", "Some One")
    repos.git(repo, "add", "-A")
    repos.git(repo, "commit", "-q", "-m", "kit")
    after = missing(scan_clone(repo, offline=True))
    again = kit(repo, FACTS, "someone", "Some One")
    readme = (repo / "README.md").read_text()
    return [
        ("kit-dry-run-writes-nothing", untouched and len(dry) == len(wrote), f"{len(dry)} listed, tree untouched"),
        ("golden-kit-fixes-its-checks", not (KIT_FIXES & after) and KIT_FIXES <= before,
         f"fixed {sorted(KIT_FIXES & before)}"),
        ("kit-idempotent", again == [], "second run writes nothing" if not again else f"rewrote {again}"),
        ("kit-readme-blocks-once", all(readme.count(f"<!-- fleet:{b}:start -->") == 1
                                       for b in ("header", "use", "anatomy", "footer")), "each block once"),
        ("kit-uvx-for-python", "uvx --from git+https://github.com/someone/bare bare-mcp" in readme, "uvx commands"),
    ]


def reporting(tmp: Path) -> list[tuple[str, bool, str]]:
    rows = [(s, checks(s)) for s in (scan_clone(repos.complete(tmp / "r"), offline=True),
                                     scan_clone(repos.bare(tmp / "r"), offline=True))]
    text = report(rows, "now", "test")
    return [("golden-report", "| complete | local | 22/26 |" in text and "| bare |" in text and "**missing**" in text,
             f"{len(text.splitlines())} lines")]


def mcp(tmp: Path) -> list[tuple[str, bool, str]]:
    repo = repos.bare(tmp / "mcp")
    facts = tmp / "facts.json"
    facts.write_text(json.dumps(FACTS))
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "fleet_kit", "arguments": {
                "path": str(repo), "facts": str(facts), "owner": "someone", "author": "Some One"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "fleet_check", "arguments": {
                "path": str(repo), "offline": True}}}]
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    proc = subprocess.run([sys.executable, "-m", "fleet_audit.mcp_server"], input="\n".join(map(json.dumps, msgs)),
                          capture_output=True, text=True, env=env, timeout=120)
    replies = {r["id"]: r for r in (json.loads(x) for x in proc.stdout.splitlines() if x.strip())}
    tools = [t["name"] for t in replies.get(2, {}).get("result", {}).get("tools", [])]
    kit_text = replies.get(3, {}).get("result", {}).get("content", [{}])[0].get("text", "")
    untouched = not subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True).stdout
    check = json.loads(replies.get(4, {}).get("result", {}).get("content", [{}])[0].get("text", "{}") or "{}")
    return [("mcp-tools-list", len(tools) == 5, ", ".join(tools)),
            ("mcp-kit-is-a-dry-run", "would write" in kit_text and untouched, "listed, wrote nothing"),
            ("mcp-check", check.get("tally", {}).get("fail") == len(BARE_MISSING), f"tally {check.get('tally')}")]


def main() -> int:
    if {"-h", "--help"} & set(sys.argv[1:]):
        print(__doc__)
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        results = detection(t / "d") + scrubbing(t / "s") + kitting(t) + reporting(t) + mcp(t)
    failed = [r for r in results if not r[1]]
    if "--json" in sys.argv:
        print(json.dumps({"passed": len(results) - len(failed), "failed": len(failed),
                          "results": [{"eval": n, "ok": ok, "detail": d} for n, ok, d in results]}, indent=2))
    else:
        for name, ok, detail in results:
            print(f"{'PASS' if ok else 'FAIL'}  {name:<32} {detail}")
        print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
