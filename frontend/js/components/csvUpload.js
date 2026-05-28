// Componente reutilizable de subida CSV con modal de esquema.
// Entities soportadas: "tarifario", "siniestros"
import { state } from "../state.js";
import { showToast } from "../utils.js";
import { API } from "../api.js";

// ── Esquemas por entidad ────────────────────────────────

const SCHEMAS = {
    tarifario: {
        title: "Importar Tarifario desde CSV",
        endpoint: "/tariffs/import-csv",
        columns: [
            { name: "code",                  required: true,  type: "texto",   example: "REP-001",        description: "Código único del item (se convierte a mayúsculas)" },
            { name: "description",           required: true,  type: "texto",   example: "Parabrisas delantero",  description: "Descripción del repuesto o servicio" },
            { name: "category",              required: true,  type: "enum",    example: "repuesto",        description: "repuesto · pintura · material · mano_obra · servicio" },
            { name: "max_price",             required: true,  type: "decimal", example: "250.00",          description: "Precio máximo acordado en USD (use punto como separador decimal)" },
            { name: "tolerance_pct",         required: false, type: "decimal", example: "10",              description: "Porcentaje de tolerancia permitida (por defecto 10)" },
            { name: "expected_qty_min",      required: false, type: "decimal", example: "1",               description: "Cantidad mínima esperada por siniestro (por defecto 1)" },
            { name: "expected_qty_max",      required: false, type: "decimal", example: "2",               description: "Cantidad máxima esperada por siniestro (por defecto 2)" },
            { name: "applicable_claim_types",required: false, type: "lista",   example: "choque_frontal;choque_lateral", description: "Tipos de siniestro separados por punto y coma (;). Valores: choque_frontal · choque_lateral · choque_trasero · robo_accesorios · daño_granizo · rayon_pintura · rotura_parabrisas · vandalismo" },
        ],
        sampleRows: [
            ["REP-001", "Parabrisas delantero", "repuesto", "250.00", "10", "1", "1", "choque_frontal;choque_lateral"],
            ["REP-002", "Guardafango lateral izquierdo", "repuesto", "180.00", "10", "1", "2", "choque_lateral"],
            ["PIN-001", "Pintura en base agua (litro)", "pintura", "45.00", "15", "1", "5", "choque_frontal;rayon_pintura"],
            ["MO-001", "Mano de obra desmontaje capot", "mano_obra", "35.00", "5", "1", "1", "choque_frontal"],
        ],
    },
    siniestros: {
        title: "Importar Siniestros desde CSV",
        endpoint: "/claims/import-csv",
        columns: [
            { name: "policy_number",   required: true,  type: "texto",   example: "POL-0001",        description: "Identificador de la póliza. Si no existe se crea un placeholder." },
            { name: "insured_id",      required: true,  type: "texto",   example: "ASE-12345",       description: "Identificador del asegurado. Si no existe se crea un placeholder." },
            { name: "incident_date",   required: true,  type: "fecha",   example: "2026-05-12",      description: "Fecha de ocurrencia (YYYY-MM-DD, DD/MM/YYYY o ISO 8601)." },
            { name: "ramo",            required: false, type: "enum",    example: "Vehículos",       description: "Vehículos · Salud · Vida · Generales · Hogar · Otro (por defecto Vehículos)" },
            { name: "cobertura",       required: false, type: "enum",    example: "Choque",          description: "Choque · Robo · Atención médica · Incendio · Daño · Otro (por defecto Otro)" },
            { name: "estado",          required: false, type: "enum",    example: "Reserva",         description: "Reserva · Pago Total · Pago Parcial · Anticipo · Negativa · Cierre Sin Consecuencia · Liquidado (por defecto Reserva)" },
            { name: "insured_name",    required: false, type: "texto",   example: "Juan Pérez",      description: "Nombre del asegurado (se usa para crear el placeholder si no existe)." },
            { name: "monto_reclamado", required: false, type: "decimal", example: "1250.00",         description: "Monto reclamado en USD (use punto como separador decimal). Por defecto 0." },
            { name: "sucursal",        required: false, type: "texto",   example: "Quito-Norte",     description: "Sucursal o agencia responsable." },
            { name: "descripcion",     required: false, type: "texto",   example: "Choque en parqueadero", description: "Descripción libre del incidente." },
            { name: "vehicle_plate",   required: false, type: "texto",   example: "PBA-1234",        description: "Placa del vehículo. Se reutiliza si ya existe, o se crea uno nuevo asociado a la póliza." },
            { name: "vehicle_brand",   required: false, type: "texto",   example: "Toyota",          description: "Marca del vehículo." },
            { name: "vehicle_model",   required: false, type: "texto",   example: "Corolla",         description: "Modelo del vehículo." },
            { name: "vehicle_year",    required: false, type: "entero",  example: "2022",            description: "Año del vehículo." },
        ],
        sampleRows: [
            ["POL-0001", "ASE-12345", "2026-05-12", "Vehículos", "Choque",  "Reserva",       "Juan Pérez",  "1250.00", "Quito-Norte", "Choque en parqueadero", "PBA-1234", "Toyota", "Corolla", "2022"],
            ["POL-0002", "ASE-67890", "2026-05-15", "Vehículos", "Robo",    "Reserva",       "María López", "8500.00", "Guayaquil-Sur", "Robo total reportado", "GBB-7788", "Chevrolet", "Sail", "2020"],
            ["POL-0003", "ASE-12345", "2026-04-30", "Vehículos", "Daño",    "Pago Parcial",  "Juan Pérez",  "450.00",  "Quito-Norte", "Daño por granizo", "PBA-1234", "Toyota", "Corolla", "2022"],
        ],
    },
};

