# Specification: mutable-gui

## Problem

Audio plugin interfaces are fixed by their developer: every musician gets the same layout,
whether they need all 200 parameters of a synthesizer or three knobs for a live set, a mouse
or a touchscreen, a dark studio or a high-contrast display. Rust developers writing CLAP
plugins with nice-plug must also hand-build each interface, which costs more than the DSP for
many plugins. mutable-gui is a Rust library that gives any nice-plug plugin an interface the
user can rebuild, rebind and restyle inside the DAW while audio runs, saved with the project
and shareable as a file, so the developer ships only DSP, a parameter tree and a default.

## Users

- Plugin developer: writes a Rust CLAP plugin with nice-plug; adopts the library with an
  embedded default package, declared signal taps and one persisted field, and does no other
  interface work.
- Musician or engineer (end user): uses the plugin in a DAW; switches to design mode to
  rearrange, bind and theme the interface, saves layouts to the library, sets defaults, and
  exchanges packages with others.
- Package recipient: imports a `.mgui` file made by someone else, which the library treats as
  untrusted input.
- Owner: runs the manual Bitwig checklist on macOS that gates version 1.

## Requirements

Ranges: R-001–R-009 adoption · R-010–R-014 editor · R-015–R-040 perform mode ·
R-041–R-056 displays and signal taps · R-057–R-066 canvas and pages ·
R-067–R-097 design mode · R-098–R-109 themes · R-110–R-124 instance state ·
R-125–R-136 library · R-137–R-144 import validation · R-145–R-148 keyboard.

### R-001 — Embedded developer default

The adapter builds the editor from a package the developer embeds in the plugin binary; an
instance with no user default and no suite default theme shows that package's layout and
theme.
Acceptance: with an empty library, the first editor of a new reference-plugin instance holds a
layout and theme equal, as documents, to those of the embedded `default.mgui`.

### R-002 — Invalid embedded default

If the embedded package fails validation, the editor uses the generated default and shows a
notice containing the validation error; parameters and audio are unaffected.
Acceptance: a test plugin embedding a truncated package opens with the generated layout and
one notice whose text contains the decoder's error message.

### R-003 — Generated default pages

When no package is embedded, the library generates a layout with one page per top-level
parameter group in declaration order, preceded by a page named after the plugin that holds
the parameters outside any group.
Acceptance: for a fake parameter tree with 3 ungrouped parameters and groups "Filter" and
"Amp", the generated pages are [plugin name, "Filter", "Amp"] and each holds exactly its
parameters.

### R-004 — Generated default control kinds

In a generated layout, float and integer parameters get knobs, boolean parameters get
switches and enum parameters get selectors, each bound to its parameter over its full range
in the normal direction.
Acceptance: the generated layout for one parameter of each kind contains a knob, a knob, a
switch and a selector bound to the matching ids with range 0–1, not reversed.

### R-005 — Generated default page capacity

A generated page holds at most 48 controls on an 8-column grid in declaration order; the
parameters of a group beyond 48 continue on pages named "<group> 2", "<group> 3" and onward.
Acceptance: a group "Mod" of 100 parameters yields pages "Mod", "Mod 2", "Mod 3" with 48, 48
and 4 controls.

### R-006 — Generated default omits hidden parameters

Parameters the plugin flags as hidden or as hidden in generic interfaces are not placed in a
generated layout.
Acceptance: a fake tree with one parameter of each flag and one plain parameter generates a
layout containing only the plain parameter.

### R-007 — Signal tap declaration

The developer declares each signal tap with a unique name and a kind, audio (1 or 2
channels, with a capacity in frames from 1,024 to 262,144) or scalar, before the plugin first
processes audio.
Acceptance: declaring "out" (audio, 2 channels, 16,384 frames) and "gr" (scalar) succeeds and
the editor's tap list holds both with their kinds and channel count.

### R-008 — Duplicate tap name refused

Declaring a tap whose name is already declared returns an error and leaves the existing tap
unchanged.
Acceptance: a second declaration of "out" returns the duplicate-name error and "out" keeps
its original kind and capacity.

### R-009 — Design mode switched off by the developer

A developer option removes design mode: the editor menu then offers pages, theme choice and
theme import only, and the design-mode shortcut does nothing.
Acceptance: with the option set, the editor menu holds no design-mode, layout-library or
layout-import entry, and pressing the shortcut leaves the editor in perform mode.

### R-010 — Editor menu always reachable

Every page shows the editor menu button above all elements in both modes; no layout content
can remove, hide or cover it.
Acceptance: on a layout whose top element is a panel covering the whole canvas, a click on
the menu button's position opens the editor menu.

### R-011 — Editor menu page list

The editor menu lists every page of the layout by name, and choosing one shows that page.
Acceptance: on a three-page layout, choosing the third entry makes the third page current.

### R-012 — Notices persist until dismissed

A notice stays visible until the user dismisses it.
Acceptance: a notice raised by a refused import is still shown after 600 frames and is gone
on the frame after the user dismisses it.

### R-013 — Editor opens in perform mode

Opening the editor always shows perform mode, whatever mode it was closed in.
Acceptance: closing the editor in design mode and opening it again shows perform mode.

### R-014 — Current page kept across editor reopen

Closing and reopening the editor shows the page that was current when it closed.
Acceptance: with page 2 current, closing and reopening the editor shows page 2.

### R-015 — Knob drag

Dragging a knob vertically changes its bound value; a drag of 200 canvas units covers the
binding's full range, upward increasing.
Acceptance: an upward drag of 100 canvas units on a knob at 0.2 with binding range 0–1 sets
the parameter to 0.7 normalized (±0.005).

### R-016 — Fader drag

Dragging a fader's handle moves the value along the fader's axis so that the handle follows
the pointer; the fader's track length covers the binding's full range.
Acceptance: dragging the handle of a vertical fader with a 200-unit track up by 50 units from
value 0.5 sets the parameter to 0.75 normalized (±0.005).

