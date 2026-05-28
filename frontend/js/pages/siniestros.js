import { apiFetch, apiPost } from "../api.js";
import { state } from "../state.js";
import { renderRiskBadge, renderStatusBadge, showToast } from "../utils.js";

export async function loadSiniestros() {
    state.claimsData = await apiFetch("/claims") || [];
    renderSiniestrosView();
}

export function renderSiniestrosView() {
    const page = document.getElementById("page-siniestros");
    const claims = getVisibleClaims();
    const types = [...new Set(state.claimsData.map(c => c.claim_type).filter(Boolean))];
    const statuses = [...new Set(state.claimsData.map(c => c.audit_status).filter(Boolean))];
    page.innerHTML = `
        <div class="page-header">
            <h1>Siniestros</h1>
            <p>Siniestros reportados y su estado. Expanda cada fila para ver facturas y configurar destinatarios de notificación.</p>
        </div>
        <div class="card">
            <div class="card-header siniestros-toolbar">
                <input class="filter-input" type="search" value="${state.claimsSearchTerm || ""}" placeholder="Buscar numero, placa, asegurado..." oninput="setClaimsSearch(this.value)">
                <select class="filter-select" onchange="setClaimsTypeFilter(this.value)">
                    <option value="all">Todos los tipos</option>
                    ${types.map(t => `<option value="${t}" ${state.claimsTypeFilter === t ? "selected" : ""}>${t.replace(/_/g, " ")}</option>`).join("")}
                </select>
                <select class="filter-select" onchange="setClaimsStatusFilter(this.value)">
                    <option value="all">Todos los estados</option>
                    ${statuses.map(s => `<option value="${s}" ${state.claimsStatusFilter === s ? "selected" : ""}>${s.replace(/_/g, " ")}</option>`).join("")}
                </select>
                <select class="filter-select" onchange="setClaimsSort(this.value)">
                    ${[
                        ["incident_date:desc", "Fecha reciente"],
                        ["incident_date:asc", "Fecha antigua"],
                        ["claim_number:asc", "Numero A-Z"],
                        ["claim_type:asc", "Tipo A-Z"],
                        ["risk_score:desc", "Mayor riesgo"],
                        ["invoice_count:desc", "Mas facturas"],
                    ].map(([value, label]) => `<option value="${value}" ${`${state.claimsSortBy}:${state.claimsSortDir}` === value ? "selected" : ""}>${label}</option>`).join("")}
                </select>
            </div>
            <div class="card-body table-wrap">
                <table>
                    <thead><tr>
                        <th style="width:24px"></th>
                        <th>Numero</th><th>Tipo</th><th>Vehiculo</th><th>Placa</th>
                        <th>Asegurado</th><th>Poliza</th><th>Facturas</th>
                        <th>Estado Auditoria</th><th>Riesgo</th><th></th>
                    </tr></thead>
                    <tbody>
                        ${claims.map(c => renderClaimRow(c)).join("") || '<tr><td colspan="11" class="empty-cell">No hay siniestros para este filtro.</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Modal destinatarios -->
        <div id="notify-modal" style="display:none; position:fixed; inset:0; z-index:500; background:rgba(0,0,0,0.4); backdrop-filter:blur(4px); display:none; align-items:center; justify-content:center;">
            <div class="siniestro-modal siniestro-modal-sm" style="background:var(--bg-secondary); border:1px solid var(--border-primary); border-radius:16px; padding:22px; width:100%; max-width:420px; box-shadow:var(--shadow-lg);">
                <h3 style="margin-bottom:6px; color:var(--text-primary);">📧 Configurar Destinatarios</h3>
                <p style="font-size:0.85rem; color:var(--text-muted); margin-bottom:16px;">Los emails aquí configurados recibirán la notificación PDF al ejecutar "Notificar Taller".</p>

                <div style="background:var(--bg-tertiary); border-radius:8px; padding:12px; margin-bottom:14px; font-size:0.83rem;">
                    <span style="color:var(--text-muted);">Email del taller (automático):</span><br>
                    <strong id="notify-workshop-email" style="color:var(--accent-indigo);">—</strong>
                </div>

                <label style="font-size:0.85rem; font-weight:600; color:var(--text-secondary); display:block; margin-bottom:6px;">
                    Correos adicionales (separados por coma):
                </label>
                <textarea id="notify-extra-emails"
                    placeholder="ej: auditor@empresa.com, supervisor@empresa.com"
                    style="width:100%; min-height:80px; border:1px solid var(--border-primary); border-radius:8px; padding:10px; font-family:var(--font-mono); font-size:0.83rem; background:var(--bg-primary); color:var(--text-primary); resize:vertical;"></textarea>

                <div style="display:flex; gap:8px; margin-top:16px; justify-content:flex-end;">
                    <button class="btn btn-ghost btn-sm" onclick="closeNotifyModal()">Cancelar</button>
                    <button class="btn btn-primary btn-sm" onclick="saveNotifyConfig()" id="btn-save-notify">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/></svg>
                        Guardar
                    </button>
                </div>
            </div>
        </div>

        <div id="summary-modal" style="display:none; position:fixed; inset:0; z-index:520; background:rgba(0,0,0,0.45); backdrop-filter:blur(4px); align-items:center; justify-content:center;">
            <div class="siniestro-modal" style="background:var(--bg-secondary); border:1px solid var(--border-primary); border-radius:16px; padding:18px; width:100%; max-width:780px; max-height:76vh; overflow:auto; box-shadow:var(--shadow-lg);">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                    <h3 style="margin:0;">Resumen Ejecutivo del Vehículo y Asegurado</h3>
                    <button class="btn btn-ghost btn-sm" onclick="closeSummaryModal()">Cerrar</button>
                </div>
                <div id="summary-content" style="font-size:0.9rem;color:var(--text-secondary);">Cargando...</div>
            </div>
        </div>
    `;
}

