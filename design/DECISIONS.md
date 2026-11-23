# Decisions: mutable-gui

Numbered and append-only. An ACCEPTED decision changes only through a new decision that
supersedes it, written as PROPOSED and ratified by the owner before any code follows.

## D-01 — A framework-neutral core with one nice-plug adapter

Status: ACCEPTED
Date: 2026-11-22
Context: The library must sit inside Rust CLAP plugins. Options were nih-plug (the owner's
grain·ai uses it at a git revision; upstream unchanged since 2026-09-03; its egui adapter
pins egui 0.31), nice-plug 0.4.2 (the community successor on crates.io, ISC, CLAP and VST3,
nice-plug-egui 0.6.0 on egui 0.37), clack 0.2.0 (raw CLAP bindings, every adopter writes CLAP
glue), or two adapters at once.
Decision: The core crate knows no plugin framework; one adapter crate targets nice-plug 0.4.2
in version 1. Other adapters may follow without changing the core.
Consequences: Adopters use nice-plug. grain·ai can adopt the library only after migrating from
nih-plug to nice-plug. The core's `ParamSource` trait must be enough for a later clack
adapter.

## D-02 — egui 0.37 renders the interface

Status: ACCEPTED
Date: 2026-11-22
Context: Candidates were egui (immediate mode, used by grain·ai), iced (nice-plug-iced 0.5,
retained, Elm-style) and vizia (CSS stylesheets reloadable at runtime, about 7,000 downloads,
no nice-plug adapter on crates.io).
Decision: egui 0.37.0 through nice-plug-egui 0.6.0 and egui-baseview 0.9.0. Every element is
custom-painted; theming is the library's own engine.
Consequences: The layout document is the only interface state and each frame draws it, so
design-mode edits need no widget tree rebuild. No stylesheet language comes for free; theming
is built here.

## D-03 — Audio safety first, layout safety second

Status: ACCEPTED
Date: 2026-11-22
Context: The two properties that must never be compromised, and their order when they
conflict.
Decision: P1: the library never allocates, locks or waits on the audio thread, and the audio
output is bit-identical whether the editor is closed, open or in design mode. P2: a user's
layout is never lost silently. P1 outranks P2; P2 outranks every interface feature.
Consequences: Invariants I-01–I-03 and I-07, I-08, I-10, I-16 exist to keep these; a feature
that needs audio-thread work beyond a tap push is out of version 1.

## D-04 — Version 1 is proven by a reference plugin in this repository

Status: ACCEPTED
Date: 2026-11-22
Context: Version 1 could be demonstrated with a purpose-built plugin, by porting grain·ai, or
both.
Decision: A nice-plug CLAP reference plugin in `examples/reference-plugin/` with about 60
parameters in groups and signal taps; in Bitwig on the owner's Mac the owner enters design
mode, builds a three-knob performance page, themes it, saves the project, reopens it
identical, exports the layout and imports it into a second instance.
Consequences: grain·ai adoption is a separate project after version 1.

## D-05 — macOS and Bitwig gate version 1; CLAP only

Status: ACCEPTED
Date: 2026-11-22
Context: The owner develops on macOS 26.7.1 arm64 with Bitwig Studio 5.3.13 and has no
Windows machine on record; the Arch Linux box is a later portability check for grain·ai.
Decision: macOS arm64, CLAP, Bitwig are the gate. Linux x86_64 (X11) and Windows x86_64
compile and pass non-host tests in CI, best-effort. VST3 is whatever nice-plug produces
without VST3-specific work.
Consequences: Host bugs seen only on Linux or Windows are recorded, not blocking.

## D-06 — Fixed canvas per layout with uniform scaling

Status: ACCEPTED
Date: 2026-11-22
Context: Elements could be placed absolutely on a fixed canvas that scales uniformly, or
anchored in a responsive layout that reflows; and a canvas could belong to the layout or to
each page.
Decision: Absolute positions in canvas units on one canvas per layout, snapped to a grid; the
window scales the canvas uniformly with bars when its shape differs.
Consequences: What the user designs is exactly what is drawn on every machine. A touchscreen
shape and a desktop shape are two layouts. No reflow.

## D-07 — Layouts travel in the project; a library holds saved ones

