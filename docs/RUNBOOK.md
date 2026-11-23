# Runbook

Operations for mutable-gui. Every command here is literal and was run when written.

## 1. Environment

| Tool | Version | Why | How to get it |
|---|---|---|---|
| macOS on Apple silicon | 26.7.1, arm64 | the development and gate platform; `tools/check-env.sh` requires `Darwin` and `arm64` | — |
| Xcode command line tools | any; `/Library/Developer/CommandLineTools` here | the C linker and macOS SDK rustc links with | `sh setup-prerequisites.sh` (below) installs them when `xcode-select -p` finds none |
| rustup | 1.29.2 here | installs and selects the pinned Rust toolchain | the installer at https://rustup.rs (a person runs it; `rustup --version` checks it) |
| Rust (rustc, cargo) with rustfmt and clippy | 1.99.1 | pinned in `rust-toolchain.toml` | `sh setup-prerequisites.sh` (below); rustup also installs the pinned toolchain by itself the first time a `cargo` or `rustc` command runs in this folder |
| clap-validator | 0.4.1 | the CLAP conformance gate | from the release page https://github.com/free-audio/clap-validator/releases/tag/0.4.1, the asset `clap-validator-0.4.1-127-g152b982-macos-15-aarch64.zip`; unpack it and put the `clap-validator` binary in a folder on `PATH` (the owner's Mac has it in `~/.local/bin/`); `clap-validator --version` prints `clap-validator 0.4.1` |
| python3 | 3.11 or later (`tomllib`); 3.15.2 here | `tools/check-stack.py` and the devpipe toolkit | any python3 of 3.11 or later first on `PATH`; this Mac's is Homebrew's `/opt/homebrew/bin/python3`, because macOS's own `/usr/bin/python3` is 3.9.6 |
| git, curl, unzip, shasum | macOS built-ins | version control; `tools/fetch-inter.sh` | — |
| Bitwig Studio | 5.3.13 | the owner's manual host check | — |

`design/STACK.md` pins every tool and library. Install rustup and clap-validator first (table
above). The other one-time steps a person runs are in `setup-prerequisites.sh`: the Xcode
command line tools, then the Rust 1.99.1 toolchain. It prints each step and asks before running
it:

```sh
sh setup-prerequisites.sh
```

Then check the environment; it prints nothing and exits 0 when everything is present, else one
line per missing item:

```sh
sh tools/check-env.sh
```

In a fresh clone, turn on the repository's git hooks (sets `core.hooksPath` to `.githooks` for
this repository only, and creates the pipeline's working folders):

```sh
python3 tools/devpipe/run.py doctor
```

## 2. Build, run, install

```sh
cargo build --workspace
cargo xtask bundle mutable-gui-reference --release
sh tools/validate-clap.sh
```

The bundle is `target/bundled/mutable-gui-reference.clap`; `tools/validate-clap.sh` runs
clap-validator over it and exits 0 when no test failed.

Install the bundle for a DAW by copying it into the user's CLAP folder (the Phase 0 exit demo,
performed by the owner; this copy was tested into a temporary folder):

```sh
mkdir -p ~/Library/Audio/Plug-Ins/CLAP && cp -R target/bundled/mutable-gui-reference.clap ~/Library/Audio/Plug-Ins/CLAP/
```

After a plugin rescan, Bitwig Studio should list "Reference FX" by "mutable-gui"; in Phase 0 it
passes audio through unchanged and has no editor.

The Inter font files are committed. To fetch them again (downloads about 32 MB from GitHub into
a temporary folder, extracts the three files, rewrites `SHA256SUMS`) and verify them:

```sh
sh tools/fetch-inter.sh
(cd crates/mutable-gui/assets && shasum -a 256 -c SHA256SUMS)
```

## 3. Configuration

| Setting | Where | Default | Meaning |
|---|---|---|---|
| Toolchain | `rust-toolchain.toml` | 1.99.1, rustfmt, clippy, profile minimal | the compiler every command uses |
| Dependency versions | `[workspace.dependencies]` in `Cargo.toml` | exact `=` pins | must equal `design/STACK.md`; `python3 tools/check-stack.py` checks both and `Cargo.lock` |
| Lints | `[workspace.lints.clippy]` in `Cargo.toml`; `clippy.toml` | see `docs/ARCHITECTURE.md` | clippy runs with `-D warnings`; tests may unwrap, expect and panic (D-49) |
| Formatting | `rustfmt.toml` | edition 2024, `max_width = 100` | `cargo fmt --all` |
| `cargo xtask` | `.cargo/config.toml` | `run --package xtask --release --` | the build helper alias |
| `UPDATE_SNAPSHOTS` | environment variable | unset | when set, snapshot tests write their pictures instead of comparing them |
| Phase gate | `phase_gate` in `.devpipe/config.json` | fmt, clippy, `cargo test --workspace`, stack check | what the pipeline runs before a phase merges; `seam_gate` adds the timing, bundle and CLAP commands |

