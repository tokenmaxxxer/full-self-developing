---
id: github-ledger
status: frozen
scope:
  globs: ["plugin/tools/otr.py", "docs/specs/**", "plugin/templates/**", "CLAUDE.md", "plugin/commands/run.md"]
  keywords: ["local-only", "offline ledger", "approvals/", "rejections/", "issue.md"]
---

# GitHub is the ledger; the orchestrator is its only writer

Date: 2026-09-08. Supersedes `git-only-ledger`.

## Decision

Requirement = GitHub issue. Work = PR from `issue-<n>/<hex>`. Rationale =
the record file inside that PR. Approval = issue comment
`APPROVE issue-<n>/<hex>` by a login in `docs/specs/approvers.md`.
Acceptance = merge; rejection = close with reason. Delegation =
`DELEGATE … UNTIL …` / `REVOKE` comments on the pinned `delegation` issue.

Subagents never talk to GitHub. They commit on a local branch; the
orchestrator reads the branch and `otr publish`es it. Every GitHub write
goes through `otr`, run by the orchestrator on the human's word.

## Why

The human's direction (northpole N1) is that the record lives on GitHub —
the same shape as the source project. Routing every write through the
orchestrator, rather than letting subagents open PRs as the source did,
keeps unread work off the remote (this repo is public), needs no second
account, and leaves subagents with no network or credential surface.

## Consequences

- The board needs the network; offline there is no state.
- With one GitHub account, "an actor cannot approve its own change" holds
  by provenance (which conversation the comment relays), not by identity.
- Records are still files, so `git log` on `main` remains a full local
  history of what landed — only decisions and requirements live solely on
  GitHub.
