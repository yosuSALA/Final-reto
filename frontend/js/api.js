// API client + fetch helpers
// Inyecta automáticamente X-Profile-Token en todas las llamadas autenticadas.
import { showToast } from "./utils.js";
import { state } from "./state.js";

export const API = "/api";

function authHeaders(extra = {}) {
    const headers = { ...extra };
    if (state.currentProfileToken) {
        headers["X-Profile-Token"] = state.currentProfileToken;
    }
    return headers;
}

function errorMessage(err, fallback) {
    const detail = err?.detail ?? err?.message ?? err;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
        return detail
            .map((item) => {
                const loc = Array.isArray(item?.loc) ? item.loc.join(".") : "";
                const msg = item?.msg || JSON.stringify(item);
                return loc ? `${loc}: ${msg}` : msg;
            })
            .join("; ");
    }
    if (detail && typeof detail === "object") {
        return detail.reason || detail.error || JSON.stringify(detail);
    }
    return fallback;
}

export async function apiFetch(endpoint) {
    try {
        const res = await fetch(`${API}${endpoint}`, {
            headers: authHeaders(),
        });
        if (res.status === 401) {
            showToast("Sesión expirada. Selecciona tu perfil.", "error");
            window.dispatchEvent(new CustomEvent("profile:expired"));
            return null;
        }
        if (res.status === 403) {
            const err = await res.json().catch(() => ({}));
            showToast(errorMessage(err, "Tu rol no tiene permisos para esta acción."), "warning");
            return null;
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(errorMessage(err, `HTTP ${res.status}`));
        }
        return await res.json();
    } catch (e) {
        console.error(`API Error: ${endpoint}`, e);
        showToast(e.message || "Error de conexión con el servidor", "error");
        return null;
    }
}

export async function apiPost(endpoint, body = null) {
    try {
        const opts = {
            method: "POST",
            headers: authHeaders(),
        };
        if (body) {
            opts.headers["Content-Type"] = "application/json";
            opts.body = JSON.stringify(body);
        }
        const res = await fetch(`${API}${endpoint}`, opts);
        if (res.status === 401) {
            showToast("Sesión expirada. Selecciona tu perfil.", "error");
            window.dispatchEvent(new CustomEvent("profile:expired"));
            return null;
        }
        if (res.status === 403) {
            const err = await res.json().catch(() => ({}));
            showToast(errorMessage(err, "Tu rol no tiene permisos para esta acción."), "warning");
            return null;
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(errorMessage(err, `HTTP ${res.status}`));
        }
        return await res.json();
    } catch (e) {
        console.error(`API Error: ${endpoint}`, e);
        showToast("Error: " + e.message, "error");
        return null;
    }
}

export async function apiDelete(endpoint) {
    try {
        const res = await fetch(`${API}${endpoint}`, {
            method: "DELETE",
            headers: authHeaders(),
        });
        if (res.status === 401) {
            showToast("Sesión expirada. Selecciona tu perfil.", "error");
            window.dispatchEvent(new CustomEvent("profile:expired"));
            return null;
        }
        if (res.status === 403) {
            const err = await res.json().catch(() => ({}));
            showToast(errorMessage(err, "Tu rol no tiene permisos para esta acción."), "warning");
            return null;
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(errorMessage(err, `HTTP ${res.status}`));
        }
        return await res.json();
    } catch (e) {
        console.error(`API Error: ${endpoint}`, e);
        showToast("Error de conexion con el servidor", "error");
        return null;
    }
}

export async function apiPut(endpoint, body) {
    try {
        const res = await fetch(`${API}${endpoint}`, {
            method: "PUT",
            headers: authHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify(body),
        });
        if (res.status === 401) {
            showToast("Sesión expirada. Selecciona tu perfil.", "error");
            window.dispatchEvent(new CustomEvent("profile:expired"));
            return null;
        }
        if (res.status === 403) {
            const err = await res.json().catch(() => ({}));
            showToast(errorMessage(err, "Tu rol no tiene permisos para esta acción."), "warning");
            return null;
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(errorMessage(err, `HTTP ${res.status}`));
        }
        return await res.json();
    } catch (e) {
        console.error(`API Error: ${endpoint}`, e);
        showToast("Error: " + e.message, "error");
        return null;
    }
}

// ── Llamadas de perfil (sin token, son el mecanismo de login) ──────────────

export async function fetchProfiles() {
    const res = await fetch(`${API}/profiles`);
    if (!res.ok) return [];
    return await res.json();
}

export async function createProfile(name, role = "analista", password = "", displayName = "") {
    const headers = { "Content-Type": "application/json" };
    if (state.adminToken) headers["X-Profile-Token"] = state.adminToken;
    const res = await fetch(`${API}/profiles`, {
        method: "POST",
        headers,
        body: JSON.stringify({ name, display_name: displayName || name, role, password }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(errorMessage(err, `HTTP ${res.status}`));
    }
    return await res.json();
}

/**
 * Login a un perfil con contraseña, o emisión por admin (token admin en header
 * permite saltar la contraseña).
 */
export async function fetchProfileToken(profileId, password = "", { viaAdmin = false } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (viaAdmin && state.adminToken) {
        headers["X-Profile-Token"] = state.adminToken;
    }
    const res = await fetch(`${API}/profiles/${profileId}/token`, {
        method: "POST",
        headers,
        body: JSON.stringify({ password }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(errorMessage(err, "No se pudo iniciar sesión en el perfil"));
    }
    return await res.json();
}

export async function adminLogin(password) {
    const res = await fetch(`${API}/profiles/admin-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(errorMessage(err, "Clave maestra incorrecta"));
    }
    return await res.json();
}

export async function deleteProfileById(profileId) {
    return apiDelete(`/profiles/${profileId}`);
}

export async function changePassword(profileId, newPassword, currentPassword = "") {
    return apiPut(`/profiles/${profileId}/password`, {
        new_password: newPassword,
        current_password: currentPassword,
    });
}

export async function fetchAuditLog({ limit = 200, offset = 0, action = "", profileId = "" } = {}) {
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    params.set("offset", String(offset));
    if (action) params.set("action", action);
    if (profileId) params.set("profile_id", profileId);
    return apiFetch(`/admin/audit-log?${params.toString()}`);
}

export async function fetchAuditLogStats() {
    return apiFetch("/admin/audit-log/stats");
}
