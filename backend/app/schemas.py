from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ThreatType(StrEnum):
    SHAHED = "shahed"
    UAV = "uav"
    GERBERA = "gerbera"
    KAB = "kab"
    FPV = "fpv"
    RECON_DRONE = "recon_drone"
    MISSILE = "missile"
    UNKNOWN = "unknown"


class Direction(StrEnum):
    NORTH = "north"
    NORTHEAST = "northeast"
    EAST = "east"
    SOUTHEAST = "southeast"
    SOUTH = "south"
    SOUTHWEST = "southwest"
    WEST = "west"
    NORTHWEST = "northwest"
    UNKNOWN = "unknown"


class Coordinate(BaseModel):
    latitude: float
    longitude: float


class ReportIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    source: str = Field(default="manual", max_length=120)
    source_message_id: str | None = Field(default=None, max_length=120)
    observed_at: datetime | None = None


class AnalyzedReport(BaseModel):
    threat_type: ThreatType
    locations: list[str]
    primary_location: str | None
    coordinate: Coordinate | None
    direction: Direction
    direction_uncertainty_deg: int = Field(ge=0, le=180)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: list[str]


class ThreatEvent(BaseModel):
    id: UUID
    threat_type: ThreatType
    raw_text: str
    source: str
    source_message_id: str | None
    locations: list[str]
    primary_location: str | None
    coordinate: Coordinate | None
    direction: Direction
    direction_uncertainty_deg: int = Field(ge=0, le=180)
    confidence: float = Field(ge=0.0, le=1.0)
    risk_radius_km: float
    observed_at: datetime
    created_at: datetime
    expires_at: datetime
    rationale: list[str]


class EventList(BaseModel):
    events: list[ThreatEvent]


class HealthResponse(BaseModel):
    status: str
    event_count: int


class GeoJsonFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, Any]


class GeoJsonFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[GeoJsonFeature]
