// -------------------------------------------------------------
// Cicada frontend - no framework, just fetch + DOM + a canvas.
// -------------------------------------------------------------

const state = {
  tests: [],
  selectedTestId: null,
  activeRun: null,
  socket: null,
  pulsePoints: [],
};

// ---------------- API helpers ----------------

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

const getTests = () => api("/api/tests");
const createTest = (payload) => api("/api/tests", { method: "POST", body: JSON.stringify(payload) });
const deleteTest = (id) => api(`/api/tests/${id}`, { method: "DELETE" });
const getRuns = (testId) => api(`/api/runs?test_id=${testId}`);
const getRun = (id) => api(`/api/runs/${id}`);
const triggerRun = (testId) => api(`/api/tests/${testId}/run`, { method: "POST" });

// ---------------- Rendering: sidebar ----------------

function renderTestList() {
  const list = document.getElementById("test-list");
  if (state.tests.length === 0) {
    list.innerHTML = `<div class="empty-hint">No tests yet - create one to get started.</div>`;
    return;
  }
  list.innerHTML = state.tests
    .map(
      (t) => `
      <div class="test-item ${t.id === state.selectedTestId ? "active" : ""}" data-id="${t.id}">
        <div class="test-item-name">${escapeHtml(t.name)}</div>
        <div class="test-item-meta">${t.method} · ${t.vus} vus</div>
      </div>`
    )
    .join("");

  list.querySelectorAll(".test-item").forEach((el) => {
    el.addEventListener("click", () => selectTest(el.dataset.id));
  });
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s ?? "";
  return div.innerHTML;
}

// ---------------- Rendering: main panel ----------------

async function selectTest(id) {
  state.selectedTestId = id;
  renderTestList();
  const test = state.tests.find((t) => t.id === id);
  if (!test) return;

  const runs = await getRuns(id).catch(() => []);
  renderTestDetail(test, runs);
}

function renderTestDetail(test, runs) {
  const main = document.getElementById("main");
  const stageSummary = test.stages.length
    ? test.stages.map((s) => `${s.target}@${s.duration}`).join(" → ")
    : `flat ${test.vus} vus / 30s`;
  const thresholdSummary = test.thresholds.length
    ? test.thresholds.map((t) => `${t.metric} ${t.expression}`).join(", ")
    : "none";

  main.innerHTML = `
    <div class="panel-header">
      <div>
        <h1 class="panel-title">${escapeHtml(test.name)}</h1>
        <div class="panel-subtitle">${test.method} ${escapeHtml(test.target_url)}</div>
      </div>
      <div class="panel-button">
        <button class="btn" id="copy-curl-btn">Copy as cURL</button>
        <button class="btn btn-primary" id="run-btn">Run test</button>
      </div>
    </div>

    <div class="spec-grid">
      <div class="spec-item">
        <div class="spec-label">Load profile</div>
        <div class="spec-value">${escapeHtml(stageSummary)}</div>
      </div>
      <div class="spec-item">
        <div class="spec-label">Thresholds</div>
        <div class="spec-value">${escapeHtml(thresholdSummary)}</div>
      </div>
      <div class="spec-item">
        <div class="spec-label">Headers</div>
        <div class="spec-value">${Object.keys(test.headers || {}).length}</div>
      </div>
      <div class="spec-item">
        <div class="spec-label">Runs</div>
        <div class="spec-value">${runs.length}</div>
      </div>
    </div>

    <div class="section-label">Run history</div>
    <div class="runs-list" id="runs-list">
      ${
        runs.length
          ? runs.map(runRowHtml).join("")
          : `<div class="empty-hint" style="padding:14px">No runs yet.</div>`
      }
    </div>

    <div id="run-view"></div>
  `;

  document.getElementById("run-btn").addEventListener("click", () => startRun(test.id));
  document.getElementById("copy-curl-btn").addEventListener("click", () => copyCurlToClipboard(test, "copy-curl-btn"));
  main.querySelectorAll(".run-row").forEach((el) => {
    el.addEventListener("click", () => openRun(el.dataset.id));
  });
}

