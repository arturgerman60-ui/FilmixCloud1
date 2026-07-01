"use client";

import type { ThreatTrack } from "@/lib/types";
import {
  ALERT_COLORS,
  ALERT_LABELS,
  formatEta,
  formatTime,
  THREAT_COLORS,
  THREAT_LABELS,
} from "@/lib/ui";

type Props = {
  alertLevel: "green" | "orange" | "red";
  activeCount: number;
  sourceCount: number;
  lastUpdate: string | null;
  soundEnabled: boolean;
  onToggleSound: () => void;
};

export default function TopBar({
  alertLevel,
  activeCount,
  sourceCount,
  lastUpdate,
  soundEnabled,
  onToggleSound,
}: Props) {
  return (
    <header className="glass-panel flex flex-wrap items-center justify-between gap-3 rounded-2xl px-4 py-3">
      <div>
        <p className="text-xs uppercase tracking-[0.28em] text-cyan-300/80">
          Ukraine Air Threat Monitor 2026
        </p>
        <h1 className="text-xl font-semibold text-white md:text-2xl">
          Реал-тайм моніторинг повітряних загроз
        </h1>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <div
          className="rounded-full px-4 py-2 text-sm font-semibold"
          style={{
            color: ALERT_COLORS[alertLevel],
            background: `${ALERT_COLORS[alertLevel]}22`,
            border: `1px solid ${ALERT_COLORS[alertLevel]}66`,
          }}
        >
          {ALERT_LABELS[alertLevel]}
        </div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-300">
          Активних: <span className="font-semibold text-white">{activeCount}</span>
        </div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-300">
          Джерел: <span className="font-semibold text-white">{sourceCount}</span>
        </div>
        <button
          type="button"
          onClick={onToggleSound}
          className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-xs text-cyan-100 transition hover:bg-cyan-400/20"
        >
          Звук: {soundEnabled ? "ON" : "OFF"}
        </button>
        <div className="text-xs text-slate-400">
          Оновлено: {lastUpdate ? formatTime(lastUpdate) : "—"}
        </div>
      </div>
    </header>
  );
}

export function ThreatCard({
  track,
  selected,
  onSelect,
}: {
  track: ThreatTrack;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  const color = THREAT_COLORS[track.threatType];
  return (
    <button
      type="button"
      onClick={() => onSelect(track.id)}
      className={`w-full rounded-2xl border p-3 text-left transition ${
        selected
          ? "border-cyan-300/50 bg-cyan-400/10 shadow-[0_0_24px_rgba(0,255,255,0.12)]"
          : "border-white/10 bg-white/5 hover:border-white/20"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold" style={{ color }}>
          {THREAT_LABELS[track.threatType]}
        </span>
        <span className="text-xs text-slate-400">{formatTime(track.observedAt)}</span>
      </div>
      <p className="mt-1 text-sm text-slate-200">
        {track.primaryLocation ?? "Локація невідома"} · {track.directionLabel}
      </p>
      <div className="mt-2 grid grid-cols-3 gap-2 text-[11px] text-slate-400">
        <div>
          Швидкість
          <div className="font-semibold text-white">{track.speedKmh} км/год</div>
        </div>
        <div>
          ETA
          <div className="font-semibold text-white">{formatEta(track.etaMinutes)}</div>
        </div>
        <div>
          Впевненість
          <div className="font-semibold text-white">{Math.round(track.confidence * 100)}%</div>
        </div>
      </div>
      {track.probableTargets.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {track.probableTargets.map((target) => (
            <span
              key={target.name}
              className="rounded-full border border-white/10 bg-black/20 px-2 py-0.5 text-[10px] text-slate-300"
            >
              {target.name} {target.probability}%
            </span>
          ))}
        </div>
      )}
      <p className="mt-2 line-clamp-2 text-xs text-slate-500">{track.rawText}</p>
    </button>
  );
}
