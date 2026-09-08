---
issue: 3
title: board: show in-flight branches with their record state
opened: 2026-09-08
state: done   # open | done | rejected
---

# issue-3 — board: show in-flight branches with their record state

## Need

`otr board` only reads records merged on main, so a branch that is still
in flight shows as a bare "in flight" line with no type/loop_state. The
orchestrator needs to see, per open branch, the record's `type` and
`loop_state` as they are on the branch tip, and whether the branch is
approved, without checking the branch out.

## Acceptance

- For every branch `issue-<n>/<hex>` not yet merged, `otr board` prints the
  record's `type` and `loop_state` read from `<branch>:docs/issue-<n>/reports/<hex>.md`
  (or `no record` if absent), plus `approved` when `docs/issue-<n>/approvals/<hex>.md`
  exists on main.
- Merged records keep their current rendering.
- `python3 tools/otr.py board` exits 0 on a repo with no issues and on this repo.

## Out of scope

- Any change to record_lint.py, templates, or the approve/accept/reject commands.
