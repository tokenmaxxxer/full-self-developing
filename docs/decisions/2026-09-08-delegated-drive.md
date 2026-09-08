---
id: delegated-drive
status: frozen
scope:
  globs: ["CLAUDE.md", "plugin/commands/run.md"]
  keywords: ["auto-approve", "auto-accept", "delegation", "via delegation", "self-assigned", "fill the gap"]
---

# Full self-drive under a human-committed delegation

Date: 2026-09-08.

## Decision

The orchestrator approves proposals and accepts deliveries on its own —
no human turn — while a delegation is live: a `DELEGATE <issues|all>
UNTIL <iso>` comment by an approver on the pinned `delegation` issue, not
followed by `REVOKE`, not expired. Every delegated act is its own comment
or merge marked `VIA DELEGATION`, so the human can audit and revert each one. Deviations become follow-up issues and are
driven the same way; nothing is handed back to the human except the stops
named in `CLAUDE.md` (frozen-principle conflict, out-of-scope, three
failures on one issue, a standard only the human holds).

## Why

The repository exists to reach a stated need without the human steering
(northpole N0). The source project split this into two mechanisms — a
GitHub `DELEGATE … UNTIL` comment (#707) and a local delegation-state file
(#3061) — because approvals warranted a live remote check. Here the
ledger is git, so one file on `main` is both the grant and the live
check: `otr` reads it from `main` on every delegated act, and a `REVOKE`
commit is honoured the moment it lands.

The human chose full drive (approve and accept both delegated) over
supervised drive (accept kept manual). Reversal cost is low in git — a
`REJECT` commit plus `git revert` of the `ACCEPT` merge.

## Scope of a delegation

A delegation covers only what the human asked for and what those sessions
report as deviations (`otr issue --origin issue-<n>/<hex> deviation`). It
never covers work the orchestrator derives on its own — from north pole
`GAP`s, from things noticed in passing, from "while we're here". Observed
in the source project: an orchestrator under delegation read the north
pole, decided to close its gaps, and drifted. Such ideas go in the final
report's **limits**, where the human can turn them into a need.

## Consequences

- Judgment does not move: the orchestrator's read of the diff before each
  delegated act is the same read it would narrate to the human, and the
  mechanical gates (lint, acceptance section, frozen-scope check) still run.
- A delegation never grants indefinite authority: `until` is required.
- What this does not solve: a drive that outlives the interactive session.
