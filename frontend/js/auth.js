import { state } from "./state.js";

const profilePermissions = {
    demo_jurado: {
        canRunAuditAll: true,
        canReviewDecision: false,
        canManageTariffs: false,
        canNotify: false,
    },
    analista: {
        canRunAuditAll: false,
        canReviewDecision: false,
        canManageTariffs: false,
        canNotify: false,
    },
    antifraude: {
        canRunAuditAll: true,
        canReviewDecision: true,
        canManageTariffs: false,
        canNotify: false,
    },
    jefatura: {
        canRunAuditAll: true,
        canReviewDecision: true,
        canManageTariffs: true,
        canNotify: true,
    },
    auditoria: {
        canRunAuditAll: true,
        canReviewDecision: true,
        canManageTariffs: true,
        canNotify: true,
    },
};

export function getPermissions(profile = state.currentProfile) {
    return profilePermissions[profile] || profilePermissions.demo_jurado;
}

export function applyProfileUI() {
    const p = getPermissions();
    const runBtn = document.getElementById("btn-run-audit");
    if (runBtn && !p.canRunAuditAll) {
        runBtn.disabled = true;
        runBtn.classList.add("btn-disabled");
        runBtn.title = "Tu perfil no permite ejecutar auditoría masiva";
    }

    const navTarif = document.getElementById("nav-tarifario");
    if (navTarif) {
        navTarif.style.display = p.canManageTariffs ? "" : "none";
    }
}

export function setProfile(profile) {
    state.currentProfile = profile;
    localStorage.setItem("currentProfile", profile);
    applyProfileUI();
}
