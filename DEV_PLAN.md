# Development plan: mutable-gui

Built from `design/`. Phases run in order; a phase closes when every gate under it is green
and its exit demo has been performed. Every step names its files, libraries, commands, tests
and gate: nothing is left for the executing agent to choose. Libraries come from
`design/STACK.md` only.

## How to read a step

- Builds: what is true after the step, with the names, values, texts and refusals it must use.
- Files: every file the step creates or edits. Test files come last. A `mod.rs` or `lib.rs`
  listed beside a new module receives only the `mod` or `pub use` line for it.
- Libraries: the `design/STACK.md` rows the step relies on. Every dependency is pinned in the
  root `Cargo.toml` in Phase 0; a later step only adds `name.workspace = true` to a member.
- Commands: run from the repository root, in the order given. A snapshot test is first run
  once with `UPDATE_SNAPSHOTS=1` in front of the command to write its picture, then without.
- Gate: the command whose exit code closes the step.
- Requirements: the `R-…` ids the step delivers or proves. A requirement listed in several
  steps is complete when the last of them is green.
- Screens: the `S-…` ids of `design/UI.md` the step builds.
- Guards: present where the step adds an operation over guarded state; it says, for every
  guard of the "Guards" table below, whether it applies and what the user sees when it does.
- Pins: present where the step changes something an earlier step's tests assert; it names
  those tests and how each assertion changes.

## Fixed names

These names are part of the plan. A step that mentions one of them uses it exactly.

### Layout

| Short form | Path |
|---|---|
| core | `crates/mutable-gui/` (package `mutable-gui`, library `mutable_gui`) |
| core tests | `crates/mutable-gui/tests/` |
| fixtures | `crates/mutable-gui/tests/fixtures/` (`v1/` valid documents, `invalid/` one document per refusal) |
| adapter | `crates/mutable-gui-nice/` (package `mutable-gui-nice`, library `mutable_gui_nice`) |
| testkit | `crates/mutable-gui-testkit/` (package `mutable-gui-testkit`, `publish = false`): fakes and harness helpers, used only as a dev-dependency; its feature `nice` adds `nice::RecordingGuiContext` and depends on nice-plug |
| reference | `examples/reference-plugin/` (package `mutable-gui-reference`, library `mutable_gui_reference`, `crate-type = ["cdylib", "lib"]`) |
| reference tests | `examples/reference-plugin/tests/`; every screen snapshot test lives here, sharing `examples/reference-plugin/tests/common/mod.rs` |
| snapshots | `examples/reference-plugin/tests/snapshots/` (screens) and `crates/mutable-gui/tests/snapshots/` (element and component pictures) |
| xtask | `xtask/` (package `xtask`); `cargo xtask …` is the alias in `.cargo/config.toml` |
| schemas | `schema/` |
| bundle | `target/bundled/mutable-gui-reference.clap` |
| check sheets | `docs/qa/phase-NN.md` (one per phase, written by an afk step, signed by the owner) |

### Identifiers

| Thing | Value |
|---|---|
| Reference plugin `NAME`, `VENDOR`, `CLAP_ID`, version | `Reference FX`, `mutable-gui`, `org.mutable-gui.reference`, `0.1.0` |
| Reference custom kind | id `org.mutable-gui.reference.transfer`, version 1, palette name `Transfer curve`, category display, icon `ICON_SHOW_CHART` |
| Reference taps | `out` (audio, 2 channels, 16,384 frames), `gr` (scalar, gain reduction in dB, ≥ 0) |
| Persisted-field key | `mutable-gui` |
| Built-in theme ids and names | `studio-dark` "Studio Dark", `studio-light` "Studio Light", `high-contrast` "High Contrast" |
| Built-in font names | `Inter`, `Inter Medium`, `Hack`, `Ubuntu Light` |
| egui font families of a theme | `mg-body`, `mg-heading`, `mg-value`; the tools use `mg-tool` (Inter) and `mg-tool-medium` (Inter Medium) |
| Library version constant | `mutable_gui::LIBRARY_VERSION` = the core package version |
| Schema versions | every format reads up to version 1: `mutable_gui::doc::SUPPORTED_VERSION` = 1 |

### Core public surface

`EditorState::frame(&mut self, ui: &mut egui::Ui, params: &dyn ParamSource)` is the per-frame
entry point. egui 0.37 hands an application a top-level `Ui` (`Context::run_ui`), so the
`frame(&egui::Context)` of `design/ARCHITECTURE.md` becomes this signature; `ui.ctx()` is the
context. `docs/ARCHITECTURE.md` records the difference.

Every core module this plan names is `pub`, so integration tests and the testkit reach it. The
surface adopters build on is the adapter's `MutableGui` builder and `PersistedUi`, and the core's
`TapRegistry`, tap producers, `ElementKind` with its property and context types; the README
documents only these.

| Item | Module | Introduced |
|---|---|---|
| `ParamSource`, `ParamInfo`, `ParamKind` | `params` | Step 1.4 |
| `generate::layout(plugin_name, &[ParamInfo]) -> Layout` | `generate` | Step 1.5 |
| `theme::builtin(id) -> Theme`, `theme::contrast(a, b) -> f32` | `theme` | Step 1.6 |
| `doc::decode_instance`, `doc::encode_instance` | `doc` | Step 1.3 |
| `doc::decode_package`, `doc::encode_package`, `doc::decode_elements`, `doc::encode_elements` | `doc` | Steps 2.5, 2.6 |
| `StateCell` | `persist` | Step 1.15 |
| `TapRegistry`, `AudioTapProducer`, `ScalarTapProducer` | `taps` | Steps 3.1–3.3 |
| `edit::Command`, `edit::apply`, `edit::UndoStack` | `edit` | Steps 5.1, 5.2 |
| `ElementKind`, `KindRegistry`, `KindContext` | `custom` | Steps 7.1, 7.4 |
| `Storage`, `FsStorage`, `FileDialog`, `RfdDialog` | `library` | Steps 8.1, 8.6 |

### Test commands

| Kind | Command form |
|---|---|
| core integration test | `cargo test -p mutable-gui --test <file stem>` |
| adapter test | `cargo test -p mutable-gui-nice --test <file stem>` |
| reference plugin test | `cargo test -p mutable-gui-reference --test <file stem>` |
| xtask test | `cargo test -p xtask --test <file stem>` |
| everything except timing bounds | `cargo test --workspace` |
| timing bounds (release) | `cargo test --workspace --release perf_` |
| benchmark report (not a gate) | `cargo bench -p mutable-gui --bench <file stem>` |
| CLAP validation | `cargo xtask bundle mutable-gui-reference --release && sh tools/validate-clap.sh` |

Timing tests are named `perf_*`, carry `#[cfg_attr(debug_assertions, ignore = "timing bound; run with --release")]`
and run in the release command only. Allocation tests live in files named `alloc_*.rs`, each
with `#[global_allocator] static A: nice_assert_no_alloc::AllocDisabler = nice_assert_no_alloc::AllocDisabler;`,
use the dev-dependency feature `warn_debug`, and assert `nice_assert_no_alloc::violation_count() == 0`;
they run in debug builds only, where the checker is active. Snapshot assertions go through
`mutable_gui_testkit::snapshot_on_macos(&mut harness, name)`, which calls `Harness::snapshot`
on macOS and returns without rendering elsewhere (D-46). Harnesses are built at
`pixels_per_point` 1.0 and at the mockup's `devpipe-viewport` size.

### Guards

| Id | Guard | Source |
|---|---|---|
| GD-1 | While an unreadable saved layout is kept, no command other than discarding it is accepted; design mode, layout import, theme choice, theme import and the Library submenu are unavailable (drawn disabled); controls operate; Reset to developer default first opens the discard confirmation. | R-119, R-150, I-16, D-29 |
| GD-2 | With design mode switched off by the developer, design mode, the Library submenu and package import are not offered and ⌘E does nothing; pages, theme choice, Import theme… and Reset to developer default are offered. | R-009, R-150 |
| GD-3 | Parameters change only through begin, set and end, only in perform mode; in design mode a press selects or moves and sends nothing. | I-04, R-068 |
| GD-4 | A layout holds 1–64 pages and at most 2,000 elements counting groups and every member; groups nest at most 16 deep; a text is at most 4,096 bytes; an instance holds at most 4 MiB of decoded assets across its layout and theme (D-11: "the worst case is 4 MiB per instance"). An operation that would break one is refused with a notice and changes nothing. | R-066, R-080, R-122, R-139, D-11 |
| GD-5 | Built-in themes and the "Developer default" entry are never overwritten or deleted; saving under their names asks for another name. | R-106, R-151 |
| GD-6 | Bytes from outside the process pass `doc` validation before any part reaches `edit::apply`; a refusal leaves layout, theme, library and undo history unchanged and raises one notice. | I-07, R-143 |
| GD-7 | A control ignores input for each parameter it is bound to that the plugin does not have; a control with no present parameter ignores all input. | R-037, R-038 |

### Reference plugin parameters

Declaration order is the order below. Normalized defaults follow from the plain defaults.
Units are the formatter's suffix. Every float uses nice-plug's `FloatRange::Skewed` with
`FloatRange::skew_factor(-2.0)` where marked "skewed", else `FloatRange::Linear`.

| Group (page) | Id | Name | Type and range | Default |
|---|---|---|---|---|
| (none) | `bypass` | Bypass | bool, `make_bypass()` | off |
| (none) | `input_gain` | Input Gain | float −24 to +24 dB | 0 dB |
| (none) | `mix` | Mix | float 0 to 100 % | 100 % |
| (none) | `quality` | Quality | enum Eco, Normal, High | Normal |
| Filter | `cutoff` | Cutoff | float 20 Hz to 20 kHz, skewed | 1,240 Hz |
| Filter | `resonance` | Resonance | float 0 to 100 % | 35 % |
| Filter | `filter_env_amount` | Env Amt | float −100 to +100 % | 0 % |
| Filter | `filter_mode` | Mode | enum LP, BP, HP, Notch | LP |
| Filter | `key_track` | Key Track | bool | on |
| Filter | `filter_drive` | Filter Drive | float 0 to 24 dB | 0 dB |
| Filter | `cutoff_lfo` | Cutoff LFO | float 0 to 100 % | 0 % |
| Filter | `filter_slope` | Slope | enum 12 dB, 24 dB | 12 dB |
| Filter | `filter_mix` | Filter Mix | float 0 to 100 % | 100 % |
| Filter | `hp_cutoff` | HP Cutoff | float 20 to 2,000 Hz, skewed | 20 Hz |
| Filter | `filter_spread` | Stereo Spread | float 0 to 100 % | 0 % |
| Filter | `filter_smooth` | Smoothing | float 1 to 100 ms | 10 ms |
| Drive | `drive` | Drive | float 0 to 24 dB | 8.8 dB |
| Drive | `oversample` | Oversample 2× | bool | off |
| Drive | `drive_type` | Drive Type | enum Tanh, Hard, Fold | Tanh |
| Drive | `drive_bias` | Bias | float −1 to +1 | 0 |
| Drive | `drive_tone` | Tone | float −100 to +100 % | 0 % |
| Drive | `drive_mix` | Drive Mix | float 0 to 100 % | 100 % |
| Drive | `drive_out` | Drive Output | float −24 to +24 dB | 0 dB |
| Drive | `drive_auto_gain` | Auto Gain | bool | off |
| Compressor | `threshold` | Threshold | float −60 to 0 dB | −18 dB |
| Compressor | `ratio` | Ratio | float 1 to 20 (": 1"), skewed | 4 |
| Compressor | `attack` | Attack | float 0.1 to 100 ms, skewed | 8 ms |
| Compressor | `release` | Release | float 10 to 1,000 ms, skewed | 120 ms |
| Compressor | `makeup` | Makeup | float 0 to 24 dB | 3.5 dB |
| Compressor | `knee` | Knee | float 0 to 24 dB | 6 dB |
| Compressor | `comp_mix` | Comp Mix | float 0 to 100 % | 100 % |
| Compressor | `sidechain_hp` | Sidechain HP | float 20 to 500 Hz, skewed | 20 Hz |
| Compressor | `comp_enable` | Compressor On | bool | on |
| Compressor | `lookahead` | Lookahead | float 0 to 10 ms | 0 ms |
| Compressor | `comp_detect` | Detector | enum Peak, RMS | Peak |
| Compressor | `comp_stereo_link` | Stereo Link | float 0 to 100 % | 100 % |
| Compressor | `comp_hold` | Hold | float 0 to 100 ms | 0 ms |
| Compressor | `sc_listen` | Sidechain Listen | bool | off |
| Compressor | `comp_range` | Range | float 0 to 60 dB | 60 dB |
| Compressor | `comp_auto_release` | Auto Release | bool | off |
| Compressor | `comp_character` | Character | enum Clean, Warm, Punch | Clean |
| Modulation | `lfo1_rate` | LFO 1 Rate | float 0.01 to 20 Hz, skewed | 2.40 Hz |
| Modulation | `lfo1_depth` | LFO 1 Depth | float 0 to 100 % | 35 % |
| Modulation | `lfo1_shape` | LFO 1 Shape | enum Sine, Triangle, Saw, Square | Sine |
| Modulation | `lfo1_sync` | LFO 1 Sync | bool | on |
| Modulation | `lfo2_rate` | LFO 2 Rate | float 0.01 to 20 Hz, skewed | 0.80 Hz |
| Modulation | `lfo2_depth` | LFO 2 Depth | float 0 to 100 % | 12 % |
| Modulation | `lfo2_shape` | LFO 2 Shape | enum Sine, Triangle, Saw, Square | Saw |
| Modulation | `lfo2_sync` | LFO 2 Sync | bool | off |
| Modulation | `env_attack` | Env Attack | float 0.1 to 500 ms, skewed | 12 ms |
| Modulation | `env_release` | Env Release | float 1 to 5,000 ms, skewed | 340 ms |
| Modulation | `mod_env_amount` | Env Amount | float −100 to +100 % | +40 % |
| Modulation | `mod_smooth` | Mod Smooth | float 0 to 100 ms | 5 ms |
| Output | `out_level` | Level | float −60 to +12 dB | −1.5 dB |
| Output | `out_pan` | Pan | float −100 to +100 ("C" at 0, "L n" / "R n" otherwise) | C |
| Output | `out_width` | Width | float 0 to 200 % | 100 % |
| Output | `out_limiter` | Limiter | bool | off |
| Output | `out_ceiling` | Ceiling | float −12 to 0 dB | −0.3 dB |
| Output | `out_dc` | DC Filter | bool | on |
| Output | `out_phase_l` | Invert L | bool | off |
| Output | `out_phase_r` | Invert R | bool | off |
| Output | `out_mono` | Mono | bool | off |
| Output | `out_trim` | Trim | float −12 to +12 dB | 0 dB |

63 parameters. Groups are nice-plug `#[nested(group = "…")]` structs; the generated pages are
"Reference FX", "Filter", "Drive", "Compressor", "Modulation", "Output".

### Colour slots per element kind

An element's `colours` map may hold only its kind's slot names; a slot it omits uses the
default role below. Values from `design/ui/kit.js`.

| Kind | Slot → default role |
|---|---|
| knob | `arc` → accent-1, `track` → border, `body` → surface-raised, `pointer` → text, `modulation` → modulation, `caption` → text, `value` → text-muted |
| macro | as knob, with `arc` → accent-5 |
| fader | `fill` → accent-2, `track` → border, `handle` → surface-raised, `modulation` → modulation, `caption` → text, `value` → text-muted |
| switch | `on` → accent-4, `off` → surface-raised, `outline` → border, `thumb` → background, `caption` → text-muted |
| xy_pad | `dot` → accent-2, `background` → surface-raised, `grid` → border, `caption` → text-muted |
| selector | `selected` → accent-1, `selected_text` → background, `background` → surface-raised, `outline` → border, `text` → text-muted |
| menu | `background` → surface-raised, `outline` → border, `text` → text |
| page_tabs | `current` → accent-1, `current_text` → text, `text` → text-muted, `outline` → border |
| oscilloscope | `trace` → accent-2, `trace_2` → accent-7, `background` → background, `grid` → border, `text` → text-muted |
| spectrum | `trace` → accent-7, `background` → background, `grid` → border, `text` → text-muted |
| level_meter | `low` → positive, `high` → warning, `peak` → text, `background` → surface-raised, `outline` → border, `value` → text-muted |
| gr_meter | `bar` → accent-1, `background` → surface-raised, `outline` → border, `value` → text-muted |
| label | `text` → text |
| panel | `outline` → border, `title` → text-muted |
| image, group, custom kinds | none (custom kinds declare colour-role properties instead) |

The "disabled" role replaces every slot of an unbound control (D-43); the "focus" role draws
the focus outline.

### Palette defaults

| Kind | Size (w × h) | Contents when added |
|---|---|---|
| knob | 72 × 100 | `binding` null |
| fader | 56 × 140 | `binding` null, `orientation` vertical |
| switch | 140 × 28 | `binding` null |
| xy_pad | 160 × 160 | `x` null, `y` null |
| macro | 80 × 106 | `targets` [null] |
| selector | 160 × 28 | `binding` null, `presentation` segments |
| menu | 130 × 28 | `label` "Menu", `items` [] |
| page_tabs | 328 × 30 | `orientation` horizontal |
| oscilloscope | 240 × 120 | `tap` null, `window_ms` 50 |
| spectrum | 240 × 120 | `tap` null, `fft_size` 4096, `floor_db` −90 |
| level_meter | 30 × 132 | `tap` null |
| gr_meter | 36 × 132 | `tap` null, `range_db` 24 |
| label | 140 × 28 | `text` "Label", `typeface` body, `size` 13, `align` left |
| panel | 240 × 160 | `surface` panel |
| image | 160 × 120 | `asset` null, `fit` contain |
| custom kind | `ElementKind::default_size()`, default 160 × 120 | each property at its declared default; binding and tap slots null |

### Icons

Material Symbols Rounded constants of egui_material_icons 0.9.0.

| Use | Constant |
|---|---|
| menu button (perform / design) | `ICON_MENU` / `ICON_EDIT` |
| palette: knob, fader, switch, xy_pad, macro, selector, menu, page_tabs | `ICON_DONUT_LARGE`, `ICON_HEIGHT`, `ICON_TOGGLE_ON`, `ICON_GRID_4X4`, `ICON_SETTINGS_INPUT_COMPONENT`, `ICON_VIEW_WEEK`, `ICON_ARROW_DROP_DOWN_CIRCLE`, `ICON_TAB` |
| palette: oscilloscope, spectrum, level_meter, gr_meter | `ICON_SHOW_CHART`, `ICON_EQUALIZER`, `ICON_BAR_CHART`, `ICON_COMPRESS` |
| palette: label, panel, image | `ICON_TITLE`, `ICON_CROP_LANDSCAPE`, `ICON_IMAGE` |
| toolbar: undo, redo, arrange, group, grid, hide tools, theme, library, done | `ICON_UNDO`, `ICON_REDO`, `ICON_DASHBOARD`, `ICON_GROUP_WORK`, `ICON_GRID_ON`, `ICON_VISIBILITY_OFF`, `ICON_PALETTE`, `ICON_FOLDER`, `ICON_CHECK` |
| arrange: align left, centre, right, top, middle, bottom | `ICON_ALIGN_HORIZONTAL_LEFT`, `ICON_ALIGN_HORIZONTAL_CENTER`, `ICON_ALIGN_HORIZONTAL_RIGHT`, `ICON_ALIGN_VERTICAL_TOP`, `ICON_ALIGN_VERTICAL_CENTER`, `ICON_ALIGN_VERTICAL_BOTTOM` |
| arrange: distribute, z-order, duplicate, delete | `ICON_HORIZONTAL_DISTRIBUTE`, `ICON_VERTICAL_DISTRIBUTE`, `ICON_FLIP_TO_FRONT`, `ICON_FLIP_TO_BACK`, `ICON_ARROW_UPWARD`, `ICON_ARROW_DOWNWARD`, `ICON_CONTENT_COPY`, `ICON_DELETE` |
| unbound, notices, dialogs, lists | `ICON_LINK_OFF`, `ICON_ERROR`, `ICON_WARNING`, `ICON_INFO`, `ICON_CLOSE`, `ICON_CHEVRON_RIGHT`, `ICON_ARROW_BACK`, `ICON_EXPAND_MORE`, `ICON_DRAG_INDICATOR`, `ICON_SEARCH`, `ICON_STAR`, `ICON_LOCK`, `ICON_ADD` |

### Notice texts

Every notice has a severity (error: red, `--tool-danger`; warning: amber, `--tool-warning`),
a bold summary and a detail; `“…”` are typographic quotes. `{file}` is the file name without
its folder.

| Cause | Summary | Detail |
|---|---|---|
| Invalid embedded default (R-002) | Built-in layout unreadable. | The plugin's own layout could not be read: {DocError}. Showing a generated layout. |
| Unreadable saved state (R-117) | This project's layout can't be read here. | {cause}. It is kept unchanged and saved back as it is; you are seeing the {user default \| developer default}, and editing is locked. — `{cause}` is "It was saved by a newer version of the plugin" for a newer schema and "It is damaged ({DocError})" otherwise. Actions: Keep it, Discard saved layout… |
| Refused import, paste or library load (R-084, R-137–R-143, R-157) | Import refused. (paste: Paste refused.; library: Couldn't open “{name}”.) | “{file}” {DocError}. Nothing was changed. |
| Cross-plugin import (R-131) | Made for another plugin. | “{package name}” comes from {source clap_id}. {n} controls found their parameters here; {m} are unbound. Actions: Show unbound, Undo import |
| Failed library write (R-134) | Couldn't save “{name}”. | {io error text}. Your library is unchanged. |
| Last page (R-065) | Page not deleted. | A layout needs at least one page. |
| Page limit (R-066) | Page not added. | A layout holds at most 64 pages. |
| Element limit (R-066) | Not added. | A layout holds at most 2,000 elements. |
| Nesting limit (R-080) | Not grouped. | Groups nest at most 16 deep. |
| Asset cap (R-122) | Not added. | Assets are limited to 4 MiB per instance; “{file}” would bring them to {x.x} MiB. Nothing was changed. |
| Asset format (R-123) | Not added. | “{file}” is not a PNG image. Images must be PNG files. (fonts: … is not a TrueType or OpenType font.) |
| Theme import without a theme | Import refused. | “{file}” holds no theme. Nothing was changed. |

`DocError`'s `Display` texts (Step 2.1 onward): "is {x.x} MiB; packages may be at most 8 MiB";
"holds {x.x} MiB of assets; at most 4 MiB are allowed"; "has more than 64 pages"; "has more than
2,000 elements"; "nests groups deeper than 16"; "has a text longer than 4,096 bytes at {path}";
"was made by a newer version ({found}; this one reads up to {supported})"; "holds the unknown
field “{name}”"; "lacks the colour role “{role}”"; "has a {font | PNG} asset that cannot be read
({id})"; "is not valid: {reason} at {path}"; "is not a mutable-gui document: {serde_json
message}"; "has a {kind id} element whose property “{name}” {reason}".

## Choices this plan makes where the specification is silent

Each is binding on the steps that use it. The owner ratified all thirty on 2026-11-22; they are
recorded as D-48 in `design/DECISIONS.md`.

| # | Choice | Used in |
|---|---|---|
| 1 | Binding slots and taps may be `null`: `binding`, `x`, `y`, each entry of `targets` (1–16 entries), a display's `tap`, an image's `asset`. A palette element starts with nulls (R-069). A null slot draws unbound with the value line "Not bound" (a display: "No signal"), ignores input, and is listed in the unbound list. | 1.1, 3.8–3.10, 5.10, 5.18 |
| 2 | Frames are integers: `x`, `y` from −4,000 to 8,000, `width`, `height` from 1 to 8,000; values outside are refused naming the field. User resizes keep at least 8 × 8 (R-074). | 1.1, 2.1, 5.7 |
| 3 | Group members keep absolute canvas frames; a group's frame is the bounding box of its members, recomputed by every command that changes a member. Selection holds top-level elements only. | 6.3–6.5 |
| 4 | Paste keeps the copied frames; incoming assets whose id the instance already has are not added again. | 6.6 |
| 5 | `SetLayout`, `SetTheme` and `SetAll` (whole-document replacements) drop the assets that neither the new layout nor the new theme refers to; no other command drops an asset, and the Type tab removes an unreferenced asset on request. A string equal to an asset id anywhere inside an unknown element's `props` counts as a reference (I-20). | 9.5, 9.7 |
| 6 | The generator gives an enum parameter with more than 32 values a knob, and leaves out the plugin-name page when every parameter is in a group and at least one group exists. | 1.5 |
| 7 | An instance state whose `current_page` names no page opens on the first page. | 1.3 |
| 8 | Undo keeps the last 200 steps. | 5.2 |
| 9 | A long press is 600 ms with the pointer within 4 logical px of where it went down; the menu button is "near" within 64 logical px of its centre. | 1.19, 4.9 |
| 10 | Library file names: the entry name with `/ \ : * ? " < > |`, control characters and a leading `.` replaced by `_`, plus `.mgui`; the listed name comes from the package's `name`. The user default is `layouts/<clap id>/.default.mgui` (a package with layout, theme and assets; its `name` is the entry it was set from, or "Current layout"); the suite default theme is `themes/.default.mgui` (a theme-only package). Listings skip names starting with `.`; the star marks the entry whose name equals the default's `name`. | 8.1–8.5 |
| 11 | "Use as my default" on a library layout entry stores that layout with the instance's current theme. Applying a library layout entry (the "Developer default" entry included) replaces the layout only; Reset to developer default replaces layout and theme. | 8.5, 8.10 |
| 12 | Editor menu "Export package…" writes the current layout and theme; a library entry's Export… writes that entry alone. | 8.6, 8.9, 8.10 |
| 13 | "Import theme…" applies only the package's theme, as one undoable change, and refuses a package with no theme. | 8.9 |
| 14 | The cross-plugin notice names the source CLAP id (packages carry no plugin name). | 8.7 |
| 15 | Packages are written with `created` as UTC `YYYY-MM-DDTHH:MM:SSZ` and no `author`; library dates show the file's UTC modification date as "20 Nov 2026". | 2.5, 8.3 |
| 16 | A host state load during a drag ends every open gesture and drops the drag before the new state is shown. | 2.15 |
| 17 | The S-02 small presentation (drill-in submenus) and the S-04 small presentation (compact toolbar, palette behind "+", bottom-sheet inspector) apply when the window is narrower than 520 logical px or lower than 420. | 5.9–5.11, 8.9, 8.10 |
| 18 | Built-in themes fill `canvas` and `display` with solid background, `panel` with solid surface, `control` with solid surface-raised; their typefaces are Inter, Inter and Hack (UI.md). | 1.6 |
| 19 | An element's `colours` may hold only its kind's slot names (table above); another name is refused naming it. | 1.1, 2.1 |
| 20 | Menu element `set` actions use a 0-based step index. | 4.5 |
| 21 | Font fallback chain for every family: the named font, then Inter, then Hack, then egui's emoji fonts; a missing glyph draws from the next font. | 1.7, 9.2 |
| 22 | An asset's decoded size is the length of its base64-decoded file bytes; the 4 MiB caps count those. | 2.4, 9.5 |
| 23 | Page tabs and menu elements open no control menu: they have no parameter value to reset, type or fine-adjust. | 4.9 |
| 24 | "Type value…" is offered for knobs, faders, switches and selectors; on XY pads and macros, which drive several parameters, it is drawn disabled. | 4.10 |
| 25 | Keyboard: on an XY pad Up and Down change Y, Left and Right change X; on page tabs Left and Right go to the previous and next page; Enter on a menu element opens its list. | 4.11 |
| 26 | Pages and elements are held as `Arc`; the undo stack keeps whole previous instance states, which share every unchanged page, element and asset. | 1.1, 5.2 |
| 27 | A design-mode drag previews the move and commits one command on release; each arrow-key press is one command. | 5.6 |
| 28 | egui-baseview 0.9.0 reads the clipboard only when ⌘V reaches the window and ignores `ViewportCommand::RequestPaste`, and the stack has no clipboard crate; so the Arrange popover's "Paste ⌘V" entry is drawn disabled with the hint "Press ⌘V in the plugin window". Every other shortcut action works from a menu. | 6.6 |
| 29 | The library preview of a layout entry draws its first page scaled into the preview area with the instance's active theme; a theme entry shows strips of its background, surface, text and eight accent colours. | 8.10 |
| 30 | A font asset is listed by the family name in its `name` table (read with skrifa), an image asset as "Image n (W × H)". | 9.7 |

## Phase 0 — Foundation

**Goal:** The repository builds, lints and tests from a clean clone with one real passing test in every test category (unit, property, harness interaction, snapshot picture, allocation, timing, benchmark, adapter, CLAP validation); every later phase only adds to it.

### Step 0.1 — Ignore rules

- Builds: `.gitignore` keeps its three lines and adds `target/`, `.DS_Store`, `*.new.png`, `*.diff.png`, `*.old.png` (egui_kittest writes these beside a failing snapshot), `/schema/*.tmp`.
- Files: `.gitignore`
- Libraries: git
- Commands: `git check-ignore -q target && git check-ignore -q crates/mutable-gui/tests/snapshots/a.new.png`
- Tests: none
- Gate: G0.1 — `git check-ignore -q target && git check-ignore -q crates/mutable-gui/tests/snapshots/a.new.png` exits 0
- Requirements: none
- Screens: none

### Step 0.2 — Prerequisite installer and environment check

- Builds: `setup-prerequisites.sh` is copied from `tools/devpipe/templates/setup-prerequisites.sh` and gains one `step` line: "the Rust 1.99.1 toolchain with rustfmt and clippy, pinned by rust-toolchain.toml" with `rustup toolchain install 1.99.1 --profile minimal --component rustfmt --component clippy`. `tools/check-env.sh` (POSIX sh) exits 0 only when `rustc +1.99.1 --version` contains `1.99.1`, `cargo +1.99.1 fmt --version` and `cargo +1.99.1 clippy --version` exit 0, `clap-validator --version` contains `0.4.1`, `uname -s` is `Darwin` and `uname -m` is `arm64`; it prints one line per failed check, and for a missing clap-validator the line "clap-validator 0.4.1 must be on PATH".
- Files: `setup-prerequisites.sh`, `tools/check-env.sh`
- Libraries: rustc, cargo, clap-validator
- Commands: `sh -n setup-prerequisites.sh && sh -n tools/check-env.sh`
- Tests: none
- Gate: G0.2 — `sh -n setup-prerequisites.sh && sh -n tools/check-env.sh` exits 0
- Requirements: none
- Screens: none

### Step 0.3 — [OWNER] Run the prerequisite installer

- Builds: the owner runs `sh setup-prerequisites.sh` once on the development Mac, answering `y`; `sh tools/check-env.sh` then prints nothing and exits 0.
- Files: `setup-prerequisites.sh`
- Libraries: rustc, clap-validator
- Commands: `sh setup-prerequisites.sh`, then `sh tools/check-env.sh`
- Tests: none
- Gate: G0.3 — `sh tools/check-env.sh` exits 0
- Requirements: none
- Screens: none

### Step 0.4 — Workspace, toolchain pin and core crate

- Builds: `rust-toolchain.toml` pins `channel = "1.99.1"`, `components = ["rustfmt", "clippy"]`, `profile = "minimal"`. `rustfmt.toml` sets `edition = "2024"` and `max_width = 100`. The root `Cargo.toml` is a virtual workspace with `resolver = "3"`, `members = ["crates/*", "examples/*", "xtask"]`, `[workspace.package]` (`version = "0.1.0"`, `edition = "2024"`, `rust-version = "1.95"`, `license = "MIT OR Apache-2.0"`, `publish = false`), `[workspace.dependencies]` with every crate row of `design/STACK.md` pinned with `=` (nice-plug `default-features = false, features = ["editor", "zstd"]`; nice-plug-egui `features = ["opengl"]`; uuid `features = ["v4", "serde"]`; egui_kittest `features = ["snapshot", "wgpu"]`; nice-assert-no-alloc `features = ["warn_debug"]`; serde `features = ["derive", "rc"]` (pages and assets are shared as `Arc` for undo, Step 5.2); schemars, base64, thiserror, arc-swap, rtrb, realfft, png, skrifa, rfd, dirs, proptest, criterion, tempfile, egui, egui_material_icons, nice-plug-xtask), `[workspace.lints.clippy]` `all` and `pedantic` at `warn` with `priority = -1`, and `unwrap_used`, `expect_used`, `panic`, `todo`, `unimplemented`, `dbg_macro`, `print_stdout`, `print_stderr` at `deny`. `clippy.toml` holds exactly `allow-unwrap-in-tests = true`, `allow-expect-in-tests = true` and `allow-panic-in-tests = true` (D-49). The core crate's `Cargo.toml` inherits the workspace package fields and `[lints] workspace = true`, depends on egui, serde, serde_json, thiserror; `src/lib.rs` starts with `#![forbid(unsafe_code)]` and exports `pub const LIBRARY_VERSION: &str = env!("CARGO_PKG_VERSION");`. `Cargo.lock` is created and committed.
- Files: `rust-toolchain.toml`, `rustfmt.toml`, `clippy.toml`, `Cargo.toml`, `Cargo.lock`, `crates/mutable-gui/Cargo.toml`, `crates/mutable-gui/src/lib.rs`
- Libraries: rustc, cargo, rustfmt, clippy, egui, serde, serde_json, thiserror
- Commands: `cargo build -p mutable-gui && cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings`
- Tests: none
- Gate: G0.4 — `cargo build -p mutable-gui && cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings` exits 0
- Requirements: none
- Screens: none

### Step 0.5 — Testkit crate with harness and snapshot helpers

- Builds: `crates/mutable-gui-testkit` depends on the core (path) and egui_kittest (features `snapshot`, `wgpu`). Its `lib.rs` exports `pub fn ui_harness<'a>(size: egui::Vec2, app: impl FnMut(&mut egui::Ui) + 'a) -> egui_kittest::Harness<'a>` (builder `with_size(size)`, `with_pixels_per_point(1.0)`) and `pub fn snapshot_on_macos(harness: &mut egui_kittest::Harness<'_, impl Sized>, name: &str)` (calls `harness.snapshot(name)` when `cfg!(target_os = "macos")`, else returns). The core's `Cargo.toml` gains `[dev-dependencies] mutable-gui-testkit = { path = "../mutable-gui-testkit" }`. `tests/harness_smoke.rs` has two tests: `click_counts` builds a harness with a button "Press", clicks it through `harness.get_by_label("Press").click()`, runs, and asserts a counter of 1 (interaction category); `smoke_picture` paints a 64 × 64 rectangle filled `#5AABFF` on a 96 × 96 harness and calls `snapshot_on_macos(&mut harness, "foundation-smoke")` (snapshot category), writing `crates/mutable-gui/tests/snapshots/foundation-smoke.png`.
- Files: `crates/mutable-gui-testkit/Cargo.toml`, `crates/mutable-gui-testkit/src/lib.rs`, `crates/mutable-gui/Cargo.toml`, `crates/mutable-gui/tests/harness_smoke.rs`, `crates/mutable-gui/tests/snapshots/foundation-smoke.png`
- Libraries: egui_kittest, egui, wgpu, egui-wgpu
- Commands: `cargo test -p mutable-gui --test harness_smoke`
- Tests: `crates/mutable-gui/tests/harness_smoke.rs`
- Gate: G0.5 — `cargo test -p mutable-gui --test harness_smoke` exits 0
- Requirements: none
- Screens: none

### Step 0.6 — Property, allocation, timing and benchmark categories

- Builds: `tests/prop_smoke.rs` runs a proptest with `ProptestConfig { cases: 256, ..ProptestConfig::default() }` asserting that `serde_json::to_string` then `from_str` of any `(u32, String)` pair returns the pair. `tests/alloc_smoke.rs` installs `AllocDisabler`, asserts `violation_count() == 0` after `assert_no_alloc(|| 1 + 1)` and `violation_count() > 0` after `assert_no_alloc(|| drop(Vec::<u8>::with_capacity(8)))` (proves the checker counts). `tests/perf_smoke.rs` holds `perf_smoke_timer`: summing 1,000,000 `u64` in a release build takes under 50 ms. `benches/smoke.rs` is a criterion benchmark of the same sum, declared `[[bench]] name = "smoke" harness = false`. The core gains dev-dependencies proptest, criterion, nice-assert-no-alloc.
- Files: `crates/mutable-gui/Cargo.toml`, `crates/mutable-gui/tests/prop_smoke.rs`, `crates/mutable-gui/tests/alloc_smoke.rs`, `crates/mutable-gui/tests/perf_smoke.rs`, `crates/mutable-gui/benches/smoke.rs`
- Libraries: proptest, nice-assert-no-alloc, criterion
- Commands: `cargo test -p mutable-gui --test prop_smoke --test alloc_smoke && cargo test -p mutable-gui --release --test perf_smoke perf_ && cargo bench -p mutable-gui --bench smoke --no-run`
- Tests: `crates/mutable-gui/tests/prop_smoke.rs`, `crates/mutable-gui/tests/alloc_smoke.rs`, `crates/mutable-gui/tests/perf_smoke.rs`
- Gate: G0.6 — `cargo test -p mutable-gui --test prop_smoke --test alloc_smoke && cargo test -p mutable-gui --release --test perf_smoke perf_ && cargo bench -p mutable-gui --bench smoke --no-run` exits 0
- Requirements: none
- Screens: none

### Step 0.7 — Adapter crate

- Builds: `crates/mutable-gui-nice` inherits the workspace fields and lints, depends on the core, nice-plug and nice-plug-egui; `lib.rs` re-exports `pub use mutable_gui;` and holds no `unsafe` yet. `tests/smoke.rs` asserts `mutable_gui_nice::mutable_gui::LIBRARY_VERSION == "0.1.0"`.
- Files: `crates/mutable-gui-nice/Cargo.toml`, `crates/mutable-gui-nice/src/lib.rs`, `crates/mutable-gui-nice/tests/smoke.rs`
- Libraries: nice-plug, nice-plug-egui
- Commands: `cargo test -p mutable-gui-nice --test smoke`
- Tests: `crates/mutable-gui-nice/tests/smoke.rs`
- Gate: G0.7 — `cargo test -p mutable-gui-nice --test smoke` exits 0
- Requirements: none
- Screens: none

### Step 0.8 — Build helper

- Builds: `xtask` depends on nice-plug-xtask; `main.rs` dispatches `bundle` and `bundle-universal` to `nice_plug_xtask::main()`; other subcommands are added by later steps. `.cargo/config.toml` has `[alias] xtask = "run --package xtask --release --"`.
- Files: `xtask/Cargo.toml`, `xtask/src/main.rs`, `.cargo/config.toml`
- Libraries: nice-plug-xtask
- Commands: `cargo xtask bundle --help 2>&1 | grep -q bundle`
- Tests: none
- Gate: G0.8 — `cargo build -p xtask` exits 0
- Requirements: none
- Screens: none

### Step 0.9 — Reference plugin skeleton and CLAP validation

- Builds: `examples/reference-plugin` (package `mutable-gui-reference`, `crate-type = ["cdylib", "lib"]`) defines `RefFx` implementing nice-plug `Plugin` and `ClapPlugin` with the identifiers of "Fixed names", one stereo in/out `AudioIOLayout`, a `RefParams` holding only `bypass`, `type Editor = ()`, processing as a pass-through, exported with `nice_export_clap!(RefFx);`. `tools/validate-clap.sh` runs `clap-validator -v quiet validate --json --only-failed target/bundled/mutable-gui-reference.clap`, saves the output to `target/clap-validator.json`, and exits 1 unless `python3 -c` finds `results` is an empty list in it (clap-validator 0.4.1 prints `{"results": []}` when nothing failed). `tests/process_smoke.rs` runs the pass-through on a 64-frame buffer of a ramp and asserts output equals input.
- Files: `examples/reference-plugin/Cargo.toml`, `examples/reference-plugin/src/lib.rs`, `tools/validate-clap.sh`, `examples/reference-plugin/tests/process_smoke.rs`
- Libraries: nice-plug, nice-plug-xtask, clap-validator
- Commands: `cargo test -p mutable-gui-reference --test process_smoke && cargo xtask bundle mutable-gui-reference --release && sh tools/validate-clap.sh`
- Tests: `examples/reference-plugin/tests/process_smoke.rs`
- Gate: G0.9 — `cargo xtask bundle mutable-gui-reference --release && sh tools/validate-clap.sh` exits 0
- Requirements: none
- Screens: none

### Step 0.10 — Bundled Inter font

- Builds: `tools/fetch-inter.sh` downloads `https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip` with `curl -fL` into a new temporary directory, lists it with `unzip -Z1`, extracts the first entries whose base names are exactly `Inter-Regular.ttf`, `Inter-Medium.ttf` and `LICENSE.txt` (`unzip -j`), copies them to `crates/mutable-gui/assets/` as `Inter-Regular.ttf`, `Inter-Medium.ttf`, `OFL.txt`, and writes `SHA256SUMS` with `shasum -a 256` of the three files. The script exits non-zero when any of the three is absent from the archive.
- Files: `tools/fetch-inter.sh`, `crates/mutable-gui/assets/Inter-Regular.ttf`, `crates/mutable-gui/assets/Inter-Medium.ttf`, `crates/mutable-gui/assets/OFL.txt`, `crates/mutable-gui/assets/SHA256SUMS`
- Libraries: Inter
- Commands: `sh tools/fetch-inter.sh && (cd crates/mutable-gui/assets && shasum -a 256 -c SHA256SUMS)`
- Tests: none
- Gate: G0.10 — `(cd crates/mutable-gui/assets && shasum -a 256 -c SHA256SUMS)` exits 0
- Requirements: none
- Screens: none

### Step 0.11 — Stack check

- Builds: `tools/check-stack.py` reads `design/STACK.md` rows and `Cargo.lock`, and exits 1 printing each mismatch when a crate row's version differs from the locked version of that crate (rows that are not crates in the lockfile, such as rustc, Bitwig Studio or Inter, are skipped by name: rustc, cargo, rustfmt, clippy, Inter, clap-validator, Bitwig Studio, git, python3, macOS).
- Files: `tools/check-stack.py`
- Libraries: python3
- Commands: `python3 tools/check-stack.py`
- Tests: none
- Gate: G0.11 — `python3 tools/check-stack.py` exits 0
- Requirements: none
- Screens: none

### Step 0.12 — Project pre-commit hook

- Builds: `.githooks/pre-commit.project` is an executable POSIX shell script running `cargo fmt --all -- --check` and then `cargo clippy --workspace --all-targets -- -D warnings`, exiting with the first failing status.
- Files: `.githooks/pre-commit.project`
- Libraries: git, rustfmt, clippy
- Commands: `test -x .githooks/pre-commit.project && .githooks/pre-commit.project`
- Tests: none
- Gate: G0.12 — `test -x .githooks/pre-commit.project && .githooks/pre-commit.project` exits 0
- Requirements: none
- Screens: none

### Step 0.13 — Continuous-integration workflow file

- Builds: `.github/workflows/ci.yml` runs on `push` and `pull_request` with three jobs: `macos` on `macos-14` (`cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets -- -D warnings`, `cargo test --workspace`), `linux` on `ubuntu-24.04` (installs `libx11-xcb-dev libxcb1-dev libxcb-dri2-0-dev libxcb-icccm4-dev libxcursor-dev libxkbcommon-dev libxcb-shape0-dev libxcb-xfixes0-dev libgl-dev libasound2-dev` with apt, then `cargo test --workspace`), `windows` on `windows-2022` (`cargo test --workspace`). Each job installs the toolchain from `rust-toolchain.toml` with `rustup show`. The repository has no remote today; the file runs once one is added.
- Files: `.github/workflows/ci.yml`
- Libraries: none
- Commands: `grep -q "ubuntu-24.04" .github/workflows/ci.yml && grep -q "windows-2022" .github/workflows/ci.yml && grep -q "cargo test --workspace" .github/workflows/ci.yml`
- Tests: none
- Gate: G0.13 — `grep -q "ubuntu-24.04" .github/workflows/ci.yml && grep -q "windows-2022" .github/workflows/ci.yml && grep -q "cargo test --workspace" .github/workflows/ci.yml` exits 0
- Requirements: none
- Screens: none

### Step 0.14 — README and changelog at Phase 0 truth

- Builds: `README.md` and `CHANGELOG.md` are written from `tools/devpipe/templates/docs/` with every blank filled: what mutable-gui is (from the specification's Problem), the quick start (`sh tools/check-env.sh`, `cargo test --workspace`, `cargo xtask bundle mutable-gui-reference --release`, `sh tools/validate-clap.sh`), the repository map with one row per crate, `examples/reference-plugin`, `xtask`, `tools`, `design`, `docs`, the licences (MIT OR Apache-2.0; Inter under SIL OFL 1.1 in `crates/mutable-gui/assets/OFL.txt`). Every command in them was run in this phase.
- Files: `README.md`, `CHANGELOG.md`
- Libraries: none
- Commands: `grep -q "## Quick start" README.md && grep -q "## Unreleased" CHANGELOG.md && ! grep -q "[<][<]" README.md CHANGELOG.md`
- Tests: none
- Gate: G0.14 — `grep -q "## Quick start" README.md && grep -q "## Unreleased" CHANGELOG.md && ! grep -q "[<][<]" README.md CHANGELOG.md` exits 0
- Requirements: none
- Screens: none

### Step 0.15 — Architecture, runbook and testing documents at Phase 0 truth

- Builds: written from `tools/devpipe/templates/docs/` with every blank filled. `docs/ARCHITECTURE.md` lists the crates that exist, I-05 as the invariant in force (`#![forbid(unsafe_code)]` in the core), and under "Differences from the design" the `EditorState::frame` signature of "Fixed names". `docs/RUNBOOK.md` covers the environment (`setup-prerequisites.sh`, `tools/check-env.sh`), build and bundle, installing the bundle by copying it to `~/Library/Audio/Plug-Ins/CLAP/`, `tools/fetch-inter.sh`, and the pipeline commands. `docs/TESTING.md` lists the categories and commands of the "Test commands" table, the snapshot procedure (`UPDATE_SNAPSHOTS=1` once, commit the PNG), and the fakes allowed: `FakeParamSource`, `FakeFileDialog`, `RecordingGuiContext`, `Storage` over a temporary directory, clipboard events.
- Files: `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, `docs/TESTING.md`
- Libraries: none
- Commands: `grep -q "## 4. Invariants in force" docs/ARCHITECTURE.md && grep -q "## 2. Build, run, install" docs/RUNBOOK.md && grep -q "## 2. Commands" docs/TESTING.md && ! grep -q "[<][<]" docs/ARCHITECTURE.md docs/RUNBOOK.md docs/TESTING.md`
- Tests: none
- Gate: G0.15 — `grep -q "## 4. Invariants in force" docs/ARCHITECTURE.md && grep -q "## 2. Build, run, install" docs/RUNBOOK.md && grep -q "## 2. Commands" docs/TESTING.md && ! grep -q "[<][<]" docs/ARCHITECTURE.md docs/RUNBOOK.md docs/TESTING.md` exits 0
- Requirements: none
- Screens: none

**Exit demo:** On a fresh clone, following `README.md` and `docs/RUNBOOK.md` only: `sh tools/check-env.sh`, `cargo test --workspace`, `cargo test --workspace --release perf_`, `cargo xtask bundle mutable-gui-reference --release` and `sh tools/validate-clap.sh` each exit 0; copying the bundle into `~/Library/Audio/Plug-Ins/CLAP/` makes "Reference FX" appear in Bitwig Studio 5.3.13, where it passes audio unchanged.

## Phase 1 — Walking skeleton: the generated interface in Bitwig

**Goal:** Reference FX opens in Bitwig on its generated default (S-13); knobs, switches, dropdown selectors and page tabs change their parameters as single host gestures and follow automation; the window scales the canvas from 0.5 to 4.0 with bars; the menu button lists the pages; layout, theme, current page and window size survive a project save and reopen.

### Step 1.1 — Layout model

- Builds: `model::layout` and `model::element` hold plain data types with `Debug, Clone, PartialEq`; every struct that serde reads directly carries `#[serde(deny_unknown_fields)]` and snake_case fields. `Layout { canvas: Size, grid: Grid, pages: Vec<Arc<Page>> }`, `Size { width: u32, height: u32 }`, `Grid { step: u32, snap: bool }`, `Page { id: PageId, name: String, elements: Vec<Arc<Element>> }` (elements and pages are shared through `Arc` so undo copies only what changes, choice 26), `PageId(Uuid)`, `ElementId(Uuid)`, `AssetId(Uuid)`, `Frame { x: i32, y: i32, width: u32, height: u32 }` (choice 2), `Binding { param: String, min: f32, max: f32, reversed: bool }`. `Element { id: ElementId, frame: Frame, colours: BTreeMap<String, ColourRole>, shape: Option<ShapeOverrides>, body: ElementBody }` (encoded and decoded by `doc`, Step 1.3). `ElementBody` has one variant per data-model kind, each wrapping a body struct with serde derives: `Knob { binding: Option<Binding>, caption: Option<String> }`, `Fader { binding, orientation: Orientation, caption }`, `Switch { binding, caption }`, `XyPad { x: Option<Binding>, y: Option<Binding>, caption }`, `Macro { targets: Vec<Option<Binding>>, caption }`, `Selector { binding, presentation: Presentation, caption }`, `Menu { label: String, items: Vec<MenuItem> }`, `PageTabs { orientation: Orientation }`, `Oscilloscope { tap: Option<String>, window_ms: u32 }`, `Spectrum { tap, fft_size: u32, floor_db: i32 }`, `LevelMeter { tap }`, `GrMeter { tap, range_db: u32 }`, `Label { text: String, typeface: TypefaceRole, size: u32, align: Align, tracking: Option<f32> }`, `Panel { surface: SurfaceRole, title: Option<String> }`, `Image { asset: Option<AssetId>, fit: Fit }`, `Group { children: Vec<Arc<Element>> }`, `Custom(CustomElement { kind: String, kind_version: u32, props: serde_json::Map<String, serde_json::Value>, status: CustomStatus })` where `CustomStatus` (`Known`, `Unknown`) is never serialized. `caption`, `title` and `tracking` are skipped when `None` (D-47); `binding`, taps and assets serialize `null` when `None` (choice 1). `MenuItem { text: String, action: MenuAction }`, `MenuAction` externally tagged snake_case: `{"open_page": "<page id>"}` or `{"set": {"param": "<id>", "step": <u32>}}`. `ShapeOverrides { radius, border, knob_style, track_thickness, handle_size }`, all `Option`, skipped when `None`. `ElementBody::kind_name()` returns the frozen names (`knob` … `group`, or the custom id). `Element::count()` counts the element and every member at any depth; `Element::depth()` is 1 for a non-group and 1 + the deepest member for a group; `Layout::element_count()` sums pages. This step also creates `model/theme.rs` holding the enums `ColourRole`, `SurfaceRole`, `TypefaceRole` and `KnobStyle` exactly as Step 1.2 describes them; Step 1.2 adds the rest of the theme model.
- Files: `crates/mutable-gui/src/model/mod.rs`, `crates/mutable-gui/src/model/layout.rs`, `crates/mutable-gui/src/model/element.rs`, `crates/mutable-gui/src/model/theme.rs`, `crates/mutable-gui/src/lib.rs`, `crates/mutable-gui/tests/model_layout.rs`
- Libraries: serde, serde_json, uuid
- Commands: `cargo test -p mutable-gui --test model_layout`
- Tests: `crates/mutable-gui/tests/model_layout.rs` (kind names of all 16 built-in bodies; `Knob { binding: None, caption: None }` serializes `{"binding":null}`; `MenuAction` JSON shapes; `Binding` with an extra field fails; a group of two knobs counts 3 with depth 2)
- Gate: G1.1 — `cargo test -p mutable-gui --test model_layout` exits 0
- Requirements: none
- Screens: none

### Step 1.2 — Theme, instance and package model

- Builds: `model::theme` (whose four enums Step 1.1 created) holds `ColourRole` (the 20 roles of the data model, serde names `background`, `surface`, `surface-raised`, `border`, `text`, `text-muted`, `accent-1` … `accent-8`, `positive`, `warning`, `negative`, `modulation`, `focus`, `disabled`; `ColourRole::ALL` in that order; `Ord` follows it), `Rgba([u8; 4])` serialized as lowercase `#rrggbbaa` and parsed from it, `SurfaceRole` (`canvas`, `panel`, `control`, `display`), `Fill` (`{"solid": role}`, `{"gradient": {"from", "to", "angle_deg"}}`, `{"grain": {"role", "amount"}}`, `{"image": asset id}`), `TypefaceRole` (`body`, `heading`, `value`), `ShapeTokens { radius, border, knob_style, track_thickness, handle_size }`, `KnobStyle` (`arc`, `pointer`, `filled`), `Theme { name: String, colours: BTreeMap<ColourRole, Rgba>, typefaces: BTreeMap<TypefaceRole, String>, surfaces: BTreeMap<SurfaceRole, Fill>, shape: ShapeTokens }`. `model::instance` holds `Asset { id: AssetId, kind: AssetKind, data: Arc<str> }` (`AssetKind` `font` | `png`, `data` the base64 text as stored), `WindowSize { width: u32, height: u32 }`, `InstanceState { layout: Layout, theme: Theme, assets: Vec<Asset>, current_page: PageId, window: WindowSize }`, `Package { name, author: Option<String>, created: String, source: Source { clap_id, plugin_version, library_version }, layout: Option<Layout>, theme: Option<Theme>, assets: Vec<Asset> }`, `ElementsDoc { elements: Vec<Element>, assets: Vec<Asset> }`.
- Files: `crates/mutable-gui/src/model/theme.rs`, `crates/mutable-gui/src/model/instance.rs`, `crates/mutable-gui/src/model/mod.rs`, `crates/mutable-gui/tests/model_theme.rs`
- Libraries: serde, serde_json, uuid
- Commands: `cargo test -p mutable-gui --test model_theme`
- Tests: `crates/mutable-gui/tests/model_theme.rs` (role names and order; `Rgba` round trip of `#ff9f43ff`; `#ff9f43` without alpha fails; every `Fill` shape)
- Gate: G1.2 — `cargo test -p mutable-gui --test model_theme` exits 0
- Requirements: none
- Screens: none

### Step 1.3 — Instance document encode and decode

- Builds: `doc::error::DocError` (thiserror) has a variant for every `DocError` text of "Fixed names" with those exact `Display` strings; each carries a JSON path where the text names one. `doc::encode_instance(&InstanceState) -> String` writes `{"format":"mutable-gui/instance","version":1,…}` with `layout` and `theme` as nested documents that also start with their own `format` (`mutable-gui/layout`, `mutable-gui/theme`) and `version`. `doc::element` encodes an element as `id`, `kind`, `frame`, `colours`, `shape` (omitted when `None`), then the body fields; a custom element as `id`, `kind`, `kind_version`, `frame`, `colours`, `props`. `doc::decode_instance(&str) -> Result<InstanceState, DocError>` parses to `serde_json::Value`, checks `format` (a different one is `Invalid` at `format`) and `version` (above `SUPPORTED_VERSION` is `Newer { found, supported: 1 }`), then reads each part with `serde_json::from_value`; an element's `kind` selects its body struct (the object without the common fields), a kind containing `.` becomes `Custom` with `status: Unknown` and `props` kept as read, any other unknown kind is `Invalid` naming it. A `current_page` that names no page becomes the first page's id (choice 7). Limits, migrations and assets arrive in Phase 2.
- Files: `crates/mutable-gui/src/doc/mod.rs`, `crates/mutable-gui/src/doc/error.rs`, `crates/mutable-gui/src/doc/element.rs`, `crates/mutable-gui/src/doc/instance.rs`, `crates/mutable-gui/tests/doc_instance.rs`
- Libraries: serde, serde_json, thiserror, uuid
- Commands: `cargo test -p mutable-gui --test doc_instance`
- Tests: `crates/mutable-gui/tests/doc_instance.rs` (round trip of a two-page instance holding every built-in kind equals the original; output starts with `{"format":"mutable-gui/instance","version":1,`; version 2 gives the text "was made by a newer version (2; this one reads up to 1)"; kind `slider` is refused naming it; an `org.vendor.wavetable` element with version 3 and props `{"bank":"A","pos":0.25}` decodes as unknown and encodes back with equal kind, version and props; a stale `current_page` opens the first page)
- Gate: G1.3 — `cargo test -p mutable-gui --test doc_instance` exits 0
- Requirements: R-124
- Screens: none

### Step 1.4 — Parameter source and its fake

- Builds: `params::ParamSource` (object safe) with `params(&self) -> &[ParamInfo]` in declaration order, `info(&self, id) -> Option<&ParamInfo>`, `base(&self, id) -> Option<f32>` (unmodulated normalized), `modulated(&self, id) -> Option<f32>`, `format(&self, id, normalized: f32) -> Option<String>` (with unit), `parse(&self, id, text) -> Option<f32>`, `begin(&self, id)`, `set(&self, id, normalized: f32)`, `end(&self, id)`. `ParamInfo { id, name, group_path: Vec<String>, kind: ParamKind, values: Option<u32>, default: f32, unit: String, hidden: bool, hidden_in_generic_ui: bool }` with `ParamKind` (`Float`, `Int`, `Bool`, `Enum`), `values` the number of distinct values of a stepped parameter (nice-plug step count + 1), `is_two_state()` (`values == Some(2)`) and `step_value(k) -> f32` (`k / (values − 1)`). The testkit's `FakeParamSource` builds a tree with `float(id, name, group_path, default)`, `int(id, name, group_path, values, default)`, `boolean(id, name, group_path, default)`, `enumeration(id, name, group_path, labels, default_index)`, `hidden(id)`, `hidden_in_generic(id)`, `formatter(id, Fn(f32) -> String)`, `parser(id, Fn(&str) -> Option<f32>)`; `set_base` and `set_modulated` change values from outside; `events()` returns the recorded `GestureEvent` list (`Begin(id)`, `Set(id, f32)`, `End(id)`); `set` also updates the base value. Default formatting is the enum label, `On`/`Off`, or `{:.2}`.
- Files: `crates/mutable-gui/src/params.rs`, `crates/mutable-gui/src/lib.rs`, `crates/mutable-gui-testkit/src/fake_params.rs`, `crates/mutable-gui-testkit/src/lib.rs`, `crates/mutable-gui/tests/fake_params.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test fake_params`
- Tests: `crates/mutable-gui/tests/fake_params.rs`
- Gate: G1.4 — `cargo test -p mutable-gui --test fake_params` exits 0
- Requirements: none
- Screens: none

### Step 1.5 — Generated default layout

- Builds: `generate::layout(plugin_name: &str, params: &[ParamInfo]) -> Layout` follows S-13. Parameters with `hidden` or `hidden_in_generic_ui` are left out (R-006). Pages: a page named after the plugin holding the parameters with an empty `group_path`, then one page per distinct first element of `group_path` in order of first declaration, each holding its parameters in declaration order (R-003); the plugin-name page is left out when it would be empty and at least one group exists (choice 6); a plugin with no parameters gets one empty page named after it. A page holds at most 48 controls; the rest continue on pages named "<name> 2", "<name> 3", … (R-005). Every page starts with a label (24, 16, 200 × 28, text the plugin name, typeface heading, size 14, align left) and page tabs (232, 16, 496 × 30, horizontal). Control i of a page sits in cell column i mod 8, row ⌊i / 8⌋ with origin (24 + 88·col, 64 + 116·row): float and int parameters, and enums with more than 32 values, get a knob at (+8, +8) 72 × 100 with no caption; booleans get a label (+4, +30, 80 × 18, the parameter name, body, size 11, centre) and a switch (+26, +54, 40 × 28, caption ""); enums of 2–32 values get the same label and a dropdown selector (+4, +54, 80 × 26, caption "") (R-004, D-43). Every binding is min 0, max 1, not reversed. Canvas 752 wide and max(200, 64 + 116 × rows + 24) high for the page with most rows; grid step 8 with snap on. Ids are deterministic version-4 UUIDs from `uuid::Builder::from_random_bytes` over the page and element counters, so two calls give equal layouts.
- Files: `crates/mutable-gui/src/generate.rs`, `crates/mutable-gui/src/lib.rs`, `crates/mutable-gui/tests/generate.rs`
- Libraries: uuid
- Commands: `cargo test -p mutable-gui --test generate`
- Tests: `crates/mutable-gui/tests/generate.rs` (the four acceptance tests of R-003–R-006; the first knob's frame is (32, 72, 72 × 100); a page of 17 controls makes the canvas 752 × 436; an enum of 33 values gets a knob; all-grouped parameters omit the plugin page; no parameters give one empty page; two calls are equal)
- Gate: G1.5 — `cargo test -p mutable-gui --test generate` exits 0
- Requirements: R-003, R-004, R-005, R-006
- Screens: none

### Step 1.6 — Contrast and the built-in themes from tokens.css

- Builds: the first interface step. `theme::contrast(a: Rgba, b: Rgba) -> f32` is the WCAG 2.2 ratio of relative luminances (sRGB channels linearized with the 0.04045 threshold; alpha ignored); `theme::is_readable(ratio) -> bool` is `ratio >= 4.5`. `theme::builtin(BuiltinTheme) -> Theme` for `StudioDark`, `StudioLight`, `HighContrast` writes every `--role-*` colour of `design/ui/tokens.css` (`:root`, `.theme-studio-light`, `.theme-high-contrast`) with alpha `ff`, names "Studio Dark", "Studio Light", "High Contrast", surfaces per choice 18, typefaces body Inter, heading Inter, value Hack, shape radius 8, border 1, knob style arc, track 4, handle 14 (High Contrast: border 2, track 6). `BuiltinTheme::id()` returns `studio-dark`, `studio-light`, `high-contrast`.
- Files: `crates/mutable-gui/src/theme/mod.rs`, `crates/mutable-gui/src/theme/contrast.rs`, `crates/mutable-gui/src/theme/builtin.rs`, `crates/mutable-gui/src/lib.rs`, `crates/mutable-gui/tests/theme_builtin.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test theme_builtin`
- Tests: `crates/mutable-gui/tests/theme_builtin.rs` (reads `../../design/ui/tokens.css` and asserts every role of each built-in equals its token; the six text pairs of High Contrast are each ≥ 7.0; focus against background and surface ≥ 3.0 in all three; black on white is 21.0 ± 0.05; #777777 on white is not readable and #767676 is)
- Gate: G1.6 — `cargo test -p mutable-gui --test theme_builtin` exits 0
- Requirements: R-104, R-105, R-107, R-109
- Screens: none

### Step 1.7 — Tool style and fonts

- Builds: `theme::tool_style` holds the fixed `--tool-*` values of `design/ui/tokens.css` as `egui::Color32` and `f32` constants (colours, scrim, handle, guide, grid, reserved hatch, text sizes 11, 12, 13, spacing 4/8/12/16, row 24, bar 36, rail 44, inspector 264, radii 4/6/10, menu button 24, the shadow as `egui::Shadow { offset: [0, 6], blur: 24, spread: 0, color: black at alpha 115 }`, quick duration 90 ms). `theme::fonts::install(ctx: &egui::Context, theme: &Theme)` builds `egui::FontDefinitions` from egui's defaults plus `Inter-Regular` and `Inter-Medium` (`include_bytes!` of `assets/`), defines the families `mg-tool`, `mg-tool-medium`, `mg-body`, `mg-heading`, `mg-value` with the fallback chain of choice 21 (built-in names map to `Inter-Regular`, `Inter-Medium`, `Hack`, `Ubuntu-Light`; an asset id falls back to Inter until Step 9.3), calls `ctx.set_fonts`, then `ctx.add_font(egui_material_icons::font_insert())`.
- Files: `crates/mutable-gui/src/theme/tool_style.rs`, `crates/mutable-gui/src/theme/fonts.rs`, `crates/mutable-gui/Cargo.toml`, `crates/mutable-gui/tests/theme_fonts.rs`
- Libraries: egui, egui_material_icons, Inter
- Commands: `cargo test -p mutable-gui --test theme_fonts`
- Tests: `crates/mutable-gui/tests/theme_fonts.rs` (a harness with fonts installed lays out "Reference FX ⌘E ↩ › × ★ −18.0 dB" in each family and an `ICON_MENU` glyph with no missing glyph, which egui_kittest refuses by default; every tool text pair of D-36 is ≥ 7:1: text and muted on bg, raised and hover; accent on bg; on-accent on accent; warning and danger on bg)
- Gate: G1.7 — `cargo test -p mutable-gui --test theme_fonts` exits 0
- Requirements: none
- Screens: none

### Step 1.8 — Canvas transform and window sizes

- Builds: `render::canvas::CanvasTransform::fit(canvas: Size, window: egui::Rect) -> CanvasTransform` with `scale = min(window.w / canvas.w, window.h / canvas.h)`, the canvas centred, `to_screen`, `to_canvas`, `canvas_rect()` and `bars() -> Vec<egui::Rect>` (the uncovered strips). `window_for_request(canvas: Size, requested: WindowSize) -> WindowSize` returns canvas × 0.5 (rounded) when the requested scale is below 0.5, canvas × 4 when above 4, and the request otherwise. `initial_window(canvas) -> WindowSize` is the canvas size. `resize_limits(canvas) -> (WindowSize, WindowSize)` is (canvas × 0.5, canvas × 4).
- Files: `crates/mutable-gui/src/render/mod.rs`, `crates/mutable-gui/src/render/canvas.rs`, `crates/mutable-gui/src/lib.rs`, `crates/mutable-gui/tests/render_canvas.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test render_canvas`
- Tests: `crates/mutable-gui/tests/render_canvas.rs` (R-058 acceptance: scale 0.5 and 200-pixel bars above and below; R-059 acceptance for scales 0.3 and 5; R-061 acceptance)
- Gate: G1.8 — `cargo test -p mutable-gui --test render_canvas` exits 0
- Requirements: R-058, R-059, R-061
- Screens: none

### Step 1.9 — Element view and theme resolution

- Builds: `theme::resolve::ResolvedTheme::new(&Theme)` maps every role to `egui::Color32` (unmultiplied RGBA) and keeps the shape tokens and family ids. `render::view::ElementView` carries the element's screen rect, scale, `&ResolvedTheme`, `VisualState` (`Normal`, `Hover`, `Dragging`, `Focused`), `unbound: bool`, `missing: Option<String>`, `value: Option<f32>`, `modulated: Option<f32>`, `value_text: Option<String>`, `caption: Option<String>`. `view.slot(element, "arc") -> Color32` returns the element's `colours` entry, else the kind's default role of "Colour slots per element kind", and the "disabled" colour for every slot of an unbound control. `view.shape(element) -> ShapeTokens` is the theme's tokens with the element's overrides applied (R-102). `caption_text(element, params)` applies D-47: the caption when present (an empty string hides it), else the bound parameter's name for knob, fader, switch and selector, "Macro" for a macro, none for an XY pad.
- Files: `crates/mutable-gui/src/theme/resolve.rs`, `crates/mutable-gui/src/render/view.rs`, `crates/mutable-gui/tests/render_view.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test render_view`
- Tests: `crates/mutable-gui/tests/render_view.rs` (knob `arc` defaults to accent-1's colour; an `arc: accent-3` entry wins; an unbound knob's every slot is the disabled colour; a knob overriding `knob_style: pointer` resolves pointer while the theme says arc; the caption rules of D-47)
- Gate: G1.9 — `cargo test -p mutable-gui --test render_view` exits 0
- Requirements: R-102
- Screens: none

### Step 1.10 — Knob drawing and shared state marks

- Builds: `render::knob::draw(painter, element, view)` draws as `design/ui/kit.js` `knob()`: dial size `min(w, h − 30)` in canvas units times scale; arc style: 270° track from 135° in `track`, value arc in `arc`, body disc in `body`, pointer line in `pointer`; pointer and filled styles as kit.js; the caption (11 units, `mg-body`, `caption` slot) and value line (10.5 units, `mg-value`, `value` slot; the missing id for an unbound control) in the bottom 30 units. `render::knob::model(element, view) -> KnobModel { value_angle, band: Option<(f32, f32)> }`; the modulation band runs from the base to the modulated value in the `modulation` slot (R-032). `render::state` draws the focus outline (focus role, 2 px, 3 units outset, radius 6), the unbound dashed outline (disabled role, dashes 4 and 3), and the value bubble while dragging (text-role box, background-role text, 18 units high, 4 above the dial).
- Files: `crates/mutable-gui/src/render/knob.rs`, `crates/mutable-gui/src/render/state.rs`, `crates/mutable-gui/tests/render_knob.rs`, `crates/mutable-gui/tests/snapshots/knob-arc.png`, `crates/mutable-gui/tests/snapshots/knob-pointer.png`, `crates/mutable-gui/tests/snapshots/knob-filled.png`, `crates/mutable-gui/tests/snapshots/knob-states.png`
- Libraries: egui, egui_kittest
- Commands: `cargo test -p mutable-gui --test render_knob`
- Tests: `crates/mutable-gui/tests/render_knob.rs` (base 0.4 with modulated 0.6 gives `band == Some((0.4, 0.6))`; no modulation gives `None`; four 72 × 100 pictures in Studio Dark, the last showing focused, dragging and unbound side by side)
- Gate: G1.10 — `cargo test -p mutable-gui --test render_knob` exits 0
- Requirements: R-032
- Screens: none

### Step 1.11 — Switch and selector drawing

- Builds: `render::switch::draw` (kit.js `toggle()`: pill track in `on` or `off`, `outline`, thumb in `thumb`, caption to its right in `caption`); `render::selector::draw` for `segments` (equal segments, the current one filled `selected` with `selected_text`, others `text` on `background` with `outline`) and `dropdown` (field with the current label and a chevron icon). Entry labels come from `ParamSource::format` of each step value (R-020's "plugin's text for each step").
- Files: `crates/mutable-gui/src/render/switch.rs`, `crates/mutable-gui/src/render/selector.rs`, `crates/mutable-gui/tests/render_switch_selector.rs`, `crates/mutable-gui/tests/snapshots/switch.png`, `crates/mutable-gui/tests/snapshots/selector-segments.png`, `crates/mutable-gui/tests/snapshots/selector-dropdown.png`
- Libraries: egui, egui_kittest, egui_material_icons
- Commands: `cargo test -p mutable-gui --test render_switch_selector`
- Tests: `crates/mutable-gui/tests/render_switch_selector.rs`
- Gate: G1.11 — `cargo test -p mutable-gui --test render_switch_selector` exits 0
- Requirements: none
- Screens: none

### Step 1.12 — Label, panel and page tabs drawing, and the drawing dispatch

- Builds: `render::label::draw` (text in `mg-body`, `mg-heading` or `mg-value` at `size` canvas units, `align`, letter spacing `tracking`, `text` slot); `render::panel::draw` (the theme's fill for `surface` drawn solid with its role in this phase, `outline` border of the theme's border width and radius, the `title` upper-cased at (12, 20) in `mg-heading` 10.5 units, `title` slot); `render::page_tabs::draw` (one tab per page name, equal widths, horizontal or vertical, current tab in `current` with `current_text`). `render::draw_element(painter, element, view_for)` dispatches knob, switch, selector, label, panel, page tabs, and a group (its members in order); every other kind goes to `render::fallback::draw`, a dashed outline in text-muted with the kind name, until its own step wires it (Steps 3.12, 4.7, 7.7).
- Files: `crates/mutable-gui/src/render/label.rs`, `crates/mutable-gui/src/render/panel.rs`, `crates/mutable-gui/src/render/page_tabs.rs`, `crates/mutable-gui/src/render/fallback.rs`, `crates/mutable-gui/src/render/mod.rs`, `crates/mutable-gui/tests/render_decor.rs`, `crates/mutable-gui/tests/snapshots/label-panel-tabs.png`
- Libraries: egui, egui_kittest
- Commands: `cargo test -p mutable-gui --test render_decor`
- Tests: `crates/mutable-gui/tests/render_decor.rs` (a label set to heading draws with the `mg-heading` family; a picture of a label, a titled panel and three-page tabs)
- Gate: G1.12 — `cargo test -p mutable-gui --test render_decor` exits 0
- Requirements: none
- Screens: none

### Step 1.13 — State cell

- Builds: `persist::StateCell` holds `arc_swap::ArcSwap<String>` and an `AtomicU64` generation. `new()` holds `""` (no saved state) at generation 0. `store_incoming(String)` swaps in the host's string and increments the generation; `publish(String)` swaps in the editor's encoding without changing the generation; `load() -> Arc<String>` returns the current string; `generation() -> u64`. `keep_unreadable(Arc<String>)` and `is_kept()` (an `AtomicBool`) mark the current string as the kept unreadable one; while kept, `publish` is ignored (R-118, I-16); `discard_kept()` clears the mark. Every method is an atomic load, store or swap (I-03).
- Files: `crates/mutable-gui/src/persist.rs`, `crates/mutable-gui/src/lib.rs`, `crates/mutable-gui/tests/persist_cell.rs`
- Libraries: arc-swap
- Commands: `cargo test -p mutable-gui --test persist_cell`
- Tests: `crates/mutable-gui/tests/persist_cell.rs` (incoming raises the generation; publish does not; while kept, publish leaves the kept bytes; a thread storing 10,000 strings while another loads sees only whole strings)
- Gate: G1.13 — `cargo test -p mutable-gui --test persist_cell` exits 0
- Requirements: none
- Screens: none

### Step 1.14 — Gesture tracker and binding mapping

- Builds: `perform::gesture::GestureTracker` keeps the set of open parameter ids: `begin(src, id)` calls `ParamSource::begin` only if `id` is not open; `set(src, id, v)` begins first when needed, then calls `set`; `end(src, id)`; `end_all(src)` ends every open id in sorted order (used on release and on editor close, R-025). `perform::binding::travel_to_normalized(&Binding, t) -> f32` is `min + (max − min)·t`, or `max − (max − min)·t` when reversed, with `t` clamped to 0–1; `normalized_to_travel` is its inverse clamped to 0–1.
- Files: `crates/mutable-gui/src/perform/mod.rs`, `crates/mutable-gui/src/perform/gesture.rs`, `crates/mutable-gui/src/perform/binding.rs`, `crates/mutable-gui/src/lib.rs`, `crates/mutable-gui/tests/perform_gesture.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test perform_gesture`
- Tests: `crates/mutable-gui/tests/perform_gesture.rs` (two begins record one; `end_all` ends each open id once; R-033 acceptance: range 0.25–0.75 reversed at full travel gives 0.25)
- Gate: G1.14 — `cargo test -p mutable-gui --test perform_gesture` exits 0
- Requirements: R-033
- Screens: none

### Step 1.15 — Knob, switch, selector and page-tab input rules

- Builds: pure functions over canvas units. `perform::knob::drag(start_travel, dy_canvas, fine) -> f32` adds `−dy / 200` (upward is negative `dy` in screen coordinates and increases the value), divided by 10 when `fine`, clamped 0–1. `perform::stepped::toggle(info, base) -> f32` returns the other of the two values; `perform::stepped::entry_value(info, k) -> f32` is `k / (values − 1)`; `perform::stepped::entry_at(rect, values, presentation, pos) -> Option<u32>` hit-tests segments. `perform::page_tabs::tab_at(rect, pages, orientation, pos) -> Option<usize>`.
- Files: `crates/mutable-gui/src/perform/knob.rs`, `crates/mutable-gui/src/perform/stepped.rs`, `crates/mutable-gui/src/perform/page_tabs.rs`, `crates/mutable-gui/tests/perform_rules.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test perform_rules`
- Tests: `crates/mutable-gui/tests/perform_rules.rs` (0.2 dragged up 100 units gives 0.7; with `fine` 0.25; toggling twice returns to the first value; the third entry of three gives 1.0; the second of three tabs is found at its centre)
- Gate: G1.15 — `cargo test -p mutable-gui --test perform_rules` exits 0
- Requirements: none
- Screens: none

### Step 1.16 — Editor state and the perform frame

- Builds: `editor::EditorConfig { plugin_name, clap_id, plugin_version, embedded_default: Option<&'static [u8]>, menu_corner: Corner, design_mode_enabled: bool }` (`Corner`: `TopLeft`, `TopRight`, `BottomLeft`, `BottomRight`). `EditorState::new(config, cell: Arc<StateCell>)`; `frame(&mut self, ui, params)` installs fonts once per `egui::Context` (it reinstalls after `editor_opened`), fills the window with the theme's background colour, sets the canvas transform, clips to the canvas, draws the current page back to front through `render::draw_element` with an `ElementView` built from `params` (base, modulated, `format` text, unbound when no bound parameter exists or the slot is null), and records a `render::drawn::DrawnElement { id, kind, rect, value, value_text, caption, band, unbound, missing }` per element in `EditorState::drawn()`. `perform::frame` routes a primary press on the topmost control under the pointer: knob drags (gesture begun on press, a set per pointer move, `end_all` on release), switch clicks, segment clicks, dropdown selectors (a popup `egui::Area` listing the entries; choosing one sets it) and page tabs (current page changes, republished). Each click change is begin, one set, end (R-024). `editor_closed(params)` ends every open gesture; `editor_opened()` keeps the document and the current page (R-014).
- Files: `crates/mutable-gui/src/editor/mod.rs`, `crates/mutable-gui/src/perform/mod.rs`, `crates/mutable-gui/src/render/drawn.rs`, `crates/mutable-gui/src/lib.rs`, `crates/mutable-gui/tests/editor_perform.rs`
- Libraries: egui, egui_kittest
- Commands: `cargo test -p mutable-gui --test editor_perform`
- Tests: `crates/mutable-gui/tests/editor_perform.rs` (harness tests over a generated layout and `FakeParamSource`: R-015 drag sets 0.7 ± 0.005; R-018 switch; R-020 clicking "Square" sets the third step; R-022 second tab; R-023 knob drag records begin, sets, end; R-024 switch click records exactly begin, set, end; R-025 closing mid-drag records an end; R-026 `drawn()` shows "440 Hz" for a formatter returning it at 0.5; R-031 a `set_base` between frames changes the next frame's drawn value; R-014 page 2 current survives `editor_closed` and `editor_opened`)
- Gate: G1.16 — `cargo test -p mutable-gui --test editor_perform` exits 0
- Requirements: R-014, R-015, R-018, R-020, R-022, R-023, R-024, R-025, R-026, R-031
- Screens: none

### Step 1.17 — Defaults at first open and publication

- Builds: `EditorState::resolve(&mut self, infos: &[ParamInfo])` resolves the document once per instance; the first `frame` calls it with `params.params()`, and the adapter calls it at `spawn` before reading the canvas and window size. When the cell holds `""`: the developer default is the generated layout (`generate::layout` over `params.params()`) with Studio Dark (D-28) and no assets, current page the first, window `initial_window(canvas)`; the result is encoded and `StateCell::publish`ed (R-112). When the cell holds a string: it is decoded with `doc::decode_instance` (failure handling arrives in Step 2.13). `EditorState` remembers the cell generation it decoded and, at the start of every frame, decodes again when `generation()` changed (R-116 path, completed in Step 2.14). After every change of current page or window size the editor publishes a new encoding.
- Files: `crates/mutable-gui/src/editor/defaults.rs`, `crates/mutable-gui/src/editor/mod.rs`, `crates/mutable-gui/tests/editor_defaults.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test editor_defaults`
- Tests: `crates/mutable-gui/tests/editor_defaults.rs` (R-112: a new cell loads `""` until the first frame, then a document; a cell preloaded with an encoded instance opens on it unchanged; changing page publishes)
- Gate: G1.17 — `cargo test -p mutable-gui --test editor_defaults` exits 0
- Requirements: R-112
- Screens: none

### Step 1.18 — Window size kept

- Builds: `EditorState::window() -> WindowSize` and `window_resized(WindowSize)` (stores it in the instance state and publishes). The adapter opens the window at `window()`; a new instance opens at `initial_window(canvas)`.
- Files: `crates/mutable-gui/src/editor/mod.rs`, `crates/mutable-gui/tests/editor_window.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test editor_window`
- Tests: `crates/mutable-gui/tests/editor_window.rs` (R-060: resized to 900 × 300, closed and reopened, `window()` is 900 × 300; R-061: a new instance with an 800 × 500 canvas reports 800 × 500)
- Gate: G1.18 — `cargo test -p mutable-gui --test editor_window` exits 0
- Requirements: R-060, R-061
- Screens: none

### Step 1.19 — Menu button

- Builds: `render::chrome::menu_button` draws the 24 px round button (tool style, `ICON_MENU`) 8 logical px from the two edges of the developer's corner, at every canvas scale, in an `egui::Area` with `egui::Order::Foreground` drawn after all layout content (I-12); its opacity is 0.35 until the pointer is within 64 px of its centre, then rises to 1.0 over 90 ms (choice 9; animation frames are requested only during the fade). A click opens the editor menu (Step 1.20). Layout input under the button's rect is ignored.
- Files: `crates/mutable-gui/src/render/chrome/mod.rs`, `crates/mutable-gui/src/render/chrome/menu_button.rs`, `crates/mutable-gui/src/render/mod.rs`, `crates/mutable-gui/tests/chrome_menu_button.rs`
- Libraries: egui, egui_material_icons
- Commands: `cargo test -p mutable-gui --test chrome_menu_button`
- Tests: `crates/mutable-gui/tests/chrome_menu_button.rs` (R-010: on a layout whose top element is a panel covering the canvas, a click at the button opens the menu; R-149: corner top-left puts the button's top-left at (8, 8), the default bottom-right puts its bottom-right 8 px from the window's)
- Gate: G1.19 — `cargo test -p mutable-gui --test chrome_menu_button` exits 0
- Requirements: R-010, R-149
- Screens: none

### Step 1.20 — Editor menu with the page list

- Builds: `render::chrome::editor_menu` opens above the menu button as an `egui::Area` (tool style: bg #17181B, outline, radius 6, shadow, rows 24 px, Inter 12 px): a header with the plugin name and "mutable-gui" in muted text, then "Pages" as a section head (11 px, uppercase, tracking 0.06 em) and one row per page with a check on the current one. Choosing a page makes it current and closes the menu (R-011). Escape and a click outside close it. Later steps add their entries to this file once each (5.4) or in their own submenu files (8.11).
- Files: `crates/mutable-gui/src/render/chrome/editor_menu.rs`, `crates/mutable-gui/src/render/chrome/mod.rs`, `crates/mutable-gui/tests/chrome_editor_menu.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test chrome_editor_menu`
- Tests: `crates/mutable-gui/tests/chrome_editor_menu.rs` (R-011: choosing the third of three pages makes it current; Escape closes the menu)
- Gate: G1.20 — `cargo test -p mutable-gui --test chrome_editor_menu` exits 0
- Requirements: R-011
- Screens: none

### Step 1.21 — Adapter parameter source

- Builds: `mutable_gui_nice::params::NiceParamSource::new(params: Arc<dyn Params>, gui: GuiContext)` reads `params.param_map()` once into `ParamInfo`s in declaration order: kind from the `ParamPtr` variant, `values` from `step_count() + 1`, `default` from `default_normalized_value()`, `unit()`, `flags()` (`HIDDEN`, `HIDE_IN_GENERIC_UI`), `group_path` from the group string split on `/`. Values: `unmodulated_normalized_value`, `modulated_normalized_value`; text: `normalized_value_to_string(v, true)`; parse: `string_to_normalized_value`; gestures: `GuiContext::raw_begin_set_parameter`, `raw_set_parameter_normalized`, `raw_end_set_parameter`. Every `unsafe` block carries `// SAFETY:` naming the guarantee: the `ParamPtr` comes from `param_map()` of the `Arc<dyn Params>` this source holds, which keeps the parameters alive for the source's lifetime (I-06). The testkit's feature `nice` adds `nice::RecordingGuiContext`, an implementation of nice-plug's `GuiContextInner` that records begin, set and end and applies sets through `ParamPtr::_internal_set_normalized_value`; the adapter and the reference plugin take the testkit as a dev-dependency with that feature. `params::infos(&dyn Params) -> Vec<ParamInfo>` builds the list without a `GuiContext`.
- Files: `crates/mutable-gui-nice/src/params.rs`, `crates/mutable-gui-nice/src/lib.rs`, `crates/mutable-gui-testkit/src/nice.rs`, `crates/mutable-gui-testkit/Cargo.toml`, `crates/mutable-gui-nice/Cargo.toml`, `crates/mutable-gui-nice/tests/params.rs`
- Libraries: nice-plug
- Commands: `cargo test -p mutable-gui-nice --test params`
- Tests: `crates/mutable-gui-nice/tests/params.rs` (a test `Params` with a float in group "Filter", a bool, a four-value enum and a hidden float gives the expected `ParamInfo`s; a set through the source changes the parameter and records begin, set, end; format returns the parameter's own text with its unit)
- Gate: G1.21 — `cargo test -p mutable-gui-nice --test params` exits 0
- Requirements: none
- Screens: none

### Step 1.22 — Persisted field

- Builds: `mutable_gui_nice::PersistedUi(Arc<StateCell>)` (`Clone`) implements `PersistentField<'a, String>`: `set` calls `StateCell::store_incoming`, `map` applies the function to `&*cell.load()`. Nothing else happens in either (I-03).
- Files: `crates/mutable-gui-nice/src/persist.rs`, `crates/mutable-gui-nice/src/lib.rs`, `crates/mutable-gui-nice/tests/persist.rs`
- Libraries: nice-plug, arc-swap
- Commands: `cargo test -p mutable-gui-nice --test persist`
- Tests: `crates/mutable-gui-nice/tests/persist.rs` (I-02: no file under `crates/mutable-gui-nice/src/` contains `set_state(`; a derived `Params` with `#[persist = "mutable-gui"] ui: PersistedUi`: `serialize_fields()` holds key `mutable-gui` with the JSON string of the published text; `deserialize_fields` of that map into a second instance stores it with a raised generation)
- Gate: G1.22 — `cargo test -p mutable-gui-nice --test persist` exits 0
- Requirements: none
- Screens: none

### Step 1.23 — Builder and editor of the adapter

- Builds: `MutableGui::builder(name, clap_id, version)` with `.embedded_default(&'static [u8])`, `.menu_corner(Corner)`, `.design_mode(bool)` and `.build() -> MutableGui`; `MutableGui` holds `Arc<Mutex<EditorState>>` (std `Mutex`, taken only on the editor thread and the host main thread, never by audio code; a poisoned lock is recovered with `PoisonError::into_inner`), the `Arc<StateCell>` and an `Arc<EguiEditorState>`. `MutableGui::persisted() -> PersistedUi` shares the cell. `MutableGui::editor(params: Arc<dyn Params>) -> Option<MutableGuiEditor>`. `MutableGuiEditor` implements nice-plug `Editor` with `type Handle = EguiEditorHandle`: `spawn` calls `EditorState::resolve(&params::infos(&*params))` under the lock, reads the canvas and `window()`, sets the egui state's size, and spawns a fresh `create_egui_editor(…)` (kept in the `MutableGuiEditor` until the next spawn) with `RepaintNotifier::new()` and `EguiNiceSettings::default().with_resize_hint(ResizeHint { can_resize: true, can_resize_horizontally: true, can_resize_vertically: true, preserve_aspect_ratio: false, aspect_ratio_width: 1, aspect_ratio_height: 1, size_constraints: SizeConstraints::Logical { min_size: Some(canvas × 0.5), max_size: Some(canvas × 4) } })` (`resize_limits`, R-059); `size()` returns the egui state's size. Its `NiceEguiApp` keeps the `GuiContext` from `build` in a `NiceParamSource`, calls `EditorState::editor_opened`, runs `EditorState::frame` in `ui`, `window_resized` in `resized`, and `editor_closed` in `editor_closed`.
- Files: `crates/mutable-gui-nice/src/builder.rs`, `crates/mutable-gui-nice/src/editor.rs`, `crates/mutable-gui-nice/src/lib.rs`, `crates/mutable-gui-nice/tests/builder.rs`
- Libraries: nice-plug, nice-plug-egui, egui
- Commands: `cargo test -p mutable-gui-nice --test builder`
- Tests: `crates/mutable-gui-nice/tests/builder.rs` (defaults are bottom-right and design mode on; `resize_hint_for(752 × 436)` gives min 376 × 218 and max 3008 × 1744; `persisted()` and the editor share one cell)
- Gate: G1.23 — `cargo test -p mutable-gui-nice --test builder` exits 0
- Requirements: R-059
- Screens: none

### Step 1.24 — Reference plugin parameters

- Builds: `examples/reference-plugin/src/params.rs` declares `RefParams` with the 63 parameters of "Reference plugin parameters" in that order, the groups as `#[nested(group = "…")]` structs, and `#[persist = "mutable-gui"] pub ui: PersistedUi`. Formatters (U+2212 for minus): gain-like dB (`input_gain`, `makeup`, `drive_out`, `out_level`, `out_ceiling`, `out_trim`) as "+3.5 dB" and "−1.5 dB"; amount dB (`drive`, `filter_drive`, `knee`, `comp_range`) as "8.8 dB"; `threshold` as "−18.0 dB"; Hz below 1,000 as "{:.0} Hz", from 1,000 as "{:.2} kHz"; LFO rates "{:.2} Hz"; ms "{:.0} ms" (below 1 ms "{:.1} ms"); unipolar % "{:.0} %"; bipolar % with sign ("+0 %", "+40 %"); ratio "{:.1} : 1"; pan "C", "L {n}", "R {n}"; bias "{:+.2}". Each float has a parser accepting a number with or without its unit ("1000", "1 kHz", "−6 dB"). Only `bypass`, `input_gain`, `mix`, `cutoff`, `resonance`, `filter_mode`, `drive`, `threshold`, `ratio`, `attack`, `release`, `makeup`, `out_level`, `lfo1_rate`, `lfo1_depth` and `cutoff_lfo` reach the DSP; the rest exist for layouts.
- Files: `examples/reference-plugin/src/params.rs`, `examples/reference-plugin/src/lib.rs`, `examples/reference-plugin/Cargo.toml`, `examples/reference-plugin/tests/params.rs`
- Libraries: nice-plug
- Commands: `cargo test -p mutable-gui-reference --test params`
- Tests: `examples/reference-plugin/tests/params.rs` (the 63 ids in order; group strings; default texts "1.24 kHz", "35 %", "+0 %", "8.8 dB", "−18.0 dB", "4.0 : 1", "8 ms", "120 ms", "+3.5 dB", "−1.5 dB", "100 %", "2.40 Hz", "C")
- Gate: G1.24 — `cargo test -p mutable-gui-reference --test params` exits 0
- Requirements: none
- Screens: none

### Step 1.25 — Reference plugin DSP

- Builds: `dsp::Dsp::new(sample_rate)` preallocates everything; `Dsp::process(&mut self, p: &DspParams, left: &mut [f32], right: &mut [f32]) -> f32` (returns the block's largest gain reduction in dB) applies input gain, a state-variable filter (mode, cutoff modulated by `lfo1` × `cutoff_lfo`, resonance), drive `drive_curve(drive_db, x) = tanh(g·x) / tanh(g)` with `g = 10^(drive_db / 20)`, a peak compressor (threshold, ratio, attack, release, makeup), output level and dry/wet mix; `bypass` copies input to output bit for bit. `DspParams` is a plain struct of the plain values read once per block. No allocation, lock or system call in `process`.
- Files: `examples/reference-plugin/src/dsp.rs`, `examples/reference-plugin/src/lib.rs`, `examples/reference-plugin/tests/dsp.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui-reference --test dsp`
- Tests: `examples/reference-plugin/tests/dsp.rs` (bypass is bit-exact; silence stays silence; `drive_curve(d, 1.0) == 1.0` for d in {0, 8.8, 24}; the curve is increasing; two runs over the same input are bit-identical)
- Gate: G1.25 — `cargo test -p mutable-gui-reference --test dsp` exits 0
- Requirements: none
- Screens: none

### Step 1.26 — Reference plugin with its editor

- Builds: `RefFx` holds a `MutableGui` built with the identifiers of "Fixed names" (no embedded default yet), its `RefParams` take `ui: gui.persisted()`, `type Editor = MutableGuiEditor`, `editor()` returns `gui.editor(self.params.clone())`, and `process` reads `DspParams` once per block and calls `Dsp::process`. `examples/reference-plugin/tests/common/mod.rs` starts with `#![cfg(test)]` (D-49) and provides `reference_fixture(options) -> (EditorState, NiceParamSource)` over a fresh `RefParams` and a `RecordingGuiContext`, and `reference_harness(size, fixture)`. The reference crate's dev-dependency is the testkit with feature `nice`.
- Files: `examples/reference-plugin/src/lib.rs`, `examples/reference-plugin/Cargo.toml`, `examples/reference-plugin/tests/common/mod.rs`, `examples/reference-plugin/tests/round_trip.rs`
- Libraries: nice-plug, nice-plug-egui, clap-validator
- Commands: `cargo test -p mutable-gui-reference --test round_trip && cargo xtask bundle mutable-gui-reference --release && sh tools/validate-clap.sh`
- Tests: `examples/reference-plugin/tests/round_trip.rs` (R-110 for layout, theme, current page and window: open, go to page 3, resize to 900 × 520, `serialize_fields()`, load into a fresh `RefParams`, open: the decoded instance equals the first as documents)
- Gate: G1.26 — `cargo test -p mutable-gui-reference --test round_trip && cargo xtask bundle mutable-gui-reference --release && sh tools/validate-clap.sh` exits 0
- Requirements: R-110
- Screens: none

### Step 1.27 — S-13 generated default screen

- Builds: `examples/reference-plugin/tests/screen_s13.rs` builds a reference fixture without an embedded default, a 752 × 436 harness, clicks the "Modulation" tab, and calls `snapshot_on_macos(&mut harness, "S-13-generated")`; it asserts the page names ["Reference FX", "Filter", "Drive", "Compressor", "Modulation", "Output"] and the canvas 752 × 436. `design/UI.md` S-13 gets `Built: examples/reference-plugin/tests/snapshots/S-13-generated.png`.
- Files: `examples/reference-plugin/tests/screen_s13.rs`, `examples/reference-plugin/tests/snapshots/S-13-generated.png`, `design/UI.md`
- Libraries: egui_kittest
- Commands: `cargo test -p mutable-gui-reference --test screen_s13 && python3 tools/devpipe/run.py ui compare S-13`
- Tests: `examples/reference-plugin/tests/screen_s13.rs`
- Gate: G1.27 — `cargo test -p mutable-gui-reference --test screen_s13 && python3 tools/devpipe/run.py ui compare S-13` exits 0
- Requirements: R-003
- Screens: S-13

### Step 1.28 — Documents at Phase 1 truth

- Builds: `README.md` (quick start adds bundling and loading Reference FX in Bitwig), `docs/ARCHITECTURE.md` (components built: model, doc, params, generate, theme, render, perform, persist, editor, adapter, reference plugin; invariants in force I-03, I-05, I-06, I-12 with their tests), `docs/RUNBOOK.md` (installing the bundle, resizing, where the state lives), `docs/TESTING.md` (snapshot and reference-fixture tests), `CHANGELOG.md` (Added: generated default, perform controls, persistence).
- Files: `README.md`, `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, `docs/TESTING.md`, `CHANGELOG.md`
- Libraries: none
- Commands: `grep -q "I-03" docs/ARCHITECTURE.md && grep -q "S-13" docs/TESTING.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/RUNBOOK.md docs/TESTING.md CHANGELOG.md`
- Tests: none
- Gate: G1.28 — `grep -q "I-03" docs/ARCHITECTURE.md && grep -q "S-13" docs/TESTING.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/RUNBOOK.md docs/TESTING.md CHANGELOG.md` exits 0
- Requirements: none
- Screens: none

### Step 1.29 — Phase 1 check sheet

- Builds: `docs/qa/phase-01.md` lists, each with a "Result:" line reading "not run": in Bitwig 5.3.13 on macOS 26.7.1, (1) Reference FX opens on the generated "Reference FX" page in Studio Dark; (2) dragging Cutoff records one undoable edit in Bitwig's history; (3) the Key Track switch and the Mode dropdown change their parameters; (4) Bitwig automation of Cutoff moves the knob while playing; (5) resizing the window to its smallest and largest stops at scales 0.5 and 4 with bars; (6) saving, closing and reopening the project shows the same page and window size; (7) the S-13 picture `.tickets/.work/ui-compare/S-13.png` matches the mockup. It ends with the line "Signed off: no".
- Files: `docs/qa/phase-01.md`
- Libraries: none
- Commands: `grep -q "^Signed off: no" docs/qa/phase-01.md && grep -c "^Result: not run" docs/qa/phase-01.md | grep -q "^7$"`
- Tests: none
- Gate: G1.29 — `grep -q "^Signed off: no" docs/qa/phase-01.md` exits 0
- Requirements: none
- Screens: none

### Step 1.30 — [OWNER] Phase 1 host and screen check

- Builds: the owner performs the seven items of `docs/qa/phase-01.md` following `README.md` and `docs/RUNBOOK.md`, writes "pass" or what failed on each "Result:" line, and changes the last line to "Signed off: yes" when all pass.
- Files: `docs/qa/phase-01.md`
- Libraries: Bitwig Studio
- Commands: `python3 tools/devpipe/run.py ui compare S-13`
- Tests: none
- Gate: G1.30 — `grep -q "^Signed off: yes" docs/qa/phase-01.md` exits 0
- Requirements: R-110
- Screens: S-13

**Exit demo:** Following `README.md` and `docs/RUNBOOK.md`: bundle and install Reference FX, insert it on a Bitwig track, see the generated pages, drag Cutoff, flip Key Track, set Mode to HP from its dropdown, switch pages from the tabs and from the menu button, resize the window to both limits, save, close and reopen the project and find the same page and window size.

## Phase 2 — Safe documents and the embedded default

**Goal:** Every byte sequence from outside the process (saved state, the embedded package, package files, clipboard text) is checked against every limit before any part is used; Reference FX opens on its embedded four-page default; an unreadable saved layout falls back with a notice and is written back unchanged; notices stay until dismissed.

### Step 2.1 — Structural limits and validation

- Builds: `doc::validate::layout(&Layout) -> Result<(), DocError>` refuses: no page (`Invalid` "a layout needs at least one page" at `pages`); more than 64 pages; more than 2,000 elements counting groups and members; nesting deeper than 16; any text over 4,096 bytes (label `text`, menu `label`, item `text`) with its path; a page name, `caption` or `title` outside 0–64 characters (page names 1–64); canvas sides outside 200–4,000; grid step outside 2–64; frames outside choice 2; a binding with `min` < 0, `max` > 1 or `min ≥ max`; a colour slot name its kind lacks (choice 19); `window_ms` outside 5–500; `fft_size` not 1,024, 2,048, 4,096 or 8,192; `floor_db` outside −120 to −30; `range_db` not 6, 12, 24 or 48; label `size` outside 6–200; `tracking` outside 0–8; macro `targets` outside 1–16; a duplicate element or page id (I-15); an id that is not a version-4 UUID. `doc::validate::theme(&Theme)` refuses a missing colour role with `MissingRole` (R-098), a missing typeface or surface role, a name outside 1–64 characters, shape tokens outside radius 0–64, border 0–8, track 1–24, handle 4–48, grain amount outside 0–1. `decode_instance` calls both. Fixtures in `fixtures/invalid/`: `pages-65.json`, `elements-2001.json`, `nesting-17.json`, `text-4097.json`, `theme-no-accent-3.json`, `binding-min-max.json`, `slot-unknown.json`, `frame-too-wide.json`, each an instance document over exactly one limit.
- Files: `crates/mutable-gui/src/doc/validate.rs`, `crates/mutable-gui/src/doc/instance.rs`, `crates/mutable-gui/src/doc/mod.rs`, `crates/mutable-gui/tests/doc_validate.rs`, `crates/mutable-gui/tests/fixtures/invalid/pages-65.json`, `crates/mutable-gui/tests/fixtures/invalid/elements-2001.json`, `crates/mutable-gui/tests/fixtures/invalid/nesting-17.json`, `crates/mutable-gui/tests/fixtures/invalid/text-4097.json`, `crates/mutable-gui/tests/fixtures/invalid/theme-no-accent-3.json`, `crates/mutable-gui/tests/fixtures/invalid/binding-min-max.json`, `crates/mutable-gui/tests/fixtures/invalid/slot-unknown.json`, `crates/mutable-gui/tests/fixtures/invalid/frame-too-wide.json`
- Libraries: serde_json, uuid
- Commands: `cargo test -p mutable-gui --test doc_validate`
- Tests: `crates/mutable-gui/tests/doc_validate.rs` (each fixture is refused with the `DocError` text naming its limit; R-098: the missing role text names "accent-3"; the same documents one under each limit decode)
- Gate: G2.1 — `cargo test -p mutable-gui --test doc_validate` exits 0
- Requirements: R-098, R-139
- Screens: none
- Pins: Step 1.3's `doc_instance.rs` documents are all within limits; its assertions hold.

### Step 2.2 — Unknown fields named

- Builds: `doc` checks the keys of every document object (`format`, `version` and the format's fields) and turns serde's "unknown field `x`, expected …" errors from body structs into `DocError::UnknownField { name: "x", path }`. The `props` of a custom element are read as a `serde_json::Map` and never checked for unknown keys (R-142's exception); the nesting and text limits apply inside them (the deepest object nesting and any string longer than 4,096 bytes).
- Files: `crates/mutable-gui/src/doc/element.rs`, `crates/mutable-gui/src/doc/instance.rs`, `crates/mutable-gui/tests/doc_unknown_fields.rs`, `crates/mutable-gui/tests/fixtures/invalid/unknown-top-level.json`, `crates/mutable-gui/tests/fixtures/invalid/unknown-in-knob.json`
- Libraries: serde, serde_json
- Commands: `cargo test -p mutable-gui --test doc_unknown_fields`
- Tests: `crates/mutable-gui/tests/doc_unknown_fields.rs` (a top-level `script` is refused with "holds the unknown field “script”"; an extra field inside a knob is refused naming it; an unknown custom element with `props` `{"anything": {"nested": [1, 2]}}` decodes)
- Gate: G2.2 — `cargo test -p mutable-gui --test doc_unknown_fields` exits 0
- Requirements: R-142
- Screens: none

### Step 2.3 — Schema versions and migration

- Builds: `doc::migrate::migrate(format: &str, version: u64, value: Value) -> Result<Value, DocError>` applies, in order, the per-format list of version-to-version functions up to `SUPPORTED_VERSION` (the lists are empty at version 1); a version above it is `Newer { found, supported }`; version 0 or a non-integer is `Invalid` at `version`. Every decode goes through it before reading parts. `fixtures/v1/` holds `instance.json` (two pages, a group, every built-in kind, three bindings to absent parameters), `layout-package.mgui`, `theme-package.mgui` and `elements.json`. A later schema version adds a `fixtures/vN/` folder and a migration; no step of this plan adds one.
- Files: `crates/mutable-gui/src/doc/migrate.rs`, `crates/mutable-gui/src/doc/instance.rs`, `crates/mutable-gui/tests/doc_migrate.rs`, `crates/mutable-gui/tests/fixtures/v1/instance.json`, `crates/mutable-gui/tests/fixtures/v1/layout-package.mgui`, `crates/mutable-gui/tests/fixtures/v1/theme-package.mgui`, `crates/mutable-gui/tests/fixtures/v1/elements.json`
- Libraries: serde_json
- Commands: `cargo test -p mutable-gui --test doc_migrate`
- Tests: `crates/mutable-gui/tests/doc_migrate.rs` (R-121: for every fixture under `fixtures/v*/`, the page, element and non-null binding counts computed from the raw JSON equal those of the decoded document; R-124: the three bindings to absent parameters keep their ids; R-141: a version-99 package gives "was made by a newer version (99; this one reads up to 1)")
- Gate: G2.3 — `cargo test -p mutable-gui --test doc_migrate` exits 0
- Requirements: R-121, R-124, R-141
- Screens: none

### Step 2.4 — Asset decoding and the asset cap

- Builds: `doc::assets::decode(&[Asset]) -> Result<DecodedAssets, DocError>` base64-decodes every asset (standard alphabet with padding), checks a `png` asset by fully decoding it with the `png` crate (`Decoder::read_info` then `next_frame`) and a `font` asset with `skrifa::FontRef::new` plus readable `head` and `cmap` tables, and sums the decoded byte lengths (choice 22): above 4 MiB (4,194,304 bytes) is `Assets { bytes }`; one failure refuses all, before anything is returned (R-140). `doc::assets::check_references` refuses an image element, image fill or typeface naming an asset id the list lacks. `doc::assets::sniff(&[u8]) -> Option<AssetKind>` recognises the PNG signature and the TrueType (`00 01 00 00`, `true`) and OpenType (`OTTO`) tags. `decode_instance` calls `decode` and `check_references`.
- Files: `crates/mutable-gui/src/doc/assets.rs`, `crates/mutable-gui/src/doc/instance.rs`, `crates/mutable-gui/tests/doc_assets.rs`
- Libraries: base64, png, skrifa
- Commands: `cargo test -p mutable-gui --test doc_assets`
- Tests: `crates/mutable-gui/tests/doc_assets.rs` (R-138: 4.5 MiB of decoded assets is refused with "holds 4.5 MiB of assets; at most 4 MiB are allowed"; R-140: a valid PNG with a corrupt font is refused and `decode` returns nothing; Inter-Regular passes; a JPEG header sniffs as `None`)
- Gate: G2.4 — `cargo test -p mutable-gui --test doc_assets` exits 0
- Requirements: R-138, R-140
- Screens: none

### Step 2.5 — Package documents and the read limit

- Builds: `doc::read_limited(reader: impl Read, max: u64) -> Result<Vec<u8>, DocError>` reads at most `max + 1` bytes and returns `TooLarge { bytes }` when it got `max + 1`; `doc::PACKAGE_MAX = 8 * 1024 * 1024`. `doc::decode_package(&[u8]) -> Result<Package, DocError>` checks format `mutable-gui/package`, migrates, requires at least one of `layout` and `theme`, checks `created` against RFC 3339 (`YYYY-MM-DDTHH:MM:SS`, optional fraction, then `Z` or `±HH:MM`, checked by hand), `name` 1–64 characters, then validates layout, theme and assets as Steps 2.1–2.4. `doc::encode_package(&Package) -> String` starts with `format` and `version`. `doc::now_rfc3339()` formats the system clock as UTC `YYYY-MM-DDTHH:MM:SSZ` (choice 15). Package fixtures over each limit: `fixtures/invalid/package-9mib.mgui` is generated by the test rather than committed; `package-pages-65.mgui`, `package-elements-2001.mgui`, `package-nesting-17.mgui`, `package-text-4097.mgui`, `package-script-field.mgui`, `package-version-99.mgui` are committed.
- Files: `crates/mutable-gui/src/doc/package.rs`, `crates/mutable-gui/src/doc/mod.rs`, `crates/mutable-gui/tests/doc_package.rs`, `crates/mutable-gui/tests/fixtures/invalid/package-pages-65.mgui`, `crates/mutable-gui/tests/fixtures/invalid/package-elements-2001.mgui`, `crates/mutable-gui/tests/fixtures/invalid/package-nesting-17.mgui`, `crates/mutable-gui/tests/fixtures/invalid/package-text-4097.mgui`, `crates/mutable-gui/tests/fixtures/invalid/package-script-field.mgui`, `crates/mutable-gui/tests/fixtures/invalid/package-version-99.mgui`
- Libraries: serde_json
- Commands: `cargo test -p mutable-gui --test doc_package`
- Tests: `crates/mutable-gui/tests/doc_package.rs` (R-137: a 9 MiB reader is refused and a counting reader saw at most 8 MiB + 1 bytes; R-139: each package fixture is refused with the text naming its limit; a layout-only and a theme-only package round-trip; a package with neither is refused)
- Gate: G2.5 — `cargo test -p mutable-gui --test doc_package` exits 0
- Requirements: R-137, R-139, R-141, R-142
- Screens: none

### Step 2.6 — Clipboard elements document

- Builds: `doc::encode_elements(&ElementsDoc) -> String` (format `mutable-gui/elements`) and `doc::decode_elements(&str) -> Result<ElementsDoc, DocError>` with the element, nesting, text and asset limits of Steps 2.1–2.4 (the 2,000-element count applies to the clipboard's own elements). Text that is not JSON or names another format is refused as "is not a mutable-gui document: …".
- Files: `crates/mutable-gui/src/doc/elements.rs`, `crates/mutable-gui/src/doc/mod.rs`, `crates/mutable-gui/tests/doc_elements.rs`
- Libraries: serde_json
- Commands: `cargo test -p mutable-gui --test doc_elements`
- Tests: `crates/mutable-gui/tests/doc_elements.rs` (a knob with an image asset round-trips; "hello" is refused; nesting 17 is refused)
- Gate: G2.6 — `cargo test -p mutable-gui --test doc_elements` exits 0
- Requirements: R-084
- Screens: none

### Step 2.7 — Malformed input never crashes

- Builds: `tests/doc_malformed.rs` runs, for each of `decode_instance`, `decode_package` and `decode_elements`, a proptest of 10,000 cases (`ProptestConfig { cases: 10_000, failure_persistence: None, ..ProptestConfig::default() }`, `rng_seed: RngSeed::Fixed(0x6d67_7569)`) half of random byte vectors of 0–4,096 bytes (passed through `String::from_utf8_lossy` where the decoder takes text) and half of the `fixtures/v1/` files truncated at a random index; each call returns `Ok` or `Err`, never panics, and takes under 1 s measured with `std::time::Instant`. Run alone.
- Files: `crates/mutable-gui/tests/doc_malformed.rs`
- Libraries: proptest
- Commands: `cargo test -p mutable-gui --test doc_malformed`
- Tests: `crates/mutable-gui/tests/doc_malformed.rs`
- Gate: G2.7 — `cargo test -p mutable-gui --test doc_malformed` exits 0
- Requirements: R-144
- Screens: none

### Step 2.8 — Package load time

- Builds: `tests/perf_package_load.rs` builds, in the test, a valid package whose four PNG assets of random pixels (seeded) total between 3.9 and 4.0 MiB decoded, encodes it, then decodes and validates it 11 times; `perf_package_load_4mib` asserts the median is at most 200 ms. `benches/package_decode.rs` reports the same with criterion. Run alone.
- Files: `crates/mutable-gui/tests/perf_package_load.rs`, `crates/mutable-gui/benches/package_decode.rs`, `crates/mutable-gui/Cargo.toml`
- Libraries: png, criterion
- Commands: `cargo test -p mutable-gui --release --test perf_package_load perf_ && cargo bench -p mutable-gui --bench package_decode --no-run`
- Tests: `crates/mutable-gui/tests/perf_package_load.rs`
- Gate: G2.8 — `cargo test -p mutable-gui --release --test perf_package_load perf_` exits 0
- Requirements: none
- Screens: none

### Step 2.9 — JSON Schemas

- Builds: the model types derive `schemars::JsonSchema`; `doc::schema::documents() -> Vec<(&'static str, schemars::Schema)>` returns the five schemas (`instance`, `layout`, `theme`, `package`, `elements`), the element schema being a `oneOf` over the 16 built-in kinds (each the common fields plus its body, `kind` a `const`) and a custom element (`kind` matching `^[a-z0-9._-]*\.[a-z0-9._-]*$`). `cargo xtask schema [--out DIR]` writes `DIR/<name>.schema.json` (default `schema/`) pretty-printed with a trailing newline. `xtask/tests/schema_current.rs` runs `env!("CARGO_BIN_EXE_xtask")` with `schema --out <temporary directory>` and compares each file byte for byte with `schema/`.
- Files: `crates/mutable-gui/src/doc/schema.rs`, `crates/mutable-gui/src/model/layout.rs`, `xtask/src/schema.rs`, `xtask/src/main.rs`, `schema/instance.schema.json`, `schema/layout.schema.json`, `schema/theme.schema.json`, `schema/package.schema.json`, `schema/elements.schema.json`, `xtask/tests/schema_current.rs`
- Libraries: schemars, tempfile
- Commands: `cargo xtask schema && cargo test -p xtask --test schema_current`
- Tests: `xtask/tests/schema_current.rs`
- Gate: G2.9 — `cargo test -p xtask --test schema_current` exits 0
- Requirements: none
- Screens: none

### Step 2.10 — Notices

- Builds: `editor::notices` holds `Notice { id: u64, severity: Severity (Error, Warning), summary: String, detail: String, actions: Vec<NoticeAction> }` with `EditorState::raise(notice)`, `dismiss(id)`, `notices()`. `render::chrome::notices` draws them as an `egui::Area` stack above the menu button, newest at the bottom, 320 px wide, each with `ICON_ERROR` in danger or `ICON_WARNING` in warning colour, the summary in Inter Medium 12 px, the detail in 12 px muted text, action buttons, and a × button; the menu button shows a 6 px accent dot while any notice exists. A notice lives until dismissed (R-012); it requests no frames by itself.
- Files: `crates/mutable-gui/src/editor/notices.rs`, `crates/mutable-gui/src/render/chrome/notices.rs`, `crates/mutable-gui/src/render/chrome/menu_button.rs`, `crates/mutable-gui/tests/chrome_notices.rs`, `crates/mutable-gui/tests/snapshots/notice-error.png`
- Libraries: egui, egui_material_icons, egui_kittest
- Commands: `cargo test -p mutable-gui --test chrome_notices`
- Tests: `crates/mutable-gui/tests/chrome_notices.rs` (R-012: a raised notice is present after 600 frames and absent on the frame after its × is clicked; the dot shows while it exists; a picture of an error notice)
- Gate: G2.10 — `cargo test -p mutable-gui --test chrome_notices` exits 0
- Requirements: R-012
- Screens: none

### Step 2.11 — Embedded developer default

- Builds: `editor::defaults` uses `config.embedded_default` when present: `decode_package` (with `PACKAGE_MAX`), then the package's layout (else the generated one), its theme (else Studio Dark) and its assets form the developer default; a package from another plugin is used as is, with no notice (bindings resolve by id). A decode failure gives the generated layout with Studio Dark and raises the "Invalid embedded default" notice with the `DocError` text (R-002). Parameters and audio never depend on it.
- Files: `crates/mutable-gui/src/editor/defaults.rs`, `crates/mutable-gui/tests/editor_embedded.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test editor_embedded`
- Tests: `crates/mutable-gui/tests/editor_embedded.rs` (R-001: with an embedded package built in the test, the first frame's layout and theme equal the package's as documents; R-002: a truncated package opens on the generated layout with exactly one notice containing the decoder's message)
- Gate: G2.11 — `cargo test -p mutable-gui --test editor_embedded` exits 0
- Requirements: R-001, R-002
- Screens: none
- Pins: Step 1.17's `editor_defaults.rs` configures no embedded default; its assertions hold.

### Step 2.12 — The reference plugin's default package

- Builds: `cargo xtask reference-default` writes `examples/reference-plugin/assets/default.mgui` from a table in `xtask/src/reference_default.rs`; `--check` exits 1 when the file differs. xtask depends on the reference plugin's library and reads its parameters with `mutable_gui_nice::params::infos(&RefParams::default())` for the generated pages. Package name "Reference FX default", source `org.mutable-gui.reference` / `0.1.0` / the core version, `created` `2026-11-22T00:00:00Z`, theme Studio Dark, no assets. Layout: canvas 840 × 520, grid 8 with snap, pages "Main", "Filter", "Dynamics", "Mod". "Main" holds the `REF` elements of `design/ui/kit.js` with the same frames: label "REFERENCE FX" (heading, size 15, tracking 2); page tabs; panels "Filter", "Drive", "Compressor", "Output" (`title`); knobs `cutoff`, `resonance`, `filter_env_amount`; segmented selector `filter_mode` (caption ""); switch `key_track` (caption "Key track"); knob `drive` (`arc: accent-3`); switch `oversample` (caption "Oversample 2×"); knobs `threshold`, `ratio` (`arc: accent-4`), `attack`, `release` (`arc: accent-4`, `knob_style: pointer`); gain-reduction meter tap `gr`; fader `makeup` (`fill: accent-4`); oscilloscope tap `out`; macro caption "Character" with targets `drive` 0–1, `filter_drive` 0–1, `resonance` 0.2–0.6; fader `out_level` (caption "Level"); level meter tap `out`; knob `mix` (`knob_style: filled`). "Filter", "Dynamics" and "Mod" hold the label and page tabs of `generate::layout`'s page geometry and the cells it produces for the groups Filter, Compressor and Modulation. Ids are deterministic version-4 UUIDs. `xtask/tests/reference_default_current.rs` runs `env!("CARGO_BIN_EXE_xtask")` with `reference-default --check`.
- Files: `xtask/src/reference_default.rs`, `xtask/src/main.rs`, `xtask/Cargo.toml`, `examples/reference-plugin/assets/default.mgui`, `xtask/tests/reference_default_current.rs`
- Libraries: uuid, serde_json
- Commands: `cargo xtask reference-default && cargo test -p xtask --test reference_default_current`
- Tests: `xtask/tests/reference_default_current.rs`
- Gate: G2.12 — `cargo test -p xtask --test reference_default_current` exits 0
- Requirements: none
- Screens: none

### Step 2.13 — Reference plugin embeds its default

- Builds: `RefFx`'s builder adds `.embedded_default(include_bytes!("../assets/default.mgui"))`. The reference fixture of `tests/common/mod.rs` gains an option to build without it (used by S-13).
- Files: `examples/reference-plugin/src/lib.rs`, `examples/reference-plugin/tests/common/mod.rs`, `examples/reference-plugin/tests/embedded_default.rs`
- Libraries: nice-plug
- Commands: `cargo test -p mutable-gui-reference --test embedded_default --test screen_s13 --test round_trip`
- Tests: `examples/reference-plugin/tests/embedded_default.rs` (R-001 acceptance: with an empty cell, the first editor's layout and theme equal those of `default.mgui` as documents)
- Gate: G2.13 — `cargo test -p mutable-gui-reference --test embedded_default --test screen_s13 --test round_trip` exits 0
- Requirements: R-001
- Screens: none
- Pins: Step 1.26's `round_trip.rs` now starts from the embedded layout; it compares saved and loaded documents and holds. Step 1.27's `screen_s13.rs` builds without the embedded default and holds.

### Step 2.14 — Unreadable saved state falls back and is kept

- Builds: `editor::load` handles a cell string that fails `decode_instance`: the editor shows the fallback (the user default once Step 8.5 exists, else the developer default), calls `StateCell::keep_unreadable` with the original string, and raises the "Unreadable saved state" notice whose cause is "It was saved by a newer version of the plugin" for `Newer` and "It is damaged ({DocError})" otherwise, with the action "Keep it" (dismisses; the layout stays kept). `EditorState::is_preserving()` is true while kept; page and window changes then publish nothing, so every host save returns the original string (R-118). Step 8.10 adds the "Discard saved layout…" action.
- Files: `crates/mutable-gui/src/editor/load.rs`, `crates/mutable-gui/src/editor/mod.rs`, `crates/mutable-gui/tests/editor_unreadable.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test editor_unreadable`
- Tests: `crates/mutable-gui/tests/editor_unreadable.rs` (R-117: truncated state shows the developer default and one notice with the summary and "It is damaged"; a version-3 state shows the newer-version cause; R-118: after loading bytes X and changing page, `cell.load()` is X byte for byte)
- Gate: G2.14 — `cargo test -p mutable-gui --test editor_unreadable` exits 0
- Requirements: R-117, R-118
- Screens: none

### Step 2.15 — State loaded while the editor is open

- Builds: at the start of each frame, when the cell's generation differs from the one decoded, `editor::load` ends every open gesture through the tracker, drops any drag (choice 16), decodes the new string (readable: it replaces the document, leaves preserving, clears the undo history once Step 5.2 exists; unreadable: Step 2.14), and shows the new state's current page on that frame.
- Files: `crates/mutable-gui/src/editor/load.rs`, `crates/mutable-gui/tests/editor_host_load.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test editor_host_load`
- Tests: `crates/mutable-gui/tests/editor_host_load.rs` (R-116: storing a saved state whose current page is page 3 shows page 3 on the following frame; storing it during a knob drag records the knob's end before the switch)
- Gate: G2.15 — `cargo test -p mutable-gui --test editor_host_load` exits 0
- Requirements: R-116
- Screens: none

### Step 2.16 — Project round trip with assets

- Builds: the reference round-trip test gains a case whose instance holds a PNG image element and a theme whose body typeface is a font asset (Inter-Medium's bytes): saved and loaded instances are equal as documents, assets included.
- Files: `examples/reference-plugin/tests/round_trip.rs`
- Libraries: base64
- Commands: `cargo test -p mutable-gui-reference --test round_trip && cargo xtask bundle mutable-gui-reference --release && sh tools/validate-clap.sh`
- Tests: `examples/reference-plugin/tests/round_trip.rs`
- Gate: G2.16 — `cargo test -p mutable-gui-reference --test round_trip && cargo xtask bundle mutable-gui-reference --release && sh tools/validate-clap.sh` exits 0
- Requirements: R-110
- Screens: none

### Step 2.17 — Documents at Phase 2 truth

- Builds: `docs/ARCHITECTURE.md` adds the `doc` module and invariants I-07, I-08, I-14, I-15, I-16 with their tests; `docs/RUNBOOK.md` adds `cargo xtask schema`, `cargo xtask reference-default`, and what the unreadable-layout notice means for a user; `docs/TESTING.md` adds the fixture folders and the malformed-input test; `CHANGELOG.md` adds the embedded default, validation limits and notices.
- Files: `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, `docs/TESTING.md`, `CHANGELOG.md`
- Libraries: none
- Commands: `grep -q "I-16" docs/ARCHITECTURE.md && grep -q "reference-default" docs/RUNBOOK.md && ! grep -q "[<][<]" docs/ARCHITECTURE.md docs/RUNBOOK.md docs/TESTING.md CHANGELOG.md`
- Tests: none
- Gate: G2.17 — `grep -q "I-16" docs/ARCHITECTURE.md && grep -q "reference-default" docs/RUNBOOK.md && ! grep -q "[<][<]" docs/ARCHITECTURE.md docs/RUNBOOK.md docs/TESTING.md CHANGELOG.md` exits 0
- Requirements: none
- Screens: none

### Step 2.18 — Phase 2 check sheet

- Builds: `docs/qa/phase-02.md` lists, each with "Result: not run": (1) a new Reference FX instance opens on the "Main" page of the default (labels, panels, knobs, switches, selector and page tabs drawn; faders, the macro and the displays as dashed frames until Phases 3–4); (2) the four page tabs switch pages; (3) a project saved with the default and reopened is identical. It ends with "Signed off: no".
- Files: `docs/qa/phase-02.md`
- Libraries: none
- Commands: `grep -q "^Signed off: no" docs/qa/phase-02.md`
- Tests: none
- Gate: G2.18 — `grep -q "^Signed off: no" docs/qa/phase-02.md` exits 0
- Requirements: none
- Screens: none

### Step 2.19 — [OWNER] Phase 2 host check

- Builds: the owner performs the items of `docs/qa/phase-02.md`, records each result and signs off.
- Files: `docs/qa/phase-02.md`
- Libraries: Bitwig Studio
- Commands: `cargo xtask bundle mutable-gui-reference --release`
- Tests: none
- Gate: G2.19 — `grep -q "^Signed off: yes" docs/qa/phase-02.md` exits 0
- Requirements: R-001
- Screens: none

**Exit demo:** Following `README.md` and `docs/RUNBOOK.md`: install the fresh bundle, insert Reference FX in Bitwig and see its four-page default, switch pages, save and reopen the project identically; run `cargo test -p mutable-gui --test doc_package --test editor_unreadable` and read the refusals and the kept-layout notice the tests assert.

## Phase 3 — Signal taps and displays

**Goal:** The scope, level meter and gain-reduction meter of Reference FX's default move with the audio in Bitwig, while the only library code on the audio thread is a wait-free push that allocates nothing and copies nothing when no display reads it.

### Step 3.1 — Tap declaration

- Builds: `taps::TapRegistry::new()`; `declare_audio(name, channels: u8, capacity: u32) -> Result<AudioTapProducer, TapError>` (channels 1 or 2, capacity 1,024–262,144 frames); `declare_scalar(name) -> Result<ScalarTapProducer, TapError>`; `TapError` (`DuplicateName`, `Channels`, `Capacity`, `EmptyName`) leaves the registry unchanged; `list() -> Vec<TapInfo { name, kind: TapKind }>` with `TapKind::Audio { channels, capacity }` or `TapKind::Scalar`, in declaration order; `into_reader(self) -> TapReader` hands every consumer to the editor. Producers are `Send` and move to the plugin's audio side.
- Files: `crates/mutable-gui/src/taps/mod.rs`, `crates/mutable-gui/src/lib.rs`, `crates/mutable-gui/tests/taps_declare.rs`
- Libraries: rtrb
- Commands: `cargo test -p mutable-gui --test taps_declare`
- Tests: `crates/mutable-gui/tests/taps_declare.rs` (R-007 acceptance; R-008: a second "out" returns `DuplicateName` and "out" keeps 2 channels and 16,384 frames; capacity 1,023 is refused)
- Gate: G3.1 — `cargo test -p mutable-gui --test taps_declare` exits 0
- Requirements: R-007, R-008
- Screens: none

### Step 3.2 — Audio tap

- Builds: `taps::audio` pairs an `rtrb::RingBuffer<f32>` of `capacity × channels` samples (interleaved) with an `Arc` of shared atomics: `reading: AtomicBool`, `copied: AtomicU64`, `sample_rate: AtomicU32` (f32 bits), `rate_changes: AtomicU32`. `AudioTapProducer::push(&mut self, channels: &[&[f32]])`: one `Acquire` load of `reading`; false returns at once (R-041); true writes the whole frames that fit through `write_chunk_uninit(...).fill_from_iter(...)`, drops the rest, and adds the frames written to `copied` (R-042, R-043). `set_sample_rate(hz)` stores the rate and increments `rate_changes` (R-046). `AudioTapConsumer` (in `TapReader`) has `set_reading(bool)`, `discard()`, `drain_into(&mut Vec<f32>)`, `sample_rate()`, `rate_changes()`, `copied_frames()`. No allocation, lock, system call or loop beyond one per frame in `push` (I-01).
- Files: `crates/mutable-gui/src/taps/audio.rs`, `crates/mutable-gui/src/taps/mod.rs`, `crates/mutable-gui/tests/taps_audio.rs`
- Libraries: rtrb
- Commands: `cargo test -p mutable-gui --test taps_audio`
- Tests: `crates/mutable-gui/tests/taps_audio.rs` (R-041: 1,000 pushes of 512 frames with no reader leave `copied_frames() == 0`; R-042: with reading set, 512 frames become available; R-043: 20,000 frames into a 16,384-frame tap never read leave exactly the first 16,384 readable; R-046: `set_sample_rate(48_000.0)` is read back)
- Gate: G3.2 — `cargo test -p mutable-gui --test taps_audio` exits 0
- Requirements: R-041, R-042, R-043, R-046
- Screens: none

### Step 3.3 — Scalar tap

- Builds: `taps::scalar` stores `latest: AtomicU32` (f32 bits) and `max: AtomicU32` holding an order-preserving key of f32 (`bits ^ 0x8000_0000` for non-negative values, `!bits` for negative). `ScalarTapProducer::push(v)` stores `latest` and calls `max.fetch_max(key(v))`. `ScalarTapConsumer::read() -> (latest, max)` swaps `max` to the key of negative infinity and returns the swapped maximum, or `latest` when nothing was pushed since the previous read.
- Files: `crates/mutable-gui/src/taps/scalar.rs`, `crates/mutable-gui/src/taps/mod.rs`, `crates/mutable-gui/tests/taps_scalar.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test taps_scalar`
- Tests: `crates/mutable-gui/tests/taps_scalar.rs` (R-045 acceptance; −3 then −1 gives maximum −1)
- Gate: G3.3 — `cargo test -p mutable-gui --test taps_scalar` exits 0
- Requirements: R-045
- Screens: none

### Step 3.4 — Push cost and allocation

- Builds: `tests/alloc_taps.rs` runs, under `assert_no_alloc`, 1,000 audio pushes of 512 stereo frames without a reader, 1,000 with a reader (draining between them outside the guard), and 1,000 scalar pushes, asserting `violation_count() == 0`. `tests/perf_scalar_push.rs` (`perf_scalar_push_under_100ns`) times 10,000,000 scalar pushes and asserts a mean at most 100 ns. `benches/tap_push.rs` reports audio pushes of 64, 512 and 4,096 frames and the scalar push. `tests/arch_boundaries.rs` reads the sources and asserts that no file under `src/taps/` mentions `analysis`, `Mutex`, `RwLock`, `std::fs`, `std::thread::sleep` or `Vec::` (R-055, I-11), that `crates/mutable-gui/Cargo.toml` names no `nice-plug`, `baseview` or `egui-baseview` (I-05), and that `Cargo.lock` holds no package named `reqwest`, `hyper`, `ureq`, `curl`, `isahc`, `surf`, `attohttpc` or `tungstenite` (I-13). Run alone.
- Files: `crates/mutable-gui/tests/alloc_taps.rs`, `crates/mutable-gui/tests/perf_scalar_push.rs`, `crates/mutable-gui/tests/arch_boundaries.rs`, `crates/mutable-gui/benches/tap_push.rs`, `crates/mutable-gui/Cargo.toml`
- Libraries: nice-assert-no-alloc, criterion
- Commands: `cargo test -p mutable-gui --test alloc_taps --test arch_boundaries && cargo test -p mutable-gui --release --test perf_scalar_push perf_`
- Tests: `crates/mutable-gui/tests/alloc_taps.rs`, `crates/mutable-gui/tests/perf_scalar_push.rs`, `crates/mutable-gui/tests/arch_boundaries.rs`
- Gate: G3.4 — `cargo test -p mutable-gui --test alloc_taps --test arch_boundaries && cargo test -p mutable-gui --release --test perf_scalar_push perf_` exits 0
- Requirements: R-044, R-055
- Screens: none

### Step 3.5 — Spectrum analysis

- Builds: `analysis::spectrum::Spectrum::new(fft_size)` (1,024, 2,048, 4,096 or 8,192; realfft planner, Hann window, scratch buffers allocated here on the editor thread); `process(&mut self, samples: &[f32]) -> &[f32]` returns magnitudes in dBFS per bin, scaled so a full-scale sine reads 0 dB (factor `2 / Σ window`); `bin_frequency(k, sample_rate)`; `x_for_frequency(f, sample_rate, width)` on a log axis from 20 Hz to `sample_rate / 2`.
- Files: `crates/mutable-gui/src/analysis/mod.rs`, `crates/mutable-gui/src/analysis/spectrum.rs`, `crates/mutable-gui/src/lib.rs`, `crates/mutable-gui/tests/analysis_spectrum.rs`
- Libraries: realfft
- Commands: `cargo test -p mutable-gui --test analysis_spectrum`
- Tests: `crates/mutable-gui/tests/analysis_spectrum.rs` (R-049: a 1 kHz sine at −6 dBFS, 48 kHz, FFT 4,096 peaks within one bin of 1 kHz and within 1 dB of −6; R-046: at 48 kHz the axis ends at 24,000 Hz)
- Gate: G3.5 — `cargo test -p mutable-gui --test analysis_spectrum` exits 0
- Requirements: R-046, R-049
- Screens: none

### Step 3.6 — Level analysis

- Builds: `analysis::level::Level::new(sample_rate)`; `feed(&mut self, samples: &[f32], channels)` updates per channel the block peak, a 300 ms RMS over a ring of squared samples, and a held peak that stays 1.5 s then falls to the current peak; `frame(dt)` advances hold time; values in dBFS clamped to −60…+6 for drawing. `analysis::level::gr_db(max: f32) -> f32` passes the scalar maximum through.
- Files: `crates/mutable-gui/src/analysis/level.rs`, `crates/mutable-gui/src/analysis/mod.rs`, `crates/mutable-gui/tests/analysis_level.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test analysis_level`
- Tests: `crates/mutable-gui/tests/analysis_level.rs` (R-050: a full-scale sine gives peak 0 dBFS and RMS −3 dBFS within 0.5 dB; after the signal stops at 60 frames per second the held peak lasts 1.5 s ± one frame)
- Gate: G3.6 — `cargo test -p mutable-gui --test analysis_level` exits 0
- Requirements: R-050
- Screens: none

### Step 3.7 — Reading taps in the editor

- Builds: `EditorState::with_taps(TapReader)` (builder-time). `editor::taps` runs before drawing each frame: the taps bound by displays on the current page (custom tap slots join in Step 7.6) get `set_reading(true)`, all others `false` (I-17); a tap turning on calls `discard()` and clears its history (R-047); a changed `rate_changes()` clears its history; audio taps drain into a per-tap history of `capacity × channels` samples kept on the editor thread, feeding `Level` and `Spectrum` there (I-11); scalar taps are read once per frame. Closing the editor turns every flag off.
- Files: `crates/mutable-gui/src/editor/taps.rs`, `crates/mutable-gui/src/editor/mod.rs`, `crates/mutable-gui/tests/editor_taps.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test editor_taps`
- Tests: `crates/mutable-gui/tests/editor_taps.rs` (I-17: the flag is set only while a scope bound to "out" is on the current page and the editor is open; R-047: samples pushed before the page switch are not in the history after it; R-042 through the editor: 512 pushed frames reach the history)
- Gate: G3.7 — `cargo test -p mutable-gui --test editor_taps` exits 0
- Requirements: R-042, R-047
- Screens: none

### Step 3.8 — Oscilloscope drawing

- Builds: `render::oscilloscope::draw` and `model` draw the most recent `window_ms × sample_rate / 1000` frames, one polyline per channel (`trace`, `trace_2`) over `background` with a centre line and quarter grid in `grid`. A tap name the plugin did not declare draws "No signal: <name>" in the `text` slot's text-muted role (R-052); a null tap draws "No signal"; a display narrower than 80 canvas units draws a dashed outline and the text rotated to read upward (D-44). `ScopeModel { samples_per_trace, traces }`.
- Files: `crates/mutable-gui/src/render/oscilloscope.rs`, `crates/mutable-gui/src/render/no_signal.rs`, `crates/mutable-gui/tests/render_scope.rs`, `crates/mutable-gui/tests/snapshots/scope.png`
- Libraries: egui, egui_kittest
- Commands: `cargo test -p mutable-gui --test render_scope`
- Tests: `crates/mutable-gui/tests/render_scope.rs` (R-048: 50 ms at 48 kHz of a pushed 1 kHz sine gives 2,400 samples per trace with 50 upward zero crossings ± 1; R-052: a scope bound to "gone" draws "No signal: gone"; a picture)
- Gate: G3.8 — `cargo test -p mutable-gui --test render_scope` exits 0
- Requirements: R-048, R-052
- Screens: none

### Step 3.9 — Spectrum drawing

- Builds: `render::spectrum::draw` and `model` draw the dB magnitudes of the tap's newest `fft_size` frames (mono sum of channels) on the log axis, from `floor_db` to 0 dB, as a filled polyline in `trace` over `background` with decade grid lines in `grid`; missing or null tap as Step 3.8. `SpectrumModel { peak_hz, peak_db, top_hz }`.
- Files: `crates/mutable-gui/src/render/spectrum.rs`, `crates/mutable-gui/tests/render_spectrum.rs`, `crates/mutable-gui/tests/snapshots/spectrum.png`
- Libraries: egui, egui_kittest
- Commands: `cargo test -p mutable-gui --test render_spectrum`
- Tests: `crates/mutable-gui/tests/render_spectrum.rs` (the model's peak lies within one bin of 1 kHz for a pushed 1 kHz sine; `top_hz` is 24,000 at 48 kHz; a picture)
- Gate: G3.9 — `cargo test -p mutable-gui --test render_spectrum` exits 0
- Requirements: R-049
- Screens: none

### Step 3.10 — Level and gain-reduction meters

- Builds: `render::level_meter::draw` draws one bar per channel on a −60…+6 dB scale (`low` below −6 dB, `high` above), the held peak as a 2-unit line in `peak`, the value text (peak, "−6.2") in `value`. `render::gr_meter::draw` draws the frame's scalar maximum in dB as a bar from the top on the `range_db` scale in `bar`, with the value text ("6.7"). Narrow displays without a tap follow D-44.
- Files: `crates/mutable-gui/src/render/level_meter.rs`, `crates/mutable-gui/src/render/gr_meter.rs`, `crates/mutable-gui/tests/render_meters.rs`, `crates/mutable-gui/tests/snapshots/meters.png`
- Libraries: egui, egui_kittest
- Commands: `cargo test -p mutable-gui --test render_meters`
- Tests: `crates/mutable-gui/tests/render_meters.rs` (R-051: pushes of 2, 9 and 3 dB between two frames draw 9 dB; R-050 drawn peak and hold through the editor; a picture of both meters and their narrow "No signal")
- Gate: G3.10 — `cargo test -p mutable-gui --test render_meters` exits 0
- Requirements: R-050, R-051, R-052
- Screens: none

### Step 3.11 — Redraw only when needed

- Builds: `EditorState::frame` calls `ctx.request_repaint_after(Duration::from_micros(16_667))` at the end of every frame on which a display (or, from Step 7.4, an animating custom element) is on the current page (R-054), and requests nothing otherwise; the menu button's fade requests frames only while it runs. Parameter changes from the host reach the window through the adapter's `RepaintNotifier` (nice-plug-egui), never through the core.
- Files: `crates/mutable-gui/src/editor/mod.rs`, `crates/mutable-gui/tests/editor_repaint.rs`
- Libraries: egui, egui_kittest
- Commands: `cargo test -p mutable-gui --test editor_repaint`
- Tests: `crates/mutable-gui/tests/editor_repaint.rs` (R-053: after the first frame of a static page, 120 frames with no events end with `repaint_delay == Duration::MAX`; R-054: with a visible scope, 60 frames each end with a delay between 16 and 17 ms)
- Gate: G3.11 — `cargo test -p mutable-gui --test editor_repaint` exits 0
- Requirements: R-053, R-054
- Screens: none

### Step 3.12 — Displays wired into drawing

- Builds: `render::draw_element` dispatches oscilloscope, spectrum, level meter and gain-reduction meter to their modules with the tap histories of Step 3.7, replacing their fallback arm.
- Files: `crates/mutable-gui/src/render/mod.rs`, `crates/mutable-gui/tests/editor_displays.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test editor_displays`
- Tests: `crates/mutable-gui/tests/editor_displays.rs` (a layout with all four displays bound to fed taps records each display's model in `drawn()`; a display bound to "gone" records "No signal: gone")
- Gate: G3.12 — `cargo test -p mutable-gui --test editor_displays` exits 0
- Requirements: R-048, R-052
- Screens: none

### Step 3.13 — Reference plugin taps

- Builds: `RefFx::default()` declares `out` (2 channels, 16,384 frames) and `gr` (scalar) in a `TapRegistry`, keeps the producers, and passes the registry to `MutableGui::builder(…).taps(registry)`; `initialize()` calls `out.set_sample_rate(buffer_config.sample_rate)`; `process` pushes the output channels to `out` and the block's gain reduction to `gr` after `Dsp::process`. The adapter builder gains `.taps(TapRegistry)`, which calls `EditorState::with_taps(registry.into_reader())`.
- Files: `examples/reference-plugin/src/lib.rs`, `crates/mutable-gui-nice/src/builder.rs`, `examples/reference-plugin/tests/taps.rs`
- Libraries: nice-plug
- Commands: `cargo test -p mutable-gui-reference --test taps`
- Tests: `examples/reference-plugin/tests/taps.rs` (the editor's tap list holds "out" (audio, 2 channels) and "gr" (scalar); one processed block with the scope visible reaches the scope's history)
- Gate: G3.13 — `cargo test -p mutable-gui-reference --test taps` exits 0
- Requirements: R-007, R-046
- Screens: none

### Step 3.14 — Allocation test over the reference plugin's processing

- Builds: `examples/reference-plugin/tests/alloc_process.rs` builds `Dsp` and both producers, sets the "out" reader flag, and runs 1,000 blocks of 512 stereo frames of a seeded noise signal through `Dsp::process` and the two pushes under `assert_no_alloc`, draining the consumer between blocks outside the guard; it asserts `violation_count() == 0` (P1, I-01).
- Files: `examples/reference-plugin/tests/alloc_process.rs`, `examples/reference-plugin/Cargo.toml`
- Libraries: nice-assert-no-alloc
- Commands: `cargo test -p mutable-gui-reference --test alloc_process`
- Tests: `examples/reference-plugin/tests/alloc_process.rs`
- Gate: G3.14 — `cargo test -p mutable-gui-reference --test alloc_process` exits 0
- Requirements: R-044
- Screens: none

### Step 3.15 — Documents at Phase 3 truth

- Builds: `README.md` gains the developer's tap declaration and push example; `docs/ARCHITECTURE.md` adds `taps`, `analysis` and invariants I-01, I-11, I-17 with their tests; `docs/TESTING.md` adds the allocation tests and `perf_` tests; `CHANGELOG.md` adds taps and displays.
- Files: `README.md`, `docs/ARCHITECTURE.md`, `docs/TESTING.md`, `CHANGELOG.md`
- Libraries: none
- Commands: `grep -q "declare_audio" README.md && grep -q "I-17" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/TESTING.md CHANGELOG.md`
- Tests: none
- Gate: G3.15 — `grep -q "declare_audio" README.md && grep -q "I-17" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/TESTING.md CHANGELOG.md` exits 0
- Requirements: none
- Screens: none

### Step 3.16 — Phase 3 check sheet

- Builds: `docs/qa/phase-03.md` lists, each with "Result: not run": (1) with audio playing through Reference FX, the scope draws both channels and the level meter moves; (2) raising Drive and lowering Threshold moves the gain-reduction meter; (3) switching to the "Filter" page and back shows the scope start fresh; (4) with the editor closed and open, playback shows no dropout in Bitwig's DSP meter. It ends with "Signed off: no".
- Files: `docs/qa/phase-03.md`
- Libraries: none
- Commands: `grep -q "^Signed off: no" docs/qa/phase-03.md`
- Tests: none
- Gate: G3.16 — `grep -q "^Signed off: no" docs/qa/phase-03.md` exits 0
- Requirements: none
- Screens: none

### Step 3.17 — [OWNER] Phase 3 host check

- Builds: the owner performs the items of `docs/qa/phase-03.md`, records each result and signs off.
- Files: `docs/qa/phase-03.md`
- Libraries: Bitwig Studio
- Commands: `cargo xtask bundle mutable-gui-reference --release`
- Tests: none
- Gate: G3.17 — `grep -q "^Signed off: yes" docs/qa/phase-03.md` exits 0
- Requirements: R-054
- Screens: none

### Step 3.18 — Event tap

- Builds: `taps::events` adds `impl TapRegistry { pub fn declare_events(&mut self, name, record_len: u8, capacity: u32) -> Result<EventTapProducer, TapError> }` (record length 1–16 values, capacity 64–65,536 records; the new `TapError::RecordLength`, and `Capacity`, `DuplicateName`, `EmptyName` as Step 3.1, each leaving the registry unchanged) and `TapKind::Events { record_len, capacity }`. The tap is an `rtrb::RingBuffer<f32>` of `record_len × capacity` values with shared `reading: AtomicBool`, `copied: AtomicU64` (records) and `dropped: AtomicU64`. `EventTapProducer::push(&mut self, record: &[f32]) -> Result<(), TapPushError>` returns `TapPushError::Length` and copies nothing when the length is not `record_len`; otherwise one acquire load of `reading`, returning `Ok(())` when false; when true it writes the record whole through `write_chunk_uninit(record_len)` and `fill_from_iter` if `slots() >= record_len`, else adds 1 to `dropped`; it never panics, allocates, locks or calls the system (I-01). `EventTapConsumer` (in `TapReader`) has `set_reading(bool)`, `discard()`, `drain_into(&mut Vec<f32>) -> usize` (records appended oldest first), `take_dropped() -> u64` (swaps in 0) and `copied_records()`. `taps/mod.rs` receives only the `mod` line, the `TapKind` variant and the error variants.
- Files: `crates/mutable-gui/src/taps/events.rs`, `crates/mutable-gui/src/taps/mod.rs`, `crates/mutable-gui/tests/taps_events.rs`
- Libraries: rtrb
- Commands: `cargo test -p mutable-gui --test taps_events`
- Tests: `crates/mutable-gui/tests/taps_events.rs` (R-169: "grains" with record length 4 and capacity 4,096 is listed as an event tap of record length 4, and record length 17 and capacity 63 are refused with the registry unchanged; R-170 with drains in place of frames: 1,000 pushes with no reader copy 0 records; [1, 2, 3, 4] and [5, 6, 7, 8] arrive in that order at the next drain and none at the one after; 5,000 pushes into a 4,096-record tap keep the first 4,096 and `take_dropped()` returns 904; a 3-value push returns `Length`)
- Gate: G3.18 — `cargo test -p mutable-gui --test taps_events` exits 0
- Requirements: R-169, R-170
- Screens: none
- Feature: F-001

### Step 3.19 — Snapshot tap and allocation of the new taps

- Builds: `taps::snapshot` adds `impl TapRegistry { pub fn declare_snapshot(&mut self, name, len: u16) -> Result<SnapshotTapProducer, TapError> }` (1–1,024 values; `TapError::Length`) and `TapKind::Snapshot { len }`. The tap holds three slots of `Box<[AtomicU32]>` (f32 bits) with one `AtomicU64` sequence each, and `middle: AtomicU8` holding the middle slot's index with a fresh bit (`0x4`). `SnapshotTapProducer` owns its back index: `publish(&mut self, values: &[f32]) -> Result<(), TapPushError>` returns `Length` on a wrong length; reads `reading` with acquire and returns when false; else stores the values relaxed into the back slot, writes the next sequence into it, and swaps `back | 0x4` into `middle` with `AcqRel`, keeping the returned index as its new back slot. `SnapshotTapConsumer` owns its front index: `latest_into(&mut self, out: &mut [f32]) -> Option<u64>` swaps its front index into `middle` only when the fresh bit is set, then copies the front slot with relaxed loads and returns its sequence, or `None` before the first publish since reading started. No `unsafe` (I-05), no lock, and no loop beyond one per value (I-01). `tests/alloc_taps.rs` gains 1,000 event pushes and 1,000 snapshot publishes, each with and without a reader, under `assert_no_alloc` (R-044).
- Files: `crates/mutable-gui/src/taps/snapshot.rs`, `crates/mutable-gui/src/taps/mod.rs`, `crates/mutable-gui/tests/taps_snapshot.rs`, `crates/mutable-gui/tests/alloc_taps.rs`
- Libraries: nice-assert-no-alloc
- Commands: `cargo test -p mutable-gui --test taps_snapshot --test alloc_taps --test arch_boundaries`
- Tests: `crates/mutable-gui/tests/taps_snapshot.rs` (R-171: eight 1s then eight 2s read eight 2s; one thread publishing 1,000,000 eight-value blocks whose values all equal a counter while another reads continuously never reads two different values in one block; with no reader a publish copies nothing), `crates/mutable-gui/tests/alloc_taps.rs`
- Gate: G3.19 — `cargo test -p mutable-gui --test taps_snapshot --test alloc_taps --test arch_boundaries` exits 0
- Requirements: R-044, R-171
- Screens: none
- Feature: F-001
- Pins: Step 3.4's `alloc_taps.rs` keeps its assertions and gains the new cases; its `arch_boundaries.rs` scans every file under `src/taps/` and holds for the two new ones.

**Exit demo:** Following `README.md` and `docs/RUNBOOK.md`: play audio through Reference FX in Bitwig and watch the scope, level meter and gain-reduction meter follow it; switch pages and see the scope restart; run `cargo test -p mutable-gui --test alloc_taps` and `cargo test -p mutable-gui-reference --test alloc_process` and see zero allocations reported.

## Phase 4 — Perform mode complete

**Goal:** Every built-in control kind works in perform mode by mouse, by long press and by keyboard; the control menu resets, types and fine-locks values; S-01 and S-03 match their mockups; a 300-element page draws within 4 ms and the editor opens within 250 ms.

### Step 4.1 — Fader

- Builds: `render::fader::draw` follows kit.js `fader()`: vertical track from 4 to `h − 34` units, horizontal from 6 to `w − 6`, fill from the start to the value in `fill`, handle (`handle` fill, 26 × handle-size units vertical, handle-size × 22 horizontal), modulation band beside the track, caption and value line below. `perform::fader::drag(start, delta_along_axis, track_len, fine) -> f32` moves the value by `delta / track_len` (upward and rightward increase), so the handle follows the pointer (R-016); a press on the track away from the handle jumps the handle there first.
- Files: `crates/mutable-gui/src/render/fader.rs`, `crates/mutable-gui/src/perform/fader.rs`, `crates/mutable-gui/tests/perform_fader.rs`, `crates/mutable-gui/tests/snapshots/fader.png`
- Libraries: egui, egui_kittest
- Commands: `cargo test -p mutable-gui --test perform_fader`
- Tests: `crates/mutable-gui/tests/perform_fader.rs` (R-016: a vertical fader whose track is 200 units, dragged up 50 from 0.5, gives 0.75 ± 0.005; a picture of vertical and horizontal faders)
- Gate: G4.1 — `cargo test -p mutable-gui --test perform_fader` exits 0
- Requirements: R-016
- Screens: none

### Step 4.2 — Fine rate and fine lock

- Builds: `perform::fine::rate(shift: bool, locked: bool) -> f32` is 0.1 when either holds, else 1.0. `EditorState` keeps the set of element ids whose fine lock is on (never saved; it lives as long as the instance, R-030); knob, fader, macro and XY drags multiply their deltas by `rate`.
- Files: `crates/mutable-gui/src/perform/fine.rs`, `crates/mutable-gui/src/editor/mod.rs`, `crates/mutable-gui/tests/perform_fine.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test perform_fine`
- Tests: `crates/mutable-gui/tests/perform_fine.rs` (R-017: the R-015 drag with Shift gives 0.25 ± 0.005; R-030: with the lock on, the unmodified drag gives 0.25; the lock survives `editor_closed` and `editor_opened`)
- Gate: G4.2 — `cargo test -p mutable-gui --test perform_fine` exits 0
- Requirements: R-017, R-030
- Screens: none

### Step 4.3 — XY pad

- Builds: `render::xy_pad::draw` (kit.js `xy()`: `background` field, quarter grid, crosshair and dot in `dot`, axis names of the X and Y parameters, caption line). `perform::xy::press(rect, pos) -> (tx, ty)` maps the pointer to travel (left→right and bottom→top increase); a drag sets both from the pointer, or moves relatively at the fine rate with Shift; each bound axis begins its gesture before its first set (R-023).
- Files: `crates/mutable-gui/src/render/xy_pad.rs`, `crates/mutable-gui/src/perform/xy.rs`, `crates/mutable-gui/tests/perform_xy.rs`, `crates/mutable-gui/tests/snapshots/xy-pad.png`
- Libraries: egui, egui_kittest
- Commands: `cargo test -p mutable-gui --test perform_xy`
- Tests: `crates/mutable-gui/tests/perform_xy.rs` (R-019: a press at the centre dragged to the top-right corner gives X and Y their binding maxima; a picture)
- Gate: G4.3 — `cargo test -p mutable-gui --test perform_xy` exits 0
- Requirements: R-019
- Screens: none

### Step 4.4 — Macro

- Builds: `render::macro_::draw` draws a knob in the `arc` style of the macro slot table, a target-count badge, the caption and "57 %"-style value text (position × 100, rounded). `perform::macro_::targets_for(position, targets) -> Vec<(param, f32)>` maps p through each bound target (`travel_to_normalized`, R-034); `perform::macro_::position(targets, params)` is the inverse of the first bound target's mapping at its base value, clamped 0–1 (R-035, D-30). Unbound targets are skipped and the unbound mark is drawn (R-036).
- Files: `crates/mutable-gui/src/render/macro_.rs`, `crates/mutable-gui/src/perform/macro_.rs`, `crates/mutable-gui/tests/perform_macro.rs`, `crates/mutable-gui/tests/snapshots/macro.png`
- Libraries: egui, egui_kittest
- Commands: `cargo test -p mutable-gui --test perform_macro`
- Tests: `crates/mutable-gui/tests/perform_macro.rs` (R-034: 0.5 with targets 0.2–0.6 and 0–1 reversed gives 0.4 and 0.5; R-035: first target at 0.5 on range 0.2–0.6 shows 0.75; a picture)
- Gate: G4.4 — `cargo test -p mutable-gui --test perform_macro` exits 0
- Requirements: R-034, R-035
- Screens: none

### Step 4.5 — Menu element

- Builds: `render::menu::draw` draws the `label` field with a chevron. A click opens an `egui::Area` list of the item texts (tool style); choosing `open_page` makes that page current; choosing `set` sets the parameter to `step_value(step)` as begin, set, end (choice 20, R-024); an item whose parameter or page is absent is drawn at half opacity and does nothing.
- Files: `crates/mutable-gui/src/render/menu.rs`, `crates/mutable-gui/src/perform/menu.rs`, `crates/mutable-gui/tests/perform_menu.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test perform_menu`
- Tests: `crates/mutable-gui/tests/perform_menu.rs` (R-021: items "Open page FX" and "Wave: Saw" make page "FX" current and set the wave parameter to "Saw")
- Gate: G4.5 — `cargo test -p mutable-gui --test perform_menu` exits 0
- Requirements: R-021
- Screens: none

### Step 4.6 — Image element

- Builds: `render::image::draw` loads a PNG asset once per asset id into an `egui::TextureHandle` cached in `EditorState` (dropped when no element uses it), drawn with `fit` contain, cover or stretch inside the frame; a null asset draws a dashed outline with "No image" in text-muted.
- Files: `crates/mutable-gui/src/render/image.rs`, `crates/mutable-gui/tests/render_image.rs`, `crates/mutable-gui/tests/snapshots/image-fits.png`
- Libraries: egui, png, egui_kittest
- Commands: `cargo test -p mutable-gui --test render_image`
- Tests: `crates/mutable-gui/tests/render_image.rs`
- Gate: G4.6 — `cargo test -p mutable-gui --test render_image` exits 0
- Requirements: none
- Screens: none

### Step 4.7 — Remaining kinds wired into drawing and input

- Builds: `render::draw_element` dispatches fader, XY pad, macro, menu and image to their modules; `perform::frame` dispatches presses on faders, XY pads, macros and menus to theirs. Only custom kinds still use the fallback (Step 7.7).
- Files: `crates/mutable-gui/src/render/mod.rs`, `crates/mutable-gui/src/perform/mod.rs`, `crates/mutable-gui/tests/editor_controls.rs`
- Libraries: egui, egui_kittest
- Commands: `cargo test -p mutable-gui --test editor_controls`
- Tests: `crates/mutable-gui/tests/editor_controls.rs` (through the editor: R-016 fader drag; R-019 XY drag; R-021 menu item; R-023 XY records begin X, begin Y, sets, ends with each begin before its first set; R-034 macro drag sets both targets)
- Gate: G4.7 — `cargo test -p mutable-gui --test editor_controls` exits 0
- Requirements: R-016, R-019, R-021, R-023, R-034
- Screens: none

### Step 4.8 — Unbound parameters ignore input

- Builds: `perform::frame` filters every control's bindings to the parameters `ParamSource::info` knows; a control with none present ignores presses and draws unbound with the missing id on its value line (R-037); a control with some present sends gestures only for those (R-038); a macro with an absent target still moves its present targets and shows the unbound mark (R-036). Guards: GD-7 applies to every perform input path of Steps 1.16, 4.1–4.5 and 4.9–4.11.
- Files: `crates/mutable-gui/src/perform/mod.rs`, `crates/mutable-gui/tests/perform_unbound.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test perform_unbound`
- Tests: `crates/mutable-gui/tests/perform_unbound.rs` (R-037: a knob bound to "gone" draws "gone" and a drag records nothing; R-038: an XY pad with Y unbound records gestures for X only; R-036: a macro with "cutoff" and "gone" changes "cutoff" and is drawn unbound-marked)
- Gate: G4.8 — `cargo test -p mutable-gui --test perform_unbound` exits 0
- Requirements: R-036, R-037, R-038
- Screens: none

### Step 4.9 — Control menu and long press

- Builds: `perform::control_menu` opens, on a right-click in perform mode or a long press (choice 9) of a knob, fader, switch, XY pad, macro or selector (choice 23), an `egui::Area` at the pointer (tool style) with a header (parameter name, current value text) and exactly three entries: "Reset" with the default value's text, "Type value…" with "↩", and "Fine adjust" as a check item. Reset sets every bound present parameter to its `default` as begin, set, end each (R-029, R-024); Fine adjust toggles the element's lock (R-030); Escape or a click outside closes with no change (R-148). `perform::long_press` tracks press time and movement; a long press never changes a value (R-039).
- Files: `crates/mutable-gui/src/perform/control_menu.rs`, `crates/mutable-gui/src/perform/long_press.rs`, `crates/mutable-gui/tests/perform_control_menu.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test perform_control_menu`
- Tests: `crates/mutable-gui/tests/perform_control_menu.rs` (R-040: a right-click on a knob opens a menu of exactly Reset, Type value, Fine adjust; R-039: a 700 ms stationary press opens it and records no gesture; R-029: Reset on a macro with two targets sets both to their defaults; R-024: Reset records begin, set, end per parameter; R-148: Escape closes it)
- Gate: G4.9 — `cargo test -p mutable-gui --test perform_control_menu` exits 0
- Requirements: R-024, R-029, R-030, R-039, R-040, R-148
- Screens: none

### Step 4.10 — Value field

- Builds: `perform::value_field` replaces the control's value line with an `egui::TextEdit` (mg-value, focused, prefilled with the current text, selected). ↩ calls `ParamSource::parse`; a value is set as begin, set, end (R-027, R-024); `None` keeps the field open with a danger outline and "Not a valid value" below it until the text changes or the field closes (R-028); Escape closes with no change (R-148). Offered for knob, fader, switch and selector; disabled for XY pad and macro (choice 24).
- Files: `crates/mutable-gui/src/perform/value_field.rs`, `crates/mutable-gui/src/perform/control_menu.rs`, `crates/mutable-gui/tests/perform_value_field.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test perform_value_field`
- Tests: `crates/mutable-gui/tests/perform_value_field.rs` (R-027: "1000" into a frequency knob whose parser maps it to 0.62 sets 0.62; R-028: "abc" leaves the value and shows the message; R-148: "5" then Escape leaves the value and closes the field)
- Gate: G4.10 — `cargo test -p mutable-gui --test perform_value_field` exits 0
- Requirements: R-024, R-027, R-028, R-148
- Screens: none

### Step 4.11 — Keyboard focus and adjustment

- Builds: `perform::keyboard`: Tab and Shift+Tab move focus through the current page's controls ordered by top edge then left edge, wrapping (R-145); the focused control draws the focus outline (R-109). Up and Right raise by 1 % of the binding's travel (0.1 % with Shift) or one step of a stepped parameter, Down and Left lower, each press one begin, set, end (R-146; choice 25 for XY pads, page tabs and menus). Enter opens the value field (R-147); Escape closes an open menu or field (R-148). Keys are read only while no egui widget wants keyboard input.
- Files: `crates/mutable-gui/src/perform/keyboard.rs`, `crates/mutable-gui/src/perform/mod.rs`, `crates/mutable-gui/tests/perform_keyboard.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test perform_keyboard`
- Tests: `crates/mutable-gui/tests/perform_keyboard.rs` (R-145: controls at (0,0), (100,0), (0,100) take focus in that order then the first again; R-146: Up on 0.5 gives 0.51 and Shift+Up 0.501; R-147: Tab, Enter, "0", Enter sets the parser's value of "0"; the focused knob's drawn model is focused)
- Gate: G4.11 — `cargo test -p mutable-gui --test perform_keyboard` exits 0
- Requirements: R-109, R-145, R-146, R-147, R-148
- Screens: none

### Step 4.12 — S-01 perform screen

- Builds: `examples/reference-plugin/tests/screen_s01.rs` opens the reference default at 840 × 520, feeds "out" a seeded 220 Hz stereo sine and "gr" 6.7 dB, sets Cutoff's modulation offset so its modulated value is 0.74 (`RecordingGuiContext`), and snapshots `S-01-perform`; a second test snapshots `S-01-perform--states` from `design/ui/S-01-perform--states.html`: Cutoff dragging (bubble), Resonance focused, the Env Amt knob rebound to the absent `env_amount` (unbound), the scope rebound to the absent tap "sidechain" (No signal), one warning notice raised (menu-button dot). `design/UI.md` S-01 gets `Built: examples/reference-plugin/tests/snapshots/S-01-perform.png`.
- Files: `examples/reference-plugin/tests/screen_s01.rs`, `examples/reference-plugin/tests/snapshots/S-01-perform.png`, `examples/reference-plugin/tests/snapshots/S-01-perform--states.png`, `design/UI.md`
- Libraries: egui_kittest
- Commands: `cargo test -p mutable-gui-reference --test screen_s01 && python3 tools/devpipe/run.py ui compare S-01`
- Tests: `examples/reference-plugin/tests/screen_s01.rs`
- Gate: G4.12 — `cargo test -p mutable-gui-reference --test screen_s01 && python3 tools/devpipe/run.py ui compare S-01` exits 0
- Requirements: R-013, R-032, R-037, R-052
- Screens: S-01

### Step 4.13 — S-03 control menu screen

- Builds: `examples/reference-plugin/tests/screen_s03.rs` right-clicks Cutoff on the reference default and snapshots `S-03-control-menu`; chooses Type value… and types "1.5k" for `S-03-control-menu--value`; types "abc", ↩, for `S-03-control-menu--error`. `design/UI.md` S-03 gets `Built: examples/reference-plugin/tests/snapshots/S-03-control-menu.png`.
- Files: `examples/reference-plugin/tests/screen_s03.rs`, `examples/reference-plugin/tests/snapshots/S-03-control-menu.png`, `examples/reference-plugin/tests/snapshots/S-03-control-menu--value.png`, `examples/reference-plugin/tests/snapshots/S-03-control-menu--error.png`, `design/UI.md`
- Libraries: egui_kittest
- Commands: `cargo test -p mutable-gui-reference --test screen_s03 && python3 tools/devpipe/run.py ui compare S-03`
- Tests: `examples/reference-plugin/tests/screen_s03.rs`
- Gate: G4.13 — `cargo test -p mutable-gui-reference --test screen_s03 && python3 tools/devpipe/run.py ui compare S-03` exits 0
- Requirements: R-027, R-028, R-040
- Screens: S-03

### Step 4.14 — Element gallery of the built-in kinds

- Builds: `mutable_gui_testkit::gallery::draw(ui, theme, rows)` lays out the S-12 reference sheet: 1080 px wide, a 200 px column with each row's name (tool text) and kind id (mono, muted), then five 160 px columns headed Normal, Hover, Dragging, Focused, Unbound; rows in the order of `design/ui/S-12-elements.html` with its element sizes and the states that row lists (a blank where it lists none). `examples/reference-plugin/tests/screen_s12.rs` snapshots the built-in rows in Studio Dark, Studio Light and High Contrast (`S-12-elements`, `S-12-elements--light`, `S-12-elements--high-contrast`, 1080 × 2780). Step 7.11 adds the custom and unknown rows and writes the `Built:` line.
- Files: `crates/mutable-gui-testkit/src/gallery.rs`, `crates/mutable-gui-testkit/src/lib.rs`, `examples/reference-plugin/tests/screen_s12.rs`, `examples/reference-plugin/tests/snapshots/S-12-elements.png`, `examples/reference-plugin/tests/snapshots/S-12-elements--light.png`, `examples/reference-plugin/tests/snapshots/S-12-elements--high-contrast.png`
- Libraries: egui_kittest
- Commands: `cargo test -p mutable-gui-reference --test screen_s12`
- Tests: `examples/reference-plugin/tests/screen_s12.rs`
- Gate: G4.14 — `cargo test -p mutable-gui-reference --test screen_s12` exits 0
- Requirements: R-102, R-106, R-109
- Screens: S-12

### Step 4.15 — Frame time

- Builds: `crates/mutable-gui/tests/fixtures/frame-300.json` is an instance whose one page holds 300 elements (120 knobs, 40 faders, 40 switches, 20 selectors, 20 labels, 20 panels, 10 macros, 10 XY pads, 10 level meters, 10 oscilloscopes, bound to a 300-parameter fake tree and two fed taps). `tests/perf_frame.rs` (`perf_frame_300_elements_under_4ms`) runs 600 frames of `EditorState::frame` through `egui::Context::run_ui` plus `Context::tessellate` at 1,200 × 800 and asserts the median frame CPU time is at most 4 ms. `benches/frame.rs` reports it. Run alone.
- Files: `crates/mutable-gui/tests/fixtures/frame-300.json`, `crates/mutable-gui/tests/perf_frame.rs`, `crates/mutable-gui/benches/frame.rs`, `crates/mutable-gui/Cargo.toml`
- Libraries: egui, criterion
- Commands: `cargo test -p mutable-gui --release --test perf_frame perf_ && cargo bench -p mutable-gui --bench frame --no-run`
- Tests: `crates/mutable-gui/tests/perf_frame.rs`
- Gate: G4.15 — `cargo test -p mutable-gui --release --test perf_frame perf_` exits 0
- Requirements: none
- Screens: none

### Step 4.16 — Editor open time

- Builds: `examples/reference-plugin/tests/perf_editor_open.rs` (`perf_editor_open_under_250ms`) measures, 11 times, from `MutableGui` construction with the embedded default to the end of the first `frame` and `tessellate` on a fresh `egui::Context` at 840 × 520, asserting the median is at most 250 ms. Run alone.
- Files: `examples/reference-plugin/tests/perf_editor_open.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui-reference --release --test perf_editor_open perf_`
- Tests: `examples/reference-plugin/tests/perf_editor_open.rs`
- Gate: G4.16 — `cargo test -p mutable-gui-reference --release --test perf_editor_open perf_` exits 0
- Requirements: none
- Screens: none

### Step 4.17 — Documents at Phase 4 truth

- Builds: `README.md` (perform-mode use: drag, Shift, right-click or long press, keyboard), `docs/ARCHITECTURE.md` (perform module, I-04 with its tests), `docs/TESTING.md` (gallery and screen tests), `CHANGELOG.md`.
- Files: `README.md`, `docs/ARCHITECTURE.md`, `docs/TESTING.md`, `CHANGELOG.md`
- Libraries: none
- Commands: `grep -q "I-04" docs/ARCHITECTURE.md && grep -q "long press" README.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/TESTING.md CHANGELOG.md`
- Tests: none
- Gate: G4.17 — `grep -q "I-04" docs/ARCHITECTURE.md && grep -q "long press" README.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/TESTING.md CHANGELOG.md` exits 0
- Requirements: none
- Screens: none

### Step 4.18 — Phase 4 check sheet

- Builds: `docs/qa/phase-04.md` lists, each with "Result: not run": (1) every control of the reference default works with the mouse; (2) Shift-drag is fine; (3) right-click and a long press on the trackpad open the control menu; Reset, Type value and Fine adjust work; (4) Tab, arrows and Enter work while the window has focus; (5) host modulation of Cutoff shows the band; (6) the pictures `.tickets/.work/ui-compare/S-01.png` and `S-03.png` match their mockups, and `examples/reference-plugin/tests/snapshots/S-12-elements*.png` match `design/ui/S-12-elements*.html` for the built-in rows; (7) with Drive at 0 dB the Oversample 2× switch is drawn faint and still switches (F-002); (8) Cutoff's control menu shows its description, and after Step 4.25 the S-03 comparison matches the updated mockup (F-003). It ends with "Signed off: no".
- Files: `docs/qa/phase-04.md`
- Libraries: none
- Commands: `grep -q "^Signed off: no" docs/qa/phase-04.md`
- Tests: none
- Gate: G4.18 — `grep -q "^Signed off: no" docs/qa/phase-04.md` exits 0
- Requirements: none
- Screens: none

### Step 4.19 — [OWNER] Phase 4 host and screen check

- Builds: the owner performs the items of `docs/qa/phase-04.md`, records each result and signs off.
- Files: `docs/qa/phase-04.md`
- Libraries: Bitwig Studio
- Commands: `python3 tools/devpipe/run.py ui compare S-01 && python3 tools/devpipe/run.py ui compare S-03`
- Tests: none
- Gate: G4.19 — `grep -q "^Signed off: yes" docs/qa/phase-04.md` exits 0
- Requirements: R-039
- Screens: S-01, S-03

### Step 4.20 — Relevance rule evaluation

- Builds: `editor::relevance` defines `ParamValues` (`normalized(&self, id) -> Option<f32>`, `step(&self, id) -> Option<u32>`, the step being `round(base × (values − 1))` for a stepped parameter and `None` otherwise) with an implementation for every `ParamSource`; `Irrelevant`, a `Vec<bool>` indexed by position in `ParamSource::params()`, with `insert(id)` (an id the plugin lacks is ignored), `contains(id)` and `clear()`, reused between evaluations; and `type RelevanceRule = dyn Fn(&dyn ParamValues, &mut Irrelevant) + Send + Sync`. `EditorState::with_relevance(Arc<RelevanceRule>)`. At the start of each perform-mode frame the editor compares every base value with the previous frame's (a reused `Vec<f32>`) and runs the rule when one differs, and on the first frame after `editor_opened`; `EditorState::irrelevant()` returns the set. The rule runs only on the editor thread.
- Files: `crates/mutable-gui/src/editor/relevance.rs`, `crates/mutable-gui/src/editor/mod.rs`, `crates/mutable-gui/tests/editor_relevance.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test editor_relevance`
- Tests: `crates/mutable-gui/tests/editor_relevance.rs` (a rule naming "crossTalk" unless "mode" is Collision: the set holds crossTalk on the frame after mode becomes Clock and not on the frame after it becomes Collision; a frame with no value change does not call the rule; an unknown id is ignored)
- Gate: G4.20 — `cargo test -p mutable-gui --test editor_relevance` exits 0
- Requirements: R-173
- Screens: none
- Feature: F-002

### Step 4.21 — Dimmed drawing

- Builds: `ElementView` gains `dimmed: bool`, true in perform mode for a knob, fader, switch, XY pad, macro or selector all of whose present bound parameters are in `irrelevant()` (page tabs and menu elements, which name no parameter value, displays and decorations are never dimmed; design mode dims nothing). `render::draw_element` draws a dimmed element through a clone of the painter with `multiply_opacity(0.45)`, then its focus outline with the full-opacity painter (D-50). `DrawnElement` gains `opacity: f32`. Input is unchanged: a dimmed control still drags, clicks, takes focus and opens its control menu.
- Files: `crates/mutable-gui/src/render/view.rs`, `crates/mutable-gui/src/render/mod.rs`, `crates/mutable-gui/src/render/drawn.rs`, `crates/mutable-gui/tests/render_dimmed.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test render_dimmed --test editor_perform`
- Tests: `crates/mutable-gui/tests/render_dimmed.rs` (R-173: the crossTalk knob records opacity 0.45 while mode is Clock and 1.0 on the frame after mode becomes Collision; dragging it while dimmed records begin, set, end; R-174: an XY pad with X irrelevant and Y relevant records 1.0 and with both irrelevant 0.45; a label beside the dimmed knob records 1.0; in design mode the knob records 1.0)
- Gate: G4.21 — `cargo test -p mutable-gui --test render_dimmed --test editor_perform` exits 0
- Requirements: R-173, R-174
- Screens: none
- Feature: F-002
- Pins: Step 1.16's `editor_perform.rs` reads other fields of `DrawnElement` and configures no rule; its assertions hold. The S-01, S-03 and S-12 pictures configure no rule and do not change.

### Step 4.22 — Relevance through the adapter and in the reference plugin

- Builds: the adapter builder gains `.relevance(rule: impl Fn(&dyn ParamValues, &mut Irrelevant) + Send + Sync + 'static) -> Self`, passed to `EditorState::with_relevance`. `RefFx` registers a rule naming `oversample` irrelevant while `drive` is at 0 dB (normalized 0). `tests/perf_frame.rs` runs its 300-element page with a rule naming 150 of its 300 fake parameters and keeps the 4 ms bound. Run alone.
- Files: `crates/mutable-gui-nice/src/builder.rs`, `examples/reference-plugin/src/lib.rs`, `crates/mutable-gui/tests/perf_frame.rs`, `examples/reference-plugin/tests/relevance.rs`
- Libraries: nice-plug
- Commands: `cargo test -p mutable-gui-reference --test relevance && cargo test -p mutable-gui --release --test perf_frame perf_`
- Tests: `examples/reference-plugin/tests/relevance.rs` (on the reference default, the Oversample 2× switch records opacity 0.45 with Drive at 0 dB and 1.0 with Drive at its default 8.8 dB), `crates/mutable-gui/tests/perf_frame.rs`
- Gate: G4.22 — `cargo test -p mutable-gui-reference --test relevance && cargo test -p mutable-gui --release --test perf_frame perf_` exits 0
- Requirements: R-173
- Screens: none
- Feature: F-002
- Pins: Step 4.15's `perf_frame.rs` gains the rule; its 4 ms median bound is unchanged. Step 4.12's S-01 pictures use Drive's default 8.8 dB, where Oversample is lit; they do not change.

### Step 4.23 — Description in the control menu

- Builds: `ParamSource` gains the default method `description(&self, id) -> Option<&str>` returning `None`, so existing implementations compile unchanged; the testkit's `FakeParamSource` gains `describe(id, text)`. `perform::control_menu` draws the description of the control's first present bound parameter under its header: Inter 12 px in `--tool-text-muted`, wrapped to the menu's inner width, newlines kept as line breaks, 4 px below the header; the menu still stays inside the window. The entries are unchanged.
- Files: `crates/mutable-gui/src/params.rs`, `crates/mutable-gui-testkit/src/fake_params.rs`, `crates/mutable-gui/src/perform/control_menu.rs`, `crates/mutable-gui/tests/perform_description.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test perform_description --test perform_control_menu --test fake_params`
- Tests: `crates/mutable-gui/tests/perform_description.rs` (R-175: with "cutoff" described as "Frequency where the filter starts to cut. Turn it down to darken the sound.", a right-click on a knob bound to cutoff shows that text under the header and exactly the entries Reset, Type value and Fine adjust; a knob bound to an undescribed parameter shows no description)
- Gate: G4.23 — `cargo test -p mutable-gui --test perform_description --test perform_control_menu --test fake_params` exits 0
- Requirements: R-175
- Screens: none
- Feature: F-003
- Pins: Step 4.9's `perform_control_menu.rs` and Step 1.4's `fake_params.rs` describe nothing; their assertions hold.

### Step 4.24 — Descriptions through the adapter and in the reference plugin

- Builds: the adapter builder gains `.describe(id: &str, text: &str) -> Result<Self, DescribeError>` (`DescribeError::Empty` for empty or whitespace-only text, `DescribeError::TooLong` above 1,024 bytes); `NiceParamSource` holds the descriptions and answers `description`. `RefFx` describes `cutoff` ("Frequency where the filter starts to cut. Turn it down to darken the sound."), `resonance` ("Boost at the cutoff frequency. High values make the filter ring."), `drive` ("Gain into the saturator. More drive adds harmonics and squashes peaks."), `threshold` ("Level above which the compressor starts to reduce gain.") and `ratio` ("How strongly the compressor reduces gain above the threshold."). The S-03 picture of the menu open on Cutoff is regenerated.
- Files: `crates/mutable-gui-nice/src/builder.rs`, `crates/mutable-gui-nice/src/params.rs`, `examples/reference-plugin/src/lib.rs`, `crates/mutable-gui-nice/tests/describe.rs`, `examples/reference-plugin/tests/snapshots/S-03-control-menu.png`
- Libraries: nice-plug, egui_kittest
- Commands: `cargo test -p mutable-gui-nice --test describe && UPDATE_SNAPSHOTS=1 cargo test -p mutable-gui-reference --test screen_s03 && cargo test -p mutable-gui-reference --test screen_s03`
- Tests: `crates/mutable-gui-nice/tests/describe.rs` (R-175: a 1,025-byte description is refused with `TooLong`, "   " with `Empty`; a described parameter's `description` returns its text through `NiceParamSource`)
- Gate: G4.24 — `cargo test -p mutable-gui-nice --test describe && cargo test -p mutable-gui-reference --test screen_s03` exits 0
- Requirements: R-175
- Screens: none
- Feature: F-003
- Pins: Step 4.13's `screen_s03.rs`: `S-03-control-menu.png` now shows Cutoff's description and is regenerated here; `S-03-control-menu--value.png` and `--error.png` show the value field with the menu closed and do not change; the test's assertions hold.

### Step 4.25 — [OWNER] S-03 mockup with the description

- Builds: the owner runs `/ui-design` for S-03 so that `design/ui/S-03-control-menu.html` shows Cutoff's description ("Frequency where the filter starts to cut. Turn it down to darken the sound.") under the menu header and `design/UI.md` S-03 "Shows" names the description, then runs the comparison and records the result in `docs/qa/phase-04.md` item (8).
- Files: `design/ui/S-03-control-menu.html`, `design/UI.md`
- Libraries: none
- Commands: `python3 tools/devpipe/run.py ui compare S-03`
- Tests: none
- Gate: G4.25 — `grep -q "Turn it down to darken the sound" design/ui/S-03-control-menu.html && python3 tools/devpipe/run.py ui compare S-03` exits 0
- Requirements: R-175
- Screens: S-03
- Feature: F-003

**Exit demo:** Following `README.md` and `docs/RUNBOOK.md`: in Bitwig, play every control of Reference FX's default with the mouse, Shift and the keyboard, open the control menu by right-click and by long press, type "1.5k" into Cutoff, reset the macro, and see the modulation band follow Bitwig's modulator on Cutoff.

## Phase 5 — Design mode: edit a page

**Goal:** In Bitwig the user switches to design mode, adds a page, places three knobs, binds them through the picker, moves, resizes and deletes elements, sees what is unbound, undoes and redoes every step, and returns to perform mode; the plugin's audio stays bit-identical with the editor closed, in perform mode and in design mode.

### Step 5.1 — Commands

- Builds: `edit::Command` with `AddElements { page, elements: Vec<Arc<Element>> }`, `RemoveElements { page, ids }`, `MoveElements { page, ids, dx: i32, dy: i32 }`, `SetFrame { page, id, frame }`, `ReplaceElement { page, element: Arc<Element> }`, `AddPage { page: Page, after: Option<PageId> }`, `RemovePage { id }`, `RenamePage { id, name }`, `MovePage { id, to: usize }`, `SetCanvas(Size)`, `SetGrid(Grid)`, `SetLayout { layout, assets }`, `SetTheme { theme, assets }`, `SetAll { layout, theme, assets }`. `edit::apply(&mut InstanceState, &Command) -> Result<(), Refusal>` changes the state and then runs `doc::validate` on the result; `Refusal` maps to the notice texts (`PageLimit`, `ElementLimit`, `NestingLimit`, `LastPage`, `Invalid(DocError)`, `Locked`). `EditorState::commit(cmd)` refuses everything with `Locked` while preserving (GD-1, I-16), else keeps a clone of the state, applies, and on success pushes the clone to the undo stack (Step 5.2), clears redo and publishes the new encoding (R-111); on refusal it raises the notice and leaves the state as it was. A removed page makes the previous page current, or the next when it was the first (R-064); menu items whose `open_page` names the removed page stay as they are and draw disabled (Step 4.5), since only a user's own edit changes an element (I-08); removed element ids leave the selection, the keyboard focus and the fine-lock set. Only `edit::apply` changes the instance state (architecture boundary).
- Files: `crates/mutable-gui/src/edit/mod.rs`, `crates/mutable-gui/src/edit/command.rs`, `crates/mutable-gui/src/edit/apply.rs`, `crates/mutable-gui/src/editor/mod.rs`, `crates/mutable-gui/tests/edit_apply.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test edit_apply`
- Tests: `crates/mutable-gui/tests/edit_apply.rs` (each command's effect; R-064: removing page 2 of 3 removes its elements and makes page 1 current; R-065: removing the only page leaves it and raises one notice; R-066: a 65th page and a 2,001st element are refused with one notice each; R-119: while preserving every command is refused and the state is unchanged)
- Gate: G5.1 — `cargo test -p mutable-gui --test edit_apply` exits 0
- Requirements: R-064, R-065, R-066, R-119
- Screens: none
- Guards: GD-1 applies: `Locked`, no change, no notice (the interface offers no editing then). GD-2 and GD-3: commands never touch parameters; design-mode commands are reachable only in design mode, while menu commands (theme choice, reset, imports, library apply) also run in perform mode. GD-4 applies to every command through `doc::validate` after applying: refused with its notice. GD-6: commands carry validated values only; outside bytes reach them through `doc` (Steps 6.6, 8.9).

### Step 5.2 — Undo and redo

- Builds: `edit::UndoStack` holds up to 200 previous states and a redo list (choice 8): `push(prev)` drops the oldest beyond 200 and clears redo; `undo(current) -> Option<InstanceState>` moves current onto redo; `redo(current)`; `clear()`; `depth()`. States share unchanged pages, elements and assets through `Arc` (choice 26). `EditorState::undo()` and `redo()` restore a state, keep the current page when it still exists, and publish. The stack lives in `EditorState` across editor close and reopen and is never encoded (R-095); a host state load clears it (`editor/load.rs`).
- Files: `crates/mutable-gui/src/edit/undo.rs`, `crates/mutable-gui/src/editor/mod.rs`, `crates/mutable-gui/src/editor/load.rs`, `crates/mutable-gui/tests/edit_undo.rs`
- Libraries: proptest
- Commands: `cargo test -p mutable-gui --test edit_undo`
- Tests: `crates/mutable-gui/tests/edit_undo.rs` (R-093: after 120 single moves, 100 undos restore the position after move 20; R-094: a proptest of 256 random sequences of up to 30 commands finds every undo equal to the prior document; R-095: move, close, reopen, undo restores; a host load clears the depth to 0)
- Gate: G5.2 — `cargo test -p mutable-gui --test edit_undo` exits 0
- Requirements: R-093, R-094, R-095
- Screens: none
- Pins: Step 2.15's `editor_host_load.rs` gains no assertion change; its loads now also clear the stack.

### Step 5.3 — Undo memory bound

- Builds: `mutable_gui_testkit::counting_alloc::CountingAlloc` wraps `std::alloc::System` and counts live bytes. `tests/undo_memory.rs` installs it as the global allocator, builds a layout of 2,000 elements over 10 pages with 4 MiB of assets, commits 100 single-element moves, and asserts live bytes stay at most 64 MiB (67,108,864).
- Files: `crates/mutable-gui-testkit/src/counting_alloc.rs`, `crates/mutable-gui-testkit/src/lib.rs`, `crates/mutable-gui/tests/undo_memory.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test undo_memory`
- Tests: `crates/mutable-gui/tests/undo_memory.rs`
- Gate: G5.3 — `cargo test -p mutable-gui --test undo_memory` exits 0
- Requirements: R-093
- Screens: none

### Step 5.4 — Design mode switch and reset to developer default

- Builds: the editor menu gains "Design mode" with the hint "⌘E" after the header and, at the bottom, "Reset to developer default". ⌘E (Ctrl+E on Linux and Windows: `egui::Modifiers::COMMAND`) and the entry toggle `EditorState::mode` between `Perform` and `Design` (R-067); `editor_opened` always sets `Perform` (R-013). In design mode `perform::frame` does not run and `design::frame` gets the input, so a press selects or moves and sends no gesture (R-068). With `design_mode_enabled == false` the entry is absent and the shortcut does nothing (R-009, GD-2); while preserving it is disabled and the shortcut does nothing (GD-1). Reset commits `SetAll` with the developer default (R-096).
- Files: `crates/mutable-gui/src/design/mod.rs`, `crates/mutable-gui/src/render/chrome/editor_menu.rs`, `crates/mutable-gui/src/editor/mod.rs`, `crates/mutable-gui/tests/design_mode.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test design_mode`
- Tests: `crates/mutable-gui/tests/design_mode.rs` (R-067: the shortcut twice returns to perform; R-013: closing in design mode and reopening shows perform; R-068: a drag on a knob in design mode moves it and the fake records nothing; R-009: with the option off the menu holds no "Design mode" and ⌘E leaves perform; R-096: reset makes the layout equal the developer default and one undo restores the prior one)
- Gate: G5.4 — `cargo test -p mutable-gui --test design_mode` exits 0
- Requirements: R-009, R-013, R-067, R-068, R-096
- Screens: none
- Guards: GD-1 applies to the switch (disabled entry, ignored shortcut) and to reset (Step 8.10 opens the discard confirmation first). GD-2 applies to the switch (absent, ignored) and not to reset, which stays offered (R-150). GD-3 applies: design mode sends nothing.

### Step 5.5 — Selection, marquee and the design overlay

- Builds: `design::select`: a click on an element selects it alone; Shift-click toggles it; a click on empty canvas clears; a drag from empty canvas draws a marquee (1 px tool accent outline, accent at 10 % fill) and selects every top-level element entirely inside (R-070, R-071; choice 3). `design::overlay` draws, in screen pixels over the canvas: grid lines every step in `--tool-grid`, the selection outline (1.5 px tool accent) with eight 7 px handles when one element is selected, the marquee, and the menu button's corner area hatched in `--tool-reserved`.
- Files: `crates/mutable-gui/src/design/select.rs`, `crates/mutable-gui/src/design/overlay.rs`, `crates/mutable-gui/src/design/mod.rs`, `crates/mutable-gui/tests/design_select.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test design_select`
- Tests: `crates/mutable-gui/tests/design_select.rs` (R-070: click A, Shift-click B, Shift-click A gives {B}, empty click gives {}; R-071: a marquee around two of three elements selects those two)
- Gate: G5.5 — `cargo test -p mutable-gui --test design_select` exits 0
- Requirements: R-070, R-071
- Screens: none

### Step 5.6 — Move, snap and nudge

- Builds: `design::move_` drags the selection with a live preview and commits one `MoveElements` on release (choice 27); `design::snap::snap_delta(d, step, snap)` rounds each axis to the nearest multiple of `step`, halves away from zero, when snap is on, else to whole units (R-072, R-075). Snap guides in `--tool-guide` show while a moved element's left, centre, right, top, middle or bottom equals that of another element on the page. Arrow keys nudge by 1 unit, or by the grid step with Shift, one command per press (R-073). The grid step (2–64) and snap toggle are `SetGrid` commands.
- Files: `crates/mutable-gui/src/design/move_.rs`, `crates/mutable-gui/src/design/snap.rs`, `crates/mutable-gui/tests/design_move.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test design_move`
- Tests: `crates/mutable-gui/tests/design_move.rs` (R-072: with an 8-unit grid a drag of (13, 3) moves by (16, 0); R-075: with snap off it moves by (13, 3); R-073: Right moves by (1, 0), Shift+Down by (0, 8); R-111: after releasing a drag, `cell.load()` on the next frame holds the new position)
- Gate: G5.6 — `cargo test -p mutable-gui --test design_move` exits 0
- Requirements: R-072, R-073, R-075, R-111
- Screens: none

### Step 5.7 — Resize handles

- Builds: `design::handles` lets the eight handles of a single selected element resize it, snapping the moved edges as Step 5.6 when snap is on, never below 8 × 8 units, committing one `SetFrame` on release (R-074). Group resizing arrives in Step 6.4.
- Files: `crates/mutable-gui/src/design/handles.rs`, `crates/mutable-gui/tests/design_handles.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test design_handles`
- Tests: `crates/mutable-gui/tests/design_handles.rs` (R-074: the bottom-right handle of a 64 × 64 knob dragged by (−100, −100) leaves 8 × 8)
- Gate: G5.7 — `cargo test -p mutable-gui --test design_handles` exits 0
- Requirements: R-074
- Screens: none

### Step 5.8 — Design shortcuts and delete

- Builds: `design::keys` reads, in design mode and while no text field has focus: Delete and Backspace remove the selection as one `RemoveElements` (R-085); ⌘Z undoes, ⇧⌘Z redoes; arrows nudge (Step 5.6); holding H hides every tool (toolbar, palette, inspector, popovers, selection marks) until released (S-04 `--peek`); ⌘E switches mode.
- Files: `crates/mutable-gui/src/design/keys.rs`, `crates/mutable-gui/src/design/mod.rs`, `crates/mutable-gui/tests/design_keys.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test design_keys`
- Tests: `crates/mutable-gui/tests/design_keys.rs` (R-085: deleting a selection of two removes both; ⌘Z restores them; H held hides the toolbar's area from `drawn` tool records)
- Gate: G5.8 — `cargo test -p mutable-gui --test design_keys` exits 0
- Requirements: R-085, R-093
- Screens: none

### Step 5.9 — Floating toolbar

- Builds: `design::toolbar` draws a 36 px floating bar (tool style, radius 10, shadow) centred 8 px from the window top: Undo, Redo (disabled when their stack is empty), Arrange, Group, the grid step field (2–64; another value keeps the previous) with a snap toggle, the page button (current page name, opens S-06), the unbound count (opens S-07; hidden at 0), Hide tools, Theme, Library, Done (returns to perform). Arrange and Group are drawn disabled until Step 6.7, Library until Step 8.14, Theme until Step 9.6 (half opacity, D-36). Below 520 × 420 logical px (choice 17) the bar shows Undo, Redo, the page button, Done and a "⋯" button holding the rest.
- Files: `crates/mutable-gui/src/design/toolbar.rs`, `crates/mutable-gui/src/design/mod.rs`, `crates/mutable-gui/tests/design_toolbar.rs`
- Libraries: egui, egui_material_icons
- Commands: `cargo test -p mutable-gui --test design_toolbar`
- Tests: `crates/mutable-gui/tests/design_toolbar.rs` (Undo and Redo act; Done returns to perform; the grid field refuses 1 and 65 and keeps 8; the compact bar appears at 400 × 300)
- Gate: G5.9 — `cargo test -p mutable-gui --test design_toolbar` exits 0
- Requirements: R-075, R-093
- Screens: none

### Step 5.10 — Palette

- Builds: `design::palette` draws a 44 px floating rail at the left (8 px inset, below the toolbar) with icons of "Fixed names" in three sections (Controls, Displays, Decorations) and tooltips with the kind name. A click adds one element of the "Palette defaults" with its frame centred on the canvas, its x and y rounded to the grid when snap is on, selected alone, as one `AddElements` (R-069). Below 520 × 420 logical px the rail collapses behind a "+" button. Step 7.8 appends the custom-kind section.
- Files: `crates/mutable-gui/src/design/palette.rs`, `crates/mutable-gui/tests/design_palette.rs`
- Libraries: egui, egui_material_icons
- Commands: `cargo test -p mutable-gui --test design_palette`
- Tests: `crates/mutable-gui/tests/design_palette.rs` (R-069: adding a knob to an empty page gives one unbound knob centred and selected; R-066: at 2,000 elements the add is refused with one notice)
- Gate: G5.10 — `cargo test -p mutable-gui --test design_palette` exits 0
- Requirements: R-066, R-069
- Screens: none
- Guards: GD-1 and GD-2 do not apply (the palette exists only in design mode, which they make unreachable). GD-4 applies: the 2,001st element is refused with "Not added. A layout holds at most 2,000 elements."

### Step 5.11 — Inspector: frame, binding and caption

- Builds: `design::inspector` draws a 264 px card beside the selection (right of it when it fits, else left; a bottom sheet below 520 × 420), headed by the kind name, with collapsing sections in the S-04 order: Binding and Look open, Frame, Shape and Caption folded. Binding shows the parameter's group path › name and id; Range as two fields in the plugin's units (`format` of min and max; typed text goes through `parse`), and Dir. (Normal, Reversed). Frame has x, y, w, h fields. Caption is a text field (0–64 characters) with a "Use parameter name" button that removes it. Each edit is one `ReplaceElement` or `SetFrame`, drawn on the next frame (R-087); several selected show "{n} selected" only; a group shows Frame only.
- Files: `crates/mutable-gui/src/design/inspector/mod.rs`, `crates/mutable-gui/src/design/inspector/binding.rs`, `crates/mutable-gui/src/design/mod.rs`, `crates/mutable-gui/tests/design_inspector.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test design_inspector`
- Tests: `crates/mutable-gui/tests/design_inspector.rs` (R-087: width 96 draws 96 units wide on the next frame; a range typed as "120 Hz" sets `min` to the parser's value; Reversed sets `reversed`; one undo per edit)
- Gate: G5.11 — `cargo test -p mutable-gui --test design_inspector` exits 0
- Requirements: R-087
- Screens: none

### Step 5.12 — Inspector: look, shape and kind settings

- Builds: `inspector::look` lists the element's colour slots (table of "Fixed names") as role dropdowns with swatches of the active theme, and the knob style override (Theme, Arc, Pointer, Filled). Shape has radius, border, track and handle fields, each "theme" until set. `inspector::settings` edits the kind's fields: fader orientation, selector presentation, page-tab orientation, display tap (opens the tap picker, Step 5.16), `window_ms`, `fft_size`, `floor_db`, `range_db`, label text, typeface, size, align and tracking, panel surface and title, image asset (a dropdown of the instance's PNG assets and None; Step 9.7 adds "Add image…"), with the ranges of Step 2.1. Each edit is one `ReplaceElement`.
- Files: `crates/mutable-gui/src/design/inspector/look.rs`, `crates/mutable-gui/src/design/inspector/settings.rs`, `crates/mutable-gui/tests/design_inspector_look.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test design_inspector_look`
- Tests: `crates/mutable-gui/tests/design_inspector_look.rs` (setting `arc` to accent-3 draws that role; a knob style override draws pointer; `window_ms` 600 is refused and stays 50)
- Gate: G5.12 — `cargo test -p mutable-gui --test design_inspector_look` exits 0
- Requirements: R-087, R-102
- Screens: none

### Step 5.13 — Macro targets and menu items in the inspector

- Builds: `inspector::macro_targets` lists a macro's targets, each with a binding field, range and direction, an "Add target" button (disabled at 16) and a remove button (disabled at 1) (R-091). `inspector::menu_items` lists a menu element's items with text, action (Open page: a page dropdown; Set: a parameter field filtered to stepped parameters of 2–32 values and a step dropdown of its labels), add, remove, move up and down. Each change is one `ReplaceElement`.
- Files: `crates/mutable-gui/src/design/inspector/macro_targets.rs`, `crates/mutable-gui/src/design/inspector/menu_items.rs`, `crates/mutable-gui/tests/design_inspector_lists.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test design_inspector_lists`
- Tests: `crates/mutable-gui/tests/design_inspector_lists.rs` (R-091: adding a 17th target is refused and 16 remain; an item set to "Wave: Saw" stores step 1)
- Gate: G5.13 — `cargo test -p mutable-gui --test design_inspector_lists` exits 0
- Requirements: R-091
- Screens: none
- Guards: GD-4 applies through validation (targets 1–16): the 17th is refused with "is not valid: macro targets … at …" and nothing changes.

### Step 5.14 — Parameter picker

- Builds: `design::picker::search(params, query, accepts) -> PickerResult` returns matches whose name, id or group path joined with " › " contains the query ignoring case (R-088), without hidden parameters (R-089), limited to what the slot accepts (R-090: two-state for a switch; 2–32 values for a selector and a menu `set`; any parameter for knob, fader, XY axis and macro target), grouped by group path in declaration order, with the count of matches left out for incompatibility. `design::picker` draws the S-05 popover beside the binding field: search field with "{n} of {total}", group headers, rows with the name (matches in tool accent), id (Hack, muted) and kind ("Float", "Int", "Bool", "Enum · 4"), a check on the current binding, and a footer naming what the slot accepts; "No parameter matches" with "({n} hidden: this control can't use them)" when empty; ↑↓ move, ↩ or click binds as one `ReplaceElement` (a null slot gets min 0, max 1, normal; a bound one keeps its range) and closes; Escape closes.
- Files: `crates/mutable-gui/src/design/picker.rs`, `crates/mutable-gui/tests/design_picker.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test design_picker`
- Tests: `crates/mutable-gui/tests/design_picker.rs` (R-088: "CUT" lists "Filter Cutoff" and "LFO Cut Depth", not "Gain"; R-089: a hidden match is absent; R-090: a switch's picker lists a boolean and not a float; binding through ↩ is undone by one undo)
- Gate: G5.14 — `cargo test -p mutable-gui --test design_picker` exits 0
- Requirements: R-088, R-089, R-090
- Screens: none

### Step 5.15 — Picker search time

- Builds: `tests/perf_picker.rs` (`perf_picker_2000_params_under_16ms`) builds 2,000 fake parameters in 40 groups and runs `design::picker::search` for each prefix of "cutoff lfo" 100 times, asserting the median per keystroke is at most 16 ms. Run alone.
- Files: `crates/mutable-gui/tests/perf_picker.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --release --test perf_picker perf_`
- Tests: `crates/mutable-gui/tests/perf_picker.rs`
- Gate: G5.15 — `cargo test -p mutable-gui --release --test perf_picker perf_` exits 0
- Requirements: none
- Screens: none

### Step 5.16 — Tap picker

- Builds: `design::tap_picker` lists the declared taps of the kind the display reads (audio for oscilloscope, spectrum and level meter; scalar for gain reduction) with their kind and channels, the current tap checked, and a footer saying why others are absent ("Scalar taps are not listed: an oscilloscope reads audio."); a click binds as one `ReplaceElement` (R-056). Step 7.6 adds custom tap slots.
- Files: `crates/mutable-gui/src/design/tap_picker.rs`, `crates/mutable-gui/tests/design_tap_picker.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test design_tap_picker`
- Tests: `crates/mutable-gui/tests/design_tap_picker.rs` (R-056: with "out" and "gr", a level meter's picker lists only "out")
- Gate: G5.16 — `cargo test -p mutable-gui --test design_tap_picker` exits 0
- Requirements: R-056
- Screens: none

### Step 5.17 — Pages and canvas popover

- Builds: `design::pages` draws S-06 below the page button: header "Pages" with "{n} of 64"; one row per page with a drag handle, name, element count, and on hover rename and delete icons; double-click or rename edits the name inline (1–64 characters; Escape cancels); a click makes the page current; dragging a row commits `MovePage` (R-063); delete commits `RemovePage` (R-064; the only page raises the R-065 notice); "Add page" commits `AddPage` after the current page named "Page {n}" with the lowest unused n, which becomes current (R-062), and is disabled at 64 (R-066); canvas width and height fields (200–4,000; another value keeps the previous, R-057) commit `SetCanvas`; grid step (2–64) and snap commit `SetGrid` (R-075).
- Files: `crates/mutable-gui/src/design/pages.rs`, `crates/mutable-gui/tests/design_pages.rs`
- Libraries: egui, egui_material_icons
- Commands: `cargo test -p mutable-gui --test design_pages`
- Tests: `crates/mutable-gui/tests/design_pages.rs` (R-062: with "Page 1", adding shows "Page 2" second; R-063: renaming "Page 2" to "FX" and moving it first gives ["FX", "Page 1"]; R-057: 1,200 × 400 applies to every page and 150 keeps the previous value; R-066: Add page is disabled at 64)
- Gate: G5.17 — `cargo test -p mutable-gui --test design_pages` exits 0
- Requirements: R-057, R-062, R-063, R-064, R-065, R-066, R-075
- Screens: none
- Guards: GD-4 applies to add page (disabled at 64; a command beyond is refused with "Page not added. A layout holds at most 64 pages.") and to delete (the last page: "Page not deleted. A layout needs at least one page."). GD-1 and GD-2 make the popover unreachable.

### Step 5.18 — Unbound list

- Builds: `design::unbound::collect(layout, params, taps) -> Vec<UnboundRow>` lists, per page in page order, every control with a null or absent binding and every display with a null or undeclared tap, with its missing id or tap name or "Not bound". `design::unbound` draws S-07 below the toolbar's count: a one-line explanation, rows grouped by page; a row makes its page current and selects the element; "Rebind…" opens the picker for it (R-092). The toolbar count is the row count; at zero it is hidden and the list is not offered. Step 7.10 adds unknown elements.
- Files: `crates/mutable-gui/src/design/unbound.rs`, `crates/mutable-gui/tests/design_unbound.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test design_unbound`
- Tests: `crates/mutable-gui/tests/design_unbound.rs` (R-092: an unbound knob on page 3 is listed, and choosing it makes page 3 current with the knob selected)
- Gate: G5.18 — `cargo test -p mutable-gui --test design_unbound` exits 0
- Requirements: R-092
- Screens: none

### Step 5.19 — S-04 workspace screen

- Builds: `examples/reference-plugin/tests/screen_s04.rs` opens the reference default in design mode at 840 × 520 with the grid on, the Env Amt knob rebound to the absent `env_amount`, Cutoff selected with its inspector, and snapshots `S-04-workspace`; with H held, `S-04-workspace--peek`; the 400 × 300 "Live" layout of `design/ui/kit.js` `SMALL`, built in the test, with Cutoff selected, `S-04-workspace--small`. Arrange, Group, Theme and Library are drawn disabled until their steps; Steps 6.7, 8.14 and 9.6 regenerate these pictures. `design/UI.md` S-04 gets `Built: examples/reference-plugin/tests/snapshots/S-04-workspace.png`.
- Files: `examples/reference-plugin/tests/screen_s04.rs`, `examples/reference-plugin/tests/snapshots/S-04-workspace.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace--peek.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace--small.png`, `design/UI.md`
- Libraries: egui_kittest
- Commands: `cargo test -p mutable-gui-reference --test screen_s04 && python3 tools/devpipe/run.py ui compare S-04`
- Tests: `examples/reference-plugin/tests/screen_s04.rs`
- Gate: G5.19 — `cargo test -p mutable-gui-reference --test screen_s04 && python3 tools/devpipe/run.py ui compare S-04` exits 0
- Requirements: R-087
- Screens: S-04

### Step 5.20 — S-05 picker screen

- Builds: `examples/reference-plugin/tests/screen_s05.rs` opens the parameter picker on Cutoff's binding in design mode and types "cut" for `S-05-picker`; opens the tap picker of the scope for `S-05-picker--tap`. `design/UI.md` S-05 gets `Built: examples/reference-plugin/tests/snapshots/S-05-picker.png`.
- Files: `examples/reference-plugin/tests/screen_s05.rs`, `examples/reference-plugin/tests/snapshots/S-05-picker.png`, `examples/reference-plugin/tests/snapshots/S-05-picker--tap.png`, `design/UI.md`
- Libraries: egui_kittest
- Commands: `cargo test -p mutable-gui-reference --test screen_s05 && python3 tools/devpipe/run.py ui compare S-05`
- Tests: `examples/reference-plugin/tests/screen_s05.rs`
- Gate: G5.20 — `cargo test -p mutable-gui-reference --test screen_s05 && python3 tools/devpipe/run.py ui compare S-05` exits 0
- Requirements: R-088
- Screens: S-05

### Step 5.21 — S-06 pages screen

- Builds: `examples/reference-plugin/tests/screen_s06.rs` opens the pages popover on the reference default with "Dynamics" being renamed inline, and snapshots `S-06-pages`. `design/UI.md` S-06 gets `Built: examples/reference-plugin/tests/snapshots/S-06-pages.png`.
- Files: `examples/reference-plugin/tests/screen_s06.rs`, `examples/reference-plugin/tests/snapshots/S-06-pages.png`, `design/UI.md`
- Libraries: egui_kittest
- Commands: `cargo test -p mutable-gui-reference --test screen_s06 && python3 tools/devpipe/run.py ui compare S-06`
- Tests: `examples/reference-plugin/tests/screen_s06.rs`
- Gate: G5.21 — `cargo test -p mutable-gui-reference --test screen_s06 && python3 tools/devpipe/run.py ui compare S-06` exits 0
- Requirements: R-063
- Screens: S-06

### Step 5.22 — S-07 unbound screen

- Builds: `examples/reference-plugin/tests/screen_s07.rs` rebinds Env Amt to `env_amount` and the "Mod" page's LFO 2 Rate knob to `lfo3_rate` (both absent), opens the unbound list, and snapshots `S-07-unbound`. `design/UI.md` S-07 gets `Built: examples/reference-plugin/tests/snapshots/S-07-unbound.png`.
- Files: `examples/reference-plugin/tests/screen_s07.rs`, `examples/reference-plugin/tests/snapshots/S-07-unbound.png`, `design/UI.md`
- Libraries: egui_kittest
- Commands: `cargo test -p mutable-gui-reference --test screen_s07 && python3 tools/devpipe/run.py ui compare S-07`
- Tests: `examples/reference-plugin/tests/screen_s07.rs`
- Gate: G5.22 — `cargo test -p mutable-gui-reference --test screen_s07 && python3 tools/devpipe/run.py ui compare S-07` exits 0
- Requirements: R-092
- Screens: S-07

### Step 5.23 — Audio bit-identical in every editor state

- Builds: `examples/reference-plugin/tests/render_identical.rs` renders 10 s of seeded stereo noise at 48 kHz in 512-frame blocks through `Dsp::process` and both tap pushes three times: with no editor; with an `EditorState` in perform mode stepping one harness frame every four blocks on the "Main" page (scope reading); and in design mode adding a knob, binding it to Cutoff, moving and deleting it during the render (R-097's automated half). The three outputs are equal bit for bit (P1).
- Files: `examples/reference-plugin/tests/render_identical.rs`
- Libraries: egui_kittest
- Commands: `cargo test -p mutable-gui-reference --test render_identical`
- Tests: `examples/reference-plugin/tests/render_identical.rs`
- Gate: G5.23 — `cargo test -p mutable-gui-reference --test render_identical` exits 0
- Requirements: R-097
- Screens: none

### Step 5.24 — Documents at Phase 5 truth

- Builds: `README.md` (design mode: switching, palette, picker, pages, undo, shortcuts), `docs/ARCHITECTURE.md` (design and edit modules, I-08 and I-15 with tests, the undo structure), `docs/TESTING.md` (undo property test, memory test, bit-identical render), `CHANGELOG.md`.
- Files: `README.md`, `docs/ARCHITECTURE.md`, `docs/TESTING.md`, `CHANGELOG.md`
- Libraries: none
- Commands: `grep -q "⌘E" README.md && grep -q "render_identical" docs/TESTING.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/TESTING.md CHANGELOG.md`
- Tests: none
- Gate: G5.24 — `grep -q "⌘E" README.md && grep -q "render_identical" docs/TESTING.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/TESTING.md CHANGELOG.md` exits 0
- Requirements: none
- Screens: none

### Step 5.25 — Phase 5 check sheet

- Builds: `docs/qa/phase-05.md` lists, each with "Result: not run": (1) Flow 2 of `design/UI.md` in Bitwig: menu button, Design mode, page button, Add page, three knobs from the palette, each bound through the picker, Done; (2) during playback, adding, binding and deleting a knob causes no dropout and no plugin reload (R-097); (3) every step of (1) undoes and redoes; (4) closing the editor in design mode and reopening shows perform mode on the same page; (5) the pictures `.tickets/.work/ui-compare/S-04.png`, `S-05.png`, `S-06.png` and `S-07.png` match their mockups except the disabled Arrange, Group, Theme and Library buttons. It ends with "Signed off: no".
- Files: `docs/qa/phase-05.md`
- Libraries: none
- Commands: `grep -q "^Signed off: no" docs/qa/phase-05.md`
- Tests: none
- Gate: G5.25 — `grep -q "^Signed off: no" docs/qa/phase-05.md` exits 0
- Requirements: none
- Screens: none

### Step 5.26 — [OWNER] Phase 5 host and screen check

- Builds: the owner performs the items of `docs/qa/phase-05.md`, records each result and signs off.
- Files: `docs/qa/phase-05.md`
- Libraries: Bitwig Studio
- Commands: `python3 tools/devpipe/run.py ui compare S-04 && python3 tools/devpipe/run.py ui compare S-05 && python3 tools/devpipe/run.py ui compare S-06 && python3 tools/devpipe/run.py ui compare S-07`
- Tests: none
- Gate: G5.26 — `grep -q "^Signed off: yes" docs/qa/phase-05.md` exits 0
- Requirements: R-097
- Screens: S-04, S-05, S-06, S-07

**Exit demo:** Following `README.md` and `docs/RUNBOOK.md`: in Bitwig with audio playing, open Reference FX, switch to design mode, add a page, place three knobs and bind them to Cutoff, Drive and Mix through the picker, move, resize and delete one, undo and redo, open the unbound list, press Done, and play the new page; the audio never drops.

## Phase 6 — Arrange and clipboard

**Goal:** The user aligns, distributes, groups, orders, duplicates, copies and pastes elements, including between two Reference FX instances in Bitwig, with every operation undoable and every limit enforced.

### Step 6.1 — Align and distribute

- Builds: `edit::Command::SetFrames { page, frames: Vec<(ElementId, Frame)> }` (one undoable change for many frames). `design::arrange::align(frames, edge) -> Vec<Frame>` aligns two or more frames' left edges, horizontal centres, right edges, top edges, vertical centres or bottom edges to the selection's bounding box (R-076); `distribute(frames, axis)` keeps the outermost two and makes the gaps between neighbours equal (sorted by position, rounded to whole units) for three or more (R-077).
- Files: `crates/mutable-gui/src/design/arrange.rs`, `crates/mutable-gui/src/edit/command.rs`, `crates/mutable-gui/src/edit/apply.rs`, `crates/mutable-gui/tests/design_arrange.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test design_arrange`
- Tests: `crates/mutable-gui/tests/design_arrange.rs` (R-076: three at x = 10, 40, 90 aligned left are at 10; R-077: widths 10 at x = 0, 15, 90 distributed horizontally end at 0, 45, 90 ± 1; one undo restores all)
- Gate: G6.1 — `cargo test -p mutable-gui --test design_arrange` exits 0
- Requirements: R-076, R-077
- Screens: none

### Step 6.2 — Drawing order

- Builds: `edit::Command::Reorder { page, order: Vec<ElementId> }`; `design::zorder` computes the new back-to-front order for "to front", "forward one", "backward one" and "to back" of the selection, keeping the selection's relative order (R-086). Shortcuts ⌘] forward, ⌘[ backward, ⇧⌘] to front, ⇧⌘[ to back.
- Files: `crates/mutable-gui/src/design/zorder.rs`, `crates/mutable-gui/src/edit/command.rs`, `crates/mutable-gui/src/design/keys.rs`, `crates/mutable-gui/tests/design_zorder.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test design_zorder`
- Tests: `crates/mutable-gui/tests/design_zorder.rs` (R-086: on [A, B, C] "to front" on A gives [B, C, A]; forward and backward move one place)
- Gate: G6.2 — `cargo test -p mutable-gui --test design_zorder` exits 0
- Requirements: R-086
- Screens: none

### Step 6.3 — Group and ungroup

- Builds: `edit::Command::Group { page, ids, group_id }` replaces two or more top-level elements by one group holding them in their drawing order, with the bounding box as its frame (choice 3), at the position of the frontmost; `Ungroup { page, id }` puts the members back at the group's position with their current frames (R-079). A press on a member selects its top-level group, and moving the group moves every member by the same offset (R-078). Grouping that would nest deeper than 16 is refused with the nesting notice (R-080); the added group element counts toward 2,000. Shortcuts ⌘G and ⇧⌘G.
- Files: `crates/mutable-gui/src/design/group.rs`, `crates/mutable-gui/src/edit/command.rs`, `crates/mutable-gui/src/edit/apply.rs`, `crates/mutable-gui/tests/design_group.rs`
- Libraries: uuid
- Commands: `cargo test -p mutable-gui --test design_group`
- Tests: `crates/mutable-gui/tests/design_group.rs` (R-078: after grouping A and B, clicking A selects the group and a drag moves both by the same offset; R-079: after ungroup, clicking A selects A alone at its position; R-080: grouping a group of depth 16 raises a notice and changes nothing)
- Gate: G6.3 — `cargo test -p mutable-gui --test design_group` exits 0
- Requirements: R-078, R-079, R-080
- Screens: none
- Guards: GD-4 applies: nesting beyond 16 ("Not grouped. Groups nest at most 16 deep.") and the element count including the new group ("Not added. A layout holds at most 2,000 elements.").

### Step 6.4 — Group resize

- Builds: resizing a selected group through its handles scales each member's position relative to the group frame and its size by the same factors, rounded to whole units, at least 1 × 1, as one `SetFrames` (R-081).
- Files: `crates/mutable-gui/src/design/handles.rs`, `crates/mutable-gui/tests/design_group_resize.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test design_group_resize`
- Tests: `crates/mutable-gui/tests/design_group_resize.rs` (R-081: doubling the width of a group whose members sit at relative x 0 and 50 places them at 0 and 100 with doubled widths)
- Gate: G6.4 — `cargo test -p mutable-gui --test design_group_resize` exits 0
- Requirements: R-081
- Screens: none
- Pins: Step 5.7's `design_handles.rs` covers single elements; its assertions hold.

### Step 6.5 — Duplicate

- Builds: `design::duplicate` copies the selection with fresh version-4 ids at every depth (I-15), the same bindings, frames offset by one grid step right and down, adds them as one `AddElements` and selects the copies (R-082); ⌘D.
- Files: `crates/mutable-gui/src/design/duplicate.rs`, `crates/mutable-gui/tests/design_duplicate.rs`
- Libraries: uuid
- Commands: `cargo test -p mutable-gui --test design_duplicate`
- Tests: `crates/mutable-gui/tests/design_duplicate.rs` (R-082: duplicating a knob bound to "cutoff" adds a second knob bound to "cutoff" with a different id, offset by (8, 8); at 2,000 elements it is refused with a notice)
- Gate: G6.5 — `cargo test -p mutable-gui --test design_duplicate` exits 0
- Requirements: R-082
- Screens: none
- Guards: GD-4 applies: the element count, with the notice of Step 5.10.

### Step 6.6 — Copy and paste through the system clipboard

- Builds: ⌘C (and the Arrange entry Copy) encodes the selection with the assets it refers to as a `mutable-gui/elements` document and calls `ctx.copy_text`. An `egui::Event::Paste(text)` in design mode with no text field focused goes through `doc::decode_elements` (GD-6); valid elements get fresh ids at every depth and are added to the current page at their copied frames as one `AddElements`, merging incoming assets by id (choice 4); invalid text raises "Paste refused." with the `DocError` text and changes nothing (R-084, R-143); limits refuse with their notice. The Arrange popover's Paste entry follows choice 28.
- Files: `crates/mutable-gui/src/design/clipboard.rs`, `crates/mutable-gui/src/design/keys.rs`, `crates/mutable-gui-testkit/src/clipboard.rs`, `crates/mutable-gui/tests/design_clipboard.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test design_clipboard`
- Tests: `crates/mutable-gui/tests/design_clipboard.rs` (R-083: copying a knob in one harness, reading the `CopyText` output command and sending it as `Event::Paste` to a second harness adds an equal knob with a new id to its current page; R-084: pasting "hello" leaves the layout unchanged and raises one notice; R-143: the undo depth is unchanged after a refused paste)
- Gate: G6.6 — `cargo test -p mutable-gui --test design_clipboard` exits 0
- Requirements: R-083, R-084, R-143
- Screens: none
- Guards: GD-6 applies: clipboard text is outside bytes and is validated before any part is added. GD-4 applies to the element count and to the 4 MiB asset cap of the instance after merging ("Not added. Assets are limited to 4 MiB per instance; …"). GD-1 and GD-2: paste exists only in design mode.

### Step 6.7 — Arrange popover

- Builds: `design::arrange_menu` opens below the toolbar's Arrange button: Align (six icons, disabled below two selected), Distribute (two icons, disabled below three), Order (four entries with their shortcuts), Group / Ungroup (⌘G, ⇧⌘G), Duplicate (⌘D), Copy (⌘C), Paste (choice 28), Delete (⌫). The toolbar's Arrange and Group buttons are enabled (Group groups or ungroups the selection).
- Files: `crates/mutable-gui/src/design/arrange_menu.rs`, `crates/mutable-gui/src/design/toolbar.rs`, `examples/reference-plugin/tests/snapshots/S-04-workspace.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace--peek.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace--small.png`, `examples/reference-plugin/tests/snapshots/S-05-picker.png`, `examples/reference-plugin/tests/snapshots/S-05-picker--tap.png`, `examples/reference-plugin/tests/snapshots/S-06-pages.png`, `examples/reference-plugin/tests/snapshots/S-07-unbound.png`, `crates/mutable-gui/tests/design_arrange_menu.rs`
- Libraries: egui, egui_material_icons
- Commands: `cargo test -p mutable-gui --test design_arrange_menu && UPDATE_SNAPSHOTS=1 cargo test -p mutable-gui-reference --test screen_s04 --test screen_s05 --test screen_s06 --test screen_s07 && cargo test -p mutable-gui-reference --test screen_s04 --test screen_s05 --test screen_s06 --test screen_s07`
- Tests: `crates/mutable-gui/tests/design_arrange_menu.rs` (each entry performs its operation; disabled states follow the selection count)
- Gate: G6.7 — `cargo test -p mutable-gui --test design_arrange_menu && cargo test -p mutable-gui-reference --test screen_s04 --test screen_s05 --test screen_s06 --test screen_s07` exits 0
- Requirements: R-076, R-077, R-078, R-082, R-085, R-086
- Screens: S-04
- Pins: the S-04, S-05, S-06 and S-07 pictures of Steps 5.19–5.22 show the toolbar, whose Arrange and Group buttons are now enabled; they are regenerated in this step and their tests then pass unchanged.

### Step 6.8 — S-04 arrange state

- Builds: `screen_s04.rs` gains a test selecting the Filter panel's three knobs with Arrange open, snapshot `S-04-workspace--arrange`.
- Files: `examples/reference-plugin/tests/screen_s04.rs`, `examples/reference-plugin/tests/snapshots/S-04-workspace--arrange.png`
- Libraries: egui_kittest
- Commands: `cargo test -p mutable-gui-reference --test screen_s04`
- Tests: `examples/reference-plugin/tests/screen_s04.rs`
- Gate: G6.8 — `cargo test -p mutable-gui-reference --test screen_s04` exits 0
- Requirements: R-076
- Screens: S-04

### Step 6.9 — Documents at Phase 6 truth

- Builds: `README.md` (arrange tools, shortcuts, the ⌘V-only paste of choice 28), `docs/ARCHITECTURE.md` ("Differences from the design": paste through ⌘V only), `CHANGELOG.md`.
- Files: `README.md`, `docs/ARCHITECTURE.md`, `CHANGELOG.md`
- Libraries: none
- Commands: `grep -q "⌘V" README.md && grep -q "⌘V" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md CHANGELOG.md`
- Tests: none
- Gate: G6.9 — `grep -q "⌘V" README.md && grep -q "⌘V" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md CHANGELOG.md` exits 0
- Requirements: none
- Screens: none

### Step 6.10 — Phase 6 check sheet

- Builds: `docs/qa/phase-06.md` lists, each with "Result: not run": (1) align, distribute, group, ungroup, order and duplicate on the reference default, each undone once; (2) a knob copied in one Reference FX instance and pasted with ⌘V into a second instance on another track; (3) pasting ordinary text raises "Paste refused."; (4) the picture `.tickets/.work/ui-compare/S-04.png` and `S-04-workspace--arrange.png` match their mockups. It ends with "Signed off: no".
- Files: `docs/qa/phase-06.md`
- Libraries: none
- Commands: `grep -q "^Signed off: no" docs/qa/phase-06.md`
- Tests: none
- Gate: G6.10 — `grep -q "^Signed off: no" docs/qa/phase-06.md` exits 0
- Requirements: none
- Screens: none

### Step 6.11 — [OWNER] Phase 6 host and screen check

- Builds: the owner performs the items of `docs/qa/phase-06.md`, records each result and signs off.
- Files: `docs/qa/phase-06.md`
- Libraries: Bitwig Studio
- Commands: `python3 tools/devpipe/run.py ui compare S-04`
- Tests: none
- Gate: G6.11 — `grep -q "^Signed off: yes" docs/qa/phase-06.md` exits 0
- Requirements: R-083
- Screens: S-04

**Exit demo:** Following `README.md` and `docs/RUNBOOK.md`: in Bitwig, align and distribute three knobs, group them, move the group, ungroup, bring one to front, duplicate it, copy it, and paste it with ⌘V into a second Reference FX instance on another track; undo each step.

## Phase 7 — Custom element kinds

**Goal:** A plugin developer registers element kinds in Rust that appear in the palette, get an inspector from their declared properties, validate, save, undo, follow the theme, draw anything and drive parameters only through library gestures; unregistered and newer kinds survive untouched; Reference FX ships its Transfer curve.

### Step 7.1 — Kind trait, declarations and registry

- Builds: `custom::ElementKind` (`Send + Sync + 'static`): `id() -> &str`, `version() -> u32`, `palette_name() -> &str`, `icon() -> &'static str` (an egui_material_icons constant), `category() -> Category` (`Control`, `Display`, `Decoration`), `properties() -> &[PropertyDecl]`, `default_size() -> (u32, u32)` (default 160 × 120), `draw(&self, ctx: &mut KindContext<'_>)`, `input(&self, ctx: &mut KindContext<'_>, input: &KindInput)` (default: nothing), `migrate(&self, from_version: u32, props: Map<String, Value>) -> Result<Map<String, Value>, String>` (default: `Err("no migration")`), `animating(&self, ctx: &KindContext<'_>) -> bool` (default false). `PropertyDecl { name: &'static str, label: &'static str, ty: PropertyType }`; `PropertyType`: `Number { min, max, step, default }`, `Choice { options: &'static [&'static str], default: usize }` (2–32 options), `Toggle { default }`, `Text { max_len, default }` (max_len ≤ 4,096 bytes), `ColourRole { default }`, `TypefaceRole { default }`, `Asset { kind: AssetKind }`, `Binding { accepts: Accepts }` (`Any`, `Stepped`, `TwoState`), `Tap { kind: TapSlotKind }` (`Audio`, `Scalar`). `KindRegistry::register(Box<dyn ElementKind>) -> Result<(), KindError>` refuses an id outside 3–64 characters of `[a-z0-9._-]` with at least one dot, an id already registered, version 0, more than 64 properties, duplicate or non-`[a-z0-9_]+` property names, a number whose default is outside `min..=max` or `min ≥ max`, choice counts outside 2–32 (R-153, R-155), and leaves the registry unchanged; `list() -> Vec<KindInfo>`, `get(id)`. The testkit's `TestKind` (`org.example.curve`, version 1, category control, one property of each of the nine types) records what its `draw` and `input` receive in a shared log and can be set to begin a gesture without ending it.
- Files: `crates/mutable-gui/src/custom/mod.rs`, `crates/mutable-gui/src/custom/registry.rs`, `crates/mutable-gui/src/custom/props.rs`, `crates/mutable-gui-testkit/src/test_kind.rs`, `crates/mutable-gui/tests/custom_registry.rs`
- Libraries: serde_json
- Commands: `cargo test -p mutable-gui --test custom_registry`
- Tests: `crates/mutable-gui/tests/custom_registry.rs` (R-152: `org.example.curve` version 1 registers and is listed with its name, category and properties; R-153: a second registration and the id "knob" fail and the registry is unchanged; R-155: the nine-type kind registers and one with 65 properties is refused)
- Gate: G7.1 — `cargo test -p mutable-gui --test custom_registry` exits 0
- Requirements: R-152, R-153, R-155
- Screens: none

### Step 7.2 — Custom properties in documents

- Builds: `doc::Decoder::new(&KindRegistry)` with `.instance(&str)`, `.package(&[u8])`, `.elements(&str)`; the Phase 1–2 functions `doc::decode_instance`, `decode_package` and `decode_elements` call it with an empty registry. `doc::custom` checks an element of a registered kind at its registered version: every declared property present and no other (missing or extra is `Property`), numbers within range, choices among the options, toggles boolean, text within `max_len`, colour and typeface role names valid, assets naming an instance asset of the declared kind, bindings a valid `Binding` or null, taps a string or null; failure is `DocError::Property { kind, name, reason }` (R-157). An unregistered kind, or a stored version above the registered one, stays `Unknown` with `kind`, `kind_version` and `props` kept exactly (R-164, I-20). `EditorState` and every later decode use the instance's registry.
- Files: `crates/mutable-gui/src/doc/custom.rs`, `crates/mutable-gui/src/doc/mod.rs`, `crates/mutable-gui/src/doc/element.rs`, `crates/mutable-gui/tests/doc_custom.rs`
- Libraries: serde_json
- Commands: `cargo test -p mutable-gui --test doc_custom --test doc_instance --test doc_package --test doc_elements`
- Tests: `crates/mutable-gui/tests/doc_custom.rs` (R-157: a curve element whose number property is above its maximum is refused with the text naming that property; R-164: an `org.vendor.wavetable` element loaded and saved keeps its kind, version and props equal; a kind registered at version 1 with a stored version 2 stays unknown)
- Gate: G7.2 — `cargo test -p mutable-gui --test doc_custom --test doc_instance --test doc_package --test doc_elements` exits 0
- Requirements: R-157, R-164
- Screens: none
- Pins: the Phase 1–2 decode tests (`doc_instance.rs`, `doc_package.rs`, `doc_elements.rs`, `doc_validate.rs`, `doc_migrate.rs`) call the empty-registry functions, where every custom element is unknown as before; their assertions hold.

### Step 7.3 — Custom kind migration

- Builds: `custom::migrate::upgrade(kind, stored_version, props)` calls `ElementKind::migrate` for each version from the stored one to the registered one in order, then validates the result as Step 7.2; any error leaves the element `Unknown` with its original version and props (R-167). `doc::custom` uses it for stored versions below the registered one.
- Files: `crates/mutable-gui/src/custom/migrate.rs`, `crates/mutable-gui/src/doc/custom.rs`, `crates/mutable-gui/tests/custom_migrate.rs`
- Libraries: serde_json
- Commands: `cargo test -p mutable-gui --test custom_migrate`
- Tests: `crates/mutable-gui/tests/custom_migrate.rs` (R-167: a version-1 element of a kind registered at version 2 loads as version 2 through the test migration; a migration returning an error leaves it unknown with its version-1 props intact; R-121's counts hold)
- Gate: G7.3 — `cargo test -p mutable-gui --test custom_migrate` exits 0
- Requirements: R-121, R-167
- Screens: none

### Step 7.4 — Kind context and drawing

- Builds: `custom::KindContext<'a>` gives a kind only: `painter()` clipped to the canvas, `rect()` (screen) and `scale()`, `props()`, `theme()` (colour of a role, `FontId` of a typeface role at a size in canvas units, the shape tokens), `value(slot) -> Option<SlotValue { base, modulated, text }>` for its binding slots, `tap(slot) -> Option<TapData>` (Step 7.6), `state()` (`VisualState`), `request_repaint()`, and, during `input` only, `begin(slot)`, `set(slot, normalized)` and `end(slot)` (Step 7.5). It holds no `ParamSource`, `StateCell`, `Storage`, tap producer, undo stack or nice-plug type (I-18). `render::custom::draw` looks the element's kind up: known kinds get `draw` with a fresh context; an `animating` kind keeps frames coming at 60 per second like a display (R-054).
- Files: `crates/mutable-gui/src/custom/context.rs`, `crates/mutable-gui/src/render/custom.rs`, `crates/mutable-gui/tests/custom_draw.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test custom_draw`
- Tests: `crates/mutable-gui/tests/custom_draw.rs` (R-159: `TestKind` filling its frame with its colour-role property draws that colour over its frame, as its log and the harness picture show; R-160: after switching to Studio Light, the same role draws Studio Light's colour; I-18: `KindContext`'s public items are the ones listed, checked by a compile-time use of each)
- Gate: G7.4 — `cargo test -p mutable-gui --test custom_draw` exits 0
- Requirements: R-159, R-160
- Screens: none

### Step 7.5 — Custom input and the gesture tracker

- Builds: in perform mode, pointer and keyboard input over an element whose kind has category `Control` goes to `ElementKind::input` with `KindInput` (pointer position in canvas units relative to the frame, press, release, drag delta, keys); never in design mode and never for displays or decorations (R-161). `custom::gestures` routes `begin`, `set` and `end` on a binding slot whose parameter is present to the editor's `GestureTracker`, and ends every gesture the element left open on pointer release and on editor close (R-162, I-19).
- Files: `crates/mutable-gui/src/custom/gestures.rs`, `crates/mutable-gui/src/perform/mod.rs`, `crates/mutable-gui/tests/custom_input.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test custom_input`
- Tests: `crates/mutable-gui/tests/custom_input.rs` (R-161: the click-counting test control counts one per perform-mode click and none in design mode; R-162: a kind that begins and never ends records an end on release, and on editor close)
- Gate: G7.5 — `cargo test -p mutable-gui --test custom_input` exits 0
- Requirements: R-161, R-162
- Screens: none
- Guards: GD-3 applies (design mode sends nothing); GD-7 applies (a slot whose parameter is absent ignores `begin`, `set`, `end`).

### Step 7.6 — Custom tap slots

- Builds: the taps bound to tap slots of custom elements on the current page join the reading set of Step 3.7 (I-17); `KindContext::tap(slot)` returns only the data of the tap bound to that slot and only when its kind matches the slot (`TapData::Audio { samples, channels, sample_rate }` or `TapData::Scalar { latest, max }`) (R-163). The tap picker opened from a custom tap slot lists only taps of the slot's kind.
- Files: `crates/mutable-gui/src/custom/context.rs`, `crates/mutable-gui/src/editor/taps.rs`, `crates/mutable-gui/src/design/tap_picker.rs`, `crates/mutable-gui/tests/custom_taps.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test custom_taps`
- Tests: `crates/mutable-gui/tests/custom_taps.rs` (R-163: a test kind whose audio slot is bound to "out" receives the samples pushed to "out", and the picker for that slot does not list "gr")
- Gate: G7.6 — `cargo test -p mutable-gui --test custom_taps` exits 0
- Requirements: R-163
- Screens: none

### Step 7.7 — Unknown placeholder and custom wiring

- Builds: `render::unknown::draw` draws an unknown element as a dashed outline in text-muted with `ICON_HELP`, "Unknown element" and its kind id and "v{version}" in Hack. `render::draw_element` dispatches custom elements to `render::custom` (known) or `render::unknown`; no kind uses the fallback any more. In design mode an unknown element can be selected, moved, resized, reordered, duplicated and deleted; its inspector shows its kind id, version and the explanation of S-04 `--unknown` and no property editors (R-165).
- Files: `crates/mutable-gui/src/render/unknown.rs`, `crates/mutable-gui/src/render/mod.rs`, `crates/mutable-gui/src/design/inspector/mod.rs`, `crates/mutable-gui/tests/custom_unknown.rs`
- Libraries: egui, egui_material_icons
- Commands: `cargo test -p mutable-gui --test custom_unknown`
- Tests: `crates/mutable-gui/tests/custom_unknown.rs` (R-164: the placeholder text holds "Unknown element" and "org.vendor.wavetable"; R-165: moving an unknown element changes its frame and its inspector has no property editors)
- Gate: G7.7 — `cargo test -p mutable-gui --test custom_unknown` exits 0
- Requirements: R-164, R-165
- Screens: none

### Step 7.8 — Custom kinds in the palette

- Builds: the palette appends, after the built-in sections, a section headed with the plugin's name holding each registered kind's icon and palette name in registration order; a click adds an element of that kind at its `default_size`, centred and snapped, with every property at its default and slots null, selected, as one `AddElements` (R-154).
- Files: `crates/mutable-gui/src/design/palette.rs`, `crates/mutable-gui/tests/custom_palette.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test custom_palette --test design_palette`
- Tests: `crates/mutable-gui/tests/custom_palette.rs` (R-154: with one registered kind, the palette shows a section "Reference FX" holding it, and choosing it adds one element of that kind at the canvas centre with its default properties)
- Gate: G7.8 — `cargo test -p mutable-gui --test custom_palette --test design_palette` exits 0
- Requirements: R-154
- Screens: none
- Pins: Step 5.10's `design_palette.rs` registers no kind; its assertions hold.

### Step 7.9 — Inspector from declarations

- Builds: `inspector::custom_props` heads a custom element's inspector with its palette name, "{plugin} · version {n}" and the kind id (Hack), then Frame, then "Properties": one row per declaration in order with the editor for its type (number: a drag value with min, max and step; choice: a dropdown; toggle: On/Off segments; text: a field limited to `max_len`; colour role: a role dropdown with swatches; typeface role: Body, Heading, Value; asset: the instance's assets of that kind and None; binding slot: the parameter picker filtered by `accepts`; tap slot: the tap picker of Step 7.6) (R-156). Each edit is one `ReplaceElement` (R-158).
- Files: `crates/mutable-gui/src/design/inspector/custom_props.rs`, `crates/mutable-gui/src/design/inspector/mod.rs`, `crates/mutable-gui/tests/custom_inspector.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test custom_inspector`
- Tests: `crates/mutable-gui/tests/custom_inspector.rs` (R-156: the nine-type kind shows nine rows whose editors match their types; R-158: changing the number property and pressing undo once restores it)
- Gate: G7.9 — `cargo test -p mutable-gui --test custom_inspector` exits 0
- Requirements: R-156, R-158
- Screens: none

### Step 7.10 — Unknown elements in the unbound list

- Builds: `design::unbound::collect` also lists every unknown element as "Unknown element · {kind id}" with a "Show" button that makes its page current and selects it (R-166); the toolbar count includes them.
- Files: `crates/mutable-gui/src/design/unbound.rs`, `crates/mutable-gui/tests/custom_unbound.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test custom_unbound --test design_unbound`
- Tests: `crates/mutable-gui/tests/custom_unbound.rs` (R-166: a layout with one unknown element lists it by kind id, and choosing it selects it)
- Gate: G7.10 — `cargo test -p mutable-gui --test custom_unbound --test design_unbound` exits 0
- Requirements: R-166
- Screens: none
- Pins: Step 5.18's `design_unbound.rs` has no unknown elements; its assertions hold.

### Step 7.11 — Registration through the adapter and the Transfer curve

- Builds: `MutableGui` builder gains `.register_kind(Box<dyn ElementKind>) -> Result<Self, KindError>`, passing the registry to `EditorState`. `examples/reference-plugin/src/transfer_curve.rs` defines `TransferCurve` with the identifiers of "Fixed names" and properties `drive` (Binding, Any, label "Drive"), `curve` (ColourRole, default accent-3, "Curve"), `grid` (Toggle, default true, "Grid"), `points` (Number 16–512, step 1, default 128, "Points"); `curve_points(drive_normalized, points) -> Vec<(f32, f32)>` samples x from −1 to 1 through `dsp::drive_curve(24 × drive_normalized, x)`; `draw` fills the frame with the theme's surface colour, draws a quarter grid in border when `grid`, and the curve polyline in the `curve` role (R-168). `RefFx` registers it.
- Files: `crates/mutable-gui-nice/src/builder.rs`, `examples/reference-plugin/src/transfer_curve.rs`, `examples/reference-plugin/src/lib.rs`, `examples/reference-plugin/tests/transfer_curve.rs`
- Libraries: egui, serde_json
- Commands: `cargo test -p mutable-gui-reference --test transfer_curve`
- Tests: `examples/reference-plugin/tests/transfer_curve.rs` (R-168: the palette offers "Transfer curve"; `curve_points` at Drive 0.2 and 0.6 differ; one placed and bound to Drive receives Drive's new base value in its `drawn()` record after Drive changes)
- Gate: G7.11 — `cargo test -p mutable-gui-reference --test transfer_curve` exits 0
- Requirements: R-152, R-168
- Screens: none

### Step 7.12 — S-04 custom and unknown states, and the full S-12 gallery

- Builds: `screen_s04.rs` gains `S-04-workspace--custom` (the scope narrowed to 300 wide and a Transfer curve at (336, 318, 144 × 186) bound to Drive, selected) and `S-04-workspace--unknown` (the same place holding an `org.vendor.wavetable` version 3 element, selected). `screen_s12.rs` adds the "Custom kind (example)" row (Transfer curve, five states) and the "Unknown element" row, regenerating the three S-12 pictures. `design/UI.md` S-12 gets `Built: examples/reference-plugin/tests/snapshots/S-12-elements.png`.
- Files: `examples/reference-plugin/tests/screen_s04.rs`, `examples/reference-plugin/tests/screen_s12.rs`, `crates/mutable-gui-testkit/src/gallery.rs`, `examples/reference-plugin/tests/snapshots/S-04-workspace--custom.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace--unknown.png`, `examples/reference-plugin/tests/snapshots/S-12-elements.png`, `examples/reference-plugin/tests/snapshots/S-12-elements--light.png`, `examples/reference-plugin/tests/snapshots/S-12-elements--high-contrast.png`, `design/UI.md`
- Libraries: egui_kittest
- Commands: `cargo test -p mutable-gui-reference --test screen_s04 --test screen_s12 && python3 tools/devpipe/run.py ui compare S-12`
- Tests: `examples/reference-plugin/tests/screen_s04.rs`, `examples/reference-plugin/tests/screen_s12.rs`
- Gate: G7.12 — `cargo test -p mutable-gui-reference --test screen_s04 --test screen_s12 && python3 tools/devpipe/run.py ui compare S-12` exits 0
- Requirements: R-159, R-164, R-168
- Screens: S-04, S-12
- Pins: Step 4.14's S-12 pictures gain two rows and are regenerated here.

### Step 7.13 — Documents at Phase 7 truth

- Builds: `README.md` gains the developer's guide to custom kinds (the trait, the nine property types, registration on the builder, migrations, what `KindContext` offers and withholds, and that a panic in kind code is not contained); `docs/ARCHITECTURE.md` adds `custom` and invariants I-18, I-19, I-20 with their tests; `CHANGELOG.md`.
- Files: `README.md`, `docs/ARCHITECTURE.md`, `CHANGELOG.md`
- Libraries: none
- Commands: `grep -q "register_kind" README.md && grep -q "I-20" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md CHANGELOG.md`
- Tests: none
- Gate: G7.13 — `grep -q "register_kind" README.md && grep -q "I-20" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md CHANGELOG.md` exits 0
- Requirements: none
- Screens: none

### Step 7.14 — Phase 7 check sheet

- Builds: `docs/qa/phase-07.md` lists, each with "Result: not run": (1) in Bitwig, the palette's "Reference FX" section adds a Transfer curve; bound to Drive it redraws while Drive moves; its Curve, Grid and Points properties edit and undo; (2) a project with a Transfer curve saved and reopened is identical; (3) the pictures `.tickets/.work/ui-compare/S-12.png` and the S-04 custom and unknown pictures match their mockups. It ends with "Signed off: no".
- Files: `docs/qa/phase-07.md`
- Libraries: none
- Commands: `grep -q "^Signed off: no" docs/qa/phase-07.md`
- Tests: none
- Gate: G7.14 — `grep -q "^Signed off: no" docs/qa/phase-07.md` exits 0
- Requirements: none
- Screens: none

### Step 7.15 — [OWNER] Phase 7 host and screen check

- Builds: the owner performs the items of `docs/qa/phase-07.md`, records each result and signs off.
- Files: `docs/qa/phase-07.md`
- Libraries: Bitwig Studio
- Commands: `python3 tools/devpipe/run.py ui compare S-12`
- Tests: none
- Gate: G7.15 — `grep -q "^Signed off: yes" docs/qa/phase-07.md` exits 0
- Requirements: R-168
- Screens: S-12

### Step 7.16 — Event and snapshot data for custom kinds

- Builds: `PropertyType::Tap` accepts `TapSlotKind::Events` and `TapSlotKind::Snapshot`. `editor::taps` sets the reading flag of an event or snapshot tap only while a custom element whose slot is bound to it is on the current page of an open editor (I-17), calls `discard()` when the flag turns on, drains each event tap once per frame into a reused buffer shared by every element bound to it together with `take_dropped()`, and reads each snapshot tap once per frame with `latest_into` into a reused buffer. `KindContext::tap(slot)` returns `TapData::Events { record_len, records, dropped }` (records drained this frame, oldest first) or `TapData::Snapshot { values, sequence }` for a slot of that kind bound to a tap of that kind, and `None` otherwise.
- Files: `crates/mutable-gui/src/custom/props.rs`, `crates/mutable-gui/src/editor/taps.rs`, `crates/mutable-gui/src/custom/context.rs`, `crates/mutable-gui/tests/custom_tap_kinds.rs`
- Libraries: none
- Commands: `cargo test -p mutable-gui --test custom_tap_kinds --test custom_taps --test editor_taps`
- Tests: `crates/mutable-gui/tests/custom_tap_kinds.rs` (R-172: a test kind, declared in the test with one event slot and one snapshot slot, bound to "grains" receives the 2 records pushed between two frames and 0 on the next frame; bound to "state" it receives the latest block; records pushed before the element's page was shown are never delivered; I-17: the "grains" flag is set only while the element is on the current page of an open editor)
- Gate: G7.16 — `cargo test -p mutable-gui --test custom_tap_kinds --test custom_taps --test editor_taps` exits 0
- Requirements: R-172
- Screens: none
- Feature: F-001
- Pins: Step 7.6's `custom_taps.rs` (audio and scalar slots) and Step 3.7's `editor_taps.rs` keep their assertions. The testkit's `TestKind` keeps its nine properties, so R-156's nine rows hold.

### Step 7.17 — Tap picker for event and snapshot slots

- Builds: the tap picker opened from a custom slot of kind event or snapshot lists only taps of that kind, each with its record length ("4 values per record") or length ("64 values"), the current tap checked, and the footer "Only event taps are listed: this slot reads events." or "Only snapshot taps are listed: this slot reads a snapshot."; a click binds as one `ReplaceElement`.
- Files: `crates/mutable-gui/src/design/tap_picker.rs`, `crates/mutable-gui/tests/custom_tap_picker.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test custom_tap_picker --test design_tap_picker`
- Tests: `crates/mutable-gui/tests/custom_tap_picker.rs` (R-172: with taps "out", "gr", "grains" and "state", the picker of an event slot lists "grains" only; binding it is undone by one undo)
- Gate: G7.17 — `cargo test -p mutable-gui --test custom_tap_picker --test design_tap_picker` exits 0
- Requirements: R-172
- Screens: none
- Feature: F-001
- Pins: Step 5.16's `design_tap_picker.rs` covers built-in displays, whose lists are unchanged; its assertions hold.

### Step 7.18 — Custom controls drawn dimmed

- Builds: a custom element of category control is dimmed in perform mode when every present parameter bound in its binding slots is in `irrelevant()`; `render::custom` then draws it through the painter with `multiply_opacity(0.45)` (D-50), and `KindContext::dimmed() -> bool` tells the kind.
- Files: `crates/mutable-gui/src/render/custom.rs`, `crates/mutable-gui/src/custom/context.rs`, `crates/mutable-gui/tests/custom_dimmed.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test custom_dimmed`
- Tests: `crates/mutable-gui/tests/custom_dimmed.rs` (R-173: `TestKind` with its binding slot on a parameter the rule names records opacity 0.45 and `dimmed()` true, and still counts a perform-mode click; with the parameter relevant, 1.0 and false)
- Gate: G7.18 — `cargo test -p mutable-gui --test custom_dimmed` exits 0
- Requirements: R-173
- Screens: none
- Feature: F-002

### Step 7.19 — Plugin-owned state in custom kinds

- Builds: the testkit's `StatefulKind` (`org.example.counter`, version 1, category control, no properties) holds an `Arc<AtomicU32>` given at construction, adds 1 on each perform-mode click in `input`, and draws the count in the body typeface. `README.md`'s developer guide gains "Plugin-owned state": the rule of D-51, the morph-pad example (scenes in the plugin's own `#[persist]` field, read by the kind, changed by Store and Reset), and that such state is outside mutable-gui's undo, packages and library. The reviewer agent's "What this project has decided (not findings)" gains: "A custom kind may hold and change its plugin's own non-parameter state (D-51); a kind writing a parameter through a captured reference is a finding."
- Files: `crates/mutable-gui-testkit/src/stateful_kind.rs`, `crates/mutable-gui-testkit/src/lib.rs`, `crates/mutable-gui/tests/custom_plugin_state.rs`, `README.md`, `.claude/agents/runtime-mutable-gui-reviewer.md`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test custom_plugin_state && grep -q "Plugin-owned state" README.md && grep -q "D-51" .claude/agents/runtime-mutable-gui-reviewer.md`
- Tests: `crates/mutable-gui/tests/custom_plugin_state.rs` (R-176: three perform-mode clicks make the counter 3 and the kind draws "3"; `cell.load()` and the undo depth are equal before and after the clicks; a design-mode click selects the element and leaves the counter at 3)
- Gate: G7.19 — `cargo test -p mutable-gui --test custom_plugin_state && grep -q "Plugin-owned state" README.md && grep -q "D-51" .claude/agents/runtime-mutable-gui-reviewer.md` exits 0
- Requirements: R-176
- Screens: none
- Feature: F-004

**Exit demo:** Following `README.md` and `docs/RUNBOOK.md`: in Bitwig, add a Transfer curve from the palette's "Reference FX" section, bind it to Drive, move Drive and watch the curve change, edit its colour and grid, undo, save and reopen the project.

## Phase 8 — Library, packages and defaults

**Goal:** The user saves, lists, applies, exports, imports and deletes layouts and themes in the shared library, sets and clears the plugin's default and the suite default theme, and imports a package from another plugin with a clear warning; every failure leaves the library and the layout as they were, and S-02, S-09, S-10 and S-11 match their mockups.

### Step 8.1 — Storage

- Builds: `library::Storage` (object safe): `list(dir) -> io::Result<Vec<FileInfo { name, modified: SystemTime, len }>>`, `read_limited(path, max) -> Result<Vec<u8>, DocError or io::Error>` (reads at most `max + 1` bytes, `TooLarge` beyond), `write_atomic(path, bytes) -> io::Result<()>` (writes `.{file name}.tmp-{pid}-{counter}` in the same folder, `sync_all`, renames over the target; removes the temporary file on any error; I-10), `delete(path)`, `create_dir_all(dir)`. `library::FsStorage` implements it with `std::fs`; `library` is the only module touching the file system.
- Files: `crates/mutable-gui/src/library/mod.rs`, `crates/mutable-gui/src/library/storage.rs`, `crates/mutable-gui/src/lib.rs`, `crates/mutable-gui/tests/library_storage.rs`
- Libraries: tempfile
- Commands: `cargo test -p mutable-gui --test library_storage`
- Tests: `crates/mutable-gui/tests/library_storage.rs` (a write leaves no temporary file; a write into a folder made read-only with `set_permissions(0o555)` fails and the folder's listing and bytes are unchanged, R-134)
- Gate: G8.1 — `cargo test -p mutable-gui --test library_storage` exits 0
- Requirements: R-134
- Screens: none

### Step 8.2 — Library paths

- Builds: `library::LibraryPaths { root, clap_id }` with `platform(clap_id) -> Option<Self>` using `dirs::data_dir()?.join("mutable-gui")` (R-125, D-32), `layouts()` = `root/layouts/<clap id>/`, `themes()` = `root/themes/`, `file_for(name)` per choice 10, `user_default_file()` = `layouts()/.default.mgui`, `suite_theme_file()` = `themes()/.default.mgui`.
- Files: `crates/mutable-gui/src/library/paths.rs`, `crates/mutable-gui/src/library/mod.rs`, `crates/mutable-gui/tests/library_paths.rs`
- Libraries: dirs
- Commands: `cargo test -p mutable-gui --test library_paths`
- Tests: `crates/mutable-gui/tests/library_paths.rs` (R-125: on macOS the reference plugin's layouts folder ends with `Library/Application Support/mutable-gui/layouts/org.mutable-gui.reference`; "a/b:c" maps to `a_b_c.mgui`; ".hidden" maps to `_hidden.mgui`)
- Gate: G8.2 — `cargo test -p mutable-gui --test library_paths` exits 0
- Requirements: R-125
- Screens: none

### Step 8.3 — Listing

- Builds: `library::listing::layouts(storage, paths, decoder) -> Vec<LayoutEntry>` starts with `LayoutEntry::DeveloperDefault` (read-only: apply and export only, R-151), then one entry per `*.mgui` not starting with `.` read with `read_limited(PACKAGE_MAX)` and decoded: readable entries carry the package name, modification date, page count, canvas, control count and asset bytes; others are `Unreadable { file name }` (R-135). Order: the entry starred as the user default first, then newest first, unreadable last. `listing::themes` starts with the three built-ins (starred one when it is the suite default), then saved themes newest first, unreadable last. Both are re-read every time the library panel or a theme submenu opens. Listing also deletes files named `.*.tmp-*` older than 10 minutes in the folder it reads, which a process killed during `write_atomic` leaves behind.
- Files: `crates/mutable-gui/src/library/listing.rs`, `crates/mutable-gui/tests/library_listing.rs`
- Libraries: tempfile
- Commands: `cargo test -p mutable-gui --test library_listing`
- Tests: `crates/mutable-gui/tests/library_listing.rs` (R-151: an empty library lists exactly "Developer default" with no delete; R-135: a corrupt file in the themes folder appears marked unreadable; order rules)
- Gate: G8.3 — `cargo test -p mutable-gui --test library_listing` exits 0
- Requirements: R-135, R-151
- Screens: none

### Step 8.4 — Saving with collisions

- Builds: `library::save::layout(storage, paths, name, layout, assets, replace: bool)` and `save::theme(…, theme, assets, replace)` write a package (layout-only or theme-only, `doc::now_rfc3339()`, source of this plugin) with `write_atomic`. Outcomes: `Saved`; `NameReserved` for "Developer default" (layouts) or a built-in theme name (themes) (GD-5, R-106, R-151); `Exists { modified }` when the file exists and `replace` is false (R-127); `Failed(io::Error)`. `save::next_free_name(name)` gives "{name} 2", "{name} 3", … at the lowest unused. Names are 1–64 characters. Two instances may race on a name: there is no lock across processes, and the last confirmed save wins (specification edge case).
- Files: `crates/mutable-gui/src/library/save.rs`, `crates/mutable-gui/tests/library_save.rs`
- Libraries: tempfile
- Commands: `cargo test -p mutable-gui --test library_save`
- Tests: `crates/mutable-gui/tests/library_save.rs` (R-126: saving "Live" creates an entry holding the layout; R-127: saving "Live" again without replace leaves the first file byte-identical; R-128: a theme saved through plugin A's paths is listed by plugin B's; R-106: "Studio Dark" is reserved; `next_free_name("Live")` is "Live 2")
- Gate: G8.4 — `cargo test -p mutable-gui --test library_save` exits 0
- Requirements: R-106, R-126, R-127, R-128
- Screens: none
- Guards: GD-5 applies: reserved names are refused before any write, and the dialog asks for another name. GD-1 and GD-2 make saving unreachable (Library disabled or absent).

### Step 8.5 — Deleting and defaults

- Builds: `library::delete::entry(storage, paths, entry)` removes a saved layout's or theme's file; the developer default and built-ins have no delete (R-136, GD-5). `library::defaults`: `set_user_default(layout, theme, assets, source_name)`, `clear_user_default()`, `user_default()`, `set_suite_theme(theme, assets)`, `clear_suite_theme()`, `suite_theme()` read and write the dot-files of choice 10 through `Storage`. `editor::defaults` resolves a new instance (empty cell): layout from the user default, else the developer default (R-113); theme from the user default, else the suite default theme, else the developer default's theme (R-114); an instance with a document is never touched by defaults (R-115). The unreadable-state fallback of Step 2.14 uses the user default first. `EditorState::with_library(Box<dyn Storage>, LibraryPaths)`; the adapter builder passes `FsStorage` and `LibraryPaths::platform(clap_id)`; without a library folder the editor works from defaults and instance state (specification edge case).
- Files: `crates/mutable-gui/src/library/delete.rs`, `crates/mutable-gui/src/library/defaults.rs`, `crates/mutable-gui/src/editor/defaults.rs`, `crates/mutable-gui/tests/library_defaults.rs`
- Libraries: tempfile
- Commands: `cargo test -p mutable-gui --test library_defaults --test editor_defaults --test editor_embedded --test editor_unreadable`
- Tests: `crates/mutable-gui/tests/library_defaults.rs` (R-136: confirming deletion of "Live" removes its file; R-113: with a user default a new instance's layout equals it, after clearing a newer one gets the developer default; R-114: the three theme cases; R-115: an open instance keeps its theme after the suite default changes; R-132 and R-133 at the library level)
- Gate: G8.5 — `cargo test -p mutable-gui --test library_defaults --test editor_defaults --test editor_embedded --test editor_unreadable` exits 0
- Requirements: R-113, R-114, R-115, R-132, R-133, R-136
- Screens: none
- Pins: Step 1.17's `editor_defaults.rs`, Step 2.11's `editor_embedded.rs` and Step 2.14's `editor_unreadable.rs` run with no library (or an empty one), where the developer default still applies; their assertions hold.

### Step 8.6 — File dialogs and export

- Builds: `library::FileDialog` (`open_package() -> Option<PathBuf>`, `save_package(default_name) -> Option<PathBuf>`, `open_image()`, `open_font()`); `library::RfdDialog` uses `rfd::FileDialog` with filters "mutable-gui package" (`mgui`), "PNG image" (`png`), "Font" (`ttf`, `otf`); the testkit's `FakeFileDialog` returns queued paths. `library::export::current(…)` writes the instance's layout, theme and assets (choice 12) and `export::entry(…)` a library entry alone, both through `write_atomic` at the chosen path (R-129). The adapter builder passes `RfdDialog`.
- Files: `crates/mutable-gui/src/library/dialog.rs`, `crates/mutable-gui/src/library/export.rs`, `crates/mutable-gui-testkit/src/fake_dialog.rs`, `crates/mutable-gui/tests/library_export.rs`
- Libraries: rfd, tempfile
- Commands: `cargo test -p mutable-gui --test library_export`
- Tests: `crates/mutable-gui/tests/library_export.rs` (an export decodes back to the instance's layout and theme as documents; a cancelled dialog writes nothing)
- Gate: G8.6 — `cargo test -p mutable-gui --test library_export` exits 0
- Requirements: R-129
- Screens: none

### Step 8.7 — Import

- Builds: `library::import::package(path)` reads with `read_limited(PACKAGE_MAX)` (R-137) and decodes with the instance's registry (GD-6), then commits one `SetAll`, `SetLayout` or `SetTheme` for what the package holds (R-130). A layout-only package whose assets plus the current theme's would pass 4 MiB is refused with the asset-cap notice (D-11). A source CLAP id other than this plugin's raises the cross-plugin warning naming it (choice 14), with n bound and m unbound controls counted after import and the actions "Show unbound" (enters design mode and opens S-07; hidden when design mode is switched off) and "Undo import" (R-131); another plugin's custom elements arrive as unknown elements. A refusal raises "Import refused." with the `DocError` text and leaves layout, theme, library and undo depth as they were (R-143).
- Files: `crates/mutable-gui/src/library/import.rs`, `crates/mutable-gui/src/editor/mod.rs`, `crates/mutable-gui/tests/library_import.rs`
- Libraries: tempfile
- Commands: `cargo test -p mutable-gui --test library_import`
- Tests: `crates/mutable-gui/tests/library_import.rs` (R-129: export both, import into a new instance, document-equal; R-130: import then one undo restores layout and theme; R-131: a package from plugin X with "cutoff" and "drive" imports "cutoff" bound, "drive" unbound and one notice naming X; R-143: for every refused fixture of R-137–R-142 the instance state and undo depth are equal before and after; R-137: a 9 MiB file is refused after reading at most 8 MiB + 1 bytes)
- Gate: G8.7 — `cargo test -p mutable-gui --test library_import` exits 0
- Requirements: R-129, R-130, R-131, R-137, R-138, R-139, R-140, R-141, R-142, R-143
- Screens: none
- Guards: GD-1 applies: import is unavailable while preserving (menu entries disabled). GD-2 applies: "Import package…" is not offered with design mode off. GD-4 applies to the instance asset cap after import. GD-6 applies to the file. Two requirements bear here, R-130 (one undoable change) and R-143 (a refusal changes nothing): a refusal happens before the command, so neither the state nor the undo stack moves.

### Step 8.8 — Discarding a kept unreadable layout

- Builds: the unreadable-state notice gains "Discard saved layout…", and the editor menu, while preserving, shows a locked row ("This project's layout is kept unchanged.") with "Discard saved layout…" and draws Design mode, Theme and Library disabled (R-119). Either opens the S-10 discard dialog (Step 8.12 draws it): "Discard the saved layout?", the cause with both versions when newer ("It was made by a newer version (format {n}; this one reads up to 1).") or "It is damaged.", then "Discarding unlocks editing, and the next project save writes the layout shown now instead. Opening this project in the newer version will then show this layout too."; buttons "Keep it" and "Discard" (danger). Discard calls `StateCell::discard_kept()`, publishes the shown layout, and makes editing available (R-120). "Reset to developer default" while preserving opens the same dialog first and resets after Discard (R-150).
- Files: `crates/mutable-gui/src/editor/load.rs`, `crates/mutable-gui/src/render/chrome/editor_menu.rs`, `crates/mutable-gui/tests/editor_discard.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test editor_discard --test editor_unreadable`
- Tests: `crates/mutable-gui/tests/editor_discard.rs` (R-120: after discarding, a save holds the fallback layout and design mode is offered; R-119: while preserving, the menu offers no enabled Design mode and a knob drag still records a gesture; R-150: the Reset entry exists in perform mode, design mode, with design mode off and while preserving, where choosing it opens the discard dialog)
- Gate: G8.8 — `cargo test -p mutable-gui --test editor_discard --test editor_unreadable` exits 0
- Requirements: R-119, R-120, R-150
- Screens: none
- Pins: Step 2.14's `editor_unreadable.rs` asserts the notice's summary and cause, which hold; its assertion on the notice's actions changes from ["Keep it"] to ["Keep it", "Discard saved layout…"].
- Guards: GD-1 is the guard being lifted: only this confirmed action ends it.

### Step 8.9 — Theme and Library submenus

- Builds: `render::chrome::theme_menu` (entry "Theme" with the active theme's name): the three built-ins, the library's themes (listed fresh), "Import theme…" (choice 13), "Use for all plugins" (sets the suite default from the active theme, R-133); choosing a theme commits `SetTheme` at once (R-108). `render::chrome::library_menu`: "Save layout…", "Save theme…", "Open library…", "Import package…", "Export package…" (choice 12), "Use as my default for {plugin}" and "Clear my default" (R-132). The editor menu places Theme and Library before Reset; below 520 × 420 logical px submenus drill in with a back row (choice 17).
- Files: `crates/mutable-gui/src/render/chrome/theme_menu.rs`, `crates/mutable-gui/src/render/chrome/library_menu.rs`, `crates/mutable-gui/src/render/chrome/editor_menu.rs`, `crates/mutable-gui/tests/chrome_submenus.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test chrome_submenus --test design_mode`
- Tests: `crates/mutable-gui/tests/chrome_submenus.rs` (R-108: choosing "High Contrast" makes it active on the next frame, also with design mode off; R-132: Use as my default then a new instance uses it, Clear then the developer default; R-009: with design mode off the menu holds no Design mode, Library or Import package entry and Theme keeps Import theme…)
- Gate: G8.9 — `cargo test -p mutable-gui --test chrome_submenus --test design_mode` exits 0
- Requirements: R-009, R-108, R-132, R-133
- Screens: none
- Guards: GD-1 applies: Theme and Library drawn disabled while preserving. GD-2 applies: Library absent; Theme, Import theme… and Use for all plugins stay. GD-4 applies to a theme choice whose assets would bring the instance over 4 MiB ("Not added. Assets are limited to 4 MiB per instance; …").
- Pins: Step 5.4's `design_mode.rs` R-009 test asserts no "Design mode" entry; it holds, and this step's test adds the Library and import assertions.

### Step 8.10 — Library panel

- Builds: `design::library_panel` draws S-09 as a modal over the `--tool-scrim`, 640 × 420 px centred (bottom sheet below 520 × 420): tabs "Layouts · {plugin}" and "Themes · all plugins"; the list at the left (developer default "as shipped", stars "my default" and "all plugins", "built in", UTC dates, "unreadable" in danger); at the right the preview of choice 29 and the details line ("1 page · 400 × 300 · 6 controls · no assets"); actions per entry: Apply (one undoable command, choice 11), Export…, Delete… (S-10), "Use as my default" or "Clear my default" (layouts), "Use for all plugins" or "Stop using for all plugins" (themes); none of Delete for the developer default and built-ins, only Delete for unreadable entries; a footer with Import package…, "Save current layout…" or "Save current theme…", and the folder path shortened to `…/layouts/{clap id}/` or `…/mutable-gui/themes/`. Escape closes. The design toolbar's Library button opens it and is enabled.
- Files: `crates/mutable-gui/src/design/library_panel.rs`, `crates/mutable-gui/src/design/toolbar.rs`, `crates/mutable-gui/tests/design_library_panel.rs`
- Libraries: egui, egui_material_icons
- Commands: `cargo test -p mutable-gui --test design_library_panel`
- Tests: `crates/mutable-gui/tests/design_library_panel.rs` (Apply on a layout entry replaces the layout and one undo restores it; the developer default entry offers no Delete; an unreadable entry offers only Delete; Use for all plugins stars the theme)
- Gate: G8.10 — `cargo test -p mutable-gui --test design_library_panel` exits 0
- Requirements: R-106, R-128, R-132, R-133, R-135, R-151
- Screens: none
- Guards: GD-1 and GD-2 make the panel unreachable (its menu entries are disabled or absent). GD-4 applies to Apply (asset cap). GD-5 applies (no delete or overwrite of built-ins and the developer default).

### Step 8.11 — Library dialogs

- Builds: `design::dialogs` draws S-10 modals over the scrim, 360 px wide: Save ("Save layout" or "Save theme", a name field of 1–64 characters, "Saved to Layouts · {plugin}." or "Saved to Themes · all plugins. 1 – 64 characters.", Cancel and Save); a reserved name shows "“{name}” is built in. Use another name." under the field and disables Save; Collision ("Replace “{name}”?", "A {layout | theme} named “{name}” is already in your library, saved {date}. Replacing it overwrites that file; it cannot be recovered.", Cancel, "Save as “{next free name}”", Replace in danger) (R-127); Delete ("Delete “{name}”?", "This removes the file from your library; it cannot be recovered.", Cancel, Delete in danger) (R-136); Discard (Step 8.8's texts). Escape cancels. A failed write raises "Couldn't save “{name}”." (R-134).
- Files: `crates/mutable-gui/src/design/dialogs.rs`, `crates/mutable-gui/tests/design_dialogs.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test design_dialogs`
- Tests: `crates/mutable-gui/tests/design_dialogs.rs` (R-127: declining the collision leaves the file byte-identical; "Save as “Live 2”" writes "Live 2"; R-136: Cancel keeps the file, Delete removes it; R-106: "Studio Dark" disables Save; R-134: a read-only folder raises the notice and the library is unchanged)
- Gate: G8.11 — `cargo test -p mutable-gui --test design_dialogs` exits 0
- Requirements: R-106, R-127, R-134, R-136
- Screens: none

### Step 8.12 — S-02 editor menu screen

- Builds: `examples/reference-plugin/tests/screen_s02.rs` snapshots the editor menu on the reference default: `S-02-editor-menu` (open, perform mode), `S-02-editor-menu--library` (Library submenu), `S-02-editor-menu--preserving` (state loaded from a version-3 document), `S-02-editor-menu--reduced` (built with `.design_mode(false)`), `S-02-editor-menu--small` (400 × 300 `SMALL` layout, Theme drilled in). `design/UI.md` S-02 gets `Built: examples/reference-plugin/tests/snapshots/S-02-editor-menu.png`.
- Files: `examples/reference-plugin/tests/screen_s02.rs`, `examples/reference-plugin/tests/snapshots/S-02-editor-menu.png`, `examples/reference-plugin/tests/snapshots/S-02-editor-menu--library.png`, `examples/reference-plugin/tests/snapshots/S-02-editor-menu--preserving.png`, `examples/reference-plugin/tests/snapshots/S-02-editor-menu--reduced.png`, `examples/reference-plugin/tests/snapshots/S-02-editor-menu--small.png`, `design/UI.md`
- Libraries: egui_kittest
- Commands: `cargo test -p mutable-gui-reference --test screen_s02 && python3 tools/devpipe/run.py ui compare S-02`
- Tests: `examples/reference-plugin/tests/screen_s02.rs`
- Gate: G8.12 — `cargo test -p mutable-gui-reference --test screen_s02 && python3 tools/devpipe/run.py ui compare S-02` exits 0
- Requirements: R-009, R-011, R-150
- Screens: S-02

### Step 8.13 — S-09 library screen

- Builds: `examples/reference-plugin/tests/screen_s09.rs` fills a temporary library with the entries of `design/ui/S-09-library.html` ("Live" as user default saved 20 Nov 2026, "Touch 16:9", "Mix engineer", "Every parameter", the unreadable "festival-v3"; modification times set with `File::set_modified`) and snapshots `S-09-library` with "Live" selected, and `S-09-library--themes` with "Studio Dark" as suite default, "Night Ink" and "Stage Amber". `design/UI.md` S-09 gets `Built: examples/reference-plugin/tests/snapshots/S-09-library.png`.
- Files: `examples/reference-plugin/tests/screen_s09.rs`, `examples/reference-plugin/tests/snapshots/S-09-library.png`, `examples/reference-plugin/tests/snapshots/S-09-library--themes.png`, `design/UI.md`
- Libraries: egui_kittest, tempfile
- Commands: `cargo test -p mutable-gui-reference --test screen_s09 && python3 tools/devpipe/run.py ui compare S-09`
- Tests: `examples/reference-plugin/tests/screen_s09.rs`
- Gate: G8.13 — `cargo test -p mutable-gui-reference --test screen_s09 && python3 tools/devpipe/run.py ui compare S-09` exits 0
- Requirements: R-135, R-151
- Screens: S-09

### Step 8.14 — S-10 dialogs screen and the design screens with Library enabled

- Builds: `examples/reference-plugin/tests/screen_s10.rs` snapshots `S-10-dialog` (save, "Live set" typed), `S-10-dialog--collision` ("Live" saved 20 Nov 2026), `S-10-dialog--delete`, `S-10-dialog--discard` (version-3 state). The S-04 to S-07 pictures are regenerated now that the toolbar's Library button is enabled. `design/UI.md` S-10 gets `Built: examples/reference-plugin/tests/snapshots/S-10-dialog.png`.
- Files: `examples/reference-plugin/tests/screen_s10.rs`, `examples/reference-plugin/tests/snapshots/S-10-dialog.png`, `examples/reference-plugin/tests/snapshots/S-10-dialog--collision.png`, `examples/reference-plugin/tests/snapshots/S-10-dialog--delete.png`, `examples/reference-plugin/tests/snapshots/S-10-dialog--discard.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace--arrange.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace--custom.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace--unknown.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace--small.png`, `examples/reference-plugin/tests/snapshots/S-05-picker.png`, `examples/reference-plugin/tests/snapshots/S-05-picker--tap.png`, `examples/reference-plugin/tests/snapshots/S-06-pages.png`, `examples/reference-plugin/tests/snapshots/S-07-unbound.png`, `design/UI.md`
- Libraries: egui_kittest
- Commands: `UPDATE_SNAPSHOTS=1 cargo test -p mutable-gui-reference --test screen_s04 --test screen_s05 --test screen_s06 --test screen_s07 && cargo test -p mutable-gui-reference --test screen_s10 --test screen_s04 --test screen_s05 --test screen_s06 --test screen_s07 && python3 tools/devpipe/run.py ui compare S-10`
- Tests: `examples/reference-plugin/tests/screen_s10.rs`
- Gate: G8.14 — `cargo test -p mutable-gui-reference --test screen_s10 --test screen_s04 --test screen_s05 --test screen_s06 --test screen_s07 && python3 tools/devpipe/run.py ui compare S-10` exits 0
- Requirements: R-120, R-127, R-136
- Screens: S-10
- Pins: the S-04 to S-07 pictures of Steps 5.19–5.22, 6.7, 6.8 and 7.12 show the toolbar, whose Library button is now enabled; they are regenerated here and their tests pass unchanged.

### Step 8.15 — S-11 notices screen

- Builds: `examples/reference-plugin/tests/screen_s11.rs` raises, on the reference default, the refused import of a 9.4 MiB "festival.mgui", the cross-plugin warning for a package "Dark Pack" from `com.ember.synth` with 14 bound and 6 unbound controls, and the failed save of "Live" into a read-only folder, and snapshots `S-11-notices`; loads a version-3 state for `S-11-notices--unreadable`. `design/UI.md` S-11 gets `Built: examples/reference-plugin/tests/snapshots/S-11-notices.png`.
- Files: `examples/reference-plugin/tests/screen_s11.rs`, `examples/reference-plugin/tests/snapshots/S-11-notices.png`, `examples/reference-plugin/tests/snapshots/S-11-notices--unreadable.png`, `design/UI.md`
- Libraries: egui_kittest, tempfile
- Commands: `cargo test -p mutable-gui-reference --test screen_s11 && python3 tools/devpipe/run.py ui compare S-11`
- Tests: `examples/reference-plugin/tests/screen_s11.rs`
- Gate: G8.15 — `cargo test -p mutable-gui-reference --test screen_s11 && python3 tools/devpipe/run.py ui compare S-11` exits 0
- Requirements: R-012, R-117, R-131, R-134, R-137
- Screens: S-11

### Step 8.16 — Documents at Phase 8 truth

- Builds: `README.md` (library, packages, defaults, the `.mgui` file), `docs/RUNBOOK.md` (library folder per platform, the dot-files of choice 10, recovering from a read-only folder, what an unreadable entry means), `docs/ARCHITECTURE.md` (library module, I-07 and I-10 with tests), `CHANGELOG.md`.
- Files: `README.md`, `docs/RUNBOOK.md`, `docs/ARCHITECTURE.md`, `CHANGELOG.md`
- Libraries: none
- Commands: `grep -q ".default.mgui" docs/RUNBOOK.md && grep -q "I-10" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/RUNBOOK.md docs/ARCHITECTURE.md CHANGELOG.md`
- Tests: none
- Gate: G8.16 — `grep -q ".default.mgui" docs/RUNBOOK.md && grep -q "I-10" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/RUNBOOK.md docs/ARCHITECTURE.md CHANGELOG.md` exits 0
- Requirements: none
- Screens: none

### Step 8.17 — Phase 8 check sheet

- Builds: `docs/qa/phase-08.md` lists, each with "Result: not run": (1) Flow 4: save the current layout as "Live", see it in the library, export it, delete it after confirming; (2) Flow 5: export a package from one instance and import it into a second instance; undo the import; (3) Flow 6: reset to developer default from the menu and from the library's "Developer default" entry; (4) set "Use as my default", insert a new instance that opens on it, clear it; set a suite default theme and see a new instance use it; (5) make the library folder read-only and see the failed-save notice with the library unchanged; (6) the pictures `.tickets/.work/ui-compare/S-02.png`, `S-09.png`, `S-10.png` and `S-11.png` match their mockups. It ends with "Signed off: no".
- Files: `docs/qa/phase-08.md`
- Libraries: none
- Commands: `grep -q "^Signed off: no" docs/qa/phase-08.md`
- Tests: none
- Gate: G8.17 — `grep -q "^Signed off: no" docs/qa/phase-08.md` exits 0
- Requirements: none
- Screens: none

### Step 8.18 — [OWNER] Phase 8 host and screen check

- Builds: the owner performs the items of `docs/qa/phase-08.md`, records each result and signs off.
- Files: `docs/qa/phase-08.md`
- Libraries: Bitwig Studio
- Commands: `python3 tools/devpipe/run.py ui compare S-02 && python3 tools/devpipe/run.py ui compare S-09 && python3 tools/devpipe/run.py ui compare S-10 && python3 tools/devpipe/run.py ui compare S-11`
- Tests: none
- Gate: G8.18 — `grep -q "^Signed off: yes" docs/qa/phase-08.md` exits 0
- Requirements: R-130
- Screens: S-02, S-09, S-10, S-11

**Exit demo:** Following `README.md` and `docs/RUNBOOK.md`: in Bitwig, save a layout to the library, export it to a `.mgui` file, import that file into a second Reference FX instance, undo the import, set and clear "my default", set a suite default theme, and reset to the developer default.

## Phase 9 — Themes and the theme editor

**Goal:** The user edits the active theme live (colour roles with contrast warnings, typefaces from built-in fonts or font assets, surface fills, shape tokens), adds fonts and images within the 4 MiB cap, and saves the theme to the shared library; S-08 and the finished design-mode screens match their mockups.

### Step 9.1 — Surface fills

- Builds: `render::fill::paint(painter, rect, radius, fill, theme, textures)` paints `solid` as a rounded rectangle; `gradient` by tessellating the rounded rectangle with `epaint::Tessellator` and setting each vertex colour from its position along the gradient (`angle_deg` as CSS `linear-gradient`: 0 points to the top, 90 to the right; `from` at the start, `to` at the end); `grain` as the role's colour under a 64 × 64 seeded value-noise texture tiled with `TextureWrapMode::Repeat` at opacity `amount`; `image` as the asset's texture covering the rectangle. The canvas draws with the `canvas` fill, panels with their `surface` role's fill, display backgrounds with the `display` fill and the background parts of controls (knob body, fader handle, switch off track, XY field, selector and menu background) with the `control` fill, each unless the element's `colours` sets that slot. Built-in themes use solid fills of the roles the slots already used, so earlier pictures do not change.
- Files: `crates/mutable-gui/src/render/fill.rs`, `crates/mutable-gui/src/render/mod.rs`, `crates/mutable-gui/src/render/panel.rs`, `crates/mutable-gui/tests/render_fill.rs`, `crates/mutable-gui/tests/snapshots/fills.png`
- Libraries: egui, egui_kittest
- Commands: `cargo test -p mutable-gui --test render_fill && cargo test -p mutable-gui-reference --test screen_s01 --test screen_s12`
- Tests: `crates/mutable-gui/tests/render_fill.rs` (R-101: a panel on a gradient fill has its first role's colour at the gradient's start vertex and the second at its end; a picture of the four fill kinds)
- Gate: G9.1 — `cargo test -p mutable-gui --test render_fill && cargo test -p mutable-gui-reference --test screen_s01 --test screen_s12` exits 0
- Requirements: R-101
- Screens: none
- Pins: Steps 4.12 and 7.12's S-01 and S-12 pictures use built-in themes, whose fills equal the colours drawn before; they pass unchanged.

### Step 9.2 — Typefaces from font assets

- Builds: `theme::fonts::install` loads every font asset of the instance named by a typeface as `FontData` named by its asset id and puts it first in `mg-body`, `mg-heading` or `mg-value`, followed by the chain of choice 21; it reinstalls fonts on the frame after the theme's typefaces or the assets change (R-100).
- Files: `crates/mutable-gui/src/theme/fonts.rs`, `crates/mutable-gui/tests/theme_font_assets.rs`
- Libraries: egui, skrifa
- Commands: `cargo test -p mutable-gui --test theme_font_assets --test theme_fonts`
- Tests: `crates/mutable-gui/tests/theme_font_assets.rs` (R-100: with Inter-Medium's bytes as a font asset named by the heading typeface, the `mg-heading` family lists that asset first and a heading label lays out with it; the family lists Inter and Hack after it)
- Gate: G9.2 — `cargo test -p mutable-gui --test theme_font_assets --test theme_fonts` exits 0
- Requirements: R-100
- Screens: none
- Pins: Step 1.7's `theme_fonts.rs` uses built-in names only; its assertions hold.

### Step 9.3 — Recolouring through roles

- Builds: `DrawnElement` gains `slots: Vec<(String, Color32)>`, the resolved colour of each of the element's slots on that frame.
- Files: `crates/mutable-gui/src/render/drawn.rs`, `crates/mutable-gui/tests/theme_recolour.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test theme_recolour --test editor_perform`
- Tests: `crates/mutable-gui/tests/theme_recolour.rs` (R-099: a knob whose `arc` slot is accent-3 records the new theme's accent-3 colour on the frame after a `SetTheme`)
- Gate: G9.3 — `cargo test -p mutable-gui --test theme_recolour --test editor_perform` exits 0
- Requirements: R-099
- Screens: none
- Pins: Step 1.16's `editor_perform.rs` reads other fields of `DrawnElement`; its assertions hold.

### Step 9.4 — Shape tokens across every kind

- Builds: every built-in kind draws its corner radius, border width, knob style, track thickness and handle size from `view.shape(element)`; `DrawnElement` gains `shape: ShapeTokens`.
- Files: `crates/mutable-gui/src/render/drawn.rs`, `crates/mutable-gui/src/render/view.rs`, `crates/mutable-gui/tests/theme_shape.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test theme_shape && cargo test -p mutable-gui-reference --test screen_s12`
- Tests: `crates/mutable-gui/tests/theme_shape.rs` (R-102: a theme with radius 16 and track 8 records them for a panel and a knob; a knob overriding knob style pointer records pointer while the theme says arc)
- Gate: G9.4 — `cargo test -p mutable-gui --test theme_shape && cargo test -p mutable-gui-reference --test screen_s12` exits 0
- Requirements: R-102
- Screens: none
- Pins: the S-12 pictures use built-in tokens equal to the geometry drawn before; they pass unchanged.

### Step 9.5 — Assets: adding, removing, the cap and formats

- Builds: `edit::Command` gains `AddAsset(Asset)`, `RemoveAsset(AssetId)` (refused while referenced) and `Batch(Vec<Command>)` (applied in order as one undoable change; any refusal undoes the batch). `edit::assets::referenced(layout, theme, registry) -> BTreeSet<AssetId>` (image elements, custom asset properties, any string equal to an asset id inside unknown props, typefaces, image fills). `SetLayout`, `SetTheme` and `SetAll` drop the assets neither the new layout nor the new theme refers to; no other command drops assets (choice 5). `edit::assets::check_cap` refuses any command after which the instance's decoded asset bytes exceed 4 MiB (GD-4, D-11). `edit::assets::from_file(bytes, file_name, expected: AssetKind)` refuses a file whose sniffed kind differs, naming the accepted format (R-123), or that does not decode, and returns the `Asset`; the cap then refuses with "Assets are limited to 4 MiB per instance; “{file}” would bring them to {x.x} MiB." (R-122).
- Files: `crates/mutable-gui/src/edit/assets.rs`, `crates/mutable-gui/src/edit/command.rs`, `crates/mutable-gui/src/edit/apply.rs`, `crates/mutable-gui/tests/edit_assets.rs`
- Libraries: png, skrifa, base64
- Commands: `cargo test -p mutable-gui --test edit_assets --test edit_apply --test design_clipboard --test library_import`
- Tests: `crates/mutable-gui/tests/edit_assets.rs` (R-122: with 3.5 MiB of assets, adding a 1 MiB PNG is refused and assets stay 3.5 MiB; R-123: a JPEG added as an image is refused with a notice naming PNG; a theme switch drops the old theme's font asset; a `Batch` of AddAsset and ReplaceElement undoes in one step)
- Gate: G9.5 — `cargo test -p mutable-gui --test edit_assets --test edit_apply --test design_clipboard --test library_import` exits 0
- Requirements: R-122, R-123
- Screens: none
- Guards: GD-4 applies to `AddAsset`, `SetTheme` (theme choice, library apply, Import theme…), `SetLayout`, `SetAll`, paste and custom asset properties: refused with the asset-cap notice, nothing changes. GD-1: every command is refused while preserving. GD-6: files pass `from_file` before any command.
- Pins: Step 5.1's `edit_apply.rs`, Step 6.6's `design_clipboard.rs` and Step 8.7's `library_import.rs` add no asset beyond the cap and replace no document with stray assets; their assertions hold.

### Step 9.6 — Theme editor panel and the Colours tab

- Builds: `design::theme_editor` draws S-08 as a floating 300 px panel at the right below the toolbar (height: window − 56 px), opened by the toolbar's Theme button (now enabled) and staying open while editing: a name field (1–64 characters) and "Save theme"; tabs Colours, Type, Surfaces, Shape; × closes and keeps the edited theme. `theme_editor::colours` pins the contrast summary on top: the six pairs of text and text-muted on background, surface and surface-raised with "{x.x}:1" (R-104), each below 4.5 in tool warning with `ICON_WARNING` (R-105); then Base roles, Accents 1–8 and State roles, each with a swatch and a hex field (`#rrggbb` or `#rrggbbaa`); a swatch opens `egui::color_picker::color_picker_color32` in a popup. Each finished edit (↩ or focus loss in a field, release in the picker) is one `SetTheme`, drawn on the next frame (R-103).
- Files: `crates/mutable-gui/src/design/theme_editor/mod.rs`, `crates/mutable-gui/src/design/theme_editor/colours.rs`, `crates/mutable-gui/src/design/toolbar.rs`, `crates/mutable-gui/tests/theme_editor_colours.rs`
- Libraries: egui, egui_material_icons
- Commands: `cargo test -p mutable-gui --test theme_editor_colours`
- Tests: `crates/mutable-gui/tests/theme_editor_colours.rs` (R-103: changing accent-1 redraws accent-1 elements on the next frame; R-104: black text on white background shows "21.0:1"; R-105: #777777 on white is marked and #767676 is not; one undo restores the previous colour)
- Gate: G9.6 — `cargo test -p mutable-gui --test theme_editor_colours` exits 0
- Requirements: R-103, R-104, R-105
- Screens: none

### Step 9.7 — Type tab and image assets

- Builds: `theme_editor::type_tab` has dropdowns for the body, heading and value typefaces listing the four built-in fonts and the instance's font assets (choice 30); the asset list (icon, name, size, a remove button enabled only when unreferenced); a meter "{x.x} of 4 MiB"; "Add font…" and "Add image…" open the file dialog and go through `edit::assets::from_file` and `AddAsset`. The inspector's image asset field gains "Add image…", committing `Batch[AddAsset, ReplaceElement]`.
- Files: `crates/mutable-gui/src/design/theme_editor/type_tab.rs`, `crates/mutable-gui/src/design/inspector/settings.rs`, `crates/mutable-gui/tests/theme_editor_type.rs`
- Libraries: egui, skrifa
- Commands: `cargo test -p mutable-gui --test theme_editor_type`
- Tests: `crates/mutable-gui/tests/theme_editor_type.rs` (adding Inter-Medium through a fake dialog lists it as "Inter Medium" and choosing it as heading applies; R-122 and R-123 through the buttons raise their notices)
- Gate: G9.7 — `cargo test -p mutable-gui --test theme_editor_type` exits 0
- Requirements: R-100, R-122, R-123
- Screens: none

### Step 9.8 — Surfaces tab

- Builds: `theme_editor::surfaces`: a segmented surface choice (Canvas, Panel, Control, Display), a segmented fill type (Solid, Gradient, Grain, Image), a preview strip, and per type: a role dropdown (solid); From and To role dropdowns and an angle 0–360 (gradient); a role dropdown and an amount slider 0–1 (grain); a PNG asset dropdown (image). Each edit is one `SetTheme`.
- Files: `crates/mutable-gui/src/design/theme_editor/surfaces.rs`, `crates/mutable-gui/tests/theme_editor_surfaces.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test theme_editor_surfaces`
- Tests: `crates/mutable-gui/tests/theme_editor_surfaces.rs` (setting Panel to a gradient from surface-raised to surface at 160° redraws panels with it; undo restores solid)
- Gate: G9.8 — `cargo test -p mutable-gui --test theme_editor_surfaces` exits 0
- Requirements: R-101
- Screens: none

### Step 9.9 — Shape tab

- Builds: `theme_editor::shape`: knob style (Arc, Pointer, Filled), corner radius 0–64, border 0–8, track 1–24, handle 4–48 as drag values; each finished edit is one `SetTheme`.
- Files: `crates/mutable-gui/src/design/theme_editor/shape.rs`, `crates/mutable-gui/tests/theme_editor_shape.rs`
- Libraries: egui
- Commands: `cargo test -p mutable-gui --test theme_editor_shape`
- Tests: `crates/mutable-gui/tests/theme_editor_shape.rs` (R-102: setting knob style Pointer redraws knobs without an override as pointer while an element overriding Filled stays filled)
- Gate: G9.9 — `cargo test -p mutable-gui --test theme_editor_shape` exits 0
- Requirements: R-102
- Screens: none

### Step 9.10 — Saving a theme from the editor

- Builds: "Save theme" opens the S-10 save dialog prefilled with the theme's name; a built-in theme's name is reserved and the dialog asks for another name (R-106); an existing name asks to replace (R-127); a saved theme is listed under Themes in S-09 for every plugin (R-128).
- Files: `crates/mutable-gui/src/design/theme_editor/mod.rs`, `crates/mutable-gui/tests/theme_editor_save.rs`
- Libraries: tempfile
- Commands: `cargo test -p mutable-gui --test theme_editor_save`
- Tests: `crates/mutable-gui/tests/theme_editor_save.rs` (R-106: saving an edited Studio Dark under "Studio Dark" asks for another name and the built-in is unchanged; saving as "Night Ink" lists it in the themes tab)
- Gate: G9.10 — `cargo test -p mutable-gui --test theme_editor_save` exits 0
- Requirements: R-106, R-128
- Screens: none
- Guards: GD-5 applies (reserved built-in names). GD-1 and GD-2: the editor exists only in design mode.

### Step 9.11 — S-08 theme editor screen

- Builds: `examples/reference-plugin/tests/screen_s08.rs` applies a theme "Night Ink" with the roles of `.theme-night-ink` in `design/ui/S-08-theme--surfaces.html` (the other roles from Studio Dark), opens the theme editor on the reference default, and snapshots `S-08-theme` (Colours, with its failing pair marked), `S-08-theme--type` (Inter-Medium added as a font asset and set as heading), `S-08-theme--surfaces` (Panel gradient from surface-raised to surface at 160°), `S-08-theme--shape`. `design/UI.md` S-08 gets `Built: examples/reference-plugin/tests/snapshots/S-08-theme.png`.
- Files: `examples/reference-plugin/tests/screen_s08.rs`, `examples/reference-plugin/tests/snapshots/S-08-theme.png`, `examples/reference-plugin/tests/snapshots/S-08-theme--type.png`, `examples/reference-plugin/tests/snapshots/S-08-theme--surfaces.png`, `examples/reference-plugin/tests/snapshots/S-08-theme--shape.png`, `design/UI.md`
- Libraries: egui_kittest
- Commands: `cargo test -p mutable-gui-reference --test screen_s08 && python3 tools/devpipe/run.py ui compare S-08`
- Tests: `examples/reference-plugin/tests/screen_s08.rs`
- Gate: G9.11 — `cargo test -p mutable-gui-reference --test screen_s08 && python3 tools/devpipe/run.py ui compare S-08` exits 0
- Requirements: R-104, R-105
- Screens: S-08

### Step 9.12 — Design-mode screens with every tool enabled

- Builds: the S-04 to S-07 pictures are regenerated with the toolbar's Theme button enabled; every toolbar button of S-04 now works.
- Files: `examples/reference-plugin/tests/snapshots/S-04-workspace.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace--arrange.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace--custom.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace--unknown.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace--peek.png`, `examples/reference-plugin/tests/snapshots/S-04-workspace--small.png`, `examples/reference-plugin/tests/snapshots/S-05-picker.png`, `examples/reference-plugin/tests/snapshots/S-05-picker--tap.png`, `examples/reference-plugin/tests/snapshots/S-06-pages.png`, `examples/reference-plugin/tests/snapshots/S-07-unbound.png`
- Libraries: egui_kittest
- Commands: `UPDATE_SNAPSHOTS=1 cargo test -p mutable-gui-reference --test screen_s04 --test screen_s05 --test screen_s06 --test screen_s07 && cargo test -p mutable-gui-reference --test screen_s04 --test screen_s05 --test screen_s06 --test screen_s07 && python3 tools/devpipe/run.py ui compare S-04`
- Tests: `examples/reference-plugin/tests/screen_s04.rs`, `examples/reference-plugin/tests/screen_s05.rs`, `examples/reference-plugin/tests/screen_s06.rs`, `examples/reference-plugin/tests/screen_s07.rs`
- Gate: G9.12 — `cargo test -p mutable-gui-reference --test screen_s04 --test screen_s05 --test screen_s06 --test screen_s07 && python3 tools/devpipe/run.py ui compare S-04 && python3 tools/devpipe/run.py ui compare S-05 && python3 tools/devpipe/run.py ui compare S-06 && python3 tools/devpipe/run.py ui compare S-07` exits 0
- Requirements: R-087
- Screens: S-04, S-05, S-06, S-07
- Pins: the pictures of Steps 5.19–5.22, 6.7, 6.8, 7.12 and 8.14 show the toolbar, whose Theme button is now enabled; they are regenerated here and their tests pass unchanged.

### Step 9.13 — Documents at Phase 9 truth

- Builds: `README.md` (theme editing, fonts and images, the 4 MiB cap, contrast warnings), `docs/ARCHITECTURE.md` (I-09 and I-21 with how they are kept), `CHANGELOG.md`.
- Files: `README.md`, `docs/ARCHITECTURE.md`, `CHANGELOG.md`
- Libraries: none
- Commands: `grep -q "4 MiB" README.md && grep -q "I-21" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md CHANGELOG.md`
- Tests: none
- Gate: G9.13 — `grep -q "4 MiB" README.md && grep -q "I-21" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md CHANGELOG.md` exits 0
- Requirements: none
- Screens: none

### Step 9.14 — Phase 9 check sheet

- Builds: `docs/qa/phase-09.md` lists, each with "Result: not run": (1) Flow 3: S-02 Theme → High Contrast applies at once; S-04 → Theme → change accent-1, a gradient panel surface, a font asset as heading and the knob style, each live and undoable; Save theme → it appears under Themes in a second plugin instance's library; (2) adding a JPEG as an image raises the format notice; a font over the cap raises the cap notice; (3) the pictures `.tickets/.work/ui-compare/S-08.png` and `S-04.png` to `S-07.png` match their mockups. It ends with "Signed off: no".
- Files: `docs/qa/phase-09.md`
- Libraries: none
- Commands: `grep -q "^Signed off: no" docs/qa/phase-09.md`
- Tests: none
- Gate: G9.14 — `grep -q "^Signed off: no" docs/qa/phase-09.md` exits 0
- Requirements: none
- Screens: none

### Step 9.15 — [OWNER] Phase 9 host and screen check

- Builds: the owner performs the items of `docs/qa/phase-09.md`, records each result and signs off.
- Files: `docs/qa/phase-09.md`
- Libraries: Bitwig Studio
- Commands: `python3 tools/devpipe/run.py ui compare S-08`
- Tests: none
- Gate: G9.15 — `grep -q "^Signed off: yes" docs/qa/phase-09.md` exits 0
- Requirements: R-103
- Screens: S-08, S-04, S-05, S-06, S-07

**Exit demo:** Following `README.md` and `docs/RUNBOOK.md`: in Bitwig, open the theme editor, recolour accent-1 and watch every accent-1 element follow, give panels a gradient, add a font file as the heading face, see a failing contrast pair marked, save the theme as "Night Ink" and pick it from another Reference FX instance's Theme menu.

## Phase 10 — Version 1 gate

**Goal:** The owner proves version 1 on macOS 26.7.1 with Bitwig Studio 5.3.13 by following the documents alone, and the handoff documents describe exactly what was built.

### Step 10.1 — Version 1 checklist

- Builds: `docs/qa/bitwig-checklist.md` lists, each with "Result: not run": (1) installation of the release bundle and its scan by Bitwig; (2) the D-04 demonstration: design mode, a three-knob performance page, a theme, project save, reopen identical, export the layout, import it into a second instance; (3) R-097: adding, binding and deleting a knob during playback with no dropout and no plugin reload; (4) every built-in control by mouse, Shift, long press, right-click and keyboard, following automation and showing modulation; (5) displays following audio, and an idle static page leaving Bitwig's plugin CPU at its idle level; (6) window scale limits, reopening at the last size and page, opening in perform mode; (7) library save, apply, export, import, delete, defaults, suite theme, developer default, read-only folder; (8) copy with ⌘C and paste with ⌘V between two instances; (9) High Contrast with the focus outline visible on every control; (10) the Transfer curve; (11) `sh tools/validate-clap.sh` clean; (12) VST3: no VST3 bundle is built, because nice-plug's VST3 export needs VST3-specific code (recorded, not fixed). It ends with "Signed off: no".
- Files: `docs/qa/bitwig-checklist.md`
- Libraries: none
- Commands: `grep -c "^Result: not run" docs/qa/bitwig-checklist.md | grep -q "^12$" && grep -q "^Signed off: no" docs/qa/bitwig-checklist.md`
- Tests: none
- Gate: G10.1 — `grep -c "^Result: not run" docs/qa/bitwig-checklist.md | grep -q "^12$"` exits 0
- Requirements: R-097
- Screens: none

### Step 10.2 — Release documents

- Builds: `README.md` is the complete adoption guide (builder with embedded default, taps, the persisted field, menu corner, design-mode switch, custom kinds) and user guide; `docs/ARCHITECTURE.md` lists every invariant I-01 to I-21 with the test or review that keeps it and every difference from `design/` (the frame signature, ⌘V-only paste, `fixtures` checked by tests); `docs/RUNBOOK.md` gains "Release and rollback" (the release is the commit tagged `v1.0.0` and the bundle built from it; rollback is the previous tag's bundle); `docs/TESTING.md` gains the manual checks table naming every `docs/qa/` sheet; `CHANGELOG.md` moves Unreleased under "## 1.0.0 (version 1 gate)".
- Files: `README.md`, `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, `docs/TESTING.md`, `CHANGELOG.md`
- Libraries: none
- Commands: `grep -q "I-21" docs/ARCHITECTURE.md && grep -q "v1.0.0" docs/RUNBOOK.md && grep -q "bitwig-checklist" docs/TESTING.md && grep -q "## 1.0.0" CHANGELOG.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/RUNBOOK.md docs/TESTING.md CHANGELOG.md`
- Tests: none
- Gate: G10.2 — `grep -q "I-21" docs/ARCHITECTURE.md && grep -q "v1.0.0" docs/RUNBOOK.md && grep -q "bitwig-checklist" docs/TESTING.md && grep -q "## 1.0.0" CHANGELOG.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/RUNBOOK.md docs/TESTING.md CHANGELOG.md` exits 0
- Requirements: none
- Screens: none

### Step 10.3 — [OWNER] Version 1 sign-off

- Builds: the owner runs every item of `docs/qa/bitwig-checklist.md` following `README.md` and `docs/RUNBOOK.md` only, records each result, and signs off; a failed item becomes a feature or fix ticket before sign-off.
- Files: `docs/qa/bitwig-checklist.md`
- Libraries: Bitwig Studio
- Commands: `cargo xtask bundle mutable-gui-reference --release && sh tools/validate-clap.sh`
- Tests: none
- Gate: G10.3 — `grep -q "^Signed off: yes" docs/qa/bitwig-checklist.md` exits 0
- Requirements: R-097, R-110
- Screens: none

**Exit demo:** Following `README.md` and `docs/RUNBOOK.md` only, the owner performs the D-04 demonstration in Bitwig Studio 5.3.13 on macOS 26.7.1: enter design mode, build a three-knob performance page, theme it, save the project, reopen it identical, export the layout and import it into a second instance.

## Gate index

| Gate | Phase | Command |
|---|---|---|
| G0.1 | 0 | `git check-ignore -q target && git check-ignore -q crates/mutable-gui/tests/snapshots/a.new.png` |
| G0.2 | 0 | `sh -n setup-prerequisites.sh && sh -n tools/check-env.sh` |
| G0.3 | 0 | `sh tools/check-env.sh` |
| G0.4 | 0 | `cargo build -p mutable-gui && cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings` |
| G0.5 | 0 | `cargo test -p mutable-gui --test harness_smoke` |
| G0.6 | 0 | `cargo test -p mutable-gui --test prop_smoke --test alloc_smoke && cargo test -p mutable-gui --release --test perf_smoke perf_ && cargo bench -p mutable-gui --bench smoke --no-run` |
| G0.7 | 0 | `cargo test -p mutable-gui-nice --test smoke` |
| G0.8 | 0 | `cargo build -p xtask` |
| G0.9 | 0 | `cargo xtask bundle mutable-gui-reference --release && sh tools/validate-clap.sh` |
| G0.10 | 0 | `(cd crates/mutable-gui/assets && shasum -a 256 -c SHA256SUMS)` |
| G0.11 | 0 | `python3 tools/check-stack.py` |
| G0.12 | 0 | `test -x .githooks/pre-commit.project && .githooks/pre-commit.project` |
| G0.13 | 0 | `grep -q "ubuntu-24.04" .github/workflows/ci.yml && grep -q "windows-2022" .github/workflows/ci.yml && grep -q "cargo test --workspace" .github/workflows/ci.yml` |
| G0.14 | 0 | `grep -q "## Quick start" README.md && grep -q "## Unreleased" CHANGELOG.md && ! grep -q "[<][<]" README.md CHANGELOG.md` |
| G0.15 | 0 | `grep -q "## 4. Invariants in force" docs/ARCHITECTURE.md && grep -q "## 2. Build, run, install" docs/RUNBOOK.md && grep -q "## 2. Commands" docs/TESTING.md && ! grep -q "[<][<]" docs/ARCHITECTURE.md docs/RUNBOOK.md docs/TESTING.md` |
| G1.1 | 1 | `cargo test -p mutable-gui --test model_layout` |
| G1.2 | 1 | `cargo test -p mutable-gui --test model_theme` |
| G1.3 | 1 | `cargo test -p mutable-gui --test doc_instance` |
| G1.4 | 1 | `cargo test -p mutable-gui --test fake_params` |
| G1.5 | 1 | `cargo test -p mutable-gui --test generate` |
| G1.6 | 1 | `cargo test -p mutable-gui --test theme_builtin` |
| G1.7 | 1 | `cargo test -p mutable-gui --test theme_fonts` |
| G1.8 | 1 | `cargo test -p mutable-gui --test render_canvas` |
| G1.9 | 1 | `cargo test -p mutable-gui --test render_view` |
| G1.10 | 1 | `cargo test -p mutable-gui --test render_knob` |
| G1.11 | 1 | `cargo test -p mutable-gui --test render_switch_selector` |
| G1.12 | 1 | `cargo test -p mutable-gui --test render_decor` |
| G1.13 | 1 | `cargo test -p mutable-gui --test persist_cell` |
| G1.14 | 1 | `cargo test -p mutable-gui --test perform_gesture` |
| G1.15 | 1 | `cargo test -p mutable-gui --test perform_rules` |
| G1.16 | 1 | `cargo test -p mutable-gui --test editor_perform` |
| G1.17 | 1 | `cargo test -p mutable-gui --test editor_defaults` |
| G1.18 | 1 | `cargo test -p mutable-gui --test editor_window` |
| G1.19 | 1 | `cargo test -p mutable-gui --test chrome_menu_button` |
| G1.20 | 1 | `cargo test -p mutable-gui --test chrome_editor_menu` |
| G1.21 | 1 | `cargo test -p mutable-gui-nice --test params` |
| G1.22 | 1 | `cargo test -p mutable-gui-nice --test persist` |
| G1.23 | 1 | `cargo test -p mutable-gui-nice --test builder` |
| G1.24 | 1 | `cargo test -p mutable-gui-reference --test params` |
| G1.25 | 1 | `cargo test -p mutable-gui-reference --test dsp` |
| G1.26 | 1 | `cargo test -p mutable-gui-reference --test round_trip && cargo xtask bundle mutable-gui-reference --release && sh tools/validate-clap.sh` |
| G1.27 | 1 | `cargo test -p mutable-gui-reference --test screen_s13 && python3 tools/devpipe/run.py ui compare S-13` |
| G1.28 | 1 | `grep -q "I-03" docs/ARCHITECTURE.md && grep -q "S-13" docs/TESTING.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/RUNBOOK.md docs/TESTING.md CHANGELOG.md` |
| G1.29 | 1 | `grep -q "^Signed off: no" docs/qa/phase-01.md` |
| G1.30 | 1 | `grep -q "^Signed off: yes" docs/qa/phase-01.md` |
| G2.1 | 2 | `cargo test -p mutable-gui --test doc_validate` |
| G2.2 | 2 | `cargo test -p mutable-gui --test doc_unknown_fields` |
| G2.3 | 2 | `cargo test -p mutable-gui --test doc_migrate` |
| G2.4 | 2 | `cargo test -p mutable-gui --test doc_assets` |
| G2.5 | 2 | `cargo test -p mutable-gui --test doc_package` |
| G2.6 | 2 | `cargo test -p mutable-gui --test doc_elements` |
| G2.7 | 2 | `cargo test -p mutable-gui --test doc_malformed` |
| G2.8 | 2 | `cargo test -p mutable-gui --release --test perf_package_load perf_` |
| G2.9 | 2 | `cargo test -p xtask --test schema_current` |
| G2.10 | 2 | `cargo test -p mutable-gui --test chrome_notices` |
| G2.11 | 2 | `cargo test -p mutable-gui --test editor_embedded` |
| G2.12 | 2 | `cargo test -p xtask --test reference_default_current` |
| G2.13 | 2 | `cargo test -p mutable-gui-reference --test embedded_default --test screen_s13 --test round_trip` |
| G2.14 | 2 | `cargo test -p mutable-gui --test editor_unreadable` |
| G2.15 | 2 | `cargo test -p mutable-gui --test editor_host_load` |
| G2.16 | 2 | `cargo test -p mutable-gui-reference --test round_trip && cargo xtask bundle mutable-gui-reference --release && sh tools/validate-clap.sh` |
| G2.17 | 2 | `grep -q "I-16" docs/ARCHITECTURE.md && grep -q "reference-default" docs/RUNBOOK.md && ! grep -q "[<][<]" docs/ARCHITECTURE.md docs/RUNBOOK.md docs/TESTING.md CHANGELOG.md` |
| G2.18 | 2 | `grep -q "^Signed off: no" docs/qa/phase-02.md` |
| G2.19 | 2 | `grep -q "^Signed off: yes" docs/qa/phase-02.md` |
| G3.1 | 3 | `cargo test -p mutable-gui --test taps_declare` |
| G3.2 | 3 | `cargo test -p mutable-gui --test taps_audio` |
| G3.3 | 3 | `cargo test -p mutable-gui --test taps_scalar` |
| G3.4 | 3 | `cargo test -p mutable-gui --test alloc_taps --test arch_boundaries && cargo test -p mutable-gui --release --test perf_scalar_push perf_` |
| G3.5 | 3 | `cargo test -p mutable-gui --test analysis_spectrum` |
| G3.6 | 3 | `cargo test -p mutable-gui --test analysis_level` |
| G3.7 | 3 | `cargo test -p mutable-gui --test editor_taps` |
| G3.8 | 3 | `cargo test -p mutable-gui --test render_scope` |
| G3.9 | 3 | `cargo test -p mutable-gui --test render_spectrum` |
| G3.10 | 3 | `cargo test -p mutable-gui --test render_meters` |
| G3.11 | 3 | `cargo test -p mutable-gui --test editor_repaint` |
| G3.12 | 3 | `cargo test -p mutable-gui --test editor_displays` |
| G3.13 | 3 | `cargo test -p mutable-gui-reference --test taps` |
| G3.14 | 3 | `cargo test -p mutable-gui-reference --test alloc_process` |
| G3.15 | 3 | `grep -q "declare_audio" README.md && grep -q "I-17" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/TESTING.md CHANGELOG.md` |
| G3.16 | 3 | `grep -q "^Signed off: no" docs/qa/phase-03.md` |
| G3.17 | 3 | `grep -q "^Signed off: yes" docs/qa/phase-03.md` |
| G3.18 | 3 | `cargo test -p mutable-gui --test taps_events` |
| G3.19 | 3 | `cargo test -p mutable-gui --test taps_snapshot --test alloc_taps --test arch_boundaries` |
| G4.1 | 4 | `cargo test -p mutable-gui --test perform_fader` |
| G4.2 | 4 | `cargo test -p mutable-gui --test perform_fine` |
| G4.3 | 4 | `cargo test -p mutable-gui --test perform_xy` |
| G4.4 | 4 | `cargo test -p mutable-gui --test perform_macro` |
| G4.5 | 4 | `cargo test -p mutable-gui --test perform_menu` |
| G4.6 | 4 | `cargo test -p mutable-gui --test render_image` |
| G4.7 | 4 | `cargo test -p mutable-gui --test editor_controls` |
| G4.8 | 4 | `cargo test -p mutable-gui --test perform_unbound` |
| G4.9 | 4 | `cargo test -p mutable-gui --test perform_control_menu` |
| G4.10 | 4 | `cargo test -p mutable-gui --test perform_value_field` |
| G4.11 | 4 | `cargo test -p mutable-gui --test perform_keyboard` |
| G4.12 | 4 | `cargo test -p mutable-gui-reference --test screen_s01 && python3 tools/devpipe/run.py ui compare S-01` |
| G4.13 | 4 | `cargo test -p mutable-gui-reference --test screen_s03 && python3 tools/devpipe/run.py ui compare S-03` |
| G4.14 | 4 | `cargo test -p mutable-gui-reference --test screen_s12` |
| G4.15 | 4 | `cargo test -p mutable-gui --release --test perf_frame perf_` |
| G4.16 | 4 | `cargo test -p mutable-gui-reference --release --test perf_editor_open perf_` |
| G4.17 | 4 | `grep -q "I-04" docs/ARCHITECTURE.md && grep -q "long press" README.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/TESTING.md CHANGELOG.md` |
| G4.18 | 4 | `grep -q "^Signed off: no" docs/qa/phase-04.md` |
| G4.19 | 4 | `grep -q "^Signed off: yes" docs/qa/phase-04.md` |
| G4.20 | 4 | `cargo test -p mutable-gui --test editor_relevance` |
| G4.21 | 4 | `cargo test -p mutable-gui --test render_dimmed --test editor_perform` |
| G4.22 | 4 | `cargo test -p mutable-gui-reference --test relevance && cargo test -p mutable-gui --release --test perf_frame perf_` |
| G4.23 | 4 | `cargo test -p mutable-gui --test perform_description --test perform_control_menu --test fake_params` |
| G4.24 | 4 | `cargo test -p mutable-gui-nice --test describe && cargo test -p mutable-gui-reference --test screen_s03` |
| G4.25 | 4 | `grep -q "Turn it down to darken the sound" design/ui/S-03-control-menu.html && python3 tools/devpipe/run.py ui compare S-03` |
| G5.1 | 5 | `cargo test -p mutable-gui --test edit_apply` |
| G5.2 | 5 | `cargo test -p mutable-gui --test edit_undo` |
| G5.3 | 5 | `cargo test -p mutable-gui --test undo_memory` |
| G5.4 | 5 | `cargo test -p mutable-gui --test design_mode` |
| G5.5 | 5 | `cargo test -p mutable-gui --test design_select` |
| G5.6 | 5 | `cargo test -p mutable-gui --test design_move` |
| G5.7 | 5 | `cargo test -p mutable-gui --test design_handles` |
| G5.8 | 5 | `cargo test -p mutable-gui --test design_keys` |
| G5.9 | 5 | `cargo test -p mutable-gui --test design_toolbar` |
| G5.10 | 5 | `cargo test -p mutable-gui --test design_palette` |
| G5.11 | 5 | `cargo test -p mutable-gui --test design_inspector` |
| G5.12 | 5 | `cargo test -p mutable-gui --test design_inspector_look` |
| G5.13 | 5 | `cargo test -p mutable-gui --test design_inspector_lists` |
| G5.14 | 5 | `cargo test -p mutable-gui --test design_picker` |
| G5.15 | 5 | `cargo test -p mutable-gui --release --test perf_picker perf_` |
| G5.16 | 5 | `cargo test -p mutable-gui --test design_tap_picker` |
| G5.17 | 5 | `cargo test -p mutable-gui --test design_pages` |
| G5.18 | 5 | `cargo test -p mutable-gui --test design_unbound` |
| G5.19 | 5 | `cargo test -p mutable-gui-reference --test screen_s04 && python3 tools/devpipe/run.py ui compare S-04` |
| G5.20 | 5 | `cargo test -p mutable-gui-reference --test screen_s05 && python3 tools/devpipe/run.py ui compare S-05` |
| G5.21 | 5 | `cargo test -p mutable-gui-reference --test screen_s06 && python3 tools/devpipe/run.py ui compare S-06` |
| G5.22 | 5 | `cargo test -p mutable-gui-reference --test screen_s07 && python3 tools/devpipe/run.py ui compare S-07` |
| G5.23 | 5 | `cargo test -p mutable-gui-reference --test render_identical` |
| G5.24 | 5 | `grep -q "⌘E" README.md && grep -q "render_identical" docs/TESTING.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/TESTING.md CHANGELOG.md` |
| G5.25 | 5 | `grep -q "^Signed off: no" docs/qa/phase-05.md` |
| G5.26 | 5 | `grep -q "^Signed off: yes" docs/qa/phase-05.md` |
| G6.1 | 6 | `cargo test -p mutable-gui --test design_arrange` |
| G6.2 | 6 | `cargo test -p mutable-gui --test design_zorder` |
| G6.3 | 6 | `cargo test -p mutable-gui --test design_group` |
| G6.4 | 6 | `cargo test -p mutable-gui --test design_group_resize` |
| G6.5 | 6 | `cargo test -p mutable-gui --test design_duplicate` |
| G6.6 | 6 | `cargo test -p mutable-gui --test design_clipboard` |
| G6.7 | 6 | `cargo test -p mutable-gui --test design_arrange_menu && cargo test -p mutable-gui-reference --test screen_s04 --test screen_s05 --test screen_s06 --test screen_s07` |
| G6.8 | 6 | `cargo test -p mutable-gui-reference --test screen_s04` |
| G6.9 | 6 | `grep -q "⌘V" README.md && grep -q "⌘V" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md CHANGELOG.md` |
| G6.10 | 6 | `grep -q "^Signed off: no" docs/qa/phase-06.md` |
| G6.11 | 6 | `grep -q "^Signed off: yes" docs/qa/phase-06.md` |
| G7.1 | 7 | `cargo test -p mutable-gui --test custom_registry` |
| G7.2 | 7 | `cargo test -p mutable-gui --test doc_custom --test doc_instance --test doc_package --test doc_elements` |
| G7.3 | 7 | `cargo test -p mutable-gui --test custom_migrate` |
| G7.4 | 7 | `cargo test -p mutable-gui --test custom_draw` |
| G7.5 | 7 | `cargo test -p mutable-gui --test custom_input` |
| G7.6 | 7 | `cargo test -p mutable-gui --test custom_taps` |
| G7.7 | 7 | `cargo test -p mutable-gui --test custom_unknown` |
| G7.8 | 7 | `cargo test -p mutable-gui --test custom_palette --test design_palette` |
| G7.9 | 7 | `cargo test -p mutable-gui --test custom_inspector` |
| G7.10 | 7 | `cargo test -p mutable-gui --test custom_unbound --test design_unbound` |
| G7.11 | 7 | `cargo test -p mutable-gui-reference --test transfer_curve` |
| G7.12 | 7 | `cargo test -p mutable-gui-reference --test screen_s04 --test screen_s12 && python3 tools/devpipe/run.py ui compare S-12` |
| G7.13 | 7 | `grep -q "register_kind" README.md && grep -q "I-20" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md CHANGELOG.md` |
| G7.14 | 7 | `grep -q "^Signed off: no" docs/qa/phase-07.md` |
| G7.15 | 7 | `grep -q "^Signed off: yes" docs/qa/phase-07.md` |
| G7.16 | 7 | `cargo test -p mutable-gui --test custom_tap_kinds --test custom_taps --test editor_taps` |
| G7.17 | 7 | `cargo test -p mutable-gui --test custom_tap_picker --test design_tap_picker` |
| G7.18 | 7 | `cargo test -p mutable-gui --test custom_dimmed` |
| G7.19 | 7 | `cargo test -p mutable-gui --test custom_plugin_state && grep -q "Plugin-owned state" README.md && grep -q "D-51" .claude/agents/runtime-mutable-gui-reviewer.md` |
| G8.1 | 8 | `cargo test -p mutable-gui --test library_storage` |
| G8.2 | 8 | `cargo test -p mutable-gui --test library_paths` |
| G8.3 | 8 | `cargo test -p mutable-gui --test library_listing` |
| G8.4 | 8 | `cargo test -p mutable-gui --test library_save` |
| G8.5 | 8 | `cargo test -p mutable-gui --test library_defaults --test editor_defaults --test editor_embedded --test editor_unreadable` |
| G8.6 | 8 | `cargo test -p mutable-gui --test library_export` |
| G8.7 | 8 | `cargo test -p mutable-gui --test library_import` |
| G8.8 | 8 | `cargo test -p mutable-gui --test editor_discard --test editor_unreadable` |
| G8.9 | 8 | `cargo test -p mutable-gui --test chrome_submenus --test design_mode` |
| G8.10 | 8 | `cargo test -p mutable-gui --test design_library_panel` |
| G8.11 | 8 | `cargo test -p mutable-gui --test design_dialogs` |
| G8.12 | 8 | `cargo test -p mutable-gui-reference --test screen_s02 && python3 tools/devpipe/run.py ui compare S-02` |
| G8.13 | 8 | `cargo test -p mutable-gui-reference --test screen_s09 && python3 tools/devpipe/run.py ui compare S-09` |
| G8.14 | 8 | `cargo test -p mutable-gui-reference --test screen_s10 --test screen_s04 --test screen_s05 --test screen_s06 --test screen_s07 && python3 tools/devpipe/run.py ui compare S-10` |
| G8.15 | 8 | `cargo test -p mutable-gui-reference --test screen_s11 && python3 tools/devpipe/run.py ui compare S-11` |
| G8.16 | 8 | `grep -q ".default.mgui" docs/RUNBOOK.md && grep -q "I-10" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/RUNBOOK.md docs/ARCHITECTURE.md CHANGELOG.md` |
| G8.17 | 8 | `grep -q "^Signed off: no" docs/qa/phase-08.md` |
| G8.18 | 8 | `grep -q "^Signed off: yes" docs/qa/phase-08.md` |
| G9.1 | 9 | `cargo test -p mutable-gui --test render_fill && cargo test -p mutable-gui-reference --test screen_s01 --test screen_s12` |
| G9.2 | 9 | `cargo test -p mutable-gui --test theme_font_assets --test theme_fonts` |
| G9.3 | 9 | `cargo test -p mutable-gui --test theme_recolour --test editor_perform` |
| G9.4 | 9 | `cargo test -p mutable-gui --test theme_shape && cargo test -p mutable-gui-reference --test screen_s12` |
| G9.5 | 9 | `cargo test -p mutable-gui --test edit_assets --test edit_apply --test design_clipboard --test library_import` |
| G9.6 | 9 | `cargo test -p mutable-gui --test theme_editor_colours` |
| G9.7 | 9 | `cargo test -p mutable-gui --test theme_editor_type` |
| G9.8 | 9 | `cargo test -p mutable-gui --test theme_editor_surfaces` |
| G9.9 | 9 | `cargo test -p mutable-gui --test theme_editor_shape` |
| G9.10 | 9 | `cargo test -p mutable-gui --test theme_editor_save` |
| G9.11 | 9 | `cargo test -p mutable-gui-reference --test screen_s08 && python3 tools/devpipe/run.py ui compare S-08` |
| G9.12 | 9 | `cargo test -p mutable-gui-reference --test screen_s04 --test screen_s05 --test screen_s06 --test screen_s07 && python3 tools/devpipe/run.py ui compare S-04 && python3 tools/devpipe/run.py ui compare S-05 && python3 tools/devpipe/run.py ui compare S-06 && python3 tools/devpipe/run.py ui compare S-07` |
| G9.13 | 9 | `grep -q "4 MiB" README.md && grep -q "I-21" docs/ARCHITECTURE.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md CHANGELOG.md` |
| G9.14 | 9 | `grep -q "^Signed off: no" docs/qa/phase-09.md` |
| G9.15 | 9 | `grep -q "^Signed off: yes" docs/qa/phase-09.md` |
| G10.1 | 10 | `grep -c "^Result: not run" docs/qa/bitwig-checklist.md \| grep -q "^12$"` |
| G10.2 | 10 | `grep -q "I-21" docs/ARCHITECTURE.md && grep -q "v1.0.0" docs/RUNBOOK.md && grep -q "bitwig-checklist" docs/TESTING.md && grep -q "## 1.0.0" CHANGELOG.md && ! grep -q "[<][<]" README.md docs/ARCHITECTURE.md docs/RUNBOOK.md docs/TESTING.md CHANGELOG.md` |
| G10.3 | 10 | `grep -q "^Signed off: yes" docs/qa/bitwig-checklist.md` |
