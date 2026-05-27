// Entry point — wires globals for inline onclick handlers + initializes router
import { navigateTo, routeFromHash } from "./router.js";
import { showToast } from "./utils.js";
import {
    loadDashboard, runFullAudit, toggleIncludeTest,
} from "./pages/dashboard.js";
import {
    loadAuditorias, setAuditSearch, setAuditTab, toggleAuditIncludeTest,
} from "./pages/auditorias.js";
import {
    loadTarifario, toggleTariffForm, submitNewTariff, deleteTariff,
    toggleTarifCat, toggleAllTarif, editTariff, cancelTariff, saveTariff,
} from "./pages/tarifario.js";
import {
    loadSiniestros, toggleClaimPreview,
    openNotifyModal, closeNotifyModal, saveNotifyConfig,
} from "./pages/siniestros.js";
import {
    loadUploadPage, genRandomFactura, clearGeneratedFacturas,
    setUploadIsTest, handleUploadFile, auditTestPdfDirect,
} from "./pages/upload.js";
import {
    loadPendingDetail, triggerJitAudit, triggerRulesAudit,
} from "./pages/pendingDetail.js";
import {
    loadAuditDetail, auditAction, previewReport, notifyWorkshop, reAuditWith,
} from "./pages/auditDetail.js";

// Lógica del modo oscuro
export function toggleTheme() {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const newTheme = isDark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
    document.getElementById("icon-moon").style.display = isDark ? "block" : "none";
    document.getElementById("icon-sun").style.display = isDark ? "none" : "block";
}

// Inicializar tema
const savedTheme = localStorage.getItem("theme") || "dark";
document.documentElement.setAttribute("data-theme", savedTheme);
if (savedTheme === "dark") {
    setTimeout(() => {
        const m = document.getElementById("icon-moon");
        const s = document.getElementById("icon-sun");
        if(m) m.style.display = "none";
        if(s) s.style.display = "block";
    }, 50);
}

// Expose to window for inline `onclick="fn(...)"` attributes in rendered HTML
Object.assign(window, {
    navigateTo, showToast,
    runFullAudit, toggleIncludeTest,
    setAuditSearch, setAuditTab, toggleAuditIncludeTest,
    toggleTariffForm, submitNewTariff, deleteTariff,
    toggleTarifCat, toggleAllTarif, editTariff, cancelTariff, saveTariff,
    toggleClaimPreview,
    openNotifyModal, closeNotifyModal, saveNotifyConfig,
    genRandomFactura, clearGeneratedFacturas, setUploadIsTest,
    handleUploadFile, auditTestPdfDirect,
    triggerJitAudit, triggerRulesAudit,
    auditAction, previewReport, notifyWorkshop, reAuditWith,
    toggleTheme,
});

// Nav links
document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", (e) => {
        e.preventDefault();
        navigateTo(link.dataset.page);
    });
});

// Top-bar audit button
const btnRunAudit = document.getElementById("btn-run-audit");
if (btnRunAudit) btnRunAudit.addEventListener("click", runFullAudit);

window.addEventListener("hashchange", routeFromHash);
document.addEventListener("DOMContentLoaded", routeFromHash);

// In case DOMContentLoaded already fired (module loaded after parse)
if (document.readyState !== "loading") routeFromHash();
