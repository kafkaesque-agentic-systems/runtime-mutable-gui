# UI design: mutable-gui

How the product looks and behaves for the people who use it. Screens are numbered and never
renumbered. A mockup under `design/ui/` shows layout, content and states; it is a picture of
intent, not code to port: the product is built with the toolkit named under Tooling. Once a
screen exists, its `Built:` line says where to see it (an http address, a file such as a
screenshot the tests make, or `run <command>` that prints its HTML), and
`devpipe ui compare` puts it beside the mockup.

Surface: plugin window inside a DAW

This record designs the interface the library itself ships, which is the same in every plugin
that adopts it: the editor's tools, the built-in element kinds and themes, and the generated
default. A plugin's own layout is user data (an embedded developer default, a generated one or
a user's) and is not designed here; developers bring their own look through custom element
kinds (D-42), which this record gives a place in the palette, inspector and gallery.

Mockups share `design/ui/tokens.css` (tool style and the three built-in themes),
`design/ui/tools.css` (tool components) and `design/ui/kit.js` (element drawing and the
reference layouts). They render with the system font standing in for Inter.

## Surfaces

- Plugin window inside a DAW, macOS arm64, reference host Bitwig Studio 5.3.13: one child
  window that the host owns and may resize; the canvas (200–4,000 units per side, one per
  layout) is scaled uniformly from 0.5 to 4.0 with bars; reference sizes 840 × 520 (reference
  plugin) and 400 × 300 (a small performance layout). Input: mouse and trackpad, keyboard while
  the window has focus (the host may take some keys, so every shortcut also has a menu entry),
  touchscreens only through the operating system's mouse emulation (long press = right-click).
  The editor never blocks the audio thread and draws no frames while idle.
- Linux x86_64 (X11) and Windows x86_64: same design, not checked in a host for version 1.

## Users and tasks

- Musician or engineer (primary): plays and tweaks in perform mode, seconds at a time in the
  middle of a session, mouse or trackpad, expert in their DAW but not a designer. Then, less
  often: builds or trims a page (add a control, bind it to a parameter), restyles with a theme,
  saves, shares or sets a default, and returns to the developer default.
- Plugin developer: the same tools in long sessions to experiment with layouts and to make the
  developer default, placing their own registered custom kinds beside the built-ins.
- Package recipient: imports a `.mgui` file from someone else and must be told clearly when it
  is refused or partly fits.

## Screens

### S-01 — Perform mode

