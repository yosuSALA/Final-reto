// Toast, animations, badge renderers
export function showToast(msg, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

export function animateCounter(el, target, prefix = "", suffix = "", decimals = 0) {
    const duration = 800;
    const start = performance.now();
    const from = 0;
    function update(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);
        const current = from + (target - from) * ease;
        el.textContent = prefix + current.toFixed(decimals) + suffix;
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

export function renderRiskBadge(score) {
    let cls = "success", label = "Bajo";
    if (score >= 70) { cls = "critical"; label = "Alto"; }
    else if (score >= 30) { cls = "warning"; label = "Medio"; }
    return `<span class="badge badge-${cls}">${score.toFixed(0)} - ${label}</span>`;
}

export function renderStatusBadge(status) {
    const map = {
        approved: { cls: "success", label: "Aprobado" },
        completed: { cls: "warning", label: "Completado" },
        escalated: { cls: "escalated", label: "Escalado" },
        rejected: { cls: "critical", label: "Rechazado" },
        pending: { cls: "info", label: "Pendiente" },
        in_progress: { cls: "info", label: "En Proceso" },
    };
    const s = map[status] || { cls: "info", label: status };
    return `<span class="badge badge-${s.cls}">${s.label}</span>`;
}

export function renderEngineBadge(engine) {
    if (!engine) return "";
    const isAI = engine === "gemini";
    return `<span class="badge ${isAI ? "badge-info" : "badge-success"}" title="Motor de auditoría" style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.5px;">${isAI ? "IA" : "REGLAS"}</span>`;
}

export function renderTestBadge(isTest) {
    if (!isTest) return "";
    return `<span class="badge badge-warning" style="font-size:0.65rem;background:#94a3b8;color:white;" title="Factura de prueba">TEST</span>`;
}
