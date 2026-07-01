const threatLabels = {
  shahed: "Шахед",
  uav: "БПЛА",
  gerbera: "Гербера",
  kab: "КАБ",
  fpv: "FPV",
  missile: "Ракета",
  unknown: "Неизв.",
};

const threatColors = {
  shahed: "#ff6b6b",
  uav: "#ffd166",
  gerbera: "#7bd88f",
  kab: "#f78c6b",
  fpv: "#c792ea",
  missile: "#ff4d9d",
  unknown: "#9aa6b2",
};

const demoReports = [
  "Шахед через Миколаївщину курсом на північний захід",
  "БПЛА в районі Кременчук, ймовірно на Полтаву",
  "КАБ у напрямку Харківського району",
  "Гербера біля Одеси, напрямок на північ",
];

const enabledThreats = new Set(Object.keys(threatLabels));
const filtersEl = document.getElementById("filters");
const feedEl = document.getElementById("feed");
const formEl = document.getElementById("reportForm");
const textInput = document.getElementById("textInput");
const sourceInput = document.getElementById("sourceInput");
const apiStatus = document.getElementById("apiStatus");
const apiStatusText = document.getElementById("apiStatusText");

const map = L.map("map", {
  zoomControl: true,
}).setView([49.0, 32.0], 6);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const markerLayer = L.layerGroup().addTo(map);
const directionLayer = L.layerGroup().addTo(map);

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

function formatTime(value) {
  return new Intl.DateTimeFormat("ru", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function markerHtml(event) {
  const label = threatLabels[event.threat_type] || "UNK";
  const shortLabel = label.length > 5 ? label.slice(0, 5) : label;
  const color = threatColors[event.threat_type] || threatColors.unknown;
  return `<div class="marker" style="background:${color}">${shortLabel}</div>`;
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
      dashArray: "8 6",
      opacity: 0.9,
      weight: 4,
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
          <div>${event.primary_location || "Локация не распознана"} / ${event.direction}</div>
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
    const [eventsResponse, geojson] = await Promise.all([
      fetchJson("/api/events"),
      fetchJson("/api/events.geojson"),
    ]);
    markerLayer.clearLayers();
    directionLayer.clearLayers();

    const events = eventsResponse.events || [];
    events
      .filter((event) => enabledThreats.has(event.threat_type))
      .forEach((event) => addMarker(event));

    (geojson.features || []).forEach(addDirection);
    renderFeed(events);
    setStatus(true, `API онлайн · событий: ${events.length}`);
  } catch (error) {
    console.error(error);
    setStatus(false, "API недоступен");
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
setInterval(refresh, 10000);
