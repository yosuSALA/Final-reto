import { state } from "./state.js";
import {
    fetchProfiles, createProfile, fetchProfileToken,
    adminLogin, deleteProfileById,
} from "./api.js";
import { showToast } from "./utils.js";

// ── Role System ────────────────────────────────────────

const ROLE_LABELS = {
    admin:        { label: "Administrador",          icon: "🛡", color: "#dc2626" },
    demo_jurado:  { label: "Demo / Jurado",          icon: "⭐", color: "#6366f1" },
    analista:     { label: "Analista de Siniestros", icon: "📋", color: "#0ea5e9" },
    antifraude:   { label: "Anti-Fraude",            icon: "🔍", color: "#ef4444" },
    jefatura:     { label: "Jefatura",               icon: "📊", color: "#f59e0b" },
    auditoria:    { label: "Auditoría",              icon: "✅", color: "#10b981" },
    operaciones:  { label: "Operaciones",            icon: "🛠", color: "#0284c7" },
    costos:       { label: "Costos",                 icon: "💲", color: "#a855f7" },
    contabilidad: { label: "Contabilidad",           icon: "📒", color: "#14b8a6" },
    legal:        { label: "Legal",                  icon: "⚖", color: "#475569" },
};

export function getRoleLabel(role) {
    return ROLE_LABELS[role] || ROLE_LABELS.analista;
}

export function detectRole(profileName) {
    const n = (profileName || "").toLowerCase();
    if (n === "admin" || n.includes("administrador")) return "admin";
    if (n.includes("jurado") || n.includes("demo")) return "demo_jurado";
    if (n.includes("antifraude") || n.includes("fraude") || n.includes("fraud")) return "antifraude";
    if (n.includes("jefatura") || n.includes("jefe") || n.includes("gerente") || n.includes("director")) return "jefatura";
    if (n.includes("auditoria") || n.includes("auditor") || n.includes("audit")) return "auditoria";
    if (n.includes("operacion") || n.includes("ops")) return "operaciones";
    if (n.includes("costos") || n.includes("costo")) return "costos";
    if (n.includes("contabilidad") || n.includes("contador") || n.includes("contable")) return "contabilidad";
    if (n.includes("legal") || n.includes("abogad")) return "legal";
    if (n.includes("analista") || n.includes("analyst")) return "analista";
    return "analista";
}

export function isAdmin() {
    return state.currentRole === "admin" || state.adminMode === true;
}

