# Muster

> **Tagline:** _Every repository answers the roll._

## Identity

I am **Muster**, the persona of fleet-audit: the roll call a set of repositories answers before anyone relies on
it. I read what is committed, never what someone remembers, and for each repository I say what is present, what is
missing, and what one command can fix. My users are coding agents first, through my command line and my MCP server,
and the people who own the repositories second.

**The one belief everything else follows from:** a repository is only as usable as its weakest surface. An agent
that cannot find AGENTS.md, cannot install the tool in one step, or cannot tell whether a change was tested will
guess, and guessing is how agents break things. So I count surfaces, not intentions.

## What I do

1. **Scan.** Measure the surfaces coding agents need, the identity and memory files, the hygiene of a mature
   project and the README, from a committed ref.
2. **Check.** Turn the scan into one line per check: pass, missing (with the fix), or unknown.
3. **Scrub.** Run your patterns over the tree, the whole history and every commit message, and gitleaks over the
   history, before a repository goes public.
4. **Fix.** Write the standard files and the README blocks a repository is missing, from its facts file.
5. **Plan the history.** Rewrite a scratch mirror to drop internal notes and scrub hits, and prove it clean.
6. **Report.** One Markdown page over many repositories.

## Personality

- Precise and unhurried. I name the file behind every verdict.
- Discreet. A scrub names a pattern by its number and never repeats what it found.
- Additive. I write what is missing and replace only my own marked blocks. I never delete a file.
- Honest about what I cannot see. A check I cannot decide is "unknown", never a pass and never a failure.

## Boundaries (what I refuse)

- **Writing to a repository unless asked to run the kit.** My MCP kit tool is a dry run until it is told to write.
- **Printing matched text** from a scrub, in any output, log or report.
- **Pushing, force-pushing, changing a repository's visibility, or publishing anything.** The history plan
  rewrites a scratch mirror and stops there; the owner decides the rest.
- **Holding your patterns.** They live in a file you name, outside every repository; I ship only neutral examples.
- **Calling a model or needing a key.** I am deterministic.

## How I introduce myself

**To a coding agent:** "I'm Muster, fleet-audit. Point me at a repository and I'll tell you what an agent will find
there, what it will miss, and which gaps one command fixes. I never write unless you ask me to run the kit."

**To a person:** "Before you publish a repository, I check that agents can use it and that nothing private comes
with it: not in the files, not in the history, not in the commit messages."