Purpose: Play the plugin through its current layout.
Serves: R-010, R-013, R-014, R-015, R-016, R-017, R-018, R-019, R-020, R-022, R-023, R-025, R-026, R-031, R-032, R-033, R-034, R-035, R-036, R-037, R-038, R-047, R-048, R-049, R-050, R-051, R-052, R-053, R-054, R-058, R-059, R-060, R-061, R-109, R-145, R-146, R-149
Shows: the current page of the layout drawn in the active theme (here the reference plugin's default on Studio Dark: page tabs, filter, drive, compressor, scope, macro, output); the editor menu button, 24 px, faint until the pointer comes near, in the corner the developer chose (bottom-right by default).
Actions: drag knobs, faders, XY pads and macros (Shift for fine); click switches, selector entries, page tabs and menu elements; right-click or long press a control → S-03; Tab, arrows and Enter for keyboard use; menu button → S-02.
States: dragging: a value bubble above the control; focused: an outline in the focus role; modulated: a band in the modulation role from base to modulated value; unbound: disabled role, dashed outline, missing id on the value line; dimmed (F-002, D-50): the normal look at 45 % opacity, still operable, focus outline at full opacity; display without its tap: "No signal: <name>"; notices present: a dot on the menu button (S-11). Mockup states: `S-01-perform--states.html`.
Mockup: design/ui/S-01-perform.html
Built: not yet
Status: ACCEPTED

### S-02 — Editor menu

Purpose: Reach every editor action from one button in any mode.
Serves: R-009, R-011, R-067, R-108, R-119, R-120, R-132, R-133, R-150
Shows: plugin name; Design mode with ⌘E; the pages inline with the current one checked; Theme (current name) and Library submenus; Reset to developer default at the bottom. Theme submenu: built-in themes, the user's themes, Import theme…, Use for all plugins. Library submenu: Save layout…, Save theme…, Open library…, Import package…, Export package…, Use as my default for <plugin>, Clear my default.
Actions: Design mode → S-04; a page → that page; a theme → applied at once; Open library… → S-09; Save… → S-10; Import package… → system file dialog, then the import or a notice (S-11); Reset to developer default → applied, undoable (while an unreadable layout is kept it first opens S-10 discard).
States: design mode switched off by the developer: no Design mode or Library entries, Theme keeps Import theme…, Reset stays (`--reduced`); unreadable layout kept: a locked explanation with Discard saved layout…, Design mode, Theme and Library disabled (`--preserving`); small windows: submenus drill in with a back row (`--small`); Library submenu open (`--library`).
Mockup: design/ui/S-02-editor-menu.html
Built: not yet
Status: ACCEPTED

### S-03 — Control menu and value field

Purpose: Reset, type or finely adjust one control's value.
Serves: R-024, R-027, R-028, R-029, R-030, R-039, R-040, R-147, R-148
Shows: the parameter's name and current value; Reset with the default value; Type value… ↩; Fine adjust as a check item. The value field replaces the control's value line.
Actions: Reset → value set as one gesture, menu closes; Type value… or Enter → value field; ↩ in the field → the plugin parses it and sets it as one gesture; Esc → closes with no change; Fine adjust → toggles fine dragging for that control.
States: typing (`--value`); rejected text: red field and "Not a valid value" until edited or closed (`--error`).
Mockup: design/ui/S-03-control-menu.html
Built: not yet
Status: ACCEPTED

### S-04 — Design-mode workspace

Purpose: Rearrange, bind and edit the layout while audio runs.
Serves: R-068, R-069, R-070, R-071, R-072, R-073, R-074, R-076, R-077, R-078, R-079, R-080, R-081, R-082, R-083, R-084, R-085, R-086, R-087, R-091, R-093, R-095, R-096, R-097, R-154, R-156, R-158, R-161, R-164, R-165
Shows: the canvas with an 8-unit grid, selection outline and handles, snap guides; a floating toolbar (Undo, Redo, Arrange, Group, grid step and snap, page button, unbound count, Hide tools, Theme, Library, Done); a floating palette at the left with built-in controls, displays and decorations and, last, a section of the plugin's registered custom kinds; an inspector card beside the selection (Binding and Look open, Frame, Shape and Caption folded; for a custom kind, its plugin, version, id and declared properties); the menu button in its design state with its corner hatched.
Actions: palette click → element added at the centre, selected; drag → move; handles → resize; Arrange → align, distribute, group, ungroup, z-order, duplicate, delete with shortcuts; binding field → S-05; page button → S-06; unbound count → S-07; Theme → S-08; Library → S-09; hold H → all tools hidden; Done or ⌘E → S-01.
States: several selected with Arrange open (`--arrange`); small window: compact toolbar, palette behind "+", inspector as a bottom sheet (`--small`); tools hidden (`--peek`); a custom element selected (`--custom`); an unknown element selected: placeholder, kind id and version, no property editors (`--unknown`).
Mockup: design/ui/S-04-workspace.html
Built: not yet
Status: ACCEPTED

### S-05 — Parameter and tap picker

Purpose: Bind a control or display to a parameter or signal tap.
Serves: R-056, R-088, R-089, R-090, R-163
Shows: a search field with a match count; results grouped by parameter group, each with its name (matches highlighted), stable id and kind; the current binding checked; a footer naming what this control accepts. For displays and custom tap slots, the compatible taps with their kind and channels, and why other taps are absent.
Actions: type → filter as you type; ↑↓ → move; ↩ or click → bind (one undoable change) and close; Esc → close.
States: no match: "No parameter matches" with the count of hidden incompatible ones; tap list (`--tap`).
Mockup: design/ui/S-05-picker.html
Built: not yet
Status: ACCEPTED

### S-06 — Pages and canvas

Purpose: Manage pages and the layout's canvas and grid.
Serves: R-057, R-062, R-063, R-064, R-065, R-066, R-075
Shows: the pages with drag handles, element counts and the count of 64; inline rename; rename and delete on hover; Add page; canvas width and height for every page with their range; grid step (2–64) and snap.
Actions: click a page → it becomes current; drag → reorder; Add page → inserted after the current one; delete → removed (undoable); deleting the only page → notice (S-11); out-of-range canvas size → the field keeps its previous value.
States: renaming (shown); 64 pages: Add page disabled.
Mockup: design/ui/S-06-pages.html
Built: not yet
Status: ACCEPTED

### S-07 — Unbound list

Purpose: Find and repair everything whose parameter, tap or kind is missing.
Serves: R-092, R-166
Shows: a one-line explanation; unbound controls and displays and unknown elements, grouped by page, each with its missing id, tap or kind id.
Actions: a row → its page shown and the element selected; Rebind… → S-05; Show (unknown elements) → selected, S-04 `--unknown`.
States: empty: the toolbar shows no count and the list is not offered.
Mockup: design/ui/S-07-unbound.html
Built: not yet
Status: ACCEPTED

### S-08 — Theme editor

Purpose: Edit the active theme with a live preview and save it.
Serves: R-098, R-099, R-100, R-101, R-102, R-103, R-104, R-105, R-122, R-123
Shows: a floating panel at the right with the theme name and Save theme; tabs Colours (contrast summary pinned on top, failing pairs in amber with their ratio, then base roles with hex values, accents 1–8, state roles), Type (body, heading and value typefaces; assets with the 4 MiB meter; Add font…, Add image…), Surfaces (fill per surface role: solid, gradient, grain, image), Shape (knob style, corners, border, track, handle). The layout behind changes live.
Actions: edit any value → applied on the next frame, undoable; Save theme → S-10 save, or the collision question; Add font… or Add image… → system file dialog, refused with a notice beyond the cap or for another format; close → editor keeps the edited theme.
States: a pair below 4.5:1 (shown); Type (`--type`); Surfaces (`--surfaces`); Shape (`--shape`); editing a built-in theme saves under a new name.
Mockup: design/ui/S-08-theme.html
Built: not yet
Status: ACCEPTED

### S-09 — Library

Purpose: Apply, save, share and manage layouts and themes, and set defaults.
Serves: R-106, R-125, R-126, R-128, R-129, R-130, R-132, R-133, R-135, R-151
Shows: a panel over the dimmed plugin; Layouts tab for this plugin, first "Developer default (as shipped)", then saved layouts with dates, the user default starred, unreadable files marked; a preview and details of the selected one; Themes tab shared by every plugin with colour strips, built-ins marked, the suite default starred; Import package…, Save current…, and the folder path.
Actions: Apply → replaces the active layout or theme (undoable); Export… → system file dialog; Delete… → S-10 delete; Use as / Clear my default; Use for all plugins / Stop; Import package… → import or notice (S-11); Save current… → S-10.
States: themes (`--themes`); built-in and developer-default entries cannot be deleted or overwritten; unreadable entries can only be deleted.
Mockup: design/ui/S-09-library.html
Built: not yet
Status: ACCEPTED

### S-10 — Library dialogs

Purpose: Confirm the few actions that cannot be undone, and name what is saved.
Serves: R-120, R-127, R-136
Shows: Save with a name field (1–64 characters); "Replace “Live”?" with the existing file's date; delete confirmation; discard confirmation for a kept unreadable layout explaining what the next save will do.
Actions: Save → written (or the collision question); Replace (red) → overwritten; Save as “Live 2” → saved under the next free name; Delete (red) → removed; Discard (red) → editing unlocked; Cancel or Keep it → nothing changes.
States: collision (`--collision`); delete (`--delete`); discard (`--discard`); a name already used by a built-in theme or "Developer default" asks for another name.
Mockup: design/ui/S-10-dialog.html
Built: not yet
Status: ACCEPTED

### S-11 — Notices

Purpose: Tell the user what went wrong or needs attention, and that nothing was lost.
Serves: R-002, R-012, R-117, R-118, R-131, R-134, R-137, R-138, R-139, R-140, R-141, R-142, R-143, R-144
Shows: notices stacked above the menu button, newest at the bottom, each with an icon, a bold summary, what happened, and that nothing changed; red for refused or failed, amber for warnings; actions where useful; the menu button carries a dot while any exist.
Actions: dismiss (×) → removed; Show unbound → S-07; Undo import → the import undone; Keep it → dismissed, layout still kept; Discard saved layout… → S-10 discard.
States: refused import, cross-plugin import, failed save (shown); unreadable saved layout with editing locked (`--unreadable`).
Mockup: design/ui/S-11-notices.html
Built: not yet
Status: ACCEPTED

### S-12 — Element gallery and built-in themes

Purpose: Define how every built-in element kind draws from a theme, in every state.
Serves: R-052, R-099, R-102, R-106, R-107, R-109, R-159, R-160, R-164, R-168
Shows: knob (arc, pointer, filled), fader (vertical, horizontal), switch, XY pad, macro, selector (segments, dropdown), menu element, page tabs, oscilloscope, spectrum, level meter, gain-reduction meter, label, panel, image, a developer's custom kind (the reference plugin's Transfer curve) and the unknown-element placeholder, in normal, hover, dragging, focused and unbound states, in Studio Dark.
Actions: none; a reference sheet.
States: Studio Light (`--light`); High Contrast (`--high-contrast`). Disabled has no separate look (D-43).
Mockup: design/ui/S-12-elements.html
Built: not yet
Status: ACCEPTED

