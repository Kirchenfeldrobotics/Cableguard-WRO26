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
  (`NOT_AVAILABLE` in `lib/format.ts`). Controls for features that do not exist yet are
  rendered **disabled**, never wired to fake state. The webapp keeps no copy of the robot's
  constants: anything it names is read from `GET /api/settings` (`useRobotSettings`).
- **Say it once, in a few words.** No text explains how a feature works, and no text repeats
  what a badge, a card, a button label or the sidebar already shows. What is left is a note
  of a few words. A `title` tooltip is only for a disabled button whose reason is not on the
  screen (`Stop first`) and for data (the label on a rope mark). The
  settings page is the exception: its explanations come from the server with each setting.

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
| Page and section title | 30px / 800, uppercase, `-0.01em` tracking (24px on phones) |
| Sub-title inside a column | 18px / 800, uppercase |
| Card value (stat, fact, comparison) | 22px / 700 (18px on phones) |
| Large button, input on a phone | 16px |
| Body, buttons, inputs | 14px / 400–600 |
| Labels, links, table cells | 13px |
| Status badge, table header, notes | 12px |
| Scale labels, captions in mono | 11px |

These eight sizes (11, 12, 13, 14, 16, 18, 22 and the title) are the whole scale. A size in
between is a sign that a screen is styling something a component already styles.

Mono is for measurements, ids and timestamps. A word stays in the text font even when it
sits in a column of numbers: `FactList` rows are mono only where `mono` is set.

### Shape and spacing

| Token | Value | Use |
| --- | --- | --- |
| `rounded-shell` | 18px | Sidebar |
| `rounded-card` | 14px | Cards, panels, camera tiles |
| `rounded-control` | 10px | Buttons, inputs, nav items |
| `rounded-row` | 9px | Log rows |
| `rounded-full` | | Badges and indicators |

### Sizes and rhythm

| Token | Value | Use |
| --- | --- | --- |
| `control` | 44px | Height of every button, input and dropdown (`h-control`) |
| `control-lg` | 58px | The main action of a screen: start and finish a run, open the robot, sign in |
| `section` | 38px | Above a section heading (`mt-section`) |
| `stack` | 18px | Under a heading, and between two blocks that follow each other (`mt-stack`, `gap-stack`) |

Cards sit 14px apart, the app has 12px of outer padding. A control never gets its own
padding or height on a screen: if `md` and `lg` do not fit, the screen is asking for the
wrong control.

A spacing token also becomes a size utility under other prefixes, so its name must not be a
CSS display value: a token called `block` turns every `inline-block` into an 18px wide box.

`Panel` has two paddings and no third: `content` (16px, 22px from `sm`) for a strip,
controls, a chart or a form, and `list` for rows that bring their own vertical padding
(settings, fact lists).

## Layout

- `app/layout.tsx`: 236px sticky black sidebar on the left and main content up to 1280px
  wide.
- A page is titled like its navigation entry. The page header row is as tall as a control
  whether or not it holds a button, so the title sits at the same height on every page,
  and the scrollbar keeps its room on a page too short to need one, so nothing shifts
  sideways between pages.
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
  status circle, and main action buttons fill the row. The actions of a page header get a
  row of their own under the title, starting at the left edge like everything else.
- Tables become one card per row (`.stack-table` in `globals.css`). Give every `Td` a
  `label` (its column header), mark the identifying cell `phone="primary"` and a row
  action `phone="end"`. A cell that is empty, such as a row action that is not offered,
  takes no room on the card.
- Inputs use 16px text below `sm`, otherwise iOS zooms the page when they are focused.
- The live screen puts what is being tracked first (numbers, position on rope, cameras,
  then drive, rope socket and log), the cameras swipe sideways, and the motion state with Stop is
  pinned above the tab bar. That pinned Stop replaces the one in the drive panel, so
  there is never more than one Stop on screen.

## Components

| Component | File | Notes |
| --- | --- | --- |
| `PageHeader`, `SectionTitle`, `SubTitle`, `HeadingMeta` | `components/ui/heading.tsx` | Title rows. Meta text, actions and a note are props of the row, never siblings of the heading: the row owns the spacing |
| `Button`, `ButtonLink`, `TextLink`, `RingIcon` | `components/ui/button.tsx` | `primary`, `secondary`, `danger`; `md` (44px) or `lg` (58px). `TextLink` is the small action next to a heading |
| `Input`, `Field` | `components/ui/input.tsx` | The one text field, and a control under its caption |
| `Dropdown` | `components/ui/dropdown.tsx` | Listbox in the control shape; a native `<select>` cannot be styled to the tokens |
| `Pill` | `components/ui/pill.tsx` | `status` variant for headers, `tag` inside tables |
| `StatCard`, `FactCard`, `Panel`, `CardGrid` | `components/ui/card.tsx` | Stat cards carry a 46px status circle. Labels sit on the bottom edge, so they stay in line when a value wraps |
| `Table`, `Th`, `Td`, `LinkRow` | `components/ui/table.tsx` | Rows navigate on click and Enter |
| `RemoveButton` | `components/ui/remove-button.tsx` | Two-step remove at the end of a table row (ropes, runs) |
| `LogRow`, `InfoRow` | `components/ui/log-row.tsx` | Tinted rows for detections and changes |
| `FactList` | `components/ui/fact-list.tsx` | Label and value rows on a panel |
| `Notice`, `StatusMessage`, `BackLink` | `components/ui/feedback.tsx` | Alerts, loading, empty and error states |
| `RopeStrip`, `RopeStripSync`, `findingMarks`, `DefectLegend` | `components/rope/` | Unrolled rope with metre scale and finding marks, drawn to scale and scrolling sideways when the rope is longer than the screen |
| `RopeLengthInput` | `components/rope/rope-length-input.tsx` | Length in metres with its unit, for adding a rope and correcting its length |
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
- **Review**: the operator reviews findings, not detections. `Mark reviewed` on the defect
  page sets every detection of the finding in one request, and a finding counts as reviewed
  only while all of them are, so a detection that joins it later in a live run opens it
  again. `Flag false positive` deletes the detections for good after a second click
  (`Confirm delete`): there is no false-positive state to show, count or undo. Unreviewed
  findings are counted per run on the rope page and over all runs of the selected rope on
  the dashboard, where the `alert` circle shows while any are left.
