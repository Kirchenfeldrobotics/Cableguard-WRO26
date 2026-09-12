# CableGuard design system

The webapp implements the Claude Design project **CableGuard v2** (`CableGuard v2.dc.html`,
with the rope strip from `RopeStripBold.dc.html`). This file is the reference for anyone
adding screens: use these tokens and components rather than new one-off styles.

## Principles

- **Operator first.** Large numbers, short labels, one status colour per meaning. The
  screen is read on site, often in a hurry.
- **Black, white, one red.** Colour is reserved for status. Everything else is ink on
  white or light grey.
- **Never invent data.** If the robot or backend does not provide a value, show `—`
  (`NOT_AVAILABLE` in `lib/format.ts`) and explain it in a `title` tooltip. Controls for
  features that do not exist yet are rendered **disabled**, never wired to fake state.

## Tokens

All tokens live in `app/globals.css` (`@theme`) and are used as Tailwind classes, for
example `bg-surface`, `text-text-muted` or `rounded-card`. Do not write hex values in
components.

### Colour

| Token | Hex | Use |
| --- | --- | --- |
| `ink` | `#0A0A0A` | Text, sidebar, primary buttons |
| `ink-soft` | `#2C2C2C` | Sidebar dividers, primary hover |
| `text-muted` | `#4A4A4A` | Secondary text, card labels |
| `text-subtle` | `#6E6E6E` | Table headers, notes, back links |
| `text-faint` | `#8C8C8C` | Sidebar meta, disabled text |
| `text-inverse-muted` | `#D8D8D8` | Inactive nav items on ink |
| `canvas` | `#FFFFFF` | Page background |
| `surface` | `#F2F2F2` | Cards and panels |
| `surface-hover` | `#F7F7F7` | Table row hover |
| `surface-strong` | `#E4E4E4` | Rows inside panels, muted indicators |
| `neutral-soft` | `#E8E8E8` | Neutral pill, disabled primary |
| `line` / `line-strong` | `#EDEDED` / `#E2E2E2` | Table rules |
| `border` | `#DADADA` | Inputs and secondary buttons |
| `mark-muted` / `mark-tick` | `#BFBFBF` / `#D6D6D6` | Unchanged marks, older trend bars |
| `danger` | `#C11119` | Broken wire (LF), Live and Link lost badges |
| `danger-strong` / `danger-deep` | `#A50C13` / `#7F080E` | Emergency stop, red text |
| `danger-soft` | `#FBE3E5` | Alert banner, red rows |
| `warning` / `warning-ink` / `warning-soft` | `#E8A33D` / `#8A5A00` / `#FDF0DC` | Corrosion (LMA) |
| `success` / `success-ink` / `success-soft` / `success-line` | `#1E9E4A` / `#14713A` / `#E9F8EE` / `#C3E7CF` | Connected, running |
| `video` / `video-stripe` / `video-text` | `#1A1D1F` / `#212528` / `#C9CDCF` | Camera tiles |

Defects have no severity in the backend yet, so the design's "Action required" red and
"Monitor" amber are mapped to the detector classes (`kindTone` in `lib/defects.ts`).

### Typography

Poppins for UI text, IBM Plex Mono for measurements, ids and timestamps. Both are loaded
with `next/font` in `app/layout.tsx` and exposed as `font-sans` and `font-mono`.

| Role | Style |
| --- | --- |
| Page and section title | 30px / 800, uppercase, `-0.01em` tracking |
| Stat card value | 22px / 700 (fact cards 20px, comparison cards 26px) |
| Body and labels | 13–14px / 400–600 |
| Status badge | 12px / 700, uppercase, `.05em` tracking |
| Table header | 12px / 600, `text-subtle` |
| Numbers, positions, ids | Plex Mono 11–13px |

### Shape and spacing

| Token | Value | Use |
| --- | --- | --- |
| `rounded-shell` | 18px | Sidebar |
| `rounded-card` | 14px | Cards, panels, camera tiles |
| `rounded-control` | 10px | Buttons, inputs, nav items |
| `rounded-row` | 9px | Log rows |
| `rounded-full` | | Badges and indicators |

Rhythm: 38px between page sections, 18px between a heading and its content, 14px gap
between cards, 12px outer padding around the app.

## Layout

- `app/layout.tsx`: 236px sticky black sidebar on the left and main content up to 1280px
  wide. Below the `lg` breakpoint the sidebar stacks on top with a scrollable nav.
- The sidebar footer always shows the robot link (green or red dot), the time since the
  last packet and the local clock.

## Components

| Component | File | Notes |
| --- | --- | --- |
| `PageHeader`, `SectionTitle`, `HeadingMeta` | `components/ui/heading.tsx` | Title row with badges and actions |
| `Button`, `ButtonLink`, `RingIcon` | `components/ui/button.tsx` | `primary`, `secondary`, `danger`; `md` or `lg` (58px action bar) |
| `Dropdown` | `components/ui/dropdown.tsx` | Listbox in the control shape; a native `<select>` cannot be styled to the tokens |
| `Pill` | `components/ui/pill.tsx` | `status` variant for headers, `tag` inside tables |
| `StatCard`, `FactCard`, `Panel`, `CardGrid` | `components/ui/card.tsx` | Stat cards carry a 46px status circle |
| `Table`, `Th`, `Td`, `LinkRow` | `components/ui/table.tsx` | Rows navigate on click and Enter |
| `LogRow`, `InfoRow` | `components/ui/log-row.tsx` | Tinted rows for detections and changes |
| `FactList` | `components/ui/fact-list.tsx` | Label and value rows on a panel |
| `Notice`, `StatusMessage`, `BackLink` | `components/ui/feedback.tsx` | Alerts, loading, empty and error states |
| `RopeStrip`, `defectMarks`, `DefectLegend` | `components/rope/` | Unrolled rope with metre scale and defect marks |
| `CameraFeed` | `components/camera/camera-feed.tsx` | Live JPEG stream or striped placeholder |
| `RunStatePill` | `components/inspection/run-state-pill.tsx` | Link lost, Live or Idle |
| `Sidebar` | `components/layout/sidebar.tsx` | Navigation and link status |

## Patterns

- **Status circle meanings** (`StatCard` `indicator`): `success` connected, `danger`
  link lost, `alert` needs review, `warning` detections, `ring` current selection
  (rope, position), `solid` motion, `muted` neutral or unavailable.
- **Rope strip**: red marks for broken wires, amber for corrosion. In comparisons, marks
  also found in the reference run are thin and grey, new ones are wider. The black
  vertical line is the robot position (only drawn when a position is known).
- **States**: every data view handles loading (`Loading…`), error (red text) and empty
  (a sentence saying what is missing and what to do).
- **Destructive actions** need a second click (`Remove` becomes `Confirm remove`).
- **Emergency stop** is never disabled while the server socket is open, even if the
  robot is reported offline. The server answers with an error if it cannot forward it.
