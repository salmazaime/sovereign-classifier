// app/static/js/app.js

let state = { token: null, companyId: null, roles: [] };
const VIEWS = ["overview", "decisions", "reviews", "reports", "team"];
const VIEW_ICONS = {
  overview: "fa-solid fa-gauge-high", decisions: "fa-solid fa-scale-balanced",
  reviews: "fa-solid fa-clipboard-check", reports: "fa-solid fa-file-shield",
  team: "fa-solid fa-users",
};
const VIEW_TITLES = {
  overview: "Overview", decisions: "Decisions", reviews: "Pending Reviews",
  reports: "Audit Reports", team: "Team",
};

let charts = { decisionsChart: null, outcomeDonut: null };
let worldMapInstance = null;

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function saveSession() { sessionStorage.setItem("sovereignty_session", JSON.stringify(state)); }
function loadSession() {
  const raw = sessionStorage.getItem("sovereignty_session");
  if (raw) state = JSON.parse(raw);
  return state.token !== null;
}
function clearSession() { sessionStorage.removeItem("sovereignty_session"); state = { token: null, companyId: null, roles: [] }; }

async function apiFetch(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) { clearSession(); window.location.href = "/dashboard/"; throw new Error("Session expired."); }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail?.message || (typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)) || `Failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

function showAuthTab(tab) {
  document.getElementById("login-form").style.display = tab === "login" ? "block" : "none";
  document.getElementById("register-form").style.display = tab === "register" ? "block" : "none";
  document.getElementById("tab-login").classList.toggle("active", tab === "login");
  document.getElementById("tab-register").classList.toggle("active", tab === "register");
}

async function login() {
  const errorEl = document.getElementById("auth-error"); errorEl.textContent = "";
  try {
    const data = await apiFetch("/auth/login", { method: "POST", body: JSON.stringify({
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-password").value,
    })});
    onAuthSuccess(data);
  } catch (err) { errorEl.textContent = err.message; }
}

async function register() {
  const errorEl = document.getElementById("auth-error"); errorEl.textContent = "";
  try {
    const data = await apiFetch("/auth/register", { method: "POST", body: JSON.stringify({
      company_name: document.getElementById("reg-company-name").value,
      company_sector: document.getElementById("reg-company-sector").value,
      admin_name: document.getElementById("reg-admin-name").value,
      admin_email: document.getElementById("reg-admin-email").value,
      admin_password: document.getElementById("reg-admin-password").value,
    })});
    onAuthSuccess(data);
  } catch (err) { errorEl.textContent = err.message; }
}

function onAuthSuccess(data) {
  const payload = JSON.parse(atob(data.access_token.split(".")[1]));
  state = { token: data.access_token, companyId: payload.company_id, roles: data.roles || [] };
  saveSession();
  renderAuthState();
}

function logout() { clearSession(); window.location.href = "/dashboard/"; }

function renderAuthState() {
  const loggedIn = state.token !== null;
  const authView = document.getElementById("auth-view");
  if (authView) authView.style.display = loggedIn ? "none" : "block";
  document.getElementById("sidebar").style.display = loggedIn ? "flex" : "none";
  document.getElementById("topbar").style.display = loggedIn ? "flex" : "none";
  if (!loggedIn) { VIEWS.forEach(v => document.getElementById(v + "-view")?.classList.remove("active")); return; }

  document.getElementById("roles-pill").textContent = state.roles.join(", ");
  document.getElementById("user-info").innerHTML = `
    <button class="btn btn-outline" style="width:100%; justify-content:center;" onclick="logout()">
      <i class="fa-solid fa-right-from-bracket"></i> Sign out
    </button>
  `;

  const currentPath = window.location.pathname;
  const onDashboard = currentPath === "/dashboard/";

  document.getElementById("main-nav").innerHTML = VIEWS.map(v => {
    const icon = `<i class="${VIEW_ICONS[v]}"></i>`;
    if (onDashboard) {
      return `<a href="#${v}" onclick="switchView('${v}'); return false;" id="nav-${v}">${icon} ${VIEW_TITLES[v]}</a>`;
    }
    return `<a href="/dashboard/#${v}" id="nav-${v}">${icon} ${VIEW_TITLES[v]}</a>`;
  }).join("") + `<a href="/dashboard/settings" class="${currentPath.includes('settings') ? 'active' : ''}"><i class="fa-solid fa-gear"></i> Settings</a>`;

  if (document.getElementById("overview-view")) {
    const hashView = window.location.hash.replace("#", "");
    switchView(VIEWS.includes(hashView) ? hashView : "overview");
  }
}

function switchView(view) {
  VIEWS.forEach(v => {
    document.getElementById(v + "-view")?.classList.toggle("active", v === view);
    document.getElementById("nav-" + v)?.classList.toggle("active", v === view);
  });
  document.getElementById("page-title").textContent = VIEW_TITLES[view] || "Dashboard";

  if (view === "overview") loadOverview();
  if (view === "decisions") loadDecisions();
  if (view === "reviews") loadReviews();
  if (view === "team") loadTeam();
  if (view === "reports") initReportDatePickers();
}

async function loadOverview() {
  const statsEl = document.getElementById("overview-stats");
  try {
    const [decisions, reviews, geo] = await Promise.all([
      apiFetch(`/companies/${state.companyId}/decisions`),
      apiFetch(`/companies/${state.companyId}/reviews`),
      apiFetch(`/companies/${state.companyId}/geo-distribution`).catch(() => []),
    ]);
    const allowed = decisions.filter(d => d.decision === "ALLOW").length;
    const denied = decisions.filter(d => d.decision === "DENY").length;

    statsEl.innerHTML = `
      <div class="stat-card"><div class="stat-icon blue"><i class="fa-solid fa-scale-balanced"></i></div>
        <div><div class="stat-num">${decisions.length}</div><div class="stat-label">Total Decisions</div></div></div>
      <div class="stat-card"><div class="stat-icon green"><i class="fa-solid fa-circle-check"></i></div>
        <div><div class="stat-num">${allowed}</div><div class="stat-label">Allowed</div></div></div>
      <div class="stat-card"><div class="stat-icon red"><i class="fa-solid fa-circle-xmark"></i></div>
        <div><div class="stat-num">${denied}</div><div class="stat-label">Denied</div></div></div>
      <div class="stat-card"><div class="stat-icon yellow"><i class="fa-solid fa-clock"></i></div>
        <div><div class="stat-num">${reviews.length}</div><div class="stat-label">Pending Reviews</div></div></div>
    `;

    renderDecisionsChart(decisions);
    renderOutcomeDonut(allowed, denied, decisions.length - allowed - denied);
    renderWorldMap(geo);
    renderGeoLegend(geo);
  } catch (err) { statsEl.innerHTML = `<span class="error">${escapeHtml(err.message)}</span>`; }
}

function renderDecisionsChart(decisions) {
  const ctx = document.getElementById("decisions-chart");
  if (!ctx) return;
  const byDay = {};
  decisions.forEach(d => {
    const day = new Date(d.decided_at).toLocaleDateString();
    byDay[day] = (byDay[day] || 0) + 1;
  });
  const labels = Object.keys(byDay);
  const values = Object.values(byDay);

  if (charts.decisionsChart) charts.decisionsChart.destroy();
  charts.decisionsChart = new Chart(ctx, {
    type: "bar",
    data: { labels, datasets: [{ data: values, backgroundColor: "#4f6df5", borderRadius: 6, maxBarThickness: 28 }] },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#6b7280", font: { size: 11 } } },
        y: { grid: { color: "#e1e5f0" }, ticks: { color: "#6b7280", font: { size: 11 }, precision: 0 } },
      },
      maintainAspectRatio: false,
    },
  });
}

function renderOutcomeDonut(allowed, denied, review) {
  const ctx = document.getElementById("outcome-donut");
  if (!ctx) return;
  if (charts.outcomeDonut) charts.outcomeDonut.destroy();
  charts.outcomeDonut = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Allowed", "Denied", "Review"],
      datasets: [{ data: [allowed, denied, review], backgroundColor: ["#16a37a", "#e0374a", "#d9971a"], borderWidth: 0 }],
    },
    options: {
      plugins: { legend: { position: "bottom", labels: { color: "#6b7280", font: { size: 11 }, padding: 14 } } },
      cutout: "70%", maintainAspectRatio: false,
    },
  });
}

// Country name -> ISO alpha-2 code, only for the countries this
// project's config/region_country_map.json can actually produce --
// jsvectormap needs ISO codes, not display names, to highlight regions.
const COUNTRY_ISO = {
  "France": "FR", "Germany": "DE", "Spain": "ES", "Portugal": "PT",
  "United States": "US", "Ireland": "IE", "Netherlands": "NL", "Morocco": "MA",
};

function renderWorldMap(geo) {
  const el = document.getElementById("world-map");
  if (!el || typeof jsVectorMap === "undefined") return;

  const countryTotals = {};
  geo.forEach(g => {
    const iso = COUNTRY_ISO[g.country];
    if (iso) countryTotals[iso] = (countryTotals[iso] || 0) + g.count;
  });

  el.innerHTML = "";
  worldMapInstance = new jsVectorMap({
    selector: "#world-map",
    map: "world",
    backgroundColor: "transparent",
    zoomButtons: false,
    regionStyle: {
      initial: { fill: "#dde3f0", stroke: "#c7cfe3", strokeWidth: 0.5 },
      hover: { fill: "#8aa0f8" },
      selected: { fill: "#4f6df5" },
    },
    selectedRegions: Object.keys(countryTotals),
    onRegionTooltipShow(event, tooltip, code) {
      const count = countryTotals[code] || 0;
      if (count > 0) {
        tooltip.text(`${tooltip.text()}: ${count} transfer${count === 1 ? "" : "s"}`, true);
      }
    },
  });
}

function renderGeoLegend(geo) {
  const el = document.getElementById("geo-legend");
  if (!el) return;
  if (geo.length === 0) { el.innerHTML = `<span class="muted">No transfer destinations recorded yet.</span>`; return; }
  const byCountryCloud = {};
  geo.forEach(g => {
    const key = `${g.country} / ${g.cloud || 'unknown'}`;
    byCountryCloud[key] = (byCountryCloud[key] || 0) + g.count;
  });
  el.innerHTML = Object.entries(byCountryCloud).map(([key, count]) => `
    <span class="badge ALLOW" style="margin-right:8px; margin-bottom:6px; display:inline-block;">
      <i class="fa-solid fa-cloud"></i> ${escapeHtml(key)} -- ${count}
    </span>
  `).join("");
}

async function loadDecisions() {
  const el = document.getElementById("decisions-list");
  const filter = document.getElementById("decision-filter")?.value;
  try {
    let decisions = await apiFetch(`/companies/${state.companyId}/decisions`);
    if (filter) decisions = decisions.filter(d => d.decision === filter);
    if (decisions.length === 0) { el.innerHTML = `<span class="muted">No decisions.</span>`; return; }
    el.innerHTML = decisions.map(d => `
      <div class="row" style="flex-direction: column; align-items: stretch;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div>${escapeHtml(d.entity_name)} <span class="muted">-> ${escapeHtml(d.destination_country || "n/a")}</span></div>
            <div class="muted">${new Date(d.decided_at).toLocaleString()} -- ${escapeHtml(d.model_name)}</div>
          </div>
          <div style="display: flex; align-items: center; gap: 10px;">
            <span class="badge ${d.decision}">${d.decision}</span>
            <button class="btn btn-outline" onclick="toggleDetails('${d.policy_decision_id}')"><i class="fa-solid fa-magnifying-glass"></i> Details</button>
          </div>
        </div>
        <div id="details-${d.policy_decision_id}" style="display:none; margin-top: 10px; padding: 14px; background: var(--panel-2); border-radius: 8px; font-size: 12px;"></div>
      </div>
    `).join("");
  } catch (err) { el.innerHTML = `<span class="error">${escapeHtml(err.message)}</span>`; }
}

async function toggleDetails(decisionId) {
  const panel = document.getElementById(`details-${decisionId}`);
  const isHidden = panel.style.display === "none";
  if (!isHidden) { panel.style.display = "none"; return; }
  panel.style.display = "block";
  panel.innerHTML = `<span class="muted">Loading...</span>`;
  try {
    const d = await apiFetch(`/policy-decisions/${decisionId}/infrastructure`);
    const infra = d.infrastructure || {};
    const net = infra.networking || {};
    const enc = infra.encryption || {};
    const findingsHtml = (d.content_findings || []).length
      ? d.content_findings.map(f => `<span class="badge REVIEW" style="margin-right:4px;">${escapeHtml(f.category)}</span>`).join("")
      : `<span class="muted">None detected</span>`;
    panel.innerHTML = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px 20px;">
        <div><span class="muted">Company:</span> ${escapeHtml(d.company_name)}</div>
        <div><span class="muted">Entity type:</span> ${escapeHtml(d.entity_type)}</div>
        <div><span class="muted">Cloud / Service:</span> ${escapeHtml(infra.vendor_attestation?.provider_name)} / ${escapeHtml(infra.resource_id?.split(':')[1]?.split('.')[0] || 'n/a')}</div>
        <div><span class="muted">Region:</span> ${escapeHtml(infra.region)}</div>
        <div><span class="muted">Account ID:</span> ${escapeHtml(infra.account_id)}</div>
        <div><span class="muted">Resource ID:</span> ${escapeHtml(infra.resource_id)}</div>
        <div><span class="muted">Publicly accessible:</span> ${net.is_publicly_accessible ? "Yes" : "No"}</div>
        <div><span class="muted">Encrypted at rest:</span> ${enc.at_rest_enabled ? "Yes (" + escapeHtml(enc.key_type) + ")" : "No"}</div>
        <div><span class="muted">Pushed by:</span> ${escapeHtml(d.pushed_by || "n/a")}</div>
        <div><span class="muted">Pushed via:</span> ${escapeHtml(d.pushed_via || "n/a")}</div>
        <div><span class="muted">Pushed at:</span> ${d.pushed_at ? new Date(d.pushed_at).toLocaleString() : "n/a"}</div>
        <div><span class="muted">Destination:</span> ${escapeHtml(d.destination_country)}</div>
      </div>
      <div style="margin-top: 10px;"><span class="muted">Detected sensitivity:</span> ${findingsHtml}</div>
    `;
  } catch (err) { panel.innerHTML = `<span class="error">${escapeHtml(err.message)}</span>`; }
}

