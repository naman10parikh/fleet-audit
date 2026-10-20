"""Write the standard into one repository's working tree from a facts file. It only adds: a missing file is created,
and the README gains marked blocks that are replaced in place on the next run. It never deletes a file and never
commits. `dry_run` lists what it would write and writes nothing.

The facts file is JSON; every key is optional:
  name, display, kind (tool | component | employee | product | list), soul, owns, one_liner, runtime (node | python),
  cli_bin, mcp_bin, plugin_name, skills [{path, what}], components {<column>: {grade, where}}, dsip_level (L0 to L3),
  loop_line, visibility (public | private), brand_line, siblings [{name, owns}], year, owner, author
The owner (a GitHub user or organisation) and the author (the licence holder) come from flags or the facts file.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from .blocks import (AGENT_KINDS, HYGIENE, anatomy_block, footer_block, header_block, outside_blocks, place, runner,
                     use_block, version_of)
from .scan import licence_kind
from .templates import CONDUCT, CONTRIBUTING, GEMINI, MIT, SECURITY


def load_facts(file: str | Path | None) -> dict:
    if not file:
        return {}
    path = Path(file).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"no facts file at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def kit(path: str | Path, facts: dict, owner: str, author: str, dry_run: bool = False) -> list[tuple[str, str]]:
    """Write what is missing. Returns (file, why) for each file written, or that would be written."""
    path = Path(path).expanduser().resolve()
    if not owner or not author:
        raise ValueError("the kit needs an owner and an author (flags --owner and --author, or the facts file)")
    name, kind = facts.get("name") or path.name, facts.get("kind") or "tool"
    display, year = facts.get("display") or name, facts.get("year") or datetime.now().year
    actions: list[tuple[str, str]] = []

    def write(rel: str, text: str, why: str) -> None:
        actions.append((rel, why))
        if not dry_run:
            target = path / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")

    texts = {"LICENSE": MIT.format(year=year, author=author), "SECURITY.md": SECURITY, "CONTRIBUTING.md": CONTRIBUTING,
             "CODE_OF_CONDUCT.md": CONDUCT}
    lic = next((path / a for a in HYGIENE["LICENSE"] if (path / a).exists()), None)
    licence = licence_kind(lic.read_text()[:600]) if lic else "MIT"  # a missing licence is written as MIT
    for f, alts in HYGIENE.items():
        if not any((path / a).exists() for a in alts):
            write(f, texts[f], "missing")
    if (path / "AGENTS.md").exists() and not (path / "GEMINI.md").exists():
        write("GEMINI.md", GEMINI, "Gemini CLI reads GEMINI.md")
    if not (path / "NOTICE").exists():
        brand = f"{display} is part of {facts['brand_line']}.\n\n" if facts.get("brand_line") else ""
        terms = (f"Licensed under the {licence} License. See LICENSE." if licence in ("MIT", "Apache-2.0")
                 else "See LICENSE for the terms.")
        write("NOTICE", f"{display}\nCopyright (c) {year} {author}\n\n{brand}{terms}\n", "the attribution beside the licence")
    version, desc = version_of(path), facts.get("one_liner", "")
    author_obj = {"name": author, "url": f"https://github.com/{owner}"}
    if kind in AGENT_KINDS:
        if not (path / ".claude-plugin/plugin.json").exists():
            write(".claude-plugin/plugin.json", json.dumps({
                "name": facts.get("plugin_name", name), "version": version, "description": desc, "author": author_obj,
                "homepage": f"https://github.com/{owner}/{name}", "repository": f"https://github.com/{owner}/{name}",
                "license": licence or "MIT", "keywords": ["agent-native", "claude-code"]}, indent=2) + "\n",
                "Claude Code reads only plugin.json")
        if not (path / ".claude-plugin/marketplace.json").exists():
            write(".claude-plugin/marketplace.json", json.dumps({
                "name": name, "owner": author_obj, "description": desc,
                "plugins": [{"name": facts.get("plugin_name", name), "source": "./", "description": desc}]}, indent=2)
                + "\n", "one-step install")
        if not (path / "gemini-extension.json").exists():
            body: dict = {"name": name, "version": version, "description": desc, "contextFileName": "GEMINI.md"}
            if facts.get("mcp_bin"):
                cmd = runner(owner, name, facts) + [facts["mcp_bin"]]
                body["mcpServers"] = {name: {"command": cmd[0], "args": cmd[1:]}}
            write("gemini-extension.json", json.dumps(body, indent=2) + "\n", "Gemini CLI extension")
        if not list(path.glob(".well-known/agent*.json")):
            write(".well-known/agent-card.json", json.dumps({
                "name": facts.get("soul") or name, "description": desc, "url": f"https://github.com/{owner}/{name}",
                "version": version, "provider": {"organization": author, "url": f"https://github.com/{owner}"},
                "capabilities": {"streaming": False}, "defaultInputModes": ["text/plain"],
                "defaultOutputModes": ["text/plain"],
                "skills": [{"id": s["path"].split("/")[-2], "name": s["path"].split("/")[-2], "description": s.get("what", "")}
                           for s in (facts.get("skills") or [])[:20]]}, indent=2) + "\n", "A2A agent card")
    readme_path = path / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else f"# {name}\n"
    if not re.search(r"^# ", readme, re.M):
        readme = f"# {name}\n\n" + readme
    has_license = bool(re.search(r"^#{1,3} .*licen[cs]e", outside_blocks(readme), re.I | re.M))
    readme = place(readme, "header", header_block(owner, name, facts, path), "after-title")
    readme = place(readme, "use", use_block(owner, name, facts, path), "before-first-section")
    if facts.get("components"):
        readme = place(readme, "anatomy", anatomy_block(facts), "end")
    readme = place(readme, "footer", footer_block(owner, name, facts, path, author, has_license), "end")
    if not readme_path.exists() or readme != readme_path.read_text(encoding="utf-8"):
        write("README.md", readme, "README blocks")
    return actions
