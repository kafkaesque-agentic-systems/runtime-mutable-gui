# Architecture (as designed): mutable-gui

This is the intended design. `docs/ARCHITECTURE.md` describes what was built.

A Cargo workspace of two library crates, a reference plugin and a build helper. The core
crate knows nothing of any plugin framework; the adapter crate is the only place nice-plug
is used. The core is an egui application whose single source of truth is the instance
state document: every frame draws that document, and every edit is a command that changes
it.

## Components

| Component | Path | Responsibility |
|---|---|---|
| Workspace | `Cargo.toml` | Members, shared dependency versions, workspace lints, edition 2024, `rust-version = "1.95"`. |
| Toolchain pin | `rust-toolchain.toml` | Pins Rust 1.99.1 with rustfmt and clippy. |
| Core: model | `crates/mutable-gui/src/model/` | Plain data types of the data model (instance state, layout, page, element, binding, theme, fill, asset, package), serde derives, no behaviour beyond accessors. |
| Core: documents | `crates/mutable-gui/src/doc/` | JSON encode and decode of every format, schema versions and migrations (`migrate.rs`), limits and validation (`validate.rs`), base64 assets, font and PNG decode checks. The only entry point for outside bytes. |
| Core: parameters | `crates/mutable-gui/src/params.rs` | The `ParamSource` trait (list parameters with id, name, group path, flags, kind, step count, default; read base and modulated value; format and parse; begin, set, end gesture) and `ParamInfo`. |
| Core: signal taps | `crates/mutable-gui/src/taps/` | `TapRegistry` (declaration, R-007/R-008); audio tap producer and consumer over a wait-free single-producer single-consumer ring; scalar tap over atomics (latest and maximum); the reader-present flag. |
| Core: analysis | `crates/mutable-gui/src/analysis/` | FFT spectrum, peak, RMS and peak hold over data drained from taps, run on the editor thread. |
| Core: theme | `crates/mutable-gui/src/theme/` | Built-in themes, role and token resolution to egui colours and strokes, WCAG contrast calculation, font loading into egui. |
| Core: rendering | `crates/mutable-gui/src/render/` | Canvas scaling and bars (`canvas.rs`), one module per element kind drawing from the document and the parameter values, editor chrome: menu button, editor menu, notices (`chrome.rs`). |
| Core: perform | `crates/mutable-gui/src/perform/` | Perform-mode input: drags, gestures and their closing, control menu, value field, keyboard focus and adjustment. |
| Core: design | `crates/mutable-gui/src/design/` | Design-mode input and panels: palette, selection and marquee, handles, snapping, align and distribute, groups, clipboard, inspector, parameter picker, tap picker, unbound list, theme editor, page management. Produces commands; never mutates the document directly. |
| Core: edit | `crates/mutable-gui/src/edit/` | `Command` values that change the instance state, applied by one function, and the undo stack with structural sharing of unchanged pages and assets. |
| Core: library | `crates/mutable-gui/src/library/` | Library paths per platform, listing, save (temporary file then rename), delete, user defaults and suite default theme, behind a `Storage` trait; the `FileDialog` trait and its rfd implementation. |
| Core: generator | `crates/mutable-gui/src/generate.rs` | The generated default layout from a parameter list (R-003–R-006). |
| Core: persistence cell | `crates/mutable-gui/src/persist.rs` | `StateCell`: the lock-free hand-off of the serialized instance state between the editor thread and whichever thread the framework saves and loads on, with a generation counter for loads. |
| Core: editor | `crates/mutable-gui/src/editor.rs` | `EditorState`, one per plugin instance and living as long as it: the decoded instance state, mode, selection, undo stack, notices, focus; `EditorState::frame(&egui::Context)` is the per-frame entry point. |
| Adapter | `crates/mutable-gui-nice/` | `MutableGui` builder (embedded package, taps, design-mode switch); `ParamSource` over nice-plug's parameter map and `GuiContext`; the nice-plug `Editor` built with nice-plug-egui that owns the `EditorState` and calls `frame`; `PersistedUi`, the `#[persist = "mutable-gui"]` field type backed by `StateCell`. |
| Reference plugin | `examples/reference-plugin/` | Crate `mutable-gui-reference`: a nice-plug CLAP effect with about 60 parameters in groups (filter, drive, compressor, modulation, output), taps "out" (audio, 2 channels) and "gr" (scalar), and `assets/default.mgui` embedded as its developer default. |
| Build helper | `xtask/` | `cargo xtask bundle` through nice-plug-xtask; `cargo xtask schema` writes the JSON Schemas; `cargo xtask fixtures` checks the schema fixtures. |
| JSON Schemas | `schema/` | Generated `instance.schema.json`, `layout.schema.json`, `theme.schema.json`, `package.schema.json`, `elements.schema.json`; CI fails when they differ from the code. |
| Fixtures | `crates/mutable-gui/tests/fixtures/` | One valid document per format and schema version, one invalid package per import limit, and the 300-element page used by the frame benchmark. |
| Manual checklist | `docs/qa/bitwig-checklist.md` | The owner's Bitwig 5.3.13 steps that gate version 1. |