### R-017 — Fine adjustment with Shift

Holding Shift during a knob, fader, macro or XY-pad drag moves the value at one tenth of the
normal rate.
Acceptance: the drag of R-015 made with Shift held sets the parameter to 0.25 normalized
(±0.005).

### R-018 — Switch click

Clicking a switch sets its two-state parameter to the other value.
Acceptance: clicking a switch bound to a parameter at its first value sets it to its second
value, and a second click sets it back.

### R-019 — XY pad drag

Dragging inside an XY pad sets its X binding from the pointer's horizontal position and its Y
binding from its vertical position within the pad, upward increasing.
Acceptance: pressing at the pad's centre and dragging to its top-right corner sets X and Y to
the top of their binding ranges.

### R-020 — Selector choice

Clicking a selector entry sets its stepped parameter to that entry's value; entry labels
are the plugin's text for each step.
Acceptance: on a selector bound to an enum parameter with steps "Sine", "Saw", "Square",
clicking "Square" sets the parameter to its third step.

### R-021 — Menu element items

Choosing an item of a menu element performs that item: opening its page, or setting its
stepped parameter to its value.
Acceptance: a menu element with items "Open page FX" and "Wave: Saw" makes page "FX" current
for the first and sets the wave parameter to "Saw" for the second.

### R-022 — Page tabs

Page tabs show the name of every page and clicking a name makes that page current.
Acceptance: clicking the second tab of a three-page layout makes the second page current.

### R-023 — One gesture per drag

Pressing a control begins a gesture on each parameter it is bound to, value changes during
the drag are sent inside it, and release ends it.
Acceptance: a fake parameter source records, for a knob drag, begin, one or more sets, end;
for an XY drag, the same sequence for both parameters, each begun before its first set.

### R-024 — Single-change gesture for clicks

A switch click, a selector choice, a menu item, a typed value and a reset each send a begin,
one set and an end for every parameter they change.
Acceptance: the fake parameter source records exactly begin, set, end for one switch click.

### R-025 — Gestures closed when the editor closes

When the editor closes during a drag, every begun gesture is ended.
Acceptance: closing the editor harness while a knob is held records an end for the knob's
parameter.

### R-026 — Values formatted by the plugin

The value text a control shows is the plugin's own text for the parameter's value, with its
unit.
Acceptance: a knob bound to a parameter whose formatter returns "440 Hz" for 0.5 shows
"440 Hz" at that value.

### R-027 — Type a value

Choosing "Type value" in the control menu opens a text field; confirming parses the text with
the plugin's parser and, when the plugin accepts it, sets the parameter as one gesture.
Acceptance: typing "1000" into the field of a frequency knob whose parser maps "1000" to 0.62
sets the parameter to 0.62.

### R-028 — Rejected typed value

When the plugin's parser rejects the typed text, the parameter is unchanged and the field
shows "Not a valid value" until edited or closed.
Acceptance: typing "abc" leaves the parameter at its prior value and the field shows the
message.

### R-029 — Reset to default

Choosing "Reset" in the control menu sets every parameter the control is bound to to that
parameter's default value.
Acceptance: resetting a macro with two targets sets both targets to their defaults.

### R-030 — Fine-adjust lock

Choosing "Fine adjust" in the control menu makes drags of that control move at the fine rate
without Shift until the user chooses it again or the instance is destroyed.
Acceptance: after locking, the unmodified drag of R-015 sets the parameter to 0.25 (±0.005).

### R-031 — Controls follow outside changes

When a bound parameter changes from outside the editor (automation, host, preset), the
control shows the new value on the next drawn frame.
Acceptance: changing a value in the fake parameter source between frames changes the drawn
knob value in the following frame.

### R-032 — Modulation band

When the host modulates a bound parameter, the control draws a modulation band from the base
value to the modulated value.
Acceptance: with base 0.4 and modulated value 0.6 in the fake source, the knob's drawn model
holds a band from 0.4 to 0.6.

### R-033 — Binding sub-range

A knob, fader, macro target or XY axis whose binding range is a–b maps its full travel onto
normalized values a to b, or b to a when reversed.
Acceptance: a knob bound with range 0.25–0.75, reversed, at full travel sets the parameter to
0.25.

### R-034 — Macro mapping

Moving a macro to position p sets each target to a + (b − a)·p, or b − (b − a)·p when that
target is reversed, where a–b is the target's range.
Acceptance: a macro at 0.5 with targets (0.2–0.6) and (0–1 reversed) sets them to 0.4 and 0.5.

### R-035 — Macro position follows its first target

A macro shows the position whose mapping gives its first bound target's current value,
clamped to 0–1.
Acceptance: when automation sets the first target (range 0.2–0.6) to 0.5, the macro shows
position 0.75.

### R-036 — Macro with an unbound target

A macro moves its bound targets while one or more targets are unbound, and its control shows
the unbound mark.
Acceptance: a macro with targets "cutoff" (present) and "gone" (absent) changes "cutoff" when
dragged and is drawn with the unbound mark.

### R-037 — Unbound control

A control none of whose parameters the plugin has is drawn in the "disabled" colour role,
shows the missing parameter id, and ignores input in perform mode.
Acceptance: a knob bound to "gone" draws the id "gone" and a drag records no gesture.

### R-038 — Controls inert while their parameter is unbound only

A control with several bindings ignores input only for its unbound parameters.
Acceptance: an XY pad with X bound and Y unbound records gestures for X only.

### R-039 — Long press opens the control menu

A press held 600 ms without movement on a control opens its control menu, for touchscreens
that send no right-click.
Acceptance: a 700 ms stationary press on a knob opens its control menu and changes no value.

### R-040 — Right-click opens the control menu

Right-clicking a control in perform mode opens its control menu with the entries Reset, Type
value and Fine adjust.
Acceptance: right-clicking a knob opens a menu with exactly these three entries.