export function getPermissions() {
    const role = state.currentRole || "analista";
    const map = {
        admin: {
            canRunAuditAll: true, canRunAI: true,
            canViewFraud: true, canViewPortfolio: true,
            canViewCustomers: true, canViewAudit: true,
            canRegisterClaim: true, canManageTariff: true,
            canApproveInitial: true, canEscalate: true,
            canFinalDecision: true, canViewLegalNotifications: true,
            canReviewDecision: true,
            canViewSystemAudit: true,
            canDeleteProfiles: true,
        },
        demo_jurado: {
            canRunAuditAll: true, canRunAI: true,
            canViewFraud: true, canViewPortfolio: true,
            canViewCustomers: true, canViewAudit: true,
            canRegisterClaim: true, canManageTariff: true,
            canApproveInitial: true, canEscalate: true,
            canFinalDecision: true, canViewLegalNotifications: true,
            canReviewDecision: true,
        },
        analista: {
            canRunAuditAll: false, canRunAI: false,
            canViewFraud: false, canViewPortfolio: false,
            canViewCustomers: true, canViewAudit: false,
            canRegisterClaim: false, canManageTariff: false,
            canApproveInitial: false, canEscalate: false,
            canFinalDecision: false, canViewLegalNotifications: false,
            canReviewDecision: false,
        },
        antifraude: {
            canRunAuditAll: true, canRunAI: true,
            canViewFraud: true, canViewPortfolio: false,
            canViewCustomers: true, canViewAudit: false,
            canRegisterClaim: false, canManageTariff: false,
            canApproveInitial: false, canEscalate: false,
            canFinalDecision: false, canViewLegalNotifications: false,
            canReviewDecision: false,
        },
        jefatura: {
            canRunAuditAll: true, canRunAI: true,
            canViewFraud: true, canViewPortfolio: true,
            canViewCustomers: true, canViewAudit: true,
            canRegisterClaim: false, canManageTariff: false,
            canApproveInitial: false, canEscalate: false,
            canFinalDecision: true, canViewLegalNotifications: false,
            canReviewDecision: false,
        },
        auditoria: {
            canRunAuditAll: true, canRunAI: true,
            canViewFraud: true, canViewPortfolio: true,
            canViewCustomers: true, canViewAudit: true,
            canRegisterClaim: false, canManageTariff: false,
            canApproveInitial: false, canEscalate: false,
            canFinalDecision: false, canViewLegalNotifications: false,
            canReviewDecision: false,
        },
        operaciones: {
            canRunAuditAll: false, canRunAI: false,
            canViewFraud: false, canViewPortfolio: false,
            canViewCustomers: true, canViewAudit: false,
            canRegisterClaim: true, canManageTariff: false,
            canApproveInitial: false, canEscalate: false,
            canFinalDecision: false, canViewLegalNotifications: false,
            canReviewDecision: false,
        },
        costos: {
            canRunAuditAll: false, canRunAI: false,
            canViewFraud: false, canViewPortfolio: false,
            canViewCustomers: true, canViewAudit: true,
            canRegisterClaim: false, canManageTariff: true,
            canApproveInitial: true, canEscalate: true,
            canFinalDecision: false, canViewLegalNotifications: false,
            canReviewDecision: false,
        },
        contabilidad: {
            canRunAuditAll: false, canRunAI: false,
            canViewFraud: false, canViewPortfolio: false,
            canViewCustomers: true, canViewAudit: true,
            canRegisterClaim: false, canManageTariff: true,
            canApproveInitial: true, canEscalate: true,
            canFinalDecision: false, canViewLegalNotifications: false,
            canReviewDecision: false,
        },
        legal: {
            canRunAuditAll: false, canRunAI: false,
            canViewFraud: false, canViewPortfolio: false,
            canViewCustomers: false, canViewAudit: false,
            canRegisterClaim: false, canManageTariff: false,
            canApproveInitial: false, canEscalate: false,
            canFinalDecision: false, canViewLegalNotifications: true,
            canReviewDecision: false,
        },
    };
    const base = map[role] || map.analista;
    // Modo admin engaged sobre un perfil prestado: hereda permisos del perfil
    // pero conserva la capacidad de ver el log de auditoría y borrar perfiles.
    if (state.adminMode) {
        return { ...base, canViewSystemAudit: true, canDeleteProfiles: true };
    }
    return base;
}

// ── Persistencia de sesión ─────────────────────────────

export function saveProfileSession(id, name, token, role) {
    const resolvedRole = role || detectRole(name);
    state.currentProfileId = id;
    state.currentProfileName = name;
    state.currentProfileToken = token;
    state.currentRole = resolvedRole;
    localStorage.setItem("profileId", id);
    localStorage.setItem("profileName", name);
    localStorage.setItem("profileToken", token);
    localStorage.setItem("profileRole", resolvedRole);
}

export function setAdminSession(token, isAdminProfile) {
    state.adminToken = token;
    state.adminMode = !!isAdminProfile;
    if (token) localStorage.setItem("adminToken", token); else localStorage.removeItem("adminToken");
    if (state.adminMode) localStorage.setItem("adminMode", "1"); else localStorage.removeItem("adminMode");
}

