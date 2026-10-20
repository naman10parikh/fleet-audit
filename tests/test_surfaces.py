"""The command line, the MCP server, the hook and the router, each run as a stranger would run them."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import repos
from fleet_audit import __version__
from fleet_audit.route import route

from . import ROOT


def run(args, stdin="", cwd=None, env_extra=None):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "FLEET_AUDIT_RUNLOG": "off", **(env_extra or {})}
    return subprocess.run([sys.executable, *args], input=stdin, capture_output=True, text=True, env=env,
                          cwd=cwd or ROOT, timeout=120)


class CliTest(unittest.TestCase):
    def test_help_and_version_do_nothing_else(self):
        out = run(["-m", "fleet_audit", "--help"])
        self.assertEqual(out.returncode, 0)
        self.assertIn("usage: fleet-audit", out.stdout)
        self.assertEqual(run(["-m", "fleet_audit", "--version"]).stdout.strip(), f"fleet-audit {__version__}")
        self.assertIn("usage: fleet-audit-mcp", run(["-m", "fleet_audit.mcp_server", "--help"]).stdout)
        self.assertIn("before a `git push`", run([str(ROOT / "hooks" / "prepush_scrub_hook.py"), "--help"]).stdout)

    def test_check_exit_codes_and_the_run_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "runs.jsonl"
            bare = run(["-m", "fleet_audit", "check", str(repos.bare(Path(tmp))), "--offline"],
                       env_extra={"FLEET_AUDIT_RUNLOG": str(log)})
            self.assertEqual(bare.returncode, 1)
            self.assertIn("MISSING  AGENTS.md", bare.stdout)
            self.assertEqual(run(["-m", "fleet_audit", "check", str(repos.complete(Path(tmp))), "--offline"]).returncode, 0)
            row = json.loads(log.read_text().splitlines()[-1])
            self.assertEqual((row["cmd"], row["outcome"], row["fail"]), ("check", "fail", 22))

    def test_scrub_report_and_kit_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            leaky, pats = repos.leaky(t), repos.patterns_file(t)
            out = run(["-m", "fleet_audit", "scrub", str(leaky), "--patterns", str(pats), "--no-leaks"])
            self.assertEqual(out.returncode, 1)
            self.assertNotIn("jane", out.stdout)
            report = t / "readiness.md"
            run(["-m", "fleet_audit", "report", str(repos.bare(t)), "--offline", "--out", str(report)])
            self.assertTrue(report.read_text().startswith("# Agent-native readiness"))
            dry = run(["-m", "fleet_audit", "kit", str(t / "bare"), "--owner", "someone", "--author", "Some One",
                       "--dry-run"])
            self.assertIn("would write LICENSE", dry.stdout)
            self.assertFalse((t / "bare" / "LICENSE").exists())

    def test_errors_are_clear(self):
        out = run(["-m", "fleet_audit", "scrub", ".", "--patterns", "no/such/patterns.txt"])
        self.assertEqual(out.returncode, 2)
        self.assertIn("no patterns file", out.stderr)


class McpTest(unittest.TestCase):
    def test_handshake_and_unknown_method(self):
        msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "ping"},
                {"jsonrpc": "2.0", "id": 3, "method": "no/such"}]
        out = run(["-m", "fleet_audit.mcp_server"], stdin="\n".join(map(json.dumps, msgs)))
        r = {x["id"]: x for x in (json.loads(s) for s in out.stdout.splitlines() if s.strip())}
        self.assertEqual(r[1]["result"]["serverInfo"]["name"], "fleet-audit")
        self.assertEqual(r[1]["result"]["protocolVersion"], "2025-11-25")
        self.assertEqual(r[2]["result"], {})
        self.assertEqual(r[3]["error"]["code"], -32601)


class HookTest(unittest.TestCase):
    def fire(self, command, cwd, patterns=None):
        payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}
        env = {"FLEET_AUDIT_PATTERNS": str(patterns)} if patterns else {"FLEET_AUDIT_PATTERNS": "/nonexistent"}
        return run([str(ROOT / "hooks" / "prepush_scrub_hook.py")], stdin=json.dumps(payload), env_extra=env)

    def test_a_push_with_a_hit_is_blocked_without_the_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            leaky, pats = repos.leaky(Path(tmp)), repos.patterns_file(Path(tmp))
            out = self.fire("git push origin main", leaky, pats)
            self.assertEqual(out.returncode, 2)
            self.assertIn("p1 in notes.txt", out.stderr)
            self.assertNotIn("jane", out.stderr)

    def test_other_commands_clean_trees_and_no_patterns_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            leaky, pats = repos.leaky(Path(tmp)), repos.patterns_file(Path(tmp))
            self.assertEqual(self.fire("git status", leaky, pats).returncode, 0)
            self.assertEqual(self.fire("git push", repos.bare(Path(tmp)), pats).returncode, 0)
            self.assertEqual(self.fire("git push", leaky).returncode, 0)


class RouteTest(unittest.TestCase):
    def test_routes(self):
        self.assertEqual(route("scrub this repo before we make it public")["route"], "scrub")
        self.assertEqual(route("rewrite the history to drop internal notes")["route"], "history")
        self.assertEqual(route("fix the missing plugin and license files")["route"], "fix")
        self.assertEqual(route("a markdown report over all my repos")["route"], "report")
        self.assertEqual(route("what is missing for agents here")["route"], "audit")
        self.assertEqual(route("hello")["route"], "audit")


if __name__ == "__main__":
    unittest.main()
