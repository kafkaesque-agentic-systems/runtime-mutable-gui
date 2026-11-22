# Stack: mutable-gui

Every tool and library the project uses, pinned. A version comes from a command that was
run, a lockfile, a registry page that was read, or the owner. It never comes from memory.
Use only what is listed here; adding a row is the owner's decision.

Registry versions were read from the crates.io API (`https://crates.io/api/v1/crates/<name>`)
on 2026-11-22. Cargo pins them with `=` in `[workspace.dependencies]`; `Cargo.lock` is
committed.

| Name | Version | Role | Source |
|---|---|---|---|
| rustc | 1.99.1 | Compiler, pinned in `rust-toolchain.toml` | `rustc --version` on this Mac |
| cargo | 1.99.1 | Build, test, bench | `cargo --version` on this Mac |
| rustfmt | 1.99.1 toolchain component | Formatting gate | `rustup component list --installed` |
| clippy | 1.99.1 toolchain component | Lint gate | `rustup component list --installed` |
| nice-plug | 0.4.2 | Plugin framework of the adapter and the reference plugin (CLAP export, parameters, persisted fields); features `editor`, `zstd` | crates.io API |
| nice-plug-egui | 0.6.0 | egui editor for nice-plug; feature `opengl` (D-20) | crates.io API |
| nice-plug-xtask | 0.1.1 | Bundling the reference plugin (`cargo xtask bundle`) | crates.io API |
| egui | 0.37.0 | Immediate-mode GUI of the core | crates.io API |
| egui-baseview | 0.9.0 | Window backend under nice-plug-egui (resolved, not a direct dependency) | crates.io API; required `^0.9.0` by nice-plug-egui 0.6.0 |
| baseview | 0.4.2 | Native plugin window (resolved, not a direct dependency) | crates.io API; required `^0.4.1` by egui-baseview 0.9.0 |
| serde | 1.0.229 | Derives for every document type | crates.io API |
| serde_json | 1.0.154 | JSON encoding and decoding of documents | crates.io API |
| schemars | 1.2.3 | JSON Schema generation for `schema/` | crates.io API |
| base64 | 0.23.1 | Asset encoding inside documents | crates.io API |
| uuid | 1.29.3 | Element, page and asset ids (v4); feature `v4`, `serde` | crates.io API |
| thiserror | 2.0.21 | Error types | crates.io API |
| arc-swap | 1.9.5 | `StateCell` atomic hand-off of the encoded instance state (D-26) | crates.io API |
| rtrb | 0.4.1 | Wait-free single-producer single-consumer ring of audio taps | crates.io API |
| realfft | 3.5.1 | Real FFT for the spectrum display (editor thread only) | crates.io API |
| png | 0.18.1 | PNG asset decoding and validation | crates.io API |
| skrifa | 0.44.0 | Font asset validation with the same parser egui uses | crates.io API; epaint 0.37.0 requires `^0.44.0` |
| rfd | 0.18.0 | System file dialogs for import and export | crates.io API |
| dirs | 7.0.0 | Platform user data directory of the library (D-32) | crates.io API |
| proptest | 1.12.0 | Property tests (round trips, undo, malformed input) | crates.io API |
| criterion | 0.8.2 | Benchmarks of the performance requirements | crates.io API |
| egui_kittest | 0.37.0 | Headless editor harness and rendering snapshots; feature `snapshot` | crates.io API |
| nice-assert-no-alloc | 1.0.0 | Allocation tests of tap pushes and the reference plugin's process call | crates.io API |
| tempfile | 3.27.0 | Temporary library folders in tests | crates.io API |
| clap-validator | 0.4.1 | CLAP conformance and state tests of the reference plugin | `clap-validator --version` on this Mac |
| Bitwig Studio | 5.3.13 | Manual host gate (owner) | `CFBundleShortVersionString` of `/Applications/Bitwig Studio.app` |
| git | 2.54.0 (Apple Git-157) | Version control | `git --version` on this Mac |
| python3 | 3.15.2 | devpipe toolkit | `python3 --version` on this Mac |
| macOS | 26.7.1 (25G241), arm64 | Development and gate platform | `sw_vers`, `uname -m` on this Mac |

## Excluded on purpose

- nih-plug: upstream is quiet and pins egui 0.31; nice-plug replaces it (D-01).
- clack, clap-sys used directly: version 1 has only the nice-plug adapter (D-01).
- vizia, iced, Slint, webviews (wry, nice-plug-webview): egui is the toolkit (D-02).
- wgpu rendering: OpenGL is the backend (D-20).
- RON, TOML, zip archives for documents or packages: JSON only (D-12).
- Any HTTP, socket or networking crate: the library opens no network connection (I-13).
- The `image` crate: `png` covers the one image format accepted (R-123).
- Scripting engines (Lua, Rhai, JavaScript): packages hold no code (D-21).
- AccessKit wiring: screen readers are out of version 1 (D-15).
