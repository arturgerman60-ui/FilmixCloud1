import * as cheerio from "cheerio";
import { v4 as uuidv4 } from "uuid";
import { parseMessage } from "./parser";
import { PUBLIC_TELEGRAM_SOURCES, CONFIG } from "./sources";
import { buildTrack } from "./trajectory";
import type { IngestStatus, ThreatTrack } from "./types";

type RawMessage = {
  source: string;
  messageId: number;
  text: string;
  observedAt: Date;
};

class ThreatStore {
  private tracks = new Map<string, ThreatTrack>();
  private seen = new Set<string>();
  private status: IngestStatus = {
    running: false,
    mode: "web_public",
    sources: PUBLIC_TELEGRAM_SOURCES,
    ingestedCount: 0,
    lastPollAt: null,
    lastError: null,
    bootstrapLimit: CONFIG.bootstrapLimit,
    pollSeconds: CONFIG.pollSeconds,
  };
  private pollTimer: NodeJS.Timeout | null = null;
  private bootstrapped = new Set<string>();
  private started = false;

  start() {
    if (this.started) return;
    this.started = true;
    this.status.running = true;
    void this.poll();
    this.pollTimer = setInterval(() => void this.poll(), CONFIG.pollSeconds * 1000);
  }

  getStatus(): IngestStatus {
    return { ...this.status };
  }

  getSnapshot() {
    const now = Date.now();
    const historyMs = CONFIG.historyHours * 60 * 60 * 1000;
    const all = [...this.tracks.values()]
      .map((track) => this.refresh(track))
      .sort((a, b) => +new Date(b.observedAt) - +new Date(a.observedAt));
    const active = all.filter((track) => +new Date(track.expiresAt) > now);
    const history = all.filter(
      (track) => now - +new Date(track.observedAt) <= historyMs,
    );
    const alertLevel =
      active.some((t) => ["shahed", "cruise_missile", "ballistic", "kab"].includes(t.threatType))
        ? "red"
        : active.length
          ? "orange"
          : "green";
    return {
      alertLevel,
      activeTracks: active,
      historyTracks: history,
      status: this.getStatus(),
      updatedAt: new Date().toISOString(),
    };
  }

  private refresh(track: ThreatTrack): ThreatTrack {
    const observedAt = new Date(track.observedAt);
    const ttlMinutes =
      (new Date(track.expiresAt).getTime() - observedAt.getTime()) / 60000;
    const elapsedMinutes = (Date.now() - observedAt.getTime()) / 60000;
    const progress =
      track.path.length > 1 ? Math.min(1, elapsedMinutes / ttlMinutes) : 0;
    const animatedPosition = track.path.length
      ? this.interpolate(track.path, progress)
      : null;
    const updated = {
      ...track,
      animatedPosition,
      progress,
    };
    this.tracks.set(track.id, updated);
    return updated;
  }

  private interpolate(
    path: Array<{ lat: number; lng: number }>,
    progress: number,
  ) {
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
    return { lat: a.lat + (b.lat - a.lat) * t, lng: a.lng + (b.lng - a.lng) * t };
  }

  private async poll() {
    try {
      for (const source of PUBLIC_TELEGRAM_SOURCES) {
        await this.syncSource(source);
      }
      this.status.lastPollAt = new Date().toISOString();
      this.status.lastError = null;
    } catch (error) {
      this.status.lastError = error instanceof Error ? error.message : "poll failed";
    }
  }

  private async syncSource(source: string) {
    const response = await fetch(`https://t.me/s/${source}`, {
      headers: { "User-Agent": "ThreatMonitor/1.0" },
      cache: "no-store",
    });
    if (!response.ok) throw new Error(`failed to fetch ${source}: ${response.status}`);
    const html = await response.text();
    const messages = this.extractMessages(html, source);
    if (!messages.length) return;

    if (!this.bootstrapped.has(source)) {
      const bootstrap = messages
        .sort((a, b) => a.messageId - b.messageId)
        .slice(-CONFIG.bootstrapLimit);
      for (const message of bootstrap) this.ingest(message);
      this.bootstrapped.add(source);
      return;
    }

    const latestSeen = Math.max(...messages.map((m) => m.messageId));
    const incoming = messages
      .filter((message) => !this.seen.has(`${source}:${message.messageId}`))
      .sort((a, b) => a.messageId - b.messageId);
    for (const message of incoming) this.ingest(message);
    if (incoming.length) this.bootstrapped.add(source);
    void latestSeen;
  }

  private extractMessages(html: string, fallbackSource: string): RawMessage[] {
    const $ = cheerio.load(html);
    const messages: RawMessage[] = [];
    $("div.tgme_widget_message").each((_, element) => {
      const dataPost = String($(element).attr("data-post") ?? "");
      if (!dataPost.includes("/")) return;
      const [source, messageIdRaw] = dataPost.split("/");
      if (!messageIdRaw || !/^\d+$/.test(messageIdRaw)) return;
      const text = $(element).find("div.tgme_widget_message_text").text().trim();
      if (!text) return;
      const timestampRaw = String($(element).attr("data-time") ?? "");
      const observedAt = timestampRaw
        ? new Date(Number(timestampRaw) * 1000)
        : new Date();
      messages.push({
        source: (source || fallbackSource).toLowerCase(),
        messageId: Number(messageIdRaw),
        text,
        observedAt,
      });
    });
    return messages;
  }

  private ingest(message: RawMessage) {
    const key = `${message.source}:${message.messageId}`;
    if (this.seen.has(key)) return;
    const parsed = parseMessage(message.text);
    if (parsed.threatType === "unknown" && !parsed.primaryLocation) return;
    const track = buildTrack({
      id: uuidv4(),
      source: `tg:${message.source}`,
      sourceMessageId: key,
      rawText: message.text,
      observedAt: message.observedAt,
      parsed,
    });
    this.tracks.set(track.id, track);
    this.seen.add(key);
    this.status.ingestedCount += 1;
  }
}

const globalStore = globalThis as typeof globalThis & {
  __threatStore?: ThreatStore;
};

export function getThreatStore(): ThreatStore {
  if (!globalStore.__threatStore) {
    globalStore.__threatStore = new ThreatStore();
    globalStore.__threatStore.start();
  }
  return globalStore.__threatStore;
}
