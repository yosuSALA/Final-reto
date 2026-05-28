import { apiFetch, apiPost } from "../api.js";
import { renderRiskBadge, renderStatusBadge, showToast } from "../utils.js";
import { state } from "../state.js";

let _activeTab = "summary";

function labelFromPayload(value) {
    if (typeof value === "string") return value;
    if (value && typeof value === "object") {
        return value.message || value.description || value.title || value.id || value.rule || value.indicator || JSON.stringify(value);
    }
    return String(value || "");
}

export async function loadClaimWorkspace(claimId) {
    const page = document.getElementById("page-claim-workspace");
    if (!page) return;

    page.innerHTML = `<div class="intel-loading"><div class="intel-spinner"></div><p>Cargando espacio de investigación...</p></div>`;

    const data = await apiFetch(`/intelligence/claim/${claimId}`);
    if (!data) {
        page.innerHTML = `<div class="intel-error"><h3>Siniestro no encontrado</h3><button class="btn btn-ghost" onclick="history.back()">Volver</button></div>`;
        return;
    }

    _activeTab = "summary";
    render(page, data);
}

function render(page, data) {
    const { claim, policy, customer, vehicle, audit, findings, invoices, documents, timeline, audit_trail, customer_history } = data;
    const classColor = { rojo: "#ef4444", amarillo: "#f59e0b", verde: "#10b981" };
    const scoreColor = classColor[(claim.fraud_classification || "verde").toLowerCase()] || "#10b981";

    page.innerHTML = `
    <div class="workspace-layout">
        <!-- Left: Summary strip -->
        <div class="workspace-sidebar">
            <button class="btn btn-ghost btn-sm workspace-back" onclick="history.back()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
                Volver
            </button>

            <div class="workspace-claim-id">
                <h2>${claim.claim_number}</h2>
                <span class="badge badge-info">${claim.ramo}</span>
                <span class="badge" style="background:${scoreColor}20;color:${scoreColor}">${claim.fraud_classification}</span>
            </div>

            <div class="workspace-score-block">
                <div class="workspace-score-ring" style="--score-color:${scoreColor}">
                    <svg viewBox="0 0 100 100" width="90" height="90">
                        <circle cx="50" cy="50" r="40" fill="none" stroke="var(--bg-glass)" stroke-width="10"/>
                        <circle cx="50" cy="50" r="40" fill="none" stroke="${scoreColor}" stroke-width="10"
                            stroke-dasharray="${Math.round((claim.fraud_score||0)*2.51)} 251"
                            stroke-linecap="round" transform="rotate(-90 50 50)"/>
                        <text x="50" y="55" text-anchor="middle" font-size="22" font-weight="800" fill="${scoreColor}">${(claim.fraud_score||0).toFixed(0)}</text>
                    </svg>
                </div>
                <span class="workspace-score-label">Score de Fraude</span>
            </div>

            <div class="workspace-meta">
                <div class="workspace-meta-row"><span>Estado</span><strong>${claim.estado}</strong></div>
                <div class="workspace-meta-row"><span>Sucursal</span><strong>${claim.sucursal || "—"}</strong></div>
                <div class="workspace-meta-row"><span>Monto Reclamado</span><strong>$${fmt(claim.amount_claimed)}</strong></div>
                <div class="workspace-meta-row"><span>Monto Pagado</span><strong>$${fmt(claim.amount_paid)}</strong></div>
                <div class="workspace-meta-row"><span>Días SLA</span><strong style="color:${claim.days_delay>30?'#ef4444':claim.days_delay>15?'#f59e0b':'#10b981'}">${claim.days_delay}d</strong></div>
                <div class="workspace-meta-row"><span>Documentos</span><strong style="color:${claim.docs_complete?'#10b981':'#f59e0b'}">${claim.docs_complete ? "Completos" : "Incompletos"}</strong></div>
            </div>

            <div class="workspace-nav">
                ${["summary", "timeline", "fraud", "documents", "policy", "customer", "vehicle", "audit-trail"].map(t =>
                    `<button class="workspace-tab-btn ${_activeTab === t ? "active" : ""}" onclick="switchWorkspaceTab('${t}','${claim.id}')">${tabLabel(t)}</button>`
                ).join("")}
            </div>
        </div>

        <!-- Right: Main content -->
        <div class="workspace-main" id="workspace-main">
            ${renderTab(_activeTab, data)}
        </div>
    </div>`;
}

