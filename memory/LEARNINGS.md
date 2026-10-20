# Muster (fleet-audit): learnings

Every mistake becomes a rule. Append only, newest last. The first entries are the lessons this tool was built from.

## 2026-10-19: the lessons behind the first release

- **A pattern written for git grep is not a Python regex.** `[[:space:]]` is a POSIX class to `git grep -E` but a
  set of characters to Python, so a history rewrite could replace the wrong text. Rule: translate POSIX classes
  before handing patterns to filter-repo (`scrub.python_regex`), and prove a rewrite by scrubbing the rewritten mirror.
- **On macOS, `git grep -E` and `git log -G` cannot match `\b` or `\d`.** Apple's git uses the BSD regex library,
  so those patterns silently matched nothing, and every "clean" for them was false. Rule: scan trees with
  `git grep -P`; for `git log -G`, translate `\b` to `[[:<:]]` and `[[:>:]]` and `\d` to `[0-9]` (`scrub.ere`);
  test every pattern on a known hit before trusting a zero.
- **Commit messages are published too.** Rule: the scrub reads every message on every ref.
- **A history rewrite breaks gitleaks fingerprints.** `.gitleaksignore` entries name a commit, so after a rewrite
  every fingerprinted false positive comes back. Rule: allowlist known false positives in the repository's
  `.gitleaks.toml` by path or regex, which survive a rewrite; the scrub reads `.gitleaks.toml` from the ref, so a
  bare mirror honours it.
- **A tool with no help option ran its default on `--help`.** A scrub started over every repository. Rule: every
  command and script answers `-h` and `--help` before it does anything else.
- **"Not applicable" was read as a failure.** Rule: a check that cannot be decided is "unknown", counted apart from
  passes and failures.
- **A package ships only what it lists.** Commands that read a file outside the package failed from a fresh
  one-step install. Rule: everything a command reads at run time lives inside the package, and the one-step install
  is proved from an empty folder, never from the clone.
- **A fixture can trip the scrub it tests.** Rule: planted strings in tests and evals are assembled at run time, so
  no committed file holds them whole.
