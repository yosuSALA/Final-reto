import { apiFetch } from "../api.js";

let isCollapsed = localStorage.getItem("auditQueueCollapsed") === "1";

function getWidget() {
    return document.getElementById("audit-queue-widget");
}

function getTopRunButton() {
    return document.getElementById("btn-run-audit");
}

function setTopRunButtonState(pendingCount) {
    const btn = getTopRunButton();
    if (!btn) return;
    const disabled = pendingCount === 0;
    btn.disabled = disabled;
    if (disabled) {
        btn.classList.add("btn-disabled");
        btn.title = "No hay facturas pendientes en cola";
    } else {
        btn.classList.remove("btn-disabled");
        btn.title = `Hay ${pendingCount} factura(s) pendiente(s)`;
    }
}

function renderQueue(pending) {
    const widget = getWidget();
    if (!widget) return;

    const count = pending.length;
    widget.hidden = count === 0;
    if (count === 0) {
        widget.innerHTML = "";
        setTopRunButtonState(0);
        return;
    }

    const preview = pending.slice(0, 3).map((inv) => `
        <div class="queue-item">
            <strong>${inv.invoice_number}</strong>
            <span>${inv.claim_number}</span>
        </div>
    `).join("");

    widget.classList.toggle("has-pending", count > 0);
    widget.classList.toggle("is-collapsed", isCollapsed);

    widget.innerHTML = `
        <div class="queue-header">
            <span>Cola de facturas</span>
            <div class="queue-header-actions">
                <span class="queue-count">${count}</span>
                <button class="queue-minimize" onclick="toggleAuditQueueMinimized()" title="${isCollapsed ? "Mostrar cola" : "Minimizar cola"}">${isCollapsed ? "+" : "−"}</button>
            </div>
        </div>
        ${isCollapsed ? "" : `
            <div class="queue-list">${preview}</div>
            <div class="queue-actions">
                <button class="btn btn-ghost btn-sm" onclick="navigateTo('auditorias')">Ver cola</button>
                <button class="btn btn-primary btn-sm" id="queue-run-btn" onclick="runFullAudit()">Auditar con IA</button>
            </div>
        `}
    `;

    setTopRunButtonState(count);
}

export function toggleAuditQueueMinimized() {
    isCollapsed = !isCollapsed;
    localStorage.setItem("auditQueueCollapsed", isCollapsed ? "1" : "0");
    refreshAuditQueue();
}

export async function refreshAuditQueue() {
    const pending = await apiFetch("/invoices/pending?include_test=1");
    if (!pending) return;
    renderQueue(pending);
}