### R-041 — Audio tap push without a reader

When no visible display reads an audio tap, a push returns without copying samples.
Acceptance: with no editor open, 1,000 pushes of 512 frames leave the tap's copied-frame
count at 0.

### R-042 — Audio tap push with a reader

When a visible display reads an audio tap, a push copies the samples into the tap's buffer.
Acceptance: with an oscilloscope on the current page bound to "out", a push of 512 frames
makes 512 frames available to the display.

### R-043 — Full audio tap drops new data

When an audio tap's buffer is full, a push drops the frames that do not fit and returns at
once.
Acceptance: pushing 20,000 frames into a 16,384-frame tap that is never read leaves the first
16,384 frames readable and returns in bounded time.

### R-044 — Tap push allocates nothing

Pushing to an audio or scalar tap never allocates memory, takes a lock or calls the
operating system.
Acceptance: pushes run under the allocation checker with zero allocations; review finds no
lock or system call in the push path.

### R-045 — Scalar tap latest and maximum

Reading a scalar tap gives its latest value and the largest value pushed since the previous
read.
Acceptance: pushes 1, 5, 2 then a read give latest 2 and maximum 5; a second read with no
push gives latest 2 and maximum 2.

### R-046 — Audio tap sample rate

The developer sets each audio tap's sample rate when the plugin is initialized, and displays
use it for time and frequency axes.
Acceptance: after setting 48,000 Hz, a spectrum display's highest frequency is 24,000 Hz.

### R-047 — Display starts with fresh data

When a display becomes visible, it draws only data pushed after it became visible.
Acceptance: switching to a page whose scope reads a tap that was filled earlier draws no
samples until new samples are pushed.

### R-048 — Oscilloscope

An oscilloscope draws the most recent window of its audio tap, one trace per channel, with a
window length from 5 to 500 ms (default 50 ms).
Acceptance: with a 50 ms window at 48 kHz and a pushed 1 kHz sine, the drawn trace spans 2,400
samples showing 50 cycles.

### R-049 — Spectrum analyser

A spectrum display draws the magnitude spectrum of its audio tap with an FFT size of 1,024,
2,048, 4,096 or 8,192 (default 4,096), a logarithmic frequency axis from 20 Hz to half the
sample rate, and a dB floor from −120 to −30 dB (default −90).
Acceptance: a pushed 1 kHz sine at −6 dBFS draws its peak within one FFT bin of 1 kHz and
within 1 dB of −6 dB.

### R-050 — Level meter

A level meter draws the peak and the 300 ms RMS of its audio tap in dBFS on a −60 to +6 dB
scale, with the peak held for 1.5 s.
Acceptance: a pushed full-scale sine draws peak 0 dBFS and RMS −3 dBFS (±0.5 dB); the peak
mark stays for 1.5 s (±1 frame) after the signal stops.

### R-051 — Gain-reduction meter

A gain-reduction meter draws the maximum of its scalar tap since the previous frame, in dB,
on a scale of 6, 12, 24 or 48 dB (default 24).
Acceptance: pushes of 2, 9, 3 dB between two frames draw 9 dB.

### R-052 — Display with a missing tap

A display bound to a tap name the plugin did not declare draws "No signal: <name>" in the
"text-muted" colour role.
Acceptance: a scope bound to "gone" draws "No signal: gone".

### R-053 — No redraw when idle

While no display is on the current page and there is no input, no parameter change and no
notice change, the editor requests no new frame.
Acceptance: after the first frame of a static page with no events, the harness records no
repaint request over 120 simulated frames.

### R-054 — Displays animate while visible

While a display is on the current page, the editor requests a new frame after every frame,
at most 60 frames per second.
Acceptance: with a visible scope, each of 60 harness frames ends with a repaint request due
between 16 and 17 ms later.

### R-055 — Analysis off the audio thread

Spectrum, RMS and peak calculations run on the editor's thread, never inside a tap push.
Acceptance: review finds no analysis call reachable from a push function.

### R-056 — Tap list for binding

Design mode offers, for a display, only the declared taps of the kind the display reads:
audio taps for oscilloscope, spectrum and level meter, scalar taps for gain reduction.
Acceptance: with taps "out" (audio) and "gr" (scalar), a level meter's tap picker lists only
"out".

### R-057 — Canvas size

In design mode the user sets the layout's canvas width and height, each from 200 to 4,000
canvas units, and every page uses it.
Acceptance: setting 1,200 × 400 makes every page's canvas 1,200 × 400; 150 is refused and the
field keeps the previous value.

### R-058 — Uniform scaling with bars

The editor draws the canvas scaled by the smaller of window width ÷ canvas width and window
height ÷ canvas height, centred, with the remaining area in the "background" colour role.
Acceptance: a 1,200 × 400 canvas in a 600 × 600 window draws at scale 0.5 with 200-pixel bars
above and below.

### R-059 — Window scale range

The user can resize the editor window to any size whose scale (as in R-058) is from 0.5 to
4.0.
Acceptance: a host resize request to scale 0.3 is answered with the size for scale 0.5, and
one for scale 5 with the size for scale 4.

### R-060 — Window size kept

The editor window opens at the size it had when it was last closed in this instance.
Acceptance: resizing to 900 × 300, closing and reopening opens at 900 × 300.

### R-061 — Initial window size

A new instance's editor opens at scale 1.0 of the canvas.
Acceptance: a new instance with a 800 × 500 canvas opens at 800 × 500 logical pixels.

### R-062 — Add a page

In design mode the user adds a page; it is inserted after the current page with the name
"Page <n>" (n the lowest unused number) and becomes current.
Acceptance: on a layout with "Page 1", adding a page creates and shows "Page 2" in second
position.

### R-063 — Rename and reorder pages

In design mode the user renames a page (1 to 64 characters) and moves it to another position.
Acceptance: renaming "Page 2" to "FX" and moving it first gives the page order ["FX",
"Page 1"].

