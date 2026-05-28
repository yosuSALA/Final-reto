import { apiFetch, apiPost, API } from "../api.js";
import { state } from "../state.js";
import { showToast } from "../utils.js";

let uploadInFlight = false;

export async function loadUploadPage() {
    const claims = await apiFetch("/claims") || [];
    renderUploadPage(claims);
}

function renderUploadPage(claims) {
    const page = document.getElementById("page-upload");
    page.innerHTML = `
        <div class="page-header">
            <h1>Auditar Factura PDF</h1>
            <p>Arrastra un PDF de factura de taller. La extracción es automática y la auditoría se lanza desde la cola de pendientes.</p>
        </div>

        <div class="grid-3-1">
            <div class="card">
                <div class="card-header"><h2>Subir Factura PDF</h2></div>
                <div class="card-body">
                    <div style="margin-bottom:14px;">
                        <label style="font-size:0.85rem; color:var(--text-muted); margin-bottom:6px; display:block;">Siniestro asociado (opcional)</label>
                        <select id="upload-claim-select" style="width:100%; padding:8px 12px; border:1px solid #cbd5e1; border-radius:6px; outline:none; font-family:inherit;">
                            <option value="">— Sin siniestro (audit solo de formato/tarifario) —</option>
                            ${claims.map(c => `<option value="${c.claim_number}">${c.claim_number} · ${c.claim_type.replace(/_/g, ' ')} · ${c.vehicle_plate}</option>`).join("")}
                        </select>
                    </div>

                    <label style="display:flex;align-items:center;gap:6px;font-size:0.85rem;color:var(--text-muted);margin-bottom:12px;">
                        <input type="checkbox" id="upload-is-test" ${state.uploadIsTest ? "checked" : ""} onchange="setUploadIsTest(this.checked)">
                        Marcar como factura de prueba (TEST) — se audita pero no afecta el dashboard real
                    </label>

                    <div id="dropzone" style="
                        border:2px dashed var(--accent-indigo);
                        border-radius:12px;
                        padding:48px 24px;
                        text-align:center;
                        background:rgba(99,102,241,0.04);
                        cursor:pointer;
                        transition:all 0.2s;
                    ">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--accent-indigo)" stroke-width="1.5" style="margin-bottom:12px;">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="17 8 12 3 7 8"/>
                            <line x1="12" y1="3" x2="12" y2="15"/>
                        </svg>
                        <div style="font-size:1.1rem; font-weight:600; color:var(--text-primary); margin-bottom:6px;">Arrastra el PDF aquí</div>
                        <div style="color:var(--text-muted); font-size:0.9rem; margin-bottom:14px;">o haz click para seleccionar</div>
                        <button class="btn btn-primary btn-sm" id="choose-file-btn">Elegir Archivo</button>
                        <input type="file" id="upload-file-input" accept="application/pdf,.pdf" style="display:none;">
                        <div style="margin-top:12px; font-size:0.75rem; color:var(--text-muted);">Solo PDF · máx 10 MB</div>
                    </div>

                    <div id="upload-status" style="margin-top:14px;"></div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <h2>Generador Random (formato SRI)</h2>
                    <button class="btn btn-ghost btn-sm" onclick="clearGeneratedFacturas()">Limpiar</button>
                </div>
                <div class="card-body">
                    <p style="color:var(--text-muted); font-size:0.85rem; margin-bottom:12px;">
                        Genera facturas aleatorias con RUC, número e items únicos. Cada click crea una nueva.
                    </p>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:14px;">
                        <button class="btn btn-success btn-sm" onclick="genRandomFactura('limpia')">+ Limpia</button>
                        <button class="btn btn-warning btn-sm" onclick="genRandomFactura('sobrecobro')">+ Sobrecobro</button>
                        <button class="btn btn-danger btn-sm" onclick="genRandomFactura('fraude')">+ Fraude</button>
                        <button class="btn btn-info btn-sm" onclick="genRandomFactura('mixed')" style="background:var(--accent-indigo); color:white;">+ Aleatorio</button>
                    </div>
                    <div id="generated-list" style="display:flex; flex-direction:column; gap:10px; max-height:520px; overflow-y:auto;">
                        ${renderGeneratedList()}
                    </div>
                </div>
            </div>
        </div>

        <div id="upload-result-container" style="margin-top:24px;"></div>
    `;

    setupDropzone();
}

