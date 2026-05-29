import { apiFetch, apiPost } from "../api.js";
import { state } from "../state.js";
import { renderRiskBadge, renderStatusBadge, showToast } from "../utils.js";
import { renderClaimsScatter, renderDonut } from "../components/charts.js";
import { getPermissions, getRoleLabel } from "../auth.js";

// ── Entry point ────────────────────────────────────────

export async function loadDashboard() {
    const page = document.getElementById("page-dashboard");
    const role = state.currentRole || "analista";
    const perms = getPermissions();

    page.innerHTML = `<div class="intel-loading"><div class="intel-spinner"></div><p>Cargando plataforma de inteligencia...</p></div>`;

    try {
        switch (role) {
            case "demo_jurado":  await renderDemoJurado(page, perms); break;
            case "analista":     await renderAnalista(page, perms); break;
            case "antifraude":   await renderAntifraude(page, perms); break;
            case "jefatura":     await renderJefatura(page, perms); break;
            case "auditoria":    await renderAuditoria(page, perms); break;
            case "operaciones":  await renderActionFlowPanel(page, perms); break;
            case "costos":       await renderActionFlowPanel(page, perms); break;
            case "contabilidad": await renderActionFlowPanel(page, perms); break;
            case "legal":        await renderLegal(page, perms); break;
            default:             await renderActionFlowPanel(page, perms);
        }
    } catch (e) {
        console.error("Dashboard error:", e);
        page.innerHTML = `<div class="intel-error"><h3>Error cargando la plataforma</h3><p>${e.message}</p><button class="btn btn-primary" onclick="loadDashboard()">Reintentar</button></div>`;
    }
}

export async function loadAuditPanel(forceGuide = false) {
    const page = document.getElementById("page-audit-panel") || document.getElementById("page-dashboard");
    if (!page) return;
    page.innerHTML = `<div class="intel-loading"><div class="intel-spinner"></div><p>Cargando panel de auditoría...</p></div>`;
    await renderActionFlowPanel(page, getPermissions(), { forceGuide });
}

export async function runFullAudit() {
    const perms = getPermissions();
    if (!perms.canRunAuditAll) {
        showToast("Tu rol no tiene permiso para auditoría masiva", "warning");
        return;
    }
    const btn = document.getElementById("btn-run-audit");
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Auditando con IA...'; }
    const result = await apiPost("/audit-ai-all");
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Auditar con IA';
    }
    if (result) {
        showToast(`Auditoría IA completada: ${result.audited} facturas procesadas`, "success");
        loadDashboard();
    }
}

export function toggleIncludeTest(checked) {
    state.includeTest = !!checked;
    loadDashboard();
}

// ── Shared: Role header ────────────────────────────────

function roleHeader(role, title, subtitle) {
    const info = getRoleLabel(role);
    return `
    <div class="intel-header">
        <div class="intel-header-left">
            <div class="intel-role-badge" style="--role-color:${info.color}">
                <span class="intel-role-icon">${info.icon}</span>
                <span class="intel-role-label">${info.label}</span>
            </div>
            <div>
                <h1 class="intel-title">${title}</h1>
                <p class="intel-subtitle">${subtitle}</p>
            </div>
        </div>
        <div class="intel-header-right">
            <div class="intel-live-indicator"><span class="pulse"></span>Sistema activo</div>
            <span class="intel-timestamp">Actualizado: ${new Date().toLocaleTimeString("es-EC")}</span>
        </div>
    </div>`;
}

// ── Shared: DeepSeek panel ──────────────────────────────

function deepseekPanel(id, type, label, context) {
    const encoded = encodeURIComponent(JSON.stringify(context));
    return `
    <div class="intel-ai-panel" id="ai-panel-${id}">
        <div class="intel-ai-header">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
            <span>Análisis IA (opcional)</span>
        </div>
        <div class="intel-ai-body" id="ai-body-${id}">
            <p class="intel-ai-placeholder">Haz clic en el botón para generar un análisis con IA. La plataforma funciona completamente sin IA.</p>
            <button class="btn btn-ghost btn-sm" onclick="triggerDeepSeekInsight('${id}','${type}','${encoded}')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/></svg>
                ${label}
            </button>
        </div>
    </div>`;
}

// ── ROLE: demo_jurado ──────────────────────────────────

async function renderDemoJurado(page, perms) {
    const [portfolio, fraud, dash, claimsDaily] = await Promise.all([
        apiFetch("/intelligence/portfolio"),
        apiFetch("/intelligence/fraud"),
        apiFetch("/dashboard?include_test=0"),
        apiFetch("/dashboard/claims-by-day?days=30"),
    ]);

    const p = portfolio || {};
    const f = fraud || {};
    const d = dash || {};

    const kpiContext = {
        period: new Date().toISOString().slice(0, 7),
        total_claims: p.total_claims, open_claims: p.open_claims,
        paid_amount: p.total_paid, reserved_amount: p.total_reserved,
        average_fraud_score: p.avg_fraud_score, fraud_alerts: p.fraud_alerts,
        branch_summary: p.branch_ranking?.slice(0, 3),
        trend_summary: p.monthly_trend?.slice(-3),
    };

    page.innerHTML = `
        ${roleHeader("demo_jurado", "Centro de Comando Ejecutivo", "Visión integral de la plataforma de inteligencia de seguros")}

        <div class="intel-kpi-wall">
            ${kpiCard("Siniestros Totales", p.total_claims ?? d.total_claims ?? 0, "", "indigo", iconClaim())}
            ${kpiCard("Siniestros Abiertos", p.open_claims ?? 0, "en proceso", "blue", iconOpen())}
            ${kpiCard("Total Pagado", "$" + fmt(p.total_paid ?? 0), "desembolsado", "emerald", iconPay())}
            ${kpiCard("Total Reservado", "$" + fmt(p.total_reserved ?? 0), "estimado", "cyan", iconReserve())}
            ${kpiCard("Alertas de Fraude", p.fraud_alerts ?? d.escalated_count ?? 0, "riesgo alto", "rose", iconAlert())}
            ${kpiCard("Pólizas Activas", p.active_policies ?? 0, "vigentes", "violet", iconPolicy())}
            ${kpiCard("Costo Prom. Siniestro", "$" + fmt(p.avg_claim_cost ?? 0), "por caso", "amber", iconCost())}
            ${kpiCard("Score Fraude Prom.", (p.avg_fraud_score ?? 0).toFixed(1), "/ 100", scoreColor(p.avg_fraud_score ?? 0), iconScore())}
        </div>

        <div class="intel-grid-3-2">
            <div class="card intel-card-wide">
                <div class="card-header">
                    <h2>Tendencia Mensual de Siniestros</h2>
                    <span class="intel-period">Últimos 6 meses</span>
                </div>
                <div class="card-body">
                    <div id="claims-scatter" style="width:100%;overflow-x:auto;"></div>
                </div>
            </div>
            <div class="card">
                <div class="card-header"><h2>Mapa de Riesgo por Clasificación</h2></div>
                <div class="card-body">
                    ${renderFraudHeatmap(f.score_distribution)}
                    <div style="margin-top:16px;">
                        ${renderScoreDistBar(f.score_distribution)}
                    </div>
                </div>
            </div>
        </div>

        <div class="intel-grid-2">
            <div class="card">
                <div class="card-header">
                    <h2>Investigaciones Destacadas</h2>
                    <span class="badge badge-danger">${f.total_high_risk ?? 0} alto riesgo</span>
                </div>
                <div class="card-body table-wrap">
                    <table>
                        <thead><tr><th>Siniestro</th><th>Score</th><th>Monto</th><th>Estado</th><th></th></tr></thead>
                        <tbody>
                            ${(f.high_risk_claims || []).slice(0, 8).map(c => `
                            <tr class="clickable" onclick="location.hash='claim/${c.claim_id}'">
                                <td><strong>${c.claim_number}</strong><br><small style="color:var(--text-muted)">${c.sucursal}</small></td>
                                <td>${renderFraudScoreBadge(c.fraud_score, c.fraud_classification)}</td>
                                <td>$${fmt(c.amount_claimed)}</td>
                                <td>${renderStatusBadge(c.audit_status)}</td>
                                <td><span class="intel-arrow">→</span></td>
                            </tr>`).join("")}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="card">
                <div class="card-header"><h2>Ranking de Sucursales</h2></div>
                <div class="card-body">
                    ${renderBranchRanking(p.branch_ranking)}
                </div>
            </div>
        </div>

        <div class="intel-grid-2">
            <div class="card">
                <div class="card-header"><h2>Distribución por Estado</h2></div>
                <div class="card-body">
                    ${renderStateDistribution(p.claims_by_state)}
                </div>
            </div>
            ${deepseekPanel("jurado-portfolio", "executive_briefing", "Generar Briefing Ejecutivo IA", kpiContext)}
        </div>
    `;

    renderClaimsScatter("claims-scatter", claimsDaily);
}

