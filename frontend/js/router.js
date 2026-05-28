import { loadDashboard } from "./pages/dashboard.js";
import { loadAuditorias } from "./pages/auditorias.js";
import { loadTarifario } from "./pages/tarifario.js";
import { loadSiniestros } from "./pages/siniestros.js";
import { loadUploadPage } from "./pages/upload.js";
import { loadPendingDetail } from "./pages/pendingDetail.js";
import { loadAuditDetail } from "./pages/auditDetail.js";
import { loadClaimWorkspace } from "./pages/claimWorkspace.js";

export function navigateTo(page, params = {}) {
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
    const target = document.getElementById(`page-${page}`);
    const link = document.querySelector(`.nav-link[data-page="${page}"]`);
    if (target) target.classList.add("active");
    if (link) link.classList.add("active");
    switch (page) {
        case "dashboard":       loadDashboard(); break;
        case "auditorias":      loadAuditorias(); break;
        case "tarifario":       loadTarifario(); break;
        case "siniestros":      loadSiniestros(); break;
        case "upload":          loadUploadPage(); break;
        case "audit-detail":
            document.getElementById("page-audit-detail").classList.add("active");
            loadAuditDetail(params.auditId);
            break;
        case "pending-detail":
            document.getElementById("page-audit-detail").classList.add("active");
            loadPendingDetail(params.invoiceId);
            break;
        case "claim-workspace":
            document.getElementById("page-claim-workspace").classList.add("active");
            loadClaimWorkspace(params.claimId);
            break;
    }
}

export function routeFromHash() {
    const hash = location.hash.replace("#", "") || "dashboard";
    if (hash.startsWith("audit/"))       navigateTo("audit-detail", { auditId: hash.split("/")[1] });
    else if (hash.startsWith("pending/")) navigateTo("pending-detail", { invoiceId: hash.split("/")[1] });
    else if (hash.startsWith("claim/"))  navigateTo("claim-workspace", { claimId: hash.split("/")[1] });
    else navigateTo(hash);
}
