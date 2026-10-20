---
name: fix-with-the-kit
description: Write a repository's missing standard files (licence, security and contributing guides, code of conduct, GEMINI.md, NOTICE, the Claude Code plugin and marketplace, the Gemini CLI extension, the A2A agent card) and its README blocks from a facts file, with a dry run first. Use after an audit lists gaps marked "the kit writes it", or when bringing a new repository up to the standard.
---

# Fix with the kit

## When to use

An audit shows gaps the kit can fill, or a new repository needs the standard files and README blocks.

## Steps

1. **Write the facts file.** Start from `facts.example.json`: the one-liner, the kind, the CLI and MCP bins, the
   skills you wrote, the runtime (`python` gives uvx commands, anything else npx) and, once tested, the component
   grades.
2. **Dry run:** `fleet-audit kit <path> --facts <facts.json> --owner <github-owner> --author "<licence holder>" --dry-run`.
   Read the list.
3. **Write:** the same command without `--dry-run`. It creates only missing files and replaces only its own marked
   README blocks.
4. **Write the README body around the blocks:** two or three plain sentences on what it is and who it is for, a
   Quick start with commands you ran, and how it works.
5. **Run it again** after you update the facts file. The blocks are replaced in place, never duplicated.
6. **Commit by explicit path,** then run `fleet-audit check <path>` again.

## Output

The list of files written, the README with its blocks, and the check table after the commit.

## Anti-patterns

- Writing without a dry run in a repository you do not know.
- Editing inside the marked blocks by hand: the next run replaces them. Change the facts file instead.
- Grading a component in the facts file before you have tested it.
