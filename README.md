# full-self-developing

Drive a stated need to a landed, recorded result. GitHub is the ledger, the
orchestrator is its only writer, subagents do the work, the human supervises.
Adapted from [tokenmaxxxer/on-the-record](https://github.com/tokenmaxxxer/on-the-record),
keeping two ideas — the GitHub record system and delegation to subagents — and
dropping roles, skills, sandboxing, and hooks.

## The loop

```
human   states a need                    orch  otr issue           → GitHub issue #n
orch    otr directive n "<task>"         → prompt; Agent tool spawns a subagent (sonnet)
agent   phase 1: proposal record         → local branch issue-n/<hex>, docs/issue-n/reports/<hex>.md
orch    reads it, otr publish n <hex>    → push + PR
human   approves                         orch  otr approve         → comment APPROVE issue-n/<hex>
orch    otr directive n --phase delivery --session <hex> → same agent continues
agent   phase 2: code + record (landed)  → same branch, local
orch    reads it, otr publish            → PR updated
human   accepts / rejects                orch  otr accept / reject → PR merged + issue closed / PR closed
```

With a live delegation (`otr delegate --until +8h` → a `DELEGATE … UNTIL …` comment on
the pinned `delegation` issue) the orchestrator runs the loop on its own — approving,
accepting, turning deviations into follow-up issues — and reports at the end; each
delegated act is a comment or merge marked `VIA DELEGATION`. `otr revoke` or expiry
ends it. That drive is what the repository is for (`docs/specs/northpole.md` N0).

`otr board` reads state from GitHub (open issues, PRs, approvals) plus each branch's record.

## Where each fact lives

| fact | location | written by |
|---|---|---|
| requirement | GitHub issue #n | orchestrator, on the human's word |
| work | branch `issue-<n>/<hex>` in a local worktree `runs/ws/` | subagent |
| rationale + evidence | `docs/issue-<n>/reports/<hex>.md` on that branch | subagent (that one only) |
| publication | push + PR | orchestrator, after reading |
| approval | issue comment `APPROVE issue-<n>/<hex>` by a login in `docs/specs/approvers.md` | orchestrator, on the human's word |
| acceptance / rejection | PR merged + issue closed / PR closed with reason | orchestrator, on the human's word |
| delegation | `DELEGATE <issues|all> UNTIL <iso>` / `REVOKE` on the `delegation` issue | orchestrator, on the human's word |
| what the repo is for | `docs/specs/northpole.md` — current intent, edited in place | orchestrator, on the human's word |
| principles | `docs/decisions/*.md` with `status: frozen` + scope | human |
| other decisions | `docs/decisions/*.md` `active` / `superseded` | either |

## Invariants

1. Neither `otr` nor the orchestrator writes a record. They read state, delegate, and relay
   human decisions to GitHub.
2. Subagents never touch GitHub. They commit locally; `otr publish` is the only push, and it
   happens after the orchestrator has read the branch.
3. A record is written by exactly one subagent — the one whose hex is in its filename.
   Correcting another's record is done with `supersedes:` / `amends:` in your own.
4. A subagent never lands, merges, or opens new work. Scope overflow goes under
   `## Deviations` in the record and the subagent stops.
5. Every claim in a record cites the command and output that produced it.
6. Judgment without a standard is `tools/record_lint.py` and the frozen-scope check in
   `otr accept` (`tools/decisions.py`); judgment with a standard is the human's
   approve / accept / reject.
7. A frozen decision is touched only with `reaffirms <id>` in the record, or it is a
   deviation and the subagent stops. Unfreezing is a human's superseding decision.

These hold by convention and by the directive text, not by sandboxing.

## Setup

`python3`, `git`, `gh` (logged in) on PATH. The repo is whatever `origin` points at.
Install as a plugin: `claude plugin marketplace add <this repo path or GitHub>` then
`claude plugin install full-self-developing@full-self-developing`. In a new target repo run
`otr init` once (approvers = your GitHub login, decisions README, empty north pole).
