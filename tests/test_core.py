import json
import sys
import tempfile
import unittest
from pathlib import Path

import repos
from fleet_audit.checks import checks, tally
from fleet_audit.kit import kit, place
from fleet_audit.scan import scan_clone
from fleet_audit.scrub import ere, line, patterns, python_regex, scrub


class ScrubTest(unittest.TestCase):
    def test_patterns_file_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "p.txt"
            f.write_text("# a comment\n\nfoo\nCS Bar==>baz\n")
            got = patterns(f)
            self.assertEqual([(p.regex, p.case_sensitive, p.replacement) for p in got],
                             [("foo", False, "[removed]"), ("Bar", True, "baz")])
        with self.assertRaises(FileNotFoundError):
            patterns("no/such/file.txt")

    def test_regex_translations(self):
        self.assertEqual(python_regex("a[[:space:]]b", False), r"(?i)a[\s]b")
        self.assertEqual(python_regex("Exact", True), "Exact")
        if sys.platform == "darwin":
            self.assertEqual(ere(r"\bword\b"), "[[:<:]]word[[:>:]]")
            self.assertEqual(ere(r"\d+"), "[0-9]+")
        else:
            self.assertEqual(ere(r"\bword\b"), r"\bword\b")

    def test_scrub_counts_by_number_and_never_prints_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, pats = repos.leaky(Path(tmp)), repos.patterns_file(Path(tmp))
            r = scrub(repo, pats, skip_leaks=True)
            self.assertEqual(r["tree"], {"p1": {"notes.txt": 1}})
            self.assertEqual(r["message_commits"], {"p1": 1})
            self.assertFalse(r["clean"])
            shown = line(r) + json.dumps(r)
            self.assertNotIn("jane", shown)
            self.assertIn("DIRTY", line(r))


class ScanAndChecksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.bare = scan_clone(repos.bare(root), offline=True)
        cls.complete = scan_clone(repos.complete(root), offline=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_scan_reads_the_surfaces(self):
        s = self.complete["surfaces"]
        self.assertEqual((s["skills"], s["subagents"], s["hooks"], s["cli"]), (3, 2, 1, "scripts"))
        self.assertEqual(self.complete["license"], "MIT")
        self.assertTrue(self.complete["hygiene"]["scheduled"])
        self.assertFalse(any(v for k, v in self.bare["surfaces"].items()))

    def test_unknown_until_facts_decide(self):
        results = {c.label: c.status for c in checks(self.complete)}
        self.assertEqual(results["runs from GitHub"], "unknown")
        facts = {"one_step": {"npx_help": "pass (uvx)"}, "components": {"Identity": {"grade": "✅"}}}
        results = {c.label: c.status for c in checks(self.complete, facts)}
        self.assertEqual((results["runs from GitHub"], results["no absent component"]), ("pass", "pass"))
        absent = {"components": {"Memory": {"grade": "❌"}}}
        self.assertEqual({c.label: c.status for c in checks(self.complete, absent)}["no absent component"], "fail")

    def test_list_kind_needs_only_its_checks(self):
        self.assertEqual(len(checks(self.bare, kind="list")), 8)
        self.assertEqual(tally(checks(self.complete))["fail"], 0)
        with self.assertRaises(ValueError):
            checks(self.bare, kind="spaceship")

    def test_a_scrub_result_decides_the_scrub_check(self):
        dirty = {c.label: c.status for c in checks(self.complete, scrub={"tree": {"p1": {"a": 1}}, "secrets": 0})}
        clean = {c.label: c.status for c in checks(self.complete, scrub={"tree": {}, "secrets": 0})}
        self.assertEqual((dirty["scrub clean"], clean["scrub clean"]), ("fail", "pass"))


class KitTest(unittest.TestCase):
    def test_kit_writes_what_is_missing_with_owner_and_author(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = repos.bare(Path(tmp))
            facts = {"kind": "tool", "one_liner": "A small tool.", "runtime": "python", "mcp_bin": "bare-mcp",
                     "year": 2030, "brand_line": "a family of small tools"}
            wrote = dict(kit(repo, facts, "someone", "Some One"))
            self.assertIn("NOTICE", wrote)
            self.assertIn("Copyright (c) 2030 Some One", (repo / "LICENSE").read_text())
            notice = (repo / "NOTICE").read_text()
            self.assertIn("bare is part of a family of small tools.", notice)
            ext = json.loads((repo / "gemini-extension.json").read_text())
            self.assertEqual(ext["mcpServers"]["bare"]["command"], "uvx")
            self.assertNotIn("GEMINI.md", wrote)  # only when AGENTS.md exists

    def test_an_existing_apache_licence_is_named_as_such(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = repos.bare(Path(tmp))
            (repo / "LICENSE").write_text("Apache License\nVersion 2.0, January 2004\n")
            kit(repo, {"kind": "list"}, "someone", "Some One")
            self.assertIn("Apache-2.0 License", (repo / "NOTICE").read_text())
            self.assertFalse((repo / ".claude-plugin").exists())  # a list ships no plugin

    def test_the_kit_needs_an_owner_and_an_author(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                kit(repos.bare(Path(tmp)), {}, "", "Some One")

    def test_place_replaces_a_block_in_place(self):
        readme = "# t\n\nintro\n\n## Usage\n\nrun it\n"
        once = place(readme, "use", "BLOCK ONE", "before-first-section")
        twice = place(once, "use", "BLOCK TWO", "before-first-section")
        self.assertEqual(twice.count("<!-- fleet:use:start -->"), 1)
        self.assertIn("BLOCK TWO", twice)
        self.assertLess(twice.index("BLOCK TWO"), twice.index("## Usage"))


if __name__ == "__main__":
    unittest.main()
