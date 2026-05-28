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
        if (res.status === 403) {
            showToast("Sesión expirada. Selecciona tu perfil.", "error");
            window.dispatchEvent(new CustomEvent("profile:expired"));
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
        if (res.status === 403) {
            showToast("Sesión expirada. Selecciona tu perfil.", "error");
            window.dispatchEvent(new CustomEvent("profile:expired"));
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
        if (res.status === 403) {
            showToast("Sesión expirada. Selecciona tu perfil.", "error");
            window.dispatchEvent(new CustomEvent("profile:expired"));
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
        if (res.status === 403) {
            showToast("Sesión expirada. Selecciona tu perfil.", "error");
            window.dispatchEvent(new CustomEvent("profile:expired"));
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

export async function createProfile(name, role = "analista", displayName = "") {
    const res = await fetch(`${API}/profiles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, display_name: displayName || name, role }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(errorMessage(err, `HTTP ${res.status}`));
    }
    return await res.json();
}

export async function fetchProfileToken(profileId, password = "") {
    const res = await fetch(`${API}/profiles/${profileId}/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(errorMessage(err, "No se pudo obtener el token de perfil"));
    }
    return await res.json();
}
