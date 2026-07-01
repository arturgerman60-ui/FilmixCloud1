import type { AlertLevel, ThreatType } from "@/lib/types";

export const THREAT_LABELS: Record<ThreatType, string> = {
  shahed: "Шахед",
  fpv: "FPV",
  kab: "КАБ",
  cruise_missile: "Крилата",
  ballistic: "Балістика",
  gerbera: "Гербера",
  uav: "БПЛА",
  recon_drone: "Розвід",
  unknown: "Невідомо",
};

export const THREAT_COLORS: Record<ThreatType, string> = {
  shahed: "#ff4d6d",
  fpv: "#c77dff",
  kab: "#ff9f1c",
  cruise_missile: "#ff006e",
  ballistic: "#fb5607",
  gerbera: "#8ecae6",
  uav: "#ffd166",
  recon_drone: "#4cc9f0",
  unknown: "#9aa6b2",
};

export const ALERT_LABELS: Record<AlertLevel, string> = {
  green: "Ситуація спокійна",
  orange: "Підвищена активність",
  red: "Повітряна загроза",
};

export const ALERT_COLORS: Record<AlertLevel, string> = {
  green: "#3ddc97",
  orange: "#ffb703",
  red: "#ff4d6d",
};

export function formatTime(value: string): string {
  return new Intl.DateTimeFormat("uk-UA", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

export function formatEta(minutes: number | null): string {
  if (minutes === null) return "—";
  if (minutes <= 0) return "зараз";
  return `~${minutes} хв`;
}
