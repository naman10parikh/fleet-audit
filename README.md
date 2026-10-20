# fleet-audit

<!-- fleet:header:start -->
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE) [![Agent-native](https://img.shields.io/badge/agent--native-yes-2f5d8a?style=flat-square)](AGENTS.md) [![MCP server](https://img.shields.io/badge/MCP-server-1e3f60?style=flat-square)](#use-it-from-any-coding-agent) [![Skills](https://img.shields.io/badge/skills-3-2f6b4f?style=flat-square)](skills/)

**Scan your repositories for every surface coding agents need, and fix them.**

Fleet Audit is an agent-native tool: other agents call it through its skills, its MCP server or its command line. Its persona is Muster. A scheduled job runs its evals and proposes fixes. A person makes every change.

_Fleet Audit is part of an agent-native play for agent-native systems that can eventually be recursively self-improving and evolving, operated by agent employees._

[AGENTS.md](AGENTS.md) · [llms.txt](llms.txt) · [Skills](skills/) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [All projects](https://github.com/naman10parikh)
<!-- fleet:header:end -->


Find out what a coding agent will find in your repository, and what it will miss. fleet-audit checks a repository
against one standard for agent-native projects, scrubs it before it goes public, and writes the standard files it
is missing. It is for anyone who publishes repositories that agents are meant to install, read and extend.

<!-- fleet:use:start -->
## Use it from any coding agent

**Claude Code**: the plugin brings the skills, sub-agents, hooks and MCP server.

```
/plugin marketplace add naman10parikh/fleet-audit
/plugin install fleet-audit@fleet-audit
```

<details><summary>Its MCP server, Codex, Cursor, Gemini CLI, one skill and the command line</summary>

**Its MCP server**, in any MCP client:

```bash
claude mcp add --transport stdio fleet-audit -- uvx --from git+https://github.com/naman10parikh/fleet-audit fleet-audit-mcp
codex mcp add fleet-audit -- uvx --from git+https://github.com/naman10parikh/fleet-audit fleet-audit-mcp
```

Cursor (`.cursor/mcp.json`), Gemini CLI (`.gemini/settings.json`) and most other clients take the same command as JSON:

```json
{
  "mcpServers": {
    "fleet-audit": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/naman10parikh/fleet-audit",
        "fleet-audit-mcp"
      ]
    }
  }
}
```

**Gemini CLI**: the extension brings the context and the MCP server.

```bash
gemini extensions install https://github.com/naman10parikh/fleet-audit
```

**One skill** (3 in all, in [skills/](skills/)), in any agent that reads Agent Skills:

```bash
gemini skills install https://github.com/naman10parikh/fleet-audit --path skills/audit-a-repo
git clone --depth 1 https://github.com/naman10parikh/fleet-audit /tmp/fleet-audit && cp -r /tmp/fleet-audit/skills/audit-a-repo ~/.claude/skills/
```

**The command line:**

```bash
uvx --from git+https://github.com/naman10parikh/fleet-audit fleet-audit --help
```

</details>

Codex, Cursor, OpenCode, GitHub Copilot and other agents read [AGENTS.md](AGENTS.md); Claude Code reads [CLAUDE.md](CLAUDE.md) and Gemini CLI reads [GEMINI.md](GEMINI.md), which import it. [llms.txt](llms.txt) maps every surface for agents that read first.
<!-- fleet:use:end -->

## Quick start

No clone needed: uv builds fleet-audit from GitHub on first use. Run this inside any git repository:

```bash
uvx --from git+https://github.com/naman10parikh/fleet-audit fleet-audit check . --offline
```

It prints one line per check (pass; MISSING, with the fix; or unknown) and ends with a tally. Run on its own
repository it ends with `fleet-audit: 22 pass, 0 missing, 4 unknown`: offline, the description check needs gh, the
scrub check needs a patterns file, and two checks need a facts file.

Before a repository goes public, scrub it with your own patterns, kept outside every repository
(`scrub-patterns.example.txt` shows the format):

```bash
fleet-audit scrub . --patterns ~/scrub-patterns.txt
```

Write what is missing from a facts file (`facts.example.json` shows the keys), with a dry run first:

```bash
fleet-audit kit . --facts facts.json --owner <github-owner> --author "<your name>" --dry-run
```

In a clone, the tests and the evals need only Python and git:

```bash
python3 -m unittest && python3 evals/run.py
```

The evals end with `18 passed, 0 failed`.

## What it checks

| Group | Checks |
| --- | --- |
| Context for every agent | AGENTS.md · llms.txt · CLAUDE.md · GEMINI.md · a README with a quick start |
| One-step surfaces | 3 or more skills · 2 or more sub-agents · a hook · an MCP server · a CLI · plugin.json · a marketplace · a Gemini CLI extension · an A2A agent card · it runs from GitHub |
| It improves itself | dsip.json · CI · a scheduled loop · memory (MEMORY.md and LEARNINGS.md) · no absent component |
| A mature project | a licence · SECURITY.md · CONTRIBUTING.md · a description and topics · a clean scrub |

A tool, a component, an employee or a product gets all 26 checks. A list gets the 8 that fit it (the context files,
the README, the hygiene files, the description and the scrub).

## How it works

**Committed state, not memory.** The scan reads a git ref: the remote's default branch, or the local HEAD with
`--head`. Uncommitted files do not count, because a stranger will never see them.

**Pass, missing or unknown.** A check that needs something fleet-audit does not have (a facts file, gh, a scrub)
says unknown. It is never quietly counted as a pass, and never as a failure.

**A scrub that keeps its findings to itself.** Your patterns run over the tree with `git grep -P`, over the whole
history with `git log -G` (translated for the BSD regex library on macOS) and over every commit message; gitleaks
covers secrets. Every result names a pattern by its number and never repeats the matched text.

**Additive fixes.** The kit creates only missing files and replaces only its own marked README blocks. It never
deletes a file and never commits. In the MCP server, the kit is a dry run until it is called with `write: true`.

**History in a scratch mirror.** `fleet-audit history` clones a bare mirror, drops the internal notes your facts
file names, replaces every pattern, and scrubs the result. Pushing that history is left to a person.

**The hook.** In Claude Code, a pre-push hook scrubs the committed tree with your patterns and blocks the push on
a match.

**The loop.** Every night a scheduled job runs the evals, audits and scrubs this repository, and writes proposals
to one issue. It never commits; a person makes every change.

**The commands** (each answers `--help`):

```text
fleet-audit check [path] [--facts FILE] [--kind KIND] [--patterns FILE] [--head] [--offline] [--json]
fleet-audit scan [path ...] [--owner OWNER] [--clones DIR] [--out FILE] [--head] [--offline]
fleet-audit report path ... [--facts-dir DIR] [--kind KIND] [--out FILE]
fleet-audit scrub path ... --patterns FILE [--head] [--tree] [--no-leaks] [--out FILE]
fleet-audit kit [path] --facts FILE --owner OWNER --author NAME [--dry-run]
fleet-audit history source ... --patterns FILE [--facts-dir DIR] [--out DIR]
fleet-audit route "TASK"
fleet-audit runs [--last N]
```

## Limits

- The checks find files and read their shape. They cannot tell a thoughtful AGENTS.md from a thin one; the
  `readiness-auditor` sub-agent opens the files to judge that.
- GitHub's description and topics need gh signed in. Without it, that check is unknown.
- A scrub is only as good as its patterns. Test each new pattern on a known hit. gitleaks and git-filter-repo are
  optional, and fleet-audit says when one is missing.
- The kit writes an MIT licence when a repository has none. Add your own first if you want another.

<!-- fleet:anatomy:start -->
## What it is made of

Every project in this fleet is graded on the same 11 harness components and on self-improvement. Each mark is backed by a file you can open.

| Component | Grade | Where |
| --- | --- | --- |
| Identity | ✅ | identity/SOUL.md:7 + identity/BRAND.md:5 |
| Memory | ✅ | memory/MEMORY.md:1 + scripts/memory_search.py:49 |
| Skills | ✅ | skills/audit-a-repo/SKILL.md:1 |
| Tools/CLIs | ✅ | pyproject.toml:25 + src/fleet_audit/cli.py:34 |
| Hooks | ✅ | .claude/settings.json:4 + hooks/hooks.json:4 |
| Sub-agents | ✅ | .claude/agents/readiness-auditor.md:1 |
| MCPs | ✅ | src/fleet_audit/mcp_server.py:35 + pyproject.toml:25 |
| Dispatch | ✅ | src/fleet_audit/route.py:37 + .github/workflows/loop.yml:5 |
| Evals | ✅ | evals/run.py:1 + .github/workflows/ci.yml:24 |
| Observability | ✅ | src/fleet_audit/runlog.py:27 |
| Sandbox/Infra | ✅ | sandbox/run_in_sandbox.py:44 |
| Self-improvement | ✅ | dsip.json:1 + .github/workflows/loop.yml:41 |

✅ real and tested · 🟡 partial, with the reason in the row · ❌ absent
<!-- fleet:anatomy:end -->

<!-- fleet:footer:start -->
## How it improves itself

It carries its own evals and a self-improvement contract, [`dsip.json`](dsip.json), which says what it may change and how a change is judged. A scheduled job runs its evals and proposes fixes. A person makes every change. Lessons it learns are kept as rules in its memory files.

## Part of a fleet

One of the projects by [Naman Parikh](https://github.com/naman10parikh). Each owns one part of an agent's harness, or of the product around an agent, and all of them follow one standard.

Siblings: [agentdial](https://github.com/naman10parikh/agentdial) (identity) · [wikimem](https://github.com/naman10parikh/wikimem) (memory) · [skillsmith](https://github.com/naman10parikh/skillsmith) (skills) · [agent-booster](https://github.com/naman10parikh/agent-booster) (tools / CLIs) · [armory](https://github.com/naman10parikh/armory) (MCPs and the component registry) · [agentgrid](https://github.com/naman10parikh/agentgrid) (dispatch) · [agentswarm](https://github.com/naman10parikh/agentswarm) (dispatch) · [agentbench](https://github.com/naman10parikh/agentbench) (evals) · [agentmoney](https://github.com/naman10parikh/agentmoney) (observability) · [claude-harness](https://github.com/naman10parikh/claude-harness) (the whole harness, as a template).

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md). AI-assisted pull requests are welcome. Report a vulnerability privately, as [SECURITY.md](SECURITY.md) explains.

## License

MIT, © 2026 Naman Parikh. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
<!-- fleet:footer:end -->
