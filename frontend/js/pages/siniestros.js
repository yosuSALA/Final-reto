import { apiFetch, apiPost } from "../api.js";
import { state } from "../state.js";
import { renderRiskBadge, renderStatusBadge, showToast } from "../utils.js";

export async function loadSiniestros() {
    state.claimsData = await apiFetch("/claims") || [];
    renderSiniestrosView();
}

export function renderSiniestrosView() {
    const page = document.getElementById("page-siniestros");
    page.innerHTML = `
        <div class="page-header">
            <h1>Siniestros</h1>
            <p>Siniestros reportados y su estado. Expanda cada fila para ver facturas y configurar destinatarios de notificación.</p>
        </div>
        <div class="card">
            <div class="card-body table-wrap">
                <table>
                    <thead><tr>
                        <th style="width:24px"></th>
                        <th>Numero</th><th>Tipo</th><th>Vehiculo</th><th>Placa</th>
                        <th>Asegurado</th><th>Poliza</th><th>Facturas</th>
                        <th>Estado Auditoria</th><th>Riesgo</th><th></th>
                    </tr></thead>
                    <tbody>
                        ${state.claimsData.map(c => renderClaimRow(c)).join("")}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Modal destinatarios -->
        <div id="notify-modal" style="display:none; position:fixed; inset:0; z-index:500; background:rgba(0,0,0,0.4); backdrop-filter:blur(4px); display:none; align-items:center; justify-content:center;">
            <div style="background:var(--bg-secondary); border:1px solid var(--border-primary); border-radius:16px; padding:28px; width:100%; max-width:480px; box-shadow:var(--shadow-lg);">
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
    `;
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
