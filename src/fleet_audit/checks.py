"""The checks a repository passes to be usable by every coding agent, computed from a scan, and from a facts file and
a scrub result when given. Each check passes, fails, or is unknown (it needs a facts file, gh or a scrub to decide).

The standard behind them: context for every agent (AGENTS.md, CLAUDE.md, GEMINI.md, llms.txt), one-step surfaces
(skills, sub-agents, hooks, an MCP server, a CLI, a Claude Code plugin, a Gemini CLI extension, an A2A card), a loop
that improves it (a self-improvement contract, CI, a scheduled job, memory), and the hygiene of a mature project.
A repository of kind "list" needs only the first group and the hygiene.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

KINDS = ("tool", "component", "employee", "product", "list")


@dataclass
class Check:
    label: str
    status: str  # pass | fail | unknown
    fix: str
    kit: bool = False  # `fleet-audit kit` writes what is missing

    def as_dict(self) -> dict:
        return asdict(self)


def _c(label: str, ok: object, fix: str, kit: bool = False) -> Check:
    return Check(label, "pass" if ok else "fail", fix, kit)


def checks(scan: dict, facts: dict | None = None, scrub: dict | None = None, kind: str | None = None) -> list[Check]:
    facts = facts or {}
    kind = kind or facts.get("kind") or "tool"
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}; use one of {', '.join(KINDS)}")
    s, h, i, rd = scan["surfaces"], scan["hygiene"], scan["identity"], scan["readme"]
    gh = scan.get("github") or {}
    out = [
        _c("AGENTS.md", s["AGENTS.md"], "Write AGENTS.md: what it does, its tools and how to call them, what not to do."),
        _c("llms.txt", s["llms.txt"], "Write llms.txt in the llmstxt.org shape: a # title, a > summary, then links."),
        _c("licence", scan["license"], "Add a LICENSE file.", kit=True),
        _c("SECURITY.md", h["SECURITY.md"], "Say how to report a vulnerability privately.", kit=True),
        _c("CONTRIBUTING.md", h["CONTRIBUTING.md"], "Say how to contribute and what a change must pass.", kit=True),
        _c("README with a quick start", rd["quick_start"] and rd["bytes"] > 1500,
           "Give the README a Quick start section with commands that run, after two or three plain sentences."),
    ]
    if gh:
        out.append(_c("description and topics", gh.get("description") and len(gh.get("topics", [])) >= 3,
                      "gh repo edit <owner>/<name> --description \"...\" --add-topic ... (three topics or more)"))
    else:
        out.append(Check("description and topics", "unknown", "Run with gh signed in to read GitHub's facts."))
    if scrub is None:
        out.append(Check("scrub clean", "unknown", "Run fleet-audit scrub <path> --patterns <file>."))
    else:
        out.append(_c("scrub clean", not scrub.get("tree") and not scrub.get("secrets"),
                      "Remove every scrub hit from the tree; rotate a real secret before you remove it."))
    if kind == "list":
        return out
    skills = len(facts["skills"]) if facts.get("skills") else s["skills"]
    out += [
        _c("SOUL.md", i["SOUL.md"], "Write identity/SOUL.md: a persona, a one-word name, a tagline and boundaries."),
        _c("CLAUDE.md", s["CLAUDE.md"], "Write CLAUDE.md: its first line @AGENTS.md, then only Claude-specific rules."),
        _c("GEMINI.md", s["GEMINI.md"], "GEMINI.md imports AGENTS.md for Gemini CLI.", kit=True),
        _c("3+ skills", skills >= 3, "Write three skills or more in skills/<name>/SKILL.md, each with name and description."),
        _c("2+ sub-agents", s["subagents"] >= 2, "Write two personas or more in .claude/agents/<name>.md, each with a scope."),
        _c("a hook", s["hooks"] or s["plugin_hooks"], "Wire a real hook in .claude/settings.json and hooks/hooks.json."),
        _c("MCP server", s["mcp_server"] or facts.get("mcp_bin"), "Ship the repository's own MCP server as a <name>-mcp bin."),
        _c("CLI", s["cli"], "Add a CLI (package.json bin or [project.scripts]) that answers --help and --version."),
        _c("plugin.json", s["plugin_json"], "Claude Code reads .claude-plugin/plugin.json.", kit=True),
        _c("marketplace", s["marketplace"], ".claude-plugin/marketplace.json lists one plugin with source ./.", kit=True),
        _c("Gemini extension", s["gemini_ext"], "gemini-extension.json, with the MCP server.", kit=True),
        _c("agent card", s["a2a_card"], ".well-known/agent-card.json: name, description, url, capabilities, skills.", kit=True),
        _c("dsip.json", s["dsip"], "Write dsip.json, the self-improvement contract, at an honest level."),
        _c("CI", h["workflows"], "Add a CI workflow that runs the tests and the evals."),
        _c("scheduled loop", h["scheduled"], "Add a scheduled (or dispatchable) workflow that runs the evals and proposes."),
        _c("memory", i["MEMORY.md"] and i["LEARNINGS.md"], "Keep MEMORY.md (short) and LEARNINGS.md (rules from mistakes)."),
    ]
    one = str((facts.get("one_step") or {}).get("npx_help", ""))
    out.append(_c("runs from GitHub", one.startswith("pass"), "Prove the one-step install from an empty folder.")
               if one else Check("runs from GitHub", "unknown", "Record the one-step proof in the facts file."))
    grades = [v.get("grade") for v in (facts.get("components") or {}).values()]
    out.append(_c("no absent component", "❌" not in grades, "Build each absent component, or mark it 🟡 with why.")
               if grades else Check("no absent component", "unknown", "Grade the 12 components in the facts file."))
    return out


def tally(results: list[Check]) -> dict:
    return {k: sum(1 for c in results if c.status == k) for k in ("pass", "fail", "unknown")}
