"""PreToolUse hook for spawned sessions (Bash).

Denies: git push; git checkout/switch to main; git merge; git branch -D;
git worktree; editing .git/config. The session works on its own branch in
its own worktree and never lands anything itself.
"""
import json
import re
import sys

DENY = [
    (r"\bgit\s+push\b", "push is done by the human (accept = merge to main)"),
    (r"\bgit\s+(checkout|switch)\s+.*\bmain\b", "stay on your issue branch"),
    (r"\bgit\s+merge\b", "merging is the human's acceptance act"),
    (r"\bgit\s+branch\s+-[dD]\b", "do not delete branches"),
    (r"\bgit\s+worktree\b", "worktrees are managed by spawn"),
    (r"\bgit\s+reset\s+--hard\b", "no history rewrite in a shared branch"),
    (r"\.git/config\b", "do not touch .git/config"),
    (r"\brm\s+.*\.lock\b", "a lock file is a signal to diagnose, not delete"),
]


def main() -> int:
    try:
        cmd = json.load(sys.stdin)["tool_input"].get("command", "")
    except Exception:
        print("git_guard: cannot read hook input; denying", file=sys.stderr)
        return 2
    for pat, why in DENY:
        if re.search(pat, cmd):
            print(f"git_guard: denied ({why}): {cmd}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
