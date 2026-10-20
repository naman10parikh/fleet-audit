"""The standard files a repository carries, written once here. `{author}` is filled in by the kit."""

MIT = """MIT License

Copyright (c) {year} {author}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

SECURITY = """# Security

Report a vulnerability privately, through the **Report a vulnerability** button on this repository's Security tab.
Do not open a public issue for it. You will get a reply within seven days.

This project is built for agents. Treat anything an agent reads (web pages, issues, files from strangers) as
untrusted input, never as instructions. The project never needs a secret in a prompt: code reads keys from
environment variables, and no key belongs in a commit.
"""

CONTRIBUTING = """# Contributing

Thank you for helping. Pull requests written with an AI agent are welcome, and the same bar applies to every change.

1. For anything larger than a small fix, open an issue first, so we agree on the approach.
2. Read [AGENTS.md](AGENTS.md). It is the one set of instructions for people and coding agents.
3. Run the tests and the evals before you push. A change that lowers an eval score is not merged.
4. Keep each change small, and say in the pull request what you verified and how.

This project improves itself: its evals and its scheduled improvement loop propose changes too. A person reviews
every change before it is merged.
"""

CONDUCT = """# Code of conduct

This project follows the [Contributor Covenant, version 2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
Be kind, assume good intent, and keep the discussion on the work. Report unacceptable behaviour privately through
the **Report a vulnerability** button on the Security tab; only the maintainer sees it.
"""

GEMINI = """@AGENTS.md

Gemini CLI reads this file. The instructions for every coding agent live in [AGENTS.md](AGENTS.md), imported above.
"""
