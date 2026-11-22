# Testing

## 1. Categories

| Category | Where | Runs with |
|---|---|---|
| <<unit / integration / end to end / performance>> | `<<path>>` | `<<command>>` |

## 2. Commands

```sh
<<everything: the command the phase gate runs>>
<<one file or one test>>
```

## 3. Gates

Each plan step names a gate (`G1.1` …) in `DEV_PLAN.md`; the gate index there lists the
command for each. A red gate blocks its phase; it is never skipped or marked flaky.

## 4. Rules

- A behaviour change ships with its test in the same commit.
- A test asserts behaviour through a public interface, with expected values from the
  specification or the ticket, never recomputed by the code under test.
- The runner checks that each ticket's test fails when the implementation is removed.
- Fakes only at process boundaries: <<which ones>>.
- Randomness is seeded; no sleeps; no skipped tests.

## 5. Manual checks

| Check | When | Recorded in |
|---|---|---|
| <<what a person verifies by hand>> | <<phase>> | `docs/qa/<<file>>` |
