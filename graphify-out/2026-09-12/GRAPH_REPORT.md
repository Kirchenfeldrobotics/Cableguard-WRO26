# Graph Report - Cableguard-WRO26  (2026-09-12)

## Corpus Check
- 101 files · ~17,450 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 544 nodes · 1202 edges · 43 communities (22 shown, 10 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 31 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9086a47b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- live-view.tsx
- database.py
- settings-view.tsx
- Frontend Build Dependencies
- use-inspection.ts
- Stepper Motor Control
- Robot Link Client
- next
- compilerOptions
- prepare_wirerope.py
- VideoHub
- Hub
- Camera Capture Pair
- repository/defects.py
- README.md
- setup-graphify.sh
- CLAUDE.md
- eslint.config.mjs
- postcss.config.mjs
- cableguard_shared
- ropes.py
- app/auth.py
- routers/auth.py
- models.py
- CableGuard design system
- authenticate_ui
- Settings
- How-to-Use.md
- AGENTS.md
- Session
- post
- BaseModel

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
- `robot_link()` --calls--> `store()`  [INFERRED]
  backend/app/routers/ws.py → backend/app/repository/ingest.py
- `create_access_token()` --uses--> `User`  [INFERRED]
  backend/app/auth.py → backend/app/models.py
- `lifespan()` --calls--> `init_db()`  [INFERRED]
  backend/app/main.py → backend/app/database.py
- `me()` --uses--> `User`  [INFERRED]
  backend/app/routers/auth.py → backend/app/models.py
- `create_run()` --uses--> `Run`  [INFERRED]
  backend/app/routers/runs.py → backend/app/models.py

## Import Cycles
- None detected.

## Communities (43 total, 10 thin omitted)

### Community 0 - "live-view.tsx"
Cohesion: 0.08
Nodes (73): RunStatePill(), DefectLegend(), defectMarks(), markColor, RopeStrip(), StripMark, Button(), buttonClass() (+65 more)

### Community 1 - "database.py"
Cohesion: 0.14
Nodes (17): Base, get_db(), init_db(), Session, session_scope(), _sqlite_pragmas(), health(), lifespan() (+9 more)

### Community 2 - "settings-view.tsx"
Cohesion: 0.07
Nodes (37): react, metadata, plexMono, poppins, metadata, Logo(), CameraFeed(), AppShell() (+29 more)

### Community 3 - "Frontend Build Dependencies"
Cohesion: 0.06
Nodes (33): eslint, eslint-config-next, react-dom, tailwind-merge, tailwindcss, @tailwindcss/postcss, @types/node, @types/react (+25 more)

### Community 4 - "use-inspection.ts"
Cohesion: 0.11
Nodes (30): api, ApiError, json(), request(), AuthUser, CurrentChangedEvent, CurrentSelection, Defect (+22 more)

### Community 6 - "Robot Link Client"
Cohesion: 0.12
Nodes (9): RobotLink, Outbox, Alive, Defect, MotionTelemetry, BaseModel, RobotMessage, SpeedCmd (+1 more)

### Community 7 - "next"
Cohesion: 0.09
Nodes (11): next, ComparePage(), first(), metadata, metadata, metadata, metadata, metadata (+3 more)

### Community 8 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 9 - "prepare_wirerope.py"
Cohesion: 0.25
Nodes (10): find_split(), load_names(), main(), place(), Class names from a Roboflow data.yaml, as a list indexed by class id., Merges several Roboflow YOLO exports into a single dataset in the layout the…, Image/label dir of one split, for both common export layouts., Hardlink if possible - a copy of ~22'000 images costs several GB twice. (+2 more)

### Community 10 - "VideoHub"
Cohesion: 0.12
Nodes (3): VideoHub, LatestFrame, VideoLink

### Community 13 - "repository/defects.py"
Cohesion: 0.40
Nodes (5): get_defect(), list_defects(), get_defect(), list_defects(), get

### Community 14 - "README.md"
Cohesion: 0.33
Nodes (5): Cableguard-WRO26, Electronic Components, Goal with Tech-Stack:, Knowledge graph (graphify), Setup

### Community 15 - "setup-graphify.sh"
Cohesion: 0.60
Nodes (4): info(), PATH, setup-graphify.sh script, warn()

### Community 18 - "CLAUDE.md"
Cohesion: 0.50
Nodes (3): Git authorship, Git safety, graphify

### Community 30 - "ropes.py"
Cohesion: 0.19
Nodes (13): _unauthorized(), Rope, create_rope(), delete_rope(), list_ropes(), delete, get, post (+5 more)

### Community 31 - "app/auth.py"
Cohesion: 0.16
Nodes (18): _b64(), decode_token(), dummy_verify(), get_current_user(), hash_password(), Robot link token, operator passwords and the webapp's JWT access tokens., Guards every REST route that serves inspection data., `pbkdf2_sha256$rounds$salt$hash`, with a fresh random salt every call. (+10 more)

### Community 32 - "routers/auth.py"
Cohesion: 0.20
Nodes (16): create_access_token(), Returns the signed token and how many seconds it stays valid., login(), me(), get, DefectOut, LoginRequest, # TODO: Create schemas for data that is persisted (+8 more)

### Community 33 - "models.py"
Cohesion: 0.16
Nodes (15): AppState, Defect, Run, # TODO: distance to start, store(), _store_defect(), get_current(), get_state() (+7 more)

### Community 34 - "CableGuard design system"
Cohesion: 0.12
Nodes (15): CableGuard design system, Colour, Components, Layout, Patterns, Principles, Shape and spacing, Tokens (+7 more)

### Community 35 - "authenticate_ui"
Cohesion: 0.39
Nodes (7): authenticate_robot(), authenticate_ui(), WebSocket, Browsers cannot set headers on a WebSocket, so the webapp sends the access…, websocket, video_in(), video_out()

### Community 36 - "Settings"
Cohesion: 0.40
Nodes (4): Accept either a JSON array or a comma-separated list from the environment., Settings, BaseSettings, field_validator

### Community 37 - "How-to-Use.md"
Cohesion: 0.50
Nodes (3): Datasets, Run, Setup

## Knowledge Gaps
- **114 isolated node(s):** `poppins`, `plexMono`, `metadata`, `metadata`, `NAV_ITEMS` (+109 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 217 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `settings-view.tsx` to `live-view.tsx`, `Frontend Build Dependencies`, `use-inspection.ts`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `next` connect `next` to `settings-view.tsx`, `Frontend Build Dependencies`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Why does `cn()` connect `live-view.tsx` to `settings-view.tsx`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **What connects `poppins`, `plexMono`, `metadata` to the rest of the system?**
  _114 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `live-view.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.0761904761904762 - nodes in this community are weakly interconnected._
- **Should `database.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1383399209486166 - nodes in this community are weakly interconnected._
- **Should `settings-view.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.06980392156862746 - nodes in this community are weakly interconnected._