function getVisibleClaims() {
    const q = (state.claimsSearchTerm || "").toLowerCase().trim();
    const filtered = state.claimsData.filter(c => {
        const matchesSearch = !q || [
            c.claim_number, c.claim_type, c.vehicle, c.vehicle_plate,
            c.insured_name, c.policy_number,
        ].some(v => String(v || "").toLowerCase().includes(q));
        const matchesType = state.claimsTypeFilter === "all" || c.claim_type === state.claimsTypeFilter;
        const matchesStatus = state.claimsStatusFilter === "all" || c.audit_status === state.claimsStatusFilter;
        return matchesSearch && matchesType && matchesStatus;
    });

    const dir = state.claimsSortDir === "asc" ? 1 : -1;
    return filtered.sort((a, b) => {
        const key = state.claimsSortBy || "incident_date";
        let av = a[key];
        let bv = b[key];
        if (key === "incident_date") {
            av = av ? Date.parse(av) : 0;
            bv = bv ? Date.parse(bv) : 0;
        } else if (typeof av === "string" || typeof bv === "string") {
            return String(av || "").localeCompare(String(bv || ""), "es") * dir;
        } else {
            av = Number(av ?? -1);
            bv = Number(bv ?? -1);
        }
        return (av === bv ? 0 : av > bv ? 1 : -1) * dir;
    });
}

export function setClaimsSearch(value) {
    state.claimsSearchTerm = value || "";
    renderSiniestrosView();
}

export function setClaimsTypeFilter(value) {
    state.claimsTypeFilter = value || "all";
    renderSiniestrosView();
}

export function setClaimsStatusFilter(value) {
    state.claimsStatusFilter = value || "all";
    renderSiniestrosView();
}

export function setClaimsSort(value) {
    const [sortBy, sortDir] = (value || "incident_date:desc").split(":");
    state.claimsSortBy = sortBy;
    state.claimsSortDir = sortDir || "desc";
    renderSiniestrosView();
}

function renderClaimRow(c) {
    const isExpanded = state.claimExpanded === c.id;
    const main = `
        <tr style="cursor:pointer; ${isExpanded ? 'background:rgba(99,102,241,0.05);' : ''}" onclick="toggleClaimPreview(${c.id})">
            <td><span style="display:inline-block; transition:transform 0.2s; transform:rotate(${isExpanded ? 90 : 0}deg); color:var(--accent-indigo); font-size:0.8rem;">▶</span></td>
            <td><strong>${c.claim_number}</strong></td>
            <td><span class="cat-tag cat-${c.claim_type.split('_')[0]}">${c.claim_type.replace(/_/g, ' ')}</span></td>
            <td>${c.vehicle}</td>
            <td style="font-family:var(--font-mono)">${c.vehicle_plate}</td>
            <td>${c.insured_name}</td>
            <td style="font-family:var(--font-mono);color:var(--text-muted)">${c.policy_number}</td>
            <td>${c.invoice_count}</td>
            <td>${renderStatusBadge(c.audit_status)}</td>
            <td>${c.risk_score !== null ? renderRiskBadge(c.risk_score) : '<span class="badge badge-info">N/A</span>'}</td>
            <td onclick="event.stopPropagation()" style="display:flex; gap:6px; align-items:center;">
                <button class="btn btn-sm" style="background:rgba(2,132,199,0.12); color:var(--accent-blue); border:1px solid rgba(2,132,199,0.2);" onclick="openSummaryModal(${c.id})" title="Ver resumen ejecutivo del vehículo y dueño">Resumen</button>
                <button class="btn btn-sm" style="background:rgba(99,102,241,0.1); color:var(--accent-indigo); border:1px solid rgba(99,102,241,0.2);" onclick="openNotifyModal(${c.id})" title="Configurar destinatarios de notificación">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,12 2,6"/></svg>
                </button>
                <button class="btn ${isExpanded ? 'btn-ghost' : 'btn-sm'} btn-sm" onclick="toggleClaimPreview(${c.id})" ${isExpanded ? '' : 'style="background-color: var(--accent-indigo); color: white;"'}>${isExpanded ? 'Ocultar' : 'Ver facturas'}</button>
            </td>
        </tr>
    `;
    if (!isExpanded) return main;
    const invs = state.claimInvoicesCache[c.id];
    let inner;
    if (invs === undefined) {
        inner = '<div style="display:flex;align-items:center;gap:8px;color:var(--text-muted);padding:12px"><span class="spinner"></span> Cargando facturas...</div>';
    } else if (invs.length === 0) {
        inner = '<div class="empty-state"><h3>Sin facturas asociadas a este siniestro</h3></div>';
    } else {
        inner = renderClaimInvoicesPreview(invs);
    }
    return main + `
        <tr class="claim-preview-row">
            <td colspan="11" style="padding:0;">
                <div style="padding:18px 24px; background:rgba(99,102,241,0.04); border-top:1px solid rgba(99,102,241,0.25);">
                    ${inner}
                </div>
            </td>
        </tr>
    `;
}