### R-064 — Delete a page

In design mode the user deletes a page with all its elements; the previous page (or the next
page, when deleting the first) becomes current.
Acceptance: deleting page 2 of 3 removes it and its elements and makes page 1 current.

### R-065 — Last page kept

Deleting the only page of a layout is refused with a notice.
Acceptance: on a one-page layout the delete action leaves the page and raises one notice.

### R-066 — Page and element counts limited

Adding a 65th page or a 2,001st element to a layout is refused with a notice.
Acceptance: on a layout with 64 pages, adding a page leaves 64 pages and raises a notice;
likewise at 2,000 elements.

### R-067 — Switch modes

The editor menu entry "Design mode" and the shortcut ⌘E (Ctrl+E on Linux and Windows) switch
between perform mode and design mode.
Acceptance: pressing the shortcut twice from perform mode goes to design mode and back.

### R-068 — Controls inert in design mode

In design mode, pressing or dragging a control selects or moves it and sends no parameter
gesture.
Acceptance: a drag on a knob in design mode moves the knob and the fake parameter source
records nothing.

### R-069 — Add an element

Choosing an element kind in the palette adds one at the canvas centre, snapped to the grid,
selected; a control is added unbound and a display without a tap.
Acceptance: adding a knob to an empty page creates one unbound knob centred on the canvas
and selected.

### R-070 — Select by click

Clicking an element selects it alone; Shift-click adds it to or removes it from the
selection; clicking empty canvas clears the selection.
Acceptance: click A, Shift-click B, Shift-click A gives selection {B}; clicking empty canvas
gives {}.

### R-071 — Marquee select

Dragging from empty canvas draws a rectangle and selects every element entirely inside it.
Acceptance: a marquee around two of three elements selects exactly those two.

### R-072 — Move by drag

Dragging a selected element moves the whole selection, snapped to the grid when snapping is
on.
Acceptance: with an 8-unit grid, dragging a selection of grid-aligned elements by (13, 3)
moves each element by (16, 0).

### R-073 — Nudge with arrow keys

In design mode an arrow key moves the selection by 1 canvas unit, or by one grid step with
Shift.
Acceptance: Right moves the selection by (1, 0); Shift+Down by (0, 8) on an 8-unit grid.

### R-074 — Resize by handles

Dragging a handle of a single selected element resizes it, snapped when snapping is on, to
no less than 8 × 8 canvas units.
Acceptance: dragging the bottom-right handle of a 64 × 64 knob by (−100, −100) leaves it
8 × 8.

### R-075 — Grid

The grid step is settable from 2 to 64 canvas units (default 8) and snapping can be turned
off (default on); with snapping off, moves and resizes use whole canvas units.
Acceptance: with snapping off, dragging by (13, 3) moves by (13, 3).

### R-076 — Align

With two or more elements selected, the user aligns their left edges, horizontal centres,
right edges, top edges, vertical centres or bottom edges to those of the selection's bounding
box.
Acceptance: aligning left three elements at x = 10, 40, 90 sets all three to x = 10.

### R-077 — Distribute

With three or more elements selected, the user spaces them so the gaps between neighbours are
equal, horizontally or vertically, keeping the outermost two in place.
Acceptance: three elements of width 10 at x = 0, 15, 90 distributed horizontally end at
x = 0, 45, 90 (±1).

### R-078 — Group

Grouping two or more selected elements makes them one group that is selected, moved and
resized as one.
Acceptance: after grouping A and B, clicking A selects the group, and dragging moves A and B
by the same offset.

### R-079 — Ungroup

Ungrouping a group restores its members as separate elements at their current positions.
Acceptance: after ungroup, clicking A selects A alone and A's position is unchanged.

### R-080 — Group nesting limit

Grouping that would nest groups more than 16 deep is refused with a notice.
Acceptance: grouping a group of depth 16 raises a notice and changes nothing.

### R-081 — Group resize

Resizing a group scales each member's position and size in proportion within the group's
frame.
Acceptance: doubling the width of a group whose members sit at relative x 0 and 50 places
them at relative x 0 and 100 with doubled widths.

### R-082 — Duplicate

Duplicating the selection copies its elements, offset by one grid step right and down, with
new element ids and the same bindings, and selects the copies.
Acceptance: duplicating a knob bound to "cutoff" creates a second knob bound to "cutoff" with a
different id.

### R-083 — Copy and paste

Copy puts the selection on the system clipboard as text; paste adds the clipboard's elements
to the current page with new ids, in this instance, another instance or another process.
Acceptance: copying a knob in one harness and pasting in a second harness adds an equal knob
with a new id to the second's current page.

### R-084 — Invalid paste refused

Pasting clipboard text that does not validate as elements changes nothing and raises a
notice.
Acceptance: pasting the text "hello" leaves the layout unchanged and raises one notice.

### R-085 — Delete elements

Delete or Backspace in design mode removes the selected elements.
Acceptance: deleting a selection of two removes both from the page.

### R-086 — Z-order

The user brings the selection to the front, forward one place, backward one place, or to the
back of the page's drawing order.
Acceptance: on order [A, B, C] (back to front), "to front" on A gives [B, C, A].

### R-087 — Inspector

With one element selected, the inspector shows and edits its position, size, bindings with
their ranges and directions, colour roles, shape overrides, text, typeface and display
settings, and each edit shows on the next frame.
Acceptance: setting a knob's width to 96 in the inspector draws it 96 units wide on the next
frame.

### R-088 — Parameter picker search

The parameter picker lists parameters whose name, id or group path contains the typed text,
ignoring case.
Acceptance: typing "CUT" lists "Filter Cutoff" (id "cutoff") and "LFO Cut Depth", not "Gain".

### R-089 — Picker omits hidden parameters

The parameter picker does not list parameters the plugin flags as hidden.
Acceptance: a hidden parameter matching the search text is absent from the results.

