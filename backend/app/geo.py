from __future__ import annotations

import math

from app.schemas import Coordinate, Direction, ThreatType


# Minimal MVP gazetteer. Replace with a complete geocoder/PostGIS table before operational use.
GAZETTEER: dict[str, Coordinate] = {
    "миколаївщина": Coordinate(latitude=47.16, longitude=31.98),
    "николаевщина": Coordinate(latitude=47.16, longitude=31.98),
    "миколаїв": Coordinate(latitude=46.98, longitude=31.99),
    "николаев": Coordinate(latitude=46.98, longitude=31.99),
    "одеса": Coordinate(latitude=46.48, longitude=30.73),
    "одесса": Coordinate(latitude=46.48, longitude=30.73),
    "київ": Coordinate(latitude=50.45, longitude=30.52),
    "киев": Coordinate(latitude=50.45, longitude=30.52),
    "харків": Coordinate(latitude=49.99, longitude=36.23),
    "харьков": Coordinate(latitude=49.99, longitude=36.23),
    "харківщина": Coordinate(latitude=49.95, longitude=36.37),
    "харьковщина": Coordinate(latitude=49.95, longitude=36.37),
    "харківська область": Coordinate(latitude=49.95, longitude=36.37),
    "харьковская область": Coordinate(latitude=49.95, longitude=36.37),
    "чугуїв": Coordinate(latitude=49.84, longitude=36.69),
    "чугуев": Coordinate(latitude=49.84, longitude=36.69),
    "ізюм": Coordinate(latitude=49.21, longitude=37.27),
    "изюм": Coordinate(latitude=49.21, longitude=37.27),
    "купянськ": Coordinate(latitude=49.71, longitude=37.62),
    "купянск": Coordinate(latitude=49.71, longitude=37.62),
    "балаклія": Coordinate(latitude=49.46, longitude=36.84),
    "балаклея": Coordinate(latitude=49.46, longitude=36.84),
    "дергачі": Coordinate(latitude=50.11, longitude=36.12),
    "дергачи": Coordinate(latitude=50.11, longitude=36.12),
    "лозова": Coordinate(latitude=48.90, longitude=36.31),
    "дніпро": Coordinate(latitude=48.46, longitude=35.05),
    "днепр": Coordinate(latitude=48.46, longitude=35.05),
    "запоріжжя": Coordinate(latitude=47.84, longitude=35.14),
    "запорожье": Coordinate(latitude=47.84, longitude=35.14),
    "полтава": Coordinate(latitude=49.59, longitude=34.55),
    "кременчук": Coordinate(latitude=49.07, longitude=33.42),
    "черкаси": Coordinate(latitude=49.44, longitude=32.06),
    "суми": Coordinate(latitude=50.91, longitude=34.80),
    "чернігів": Coordinate(latitude=51.49, longitude=31.29),
    "чернигов": Coordinate(latitude=51.49, longitude=31.29),
    "львів": Coordinate(latitude=49.84, longitude=24.03),
    "львов": Coordinate(latitude=49.84, longitude=24.03),
}


LOCATION_ALIASES: dict[str, str] = {
    "миколаївщину": "миколаївщина",
    "николаевщину": "николаевщина",
    "харківського": "харків",
    "харьковского": "харьков",
    "харківщину": "харківщина",
    "харьковщину": "харьковщина",
    "харківщині": "харківщина",
    "харьковщине": "харьковщина",
    "харкові": "харків",
    "харькове": "харьков",
    "у харкові": "харків",
    "в харькове": "харьков",
    "полтавщину": "полтава",
}


DIRECTION_BEARINGS: dict[Direction, float] = {
    Direction.NORTH: 0,
    Direction.NORTHEAST: 45,
    Direction.EAST: 90,
    Direction.SOUTHEAST: 135,
    Direction.SOUTH: 180,
    Direction.SOUTHWEST: 225,
    Direction.WEST: 270,
    Direction.NORTHWEST: 315,
}


def normalize_location(text: str) -> str:
    return text.strip().lower().replace("ё", "е")


def lookup_coordinate(location: str) -> Coordinate | None:
    normalized = normalize_location(location)
    canonical = LOCATION_ALIASES.get(normalized, normalized)
    return GAZETTEER.get(canonical)


def risk_radius_km(threat_type: ThreatType, confidence: float) -> float:
    base_radius = {
        ThreatType.SHAHED: 35.0,
        ThreatType.UAV: 25.0,
        ThreatType.GERBERA: 20.0,
        ThreatType.KAB: 18.0,
        ThreatType.FPV: 8.0,
        ThreatType.RECON_DRONE: 22.0,
        ThreatType.MISSILE: 45.0,
        ThreatType.UNKNOWN: 30.0,
    }[threat_type]
    uncertainty_multiplier = 1.3 - min(max(confidence, 0.0), 1.0) * 0.4
    return round(base_radius * uncertainty_multiplier, 1)


def destination_point(origin: Coordinate, bearing_degrees: float, distance_km: float) -> Coordinate:
    radius_km = 6371.0
    bearing = math.radians(bearing_degrees)
    lat1 = math.radians(origin.latitude)
    lon1 = math.radians(origin.longitude)
    angular_distance = distance_km / radius_km

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_distance)
        + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
    )
    return Coordinate(latitude=math.degrees(lat2), longitude=math.degrees(lon2))


def risk_geometry(
    coordinate: Coordinate | None,
    direction: Direction,
    radius_km: float,
) -> dict:
    if coordinate is None:
        return {"type": "GeometryCollection", "geometries": []}

    if direction in DIRECTION_BEARINGS:
        end = destination_point(coordinate, DIRECTION_BEARINGS[direction], max(radius_km * 2.5, 25.0))
        return {
            "type": "LineString",
            "coordinates": [
                [coordinate.longitude, coordinate.latitude],
                [end.longitude, end.latitude],
            ],
        }

    return {
        "type": "Point",
        "coordinates": [coordinate.longitude, coordinate.latitude],
    }