function renderClaimInvoicesPreview(invoices) {
    return `
        <h3 style="margin:0 0 12px; color:var(--accent-indigo); font-size:1rem;">Facturas Preliminares (${invoices.length})</h3>
        <div style="display:flex; flex-direction:column; gap:14px;">
            ${invoices.map(inv => {
                const statusBadge = inv.audit_id ? renderStatusBadge(inv.audit_status) : '<span class="badge badge-warning">Pendiente</span>';
                const goBtn = inv.audit_id
                    ? `<button class="btn btn-primary btn-sm" onclick="location.hash='audit/${inv.audit_id}'">Ver auditoría</button>`
                    : `<button class="btn btn-warning btn-sm" onclick="location.hash='pending/${inv.id}'">Auditar ahora</button>`;
                const risk = inv.risk_score !== null && inv.risk_score !== undefined ? renderRiskBadge(inv.risk_score) : '';
                return `
                <div style="background:var(--bg-card); border:1px solid var(--border-primary); border-radius:8px; padding:14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:8px;">
                        <div>
                            <strong style="font-size:1rem;">${inv.invoice_number}</strong>
                            <span style="color:var(--text-muted); margin-left:12px;">${inv.workshop_name || '-'}</span>
                            <span style="color:var(--text-muted); font-family:var(--font-mono); margin-left:8px; font-size:0.85rem;">RUC ${inv.workshop_ruc || '-'}</span>
                        </div>
                        <div style="display:flex; gap:8px; align-items:center;">
                            ${risk}${statusBadge}${goBtn}
                        </div>
                    </div>
                    <table style="margin-bottom:0;">
                        <thead><tr><th>Codigo</th><th>Descripcion</th><th>Cant.</th><th>Unitario</th><th>Total</th></tr></thead>
                        <tbody>
                            ${inv.items.map(it => `
                                <tr>
                                    <td><span style="font-family:var(--font-mono);color:var(--text-muted)">${it.code || '-'}</span></td>
                                    <td>${it.description}</td>
                                    <td>${it.quantity}</td>
                                    <td>$${(it.unit_price || 0).toFixed(2)}</td>
                                    <td>$${(it.total_price || 0).toFixed(2)}</td>
                                </tr>
                            `).join("")}
                        </tbody>
                        <tfoot>
                            <tr><td colspan="4" style="text-align:right;font-weight:600">Subtotal</td><td>$${(inv.subtotal||0).toFixed(2)}</td></tr>
                            <tr><td colspan="4" style="text-align:right;font-weight:600">IVA</td><td>$${(inv.iva||0).toFixed(2)}</td></tr>
                            <tr><td colspan="4" style="text-align:right;font-weight:700">Total</td><td style="font-weight:700">$${(inv.total||0).toFixed(2)}</td></tr>
                        </tfoot>
                    </table>
                </div>
            `}).join("")}
        </div>
    `;
}

export async function toggleClaimPreview(claimId) {
    if (state.claimExpanded === claimId) {
        state.claimExpanded = null;
        renderSiniestrosView();
        return;
    }
    state.claimExpanded = claimId;
    renderSiniestrosView();
    if (!state.claimInvoicesCache[claimId]) {
        const invs = await apiFetch(`/claims/${claimId}/invoices`);
        state.claimInvoicesCache[claimId] = invs || [];
        if (state.claimExpanded === claimId) renderSiniestrosView();
    }
}

// ── Modal de configuración de destinatarios ─────────────

let _currentNotifyClaimId = null;
let _currentSummaryClaimId = null;

