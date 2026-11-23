---
id: F-002
title: "Dim irrelevant controls"
status: ACCEPTED
placement: later
requirements: [R-173, R-174]
changes: []
serves: []
touches: ["crates/mutable-gui/src/editor/relevance.rs", "crates/mutable-gui/src/editor/mod.rs", "crates/mutable-gui/src/render/view.rs", "crates/mutable-gui/src/render/mod.rs", "crates/mutable-gui/src/render/drawn.rs", "crates/mutable-gui/src/render/custom.rs", "crates/mutable-gui/src/custom/context.rs", "crates/mutable-gui-nice/src/builder.rs", "examples/reference-plugin/src/lib.rs", "crates/mutable-gui/tests/editor_relevance.rs", "crates/mutable-gui/tests/render_dimmed.rs", "crates/mutable-gui/tests/perf_frame.rs", "crates/mutable-gui/tests/custom_dimmed.rs", "examples/reference-plugin/tests/relevance.rs", "design/UI.md", "design/DECISIONS.md"]
steps: ["4.20", "4.21", "4.22", "7.18"]
---
## Idea

Particle Arp migration, owner 2026-11-23: if mutable-gui requires features to make the migration work, then we should draft those. Dimming: controls the plugin marks irrelevant in the current mode are drawn dimmed (owner chose: dimmed, still operable).

## Behaviour

The developer gives the builder a relevance rule: a function that, from the current parameter values, names the parameters that have no effect right now (for Particle Arp, Cross-Talk outside Collision mode, Division while Tempo Sync is off, and about a dozen more). In perform mode, a control whose present bound parameters are all named is drawn at 45 % opacity, caption and value line included; it still responds to dragging, clicks, the keyboard and the control menu, so a musician can set a value before switching mode. The rule runs on the editor thread on a frame where a parameter value changed since the previous one, and once when the editor opens. Design mode draws every element at full opacity. Custom elements of the control category learn that they are dimmed and are drawn through a painter at the same opacity. Today every control looks equally live, whatever the mode.

## Requirements

- **R-173 — Irrelevant controls dimmed.** In perform mode, a control all of whose present bound parameters the developer's relevance rule names is drawn at 45 % opacity from the first frame after the value change that made it so, and still accepts input.
  Acceptance: with a rule naming "crossTalk" irrelevant unless "mode" is Collision, a knob bound to crossTalk is drawn at opacity 0.45 while mode is Clock and at 1.0 on the frame after mode becomes Collision; dragging it while dimmed records begin, set, end.
- **R-174 — Partly irrelevant controls stay lit.** A control bound to several parameters is dimmed only when every present one is irrelevant; displays and decorations are never dimmed; design mode dims nothing.
  Acceptance: an XY pad with X irrelevant and Y relevant is drawn at 1.0, and at 0.45 with both irrelevant; a label beside a dimmed knob stays at 1.0; in design mode the dimmed knob is drawn at 1.0.

Changed requirements: none. Decision D-43 is superseded in one part by D-50: "Element states are normal, hover, dragging, focused, unbound and dimmed; dimmed draws the normal look at 45 % opacity and changes no colour role." `design/UI.md` S-01 gains the state "dimmed: 45 % opacity, still operable"; the S-12 gallery keeps its five columns, since dimmed is the Normal column at 45 %.

## Data and interfaces

- Nothing is stored: the rule is code; no document, package or library file changes.
- Adapter: `MutableGui::builder(…).relevance(rule)` where `rule: impl Fn(&dyn ParamValues, &mut Irrelevant) + Send + Sync + 'static`. `ParamValues` offers `normalized(id) -> Option<f32>` and `step(id) -> Option<u32>` (for stepped parameters); `Irrelevant` is a set the editor clears and reuses each evaluation, with `insert(id)`, so a frame allocates nothing for it after the first.
- Core: `EditorConfig` gains `relevance: Option<Arc<RelevanceRule>>`; `render::view::VisualState` gains the `dimmed` flag; `DrawnElement` records it; `KindContext::state()` reports it and the custom kind's painter carries the opacity.

