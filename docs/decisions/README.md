# Decisions

One file per decision, `YYYY-MM-DD-<slug>.md`, with frontmatter:

```yaml
---
id: git-only-ledger        # stable slug; defaults to the filename stem
status: frozen             # frozen | active | superseded
scope:                     # required when frozen
  globs: ["tools/otr.py", "docs/issue-*/**"]
  keywords: ["github issue", "label"]
---
```

- `frozen` — a principle. Only the human changes it, by a new decision that
  supersedes this one. A subagent whose change touches a frozen decision's
  `scope` (any path glob in its diff, or any keyword in its record) must
  write `reaffirms <id>` under `## Principles` in its record — or, if the
  change works against the principle, put it under `## Deviations` and stop.
  `otr accept` refuses a branch that touches a frozen scope with neither.
- `active` — a normal landed decision; informational.
- `superseded` — kept for history; the body names the successor.

A withdrawn design stays here with its cause of death, so it is not dug twice.

`python3 tools/decisions.py` lints every file and lists the frozen ones.
