# Private Local Threat Map MVP

Closed, personal situational-awareness MVP that runs as a local website.

Open one local link, paste Telegram-style reports, and see approximate civil-risk markers/directions on a map.

This repository contains:

- `backend/` - FastAPI app that serves both the web UI and API.
- `backend/app/static/` - local website with map, report form, filters, and event feed.

## Safety boundary

The app is designed for civil alerts and approximate risk visualization. It intentionally models reports as
probabilistic zones/corridors with confidence and expiry, not as exact targeting, interception, or weapons guidance data.

## MVP capabilities

- Run locally at `http://127.0.0.1:8000`.
- Parse text reports from the web form or API calls.
- Detect threat type: `shahed`, `uav`, `gerbera`, `kab`, `fpv`, `missile`, `unknown`.
- Extract known locations and directions from Ukrainian/Russian-language messages.
- Produce event records and GeoJSON features for a map.
- Render approximate markers and direction lines on an online OpenStreetMap/Leaflet map.
- Keep all deployment private: local machine or locked-down VPS.

## Local website start

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open:

- Website: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Events API: `http://127.0.0.1:8000/api/events`
- GeoJSON API: `http://127.0.0.1:8000/api/events.geojson`

Seed a demo report from terminal:

```bash
curl -X POST http://localhost:8000/api/reports \
  -H 'Content-Type: application/json' \
  -d '{"text":"Шахед через Миколаївщину курсом на північний захід","source":"demo"}'
```

Or paste this into the site form:

```text
Шахед через Миколаївщину курсом на північний захід
```

## Next production steps

1. Add authenticated Telegram ingestion on the backend (`Telethon` user session or bot where supported).
2. Replace the demo gazetteer with a complete geocoding source and PostGIS persistence.
3. Add private authentication before exposing the site outside localhost.
4. Add push/browser notifications for selected regions.
5. Run the backend on a locked-down VPS over HTTPS if remote access is needed.