function renderGeneratedList() {
    if (!state.generatedFacturas.length) {
        return '<div style="padding:24px; text-align:center; color:var(--text-muted); font-size:0.85rem;">Aún no has generado facturas. Click en uno de los botones de arriba.</div>';
    }
    return state.generatedFacturas.map((f, idx) => {
        const scColor = f.scenario === "fraude" ? "var(--accent-rose)"
                      : f.scenario === "sobrecobro" ? "var(--accent-warning)"
                      : f.scenario === "limpia" ? "var(--accent-emerald)"
                      : "var(--accent-indigo)";
        const itemsPreview = (f.items_preview || []).slice(0, 3).map(it =>
            `<div style="display:flex; justify-content:space-between; font-size:0.75rem; padding:2px 0;">
                <span style="color:var(--text-muted); font-family:var(--font-mono);">${it.code}</span>
                <span style="flex:1; padding:0 6px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${it.description}</span>
                <span style="font-weight:600;">${it.quantity} × $${it.unit_price.toFixed(2)}</span>
            </div>`
        ).join("");
        const more = (f.items_preview || []).length > 3
            ? `<div style="font-size:0.7rem; color:var(--text-muted); padding-top:4px;">+ ${f.items_preview.length - 3} items más...</div>`
            : "";
        return `
        <div style="border:1px solid #e2e8f0; border-left:4px solid ${scColor}; border-radius:8px; padding:12px; background:white;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:8px;">
                <div style="flex:1; min-width:0;">
                    <div style="font-weight:700; font-size:0.95rem;">${f.invoice_number}</div>
                    <div style="font-size:0.75rem; color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${f.workshop_comercial} · RUC ${f.ruc}</div>
                </div>
                <span class="badge" style="background:${scColor}; color:white; font-size:0.7rem; text-transform:uppercase;">${f.scenario}</span>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:0.78rem; margin-bottom:8px;">
                <div><strong>Fecha:</strong> ${f.issue_date}</div>
                <div><strong>Siniestro:</strong> ${f.claim_number}</div>
                <div><strong>Vehículo:</strong> ${f.plate}</div>
                <div><strong>Items:</strong> ${f.items_count}</div>
            </div>
            <div style="background:#f8fafc; padding:8px; border-radius:6px; margin-bottom:8px;">
                ${itemsPreview}
                ${more}
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-top:1px solid #f1f5f9; margin-bottom:8px;">
                <span style="font-size:0.75rem; color:var(--text-muted);">Total preliminar:</span>
                <span style="font-weight:700; font-size:1rem;">$${f.total.toFixed(2)}</span>
            </div>
            <div style="font-size:0.7rem; color:var(--text-muted); margin-bottom:8px;"><em>Esperado: ${f.expected_finding}</em></div>
            <div style="display:flex; gap:6px;">
                <a href="${API}/test-pdfs/${f.filename}" download="${f.filename}" target="_blank" class="btn btn-info btn-sm" style="background:var(--accent-indigo); color:white; text-decoration:none; flex:1; text-align:center;">Descargar PDF</a>
                <button class="btn btn-ghost btn-sm" onclick="auditTestPdfDirect('${f.filename}')" style="flex:1;">Auditar directo</button>
            </div>
        </div>`;
    }).join("");
}

export async function genRandomFactura(scenario) {
    const labels = { limpia: "limpia", sobrecobro: "sobrecobro", fraude: "fraude", mixed: "aleatoria" };
    showToast(`Generando factura ${labels[scenario]}...`, "info");
    try {
        const data = await apiPost(`/test-pdfs/random?scenario=${scenario}&count=1`);
        if (!data) throw new Error("No se pudo generar la factura de prueba");
        if (data.files && data.files.length) {
            state.generatedFacturas.unshift(data.files[0]);
            const list = document.getElementById("generated-list");
            if (list) list.innerHTML = renderGeneratedList();
            showToast(`Factura ${data.files[0].invoice_number} generada`, "success");
        }
    } catch (e) {
        showToast("Error generando factura: " + e.message, "error");
    }
}

