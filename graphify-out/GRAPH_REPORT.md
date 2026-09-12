# Graph Report - Cableguard-WRO26  (2026-09-12)

## Corpus Check
- 101 files · ~17,450 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 540 nodes · 1217 edges · 40 communities (20 shown, 9 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 27 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `351949ef`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- live-view.tsx
- backend/app/main.py
- settings-view.tsx
- Frontend Build Dependencies
- ropes-view.tsx
- Stepper Motor Control
- Robot Link Client
- next
- compilerOptions
- prepare_wirerope.py
- LatestFrame
- Hub
- Camera Capture Pair
- VideoHub
- README.md
- setup-graphify.sh
- CLAUDE.md
- eslint.config.mjs
- postcss.config.mjs
- cableguard_shared
- models.py
- app/auth.py
- routers/auth.py
- ingest.py
- CableGuard design system
- routers/video.py
- Settings
- How-to-Use.md
- AGENTS.md

## God Nodes (most connected - your core abstractions)
1. `cn()` - 35 edges
2. `Stepper` - 25 edges
3. `formatMetres()` - 17 edges
4. `shortId()` - 16 edges
5. `compilerOptions` - 16 edges
6. `defectMarks()` - 15 edges
7. `LiveView()` - 15 edges
8. `useRopeHistory()` - 15 edges
9. `PageHeader()` - 13 edges
10. `defectTypeLabel()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `create_access_token()` --uses--> `User`  [INFERRED]
  backend/app/auth.py → backend/app/models.py
- `me()` --uses--> `User`  [INFERRED]
  backend/app/routers/auth.py → backend/app/models.py
- `get_current()` --uses--> `CurrentSelection`  [INFERRED]
  backend/app/routers/current.py → backend/app/schemas.py
- `login()` --calls--> `verify_password()`  [EXTRACTED]
  backend/app/routers/auth.py → backend/app/auth.py
- `login()` --calls--> `dummy_verify()`  [EXTRACTED]
  backend/app/routers/auth.py → backend/app/auth.py

## Import Cycles
- None detected.

## Communities (40 total, 9 thin omitted)

### Community 0 - "live-view.tsx"
Cohesion: 0.09
Nodes (65): RunStatePill(), DefectLegend(), defectMarks(), markColor, RopeStrip(), StripMark, Button(), buttonClass() (+57 more)

### Community 1 - "backend/app/main.py"
Cohesion: 0.19
Nodes (14): get_db(), init_db(), Session, session_scope(), _sqlite_pragmas(), health(), lifespan(), get (+6 more)

### Community 2 - "settings-view.tsx"
Cohesion: 0.08
Nodes (30): metadata, Logo(), AppShell(), formatClock(), isActive(), LinkStatus(), NAV_ITEMS, Operator() (+22 more)

### Community 3 - "Frontend Build Dependencies"
Cohesion: 0.06
Nodes (33): eslint, eslint-config-next, react-dom, tailwind-merge, tailwindcss, @tailwindcss/postcss, @types/node, @types/react (+25 more)

### Community 4 - "ropes-view.tsx"
Cohesion: 0.06
Nodes (46): react, metadata, plexMono, poppins, metadata, CameraFeed(), loadOverview(), RopesView() (+38 more)

### Community 6 - "Robot Link Client"
Cohesion: 0.12
Nodes (9): RobotLink, Outbox, Alive, Defect, MotionTelemetry, BaseModel, RobotMessage, SpeedCmd (+1 more)

### Community 7 - "next"
Cohesion: 0.11
Nodes (10): next, ComparePage(), first(), metadata, metadata, metadata, metadata, metadata (+2 more)

### Community 8 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 9 - "prepare_wirerope.py"
Cohesion: 0.25
Nodes (10): find_split(), load_names(), main(), place(), Class names from a Roboflow data.yaml, as a list indexed by class id., Merges several Roboflow YOLO exports into a single dataset in the layout the…, Image/label dir of one split, for both common export layouts., Hardlink if possible - a copy of ~22'000 images costs several GB twice. (+2 more)

### Community 14 - "README.md"
Cohesion: 0.33
Nodes (5): Cableguard-WRO26, Electronic Components, Goal with Tech-Stack:, Knowledge graph (graphify), Setup

### Community 15 - "setup-graphify.sh"
Cohesion: 0.60
Nodes (4): info(), PATH, setup-graphify.sh script, warn()

### Community 18 - "CLAUDE.md"
Cohesion: 0.50
Nodes (3): Git authorship, Git safety, graphify

### Community 30 - "models.py"
Cohesion: 0.13
Nodes (19): Base, Rope, Run, post, set_current(), create_rope(), delete_rope(), list_ropes() (+11 more)

### Community 31 - "app/auth.py"
Cohesion: 0.16
Nodes (19): _b64(), decode_token(), dummy_verify(), get_current_user(), hash_password(), Session, Robot link token, operator passwords and the webapp's JWT access tokens., Guards every REST route that serves inspection data. (+11 more)

### Community 32 - "routers/auth.py"
Cohesion: 0.19
Nodes (17): create_access_token(), Returns the signed token and how many seconds it stays valid., login(), me(), get, post, CurrentSelection, DefectOut (+9 more)

### Community 33 - "ingest.py"
Cohesion: 0.18
Nodes (14): AppState, Defect, get_defect(), list_defects(), # TODO: distance to start, _store_defect(), get_current(), get_state() (+6 more)

### Community 34 - "CableGuard design system"
Cohesion: 0.12
Nodes (15): CableGuard design system, Colour, Components, Layout, Patterns, Principles, Shape and spacing, Tokens (+7 more)

### Community 35 - "routers/video.py"
Cohesion: 0.31
Nodes (7): authenticate_robot(), authenticate_ui(), WebSocket, Browsers cannot set headers on a WebSocket, so the webapp sends the access…, websocket, video_in(), video_out()

### Community 36 - "Settings"
Cohesion: 0.40
Nodes (4): Accept either a JSON array or a comma-separated list from the environment., Settings, BaseSettings, field_validator

### Community 37 - "How-to-Use.md"
Cohesion: 0.50
Nodes (3): Datasets, Run, Setup

## Knowledge Gaps
- **114 isolated node(s):** `PATH`, `cableguard_shared`, `metadata`, `poppins`, `plexMono` (+109 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 214 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `ropes-view.tsx` to `live-view.tsx`, `settings-view.tsx`, `Frontend Build Dependencies`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `next` connect `next` to `settings-view.tsx`, `Frontend Build Dependencies`, `ropes-view.tsx`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Why does `cn()` connect `live-view.tsx` to `settings-view.tsx`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **What connects `PATH`, `cableguard_shared`, `metadata` to the rest of the system?**
  _114 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `live-view.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.08815097945532728 - nodes in this community are weakly interconnected._
- **Should `settings-view.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.08362369337979095 - nodes in this community are weakly interconnected._
- **Should `Frontend Build Dependencies` be split into smaller, more focused modules?**
  _Cohesion score 0.058823529411764705 - nodes in this community are weakly interconnected._