Status: ACCEPTED
Date: 2026-11-22
Context: Instance state could hold the full layout or only a reference to a library file.
Scenario: the project opens on a Mac that has never seen the user's files.
Decision: Each instance saves its full layout, theme and assets in its state; a library
folder holds saved layouts per plugin and themes shared by all plugins; new instances use
the user default, else the developer default.
Consequences: Projects reopen identically anywhere; project size grows with assets (bounded
by D-11).

## D-08 — Macros fan out from the editor

Status: ACCEPTED
Date: 2026-11-22
Context: A macro could be an editor-side control that drives its targets, or a
host-automatable parameter whose mapping the plugin applies even with the editor closed.
Decision: Editor-side fan-out: moving a macro sends gestures to every target; the host records
the targets.
Consequences: No macro automation lane in the host; nothing runs in the plugin for macros, so
P1 is untouched.

## D-09 — Contextual menus are the control menu and the menu element

Status: ACCEPTED
Date: 2026-11-22
Context: nice-plug's CLAP wrapper implements audio-ports, audio-ports-config, gui, latency,
note-ports, params, remote-controls, render, state, tail, thread-check, track-info and
voice-info, and not the context-menu extension, so host parameter menus are unreachable.
Decision: A built-in control menu (reset, type value, fine adjust) on every control, and a
menu element whose items open pages or set stepped parameters. No host menu items.
Consequences: Users cannot author per-control right-click actions in version 1.

## D-10 — Developer-declared signal taps, lock-free, dropping when full

Status: ACCEPTED
Date: 2026-11-22
Context: Displays need data from DSP the library does not own.
Decision: The developer declares named taps of two kinds, audio (1 or 2 channels) and scalar,
before audio starts. Pushes are wait-free and allocation-free; with no reader a push costs
one atomic load; a full buffer drops new data. All analysis runs on the editor thread.
Displays bind to taps by name.
Consequences: Plugins that declare no taps have no live displays. The library never copies
audio by itself.

## D-11 — Fonts and images embedded, at most 4 MiB

Status: ACCEPTED
Date: 2026-11-22
Context: Custom typography and textures could be embedded, procedural only, or absent.
Scenario: 20 instances each carrying a 5 MB theme.
Decision: TrueType/OpenType fonts and PNG images are embedded in instance state and packages,
at most 4 MiB of decoded assets per layout and theme; font licensing is the user's
responsibility.
Consequences: Projects reopen identically; the worst case is 4 MiB per instance.

## D-12 — JSON documents and single-file JSON packages

Status: ACCEPTED
Date: 2026-11-22
Context: Formats considered: JSON, RON, JSON inside a zip.
Decision: Every document is JSON with a format name and an integer schema version; a `.mgui`
package is one JSON file with base64 assets. Bindings name parameters by nice-plug's stable
string id, displays name taps by their developer-given name, packages record the source
plugin's CLAP id, and element ids are stable inside a layout. JSON Schemas are published.
Consequences: One parser; packages are about a third larger than their assets; the frozen
identifiers are listed in the specification's data model.

## D-13 — Broken bindings are kept and flagged

Status: ACCEPTED
Date: 2026-11-22
Context: A plugin update may rename or remove a parameter; a package may come from another
plugin.
Decision: The library never rewrites a user's layout by itself. Controls whose parameter is
missing are drawn unbound and listed for rebinding; cross-plugin imports bind matching ids
and warn; newer schema versions are refused.
Consequences: No developer rename map in version 1; renamed parameters need the user to
rebind.

## D-14 — The full design tool set; developers may switch design mode off

Status: ACCEPTED
Date: 2026-11-22
Context: Scope of design-mode tools, and whether a developer can lock the interface.
Decision: Palette, click, Shift and marquee selection, move, resize, grid snap, align,
distribute, group, ungroup, duplicate, copy and paste across pages and instances, delete,
z-order, inspector, searchable parameter picker, undo and redo of at least 100 steps, reset
to developer default. Design mode is on by default; a developer option removes it, leaving
pages and theme choice.
Consequences: The largest part of version 1 is the designer.

## D-15 — Visual and keyboard accessibility; no screen reader

Status: ACCEPTED
Date: 2026-11-22
Context: egui-baseview 0.9.0 has no AccessKit dependency, so screen readers cannot read the
plugin window.
Decision: Built-in High Contrast theme at 7:1, contrast readout with warnings below 4.5:1, UI
scale 0.5–4.0, full keyboard operation in perform mode. Screen readers are out of version 1.
Consequences: Blind users are not served by version 1.

