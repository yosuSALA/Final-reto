import { apiFetch, apiPost, apiPut, apiDelete, API } from "../api.js";
import { state } from "../state.js";
import { showToast } from "../utils.js";
import { showCsvSchemaModal } from "../components/csvUpload.js";

const CLAIM_TYPES = [
    "choque_frontal", "choque_lateral", "choque_trasero",
    "robo_accesorios", "daño_granizo", "rayon_pintura",
    "rotura_parabrisas", "vandalismo",
];

const CATEGORIES = ["repuesto", "pintura", "material", "mano_obra", "servicio"];

export { showCsvSchemaModal };

export async function loadTarifario() {
    state.tariffData = await apiFetch("/tariffs") || [];
    const categories = [...new Set(state.tariffData.map(t => t.category))];
    if (Object.keys(state.tarifExpanded).length === 0) {
        categories.forEach((c, i) => { state.tarifExpanded[c] = i === 0; });
    }
    renderTarifarioView();
    window._tarifarioLoaded = true;
}

// Recarga el tarifario cuando se completa una importación CSV exitosa
window.addEventListener("csv:imported", async (e) => {
    if (e.detail?.entity === "tarifario" && window._tarifarioLoaded) {
        await loadTarifario();
    }
});

export function renderTarifarioView() {
    const page = document.getElementById("page-tarifario");
    const categories = [...new Set(state.tariffData.map(t => t.category))];
    page.innerHTML = `
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;">
            <div>
                <h1>Tarifario Acordado</h1>
                <p>Precios maximos acordados entre la aseguradora y los talleres.</p>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <button class="btn btn-ghost" onclick="showCsvSchemaModal('tarifario')" title="Importar múltiples items desde archivo CSV">
                    ⬆ Importar CSV
                </button>
                <button class="btn btn-primary" onclick="toggleTariffForm()">
                    ${state.showTariffForm ? "✕ Cerrar formulario" : "+ Añadir Manual"}
                </button>
            </div>
        </div>
        ${state.showTariffForm ? renderTariffForm() : ""}
        <div style="display:flex; gap:8px; margin-bottom:16px;">
            <button class="btn btn-ghost btn-sm" onclick="toggleAllTarif(true)">Expandir todo</button>
            <button class="btn btn-ghost btn-sm" onclick="toggleAllTarif(false)">Colapsar todo</button>
        </div>
        ${categories.map(cat => {
            const items = state.tariffData.filter(t => t.category === cat);
            const expanded = !!state.tarifExpanded[cat];
            return `
            <div class="card" style="margin-bottom:14px">
                <div class="card-header" style="cursor:pointer; user-select:none;" onclick="toggleTarifCat('${cat}')">
                    <h2 style="display:flex; align-items:center; gap:10px; margin:0;">
                        <span style="display:inline-block; transition:transform 0.2s; transform:rotate(${expanded ? 90 : 0}deg); color:var(--accent-indigo); font-size:0.8rem;">▶</span>
                        <span class="cat-tag cat-${cat}">${cat.replace(/_/g, ' ').toUpperCase()}</span>
                    </h2>
                    <span style="color:var(--text-muted);font-size:0.8rem">${items.length} items ${expanded ? '· abierto' : '· cerrado'}</span>
                </div>
                ${expanded ? `
                <div class="card-body table-wrap">
                    <table>
                        <thead><tr><th>Codigo</th><th>Descripcion</th><th>Precio Max.</th><th>Tolerancia</th><th>Cant. Min</th><th>Cant. Max</th><th>Aplica a</th><th style="text-align:right">Acción</th></tr></thead>
                        <tbody>
                            ${items.map(t => renderTarifRow(t)).join("")}
                        </tbody>
                    </table>
                </div>` : ''}
            </div>
            `;
        }).join("")}
    `;
}

function renderTariffForm() {
    return `
    <div class="card" style="margin-bottom:18px;border-left:4px solid var(--accent-indigo);">
        <div class="card-header"><h2>Nuevo Tarifario Manual</h2></div>
        <div class="card-body">
            <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;">
                <label>Código <input id="tf-code" type="text" placeholder="REP-XYZ01" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <label>Categoría
                    <select id="tf-cat" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;">
                        ${CATEGORIES.map(c => `<option value="${c}">${c}</option>`).join("")}
                    </select>
                </label>
                <label style="grid-column:1/3;">Descripción <input id="tf-desc" type="text" placeholder="Repuesto delantero ..." style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <label>Precio Máx (USD) <input id="tf-price" type="number" step="0.01" min="0" value="100" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <label>Tolerancia % <input id="tf-tol" type="number" step="1" min="0" max="100" value="10" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <label>Cant. Mín <input id="tf-qmin" type="number" step="1" min="0" value="1" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <label>Cant. Máx <input id="tf-qmax" type="number" step="1" min="1" value="2" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:4px;"></label>
                <div style="grid-column:1/3;">
                    <label style="display:block;margin-bottom:6px;font-weight:500;">Aplicable a siniestros:</label>
                    <div style="display:flex;flex-wrap:wrap;gap:8px;">
                        ${CLAIM_TYPES.map(ct => `
                            <label class="tariff-claim-option" style="display:flex;align-items:center;gap:4px;font-size:0.85rem;background:var(--bg-tertiary);color:var(--text-primary);padding:4px 8px;border-radius:4px;cursor:pointer;">
                                <input type="checkbox" class="tf-claim" value="${ct}"> ${ct.replace(/_/g, ' ')}
                            </label>
                        `).join("")}
                    </div>
                </div>
            </div>
            <div style="margin-top:14px;display:flex;gap:8px;">
                <button class="btn btn-success" onclick="submitNewTariff()">Guardar Tarifario</button>
                <button class="btn btn-ghost" onclick="toggleTariffForm()">Cancelar</button>
            </div>
        </div>
    </div>
    `;
}