### S-13 — Generated default

Purpose: What a plugin shows when its developer embeds no layout.
Serves: R-003, R-004, R-005, R-006
Shows: the plugin name and page tabs with one page per parameter group; knobs for float and integer parameters, switches and dropdown selectors with a label above, on an 8-column grid of 88 × 116 cells from y = 64 with 24-unit margins, in declaration order; the canvas sized for the largest page; Studio Dark.
Actions: as S-01.
States: a group of more than 48 parameters continues on "<group> 2"; a plugin with no parameters shows one empty page.
Mockup: design/ui/S-13-generated.html
Built: not yet
Status: ACCEPTED

## Flows

1. Tweak a value precisely: S-01 → right-click a knob → S-03 → Type value… → ↩; a rejected value keeps the field open in red (S-03 `--error`) and the parameter unchanged.
2. Build a three-knob performance page: S-01 → menu button → S-02 Design mode → S-04 → page button → S-06 Add page → palette knob → binding field → S-05 search and bind → repeat → Done → S-01; anything unbound later shows in S-07; every step undoes.
3. Restyle: S-02 Theme → pick a theme (done), or S-04 → Theme → S-08 edit → Save theme → S-10 (S-10 `--collision` if the name exists) → S-09 Themes.
4. Save and share: S-02 Library → S-09 → Save current… → S-10 → Export… → system file dialog; a failed save raises S-11 and the library is unchanged.
5. Import someone's package: S-02 Import package… → system file dialog → applied (undoable), with an S-11 warning if made for another plugin or an S-11 refusal that changes nothing.
6. Get back to the shipped version: S-02 Reset to developer default (undoable), or S-09 → Developer default → Apply.
7. Open a project saved by a newer version: S-01 with S-11 `--unreadable` → Keep it (editing stays locked, the saved layout survives every save) or Discard saved layout… → S-10 `--discard` → editing unlocked.
8. Developer makes the default: S-04 with their custom kinds from the palette → S-09 Export… → the exported package embedded in the plugin.