export async function openNotifyModal(claimId) {
    _currentNotifyClaimId = claimId;
    const modal = document.getElementById("notify-modal");
    if (!modal) return;
    modal.style.display = "flex";

    // Cargar config actual
    const cfg = await apiFetch(`/claims/${claimId}/notify-config`);
    document.getElementById("notify-workshop-email").textContent = cfg?.workshop_email || '(no configurado)';
    document.getElementById("notify-extra-emails").value = cfg?.notify_emails || '';
}

export function closeNotifyModal() {
    const modal = document.getElementById("notify-modal");
    if (modal) modal.style.display = "none";
    _currentNotifyClaimId = null;
}

export async function saveNotifyConfig() {
    if (!_currentNotifyClaimId) return;
    const emails = document.getElementById("notify-extra-emails")?.value || "";
    const btn = document.getElementById("btn-save-notify");
    if (btn) { btn.disabled = true; btn.textContent = "Guardando..."; }

    const res = await fetch(`/api/claims/${_currentNotifyClaimId}/notify-config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notify_emails: emails }),
    });

    if (btn) { btn.disabled = false; btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/></svg> Guardar`; }

    if (res.ok) {
        showToast("Destinatarios guardados correctamente", "success");
        closeNotifyModal();
    } else {
        showToast("Error al guardar destinatarios", "error");
    }
}

export async function openSummaryModal(claimId) {
    _currentSummaryClaimId = claimId;
    const modal = document.getElementById("summary-modal");
    const content = document.getElementById("summary-content");
    if (!modal || !content) return;
    modal.style.display = "flex";
    content.innerHTML = '<div style="display:flex;align-items:center;gap:8px;"><span class="spinner"></span> Cargando resumen...</div>';

    const data = await apiFetch(`/claims/${claimId}/executive-summary`);
    if (!data) {
        content.textContent = "No se pudo cargar el resumen.";
        return;
    }

    const c = data.claim || {};
    const v = c.vehicle || {};
    const ownerRows = (data.owner_history || []).map((r) => `
        <tr><td>${r.claim_number}</td><td>${r.coverage || "-"}</td><td>${(r.date || "-").slice(0,10)}</td><td>$${(r.amount || 0).toFixed(2)}</td><td>${r.risk_score ?? "N/A"}</td></tr>
    `).join("");
    const vehicleRows = (data.vehicle_history || []).map((r) => `
        <tr><td>${r.claim_number}</td><td>${r.coverage || "-"}</td><td>${(r.date || "-").slice(0,10)}</td><td>$${(r.amount || 0).toFixed(2)}</td><td>${r.risk_score ?? "N/A"}</td></tr>
    `).join("");

    content.innerHTML = `
        <div class="card" style="margin-bottom:12px;"><div class="card-body">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                <div><strong>Siniestro:</strong> ${c.claim_number || "-"}</div>
                <div><strong>Póliza:</strong> ${c.policy_number || "-"}</div>
                <div><strong>Asegurado:</strong> ${c.insured_name || "-"}</div>
                <div><strong>ID Asegurado:</strong> ${c.insured_id || "-"}</div>
                <div><strong>Vehículo:</strong> ${v.brand || "-"} ${v.model || ""} ${v.year || ""}</div>
                <div><strong>Placa:</strong> ${v.plate || "-"}</div>
                <div><strong>Riesgo actual:</strong> ${c.risk_score ?? "N/A"}</div>
                <div><strong>Estado auditoría:</strong> ${c.audit_status || "pending"}</div>
            </div>
            <p style="margin-top:10px;"><strong>Resumen:</strong> ${data.executive_summary || "-"}</p>
            <p style="font-size:0.8rem;color:var(--text-muted);margin-top:6px;">${data.note || ""}</p>
        </div></div>

        <div class="grid-2">
            <div class="card"><div class="card-header"><h2>Historial del Dueño</h2></div><div class="card-body table-wrap"><table><thead><tr><th>Siniestro</th><th>Cobertura</th><th>Fecha</th><th>Monto</th><th>Riesgo</th></tr></thead><tbody>${ownerRows || "<tr><td colspan='5'>Sin historial</td></tr>"}</tbody></table></div></div>
            <div class="card"><div class="card-header"><h2>Historial del Vehículo</h2></div><div class="card-body table-wrap"><table><thead><tr><th>Siniestro</th><th>Cobertura</th><th>Fecha</th><th>Monto</th><th>Riesgo</th></tr></thead><tbody>${vehicleRows || "<tr><td colspan='5'>Sin historial</td></tr>"}</tbody></table></div></div>
        </div>
    `;
}

export function closeSummaryModal() {
    const modal = document.getElementById("summary-modal");
    if (modal) modal.style.display = "none";
    _currentSummaryClaimId = null;
}
