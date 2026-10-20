# Muster (fleet-audit): memory

The short bootstrap an agent reads first. Search everything else with
`python3 scripts/memory_search.py "<query>"` (BM25 over memory/, identity/, the skills, AGENTS.md and docs/).

## What it is

A command line (`fleet-audit`) and an MCP server (`fleet-audit-mcp`, 5 tools) that scan repositories for the surfaces
coding agents need, check them against one standard, scrub them before they go public, write what is missing from a
facts file, plan history rewrites in a scratch mirror, and report in Markdown. 3 skills, 2 sub-agents, 1 hook.

## Invariants (never break them)

- **Reads committed state** (a ref), never the working tree; only the kit writes, and only the working tree.
- **Never writes to a repository unless the kit is asked;** never commits, never pushes, never changes visibility.
- **A scrub prints pattern numbers and counts, never matched text.** The patterns file lives outside every repository.
- **Unknown is neither a pass nor a failure.**
- **Standard library only** in `src/`. git is required; gh, gitleaks and git-filter-repo are optional and named when
  missing. The `e2b` package is optional and used only by `sandbox/`.
- **No model calls and no keys.**

## Where things are

- Scan: `src/fleet_audit/scan.py`; git and gh helpers: `gitutil.py`.
- Checks: `checks.py` (26 for a tool, 8 for a list). Report: `report.py`.
- Scrub: `scrub.py`. History plan: `history.py`. Kit: `kit.py` (files) and `blocks.py` (README blocks).
- Surfaces: `cli.py`, `mcp_server.py`, `route.py`, `runlog.py` (default `~/.local/state/fleet-audit/runs.jsonl`;
  `FLEET_AUDIT_RUNLOG=off` stops it). Hook: `hooks/prepush_scrub_hook.py`.
- Evals: `evals/run.py` on fixture repositories from `evals/repos.py`. The loop: `evals/loop.py`, `.github/workflows/loop.yml`.

## Decisions

- Trees are scanned with `git grep -P` (Perl regexes: `\b` and `\d` work everywhere); `git log -G` takes ERE,
  translated on macOS (`scrub.ere`); commit messages and filter-repo use Python regexes (`scrub.python_regex`).
- Patterns: a `CS ` prefix makes one case-sensitive; a `==>text` suffix is its history replacement.
- The kit's brand line and sibling list are opt-in facts, so nothing names an owner the user did not give.
- A repository of kind "list" needs only the context and hygiene checks.

## Lessons

`memory/LEARNINGS.md` holds every correction as a rule. Read it before changing the scrub or the checks.