export function switchWorkspaceTab(tab, claimId) {
    _activeTab = tab;
    document.querySelectorAll(".workspace-tab-btn").forEach(b => {
        b.classList.toggle("active", b.textContent === tabLabel(tab));
    });
    const main = document.getElementById("workspace-main");
    if (!main) return;

    apiFetch(`/intelligence/claim/${claimId}`).then(data => {
        if (data) main.innerHTML = renderTab(tab, data);
    });
}

function renderTab(tab, data) {
    switch (tab) {
        case "summary":    return renderSummary(data);
        case "timeline":   return renderTimeline(data);
        case "fraud":      return renderFraudAnalysis(data);
        case "documents":  return renderDocuments(data);
        case "policy":     return renderPolicy(data);
        case "customer":   return renderCustomer(data);
        case "vehicle":    return renderVehicle(data);
        case "audit-trail": return renderAuditTrail(data);
        default:           return renderSummary(data);
    }
}

function renderSummary(data) {
    const { claim, audit, findings, invoices, customer } = data;
    const critical = findings.filter(f => f.severity === "critical").length;
    const warning = findings.filter(f => f.severity === "warning").length;
    return `
    <div class="workspace-section">
        <h3 class="workspace-section-title">Resumen del Siniestro</h3>
        <div class="workspace-summary-grid">
            <div class="workspace-summary-card">
                <h4>Estado de Auditoría</h4>
                ${audit?.id ? `
                <p>${renderStatusBadge(audit.status)}</p>
                <p>Score: ${renderRiskBadge(audit.risk_score)}</p>
                <p>Sobrecosto detectado: <strong>$${fmt(audit.total_overcharge)}</strong></p>
                <p>Motor: <span class="badge badge-info">${audit.engine}</span></p>
                ${audit.summary ? `<p style="margin-top:8px;color:var(--text-secondary);font-size:0.85rem">${audit.summary}</p>` : ""}
                ` : '<p style="color:var(--text-muted)">Sin auditoría registrada</p>'}
            </div>

            <div class="workspace-summary-card">
                <h4>Hallazgos</h4>
                ${findings.length === 0
                    ? '<p style="color:var(--text-muted)">Sin hallazgos registrados</p>'
                    : `<div class="intel-kpi-mini-grid">
                        <div style="color:#ef4444"><strong>${critical}</strong> críticos</div>
                        <div style="color:#f59e0b"><strong>${warning}</strong> advertencia</div>
                        <div style="color:#10b981"><strong>${findings.length - critical - warning}</strong> limpios</div>
                       </div>
                       ${findings.slice(0, 3).map(f => `
                       <div class="workspace-finding-mini ${f.severity}">
                           <span class="badge badge-${f.severity === 'critical' ? 'danger' : f.severity === 'warning' ? 'warning' : 'success'}">${f.severity}</span>
                           <span>${f.title}</span>
                       </div>`).join("")}`}
            </div>

            <div class="workspace-summary-card">
                <h4>Indicadores de Fraude</h4>
                ${claim.fraud_indicators?.length > 0
                    ? claim.fraud_indicators.map(i => `<div class="intel-indicator-tag" style="margin-bottom:4px">${labelFromPayload(i)}</div>`).join("")
                    : '<p style="color:var(--text-muted)">Sin indicadores</p>'}
            </div>

            <div class="workspace-summary-card">
                <h4>Facturas Asociadas</h4>
                ${invoices.length === 0
                    ? '<p style="color:var(--text-muted)">Sin facturas</p>'
                    : invoices.map(inv => `
                    <div class="workspace-invoice-mini">
                        <span>${inv.invoice_number}</span>
                        <span>$${fmt(inv.total)}</span>
                        ${renderStatusBadge(inv.audit_status)}
                    </div>`).join("")}
            </div>
        </div>
    </div>`;
}