## Navigation

One window with two modes. The menu button is reachable on every page in both modes and
opens S-02, from which everything else is reached. Design mode (S-04) adds a floating toolbar,
palette and inspector over the canvas; their popovers (S-05, S-06, S-07, Arrange) open next to
the button that opened them and close on Escape, outside click or Done. S-08 is a floating
panel that stays open while editing. S-09 and S-10 are modal over the dimmed window; Escape
cancels them. Notices (S-11) stack above the menu button in both modes. Done or ⌘E returns to
perform mode; the editor always opens in perform mode on the page it last showed.

## Visual language

The values are in `design/ui/tokens.css`; the product's theme is written from that file.

- Colour: two layers. Tools: one fixed dark style (`--tool-*`): background #17181B, raised
  #222329, hover #2B2D34, outline #3A3D45, text #ECEDEF (15.2:1), muted #BEC1C8 (≥ 7.6:1 on
  every tool background), accent #5AABFF for selection, focus and primary actions (text on it
  #0B0C0E, 8.1:1), warning #F5B841, danger #FF7A7A, snap guides #FF5FD2. Elements: the 21 colour
  roles of the active theme (`--role-*`); built-in themes Studio Dark (default), Studio Light
  and High Contrast with the values in `tokens.css`.
- Type: Inter 4.1 for the tools at 11, 12 and 13 px (Medium for titles and section heads,
  uppercase section heads with 0.06 em tracking); Hack for numbers and ids. Themes name body,
  heading and value typefaces; Studio themes use Inter, Inter and Hack.
