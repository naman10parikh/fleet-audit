@AGENTS.md

# fleet-audit: notes for Claude Code

- **The hook.** `.claude/settings.json` runs `hooks/prepush_scrub_hook.py` before every Bash command. On a
  `git push` it scrubs the committed tree with the patterns file in `$FLEET_AUDIT_PATTERNS` (or
  `.fleet-audit/scrub-patterns.txt`, which git ignores) and blocks the push on a match, naming the pattern number and
  the file. With no patterns file it lets the push through. The plugin ships the same hook in `hooks/hooks.json`.
- **The MCP server.** `.mcp.json` runs the server from GitHub through `uvx`. To try your local changes, start Claude
  Code with `claude --mcp-config .mcp.dev.json`, which runs it from `src/`.
- **Sub-agents.** Hand an audit to `readiness-auditor` (it changes nothing) and agreed fixes to `surface-fixer`.
- **Before you finish:** `python3 -m unittest && python3 evals/run.py`, then `PYTHONPATH=src python3 -m fleet_audit
  check . --offline --head`, which must show nothing missing.
- **Code style.** Standard library only in `src/` (the `e2b` package is optional and used only by `sandbox/`), files
  under 400 lines, and planted test strings assembled at run time (see `evals/repos.py`).
- **No model ID anywhere.** fleet-audit calls no model.