// app/static/js/app.js -- replace loadReviews() entirely

async function loadReviews() {
  const el = document.getElementById("reviews-list");
  try {
    const reviews = await apiFetch(`/companies/${state.companyId}/reviews`);
    if (reviews.length === 0) { el.innerHTML = `<span class="muted">No pending reviews.</span>`; return; }
    const canReview = state.roles.includes("compliance_reviewer") || state.roles.includes("admin");
    el.innerHTML = reviews.map(r => `
      <div class="row" style="flex-direction: column; align-items: stretch;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div>${escapeHtml(r.entity_name)} <span class="muted">(${escapeHtml(r.entity_type)})</span></div>
            <div class="muted">${escapeHtml(r.reason)} -- expires ${new Date(r.expires_at).toLocaleString()}</div>
          </div>
          <div style="display: flex; align-items: center; gap: 10px;">
            <button class="btn btn-outline" onclick="toggleReviewDetails('${r.policy_decision_id}', '${r.entity_id}')">
              <i class="fa-solid fa-magnifying-glass"></i> Investigate
            </button>
            ${canReview ? `
              <button class="btn btn-approve" onclick="resolveReview('${r.authorization_request_id}', true)"><i class="fa-solid fa-check"></i> Approve</button>
              <button class="btn btn-reject" onclick="resolveReview('${r.authorization_request_id}', false)"><i class="fa-solid fa-xmark"></i> Reject</button>
            ` : `<span class="muted">Read-only</span>`}
          </div>
        </div>
        <div id="review-details-${r.policy_decision_id}" style="display:none; margin-top: 10px; padding: 14px; background: var(--panel-2); border-radius: 8px; font-size: 12px;"></div>
      </div>
    `).join("");
  } catch (err) { el.innerHTML = `<span class="error">${escapeHtml(err.message)}</span>`; }
}

