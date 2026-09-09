---
id: minimal-change
status: frozen
scope:
  globs: [".github/**", "**/ci/**", "**/deploy/**", "**/*.yml", "**/*.yaml", "plugin/templates/record.md", "plugin/tools/otr.py"]
  keywords: ["CI", "CD", "pipeline", "deploy", "workflow", "abstraction", "framework", "refactor", "test suite", "coverage"]
---

# The smallest change that solves the stated problem

Date: 2026-09-09.

## Decision

A proposal always contains the smallest change that satisfies the issue's
Problem. If the agent chooses a larger one, the record says why under
`## Judgment`. Tests, CI/CD, deployment, abstraction, configurability or
refactoring that the Problem does not require are Deviations to record,
not deliverables to build. `otr accept` requires a recorded reason when
the diff adds files of a kind the Problem did not ask for; it does not
forbid them.

## Why

Agents default to doing more: surveyed reports show unrequested tests per
function, unrequested deployments, unrequested architecture changes. The
human's correction ("keep it simple") does not survive an unattended
night unless it is a gate.