// ---------------- Copy Test as cURL to Clipboard----------------

function copyCurlToClipboard(test, btnId) {
  const curl = generateCurl(test);
  copyToClipboard(curl);
  
  const btn = document.getElementById(btnId);
  if (btn) {
    const originalText = btn.textContent;
    btn.textContent = "Copied!";
    
    setTimeout(() => {
      btn.textContent = originalText;
    }, 2000);
  }
}

function generateCurl(test) {
  const method = (test.method || "GET").toUpperCase();
  const parts = [`curl -X ${method} '${test.target_url}'`];

  // Process and append headers
  if (test.headers && Object.keys(test.headers).length > 0) {
    for (const [key, value] of Object.entries(test.headers)) {
      if (key.trim()) {
        const escapedValue = String(value).replace(/'/g, "'\\''");
        parts.push(`  -H '${key}: ${escapedValue}'`);
      }
    }
  }

  // Process and append body (omit for GET method, or if empty)
  if (method !== "GET" && test.body) {
    let bodyStr = typeof test.body === "object" ? JSON.stringify(test.body) : test.body;
    if (bodyStr.trim()) {
      // Escape inner backslashes first, then escape single quotes
      const escapedBody = bodyStr.replace(/\\/g, '\\\\').replace(/'/g, "'\\''");
      parts.push(`  -d '${escapedBody}'`);
    }
  }

  return parts.join(" \\\n");
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text)
    .catch((err) => {
      console.error("Failed to copy cURL command string to clipboard: ", err);
    });
}

function runRowHtml(run) {
  return `
    <div class="run-row" data-id="${run.id}">
      <span class="badge badge-${run.status}">${run.status}</span>
      <span class="run-time">${formatTime(run.created_at)}</span>
      <span>${run.summary ? summaryOneLiner(run.summary) : "-"}</span>
      <span class="run-time">${run.id.slice(0, 8)}</span>
    </div>`;
}

function summaryOneLiner(summary) {
  try {
    const reqs = summary?.metrics?.http_reqs?.count ?? "?";
    const avg = summary?.metrics?.http_req_duration?.avg;
    return `${reqs} req${avg ? `, avg ${avg.toFixed(0)}ms` : ""}`;
  } catch {
    return "-";
  }
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

// ---------------- Run view ----------------

async function startRun(testId) {
  const run = await triggerRun(testId);
  openRun(run.id);
}

async function openRun(runId) {
  const run = await getRun(runId);
  state.activeRun = run;
  state.pulsePoints = run.timeline || [];
  renderRunView(run);
  connectSocket(runId);
}

function renderRunView(run) {
  const view = document.getElementById("run-view");
  view.innerHTML = `
    <div class="section-label" style="margin-top:32px">Live run</div>
    <div class="run-view-header">
      <div class="run-view-title">Run ${run.id.slice(0, 8)}</div>
      <span class="badge badge-${run.status}" id="run-status-badge">${run.status}</span>
    </div>

    <div class="pulse-wrap">
      <canvas id="pulse-canvas" width="900" height="120"></canvas>
    </div>

    <div class="stat-grid">
      <div class="stat-cell"><div class="stat-label">VUs</div><div class="stat-value" id="stat-vus">0</div></div>
      <div class="stat-cell"><div class="stat-label">Req/s</div><div class="stat-value" id="stat-rps">0</div></div>
      <div class="stat-cell"><div class="stat-label">Avg latency</div><div class="stat-value" id="stat-avg">0ms</div></div>
      <div class="stat-cell"><div class="stat-label">p95 latency</div><div class="stat-value" id="stat-p95">0ms</div></div>
      <div class="stat-cell stat-error"><div class="stat-label">Error rate</div><div class="stat-value" id="stat-err">0%</div></div>
    </div>

    <div id="summary-container"></div>
  `;

  drawPulse();
  if (run.summary) renderSummary(run.summary, run.error);
}

function connectSocket(runId) {
  if (state.socket) {
    state.socket.close();
    state.socket = null;
  }
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${proto}//${location.host}/ws/runs/${runId}`);
  state.socket = socket;

  socket.addEventListener("message", (evt) => {
    const msg = JSON.parse(evt.data);
    if (msg.type === "point") {
      handlePoint(msg.point);
    } else if (msg.type === "done") {
      handleDone(msg);
    }
  });
}

function handlePoint(point) {
  state.pulsePoints.push(point);
  if (state.pulsePoints.length > 120) state.pulsePoints.shift();

  setText("stat-vus", point.vus);
  setText("stat-rps", point.rps);
  setText("stat-avg", `${point.avg_ms}ms`);
  setText("stat-p95", `${point.p95_ms}ms`);
  setText("stat-err", `${(point.error_rate * 100).toFixed(1)}%`);

  drawPulse();
}

function handleDone(msg) {
  const badge = document.getElementById("run-status-badge");
  if (badge) {
    badge.textContent = msg.status;
    badge.className = `badge badge-${msg.status}`;
  }
  if (msg.summary) renderSummary(msg.summary, msg.error);
  else if (msg.error) renderSummary(null, msg.error);

  if (state.selectedTestId) {
    getRuns(state.selectedTestId).then((runs) => {
      const list = document.getElementById("runs-list");
      if (list) {
        list.innerHTML = runs.length
          ? runs.map(runRowHtml).join("")
          : `<div class="empty-hint" style="padding:14px">No runs yet.</div>`;
        list.querySelectorAll(".run-row").forEach((el) => {
          el.addEventListener("click", () => openRun(el.dataset.id));
        });
      }
    });
  }
}

function renderSummary(summary, error) {
  const container = document.getElementById("summary-container");
  if (!container) return;
  if (error) {
    container.innerHTML = `
      <div class="section-label">Error</div>
      <div class="summary-box"><pre>${escapeHtml(error)}</pre></div>`;
    return;
  }
  if (!summary) return;
  container.innerHTML = `
    <div class="section-label">Summary</div>
    <div class="summary-box"><pre>${escapeHtml(JSON.stringify(summary.metrics ?? summary, null, 2))}</pre></div>`;
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ---------------- The signature element: the pulse chart ----------------
// A waveform strip literally driven by live RPS, evoking a cicada's
// pulsing call. Amplitude = requests/sec, baseline = the run's timeline.

function drawPulse() {
  const canvas = document.getElementById("pulse-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const w = rect.width || 900;
  const h = 120;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  const points = state.pulsePoints.slice(-90);
  if (points.length === 0) {
    ctx.strokeStyle = "#cccccc";
    ctx.beginPath();
    ctx.moveTo(0, h / 2);
    ctx.lineTo(w, h / 2);
    ctx.stroke();
    return;
  }

  const maxRps = Math.max(1, ...points.map((p) => p.rps));
  const stepX = w / Math.max(1, points.length - 1 || 1);
  const mid = h / 2;

  ctx.strokeStyle = "#1a5fb4";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  points.forEach((p, i) => {
    const amp = (p.rps / maxRps) * (h / 2 - 8);
    const x = i * stepX;
    const yTop = mid - amp;
    if (i === 0) ctx.moveTo(x, yTop);
    else ctx.lineTo(x, yTop);
  });
  ctx.stroke();

  ctx.strokeStyle = "rgba(26,95,180,0.3)";
  ctx.beginPath();
  points.forEach((p, i) => {
    const amp = (p.rps / maxRps) * (h / 2 - 8);
    const x = i * stepX;
    const yBottom = mid + amp;
    if (i === 0) ctx.moveTo(x, yBottom);
    else ctx.lineTo(x, yBottom);
  });
  ctx.stroke();

  ctx.strokeStyle = "#cccccc";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, mid);
  ctx.lineTo(w, mid);
  ctx.stroke();
}

window.addEventListener("resize", drawPulse);

// ---------------- Modal: new test form ----------------

const modalOverlay = document.getElementById("modal-overlay");
const testForm = document.getElementById("test-form");

document.getElementById("btn-new-test").addEventListener("click", openModal);
document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("modal-cancel").addEventListener("click", closeModal);
modalOverlay.addEventListener("click", (e) => {
  if (e.target === modalOverlay) closeModal();
});

function openModal() {
  testForm.reset();
  document.getElementById("headers-rows").innerHTML = "";
  document.getElementById("stages-rows").innerHTML = "";
  document.getElementById("thresholds-rows").innerHTML = "";
  document.getElementById("body-field").style.display = "none";
  modalOverlay.classList.add("open");
}

function closeModal() {
  modalOverlay.classList.remove("open");
}

testForm.elements["method"].addEventListener("change", (e) => {
  const showBody = !["GET", "HEAD"].includes(e.target.value);
  document.getElementById("body-field").style.display = showBody ? "block" : "none";
});

document.querySelectorAll("[data-add]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const kind = btn.dataset.add;
    if (kind === "header") addHeaderRow();
    if (kind === "stage") addStageRow();
    if (kind === "threshold") addThresholdRow();
  });
});

