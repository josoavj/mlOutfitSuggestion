const endpoints = [
  {
    id: "health",
    method: "GET",
    path: "/health",
    name: "Santé",
    category: "Core",
    description: "Vérification de l'état du service",
    sample: "",
  },
  {
    id: "dashboard",
    method: "GET",
    path: "/dashboard/technical",
    name: "Dashboard technique",
    category: "Dashboard",
    description: "Métriques modèle, feedback et état du service",
    sample: "",
  },
  {
    id: "recommend",
    method: "POST",
    path: "/recommend",
    name: "Recommandation (manuel)",
    category: "Recommendations",
    description: "Payload manuel avec météo et agenda",
    sample: JSON.stringify(
      {
        user_id: "u-001",
        gender: "female",
        age: 29,
        height_cm: 168,
        clothing_size: "m",
        top_size: "m",
        bottom_size: "m",
        shoe_size: "40",
        style_preferences: ["minimalist", "elegant"],
        body_shape: "hourglass",
        agenda: ["work", "meeting"],
        location: "Lyon",
        weather: { temperature_c: 14.0, condition: "rain" },
        top_k: 3,
      },
      null,
      2
    ),
  },
  {
    id: "recommend-context",
    method: "POST",
    path: "/recommend/context",
    name: "Recommandation (contexte)",
    category: "Recommendations",
    description: "Agenda structuré + localisation",
    sample: JSON.stringify(
      {
        user_id: "u-001",
        gender: "female",
        age: 29,
        height_cm: 168,
        clothing_size: "m",
        top_size: "m",
        bottom_size: "m",
        shoe_size: "40",
        style_preferences: ["minimalist", "elegant"],
        body_shape: "hourglass",
        agenda_entries: [
          { title: "Client meeting", category: "work", tags: ["meeting"] },
          { title: "Evening run", category: "sport", tags: ["outdoor"] },
        ],
        location: "Lyon",
        top_k: 3,
      },
      null,
      2
    ),
  },
  {
    id: "recommend-auto",
    method: "POST",
    path: "/recommend/auto",
    name: "Recommandation (auto)",
    category: "Recommendations",
    description: "Mode auto avec overrides",
    sample: JSON.stringify(
      {
        user_id: "u-001",
        location: "Lyon",
        gender: "female",
        age: 29,
        top_size: "m",
        bottom_size: "m",
        shoe_size: "40",
        style_preferences: ["minimalist", "elegant"],
        agenda: ["work", "meeting"],
        top_k: 3,
      },
      null,
      2
    ),
  },
  {
    id: "vision-enroll",
    method: "POST",
    path: "/vision/enroll",
    name: "Vision - Enrôlement",
    category: "Vision",
    description: "Enrôler un visage utilisateur",
    sample: JSON.stringify(
      {
        user_id: "u-001",
        image_base64: "data:image/jpeg;base64,...",
      },
      null,
      2
    ),
  },
  {
    id: "vision-identify",
    method: "POST",
    path: "/vision/identify",
    name: "Vision - Identification",
    category: "Vision",
    description: "Identifier un visage utilisateur",
    sample: JSON.stringify(
      {
        image_base64: "data:image/jpeg;base64,...",
        threshold: 0.45,
        max_results: 1,
      },
      null,
      2
    ),
  },
  {
    id: "mirror-recommend",
    method: "POST",
    path: "/mirror/recommend-from-camera",
    name: "Miroir - Recommandation",
    category: "Vision",
    description: "Flux caméra avec recommandation",
    sample: JSON.stringify(
      {
        image_base64: "data:image/jpeg;base64,...",
        location: "Lyon",
        threshold: 0.45,
        top_k: 3,
      },
      null,
      2
    ),
  },
  {
    id: "feedback-event",
    method: "POST",
    path: "/feedback/event",
    name: "Feedback - Événement",
    category: "Feedback",
    description: "Envoyer un événement",
    sample: JSON.stringify(
      {
        user_id: "u-001",
        event_type: "impression",
        outfit_id: "outfit-001",
        score: 0.9,
        session_id: "session-001",
        metadata: { source: "api-console" },
      },
      null,
      2
    ),
  },
  {
    id: "feedback-batch",
    method: "POST",
    path: "/feedback/batch",
    name: "Feedback - Batch",
    category: "Feedback",
    description: "Envoyer des événements en batch",
    sample: JSON.stringify(
      {
        events: [
          {
            user_id: "u-001",
            event_type: "click",
            outfit_id: "outfit-001",
            score: 0.5,
            session_id: "session-001",
            metadata: { source: "api-console" },
          },
        ],
      },
      null,
      2
    ),
  },
  {
    id: "feedback-events",
    method: "POST",
    path: "/feedback/events",
    name: "Feedback - Events",
    category: "Feedback",
    description: "Alias du batch d'événements",
    sample: JSON.stringify(
      {
        events: [
          {
            user_id: "u-001",
            event_type: "dismissed",
            outfit_id: "outfit-002",
            score: 0.1,
            session_id: "session-001",
            metadata: { source: "api-console" },
          },
        ],
      },
      null,
      2
    ),
  },
  {
    id: "feedback-stats",
    method: "GET",
    path: "/feedback/stats",
    name: "Feedback - Statistiques",
    category: "Feedback",
    description: "Statistiques agrégées de feedback",
    sample: "",
  },
  {
    id: "wardrobe-create",
    method: "POST",
    path: "/wardrobe/items",
    name: "Garde-robe - Créer",
    category: "Wardrobe",
    description: "Ajouter un item à la garde-robe individuelle",
    sample: JSON.stringify(
      {
        user_id: "u-001",
        category: "top",
        subcategory: "chemise",
        color_primary: "bleu_marine",
        formality_level: 3,
        warmth_rating: 2,
        pattern: "uni",
        season_suitability: ["printemps", "automne"]
      },
      null,
      2
    ),
  },
  {
    id: "wardrobe-list",
    method: "GET",
    path: "/wardrobe/items",
    name: "Garde-robe - Lister",
    category: "Wardrobe",
    description: "Lister les items (ajouter ?user_id=...)",
    sample: "",
  },
  {
    id: "preferences-get",
    method: "GET",
    path: "/preferences/u-001",
    name: "Préférences - Récupérer",
    category: "Preferences",
    description: "Récupérer le profil de préférences complet",
    sample: "",
  },
  {
    id: "preferences-onboarding",
    method: "PUT",
    path: "/preferences/u-001",
    name: "Préférences - Onboarding",
    category: "Preferences",
    description: "Soumettre le questionnaire initial",
    sample: JSON.stringify(
      {
        styles_aimes: ["minimalist", "elegant"],
        styles_evites: ["sport"],
        couleurs_aimees: ["bleu_marine", "noir"],
        couleurs_evitees: ["orange"],
        niveau_formalite_prefere: 3,
        tolerance_meteo: "neutre"
      },
      null,
      2
    ),
  },
  {
    id: "preferences-micro-survey",
    method: "POST",
    path: "/preferences/u-001/micro-survey",
    name: "Préférences - Micro-survey",
    category: "Preferences",
    description: "Répondre à un micro-questionnaire ponctuel",
    sample: JSON.stringify(
      {
        kind: "ban_item",
        item_id: "itm_8f3a1c",
        accepted: true
      },
      null,
      2
    ),
  },
];