// ── Estado local del modal ──────────────────────────────

let _currentEntity = null;

function _messageFromDetail(detail) {
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map(d => d?.msg || JSON.stringify(d)).join("; ");
    if (detail && typeof detail === "object") return detail.reason || detail.error || JSON.stringify(detail);
    return "Error al procesar el archivo";
}

// ── Funciones públicas ──────────────────────────────────

export function showCsvSchemaModal(entity) {
    _currentEntity = entity;
    const schema = SCHEMAS[entity];
    if (!schema) { showToast("Entidad no soportada para importación CSV", "error"); return; }

    const existing = document.getElementById("csv-upload-modal");
    if (existing) existing.remove();

    const overlay = document.createElement("div");
    overlay.id = "csv-upload-modal";
    overlay.style.cssText = "position:fixed;inset:0;z-index:600;background:rgba(0,0,0,0.55);backdrop-filter:blur(4px);display:flex;align-items:flex-start;justify-content:center;overflow-y:auto;padding:24px 16px;";
    overlay.innerHTML = _renderModalContent(schema, entity);

    overlay.addEventListener("click", (e) => {
        if (e.target === overlay) closeCsvModal();
    });

    document.body.appendChild(overlay);
}

export function closeCsvModal() {
    const modal = document.getElementById("csv-upload-modal");
    if (modal) modal.remove();
    _currentEntity = null;
}

export function triggerCsvFilePicker() {
    const input = document.getElementById("csv-file-input");
    if (input) input.click();
}

export function handleCsvFileChange(input) {
    const file = input.files && input.files[0];
    if (!file) return;
    const nameEl = document.getElementById("csv-selected-filename");
    if (nameEl) nameEl.textContent = file.name;
    document.getElementById("csv-btn-upload").disabled = false;
}

