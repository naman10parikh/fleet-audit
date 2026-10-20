"""A standalone Markdown report over one or more scanned repositories: a summary table, then each repository's
checks with the fix for every one that fails."""

from __future__ import annotations

from .checks import Check, tally

MARK = {"pass": "pass", "fail": "**missing**", "unknown": "unknown"}


def report(rows: list[tuple[dict, list[Check]]], stamp: str, version: str) -> str:
    """`rows` pairs each scan with its checks."""
    lines = ["# Agent-native readiness", "",
             f"Measured {stamp} by fleet-audit {version}: {len(rows)} repositor{'y' if len(rows) == 1 else 'ies'}. "
             "A check passes, is missing, or is unknown (it needs a facts file, gh or a scrub to decide).", "",
             "| Repository | Visibility | Passed | Missing | Unknown |", "| --- | --- | --- | --- | --- |"]
    for scan, results in rows:
        t = tally(results)
        missing = ", ".join(c.label for c in results if c.status == "fail") or "none"
        visibility = (scan.get("github") or {}).get("visibility") or "local"
        lines.append(f"| {scan['name']} | {visibility} | {t['pass']}/{len(results)} | {missing} | {t['unknown']} |")
    for scan, results in rows:
        lines += ["", f"## {scan['name']}", "", f"Read from `{scan.get('ref', '')}`, {scan.get('files', 0)} files.", "",
                  "| Check | Result | To fix |", "| --- | --- | --- |"]
        for c in results:
            fix = "" if c.status == "pass" else c.fix + (" (the kit writes it)" if c.kit else "")
            lines.append(f"| {c.label} | {MARK[c.status]} | {fix} |")
    return "\n".join(lines) + "\n"
