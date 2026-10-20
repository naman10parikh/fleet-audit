---
name: scrub-before-public
description: Scrub a repository before it goes public, over the tree, the whole history, the commit messages and secrets, with a patterns file kept outside every repository; triage each hit and plan any history rewrite in a scratch mirror. Use before a repository's visibility changes to public, before the first push of a repository carved out of a private one, or when a confidential name, a personal detail or a key may be in it.
---

# Scrub before going public

## When to use

Before a repository is made public (going public publishes every commit), before pushing a repository carved out
of a private one, or when a leak is suspected.

## Steps

1. **Write your patterns** in a file outside every repository. Copy `scrub-patterns.example.txt`: one regex per
   line, `CS ` in front for case-sensitive, `==>text` at the end for the history replacement. Test each new pattern
   on a known hit before you trust a zero.
2. **Scrub:** `fleet-audit scrub <path> --patterns <file>` checks the tree, the history, the commit messages and,
   with gitleaks installed, secrets. Before a push, `--head --tree` checks the committed tree in seconds.
3. **Triage by pattern number.** A tree hit: remove it in a new commit. A secret: rotate it at the provider first,
   then remove it. A test fixture shaped like a secret: assemble it at run time, or allowlist it in `.gitleaks.toml`
   by path or regex.
4. **History:** when the history or the messages still match, plan the rewrite:
   `fleet-audit history <owner/name> --patterns <file> --facts-dir <folder> --out <scratch>`. It rewrites a scratch
   mirror, drops the facts file's `internal_files`, and scrubs the result. It pushes nothing.
5. **Stop for the owner.** Pushing a rewritten history is a force-push, and going public changes visibility. Both
   wait for the owner's explicit yes.

## Output

The scrub line (CLEAN, or DIRTY with counts per pattern number), the triage list (pattern, file, action) and, when
needed, the history plan's result: commits before and after, notes dropped, clean or not.

## Anti-patterns

- Pasting matched text into a report or an issue. Name the pattern number and the file.
- Keeping the patterns file inside the repository you are about to publish.
- Removing a live key without rotating it first.
