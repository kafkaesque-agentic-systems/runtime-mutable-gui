---
id: F-003
title: "Parameter descriptions in control menu"
status: ACCEPTED
placement: later
requirements: [R-175]
changes: []
serves: []
touches: ["crates/mutable-gui/src/params.rs", "crates/mutable-gui-testkit/src/fake_params.rs", "crates/mutable-gui/src/perform/control_menu.rs", "crates/mutable-gui-nice/src/builder.rs", "crates/mutable-gui-nice/src/params.rs", "examples/reference-plugin/src/lib.rs", "crates/mutable-gui/tests/perform_description.rs", "crates/mutable-gui-nice/tests/describe.rs", "examples/reference-plugin/tests/snapshots/S-03-control-menu.png", "design/ui/S-03-control-menu.html", "design/UI.md"]
steps: ["4.23", "4.24", "4.25"]
---
## Idea

Particle Arp migration, owner 2026-11-23: if mutable-gui requires features to make the migration work, then we should draft those. Descriptions: the developer registers a description per parameter (owner chose: shown in the control menu only).

## Behaviour

The developer registers a plain-text description for any parameter id on the builder; nice-plug parameters carry none of their own. When the user opens a control's menu (right-click or long press, S-03), the menu shows the description of the control's first present bound parameter under its header (name and current value), wrapped to the menu's width in muted tool text, above the entries Reset, Type value and Fine adjust. A control whose parameter has no description shows the menu as today. Nothing pops up by itself: there are no hover tooltips. Today a user has no way to read what a parameter does from inside the plugin, while Particle Arp gives each of its 58 parameters a sentence or two.

## Requirements

- **R-175 — Parameter description in the control menu.** A control menu shows the description the developer registered for the control's first present bound parameter, under the header.
  Acceptance: with "cutoff" described as "Frequency where the filter starts to cut. Turn it down to darken the sound.", right-clicking a knob bound to cutoff opens a menu whose text under the header is that sentence and whose entries are still exactly Reset, Type value and Fine adjust; a knob bound to an undescribed parameter shows no description line; registering a description of 1,025 bytes is refused.

Changed requirements: none. R-040's acceptance ("a menu with exactly these three entries") holds: the description is header text, not an entry. `design/UI.md` S-03 "Shows" gains "the parameter's description, when the developer registered one, under the header"; Because the reference plugin will describe Cutoff, S-03's main mockup (`design/ui/S-03-control-menu.html`, the menu open on Cutoff) gains the description line through the `/ui-design` stage before the step that draws it runs, so `ui compare` sets matching pictures side by side; the `--value` and `--error` states show the value field with the menu closed and do not change.

## Data and interfaces

- Nothing is stored: descriptions are code; no document, package or library file changes; descriptions are never exported.
- Adapter: `MutableGui::builder(…).describe(id: &str, text: &str) -> Result<Self, DescribeError>` with `DescribeError::Empty` (empty or only whitespace) and `DescribeError::TooLong` (over 1,024 bytes). Newlines in the text are kept as line breaks; there is no markup.
- Core: `EditorConfig` gains `descriptions: BTreeMap<String, String>`; the control menu reads it.
- Tool style (D-36): Inter 12 px in `--tool-text-muted`, the menu's 280 px width less its padding, 4 px below the header.

## Dependencies

None.

## Edges

- A description for an id the plugin does not have: kept and never shown.
- An unbound control: its menu entries are disabled (Step 4.9) and no description shows, because no present parameter is bound.
- A description of about 600 characters (Particle Arp's longest): wraps to about nine lines; the menu grows and is placed so it stays inside the window, as the menu already is.
- A macro or XY pad: the first present bound parameter's description shows.

## Acceptance

- The Acceptance line under "Requirements" above, and the regenerated S-03 picture compared with the updated mockup.

## Out of scope

- Hover tooltips, descriptions in the parameter picker, the inspector or the library.
- Rich text, links or images in descriptions; translations.
- Descriptions written by users or carried in packages.

## Invariants

- I-01 (The only library functions reachable from the audio thread are the tap producers'): not affected.
- I-02 (No library code calls nice-plug's `GuiContext::set_state`, because nice-plug): not affected.
- I-03 (`PersistedUi`'s serialize and deserialize and every `StateCell` method do only): not affected; descriptions are not saved.
- I-04 (Parameter values change only through `ParamSource` begin, set and end, only in): not affected; showing text changes no value.
- I-05 (`crates/mutable-gui` has `#![forbid(unsafe_code)]` and no dependency on nice-plug,): kept: the core holds plain strings handed over by the adapter.
- I-06 (Every `unsafe` block in `crates/mutable-gui-nice` carries a `// SAFETY:` comment): not affected; `describe` needs no `unsafe`.
- I-07 (Every byte sequence from outside the process passes `doc` validation before any): not affected; descriptions come from the plugin's own code.
- I-08 (No code path removes, renames or rebinds an element except a `Command` built from): not affected.
- I-09 (Elements store colours only as colour role names; colour values appear only in): not affected.
- I-10 (Every library file write goes to a temporary file in the destination folder and): not affected.
- I-11 (Analysis code (FFT, RMS, peak) is called only from the editor thread.): not affected.
- I-12 (The editor chrome (menu button, editor menu, notices) is drawn after all layout): not affected; the control menu keeps its place in the top layer.
- I-13 (No crate in the dependency graph of `crates/mutable-gui` or): not affected.
- I-14 (Every document is encoded with its `format` and `version` first, and decoding a): not affected.
- I-15 (Element ids are unique within a layout; edits and moves keep ids; duplicate,): not affected.
- I-16 (While an unreadable saved state is kept, `StateCell` holds that string for saving): not affected; the control menu works while preserving, as it does today.
- I-17 (The tap reader flag is set only while a display or custom element bound to that): not affected.
- I-18 (Custom kind code receives only a `KindContext`; no path hands it `ParamSource`,): not affected; a custom control's menu shows its first present binding slot's description like any control.
- I-19 (Every gesture a custom element begins through `KindContext` is ended, by the element): not affected.
- I-20 (An unknown element's stored kind, version and props are encoded back exactly as they): not affected.
- I-21 (The tool layer (menu button, editor menu, design panels, dialogs, notices) is drawn): kept: the description is drawn in the fixed tool style only, never from the theme.

## Plan steps

- Step 4.23 — Description in the control menu (R-175; pins Steps 4.9 and 1.4).
- Step 4.24 — Descriptions through the adapter and in the reference plugin (R-175; regenerates Step 4.13's `S-03-control-menu.png`).
- Step 4.25 — [OWNER] S-03 mockup with the description, through `/ui-design`, and its comparison (R-175).

## Rework

None: the impact report of 2026-11-23 lists no ticket that writes these files or cites a changed requirement.

## Placement

Recommended `later`, Phase 4, beside the control menu it extends; nothing built or queued depends on it (impact report, 2026-11-23). It waits for the updated S-03 mockup from `/ui-design`.
