import { state } from "./state.js";
import { fetchProfiles, createProfile, fetchProfileToken } from "./api.js";

// ── Role System ────────────────────────────────────────

const ROLE_LABELS = {
    demo_jurado:  { label: "Demo / Jurado",        icon: "⭐", color: "#6366f1" },
    analista:     { label: "Analista de Siniestros", icon: "📋", color: "#0ea5e9" },
    antifraude:   { label: "Anti-Fraude",           icon: "🔍", color: "#ef4444" },
    jefatura:     { label: "Jefatura",              icon: "📊", color: "#f59e0b" },
    auditoria:    { label: "Auditoría",             icon: "✅", color: "#10b981" },
};

export function getRoleLabel(role) {
    return ROLE_LABELS[role] || ROLE_LABELS.analista;
}

export function detectRole(profileName) {
    const n = (profileName || "").toLowerCase();
    if (n.includes("jurado") || n.includes("demo")) return "demo_jurado";
    if (n.includes("antifraude") || n.includes("fraude") || n.includes("fraud")) return "antifraude";
    if (n.includes("jefatura") || n.includes("jefe") || n.includes("gerente") || n.includes("director")) return "jefatura";
    if (n.includes("auditoria") || n.includes("auditor") || n.includes("audit")) return "auditoria";
    if (n.includes("analista") || n.includes("analyst")) return "analista";
    return "analista";
}

export function getPermissions() {
    const role = state.currentRole || "analista";
    const map = {
        demo_jurado: {
            canRunAuditAll: true, canRunGemini: true,
            canViewFraud: true, canViewPortfolio: true,
            canViewCustomers: true, canViewAudit: true,
            canNotify: false, canReviewDecision: false, canManageTariff: false,
        },
        analista: {
            canRunAuditAll: false, canRunGemini: false,
            canViewFraud: false, canViewPortfolio: false,
            canViewCustomers: true, canViewAudit: false,
            canNotify: true, canReviewDecision: true, canManageTariff: false,
        },
        antifraude: {
            canRunAuditAll: true, canRunGemini: true,
            canViewFraud: true, canViewPortfolio: false,
            canViewCustomers: true, canViewAudit: false,
            canNotify: true, canReviewDecision: true, canManageTariff: false,
        },
        jefatura: {
            canRunAuditAll: true, canRunGemini: true,
            canViewFraud: true, canViewPortfolio: true,
            canViewCustomers: true, canViewAudit: true,
            canNotify: false, canReviewDecision: false, canManageTariff: true,
        },
        auditoria: {
            canRunAuditAll: true, canRunGemini: true,
            canViewFraud: true, canViewPortfolio: true,
            canViewCustomers: true, canViewAudit: true,
            canNotify: false, canReviewDecision: false, canManageTariff: false,
        },
    };
    return map[role] || map.analista;
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

export function clearProfileSession() {
    state.currentProfileId = null;
    state.currentProfileName = null;
    state.currentProfileToken = null;
    state.currentRole = "analista";
    localStorage.removeItem("profileId");
    localStorage.removeItem("profileName");
    localStorage.removeItem("profileToken");
    localStorage.removeItem("profileRole");
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
                <p class="profile-modal-sub">Selecciona tu perfil para acceder al sistema</p>
            </div>
            <div class="profile-list" id="profile-list-container">
                <div class="profile-loading">Cargando perfiles...</div>
            </div>
            <div class="profile-modal-divider">
                <span>o crea uno nuevo</span>
            </div>
            <div class="profile-create-form">
                <input
                    type="text"
                    id="new-profile-name"
                    class="profile-name-input"
                    placeholder="Nombre del perfil (ej: María Analista)"
                    maxlength="80"
                />
                <select id="new-profile-role" class="profile-role-select">
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
        if (e.key === "Enter") handleCreateProfile();
    });
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
        return `
        <button class="profile-item" data-id="${p.id}" data-name="${p.display_name || p.name}" data-role="${role}">
            <div class="profile-avatar" style="background:${roleInfo.color}22;color:${roleInfo.color}">${roleInfo.icon}</div>
            <div class="profile-item-info">
                <span class="profile-item-name">${p.display_name || p.name}</span>
                <span class="profile-item-role" style="color:${roleInfo.color}">${roleInfo.label}</span>
            </div>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
        </button>`;
    }).join("");

    container.querySelectorAll(".profile-item").forEach(btn => {
        btn.addEventListener("click", () =>
            handleSelectProfile(btn.dataset.id, btn.dataset.name, btn.dataset.role)
        );
    });
}

async function handleSelectProfile(profileId, profileName, roleHint) {
    showProfileError("");
    const password = prompt(`Contraseña para acceder a ${profileName}:`);
    if (password === null) return;
    try {
        const data = await fetchProfileToken(profileId, password);
        const role = data.role || roleHint || detectRole(data.display_name || data.name);
        saveProfileSession(data.profile_id, data.display_name || data.name, data.token, role);
        dismissProfileSelector();
        window.dispatchEvent(new CustomEvent("profile:selected", { detail: { name: profileName, role } }));
    } catch (e) {
        showProfileError("No se pudo conectar con el perfil: " + e.message);
    }
}

async function handleCreateProfile() {
    const input = document.getElementById("new-profile-name");
    const roleSelect = document.getElementById("new-profile-role");
    const name = (input?.value || "").trim();
    if (!name) {
        showProfileError("Escribe un nombre para el perfil.");
        return;
    }
    const role = roleSelect?.value || "analista";
    showProfileError("");

    const btn = document.getElementById("btn-create-profile");
    btn.disabled = true;
    btn.textContent = "Creando...";

    try {
        const data = await createProfile(name, role);
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
        roleBadge.textContent = roleInfo.icon + " " + roleInfo.label;
        roleBadge.style.color = roleInfo.color;
    }
}

export function applyProfileUI() {
    updateProfileBadge();
}

export function setProfile(profile) {
    // mantener compatibilidad legada
}
