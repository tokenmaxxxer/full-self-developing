"""Decision registry: parse docs/decisions/*.md frontmatter, lint it, and
answer "which frozen decisions does this change touch?".

    python3 tools/decisions.py            # lint + list frozen decisions
Importable:
    frozen() -> list[Decision]
    touched(paths, text) -> list[(Decision, why)]
"""
from __future__ import annotations
import re
import sys
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from record_lint import parse_frontmatter  # noqa: E402

import subprocess
_top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
ROOT = Path(_top.stdout.strip()) if _top.returncode == 0 else Path.cwd()   # the target repo
DIR = ROOT / "docs" / "decisions"
STATUSES = {"frozen", "active", "superseded"}


@dataclass
class Decision:
    id: str
    status: str
    path: Path
    globs: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


def _scope(fm: dict) -> tuple[list[str], list[str]]:
    """parse_frontmatter folds the nested `scope:` mapping into one string:
    'globs: ["a", "b"] keywords: ["x"]' — pull the two lists back out."""
    raw = fm.get("scope", "")
    out = []
    for key in ("globs", "keywords"):
        m = re.search(key + r":\s*\[(.*?)\]", raw)
        out.append([x.strip().strip('"\'') for x in m.group(1).split(",") if x.strip()] if m else [])
    return out[0], out[1]


def load() -> tuple[list[Decision], list[str]]:
    decs, errs = [], []
    for p in sorted(DIR.glob("*.md")):
        if p.name == "README.md":
            continue
        fm, _ = parse_frontmatter(p.read_text())
        if fm is None:
            errs.append(f"{p.name}: no frontmatter")
            continue
        status = fm.get("status", "")
        if status not in STATUSES:
            errs.append(f"{p.name}: status must be one of {sorted(STATUSES)}, got {status!r}")
        globs, keywords = _scope(fm)
        d = Decision(fm.get("id") or p.stem[11:], status, p, globs, keywords)
        if status == "frozen" and not (d.globs or d.keywords):
            errs.append(f"{p.name}: frozen decision needs a non-empty scope (globs or keywords)")
        decs.append(d)
    return decs, errs


def frozen() -> list[Decision]:
    return [d for d in load()[0] if d.status == "frozen"]


def _glob_hit(path: str, pat: str) -> bool:
    if fnmatch(path, pat):
        return True
    return pat.endswith("/**") and (path == pat[:-3] or path.startswith(pat[:-3] + "/"))


def touched(paths: list[str], text: str = "") -> list[tuple[Decision, str]]:
    hits, low = [], text.lower()
    for d in frozen():
        for p in paths:
            g = next((g for g in d.globs if _glob_hit(p, g)), None)
            if g:
                hits.append((d, f"path {p} matches {g}"))
                break
        else:
            k = next((k for k in d.keywords if k.lower() in low), None)
            if k:
                hits.append((d, f"record mentions {k!r}"))
    return hits


def main() -> int:
    decs, errs = load()
    for e in errs:
        print(e)
    for d in decs:
        if d.status == "frozen":
            print(f"frozen  {d.id:<32} {d.path.relative_to(ROOT)}")
    if not errs:
        print(f"ok: {len(decs)} decision(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
