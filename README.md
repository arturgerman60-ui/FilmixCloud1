# Private Local Threat Map MVP

Closed, personal situational-awareness MVP that runs as a local website.

Open one local link, ingest reports (manual or Telegram), and see approximate civil-risk markers/directions on a map.

This repository contains:

- `backend/` - FastAPI app that serves both the web UI and API.
- `backend/app/static/` - local website with map, report form, filters, and event feed.

## Safety boundary

The app is designed for civil alerts and approximate risk visualization. It intentionally models reports as
probabilistic zones/corridors with confidence and expiry, not as exact targeting, interception, or weapons guidance data.

## MVP capabilities

- Run locally at `http://127.0.0.1:8000`.
- Parse text reports from the web form, API calls, or Telegram polling.
- Detect threat type: `shahed`, `uav`, `gerbera`, `kab`, `fpv`, `recon_drone`, `missile`, `unknown`.
- Extract known locations and directions from Ukrainian/Russian-language messages.
- Show direction as approximate heading with angular uncertainty (`±`), not exact route.
- Produce event records and GeoJSON features for a map.
- Render approximate markers and direction lines on a Leaflet map with Kharkiv oblast focus.
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
- Telegram status: `http://127.0.0.1:8000/api/telegram/status`

## Telegram ingestion setup

Set environment variables before starting backend:

```bash
export TELEGRAM_ENABLED=1
export TELEGRAM_BOT_TOKEN=<your_bot_token>
export TELEGRAM_SOURCES="monitor_ukr,cxidua,war_monitor,-1001234567890"
export TELEGRAM_POLL_SECONDS=20
```

Simple mode notes (recommended):

- Bot must be added to target channels/chats to read their updates.
- For groups, disable bot privacy in BotFather to read all messages.
- Sources can be usernames, numeric chat IDs, or `https://t.me/...` links.

Alternative advanced mode (user session via Telethon):

```bash
export TELEGRAM_API_ID=<your_api_id>
export TELEGRAM_API_HASH=<your_api_hash>
export TELEGRAM_SESSION_STRING=<your_telethon_string_session>
export TELEGRAM_SOURCES="channel_username,chat_username_or_id"
```

General notes:

- You must have access rights to listed channels/chats in Telegram.
- First run establishes the cursor and then ingests only new messages.
- The UI shows ingestion state in "Telegram ingestion" block.

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

1. Replace the demo gazetteer with a complete geocoding source and PostGIS persistence.
2. Add private authentication before exposing the site outside localhost.
3. Add push/browser notifications for selected regions.
4. Run the backend on a locked-down VPS over HTTPS if remote access is needed.
