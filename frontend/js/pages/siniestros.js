import { apiFetch, apiPost } from "../api.js";
import { state } from "../state.js";
import { renderRiskBadge, renderStatusBadge, showToast } from "../utils.js";
import { getPermissions } from "../auth.js";

const RAMO_OPTIONS = ["Vehículos", "Salud", "Vida", "Generales", "Hogar", "Otro"];
const COBERTURA_OPTIONS = ["Choque", "Robo", "Atención médica", "Incendio", "Daño", "Otro"];
const ESTADO_OPTIONS = ["Reserva", "Pago Total", "Pago Parcial", "Anticipo", "Negativa", "Cierre Sin Consecuencia", "Liquidado"];

export async function loadSiniestros() {
    state.claimsData = await apiFetch("/claims") || [];
    renderSiniestrosView();
    window._siniestrosLoaded = true;
    // Si un siniestro viene pre-expandido (p.ej. desde el flujo del Panel),
    // su fila muestra el spinner pero nadie dispara el fetch de facturas:
    // solo toggleClaimPreview lo hace. Hidratamos el caché aquí.
    const preOpenedId = state.claimExpanded;
    if (preOpenedId != null && state.claimInvoicesCache[preOpenedId] === undefined) {
        const invs = await apiFetch(`/claims/${preOpenedId}/invoices`);
        state.claimInvoicesCache[preOpenedId] = invs || [];
        if (state.claimExpanded === preOpenedId) renderSiniestrosView();
    }
}

// Recarga la lista cuando se completa una importación CSV exitosa
window.addEventListener("csv:imported", async (e) => {
    if (e.detail?.entity === "siniestros" && window._siniestrosLoaded) {
        await loadSiniestros();
    }
});

