# CableGuard webapp

Operator console for the CableGuard rope inspection robot. Next.js 16 (App Router),
React 19, Tailwind CSS 4, TypeScript. It talks only to the FastAPI backend in
`../backend`, never to the robot directly.

The visual language is documented in [DESIGN.md](./DESIGN.md).

## Getting started

```bash
npm install
cp .env.example .env.local   # point NEXT_PUBLIC_API_URL at your backend
npm run dev                   # http://localhost:3000
```

For local development the backend must allow the webapp origin, for example
`CORS_ORIGINS=http://localhost:3000` in `backend/.env`.

| Script | Purpose |
| --- | --- |
| `npm run dev` | Development server |
| `npm run build` / `npm start` | Production build and server |
| `npm run lint` | ESLint (Next.js core web vitals and TypeScript rules) |
| `npm run typecheck` | Generate route types and run `tsc` |

### Environment

| Variable | Default | Description |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | empty (same origin) | Backend base URL for REST and WebSockets. Inlined at build time. |

## Structure

```
app/                      Routes only: thin server components, metadata, error and not-found
  page.tsx                Dashboard
  live/                   Live run
  ropes/                  Ropes list
    [ropeId]/             Rope detail
      runs/[runId]/       Run detail
        defects/[defectId]/  Defect detail
  compare/                Compare two runs (?rope=&a=&b=)
  settings/               Robot settings
features/<screen>/        One client view per screen: data loading and composition
components/
  ui/                     Design system primitives (see DESIGN.md)
  layout/                 App shell (sidebar)
  rope/ camera/ inspection/  Domain components
lib/
  api/                    Backend contract types and typed REST client
  robot/                  WebSocket connections (robot link, video)
  hooks/                  useApi, useRopeHistory, useCurrentSelection, useNow
  defects.ts format.ts routes.ts config.ts cn.ts
public/                   Logo
```

Conventions:

- Pages in `app/` stay thin: read `params` or `searchParams`, render a view from `features/`.
- All URLs come from `lib/routes.ts`, all endpoints from `lib/api/client.ts`.
- When the backend changes, update `lib/api/types.ts` first. It mirrors
  `backend/app/schemas.py` and `shared/comm_protocols/messages.py`.

## Data flow

| Channel | Endpoint | Used for |
| --- | --- | --- |
| REST | `GET /api/ropes`, `POST /api/ropes`, `DELETE /api/ropes/{id}` | Ropes list, add, remove |
| REST | `GET /api/runs?rope_id=` | Run history per rope |
| REST | `GET /api/defects?run_id=` | Defects per run (live view polls every 5 s) |
| REST | `GET /api/current` | Rope and run selected on the server |
| WebSocket | `/api/ws/ui` | `robot_status`, `alive`, `motion_telemetry`, `current_changed`, `error`; sends `speed` and `stop` |
| WebSocket | `/api/ws/video/ui` | JPEG frames of two cameras, first byte is the camera index |

`RobotLinkProvider` (in the root layout) keeps one UI socket open for the whole app and
reconnects with backoff. The robot counts as connected only while the server reports it
online and it has been heard from (heartbeat or telemetry) in the last 12 s, because the
server itself only notices a dead robot link when its pings time out. Telemetry older than
2 s is not shown as current.

The video socket is only opened while the live view is mounted. A camera tile that receives
no frame for 2 s dims its last image and marks it as not live.

Neither the server nor the robot acknowledges commands. The live view therefore treats a
command as carried out only once telemetry reports the expected speed, and warns the operator
if that has not happened 5 s after sending. The drive limits in `lib/config.ts` mirror the
robot's own clamping and must be kept in sync with it.

## Feature status

Connected to real data:

- Robot link state, last packet and telemetry age, telemetry sequence, microsteps and drive speed
- Drive control: target speed and direction, Drive, Resume after a stop, Emergency stop
- Camera A and B live streams
- Ropes list with add and remove, rope detail, run history, defect trend
- Run detail, defect detail with change since the previous run
- Run comparison (defects within 1.5 m count as the same defect)

Present in the design but not supported by the robot or backend yet, so they are shown
disabled or as `—`:

- Robot position and distance covered on the rope
- Defect confidence, severity and review status (Mark reviewed, Flag false positive)
- Rope installation date and condition rating
- Session planning, run report export
- Stored camera frame for a defect