### R-090 — Picker offers compatible parameters

The picker lists only parameters the control can drive: two-state parameters for a switch,
stepped parameters with 2 to 32 steps for a selector and a menu item, any parameter for a
knob, fader, XY axis or macro target.
Acceptance: binding a switch lists a boolean parameter and not a float parameter.

### R-091 — Macro targets

In the inspector the user adds and removes macro targets, from 1 to 16, each with its own
range and direction.
Acceptance: adding a 17th target is refused and the macro keeps 16.

### R-092 — Unbound list

Design mode lists every unbound control and display on every page; choosing an entry shows
its page and selects it.
Acceptance: a layout with an unbound knob on page 3 lists it, and choosing it makes page 3
current with the knob selected.

### R-093 — Undo and redo

Every design-mode change, including theme edits, page changes, imports and reset to default,
can be undone and redone, at least 100 steps back.
Acceptance: after 120 single moves, 100 undos restore the position the element had after
move 20.

### R-094 — Undo restores exactly

Undoing a change gives a layout and theme equal, as documents, to those before the change.
Acceptance: a property test over random sequences of design-mode changes finds every undo
equal to the prior document.

### R-095 — Undo kept across editor reopen

Undo history survives closing and reopening the editor and is discarded when the instance is
destroyed; it is never saved in the project.
Acceptance: move an element, close and reopen the editor, undo: the element is back.

### R-096 — Reset to developer default

"Reset to developer default" replaces the layout and theme with the developer default as one
undoable change.
Acceptance: after reset the layout equals the developer default; one undo restores the prior
layout.

### R-097 — Design changes made while audio runs

Every design-mode change takes effect without reloading the plugin, restarting audio or
recompiling.
Acceptance: in the reference plugin under Bitwig, adding, binding and deleting a knob during
playback produces no audio dropout and no plugin reload (manual checklist item).

### R-098 — Colour roles defined

A theme gives a colour, with alpha, to every colour role of the fixed role set.
Acceptance: decoding a theme that lacks the role "accent-3" fails validation naming
"accent-3".

### R-099 — Elements use colour roles

Each colour slot of an element names a colour role, defaulting to its kind's standard role,
and switching the theme recolours every element through its roles.
Acceptance: a knob whose arc slot is "accent-3" draws the new theme's "accent-3" colour after
a theme switch.

### R-100 — Typefaces

A theme names a typeface for each of the roles body, heading and value, each a built-in font
or a font asset of the theme; labels choose one of the three.
Acceptance: a label set to "heading" draws with the theme's heading typeface.

### R-101 — Surface fills

Each surface role of a theme has a fill: a solid colour role, a linear gradient between two
colour roles at an angle, grain over a colour role with an amount from 0 to 1, or an image
asset.
Acceptance: a panel on a surface with a gradient fill draws the first role at the gradient's
start and the second at its end.

### R-102 — Shape tokens

A theme sets corner radius (0–64), border width (0–8), knob style (arc, pointer or filled),
track thickness (1–24) and handle size (4–48), and an element may override any of them for
itself.
Acceptance: a knob overriding knob style "pointer" draws as pointer while others draw in the
theme's style.

### R-103 — Theme edits preview live

In design mode the theme editor changes the active theme, and every change shows on the next
frame.
Acceptance: changing "accent-1" redraws accent-1 elements in the new colour on the next frame.

### R-104 — Contrast ratio shown

The theme editor shows the contrast ratio, by the WCAG 2.2 formula, of each text role
("text", "text-muted") on each background role ("background", "surface", "surface-raised").
Acceptance: black text on a white background shows 21.0:1.

### R-105 — Contrast warning

The theme editor marks every pair from R-104 whose ratio is below 4.5:1.
Acceptance: grey #777777 on white (4.48:1) is marked; #767676 on white (4.54:1) is not.

### R-106 — Built-in themes

The themes "Studio Dark", "Studio Light" and "High Contrast" are always available and cannot
be overwritten or deleted.
Acceptance: saving a user theme named "Studio Dark" asks for another name; the built-in is
unchanged.

### R-107 — High-contrast ratios

Every pair from R-104 in "High Contrast" has a contrast ratio of at least 7:1.
Acceptance: a unit test computes all six ratios of the built-in theme and each is ≥ 7.0.

### R-108 — Choose a theme

The editor menu lets the user choose any built-in or library theme as the active theme, also
when the developer has switched design mode off.
Acceptance: choosing "High Contrast" makes it the active theme on the next frame.

### R-109 — Focus indicator

The keyboard-focused control draws an outline in the "focus" colour role, which every
built-in theme sets to a contrast of at least 3:1 against "background" and "surface".
Acceptance: a unit test checks the focus ratios of the three built-in themes.

### R-110 — Project round trip

Saving a plugin instance's state and loading it into a new instance restores the layout,
theme, assets, current page and window size exactly.
Acceptance: under clap-validator's state tests and a unit round trip, the loaded instance
state equals the saved one as documents.

### R-111 — Save holds the latest edit

A state save made after a design-mode change is complete contains that change.
Acceptance: release a dragged element, request a save on the next frame: the saved layout
has the new position.

### R-112 — Layout received at first editor open

An instance with no saved instance state receives its layout and theme when its editor first
opens.
Acceptance: an instance whose editor never opened saves no layout; after the first open, a
save contains one.

### R-113 — New instance layout

A new instance's layout is the plugin's user default layout when one is set, otherwise the
developer default.
Acceptance: with a user default set, a new instance's first layout equals it; after clearing
it, a newer instance gets the developer default.

### R-114 — New instance theme

A new instance's theme is the plugin's user default theme when set, otherwise the suite
default theme when set, otherwise the developer default theme.
Acceptance: the three cases each give the expected theme in a fresh instance.

### R-115 — Existing instances unchanged by defaults

