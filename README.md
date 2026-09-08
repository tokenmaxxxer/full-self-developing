# full-self-developing

On-the-record development with git as the only ledger. Adapted from
[tokenmaxxxer/on-the-record](https://github.com/tokenmaxxxer/on-the-record)
keeping two ideas — the git record system and delegation to subagents — and
dropping roles, skills, sandboxing, and GitHub as a state store.

## The loop

```
human   otr issue "<title>"            → docs/issue-<n>/issue.md on main   (requirement)
orch    otr directive <n> "<task>"     → prompt; orchestrator spawns a subagent with it
agent   phase 1: proposal record        → branch issue-<n>/<hex>, docs/issue-<n>/reports/<hex>.md (proposed)
human   otr approve <n> <hex>          → docs/issue-<n>/approvals/<hex>.md on main
orch    otr directive <n> --phase delivery --session <hex>  → spawn again
agent   phase 2: code + record          → same branch                        (loop_state: landed)
human   otr accept <n> <hex>           → merge --no-ff into main
   or   otr reject <n> <hex> "<why>"   → docs/issue-<n>/rejections/<hex>.md on main
```

`otr board` reads the state of every issue from what is merged on `main`.
`otr accept`/`reject` remove the session's worktree, branch and scratch; `otr clean [--all]`
sweeps leftovers of finished (or, with `--all`, crashed) sessions. Nothing is written
outside the repo.
The orchestrator is the interactive Claude Code session; its protocol is `CLAUDE.md`.

## Where each fact lives

| fact | location | written by |
|---|---|---|
| requirement | `docs/issue-<n>/issue.md` | human |
| work | branch `issue-<n>/<hex>`, worktree `runs/ws/`, scratch `runs/scratch/` | subagent |
| rationale + evidence | `docs/issue-<n>/reports/<hex>.md` | subagent (that one only) |
| approval | `docs/issue-<n>/approvals/<hex>.md` | human in `docs/specs/approvers.md` |
| acceptance | merge commit `ACCEPT issue-<n>/<hex>` | human |
| rejection | `docs/issue-<n>/rejections/<hex>.md` | human |
| design decisions | `docs/decisions/` | either, by PR |

## Invariants

1. Neither `otr` nor the orchestrator writes a record. They read state, delegate, and relay
   human decisions as commits.
2. A record is written by exactly one subagent — the one whose hex is in its filename.
   Correcting another's record is done with `supersedes:` / `amends:` in your own.
3. A subagent never lands, pushes, merges, or opens new work. Scope overflow goes under
   `## Deviations` in the record and the subagent stops.
4. Every claim in a record cites the command and output that produced it.
5. Judgment without a standard is `tools/record_lint.py` (run by the subagent before its
   last commit and by `otr accept`); judgment with a standard is the human's
   approve / accept / reject.

These hold by convention and by the directive text, not by sandboxing — the source
project's hooks and per-role environments were deliberately left out.

## Setup

`python3`, `git`. Put your git author email in
`docs/specs/approvers.md`. Alias: `alias otr='python3 tools/otr.py'`.
