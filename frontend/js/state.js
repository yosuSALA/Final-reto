// Shared mutable state (single source of truth)
export const state = {
    // ── Perfil activo ──────────────────────────────────────
    currentProfileId: localStorage.getItem("profileId") || null,
    currentProfileName: localStorage.getItem("profileName") || null,
    currentProfileToken: localStorage.getItem("profileToken") || null,
    currentRole: localStorage.getItem("profileRole") || "analista",

    // ── Datos de la aplicación ─────────────────────────────
    dashboardData: null,
    auditResults: [],
    pendingInvoices: [],
    tariffData: [],
    claimsData: [],

    // Auditorias view
    currentAuditTab: "pendientes",
    auditSearchTerm: "",

    // Tarifario view
    tarifEditingId: null,
    tarifExpanded: {},
    showTariffForm: false,

    // Siniestros view
    claimInvoicesCache: {},
    claimExpanded: null,
    claimsSearchTerm: "",
    claimsSortBy: "incident_date",
    claimsSortDir: "desc",
    claimsTypeFilter: "all",
    claimsStatusFilter: "all",

    // Upload page
    generatedFacturas: [],
    uploadResult: null,
    uploadIsTest: true,

    // Filtros globales
    includeTest: true,
    workflowFocus: null,
};