export function clearProfileSession() {
    state.currentProfileId = null;
    state.currentProfileName = null;
    state.currentProfileToken = null;
    state.currentRole = "analista";
    state.adminToken = null;
    state.adminMode = false;
    localStorage.removeItem("profileId");
    localStorage.removeItem("profileName");
    localStorage.removeItem("profileToken");
    localStorage.removeItem("profileRole");
    localStorage.removeItem("adminToken");
    localStorage.removeItem("adminMode");
}

export function hasActiveSession() {
    return !!(state.currentProfileToken && state.currentProfileId);
}

// ── UI del selector de perfil ──────────────────────────

export function showProfileSelector() {
    const existing = document.getElementById("profile-selector-overlay");
    if (existing) existing.remove();

    const overlay = document.createElement("div");
    overlay.id = "profile-selector-overlay";
    overlay.innerHTML = `
        <div class="profile-modal">
            <div class="profile-modal-header">
                <div class="profile-modal-logo">
                    <svg width="32" height="32" viewBox="0 0 28 28" fill="none">
                        <rect width="28" height="28" rx="8" fill="url(#pm-grad)"/>
                        <path d="M8 14L12 18L20 10" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                        <defs><linearGradient id="pm-grad" x1="0" y1="0" x2="28" y2="28"><stop stop-color="#6366f1"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs>
                    </svg>
                </div>
                <h2>Plataforma de Inteligencia</h2>
                <p class="profile-modal-sub">Inicia sesión con tu perfil</p>
            </div>

            <div id="admin-mode-banner" class="profile-admin-banner" style="display:${state.adminMode ? "flex" : "none"};">
                <span>🛡 <strong>Modo Admin activo</strong> — puedes saltar entre perfiles sin contraseña</span>
                <button class="btn btn-ghost btn-sm" id="btn-disable-admin">Salir</button>
            </div>

            <div class="profile-list" id="profile-list-container">
                <div class="profile-loading">Cargando perfiles...</div>
            </div>

            <div class="profile-modal-divider">
                <span>Administrador</span>
            </div>
            <details class="profile-admin-section" id="admin-login-section" ${state.adminMode ? "" : ""}>
                <summary class="profile-admin-toggle">🛡 Acceder con clave maestra (modo testing)</summary>
                <div class="profile-admin-form">
                    <p class="profile-admin-hint">Permite saltar entre perfiles sin contraseñas. Default: <code>admin</code> (configurable vía env <code>ADMIN_PASSWORD</code>).</p>
                    <input type="password" id="admin-master-password" class="profile-name-input" placeholder="Clave maestra" autocomplete="off">
                    <button class="btn btn-danger" id="btn-admin-login">Activar modo admin</button>
                </div>
            </details>

            <div class="profile-modal-divider">
                <span>o crea un perfil nuevo</span>
            </div>
            <div class="profile-create-form">
                <input
                    type="text"
                    id="new-profile-name"
                    class="profile-name-input"
                    placeholder="Nombre del perfil (ej: María Analista)"
                    maxlength="80"
                    autocomplete="off"
                />
                <input
                    type="password"
                    id="new-profile-password"
                    class="profile-name-input"
                    placeholder="Contraseña (mín. 4 caracteres)"
                    autocomplete="new-password"
                />
                <select id="new-profile-role" class="profile-role-select">
                    <option value="operaciones">🛠 Operaciones</option>
                    <option value="costos">💲 Costos</option>
                    <option value="contabilidad">📒 Contabilidad</option>
                    <option value="legal">⚖ Legal</option>
                    <option value="analista">📋 Analista de Siniestros</option>
                    <option value="antifraude">🔍 Anti-Fraude</option>
                    <option value="jefatura">📊 Jefatura</option>
                    <option value="auditoria">✅ Auditoría</option>
                    <option value="demo_jurado">⭐ Demo / Jurado</option>
                </select>
                <button class="btn btn-primary" id="btn-create-profile">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                    Crear perfil
                </button>
            </div>
            <div id="profile-error" class="profile-error" style="display:none;"></div>
        </div>
    `;
    document.body.appendChild(overlay);

    loadProfileList();

    document.getElementById("btn-create-profile").addEventListener("click", handleCreateProfile);
    document.getElementById("new-profile-name").addEventListener("keydown", (e) => {
        if (e.key === "Enter") document.getElementById("new-profile-password")?.focus();
    });
    document.getElementById("new-profile-password").addEventListener("keydown", (e) => {
        if (e.key === "Enter") handleCreateProfile();
    });
    document.getElementById("btn-admin-login").addEventListener("click", handleAdminLogin);
    document.getElementById("admin-master-password").addEventListener("keydown", (e) => {
        if (e.key === "Enter") handleAdminLogin();
    });
    const btnDisableAdmin = document.getElementById("btn-disable-admin");
    if (btnDisableAdmin) {
        btnDisableAdmin.addEventListener("click", () => {
            setAdminSession(null, false);
            showToast("Modo admin desactivado.", "info");
            showProfileSelector(); // re-render
        });
    }
}

