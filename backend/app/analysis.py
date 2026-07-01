from __future__ import annotations

import re

from app.geo import GAZETTEER, lookup_coordinate, normalize_location
from app.schemas import AnalyzedReport, Direction, ThreatType


THREAT_PATTERNS: list[tuple[ThreatType, tuple[str, ...]]] = [
    (ThreatType.SHAHED, ("шахед", "shahed", "шахід", "шахид")),
    (ThreatType.GERBERA, ("гербера", "gerbera")),
    (ThreatType.KAB, ("каб", "керована авіабомба", "упаб", "guided bomb")),
    (ThreatType.FPV, ("fpv", "фпв")),
    (ThreatType.MISSILE, ("ракета", "missile", "крилата", "баллист")),
    (ThreatType.UAV, ("бпла", "бпіл", "uav", "дрон", "безпілот")),
]


DIRECTION_PATTERNS: list[tuple[Direction, tuple[str, ...]]] = [
    (Direction.NORTHWEST, ("північний захід", "северо-запад", "пнзх", "nw")),
    (Direction.NORTHEAST, ("північний схід", "северо-восток", "пнсх", "ne")),
    (Direction.SOUTHWEST, ("південний захід", "юго-запад", "пдзх", "sw")),
    (Direction.SOUTHEAST, ("південний схід", "юго-восток", "пдсх", "se")),
    (Direction.NORTH, ("на північ", "на север", "північ", "север", "north")),
    (Direction.SOUTH, ("на південь", "на юг", "південь", "юг", "south")),
    (Direction.WEST, ("на захід", "на запад", "захід", "запад", "west")),
    (Direction.EAST, ("на схід", "на восток", "схід", "восток", "east")),
]


def _contains_term(text: str, term: str) -> bool:
    if re.search(r"[a-zA-Z]", term):
        return term in text
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) is not None


def detect_threat_type(text: str) -> tuple[ThreatType, str | None]:
    normalized = normalize_location(text)
    for threat_type, terms in THREAT_PATTERNS:
        for term in terms:
            if _contains_term(normalized, normalize_location(term)):
                return threat_type, term
    return ThreatType.UNKNOWN, None


def detect_direction(text: str) -> tuple[Direction, str | None]:
    normalized = normalize_location(text)
    for direction, terms in DIRECTION_PATTERNS:
        for term in terms:
            if normalize_location(term) in normalized:
                return direction, term
    return Direction.UNKNOWN, None


def extract_locations(text: str) -> list[str]:
    normalized = normalize_location(text)
    hits: list[str] = []
    for name in GAZETTEER:
        if name in normalized:
            hits.append(name)
    return sorted(set(hits), key=lambda value: normalized.find(value))


def confidence_score(
    threat_type: ThreatType,
    locations: list[str],
    direction: Direction,
    source_weight: float = 0.65,
) -> float:
    score = 0.1
    rationale_parts = [
        source_weight * 0.25,
        (0.25 if threat_type != ThreatType.UNKNOWN else 0.0),
        (0.25 if locations else 0.0),
        (0.15 if direction != Direction.UNKNOWN else 0.0),
    ]
    score += sum(rationale_parts)
    return round(min(score, 0.95), 2)


def analyze_report(text: str, source_weight: float = 0.65) -> AnalyzedReport:
    threat_type, threat_match = detect_threat_type(text)
    direction, direction_match = detect_direction(text)
    locations = extract_locations(text)
    primary_location = locations[0] if locations else None
    coordinate = lookup_coordinate(primary_location) if primary_location else None
    confidence = confidence_score(threat_type, locations, direction, source_weight=source_weight)

    rationale: list[str] = []
    if threat_match:
        rationale.append(f"matched threat term: {threat_match}")
    if primary_location:
        rationale.append(f"matched location: {primary_location}")
    if direction_match:
        rationale.append(f"matched direction term: {direction_match}")
    if not rationale:
        rationale.append("no structured markers found; kept as unknown low-confidence report")

    return AnalyzedReport(
        threat_type=threat_type,
        locations=locations,
        primary_location=primary_location,
        coordinate=coordinate,
        direction=direction,
        confidence=confidence,
        rationale=rationale,
    )