function addHeaderRow() {
  const row = document.createElement("div");
  row.className = "kv-row";
  row.innerHTML = `
    <input type="text" placeholder="Header name (e.g. Authorization)" class="h-key" />
    <input type="text" placeholder="Value" class="h-val" />
    <button type="button" class="remove-row">&times;</button>`;
  row.querySelector(".remove-row").addEventListener("click", () => row.remove());
  document.getElementById("headers-rows").appendChild(row);
}

function addStageRow() {
  const row = document.createElement("div");
  row.className = "kv-row";
  row.innerHTML = `
    <input type="text" placeholder="Duration (e.g. 30s, 2m)" class="s-duration" />
    <input type="number" placeholder="Target VUs" class="s-target" min="0" />
    <button type="button" class="remove-row">&times;</button>`;
  row.querySelector(".remove-row").addEventListener("click", () => row.remove());
  document.getElementById("stages-rows").appendChild(row);
}

function addThresholdRow() {
  const row = document.createElement("div");
  row.className = "kv-row";
  row.innerHTML = `
    <select class="t-metric">
      <option value="http_req_duration">http_req_duration</option>
      <option value="http_req_failed">http_req_failed</option>
    </select>
    <input type="text" placeholder="Expression (e.g. p(95)<500)" class="t-expr" />
    <button type="button" class="remove-row">&times;</button>`;
  row.querySelector(".remove-row").addEventListener("click", () => row.remove());
  document.getElementById("thresholds-rows").appendChild(row);
}

testForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(testForm);

  const headers = {};
  document.querySelectorAll("#headers-rows .kv-row").forEach((row) => {
    const k = row.querySelector(".h-key").value.trim();
    const v = row.querySelector(".h-val").value.trim();
    if (k) headers[k] = v;
  });

  const stages = [];
  document.querySelectorAll("#stages-rows .kv-row").forEach((row) => {
    const duration = row.querySelector(".s-duration").value.trim();
    const target = parseInt(row.querySelector(".s-target").value, 10);
    if (duration && !Number.isNaN(target)) stages.push({ duration, target });
  });

  const thresholds = [];
  document.querySelectorAll("#thresholds-rows .kv-row").forEach((row) => {
    const metric = row.querySelector(".t-metric").value;
    const expression = row.querySelector(".t-expr").value.trim();
    if (expression) thresholds.push({ metric, expression });
  });

  const payload = {
    name: fd.get("name"),
    target_url: fd.get("target_url"),
    method: fd.get("method"),
    headers,
    body: fd.get("body") || null,
    vus: parseInt(fd.get("vus"), 10) || 10,
    stages,
    thresholds,
  };

  try {
    const test = await createTest(payload);
    closeModal();
    await refreshTests();
    selectTest(test.id);
  } catch (err) {
    alert(`Could not create test: ${err.message}`);
  }
});

// ---------------- Boot ----------------

async function refreshTests() {
  state.tests = await getTests();
  renderTestList();
}

refreshTests().catch((err) => {
  document.getElementById("test-list").innerHTML = `<div class="empty-hint">Could not reach the API: ${escapeHtml(err.message)}</div>`;
});