## D-16 — Elements use colour roles, never raw colours

Status: ACCEPTED
Date: 2026-11-22
Context: Scenario: one knob made red on a dark theme, then the high-contrast theme is chosen.
Decision: Themes define named colour roles; elements pick roles for their colour slots and
may override shape tokens; colour values live only in themes.
Consequences: Theme switches always recolour consistently; a user who wants one red knob
uses an accent role.

## D-17 — Unreadable saved state falls back and is preserved

Status: ACCEPTED
Date: 2026-11-22
Context: Scenario: a project saved with plugin version 3 opened with version 2, or corrupt
state.
Decision: The editor shows the user default or developer default with a notice; the
unreadable bytes are written back unchanged on every save until the user discards them.
Consequences: Opening a project in an older plugin never destroys the newer layout.

## D-18 — Shared themes and a suite default theme

Status: ACCEPTED
Date: 2026-11-22
Context: The pitch asks for consistent visuals across a suite of plugins.
Decision: Themes live in one folder shared by every plugin using the library; the user may
set a suite default theme. New-instance theme order: the plugin's user default, else the
suite default theme, else the developer default. Existing instances never change by
themselves.
Consequences: Plugins from different developers that adopt the library share the user's
themes.

## D-19 — Undo history lives as long as the instance

Status: ACCEPTED
Date: 2026-11-22
Context: Undo could end with the editor window, with the instance, or be saved in the project.
Decision: At least 100 steps, kept while the instance exists, across editor close and reopen;
never saved.
Consequences: `EditorState` lives in the adapter's editor object for the instance's lifetime;
undo memory needs structural sharing (64 MiB bound in the specification).

## D-20 — OpenGL rendering

Status: ACCEPTED
Date: 2026-11-22
Context: nice-plug-egui 0.6.0 defaults to OpenGL and offers wgpu; upstream nih-plug called
egui's wgpu backend unstable; OpenGL is deprecated on macOS but works, and grain·ai uses it in
Bitwig on this Mac.
Decision: The `opengl` feature of nice-plug-egui.
Consequences: A move to wgpu, if macOS removes OpenGL, is confined to the adapter.

## D-21 — Limits on imported packages

Status: ACCEPTED
Date: 2026-11-22
Context: Packages are shared between users and are untrusted.
Decision: File at most 8 MiB, decoded assets at most 4 MiB, at most 64 pages, 2,000 elements,
group nesting 16, text fields 4,096 bytes; fonts and images must decode before anything is
applied; any failure refuses the whole import and changes nothing; packages never hold code.
Consequences: Fixtures and property tests for each limit; unknown fields are refused.

## D-22 — Working name mutable-gui, dual licence, unpublished

Status: ACCEPTED
Date: 2026-11-22
Context: Crate names `mutable-gui` and `mutagui` were free on crates.io on 2026-11-22.
Decision: Crates `mutable-gui` (core) and `mutable-gui-nice` (adapter), package extension
`.mgui`, licence MIT OR Apache-2.0, not published to crates.io in version 1. Crate names may
change before a first publish; the extension and format names are frozen at version 1.
Consequences: The format names in the data model use the prefix `mutable-gui/`.

## D-23 — Adoption through an embedded package, with a generated fallback

Status: ACCEPTED
Date: 2026-11-22
Context: A developer could author the default in design mode and embed the exported package,
describe it in Rust code, or ship nothing.
Decision: The developer designs in a host, exports a package and embeds it; with no package
the library generates a default from the parameter tree. No Rust layout-building API.
Consequences: Adoption is a builder call with the embedded bytes, tap declarations and one
persisted field.

## D-24 — Values, automation and modulation come from the plugin

Status: ACCEPTED
Date: 2026-11-22
Context: How controls show and accept values.
Decision: Value text and typed-value parsing use the plugin's own formatting; controls
follow host automation live; host modulation is drawn as a modulation band from the base
value. Bitwig remote-control pages are out of version 1.
Consequences: The adapter exposes nice-plug's modulated value and formatting through
`ParamSource`.

## D-25 — Performance numbers and test gates