export function clearGeneratedFacturas() {
    state.generatedFacturas = [];
    const list = document.getElementById("generated-list");
    if (list) list.innerHTML = renderGeneratedList();
}

export function setUploadIsTest(checked) {
    state.uploadIsTest = !!checked;
}

function setupDropzone() {
    const dz = document.getElementById("dropzone");
    if (!dz) return;
    const fileInput = document.getElementById("upload-file-input");
    const chooseBtn = document.getElementById("choose-file-btn");

    chooseBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        fileInput.click();
    });
    fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) handleUploadFile(e.target.files[0]);
    });

    ["dragenter", "dragover"].forEach(ev => {
        dz.addEventListener(ev, e => {
            e.preventDefault();
            e.stopPropagation();
            dz.style.background = "rgba(99,102,241,0.12)";
            dz.style.borderColor = "var(--accent-emerald)";
        });
    });
    ["dragleave", "drop"].forEach(ev => {
        dz.addEventListener(ev, e => {
            e.preventDefault();
            e.stopPropagation();
            dz.style.background = "rgba(99,102,241,0.04)";
            dz.style.borderColor = "var(--accent-indigo)";
        });
    });
    dz.addEventListener("drop", e => {
        const files = e.dataTransfer && e.dataTransfer.files;
        if (files && files.length) handleUploadFile(files[0]);
    });
    dz.addEventListener("click", e => {
        if (e.target === dz || e.target.tagName === "DIV" || e.target.tagName === "svg" || e.target.tagName === "SVG") {
            fileInput.click();
        }
    });
}

export async function handleUploadFile(file) {
    if (uploadInFlight) {
        showToast("Ya hay una carga en curso, espera...", "warning");
        return;
    }
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
        showToast("Solo se aceptan archivos PDF", "error");
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        showToast("PDF demasiado grande (máx 10 MB)", "error");
        return;
    }
    uploadInFlight = true;
    const status = document.getElementById("upload-status");
    if (status) status.innerHTML = `<div style="display:flex; align-items:center; gap:8px; color:var(--text-muted); padding:8px 0;"><span class="spinner"></span> Cargando <strong>${file.name}</strong>...</div>`;

    const claimSelect = document.getElementById("upload-claim-select");
    const claimNumber = claimSelect ? claimSelect.value : "";
    const fd = new FormData();
    fd.append("file", file);
    if (claimNumber) fd.append("claim_number", claimNumber);
    fd.append("is_test", state.uploadIsTest ? "1" : "0");

    try {
        const headers = state.currentProfileToken ? { "X-Profile-Token": state.currentProfileToken } : {};
        const res = await fetch(`${API}/audit-pdf`, { method: "POST", headers, body: fd });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
            throw new Error(err.detail || "Error desconocido");
        }
        state.uploadResult = await res.json();
        if (state.uploadResult.status === "already_exists") {
            if (status) status.innerHTML = `<div style="color:var(--accent-warning); padding:8px 0;">⚠ ${state.uploadResult.message}</div>`;
            showToast(state.uploadResult.message, "warning");
        } else {
            if (status) status.innerHTML = `<div style="color:var(--accent-emerald); padding:8px 0;">PDF cargado correctamente — <strong>${file.name}</strong></div>`;
            showToast("Factura añadida a la cola de auditoría", "success");
        }
        renderUploadQueued();
    } catch (e) {
        if (status) status.innerHTML = `<div style="color:var(--accent-rose); padding:8px 0;">${e.message}</div>`;
        showToast("Error: " + e.message, "error");
    } finally {
        uploadInFlight = false;
    }
}

