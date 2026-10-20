"""The fleet-audit command line. Every command answers --help; nothing runs before the arguments are read."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from . import __version__, runlog
from .checks import KINDS, checks, tally
from .history import plan
from .kit import kit, load_facts
from .report import report
from .route import route
from .scan import scan_clone, scan_owner, stamp
from .scrub import line, scrub

DESCRIPTION = "Scan your repositories for every surface coding agents need, and fix them."
EPILOG = """examples:
  fleet-audit check .                                   what this repository has, and the fix for each gap
  fleet-audit report ~/code/* --out readiness.md        one Markdown page over many repositories
  fleet-audit scan --owner <you> --clones ~/code        every repository of a GitHub owner
  fleet-audit scrub . --patterns ~/scrub-patterns.txt   before a repository goes public
  fleet-audit kit . --facts facts.json --owner <you> --author "Your Name" --dry-run
  fleet-audit history <you>/<repo> --patterns ~/scrub-patterns.txt --out /tmp/plan

Keep your patterns file outside every repository; scrub-patterns.example.txt shows the format.
The MCP server is fleet-audit-mcp."""


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fleet-audit", description=DESCRIPTION, epilog=EPILOG,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"fleet-audit {__version__}")
    sub = p.add_subparsers(dest="cmd", metavar="<command>")

    def reading(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--head", action="store_true", help="read the local HEAD instead of the remote default branch")
        sp.add_argument("--offline", action="store_true", help="skip GitHub's facts (no gh call)")

    s = sub.add_parser("scan", help="measure the agent-native surfaces of local clones, or of an owner's repositories")
    s.add_argument("paths", nargs="*", help="local clones")
    s.add_argument("--owner", help="a GitHub user or organisation: scan every repository it has (needs gh)")
    s.add_argument("--clones", help="with --owner: the folder that holds clones named like the repositories")
    s.add_argument("--out", help="write the scan as JSON to this file")
    reading(s)

    c = sub.add_parser("check", help="the standard's checks for one repository, with the fix for each gap")
    c.add_argument("path", nargs="?", default=".", help="a local clone (default: .)")
    c.add_argument("--facts", help="the repository's facts file (JSON)")
    c.add_argument("--kind", choices=KINDS, help="the repository's kind (default: the facts file's, else tool)")
    c.add_argument("--patterns", help="also run a tree scrub with this patterns file")
    c.add_argument("--json", action="store_true", help="print the checks as JSON")
    reading(c)

    r = sub.add_parser("report", help="a Markdown report over one or more repositories")
    r.add_argument("paths", nargs="+", help="local clones")
    r.add_argument("--facts-dir", help="a folder of facts files named <repository>.json")
    r.add_argument("--kind", choices=KINDS, help="the kind for repositories without a facts file (default: tool)")
    r.add_argument("--out", help="write the report to this file (default: print it)")
    reading(r)

    sc = sub.add_parser("scrub", help="patterns, history, commit messages and secrets, before a repository goes public")
    sc.add_argument("paths", nargs="+", help="local clones or bare mirrors")
    sc.add_argument("--patterns", required=True, help="your patterns file (keep it outside every repository)")
    sc.add_argument("--head", action="store_true", help="check the local HEAD, before a push")
    sc.add_argument("--tree", action="store_true", help="the tree only (seconds)")
    sc.add_argument("--no-leaks", action="store_true", help="skip gitleaks")
    sc.add_argument("--out", help="write the results as JSON to this file")

    k = sub.add_parser("kit", help="write the missing standard files and README blocks from a facts file")
    k.add_argument("path", nargs="?", default=".", help="the repository to write into (default: .)")
    k.add_argument("--facts", help="the facts file (JSON); see `fleet-audit kit --help` and the README")
    k.add_argument("--owner", help="the GitHub owner (default: the facts file's owner)")
    k.add_argument("--author", help="the licence holder (default: the facts file's author)")
    k.add_argument("--dry-run", action="store_true", help="list what it would write, and write nothing")

    h = sub.add_parser("history", help="rewrite a scratch mirror to drop internal notes and scrub hits (pushes nothing)")
    h.add_argument("sources", nargs="+", help="owner/name (through gh), a git URL, or a local path")
    h.add_argument("--patterns", required=True, help="your patterns file")
    h.add_argument("--facts-dir", help="a folder of facts files named <repository>.json (for internal_files)")
    h.add_argument("--out", help="the scratch folder for the mirrors (default: a new temporary folder)")

    ro = sub.add_parser("route", help="the skill and the command for a task in plain words")
    ro.add_argument("task", nargs="+", help="the task, in plain words")
    ro.add_argument("--json", action="store_true", help="print the route as JSON")

    ru = sub.add_parser("runs", help="show the run log")
    ru.add_argument("--last", type=int, default=20, help="how many runs (default: 20)")
    return p


def facts_for(name: str, folder: str | None) -> dict:
    return load_facts(Path(folder) / f"{name}.json") if folder and (Path(folder) / f"{name}.json").exists() else {}


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.cmd is None:
        parser().print_help()
        return 0
    started = time.monotonic()
    try:
        code, facts = run(args)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"fleet-audit: {exc}", file=sys.stderr)
        runlog.append(args.cmd, started, "error", error=str(exc)[:200])
        return 2
    if args.cmd != "runs":
        runlog.append(args.cmd, started, "ok" if code == 0 else "fail", **facts)
    return code


def run(args: argparse.Namespace) -> tuple[int, dict]:
    if args.cmd == "scan":
        if not args.paths and not args.owner:
            raise ValueError("name a clone, or --owner")
        rows = scan_owner(args.owner, args.clones, args.offline) if args.owner else []
        rows += [scan_clone(p, args.head, args.offline) for p in args.paths]
        if args.out:
            Path(args.out).write_text(json.dumps({"scanned": stamp(), "version": __version__, "repos": rows}, indent=1,
                                                 ensure_ascii=False) + "\n")
            print(f"wrote {args.out}: {len(rows)} repositories")
        for r in rows:
            s = r.get("surfaces") or {}
            present = [k for k, v in s.items() if v]
            print(f"{r['name']:<24} {r.get('files', '-'):>5} files  {len(present)}/{len(s) or '-'} surfaces"
                  + (f"  ({r['error']})" if "error" in r else ""))
        return 0, {"repos": len(rows)}
    if args.cmd == "check":
        scan = scan_clone(args.path, args.head, args.offline)
        if "error" in scan:
            raise ValueError(f"{args.path}: {scan['error']}")
        facts = load_facts(args.facts)
        scrubbed = scrub(args.path, args.patterns, head=args.head, tree_only=True) if args.patterns else None
        results = checks(scan, facts, scrubbed, args.kind)
        t = tally(results)
        if args.json:
            print(json.dumps({"name": scan["name"], "tally": t, "checks": [c.as_dict() for c in results]}, indent=2))
        else:
            for c in results:
                mark = {"pass": "pass   ", "fail": "MISSING", "unknown": "unknown"}[c.status]
                print(f"{mark}  {c.label:<26} {'' if c.status == 'pass' else c.fix}")
            print(f"\n{scan['name']}: {t['pass']} pass, {t['fail']} missing, {t['unknown']} unknown")
        return (1 if t["fail"] else 0), {"repo": scan["name"], **t}
    if args.cmd == "report":
        rows = []
        for p in args.paths:
            scan = scan_clone(p, args.head, args.offline)
            if "error" not in scan:
                rows.append((scan, checks(scan, facts_for(scan["name"], args.facts_dir), None, args.kind)))
        text = report(rows, stamp(), __version__)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"wrote {args.out}: {len(rows)} repositories")
        else:
            print(text, end="")
        return 0, {"repos": len(rows)}
    if args.cmd == "scrub":
        results = [scrub(p, args.patterns, args.head, args.tree, args.no_leaks) for p in args.paths]
        for r in results:
            print(line(r))
        if args.out:
            Path(args.out).write_text(json.dumps({"scrubbed": stamp(), "repos": results}, indent=1) + "\n")
        dirty = sum(1 for r in results if not r.get("clean"))
        return (1 if dirty else 0), {"repos": len(results), "dirty": dirty}
    if args.cmd == "kit":
        facts = load_facts(args.facts)
        actions = kit(args.path, facts, args.owner or facts.get("owner", ""), args.author or facts.get("author", ""),
                      dry_run=args.dry_run)
        for rel, why in actions:
            print(f"  {'would write' if args.dry_run else 'wrote'} {rel} ({why})")
        print(f"{len(actions)} file(s){' (dry run: nothing written)' if args.dry_run else ''}")
        return 0, {"files": len(actions), "dry_run": args.dry_run}
    if args.cmd == "history":
        out = args.out or tempfile.mkdtemp(prefix="fleet-audit-history-")
        results = [plan(s, args.patterns, out, facts_for(Path(s.rstrip("/")).name.removesuffix(".git"), args.facts_dir))
                   for s in args.sources]
        print(json.dumps(results, indent=1))
        print(f"mirrors in {out}; nothing was pushed")
        bad = sum(1 for r in results if "error" in r or not (r.get("after") or {}).get("clean"))
        return (1 if bad else 0), {"repos": len(results), "not_clean": bad}
    if args.cmd == "route":
        r = route(" ".join(args.task))
        print(json.dumps(r, indent=2) if args.json else f"skill: {r['skill']}\ncommand: {r['command']}\nwhy: {r['why']}")
        return 0, {"route": r["route"]}
    if args.cmd == "runs":
        rows = runlog.tail(args.last)
        print("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) or f"no runs logged yet ({runlog.log_path()})")
        return 0, {}
    raise ValueError(f"unknown command {args.cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