export function signOut() {
    clearProfileSession();
    showProfileSelector();
}

async function loadProfileList() {
    const container = document.getElementById("profile-list-container");
    if (!container) return;

    container.innerHTML = '<div class="profile-loading">Cargando perfiles...</div>';
    const profiles = await fetchProfiles();

    if (!profiles || profiles.length === 0) {
        container.innerHTML = '<div class="profile-empty">No hay perfiles aún. Crea el primero.</div>';
        return;
    }

    container.innerHTML = profiles.map(p => {
        const role = p.role || detectRole(p.display_name || p.name);
        const roleInfo = getRoleLabel(role);
        const isAdminProfile = role === "admin";
        const needsPassword = !state.adminMode && !isAdminProfile;
        return `
        <div class="profile-row" data-id="${p.id}" data-name="${p.display_name || p.name}" data-role="${role}" data-admin="${isAdminProfile ? 1 : 0}">
            <button class="profile-item">
                <div class="profile-avatar" style="background:${roleInfo.color}22;color:${roleInfo.color}">${roleInfo.icon}</div>
                <div class="profile-item-info">
                    <span class="profile-item-name">${p.display_name || p.name}</span>
                    <span class="profile-item-role" style="color:${roleInfo.color}">${roleInfo.label}</span>
                </div>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
            <div class="profile-row-password" style="display:none;">
                <input type="password" class="profile-name-input profile-pwd-input" placeholder="${isAdminProfile ? "Clave maestra del admin" : "Contraseña del perfil"}" autocomplete="off">
                <button class="btn btn-primary btn-sm profile-pwd-submit">Entrar</button>
            </div>
        </div>`;
    }).join("");

    container.querySelectorAll(".profile-row").forEach(row => {
        const id = row.dataset.id;
        const name = row.dataset.name;
        const role = row.dataset.role;
        const isAdminProfile = row.dataset.admin === "1";
        const btn = row.querySelector(".profile-item");
        const pwdBox = row.querySelector(".profile-row-password");
        const pwdInput = row.querySelector(".profile-pwd-input");
        const pwdSubmit = row.querySelector(".profile-pwd-submit");

        const handleEnter = async () => {
            const pwd = (pwdInput?.value || "").trim();
            await handleSelectProfile(id, name, role, pwd, { isAdminProfile });
        };

        btn.addEventListener("click", async () => {
            if (state.adminMode && !isAdminProfile) {
                // Switch libre en modo admin
                await handleSelectProfile(id, name, role, "", { viaAdmin: true });
                return;
            }
            if (isAdminProfile) {
                // Toggle inline password
                pwdBox.style.display = pwdBox.style.display === "none" ? "flex" : "none";
                if (pwdBox.style.display === "flex") pwdInput.focus();
                return;
            }
            // Toggle inline password para perfil normal
            pwdBox.style.display = pwdBox.style.display === "none" ? "flex" : "none";
            if (pwdBox.style.display === "flex") pwdInput.focus();
        });

        if (pwdSubmit) pwdSubmit.addEventListener("click", handleEnter);
        if (pwdInput) pwdInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") handleEnter();
        });
    });
}