export function renderSiniestrosView() {
    const page = document.getElementById("page-siniestros");
    if (!page) return;

    const claims = getVisibleClaims();
    const types = [...new Set(state.claimsData.map(c => c.claim_type).filter(Boolean))];
    const statuses = [...new Set(state.claimsData.map(c => c.audit_status).filter(Boolean))];
    const groups = groupByInsured(claims);

    // Solo reconstruir toolbar/outer si no existe
    let toolbar = page.querySelector(".siniestros-toolbar");
    if (!toolbar) {
        const canRegister = !!getPermissions().canRegisterClaim;
        page.innerHTML = `
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;">
            <div>
                <h1>Siniestros</h1>
                <p>Siniestros reportados agrupados por asegurado. Expanda cada fila para ver facturas y consultar el riesgo con DeepSeek.</p>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
                ${canRegister ? `<button class="btn btn-ghost" onclick="showCsvSchemaModal('siniestros')" title="Importar múltiples siniestros desde archivo CSV">
                    ⬆ Importar CSV
                </button>` : ""}
                ${canRegister ? `<button class="btn btn-primary" onclick="toggleClaimForm()">
                    ${state.showClaimForm ? "✕ Cerrar formulario" : "+ Añadir Manual"}
                </button>` : ""}
            </div>
        </div>
        <div id="claim-form-container">
            ${state.showClaimForm ? renderClaimForm() : ""}
        </div>
        ${renderWorkflowContext()}
        ${renderFraudReferencePanel()}
        <div class="card">
            <div class="card-header siniestros-toolbar">
                <input class="filter-input" type="search" value="${state.claimsSearchTerm || ""}" placeholder="Buscar numero, placa, asegurado..." oninput="debouncedSearch(this.value)">
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
                        ["insured_name:asc", "Asegurado A-Z"],
                        ["risk_score:desc", "Mayor riesgo"],
                        ["invoice_count:desc", "Mas facturas"],
                    ].map(([value, label]) => `<option value="${value}" ${`${state.claimsSortBy}:${state.claimsSortDir}` === value ? "selected" : ""}>${label}</option>`).join("")}
                </select>
            </div>
            <div class="card-body table-wrap" id="claims-table-wrap"></div>
        </div>

        <div id="summary-modal" style="display:none; position:fixed; inset:0; z-index:520; background:rgba(0,0,0,0.45); backdrop-filter:blur(4px); align-items:center; justify-content:center;">
            <div class="siniestro-modal" style="background:var(--bg-secondary); border:1px solid var(--border-primary); border-radius:16px; padding:18px; width:100%; max-width:780px; max-height:76vh; overflow:auto; box-shadow:var(--shadow-lg);">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                    <h3 style="margin:0;">Resumen Ejecutivo del Vehículo y Asegurado</h3>
                    <button class="btn btn-ghost btn-sm" onclick="closeSummaryModal()">Cerrar</button>
                </div>
                <div id="summary-content" style="font-size:0.9rem;color:var(--text-secondary);">Cargando...</div>
            </div>
        </div>`;
        toolbar = page.querySelector(".siniestros-toolbar");
    } else {
        // Actualizar selectores sin recrear el DOM (mantiene foco del buscador)
        const searchInput = toolbar.querySelector("input[type=search]");
        if (searchInput && document.activeElement !== searchInput) {
            searchInput.value = state.claimsSearchTerm || "";
        }
        const typeSelect = toolbar.querySelector("select:nth-of-type(1)");
        const statusSelect = toolbar.querySelector("select:nth-of-type(2)");
        const sortSelect = toolbar.querySelector("select:nth-of-type(3)");
        if (typeSelect) typeSelect.value = state.claimsTypeFilter || "all";
        if (statusSelect) statusSelect.value = state.claimsStatusFilter || "all";
        if (sortSelect) sortSelect.value = `${state.claimsSortBy}:${state.claimsSortDir}`;

        const formContainer = page.querySelector("#claim-form-container");
        if (formContainer) {
            const canRegister = !!getPermissions().canRegisterClaim;
            formContainer.innerHTML = (state.showClaimForm && canRegister) ? renderClaimForm() : "";
        }
    }

    // Renderizar solo el cuerpo de la tabla
    const wrap = page.querySelector("#claims-table-wrap");
    if (wrap) {
        const useGrouping = state.claimsSortBy === "insured_name" || !state.claimsSearchTerm?.trim();
        wrap.innerHTML = `<table>
            <thead><tr>
                <th style="width:24px"></th>
                <th>Numero</th><th>Ramo</th><th>Cobertura</th><th>Bien Asegurado</th>
                <th>Asegurado</th><th>Poliza</th><th>Facturas</th>
                <th>Estado</th><th>Score Fraude</th><th></th>
            </tr></thead>
            <tbody>
                ${useGrouping ? renderGroupedRows(groups) : claims.map(c => renderClaimRow(c)).join("") || '<tr><td colspan="11" class="empty-cell">No hay siniestros para este filtro.</td></tr>'}
            </tbody>
        </table>`;
    }
}

function renderWorkflowContext() {
    const focus = state.workflowFocus;
    if (!focus || focus.page !== "siniestros") return "";
    const chips = [focus.claim_number].filter(Boolean);
    return `<div class="workflow-context-banner">
        <div>
            <strong>${focus.title || "Siniestro seleccionado desde Flujo"}</strong>
            <span>${focus.detail || "Revisa la fila resaltada y sus facturas asociadas."}</span>
        </div>
        <div class="workflow-context-actions">
            ${chips.map(chip => `<span class="workflow-chip">${chip}</span>`).join("")}
            <button class="btn btn-ghost btn-sm" onclick="clearClaimsWorkflowFocus()">Cerrar</button>
        </div>
    </div>`;
}