// ── ROLE: analista ─────────────────────────────────────

async function renderAnalista(page, perms) {
    const [ops, dash] = await Promise.all([
        apiFetch("/intelligence/operations"),
        apiFetch("/dashboard?include_test=0"),
    ]);

    const o = ops || {};
    const d = dash || {};

    page.innerHTML = `
        ${roleHeader("analista", "Centro de Operaciones", "Cola de trabajo, SLA y control de expedientes")}

        <div class="intel-kpi-wall intel-kpi-4">
            ${kpiCard("Cola Pendiente", o.audit_queue?.pending ?? 0, "sin auditar", "amber", iconQueue())}
            ${kpiCard("En Proceso", o.audit_queue?.in_progress ?? 0, "en revisión", "blue", iconProcess())}
            ${kpiCard("Escalados", o.audit_queue?.escalated ?? 0, "requieren atención", "rose", iconAlert())}
            ${kpiCard("Completados", o.audit_queue?.completed ?? 0, "procesados", "emerald", iconCheck())}
        </div>

        <div class="intel-grid-3-2">
            <div class="card intel-card-wide">
                <div class="card-header">
                    <h2>Cola de Siniestros</h2>
                    <div class="intel-header-actions">
                        <a href="#siniestros" class="btn btn-ghost btn-sm">Ver todos</a>
                        <a href="#auditorias" class="btn btn-primary btn-sm">Ir a Auditorías</a>
                    </div>
                </div>
                <div class="card-body table-wrap">
                    <table>
                        <thead><tr>
                            <th>Siniestro</th><th>Ramo</th><th>Monto</th>
                            <th>Días SLA</th><th>Docs</th><th>Auditoría</th><th></th>
                        </tr></thead>
                        <tbody>
                            ${(o.claims_queue || []).slice(0, 12).map(c => `
                            <tr class="clickable" onclick="location.hash='claim/${c.claim_id}'">
                                <td>
                                    <strong>${c.claim_number}</strong>
                                    <br><small style="color:var(--text-muted)">${c.sucursal}</small>
                                </td>
                                <td><span class="badge badge-info">${c.ramo}</span></td>
                                <td>$${fmt(c.amount_claimed)}</td>
                                <td>${renderSlaBadge(c.dias_reporte)}</td>
                                <td>${c.docs_complete ? '<span class="badge badge-success">OK</span>' : '<span class="badge badge-warning">Falta</span>'}</td>
                                <td>${renderStatusBadge(c.audit_status)}</td>
                                <td><span class="intel-arrow">→</span></td>
                            </tr>`).join("")}
                        </tbody>
                    </table>
                </div>
            </div>

            <div>
                <div class="card" style="margin-bottom:16px;">
                    <div class="card-header"><h2>Monitor SLA</h2></div>
                    <div class="card-body">
                        ${renderSlaMonitor(o.sla)}
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>Documentación</h2></div>
                    <div class="card-body">
                        ${renderDocMonitor(o.documentation)}
                        <div style="margin-top:16px;">
                            <a href="#upload" class="btn btn-ghost btn-sm" style="width:100%">Subir Documentos</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="intel-grid-2">
            <div class="card">
                <div class="card-header"><h2>Siniestros por Estado</h2></div>
                <div class="card-body">
                    ${renderStateDistribution(o.by_state)}
                </div>
            </div>
            <div class="card">
                <div class="card-header"><h2>Acciones Rápidas</h2></div>
                <div class="card-body action-grid">
                    <a href="#auditorias" class="action-item blue" style="text-decoration:none">
                        <strong>Revisar Pendientes</strong>
                        <span>${o.audit_queue?.pending ?? 0} facturas esperan auditoría</span>
                    </a>
                    <a href="#upload" class="action-item amber" style="text-decoration:none">
                        <strong>Cargar PDF</strong>
                        <span>Subir nuevas facturas para auditar</span>
                    </a>
                    <div class="action-item ${(o.sla?.breach ?? 0) > 0 ? 'red' : 'green'}">
                        <strong>SLA Breaches</strong>
                        <span>${o.sla?.breach ?? 0} siniestros fuera de plazo</span>
                    </div>
                    <div class="action-item ${(o.documentation?.missing ?? 0) > 0 ? 'amber' : 'green'}">
                        <strong>Documentos Faltantes</strong>
                        <span>${o.documentation?.missing ?? 0} expedientes incompletos</span>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ── ROLE: antifraude ───────────────────────────────────

async function renderAntifraude(page, perms) {
    const [fraud, portfolio] = await Promise.all([
        apiFetch("/intelligence/fraud"),
        apiFetch("/intelligence/portfolio"),
    ]);

    const f = fraud || {};
    const p = portfolio || {};

    const fraudContext = {
        total_high_risk: f.total_high_risk,
        total_medium_risk: f.total_medium_risk,
        score_distribution: f.score_distribution,
        top_indicators: f.top_indicators?.slice(0, 5),
        shared_beneficiaries: f.shared_beneficiaries?.slice(0, 3),
        frequent_claimants: f.frequent_claimants?.slice(0, 3),
    };

    page.innerHTML = `
        ${roleHeader("antifraude", "Centro de Inteligencia Anti-Fraude", "Investigación de patrones sospechosos y análisis de riesgo")}

        <div class="intel-kpi-wall intel-kpi-4">
            ${kpiCard("Alto Riesgo", f.total_high_risk ?? 0, "score ≥ 75", "rose", iconAlert())}
            ${kpiCard("Riesgo Medio", f.total_medium_risk ?? 0, "score 40-74", "amber", iconWarn())}
            ${kpiCard("Beneficiarios Compartidos", (f.shared_beneficiaries || []).length, "en múltiples claims", "violet", iconNetwork())}
            ${kpiCard("Reclamantes Frecuentes", (f.frequent_claimants || []).length, "más de 1 claim", "blue", iconRepeat())}
        </div>

        <div class="intel-grid-3-2">
            <div class="card intel-card-wide">
                <div class="card-header">
                    <h2>Cola de Alto Riesgo</h2>
                    <div class="intel-header-actions">
                        <span class="badge badge-danger">${f.total_high_risk ?? 0} casos críticos</span>
                    </div>
                </div>
                <div class="card-body table-wrap">
                    <table>
                        <thead><tr>
                            <th>Siniestro</th><th>Score</th><th>Indicadores</th>
                            <th>Monto</th><th>Beneficiario</th><th>Estado</th><th></th>
                        </tr></thead>
                        <tbody>
                            ${(f.high_risk_claims || []).slice(0, 12).map(c => `
                            <tr class="clickable" onclick="location.hash='claim/${c.claim_id}'" style="${c.fraud_score >= 75 ? 'border-left:3px solid #ef4444' : ''}">
                                <td>
                                    <strong>${c.claim_number}</strong>
                                    <br><small style="color:var(--text-muted)">${c.sucursal}</small>
                                </td>
                                <td>${renderFraudScoreBadge(c.fraud_score, c.fraud_classification)}</td>
                                <td>
                                    <div class="intel-indicators">
                                        ${(c.indicators || []).slice(0, 2).map(i => `<span class="intel-indicator-tag">${truncate(labelFromPayload(i), 20)}</span>`).join("")}
                                    </div>
                                </td>
                                <td>$${fmt(c.amount_claimed)}</td>
                                <td><small>${c.beneficiary || "—"}</small></td>
                                <td>${renderStatusBadge(c.audit_status)}</td>
                                <td><span class="intel-arrow">→</span></td>
                            </tr>`).join("")}
                        </tbody>
                    </table>
                </div>
            </div>

            <div>
                <div class="card" style="margin-bottom:16px;">
                    <div class="card-header"><h2>Distribución de Riesgo</h2></div>
                    <div class="card-body">
                        ${renderFraudHeatmap(f.score_distribution)}
                        ${renderScoreDistBar(f.score_distribution)}
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>Top Indicadores de Fraude</h2></div>
                    <div class="card-body">
                        ${renderIndicatorBars(f.top_indicators)}
                    </div>
                </div>
            </div>
        </div>

        <div class="intel-grid-2">
            <div class="card">
                <div class="card-header">
                    <h2>Red de Beneficiarios Compartidos</h2>
                    <span class="badge badge-warning">${(f.shared_beneficiaries || []).length} nodos</span>
                </div>
                <div class="card-body">
                    ${renderFraudNetwork(f.shared_beneficiaries, f.frequent_claimants)}
                </div>
            </div>
            ${deepseekPanel("fraude-analysis", "explain_anomaly", "Analizar Patrones con IA", fraudContext)}
        </div>
    `;
}

// ── ROLE: jefatura ─────────────────────────────────────

async function renderJefatura(page, perms) {
    const [portfolio, fraud] = await Promise.all([
        apiFetch("/intelligence/portfolio"),
        apiFetch("/intelligence/fraud"),
    ]);

    const p = portfolio || {};
    const f = fraud || {};

    const portfolioContext = {
        period: new Date().toISOString().slice(0, 7),
        total_claims: p.total_claims, open_claims: p.open_claims,
        paid_amount: p.total_paid, reserved_amount: p.total_reserved,
        average_fraud_score: p.avg_fraud_score, fraud_alerts: p.fraud_alerts,
        branch_summary: p.branch_ranking?.slice(0, 5),
        trend_summary: p.monthly_trend,
        escalated: p.escalated,
    };

    page.innerHTML = `
        ${roleHeader("jefatura", "Centro de Inteligencia de Portafolio", "KPIs ejecutivos, exposición financiera y control de sucursales")}

        <div class="intel-kpi-wall intel-kpi-4">
            ${kpiCard("Exposición Total", "$" + fmt(p.total_claimed ?? 0), "monto reclamado", "indigo", iconClaim())}
            ${kpiCard("Pagos Realizados", "$" + fmt(p.total_paid ?? 0), "desembolsado", "emerald", iconPay())}
            ${kpiCard("Reservas Activas", "$" + fmt(p.total_reserved ?? 0), "estimado vigente", "cyan", iconReserve())}
            ${kpiCard("Sobrecostos Detectados", "$" + fmt(p.total_overcharge ?? 0), "fraude/error", "rose", iconAlert())}
        </div>

        <div class="intel-grid-3-2">
            <div class="card intel-card-wide">
                <div class="card-header">
                    <h2>Ranking de Sucursales</h2>
                    <span class="intel-period">${(p.branch_ranking || []).length} sucursales</span>
                </div>
                <div class="card-body">
                    ${renderBranchRankingFull(p.branch_ranking)}
                </div>
            </div>

            <div>
                <div class="card" style="margin-bottom:16px;">
                    <div class="card-header"><h2>Distribución por Estado</h2></div>
                    <div class="card-body">
                        ${renderStateDistribution(p.claims_by_state)}
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>Indicadores de Riesgo</h2></div>
                    <div class="card-body">
                        ${kpiMini("Score Fraude Prom.", (p.avg_fraud_score ?? 0).toFixed(1), scoreColor(p.avg_fraud_score ?? 0))}
                        ${kpiMini("Alertas Fraude", p.fraud_alerts ?? 0, "rose")}
                        ${kpiMini("Casos Escalados", p.escalated ?? 0, "amber")}
                        ${kpiMini("Siniestros Abiertos", p.open_claims ?? 0, "blue")}
                    </div>
                </div>
            </div>
        </div>

        <div class="intel-grid-2">
            <div class="card">
                <div class="card-header"><h2>Tendencia Mensual</h2></div>
                <div class="card-body">
                    ${renderMonthlyTrend(p.monthly_trend)}
                </div>
            </div>
            ${deepseekPanel("jefatura-portfolio", "portfolio_summary", "Resumen Ejecutivo IA", portfolioContext)}
        </div>

        <div class="card" style="margin-top:16px;">
            <div class="card-header">
                <h2>Acciones Estratégicas</h2>
            </div>
            <div class="card-body action-grid">
                <a href="#tarifario" class="action-item blue" style="text-decoration:none">
                    <strong>Gestionar Tarifario</strong>
                    <span>Actualizar precios y coberturas autorizadas</span>
                </a>
                <div class="action-item ${(p.fraud_alerts ?? 0) > 5 ? 'red' : 'green'}">
                    <strong>Alertas de Fraude</strong>
                    <span>${p.fraud_alerts ?? 0} siniestros en zona de riesgo alto</span>
                </div>
                <div class="action-item ${(p.escalated ?? 0) > 0 ? 'amber' : 'green'}">
                    <strong>Casos Escalados</strong>
                    <span>${p.escalated ?? 0} requieren decisión ejecutiva</span>
                </div>
                <div class="action-item ${(p.open_claims ?? 0) > 20 ? 'amber' : 'green'}">
                    <strong>Flujo Operativo</strong>
                    <span>${p.open_claims ?? 0} siniestros en proceso activo</span>
                </div>
            </div>
        </div>
    `;
}

// ── ROLE: legal ────────────────────────────────────────

async function renderLegal(page, perms) {
    const [notifications, claims, tariffs] = await Promise.all([
        apiFetch("/legal/notifications"),
        apiFetch("/claims"),
        apiFetch("/tariffs"),
    ]);

    const notif = notifications || [];
    const allClaims = claims || [];
    const allTariffs = tariffs || [];

    page.innerHTML = `
        ${roleHeader("legal", "Bandeja Legal", "Tarifarios vigentes, listado de siniestros y notificaciones de Jefatura")}

        <div class="intel-kpi-wall intel-kpi-4">
            ${kpiCard("Notificaciones de Jefatura", notif.length, notif.length > 0 ? "requieren revisión urgente" : "sin pendientes", notif.length > 0 ? "rose" : "emerald", iconAlert())}
            ${kpiCard("Siniestros Registrados", allClaims.length, "total en cartera", "indigo", iconClaim())}
            ${kpiCard("Items del Tarifario", allTariffs.length, "vigentes", "blue", iconReserve())}
            ${kpiCard("Alta Urgencia", notif.filter(n => (n.urgency || "") === "alta").length, "casos derivados", "amber", iconWarn())}
        </div>

        <div class="card" style="margin-bottom:16px;border-left:4px solid ${notif.length > 0 ? '#ef4444' : '#10b981'};">
            <div class="card-header">
                <h2>📨 Notificaciones de Jefatura ${notif.length > 0 ? `<span class="badge badge-danger" style="margin-left:8px;">URGENTE</span>` : ""}</h2>
                <span style="color:var(--text-muted);font-size:0.85rem;">Siniestros escalados derivados al área Legal</span>
            </div>
            <div class="card-body table-wrap">
                ${notif.length === 0 ? '<div class="empty-state"><h3>Sin notificaciones</h3><p>Jefatura no ha derivado casos al área Legal.</p></div>' : `
                <table>
                    <thead><tr>
                        <th>Siniestro</th><th>Factura</th><th>Asegurado</th>
                        <th>Monto Reclamado</th><th>Sobrecobro</th>
                        <th>Riesgo</th><th>Derivado</th><th>Urgencia</th>
                    </tr></thead>
                    <tbody>
                        ${notif.map(n => `
                        <tr class="clickable" onclick="location.hash='claim/${n.claim_id}'" style="border-left:3px solid #ef4444;">
                            <td><strong>${n.claim_number}</strong><br><small style="color:var(--text-muted)">${n.claim_type || "—"}</small></td>
                            <td><span style="font-family:var(--font-mono);font-size:0.85rem;">${n.invoice_number || "—"}</span></td>
                            <td>${n.insured_id || "—"}<br><small style="color:var(--text-muted);font-family:var(--font-mono);">${n.policy_number || ""}</small></td>
                            <td>$${fmt(n.amount_claimed ?? n.invoice_total ?? 0)}</td>
                            <td style="color:var(--accent-rose);font-weight:600;">$${fmt(n.total_overcharge ?? 0)}</td>
                            <td>${n.risk_score != null ? renderFraudScoreBadge(n.risk_score, n.risk_score >= 70 ? "Alto" : n.risk_score >= 30 ? "Medio" : "Bajo") : "—"}</td>
                            <td><small>${n.received_at ? new Date(n.received_at).toLocaleString("es-EC", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—"}</small></td>
                            <td><span class="badge badge-danger">${(n.urgency || "alta").toUpperCase()}</span></td>
                        </tr>`).join("")}
                    </tbody>
                </table>`}
            </div>
        </div>

        <div class="intel-grid-2">
            <div class="card">
                <div class="card-header">
                    <h2>📋 Siniestros (sólo lectura)</h2>
                    <span class="intel-period">${allClaims.length} registros</span>
                </div>
                <div class="card-body table-wrap" style="max-height:520px;overflow-y:auto;">
                    <table>
                        <thead><tr><th>Número</th><th>Ramo</th><th>Asegurado</th><th>Estado</th></tr></thead>
                        <tbody>
                            ${allClaims.slice(0, 50).map(c => `
                            <tr class="clickable" onclick="location.hash='claim/${c.id}'">
                                <td><strong>${c.claim_number}</strong></td>
                                <td><small>${(c.claim_type || "").replace(/_/g, " ")}</small></td>
                                <td><small>${c.insured_name || "—"}</small></td>
                                <td>${renderStatusBadge(c.audit_status || c.estado || "pending")}</td>
                            </tr>`).join("")}
                        </tbody>
                    </table>
                    ${allClaims.length > 50 ? `<div style="padding:12px;text-align:center;color:var(--text-muted);font-size:0.85rem;">Mostrando primeros 50 — usa la pestaña "Siniestros" para ver todos.</div>` : ""}
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <h2>💲 Tarifario Vigente</h2>
                    <span class="intel-period">${allTariffs.length} items</span>
                </div>
                <div class="card-body table-wrap" style="max-height:520px;overflow-y:auto;">
                    <table>
                        <thead><tr><th>Código</th><th>Descripción</th><th>Categoría</th><th>Precio Máx.</th></tr></thead>
                        <tbody>
                            ${allTariffs.slice(0, 80).map(t => `
                            <tr>
                                <td><span style="font-family:var(--font-mono);color:var(--accent-indigo);font-size:0.85rem;">${t.code}</span></td>
                                <td><small>${t.description}</small></td>
                                <td><span class="cat-tag cat-${t.category || 'general'}">${t.category || 'general'}</span></td>
                                <td><strong>$${(t.max_price ?? 0).toFixed(2)}</strong></td>
                            </tr>`).join("")}
                        </tbody>
                    </table>
                    ${allTariffs.length > 80 ? `<div style="padding:12px;text-align:center;color:var(--text-muted);font-size:0.85rem;">Mostrando primeros 80 — usa la pestaña "Tarifario" para ver todos.</div>` : ""}
                </div>
            </div>
        </div>
    `;
}

// ── ROLE: auditoria ────────────────────────────────────

async function renderAuditoria(page, perms) {
    const [coverage, dash] = await Promise.all([
        apiFetch("/intelligence/audit-coverage"),
        apiFetch("/dashboard?include_test=0"),
    ]);

    const c = coverage || {};
    const d = dash || {};

    page.innerHTML = `
        ${roleHeader("auditoria", "Centro de Auditoría y Cumplimiento", "Cobertura de auditorías, trazabilidad y métricas de compliance")}

        <div class="intel-kpi-wall intel-kpi-4">
            ${kpiCard("Cobertura de Auditoría", (c.coverage_pct ?? 0) + "%", `${c.audited_claims ?? 0} / ${c.total_claims ?? 0}`, coverageColor(c.coverage_pct ?? 0), iconCheck())}
            ${kpiCard("Score de Compliance", (c.compliance_score ?? 0) + "%", "índice de cumplimiento", coverageColor(c.compliance_score ?? 0), iconScore())}
            ${kpiCard("Hallazgos Críticos", c.critical_findings ?? 0, "violaciones severas", "rose", iconAlert())}
            ${kpiCard("Revisiones Manuales", c.reviewed ?? 0, "verificadas por humano", "emerald", iconProcess())}
        </div>

        <div class="intel-grid-3-2">
            <div class="card intel-card-wide">
                <div class="card-header">
                    <h2>Rastro de Auditoría</h2>
                    <span class="intel-period">Últimas ${(c.recent_audit_trail || []).length} acciones</span>
                </div>
                <div class="card-body table-wrap">
                    <table>
                        <thead><tr>
                            <th>Auditoría</th><th>Siniestro</th><th>Motor</th>
                            <th>Score</th><th>Estado</th><th>Revisor</th><th>Fecha</th>
                        </tr></thead>
                        <tbody>
                            ${(c.recent_audit_trail || []).map(a => `
                            <tr class="clickable" onclick="location.hash='audit/${a.audit_id}'">
                                <td><strong>#${a.audit_id}</strong></td>
                                <td>SIN-${a.claim_id}</td>
                                <td>
                                    <span class="badge ${a.engine === 'rules' ? 'badge-warning' : 'badge-info'}">${a.engine === 'rules' ? 'rules' : 'deepseek'}</span>
                                </td>
                                <td>${renderRiskBadge(a.risk_score)}</td>
                                <td>${renderStatusBadge(a.status)}</td>
                                <td><small>${a.reviewed_by || "—"}</small></td>
                                <td><small>${fmtDate(a.audited_at)}</small></td>
                            </tr>`).join("")}
                        </tbody>
                    </table>
                </div>
            </div>

            <div>
                <div class="card" style="margin-bottom:16px;">
                    <div class="card-header"><h2>Estado de Auditorías</h2></div>
                    <div class="card-body">
                        ${renderStatusBreakdown(c.by_status)}
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h2>Motor de Auditoría</h2></div>
                    <div class="card-body">
                        ${renderEngineBreakdown(c.by_engine)}
                    </div>
                </div>
            </div>
        </div>

        <div class="intel-grid-2">
            <div class="card">
                <div class="card-header"><h2>Métricas de Compliance</h2></div>
                <div class="card-body">
                    ${renderComplianceMetrics(c)}
                </div>
            </div>
            <div class="card">
                <div class="card-header"><h2>Acciones de Auditoría</h2></div>
                <div class="card-body action-grid">
                    <a href="#auditorias" class="action-item blue" style="text-decoration:none">
                        <strong>Cola de Revisión</strong>
                        <span>${c.not_reviewed ?? 0} auditorías sin revisión humana</span>
                    </a>
                    <div class="action-item ${(c.critical_findings ?? 0) > 0 ? 'red' : 'green'}">
                        <strong>Hallazgos Críticos</strong>
                        <span>${c.critical_findings ?? 0} violaciones requieren acción</span>
                    </div>
                    <div class="action-item ${(c.coverage_pct ?? 0) < 80 ? 'amber' : 'green'}">
                        <strong>Cobertura de Auditoría</strong>
                        <span>${c.coverage_pct ?? 0}% de siniestros auditados</span>
                    </div>
                    <div class="action-item indigo">
                        <strong>Decisiones Manuales</strong>
                        <span>${c.overrides ?? 0} resoluciones registradas</span>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ── Shared Chart Components ────────────────────────────

function renderFraudHeatmap(dist) {
    if (!dist) return '<div class="intel-empty">Sin datos</div>';
    const total = (dist.rojo || 0) + (dist.amarillo || 0) + (dist.verde || 0);
    if (total === 0) return '<div class="intel-empty">Sin datos de clasificación</div>';
    return `
    <div class="intel-heatmap">
        <div class="intel-heatmap-cell rojo" style="flex:${Math.max(dist.rojo || 0, 0.5)}">
            <span class="intel-heatmap-val">${dist.rojo || 0}</span>
            <span class="intel-heatmap-lbl">Alto Riesgo</span>
        </div>
        <div class="intel-heatmap-cell amarillo" style="flex:${Math.max(dist.amarillo || 0, 0.5)}">
            <span class="intel-heatmap-val">${dist.amarillo || 0}</span>
            <span class="intel-heatmap-lbl">Medio Riesgo</span>
        </div>
        <div class="intel-heatmap-cell verde" style="flex:${Math.max(dist.verde || 0, 0.5)}">
            <span class="intel-heatmap-val">${dist.verde || 0}</span>
            <span class="intel-heatmap-lbl">Bajo Riesgo</span>
        </div>
    </div>`;
}

function renderScoreDistBar(dist) {
    if (!dist) return "";
    const total = Math.max((dist.rojo || 0) + (dist.amarillo || 0) + (dist.verde || 0), 1);
    const rp = Math.round((dist.rojo || 0) / total * 100);
    const ap = Math.round((dist.amarillo || 0) / total * 100);
    const gp = 100 - rp - ap;
    return `
    <div class="intel-score-dist">
        <div class="intel-dist-bar">
            <div style="width:${rp}%;background:#ef4444;" title="Alto riesgo: ${rp}%"></div>
            <div style="width:${ap}%;background:#f59e0b;" title="Medio riesgo: ${ap}%"></div>
            <div style="width:${gp}%;background:#10b981;" title="Bajo riesgo: ${gp}%"></div>
        </div>
        <div class="intel-dist-labels">
            <span style="color:#ef4444">${rp}% alto</span>
            <span style="color:#f59e0b">${ap}% medio</span>
            <span style="color:#10b981">${gp}% bajo</span>
        </div>
    </div>`;
}

function renderBranchRanking(branches) {
    if (!branches || branches.length === 0) return '<div class="intel-empty">Sin datos</div>';
    const maxClaims = Math.max(...branches.map(b => b.claims), 1);
    return branches.slice(0, 6).map((b, i) => `
    <div class="intel-branch-row">
        <span class="intel-branch-rank">${i + 1}</span>
        <div class="intel-branch-info">
            <span class="intel-branch-name">${b.branch}</span>
            <div class="intel-branch-bar-track">
                <div class="intel-branch-bar" style="width:${Math.round(b.claims / maxClaims * 100)}%"></div>
            </div>
        </div>
        <div class="intel-branch-stats">
            <span>${b.claims} casos</span>
            ${b.fraud_alerts > 0 ? `<span class="badge badge-danger">${b.fraud_alerts} alertas</span>` : ""}
        </div>
    </div>`).join("");
}

function renderBranchRankingFull(branches) {
    if (!branches || branches.length === 0) return '<div class="intel-empty">Sin datos</div>';
    return `
    <table>
        <thead><tr><th>#</th><th>Sucursal</th><th>Siniestros</th><th>Pagado</th><th>Alertas</th><th>Score Prom.</th></tr></thead>
        <tbody>
            ${branches.slice(0, 10).map((b, i) => `
            <tr>
                <td><strong>${i + 1}</strong></td>
                <td>${b.branch}</td>
                <td>${b.claims}</td>
                <td>$${fmt(b.paid)}</td>
                <td>${b.fraud_alerts > 0 ? `<span class="badge badge-danger">${b.fraud_alerts}</span>` : '<span class="badge badge-success">0</span>'}</td>
                <td>${renderRiskBadge(b.avg_score)}</td>
            </tr>`).join("")}
        </tbody>
    </table>`;
}

function renderStateDistribution(byState) {
    if (!byState || Object.keys(byState).length === 0) return '<div class="intel-empty">Sin datos</div>';
    const total = Object.values(byState).reduce((a, b) => a + b, 0);
    const stateColors = {
        "Reserva": "#0ea5e9", "Pago Total": "#10b981", "Pago Parcial": "#6366f1",
        "Anticipo": "#f59e0b", "Negativa": "#ef4444", "Liquidado": "#8b5cf6",
        "Cierre Sin Consecuencia": "#94a3b8",
    };
    return Object.entries(byState).map(([k, v]) => {
        const pct = Math.round(v / total * 100);
        const color = stateColors[k] || "#64748b";
        return `
        <div class="intel-state-row">
            <span class="intel-state-dot" style="background:${color}"></span>
            <span class="intel-state-name">${k}</span>
            <div class="intel-state-bar-wrap">
                <div class="intel-state-bar" style="width:${pct}%;background:${color}22;border-left:3px solid ${color}"></div>
            </div>
            <span class="intel-state-count">${v}</span>
            <span class="intel-state-pct">${pct}%</span>
        </div>`;
    }).join("");
}

function renderSlaMonitor(sla) {
    if (!sla) return '<div class="intel-empty">Sin datos</div>';
    const total = Math.max((sla.ok || 0) + (sla.at_risk || 0) + (sla.breach || 0), 1);
    return `
    <div class="intel-sla-grid">
        <div class="intel-sla-item ok">
            <span class="intel-sla-count">${sla.ok || 0}</span>
            <span class="intel-sla-label">En plazo</span>
            <div class="intel-sla-bar" style="width:${Math.round((sla.ok||0)/total*100)}%;background:#10b981"></div>
        </div>
        <div class="intel-sla-item risk">
            <span class="intel-sla-count">${sla.at_risk || 0}</span>
            <span class="intel-sla-label">En riesgo</span>
            <div class="intel-sla-bar" style="width:${Math.round((sla.at_risk||0)/total*100)}%;background:#f59e0b"></div>
        </div>
        <div class="intel-sla-item breach">
            <span class="intel-sla-count">${sla.breach || 0}</span>
            <span class="intel-sla-label">Incumplido</span>
            <div class="intel-sla-bar" style="width:${Math.round((sla.breach||0)/total*100)}%;background:#ef4444"></div>
        </div>
    </div>`;
}

function renderDocMonitor(docs) {
    if (!docs) return '<div class="intel-empty">Sin datos</div>';
    const total = Math.max((docs.complete || 0) + (docs.missing || 0), 1);
    const okPct = Math.round((docs.complete || 0) / total * 100);
    return `
    <div class="intel-doc-monitor">
        <div class="intel-doc-gauge">
            <div class="intel-doc-fill" style="width:${okPct}%"></div>
        </div>
        <div class="intel-doc-stats">
            <span style="color:#10b981">${docs.complete || 0} completos</span>
            <span style="color:#f59e0b">${docs.missing || 0} con faltantes</span>
        </div>
    </div>`;
}

function renderIndicatorBars(indicators) {
    if (!indicators || indicators.length === 0) return '<div class="intel-empty">Sin indicadores detectados</div>';
    const maxCount = Math.max(...indicators.map(i => i.count), 1);
    return indicators.slice(0, 10).map(ind => `
    <div class="intel-indicator-row">
        <span class="intel-indicator-name">${truncate(labelFromPayload(ind.indicator), 30)}</span>
        <div class="intel-indicator-bar-wrap">
            <div class="intel-indicator-bar" style="width:${Math.round(ind.count/maxCount*100)}%"></div>
        </div>
        <span class="intel-indicator-count">${ind.count}</span>
    </div>`).join("");
}

function renderFraudNetwork(sharedBeneficiaries, frequentClaimants) {
    const benefRows = (sharedBeneficiaries || []).slice(0, 6).map(b => `
    <div class="intel-network-node shared">
        <div class="intel-node-icon">👥</div>
        <div class="intel-node-info">
            <span class="intel-node-label">${truncate(b.beneficiary, 28)}</span>
            <span class="intel-node-meta">${b.claim_count} siniestros</span>
        </div>
        <span class="badge badge-warning">${b.claim_count}x</span>
    </div>`).join("");

    const claimRows = (frequentClaimants || []).slice(0, 4).map(c => `
    <div class="intel-network-node claimant">
        <div class="intel-node-icon">🔄</div>
        <div class="intel-node-info">
            <span class="intel-node-label">${truncate(c.customer_id, 28)}</span>
            <span class="intel-node-meta">${c.claim_count} reclamaciones · max score ${c.max_score.toFixed(0)}</span>
        </div>
        <span class="badge badge-danger">${c.claim_count}x</span>
    </div>`).join("");

    if (!benefRows && !claimRows) return '<div class="intel-empty">No se detectaron conexiones sospechosas</div>';

    return `
    <div style="margin-bottom:12px">
        <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:8px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em">Beneficiarios en múltiples siniestros</p>
        ${benefRows || '<p style="color:var(--text-muted);font-size:0.85rem">Sin beneficiarios compartidos</p>'}
    </div>
    ${claimRows ? `
    <div>
        <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:8px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em">Reclamantes frecuentes</p>
        ${claimRows}
    </div>` : ""}`;
}

function renderMonthlyTrend(months) {
    if (!months || months.length === 0) return '<div class="intel-empty">Sin datos</div>';
    const maxClaims = Math.max(...months.map(m => m.claims), 1);
    return `
    <div class="intel-trend-chart">
        ${months.map(m => `
        <div class="intel-trend-col">
            <span class="intel-trend-val">${m.claims}</span>
            <div class="intel-trend-bar-wrap">
                <div class="intel-trend-bar" style="height:${Math.round(m.claims/maxClaims*100)}%"></div>
            </div>
            <span class="intel-trend-label">${m.month.slice(5)}</span>
        </div>`).join("")}
    </div>`;
}

function renderStatusBreakdown(byStatus) {
    if (!byStatus || Object.keys(byStatus).length === 0) return '<div class="intel-empty">Sin datos</div>';
    return Object.entries(byStatus).map(([k, v]) => `
    <div class="intel-state-row">
        ${renderStatusBadge(k)}
        <div class="intel-state-bar-wrap" style="flex:1;margin:0 8px;">
            <div class="intel-state-bar" style="width:${Math.min(100, v * 5)}%"></div>
        </div>
        <strong>${v}</strong>
    </div>`).join("");
}

function renderEngineBreakdown(byEngine) {
    if (!byEngine || Object.keys(byEngine).length === 0) return '<div class="intel-empty">Sin datos</div>';
    const total = Object.values(byEngine).reduce((a, b) => a + b, 0);
    return Object.entries(byEngine).map(([k, v]) => {
        const pct = Math.round(v / Math.max(total, 1) * 100);
        return `
        <div class="intel-engine-row">
            <span class="badge ${k === 'rules' ? 'badge-warning' : 'badge-info'}">${k === 'rules' ? 'rules' : 'deepseek'}</span>
            <div class="intel-gauge-bar" style="flex:1;margin:0 8px;height:8px;background:var(--bg-glass);border-radius:4px;overflow:hidden;">
                <div style="width:${pct}%;height:100%;background:${k==='rules'?'#f59e0b':'#0ea5e9'};border-radius:4px;"></div>
            </div>
            <span>${v} (${pct}%)</span>
        </div>`;
    }).join("");
}

function renderComplianceMetrics(c) {
    return `
    <div class="intel-compliance-grid">
        <div class="intel-compliance-item">
            <div class="intel-compliance-gauge" style="--score:${c.compliance_score ?? 0}">
                <svg viewBox="0 0 100 100" class="intel-gauge-svg">
                    <circle cx="50" cy="50" r="40" fill="none" stroke="var(--bg-glass)" stroke-width="8"/>
                    <circle cx="50" cy="50" r="40" fill="none" stroke="${(c.compliance_score??0)>=80?'#10b981':(c.compliance_score??0)>=60?'#f59e0b':'#ef4444'}" stroke-width="8"
                        stroke-dasharray="${Math.round((c.compliance_score??0)*2.51)} 251"
                        stroke-linecap="round" transform="rotate(-90 50 50)"/>
                    <text x="50" y="55" text-anchor="middle" font-size="18" font-weight="800" fill="var(--text-primary)">${c.compliance_score ?? 0}%</text>
                </svg>
                <span>Compliance</span>
            </div>
        </div>
        <div class="intel-compliance-stats">
            <div class="intel-stat-row"><span>Total siniestros</span><strong>${c.total_claims ?? 0}</strong></div>
            <div class="intel-stat-row"><span>Auditados</span><strong>${c.audited_claims ?? 0}</strong></div>
            <div class="intel-stat-row"><span>Revisados manualmente</span><strong>${c.reviewed ?? 0}</strong></div>
            <div class="intel-stat-row"><span>Sin revisión</span><strong style="color:${(c.not_reviewed??0)>0?'#f59e0b':'#10b981'}">${c.not_reviewed ?? 0}</strong></div>
            <div class="intel-stat-row"><span>Hallazgos críticos</span><strong style="color:${(c.critical_findings??0)>0?'#ef4444':'#10b981'}">${c.critical_findings ?? 0}</strong></div>
            <div class="intel-stat-row"><span>Hallazgos advertencia</span><strong style="color:${(c.warning_findings??0)>0?'#f59e0b':'#10b981'}">${c.warning_findings ?? 0}</strong></div>
            <div class="intel-stat-row"><span>Decisiones manuales</span><strong>${c.overrides ?? 0}</strong></div>
        </div>
    </div>`;
}

// ── DeepSeek trigger ────────────────────────────────────

export async function triggerDeepSeekInsight(panelId, type, encodedContext) {
    const bodyEl = document.getElementById(`ai-body-${panelId}`);
    if (!bodyEl) return;

    let context = {};
    try { context = JSON.parse(decodeURIComponent(encodedContext)); } catch (e) { /* ignore */ }

    bodyEl.innerHTML = `<div class="intel-ai-loading"><div class="intel-spinner-sm"></div> Generando análisis con DeepSeek...</div>`;

    const result = await apiPost("/intelligence/deepseek-insight", {
        type, context, role: state.currentRole || "analista",
    });

    if (!result) {
        bodyEl.innerHTML = `<div class="intel-ai-error">Error al conectar con el servicio de IA. La plataforma continúa funcionando sin IA.</div>`;
        return;
    }

    const statusClass = result.status === "success" ? "intel-ai-response" : "intel-ai-error";
    bodyEl.innerHTML = `
        <div class="${statusClass}">
            <div class="intel-ai-response-header">
                <span>Análisis DeepSeek</span>
                <span class="intel-ai-timestamp">${new Date().toLocaleTimeString("es-EC")}</span>
            </div>
            <div class="intel-ai-response-body">${result.insight.replace(/\n/g, "<br>")}</div>
            <div class="intel-ai-disclaimer">Este análisis es orientativo. Toda decisión requiere revisión humana.</div>
        </div>`;
}

// ── KPI Card helpers ───────────────────────────────────

function kpiCard(label, value, sub, color, icon) {
    return `
    <div class="intel-metric ${color}">
        <div class="intel-metric-icon">${icon}</div>
        <div class="intel-metric-body">
            <div class="intel-metric-label">${label}</div>
            <div class="intel-metric-value ${color}">${value}</div>
            <div class="intel-metric-sub">${sub}</div>
        </div>
    </div>`;
}

function kpiMini(label, value, color) {
    return `
    <div class="intel-mini-stat">
        <span class="intel-mini-label">${label}</span>
        <span class="intel-mini-value ${color}">${value}</span>
    </div>`;
}

// ── Badge helpers ──────────────────────────────────────

function renderFraudScoreBadge(score, classification) {
    const cl = (classification || "").toLowerCase();
    const color = cl === "rojo" ? "#ef4444" : cl === "amarillo" ? "#f59e0b" : "#10b981";
    return `<span class="intel-score-badge" style="background:${color}20;color:${color};border:1px solid ${color}40">${score.toFixed(0)}</span>`;
}

function renderSlaBadge(days) {
    if (days > 30) return `<span class="badge badge-danger">${days}d</span>`;
    if (days > 15) return `<span class="badge badge-warning">${days}d</span>`;
    return `<span class="badge badge-success">${days}d</span>`;
}

// ── Color helpers ──────────────────────────────────────

function scoreColor(score) {
    if (score >= 75) return "rose";
    if (score >= 40) return "amber";
    return "emerald";
}

function coverageColor(pct) {
    if (pct >= 80) return "emerald";
    if (pct >= 50) return "amber";
    return "rose";
}

// ── Formatting helpers ─────────────────────────────────

function fmt(n) {
    return (n || 0).toLocaleString("es-EC", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function fmtDate(iso) {
    if (!iso) return "—";
    try { return new Date(iso).toLocaleDateString("es-EC", { day: "2-digit", month: "short" }); }
    catch { return "—"; }
}

function truncate(str, n) {
    if (!str) return "";
    return str.length > n ? str.slice(0, n) + "…" : str;
}

// ── SVG Icons ──────────────────────────────────────────

const svgIcon = (path) => `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${path}</svg>`;
const iconClaim = () => svgIcon('<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>');
const iconOpen = () => svgIcon('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>');
const iconPay = () => svgIcon('<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>');
const iconReserve = () => svgIcon('<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>');
const iconAlert = () => svgIcon('<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>');
const iconPolicy = () => svgIcon('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>');
const iconCost = () => svgIcon('<circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>');
const iconScore = () => svgIcon('<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>');
const iconQueue = () => svgIcon('<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>');
const iconProcess = () => svgIcon('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>');
const iconCheck = () => svgIcon('<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>');
const iconWarn = () => svgIcon('<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>');
const iconNetwork = () => svgIcon('<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>');
const iconRepeat = () => svgIcon('<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>');

// Overrides for the actionable workflow panel. Kept near the end so these
// definitions are the active ones while preserving the existing dashboards.
async function renderActionFlowPanel(page, perms, options = {}) {
    const include = state.includeTest ? 1 : 0;
    const [ops, fraud, dash, pendingInvoices, auditResults] = await Promise.all([
        apiFetch("/intelligence/operations"),
        apiFetch("/intelligence/fraud"),
        apiFetch("/dashboard?include_test=0"),
        apiFetch(`/invoices/pending?include_test=${include}`),
        apiFetch(`/audit-results?include_test=${include}`),
    ]);
    const role = state.currentRole || "analista";
    const guideStep = Number(localStorage.getItem("auditPanelGuideStep") || "1");
    const showGuide = role === "demo_jurado" && (options.forceGuide || localStorage.getItem("auditPanelGuideHidden") !== "1");
    const workflow = buildActionWorkflow(ops || {}, fraud || {}, dash || {}, pendingInvoices || [], auditResults || []);

    page.innerHTML = `<div class="audit-panel-shell ${showGuide ? `guide-step-${guideStep}` : ""}">
        ${roleHeader(role, "Panel de Auditoría de Siniestros", "Registro, facturas, fraude, aprobación conjunta y cálculo del monto a cubrir")}
        ${showGuide ? renderGameTutorialGuide(guideStep, workflow) : role === "demo_jurado" ? `<div class="audit-guide-restore"><button class="btn btn-ghost btn-sm" onclick="reactivateAuditGuide()">Reactivar guía</button></div>` : ""}
        <div class="audit-value-strip">
            <div><strong>Propósito</strong><span>Trazabilidad entre Analista, Antifraude, Contabilidad y Auditoría para reducir pérdidas y acelerar cierres.</span></div>
            <div><strong>Monto estimado a cubrir</strong><span>$${fmt(((dash || {}).invoice_total_sum || 0) - ((dash || {}).total_overcharge || 0))}</span></div>
            <div><strong>Control activo</strong><span>${(fraud || {}).total_high_risk ?? 0} alto riesgo · ${(ops || {}).audit_queue?.pending ?? 0} facturas pendientes</span></div>
        </div>
        ${renderDemoVerificationFlow()}
        ${renderNextWorkStrip(workflow)}
        <div class="audit-workflow">${workflow.map(step => renderActionWorkflowStep(step, role)).join("")}</div>
        <div class="intel-grid-2">
            <div class="card"><div class="card-header"><h2>Trabajo del Perfil Actual</h2></div><div class="card-body audit-actions-grid">${renderRoleActions(role, ops || {})}</div></div>
            <div class="card"><div class="card-header"><h2>Alertas de Auditoría</h2></div><div class="card-body">${renderAuditAlerts(fraud || {}, ops || {})}</div></div>
        </div>
    </div>`;
}

function renderDemoVerificationFlow() {
    const steps = [
        ["1", "Generar PDFs", "En Carga, el juez puede generar declaración, parte policial y factura por separado, o crear un expediente automático."],
        ["2", "Cargar documentos", "El selector de siniestro es opcional: si el PDF trae referencia SIN-..., el sistema detecta o crea el expediente."],
        ["3", "Orden del expediente", "Declaración, parte policial y factura quedan asociados al mismo siniestro para revisar trazabilidad."],
        ["4", "Auditar con IA", "DeepSeek es el motor principal. Las reglas quedan como respaldo técnico o acción manual si la API no responde."],
    ];
    return `<div class="card" style="margin-bottom:16px;border-left:4px solid var(--accent-indigo);">
        <div class="card-header" style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
            <div>
                <h2>Flujo verificable para jurado</h2>
                <p style="margin:4px 0 0;color:var(--text-muted);">Ruta actual de la demo: manual paso a paso o expediente automático con IA.</p>
            </div>
            <button class="btn btn-primary btn-sm" onclick="navigateTo('upload')">Ir a Carga</button>
        </div>
        <div class="card-body">
            <div class="audit-workflow">
                ${steps.map(([n, title, text]) => `<div class="audit-step completado">
                    <div class="audit-step-index">${n}</div>
                    <div class="audit-step-title"><h3>${title}</h3></div>
                    <div class="audit-step-subject">${text}</div>
                    <span class="audit-status completado">verificable</span>
                </div>`).join("")}
            </div>
        </div>
    </div>`;
}

function buildActionWorkflow(ops, fraud, dash, pendingInvoices = [], auditResults = []) {
    const pending = ops.audit_queue?.pending ?? 0;
    const completed = ops.audit_queue?.completed ?? 0;
    const escalated = ops.audit_queue?.escalated ?? 0;
    const highRisk = fraud.total_high_risk ?? 0;
    const totalClaims = dash.total_claims ?? ops.claims_queue?.length ?? 0;
    const pendingInvoice = pendingInvoices[0] || null;
    const highRiskClaim = (fraud.high_risk_claims || [])[0] || (ops.claims_queue || []).find(c => (c.fraud_score || 0) >= 40) || null;
    const escalatedAudit = auditResults.find(a => a.status === "escalated" || a.status === "in_progress") || auditResults[0] || null;
    const finalAudit = auditResults.find(a => a.status === "approved" || a.status === "completed") || auditResults[0] || null;
    const now = new Date();
    const stamp = (mins) => new Date(now.getTime() - mins * 60000).toLocaleString("es-EC", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

    return [
        { n: 1, title: "Registrar nuevo siniestro", owner: "Analista", status: totalClaims > 0 ? "completado" : "pendiente", time: stamp(80), action: "Cargar", subject: "Nuevo expediente", focus: { page: "upload", title: "Registrar nuevo siniestro", detail: "Crea o carga la documentación inicial del expediente." } },
        { n: 2, title: "Agregar facturas al siniestro", owner: "Analista / Taller", status: pending > 0 ? "en curso" : completed > 0 ? "completado" : "pendiente", time: stamp(62), action: "Ver facturas", subject: pendingInvoice ? `${pendingInvoice.invoice_number} · ${pendingInvoice.claim_number}` : "Sin facturas pendientes", focus: { page: "auditorias", tab: "pendientes", search: pendingInvoice?.invoice_number || "", invoice_id: pendingInvoice?.id, invoice_number: pendingInvoice?.invoice_number, claim_number: pendingInvoice?.claim_number, title: "Factura pendiente a auditar", detail: pendingInvoice ? `Revisa ${pendingInvoice.invoice_number} asociada a ${pendingInvoice.claim_number}.` : "No hay facturas pendientes en cola." } },
        { n: 3, title: "Cuantificar daños y detectar fraude", owner: "Antifraude", status: highRisk > 0 || completed > 0 ? "en curso" : "pendiente", time: stamp(38), action: "Investigar", subject: highRiskClaim ? `${highRiskClaim.claim_number} · score ${Math.round(highRiskClaim.fraud_score || 0)}` : "Sin alertas activas", focus: { page: "siniestros", search: highRiskClaim?.claim_number || "", claim_id: highRiskClaim?.claim_id || highRiskClaim?.id, claim_number: highRiskClaim?.claim_number, title: "Siniestro prioritario", detail: highRiskClaim ? `Cuantifica daños y revisa indicadores de ${highRiskClaim.claim_number}.` : "No hay siniestros de alto riesgo pendientes." } },
        { n: 4, title: "Aprobación conjunta del siniestro", owner: "Fraude + Contabilidad", status: escalated > 0 ? "en curso" : completed > 0 ? "completado" : "pendiente", time: stamp(20), action: "Revisar", subject: escalatedAudit ? `${escalatedAudit.invoice_number} · ${escalatedAudit.claim_number}` : "Sin aprobaciones abiertas", focus: { page: "auditorias", tab: "revisadas", search: escalatedAudit?.invoice_number || "", audit_id: escalatedAudit?.audit_id, invoice_number: escalatedAudit?.invoice_number, claim_number: escalatedAudit?.claim_number, title: "Aprobación conjunta pendiente", detail: escalatedAudit ? `Valida hallazgos y monto de ${escalatedAudit.invoice_number}.` : "No hay casos escalados para aprobación conjunta." } },
        { n: 5, title: "Verificación final del siniestro", owner: "Auditoría", status: completed > 0 && pending === 0 ? "completado" : "pendiente", time: stamp(6), action: "Verificar", subject: finalAudit ? `${finalAudit.invoice_number} · cubrir $${fmt((finalAudit.invoice_total || 0) - (finalAudit.total_overcharge || 0))}` : "Sin verificaciones listas", focus: { page: "auditorias", tab: "revisadas", search: finalAudit?.invoice_number || "", audit_id: finalAudit?.audit_id, invoice_number: finalAudit?.invoice_number, claim_number: finalAudit?.claim_number, title: "Verificación final", detail: finalAudit ? `Confirma el monto a cubrir de ${finalAudit.invoice_number}.` : "No hay verificaciones finales listas." } },
    ];
}

function renderNextWorkStrip(workflow) {
    const next = workflow.find(s => s.status !== "completado") || workflow[workflow.length - 1];
    return `<div class="audit-next-work">
        <div><strong>Siguiente pendiente</strong><span>${next.title}</span></div>
        <div><strong>Elemento</strong><span>${next.subject}</span></div>
        <button class="btn btn-primary btn-sm" onclick="openWorkflowTarget('${encodeURIComponent(JSON.stringify(next.focus))}')">Abrir trabajo</button>
    </div>`;
}

function renderActionWorkflowStep(step, role) {
    const canAct = roleCanActOnStep(role, step.n);
    const statusClass = step.status.replace(" ", "-");
    return `<div class="audit-step ${statusClass}">
        <div class="audit-step-index">${step.n}</div>
        <div class="audit-step-title"><h3>${step.title}</h3></div>
        <div class="audit-step-subject">${step.subject}</div>
        <div class="audit-step-owner">${step.owner}</div>
        <div class="audit-step-time">${step.time}</div>
        <span class="audit-status ${statusClass}">${step.status}</span>
        <button class="btn ${canAct ? "btn-primary" : "btn-ghost"} btn-sm" ${canAct ? `onclick="openWorkflowTarget('${encodeURIComponent(JSON.stringify(step.focus))}')"` : "disabled"}>${step.action}</button>
    </div>`;
}

function renderGameTutorialGuide(step, workflow) {
    const current = workflow[Math.max(0, Math.min(step - 1, workflow.length - 1))];
    return `<div class="game-tutorial">
        <div class="tutorial-step-badge">Tutorial ${step}/5</div>
        <div class="tutorial-copy">
            <strong>${current.title}</strong>
            <p>${current.focus.detail}</p>
            <span>Botón objetivo: ${current.action}</span>
        </div>
        <div class="tutorial-controls">
            <button class="btn btn-ghost btn-sm" onclick="prevDemoGuide()" ${step <= 1 ? "disabled" : ""}>Anterior</button>
            <button class="btn btn-primary btn-sm" onclick="${step >= 5 ? "skipAuditGuide()" : "nextDemoGuide()"}">${step >= 5 ? "Terminar" : "Siguiente"}</button>
            <button class="btn btn-ghost btn-sm" onclick="skipAuditGuide()">Saltar</button>
        </div>
    </div>`;
}

export function openWorkflowTarget(encodedFocus) {
    let focus = {};
    try { focus = JSON.parse(decodeURIComponent(encodedFocus)); } catch (e) { focus = {}; }
    state.workflowFocus = focus;
    if (focus.page === "auditorias") {
        state.currentAuditTab = focus.tab || "pendientes";
        state.auditSearchTerm = focus.search || "";
    }
    if (focus.page === "siniestros") {
        state.claimsSearchTerm = focus.search || "";
        state.claimExpanded = focus.claim_id || null;
    }
    if (typeof window.navigateTo === "function") window.navigateTo(focus.page || "audit-panel");
}

export function nextDemoGuide() {
    const step = Math.min(5, Number(localStorage.getItem("auditPanelGuideStep") || "1") + 1);
    localStorage.setItem("auditPanelGuideStep", String(step));
    loadAuditPanel(true);
}

export function prevDemoGuide() {
    const step = Math.max(1, Number(localStorage.getItem("auditPanelGuideStep") || "1") - 1);
    localStorage.setItem("auditPanelGuideStep", String(step));
    loadAuditPanel(true);
}

function labelFromPayload(value) {
    if (typeof value === "string") return value;
    if (value && typeof value === "object") {
        return value.message || value.description || value.title || value.id || value.rule || value.indicator || JSON.stringify(value);
    }
    return String(value || "");
}

async function renderAuditPanel(page, perms, options = {}) {
    const [ops, fraud, dash] = await Promise.all([
        apiFetch("/intelligence/operations"),
        apiFetch("/intelligence/fraud"),
        apiFetch("/dashboard?include_test=0"),
    ]);
    const role = state.currentRole || "analista";
    const showGuide = role === "demo_jurado" && (options.forceGuide || localStorage.getItem("auditPanelGuideHidden") !== "1");
    const workflow = buildWorkflow(ops || {}, fraud || {}, dash || {});
    page.innerHTML = `
        ${roleHeader(role, "Panel de Auditoría de Siniestros", "Registro, facturas, fraude, aprobación conjunta y cálculo del monto a cubrir")}
        ${showGuide ? renderAuditPanelGuide() : role === "demo_jurado" ? `<div class="audit-guide-restore"><button class="btn btn-ghost btn-sm" onclick="reactivateAuditGuide()">Reactivar guía</button></div>` : ""}
        <div class="audit-value-strip">
            <div><strong>Propósito</strong><span>Trazabilidad entre Analista, Antifraude, Contabilidad y Auditoría para reducir pérdidas y acelerar cierres.</span></div>
            <div><strong>Monto estimado a cubrir</strong><span>$${fmt(((dash || {}).invoice_total_sum || 0) - ((dash || {}).total_overcharge || 0))}</span></div>
            <div><strong>Control activo</strong><span>${(fraud || {}).total_high_risk ?? 0} alto riesgo · ${(ops || {}).audit_queue?.pending ?? 0} facturas pendientes</span></div>
        </div>
        <div class="audit-workflow">${workflow.map(step => renderWorkflowStep(step, role)).join("")}</div>
        <div class="intel-grid-2">
            <div class="card"><div class="card-header"><h2>Trabajo del Perfil Actual</h2></div><div class="card-body audit-actions-grid">${renderRoleActions(role, ops || {})}</div></div>
            <div class="card"><div class="card-header"><h2>Alertas de Auditoría</h2></div><div class="card-body">${renderAuditAlerts(fraud || {}, ops || {})}</div></div>
        </div>`;
}

function buildWorkflow(ops, fraud, dash) {
    const pending = ops.audit_queue?.pending ?? 0;
    const completed = ops.audit_queue?.completed ?? 0;
    const escalated = ops.audit_queue?.escalated ?? 0;
    const highRisk = fraud.total_high_risk ?? 0;
    const totalClaims = dash.total_claims ?? ops.claims_queue?.length ?? 0;
    const now = new Date();
    const stamp = (mins) => new Date(now.getTime() - mins * 60000).toLocaleString("es-EC", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
    return [
        { n: 1, title: "Registrar nuevo siniestro", owner: "Analista", status: totalClaims > 0 ? "completado" : "pendiente", time: stamp(80), action: "Cargar", target: "upload" },
        { n: 2, title: "Agregar facturas al siniestro", owner: "Analista / Taller", status: pending > 0 ? "en curso" : completed > 0 ? "completado" : "pendiente", time: stamp(62), action: "Ver facturas", target: "auditorias" },
        { n: 3, title: "Cuantificar daños y detectar fraude", owner: "Antifraude", status: highRisk > 0 || completed > 0 ? "en curso" : "pendiente", time: stamp(38), action: "Investigar", target: "siniestros" },
        { n: 4, title: "Aprobación conjunta del siniestro", owner: "Analista de fraude + Contabilidad", status: escalated > 0 ? "en curso" : completed > 0 ? "completado" : "pendiente", time: stamp(20), action: "Revisar", target: "auditorias" },
        { n: 5, title: "Verificación final del siniestro", owner: "Auditoría", status: completed > 0 && pending === 0 ? "completado" : "pendiente", time: stamp(6), action: "Verificar", target: "auditorias" },
    ];
}

function renderWorkflowStep(step, role) {
    const canAct = roleCanActOnStep(role, step.n);
    const statusClass = step.status.replace(" ", "-");
    return `<div class="audit-step ${statusClass}">
        <div class="audit-step-index">${step.n}</div>
        <div class="audit-step-title"><h3>${step.title}</h3></div>
        <div class="audit-step-owner">${step.owner}</div>
        <div class="audit-step-time">${step.time}</div>
        <span class="audit-status ${statusClass}">${step.status}</span>
        <button class="btn ${canAct ? "btn-primary" : "btn-ghost"} btn-sm" ${canAct ? `onclick="navigateTo('${step.target}')"` : "disabled"}>${step.action}</button>
    </div>`;
}

function roleCanActOnStep(role, step) {
    const map = { analista: [1, 2, 4], antifraude: [3, 4], auditoria: [4, 5], demo_jurado: [1, 2, 3, 4, 5] };
    return (map[role] || []).includes(step);
}

function renderRoleActions(role, ops) {
    const byRole = {
        analista: [["Registrar siniestro", "upload", "Crear expediente y anexar documentos."], ["Agregar facturas", "auditorias", `${ops.audit_queue?.pending ?? 0} factura(s) pendientes.`]],
        antifraude: [["Cuantificar y detectar fraude", "siniestros", "Abrir casos con score alto."], ["Aprobación conjunta", "auditorias", "Preparar decisión con Contabilidad."]],
        auditoria: [["Verificación final", "auditorias", "Validar trazabilidad y monto automático."], ["Auditoría completa", "auditorias", "Revisar evidencia y resultado final."]],
        demo_jurado: [["Probar Analista", "upload", "Carga facturas y crea expediente."], ["Probar Antifraude", "siniestros", "Investiga señales."], ["Probar Auditoría", "auditorias", "Cierra la revisión."]],
    };
    return (byRole[role] || byRole.analista).map(([label, target, text]) => `<button class="audit-action" onclick="navigateTo('${target}')"><strong>${label}</strong><span>${text}</span></button>`).join("");
}

function renderAuditAlerts(fraud, ops) {
    const indicators = (fraud.top_indicators || []).slice(0, 5);
    return `<div class="audit-alert-row"><strong>${fraud.total_high_risk ?? 0}</strong><span>Siniestros en alto riesgo</span></div>
        <div class="audit-alert-row"><strong>${ops.audit_queue?.escalated ?? 0}</strong><span>Casos escalados para aprobación</span></div>
        <div class="audit-alert-row"><strong>${ops.documentation?.missing ?? 0}</strong><span>Expedientes con documentación faltante</span></div>
        <div class="audit-alert-tags">${indicators.length ? indicators.map(i => `<span class="intel-indicator-tag">${truncate(labelFromPayload(i.indicator), 28)}</span>`).join("") : '<span class="intel-empty">Sin indicadores recurrentes</span>'}</div>`;
}

function renderAuditPanelGuide() {
    return `<div class="audit-guide"><div><strong>Guía rápida Demo/Jurado</strong><p>Recorre el proceso por departamentos: Analista registra y carga; Antifraude cuantifica y detecta anomalías; Contabilidad coaprueba; Auditoría verifica el monto final. Cambia de perfil con <strong>Sign Out</strong> y selecciona el rol correspondiente.</p></div><div class="audit-guide-steps"><span>1. Analista: Cargar</span><span>2. Antifraude: Siniestros</span><span>3. Contabilidad/Auditoría: Auditorías</span><span>4. Ver monto a cubrir</span></div><button class="btn btn-ghost btn-sm" onclick="skipAuditGuide()">Saltar guía</button></div>`;
}

export function skipAuditGuide() {
    localStorage.setItem("auditPanelGuideHidden", "1");
    loadAuditPanel(false);
}

export function reactivateAuditGuide() {
    localStorage.removeItem("auditPanelGuideHidden");
    localStorage.setItem("auditPanelGuideStep", "1");
    loadAuditPanel(true);
}
