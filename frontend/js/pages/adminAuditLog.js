// Panel admin: log inmutable de acciones del sistema y gestor de perfiles.
import { fetchAuditLog, fetchAuditLogStats, fetchProfiles } from "../api.js";
import { state } from "../state.js";
import { getRoleLabel, adminDeleteProfile, isAdmin } from "../auth.js";
import { showToast } from "../utils.js";

const ACTION_LABELS = {
    login:              { label: "Login",                    color: "#10b981", icon: "🔑" },
    login_via_admin:    { label: "Login (modo admin)",       color: "#dc2626", icon: "🛡" },
    login_failed:       { label: "Login fallido",            color: "#f59e0b", icon: "⚠" },
    admin_login:        { label: "Admin login",              color: "#dc2626", icon: "🛡" },
    admin_login_failed: { label: "Admin login fallido",      color: "#dc2626", icon: "⚠" },
    profile_created:    { label: "Perfil creado",            color: "#0ea5e9", icon: "➕" },
    profile_deleted:    { label: "Perfil eliminado",         color: "#ef4444", icon: "🗑" },
    password_changed:   { label: "Contraseña cambiada",      color: "#a855f7", icon: "🔒" },
    http_write:         { label: "Acción de escritura",      color: "#6366f1", icon: "✏" },
};

function actionInfo(action) {
    return ACTION_LABELS[action] || { label: action || "(desconocido)", color: "#64748b", icon: "•" };
}

function fmtTimestamp(ts) {
    if (!ts) return "—";
    try {
        const d = new Date(ts);
        return d.toLocaleString("es-EC", {
            year: "numeric", month: "2-digit", day: "2-digit",
            hour: "2-digit", minute: "2-digit", second: "2-digit",
        });
    } catch (e) {
        return ts;
    }
}

function statusBadge(code) {
    if (!code) return "";
    let color = "#64748b";
    if (code >= 500) color = "#dc2626";
    else if (code >= 400) color = "#f59e0b";
    else if (code >= 200 && code < 300) color = "#10b981";
    return `<span style="font-family:var(--font-mono); font-size:0.72rem; color:white; background:${color}; padding:1px 6px; border-radius:4px;">${code}</span>`;
}

export async function loadAdminAuditLog() {
    if (!isAdmin()) {
        showToast("Acceso restringido al administrador.", "error");
        return;
    }
    const page = document.getElementById("page-admin-audit");
    if (!page) return;
    page.innerHTML = `<div style="padding:48px; text-align:center; color:var(--text-muted);">Cargando log de auditoría...</div>`;

    const [stats, log, profiles] = await Promise.all([
        fetchAuditLogStats(),
        fetchAuditLog({
            limit: 200,
            action: state.auditLogFilter?.action || "",
            profileId: state.auditLogFilter?.profileId || "",
        }),
        fetchProfiles(),
    ]);

    renderAdminAuditPage(page, stats, log, profiles || []);
}