const el = (id) => document.getElementById(id);

const endpointList = el("endpointList");
const searchInput = el("searchInput");
const baseUrlInput = el("baseUrl");
const activeEndpoint = el("activeEndpoint");
const methodSelect = el("methodSelect");
const pathInput = el("pathInput");
const headersInput = el("headersInput");
const bodyInput = el("bodyInput");
const bodyField = el("bodyField");
const sendBtn = el("sendBtn");
const sendBtnTop = el("sendBtnTop");
const formatBtn = el("formatBtn");
const formatBtnTop = el("formatBtnTop");
const resetBtn = el("resetBtn");
const methodPill = el("methodPill");
const timePill = el("timePill");
const httpStatus = el("httpStatus");
const sizeStat = el("sizeStat");
const typeStat = el("typeStat");
const responseOutput = el("responseOutput");
const headersOutput = el("headersOutput");
const historyList = el("historyList");
const lastStatus = el("lastStatus");
const clearHistory = el("clearHistory");

const latencyClasses = ["latency-excellent", "latency-good", "latency-medium", "latency-bad"];
const statusClasses = ["status-ok", "status-warn", "status-err"];

const state = {
  selectedId: "health",
  history: [],
};

const defaultHeaders = () => ({
  "Content-Type": "application/json",
});

