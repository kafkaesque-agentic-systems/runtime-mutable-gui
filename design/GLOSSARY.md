# Glossary: mutable-gui

Domain terms only: no implementation detail. One meaning per term; code, tests and tickets
use these words.

- **Adapter**: the part of the library that connects the framework-neutral core to one
  plugin framework, giving the core the plugin's parameters, the editor window and the saved
  state. Version 1 has one adapter, for nice-plug.
- **Asset**: a font file or an image file carried inside a theme, a layout, a package or an
  instance's state, so that the interface looks the same on any computer.
- **Binding**: the link from a control to one parameter, with the part of the parameter's
  range the control covers and its direction. A control has one binding, except an XY pad
  (two) and a macro (one or more). Not to be confused with a signal tap, which feeds a display.
- **Canvas**: the fixed logical drawing area of a layout, with a width and height in logical
  units that the layout author sets; every page of the layout uses it. The window shows the
  canvas scaled uniformly; a window whose shape differs shows bars beside or above it. Not to
  be confused with the window, whose size the host and the user control.
- **Colour role**: a named colour in a theme, such as "background", "text" or "accent 3".
  Elements name colour roles, never colours, so that changing the theme recolours them.
- **Control**: an element the user operates in perform mode: knob, fader, switch, XY pad,
  macro, selector, menu element, page tabs. Most controls are bound to parameters; page tabs
  and some menu items open pages instead. Not to be confused with a display, which only shows
  data.
- **Control menu**: the built-in menu that opens on a control in perform mode (right-click or
  long press) to reset it, type a value or lock fine adjustment. Not to be confused with the
  menu element and the editor menu.
- **Decoration**: an element bound to nothing: label, panel, image.
- **Design mode**: the state of the editor in which the user adds, moves, resizes, groups,
  binds and removes elements, manages pages and edits the theme. Operating a control in
  design mode selects it; it never changes a parameter.
- **Developer default**: the layout and theme the plugin developer ships inside the plugin,
  or, when the developer ships none, the layout the library generates from the plugin's
  parameters.
- **Display**: an element that draws data from a signal tap: oscilloscope, spectrum,
  level meter, gain-reduction meter.
- **Editor**: the plugin's window as a whole: the current page of the layout plus the editor
  menu and the notices.
- **Editor menu**: the menu, always reachable from a button no layout can remove or cover,
  that switches modes, lists pages, chooses themes and opens the library actions.
- **Element**: one item placed on a page: a control, a display or a decoration.
- **Gesture**: one continuous change of a parameter by the user, from press to release,
  reported to the host as a single edit so that automation recording and host undo treat it
  as one action.
- **Group**: elements joined so that they are selected, moved and resized together. A group
  may contain groups.
- **Instance state**: everything the library saves inside one plugin instance in the DAW
  project: the active layout, the active theme, their assets, the current page and the
  window size.
- **Layout**: the editable arrangement of one plugin instance: its canvas, its pages, their
  elements and the elements' bindings. Not to be confused with the theme, which says how
  things look.
- **Library**: the folder on the user's computer where the user's saved layouts (one set per
  plugin) and themes (one set shared by every plugin that uses mutable-gui) are kept. Not to
  be confused with the instance state, which travels inside the DAW project.
- **Macro**: a control bound to several parameters at once, each through its own range and
  direction. Moving a macro moves every target parameter as if the user had moved each one;
  the host sees and records only the targets. A macro is not a host parameter.
- **Menu element**: a control the user places on a page whose items open a page or choose a
  value of a stepped parameter.
- **Modulation band**: the mark a control draws between a parameter's base value and the
  value the host's modulation currently gives it.
- **Notice**: a message the editor shows until the user dismisses it, used for refused
  imports, failed saves and unreadable state.
- **Package**: one exported file holding a layout, a theme, or both, together with the assets
  they use, made to be shared and imported. Its file name ends in `.mgui`.
- **Page**: one screen of a layout. A layout has one or more pages and the user moves between
  them in perform mode.
- **Perform mode**: the state of the editor in which controls change parameters and the
  layout cannot be edited. The editor opens in perform mode.
- **Reference plugin**: the demonstration plugin in this repository that adopts the library;
  it is how version 1 is shown to work.
- **Signal tap**: a named stream of data that the plugin's DSP publishes for displays, either
  audio samples or a single changing number such as gain reduction. The developer declares
  the taps; the user chooses which display shows which tap.
- **Stepped parameter**: a parameter with a fixed number of values, such as an on/off switch,
  a waveform choice or an integer count. A two-state parameter is a stepped parameter with
  exactly two values.
- **Suite default theme**: the theme the user has chosen, in the library, for new instances
  of every plugin that uses mutable-gui, unless that plugin has its own user default.
- **Theme**: the visual tokens of an interface (colour roles, typefaces, surfaces, borders,
  control shapes), separate from any layout so that one theme can dress many plugins.
- **Unbound**: the state of a control whose parameter, or a display whose signal tap, the
  plugin does not have. It stays in the layout, drawn as unbound, until the user rebinds or
  removes it.
- **User default**: the layout and theme the user has chosen, in the library, to show in every
  new instance of one plugin in place of the developer default.
