# AGENTS.md: how to use fleet-audit

fleet-audit scans repositories for every surface coding agents need, checks them against one standard, scrubs them
before they go public, and writes what is missing. Its persona is Muster. This file is the one set of instructions
for every coding agent; Claude Code and Gemini CLI read it through `CLAUDE.md` and `GEMINI.md`.

## What it does

- **Scan** a repository from a committed ref: AGENTS.md, CLAUDE.md, GEMINI.md, llms.txt, skills, sub-agents, hooks,
  an MCP server, a CLI, a Claude Code plugin and marketplace, a Gemini CLI extension, an A2A agent card, a
  self-improvement contract (dsip.json), identity and memory files, CI, a scheduled loop, the README's shape, and
  GitHub's description and topics (with gh).
- **Check** it: 26 checks for a tool, component, employee or product, 8 for a list. Each passes, is missing (with
  the fix), or is unknown (it needs a facts file, gh, or a scrub to decide).
- **Scrub** it before it goes public: your patterns over the tree, the history and every commit message, and
  gitleaks over the history. Results name patterns by number and never print the matched text.
- **Fix** it: write the missing standard files and README blocks from a facts file.
- **Plan the history:** rewrite a scratch mirror to drop internal notes and scrub hits, and prove it clean.
- **Report** on many repositories in one Markdown page.

It calls no model and needs no key. It is standard-library Python 3.10 or newer; it needs git, and uses gh,
gitleaks and git-filter-repo when they are installed.

## The command line (`fleet-audit`)

Without a clone: `uvx --from git+https://github.com/naman10parikh/fleet-audit fleet-audit <command>`. In a clone:
`pip install -e .`, or `PYTHONPATH=src python3 -m fleet_audit <command>`.

| Command | What it does |
| --- | --- |
| `fleet-audit check [path] [--facts FILE] [--kind KIND] [--patterns FILE] [--head] [--offline] [--json]` | The checks for one repository. Exit 1 when one is missing. |
| `fleet-audit scan [path ...] [--owner OWNER] [--clones DIR] [--out FILE] [--head] [--offline]` | Measure local clones, or every repository of a GitHub owner. |
| `fleet-audit report path ... [--facts-dir DIR] [--kind KIND] [--out FILE]` | One Markdown page over many repositories. |
| `fleet-audit scrub path ... --patterns FILE [--head] [--tree] [--no-leaks] [--out FILE]` | Patterns, history, messages and secrets. Exit 1 when any is dirty. |
| `fleet-audit kit [path] --facts FILE --owner OWNER --author NAME [--dry-run]` | Write what is missing. It never deletes and never commits. |
| `fleet-audit history source ... --patterns FILE [--facts-dir DIR] [--out DIR]` | Rewrite a scratch mirror and scrub it. It pushes nothing. |
| `fleet-audit route "TASK" [--json]` | The skill and the command for a task in plain words. |
| `fleet-audit runs [--last N]` | The run log. |
| `fleet-audit --help`, `fleet-audit --version` | Print help or the version, and nothing else. |

Exit codes: 0 success; 1 a missing check, a dirty scrub or a history plan that is not clean; 2 a usage error (a
missing patterns file, facts file or repository).

## The MCP server (`fleet-audit-mcp`, stdio)

Start it with `uvx --from git+https://github.com/naman10parikh/fleet-audit fleet-audit-mcp`; the root `.mcp.json`
does exactly that. Tools:

- `fleet_scan({path, head?, offline?})`: the scan of one repository, as JSON. Reads only.
- `fleet_check({path, facts?, kind?, patterns?, head?, offline?})`: the checks with their tally. Reads only.
- `fleet_report({paths, facts_dir?, kind?, head?, offline?})`: the Markdown report. Reads only.
- `fleet_scrub({path, patterns, head?, tree_only?, skip_leaks?})`: counts by pattern number. Reads only.
- `fleet_kit({path, facts?, owner?, author?, write?})`: what the kit would write; it writes only with `write: true`.

## Skills (`skills/`)

- `audit-a-repo`: check a repository or an owner's repositories, and plan the fixes.
- `scrub-before-public`: scrub, triage by pattern number, and plan a history rewrite in a scratch mirror.
- `fix-with-the-kit`: write the facts file, dry-run the kit, write, and write the README body around the blocks.

## Sub-agents (`.claude/agents/`)

- `readiness-auditor`: audits and reports; changes nothing.
- `surface-fixer`: closes the agreed gaps in one repository, with the kit and by hand; never pushes.

## Files you give it

- **A patterns file** for the scrub, kept outside every repository. `scrub-patterns.example.txt` shows the format.
- **A facts file** per repository for the kit and the facts-based checks. `facts.example.json` shows the keys.

## What not to do

- Do not put a real patterns file in any repository, and never paste a scrub's matched text anywhere.
- Do not run the kit without `--dry-run` in a repository you do not know.
- Do not push a rewritten history, force-push, or change a repository's visibility on your own; those wait for the
  owner's explicit yes.
- Do not count "unknown" as a pass.
- Do not add a model call or a key. fleet-audit is deterministic.

## Verify a change

```bash
python3 -m unittest && python3 evals/run.py
```

Memory: `memory/MEMORY.md` (start here) and `memory/LEARNINGS.md` (rules from past mistakes); search them with
`python3 scripts/memory_search.py "<query>"`.
