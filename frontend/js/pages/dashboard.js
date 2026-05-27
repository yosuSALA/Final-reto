import { apiFetch, apiPost } from "../api.js";
import { state } from "../state.js";
import { renderRiskBadge, renderStatusBadge, showToast } from "../utils.js";
import { renderClaimsScatter, renderDonut } from "../components/charts.js";
import { getPermissions } from "../auth.js";

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
    const red = d.by_severity?.critical || 0;
    const yellow = d.by_severity?.warning || 0;
    const green = d.by_severity?.clean || 0;
    const totalCases = Math.max(red + yellow + green, 1);
    const redPct = Math.round((red / totalCases) * 100);
    const yellowPct = Math.round((yellow / totalCases) * 100);
    const greenPct = Math.round((green / totalCases) * 100);
    const reviewLoad = Math.min(100, Math.round(((red * 1.3 + yellow * 0.8) / totalCases) * 100));
    const targetLoad = 55;
    const monthlyProgress = Math.min(100, Math.round((d.total_audited / Math.max(d.total_invoices, 1)) * 100));

    const topWorkshops = summarizeWorkshops(state.auditResults);

    page.innerHTML = `
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;">
            <div>
                <h1>Detector de Posibles Fraudes en Siniestros <span class="pulse"></span></h1>
                <p>Priorizacion por riesgo para revision humana con trazabilidad de alertas</p>
            </div>
            <label style="display:flex;align-items:center;gap:8px;font-size:0.85rem;color:var(--text-muted);cursor:pointer;">
                <input type="checkbox" id="dash-include-test" ${state.includeTest ? "checked" : ""} onchange="toggleIncludeTest(this.checked)">
                Incluir facturas TEST (${d.test_count || 0})
            </label>
        </div>
        <div class="card" style="margin-bottom:14px;border-left:4px solid var(--accent-blue)">
            <div class="card-body" style="font-size:0.88rem;color:var(--text-secondary)">
                Este sistema genera alertas de posible fraude. No emite acusaciones automaticas ni decisiones legales; todo caso requiere revision humana.
            </div>
        </div>
        <div class="kpi-grid kpi-grid-hero">
            <div class="kpi-card indigo">
                <div class="kpi-label">Siniestros Analizados</div>
                <div class="kpi-value indigo">${d.total_audited}</div>
                <div class="kpi-sub">de ${d.total_invoices} casos cargados</div>
            </div>
            <div class="kpi-card emerald">
                <div class="kpi-label">Monto en Revision</div>
                <div class="kpi-value emerald">$${d.invoice_total_sum.toLocaleString("es", {minimumFractionDigits: 2})}</div>
                <div class="kpi-sub">${d.total_claims} siniestros procesados</div>
            </div>
            <div class="kpi-card rose">
                <div class="kpi-label">Riesgo Economico Detectado</div>
                <div class="kpi-value rose">$${d.total_overcharge.toLocaleString("es", {minimumFractionDigits: 2})}</div>
                <div class="kpi-sub">${d.savings_pct}% del monto total</div>
            </div>
            <div class="kpi-card amber">
                <div class="kpi-label">Casos Escalados</div>
                <div class="kpi-value amber">${d.escalated_count}</div>
                <div class="kpi-sub">requieren revision manual</div>
            </div>
        </div>
        <div class="dashboard-grid-pro" style="margin-bottom:20px;">
            <div class="card panel-wide">
                <div class="card-header"><h2>Control Mensual de Revision</h2></div>
                <div class="card-body">
                    <div class="meter-head">
                        <strong>${monthlyProgress}%</strong>
                        <span>Meta de cobertura: ${d.total_invoices} casos</span>
                    </div>
                    <div class="meter-track"><div class="meter-fill" style="width:${monthlyProgress}%"></div></div>
                    <div class="meter-foot">
                        <span>0</span>
                        <span>Meta: ${d.total_invoices}</span>
                    </div>
                </div>
            </div>

            <div class="card panel-sm">
                <div class="card-header"><h2>Carga de Riesgo</h2></div>
                <div class="card-body">
                    <div class="risk-gauge-lite">${reviewLoad}%</div>
                    <div class="kpi-sub">indice operativo de revisión</div>
                    <div class="kpi-sub">meta sugerida: ${targetLoad}%</div>
                </div>
            </div>

            <div class="card panel-sm">
                <div class="card-header"><h2>Semaforo de Casos</h2></div>
                <div class="card-body">
                    <div class="stack-row"><span>Rojo</span><strong>${red} (${redPct}%)</strong></div>
                    <div class="stack-track"><div class="stack-fill red" style="width:${redPct}%"></div></div>
                    <div class="stack-row"><span>Amarillo</span><strong>${yellow} (${yellowPct}%)</strong></div>
                    <div class="stack-track"><div class="stack-fill amber" style="width:${yellowPct}%"></div></div>
                    <div class="stack-row"><span>Verde</span><strong>${green} (${greenPct}%)</strong></div>
                    <div class="stack-track"><div class="stack-fill green" style="width:${greenPct}%"></div></div>
                </div>
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
        <div class="grid-2" style="margin-bottom:24px;">
            <div class="card">
                <div class="card-header"><h2>Accion Sugerida por Nivel</h2></div>
                <div class="card-body action-grid">
                    <div class="action-item green"><strong>Verde (0-40)</strong><span>Continuar flujo normal.</span></div>
                    <div class="action-item amber"><strong>Amarillo (41-75)</strong><span>Escalar a revisión documental antifraude.</span></div>
                    <div class="action-item red"><strong>Rojo (76-100)</strong><span>Escalar a revisión especializada de campo.</span></div>
                </div>
            </div>
            <div class="card">
                <div class="card-header"><h2>Proveedores con Mayor Concentracion</h2></div>
                <div class="card-body table-wrap">
                    <table>
                        <thead><tr><th>Proveedor</th><th>Casos</th><th>Peso</th></tr></thead>
                        <tbody>
                            ${topWorkshops.map((w) => `
                                <tr>
                                    <td>${w.name}</td>
                                    <td>${w.count}</td>
                                    <td>${w.pct}%</td>
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
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
    const perms = getPermissions();
    if (!perms.canRunAuditAll) {
        showToast("Tu perfil no tiene permiso para auditoría masiva", "warning");
        return;
    }
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

function summarizeWorkshops(audits) {
    if (!audits || audits.length === 0) {
        return [{ name: "Sin datos", count: 0, pct: 0 }];
    }
    const counts = {};
    audits.forEach((a) => {
        const name = a.workshop_name || "Sin proveedor";
        counts[name] = (counts[name] || 0) + 1;
    });
    const total = audits.length;
    return Object.entries(counts)
        .map(([name, count]) => ({ name, count, pct: Math.round((count / total) * 100) }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 5);
}
