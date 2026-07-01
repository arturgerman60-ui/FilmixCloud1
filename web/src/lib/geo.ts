import type { Coordinate } from "./types";

export const GAZETTEER: Record<string, Coordinate> = {
  київ: { lat: 50.45, lng: 30.52 },
  киев: { lat: 50.45, lng: 30.52 },
  харків: { lat: 49.99, lng: 36.23 },
  харьков: { lat: 49.99, lng: 36.23 },
  харківщина: { lat: 49.95, lng: 36.37 },
  харьковщина: { lat: 49.95, lng: 36.37 },
  дніпро: { lat: 48.46, lng: 35.05 },
  днепр: { lat: 48.46, lng: 35.05 },
  одеса: { lat: 46.48, lng: 30.73 },
  одесса: { lat: 46.48, lng: 30.73 },
  полтава: { lat: 49.59, lng: 34.55 },
  кременчук: { lat: 49.07, lng: 33.42 },
  запоріжжя: { lat: 47.84, lng: 35.14 },
  запорожье: { lat: 47.84, lng: 35.14 },
  суми: { lat: 50.91, lng: 34.8 },
  чернігів: { lat: 51.49, lng: 31.29 },
  чернигов: { lat: 51.49, lng: 31.29 },
  львів: { lat: 49.84, lng: 24.03 },
  львов: { lat: 49.84, lng: 24.03 },
  миколаїв: { lat: 46.98, lng: 31.99 },
  николаев: { lat: 46.98, lng: 31.99 },
  чугуїв: { lat: 49.84, lng: 36.69 },
  чугуев: { lat: 49.84, lng: 36.69 },
  ізюм: { lat: 49.21, lng: 37.27 },
  изюм: { lat: 49.21, lng: 37.27 },
  купянськ: { lat: 49.71, lng: 37.62 },
  купянск: { lat: 49.71, lng: 37.62 },
};

export const LOCATION_ALIASES: Record<string, string> = {
  харкові: "харків",
  харькове: "харьков",
  харківського: "харків",
  харьковского: "харьков",
  харківщину: "харківщина",
  харьковщину: "харьковщина",
};

export const MAJOR_TARGETS = [
  "київ",
  "харків",
  "дніпро",
  "одеса",
  "полтава",
  "запоріжжя",
  "суми",
  "чернігів",
  "львів",
  "миколаїв",
];

export function normalizeText(value: string): string {
  return value.trim().toLowerCase().replace(/ё/g, "е");
}

export function lookupCoordinate(location: string | null): Coordinate | null {
  if (!location) return null;
  const normalized = normalizeText(location);
  const canonical = LOCATION_ALIASES[normalized] ?? normalized;
  return GAZETTEER[canonical] ?? null;
}

export function destinationPoint(
  origin: Coordinate,
  bearingDeg: number,
  distanceKm: number,
): Coordinate {
  const radiusKm = 6371;
  const bearing = (bearingDeg * Math.PI) / 180;
  const lat1 = (origin.lat * Math.PI) / 180;
  const lng1 = (origin.lng * Math.PI) / 180;
  const angular = distanceKm / radiusKm;

  const lat2 = Math.asin(
    Math.sin(lat1) * Math.cos(angular) +
      Math.cos(lat1) * Math.sin(angular) * Math.cos(bearing),
  );
  const lng2 =
    lng1 +
    Math.atan2(
      Math.sin(bearing) * Math.sin(angular) * Math.cos(lat1),
      Math.cos(angular) - Math.sin(lat1) * Math.sin(lat2),
    );

  return {
    lat: (lat2 * 180) / Math.PI,
    lng: (lng2 * 180) / Math.PI,
  };
}

export function haversineKm(a: Coordinate, b: Coordinate): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
}

export function interpolatePath(path: Coordinate[], progress: number): Coordinate | null {
  if (!path.length) return null;
  if (path.length === 1) return path[0];
  const clamped = Math.max(0, Math.min(1, progress));
  const total = path.length - 1;
  const scaled = clamped * total;
  const idx = Math.floor(scaled);
  const t = scaled - idx;
  if (idx >= total) return path[path.length - 1];
  const a = path[idx];
  const b = path[idx + 1];
  return {
    lat: a.lat + (b.lat - a.lat) * t,
    lng: a.lng + (b.lng - a.lng) * t,
  };
}
