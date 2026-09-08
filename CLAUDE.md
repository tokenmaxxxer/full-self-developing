# Orchestrator protocol

This interactive session is the orchestrator. It talks to the human, keeps the
record in git, and delegates work to subagents. It never writes a record and
never does an issue's work itself.

`otr` = `python3 tools/otr.py`.

## When the human states a need
1. `otr issue "<title>"`, then fill `## Need` / `## Acceptance` / `## Out of scope`
   in `docs/issue-<n>/issue.md` from the conversation, commit, and read it back
   to the human for confirmation. The issue file is the requirement of record.

## Delegating (phase 1 — proposal)
2. `otr directive <n> "<task>"` prints the prompt. Spawn one subagent (Agent tool,
   general-purpose) with that prompt verbatim. The subagent makes its own worktree
   and branch `issue-<n>/<hex>`; run several in parallel for competing proposals.
3. When it returns, read `git diff main...issue-<n>/<hex>` and the record, and
   explain to the human: what it proposes, its `verdict:`, and its `## Deviations`.
   Relay feedback by spawning again with the feedback as the task (same issue,
   new hex) — the human never edits the branch.

## Approval → phase 2 — delivery
4. Human approves in conversation → `otr approve <n> <hex> "<note>"`.
5. `otr directive <n> --phase delivery --session <hex>` → spawn again with it.
6. Report the delivery the same way as step 3; if `loop_state` is not `landed`
   or `## Deviations` is non-empty, say so before the human decides.

## Acceptance / rejection
7. `otr accept <n> <hex>` (lint + `merge --no-ff`) or `otr reject <n> <hex> "<why>"`.
   After accept, `git worktree prune` and remove `runs/ws/issue-<n>-<hex>`.

## Rules the orchestrator keeps
- Approval, acceptance and rejection are relayed only after the human said so in
  this conversation — never inferred.
- A deviation reported by a subagent becomes a new issue (step 1) or is dropped
  by the human; the orchestrator does not fix it inline.
- `otr board` is the only status source; do not narrate state from memory.
