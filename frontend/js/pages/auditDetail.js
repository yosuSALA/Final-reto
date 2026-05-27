import { apiFetch, apiPost, API } from "../api.js";
import { showToast, renderStatusBadge } from "../utils.js";
import { getPermissions } from "../auth.js";

export async function loadAuditDetail(auditId) {
    const data = await apiFetch(`/audit-results/${auditId}`);
    if (!data) return;
    const perms = getPermissions();
    const page = document.getElementById("page-audit-detail");
    const riskColor = data.risk_score >= 70 ? "#ef4444" : data.risk_score >= 30 ? "#f59e0b" : "#10b981";
    const circumference = 2 * Math.PI * 45;
    const dashLen = (data.risk_score / 100) * circumference;
    const engine = data.audit_engine || "rules";
    const engineLabel = engine === "gemini" ? "🤖 IA Gemini" : "⚡ Reglas";
    const engineColor = engine === "gemini" ? "var(--accent-indigo)" : "var(--accent-emerald)";
    page.innerHTML = `
        <button class="back-btn" onclick="navigateTo('auditorias')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            Volver a Auditorias
        </button>
        <div class="detail-header">
            <div class="detail-info">
                <h1>Auditoria #${data.audit_id} — ${data.invoice_number}
                    <span class="badge" style="background:${engineColor};color:white;font-size:0.7rem;margin-left:8px;vertical-align:middle;">${engineLabel}</span>
                </h1>
                <div class="detail-meta">
                    <div class="detail-meta-item"><strong>Siniestro:</strong> ${data.claim_number}</div>
                    <div class="detail-meta-item"><strong>Tipo:</strong> ${data.claim_type.replace(/_/g, ' ')}</div>
                    <div class="detail-meta-item"><strong>Vehiculo:</strong> ${data.vehicle} (${data.vehicle_plate})</div>
                    <div class="detail-meta-item"><strong>Asegurado:</strong> ${data.insured_name}</div>
                    <div class="detail-meta-item"><strong>Taller:</strong> ${data.workshop_name} (${data.workshop_ruc})</div>
                </div>
                <div style="margin-top:10px;padding:8px 12px;background:#f1f5f9;border-radius:6px;font-size:0.8rem;color:var(--text-muted);">
                    Re-auditar reemplaza el resultado existente (no duplica). Cambia el motor solo si quieres comparar.
                </div>
            </div>
            <div class="detail-actions">
                <button class="btn btn-info btn-sm" onclick="reAuditWith(${data.invoice_id}, 'rules')" style="background-color: var(--accent-emerald); color: white;" title="Re-auditar con motor de reglas (rápido)">⚡ Re-auditar Reglas</button>
                <button class="btn btn-info btn-sm" onclick="reAuditWith(${data.invoice_id}, 'gemini')" style="background-color: var(--accent-indigo); color: white;" title="Re-auditar con Gemini IA (15-30s)">🤖 Re-auditar IA</button>
                <button class="btn btn-info btn-sm" onclick="previewReport(${data.audit_id}, 'internal')" style="background-color: #475569; color: white;">Reporte Interno</button>
                ${perms.canNotify ? `<button class="btn btn-info btn-sm" onclick="previewReport(${data.audit_id}, 'workshop')" style="background-color: #475569; color: white;">Notificación Taller</button>` : ""}
                ${perms.canReviewDecision ? `<button class="btn btn-success btn-sm" onclick="auditAction(${data.audit_id}, 'approve')">Aprobar</button>` : ""}
                ${perms.canReviewDecision ? `<button class="btn btn-danger btn-sm" onclick="auditAction(${data.audit_id}, 'reject')">Rechazar</button>` : ""}
                ${perms.canReviewDecision ? `<button class="btn btn-warning btn-sm" onclick="auditAction(${data.audit_id}, 'escalate')">Escalar</button>` : ""}
            </div>
        </div>
        <div class="summary-box">${data.summary || ""}</div>
        <div id="pdf-preview-container" style="display:none; margin-bottom:24px; padding:16px; border:1px solid var(--accent-indigo); border-radius:8px; background:rgba(99, 102, 241, 0.05);">
            <div style="display:flex; justify-content:space-between; margin-bottom:12px; align-items:center; flex-wrap:wrap; gap:8px;">
                <h3 id="pdf-preview-title" style="margin:0; color:var(--accent-indigo);">Vista Previa</h3>
                <div style="display:flex; gap:6px;">
                    <button class="btn btn-ghost btn-sm" onclick="document.getElementById('pdf-preview-container').style.display='none'">Cerrar</button>
                    <button id="pdf-send-btn" class="btn btn-primary btn-sm" onclick="notifyWorkshop(${data.audit_id})" style="display:none;">Confirmar y Enviar al Taller</button>
                </div>
            </div>
            <iframe id="pdf-iframe" style="width:100%; height:560px; border:none; border-radius:4px; background:white;"></iframe>
        </div>
        <div class="grid-3-1" style="margin-bottom:24px">
            <div class="card">
                <div class="card-header"><h2>Items de la Factura</h2></div>
                <div class="card-body table-wrap">
                    <table>
                        <thead><tr><th>Codigo</th><th>Descripcion</th><th>Categoria</th><th>Cant.</th><th>P. Unitario</th><th>P. Tarifario</th><th>Total</th></tr></thead>
                        <tbody>
                            ${data.items.map(i => {
                                const isOver = i.tariff_price && i.unit_price > i.tariff_price * (1 + (i.tariff_tolerance || 10) / 100);
                                return `<tr>
                                    <td><span style="font-family:var(--font-mono);color:var(--text-muted)">${i.code || '-'}</span></td>
                                    <td>${i.description}</td>
                                    <td><span class="cat-tag cat-${i.category || 'general'}">${i.category || 'general'}</span></td>
                                    <td>${i.quantity}</td>
                                    <td class="${isOver ? 'price-over' : ''}">$${i.unit_price.toFixed(2)}</td>
                                    <td class="price-tariff">${i.tariff_price ? '$' + i.tariff_price.toFixed(2) : '-'}</td>
                                    <td>$${i.total_price.toFixed(2)}</td>
                                </tr>`;
                            }).join("")}
                        </tbody>
                        <tfoot>
                            <tr><td colspan="6" style="text-align:right;font-weight:600">Subtotal</td><td>$${data.invoice_subtotal.toFixed(2)}</td></tr>
                            <tr><td colspan="6" style="text-align:right;font-weight:600">IVA</td><td>$${data.invoice_iva.toFixed(2)}</td></tr>
                            <tr><td colspan="6" style="text-align:right;font-weight:700;font-size:1rem">Total</td><td style="font-weight:700;font-size:1rem">$${data.invoice_total.toFixed(2)}</td></tr>
                        </tfoot>
                    </table>
                </div>
            </div>
            <div class="card">
                <div class="card-header"><h2>Score de Riesgo</h2></div>
                <div class="card-body" style="display:flex;flex-direction:column;align-items:center;padding:30px">
                    <div class="risk-gauge">
                        <svg width="120" height="120" viewBox="0 0 120 120">
                            <circle cx="60" cy="60" r="45" fill="none" stroke="rgba(0,0,0,0.05)" stroke-width="10"/>
                            <circle cx="60" cy="60" r="45" fill="none" stroke="${riskColor}" stroke-width="10" stroke-dasharray="${dashLen} ${circumference - dashLen}" stroke-linecap="round" style="transition:stroke-dasharray 0.8s ease"/>
                        </svg>
                        <div class="risk-gauge-label">
                            <div class="risk-gauge-value" style="color:${riskColor}">${data.risk_score.toFixed(0)}</div>
                            <div class="risk-gauge-text">Riesgo</div>
                        </div>
                    </div>
                    <div style="margin-top:20px;text-align:center">
                        <div style="margin-bottom:8px">${renderStatusBadge(data.status)}</div>
                        <div style="font-size:0.8rem;color:var(--text-muted)">Sobrecobro detectado:</div>
                        <div style="font-size:1.3rem;font-weight:800;color:var(--accent-rose)">$${data.total_overcharge.toFixed(2)}</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="card">
            <div class="card-header"><h2>Hallazgos del Agente (${data.findings.length})</h2></div>
            <div class="card-body">
                ${data.findings.length === 0 ? '<div class="empty-state"><h3>Sin hallazgos — factura limpia</h3></div>' : ''}
                ${data.findings.map(f => `
                    <div class="finding-card ${f.severity}">
                        <div class="finding-header">
                            <div class="finding-title">${f.title}</div>
                            <span class="badge badge-${f.severity}">${f.severity.toUpperCase()}</span>
                        </div>
                        <div class="finding-description">${f.description}</div>
                        <div class="finding-meta">
                            ${f.expected_value ? `<div class="finding-meta-item">Esperado: <span>${f.expected_value}</span></div>` : ''}
                            ${f.actual_value ? `<div class="finding-meta-item">Real: <span>${f.actual_value}</span></div>` : ''}
                            ${f.difference ? `<div class="finding-meta-item">Diferencia: <span style="color:var(--accent-rose)">$${f.difference.toFixed(2)}</span></div>` : ''}
                        </div>
                        ${f.recommendation ? `<div class="finding-recommendation">${f.recommendation}</div>` : ''}
                    </div>
                `).join("")}
            </div>
        </div>
    `;
}

