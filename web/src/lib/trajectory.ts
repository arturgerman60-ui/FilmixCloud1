import {
  destinationPoint,
  GAZETTEER,
  haversineKm,
  interpolatePath,
  lookupCoordinate,
} from "./geo";
import type { Coordinate, ParsedMessage, ThreatTrack, ThreatType } from "./types";

const SPEED_KMH: Record<ThreatType, number> = {
  shahed: 185,
  fpv: 120,
  kab: 700,
  cruise_missile: 900,
  ballistic: 3200,
  gerbera: 150,
  uav: 180,
  recon_drone: 160,
  unknown: 220,
};

const TTL_MINUTES: Record<ThreatType, number> = {
  shahed: 50,
  fpv: 20,
  kab: 25,
  cruise_missile: 30,
  ballistic: 15,
  gerbera: 35,
  uav: 40,
  recon_drone: 35,
  unknown: 30,
};

function buildPath(
  origin: Coordinate,
  directionDeg: number,
  speedKmh: number,
  minutes: number,
): Coordinate[] {
  const points: Coordinate[] = [origin];
  const stepMinutes = 4;
  const steps = Math.max(3, Math.ceil(minutes / stepMinutes));
  const distancePerStep = (speedKmh * stepMinutes) / 60;
  let current = origin;
  for (let i = 1; i <= steps; i += 1) {
    const wobble = Math.sin(i * 0.9) * 4;
    current = destinationPoint(current, directionDeg + wobble, distancePerStep);
    points.push(current);
  }
  return points;
}

function probableTargets(
  origin: Coordinate | null,
  directionDeg: number | null,
): Array<{ name: string; probability: number }> {
  if (!origin || directionDeg === null) return [];
  const scored = Object.entries(GAZETTEER).map(([name, coord]) => {
    const distance = haversineKm(origin, coord);
    const bearingToTarget =
      (Math.atan2(
        Math.sin(((coord.lng - origin.lng) * Math.PI) / 180) *
          Math.cos((coord.lat * Math.PI) / 180),
        Math.cos((origin.lat * Math.PI) / 180) *
          Math.sin((coord.lat * Math.PI) / 180) -
          Math.sin((origin.lat * Math.PI) / 180) *
            Math.cos((coord.lat * Math.PI) / 180) *
            Math.cos(((coord.lng - origin.lng) * Math.PI) / 180),
      ) *
        180) /
      Math.PI;
    const normalizedBearing = (bearingToTarget + 360) % 360;
    let angleDiff = Math.abs(normalizedBearing - directionDeg);
    if (angleDiff > 180) angleDiff = 360 - angleDiff;
    const directionScore = Math.max(0, 1 - angleDiff / 70);
    const distanceScore = Math.max(0, 1 - distance / 450);
    const probability = Math.round((directionScore * 0.65 + distanceScore * 0.35) * 100);
    return { name, probability };
  });
  return scored
    .filter((item) => item.probability >= 20)
    .sort((a, b) => b.probability - a.probability)
    .slice(0, 4);
}

export function buildTrack(input: {
  id: string;
  source: string;
  sourceMessageId: string;
  rawText: string;
  observedAt: Date;
  parsed: ParsedMessage;
}): ThreatTrack {
  const { parsed, observedAt } = input;
  const speedKmh = SPEED_KMH[parsed.threatType];
  const ttlMinutes = TTL_MINUTES[parsed.threatType];
  const origin = parsed.coordinate;
  const directionDeg = parsed.directionDeg ?? 90;
  const path =
    origin && parsed.directionDeg !== null
      ? buildPath(origin, directionDeg, speedKmh, ttlMinutes)
      : origin
        ? [origin]
        : [];
  const now = Date.now();
  const elapsedMinutes = (now - observedAt.getTime()) / 60000;
  const progress = path.length > 1 ? Math.min(1, elapsedMinutes / ttlMinutes) : 0;
  const animatedPosition = interpolatePath(path, progress);
  const remainingKm =
    path.length > 1 && animatedPosition
      ? haversineKm(animatedPosition, path[path.length - 1])
      : 0;
  const etaMinutes = speedKmh > 0 ? Math.round((remainingKm / speedKmh) * 60) : null;

  return {
    id: input.id,
    threatType: parsed.threatType,
    source: input.source,
    sourceMessageId: input.sourceMessageId,
    rawText: input.rawText,
    observedAt: observedAt.toISOString(),
    expiresAt: new Date(observedAt.getTime() + ttlMinutes * 60000).toISOString(),
    origin,
    primaryLocation: parsed.primaryLocation,
    directionDeg: parsed.directionDeg,
    directionLabel: parsed.directionLabel,
    speedKmh,
    confidence: parsed.confidence,
    path,
    animatedPosition,
    progress,
    etaMinutes,
    probableTargets: probableTargets(origin, parsed.directionDeg),
    rationale: parsed.rationale,
  };
}

export function refreshTrackMotion(track: ThreatTrack): ThreatTrack {
  const observedAt = new Date(track.observedAt);
  const ttlMinutes =
    (new Date(track.expiresAt).getTime() - observedAt.getTime()) / 60000;
  const elapsedMinutes = (Date.now() - observedAt.getTime()) / 60000;
  const progress =
    track.path.length > 1 ? Math.min(1, elapsedMinutes / ttlMinutes) : 0;
  const animatedPosition = interpolatePath(track.path, progress);
  const remainingKm =
    track.path.length > 1 && animatedPosition
      ? haversineKm(animatedPosition, track.path[track.path.length - 1])
      : 0;
  const etaMinutes =
    track.speedKmh > 0 ? Math.round((remainingKm / track.speedKmh) * 60) : null;
  return {
    ...track,
    animatedPosition,
    progress,
    etaMinutes,
    probableTargets: probableTargets(track.origin, track.directionDeg),
  };
}

export function lookupCityCoordinate(name: string) {
  return lookupCoordinate(name);
}
