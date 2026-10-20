#!/usr/bin/env python3
"""Search fleet-audit's memory with BM25: the memory files, the identity, the skills and the guides.

  python3 scripts/memory_search.py "why does the scrub use git grep -P" [--limit 5]

Each paragraph, and each list item, is a document. Results print the file, the line and the first line of
the match, best first.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ["memory/*.md", "identity/*.md", "skills/*/SKILL.md", "AGENTS.md", "docs/*.md"]
K1, B = 1.5, 0.75
STOP = set("a an and are as at be by do does for from how in is it its not of on or the to what when why with".split())
ITEM = re.compile(r"^(\s{0,2}[-*] |\d+\. )")


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]


def paragraphs() -> list[tuple[str, int, str]]:
    out = []
    for pattern in SOURCES:
        for path in sorted(ROOT.glob(pattern)):
            line, buf, start = 0, [], 1
            for line, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if buf and ITEM.match(text):  # each list item is its own document
                    out.append((str(path.relative_to(ROOT)), start, "\n".join(buf)))
                    buf = []
                if text.strip():
                    if not buf:
                        start = line
                    buf.append(text)
                elif buf:
                    out.append((str(path.relative_to(ROOT)), start, "\n".join(buf)))
                    buf = []
            if buf:
                out.append((str(path.relative_to(ROOT)), start, "\n".join(buf)))
    return out


def search(query: str, limit: int = 5) -> list[tuple[float, str, int, str]]:
    docs = paragraphs()
    toks = [tokens(d[2]) for d in docs]
    avg = sum(len(t) for t in toks) / max(len(toks), 1)
    df: dict[str, int] = {}
    for t in toks:
        for w in set(t):
            df[w] = df.get(w, 0) + 1
    scored = []
    for (path, line, text), t in zip(docs, toks):
        score = 0.0
        for q in set(tokens(query)):
            tf = t.count(q)
            if tf:
                idf = math.log(1 + (len(docs) - df[q] + 0.5) / (df[q] + 0.5))
                score += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * len(t) / avg))
        if score:
            scored.append((score, path, line, text))
    return sorted(scored, key=lambda s: -s[0])[:limit]


def main() -> int:
    args = sys.argv[1:]
    if not args or {"-h", "--help"} & set(args):
        print(__doc__)
        return 0
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 5
    query = " ".join(a for i, a in enumerate(args) if a != "--limit" and (i == 0 or args[i - 1] != "--limit"))
    hits = search(query, limit)
    for score, path, line, text in hits:
        print(f"{score:6.2f}  {path}:{line}  {text.splitlines()[0][:100]}")
    if not hits:
        print("no match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