async function handleSelectProfile(profileId, profileName, roleHint, password, { isAdminProfile = false, viaAdmin = false } = {}) {
    showProfileError("");
    try {
        let data;
        if (isAdminProfile) {
            // Login admin con clave maestra
            data = await adminLogin(password);
            setAdminSession(data.token, true);
        } else {
            data = await fetchProfileToken(profileId, password, { viaAdmin: viaAdmin || state.adminMode });
        }
        const role = data.role || roleHint || detectRole(data.display_name || data.name);
        saveProfileSession(data.profile_id, data.display_name || data.name, data.token, role);
        // Si la persona acaba de loguear como admin, registrar también el admin token
        if (role === "admin") setAdminSession(data.token, true);
        dismissProfileSelector();
        window.dispatchEvent(new CustomEvent("profile:selected", { detail: { name: data.display_name || data.name, role } }));
    } catch (e) {
        showProfileError(e.message || "No se pudo iniciar sesión");
    }
}

async function handleAdminLogin() {
    const input = document.getElementById("admin-master-password");
    const password = (input?.value || "").trim();
    if (!password) {
        showProfileError("Ingresa la clave maestra.");
        return;
    }
    const btn = document.getElementById("btn-admin-login");
    btn.disabled = true;
    const original = btn.textContent;
    btn.textContent = "Validando...";
    try {
        const data = await adminLogin(password);
        setAdminSession(data.token, true);
        saveProfileSession(data.profile_id, data.display_name || data.name, data.token, "admin");
        dismissProfileSelector();
        window.dispatchEvent(new CustomEvent("profile:selected", { detail: { name: data.display_name || data.name, role: "admin" } }));
        showToast("🛡 Modo admin activado — switch libre entre perfiles", "success");
    } catch (e) {
        showProfileError(e.message || "Clave maestra incorrecta");
    } finally {
        btn.disabled = false;
        btn.textContent = original;
    }
}