function renderAdminAuditPage(page, stats, log, profiles) {
    const entries = (log && log.entries) || [];
    const total = (log && log.total) || 0;
    const filter = state.auditLogFilter || { action: "", profileId: "" };

    const statTotal = stats?.total ?? 0;
    const byAction = stats?.by_action || [];
    const byRole = stats?.by_role || [];

    page.innerHTML = `
        <div class="page-header">
            <h1>🛡 Panel del Administrador</h1>
            <p>Log inmutable de acciones del sistema y gestión de perfiles.</p>
        </div>

        <div class="kpi-grid" style="grid-template-columns: repeat(auto-fit, minmax(180px,1fr));">
            <div class="kpi-card">
                <div class="kpi-label">Eventos totales</div>
                <div class="kpi-value">${statTotal}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Último evento</div>
                <div class="kpi-value" style="font-size:0.95rem; line-height:1.2;">${fmtTimestamp(stats?.last_event_at)}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Perfiles activos</div>
                <div class="kpi-value">${profiles.length}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Acciones por admin</div>
                <div class="kpi-value">${(byAction.find(a => a.action === "http_write")?.count) || 0}</div>
            </div>
        </div>

        <div class="grid-2" style="display:grid; grid-template-columns: 2fr 1fr; gap:18px; margin-top:18px;">
            <div class="card">
                <div class="card-header" style="display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap;">
                    <h2>Log de auditoría (${entries.length} de ${total})</h2>
                    <div style="display:flex; gap:8px; flex-wrap:wrap;">
                        <select id="audit-filter-action" class="profile-role-select" style="min-width:170px;">
                            <option value="">— Todas las acciones —</option>
                            ${Object.entries(ACTION_LABELS).map(([k, v]) => `
                                <option value="${k}" ${filter.action === k ? "selected" : ""}>${v.icon} ${v.label}</option>
                            `).join("")}
                        </select>
                        <select id="audit-filter-profile" class="profile-role-select" style="min-width:180px;">
                            <option value="">— Todos los perfiles —</option>
                            ${profiles.map(p => `
                                <option value="${p.id}" ${filter.profileId === p.id ? "selected" : ""}>${p.display_name || p.name}</option>
                            `).join("")}
                        </select>
                        <button class="btn btn-ghost btn-sm" id="btn-audit-clear">Limpiar</button>
                        <button class="btn btn-primary btn-sm" id="btn-audit-refresh">↻ Refrescar</button>
                    </div>
                </div>
                <div class="card-body" style="padding:0;">
                    ${entries.length === 0 ? `
                        <div style="padding:32px; text-align:center; color:var(--text-muted);">Sin entradas para este filtro.</div>
                    ` : `
                    <table style="width:100%;">
                        <thead>
                            <tr>
                                <th>Cuándo</th>
                                <th>Perfil</th>
                                <th>Rol</th>
                                <th>Acción</th>
                                <th>Método / Ruta</th>
                                <th>Estado</th>
                                <th>Detalle</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${entries.map(e => {
                                const info = actionInfo(e.action);
                                const roleInfo = getRoleLabel(e.role || "analista");
                                const adminMark = e.actor_admin ? `<span title="Acción ejecutada por admin" style="color:#dc2626; font-weight:700;">🛡</span> ` : "";
                                return `
                                <tr>
                                    <td style="white-space:nowrap; font-family:var(--font-mono); font-size:0.78rem;">${fmtTimestamp(e.timestamp)}</td>
                                    <td>${adminMark}${e.profile_name || "(sin perfil)"}</td>
                                    <td><span style="color:${roleInfo.color}; font-weight:600;">${roleInfo.icon} ${roleInfo.label}</span></td>
                                    <td><span style="color:${info.color}; font-weight:600;">${info.icon} ${info.label}</span></td>
                                    <td style="font-family:var(--font-mono); font-size:0.78rem; max-width:280px; overflow:hidden; text-overflow:ellipsis;" title="${(e.method || "")} ${(e.path || "")}">
                                        ${e.method ? `<strong>${e.method}</strong> ` : ""}${e.path || ""}
                                    </td>
                                    <td>${statusBadge(e.status_code)}</td>
                                    <td style="font-size:0.78rem; color:var(--text-muted);">${e.detail || ""}</td>
                                </tr>`;
                            }).join("")}
                        </tbody>
                    </table>
                    `}
                </div>
            </div>

            <div class="card">
                <div class="card-header"><h2>Gestión de perfiles</h2></div>
                <div class="card-body" style="display:flex; flex-direction:column; gap:8px;">
                    ${profiles.map(p => {
                        const role = p.role || "analista";
                        const roleInfo = getRoleLabel(role);
                        const isProtected = p.is_admin || role === "demo_jurado";
                        return `
                        <div class="admin-profile-row" style="display:flex; justify-content:space-between; align-items:center; padding:10px; border:1px solid var(--border-color, #e2e8f0); border-radius:8px;">
                            <div style="display:flex; align-items:center; gap:10px;">
                                <div class="profile-avatar" style="background:${roleInfo.color}22;color:${roleInfo.color}; width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center;">${roleInfo.icon}</div>
                                <div>
                                    <div style="font-weight:600;">${p.display_name || p.name}</div>
                                    <div style="font-size:0.75rem; color:${roleInfo.color};">${roleInfo.label} ${p.has_password ? "" : "<span style='color:#f59e0b'>· sin clave</span>"}</div>
                                </div>
                            </div>
                            ${isProtected ? `
                                <span class="badge" style="background:#cbd5e1; color:#475569;">${p.is_admin ? "Admin" : "Protegido"}</span>
                            ` : `
                                <button class="btn btn-danger btn-sm" data-delete-id="${p.id}" data-delete-name="${p.display_name || p.name}">🗑 Eliminar</button>
                            `}
                        </div>`;
                    }).join("")}
                </div>
            </div>
        </div>
    `;

    document.getElementById("audit-filter-action")?.addEventListener("change", (e) => {
        state.auditLogFilter = { ...(state.auditLogFilter || {}), action: e.target.value };
        loadAdminAuditLog();
    });
    document.getElementById("audit-filter-profile")?.addEventListener("change", (e) => {
        state.auditLogFilter = { ...(state.auditLogFilter || {}), profileId: e.target.value };
        loadAdminAuditLog();
    });
    document.getElementById("btn-audit-clear")?.addEventListener("click", () => {
        state.auditLogFilter = { action: "", profileId: "" };
        loadAdminAuditLog();
    });
    document.getElementById("btn-audit-refresh")?.addEventListener("click", loadAdminAuditLog);

    page.querySelectorAll("[data-delete-id]").forEach(btn => {
        btn.addEventListener("click", async () => {
            const id = btn.dataset.deleteId;
            const name = btn.dataset.deleteName;
            const ok = await adminDeleteProfile(id, name);
            if (ok) loadAdminAuditLog();
        });
    });
}
