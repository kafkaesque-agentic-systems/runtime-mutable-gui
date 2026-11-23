# Architecture (as built)

What exists in the repository today. The intended design is `design/ARCHITECTURE.md`; where
the two differ, the difference and its decision number are stated here.

## 1. What it is

A Cargo workspace (Rust 1.99.1, edition 2024) holding the foundation of mutable-gui: the core
library crate, the nice-plug adapter crate, a test kit, the reference CLAP plugin "Reference FX"
and the `cargo xtask` build helper. At the end of Phase 0 every crate is a skeleton: the core
exports only `LIBRARY_VERSION`, the adapter re-exports the core, and the reference plugin passes
audio through with no editor. None of the core modules of the design (model, documents,
parameters, taps, theme, rendering, perform, design, edit, library, custom kinds, generator,
persistence cell, editor) exists yet; `DEV_PLAN.md` adds them from Phase 1 on.

## 2. Components

| Component | Path | Responsibility | Depends on |
|---|---|---|---|
| Workspace | `Cargo.toml`, `Cargo.lock` | Members `crates/*`, `examples/*`, `xtask`; resolver 3; shared package fields (version 0.1.0, edition 2024, `rust-version = "1.95"`, MIT OR Apache-2.0, `publish = false`); every `design/STACK.md` crate pinned with `=` in `[workspace.dependencies]`; clippy `all` and `pedantic` warn, `unwrap_used`, `expect_used`, `panic`, `todo`, `unimplemented`, `dbg_macro`, `print_stdout`, `print_stderr` deny | — |
| Toolchain and style | `rust-toolchain.toml`, `rustfmt.toml`, `clippy.toml`, `.cargo/config.toml` | Rust 1.99.1 with rustfmt and clippy; edition 2024, line width 100; unwrap, expect and panic allowed in tests (D-49); the `cargo xtask` alias | — |
| Core | `crates/mutable-gui/` (library `mutable_gui`) | `LIBRARY_VERSION`; `#![forbid(unsafe_code)]` | egui (feature `default_fonts`), serde, serde_json, thiserror |
| Core: bundled assets | `crates/mutable-gui/assets/` | Inter 4.1 Regular and Medium, `OFL.txt`, `SHA256SUMS`; not yet loaded by code (Step 1.7) | — |
| Test kit | `crates/mutable-gui-testkit/` (library `mutable_gui_testkit`) | `ui_harness(size, app)` (egui_kittest harness at `pixels_per_point` 1.0), `snapshot_on_macos(harness, name)`; re-exports `egui_kittest`; a dev-dependency only | core, egui, egui_kittest (features `snapshot`, `wgpu`) |
| Adapter | `crates/mutable-gui-nice/` (library `mutable_gui_nice`) | Re-exports the core as `mutable_gui_nice::mutable_gui` | core, nice-plug, nice-plug-egui |
| Reference plugin | `examples/reference-plugin/` (package `mutable-gui-reference`, cdylib and lib) | `RefFx`: nice-plug `Plugin` and `ClapPlugin` ("Reference FX", vendor "mutable-gui", CLAP id `org.mutable-gui.reference`, 0.1.0), one stereo in/out layout, `RefParams` with `bypass` and `input_gain`, `type Editor = ()`, pass-through `process`, exported with `nice_export_clap!` | nice-plug |
| Build helper | `xtask/` | `cargo xtask bundle` and `bundle-universal` through `nice_plug_xtask::main()`; any other command is refused naming the two | nice-plug-xtask |
| Tools | `tools/` | `check-env.sh` (environment), `validate-clap.sh` (clap-validator gate), `fetch-inter.sh` (font download and checksums), `check-stack.py` (`design/STACK.md` against `Cargo.lock` and the pins) | python3, clap-validator, curl, unzip, shasum |
| Hooks and CI | `.githooks/pre-commit.project`, `.github/workflows/ci.yml` | fmt and clippy before every commit; CI jobs for macOS 14, Ubuntu 24.04 and Windows 2022 | — |

## 3. Main flow

1. `cargo xtask bundle mutable-gui-reference --release` → alias in `.cargo/config.toml` →
   `xtask/src/main.rs` → `nice_plug_xtask::main()` → release build of
   `examples/reference-plugin` → `target/bundled/mutable-gui-reference.clap`.
2. A host or clap-validator loads the bundle → `nice_export_clap!(RefFx)` in
   `examples/reference-plugin/src/lib.rs` → nice-plug's CLAP wrapper → `RefFx::process`, which
   leaves the buffer the host filled with the input untouched → audio passes through unchanged.
3. `cargo test --workspace` → integration tests in `crates/*/tests/` and
   `examples/reference-plugin/tests/` → harness tests through `crates/mutable-gui-testkit` →
   egui_kittest, whose wgpu renderer draws the snapshot pictures on macOS.

## 4. Invariants in force

- **I-05** `crates/mutable-gui` forbids unsafe code: `crates/mutable-gui/src/lib.rs` starts with
  `#![forbid(unsafe_code)]`, so the compiler refuses any `unsafe` in the core. The core does not
  depend on nice-plug, baseview or egui-baseview: `cargo tree -p mutable-gui -e normal --prefix none`
  lists none of them (checked by hand on 2026-11-23; no automated test yet).
- The other invariants (I-01 to I-04, I-06 to I-21) concern code that does not exist yet.

## 5. Differences from the design

- **`EditorState::frame` signature** (DEV_PLAN "Fixed names", D-48). egui 0.37 hands an
  application a top-level `Ui` (`Context::run_ui`), so the per-frame entry point becomes
  `EditorState::frame(&mut self, ui: &mut egui::Ui, params: &dyn ParamSource)` instead of
  `frame(&egui::Context)`; `ui.ctx()` is the context. `EditorState` itself arrives in Phase 1.
- **Test kit crate.** `crates/mutable-gui-testkit/` is not in the design's component table; it
  comes from DEV_PLAN "Fixed names" (D-48) and keeps egui_kittest and wgpu in tests only (D-46).
  It re-exports `egui_kittest` so tests reach `egui_kittest::kittest::Queryable` through this
  one dev-dependency.
- **egui's `default_fonts` feature.** egui 0.37's default feature set is empty. D-41's built-in
  fonts Hack and Ubuntu Light (and the emoji fonts of the fallback chain) come from this feature,
  and without it a harness cannot lay out any text. `design/STACK.md` records the feature.
- **Reference FX declares Input Gain in Phase 0.** DEV_PLAN Step 0.9 gives `RefParams` only
  `bypass`. With bypass as the only parameter, clap-validator 0.4.1's `param-set-events` and
  `param-set-no-cookies` tests fail ("After calling `clap_plugin_params::flush()`, the parameter
  values did not change"): their seeded random value for the two-state parameter equals its
  default. `input_gain` is declared as the plan's parameter table defines it (−24 to +24 dB,
  default 0 dB) and is not yet applied by `process`; Step 1.24 replaces `RefParams` with all 63
  parameters.
- **wgpu 30.0.2.** D-46 names wgpu 30.0.1 from a scratch build; this workspace's lockfile
  resolves 30.0.2, and `design/STACK.md` now says so.