async function handleCreateProfile() {
    const nameInput = document.getElementById("new-profile-name");
    const pwdInput = document.getElementById("new-profile-password");
    const roleSelect = document.getElementById("new-profile-role");
    const name = (nameInput?.value || "").trim();
    const password = (pwdInput?.value || "").trim();
    if (!name) {
        showProfileError("Escribe un nombre para el perfil.");
        return;
    }
    if (password.length < 4) {
        showProfileError("La contraseña debe tener al menos 4 caracteres.");
        return;
    }
    const role = roleSelect?.value || "analista";
    showProfileError("");

    const btn = document.getElementById("btn-create-profile");
    btn.disabled = true;
    btn.textContent = "Creando...";

    try {
        const data = await createProfile(name, role, password);
        const resolvedRole = data.role || role;
        saveProfileSession(data.id, data.display_name || data.name, data.token, resolvedRole);
        dismissProfileSelector();
        window.dispatchEvent(new CustomEvent("profile:selected", { detail: { name: data.name, role: resolvedRole } }));
    } catch (e) {
        showProfileError(e.message || "Error al crear el perfil.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg> Crear perfil`;
    }
}

function dismissProfileSelector() {
    const overlay = document.getElementById("profile-selector-overlay");
    if (overlay) overlay.remove();
}

function showProfileError(msg) {
    const el = document.getElementById("profile-error");
    if (!el) return;
    el.textContent = msg;
    el.style.display = msg ? "block" : "none";
}

// ── Acciones admin sobre perfiles ──────────────────────────────────────────

export async function adminDeleteProfile(profileId, profileName) {
    if (!state.adminMode && state.currentRole !== "admin") {
        showToast("Solo el administrador puede borrar perfiles.", "error");
        return false;
    }
    const ok = window.confirm(`¿Eliminar el perfil "${profileName}"?\nEsta acción es irreversible.`);
    if (!ok) return false;
    const res = await deleteProfileById(profileId);
    if (res) {
        showToast(`Perfil "${profileName}" eliminado`, "success");
        return true;
    }
    return false;
}

// ── Navbar ─────────────────────────────────────────────

export function updateProfileBadge() {
    const badge = document.getElementById("active-profile-badge");
    if (!badge) return;
    if (state.currentProfileName) {
        const roleInfo = getRoleLabel(state.currentRole);
        badge.textContent = state.currentProfileName;
        badge.title = `${roleInfo.label} — ${state.currentProfileName}`;
    } else {
        badge.textContent = "Sin perfil";
    }

    const roleBadge = document.getElementById("nav-role-badge");
    if (roleBadge && state.currentRole) {
        const roleInfo = getRoleLabel(state.currentRole);
        const prefix = state.adminMode && state.currentRole !== "admin" ? "🛡 " : "";
        roleBadge.textContent = prefix + roleInfo.icon + " " + roleInfo.label;
        roleBadge.style.color = state.adminMode && state.currentRole !== "admin" ? "#dc2626" : roleInfo.color;
    }

    const role = state.currentRole;
    const isDashboardRole = ["jefatura", "demo_jurado", "legal", "admin", "analista", "antifraude", "auditoria"].includes(role);
    const homeLink = document.getElementById("nav-dashboard");
    const homeLabel = document.getElementById("nav-home-label");
    const auditPanelLink = document.getElementById("nav-audit-panel");
    if (homeLink && homeLabel) {
        homeLink.dataset.page = isDashboardRole ? "dashboard" : "audit-panel";
        homeLink.href = isDashboardRole ? "#dashboard" : "#audit-panel";
        homeLabel.textContent = isDashboardRole ? "Dashboard" : "Flujo";
    }
    if (auditPanelLink) {
        auditPanelLink.style.display = (isDashboardRole && role !== "legal") ? "flex" : "none";
        const textNode = Array.from(auditPanelLink.childNodes).find((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
        if (textNode) textNode.textContent = " Flujo";
    }

    // Visibilidad de items del navbar según restricciones por rol
    const perms = getPermissions();
    const uploadLink = document.getElementById("nav-upload");
    if (uploadLink) {
        uploadLink.style.display = (role === "legal") ? "none" : "";
    }
    const tarifarioLink = document.getElementById("nav-tarifario");
    if (tarifarioLink) {
        tarifarioLink.style.display = "";
    }
    const auditLink = document.getElementById("nav-auditorias");
    if (auditLink) {
        auditLink.style.display = (role === "legal") ? "none" : "";
    }
    const sinLink = document.getElementById("nav-siniestros");
    if (sinLink) {
        sinLink.style.display = "";
    }
    const runAuditBtn = document.getElementById("btn-run-audit");
    if (runAuditBtn) {
        runAuditBtn.style.display = perms.canRunAuditAll ? "" : "none";
    }
    // Admin: panel del log de auditoría interna
    const adminLink = document.getElementById("nav-admin-audit");
    if (adminLink) {
        adminLink.style.display = perms.canViewSystemAudit ? "flex" : "none";
    }
    // Botón "Cambiar perfil" disponible en modo admin para switch rápido
    const switchBtn = document.getElementById("btn-switch-profile");
    if (switchBtn) {
        switchBtn.style.display = state.adminMode ? "flex" : "none";
    }
}

export function applyProfileUI() {
    updateProfileBadge();
}

export function setProfile(profile) {
    // mantener compatibilidad legada
}

// ── Triggers públicos ─────────────────────────────────

export function openProfileSwitcher() {
    showProfileSelector();
}
