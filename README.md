# full-self-developing

On-the-record development with git as the only ledger. Adapted from
[tokenmaxxxer/on-the-record](https://github.com/tokenmaxxxer/on-the-record)
with the role axis, the skill axis, and GitHub as a state store removed.

## The loop

```
human   otr issue "<title>"            → docs/issue-<n>/issue.md on main   (requirement)
human   otr spawn <n> "<task>"         → branch issue-<n>/<hex>, headless session
session phase 1: proposal record        → docs/issue-<n>/reports/<hex>.md   (loop_state: proposed)
human   otr approve <n> <hex>          → docs/issue-<n>/approvals/<hex>.md on main
human   otr spawn <n> --phase delivery --session <hex>
session phase 2: code + record          → same branch                        (loop_state: landed)
human   otr accept <n> <hex>           → merge --no-ff into main
   or   otr reject <n> <hex> "<why>"   → docs/issue-<n>/rejections/<hex>.md on main
```

`otr board` reads the state of every issue from what is merged on `main`.

## Where each fact lives

| fact | location | written by |
|---|---|---|
| requirement | `docs/issue-<n>/issue.md` | human |
| work | branch `issue-<n>/<hex>`, worktree `runs/ws/` | session |
| rationale + evidence | `docs/issue-<n>/reports/<hex>.md` | session (that one only) |
| approval | `docs/issue-<n>/approvals/<hex>.md` | human in `docs/specs/approvers.md` |
| acceptance | merge commit `ACCEPT issue-<n>/<hex>` | human |
| rejection | `docs/issue-<n>/rejections/<hex>.md` | human |
| design decisions | `docs/decisions/` | either, by PR |

## Invariants

1. `otr` never writes a record. It reads state, spawns, and relays human decisions as commits.
2. A record is written by exactly one session — the one whose hex is in its filename.
   Correcting another's record is done with `supersedes:` / `amends:` in your own.
3. A session never lands, pushes, merges, or opens new work. Scope overflow goes under
   `## Deviations` in the record and the session stops.
4. Every claim in a record cites the command and output that produced it.
5. Judgment without a standard is a gate (`tools/record_lint.py`, hooks in `tools/hooks/`);
   judgment with a standard is the human's approve / accept / reject.

## Gates on a spawned session

- `record_guard.py` (Write/Edit) — only its own record; never approvals or approvers.
- `git_guard.py` (Bash) — no push, merge, checkout main, branch delete, history rewrite.
- `stop_gate.py` (Stop) — refuses to end while the record fails lint or the tree is dirty.
- `record_lint.py` — frontmatter enums, author/path match, no placeholders, evidence
  section non-empty, acceptance verification on terminal records.

## Setup

`python3`, `git`, `claude` on PATH. Put your git author email in
`docs/specs/approvers.md`. Alias: `alias otr='python3 tools/otr.py'`.
