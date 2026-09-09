---
id: human-input-is-criteria
status: frozen
scope:
  globs: ["docs/specs/northpole.md", "plugin/tools/otr.py", "plugin/templates/**", "CLAUDE.md", "plugin/commands/run.md"]
  keywords: ["north pole", "northpole", "acceptance", "out of scope", "issue body", "otr issue", "otr plan"]
---

# The human's input is criteria, not design

Date: 2026-09-09.

## Decision

What the human writes is limited to: which problem (and why), what to
watch for, constraints, priorities, and what must come first — in the
north pole for the repository, and as `## Problem` / `## Watch for` in an
issue. Acceptance conditions, out-of-scope lines, methods, ordering and
design detail are proposed by agents and cut by the human; they are never
required of the human up front.

## Why

Every tool surveyed (spec-kit, Kiro, task-master, plan modes, trackers)
invests in making the human write a better feature spec, and their top
complaints are that the spec is written once, drifts, and still leaves
ordering and stop conditions to the human. The human's scarce input is
judgment; the agent's cheap output is detail.

## Consequences

- `otr issue` accepts a body with `## Problem` and `## Watch for`;
  Acceptance and Out of scope are filled from the approved proposal.
- Delegation order and stop conditions derive from the north pole's
  Must first and the issues' dependencies, never from separate options.