function formatJsonString(value) {
  if (!value.trim()) return "";
  const parsed = JSON.parse(value);
  return JSON.stringify(parsed, null, 2);
}

function renderEndpoints(list) {
  endpointList.innerHTML = "";
  list.forEach((item) => {
    const card = document.createElement("div");
    card.className = "endpoint" + (item.id === state.selectedId ? " active" : "");
    const row = document.createElement("div");
    row.className = "row";

    const method = document.createElement("span");
    method.className = "method";
    method.textContent = item.method;

    const path = document.createElement("span");
    path.className = "path";
    path.textContent = item.path;

    row.append(method, path);

    const desc = document.createElement("div");
    desc.className = "desc";
    desc.textContent = `${item.name} - ${item.description}`;

    card.append(row, desc);
    card.addEventListener("click", () => selectEndpoint(item.id));
    endpointList.appendChild(card);
  });
}

function selectEndpoint(id) {
  const endpoint = endpoints.find((item) => item.id === id);
  if (!endpoint) return;
  state.selectedId = id;
  methodSelect.value = endpoint.method;
  pathInput.value = endpoint.path;
  methodPill.textContent = endpoint.method;
  activeEndpoint.textContent = endpoint.path;
  bodyInput.value = endpoint.sample || "";
  updateBodyVisibility(endpoint.method);
  renderEndpoints(filterEndpoints(searchInput.value));
}

function updateBodyVisibility(method) {
  const upper = method.toUpperCase();
  bodyField.style.display = upper === "GET" ? "none" : "grid";
}

function filterEndpoints(query) {
  const term = query.trim().toLowerCase();
  if (!term) return endpoints;
  return endpoints.filter((item) =>
    item.path.toLowerCase().includes(term) ||
    item.name.toLowerCase().includes(term) ||
    item.category.toLowerCase().includes(term)
  );
}

function setStatus(text, type) {
  lastStatus.textContent = text;
  lastStatus.style.color = type === "err" ? "#ff7a6e" : "#3ee29a";
}

function setLatency(duration) {
  timePill.classList.remove(...latencyClasses);
  if (typeof duration !== "number") {
    return;
  }
  if (duration <= 120) {
    timePill.classList.add("latency-excellent");
  } else if (duration <= 300) {
    timePill.classList.add("latency-good");
  } else if (duration <= 800) {
    timePill.classList.add("latency-medium");
  } else {
    timePill.classList.add("latency-bad");
  }
}

function setHttpStatusColor(statusCode) {
  httpStatus.classList.remove(...statusClasses);
  if (typeof statusCode !== "number") {
    return;
  }
  if (statusCode >= 200 && statusCode < 300) {
    httpStatus.classList.add("status-ok");
  } else if (statusCode >= 300 && statusCode < 400) {
    httpStatus.classList.add("status-warn");
  } else {
    httpStatus.classList.add("status-err");
  }
}

function addHistory(entry) {
  state.history.unshift(entry);
  state.history = state.history.slice(0, 12);
  historyList.innerHTML = "";
  state.history.forEach((item) => {
    const row = document.createElement("div");
    row.className = "history-item";
    const summary = document.createElement("div");
    summary.textContent = `${item.method} ${item.path}`;

    const status = document.createElement("div");
    status.className = `status ${item.ok ? "ok" : "err"}`;
    status.textContent = String(item.status);

    const duration = document.createElement("div");
    duration.textContent = `${item.duration} ms`;

    row.append(summary, status, duration);
    historyList.appendChild(row);
  });
}