function renderTimeline(data) {
    const { timeline, claim } = data;
    return `
    <div class="workspace-section">
        <h3 class="workspace-section-title">Línea de Tiempo</h3>
        <div class="workspace-timeline">
            ${timeline.map((e, i) => `
            <div class="workspace-timeline-item ${i === timeline.length - 1 ? 'last' : ''}">
                <div class="workspace-timeline-dot"></div>
                <div class="workspace-timeline-content">
                    <span class="workspace-timeline-event">${e.event}</span>
                    <span class="workspace-timeline-date">${fmtDateFull(e.date)}</span>
                </div>
            </div>`).join("")}
        </div>
    </div>`;
}

function renderFraudAnalysis(data) {
    const { claim, findings } = data;
    return `
    <div class="workspace-section">
        <h3 class="workspace-section-title">Análisis de Fraude</h3>

        <div class="workspace-fraud-header">
            <div class="workspace-fraud-score-display" style="color:${scoreColorByClass(claim.fraud_classification)}">
                <span class="workspace-fraud-score-num">${(claim.fraud_score||0).toFixed(1)}</span>
                <span>/ 100</span>
            </div>
            <div>
                <p><strong>Clasificación:</strong> ${claim.fraud_classification}</p>
                <p><strong>Reglas fallidas:</strong> ${claim.rules_failed?.length ?? 0}</p>
                <p><strong>Beneficiario:</strong> ${claim.beneficiary || "—"}</p>
            </div>
        </div>

        ${claim.fraud_indicators?.length > 0 ? `
        <h4 style="margin:16px 0 8px">Indicadores Detectados</h4>
        <div class="workspace-indicators-list">
            ${claim.fraud_indicators.map(i => `<div class="intel-indicator-full"><span class="intel-ind-bullet">⚠</span>${labelFromPayload(i)}</div>`).join("")}
        </div>` : ""}

        ${claim.rules_failed?.length > 0 ? `
        <h4 style="margin:16px 0 8px">Reglas Incumplidas</h4>
        <div class="workspace-rules-list">
            ${claim.rules_failed.map(r => `<div class="workspace-rule-fail"><span>✗</span><span>${labelFromPayload(r)}</span></div>`).join("")}
        </div>` : ""}

        ${findings.length > 0 ? `
        <h4 style="margin:16px 0 8px">Hallazgos de Auditoría</h4>
        ${findings.map(f => `
        <div class="workspace-finding ${f.severity}">
            <div class="workspace-finding-header">
                <span class="badge badge-${f.severity === 'critical' ? 'danger' : f.severity === 'warning' ? 'warning' : 'success'}">${f.severity}</span>
                <strong>${f.title}</strong>
                <span class="badge badge-info">${f.type}</span>
            </div>
            <p style="color:var(--text-secondary);margin:4px 0">${f.description}</p>
            ${f.expected || f.actual ? `
            <div class="workspace-finding-diff">
                ${f.expected ? `<span>Esperado: <code>${f.expected}</code></span>` : ""}
                ${f.actual ? `<span>Actual: <code>${f.actual}</code></span>` : ""}
                ${f.difference ? `<span style="color:#ef4444">Diferencia: $${fmt(f.difference)}</span>` : ""}
            </div>` : ""}
            ${f.recommendation ? `<p class="workspace-finding-rec">${f.recommendation}</p>` : ""}
        </div>`).join("")}` : ""}
    </div>`;
}

