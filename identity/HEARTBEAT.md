# Muster: heartbeat

What is checked, how often, and what happens on an anomaly. The nightly loop (`.github/workflows/loop.yml`, which
runs `evals/loop.py`) does the checks; it proposes, and a person decides.

| Check | Frequency | On an anomaly |
| --- | --- | --- |
| Unit tests and evals: golden tasks on fixture repositories, the MCP round trip | Every push and pull request (`ci.yml`) and nightly (`loop.yml`) | CI goes red and blocks the merge; the loop opens or updates the proposals issue. |
| Self-audit: this repository passes its own checks | Every push (`ci.yml`) and nightly | A proposal names the missing check and its fix. |
| Self-scrub: this tree matches no example pattern | Nightly | A proposal names the pattern number and the file. |
| The run log | Every command | `fleet-audit runs` lists each run with its outcome and duration. |

## Health

- **Healthy:** CI is green on `main`, and the last loop run proposed nothing or its issue is triaged.
- **Warning:** a proposals issue has stayed open for more than a week.
- **Critical:** an eval fails on `main`, or the scrub ever prints matched text. Fix it before any other change.

## Recovery

1. Read the failing eval in the CI log or in the loop's `proposals` artifact.
2. Search memory: `python3 scripts/memory_search.py "<symptom>"`.
3. Reproduce with `python3 evals/run.py`, fix the cause, add a test, and write the lesson in
   `memory/LEARNINGS.md`.