async function toggleReviewDetails(policyDecisionId, entityId) {
  const panel = document.getElementById(`review-details-${policyDecisionId}`);
  const isHidden = panel.style.display === "none";
  if (!isHidden) { panel.style.display = "none"; return; }
  panel.style.display = "block";
  panel.innerHTML = `<span class="muted">Loading investigation details...</span>`;
  try {
    const [d, reasoning] = await Promise.all([
      apiFetch(`/policy-decisions/${policyDecisionId}/infrastructure`),
      apiFetch(`/policy-decisions/${policyDecisionId}/review-reasoning`),
    ]);

    const infra = d.infrastructure || {};
    const net = infra.networking || {};
    const enc = infra.encryption || {};
    const findingsHtml = (d.content_findings || []).length
      ? d.content_findings.map(f => `<span class="badge REVIEW" style="margin-right:4px;">${escapeHtml(f.category)} (${Math.round(f.confidence * 100)}%)</span>`).join("")
      : `<span class="muted">None detected</span>`;

    const factsHtml = (reasoning.known_facts || []).map(f =>
      `<li style="margin-bottom:6px;"><i class="fa-solid fa-circle-check" style="color:var(--allow); margin-right:6px;"></i>${escapeHtml(f)}</li>`
    ).join("");
    const questionsHtml = (reasoning.unresolved_questions || []).map(q =>
      `<li style="margin-bottom:8px;"><i class="fa-solid fa-circle-question" style="color:var(--review); margin-right:6px;"></i>${escapeHtml(q)}</li>`
    ).join("");

    panel.innerHTML = `
      <div style="background:var(--review-soft); border:1px solid var(--review); border-radius:8px; padding:14px; margin-bottom:14px;">
        <div style="font-weight:700; color:var(--review); margin-bottom:8px;">
          <i class="fa-solid fa-triangle-exclamation"></i> Why this needs human review
        </div>
        <div style="font-weight:600; font-size:11px; text-transform:uppercase; color:var(--muted); margin:10px 0 6px;">What the system determined</div>
        <ul style="margin:0; padding-left:4px; list-style:none;">${factsHtml}</ul>
        <div style="font-weight:600; font-size:11px; text-transform:uppercase; color:var(--muted); margin:12px 0 6px;">What it could not resolve automatically</div>
        <ul style="margin:0; padding-left:4px; list-style:none;">${questionsHtml}</ul>
      </div>

      <div style="font-weight:700; margin-bottom:10px; color:var(--text);">Infrastructure Detail</div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px 20px;">
        <div><span class="muted">Company:</span> ${escapeHtml(d.company_name)}</div>
        <div><span class="muted">Entity type:</span> ${escapeHtml(d.entity_type)}</div>
        <div><span class="muted">Cloud / Service:</span> ${escapeHtml(infra.vendor_attestation?.provider_name)} / ${escapeHtml(infra.resource_id?.split(':')[1]?.split('.')[0] || 'n/a')}</div>
        <div><span class="muted">Region:</span> ${escapeHtml(infra.region)}</div>
        <div><span class="muted">Account ID:</span> ${escapeHtml(infra.account_id)}</div>
        <div><span class="muted">Resource ID:</span> ${escapeHtml(infra.resource_id)}</div>
        <div><span class="muted">Publicly accessible:</span> ${net.is_publicly_accessible ? "Yes" : "No"}</div>
        <div><span class="muted">Encrypted at rest:</span> ${enc.at_rest_enabled ? "Yes (" + escapeHtml(enc.key_type) + ")" : "No"}</div>
        <div><span class="muted">Pushed by:</span> ${escapeHtml(d.pushed_by || "n/a")}</div>
        <div><span class="muted">Pushed via:</span> ${escapeHtml(d.pushed_via || "n/a")}</div>
        <div><span class="muted">Pushed at:</span> ${d.pushed_at ? new Date(d.pushed_at).toLocaleString() : "n/a"}</div>
        <div><span class="muted">Destination:</span> ${escapeHtml(d.destination_country)}</div>
      </div>
      <div style="margin-top: 10px;"><span class="muted">Detected sensitivity:</span> ${findingsHtml}</div>
    `;
  } catch (err) {
    panel.innerHTML = `<span class="error">${escapeHtml(err.message)}</span>`;
  }
}

