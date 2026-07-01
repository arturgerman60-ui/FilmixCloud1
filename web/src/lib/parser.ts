import {
  GAZETTEER,
  LOCATION_ALIASES,
  lookupCoordinate,
  normalizeText,
} from "./geo";
import type { ParsedMessage, ThreatType } from "./types";

const THREAT_PATTERNS: Array<[ThreatType, string[]]> = [
  ["shahed", ["шахед", "shahed", "шахід", "шахид", "герань"]],
  ["gerbera", ["гербера", "gerbera"]],
  ["kab", ["каб", "керована авіабомба", "упаб"]],
  ["fpv", ["fpv", "фпв"]],
  ["cruise_missile", ["крилата", "крылатая", "cruise", "калібр", "калибр"]],
  ["ballistic", ["баллист", "баліст", "iskander", "искандер"]],
  ["recon_drone", ["розвіддрон", "разведдрон", "recon drone"]],
  ["uav", ["бпла", "бпіл", "uav", "дрон", "безпілот"]],
];

const DIRECTION_PATTERNS: Array<[number, string, string[]]> = [
  [315, "північний захід", ["північний захід", "северо-запад", "пнзх", "nw"]],
  [45, "північний схід", ["північний схід", "северо-восток", "пнсх", "ne"]],
  [225, "південний захід", ["південний захід", "юго-запад", "пдзх", "sw"]],
  [135, "південний схід", ["південний схід", "юго-восток", "пдсх", "se"]],
  [0, "північ", ["на північ", "на север", "північ", "север", "north"]],
  [180, "південь", ["на південь", "на юг", "південь", "юг", "south"]],
  [270, "захід", ["на захід", "на запад", "захід", "запад", "west"]],
  [90, "схід", ["на схід", "на восток", "схід", "восток", "east"]],
];

function extractLocations(text: string): string[] {
  const normalized = normalizeText(text);
  const matches: Array<[number, number, string]> = [];
  const names = new Set([...Object.keys(GAZETTEER), ...Object.keys(LOCATION_ALIASES)]);
  for (const name of names) {
    const start = normalized.indexOf(name);
    if (start >= 0) {
      matches.push([start, start + name.length, LOCATION_ALIASES[name] ?? name]);
    }
  }
  matches.sort((a, b) => a[0] - b[0] || b[1] - b[0] - (a[1] - a[0]));
  const seen = new Set<string>();
  const spans: Array<[number, number]> = [];
  const locations: string[] = [];
  for (const [start, end, canonical] of matches) {
    if (seen.has(canonical)) continue;
    if (spans.some(([s, e]) => start < e && end > s)) continue;
    seen.add(canonical);
    spans.push([start, end]);
    locations.push(canonical);
  }
  return locations;
}

export function parseMessage(text: string): ParsedMessage {
  const normalized = normalizeText(text);
  let threatType: ThreatType = "unknown";
  let threatMatch: string | null = null;
  for (const [type, terms] of THREAT_PATTERNS) {
    for (const term of terms) {
      if (normalized.includes(normalizeText(term))) {
        threatType = type;
        threatMatch = term;
        break;
      }
    }
    if (threatType !== "unknown") break;
  }

  let directionDeg: number | null = null;
  let directionLabel = "невідомо";
  let directionMatch: string | null = null;
  for (const [deg, label, terms] of DIRECTION_PATTERNS) {
    for (const term of terms) {
      if (normalized.includes(normalizeText(term))) {
        directionDeg = deg;
        directionLabel = label;
        directionMatch = term;
        break;
      }
    }
    if (directionDeg !== null) break;
  }

  const locations = extractLocations(text);
  const primaryLocation = locations[0] ?? null;
  const coordinate = lookupCoordinate(primaryLocation);
  const confidence = Math.min(
    0.95,
    0.15 +
      (threatType !== "unknown" ? 0.28 : 0) +
      (primaryLocation ? 0.28 : 0) +
      (directionDeg !== null ? 0.18 : 0),
  );

  const rationale: string[] = [];
  if (threatMatch) rationale.push(`тип: ${threatMatch}`);
  if (primaryLocation) rationale.push(`локація: ${primaryLocation}`);
  if (directionMatch) rationale.push(`напрямок: ${directionMatch}`);
  if (!rationale.length) rationale.push("мало структурованих маркерів");

  return {
    threatType,
    locations,
    primaryLocation,
    coordinate,
    directionDeg,
    directionLabel,
    confidence,
    rationale,
  };
}

export function isAlertMessage(text: string): boolean {
  const normalized = normalizeText(text);
  return ["тривога", "тревога", "alert", "повітряна", "воздушная"].some((term) =>
    normalized.includes(term),
  );
}
