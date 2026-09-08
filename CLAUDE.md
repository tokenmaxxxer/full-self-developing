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
   Both remove the worktree, branch, and scratch dir. If a subagent died mid-run,
   `otr clean --all` removes what it left; plain `otr clean` only touches finished sessions.

## Direction of record
- `docs/specs/northpole.md` states what the repo is for *as currently understood*. It is
  managed, not appended: when the human states, changes, or sharpens a direction, edit
  the matching entry in place (bump `revised`), merge entries that now say one thing, or
  remove one that no longer holds — and say in the commit message what changed and why.
  Add a new `## N<k>` only for a genuinely new intent. Read the current file before
  editing; never reconstruct it from memory of the conversation.
- A principle the human settles becomes `docs/decisions/<date>-<slug>.md` with
  `status: frozen` and a scope. Only the human unfreezes it (new superseding decision).
- Before accepting, `otr accept` checks every frozen decision the diff touches has a
  `reaffirms <id>` line; the orchestrator still reads the diff and says whether it
  actually honours the principle — the check is mechanical, the judgment is not.

## Drive (full self-developing)
The default mode once the human has granted a delegation (`otr delegation` says
`live`). The loop above runs without a human turn:

1. Confirm: the human's stated need becomes an issue; read it back once, then go.
2. Proposal returns → read the diff and record yourself. If the record lints, the
   proposal covers every acceptance item, and `## Deviations` is empty or only names
   follow-ups → `otr approve <n> <hex> --via delegation` and spawn delivery, same turn.
3. Delivery returns → same read. If `loop_state: landed`, acceptance verification cites
   real commands, and `otr accept <n> <hex> --via delegation` passes its gates → accepted.
4. Every `## Deviations` entry that is real work becomes `otr issue "<title>" --origin
   "issue-<n>/<hex> deviation"` and is driven the same way. Nothing is handed back.
5. Rejected or failed delivery → `otr reject` with the reason, then spawn a new session
   on the same issue with the reason as the task. Third failure on one issue → stop.

Stop and ask the human only when: `otr accept` refuses on a frozen principle; the
delegation does not cover the issue or has expired; an issue has failed three sessions;
or the change needs a standard only the human holds (product taste, spend, outward
effect). Say which of these it is.

When the drive ends (all issues done, or a stop), report in four parts:
**problem** each issue solved · **result** what landed (`otr board`) · **changed** the
diff in one paragraph per issue · **limits** what remains, including open follow-ups
and every `--via delegation` act taken, so the human can revert any of them
(`REJECT` commit + `git revert` of the `ACCEPT` merge).

Without a live delegation, stop at each gate as before.

## Rules the orchestrator keeps
- Approval, acceptance and rejection are relayed only after the human said so in
  this conversation, or under a live delegation (`--via delegation`, which lands as
  its own commit naming the grant) — never inferred from tone.
- A deviation reported by a subagent becomes a new issue (step 1) or is dropped
  by the human; the orchestrator does not fix it inline.
- `otr board` is the only status source; do not narrate state from memory.
- Nothing of a round lives outside the repo: worktrees in `runs/ws/`, subagent scratch in
  `runs/scratch/` (the directive forbids /tmp and $HOME), both git-ignored and removed on
  accept/reject/clean.