async function resolveReview(id, approve) {
  try {
    await apiFetch(`/reviews/${id}/resolve`, { method: "POST", body: JSON.stringify({ approve }) });
    loadReviews(); loadOverview();
  } catch (err) { alert(err.message); }
}

function initReportDatePickers() {
  if (typeof flatpickr === "undefined") return;
  flatpickr("#report-start", { dateFormat: "Y-m-d", altInput: true, altFormat: "M j, Y" });
  flatpickr("#report-end", { dateFormat: "Y-m-d", altInput: true, altFormat: "M j, Y" });
}

async function generateReport() {
  const start = document.getElementById("report-start").value;
  const end = document.getElementById("report-end").value;
  const el = document.getElementById("report-result");
  if (!start || !end) { el.innerHTML = `<span class="error">Pick both dates.</span>`; return; }
  try {
    const pack = await apiFetch("/compliance/evidence-packs", {
      method: "POST", body: JSON.stringify({ period_start: start, period_end: end }),
    });
    el.innerHTML = `
      <div class="muted">Pack ${escapeHtml(pack.pack_id)} -- ${pack.item_count} decision(s)</div>
      <a class="btn btn-primary" style="display:inline-flex; margin-top:8px; text-decoration:none;"
         href="#" onclick="downloadWithAuth(event, '${pack.pack_id}', '${start}', '${end}')">
         <i class="fa-solid fa-download"></i> Download PDF</a>
    `;
  } catch (err) { el.innerHTML = `<span class="error">${escapeHtml(err.message)}</span>`; }
}

