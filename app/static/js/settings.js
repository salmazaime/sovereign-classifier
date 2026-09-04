// app/static/js/settings.js
// Runs on /dashboard/settings only. Relies on state already being
// populated by app.js's loadSession() call (which runs immediately
// when app.js loads, before this file's DOMContentLoaded fires).

async function loadSettingsPage() {
  if (!state.token) { window.location.href = "/dashboard/"; return; }

  const accountEl = document.getElementById("settings-account");
  const companyEl = document.getElementById("settings-company");

  try {
    const me = await apiFetch("/auth/me");

    accountEl.innerHTML = `
      <div class="two-col">
        <div><label>Name</label><input value="${escapeHtml(me.name)}" disabled></div>
        <div><label>Email</label><input value="${escapeHtml(me.email)}" disabled></div>
      </div>
      <label>Roles</label>
      <div style="margin-bottom: 8px;">
        ${me.roles.map(r => `<span class="badge ALLOW" style="margin-right:6px;">${escapeHtml(r)}</span>`).join("")}
      </div>
    `;

    const isAdmin = me.roles.includes("admin");
    const c = me.company;

    companyEl.innerHTML = `
      <div class="two-col">
        <div><label>Company name</label><input value="${escapeHtml(c.name)}" disabled></div>
        <div>
          <label>Sector</label>
          <input id="settings-sector" value="${escapeHtml(c.sector || '')}" ${isAdmin ? '' : 'disabled'}>
        </div>
      </div>

      <div class="toggle-row">
        <div>
          <div>Designated OIV (Infrastructure d'Importance Vitale)</div>
          <div class="desc">Enable if this organization has been officially designated as critical infrastructure under Loi 05-20. Triggers mandatory qualified-provider hosting.</div>
        </div>
        <label class="switch">
          <input type="checkbox" id="settings-is-oiv" ${c.is_oiv ? "checked" : ""} ${isAdmin ? '' : 'disabled'}>
          <span class="slider"></span>
        </label>
      </div>

      <div class="toggle-row">
        <div>
          <div>Require qualified provider hosting</div>
          <div class="desc">When enabled, ALL data must be hosted on a certified sovereign provider (Decree 2.24.921) -- standard AWS/Azure regions will be automatically denied.</div>
        </div>
        <label class="switch">
          <input type="checkbox" id="settings-qpr" ${c.qualified_provider_required ? "checked" : ""} ${isAdmin ? '' : 'disabled'}>
          <span class="slider"></span>
        </label>
      </div>

      <div class="toggle-row" id="oiv-sector-row" style="${c.is_oiv ? '' : 'display:none;'}">
        <div style="flex: 1;">
          <label>OIV Sector</label>
          <select id="settings-oiv-sector" ${isAdmin ? '' : 'disabled'}>
            <option value="banking" ${c.oiv_sector === 'banking' ? 'selected' : ''}>Banking</option>
            <option value="telecom" ${c.oiv_sector === 'telecom' ? 'selected' : ''}>Telecom</option>
            <option value="energy" ${c.oiv_sector === 'energy' ? 'selected' : ''}>Energy</option>
            <option value="health" ${c.oiv_sector === 'health' ? 'selected' : ''}>Health</option>
            <option value="government" ${c.oiv_sector === 'government' ? 'selected' : ''}>Government</option>
          </select>
        </div>
      </div>

      ${isAdmin ? `
        <button class="btn btn-primary" onclick="saveCompanySettings()" style="margin-top: 10px;"><i class="fa-solid fa-floppy-disk"></i> Save changes</button>
        <div id="settings-save-result" style="margin-top: 10px;"></div>
      ` : `<p class="muted" style="margin-top:10px;">Only admins can modify these settings.</p>`}
    `;

    if (isAdmin) {
      document.getElementById("settings-is-oiv").addEventListener("change", (e) => {
        document.getElementById("oiv-sector-row").style.display = e.target.checked ? "" : "none";
      });
    }
  } catch (err) {
    companyEl.innerHTML = `<span class="error">${escapeHtml(err.message)}</span>`;
  }
}

async function saveCompanySettings() {
  const resultEl = document.getElementById("settings-save-result");
  const isOiv = document.getElementById("settings-is-oiv").checked;
  const body = {
    sector: document.getElementById("settings-sector").value,
    is_oiv: isOiv,
    qualified_provider_required: document.getElementById("settings-qpr").checked,
    oiv_sector: isOiv ? document.getElementById("settings-oiv-sector").value : null,
  };
  try {
    await apiFetch("/auth/company", { method: "PATCH", body: JSON.stringify(body) });
    resultEl.innerHTML = `<span style="color: var(--allow);"><i class="fa-solid fa-check"></i> Saved.</span>`;
  } catch (err) {
    resultEl.innerHTML = `<span class="error">${escapeHtml(err.message)}</span>`;
  }
}

// app.js's own bottom-of-file code already calls renderAuthState()
// on page load (via loadSession() check), which builds the sidebar
// on THIS page too -- settings.html extends the same base.html with
// the same #sidebar/#topbar markup. We only need to additionally
// load the settings-specific content once the DOM and session are ready.
document.addEventListener("DOMContentLoaded", () => {
  if (state.token) {
    document.getElementById("page-title").textContent = "Settings";
    loadSettingsPage();
  }
});
