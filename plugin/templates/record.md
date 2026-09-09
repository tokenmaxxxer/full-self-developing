---
issue: <n>
author: <8hex>          # session id; written once, never changed
type: proposal          # proposal | implementation | verification | repair
loop_state: proposed    # proposed | approved | landed | done
verifies_subject: false
code_under_review: []
verdict: <one paragraph; every claim cites a command and its output below>
upstream: []            # [{path: <record or file>, sha: <commit>}]
---

# issue-<n> — <8hex> record

## What was done

## Evidence

<command → output pairs. A claim without one is a claim, not a fact.>

## What did not work

## Principles

<For each frozen decision in docs/decisions/ whose scope your diff or this record
touches: `reaffirms <id>` — one per line. Write `none touched` otherwise.>

## Judgment

<Methods considered, one line each, the smallest marked `(smallest)`; the one chosen;
why, naming the Priority or Watch for item that decided it. `none` if there was only
one method to choose from.>

## Acceptance

<Proposal record: propose it here, or, if the issue already has one, keep or refine it
and say which — required non-empty on a proposal record. Delivery record: leave as
carried over, or note the issue's Acceptance was left unchanged.>

## Out of scope

<Same as ## Acceptance above. May be empty — a proposal need not exclude anything.>

## Deviations

<Anything outside the issue's scope that came up. Recorded, not fixed.>

## Acceptance verification

<Required when loop_state is landed/done: each acceptance item from
issue.md, with the command that demonstrates it.>

## Next steps