async function sendRequest() {
  const baseUrl = baseUrlInput.value.trim() || window.location.origin;
  const method = methodSelect.value.toUpperCase();
  const path = pathInput.value.trim() || "/health";
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = baseUrl.replace(/\/$/, "") + normalizedPath;

  let headers = {};
  try {
    headers = headersInput.value.trim() ? JSON.parse(headersInput.value) : defaultHeaders();
  } catch (err) {
    responseOutput.textContent = "Invalid headers JSON";
    setStatus("Headers JSON error", "err");
    return;
  }

  const options = { method, headers };

  if (method !== "GET") {
    try {
      options.body = bodyInput.value.trim() ? JSON.stringify(JSON.parse(bodyInput.value)) : "{}";
    } catch (err) {
      responseOutput.textContent = "Invalid body JSON";
      setStatus("Body JSON error", "err");
      return;
    }
  }

  const start = performance.now();
  try {
    setStatus("Sending...", "ok");
    const response = await fetch(url, options);
    const duration = Math.round(performance.now() - start);
    const contentType = response.headers.get("content-type") || "-";
    const rawText = await response.text();
    const isJson = contentType.includes("application/json");
    let pretty = rawText;
    if (isJson && rawText) {
      try {
        pretty = JSON.stringify(JSON.parse(rawText), null, 2);
      } catch (err) {
        pretty = rawText;
      }
    }

    responseOutput.textContent = pretty || "-";
    headersOutput.textContent = Array.from(response.headers.entries())
      .map(([key, value]) => `${key}: ${value}`)
      .join("\n") || "-";

    httpStatus.textContent = `${response.status} ${response.statusText}`;
    setHttpStatusColor(response.status);
    sizeStat.textContent = `${rawText.length} bytes`;
    typeStat.textContent = contentType;
    timePill.textContent = `${duration} ms`;
    setLatency(duration);

    setStatus(response.ok ? "Success" : "Error", response.ok ? "ok" : "err");
    addHistory({ method, path, status: response.status, ok: response.ok, duration });
  } catch (err) {
    responseOutput.textContent = String(err);
    headersOutput.textContent = "-";
    httpStatus.textContent = "-";
    setHttpStatusColor(null);
    sizeStat.textContent = "-";
    typeStat.textContent = "-";
    timePill.textContent = "-";
    setLatency(null);
    setStatus("Network error", "err");
    addHistory({ method, path, status: "ERR", ok: false, duration: 0 });
  }
}

function formatBody() {
  try {
    bodyInput.value = formatJsonString(bodyInput.value);
  } catch (err) {
    responseOutput.textContent = "Invalid body JSON";
  }
}

function formatHeaders() {
  try {
    headersInput.value = formatJsonString(headersInput.value);
  } catch (err) {
    responseOutput.textContent = "Invalid headers JSON";
  }
}

function resetForm() {
  const endpoint = endpoints.find((item) => item.id === state.selectedId);
  if (!endpoint) return;
  methodSelect.value = endpoint.method;
  pathInput.value = endpoint.path;
  bodyInput.value = endpoint.sample || "";
  headersInput.value = JSON.stringify(defaultHeaders(), null, 2);
  updateBodyVisibility(endpoint.method);
  responseOutput.textContent = "-";
  headersOutput.textContent = "-";
  httpStatus.textContent = "-";
  setHttpStatusColor(null);
  sizeStat.textContent = "-";
  typeStat.textContent = "-";
  timePill.textContent = "0 ms";
  setLatency(null);
  setStatus("Idle", "ok");
}

searchInput.addEventListener("input", (event) => {
  renderEndpoints(filterEndpoints(event.target.value));
});

methodSelect.addEventListener("change", (event) => {
  updateBodyVisibility(event.target.value);
  methodPill.textContent = event.target.value;
});

sendBtn.addEventListener("click", sendRequest);
sendBtnTop.addEventListener("click", sendRequest);
formatBtn.addEventListener("click", () => { formatBody(); formatHeaders(); });
formatBtnTop.addEventListener("click", () => { formatBody(); formatHeaders(); });
resetBtn.addEventListener("click", resetForm);
clearHistory.addEventListener("click", () => {
  state.history = [];
  historyList.innerHTML = "";
});

baseUrlInput.value = window.location.origin;
headersInput.value = JSON.stringify(defaultHeaders(), null, 2);

renderEndpoints(endpoints);
selectEndpoint(state.selectedId);
