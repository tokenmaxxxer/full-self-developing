---
id: evidence-per-acceptance-item
status: frozen
scope:
  globs: ["plugin/templates/record.md", "plugin/tools/record_lint.py", "plugin/tools/otr.py"]
  keywords: ["evidence", "acceptance verification", "all tests pass", "test run"]
---

# Evidence is one minimal check per Acceptance item

Date: 2026-09-09.

## Decision

Every Acceptance item is verified by the minimal command that confirms it,
cited with its output. The evidence rule exists to make "done" externally
checkable, not to reward volume: a record is not stronger for more tests
run, and running checks beyond what the items need is itself a Deviation
under `minimal-change`.

## Why

The directive's "bare counts are not evidence" is right, but read alone it
pushes agents toward writing and running more tests to manufacture
evidence. Practitioners who ran agents overnight converged on "one
machine-checkable condition per task", not "more tests".