Setting or clearing a user default or the suite default theme does not change any instance
that already has a layout.
Acceptance: an open instance keeps its theme after the suite default theme changes.

### R-116 — Loaded state shown while open

When the host loads instance state while the editor is open, the editor shows the loaded
layout on the next frame.
Acceptance: loading a saved state into an instance with an open editor shows that state's
current page on the following frame.

### R-117 — Unreadable state falls back

When saved instance state cannot be read (corrupt or from a newer schema), the editor shows
the user default, else the developer default, with a notice saying the saved layout could not
be read and is kept.
Acceptance: loading truncated state shows the developer default and one notice with that
text.

### R-118 — Unreadable state preserved

While an unreadable saved layout is kept, every state save writes its original bytes
unchanged.
Acceptance: load unreadable bytes X, save: the saved state contains X byte for byte.

### R-119 — Editing blocked while preserving

While an unreadable saved layout is kept, design mode, layout import and theme choice are
unavailable; controls still operate in perform mode.
Acceptance: in this state the editor menu offers no design mode, and a knob drag still sends
a gesture.

### R-120 — Discard preserved state

The notice of R-117 offers "Discard saved layout"; choosing it, after confirmation, drops the
kept bytes so that the next save writes the current layout, and editing becomes available.
Acceptance: after discarding, a save contains the fallback layout and design mode is offered.

### R-121 — Older schema migrated

Instance state, layouts, themes and packages of an older schema version load by migration
that keeps every page, element and binding.
Acceptance: each fixture of every past schema version loads with the same page, element and
binding count as the fixture.

### R-122 — Asset cap per instance

Adding a font or image whose decoded size would bring the assets of the instance's layout and
theme above 4 MiB is refused with a notice.
Acceptance: with 3.5 MiB of assets, adding a 1 MiB PNG is refused and assets stay at 3.5 MiB.

### R-123 — Image and font formats

Image assets are PNG files and font assets are TrueType or OpenType files; other files are
refused with a notice.
Acceptance: adding a JPEG as an image asset is refused with a notice naming the accepted
format.

### R-124 — Layout edits never automatic

Loading, migrating or importing never removes, renames or rebinds an element of the user's
layout; only a user action does.
Acceptance: loading a layout whose 3 controls are bound to absent parameters keeps all 3,
bound to the same ids.

### R-125 — Library locations

The library is the folder "mutable-gui" in the platform's user data directory, with one
"layouts/<plugin CLAP id>" folder per plugin and one shared "themes" folder.
Acceptance: on macOS the reference plugin saves layouts under
`~/Library/Application Support/mutable-gui/layouts/<its CLAP id>/`.

### R-126 — Save a layout

In design mode the user saves the current layout to the library under a name of 1 to 64
characters.
Acceptance: saving as "Live" creates a library entry "Live" holding the current layout.

### R-127 — Name collision asks

Saving a layout or theme under a name already in the library asks whether to replace it; the
existing file is unchanged unless the user confirms.
Acceptance: saving "Live" twice and declining leaves the first file byte-identical.

### R-128 — Save a theme

The user saves the active theme to the shared themes folder under a name of 1 to 64
characters.
Acceptance: a theme saved from plugin A appears in the theme list of plugin B.

### R-129 — Export a package

The user exports the layout, the theme or both, with their assets, to a `.mgui` file at a
location chosen in the system file dialog.
Acceptance: exporting both and importing the file into a new instance gives a document-equal
layout and theme.

### R-130 — Import a package

The user imports a `.mgui` file chosen in the system file dialog; its layout and theme replace
the active ones as one undoable change.
Acceptance: importing a package and pressing undo once restores the prior layout and theme.

### R-131 — Import from another plugin

Importing a package whose source plugin has a different CLAP id raises a notice naming that
plugin; bindings to ids this plugin has are bound, the rest unbound.
Acceptance: a package from plugin X with ids "cutoff" (present) and "drive" (absent) imports
with "cutoff" bound, "drive" unbound, and one notice naming X.

### R-132 — Set and clear the user default

The user sets the current layout and theme as the plugin's user default, and clears it.
Acceptance: after set, a new instance uses it; after clear, a new instance uses the developer
default.

### R-133 — Set and clear the suite default theme

The user sets the active theme as the suite default theme, and clears it.
Acceptance: after set in plugin A, a new instance of plugin B (with no user default) uses that
theme.

### R-134 — Library writes are all or nothing

A library save either writes the whole new file or leaves the previous file unchanged, and a
failure raises a notice.
Acceptance: a save into a read-only library folder raises a notice and the folder's contents
are unchanged.

### R-135 — Library listing

The library lists this plugin's saved layouts and all shared themes by name, and marks files
it cannot read as unreadable instead of hiding them.
Acceptance: a corrupt file in the themes folder appears in the list marked unreadable.

### R-136 — Delete from the library

The user deletes a saved layout or theme after confirming; built-in themes cannot be deleted.
Acceptance: confirming deletion of "Live" removes its file; declining keeps it.

### R-137 — Package file size limit

A package file larger than 8 MiB is refused before its contents are read.
Acceptance: importing a 9 MiB file is refused with a notice and the importer reads at most
8 MiB + 1 byte.

### R-138 — Package asset limit

A package whose decoded assets exceed 4 MiB is refused.
Acceptance: a package with 4.5 MiB of decoded assets is refused with a notice.

### R-139 — Package structure limits

A package with more than 64 pages, more than 2,000 elements, group nesting deeper than 16,
or a text field longer than 4,096 bytes is refused.
Acceptance: one fixture per limit, each one over it, is refused with a notice naming that
limit.

### R-140 — Assets must decode

Every font and image of a package must decode before anything is applied; one failure refuses
the whole package.
Acceptance: a package with a valid PNG and a corrupt font is refused and neither is applied.

### R-141 — Newer schema refused

