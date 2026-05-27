// Shared mutable state (single source of truth)
export const state = {
    currentProfile: localStorage.getItem("currentProfile") || "demo_jurado",
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
    // Upload page
    generatedFacturas: [],
    uploadResult: null,
    uploadIsTest: true,
    // Filtros globales
    includeTest: true,
};
