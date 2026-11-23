# mutable-gui

mutable-gui is a Rust library that gives any nice-plug CLAP plugin an interface the user can
rebuild, rebind and restyle inside the DAW while audio runs, saved with the project and
shareable as a file, so the developer ships only DSP, a parameter tree and a default. It is for
Rust developers writing CLAP plugins with [nice-plug](https://codeberg.org/RustAudio/nice-plug),
and for the musicians who use those plugins.

Today the repository is at the end of Phase 0 (foundation): the workspace builds, lints and
tests, and the reference plugin "Reference FX" is a pass-through skeleton with no editor. The
library itself has no features yet; `DEV_PLAN.md` lists the phases that add them.

## Quick start

On an Apple silicon Mac with macOS:

```sh
git clone git@github.com:kafkaesque-agentic-systems/runtime-mutable-gui.git
cd runtime-mutable-gui
sh tools/check-env.sh
python3 tools/devpipe/run.py doctor
cargo test --workspace
cargo xtask bundle mutable-gui-reference --release
sh tools/validate-clap.sh
```

- `sh tools/check-env.sh` prints nothing and exits 0 when the Mac has the pinned toolchain and
  clap-validator 0.4.1; each line it prints names what is missing. `docs/RUNBOOK.md` section 1
  says how to install each.
- `python3 tools/devpipe/run.py doctor` turns on the repository's git hooks (formatting and
  clippy before every commit) and creates the pipeline's working folders. In a fresh clone it
  also writes a default `.devpipe/config.json` with no gates (see the repository map).
- `cargo test --workspace` runs every test except the timing bounds, which run with
  `cargo test --workspace --release perf_`.
- The bundle lands in `target/bundled/mutable-gui-reference.clap`; `sh tools/validate-clap.sh`
  runs clap-validator over it and exits 0 when no conformance test failed.

## Repository map

| Path | What lives there |
|---|---|
| `design/` | the specification, intended architecture, decisions, glossary, pinned stack, interface design (`design/ui/` mockups) |
| `DEV_PLAN.md` | phases, steps and gates |
| `.tickets/` | one file per ticket; `status:` is the record of progress (created by the pipeline) |
| `docs/` | as-built architecture, runbook, testing guide; later the ledger, review briefs and check sheets |
| `tools/devpipe/` | the vendored pipeline toolkit (`python3 tools/devpipe/run.py --help`) |
| `crates/mutable-gui/` | the core library (`mutable_gui`): toolkit-level, no plugin-framework code, `#![forbid(unsafe_code)]`; its bundled Inter font in `assets/`, its tests, snapshots and benchmarks |
| `crates/mutable-gui-nice/` | the nice-plug adapter (`mutable_gui_nice`): the only crate that uses nice-plug |
| `crates/mutable-gui-testkit/` | fakes and harness helpers for tests (`ui_harness`, `snapshot_on_macos`); a dev-dependency only, never published |
| `examples/reference-plugin/` | Reference FX (`mutable-gui-reference`), the CLAP effect that exercises the library, and its tests |
| `xtask/` | the build helper behind `cargo xtask` (`bundle`, `bundle-universal`) |
| `tools/` | `check-env.sh` (environment check), `validate-clap.sh` (CLAP gate), `fetch-inter.sh` (font download), `check-stack.py` (STACK.md against `Cargo.lock`) |
| `.githooks/` | git hooks; `pre-commit.project` runs `cargo fmt --check` and clippy |
| `.github/workflows/ci.yml` | GitHub Actions CI for macOS, Linux and Windows on every push and pull request |
| `setup-prerequisites.sh` | the one-time installer the owner runs (Xcode command line tools, pinned Rust toolchain) |
| `.devpipe/`, `.claude/`, `.opencode/` | the owner's local pipeline configuration and agent files; ignored by git, so a clone does not have them |

## Status

`python3 tools/devpipe/run.py status` shows the pipeline's state; once the pipeline has run a
phase, `HANDOFF.md` holds the current phase, the next ticket and anything waiting on the owner.
`CHANGELOG.md` lists what changed.

## Read next

`docs/ARCHITECTURE.md`, then `docs/RUNBOOK.md`, then `docs/TESTING.md`.

## Licences

mutable-gui is licensed under MIT OR Apache-2.0 (`license` in `Cargo.toml`). The bundled Inter
font 4.1 (`crates/mutable-gui/assets/Inter-Regular.ttf`, `Inter-Medium.ttf`) is under the SIL
Open Font License 1.1, whose text is `crates/mutable-gui/assets/OFL.txt`.
