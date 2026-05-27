import { apiFetch, apiPost } from "../api.js";
import { state } from "../state.js";
import { renderRiskBadge, renderStatusBadge, showToast } from "../utils.js";
import { renderClaimsScatter, renderDonut } from "../components/charts.js";

export async function loadDashboard() {
    const include = state.includeTest ? 1 : 0;
    const [d, audits, claimsDaily] = await Promise.all([
        apiFetch(`/dashboard?include_test=${include}`),
        apiFetch(`/audit-results?include_test=${include}`),
        apiFetch("/dashboard/claims-by-day?days=30"),
    ]);
    state.dashboardData = d;
    state.auditResults = audits || [];
    if (!d) return;
    const page = document.getElementById("page-dashboard");
    page.innerHTML = `
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;">
            <div>
                <h1>Dashboard de Auditoria <span class="pulse"></span></h1>
                <p>Vision general del sistema de auditoria agentica de facturacion</p>
            </div>
            <label style="display:flex;align-items:center;gap:8px;font-size:0.85rem;color:var(--text-muted);cursor:pointer;">
                <input type="checkbox" id="dash-include-test" ${state.includeTest ? "checked" : ""} onchange="toggleIncludeTest(this.checked)">
                Incluir facturas TEST (${d.test_count || 0})
            </label>
        </div>
        <div class="kpi-grid">
            <div class="kpi-card indigo">
                <div class="kpi-label">Facturas Auditadas</div>
                <div class="kpi-value indigo">${d.total_audited}</div>
                <div class="kpi-sub">de ${d.total_invoices} facturas totales</div>
            </div>
            <div class="kpi-card emerald">
                <div class="kpi-label">Monto Total Auditado</div>
                <div class="kpi-value emerald">$${d.invoice_total_sum.toLocaleString("es", {minimumFractionDigits: 2})}</div>
                <div class="kpi-sub">${d.total_claims} siniestros procesados</div>
            </div>
            <div class="kpi-card rose">
                <div class="kpi-label">Sobrecobros Detectados</div>
                <div class="kpi-value rose">$${d.total_overcharge.toLocaleString("es", {minimumFractionDigits: 2})}</div>
                <div class="kpi-sub">${d.savings_pct}% del monto total</div>
            </div>
            <div class="kpi-card amber">
                <div class="kpi-label">Facturas Escaladas</div>
                <div class="kpi-value amber">${d.escalated_count}</div>
                <div class="kpi-sub">requieren revision manual</div>
            </div>
        </div>
        <div class="grid-2" style="margin-bottom:24px;">
            <div class="card">
                <div class="card-header">
                    <h2>Siniestros Diarios (30 días)</h2>
                    <span style="color:var(--text-muted);font-size:0.85rem">Total: <strong>${claimsDaily ? claimsDaily.total : 0}</strong></span>
                </div>
                <div class="card-body">
                    <div id="claims-scatter" style="width:100%; overflow-x:auto;"></div>
                </div>
            </div>
            <div class="card">
                <div class="card-header"><h2>Distribucion de Hallazgos</h2></div>
                <div class="card-body" style="display:flex;flex-direction:row;align-items:center;justify-content:center;gap:32px;">
                    <div class="donut-chart" id="donut-chart"></div>
                    <div class="donut-legend" id="donut-legend"></div>
                </div>
            </div>
        </div>
        <div class="card">
            <div class="card-header">
                <h2>Ultimas Auditorias</h2>
                <a href="#auditorias" class="btn btn-ghost btn-sm">Ver todas</a>
            </div>
            <div class="card-body table-wrap">
                <table><thead><tr>
                    <th>Factura</th><th>Siniestro</th><th>Taller</th>
                    <th>Riesgo</th><th>Estado</th><th>Sobrecobro</th>
                </tr></thead><tbody id="tbody-recent"></tbody></table>
            </div>
        </div>
    `;
    renderRecentTable(state.auditResults);
    renderDonut("donut-chart", "donut-legend", d.by_severity);
    renderClaimsScatter("claims-scatter", claimsDaily);
}

function renderRecentTable(results) {
    const tbody = document.getElementById("tbody-recent");
    if (!tbody) return;
    tbody.innerHTML = results.slice(0, 20).map(r => `
        <tr class="clickable" onclick="location.hash='audit/${r.audit_id}'">
            <td><strong>${r.invoice_number}</strong>${r.is_test ? ' <span class="badge badge-warning" style="font-size:0.6rem;background:#94a3b8">TEST</span>' : ""}</td>
            <td>${r.claim_number}</td>
            <td>${r.workshop_name}</td>
            <td>${renderRiskBadge(r.risk_score)}</td>
            <td>${renderStatusBadge(r.status)}</td>
            <td class="${r.total_overcharge > 0 ? 'price-over' : 'price-ok'}">$${(r.total_overcharge || 0).toFixed(2)}</td>
        </tr>
    `).join("");
}

export async function runFullAudit() {
    const btn = document.getElementById("btn-run-audit");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Auditando...';
    }
    const result = await apiPost("/audit-all");
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Ejecutar Auditoria';
    }
    if (result) {
        showToast(`Auditoria completada: ${result.audited} facturas procesadas`, "success");
        loadDashboard();
    }
}

export function toggleIncludeTest(checked) {
    state.includeTest = !!checked;
    loadDashboard();
}