## Boundaries

- `crates/mutable-gui` never depends on nice-plug, baseview, egui-baseview or any plugin
  framework; it depends on egui and talks to the plugin only through `ParamSource`,
  `TapRegistry` and `StateCell`.
- `crates/mutable-gui-nice` depends on the core and nice-plug; it holds no layout, theme or
  rendering logic of its own.
- The reference plugin uses only the adapter's public API and the tap producer types; it
  never reaches into core modules other than `taps`.
- Threads:
  - Audio thread: runs the plugin's DSP; the only library code it may run is the push
    functions of tap producers (and `StateCell::store_incoming` when nice-plug applies a
    state set from the editor during processing, which the library never requests).
  - Host main thread: nice-plug's state save and load call `PersistedUi`, which calls only
    `StateCell`.
  - Editor thread (the window's thread, the main thread on macOS): owns `EditorState`;
    drains taps, runs analysis, decodes documents, writes library files, shows file
    dialogs, and sends parameter gestures through `ParamSource`.
- `EditorState` is held by the adapter's editor object behind a mutex that only the editor
  thread and the host main thread take; the audio thread never touches it.
- Only `doc` turns outside bytes (instance state, package files, clipboard text, library
  files, the embedded default) into model values; every other module receives validated
  model values.
- Only `edit::apply` changes the instance state; design-mode and perform-mode code build
  commands. Parameter values are not part of the instance state; they change only through
  `ParamSource` gestures.
- `library` is the only module that touches the file system, through `Storage`.

## Data flow

1. Host loads a project → main thread → nice-plug state load → `PersistedUi` deserialize →
   `StateCell::store_incoming` (the raw string, a new generation; no parsing) → next editor
   frame or next editor open → `doc::decode_instance` → validate and migrate →
   `EditorState` replaces its document and clears undo; on failure, the fallback layout
   with a notice and the raw string kept for saving (R-117, R-118).
2. Editor opens with no stored state → `EditorState` resolves the defaults (user default,
   suite default theme, developer default from the embedded package, else `generate`) →
   publishes the encoded instance state to `StateCell` (R-112–R-114).
3. User drags a knob in perform mode → `perform` → `ParamSource::begin`, `set` per pointer
   move, `end` on release → nice-plug `GuiContext` → host and the plugin's parameter
   atomics → the plugin's DSP reads the parameter.
4. Host automation or modulation changes a parameter → nice-plug calls the editor's change
   callback → repaint requested → next frame reads base and modulated values from
   `ParamSource` → `render` draws value and modulation band.
5. Plugin DSP on the audio thread → tap producer `push` → if no reader, return; else copy
   into the ring, dropping what does not fit → editor frame drains each tap read by a
   visible display → `analysis` → display drawn.
6. Design-mode edit → `design` builds a `Command` → `edit::apply` changes the document and
   pushes the inverse onto the undo stack → `doc::encode_instance` → `StateCell::publish`
   (an atomic swap of the encoded string) → a later host save reads it (R-111).
7. Host saves the project → main thread → `PersistedUi` serialize → `StateCell::load`
   (atomic load of the current string, or the kept unreadable string) → nice-plug state.
8. Import or library load → `FileDialog` or `Storage` → size check before reading → bytes →
   `doc::decode_package` → limits, schema, unknown fields, asset decode → on success one
   `Command::Replace` through `edit::apply`; on failure a notice and no change.
9. Export or library save → `doc::encode_package` → `Storage::write_atomic` (temporary file
   in the same folder, then rename) or the file chosen in `FileDialog`.

## Invariants

- **I-01** The only library functions reachable from the audio thread are the tap producers'
  push functions and `StateCell::store_incoming`; none of them allocates, takes a lock,
  waits, calls the operating system or loops more than once per pushed frame.
- **I-02** No library code calls nice-plug's `GuiContext::set_state`, because nice-plug
  applies such a state on the audio thread while processing.
- **I-03** `PersistedUi`'s serialize and deserialize and every `StateCell` method do only
  atomic loads, stores and swaps of reference-counted strings; no lock, no parsing, no
  encoding.
- **I-04** Parameter values change only through `ParamSource` begin, set and end, only in
  perform mode, and every begin is matched by an end, including when the editor closes.
- **I-05** `crates/mutable-gui` has `#![forbid(unsafe_code)]` and no dependency on nice-plug,
  baseview or egui-baseview.
- **I-06** Every `unsafe` block in `crates/mutable-gui-nice` carries a `// SAFETY:` comment
  stating the nice-plug guarantee it relies on.
- **I-07** Every byte sequence from outside the process passes `doc` validation before any
  part of it reaches `edit::apply`; a validation failure leaves the instance state, the
  undo stack and the library unchanged.
- **I-08** No code path removes, renames or rebinds an element except a `Command` built from
  a user action; decode and migration preserve every element and binding.
- **I-09** Elements store colours only as colour role names; colour values appear only in
  themes.
- **I-10** Every library file write goes to a temporary file in the destination folder and
  is renamed over the destination only after a complete write.
- **I-11** Analysis code (FFT, RMS, peak) is called only from the editor thread.
- **I-12** The editor chrome (menu button, editor menu, notices) is drawn after all layout
  elements in a layer that layout content cannot occupy.
- **I-13** No crate in the dependency graph of `crates/mutable-gui` or
  `crates/mutable-gui-nice` is used to open a network connection; neither crate depends
  directly on an HTTP or socket library.
- **I-14** Every document is encoded with its `format` and `version` first, and decoding a
  version above the supported one fails with an error carrying both numbers.
- **I-15** Element ids are unique within a layout; edits and moves keep ids; duplicate,
  paste and import of elements assign new ids.
- **I-16** While an unreadable saved state is kept, `StateCell` holds that string for saving
  and no `Command` other than discarding it is accepted.
- **I-17** The tap reader flag is set only while a display bound to that tap is on the
  current page of an open editor.

## Test seams

- Model, documents, edit, generator, theme, analysis: unit tests and proptest property
  tests through the public functions `doc::decode_*`, `doc::encode_*`, `edit::apply`,
  `edit::UndoStack`, `generate::layout`, `theme::contrast`; nothing faked.
- Editor behaviour in both modes: egui_kittest `Harness` driving `EditorState::frame` with a
  `FakeParamSource` (an in-memory parameter tree that records every begin, set and end), a
  `FakeFileDialog`, `Storage` over a temporary directory, a fake clipboard and real taps fed
  from the test thread. Rendering snapshots per element kind and built-in theme use the
  harness's snapshot feature.
- Signal taps: unit tests on producer and consumer pairs; allocation tests running pushes
  under nice-assert-no-alloc; criterion benchmarks for push cost.
- Persistence: unit tests on `StateCell` and `PersistedUi`; round trips through the adapter's
  serialize and deserialize.
- Adapter and reference plugin: `cargo xtask bundle` then clap-validator 0.4.1 over the CLAP
  bundle (state, parameter and thread tests); an allocation test over the reference
  plugin's process call; an offline render compared sample for sample with the editor
  closed, in perform mode and in design mode.
- Performance: criterion benchmarks for the frame function over the 300-element fixture,
  package decode, picker search over 2,000 fake parameters, and undo memory.
- Host: the owner's manual Bitwig 5.3.13 checklist on macOS in `docs/qa/bitwig-checklist.md`.
