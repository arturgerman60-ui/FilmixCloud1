export type ThreatType =
  | "shahed"
  | "fpv"
  | "kab"
  | "cruise_missile"
  | "ballistic"
  | "gerbera"
  | "uav"
  | "recon_drone"
  | "unknown";

export type AlertLevel = "green" | "orange" | "red";

export type Coordinate = {
  lat: number;
  lng: number;
};

export type ParsedMessage = {
  threatType: ThreatType;
  locations: string[];
  primaryLocation: string | null;
  coordinate: Coordinate | null;
  directionDeg: number | null;
  directionLabel: string;
  confidence: number;
  rationale: string[];
};

export type ThreatTrack = {
  id: string;
  threatType: ThreatType;
  source: string;
  sourceMessageId: string;
  rawText: string;
  observedAt: string;
  expiresAt: string;
  origin: Coordinate | null;
  primaryLocation: string | null;
  directionDeg: number | null;
  directionLabel: string;
  speedKmh: number;
  confidence: number;
  path: Coordinate[];
  animatedPosition: Coordinate | null;
  progress: number;
  etaMinutes: number | null;
  probableTargets: Array<{ name: string; probability: number }>;
  rationale: string[];
};

export type IngestStatus = {
  running: boolean;
  mode: "web_public" | "demo";
  sources: string[];
  ingestedCount: number;
  lastPollAt: string | null;
  lastError: string | null;
  bootstrapLimit: number;
  pollSeconds: number;
};

export type DashboardSnapshot = {
  alertLevel: AlertLevel;
  activeTracks: ThreatTrack[];
  historyTracks: ThreatTrack[];
  status: IngestStatus;
  updatedAt: string;
};
