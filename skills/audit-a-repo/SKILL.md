---
name: audit-a-repo
description: Measure a repository, or every repository of a GitHub owner, for the surfaces coding agents need (AGENTS.md, llms.txt, skills, sub-agents, hooks, an MCP server, a CLI, a plugin, an extension, an agent card, a self-improvement loop) and list each gap with its fix. Use when asked what a repository is missing for agents, whether it is ready to publish, or where a set of repositories stands.
---

# Audit a repository

## When to use

Before publishing a repository, when someone asks whether it is ready for agents, or to see where a set of
repositories stands.

## Steps

1. **Check one repository:** `fleet-audit check <path>`. Add `--head` before a push (it reads the local HEAD) and
   `--offline` without gh. Pass `--facts <facts.json>` when the repository has a facts file: it decides the skill
   count, the one-step proof and the component grades.
2. **Read each line:** pass; MISSING, with the fix; or unknown, which needs a facts file, gh, or `--patterns` for
   the scrub.
3. **Many repositories:** `fleet-audit report <path> ... --facts-dir <folder> --out readiness.md`, or
   `fleet-audit scan --owner <owner> --clones <folder> --out scan.json` for everything an owner has.
4. **Split the work:** lines marked "the kit writes it" are one command away (the fix-with-the-kit skill). The rest
   need writing by hand: AGENTS.md, skills, a hook, an MCP server, evals.
5. **Check again after the fixes are committed.** The check reads committed state.

## Output

The check table or the Markdown report, then a short plan: what the kit will write, what needs hand work, and what
is unknown and why.

## Anti-patterns

- Counting "unknown" as a pass. Decide it: add the facts file, sign in to gh, or run the scrub.
- Auditing uncommitted work. Commit first, or use `--head` after committing locally.
