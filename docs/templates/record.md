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

## Deviations

<Anything outside the issue's scope that came up. Recorded, not fixed.>

## Acceptance verification

<Required when loop_state is landed/done: each acceptance item from
issue.md, with the command that demonstrates it.>

## Next steps