`.env.example` lists the environment variables by name. Secrets: none; the project uses no keys,
tokens or passwords, and git ignores `.env` files.

## 4. Logs

- Reference FX in a host writes no log in Phase 0: the stack builds nice-plug without its
  `tracing-subscriber` feature and the plugin installs no logger, and nice-plug then logs
  nothing.
- `sh tools/validate-clap.sh` writes the failed clap-validator tests as JSON to
  `target/clap-validator.json` (`{"results": []}` when all passed) and prints them on failure.
- A failing snapshot test leaves `<name>.new.png` and `<name>.diff.png` beside the snapshot in
  `tests/snapshots/` (git ignores both).
- `cargo bench` writes criterion's reports to `target/criterion/`.

## 5. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `tools/check-env.sh` prints "rustc 1.99.1 is missing" (or rustfmt, clippy) | the pinned toolchain is not installed | `sh setup-prerequisites.sh`, answer `y` |
| `setup-prerequisites.sh` stops with "rustup: command not found" | rustup is not installed or not on `PATH` | install rustup (https://rustup.rs), open a new shell, run `rustup --version`, then the installer again |
| Linking fails with "linker `cc` not found" | no Xcode command line tools | `sh setup-prerequisites.sh`, answer `y` to the Xcode step; `xcode-select -p` then prints a path |
| `tools/check-env.sh` prints "clap-validator 0.4.1 must be on PATH" | clap-validator missing or another version | put the 0.4.1 binary in a folder on `PATH`, then `clap-validator --version` |
| `tools/validate-clap.sh` prints "target/bundled/mutable-gui-reference.clap is missing" | not bundled yet | `cargo xtask bundle mutable-gui-reference --release` |
| `tools/validate-clap.sh` prints failures | a CLAP conformance test failed | read `target/clap-validator.json`; rerun one test readably with `clap-validator validate -t param-set-events --in-process target/bundled/mutable-gui-reference.clap` (test name from the JSON) |
| A harness test panics "No glyph for … Installed fonts: []" | egui built without its fonts | keep `features = ["default_fonts"]` on `egui` in `Cargo.toml` |
| A snapshot test fails and leaves a `.diff.png` | the picture changed | look at the `.new.png` and `.diff.png`; if the change is intended, rerun with `UPDATE_SNAPSHOTS=1` and commit the PNG (`docs/TESTING.md`) |
| `cargo test --release` fails to compile an `alloc_*.rs` file ("cannot find `AllocDisabler`") | the allocation checker exists only in debug builds | keep `#![cfg(debug_assertions)]` at the top of every `alloc_*.rs` |
| A commit is refused with a rustfmt diff or a clippy error | the pre-commit hook ran `.githooks/pre-commit.project` | `cargo fmt --all`, fix the clippy error, commit again |
| Commits in a fresh clone skip the checks | `core.hooksPath` is not set in a clone | `python3 tools/devpipe/run.py doctor` |
| `python3 tools/check-stack.py` fails with "No module named 'tomllib'" | the `python3` first on `PATH` is older than 3.11 (macOS's `/usr/bin/python3` is 3.9.6) | put a python3 of 3.11 or later first on `PATH`, then `python3 --version` |
| `python3 tools/check-stack.py` prints a mismatch | `design/STACK.md`, `Cargo.toml` and `Cargo.lock` disagree | a new version is the owner's stack decision: correct the row or the pin, then rerun |

## 6. Working with the pipeline

- Current state: `HANDOFF.md` (written by the runner once a phase has run),
  `python3 tools/devpipe/run.py status`.
- Run a phase: `python3 tools/devpipe/run.py run --phase N` (commits locally on `phase/NN`, never pushes).
- A blocked ticket leaves `.tickets/.work/<id>/RESCUE.md`; fix it, set `status: todo`, run again.
- Check artifacts: `python3 tools/devpipe/run.py lint all`.

## 7. Release and rollback

There is no release yet: every crate is version 0.1.0 with `publish = false`. The remote is
`origin`, `git@github.com:kafkaesque-agentic-systems/runtime-mutable-gui.git`; the pipeline
commits locally and never pushes, and the owner pushes `main`. Each plan step is one commit
whose subject starts with its phase tag (`[P00] step 0.4 …`); going back means reverting those
commits with `git revert`.
