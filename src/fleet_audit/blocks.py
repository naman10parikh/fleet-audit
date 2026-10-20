"""The README blocks the kit writes (header, use, anatomy, footer) and how it places them. Each block sits between
<!-- fleet:<block>:start --> and <!-- fleet:<block>:end -->, so the next run replaces it in place."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from .scan import licence_kind

COMPONENTS = ["Identity", "Memory", "Skills", "Tools/CLIs", "Hooks", "Sub-agents", "MCPs", "Dispatch", "Evals",
              "Observability", "Sandbox/Infra", "RSI / open-endedness"]
LABEL = {"RSI / open-endedness": "Self-improvement"}
HYGIENE = {"LICENSE": ["LICENSE", "LICENSE.md", "LICENSE.txt"], "SECURITY.md": ["SECURITY.md", ".github/SECURITY.md"],
           "CONTRIBUTING.md": ["CONTRIBUTING.md", ".github/CONTRIBUTING.md"],
           "CODE_OF_CONDUCT.md": ["CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md"]}
AGENT_KINDS = ("component", "employee", "product", "tool")  # kinds that ship a plugin, an extension and a card
EMPLOYEE = "a packaged specialist agent with its own skills, memory and tests"
LOOP = {"L0": "It carries its own evals. A person makes every change.",
        "L1": "Its evals gate every merge in CI. A person makes every change.",
        "L2": "A scheduled job runs its evals and proposes fixes. A person makes every change."}


def loop_line(facts: dict) -> str:
    return facts.get("loop_line") or LOOP.get(facts.get("dsip_level") or "", LOOP["L0"])


def job(owns: str) -> str:
    return owns[0].lower() + owns[1:] if owns[1:2].islower() else owns


def runner(owner: str, name: str, facts: dict) -> list[str]:
    """The prefix that runs a bin straight from GitHub: uvx for a Python package, npx for a Node one."""
    if facts.get("runtime") == "python":
        return ["uvx", "--from", f"git+https://github.com/{owner}/{name}"]
    return ["npx", "-y", "-p", f"github:{owner}/{name}"]


def version_of(path: Path) -> str:
    pkg = path / "package.json"
    if pkg.exists():
        try:
            return json.loads(pkg.read_text()).get("version") or "0.1.0"
        except ValueError:
            pass
    py = path / "pyproject.toml"
    m = re.search(r'^version\s*=\s*"([^"]+)"', py.read_text(), re.M) if py.exists() else None
    return m.group(1) if m else "0.1.0"


def badges(owner: str, name: str, facts: dict, path: Path) -> str:
    public = facts.get("visibility") == "public"
    flows = sorted(p.name for p in (path / ".github/workflows").glob("*.y*ml"))
    ci = next((w for w in flows if re.match(r"(ci|test|tests|build)\.ya?ml$", w)), flows[0] if flows else "")
    b = []
    if public and ci:
        b.append(f"[![CI](https://img.shields.io/github/actions/workflow/status/{owner}/{name}/{ci}?style=flat-square"
                 f"&label=ci)](https://github.com/{owner}/{name}/actions)")
    b.append("[![License](https://img.shields.io/badge/license-" + (licence_kind(_licence_text(path)) or "MIT")
             .replace("-", "--") + "-green?style=flat-square)](LICENSE)")
    b.append("[![Agent-native](https://img.shields.io/badge/agent--native-yes-2f5d8a?style=flat-square)](AGENTS.md)")
    if facts.get("mcp_bin"):
        b.append("[![MCP server](https://img.shields.io/badge/MCP-server-1e3f60?style=flat-square)](#use-it-from-any-coding-agent)")
    if facts.get("skills"):
        b.append(f"[![Skills](https://img.shields.io/badge/skills-{len(facts['skills'])}-2f6b4f?style=flat-square)](skills/)")
    if public:
        b.append(f"[![Stars](https://img.shields.io/github/stars/{owner}/{name}?style=flat-square)]"
                 f"(https://github.com/{owner}/{name}/stargazers)")
    return " ".join(b)


def _licence_text(path: Path) -> str:
    lic = next((path / f for f in HYGIENE["LICENSE"] if (path / f).exists()), None)
    return lic.read_text()[:600] if lic else ""


def header_block(owner: str, name: str, facts: dict, path: Path) -> str:
    display, soul, kind = facts.get("display") or name, facts.get("soul") or "", facts.get("kind") or "tool"
    persona = f" Its persona is {soul}." if soul and soul.lower() != display.lower() else ""
    loop = f" {loop_line(facts)}" if (path / "dsip.json").exists() else ""
    if kind in ("component", "employee"):
        owns = f" It owns one job: {job(facts['owns'])}." if facts.get("owns") else ""
        what = (f"{display} is an agent employee, {EMPLOYEE}.{owns}{persona} Coding agents use it through its skills, "
                f"its MCP server and its command line.{loop}")
    elif kind == "list":
        what = ("An agent-native list: written for people and kept machine-readable for agents, with "
                "[AGENTS.md](AGENTS.md) and [llms.txt](llms.txt) telling an agent how to read and extend it.")
    else:
        what = (f"{display} is an agent-native {'tool' if kind == 'tool' else 'product'}: other agents call it through "
                f"its skills, its MCP server or its command line.{persona}{loop}")
    if facts.get("brand_line"):
        what += f"\n\n_{display} is part of {facts['brand_line']}._"
    links = [f"[{x}]({x})" for x in ("AGENTS.md", "llms.txt") if (path / x).exists()]
    links += (["[Skills](skills/)"] if facts.get("skills") else []) + ["[Security](SECURITY.md)",
                                                                      "[Contributing](CONTRIBUTING.md)"]
    line = facts.get("one_liner", "")
    return "\n".join([badges(owner, name, facts, path), "", f"**{line}**" if line else "", "", what, "",
                      " · ".join(links)])


def use_block(owner: str, name: str, facts: dict, path: Path) -> str:
    kind = facts.get("kind") or "tool"
    out = ["## Use it from any coding agent", ""]
    if kind in AGENT_KINDS:
        out += ["**Claude Code**: the plugin brings the skills, sub-agents, hooks and MCP server.", "", "```",
                f"/plugin marketplace add {owner}/{name}", f"/plugin install {facts.get('plugin_name', name)}@{name}",
                "```", ""]
    visible = len(out)
    cmd = runner(owner, name, facts) + [facts["mcp_bin"]] if facts.get("mcp_bin") else None
    if cmd:
        out += ["**Its MCP server**, in any MCP client:", "", "```bash",
                f"claude mcp add --transport stdio {name} -- {' '.join(cmd)}", f"codex mcp add {name} -- {' '.join(cmd)}",
                "```", "", "Cursor (`.cursor/mcp.json`), Gemini CLI (`.gemini/settings.json`) and most other clients "
                "take the same command as JSON:", "", "```json",
                json.dumps({"mcpServers": {name: {"command": cmd[0], "args": cmd[1:]}}}, indent=2), "```", ""]
    if kind in AGENT_KINDS:
        out += ["**Gemini CLI**: the extension brings the context and the MCP server.", "", "```bash",
                f"gemini extensions install https://github.com/{owner}/{name}", "```", ""]
    skills = facts.get("skills") or []
    if skills:
        first = skills[0]["path"].rsplit("/SKILL.md", 1)[0]
        out += [f"**One skill** ({len(skills)} in all, in [skills/](skills/)), in any agent that reads Agent Skills:", "",
                "```bash", f"gemini skills install https://github.com/{owner}/{name} --path {first}",
                f"git clone --depth 1 https://github.com/{owner}/{name} /tmp/{name} && cp -r /tmp/{name}/{first} "
                "~/.claude/skills/", "```", ""]
    if facts.get("cli_bin"):
        out += ["**The command line:**", "", "```bash", " ".join(runner(owner, name, facts) + [facts["cli_bin"], "--help"]),
                "```", ""]
    if len(out) > visible:  # one install shows; every other route is one click away
        out[visible:] = (["<details><summary>Its MCP server, Codex, Cursor, Gemini CLI, one skill and the command line"
                          "</summary>", ""] + out[visible:] + ["</details>", ""])
    readers = "Codex, Cursor, OpenCode, GitHub Copilot and other agents read [AGENTS.md](AGENTS.md)"
    if (path / "CLAUDE.md").exists():
        readers += "; Claude Code reads [CLAUDE.md](CLAUDE.md) and Gemini CLI reads [GEMINI.md](GEMINI.md), which import it"
    tail = " [llms.txt](llms.txt) maps every surface for agents that read first." if (path / "llms.txt").exists() else ""
    return "\n".join(out + [readers + "." + tail])


def anatomy_block(facts: dict) -> str:
    grades = facts.get("components") or {}
    out = ["## What it is made of", "", "Graded on the 11 harness components and on self-improvement. Each mark is "
           "backed by a file you can open.", "", "| Component | Grade | Where |", "| --- | --- | --- |"]
    out += [f"| {LABEL.get(c, c)} | {grades.get(c, {}).get('grade', '·')} | {grades.get(c, {}).get('where', '')} |"
            for c in COMPONENTS]
    return "\n".join(out + ["", "✅ real and tested · 🟡 partial, with the reason in the row · ❌ absent"])


def footer_block(owner: str, name: str, facts: dict, path: Path, author: str, has_license: bool) -> str:
    out = []
    if (path / "dsip.json").exists():
        out += ["## How it improves itself", "", "It carries its own evals and a self-improvement contract, "
                f"[`dsip.json`](dsip.json), which says what it may change and how a change is judged. {loop_line(facts)} "
                "Lessons it learns are kept as rules in its memory files.", ""]
    sibs = facts.get("siblings") or []
    if sibs:
        out += ["## Part of a fleet", "", f"One of the projects by [{author}](https://github.com/{owner}). Siblings: "
                + " · ".join(f"[{s['name']}](https://github.com/{owner}/{s['name']})"
                             + (f" ({job(s['owns'])})" if s.get("owns") else "") for s in sibs) + ".", ""]
    out += ["## Contributing and security", "", "Read [CONTRIBUTING.md](CONTRIBUTING.md). AI-assisted pull requests are "
            "welcome. Report a vulnerability privately, as [SECURITY.md](SECURITY.md) explains."]
    if not has_license:
        kind = licence_kind(_licence_text(path)) or "MIT"
        out += ["", "## License", "", f"{kind}, © {facts.get('year') or datetime.now().year} {author}. See [LICENSE](LICENSE)"
                + (" and [NOTICE](NOTICE)." if (path / "NOTICE").exists() else ".")]
    if facts.get("visibility") == "public":
        out += ["", "## Star history", "", f"[![Star history chart](https://api.star-history.com/svg?repos={owner}/{name}"
                f"&type=Date)](https://star-history.com/#{owner}/{name}&Date)"]
    return "\n".join(out)


def prose_lines(lines: list[str]) -> list[int]:
    """Indexes of lines outside code fences and outside the kit's own blocks: only these can be headings."""
    out, fence, block = [], False, False
    for n, line in enumerate(lines):
        if line.lstrip().startswith(("```", "~~~")):
            fence = not fence
        elif re.match(r"<!-- fleet:\w+:start -->", line):
            block = True
        elif re.match(r"<!-- fleet:\w+:end -->", line):
            block = False
        elif not fence and not block:
            out.append(n)
    return out


