"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import type { DashboardSnapshot, ThreatType } from "@/lib/types";
import TopBar, { ThreatCard } from "@/components/TopBar";
import { THREAT_LABELS, THREAT_COLORS } from "@/lib/ui";

const ThreatMap = dynamic(() => import("@/components/ThreatMap"), { ssr: false });

const ALL_TYPES = Object.keys(THREAT_LABELS) as ThreatType[];

export default function Dashboard() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [enabledTypes, setEnabledTypes] = useState<Set<ThreatType>>(
    () => new Set(ALL_TYPES),
  );
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const lastAlert = useRef<"green" | "orange" | "red">("green");

  useEffect(() => {
    const source = new EventSource("/api/stream");
    source.onmessage = (event) => {
      const data = JSON.parse(event.data) as DashboardSnapshot;
      setSnapshot(data);
      if (soundEnabled && data.alertLevel === "red" && lastAlert.current !== "red") {
        void playAlertTone();
      }
      lastAlert.current = data.alertLevel;
    };
    source.onerror = () => {
      source.close();
    };
    return () => source.close();
  }, [soundEnabled]);

  const tracks = snapshot?.activeTracks ?? [];
  const history = snapshot?.historyTracks ?? [];

  const selectedTrack = useMemo(
    () => tracks.find((track) => track.id === selectedId) ?? tracks[0] ?? null,
    [tracks, selectedId],
  );

  function toggleType(type: ThreatType) {
    setEnabledTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#04070f] text-white">
      <div className="particles pointer-events-none absolute inset-0" />
      <div className="relative z-10 mx-auto flex min-h-screen max-w-[1600px] flex-col gap-4 p-3 md:p-5">
        <TopBar
          alertLevel={snapshot?.alertLevel ?? "green"}
          activeCount={tracks.length}
          sourceCount={snapshot?.status.sources.length ?? 0}
          lastUpdate={snapshot?.updatedAt ?? null}
          soundEnabled={soundEnabled}
          onToggleSound={() => setSoundEnabled((v) => !v)}
        />

        <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 xl:grid-cols-[360px_1fr]">
          <aside className="glass-panel flex max-h-[42vh] flex-col gap-3 overflow-hidden rounded-3xl p-4 xl:max-h-none">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-200/80">
                Активні цілі
              </h2>
              <span className="text-xs text-slate-400">{tracks.length} live</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {ALL_TYPES.map((type) => (
                <label
                  key={type}
                  className="flex cursor-pointer items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-2 py-1.5 text-xs"
                >
                  <input
                    type="checkbox"
                    checked={enabledTypes.has(type)}
                    onChange={() => toggleType(type)}
                  />
                  <span style={{ color: THREAT_COLORS[type] }}>{THREAT_LABELS[type]}</span>
                </label>
              ))}
            </div>
            <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
              {tracks.length === 0 ? (
                <p className="text-sm text-slate-400">
                  Очікування даних з Telegram-каналів…
                </p>
              ) : (
                tracks.map((track) => (
                  <ThreatCard
                    key={track.id}
                    track={track}
                    selected={selectedTrack?.id === track.id}
                    onSelect={setSelectedId}
                  />
                ))
              )}
            </div>
            <div className="border-t border-white/10 pt-3">
              <h3 className="mb-2 text-xs uppercase tracking-[0.18em] text-slate-400">
                Історія 2 год
              </h3>
              <div className="max-h-28 space-y-1 overflow-y-auto text-xs text-slate-500">
                {history.slice(0, 12).map((track) => (
                  <div key={`${track.id}-history`} className="truncate">
                    {THREAT_LABELS[track.threatType]} · {track.primaryLocation ?? "—"} ·{" "}
                    {track.source}
                  </div>
                ))}
              </div>
            </div>
          </aside>

          <section className="relative min-h-[58vh] xl:min-h-0">
            <ThreatMap
              tracks={tracks}
              enabledTypes={enabledTypes}
              selectedId={selectedTrack?.id ?? null}
              onSelect={setSelectedId}
            />
            {selectedTrack && (
              <div className="glass-panel absolute bottom-4 left-4 right-4 rounded-2xl p-3 md:right-auto md:max-w-md">
                <div className="text-xs uppercase tracking-[0.18em] text-cyan-200/70">
                  Обрана ціль
                </div>
                <div className="mt-1 text-lg font-semibold">
                  {THREAT_LABELS[selectedTrack.threatType]} ·{" "}
                  {selectedTrack.primaryLocation ?? "невідома локація"}
                </div>
                <p className="mt-1 text-sm text-slate-300">{selectedTrack.rawText}</p>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

async function playAlertTone() {
  try {
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = 880;
    gain.gain.value = 0.03;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    setTimeout(() => {
      osc.stop();
      void ctx.close();
    }, 180);
  } catch {
    // optional sound
  }
}