export async function auditTestPdfDirect(filename) {
    if (uploadInFlight) {
        showToast("Espera, hay una carga en curso...", "warning");
        return;
    }
    showToast(`Descargando ${filename}...`, "info");
    try {
        const r = await fetch(`${API}/test-pdfs/${filename}`);
        if (!r.ok) throw new Error("No se pudo descargar el PDF");
        const blob = await r.blob();
        const file = new File([blob], filename, { type: "application/pdf" });
        await handleUploadFile(file);
    } catch (e) {
        showToast(e.message, "error");
    }
}

function renderUploadQueued() {
    const container = document.getElementById("upload-result-container");
    if (!container || !state.uploadResult) return;
    const inv = state.uploadResult.invoice_extracted || {};
    const items = inv.items || [];
    const isNew = state.uploadResult.status !== "already_exists";
    const borderColor = isNew ? "var(--accent-emerald)" : "var(--accent-warning)";
    const headerColor = isNew ? "var(--accent-emerald)" : "var(--accent-warning)";
    const headerText = isNew ? "Factura añadida a la cola de auditoría" : "Factura ya registrada";
    const testTag = state.uploadResult.is_test ? '<span class="badge badge-warning" style="background:#94a3b8;color:white;margin-left:8px;">TEST</span>' : "";

    container.innerHTML = `
        <div class="card" style="border-left: 4px solid ${borderColor};">
            <div class="card-header">
                <h2 style="color:${headerColor};">${headerText} ${testTag}</h2>
                <span class="badge badge-warning">Pendiente de auditoría</span>
            </div>
            <div class="card-body">
                <div style="margin-bottom:16px;">
                    <h3 style="margin:0 0 8px; color:var(--accent-indigo); font-size:0.95rem;">Datos Extraídos del PDF</h3>
                    <table>
                        <tbody>
                            <tr><td><strong>Archivo:</strong></td><td>${state.uploadResult.filename}</td></tr>
                            <tr><td><strong>RUC:</strong></td><td style="font-family:var(--font-mono)">${inv.ruc || '<span style="color:var(--accent-rose)">FALTA</span>'}</td></tr>
                            <tr><td><strong>Factura Nº:</strong></td><td><strong>${inv.invoice_number || '<span style="color:var(--accent-rose)">FALTA</span>'}</strong></td></tr>
                            <tr><td><strong>Taller:</strong></td><td>${inv.workshop_name || '-'}</td></tr>
                            <tr><td><strong>Fecha:</strong></td><td>${inv.issue_date || '-'}</td></tr>
                            <tr><td><strong>Subtotal:</strong></td><td>$${(inv.subtotal||0).toFixed(2)}</td></tr>
                            <tr><td><strong>Total:</strong></td><td><strong>$${(inv.total||0).toFixed(2)}</strong></td></tr>
                        </tbody>
                    </table>
                </div>

                ${items.length > 0 ? `
                <h3 style="color:var(--accent-indigo); font-size:0.95rem; margin-bottom:8px;">Items Facturados (${items.length})</h3>
                <table style="margin-bottom:18px;">
                    <thead><tr><th>Código</th><th>Descripción</th><th>Cant.</th><th>P. Unit.</th><th>Total</th></tr></thead>
                    <tbody>
                        ${items.map(i => `
                            <tr>
                                <td><span style="font-family:var(--font-mono); color:var(--text-muted);">${i.code || '-'}</span></td>
                                <td>${i.description}</td>
                                <td>${(i.quantity||0).toFixed(0)}</td>
                                <td>$${(i.unit_price||0).toFixed(2)}</td>
                                <td>$${(i.total_price||0).toFixed(2)}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
                ` : ''}

                <div style="display:flex; gap:12px; align-items:center; padding-top:8px; border-top:1px solid #e2e8f0;">
                    <p style="margin:0; color:var(--text-muted); font-size:0.9rem;">La auditoría se ejecuta desde la cola de pendientes.</p>
                    <button class="btn btn-primary" onclick="navigateTo('auditorias')" style="white-space:nowrap;">Ver Pendientes →</button>
                </div>
            </div>
        </div>
    `;
    container.scrollIntoView({ behavior: "smooth", block: "start" });
}