def place(readme: str, key: str, block: str, where: str) -> str:
    start, end = f"<!-- fleet:{key}:start -->", f"<!-- fleet:{key}:end -->"
    chunk = f"{start}\n{block}\n{end}"
    if start in readme:
        return re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: chunk, readme, flags=re.S)
    lines = readme.rstrip("\n").splitlines()
    prose = prose_lines(lines)
    if where == "after-title":
        i = next((n for n in prose if lines[n].startswith("# ")), -1)
        return "\n".join(lines[:i + 1] + ["", chunk, ""] + lines[i + 1:]) + "\n"
    if where == "before-first-section":
        i = next((n for n in prose if lines[n].startswith("## ")), len(lines))
        return "\n".join(lines[:i] + [chunk, ""] + lines[i:]) + "\n"
    footer = next((n for n, line in enumerate(lines) if line == "<!-- fleet:footer:start -->"), None)
    lic = next((n for n in prose if re.match(r"^#{1,3} .*licen[cs]e", lines[n], re.I)), len(lines))
    i = footer if footer is not None and key != "footer" else lic
    return "\n".join(lines[:i] + ["", chunk, ""] + lines[i:]).rstrip() + "\n"


def outside_blocks(readme: str) -> str:
    return re.sub(r"<!-- fleet:(\w+):start -->.*?<!-- fleet:\1:end -->", "", readme, flags=re.S)
