"""Lint one record (docs/issue-<n>/reports/<hex>.md) or sweep the repo.

Deterministic, zero LLM calls. Prints every violation in one pass so a
session fixes them all at once instead of one refusal per turn.

Usage:
    python3 tools/record_lint.py [path]        # one record, or sweep cwd
Importable:
    lint_record(path) -> list[str]
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

TYPES = {"proposal", "implementation", "verification", "repair"}
LOOP_STATES = {"proposed", "approved", "landed", "done"}
TERMINAL = {"landed", "done"}
REQUIRED = ["issue", "author", "type", "loop_state", "verdict"]
REQUIRED_SECTIONS = ["## What was done", "## Evidence", "## Principles"]
HEX_RE = re.compile(r"^[0-9a-f]{8}$")


def parse_frontmatter(text: str) -> tuple[dict[str, str] | None, str]:
    """Return ({key: raw value}, body). Trailing `# comments` are stripped.
    Multi-line values are folded onto their key. None if no block."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, text
    block, body = text[4:end], text[end + 5:]
    fm: dict[str, str] = {}
    key = None
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*):(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = _strip_comment(m.group(2))
        elif key is not None:
            fm[key] = (fm[key] + " " + _strip_comment(line)).strip()
    return fm, body


def _strip_comment(s: str) -> str:
    return re.sub(r"\s+#.*$", "", s).strip()


def lint_record(path: Path) -> list[str]:
    errs: list[str] = []
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    if fm is None:
        return [f"{path}: no frontmatter block"]

    for k in REQUIRED:
        if not fm.get(k):
            errs.append(f"missing required field: {k}")

    m = re.match(r"docs/issue-(\d+)/reports/([0-9a-f]{8})\.md$", path.as_posix())
    if not m:
        errs.append("path must be docs/issue-<n>/reports/<8hex>.md")
    else:
        issue, hexid = m.groups()
        if fm.get("issue") and fm["issue"] != issue:
            errs.append(f"issue: {fm['issue']} does not match path issue-{issue}")
        if fm.get("author") and fm["author"] != hexid:
            errs.append(f"author: {fm['author']} does not match filename {hexid}")

    if fm.get("author") and not HEX_RE.match(fm["author"]):
        errs.append("author must be 8 lowercase hex chars")
    if fm.get("type") and fm["type"] not in TYPES:
        errs.append(f"type must be one of {sorted(TYPES)}, got {fm['type']}")
    ls = fm.get("loop_state")
    if ls and ls not in LOOP_STATES:
        errs.append(f"loop_state must be one of {sorted(LOOP_STATES)}, got {ls}")

    if "PLACEHOLDER" in text or re.search(r"<[a-z][^>\n]{0,60}>", body):
        errs.append("template placeholder text survives (PLACEHOLDER or <...>)")

    for sec in REQUIRED_SECTIONS:
        if sec not in body:
            errs.append(f"missing section: {sec}")
    if ls in TERMINAL and "## Acceptance verification" not in body:
        errs.append("terminal record (landed/done) needs ## Acceptance verification")
    if ls in TERMINAL and not _section_has_content(body, "## Acceptance verification"):
        errs.append("## Acceptance verification is empty")
    if fm.get("type") == "proposal" and not _section_has_content(body, "## Acceptance"):
        errs.append("proposal record needs a non-empty ## Acceptance section")
    if not _section_has_content(body, "## Evidence"):
        errs.append("## Evidence is empty — a record with no evidence is a claim")
    if fm.get("type") == "proposal" and not _section_has_content(body, "## Judgment"):
        errs.append("proposal record needs a non-empty ## Judgment section")
    errs.extend(_judgment_errors(body))

    for ref in re.findall(r"path:\s*([^\s,]+)", fm.get("upstream", "")):
        if not (Path(ref).exists()):
            errs.append(f"upstream path does not exist: {ref}")

    return [f"{path}: {e}" for e in errs]


def find_section(body: str, header: str) -> int:
    """Index of `header` as its own line (not a prefix of a longer header, e.g.
    `## Acceptance` must not match inside `## Acceptance verification`)."""
    m = re.search(rf"(?m)^{re.escape(header)}\s*$", body)
    return m.start() if m else -1


def _section_has_content(body: str, header: str) -> bool:
    return bool(_section_content(body, header).strip())


def _section_content(body: str, header: str) -> str:
    i = find_section(body, header)
    if i < 0:
        return ""
    rest = body[i + len(header):]
    j = rest.find("\n## ")
    return rest if j < 0 else rest[:j]


def _judgment_errors(body: str) -> list[str]:
    """`## Judgment` (when present) must be `none` or, if it lists more than one
    method, mark which is smallest."""
    content = _section_content(body, "## Judgment").strip()
    if not content or content.lower() == "none":
        return []
    methods = [ln for ln in content.splitlines() if ln.strip().startswith("-")]
    if len(methods) > 1 and not any("(smallest)" in ln for ln in methods):
        return ["## Judgment lists more than one method without marking which is smallest"]
    return []


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        paths = [Path(argv[1])]
    else:
        paths = sorted(Path(".").glob("docs/issue-*/reports/*.md"))
        if not paths:
            print("no records found")
            return 0
    errs = [e for p in paths for e in lint_record(p)]
    for e in errs:
        print(e)
    if not errs:
        print(f"ok: {len(paths)} record(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