function renderDocuments(data) {
    const { documents } = data;
    if (!documents || documents.length === 0) return `<div class="workspace-section"><h3 class="workspace-section-title">Documentos</h3><div class="intel-empty">Sin documentos registrados</div></div>`;
    return `
    <div class="workspace-section">
        <h3 class="workspace-section-title">Documentos del Expediente</h3>
        <table>
            <thead><tr><th>Tipo</th><th>Entregado</th><th>Legible</th><th>Inconsistencia</th><th>Observación</th></tr></thead>
            <tbody>
                ${documents.map(d => `
                <tr>
                    <td>${d.type}</td>
                    <td>${d.delivered ? '<span class="badge badge-success">Sí</span>' : '<span class="badge badge-danger">No</span>'}</td>
                    <td>${d.legible ? '<span class="badge badge-success">Sí</span>' : '<span class="badge badge-warning">No</span>'}</td>
                    <td>${d.inconsistency ? '<span class="badge badge-danger">Detectada</span>' : '<span class="badge badge-success">OK</span>'}</td>
                    <td><small>${d.observation || "—"}</small></td>
                </tr>`).join("")}
            </tbody>
        </table>
    </div>`;
}

function renderPolicy(data) {
    const { policy } = data;
    if (!policy || !policy.id) return `<div class="workspace-section"><h3 class="workspace-section-title">Póliza</h3><div class="intel-empty">Sin información de póliza</div></div>`;
    return `
    <div class="workspace-section">
        <h3 class="workspace-section-title">Información de Póliza</h3>
        <div class="workspace-detail-grid">
            <div class="workspace-detail-row"><span>ID Póliza</span><strong>${policy.id}</strong></div>
            <div class="workspace-detail-row"><span>Ramo</span><strong>${policy.ramo}</strong></div>
            <div class="workspace-detail-row"><span>Prima</span><strong>$${fmt(policy.prima)}</strong></div>
            <div class="workspace-detail-row"><span>Suma Asegurada</span><strong>$${fmt(policy.suma_asegurada)}</strong></div>
            <div class="workspace-detail-row"><span>Deducible</span><strong>$${fmt(policy.deducible)}</strong></div>
            <div class="workspace-detail-row"><span>Estado</span><strong>${policy.estado || "—"}</strong></div>
            <div class="workspace-detail-row"><span>Canal de Venta</span><strong>${policy.canal || "—"}</strong></div>
        </div>
    </div>`;
}

function renderCustomer(data) {
    const { customer, customer_history } = data;
    if (!customer || !customer.id) return `<div class="workspace-section"><h3 class="workspace-section-title">Cliente</h3><div class="intel-empty">Sin información del cliente</div></div>`;
    return `
    <div class="workspace-section">
        <h3 class="workspace-section-title">Perfil del Cliente</h3>
        <div class="workspace-detail-grid">
            <div class="workspace-detail-row"><span>Nombre</span><strong>${customer.name || customer.id}</strong></div>
            <div class="workspace-detail-row"><span>Segmento</span><strong>${customer.segment || "—"}</strong></div>
            <div class="workspace-detail-row"><span>Ciudad</span><strong>${customer.city || "—"}</strong></div>
            <div class="workspace-detail-row"><span>Reclamaciones (12m)</span><strong style="color:${(customer.claims_12m||0)>2?'#ef4444':'inherit'}">${customer.claims_12m || 0}</strong></div>
            <div class="workspace-detail-row"><span>Score de Cliente</span><strong>${customer.score || 0}</strong></div>
            <div class="workspace-detail-row"><span>Total siniestros históricos</span><strong>${customer.total_claims || 0}</strong></div>
        </div>

        ${customer_history?.length > 0 ? `
        <h4 style="margin:20px 0 8px">Historial de Siniestros</h4>
        <table>
            <thead><tr><th>Siniestro</th><th>Fecha</th><th>Monto</th><th>Estado</th><th>Score</th></tr></thead>
            <tbody>
                ${customer_history.map(h => `
                <tr>
                    <td>${h.claim_number}</td>
                    <td>${fmtDateFull(h.date)}</td>
                    <td>$${fmt(h.amount)}</td>
                    <td>${renderStatusBadge ? renderStatusBadge(h.estado) : h.estado}</td>
                    <td>${renderRiskBadge(h.fraud_score)}</td>
                </tr>`).join("")}
            </tbody>
        </table>` : ""}
    </div>`;
}

