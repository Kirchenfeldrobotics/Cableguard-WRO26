# Graph Report - Cableguard-WRO26  (2026-09-12)

## Corpus Check
- 92 files · ~15,245 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 457 nodes · 1019 edges · 30 communities (12 shown, 8 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 14 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `351949ef`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- live-view.tsx
- ws.py
- settings-view.tsx
- Frontend Build Dependencies
- use-inspection.ts
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

## God Nodes (most connected - your core abstractions)
1. `cn()` - 35 edges
2. `Stepper` - 25 edges
3. `formatMetres()` - 17 edges
4. `shortId()` - 16 edges
5. `compilerOptions` - 16 edges
6. `defectMarks()` - 15 edges
7. `LiveView()` - 15 edges
8. `useRopeHistory()` - 15 edges
9. `defectTypeLabel()` - 13 edges
10. `PageHeader()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `RunView()` --indirect_call--> `byPosition()`  [INFERRED]
  webapp/features/run/run-view.tsx → webapp/lib/defects.ts
- `get_defect()` --uses--> `Defect`  [INFERRED]
  backend/app/repository/defects.py → backend/app/models.py
- `list_defects()` --uses--> `Defect`  [INFERRED]
  backend/app/repository/defects.py → backend/app/models.py
- `create_rope()` --uses--> `Rope`  [INFERRED]
  backend/app/routers/ropes.py → backend/app/models.py
- `delete_rope()` --uses--> `Rope`  [INFERRED]
  backend/app/routers/ropes.py → backend/app/models.py

## Import Cycles
- None detected.

## Communities (30 total, 8 thin omitted)

### Community 0 - "live-view.tsx"
Cohesion: 0.09
Nodes (63): DefectLegend(), defectMarks(), markColor, RopeStrip(), StripMark, Button(), buttonClass(), ButtonLink() (+55 more)

### Community 1 - "ws.py"
Cohesion: 0.05
Nodes (62): authenticate_robot(), Accept either a JSON array or a comma-separated list from the environment., Settings, Base, get_db(), init_db(), session_scope(), _sqlite_pragmas() (+54 more)

### Community 2 - "settings-view.tsx"
Cohesion: 0.06
Nodes (41): react, metadata, plexMono, poppins, metadata, Logo(), CameraFeed(), RunStatePill() (+33 more)

### Community 3 - "Frontend Build Dependencies"
Cohesion: 0.06
Nodes (33): eslint, eslint-config-next, react-dom, tailwind-merge, tailwindcss, @tailwindcss/postcss, @types/node, @types/react (+25 more)

### Community 4 - "use-inspection.ts"
Cohesion: 0.12
Nodes (22): api, ApiError, json(), request(), CurrentChangedEvent, CurrentSelection, Defect, DefectKind (+14 more)

### Community 6 - "Robot Link Client"
Cohesion: 0.12
Nodes (9): RobotLink, Outbox, Alive, Defect, MotionTelemetry, BaseModel, RobotMessage, SpeedCmd (+1 more)

### Community 7 - "next"
Cohesion: 0.11
Nodes (9): next, ComparePage(), first(), metadata, metadata, metadata, metadata, metadata (+1 more)

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

## Knowledge Gaps
- **95 isolated node(s):** `graphify`, `Git authorship`, `Git safety`, `Cableguard-WRO26`, `Goal with Tech-Stack:` (+90 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 177 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `settings-view.tsx` to `live-view.tsx`, `Frontend Build Dependencies`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Why does `next` connect `next` to `settings-view.tsx`, `Frontend Build Dependencies`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `cn()` connect `live-view.tsx` to `settings-view.tsx`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **What connects `graphify`, `Git authorship`, `Git safety` to the rest of the system?**
  _95 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `live-view.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.09313358302122347 - nodes in this community are weakly interconnected._
- **Should `ws.py` be split into smaller, more focused modules?**
  _Cohesion score 0.052393857271906055 - nodes in this community are weakly interconnected._
- **Should `settings-view.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.06077694235588972 - nodes in this community are weakly interconnected._