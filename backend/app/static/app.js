const threatLabels = {
  shahed: "Шахед",
  uav: "БПЛА",
  gerbera: "Гербера",
  kab: "КАБ",
  fpv: "FPV",
  recon_drone: "Развед. дрон",
  missile: "Ракета",
  unknown: "Неизв.",
};

const threatColors = {
  shahed: "#ff6b6b",
  uav: "#ffd166",
  gerbera: "#7bd88f",
  kab: "#f78c6b",
  fpv: "#c792ea",
  recon_drone: "#7ad3ff",
  missile: "#ff4d9d",
  unknown: "#9aa6b2",
};

const threatBadge = {
  shahed: "SHD",
  uav: "UAV",
  gerbera: "GRB",
  kab: "KAB",
  fpv: "FPV",
  recon_drone: "RCN",
  missile: "MSL",
  unknown: "UNK",
};
const POLL_INTERVAL_MS = 5000;

const demoReports = [
  "Шахед у Харківській області курсом на південний захід",
  "Розвіддрон біля Чугуїв, напрямок на Харків",
  "FPV дрон у напрямку Купянськ",
  "КАБ у напрямку Харківського району",
  "Гербера над Ізюмом, курс на північ",
];

const enabledThreats = new Set(Object.keys(threatLabels));
const filtersEl = document.getElementById("filters");
const feedEl = document.getElementById("feed");
const formEl = document.getElementById("reportForm");
const textInput = document.getElementById("textInput");
const sourceInput = document.getElementById("sourceInput");
const apiStatus = document.getElementById("apiStatus");
const apiStatusText = document.getElementById("apiStatusText");
const telegramStatus = document.getElementById("telegramStatus");

const kharkivBounds = [
  [48.55, 34.65],
  [50.55, 38.2],
];
const kharkivCenter = [49.9935, 36.2304];

const map = L.map("map", {
  zoomControl: true,
}).setView(kharkivCenter, 8);

L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
  maxZoom: 18,
  attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
}).addTo(map);
map.fitBounds(kharkivBounds, { padding: [18, 18] });
map.setMaxBounds([
  [44.0, 21.5],
  [53.0, 41.5],
]);

L.rectangle(kharkivBounds, {
  color: "#4da3ff",
  weight: 2,
  opacity: 0.8,
  fillOpacity: 0.08,
}).addTo(map);

L.circle(kharkivCenter, {
  radius: 42000,
  color: "#4da3ff",
  weight: 1.5,
  opacity: 0.8,
  fillOpacity: 0.05,
}).addTo(map);

const markerLayer = L.layerGroup().addTo(map);
const directionLayer = L.layerGroup().addTo(map);

const directionLabels = {
  north: "север",
  northeast: "северо-восток",
  east: "восток",
  southeast: "юго-восток",
  south: "юг",
  southwest: "юго-запад",
  west: "запад",
  northwest: "северо-запад",
  unknown: "не определено",
};

function buildFilters() {
  filtersEl.innerHTML = "";
  Object.entries(threatLabels).forEach(([value, label]) => {
    const pill = document.createElement("label");
    pill.className = "filter-pill";
    pill.innerHTML = `
      <input type="checkbox" value="${value}" checked />
      <span>${label}</span>
    `;
    const input = pill.querySelector("input");
    input.addEventListener("change", () => {
      if (input.checked) {
        enabledThreats.add(value);
      } else {
        enabledThreats.delete(value);
      }
      refresh();
    });
    filtersEl.appendChild(pill);
  });
}

function setStatus(online, text) {
  apiStatus.classList.toggle("online", online);
  apiStatus.classList.toggle("offline", !online);
  apiStatusText.textContent = text;
}