function renderVehicle(data) {
    const { vehicle, claim } = data;
    if (!vehicle || !vehicle.plate) return `<div class="workspace-section"><h3 class="workspace-section-title">Vehículo</h3><div class="intel-empty">Sin información del vehículo</div></div>`;
    return `
    <div class="workspace-section">
        <h3 class="workspace-section-title">Vehículo Asegurado</h3>
        <div class="workspace-vehicle-card">
            <div class="workspace-vehicle-plate">${vehicle.plate}</div>
            <div class="workspace-detail-grid">
                <div class="workspace-detail-row"><span>Marca</span><strong>${vehicle.brand || "—"}</strong></div>
                <div class="workspace-detail-row"><span>Modelo</span><strong>${vehicle.model || "—"}</strong></div>
                <div class="workspace-detail-row"><span>Año</span><strong>${vehicle.year || "—"}</strong></div>
                <div class="workspace-detail-row"><span>Chasis</span><strong>${vehicle.chasis || "—"}</strong></div>
                <div class="workspace-detail-row"><span>Cobertura</span><strong>${claim.cobertura}</strong></div>
            </div>
        </div>
    </div>`;
}

function renderAuditTrail(data) {
    const { audit_trail } = data;
    if (!audit_trail || audit_trail.length === 0) return `<div class="workspace-section"><h3 class="workspace-section-title">Rastro de Auditoría</h3><div class="intel-empty">Sin historial de auditorías</div></div>`;
    return `
    <div class="workspace-section">
        <h3 class="workspace-section-title">Rastro de Auditoría</h3>
        <table>
            <thead><tr><th>ID</th><th>Motor</th><th>Score</th><th>Estado</th><th>Sobrecosto</th><th>Revisor</th><th>Fecha</th></tr></thead>
            <tbody>
                ${audit_trail.map(a => `
                <tr class="clickable" onclick="location.hash='audit/${a.audit_id}'">
                    <td>#${a.audit_id}</td>
                    <td><span class="badge ${a.engine === 'gemini' ? 'badge-info' : 'badge-warning'}">${a.engine}</span></td>
                    <td>${renderRiskBadge(a.risk_score)}</td>
                    <td>${renderStatusBadge(a.status)}</td>
                    <td style="color:${a.total_overcharge>0?'#ef4444':'#10b981'}">$${fmt(a.total_overcharge)}</td>
                    <td>${a.reviewed_by || "—"}</td>
                    <td>${fmtDateFull(a.audited_at)}</td>
                </tr>`).join("")}
            </tbody>
        </table>
    </div>`;
}

// ── Helpers ────────────────────────────────────────────

function tabLabel(t) {
    const labels = {
        summary: "Resumen", timeline: "Línea de Tiempo", fraud: "Análisis Fraude",
        documents: "Documentos", policy: "Póliza", customer: "Cliente",
        vehicle: "Vehículo", "audit-trail": "Rastro Auditoría",
    };
    return labels[t] || t;
}

function fmt(n) { return (n || 0).toLocaleString("es-EC", { minimumFractionDigits: 0, maximumFractionDigits: 0 }); }

function fmtDateFull(iso) {
    if (!iso) return "—";
    try { return new Date(iso).toLocaleDateString("es-EC", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }); }
    catch { return "—"; }
}

function scoreColorByClass(cl) {
    const m = { "rojo": "#ef4444", "amarillo": "#f59e0b", "verde": "#10b981" };
    return m[(cl || "verde").toLowerCase()] || "#10b981";
}
