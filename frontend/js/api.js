// API client + fetch helpers
import { showToast } from "./utils.js";

export const API = "/api";

export async function apiFetch(endpoint) {
    try {
        const res = await fetch(`${API}${endpoint}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error(`API Error: ${endpoint}`, e);
        showToast("Error de conexion con el servidor", "error");
        return null;
    }
}

export async function apiPost(endpoint, body = null) {
    try {
        const opts = { method: "POST" };
        if (body) {
            opts.headers = { "Content-Type": "application/json" };
            opts.body = JSON.stringify(body);
        }
        const res = await fetch(`${API}${endpoint}`, opts);
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
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
        const res = await fetch(`${API}${endpoint}`, { method: "DELETE" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
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
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error(`API Error: ${endpoint}`, e);
        showToast("Error: " + e.message, "error");
        return null;
    }
}