function renderFraudReferencePanel() {
    const signals = [
        ["Vigencia", "Reclamo cercano al borde de vigencia", "<= 10 dias: 8 pts"],
        ["Robo", "Demora entre ocurrencia y denuncia formal", "> 48 horas: 8 pts"],
        ["Frecuencia asegurado", "Multiples siniestros en 18 meses", ">= 3 siniestros: 8 pts"],
        ["Frecuencia vehiculo", "Vehiculo con multiples reclamos", ">= 3 siniestros: 6 pts"],
        ["Proveedor recurrente", "Beneficiario/proveedor asociado a varios casos", "> 2 casos observados: 5 pts"],
        ["Documentos", "Faltantes o inconsistentes", "Hasta 10 pts"],
        ["Narrativas", "Descripciones similares entre reclamos", "> 85% similitud: 8 pts"],
        ["Monto", "Cercano o superior a suma asegurada", ">95% suma asegurada: 5 pts"],
    ];
    return `<div class="card" style="margin-bottom:16px;border-left:4px solid var(--accent-indigo);">
        <div class="card-header" style="cursor:pointer;display:flex;justify-content:space-between;align-items:center;" onclick="var b=this.parentElement.querySelector('.card-body');var o=b.style.display==='none';b.style.display=o?'block':'';this.querySelector('span').textContent=o?'\u2212':'+'">
            <h2>Señales de posible fraude</h2>
            <span style="font-size:1.2rem;color:var(--accent-indigo);">+</span>
        </div>
        <div class="card-body" style="display:none">${miniTable(["Señal", "Criterio", "Puntaje"], signals)}</div>
    </div>`;
}

function miniTable(headers, rows) {
    return `<table style="font-size:0.76rem;"><thead><tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

function getVisibleClaims() {
    const q = (state.claimsSearchTerm || "").toLowerCase().trim();
    const filtered = state.claimsData.filter(c => {
        const matchesSearch = !q || [
            c.claim_number, c.claim_type, c.cobertura, c.vehicle, c.vehicle_plate,
            c.insured_name, c.policy_number, c.beneficiario, c.sucursal,
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

export function clearClaimsWorkflowFocus() {
    state.workflowFocus = null;
    renderSiniestrosView();
}

function bienAsegurado(c) {
    const ramo = c.claim_type || "";
    if (ramo === "Vehículos") {
        const parts = [];
        if (c.vehicle && c.vehicle !== "N/D") parts.push(c.vehicle);
        if (c.vehicle_plate && c.vehicle_plate !== "N/D") parts.push(`<span style="font-family:var(--font-mono);font-size:0.8rem;color:var(--text-muted);">(${c.vehicle_plate})</span>`);
        return parts.join(" ") || "Vehículo N/D";
    } else if (ramo === "Hogar") {
        return "🏠 Inmueble Asegurado";
    } else if (ramo === "Salud" || ramo === "Vida") {
        return `👤 ${c.insured_name || "Persona Asegurada"}`;
    } else if (ramo === "Generales") {
        return "📦 Bienes Generales";
    } else {
        return `💼 Cobertura ${c.cobertura || "General"}`;
    }
}

function renderClaimRow(c) {
    const isExpanded = state.claimExpanded === c.id;
    const main = `
        <tr style="cursor:pointer; ${isExpanded ? 'background:rgba(99,102,241,0.05);' : ''}" onclick="toggleClaimPreview(${c.id})">
            <td><span style="display:inline-block; transition:transform 0.2s; transform:rotate(${isExpanded ? 90 : 0}deg); color:var(--accent-indigo); font-size:0.8rem;">▶</span></td>
            <td><strong>${c.claim_number}</strong></td>
            <td><span class="cat-tag cat-${(c.claim_type || '').split('_')[0].toLowerCase()}">${(c.claim_type || '').replace(/_/g, ' ')}</span></td>
            <td>${c.cobertura || '-'}</td>
            <td>${bienAsegurado(c)}</td>
            <td>${c.insured_name || '-'}</td>
            <td style="font-family:var(--font-mono);color:var(--text-muted)">${c.policy_number || '-'}</td>
            <td>${c.invoice_count}</td>
            <td>${renderStatusBadge(c.audit_status)}</td>
            <td onclick="event.stopPropagation()">
                <div style="display:flex; align-items:center; gap:6px; justify-content:center;">
                    ${c.fraud_score !== null && c.fraud_score !== undefined ? renderRiskBadge(c.fraud_score) : '<span class="badge badge-info">N/A</span>'}
                    <button class="btn btn-ghost btn-sm" onclick="askDeepSeekAboutClaim(${c.id})" title="Consultar DeepSeek" style="padding:2px 6px; font-size:0.75rem; border:1px solid var(--border-primary);">
                        🤖 DeepSeek
                    </button>
                </div>
            </td>
            <td onclick="event.stopPropagation()" style="display:flex; gap:6px; align-items:center; justify-content:flex-end;">
                <button class="btn btn-sm" style="background:rgba(2,132,199,0.12); color:var(--accent-blue); border:1px solid rgba(2,132,199,0.2);" onclick="openSummaryModal(${c.id})" title="Ver resumen ejecutivo del siniestro">Resumen</button>
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

let _currentSummaryClaimId = null;

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
            </div>
            <p style="margin-top:10px;"><strong>Resumen:</strong> ${data.executive_summary || "-"}</p>
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

function groupByInsured(claims) {
    const groups = {};
    for (const c of claims) {
        const name = c.insured_name || "Sin asignar";
        if (!groups[name]) groups[name] = [];
        groups[name].push(c);
    }
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b, "es"));
}