function renderTarifRow(t) {
    const editing = state.tarifEditingId === t.id;
    const aplica = (t.applicable_claim_types || []).map(c => c.replace(/_/g, ' ')).join(", ") || "—";
    const priceCell = editing
        ? `<div style="display:flex;align-items:center;gap:6px;">$<input type="number" step="0.01" id="tariff-${t.id}" value="${t.max_price.toFixed(2)}" style="width:90px; padding:4px 6px; border:1px solid var(--accent-indigo); border-radius:4px;" autofocus></div>`
        : `<span style="font-weight:600">$${t.max_price.toFixed(2)}</span>`;
    const actionCell = editing
        ? `<div style="display:flex;gap:4px;justify-content:flex-end;">
              <button class="btn btn-success btn-sm" onclick="saveTariff(${t.id})">Guardar</button>
              <button class="btn btn-ghost btn-sm" onclick="cancelTariff()">Cancelar</button>
           </div>`
        : `<div style="display:flex;gap:4px;justify-content:flex-end;">
              <button class="btn btn-info btn-sm" onclick="editTariff(${t.id})" style="background-color: var(--accent-indigo); color: white;">Modificar</button>
              <button class="btn btn-danger btn-sm" onclick="deleteTariff(${t.id}, '${t.code}')">Eliminar</button>
           </div>`;
    return `
        <tr ${editing ? 'style="background:rgba(99,102,241,0.06)"' : ''}>
            <td><span style="font-family:var(--font-mono);color:var(--accent-indigo)">${t.code}</span></td>
            <td>${t.description}</td>
            <td>${priceCell}</td>
            <td>${t.tolerance_pct}%</td>
            <td>${t.expected_qty_min}</td>
            <td>${t.expected_qty_max}</td>
            <td style="font-size:0.75rem;color:var(--text-muted);">${aplica}</td>
            <td style="text-align:right">${actionCell}</td>
        </tr>
    `;
}

export function toggleTariffForm() {
    state.showTariffForm = !state.showTariffForm;
    renderTarifarioView();
}

export async function submitNewTariff() {
    const code = (document.getElementById("tf-code").value || "").trim();
    const description = (document.getElementById("tf-desc").value || "").trim();
    if (!code || !description) {
        showToast("Código y descripción requeridos", "error");
        return;
    }
    const payload = {
        code,
        description,
        category: document.getElementById("tf-cat").value,
        max_price: parseFloat(document.getElementById("tf-price").value || "0"),
        tolerance_pct: parseFloat(document.getElementById("tf-tol").value || "10"),
        expected_qty_min: parseFloat(document.getElementById("tf-qmin").value || "1"),
        expected_qty_max: parseFloat(document.getElementById("tf-qmax").value || "2"),
        applicable_claim_types: Array.from(document.querySelectorAll(".tf-claim:checked")).map(c => c.value),
    };
    const res = await apiPost("/tariffs", payload);
    if (res) {
        showToast(`Tarifario ${res.code} creado`, "success");
        state.showTariffForm = false;
        await loadTarifario();
    }
}

export async function deleteTariff(id, code) {
    if (!confirm(`Eliminar tarifario ${code}? Esta acción no se puede deshacer.`)) return;
    const res = await apiDelete(`/tariffs/${id}`);
    if (res) {
        showToast(`Tarifario ${code} eliminado`, "success");
        await loadTarifario();
    }
}

export function toggleTarifCat(cat) {
    state.tarifExpanded[cat] = !state.tarifExpanded[cat];
    renderTarifarioView();
}

export function toggleAllTarif(expand) {
    [...new Set(state.tariffData.map(t => t.category))].forEach(c => { state.tarifExpanded[c] = expand; });
    renderTarifarioView();
}

export function editTariff(id) {
    state.tarifEditingId = id;
    renderTarifarioView();
}

export function cancelTariff() {
    state.tarifEditingId = null;
    renderTarifarioView();
}

export async function saveTariff(id) {
    const input = document.getElementById(`tariff-${id}`);
    const newVal = parseFloat(input.value);
    if (isNaN(newVal) || newVal < 0) {
        showToast("Valor inválido", "error");
        return;
    }
    const res = await apiPut(`/tariffs/${id}`, { max_price: newVal });
    if (res) {
        showToast("Tarifario actualizado", "success");
        state.tarifEditingId = null;
        await loadTarifario();
    }
}
