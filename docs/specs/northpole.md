# North pole

What the human has decided for this repository. Five sections, each holding
only the human's own words: which problem, what to watch for, which
constraints, which priorities, and what must come first. How to solve it,
in what detail, with what design — that is the agents' work, proposed in
issues and records and cut by the human against what is written here.

This file is a standard for judging work, never a source of work. It is
edited in place when the human's thinking changes; history is
`git log -p docs/specs/northpole.md`. Each section carries `since` (first
stated) and `revised` (last changed).

## Problem

A stated need is driven to a verified, landed, legibly reported result
without the human in the loop for anything but judgment that needs their
standard. Once development is delegated, the human's working hours go to
deciding — which problem, what to watch for, constraints, priorities,
what must come first — and reading the result the next morning. The
plugin must make that deciding short and that reading fast: the human
writes criteria, agents find methods, solve, optimise, and hand back
work the human can cut, accept, or revert one unit at a time.

- since 2026-09-08 · revised 2026-09-09 (was "full self-developing" + N5; now states the human's job as criteria, not design)

## Watch for

- Agents adding what was not asked for: tests, CI/CD, deployment,
  abstraction, configurability, "improvements". Anything the issue's
  Problem does not require is a Deviation to record, not a deliverable.
- The evidence requirement turning into over-verification. Evidence is
  the minimal command that confirms one Acceptance item, not a test suite.
- A tool remembering state on its own. `otr board` and GitHub are the only
  state; nothing cached locally decides anything.
- The human being asked to write the same thing twice (in the north pole
  and again as a delegation option, in an issue and again in a plan).
- Plausible claims of serving a priority. An agent saying "this serves
  Priorities #1" is a claim to be cut against, not evidence.
- An orchestrator inventing work from gaps, "while we're here", or its own
  reading of this file.

- since 2026-09-09 · revised 2026-09-09

## Constraints

Project-level constraints are the frozen decisions in `docs/decisions/`;
a change that touches one must reaffirm it or stop. In addition:

- GitHub is the whole record and the orchestrator is its only writer
  (`github-ledger`).
- Work is delegated to subagents on their own branch; judgment stays with
  the human at fixed gates (`no-roles-skills-or-isolation`).
- A round leaves no residue outside `runs/` (`no-residue`).
- The repository states its own direction in this file and in decisions
  (`repo-states-direction`).
- The drive runs inside one interactive session that the human leaves
  running; nothing resumes it if that session ends. Accepted, not a gap.

- since 2026-09-08 · revised 2026-09-09 (N1–N4 folded here and into decisions; single-session drive accepted)

## Priorities

When two goods conflict, the higher wins:

1. Completeness of the record — what is not on GitHub did not happen.
2. The human can revert any delegated act, one unit at a time.
3. The smallest change that solves the stated problem, over completeness,
   generality, or future-proofing.
4. The human's judgment is recorded as applied, not only the result: how a
   method was chosen, what was rejected and why.
5. Speed of the drive.

- since 2026-09-09 · revised 2026-09-09

## Must first

Before anything else is worth accepting:

- Every act taken under delegation is on GitHub in a form the human can
  revert with one command and one comment.
- An agent's proposal names the smallest change and, if it chose another,
  says why.

- since 2026-09-09 · revised 2026-09-09