function renderGroupedRows(groups) {
    if (groups.length === 0) return '<tr><td colspan="11" class="empty-cell">No hay siniestros para este filtro.</td></tr>';
    return groups.map(([name, claims]) => `
        <tr class="group-header"><td colspan="11"><strong>${name}</strong> (${claims.length} siniestro${claims.length !== 1 ? "s" : ""})</td></tr>
        ${claims.map(c => renderClaimRow(c)).join("")}
    `).join("");
}

let _searchTimer = null;
window.debouncedSearch = function(value) {
    if (_searchTimer) clearTimeout(_searchTimer);
    _searchTimer = setTimeout(() => {
        setClaimsSearch(value);
    }, 250);
};

window.askDeepSeekAboutClaim = async function(claimId) {
    const c = state.claimsData.find(x => x.id === claimId);
    if (!c) return;
    const q = `Analiza el siniestro ${c.claim_number} del asegurado ${c.insured_name} (tipo: ${c.claim_type}, cobertura: ${c.cobertura}, monto reclamado: $${c.monto_reclamado || 0}). Score de fraude actual: ${c.fraud_score ?? "N/A"} (${c.fraud_classification || "N/A"}). ¿Por qué fue marcado con este riesgo? ¿Qué señales de fraude aplican y qué recomendación das?`;

    const panel = document.getElementById("chatbot-panel");
    const toggle = document.getElementById("chatbot-toggle");
    const input = document.getElementById("chatbot-input");

    if (panel && toggle) {
        if (panel.style.display === "none") {
            toggle.click();
            await new Promise(r => setTimeout(r, 400));
        }
    }

    if (input) {
        input.value = q;
        input.focus();
        const sendBtn = document.getElementById("chatbot-send");
        if (sendBtn) {
            setTimeout(() => sendBtn.click(), 300);
        }
    }
};

