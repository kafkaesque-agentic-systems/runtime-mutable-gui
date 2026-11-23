---
id: F-001
title: "Event and snapshot taps"
status: ACCEPTED
placement: later
requirements: [R-169, R-170, R-171, R-172]
changes: [R-007, R-044, R-155]
serves: []
touches: ["crates/mutable-gui/src/taps/events.rs", "crates/mutable-gui/src/taps/snapshot.rs", "crates/mutable-gui/src/taps/mod.rs", "crates/mutable-gui/src/custom/props.rs", "crates/mutable-gui/src/custom/context.rs", "crates/mutable-gui/src/editor/taps.rs", "crates/mutable-gui/src/design/tap_picker.rs", "crates/mutable-gui/tests/taps_events.rs", "crates/mutable-gui/tests/taps_snapshot.rs", "crates/mutable-gui/tests/alloc_taps.rs", "crates/mutable-gui/tests/custom_tap_kinds.rs", "crates/mutable-gui/tests/custom_tap_picker.rs"]
steps: ["3.18", "3.19", "7.16", "7.17"]
---
## Idea

Particle Arp migration, owner 2026-11-23: if mutable-gui requires features to make the migration work, then we should draft those. Telemetry: event and snapshot taps, so a custom display can draw every emitted grain and the latest engine state (owner chose: events + snapshot taps).

## Behaviour

A plugin developer can declare two more kinds of signal tap besides audio and scalar. An event tap carries fixed-length records of 1 to 16 numbers, such as one record per emitted grain (pitch, velocity, channel, sample offset); while a visible custom element reads it, every record pushed is kept until the next frame, up to the tap's capacity, and records that do not fit are dropped and counted. A snapshot tap carries one block of 1 to 1,024 numbers, such as the engine's energy, bloom and held-note pool; the reader always gets the latest complete block, never a mix of two publications. A custom element kind declares tap slots of these kinds; in design mode the tap picker binds them; each frame the element receives the records pushed since the previous frame, or the latest block. Today a custom display can read only audio samples and single numbers, so Particle Arp's grain canvas and key strip cannot be built.

## Requirements

- **R-169 — Event tap declaration.** The developer declares an event tap with a unique name, a record length of 1 to 16 values and a capacity of 64 to 65,536 records, before the plugin first processes audio.
  Acceptance: declaring "grains" (record length 4, capacity 4,096) succeeds and the editor's tap list holds it as an event tap of record length 4; record length 17 and capacity 63 are each refused and the registry is unchanged.
- **R-170 — Event tap push.** Pushing a record copies it whole when a visible custom element reads the tap and returns at once otherwise; a record that does not fit is dropped and counted; a record of the wrong length is refused and nothing is copied.
  Acceptance: with no reader, 1,000 pushes leave 0 records copied; with a reader, records [1, 2, 3, 4] and [5, 6, 7, 8] pushed between two frames arrive in that order on the next frame and none arrive on the frame after; 5,000 pushes into a 4,096-record tap that is never drained keep the first 4,096 and count 904 dropped; a 3-value push into a record-length-4 tap returns the length error.
- **R-171 — Snapshot tap.** The developer declares a snapshot tap with a unique name and a length of 1 to 1,024 values; a publish copies the whole block when a visible custom element reads the tap and returns at once otherwise; a reader always gets the latest complete block.
  Acceptance: publishing eight 1s then eight 2s reads eight 2s; while one thread publishes 1,000,000 blocks whose values all equal a counter and another thread reads continuously, no read holds two different values; with no reader, a publish copies nothing.
- **R-172 — Custom tap slots of event and snapshot taps.** A custom kind declares a tap slot of kind event or snapshot; the tap picker for that slot lists only taps of that kind; each frame the element receives the records pushed since the previous frame with the dropped count, or the latest block with its sequence number; records pushed before the element became visible are never delivered.
  Acceptance: a test kind whose event slot is bound to "grains" receives the 2 records pushed between two frames and 0 on the next frame; its snapshot slot bound to "state" receives the latest block; the picker for the event slot lists "grains" and not "out", "gr" or "state".

Changed requirements: R-007 (the declared kinds become audio, scalar, event or snapshot), R-044 (pushes and publishes to event and snapshot taps allocate nothing, lock nothing and call no system function; its allocation test covers them), R-155 (a tap slot accepts audio, scalar, event or snapshot taps). The specification's data model lines "Signal tap" and "Custom element kind" gain the two kinds.

## Data and interfaces

- Nothing new is stored: taps are declared in code, and a tap slot already stores a tap name. No frozen identifier is added.
- `TapRegistry::declare_events(name, record_len: u8, capacity: u32) -> Result<EventTapProducer, TapError>` and `EventTapProducer::push(&mut self, record: &[f32]) -> Result<(), TapPushError>` (`TapPushError::Length`).
- `TapRegistry::declare_snapshot(name, len: u16) -> Result<SnapshotTapProducer, TapError>` and `SnapshotTapProducer::publish(&mut self, values: &[f32]) -> Result<(), TapPushError>`.
- `TapKind` gains `Events { record_len, capacity }` and `Snapshot { len }`; custom `TapSlotKind` gains `Events` and `Snapshot`; `TapData` gains `Events { record_len, records: &[f32] (oldest first), dropped: u64 }` and `Snapshot { values: &[f32], sequence: u64 }`.
- The event tap is an `rtrb` ring of `record_len × capacity` values written one whole record at a time. The snapshot tap is a triple buffer written in safe Rust: three preallocated `Box<[AtomicU32]>` slots (f32 bits, relaxed stores) and one `AtomicU8` holding the slot indices and a fresh flag, swapped with release and acquire, so the core keeps `#![forbid(unsafe_code)]` (I-05).

