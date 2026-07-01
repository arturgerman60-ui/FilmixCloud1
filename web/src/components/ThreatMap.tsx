"use client";

import { Fragment, useEffect, useMemo } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Tooltip,
  useMap,
} from "react-leaflet";
import type { ThreatTrack, ThreatType } from "@/lib/types";
import { THREAT_COLORS, THREAT_LABELS } from "@/lib/ui";
import "leaflet/dist/leaflet.css";

function MapResizer() {
  const map = useMap();
  useEffect(() => {
    const timer = setTimeout(() => map.invalidateSize(), 250);
    const onResize = () => map.invalidateSize();
    window.addEventListener("resize", onResize);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("resize", onResize);
    };
  }, [map]);
  return null;
}

type Props = {
  tracks: ThreatTrack[];
  enabledTypes: Set<ThreatType>;
  selectedId: string | null;
  onSelect: (id: string) => void;
};

export default function ThreatMap({
  tracks,
  enabledTypes,
  selectedId,
  onSelect,
}: Props) {
  const visible = useMemo(
    () => tracks.filter((track) => enabledTypes.has(track.threatType) && track.origin),
    [tracks, enabledTypes],
  );

  return (
    <div className="map-shell relative h-full w-full overflow-hidden rounded-3xl border border-cyan-400/20 shadow-[0_0_60px_rgba(0,255,255,0.08)]">
      <div className="pointer-events-none absolute inset-0 z-[500] bg-[radial-gradient(circle_at_20%_20%,rgba(0,255,255,0.08),transparent_35%),radial-gradient(circle_at_80%_70%,rgba(255,0,110,0.08),transparent_40%)]" />
      <MapContainer
        center={[49.0, 31.5]}
        zoom={6}
        className="h-full w-full"
        zoomControl={false}
        preferCanvas
      >
        <MapResizer />
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        {visible.map((track) => {
          const color = THREAT_COLORS[track.threatType];
          const pathLatLng = track.path.map((p) => [p.lat, p.lng] as [number, number]);
          const active = track.animatedPosition ?? track.origin;
          const isSelected = selectedId === track.id;
          return (
            <Fragment key={track.id}>
              {pathLatLng.length > 1 && (
                <Polyline
                  positions={pathLatLng}
                  pathOptions={{
                    color,
                    weight: isSelected ? 5 : 3,
                    opacity: 0.85,
                    dashArray: "10 8",
                    className: "trajectory-line",
                  }}
                />
              )}
              {active && (
                <CircleMarker
                  center={[active.lat, active.lng]}
                  radius={isSelected ? 11 : 8}
                  pathOptions={{
                    color: "#ffffff",
                    weight: 2,
                    fillColor: color,
                    fillOpacity: 0.95,
                    className: "pulse-marker",
                  }}
                  eventHandlers={{ click: () => onSelect(track.id) }}
                >
                  <Tooltip direction="top" offset={[0, -8]} opacity={0.95}>
                    <div className="text-xs">
                      <strong>{THREAT_LABELS[track.threatType]}</strong>
                      <div>{track.primaryLocation ?? "локація невідома"}</div>
                      <div>ETA {track.etaMinutes ?? "—"} хв</div>
                    </div>
                  </Tooltip>
                </CircleMarker>
              )}
            </Fragment>
          );
        })}
      </MapContainer>
    </div>
  );
}