function renderClaimForm() {
    const today = new Date().toISOString().slice(0, 10);
    return `
    <div class="card" style="margin-bottom:18px;border-left:4px solid var(--accent-indigo);">
        <div class="card-header"><h2>Nuevo Siniestro Manual</h2></div>
        <div class="card-body">
            <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;">
                <label>Poliza <input id="sn-policy" type="text" placeholder="POL-0001" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <label>ID Asegurado <input id="sn-insured-id" type="text" placeholder="ASE-12345" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <label>Nombre del Asegurado <input id="sn-insured-name" type="text" placeholder="Juan Perez" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <label>Fecha de Ocurrencia <input id="sn-date" type="date" value="${today}" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <label>Ramo
                    <select id="sn-ramo" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;">
                        ${RAMO_OPTIONS.map(r => `<option value="${r}" ${r === "Vehículos" ? "selected" : ""}>${r}</option>`).join("")}
                    </select>
                </label>
                <label>Cobertura
                    <select id="sn-cobertura" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;">
                        ${COBERTURA_OPTIONS.map(c => `<option value="${c}" ${c === "Choque" ? "selected" : ""}>${c}</option>`).join("")}
                    </select>
                </label>
                <label>Estado
                    <select id="sn-estado" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;">
                        ${ESTADO_OPTIONS.map(s => `<option value="${s}" ${s === "Reserva" ? "selected" : ""}>${s}</option>`).join("")}
                    </select>
                </label>
                <label>Monto Reclamado (USD) <input id="sn-monto" type="number" step="0.01" min="0" value="0" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <label>Sucursal <input id="sn-sucursal" type="text" placeholder="Quito-Norte" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <label>Placa del Vehiculo <input id="sn-plate" type="text" placeholder="PBA-1234" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;text-transform:uppercase;"></label>
                <label>Marca <input id="sn-brand" type="text" placeholder="Toyota" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <label>Modelo <input id="sn-model" type="text" placeholder="Corolla" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <label>Anio <input id="sn-year" type="number" min="1900" max="2100" placeholder="2022" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <label style="grid-column:1/3;">Descripcion <textarea id="sn-desc" placeholder="Detalles del incidente..." style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;min-height:60px;resize:vertical;"></textarea></label>
            </div>
            <p style="margin-top:10px;font-size:0.78rem;color:var(--text-muted);">
                Si la poliza, asegurado o vehiculo no existen aun, se crearan placeholders preservando el audit trail.
            </p>
            <div style="margin-top:14px;display:flex;gap:8px;">
                <button class="btn btn-success" onclick="submitNewClaim()">Guardar Siniestro</button>
                <button class="btn btn-ghost" onclick="toggleClaimForm()">Cancelar</button>
            </div>
        </div>
    </div>
    `;
}

export function toggleClaimForm() {
    state.showClaimForm = !state.showClaimForm;
    renderSiniestrosView();
}

export async function submitNewClaim() {
    const policy = (document.getElementById("sn-policy").value || "").trim();
    const insuredId = (document.getElementById("sn-insured-id").value || "").trim();
    const incidentDate = (document.getElementById("sn-date").value || "").trim();
    if (!policy || !insuredId || !incidentDate) {
        showToast("Poliza, ID asegurado y fecha son requeridos", "error");
        return;
    }
    const yearRaw = (document.getElementById("sn-year").value || "").trim();
    const payload = {
        policy_number: policy,
        insured_id: insuredId,
        insured_name: (document.getElementById("sn-insured-name").value || "").trim(),
        ramo: document.getElementById("sn-ramo").value,
        cobertura: document.getElementById("sn-cobertura").value,
        estado: document.getElementById("sn-estado").value,
        incident_date: incidentDate,
        monto_reclamado: parseFloat(document.getElementById("sn-monto").value || "0"),
        sucursal: (document.getElementById("sn-sucursal").value || "").trim(),
        descripcion: (document.getElementById("sn-desc").value || "").trim(),
        vehicle_plate: (document.getElementById("sn-plate").value || "").trim().toUpperCase(),
        vehicle_brand: (document.getElementById("sn-brand").value || "").trim(),
        vehicle_model: (document.getElementById("sn-model").value || "").trim(),
        vehicle_year: yearRaw ? parseInt(yearRaw, 10) : null,
    };
    const res = await apiPost("/claims", payload);
    if (res) {
        showToast(`Siniestro ${res.claim_number} creado`, "success");
        state.showClaimForm = false;
        await loadSiniestros();
    }
}
