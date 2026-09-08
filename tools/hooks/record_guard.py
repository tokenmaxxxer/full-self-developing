"""PreToolUse hook for spawned sessions (Write/Edit/MultiEdit).

Denies a write when:
  - the target is a record under docs/issue-*/reports/ that is not this
    session's own (`$OTR_SESSION` hex), or belongs to another issue;
  - the target is under docs/issue-<n>/approvals/ (human-only);
  - the target is docs/specs/approvers.md (human-only).

Everything else passes. Exit 2 + stderr = deny in Claude Code hooks.
Fails closed on unreadable input.
"""
import json
import os
import re
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        path = payload["tool_input"].get("file_path") or payload["tool_input"].get("notebook_path")
    except Exception:
        print("record_guard: cannot read hook input; denying", file=sys.stderr)
        return 2
    if not path:
        return 0
    session = os.environ.get("OTR_SESSION", "")
    issue = os.environ.get("OTR_ISSUE", "")
    rel = os.path.relpath(path, os.getcwd()).replace(os.sep, "/")

    if rel == "docs/specs/approvers.md" or re.search(r"^docs/issue-\d+/approvals/", rel):
        print(f"record_guard: {rel} is written by a human only", file=sys.stderr)
        return 2
    m = re.match(r"^docs/issue-(\d+)/reports/([0-9a-f]{8})\.md$", rel)
    if m:
        if m.group(1) != issue:
            print(f"record_guard: this session is bound to issue-{issue}, not issue-{m.group(1)}", file=sys.stderr)
            return 2
        if m.group(2) != session:
            print(f"record_guard: {rel} belongs to another session; use supersedes:/amends: in your own record", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
