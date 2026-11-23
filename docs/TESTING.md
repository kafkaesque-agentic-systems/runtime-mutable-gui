# Testing

## 1. Categories

Phase 0 holds one real passing test in each category; later steps add tests beside them.

| Category | Where | Runs with |
|---|---|---|
| Unit (plain assertions on a public item) | `examples/reference-plugin/tests/process_smoke.rs`: `RefFx::process` passes a 64-frame stereo ramp through | `cargo test -p mutable-gui-reference --test process_smoke` |
| Harness interaction | `crates/mutable-gui/tests/harness_smoke.rs`: `click_counts` clicks a button found by its label | `cargo test -p mutable-gui --test harness_smoke` |
| Snapshot picture | `crates/mutable-gui/tests/harness_smoke.rs`: `smoke_picture` against `crates/mutable-gui/tests/snapshots/foundation-smoke.png` | `cargo test -p mutable-gui --test harness_smoke` |
| Property | `crates/mutable-gui/tests/prop_smoke.rs`: JSON round trip of any `(u32, String)`, 256 cases | `cargo test -p mutable-gui --test prop_smoke` |
| Allocation | `crates/mutable-gui/tests/alloc_smoke.rs` (files `alloc_*.rs`; debug builds only) | `cargo test -p mutable-gui --test alloc_smoke` |
| Timing | `crates/mutable-gui/tests/perf_smoke.rs` (tests `perf_*`; release builds only) | `cargo test --workspace --release perf_` |
| Benchmark (a report, not a gate) | `crates/mutable-gui/benches/smoke.rs` | `cargo bench -p mutable-gui --bench smoke` |
| Adapter | `crates/mutable-gui-nice/tests/smoke.rs` | `cargo test -p mutable-gui-nice --test smoke` |
| CLAP validation | `tools/validate-clap.sh` over the bundle | `cargo xtask bundle mutable-gui-reference --release && sh tools/validate-clap.sh` |

The command forms of `DEV_PLAN.md` "Test commands": a core integration test is
`cargo test -p mutable-gui --test <file stem>`, an adapter test
`cargo test -p mutable-gui-nice --test <file stem>`, a reference plugin test
`cargo test -p mutable-gui-reference --test <file stem>`, an xtask test
`cargo test -p xtask --test <file stem>` (none exists yet).

## 2. Commands

Everything the phase gate runs (`phase_gate` in `.devpipe/config.json`):

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
python3 tools/check-stack.py
```

The slower checks (`seam_gate` in `.devpipe/config.json`): timing bounds, bundle, CLAP validation:

```sh
cargo test --workspace --release perf_
cargo xtask bundle mutable-gui-reference --release
sh tools/validate-clap.sh
```

One file, then one test:

```sh
cargo test -p mutable-gui --test harness_smoke
cargo test -p mutable-gui --test harness_smoke click_counts
```

### Snapshot pictures

Assertions go through `mutable_gui_testkit::snapshot_on_macos(&mut harness, name)`, which
compares on macOS and returns without rendering elsewhere (D-46); harnesses come from
`mutable_gui_testkit::ui_harness(size, app)` at `pixels_per_point` 1.0. A new snapshot is
written once, then checked:

```sh
UPDATE_SNAPSHOTS=1 cargo test -p mutable-gui --test harness_smoke
cargo test -p mutable-gui --test harness_smoke
```

Look at the written PNG in `tests/snapshots/` of the crate, then commit it. A mismatch fails the
test and leaves `<name>.new.png` and `<name>.diff.png` beside the snapshot; git ignores them.

### Timing and allocation tests

- A timing test is named `perf_*` and carries
  `#[cfg_attr(debug_assertions, ignore = "timing bound; run with --release")]`; it runs only in
  `cargo test --workspace --release perf_`.
- An allocation test lives in a file named `alloc_*.rs` that starts with
  `#![cfg(debug_assertions)]` (the checker exists only in debug builds), installs
  `#[global_allocator] static A: nice_assert_no_alloc::AllocDisabler = nice_assert_no_alloc::AllocDisabler;`,
  runs the code under `assert_no_alloc` and asserts `nice_assert_no_alloc::violation_count() == 0`.
  The workspace enables the checker's `warn_debug` feature, so a violation is counted, not fatal.

## 3. Gates

Each plan step names a gate (`G1.1` …) in `DEV_PLAN.md`; the gate index there lists the
command for each. A red gate blocks its phase; it is never skipped or marked flaky.

To add a project-wide gate:

1. Add its command to `phase_gate` in `.devpipe/config.json` (or `seam_gate` for a slow one). It
   must run its tests on every call, never reuse an earlier result. That file is local and not
   in git, so also add the command to section 2 of this document.
2. Add the same command to the macOS job of `.github/workflows/ci.yml`.
3. If it takes seconds, also add it to `.githooks/pre-commit.project`, which stops at the first
   failing command.
4. Prove it: break the thing it checks once, see it exit non-zero, undo the break.

`python3 tools/check-stack.py` accepts a `design/STACK.md` crate row when its version is in
`Cargo.lock`, or, for a crate no member uses yet, when it equals the `=` pin in
`[workspace.dependencies]`; a workspace dependency without a row is a mismatch.

## 4. Rules

- A behaviour change ships with its test in the same commit.
- A test asserts behaviour through a public interface, with expected values from the
  specification or the ticket, never recomputed by the code under test.
- The runner checks that each ticket's test fails when the implementation is removed.
- Tests may `unwrap`, `expect` and `panic` (D-49, `clippy.toml`); library code may not.
- Fakes only at process boundaries: `FakeParamSource` (the plugin's parameters; testkit,
  Step 1.4), `RecordingGuiContext` (nice-plug's GUI context; testkit feature `nice`, Step 1.21),
  `FakeFileDialog` (system file dialogs; testkit, Step 8.6), `Storage` over a temporary
  directory (the file system; `tempfile`, Step 8.1), and clipboard events fed to the harness.
  None of them exists yet.
- Randomness is seeded; no sleeps; no skipped tests.

## 5. Manual checks

| Check | When | Recorded in |
|---|---|---|
| Copying the bundle to `~/Library/Audio/Plug-Ins/CLAP/` makes "Reference FX" appear in Bitwig Studio 5.3.13, where it passes audio unchanged | Phase 0 exit demo | the owner's sign-off of Phase 0 (Phase 0 has no check-sheet step) |
| Phase 1 host and screen check | Phase 1 (Step 1.30) | `docs/qa/phase-01.md` |
