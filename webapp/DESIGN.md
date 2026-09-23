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
| `danger-strong` / `danger-deep` | `#A50C13` / `#7F080E` | Red text, `danger` buttons |
| `danger-soft` | `#FBE3E5` | Alert banner, red rows |
| `warning` / `warning-ink` / `warning-soft` | `#E8A33D` / `#8A5A00` / `#FDF0DC` | Corrosion (LMA) |
| `success` / `success-ink` / `success-soft` / `success-line` | `#1E9E4A` / `#14713A` / `#E9F8EE` / `#C3E7CF` | Connected, running |
| `video` / `video-stripe` / `video-text` | `#1A1D1F` / `#212528` / `#C9CDCF` | Camera tiles |

Defects have no severity in the backend yet, so the design's "Action required" red and
"Monitor" amber are mapped to the two buckets the robot sorts its detector classes into
(`kindTone` in `lib/defects.ts`): local faults are red, loss of metallic area amber. The
model knows eight classes and seven of them are local faults, so colour alone is coarse:
the class itself is always shown as text next to it (`defectClassLabel` in `lib/format.ts`).

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
  wide.
- The sidebar footer always shows the robot link (green or red dot), the time since the
  last packet and the local clock.
- **Phones and tablets** (below `lg`): the sidebar is replaced by a sticky black top bar
  (logo, robot link with the time since the last packet, sign out) and a fixed bottom tab
  bar with the same destinations under short labels (Status, Live, Ropes, Compare, Robot).
  The tab bar follows the sidebar's rules: Live only appears while a run is recording, and
  carries a red dot then. Both bars pad themselves with the safe-area insets
  (`viewportFit: "cover"`), and `--tabbar-h` is the tab bar's height for anything that
  has to sit above it.

### Phone rules

- Below `sm`, headings drop to 24px, stat and fact cards go two to a row with a 20px
  status circle, and main action buttons fill the row.
- Tables become one card per row (`.stack-table` in `globals.css`). Give every `Td` a
  `label` (its column header), mark the identifying cell `phone="primary"` and a row
  action `phone="end"`. Columns that only ever show `—` because the backend has no data
  for them get `phone="hide"`.
- Inputs use 16px text below `sm`, otherwise iOS zooms the page when they are focused.
- The live screen puts what is being tracked first (numbers, position on rope, cameras,
  then drive, rope socket and log), the cameras swipe sideways, and the motion state with Stop is
  pinned above the tab bar. That pinned Stop replaces the one in the drive panel, so
  there is never more than one Stop on screen.

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
| `RopeStrip`, `findingMarks`, `DefectLegend` | `components/rope/` | Unrolled rope with metre scale and finding marks |
| `CameraFeed` | `components/camera/camera-feed.tsx` | Live JPEG stream, dimmed with a "Not live" badge when frames stop, or striped placeholder |
| `DetectionFrame` | `components/camera/detection-frame.tsx` | The stored JPEG a defect was found in, with its box on top; fetched as a blob because an `<img>` cannot send the token |
| `RunStatePill` | `components/inspection/run-state-pill.tsx` | Link lost, Live or Idle |
| `Sidebar` | `components/layout/sidebar.tsx` | Desktop navigation and link status |
| `MobileTopBar`, `TabBar` | `components/layout/mobile-nav.tsx` | Phone navigation and link status |
| `useNavItems` | `components/layout/nav.tsx` | Destinations and icons shared by both |

## Patterns

- **Status circle meanings** (`StatCard` `indicator`): `success` connected, `danger`
  link lost, `alert` needs review, `warning` detections, `ring` current selection
  (rope, position), `solid` motion, `muted` neutral or unavailable.
- **Findings, not detections**: the robot stores one row per detection and runs the
  detector every two seconds on both cameras, so one flaw arrives as several rows a few
  centimetres apart. `clusterDefects` groups rows of the same kind that are closer than
  `CLUSTER_GAP_M` into a **finding**, and every screen counts and draws findings.
  Detections stay reachable: the run page shows how many back each finding, and the defect
  page lists them. Comparing runs also works on findings, otherwise repeat sightings would
  be counted as new defects.
- **Rope strip**: red marks for local faults, amber for loss of metallic area. A finding is
  drawn over the stretch its detections cover, down to a minimum width so a single one
  stays clickable, and faded by its confidence so a weak detection does not read like a
  certain one. In comparisons, marks also found in the reference run are thin and grey,
  new ones are wider and keep full opacity. The black vertical line is the robot position
  (only drawn when a position is known).
- **States**: every data view handles loading (`Loading…`), error (red text) and empty
  (a sentence saying what is missing and what to do).
- **Destructive actions** need a second click (`Remove` becomes `Confirm remove`).
- **Stop** is never disabled while the server socket is open, even if the robot is reported
  offline. The server answers with an error if it cannot forward it. There is no separate
  emergency stop: it sent the same command as Stop, and a second button that looks more
  urgent than the one that does the job is worse than no button.
- **Drive controls**: the operator only starts, stops and picks the direction. The robot
  times its own detector at startup and drives exactly fast enough for the camera frames to
  cover the rope end to end (`robot/src/vision/pacing.py`), and reports the speed and
  detector rate it settled on in every motion telemetry packet. Start is disabled while the
  robot is unreachable or already scanning, and the direction buttons are disabled while it
  moves, so no single click can reverse a moving machine. A command is reported as carried
  out only when telemetry shows it, never because the socket accepted it.
- **Rope socket**: the camera ring cannot turn past the fitting a rope ends in, so the robot
  *opens* — the ring parks clear of it and the detector stops, while the drive and the camera
  streams carry on. The live view has the large Open/Close button and, beside it, the small
  switch for the robot's own trigger on the distance sensor; both read their state from
  `robot_open` and `socket_watch` in the motion telemetry, never from what was clicked. An
  opening the operator asked for ends only on their click, one the sensor made closes itself
  once the robot has driven clear. The angles and distances shown on the settings page are
  copies of the robot's constants (`lib/robot/robot-config.ts`), not values it reported.
- **Position** is metres since the origin, which the backend resets on the robot whenever a
  run is selected. The webapp never converts steps to metres, the robot owns the drive
  geometry and reports both.
- **Stale live data** is never shown as current: telemetry older than 2 s shows `—`, a
  detector frame older than 8 s shows `—`, and a camera tile without a new frame for 2 s
  dims its image and shows a "Not live" badge.
- **Live detections**: `vision_telemetry` arrives for every detector frame, empty ones
  included, so it doubles as the detector's heartbeat on the live screen. It carries no row
  ids, so a frame with detections only triggers a reload of the stored run; the log itself
  is always built from what the backend persisted.