export async function submitCsvUpload() {
    const input = document.getElementById("csv-file-input");
    const file = input && input.files && input.files[0];
    if (!file || !_currentEntity) return;

    const schema = SCHEMAS[_currentEntity];
    const btn = document.getElementById("csv-btn-upload");
    const resultEl = document.getElementById("csv-upload-result");

    btn.disabled = true;
    btn.textContent = "Subiendo...";
    resultEl.innerHTML = "";

    const formData = new FormData();
    formData.append("file", file);

    try {
        const headers = {};
        if (state.currentProfileToken) {
            headers["X-Profile-Token"] = state.currentProfileToken;
        }

        const res = await fetch(`${API}${schema.endpoint}`, {
            method: "POST",
            headers,
            body: formData,
        });

        if (res.status === 401) {
            showToast("Sesión expirada. Selecciona tu perfil.", "error");
            window.dispatchEvent(new CustomEvent("profile:expired"));
            return;
        }
        if (res.status === 403) {
            const data = await res.json().catch(() => ({}));
            const msg = _messageFromDetail(data.detail) || "Tu rol no tiene permisos para esta importación.";
            resultEl.innerHTML = `<div class="csv-result-box csv-result-error"><strong>Permiso denegado:</strong> ${msg}</div>`;
            btn.disabled = false;
            btn.textContent = "Importar CSV";
            return;
        }

        const data = await res.json();

        if (!res.ok) {
            resultEl.innerHTML = `<div class="csv-result-box csv-result-error"><strong>Error:</strong> ${_messageFromDetail(data.detail)}</div>`;
            btn.disabled = false;
            btn.textContent = "Importar CSV";
            return;
        }

        resultEl.innerHTML = _renderImportResult(data);

        const unit = _currentEntity === "siniestros" ? "siniestro(s)" : "item(s)";
        if (data.inserted > 0) {
            showToast(`${data.inserted} ${unit} importados correctamente`, "success");
            window.dispatchEvent(new CustomEvent("csv:imported", { detail: { entity: _currentEntity } }));
        } else if (data.errors === 0 && data.skipped > 0) {
            showToast(`No se insertaron ${unit}: todos ya existen en este perfil`, "warning");
        }

    } catch (e) {
        resultEl.innerHTML = `<div class="csv-result-box csv-result-error"><strong>Error de conexión:</strong> ${e.message}</div>`;
        showToast("Error de conexión con el servidor", "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Importar CSV";
    }
}

export function downloadCsvTemplate(entity) {
    const schema = SCHEMAS[entity];
    if (!schema) return;

    const headers = schema.columns.map(c => c.name).join(",");
    const rows = schema.sampleRows.map(r =>
        r.map(cell => (cell.includes(",") || cell.includes(";")) ? `"${cell}"` : cell).join(",")
    );
    const csv = [headers, ...rows].join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `plantilla_${entity}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ── Renderizado interno ─────────────────────────────────

function _renderEntityNotes(entity) {
    const common = `<li>La primera fila debe contener los nombres de columna (exactamente como se muestran arriba).</li>`;
    if (entity === "tarifario") {
        return common + `
            <li>El separador de columnas debe ser <strong>coma (,)</strong>. Para la columna <code>applicable_claim_types</code> use <strong>punto y coma (;)</strong> entre valores.</li>
            <li>Los items cuyo <code>code</code> ya existan en este perfil serán omitidos (no duplicados).</li>`;
    }
    if (entity === "siniestros") {
        return common + `
            <li>El separador de columnas debe ser <strong>coma (,)</strong>.</li>
            <li>Las fechas aceptan formato <code>YYYY-MM-DD</code>, <code>DD/MM/YYYY</code> o ISO 8601.</li>
            <li>Si la <code>policy_number</code>, <code>insured_id</code> o <code>vehicle_plate</code> no existen, se crean como placeholders para preservar el audit trail.</li>
            <li>Se omiten siniestros duplicados (misma póliza, asegurado, fecha y cobertura) que ya existan en el sistema o estén repetidos en el archivo.</li>`;
    }
    return common;
}

function _renderModalContent(schema, entity) {
    const cols = schema.columns;
    return `
    <div style="background:var(--bg-secondary);border:1px solid var(--border-primary);border-radius:16px;width:100%;max-width:780px;padding:28px;box-shadow:var(--shadow-lg);">

        <!-- Encabezado -->
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;">
            <div>
                <h2 style="margin:0 0 4px;color:var(--text-primary);font-size:1.2rem;">${schema.title}</h2>
                <p style="margin:0;font-size:0.82rem;color:var(--text-muted);">
                    Perfil activo: <strong style="color:var(--accent-indigo);">${state.currentProfileName || "—"}</strong>
                    &nbsp;·&nbsp; Los datos se importarán aislados a este perfil.
                </p>
            </div>
            <button onclick="closeCsvModal()" style="background:none;border:none;cursor:pointer;font-size:1.4rem;color:var(--text-muted);line-height:1;padding:2px 6px;">&times;</button>
        </div>

        <!-- Esquema requerido -->
        <div style="margin-bottom:20px;">
            <h3 style="font-size:0.9rem;text-transform:uppercase;letter-spacing:0.5px;color:var(--text-secondary);margin:0 0 10px;">Esquema requerido</h3>
            <div style="overflow-x:auto;border:1px solid var(--border-primary);border-radius:8px;">
                <table style="width:100%;border-collapse:collapse;font-size:0.8rem;">
                    <thead>
                        <tr style="background:var(--bg-tertiary);">
                            <th style="padding:8px 12px;text-align:left;font-weight:600;color:var(--text-secondary);border-bottom:1px solid var(--border-primary);">Columna</th>
                            <th style="padding:8px 12px;text-align:center;font-weight:600;color:var(--text-secondary);border-bottom:1px solid var(--border-primary);">Requerida</th>
                            <th style="padding:8px 12px;text-align:left;font-weight:600;color:var(--text-secondary);border-bottom:1px solid var(--border-primary);">Tipo</th>
                            <th style="padding:8px 12px;text-align:left;font-weight:600;color:var(--text-secondary);border-bottom:1px solid var(--border-primary);">Ejemplo</th>
                            <th style="padding:8px 12px;text-align:left;font-weight:600;color:var(--text-secondary);border-bottom:1px solid var(--border-primary);">Descripción</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${cols.map((col, i) => `
                        <tr style="${i % 2 === 0 ? "background:var(--bg-primary);" : "background:var(--bg-secondary);"}">
                            <td style="padding:8px 12px;font-family:var(--font-mono);color:var(--accent-indigo);font-weight:600;">${col.name}</td>
                            <td style="padding:8px 12px;text-align:center;">${col.required ? '<span style="color:#22c55e;font-weight:700;">✓ Sí</span>' : '<span style="color:var(--text-muted);">Opcional</span>'}</td>
                            <td style="padding:8px 12px;color:var(--text-secondary);">${col.type}</td>
                            <td style="padding:8px 12px;font-family:var(--font-mono);font-size:0.75rem;color:var(--text-muted);">${col.example}</td>
                            <td style="padding:8px 12px;color:var(--text-secondary);font-size:0.78rem;">${col.description}</td>
                        </tr>
                        `).join("")}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Notas -->
        <div style="background:var(--bg-tertiary);border-radius:8px;padding:12px 14px;margin-bottom:20px;font-size:0.8rem;color:var(--text-secondary);line-height:1.6;">
            <strong style="color:var(--text-primary);">Notas importantes:</strong>
            <ul style="margin:6px 0 0;padding-left:18px;">
                ${_renderEntityNotes(entity)}
                <li>Codificación recomendada: <strong>UTF-8</strong>. Se acepta también exportación directa desde Excel.</li>
            </ul>
        </div>

        <!-- Zona de subida -->
        <div style="border:2px dashed var(--border-primary);border-radius:10px;padding:20px;text-align:center;margin-bottom:16px;transition:border-color 0.2s;"
             id="csv-dropzone"
             ondragover="event.preventDefault();document.getElementById('csv-dropzone').style.borderColor='var(--accent-indigo)';"
             ondragleave="document.getElementById('csv-dropzone').style.borderColor='var(--border-primary)';"
             ondrop="event.preventDefault();document.getElementById('csv-dropzone').style.borderColor='var(--border-primary)';
                     document.getElementById('csv-file-input').files=event.dataTransfer.files;
                     handleCsvFileChange(document.getElementById('csv-file-input'));">
            <div style="font-size:2rem;margin-bottom:8px;">📂</div>
            <p style="margin:0 0 10px;color:var(--text-secondary);font-size:0.88rem;">Arrastra tu archivo CSV aquí o</p>
            <button class="btn btn-ghost btn-sm" onclick="triggerCsvFilePicker()">Seleccionar archivo</button>
            <input type="file" id="csv-file-input" accept=".csv" style="display:none;"
                   onchange="handleCsvFileChange(this)">
            <p id="csv-selected-filename" style="margin:10px 0 0;font-size:0.8rem;color:var(--accent-indigo);font-family:var(--font-mono);min-height:18px;"></p>
        </div>

        <!-- Resultado de importación -->
        <div id="csv-upload-result" style="margin-bottom:16px;"></div>

        <!-- Botones de acción -->
        <div style="display:flex;gap:10px;justify-content:flex-end;flex-wrap:wrap;">
            <button class="btn btn-ghost btn-sm" onclick="downloadCsvTemplate('${entity}')">
                ⬇ Descargar plantilla CSV
            </button>
            <button class="btn btn-ghost" onclick="closeCsvModal()">Cancelar</button>
            <button class="btn btn-primary" id="csv-btn-upload" disabled onclick="submitCsvUpload()">
                Importar CSV
            </button>
        </div>
    </div>
    `;
}

function _renderImportResult(data) {
    const hasErrors = data.errors > 0;
    const hasSkipped = data.skipped > 0;
    const hasInserted = data.inserted > 0;

    let html = `<div style="border:1px solid var(--border-primary);border-radius:8px;overflow:hidden;font-size:0.82rem;">`;

    // Summary bar
    html += `
    <div style="display:flex;gap:0;border-bottom:1px solid var(--border-primary);">
        <div style="flex:1;padding:10px 14px;text-align:center;background:${hasInserted ? "rgba(34,197,94,0.1)" : "var(--bg-tertiary)"};">
            <div style="font-size:1.4rem;font-weight:700;color:${hasInserted ? "#22c55e" : "var(--text-muted)"};">${data.inserted}</div>
            <div style="color:var(--text-secondary);">Insertados</div>
        </div>
        <div style="flex:1;padding:10px 14px;text-align:center;background:${hasSkipped ? "rgba(234,179,8,0.08)" : "var(--bg-tertiary)"};border-left:1px solid var(--border-primary);">
            <div style="font-size:1.4rem;font-weight:700;color:${hasSkipped ? "#eab308" : "var(--text-muted)"};">${data.skipped}</div>
            <div style="color:var(--text-secondary);">Omitidos</div>
        </div>
        <div style="flex:1;padding:10px 14px;text-align:center;background:${hasErrors ? "rgba(239,68,68,0.08)" : "var(--bg-tertiary)"};border-left:1px solid var(--border-primary);">
            <div style="font-size:1.4rem;font-weight:700;color:${hasErrors ? "#ef4444" : "var(--text-muted)"};">${data.errors}</div>
            <div style="color:var(--text-secondary);">Errores</div>
        </div>
    </div>`;

    const detail = data.detail || {};

    if (detail.errors && detail.errors.length > 0) {
        html += `<div style="padding:10px 14px;border-bottom:1px solid var(--border-primary);background:rgba(239,68,68,0.04);">
            <strong style="color:#ef4444;">Filas con errores:</strong>
            <ul style="margin:6px 0 0;padding-left:16px;color:var(--text-secondary);">
                ${detail.errors.slice(0, 10).map(e => `<li>Fila ${e.row}${e.code ? ` (${e.code})` : ""}: ${e.reason}</li>`).join("")}
                ${detail.errors.length > 10 ? `<li>…y ${detail.errors.length - 10} más</li>` : ""}
            </ul>
        </div>`;
    }

    if (detail.skipped && detail.skipped.length > 0) {
        html += `<div style="padding:10px 14px;background:rgba(234,179,8,0.04);">
            <strong style="color:#eab308;">Códigos omitidos (ya existen):</strong>
            <span style="color:var(--text-muted);margin-left:8px;">${detail.skipped.map(s => s.code).join(", ")}</span>
        </div>`;
    }

    html += `</div>`;
    return html;
}
