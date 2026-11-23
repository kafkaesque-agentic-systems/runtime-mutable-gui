---
id: F-002
title: "Dim irrelevant controls"
status: PROPOSED     # PROPOSED | ACCEPTED | DONE | DROPPED
placement: none      # none | now | later | rework
requirements: []     # requirements this feature adds, e.g. [R-014]
changes: []          # existing requirements whose text it changes
serves: []           # for a change with no new behaviour: the requirement it serves
touches: []          # source files it creates or modifies
steps: []            # plan steps added for it, e.g. ["2.7", "2.8"]
---
## Idea

Particle Arp migration, owner 2026-11-23: if mutable-gui requires features to make the migration work, then we should draft those. Dimming: controls the plugin marks irrelevant in the current mode are drawn dimmed (owner chose: dimmed, still operable).

## Behaviour

<<What a user can observe once this exists that they cannot observe today. One paragraph.>>

## Acceptance

- <<a result with concrete values that a test can assert>>

## Out of scope

- <<the adjacent thing this feature will not do>>

## Invariants

- I-01 (The only library functions reachable from the audio thread are the tap producers'): <<not affected, or how the feature keeps it>>
- I-02 (No library code calls nice-plug's `GuiContext::set_state`, because nice-plug): <<not affected, or how the feature keeps it>>
- I-03 (`PersistedUi`'s serialize and deserialize and every `StateCell` method do only): <<not affected, or how the feature keeps it>>
- I-04 (Parameter values change only through `ParamSource` begin, set and end, only in): <<not affected, or how the feature keeps it>>
- I-05 (`crates/mutable-gui` has `#![forbid(unsafe_code)]` and no dependency on nice-plug,): <<not affected, or how the feature keeps it>>
- I-06 (Every `unsafe` block in `crates/mutable-gui-nice` carries a `// SAFETY:` comment): <<not affected, or how the feature keeps it>>
- I-07 (Every byte sequence from outside the process passes `doc` validation before any): <<not affected, or how the feature keeps it>>
- I-08 (No code path removes, renames or rebinds an element except a `Command` built from): <<not affected, or how the feature keeps it>>
- I-09 (Elements store colours only as colour role names; colour values appear only in): <<not affected, or how the feature keeps it>>
- I-10 (Every library file write goes to a temporary file in the destination folder and): <<not affected, or how the feature keeps it>>
- I-11 (Analysis code (FFT, RMS, peak) is called only from the editor thread.): <<not affected, or how the feature keeps it>>
- I-12 (The editor chrome (menu button, editor menu, notices) is drawn after all layout): <<not affected, or how the feature keeps it>>
- I-13 (No crate in the dependency graph of `crates/mutable-gui` or): <<not affected, or how the feature keeps it>>
- I-14 (Every document is encoded with its `format` and `version` first, and decoding a): <<not affected, or how the feature keeps it>>
- I-15 (Element ids are unique within a layout; edits and moves keep ids; duplicate,): <<not affected, or how the feature keeps it>>
- I-16 (While an unreadable saved state is kept, `StateCell` holds that string for saving): <<not affected, or how the feature keeps it>>
- I-17 (The tap reader flag is set only while a display or custom element bound to that): <<not affected, or how the feature keeps it>>
- I-18 (Custom kind code receives only a `KindContext`; no path hands it `ParamSource`,): <<not affected, or how the feature keeps it>>
- I-19 (Every gesture a custom element begins through `KindContext` is ended, by the element): <<not affected, or how the feature keeps it>>
- I-20 (An unknown element's stored kind, version and props are encoded back exactly as they): <<not affected, or how the feature keeps it>>
- I-21 (The tool layer (menu button, editor menu, design panels, dialogs, notices) is drawn): <<not affected, or how the feature keeps it>>

## Rework

<<One line per ticket the impact report lists as citing a changed requirement: "- P01-T03: reworked in step 2.7" or "- P01-T03: no change needed, because …". Write "None." when the report lists none.>>

## Placement

<<now, later or rework; the phase; and the reason, taken from the impact report.>>