function setTelegramStatus(status) {
  telegramStatus.classList.remove("ok", "warn", "error");
  if (!status || !status.enabled) {
    telegramStatus.classList.add("warn");
    telegramStatus.textContent =
      "Telegram ingestion выключен. Включи TELEGRAM_ENABLED=1 и заполни TELEGRAM_* переменные.";
    return;
  }
  if (status.running) {
    telegramStatus.classList.add("ok");
    const modeLabel =
      status.mode === "bot_api"
        ? "Bot API"
        : status.mode === "web_public"
          ? "Public t.me"
          : "Telethon";
    telegramStatus.textContent = `${modeLabel}: ${status.sources.join(", ")} · сообщений: ${status.ingested_count}`;
    return;
  }
  if (!status.configured) {
    telegramStatus.classList.add("warn");
    telegramStatus.textContent =
      "Telegram включен, но не готов: укажи TELEGRAM_SOURCES и один из режимов (BOT token / Telethon / Public t.me).";
    return;
  }
  if (status.mode === "telethon" && !status.telethon_available) {
    telegramStatus.classList.add("warn");
    telegramStatus.textContent = "Режим Telethon выбран, но пакет telethon не установлен.";
    return;
  }
  if (status.mode === "web_public" && !status.bs4_available) {
    telegramStatus.classList.add("warn");
    telegramStatus.textContent = "Режим Public t.me выбран, но пакет beautifulsoup4 не установлен.";
    return;
  }
  telegramStatus.classList.add("error");
  telegramStatus.textContent = `Telegram остановлен: ${status.last_error || "unknown error"}`;
}

