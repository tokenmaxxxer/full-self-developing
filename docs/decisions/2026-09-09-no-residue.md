---
id: no-residue
status: frozen
scope:
  globs: ["plugin/tools/otr.py", ".gitignore", "runs/**"]
  keywords: ["/tmp", "$HOME", "scratch", "worktree", "runs/"]
---

# A round leaves no residue

Date: 2026-09-09 (was north pole N3 since 2026-09-08).

## Decision

Everything a session creates lives under `runs/` inside the repo
(worktrees in `runs/ws/`, scratch in `runs/scratch/`), is git-ignored, and
is removed on accept, reject, or `otr clean`. Nothing is written to `/tmp`
or `$HOME`.
