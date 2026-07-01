# Ukraine Air Threat Monitor 2026

Modern real-time civil air-threat monitoring dashboard for Ukraine.

## Stack

- **Frontend:** Next.js 16 (App Router) + TypeScript + Tailwind CSS
- **Map:** Leaflet + react-leaflet (dark Carto basemap)
- **Realtime:** Server-Sent Events (`/api/stream`)
- **Ingestion:** public Telegram channel web polling (`https://t.me/s/<channel>`)

## Features

- Auto-ingest from public Telegram OSINT/monitoring channels
- Bootstrap last N posts per source on startup
- 5-second backend polling + 5-second SSE/UI refresh
- Predictive trajectories with speed by threat type
- Animated moving markers along paths
- Sidebar with ETA, confidence, probable targets
- Threat filters, 2-hour history, optional alert sound
- Mobile-friendly dark cyber-military UI

## Safety note

Trajectories are **predictive approximations with uncertainty**, not exact operational targeting data.

## Run locally

```bash
cd web
npm install
npm run dev
```

Open: `http://127.0.0.1:3000`

## Environment

```bash
INGEST_POLL_SECONDS=5
INGEST_BOOTSTRAP_LIMIT=20
```

## API

- `GET /api/events` — full dashboard snapshot JSON
- `GET /api/stream` — SSE realtime updates
- `GET /api/health` — ingestion status

## Legacy backend

The older Python FastAPI MVP remains in `backend/` for reference.