Status: ACCEPTED
Date: 2026-11-22
Context: Quality bars for version 1.
Decision: Frame at most 4 ms for 300 elements at 60 fps; no redraw when idle; editor open
within 250 ms; 4 MiB package load within 200 ms; picker search over 2,000 parameters within
16 ms; scalar push at most 100 ns with zero allocations. Gates: unit tests; proptest round
trips and undo; egui_kittest snapshots and interaction tests; allocation tests over tap
pushes and the reference plugin's process; clap-validator 0.4.1; the owner's Bitwig
checklist; the lint set of the specification.
Consequences: Benchmarks and fixtures are part of the build from the first phase that
touches each area.

## D-26 — Persisted state crosses threads only by atomic swap

Status: ACCEPTED
Date: 2026-11-22 (owner ratified, 2026-11-22: "Ratify all")
Context: nice-plug's CLAP wrapper loads host state on the main thread, but a state set from
the editor through `GuiContext::set_state` while audio is processing is applied on the audio
thread, inside `deserialize_fields` (checked in nice-plug's `wrapper/clap/wrapper.rs`). A
persisted field guarded by a lock could then block the audio thread.
Decision: The library never calls `GuiContext::set_state`. Its persisted field stores and
returns the encoded instance state through `StateCell`, an atomic swap of a reference-counted
string; parsing and encoding happen only on the editor thread.
Consequences: Saving never encodes on the main thread, so the editor publishes a fresh
encoding after every committed change; a host load is decoded at the next editor frame or
open.

## D-27 — An editor menu button no layout can cover

Status: ACCEPTED
Date: 2026-11-22 (owner ratified, 2026-11-22: "Ratify all")
Context: With a fully user-defined layout, nothing guarantees a way back to design mode, the
library or the page list.
Decision: The editor always draws a menu button and the notices in a top layer above layout
content; the button opens the editor menu (mode switch, pages, themes, library actions). Its
look and position are set in the interface design stage.
Consequences: A small part of every canvas is always taken by the button.

## D-28 — Three built-in themes

Status: ACCEPTED
Date: 2026-11-22 (owner ratified, 2026-11-22: "Ratify all")
Context: The library needs a theme before any user theme exists, and the accessibility
decision needs a high-contrast theme.
Decision: "Studio Dark" (the theme of generated defaults), "Studio Light" and "High Contrast"
(at least 7:1), built in, never overwritten or deleted.
Consequences: Their exact colours are set in the interface design stage.

## D-29 — Editing is blocked while an unreadable layout is preserved

Status: ACCEPTED
Date: 2026-11-22 (owner ratified, 2026-11-22: "Ratify all")
Context: D-17 keeps the unreadable bytes. If the user also edited the fallback layout, a save
would have to choose between the kept bytes and the new edits, and one of them would be lost.
Decision: While unreadable bytes are kept, design mode, layout import and theme choice are
unavailable; controls still work. The notice offers "Discard saved layout"; after confirming,
editing becomes available and saves write the current layout.
Consequences: The user must decide explicitly before editing in an older plugin version.

## D-30 — A macro shows its first target's position

Status: ACCEPTED
Date: 2026-11-22 (owner ratified, 2026-11-22: "Ratify all")
Context: Under D-08 automation moves a macro's targets, not the macro. A macro that kept its
own stored position would stand still while its targets move.
Decision: A macro's drawn position is the inverse of its first bound target's mapping, clamped
to 0–1.
Consequences: Targets moved independently of each other make the macro follow only the first.

## D-31 — Copy and paste through the system clipboard

Status: ACCEPTED
Date: 2026-11-22 (owner ratified, 2026-11-22: "Ratify all")
Context: Bitwig can host instances of one plugin in separate processes, so in-memory copy
cannot reach every instance. egui-baseview 0.9.0 already uses the system clipboard
(copypasta).
Decision: Copy writes a `mutable-gui/elements` JSON document as clipboard text; paste
validates it exactly like an import.
Consequences: Copied elements carry their assets in the clipboard text, bounded by the import
limits.

## D-32 — Library folder per platform

Status: ACCEPTED
Date: 2026-11-22 (owner ratified, 2026-11-22: "Ratify all")
Context: The library needs one location that every plugin using mutable-gui agrees on.
Decision: `mutable-gui` inside the platform user data directory as the `dirs` crate reports
it: `~/Library/Application Support` on macOS, `$XDG_DATA_HOME` (default `~/.local/share`) on
Linux, the roaming AppData folder on Windows; under it `layouts/<plugin CLAP id>/` and
`themes/`.
Consequences: The folder name is frozen at version 1.

## D-33 — Rust 1.99.1 toolchain, edition 2024, minimum Rust 1.95

Status: ACCEPTED
Date: 2026-11-22 (owner ratified, 2026-11-22: "Ratify all")
Context: The installed toolchain is 1.99.1; egui 0.37.0 declares rust-version 1.95 and
nice-plug 0.4.2 declares 1.88.
Decision: `rust-toolchain.toml` pins 1.99.1 with rustfmt and clippy; crates use edition 2024
and `rust-version = "1.95"`.
Consequences: Adopters need Rust 1.95 or newer.

## D-34 — Interaction conventions

Status: ACCEPTED
Date: 2026-11-22 (owner ratified, 2026-11-22: "Ratify all")
Context: The specification needs exact numbers for control interaction that the owner did not
set.
Decision: A knob covers its range in a 200-canvas-unit vertical drag; Shift or the fine lock
gives one tenth; a long press of 600 ms opens the control menu; arrow keys step 1 % (0.1 %
with Shift) or one step; Tab follows reading order; the design-mode shortcut is ⌘E (Ctrl+E);
generated pages hold 48 controls on 8 columns; switches take two-state parameters and
selectors 2–32 steps; macros have 1–16 targets.
Consequences: The interface design stage may refine these through a superseding decision.

## D-35 — Design tools float over the canvas

Status: ACCEPTED
Date: 2026-11-22 (owner chose direction B of S-04)
Context: Design mode needs a palette, toolbar and inspector in plugin windows as small as
400 × 300. Directions shown: A, grow the window and dock panels around the canvas; B, keep
the window and float the tools over the canvas; C, keep the window and put every tool in a
bottom drawer above which the canvas shrinks.
Decision: B. A floating toolbar at the top, a floating palette at the left, an inspector card
beside the selection (a bottom sheet in small windows); holding H hides every tool to see what
they cover.
Consequences: Tools cover part of the layout while editing; the window size never changes, so
no host resize negotiation is needed.

## D-36 — The library's tools have one fixed style and size

Status: ACCEPTED
Date: 2026-11-22 (owner)
Context: The tools could follow the user's theme, scale with the canvas, or be restyled by
the developer. Scenario: a theme with grey text on grey makes its own editor unreadable.
Decision: Menu button, menus, design panels, dialogs and notices use one fixed dark style
(`--tool-*` in `design/ui/tokens.css`) with every text pair at least 7:1, at one physical size
(12 px text, 24 px hit targets) whatever the canvas scale; neither themes nor developers
restyle them. Disabled tool items are drawn at half opacity and are exempt from the 7:1 rule.
Consequences: The tools look the same in every plugin that uses the library.

## D-37 — The menu button's corner is the developer's choice

Status: ACCEPTED
Date: 2026-11-22 (owner)
Context: D-27 left the menu button's look and position to the interface design stage.
Decision: A 24 px round button 8 px from two window edges, drawn faint until the pointer is
near; the developer picks the corner, bottom-right by default. In design mode its corner
area is hatched so users do not place controls under it; it carries a dot while notices exist.
Consequences: R-149; the adapter builder gains a corner option.

## D-38 — The developer default is always one step away

Status: ACCEPTED
Date: 2026-11-22 (owner: "there should always be a way to get back to the version that the
developer ships with")
Context: Reset to developer default existed only in design mode.
Decision: The editor menu offers "Reset to developer default" in every state, and the
library lists a read-only "Developer default" entry first.
Consequences: R-150 and R-151.

## D-39 — Only actions that cannot be undone ask first

Status: ACCEPTED
Date: 2026-11-22 (owner)
Context: Which mistakes need a confirmation.
Decision: Undoable actions (deleting elements or pages, reset, replacing imports) happen at
once, with Undo and Redo always in the design toolbar; overwriting or deleting a library file
and discarding a kept unreadable layout ask first.
Consequences: Three confirmation dialogs in total (S-10).

## D-40 — Material Symbols icons through egui_material_icons

Status: ACCEPTED
Date: 2026-11-22 (owner)
Context: egui-phosphor 0.14.0 requires egui 0.36 and cannot be used with egui 0.37;
egui_material_icons 0.9.0 supports egui 0.37 (crate MIT, font Material Symbols Rounded,
Apache-2.0), about 1.3 MB compressed added to every plugin.
Decision: egui_material_icons 0.9.0 for every tool icon and the built-in palette icons.
Consequences: Larger plugin binaries; custom kinds may use the same icons in the palette.

## D-41 — Inter is bundled

Status: ACCEPTED
Date: 2026-11-22 (owner)
Context: egui 0.37 bundles only Ubuntu Light, Hack and emoji fonts; Ubuntu Light is thin at
11–12 px on dark backgrounds.
Decision: Inter 4.1 (SIL OFL 1.1) Regular and Medium are bundled for the tools; themes may
choose the built-in fonts Inter, Inter Medium, Hack and Ubuntu Light, or font assets.
Consequences: Two font files and the OFL text ship in every plugin.

## D-42 — Developers register custom element kinds in Rust

Status: ACCEPTED
Date: 2026-11-22 (owner: "a developer may have their own ideas about the look of the interface
for a plugin they are creating and we must be able to accommodate that. that is the point.")
Context: The built-in kinds are a default set; developers need their own elements and look.
Options were custom kinds in Rust, redrawing built-in kinds, image (filmstrip) skins and hiding
built-ins; the owner chose custom kinds. Supersedes the specification's former out-of-scope
line "third-party element types supplied by plugins or users".
Decision: A developer registers custom element kinds with the library: id (frozen at release),
integer version with migrations, palette name, icon, category and declared typed properties,
from which the library builds the inspector, validation, saving and undo. Only developers add
kinds; packages never carry code (D-21 stands). Custom elements draw anything with egui's
painter and receive the active theme; their code runs only on the editor thread through a
narrow `KindContext` and changes parameters only through the library's gestures. Unregistered
or newer kinds are kept as unknown elements, never deleted.
Consequences: R-152–R-168, I-18–I-20. P1, I-04 and P2 hold whatever a custom element does,
except a panic or hang in its own code, which the library does not contain.

## D-43 — Generated selectors are dropdowns; "disabled" looks like unbound

Status: ACCEPTED
Date: 2026-11-22 (owner ratified, 2026-11-22: "Ratify all")
Context: In the 80-unit cells of a generated layout, segmented selectors overflow (S-13).
nice-plug parameters have no read-only or disabled flag, so no control can be disabled other
than by being unbound.
Decision: Generated selectors use the dropdown presentation. Element states are normal, hover,
dragging, focused and unbound; the "disabled" colour role draws unbound elements.
Consequences: The element gallery (S-12) has five state columns.

## D-44 — Narrow meters show "No signal" vertically

Status: ACCEPTED
Date: 2026-11-22 (owner ratified, 2026-11-22: "Ratify all")
Context: R-052's "No signal: <name>" does not fit across a 30-unit level or gain-reduction
meter.
Decision: A display narrower than 80 canvas units draws a dashed outline and the text rotated
to read upward.
Consequences: None beyond the meter drawing code.

## D-45 — The reference plugin's custom kind is a transfer curve

Status: ACCEPTED
Date: 2026-11-22 (owner ratified, 2026-11-22: "Ratify all")
Context: R-168 needs a custom kind that proves the API end to end without new DSP.
Decision: "Transfer curve", a display drawing the drive stage's input-to-output curve from the
parameter bound to its binding slot, with a colour-role property and a grid toggle.
Consequences: The reference plugin's palette has a "Reference FX" section.

## D-46 — Snapshot pictures rendered by egui_kittest's wgpu renderer, in tests only

Status: ACCEPTED
Date: 2026-11-22 (owner, during /dev-plan)
Context: Every screen of `design/UI.md` is proven by an egui_kittest snapshot that
`devpipe ui compare` puts beside its mockup. egui_kittest 0.37.0 with only its `snapshot`
feature has no renderer: `Harness::snapshot` fails with "No default renderer available. Enable
the wgpu feature or set one via HarnessBuilder::renderer". Options were egui_kittest's `wgpu`
feature as a test-only dependency, a hand-written CPU rasterizer, or interaction tests without
pictures.
Decision: The `wgpu` feature of egui_kittest, in `[dev-dependencies]` only. wgpu 30.0.1 and
egui-wgpu 0.37.0 enter the test build and never the plugin, which keeps drawing with OpenGL
(D-20 holds). Snapshot pictures are compared on macOS; on Linux and Windows the same tests run
their interaction part and skip the picture.
Consequences: STACK.md gains rows for wgpu and egui-wgpu as test-only. Snapshot PNGs under
`crates/mutable-gui/tests/snapshots/` are produced on the owner's Mac and committed.

## D-47 — Captions on controls, titles on panels, tracking on labels

Status: ACCEPTED
Date: 2026-11-22 (owner, during /dev-plan)
Context: The mockups (S-01, S-04, S-12, S-13) draw a caption under knobs, faders, switches and
macros ("Character" on a macro is no parameter's name), a Caption section in the inspector, a
title on panels and letter-spacing on labels; the data model had no field for any of them, and
R-142 refuses undeclared fields.
Decision: Optional `caption` (0 to 64 characters) on knob, fader, switch, xy_pad, macro and
selector; when absent, knob, fader, switch and selector show the bound parameter's name, a macro
shows "Macro" and an XY pad shows none; an empty string shows no caption. Optional `title` (0 to
64 characters) on panel. Optional `tracking` (0 to 8 canvas units, default 0) on label.
Consequences: The specification's data model lists the three fields; schema version 1 includes
them; the inspector's Caption section edits `caption`.

## D-48 — The development plan's choices where the specification is silent

Status: ACCEPTED
Date: 2026-11-22 (owner ratified, 2026-11-22: "Ratify all")
Context: Writing `DEV_PLAN.md` met thirty points the specification, the architecture and the
interface record leave open: data-model nullability and ranges, undo depth, library file names,
interaction thresholds, the asset rule, and one limit of the window backend (egui-baseview 0.9.0
reads the clipboard only on ⌘V).
Decision: The thirty choices below, numbered as in the plan's table "Choices this plan makes
where the specification is silent":

1. Binding slots and taps may be `null`: `binding`, `x`, `y`, each entry of `targets` (1–16 entries), a display's `tap`, an image's `asset`. A palette element starts with nulls (R-069). A null slot draws unbound with the value line "Not bound" (a display: "No signal"), ignores input, and is listed in the unbound list.
2. Frames are integers: `x`, `y` from −4,000 to 8,000, `width`, `height` from 1 to 8,000; values outside are refused naming the field. User resizes keep at least 8 × 8 (R-074).
3. Group members keep absolute canvas frames; a group's frame is the bounding box of its members, recomputed by every command that changes a member. Selection holds top-level elements only.
4. Paste keeps the copied frames; incoming assets whose id the instance already has are not added again.
5. `SetLayout`, `SetTheme` and `SetAll` (whole-document replacements) drop the assets that neither the new layout nor the new theme refers to; no other command drops an asset, and the Type tab removes an unreferenced asset on request. A string equal to an asset id anywhere inside an unknown element's `props` counts as a reference (I-20).
6. The generator gives an enum parameter with more than 32 values a knob, and leaves out the plugin-name page when every parameter is in a group and at least one group exists.
7. An instance state whose `current_page` names no page opens on the first page.
8. Undo keeps the last 200 steps.
9. A long press is 600 ms with the pointer within 4 logical px of where it went down; the menu button is "near" within 64 logical px of its centre.
10. Library file names: the entry name with `/ \ : * ? " < > |`, control characters and a leading `.` replaced by `_`, plus `.mgui`; the listed name comes from the package's `name`. The user default is `layouts/<clap id>/.default.mgui` (a package with layout, theme and assets; its `name` is the entry it was set from, or "Current layout"); the suite default theme is `themes/.default.mgui` (a theme-only package). Listings skip names starting with `.`; the star marks the entry whose name equals the default's `name`.
11. "Use as my default" on a library layout entry stores that layout with the instance's current theme. Applying a library layout entry (the "Developer default" entry included) replaces the layout only; Reset to developer default replaces layout and theme.
12. Editor menu "Export package…" writes the current layout and theme; a library entry's Export… writes that entry alone.
13. "Import theme…" applies only the package's theme, as one undoable change, and refuses a package with no theme.
14. The cross-plugin notice names the source CLAP id (packages carry no plugin name).
15. Packages are written with `created` as UTC `YYYY-MM-DDTHH:MM:SSZ` and no `author`; library dates show the file's UTC modification date as "20 Nov 2026".
16. A host state load during a drag ends every open gesture and drops the drag before the new state is shown.
17. The S-02 small presentation (drill-in submenus) and the S-04 small presentation (compact toolbar, palette behind "+", bottom-sheet inspector) apply when the window is narrower than 520 logical px or lower than 420.
18. Built-in themes fill `canvas` and `display` with solid background, `panel` with solid surface, `control` with solid surface-raised; their typefaces are Inter, Inter and Hack (UI.md).
19. An element's `colours` may hold only its kind's slot names (table above); another name is refused naming it.
20. Menu element `set` actions use a 0-based step index.
21. Font fallback chain for every family: the named font, then Inter, then Hack, then egui's emoji fonts; a missing glyph draws from the next font.
22. An asset's decoded size is the length of its base64-decoded file bytes; the 4 MiB caps count those.
23. Page tabs and menu elements open no control menu: they have no parameter value to reset, type or fine-adjust.
24. "Type value…" is offered for knobs, faders, switches and selectors; on XY pads and macros, which drive several parameters, it is drawn disabled.
25. Keyboard: on an XY pad Up and Down change Y, Left and Right change X; on page tabs Left and Right go to the previous and next page; Enter on a menu element opens its list.
26. Pages and elements are held as `Arc`; the undo stack keeps whole previous instance states, which share every unchanged page, element and asset.
27. A design-mode drag previews the move and commits one command on release; each arrow-key press is one command.
28. egui-baseview 0.9.0 reads the clipboard only when ⌘V reaches the window and ignores `ViewportCommand::RequestPaste`, and the stack has no clipboard crate; so the Arrange popover's "Paste ⌘V" entry is drawn disabled with the hint "Press ⌘V in the plugin window". Every other shortcut action works from a menu.
29. The library preview of a layout entry draws its first page scaled into the preview area with the instance's active theme; a theme entry shows strips of its background, surface, text and eight accent colours.
30. A font asset is listed by the family name in its `name` table (read with skrifa), an image asset as "Image n (W × H)".

Consequences: Every step that uses a choice cites its number. Choice 28 leaves the edge case
"the editor menu offers every action that has a shortcut" unmet for Paste; closing it needs a
clipboard crate in the stack, which is a separate decision.

## D-49 — Tests may unwrap, expect and panic

Status: ACCEPTED
Date: 2026-11-23 (owner ratified, 2026-11-23: "Ratify D-49")
Context: The specification's lint set (Non-functional requirements, "Code") denies `unwrap_used`,
`expect_used` and `panic`, and the gate runs `cargo clippy --workspace --all-targets -- -D
warnings`, which reaches test code as well. A probe workspace with this lint set on rustc 1.99.1
(2026-11-23) showed `.unwrap()`, `.expect()` and `panic!` in `tests/*.rs` failing the gate, so
every test would have to return `Result` and use `?`, and a failed `?` names the error but not
the line where it arose. With `allow-unwrap-in-tests`, `allow-expect-in-tests` and
`allow-panic-in-tests` in a root `clippy.toml`, the same probe passed: the three are accepted
inside `#[test]` functions (closures included) and inside modules marked `#[cfg(test)]` (an
inner `#![cfg(test)]` counts), and still refused in library code, in a library crate used only
by tests, and in a test-file helper outside both. `dbg!` and the print macros stay refused, and
pedantic `manual_assert` still asks for `assert!` in place of `if … { panic!(…) }`.
Decision: A `clippy.toml` at the repository root holds exactly `allow-unwrap-in-tests = true`,
`allow-expect-in-tests = true` and `allow-panic-in-tests = true`. A module of shared test
helpers, such as `examples/reference-plugin/tests/common/mod.rs`, starts with `#![cfg(test)]`.
Every other lint of the specification's set stays as it is in tests and in library code;
`crates/mutable-gui-testkit` is library code.
Consequences: `DEV_PLAN.md` Step 0.4 adds `clippy.toml` to its Files and its Builds line, and
Step 1.26 starts `examples/reference-plugin/tests/common/mod.rs` with `#![cfg(test)]`. The
specification's "Code" line gains "tests may unwrap, expect and panic (D-49)". The project
agents' rule "tests return `Result` and use `?`" becomes this rule. A test failure reports the
line that failed; library code and the testkit still cannot unwrap.
