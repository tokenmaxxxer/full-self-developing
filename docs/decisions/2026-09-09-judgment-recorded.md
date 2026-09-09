---
id: judgment-recorded
status: frozen
scope:
  globs: ["plugin/templates/record.md", "plugin/tools/record_lint.py", "plugin/tools/otr.py", "CLAUDE.md"]
  keywords: ["## Judgment", "priorities", "watch for", "chose", "rejected", "deviation"]
---

# Judgment is recorded as applied

Date: 2026-09-09.

## Decision

When an agent chooses between methods by the north pole's Priorities, or
changes course because of a Watch for item, that judgment goes in the
record under `## Judgment`: what was chosen, what was rejected, which
priority or watch item decided it. The end-of-drive report lists these
judgments before the diffs, so the human reads how their criteria were
applied, not only what landed.

## Why

The north pole is only as good as the human's ability to see it applied.
Without recorded judgment, "this serves Priorities #1" is an unfalsifiable
claim and the human cannot tell the next morning whether the criteria
held.
