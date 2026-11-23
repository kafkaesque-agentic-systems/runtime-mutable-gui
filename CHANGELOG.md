# Changelog

Format: Keep a Changelog. Every user-visible change goes under *Unreleased* in the commit that makes it.

## Unreleased

### Added

- Cargo workspace on Rust 1.99.1 (`rust-toolchain.toml`) with every dependency of
  `design/STACK.md` pinned exactly and `Cargo.lock` committed; clippy `all` and `pedantic` as
  warnings, `unwrap`, `expect`, `panic`, `todo`, `unimplemented`, `dbg!`, `print!` and `eprint!`
  denied outside tests.
- Core crate `mutable-gui` with `LIBRARY_VERSION` and `#![forbid(unsafe_code)]`; the Inter 4.1
  font (Regular, Medium, SIL OFL 1.1) bundled in `crates/mutable-gui/assets/`.
- Adapter crate `mutable-gui-nice` re-exporting the core.
- Test kit `mutable-gui-testkit` with `ui_harness` and `snapshot_on_macos`, and one passing
  test in each category: harness interaction, snapshot picture, property, allocation,
  timing, benchmark, adapter, reference plugin processing, CLAP validation.
- Reference FX (`examples/reference-plugin`, CLAP id `org.mutable-gui.reference`): a stereo
  pass-through with Bypass and Input Gain parameters and no editor, bundled with
  `cargo xtask bundle mutable-gui-reference --release` and passing clap-validator 0.4.1.
- Tools: `tools/check-env.sh`, `tools/validate-clap.sh`, `tools/fetch-inter.sh`,
  `tools/check-stack.py`, `setup-prerequisites.sh`; the `pre-commit.project` hook; the CI
  workflow for macOS, Linux and Windows.
