---
id: F-004
title: "Custom kinds with plugin state"
status: ACCEPTED
placement: later
requirements: [R-176]
changes: []
serves: []
touches: ["crates/mutable-gui-testkit/src/stateful_kind.rs", "crates/mutable-gui-testkit/src/lib.rs", "crates/mutable-gui/tests/custom_plugin_state.rs", "README.md", ".claude/agents/runtime-mutable-gui-reviewer.md", "design/DECISIONS.md"]
steps: ["7.19"]
---
## Idea

Particle Arp migration, owner 2026-11-23: if mutable-gui requires features to make the migration work, then we should draft those. Custom kinds may hold and change plugin state they captured at registration, such as stored scenes and a CC step pattern (owner chose: yes, never parameters).

## Behaviour

A developer's custom element kind may hold references, captured when it is registered, to the plugin's own state that is not a host parameter (Particle Arp's four stored scenes, its 16-step CC pattern), read that state while drawing, and change it in response to perform-mode input. mutable-gui calls that code only on the editor thread, as for every kind, and treats the state as the plugin's: it is not part of the instance state, the layout's undo, packages, the clipboard or the library, and the plugin saves and loads it through its own persisted fields. A host parameter still changes only through gestures on the kind's binding slots. Today the design says what the library hands a kind but not whether a kind may act on anything else, so a reviewer could refuse Particle Arp's scene list, morph pad and step editor.

## Requirements

- **R-176 — Custom kinds act on plugin-owned state.** A custom kind may change state of its plugin that it captured at registration, in response to perform-mode input; such changes leave the instance state and the undo history unchanged.
  Acceptance: a test control kind holding an `Arc<AtomicU32>` captured at registration increments it on each perform-mode click and draws its value: three clicks give 3 and the kind draws "3"; the encoded instance state and the undo depth are the same before and after the clicks; in design mode a click selects the element and leaves the counter at 3.

Changed requirements: none; R-162 ("a custom element changes a parameter only through begin, set and end on one of its binding slots") stands as written.

New decision (D-51): "A custom kind may hold references to its plugin's own state, captured at registration, and read and change it on the editor thread. That state belongs to the plugin: the plugin persists it, and it is outside the instance state, undo, packages, the clipboard and the library. A kind never changes a host parameter except through its binding slots; a captured reference to the plugin's parameters may be read and never written. State the audio thread also reads is shared through the plugin's own wait-free structures." This makes explicit what I-18 leaves open: I-18 lists what the library hands a kind, not what the developer gives it.

## Data and interfaces

- Nothing new in the library's API or documents: a kind is a developer's struct and may own `Arc`s; the requirement is a guarantee about how the library treats that.
- The README's developer guide gains a section "Plugin-owned state" with the morph-pad example (scenes in the plugin's `#[persist]` field, read by the kind, Store and Reset changing them) and the rule against writing parameters.
- The reviewer agent's checklist gains: a custom kind writes no parameter through a captured reference.

## Dependencies

None.

## Edges

- The host loads a project while the editor is open: the plugin's own fields change, and the kind draws the loaded state on the next frame it is drawn; mutable-gui does nothing for it.
- The user presses Undo after storing a scene: the scene stays stored, because plugin state is outside mutable-gui's undo; the developer guide says so, and a plugin that wants undo for it keeps its own.
- A layout with the kind is exported as a package and imported into another instance: the element and its properties travel; the plugin state does not.

## Acceptance

- The Acceptance line under "Requirements" above.

## Out of scope

- An undo API for plugin-owned state.
- Library "action" elements that call developer callbacks.
- Any check by the library that a kind writes no parameter through a captured reference: it is a rule for developers and reviewers.

## Invariants

- I-01 (The only library functions reachable from the audio thread are the tap producers'): not affected: kind code runs on the editor thread; sharing state with the audio thread is the plugin's, through its own wait-free structures, as the decision says.
- I-02 (No library code calls nice-plug's `GuiContext::set_state`, because nice-plug): not affected.
- I-03 (`PersistedUi`'s serialize and deserialize and every `StateCell` method do only): not affected; plugin state is persisted by the plugin's own fields, never through `PersistedUi`.
- I-04 (Parameter values change only through `ParamSource` begin, set and end, only in): kept by the decision's rule (no parameter writes through captured references) and the reviewer's check; the library cannot enforce it.
- I-05 (`crates/mutable-gui` has `#![forbid(unsafe_code)]` and no dependency on nice-plug,): not affected.
- I-06 (Every `unsafe` block in `crates/mutable-gui-nice` carries a `// SAFETY:` comment): not affected.
- I-07 (Every byte sequence from outside the process passes `doc` validation before any): not affected; plugin state never enters a document.
- I-08 (No code path removes, renames or rebinds an element except a `Command` built from): not affected.
- I-09 (Elements store colours only as colour role names; colour values appear only in): not affected.
- I-10 (Every library file write goes to a temporary file in the destination folder and): not affected.
- I-11 (Analysis code (FFT, RMS, peak) is called only from the editor thread.): not affected.
- I-12 (The editor chrome (menu button, editor menu, notices) is drawn after all layout): not affected.
- I-13 (No crate in the dependency graph of `crates/mutable-gui` or): not affected.
- I-14 (Every document is encoded with its `format` and `version` first, and decoding a): not affected.
- I-15 (Element ids are unique within a layout; edits and moves keep ids; duplicate,): not affected.
- I-16 (While an unreadable saved state is kept, `StateCell` holds that string for saving): not affected; plugin state is outside `StateCell`.
- I-17 (The tap reader flag is set only while a display or custom element bound to that): not affected.
- I-18 (Custom kind code receives only a `KindContext`; no path hands it `ParamSource`,): kept and made explicit: the library still hands only a `KindContext`; references the developer gives the kind are the developer's.
- I-19 (Every gesture a custom element begins through `KindContext` is ended, by the element): not affected.
- I-20 (An unknown element's stored kind, version and props are encoded back exactly as they): not affected.
- I-21 (The tool layer (menu button, editor menu, design panels, dialogs, notices) is drawn): not affected.

## Plan steps

- Step 7.19 — Plugin-owned state in custom kinds (R-176): the testkit's `StatefulKind`, its test, the README section and the reviewer agent's line. D-51 is already recorded in `design/DECISIONS.md`.

## Rework

None: the impact report of 2026-11-23 lists no ticket that writes these files or cites a changed requirement.

## Placement

Recommended `later`, Phase 7, with the other custom-kind steps; nothing built or queued depends on it (impact report, 2026-11-23).
