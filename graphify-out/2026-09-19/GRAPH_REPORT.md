# Graph Report - Cableguard-WRO26  (2026-09-19)

## Corpus Check
- 101 files · ~20,726 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 573 nodes · 1350 edges · 39 communities (21 shown, 9 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 45 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `af81a118`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- live-view.tsx
- backend/app/main.py
- robot-link.tsx
- Frontend Build Dependencies
- types.ts
- Stepper
- RobotLink
- next
- compilerOptions
- prepare_wirerope.py
- VideoLink
- Hub
- CameraPair
- VideoHub
- README.md
- setup-graphify.sh
- CLAUDE.md
- eslint.config.mjs
- postcss.config.mjs
- cableguard_shared
- src/app/main.py
- schemas.py
- app/auth.py
- messages.py
- models.py
- CableGuard design system
- routers/defects.py
- Settings
- How-to-Use.md
- MotionController

## God Nodes (most connected - your core abstractions)
1. `cn()` - 40 edges
2. `Stepper` - 30 edges
3. `LiveView()` - 21 edges
4. `formatMetres()` - 17 edges
5. `shortId()` - 16 edges
6. `compilerOptions` - 16 edges
7. `defectMarks()` - 15 edges
8. `useRopeHistory()` - 15 edges
9. `useRobotConnected()` - 14 edges
10. `react` - 14 edges

## Surprising Connections (you probably didn't know these)
- `telemetry_sender()` --uses--> `MotionTelemetry`  [INFERRED]
  robot/src/app/main.py → shared/comm_protocols/messages.py
- `make_command_handler()` --uses--> `SpeedCmd`  [INFERRED]
  robot/src/app/main.py → shared/comm_protocols/messages.py
- `make_command_handler()` --uses--> `StopCmd`  [INFERRED]
  robot/src/app/main.py → shared/comm_protocols/messages.py
- `create_run()` --uses--> `Run`  [INFERRED]
  backend/app/routers/runs.py → backend/app/models.py
- `delete_run()` --uses--> `Run`  [INFERRED]
  backend/app/routers/runs.py → backend/app/models.py

## Import Cycles
- None detected.

## Communities (39 total, 9 thin omitted)

### Community 0 - "live-view.tsx"
Cohesion: 0.08
Nodes (73): DefectLegend(), defectMarks(), markColor, RopeStrip(), StripMark, Button(), buttonClass(), ButtonLink() (+65 more)

### Community 1 - "backend/app/main.py"
Cohesion: 0.13
Nodes (21): authenticate_robot(), authenticate_ui(), WebSocket, Browsers cannot set headers on a WebSocket, so the webapp sends the access…, init_db(), _migrate_sqlite(), Session, session_scope() (+13 more)

### Community 2 - "robot-link.tsx"
Cohesion: 0.06
Nodes (47): react, metadata, metadata, Logo(), CameraFeed(), RunStatePill(), AppShell(), formatClock() (+39 more)

### Community 3 - "Frontend Build Dependencies"
Cohesion: 0.06
Nodes (33): eslint, eslint-config-next, react-dom, tailwind-merge, tailwindcss, @tailwindcss/postcss, @types/node, @types/react (+25 more)

### Community 4 - "types.ts"
Cohesion: 0.08
Nodes (37): metadata, plexMono, poppins, api, ApiError, json(), request(), AliveEvent (+29 more)

### Community 6 - "RobotLink"
Cohesion: 0.22
Nodes (4): link_guard(), main(), telemetry_sender(), RobotLink

### Community 7 - "next"
Cohesion: 0.11
Nodes (9): next, ComparePage(), first(), metadata, metadata, metadata, metadata, metadata (+1 more)

### Community 8 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 9 - "prepare_wirerope.py"
Cohesion: 0.25
Nodes (10): find_split(), load_names(), main(), place(), Class names from a Roboflow data.yaml, as a list indexed by class id., Merges several Roboflow YOLO exports into a single dataset in the layout the…, Image/label dir of one split, for both common export layouts., Hardlink if possible - a copy of ~22'000 images costs several GB twice. (+2 more)

### Community 12 - "CameraPair"
Cohesion: 0.24
Nodes (3): frame_producer(), CameraPair, encode()

### Community 14 - "README.md"
Cohesion: 0.33
Nodes (5): Cableguard-WRO26, Electronic Components, Goal with Tech-Stack:, Knowledge graph (graphify), Setup

### Community 15 - "setup-graphify.sh"
Cohesion: 0.60
Nodes (4): info(), PATH, setup-graphify.sh script, warn()

### Community 18 - "CLAUDE.md"
Cohesion: 0.50
Nodes (3): Git authorship, Git safety, graphify

### Community 30 - "schemas.py"
Cohesion: 0.12
Nodes (27): _unauthorized(), Rope, create_rope(), delete_rope(), list_ropes(), delete, get, post (+19 more)

### Community 31 - "app/auth.py"
Cohesion: 0.14
Nodes (25): _b64(), create_access_token(), decode_token(), dummy_verify(), get_current_user(), hash_password(), Session, Robot link token, operator passwords and the webapp's JWT access tokens. (+17 more)

### Community 32 - "messages.py"
Cohesion: 0.33
Nodes (8): make_command_handler(), Alive, Defect, MotionTelemetry, BaseModel, RobotMessage, SpeedCmd, StopCmd

### Community 33 - "models.py"
Cohesion: 0.16
Nodes (18): Base, AppState, Defect, Run, get_defect(), list_defects(), _store_defect(), get_current() (+10 more)

### Community 34 - "CableGuard design system"
Cohesion: 0.12
Nodes (15): CableGuard design system, Colour, Components, Layout, Patterns, Principles, Shape and spacing, Tokens (+7 more)

### Community 35 - "routers/defects.py"
Cohesion: 0.47
Nodes (4): get_defect(), list_defects(), get, Session

### Community 36 - "Settings"
Cohesion: 0.40
Nodes (4): Accept either a JSON array or a comma-separated list from the environment., Settings, BaseSettings, field_validator

### Community 37 - "How-to-Use.md"
Cohesion: 0.50
Nodes (3): Datasets, Run, Setup

## Knowledge Gaps
- **118 isolated node(s):** `PATH`, `cableguard_shared`, `metadata`, `poppins`, `plexMono` (+113 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 218 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `robot-link.tsx` to `live-view.tsx`, `Frontend Build Dependencies`, `types.ts`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `Stepper` connect `Stepper` to `MotionController`, `src/app/main.py`, `RobotLink`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Why does `main()` connect `RobotLink` to `messages.py`, `Stepper`, `MotionController`, `VideoLink`, `CameraPair`, `src/app/main.py`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Stepper` (e.g. with `telemetry_sender()` and `MotionController`) actually correct?**
  _`Stepper` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `PATH`, `cableguard_shared`, `metadata` to the rest of the system?**
  _118 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `live-view.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.07746068724519511 - nodes in this community are weakly interconnected._
- **Should `backend/app/main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1349206349206349 - nodes in this community are weakly interconnected._