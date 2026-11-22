---
id: P01-T01
title: <<the behaviour, in a few words>>
plan_ref: "Phase 1, step 1.1"
requirement: R-001
mode: afk            # afk = the runner does it | hitl = the owner does it
host: any            # any | linux | mac
blocked_by: []
status: todo
read:
  - {path: <<file the engineer must open>>, lines: "1-80"}
  - {path: design/ARCHITECTURE.md, section: "I-01"}
writes: [<<the one source file>>]
tests: [<<the one test file>>]
verify: "<<command that exits 0 only when this ticket works>>"
red_check: true
---
## Behaviour

<<One paragraph: what is true after this ticket that was not true before.>>

## Acceptance

- [ ] <<observable result, with concrete values a test can assert>>

## Out of scope

- <<the adjacent thing this ticket must not do>>
