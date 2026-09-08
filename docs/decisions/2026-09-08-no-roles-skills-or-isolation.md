---
id: no-roles-skills-or-isolation
status: frozen
scope:
  globs: ["plugin/tools/**", "CLAUDE.md", ".claude/**", "roles/**", "skills/**"]
  keywords: ["role file", "rulebook", "skill axis", "sandbox", "hook", "settings.json", "claude -p"]
---

# No roles, no skills, no per-session isolation

Date: 2026-09-08.

## Decision

A session is `issue + hex`; what it does is the task text. There is no role
file, no rulebook or skill mounted per session, no sandbox, no hooks, and
no headless `claude -p` spawn. The subagent shares the operator's
environment and uses whatever is in it — including any skills installed
there — on its own judgment; the directive never names one. Delegation is the interactive session
passing `otr directive` output to the Agent tool.

## Why

The operator wanted only two ideas from the source project — the git
record system and delegation to subagents (northpole N1, N3). The source
project's own trajectory (issue #2241, role-axis retirement) points the
same way. Isolation was built once here (hooks, `--settings`, env) and
removed the same day: it added surface without serving either idea.

## Consequences

- Invariants hold by directive text and by `otr accept` checks, not by
  enforcement around the subagent.
- Re-introducing any of these is a new decision that supersedes this one.
