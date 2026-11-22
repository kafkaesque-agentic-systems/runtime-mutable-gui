# Development plan: <<project name>>

Built from `design/`. Phases run in order; a phase closes when every gate under it is green
and its exit demo has been performed. Every step names its files, libraries, commands, tests
and gate: nothing is left for the executing agent to choose. Libraries come from
`design/STACK.md` only.

## Phase 0 — Foundation

**Goal:** <<the repository builds, tests and lints from a clean clone; every later phase only adds to it>>

### Step 0.1 — <<title>>

- Files: `<<path>>`, `<<path>>`
- Libraries: <<names from STACK.md, or none>>
- Commands: `<<exact command>>`
- Tests: `<<test file or suite>>`, or none
- Gate: G0.1 — `<<command>>` exits 0
- Requirements: none

**Exit demo:** <<what a person can do once the phase is closed, following README and RUNBOOK only>>

## Phase 1 — <<name>>

**Goal:** <<one sentence>>

### Step 1.1 — <<title>>

- Files: `<<path>>`
- Libraries: <<names from STACK.md, or none>>
- Commands: `<<exact command>>`
- Tests: `<<test file>>`
- Gate: G1.1 — `<<command>>` exits 0
- Requirements: R-001
- Screens: <<S-01, or none>>

**Exit demo:** <<observable result>>

## Gate index

| Gate | Phase | Command |
|---|---|---|
| G0.1 | 0 | `<<command>>` |