async function downloadWithAuth(event, packId, start, end) {
  event.preventDefault();
  try {
    const response = await fetch(`/compliance/evidence-packs/${packId}/document?period_start=${start}&period_end=${end}`, {
      headers: { "Authorization": `Bearer ${state.token}` },
    });
    if (!response.ok) throw new Error(`Download failed (${response.status})`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `evidence_pack_${packId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) { alert(err.message); }
}

async function loadTeam() {
  const isAdmin = state.roles.includes("admin");
  document.getElementById("invite-form-container").style.display = isAdmin ? "block" : "none";
  document.getElementById("api-keys-card").style.display = isAdmin ? "block" : "none";
  try {
    const users = await apiFetch("/auth/users");
    document.getElementById("team-list").innerHTML = users.map(u => `
      <div class="row">
        <div>${escapeHtml(u.name)} <span class="muted">${escapeHtml(u.email)}</span></div>
        <span class="muted">${escapeHtml(u.roles.join(", "))}</span>
      </div>
    `).join("");
  } catch (err) { document.getElementById("team-list").innerHTML = `<span class="error">${escapeHtml(err.message)}</span>`; }
  if (isAdmin) loadApiKeys();
}

async function inviteUser() {
  try {
    await apiFetch("/auth/users", { method: "POST", body: JSON.stringify({
      name: document.getElementById("invite-name").value,
      email: document.getElementById("invite-email").value,
      password: document.getElementById("invite-password").value,
      role: document.getElementById("invite-role").value,
    })});
    loadTeam();
  } catch (err) { alert(err.message); }
}

async function loadApiKeys() {
  try {
    const keys = await apiFetch("/auth/api-keys");
    document.getElementById("api-keys-list").innerHTML = keys.map(k => `
      <div class="row">
        <div>${escapeHtml(k.name)} <span class="muted">${k.revoked ? "revoked" : "active"}</span></div>
        ${!k.revoked ? `<button class="btn btn-outline" onclick="revokeKey('${k.id}')">Revoke</button>` : ""}
      </div>
    `).join("");
  } catch (err) { document.getElementById("api-keys-list").innerHTML = `<span class="error">${escapeHtml(err.message)}</span>`; }
}

async function createApiKey() {
  const name = document.getElementById("new-key-name").value;
  try {
    const result = await apiFetch("/auth/api-keys", { method: "POST", body: JSON.stringify({ name }) });
    document.getElementById("new-key-result").innerHTML = `
      <div class="muted">Copy this now -- shown only once:</div>
      <code class="key">${escapeHtml(result.plaintext_key)}</code>
    `;
    loadApiKeys();
  } catch (err) { alert(err.message); }
}

async function revokeKey(id) {
  try { await apiFetch(`/auth/api-keys/${id}`, { method: "DELETE" }); loadApiKeys(); }
  catch (err) { alert(err.message); }
}

if (loadSession()) {
  renderAuthState();
} else if (document.getElementById("auth-view")) {
  renderAuthState();
} else {
  window.location.href = "/dashboard/";
}
