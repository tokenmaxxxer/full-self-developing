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
does not steer. The destination is only what the human said: this file
constrains how the car drives, it is not a map of places to go. Gaps here
are reported, never self-assigned.

- since 2026-09-08 · revised 2026-09-09 (the drive living inside one interactive session is accepted, not a gap: the human keeps the machine on across off-hours)
- served by: `DELEGATE … UNTIL …` comment on the `delegation` issue,
  `otr approve/accept --via delegation`, `otr issue --origin` for deviations,
  the Drive section of `CLAUDE.md`. The drive runs inside one interactive
  session that the human leaves running; nothing resumes it if that
  session ends mid-round, and that is the accepted operating mode.

## N1 — GitHub is the whole record

Everything a future session or person needs is on GitHub: the
requirement (issue), the work (PR), the rationale with evidence (record
in the PR), approval (comment), acceptance (merge), rejection (close),
delegation (comment), and the repo's own direction (this file and
`docs/decisions/`). Nothing of record lives only in a chat or on one
machine, and the orchestrator is GitHub's only writer.

- since 2026-09-08 · revised 2026-09-08 (was "git is the whole record" — a misreading; the human said GitHub)
- served by: `plugin/tools/otr.py`, `docs/issue-<n>/reports/`, `docs/decisions/`, this file; decision `github-ledger`

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

## N5 — The human's working hours go to setting the destination, and that work is assisted

Once work is delegated, what the human does during the day is decide
what the agent will do through the night: which needs, in what order,
with what acceptance, how far it may go and when it must stop, and how
the result is read the next morning. The plugin supports that planning
work as a first-class activity, not only the one-need-at-a-time
conversation: a rough brief becomes a reviewed batch of issues; the
delegation carries the plan (order, stop conditions, limits); the
end-of-drive report lands on GitHub, not only in the chat.

- since 2026-09-09 · revised 2026-09-09
- served by: `GAP` — `otr issue` takes one need at a time; `otr delegate`
  takes only issues and an expiry; the drive report exists only in the session
