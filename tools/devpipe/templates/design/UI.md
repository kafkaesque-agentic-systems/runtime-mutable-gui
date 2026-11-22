# UI design: <<project name>>

How the product looks and behaves for the people who use it. Screens are numbered and never
renumbered. A mockup under `design/ui/` shows layout, content and states; it is a picture of
intent, not code to port: the product is built with the toolkit named under Tooling. Once a
screen exists, its `Built:` line says where to see it (an http address, a file such as a
screenshot the tests make, or `run <command>` that prints its HTML), and
`devpipe ui compare` puts it beside the mockup.

Surface: <<what the interface runs on, for example "Android phone and tablet", "desktop web browser", "plugin window inside a DAW", "terminal"; write "none" for a product nobody looks at, and add a line "Reason: …">>

## Surfaces

- <<platform>>: <<sizes and form factors, input methods, orientation, minimum OS or browser, limits the host imposes>>

## Users and tasks

- <<actor>>: <<their most frequent task>>; <<where and how they do it: device, attention, frequency, expertise>>

## Screens

### S-01 — <<name>>

Purpose: <<the one thing a person does here>>
Serves: <<R-001, R-004, or none>>
Shows: <<the content, most important first>>
Actions: <<what can be done, and where each leads: S-02, back, a dialog>>
States: <<empty: …; loading: …; error: …; offline: …>>
Mockup: design/ui/S-01-<<slug>>.html
Built: not yet
Status: PROPOSED

## Flows

1. <<task>>: S-01 → S-02 → S-03; <<what ends it, and what the person sees when it fails halfway>>

## Navigation

<<The structure (tabs, stack, drawer, single window), what back does, and what is reachable from where.>>

## Visual language

The values are in `design/ui/tokens.css`; the product's theme is written from that file.

- Colour: <<roles and their pairs, light and dark>>
- Type: <<families, scale, weights>>
- Space and shape: <<spacing scale, radii, elevation>>
- Motion: <<durations, what animates, what happens under reduced motion>>
- Icons and imagery: <<icon set, illustration style>>

## Components

| Component | Used on | Built from |
|---|---|---|
| <<name>> | <<S-01, S-03>> | <<the toolkit component it is, or "custom">> |

## Accessibility

- <<contrast target; smallest touch or click target; text scaling range; screen reader labels; keyboard access; right-to-left; colour-blind safety>>

## Tooling

| Name | Role |
|---|---|
| <<a name from design/STACK.md>> | <<UI toolkit, components, icons, fonts, navigation, previews, screenshot tests>> |

## Not yet decided

None.