function formatTime(value) {
  return new Intl.DateTimeFormat("ru", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function inKharkivBounds(coordinate) {
  if (!coordinate) return false;
  const [south, west] = kharkivBounds[0];
  const [north, east] = kharkivBounds[1];
  return (
    coordinate.latitude >= south &&
    coordinate.latitude <= north &&
    coordinate.longitude >= west &&
    coordinate.longitude <= east
  );
}

function isKharkivFocused(event) {
  if (event.coordinate && inKharkivBounds(event.coordinate)) return true;
  const location = (event.primary_location || "").toLowerCase();
  return (
    location.includes("харків") ||
    location.includes("харьков") ||
    location.includes("изюм") ||
    location.includes("ізюм") ||
    location.includes("чугуев") ||
    location.includes("чугуїв") ||
    location.includes("купян") ||
    location.includes("балакле") ||
    location.includes("балаклі")
  );
}

function markerHtml(event) {
  const color = threatColors[event.threat_type] || threatColors.unknown;
  const glyphs = {
    shahed: '<path d="M4 22L20 4L36 22L20 30Z" />',
    uav: '<path d="M4 18L20 10L36 18L20 26Z" /><path d="M20 10V30" />',
    gerbera:
      '<circle cx="20" cy="20" r="4" /><circle cx="20" cy="9" r="3" /><circle cx="30" cy="14" r="3" /><circle cx="30" cy="26" r="3" /><circle cx="20" cy="31" r="3" /><circle cx="10" cy="26" r="3" /><circle cx="10" cy="14" r="3" />',
    kab: '<rect x="14" y="6" width="12" height="20" rx="4" /><path d="M20 26V34M15 31H25" />',
    fpv: '<circle cx="20" cy="20" r="6" /><path d="M20 4V12M20 28V36M4 20H12M28 20H36" />',
    recon_drone: '<path d="M6 20C10 10 30 10 34 20C30 30 10 30 6 20Z" /><circle cx="20" cy="20" r="4" />',
    missile: '<path d="M20 4L28 16L20 36L12 16Z" />',
    unknown: '<path d="M20 6C26 6 30 10 30 16C30 20 28 22 24 25C22 26 21 27 21 29H17C17 25 18 23 21 21C24 19 26 17 26 15C26 12 24 10 20 10C16 10 14 12 13 16L9 15C10 10 14 6 20 6Z" /><circle cx="19" cy="33" r="2" />',
  };
  const svg = glyphs[event.threat_type] || glyphs.unknown;
  const fallback = threatBadge[event.threat_type] || "UNK";
  return `
    <div class="marker marker--${event.threat_type}" style="--marker-color:${color}">
      <div class="marker-pulse"></div>
      <svg viewBox="0 0 40 40" aria-hidden="true">${svg}</svg>
      <span>${fallback}</span>
    </div>
  `;
}

function directionText(event) {
  const directionLabel = directionLabels[event.direction] || event.direction || "не определено";
  if (event.direction === "unknown") return `направление: ${directionLabel}`;
  const spread = Number(event.direction_uncertainty_deg || 180);
  return `${directionLabel} ±${spread}°`;
}

function addMarker(event) {
  if (!event.coordinate) return;
  const icon = L.divIcon({
    className: "",
    html: markerHtml(event),
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });
  L.marker([event.coordinate.latitude, event.coordinate.longitude], { icon })
    .bindPopup(
      `<strong>${threatLabels[event.threat_type] || event.threat_type}</strong><br />
       ${event.primary_location || "Локация не распознана"}<br />
       Направление: ${directionText(event)}<br />
       Уверенность: ${Math.round(event.confidence * 100)}%<br />
       Источник: ${event.source}<br />
       <small>${event.raw_text}</small>`,
    )
    .addTo(markerLayer);
}

function addDirection(feature) {
  if (!feature.geometry || feature.geometry.type !== "LineString") return;
  const type = feature.properties.threat_type;
  if (!enabledThreats.has(type)) return;
  L.geoJSON(feature, {
    style: {
      color: threatColors[type] || threatColors.unknown,
      dashArray: "12 10",
      lineCap: "round",
      lineJoin: "round",
      opacity: 0.95,
      weight: 5,
      className: "trajectory-flow",
    },
  }).addTo(directionLayer);
}

function renderFeed(events) {
  const visibleEvents = events.filter((event) => enabledThreats.has(event.threat_type));
  if (!visibleEvents.length) {
    feedEl.innerHTML = `<p class="muted">Нет активных событий по выбранным фильтрам.</p>`;
    return;
  }
  feedEl.innerHTML = visibleEvents
    .map(
      (event) => `
        <article class="event">
          <strong style="color:${threatColors[event.threat_type] || threatColors.unknown}">
            ${threatLabels[event.threat_type] || event.threat_type}
          </strong>
          <div>${event.primary_location || "Локация не распознана"} / ${directionText(event)}</div>
          <div class="event-meta">
            ${formatTime(event.observed_at)} · уверенность ${Math.round(event.confidence * 100)}%
            · радиус риска ${event.risk_radius_km} км<br />
            Источник: ${event.source}<br />
            ${event.raw_text}
          </div>
        </article>
      `,
    )
    .join("");
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  if (response.status === 204) return null;
  return response.json();
}

async function refresh() {
  try {
    const [eventsResponse, geojson, telegram] = await Promise.all([
      fetchJson("/api/events"),
      fetchJson("/api/events.geojson"),
      fetchJson("/api/telegram/status"),
    ]);
    markerLayer.clearLayers();
    directionLayer.clearLayers();

    const allEvents = eventsResponse.events || [];
    const events = allEvents.filter(isKharkivFocused);
    const visibleEventIds = new Set(events.map((event) => event.id));
    events
      .filter((event) => enabledThreats.has(event.threat_type))
      .forEach((event) => addMarker(event));

    (geojson.features || [])
      .filter((feature) => visibleEventIds.has(feature.properties.id))
      .forEach(addDirection);
    renderFeed(events);
    setStatus(
      true,
      `API онлайн · Харьков фокус: ${events.length} из ${allEvents.length} · автообновление ${Math.round(
        POLL_INTERVAL_MS / 1000,
      )}с`,
    );
    setTelegramStatus(telegram);
  } catch (error) {
    console.error(error);
    setStatus(false, "API недоступен");
    setTelegramStatus(null);
  }
}

function refreshMapLayout() {
  map.invalidateSize({ animate: false });
  if (window.innerWidth <= 900) {
    map.fitBounds(kharkivBounds, { padding: [12, 12] });
  }
}

async function submitReport(event) {
  event.preventDefault();
  const text = textInput.value.trim();
  if (!text) return;
  await fetchJson("/api/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      source: sourceInput.value.trim() || "manual",
    }),
  });
  textInput.value = "";
  await refresh();
}

async function seedDemo() {
  const text = demoReports[Math.floor(Math.random() * demoReports.length)];
  textInput.value = text;
  await fetchJson("/api/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, source: "demo" }),
  });
  await refresh();
}

async function clearEvents() {
  await fetchJson("/api/events", { method: "DELETE" });
  await refresh();
}

formEl.addEventListener("submit", submitReport);
document.getElementById("demoButton").addEventListener("click", seedDemo);
document.getElementById("clearButton").addEventListener("click", clearEvents);
document.getElementById("refreshButton").addEventListener("click", refresh);

buildFilters();
refresh();
setTimeout(refreshMapLayout, 200);
window.addEventListener("resize", () => {
  setTimeout(refreshMapLayout, 120);
});
window.addEventListener("orientationchange", () => {
  setTimeout(refreshMapLayout, 200);
});
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) {
    setTimeout(refreshMapLayout, 120);
  }
});
setInterval(refresh, POLL_INTERVAL_MS);