A document whose schema version is newer than the library supports is refused with a notice
naming both versions.
Acceptance: a version-99 package is refused with "made by a newer version (99; this one reads
up to 1)".

### R-142 — Unknown fields refused

A document holding a field its schema version does not define is refused.
Acceptance: a package with an extra top-level field "script" is refused with a notice naming
"script".

### R-143 — Refused import changes nothing

A refused import, paste or library load leaves the layout, theme, library and undo history as
they were.
Acceptance: before and after each refused fixture of R-137–R-142, the instance state and undo
depth are equal.

### R-144 — Malformed input never crashes

Decoding arbitrary bytes as a package, instance state or clipboard text returns an error or a
valid document and never panics or hangs.
Acceptance: a property test feeding 10,000 random and truncated inputs per decoder completes
without panic, each input in under 1 s.

### R-145 — Keyboard focus order

In perform mode, Tab moves keyboard focus to the next control of the current page in reading
order (by top edge, then left edge) and Shift+Tab to the previous, wrapping around.
Acceptance: controls at (0,0), (100,0), (0,100) receive focus in that order and then the first
again.

### R-146 — Keyboard adjustment

Up and Right raise the focused control's value by 1 % of its range (0.1 % with Shift), or one
step for a stepped parameter; Down and Left lower it; each key press is one gesture.
Acceptance: Up on a knob at 0.5 with range 0–1 sets 0.51; Shift+Up sets 0.501.

### R-147 — Keyboard value entry

Enter on the focused control opens its value field as in R-027.
Acceptance: Tab to a knob, Enter, type "0", Enter: the parameter is set to the plugin's parse
of "0".

### R-148 — Escape closes

Escape closes an open menu or value field without changing any value.
Acceptance: open a value field, type "5", press Escape: the parameter is unchanged and the
field is closed.

## Non-functional requirements

- Platforms: macOS on Apple silicon (aarch64-apple-darwin) is the version 1 gate, tested on
  macOS 26.7.1 with Bitwig Studio 5.3.13. Linux x86_64 (X11) and Windows x86_64 must compile
  and pass all non-host tests in CI; they are not tested in a host for version 1.
- Plugin format: CLAP. A VST3 build exists only if nice-plug produces it with no
  VST3-specific code; its failures are recorded, not fixed.
- Audio safety (P1): no allocation, lock, wait or system call by this library on the audio
  thread; the plugin's audio output is bit-identical with the editor closed, open in perform
  mode and open in design mode. Check: allocation test over the reference plugin's process
  call with the editor open; an offline render of the reference plugin compared sample for
  sample in the three editor states.
- Layout safety (P2): no layout is lost silently; every failed load, save or import is
  reported by a notice and leaves the last good layout in place. Check: R-117–R-120,
  R-134, R-143.
- Frame time: at most 4 ms of editor CPU time per frame for a 300-element page at 60 frames
  per second, release build, on this M-series Mac. Check: benchmark of the frame function
  over the 300-element fixture page.
- Idle cost: zero frames drawn while idle as defined in R-053.
- Editor open: the editor draws its first frame within 250 ms of the host's request to show
  it, for the reference plugin's default layout. Check: timed harness open, release build.
- Package load: decoding and validating a 4 MiB-asset package takes at most 200 ms. Check:
  benchmark over the largest valid fixture.
- Picker search: results for 2,000 parameters within 16 ms of a keystroke. Check: benchmark.
- Scalar tap push: at most 100 ns, zero allocations. Audio tap push: zero allocations and no
  lock, cost linear in the frames pushed. Check: benchmarks and allocation tests.
- Undo memory: 100 undo steps of a 2,000-element layout with 4 MiB of assets hold at most
  64 MiB. Check: memory measurement test.
- Accessibility: contrast readout and warnings (R-104, R-105); High Contrast at 7:1 (R-107);
  UI scale 0.5–4.0 (R-059); full keyboard operation in perform mode (R-145–R-148). Screen
  readers are not supported in version 1.
- Security: the library opens no network connection; packages, clipboard text and saved
  state are untrusted data and hold no executable content; every limit of R-137–R-142 holds.
- Code: Rust edition 2024; minimum supported Rust 1.95; workspace lints are clippy `all` and
  `pedantic` as warnings with `unwrap_used`, `expect_used`, `panic`, `todo`,
  `unimplemented`, `dbg_macro`, `print_stdout`, `print_stderr` denied; `unsafe_code` is
  forbidden in the core crate and allowed in the adapter only with a `// SAFETY:` comment on
  each block; `cargo fmt --check` and `cargo clippy -- -D warnings` pass.
- Licence: MIT OR Apache-2.0 for the library crates and the reference plugin; not published
  to crates.io in version 1.

## Data model

All documents are JSON objects with two leading fields, `format` and `version`. Field names
are snake_case. Unknown fields are refused (R-142).

- **Instance state** (`format: "mutable-gui/instance"`, `version: 1`): `layout` (Layout),
  `theme` (Theme), `assets` (list of Asset), `current_page` (page id), `window`
  (`{ width, height }` in logical pixels). Stored by nice-plug under the persisted-field key
  `mutable-gui`. When an unreadable state is kept (R-118), the stored value is the original
  string and none of these fields are produced.
- **Layout** (`format: "mutable-gui/layout"`): `canvas` (`{ width, height }`, 200–4,000 each),
  `grid` (`{ step, snap }`), `pages` (1–64 Page).
- **Page**: `id` (UUID v4 string), `name` (1–64 characters), `elements` (list of Element in
  drawing order, back to front).
