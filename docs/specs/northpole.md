# North pole

What this repository is for, as currently understood. This is a managed
document, not a log: when the human's thinking changes or sharpens, the
entry is edited in place, merged with a neighbour, or removed. History is
`git log -p docs/specs/northpole.md`; the file only ever states the present.

Each entry: one sentence of intent, `since` (first stated) and `revised`
(last changed), and what currently serves it — or `GAP`.

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
(confirm issue, approve proposal, accept or reject delivery). Nothing
else from the source project — roles, skills, sandboxing, hooks — is
carried over.

- since 2026-09-08 · revised 2026-09-08
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
