"""fleet-audit's MCP server: JSON-RPC 2.0 over stdio, standard library only.

It exposes the scan, the checks, the report and the scrub as tools that only read. The one tool that can write is
fleet_kit, and it writes only when called with write=true; by default it lists what it would write.
Run: fleet-audit-mcp (or python3 -m fleet_audit.mcp_server).
"""

from __future__ import annotations

import json
import sys
import time

from . import __version__, runlog
from .checks import KINDS, checks, tally
from .cli import facts_for
from .kit import kit, load_facts
from .report import report
from .scan import scan_clone, stamp
from .scrub import scrub

PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
HELP = """fleet-audit-mcp: fleet-audit's MCP server (stdio, JSON-RPC 2.0).

usage: fleet-audit-mcp [--help] [--version]

Tools: fleet_scan, fleet_check, fleet_report, fleet_scrub (read only) and fleet_kit (writes only with write=true).
Add it to a client, for example:
  claude mcp add --transport stdio fleet-audit -- uvx --from git+https://github.com/naman10parikh/fleet-audit fleet-audit-mcp
"""
PATH = {"type": "string", "description": "A local clone (a folder path)."}
READING = {"head": {"type": "boolean", "description": "Read the local HEAD instead of the remote default branch."},
           "offline": {"type": "boolean", "description": "Skip GitHub's facts (no gh call)."}}

TOOLS = [
    {"name": "fleet_scan",
     "description": "Measure one repository's agent-native surfaces (AGENTS.md, CLAUDE.md, llms.txt, skills, "
                    "sub-agents, hooks, MCP server, CLI, plugin, extension, agent card, dsip.json), identity and "
                    "hygiene files, README shape and GitHub facts. Reads only.",
     "inputSchema": {"type": "object", "properties": {"path": PATH, **READING}, "required": ["path"]}},
    {"name": "fleet_check",
     "description": "Run the standard's checks on one repository: each passes, is missing (with the fix), or is "
                    "unknown. Reads only.",
     "inputSchema": {"type": "object", "properties": {
         "path": PATH, "facts": {"type": "string", "description": "Path to the repository's facts file (JSON)."},
         "kind": {"type": "string", "enum": list(KINDS)},
         "patterns": {"type": "string", "description": "A patterns file: also run a tree scrub."}, **READING},
         "required": ["path"]}},
    {"name": "fleet_report",
     "description": "A Markdown readiness report over several repositories. Reads only.",
     "inputSchema": {"type": "object", "properties": {
         "paths": {"type": "array", "items": {"type": "string"}},
         "facts_dir": {"type": "string", "description": "A folder of facts files named <repository>.json."},
         "kind": {"type": "string", "enum": list(KINDS)}, **READING}, "required": ["paths"]}},
    {"name": "fleet_scrub",
     "description": "Scrub a repository with your patterns file: tree, history, commit messages and secrets. "
                    "Results name patterns by number and never repeat the matched text. Reads only.",
     "inputSchema": {"type": "object", "properties": {
         "path": PATH, "patterns": {"type": "string", "description": "Your patterns file."},
         "head": {"type": "boolean"}, "tree_only": {"type": "boolean"}, "skip_leaks": {"type": "boolean"}},
         "required": ["path", "patterns"]}},
    {"name": "fleet_kit",
     "description": "List the standard files and README blocks a repository is missing, from its facts file. "
                    "Writes them only when write is true; it never deletes and never commits.",
     "inputSchema": {"type": "object", "properties": {
         "path": PATH, "facts": {"type": "string", "description": "Path to the facts file (JSON)."},
         "owner": {"type": "string"}, "author": {"type": "string"},
         "write": {"type": "boolean", "description": "Write the files (default false: a dry run)."}},
         "required": ["path"]}},
]


def call(name: str, a: dict) -> tuple[str, bool]:
    if name == "fleet_scan":
        row = scan_clone(a["path"], bool(a.get("head")), bool(a.get("offline")))
        return json.dumps(row, indent=1, ensure_ascii=False), "error" in row
    if name == "fleet_check":
        row = scan_clone(a["path"], bool(a.get("head")), bool(a.get("offline")))
        if "error" in row:
            return row["error"], True
        scrubbed = scrub(a["path"], a["patterns"], head=bool(a.get("head")), tree_only=True) if a.get("patterns") else None
        results = checks(row, load_facts(a.get("facts")), scrubbed, a.get("kind"))
        return json.dumps({"name": row["name"], "tally": tally(results), "checks": [c.as_dict() for c in results]},
                          indent=1, ensure_ascii=False), False
    if name == "fleet_report":
        rows = []
        for p in a.get("paths") or []:
            row = scan_clone(p, bool(a.get("head")), bool(a.get("offline")))
            if "error" not in row:
                rows.append((row, checks(row, facts_for(row["name"], a.get("facts_dir")), None, a.get("kind"))))
        return report(rows, stamp(), __version__), False
    if name == "fleet_scrub":
        r = scrub(a["path"], a["patterns"], bool(a.get("head")), bool(a.get("tree_only")), bool(a.get("skip_leaks")))
        return json.dumps(r, indent=1), "error" in r
    if name == "fleet_kit":
        facts = load_facts(a.get("facts"))
        actions = kit(a["path"], facts, a.get("owner") or facts.get("owner", ""), a.get("author") or facts.get("author", ""),
                      dry_run=not a.get("write"))
        verb = "wrote" if a.get("write") else "would write"
        return "\n".join(f"{verb} {rel} ({why})" for rel, why in actions) or "nothing to write", False
    return f"unknown tool {name!r}", True


def send(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def handle(req: dict) -> dict | None:
    method, rid = req.get("method"), req.get("id")
    if rid is None:  # a notification: no reply
        return None
    if method == "initialize":
        asked = (req.get("params") or {}).get("protocolVersion")
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": asked if asked in PROTOCOLS else PROTOCOLS[1], "capabilities": {"tools": {}},
            "serverInfo": {"name": "fleet-audit", "version": __version__}}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = req.get("params") or {}
        name, started = params.get("name", ""), time.monotonic()
        try:
            text, is_error = call(name, params.get("arguments") or {})
        except Exception as exc:  # report to the client; never kill the server
            text, is_error = f"error: {exc}", True
        runlog.append(f"mcp:{name}", started, "fail" if is_error else "ok")
        return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": text}],
                                                         "isError": is_error}}
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"method not found: {method}"}}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if {"-h", "--help"} & set(argv):
        print(HELP)
        return 0
    if "--version" in argv:
        print(f"fleet-audit-mcp {__version__}")
        return 0
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            continue
        reply = handle(req)
        if reply is not None:
            send(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
