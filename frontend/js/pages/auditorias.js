import { apiFetch } from "../api.js";
import { state } from "../state.js";
import { renderRiskBadge, renderStatusBadge, renderEngineBadge, renderTestBadge } from "../utils.js";

export async function loadAuditorias() {
    const include = state.includeTest ? 1 : 0;
    const [audits, pending] = await Promise.all([
        apiFetch(`/audit-results?include_test=${include}`),
        apiFetch(`/invoices/pending?include_test=${include}`),
    ]);
    state.auditResults = audits || [];
    state.pendingInvoices = pending || [];
    renderAuditoriasView();
}

export function renderAuditoriasView() {
    const page = document.getElementById("page-auditorias");
    const term = state.auditSearchTerm.toLowerCase();
    const filteredPending = state.pendingInvoices.filter(i =>
        (i.invoice_number || "").toLowerCase().includes(term) ||
        (i.workshop_name || "").toLowerCase().includes(term)
    );
    const filteredReviewed = state.auditResults.filter(r =>
        (r.invoice_number || "").toLowerCase().includes(term) ||
        (r.workshop_name || "").toLowerCase().includes(term)
    );

    page.innerHTML = `
        <div class="page-header" style="display:flex; justify-content:space-between; align-items:flex-end;">
            <div>
                <h1>Auditorías</h1>
                <p>Gestión de facturas pendientes y auditadas</p>
            </div>
            <div style="display:flex;gap:12px;align-items:center;">
                <label style="display:flex;align-items:center;gap:6px;font-size:0.85rem;color:var(--text-muted);">
                    <input type="checkbox" id="aud-include-test" ${state.includeTest ? "checked" : ""} onchange="toggleAuditIncludeTest(this.checked)">
                    Incluir TEST
                </label>
                <input type="text" id="audit-search" placeholder="Buscar factura o taller..." value="${state.auditSearchTerm}"
                       style="padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; width: 250px; outline: none;"
                       onkeyup="setAuditSearch(this.value)">
            </div>
        </div>

        <div class="tabs" style="display:flex; gap:16px; margin-bottom:16px; border-bottom:1px solid #e2e8f0;">
            <button class="btn btn-ghost"
                    style="${state.currentAuditTab === 'pendientes' ? 'border-bottom:2px solid var(--accent-indigo); color:var(--accent-indigo); font-weight:600;' : ''}"
                    onclick="setAuditTab('pendientes')">
                Pendientes <span class="badge badge-warning" style="margin-left:8px">${filteredPending.length}</span>
            </button>
            <button class="btn btn-ghost"
                    style="${state.currentAuditTab === 'revisadas' ? 'border-bottom:2px solid var(--accent-indigo); color:var(--accent-indigo); font-weight:600;' : ''}"
                    onclick="setAuditTab('revisadas')">
                Revisadas <span class="badge badge-info" style="margin-left:8px">${filteredReviewed.length}</span>
            </button>
        </div>

        <div class="card">
            <div class="card-body table-wrap">
                ${state.currentAuditTab === 'pendientes' ? renderPendingTable(filteredPending) : renderReviewedTable(filteredReviewed)}
            </div>
        </div>
    `;

    const searchInput = document.getElementById("audit-search");
    if (searchInput && document.activeElement !== searchInput) {
        // keep current value in state, don't auto-focus on initial load
    }
}

function renderPendingTable(data) {
    if (data.length === 0) return '<div class="empty-state"><h3>No hay facturas pendientes</h3></div>';
    return `
        <table>
            <thead><tr>
                <th>ID</th><th>Factura</th><th>Siniestro</th><th>Tipo</th>
                <th>Taller</th><th>Monto</th><th>Acción</th>
            </tr></thead>
            <tbody>
                ${data.map(i => `
                    <tr class="clickable" onclick="location.hash='pending/${i.id}'" style="border-left: 4px solid var(--accent-warning)">
                        <td><span style="color:var(--text-muted);font-family:var(--font-mono)">#${i.id}</span></td>
                        <td><strong>${i.invoice_number}</strong> ${renderTestBadge(i.is_test)}</td>
                        <td>${i.claim_number}</td>
                        <td><span class="cat-tag cat-${(i.claim_type||'general').split('_')[0]}">${(i.claim_type||'-').replace(/_/g, ' ')}</span></td>
                        <td>${i.workshop_name}</td>
                        <td>$${(i.total || 0).toFixed(2)}</td>
                        <td><button class="btn btn-primary btn-sm">Auditar ahora</button></td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

function renderReviewedTable(data) {
    if (data.length === 0) return '<div class="empty-state"><h3>No hay facturas revisadas</h3></div>';
    return `
        <table>
            <thead><tr>
                <th>ID</th><th>Factura</th><th>Siniestro</th><th>Taller</th>
                <th>Motor</th><th>Riesgo</th><th>Hallazgos</th>
                <th>Sobrecobro</th><th>Estado</th><th>Acción</th>
            </tr></thead>
            <tbody>
                ${data.map(r => {
                    const bColor = r.status === 'approved' ? 'var(--accent-emerald)' : (r.status === 'rejected' ? 'var(--accent-rose)' : 'var(--accent-warning)');
                    return `
                    <tr class="clickable" onclick="location.hash='audit/${r.audit_id}'" style="border-left: 4px solid ${bColor}">
                        <td><span style="color:var(--text-muted);font-family:var(--font-mono)">#${r.audit_id}</span></td>
                        <td><strong>${r.invoice_number}</strong> ${renderTestBadge(r.is_test)}</td>
                        <td>${r.claim_number}</td>
                        <td>${r.workshop_name}</td>
                        <td>${renderEngineBadge(r.audit_engine)}</td>
                        <td>${renderRiskBadge(r.risk_score)}</td>
                        <td>
                            ${r.findings_count.critical > 0 ? `<span class="badge badge-critical">${r.findings_count.critical} crit</span> ` : ''}
                            ${r.findings_count.warning > 0 ? `<span class="badge badge-warning">${r.findings_count.warning} adv</span> ` : ''}
                            ${r.findings_count.critical === 0 && r.findings_count.warning === 0 ? '<span class="badge badge-success">Limpio</span>' : ''}
                        </td>
                        <td class="${r.total_overcharge > 0 ? 'price-over' : 'price-ok'}">$${(r.total_overcharge || 0).toFixed(2)}</td>
                        <td>${renderStatusBadge(r.status)}</td>
                        <td><button class="btn btn-ghost btn-sm">Ver</button></td>
                    </tr>
                `}).join("")}
            </tbody>
        </table>
    `;
}

export function setAuditSearch(val) {
    state.auditSearchTerm = val;
    renderAuditoriasView();
    const input = document.getElementById("audit-search");
    if (input) {
        input.focus();
        const len = input.value.length;
        input.setSelectionRange(len, len);
    }
}

export function setAuditTab(tab) {
    state.currentAuditTab = tab;
    renderAuditoriasView();
}

export function toggleAuditIncludeTest(checked) {
    state.includeTest = !!checked;
    loadAuditorias();
}
