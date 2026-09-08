# North pole

What this repository is for, as currently understood. N0 is the
destination; the others are what makes it reachable. This is a managed
document, not a log: when the human's thinking changes or sharpens, the
entry is edited in place, merged with a neighbour, or removed. History is
`git log -p docs/specs/northpole.md`; the file only ever states the present.

Each entry: one sentence of intent, `since` (first stated) and `revised`
(last changed), and what currently serves it — or `GAP`.

## N0 — Full self-developing

The point of the repository, and its name: a stated need is driven to a
verified, landed, legibly reported result without the human in the loop
for anything but judgment that needs their standard. Mid-course problems
are solved by delegating again, not handed back; every turn of that
drive is on the record. The human supervises — sets the destination,
can take the wheel at any time, and is shown the route afterwards — but
does not steer.

- since 2026-09-08 · revised 2026-09-08
- served by: N1–N4 are the preconditions; the drive itself is `GAP` —
  today the orchestrator stops at every gate (confirm, approve, accept)
  and waits for a human turn

## N1 — Git is the whole record

Everything a future session or person needs is in the repository:
requirement, work, rationale with evidence, approval, acceptance,
rejection, and the repo's own direction. Nothing of record lives in a
chat, a GitHub issue, or a label.

- since 2026-09-08 · revised 2026-09-08
- served by: `docs/issue-<n>/`, `docs/decisions/`, this file; decision `git-only-ledger`

## N2 — Work is delegated to subagents, judgment stays with the human

The interactive session orchestrates; subagents do the work on their own
branch and hand back a record; the human decides at fixed points
(confirm issue, approve proposal, accept or reject delivery). A subagent
gets a task and the shared environment, nothing more: no role, no
mounted skill set, no per-session sandbox or hooks. Whatever tools or
skills already exist in the environment, it uses at its own discretion.

- since 2026-09-08 · revised 2026-09-08 (subagents pick their own means; nothing is prescribed per session)
- served by: `tools/otr.py directive`, `CLAUDE.md`; decision `no-roles-skills-or-isolation`

## N3 — A round leaves no residue

Everything a session creates lives under `runs/` inside the repo and is
removed on accept, reject, or `otr clean`; nothing is written to `/tmp`
or `$HOME`.

- since 2026-09-08 · revised 2026-09-08
- served by: directive scratch rule, `otr accept/reject/clean`

## N4 — The repo states its own direction

This file says what the repo is for; frozen decisions say which
principles a change may not silently cross. Both are kept current by
editing, so a reader gets today's intent, not a history to reconstruct.

- since 2026-09-08 · revised 2026-09-08
- served by: this file, `docs/decisions/` (`status: frozen`), `otr accept` principle check
