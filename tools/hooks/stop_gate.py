"""Stop hook for spawned sessions: refuse to end while the session's own
record fails lint or has uncommitted changes. Output goes back to the
session as additionalContext so it can fix and retry.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from record_lint import lint_record  # noqa: E402
from pathlib import Path  # noqa: E402


def main() -> int:
    issue = os.environ.get("OTR_ISSUE", "")
    session = os.environ.get("OTR_SESSION", "")
    rec = Path(f"docs/issue-{issue}/reports/{session}.md")
    problems = []
    if not rec.exists():
        problems.append(f"record {rec} does not exist — write it before stopping")
    else:
        problems += lint_record(rec)
    dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    if dirty:
        problems.append("uncommitted changes:\n" + dirty)
    if problems:
        print(json.dumps({"decision": "block", "reason": "\n".join(problems)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
