import { apiPost, API } from "../api.js";
import { showToast } from "../utils.js";

export async function loadPendingDetail(invoiceId) {
    const page = document.getElementById("page-audit-detail");
    page.classList.add("active");
    page.innerHTML = `
        <button class="back-btn" onclick="navigateTo('auditorias')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            Volver a Pendientes
        </button>
        <div class="detail-header" style="justify-content:center; flex-direction:column; align-items:center; padding:40px 24px; text-align:center;">
            <h1>Factura #${invoiceId} lista para auditoría</h1>
            <p style="color:var(--text-muted); margin-bottom:24px;">Elige el motor de auditoría:</p>
            <div style="display:flex;gap:12px;flex-wrap:wrap;justify-content:center;">
                <button class="btn btn-success" id="btn-jit-rules" onclick="triggerRulesAudit(${invoiceId})" style="font-size:1.05rem; padding:12px 24px;">
                    ⚡ Auditar con Reglas (rápido, 1-2s)
                </button>
                <button class="btn btn-primary" id="btn-jit-ai" onclick="triggerJitAudit(${invoiceId})" style="font-size:1.05rem; padding:12px 24px;">
                    🤖 Auditar con Agente de IA
                </button>
            </div>
            <p style="color:var(--text-muted); font-size:0.8rem; margin-top:14px;">
                Reglas usa el motor determinístico (tarifario + cantidades + duplicados + coherencia).<br>
                El agente de IA añade razonamiento avanzado con DeepSeek v4 Flash.
            </p>
        </div>
    `;
}

export async function triggerRulesAudit(invoiceId) {
    const btn = document.getElementById("btn-jit-rules");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Auditando con reglas...';
    }
    const result = await apiPost(`/audit-rules/${invoiceId}`);
    if (result) {
        showToast(`Auditoría rápida completada (motor: reglas)`, "success");
        location.hash = `audit/${result.audit_id}`;
    } else if (btn) {
        btn.disabled = false;
        btn.innerHTML = '⚡ Reintentar con Reglas';
    }
}

export async function triggerJitAudit(invoiceId) {
    const btn = document.getElementById("btn-jit-ai");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Auditando con IA...';
    }
    const result = await apiPost(`/audit-ai/${invoiceId}`);
    if (result) {
        showToast("Auditoría IA completada", "success");
        location.hash = `audit/${result.audit_id}`;
    } else if (btn) {
        btn.disabled = false;
        btn.innerHTML = '🤖 Reintentar con IA';
    }
}