export async function auditAction(auditId, action) {
    const result = await apiPost(`/audit-results/${auditId}/${action}`);
    if (result) {
        const labels = { approve: "Aprobada", reject: "Rechazada", escalate: "Escalada" };
        showToast(`Auditoría ${labels[action]} correctamente`, "success");
        if (typeof window.navigateTo === "function") window.navigateTo("auditorias");
        else location.hash = "auditorias";
    }
}

export async function previewReport(auditId, type = "internal") {
    showToast(type === "workshop" ? "Generando notificación al taller..." : "Generando reporte interno...", "info");
    const container = document.getElementById("pdf-preview-container");
    const iframe = document.getElementById("pdf-iframe");
    const title = document.getElementById("pdf-preview-title");
    const sendBtn = document.getElementById("pdf-send-btn");
    if (title) title.textContent = type === "workshop" ? "Vista Previa — Notificación al Taller" : "Vista Previa — Reporte Interno";
    if (sendBtn) sendBtn.style.display = type === "workshop" ? "" : "none";
    iframe.src = `${API}/audit-results/${auditId}/report-preview?type=${type}&t=${Date.now()}`;
    container.style.display = "block";
    container.scrollIntoView({ behavior: "smooth", block: "start" });
}

export async function notifyWorkshop(auditId) {
    showToast("Enviando reporte...", "info");
    const result = await apiPost(`/audit-results/${auditId}/notify`);
    if (result) {
        showToast(result.message, "success");
        document.getElementById("pdf-preview-container").style.display = "none";
    }
}

export async function reAuditWith(invoiceId, engine) {
    const label = engine === "gemini" ? "IA Gemini" : "Reglas";
    showToast(`Re-auditando con ${label}...`, "info");
    const path = engine === "gemini" ? `/audit-ai/${invoiceId}` : `/audit-rules/${invoiceId}`;
    const result = await apiPost(path);
    if (result) {
        showToast(`Resultado actualizado (motor: ${engine}). audit_id sin cambios.`, "success");
        location.hash = `audit/${result.audit_id}`;
        // force reload since hash may not change if same audit_id
        loadAuditDetail(result.audit_id);
    }
}