## Dependencies

None: `rtrb` and the standard atomics are already in `design/STACK.md`.

## Edges

- A host block longer than one frame pushes 600 grains: all reach the element on the next frame while they fit in the capacity; beyond it, the newest are dropped and `dropped` says how many.
- Two custom elements bound to the same event tap both receive the same records: the editor drains each tap once per frame and shares the result.
- The developer publishes snapshots faster than frames are drawn: the reader sees the latest only; skipped blocks are by design.
- A push of the wrong length on the audio thread returns an error and never panics.

## Acceptance

- The four Acceptance lines under "Requirements" above, plus R-044's allocation test extended with 1,000 event pushes and 1,000 snapshot publishes, with and without a reader, at `violation_count() == 0`.

## Out of scope

- Built-in displays reading event or snapshot taps; only custom kinds read them.
- Keeping records for longer than one frame; the custom kind keeps what it needs.
- Timestamps or units added by the library: a record holds what the developer pushes.
- A built-in MIDI keyboard or note display (still out of scope in the specification).

## Invariants

- I-01 (The only library functions reachable from the audio thread are the tap producers'): kept and extended: `EventTapProducer::push` and `SnapshotTapProducer::publish` join the push functions; each makes one acquire load of the reader flag, then at most one ring write of `record_len` values or one store of `len` values and an index swap; no allocation, lock, wait or system call; the allocation test covers them.
- I-02 (No library code calls nice-plug's `GuiContext::set_state`, because nice-plug): not affected.
- I-03 (`PersistedUi`'s serialize and deserialize and every `StateCell` method do only): not affected.
- I-04 (Parameter values change only through `ParamSource` begin, set and end, only in): not affected; taps never touch parameters.
- I-05 (`crates/mutable-gui` has `#![forbid(unsafe_code)]` and no dependency on nice-plug,): kept: the triple buffer uses atomic slots instead of `UnsafeCell`.
- I-06 (Every `unsafe` block in `crates/mutable-gui-nice` carries a `// SAFETY:` comment): not affected; the adapter gains no `unsafe`.
- I-07 (Every byte sequence from outside the process passes `doc` validation before any): not affected; tap data never leaves the process or enters a document.
- I-08 (No code path removes, renames or rebinds an element except a `Command` built from): not affected.
- I-09 (Elements store colours only as colour role names; colour values appear only in): not affected.
- I-10 (Every library file write goes to a temporary file in the destination folder and): not affected.
- I-11 (Analysis code (FFT, RMS, peak) is called only from the editor thread.): kept: the library adds no analysis; whatever a custom kind computes from records runs in its `draw` on the editor thread.
- I-12 (The editor chrome (menu button, editor menu, notices) is drawn after all layout): not affected.
- I-13 (No crate in the dependency graph of `crates/mutable-gui` or): not affected; no dependency is added.
- I-14 (Every document is encoded with its `format` and `version` first, and decoding a): not affected; no document changes.
- I-15 (Element ids are unique within a layout; edits and moves keep ids; duplicate,): not affected.
- I-16 (While an unreadable saved state is kept, `StateCell` holds that string for saving): not affected.
- I-17 (The tap reader flag is set only while a display or custom element bound to that): kept and extended: an event or snapshot tap's flag is set only while a custom element whose slot is bound to it is on the current page of an open editor, by the same per-frame pass as audio taps.
- I-18 (Custom kind code receives only a `KindContext`; no path hands it `ParamSource`,): kept: `KindContext` gains the two `TapData` variants and still hands over no producer.
- I-19 (Every gesture a custom element begins through `KindContext` is ended, by the element): not affected.
- I-20 (An unknown element's stored kind, version and props are encoded back exactly as they): not affected.
- I-21 (The tool layer (menu button, editor menu, design panels, dialogs, notices) is drawn): not affected; the tap picker lists the new kinds in the same tool style.

## Plan steps

- Step 3.18 — Event tap (R-169, R-170).
- Step 3.19 — Snapshot tap and allocation of the new taps (R-171, R-044; pins Step 3.4's `alloc_taps.rs`).
- Step 7.16 — Event and snapshot data for custom kinds (R-172; pins Steps 7.6 and 3.7).
- Step 7.17 — Tap picker for event and snapshot slots (R-172; pins Step 5.16).

## Rework

None: the impact report of 2026-11-23 lists no finished or unfinished ticket that writes these files or cites R-007, R-044 or R-155.

## Placement

Recommended `later`: Phase 3 for the taps and Phase 7 for the slots, beside the steps that build the audio and scalar versions; nothing built or queued depends on it (impact report, 2026-11-23: only Phase 0 has tickets, all done, none touching these files).
