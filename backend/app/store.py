from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import UUID, uuid4

from app.analysis import analyze_report
from app.geo import risk_radius_km
from app.schemas import ReportIn, ThreatEvent, ThreatType


EVENT_TTL_BY_TYPE: dict[ThreatType, timedelta] = {
    ThreatType.SHAHED: timedelta(minutes=45),
    ThreatType.UAV: timedelta(minutes=35),
    ThreatType.GERBERA: timedelta(minutes=30),
    ThreatType.KAB: timedelta(minutes=20),
    ThreatType.FPV: timedelta(minutes=15),
    ThreatType.RECON_DRONE: timedelta(minutes=30),
    ThreatType.MISSILE: timedelta(minutes=20),
    ThreatType.UNKNOWN: timedelta(minutes=20),
}


class EventStore:
    def __init__(self) -> None:
        self._events: dict[UUID, ThreatEvent] = {}
        self._external_ref_to_event_id: dict[str, UUID] = {}
        self._lock = Lock()

    def create_from_report(self, report: ReportIn) -> ThreatEvent:
        now = datetime.now(UTC)
        observed_at = report.observed_at or now
        unique_ref: str | None = None
        if report.source_message_id:
            unique_ref = f"{report.source}:{report.source_message_id}"
            with self._lock:
                existing_id = self._external_ref_to_event_id.get(unique_ref)
                if existing_id:
                    return self._events[existing_id]
        analyzed = analyze_report(report.text)
        radius_km = risk_radius_km(analyzed.threat_type, analyzed.confidence)
        event = ThreatEvent(
            id=uuid4(),
            threat_type=analyzed.threat_type,
            raw_text=report.text,
            source=report.source,
            source_message_id=report.source_message_id,
            locations=analyzed.locations,
            primary_location=analyzed.primary_location,
            coordinate=analyzed.coordinate,
            direction=analyzed.direction,
            direction_uncertainty_deg=analyzed.direction_uncertainty_deg,
            confidence=analyzed.confidence,
            risk_radius_km=radius_km,
            observed_at=observed_at,
            created_at=now,
            expires_at=observed_at + EVENT_TTL_BY_TYPE[analyzed.threat_type],
            rationale=analyzed.rationale,
        )
        with self._lock:
            self._events[event.id] = event
            if unique_ref:
                self._external_ref_to_event_id[unique_ref] = event.id
        return event

    def list_active(self, include_expired: bool = False) -> list[ThreatEvent]:
        now = datetime.now(UTC)
        with self._lock:
            events = list(self._events.values())
        if not include_expired:
            events = [event for event in events if event.expires_at > now]
        return sorted(events, key=lambda event: event.observed_at, reverse=True)

    def get(self, event_id: UUID) -> ThreatEvent | None:
        with self._lock:
            return self._events.get(event_id)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._external_ref_to_event_id.clear()
