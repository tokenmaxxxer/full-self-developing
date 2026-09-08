---
id: git-only-ledger
status: superseded
scope:
  globs: ["plugin/tools/otr.py", "docs/specs/**", "plugin/templates/**"]
  keywords: ["github issue", "pull request", "label", "gh api", "gh pr", "gh issue"]
---

# Git is the only ledger — superseded by `github-ledger` (same day)

Superseded: the human had said "GitHub", not "git". Kept as the cause of death.

Date: 2026-09-08.

## Decision

Requirement, approval, acceptance and rejection are all commits on `main`;
work and its record are commits on `issue-<n>/<hex>`. No GitHub issue,
PR comment, or label carries state.

## Why

The source project moved its board in-repo after a label state machine on
GitHub created a second source of truth (protocol.md §2, "a false quiet is
the failure mode being avoided"). The three remaining GitHub-held facts —
issue body, `APPROVE` comment, merge — have exact git equivalents: a file
on `main`, a commit by an approver, a `--no-ff` merge commit. Keeping them
in git means `git log` alone reconstructs the whole history, offline, with
no account.

## Consequences

- Approval authenticity rests on `git config user.email` matching
  `docs/specs/approvers.md`. Adequate for a single operator; a multi-party
  setup would add signed commits.
- Roles and skills are gone: a session is `issue + hex`, and what it does is
  the task text. Methodology is not injected.
