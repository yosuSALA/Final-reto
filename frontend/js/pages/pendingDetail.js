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
            <p style="color:var(--text-muted); margin-bottom:24px;">Motor predeterminado: IA DeepSeek. Usa reglas solo si quieres forzar revisión determinística.</p>
            <div style="display:flex;gap:12px;flex-wrap:wrap;justify-content:center;">
                <button class="btn btn-primary" id="btn-jit-ai" onclick="triggerJitAudit(${invoiceId})" style="font-size:1.05rem; padding:12px 24px;">
                    Auditar con IA DeepSeek
                </button>
                <button class="btn btn-ghost" id="btn-jit-rules" onclick="triggerRulesAudit(${invoiceId})" style="font-size:0.95rem; padding:12px 20px;">
                    Usar reglas manualmente
                </button>
            </div>
            <div id="jit-audit-status" style="display:none;margin-top:18px;padding:12px 14px;border-radius:8px;background:rgba(99,102,241,0.08);color:var(--accent-indigo);font-weight:600;"></div>
            <p style="color:var(--text-muted); font-size:0.8rem; margin-top:14px;">
                La IA añade razonamiento avanzado con DeepSeek v4 Flash. Reglas es fallback/manual.
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
    setJitStatus("Auditando manualmente con motor de reglas...");
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
    setJitStatus("DeepSeek está auditando la factura. No cierres esta pantalla...");
    const result = await apiPost(`/audit-ai/${invoiceId}`);
    if (result) {
        setJitStatus("Auditoría IA completada. Abriendo resultado actualizado...");
        showToast("Auditoría IA completada", "success");
        location.hash = `audit/${result.audit_id}`;
    } else if (btn) {
        btn.disabled = false;
        btn.innerHTML = '🤖 Reintentar con IA';
    }
}

function setJitStatus(message) {
    const el = document.getElementById("jit-audit-status");
    if (!el) return;
    el.style.display = "block";
    el.innerHTML = `<span class="spinner"></span> ${message}`;
}
