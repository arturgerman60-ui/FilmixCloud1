from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.geo import risk_geometry
from app.schemas import (
    EventList,
    GeoJsonFeature,
    GeoJsonFeatureCollection,
    HealthResponse,
    ReportIn,
    ThreatEvent,
    ThreatType,
)
from app.store import EventStore


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Private Local Threat Map",
    description="Local civil-risk visualization MVP. Shows approximate reports, not exact operational tracks.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

store = EventStore()


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", event_count=len(store.list_active(include_expired=True)))


@app.post("/api/reports", response_model=ThreatEvent, status_code=201)
def create_report(report: ReportIn) -> ThreatEvent:
    return store.create_from_report(report)


@app.get("/api/events", response_model=EventList)
def list_events(
    include_expired: bool = False,
    threat_type: ThreatType | None = Query(default=None),
) -> EventList:
    events = store.list_active(include_expired=include_expired)
    if threat_type:
        events = [event for event in events if event.threat_type == threat_type]
    return EventList(events=events)


@app.get("/api/events/{event_id}", response_model=ThreatEvent)
def get_event(event_id: UUID) -> ThreatEvent:
    event = store.get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.delete("/api/events", status_code=204)
def clear_events() -> None:
    store.clear()


@app.get("/api/events.geojson", response_model=GeoJsonFeatureCollection)
def events_geojson(include_expired: bool = False) -> GeoJsonFeatureCollection:
    features: list[GeoJsonFeature] = []
    for event in store.list_active(include_expired=include_expired):
        geometry = risk_geometry(event.coordinate, event.direction, event.risk_radius_km)
        features.append(
            GeoJsonFeature(
                geometry=geometry,
                properties={
                    "id": str(event.id),
                    "threat_type": event.threat_type.value,
                    "source": event.source,
                    "confidence": event.confidence,
                    "direction": event.direction.value,
                    "risk_radius_km": event.risk_radius_km,
                    "primary_location": event.primary_location,
                    "observed_at": event.observed_at.isoformat(),
                    "expires_at": event.expires_at.isoformat(),
                    "raw_text": event.raw_text,
                },
            )
        )
    return GeoJsonFeatureCollection(features=features)