- **Element**: `id` (UUID v4 string, unique in the layout), `kind` (one of `knob`, `fader`,
  `switch`, `xy_pad`, `macro`, `selector`, `menu`, `page_tabs`, `oscilloscope`, `spectrum`,
  `level_meter`, `gr_meter`, `label`, `panel`, `image`, `group`), `frame`
  (`{ x, y, width, height }` in canvas units), `colours` (map of slot name → colour role
  name), `shape` (optional shape-token overrides), and kind-specific fields:
  - knob, fader, switch, selector: `binding` (Binding); fader adds `orientation`
    (`vertical` | `horizontal`); selector adds `presentation` (`segments` | `dropdown`).
  - xy_pad: `x` and `y` (Binding each).
  - macro: `targets` (1–16 Binding).
  - menu: `label` (text) and `items` (list of `{ text, action }`, action being
    `{ open_page: page id }` or `{ set: { param, step } }`).
  - page_tabs: `orientation`.
  - oscilloscope: `tap`, `window_ms` (5–500). spectrum: `tap`, `fft_size`, `floor_db`.
    level_meter: `tap`. gr_meter: `tap`, `range_db` (6 | 12 | 24 | 48).
  - label: `text` (≤ 4,096 bytes), `typeface` (`body` | `heading` | `value`), `size`
    (6–200), `align` (`left` | `centre` | `right`).
  - panel: `surface` (surface role name).
  - image: `asset` (asset id), `fit` (`contain` | `cover` | `stretch`).
  - group: `children` (list of Element, nesting ≤ 16). Element counts (R-066, R-139)
    include groups and every member at any depth.
- **Binding**: `param` (the plugin's stable string parameter id), `min` and `max`
  (normalized 0–1, min < max), `reversed` (bool).
- **Theme** (`format: "mutable-gui/theme"`): `name`, `colours` (every colour role → RGBA
  hex `#rrggbbaa`), `typefaces` (`body`, `heading`, `value` → built-in font name or asset
  id), `surfaces` (surface role → Fill), `shape` (radius, border, knob_style,
  track_thickness, handle_size).
- **Colour roles** (fixed set, version 1): `background`, `surface`, `surface-raised`,
  `border`, `text`, `text-muted`, `accent-1` … `accent-8`, `positive`, `warning`,
  `negative`, `modulation`, `focus`, `disabled`.
- **Surface roles** (fixed set, version 1): `canvas`, `panel`, `control`, `display`.
- **Fill**: `{ solid: role }` | `{ gradient: { from: role, to: role, angle_deg } }` |
  `{ grain: { role, amount } }` | `{ image: asset id }`.
- **Asset**: `id` (UUID v4 string), `kind` (`font` | `png`), `data` (base64 of the file).
- **Package** (`format: "mutable-gui/package"`): `name`, `author` (optional), `created`
  (RFC 3339 time), `source` (`{ clap_id, plugin_version, library_version }`), `layout`
  (optional), `theme` (optional, at least one of the two present), `assets`.
- **Clipboard text**: a document with `format: "mutable-gui/elements"`, `version`, `elements`
  and `assets`.
- **Signal tap** (declared by the developer, not stored): `name`, `kind` (`audio` with
  `channels` 1 | 2 and `capacity` frames, or `scalar`).

Identifiers that never change once version 1 is released: the format names above; schema
version numbers (an integer per format, starting at 1, raised for every change); the file
extension `.mgui`; the persisted-field key `mutable-gui`; the library folder names
`mutable-gui`, `layouts`, `themes`; the colour role, surface role, element kind and field
names of version 1; the built-in theme ids `studio-dark`, `studio-light`, `high-contrast`.
Parameter ids, tap names and the CLAP id belong to the plugin developer, who must keep them
stable.

## Edge cases

- A parameter is renamed or removed in a plugin update: controls bound to it stay, drawn as
  unbound (R-037), and appear in the unbound list (R-092).
- The host closes the editor during a drag: every begun gesture is ended (R-025).
- The host resizes the window during a drag: the drag continues in canvas units at the new
  scale.
- Two instances of the same plugin are open: each has its own instance state and undo
  history; the library is shared and the last save to a name wins after the R-127 question.
- The library folder is missing or not writable: the editor works from defaults and instance
  state; saves raise a notice (R-134).
- A library file is changed by another instance or by hand while listed: the list is re-read
  when the library view opens.
- An audio tap is never read: pushes copy nothing (R-041) and drop when full (R-043).
- The plugin declares no taps: every display shows "No signal" (R-052) and the tap picker is
  empty.
- The plugin has no parameters: the generated layout has one empty page named after the
  plugin.
- The developer's embedded package is from another plugin: it is used, with bindings resolved
  as in R-131, and no notice.
- A layout's canvas is changed to a smaller size: elements outside the new canvas keep their
  positions and are drawn clipped; the change is undoable like any other.
- A font asset decodes but lacks glyphs for a label's text: missing glyphs are drawn with the
  built-in body font.
- Keyboard input is taken by the host before the plugin window sees it: the editor menu offers
  every action that has a shortcut.
- The sample rate changes: the developer sets the tap's new rate (R-046); displays clear their
  history.
- The host loads state into an instance whose editor is closed: the state is decoded when the
  editor next opens.

## Out of scope

- Screen-reader support (the window backend has no AccessKit support).
- Host-automatable macros; macros exist only in the editor.
- The host's own parameter menu items (the CLAP context-menu extension).
- Building host remote-control pages from layout pages.
- Multi-touch: two simultaneous touches; touch input works as the operating system's mouse
  emulation.
- Adapters for frameworks other than nice-plug, including clack and nih-plug.
- VST3-specific work, AU, LV2 and standalone builds.
- Testing in a host on Linux or Windows.
- Online sharing, accounts or any network feature.
- Scripts, expressions or custom code inside layouts, themes or packages.
- Third-party element types supplied by plugins or users.
- Raw colours on individual elements.
- Responsive layouts that reflow with window shape, and canvases per page.
- Animations and transitions.
- Undo history saved in the project.
- A Rust API for building layouts in code.
- A MIDI keyboard element.
- Translations of the editor's own text; it is in English.
- Audio preset (patch) management.
- Publishing the crates to crates.io.

## Not yet specified

None.
