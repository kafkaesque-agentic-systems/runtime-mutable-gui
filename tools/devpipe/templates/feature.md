---
id: {{id}}
title: "{{title}}"
status: PROPOSED     # PROPOSED | ACCEPTED | DONE | DROPPED
placement: none      # none | now | later | rework
requirements: []     # requirements this feature adds, e.g. [R-014]
changes: []          # existing requirements whose text it changes
serves: []           # for a change with no new behaviour: the requirement it serves
touches: []          # source files it creates or modifies
steps: []            # plan steps added for it, e.g. ["2.7", "2.8"]
---
## Idea

{{idea}}

## Behaviour

<<What a user can observe once this exists that they cannot observe today. One paragraph.>>

## Acceptance

- <<a result with concrete values that a test can assert>>

## Out of scope

- <<the adjacent thing this feature will not do>>

## Invariants

{{invariants}}

## Rework

<<One line per ticket the impact report lists as citing a changed requirement: "- P01-T03: reworked in step 2.7" or "- P01-T03: no change needed, because …". Write "None." when the report lists none.>>

## Placement

<<now, later or rework; the phase; and the reason, taken from the impact report.>>