## Dependencies

None.

## Edges

- The rule names an id the plugin does not have: ignored.
- Automation flips relevance in the middle of a drag: the drag continues; the opacity changes on the next frame.
- A dimmed control has keyboard focus: the focus outline is drawn at full opacity so focus stays visible (R-109).
- The rule panics: like a custom kind's code (D-42), the library does not contain it.
- Cost: the rule runs at most once per frame and only after a value change; the 300-element frame test runs with a rule naming 150 parameters and stays within 4 ms.

## Acceptance

- The two Acceptance lines under "Requirements" above, and the frame-time test (Step 4.15) passing with a 150-name rule.

## Out of scope

- Hiding, moving or resizing controls by mode; layouts do not reflow.
- Making dimmed controls inert.
- Rules written by users or carried in packages (packages hold no code, D-21).
- Dimming in design mode, and dimming any tool.

## Invariants

- I-01 (The only library functions reachable from the audio thread are the tap producers'): not affected; the rule runs on the editor thread.
- I-02 (No library code calls nice-plug's `GuiContext::set_state`, because nice-plug): not affected.
- I-03 (`PersistedUi`'s serialize and deserialize and every `StateCell` method do only): not affected.
- I-04 (Parameter values change only through `ParamSource` begin, set and end, only in): kept: the rule only reads values, and input to a dimmed control takes the same gesture path.
- I-05 (`crates/mutable-gui` has `#![forbid(unsafe_code)]` and no dependency on nice-plug,): kept: `ParamValues` is a core trait the adapter implements over `ParamSource`.
- I-06 (Every `unsafe` block in `crates/mutable-gui-nice` carries a `// SAFETY:` comment): not affected; reading values reuses `NiceParamSource`.
- I-07 (Every byte sequence from outside the process passes `doc` validation before any): not affected.
- I-08 (No code path removes, renames or rebinds an element except a `Command` built from): not affected; dimming changes no element.
- I-09 (Elements store colours only as colour role names; colour values appear only in): kept: opacity is applied at drawing time; no colour is stored.
- I-10 (Every library file write goes to a temporary file in the destination folder and): not affected.
- I-11 (Analysis code (FFT, RMS, peak) is called only from the editor thread.): not affected.
- I-12 (The editor chrome (menu button, editor menu, notices) is drawn after all layout): kept: the chrome is never dimmed.
- I-13 (No crate in the dependency graph of `crates/mutable-gui` or): not affected.
- I-14 (Every document is encoded with its `format` and `version` first, and decoding a): not affected.
- I-15 (Element ids are unique within a layout; edits and moves keep ids; duplicate,): not affected.
- I-16 (While an unreadable saved state is kept, `StateCell` holds that string for saving): not affected; dimming works on the fallback layout like any other.
- I-17 (The tap reader flag is set only while a display or custom element bound to that): not affected; displays are never dimmed.
- I-18 (Custom kind code receives only a `KindContext`; no path hands it `ParamSource`,): kept: a custom kind learns only that it is dimmed. The rule itself is developer code that receives parameter values and nothing else.
- I-19 (Every gesture a custom element begins through `KindContext` is ended, by the element): not affected.
- I-20 (An unknown element's stored kind, version and props are encoded back exactly as they): not affected.
- I-21 (The tool layer (menu button, editor menu, design panels, dialogs, notices) is drawn): kept: no tool is dimmed.

## Plan steps

- Step 4.20 — Relevance rule evaluation (R-173).
- Step 4.21 — Dimmed drawing (R-173, R-174; pins Step 1.16's `editor_perform.rs`).
- Step 4.22 — Relevance through the adapter and in the reference plugin (R-173; pins Step 4.15's `perf_frame.rs`).
- Step 7.18 — Custom controls drawn dimmed (R-173).

## Rework

None: the impact report of 2026-11-23 lists no ticket that writes these files or cites a changed requirement.

## Placement

Recommended `later`: Phase 4 (perform mode) for the rule and drawing, Phase 7 for custom kinds; nothing built or queued depends on it (impact report, 2026-11-23).
