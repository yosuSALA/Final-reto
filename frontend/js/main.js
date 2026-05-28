// Entry point — wires globals for inline onclick handlers + initializes router
import { navigateTo, routeFromHash } from "./router.js";
import { showToast } from "./utils.js";
import {
    loadDashboard, loadAuditPanel, runFullAudit, toggleIncludeTest, triggerDeepSeekInsight,
    skipAuditGuide, reactivateAuditGuide, openWorkflowTarget, nextDemoGuide, prevDemoGuide,
} from "./pages/dashboard.js";
import { loadClaimWorkspace, switchWorkspaceTab } from "./pages/claimWorkspace.js";
import {
    loadAuditorias, setAuditSearch, setAuditTab, toggleAuditIncludeTest, clearAuditWorkflowFocus, openReviewedAudit,
} from "./pages/auditorias.js";
import {
    loadTarifario, toggleTariffForm, submitNewTariff, deleteTariff,
    toggleTarifCat, toggleAllTarif, editTariff, cancelTariff, saveTariff,
    showCsvSchemaModal,
} from "./pages/tarifario.js";
import {
    closeCsvModal, triggerCsvFilePicker, handleCsvFileChange,
    submitCsvUpload, downloadCsvTemplate,
} from "./components/csvUpload.js";
import {
    loadSiniestros, toggleClaimPreview,
    openSummaryModal, closeSummaryModal,
    setClaimsSearch, setClaimsTypeFilter, setClaimsStatusFilter, setClaimsSort, clearClaimsWorkflowFocus,
    toggleClaimForm, submitNewClaim,
} from "./pages/siniestros.js";
import {
    loadUploadPage, genRandomFactura, clearGeneratedFacturas,
    setUploadIsTest, handleUploadFile, auditTestPdfDirect,
} from "./pages/upload.js";
import {
    loadPendingDetail, triggerJitAudit, triggerRulesAudit,
} from "./pages/pendingDetail.js";
import {
    loadAuditDetail, auditAction, previewReport, reAuditWith,
} from "./pages/auditDetail.js";
import { refreshAuditQueue, toggleAuditQueueMinimized } from "./components/auditQueue.js";
import { initChatbotBubble } from "./components/chatbotBubble.js";
import {
    applyProfileUI, showProfileSelector, hasActiveSession, clearProfileSession,
    updateProfileBadge, signOut, openProfileSwitcher, adminDeleteProfile,
} from "./auth.js";
import { loadAdminAuditLog } from "./pages/adminAuditLog.js";
import { state } from "./state.js";

// ── Modo oscuro ────────────────────────────────────────

export function toggleTheme() {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const newTheme = isDark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
    document.getElementById("icon-moon").style.display = isDark ? "block" : "none";
    document.getElementById("icon-sun").style.display = isDark ? "none" : "block";
}

const savedTheme = localStorage.getItem("theme") || "dark";
document.documentElement.setAttribute("data-theme", savedTheme);
if (savedTheme === "dark") {
    setTimeout(() => {
        const m = document.getElementById("icon-moon");
        const s = document.getElementById("icon-sun");
        if (m) m.style.display = "none";
        if (s) s.style.display = "block";
    }, 50);
}

// ── Exponer funciones a atributos onclick en HTML ──────

Object.assign(window, {
    navigateTo, showToast, loadDashboard,
    runFullAudit, toggleIncludeTest, triggerDeepSeekInsight,
    loadAuditPanel, skipAuditGuide, reactivateAuditGuide,
    openWorkflowTarget, nextDemoGuide, prevDemoGuide,
    loadClaimWorkspace, switchWorkspaceTab,
    setAuditSearch, setAuditTab, toggleAuditIncludeTest, clearAuditWorkflowFocus, openReviewedAudit,
    toggleTariffForm, submitNewTariff, deleteTariff,
    toggleTarifCat, toggleAllTarif, editTariff, cancelTariff, saveTariff,
    showCsvSchemaModal, closeCsvModal, triggerCsvFilePicker,
    handleCsvFileChange, submitCsvUpload, downloadCsvTemplate,
    toggleClaimPreview,
    openSummaryModal, closeSummaryModal,
    setClaimsSearch, setClaimsTypeFilter, setClaimsStatusFilter, setClaimsSort, clearClaimsWorkflowFocus,
    toggleClaimForm, submitNewClaim,
    genRandomFactura, clearGeneratedFacturas, setUploadIsTest,
    handleUploadFile, auditTestPdfDirect,
    triggerJitAudit, triggerRulesAudit,
    auditAction, previewReport, reAuditWith,
    toggleTheme, signOut, toggleAuditQueueMinimized,
    openProfileSwitcher, adminDeleteProfile, loadAdminAuditLog,
});

// ── Nav links ──────────────────────────────────────────

document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", (e) => {
        e.preventDefault();
        navigateTo(link.dataset.page);
    });
});

const btnRunAudit = document.getElementById("btn-run-audit");
if (btnRunAudit) btnRunAudit.addEventListener("click", runFullAudit);

// ── Botón "Sign Out" en el navbar ───────────────────────

const btnSignOut = document.getElementById("btn-sign-out");
if (btnSignOut) {
    btnSignOut.addEventListener("click", signOut);
}

const btnSwitchProfile = document.getElementById("btn-switch-profile");
if (btnSwitchProfile) {
    btnSwitchProfile.addEventListener("click", openProfileSwitcher);
}

// ── Eventos de perfil ──────────────────────────────────

window.addEventListener("profile:selected", (e) => {
    updateProfileBadge();
    showToast(`Perfil activo: ${e.detail?.name || ""}`, "success");
    routeFromHash();
    refreshAuditQueue();
    initChatbotBubble();
    applyProfileUI();
});

window.addEventListener("profile:expired", () => {
    clearProfileSession();
    showProfileSelector();
});

// ── Inicialización principal ───────────────────────────

function boot() {
    if (!hasActiveSession()) {
        showProfileSelector();
        return;
    }
    updateProfileBadge();
    routeFromHash();
    refreshAuditQueue();
    initChatbotBubble();
    applyProfileUI();
}

window.addEventListener("hashchange", routeFromHash);
window.addEventListener("hashchange", refreshAuditQueue);

document.addEventListener("DOMContentLoaded", boot);

if (document.readyState !== "loading") {
    boot();
}

setInterval(refreshAuditQueue, 15000);