- **Run report**: `Export run report` builds a PDF in the browser
  (`features/run/run-report.ts`): the run's numbers, the rope with its findings, the
  findings table with their review status, and one photo per finding with the detector's
  box. jsPDF is loaded on the click, it is far heavier than the page. A PDF cannot read the
  stylesheet, so the report module carries its own copy of the few colour tokens it uses,
  and the PDF's built-in Helvetica stands in for Poppins.
- **Findings, not detections**: the robot stores one row per detection and runs the
  detector every two seconds on both cameras, so one flaw arrives as several rows a few
  centimetres apart. `clusterDefects` groups rows of the same kind that are closer than
  `CLUSTER_GAP_M` into a **finding**, and every screen counts and draws findings.
  Detections stay reachable: the run page shows how many back each finding, and the defect
  page lists them. Comparing runs also works on findings, otherwise repeat sightings would
  be counted as new defects.
- **Tables**: columns are 24px apart, so a right-aligned number never touches the column
  after it. A status in a table is plain text: what is still to do in the strong weight,
  what is done muted.
- **Error text** is the server's own sentence and nothing else (`ApiError` in
  `lib/api/client.ts`): no endpoint, no status code.
- **Rope strip**: the rope is a white bar on the grey panel, with red marks for local
  faults and amber ones for loss of metallic area. A finding is
  drawn over the stretch its detections cover, down to a minimum width so a single one
  stays clickable, and faded by its confidence so a weak detection does not read like a
  certain one. In comparisons, marks also found in the reference run are thin and grey,
  new ones are wider and keep full opacity. The black vertical line is the robot position
  (only drawn when a position is known).
- **Rope strip scale**: the strip is drawn at 10 px per metre (`PX_PER_M` in
  `components/rope/strip-layout.ts`), about 100 m across a desktop panel and 30 m on a phone.
  A rope that fits is stretched to the full width. A longer one scrolls sideways and gets an
  overview bar underneath: the whole rope in one line, a tick per mark and a frame around the
  part on screen. The overview is the strip's scrollbar (drag, click, arrow keys, Page
  Up/Down, Home, End), the browser's own is hidden. The scale is what keeps marks apart:
  findings of one type are never closer than `CLUSTER_GAP_M`, which is wider than a mark at
  10 px per metre. A local fault and a loss of metallic area on the same spot share the bar
  height, the fault on top. A mark's click margin stops halfway to its neighbour. The scale
  labels step by 1, 2, 5, 10, ... metres, whatever keeps them about 64 px apart.
- **Rope strip position**: a strip opens at the start of the rope. On the live screen it
  follows the robot and moves on when the robot nears the edge. While the operator has hold
  of the strip it stays where they put it, and it follows again once they have let go with
  the robot on screen. Strips inside one `RopeStripSync` scroll together (run comparison).
- **Rope length** is asked for when a rope is added and can be corrected on the rope page
  (`Edit length`). Only a rope from before the length was asked for has none, and its strip
  says so instead of drawing.
- **States**: every data view handles loading (`Loading…`), error (red text) and empty
  (a few words saying what is missing). An empty list whose count already shows as 0 on a
  card is not drawn at all, heading included.
- **Destructive actions** need a second click (`Remove` becomes `Confirm remove`,
  `Flag false positive` becomes `Confirm delete`).
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
  once the robot has driven clear. The opening threshold itself is set on the settings page.
  The sensor triggers on a *departure* from what it read at startup, not on a distance, so
  the panel also shows the reading it calibrated on: `Not calibrated` there means it found
  nothing to measure against, which is why the robot will not open by itself. Arming the
  sensor is not a setting: it is a command like Start and Stop, and lives only in the live
  view.
- **Settings** are the robot's own constants (`shared/comm_protocols/settings.py`), kept in
  the backend's database and sent to the robot as a `SettingsCmd`. The page draws itself from
  what `GET /api/settings` returns: the label, the explanation, the unit and the bounds of
  every setting come from the server, so no setting is ever described twice. A change is a
  `PUT` of only the settings that moved, and the server refuses one while the robot reports
  movement, so the page disables its inputs then. The robot echoes the version it is running
  on in every motion telemetry packet, and the page says a change is **in force** only when
  that version matches the stored one, never because the `PUT` came back 200.
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