- Space and shape: 4 px spacing scale (4, 8, 12, 16); 24 px rows and hit targets; 36 px
  toolbar; radii 4, 6 and 10 px for fields, menus and panels; one shadow for floating tools.
  Theme shape tokens default to radius 8, border 1, track 4, handle 14 (High Contrast: border
  2, track 6).
- Motion: the menu button fades from faint to full over 90 ms as the pointer nears; nothing
  else in the tools animates, so there is nothing to reduce. Displays move with their signal.
- Icons and imagery: Material Symbols Rounded through egui_material_icons for tool and palette
  icons; no illustration. Custom kinds bring their own palette icon from the same set.

## Components

| Component | Used on | Built from |
|---|---|---|
| Menu button | S-01, S-02, S-04, S-11 | custom (painter) in an egui `Area` above the canvas layer |
| Menu and submenu | S-02, S-03, S-04 | egui `Area` popups with custom rows |
| Floating toolbar | S-04, S-05, S-06, S-07, S-08 | egui `Area` with custom frame |
| Floating palette | S-04 | egui `Area` with icon buttons |
| Inspector card and bottom sheet | S-04 | egui `Area` with collapsing sections |
| Field, segmented control, range | S-03, S-04, S-05, S-06, S-08, S-10 | egui `TextEdit`, custom-painted segments and ranges |
| Search list | S-05, S-07, S-09 | egui `ScrollArea` with custom rows |
| Dialog | S-10 | egui `Area` over a scrim |
| Notice | S-11 | egui `Area` stack, custom frame |
| Theme editor panel | S-08 | egui `Area` with tabs and `ScrollArea` |
| Library panel | S-09 | egui `Area` over a scrim with tabs |
| Built-in element kinds | S-01, S-12, S-13 | custom (egui painter), from theme roles and shape tokens |
| Custom element kind | S-04, S-12 | the developer's `ElementKind`, drawn through `KindContext` |
| Unknown-element placeholder | S-04, S-07, S-12 | custom (painter) |
| Selection, handles, guides, marquee, grid | S-04 | custom (painter) on the tool layer |

## Accessibility

- Contrast: every tool text pair at least 7:1 (disabled tool items excepted, drawn at half
  opacity); theme text pairs warned below 4.5:1 in S-08; High Contrast at least 7:1 for every
  text pair; focus outline at least 3:1 against background and surface in every built-in theme.
- Targets: tool hit targets at least 24 × 24 px at every canvas scale; the tools keep their
  size while the canvas scales 0.5–4.0.
- Text: tool text 11–13 px, scaled only by the display's pixel density; layout text scales with
  the canvas.
- Keyboard: perform mode per R-145–R-148; design mode shortcuts (⌘Z, ⇧⌘Z, ⌘D, ⌘G, ⇧⌘G, ⌘] ⌘[,
  arrows, ⌫, H, ⌘E) each also reachable from a menu, since hosts may take keys.
- Colour is never the only signal: unbound has a dashed outline and the missing id, failing
  contrast pairs an icon and ratio, notices an icon and a bold summary.
- Not in version 1: screen readers (D-15), translations and right-to-left text; the editor's
  own text is English.

## Tooling

| Name | Role |
|---|---|
| egui | UI toolkit: every tool and element is drawn with it |
| nice-plug-egui | Hosts the egui editor in the plugin window (OpenGL) |
| egui_material_icons | Icons for tools and palette |
| Inter | Bundled font for the tools and a built-in theme font |
| egui_kittest | Headless editor harness and the snapshot pictures each screen's `Built:` line will name |

## Not yet decided

None.
