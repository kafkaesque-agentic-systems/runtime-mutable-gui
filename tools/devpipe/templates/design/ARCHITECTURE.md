# Architecture (as designed): <<project name>>

This is the intended design. `docs/ARCHITECTURE.md` describes what was built.

## Components

| Component | Path | Responsibility |
|---|---|---|
| <<name>> | `<<path>>` | <<one line>> |

## Boundaries

- <<which component may call which; what is never imported where; process and thread ownership>>

## Data flow

1. <<input>> → <<component>> → <<component>> → <<output or storage>>

## Invariants

- **I-01** <<a property the code must never break, stated so a reviewer can check it>>

## Test seams

- <<the public boundary each kind of test goes through, and what is faked there>>
