import { apiFetch, apiPost } from "../api.js";
import { state } from "../state.js";
import { renderRiskBadge, renderStatusBadge, showToast } from "../utils.js";
import { showCsvSchemaModal } from "../components/csvUpload.js";

export { showCsvSchemaModal };

const RAMO_OPTIONS = ["Vehículos", "Salud", "Vida", "Generales", "Hogar", "Otro"];
const COBERTURA_OPTIONS = ["Choque", "Robo", "Atención médica", "Incendio", "Daño", "Otro"];
const ESTADO_OPTIONS = ["Reserva", "Pago Total", "Pago Parcial", "Anticipo", "Negativa", "Cierre Sin Consecuencia", "Liquidado"];

export async function loadSiniestros() {
    state.claimsData = await apiFetch("/claims") || [];
    renderSiniestrosView();
    window._siniestrosLoaded = true;
}

// Recarga la lista cuando se completa una importación CSV exitosa
window.addEventListener("csv:imported", async (e) => {
    if (e.detail?.entity === "siniestros" && window._siniestrosLoaded) {
        await loadSiniestros();
    }
});

export function renderSiniestrosView() {
    const page = document.getElementById("page-siniestros");
    const claims = getVisibleClaims();
    const types = [...new Set(state.claimsData.map(c => c.claim_type).filter(Boolean))];
    const statuses = [...new Set(state.claimsData.map(c => c.audit_status).filter(Boolean))];
    const groups = groupByInsured(claims);

    // Solo reconstruir toolbar si no existe o si cambian opciones dinámicas
    let toolbar = page.querySelector(".siniestros-toolbar");
    if (!toolbar) {
        page.innerHTML = `
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;">
            <div>
                <h1>Siniestros</h1>
                <p>Siniestros reportados agrupados por asegurado. Expanda cada fila para ver facturas y consultar el riesgo con DeepSeek.</p>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <button class="btn btn-ghost" onclick="showCsvSchemaModal('siniestros')" title="Importar múltiples siniestros desde archivo CSV">
                    ⬆ Importar CSV
                </button>
                <button class="btn btn-primary" onclick="toggleClaimForm()">
                    ${state.showClaimForm ? "✕ Cerrar formulario" : "+ Añadir Manual"}
                </button>
            </div>
        </div>
        ${state.showClaimForm ? renderClaimForm() : ""}
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
        // Actualizar selectores sin recrear el DOM
        const searchInput = toolbar.querySelector("input[type=search]");
        if (searchInput && document.activeElement !== searchInput) {
            searchInput.value = state.claimsSearchTerm || "";
        }
        const typeSelect = toolbar.querySelector("select:nth-of-type(1)");
        const statusSelect = toolbar.querySelector("select:nth-of-type(2)");
        const sortSelect = toolbar.querySelector("select:nth-of-type(3)");
        if (typeSelect) typeSelect.value = state.claimsTypeFilter;
        if (statusSelect) statusSelect.value = state.claimsStatusFilter;
        if (sortSelect) sortSelect.value = `${state.claimsSortBy}:${state.claimsSortDir}`;
    }

    // Render solo el body de la tabla
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
            <h2>Seniales de posible fraude</h2>
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

// ── Agrupacion por asegurado ────────────────────────────

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
    if (groups.length === 0) return '<tr><td colspan="12" class="empty-cell">No hay siniestros para este filtro.</td></tr>';
    return groups.map(([name, claims]) => `
        <tr class="group-header"><td colspan="12"><strong>${name}</strong> (${claims.length} siniestro${claims.length !== 1 ? "s" : ""})</td></tr>
        ${claims.map(c => renderClaimRow(c)).join("")}
    `).join("");
}

// ── Busqueda con debounce ───────────────────────────────

let _searchTimer = null;
window.debouncedSearch = function (value) {
    if (_searchTimer) clearTimeout(_searchTimer);
    _searchTimer = setTimeout(() => {
        setClaimsSearch(value);
    }, 250);
};

// ── Consultar DeepSeek sobre un siniestro ────────────────

window.askDeepSeekAboutClaim = async function (claimId) {
    const c = state.claimsData.find(x => x.id === claimId);
    if (!c) return;
    const q = `Analiza el siniestro ${c.claim_number} del asegurado ${c.insured_name} (vehiculo: ${c.vehicle} placa ${c.vehicle_plate}, tipo: ${c.claim_type}, cobertura: ${c.cobertura}, monto reclamado: $${c.monto_reclamado || 0}). Score de fraude actual: ${c.fraud_score ?? "N/A"} (${c.fraud_classification || "N/A"}). ¿Por qué fue marcado con este riesgo? ¿Qué seniales de fraude aplican y que recomendacion das?`;

    const panel = document.getElementById("chatbot-panel");
    const toggle = document.getElementById("chatbot-toggle");
    const body = document.getElementById("chatbot-body");
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

export async function submitNewClaim() {
    const policy = (document.getElementById("sn-policy").value || "").trim();
    const insuredId = (document.getElementById("sn-insured-id").value || "").trim();
    const incidentDate = (document.getElementById("sn-date").value || "").trim();
    if (!policy || !insuredId || !incidentDate) {
        showToast("Póliza, ID asegurado y fecha son requeridos", "error");
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
