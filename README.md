# Auditor Agéntico de Facturación de Siniestros

Sistema agéntico que audita automáticamente facturas de talleres enviadas a aseguradoras. Cruza ítems facturados contra el siniestro declarado y el tarifario maestro, detectando sobrecobros, duplicados, incoherencias y patrones de fraude antes de la revisión humana.

**Doble motor**: motor de reglas determinístico (rápido, ~1s) + motor IA Gemini (opcional, 15-30s). Re-auditar el mismo invoice **reemplaza** el resultado existente — un único `AuditResult` por factura, sin duplicación.

---

## Arquitectura

```
reto-Hackiaton/
├── backend/
│   ├── main.py                     # API FastAPI (entrypoint)
│   ├── agent.py                    # Agente Auditor (motor reglas)
│   ├── gemini_auditor.py           # Auditor IA — Gemini 2.5 Flash (CoT, few-shot)
│   ├── rules_engine.py             # Motor de reglas determinístico
│   ├── pdf_extractor.py            # Extractor de facturas desde PDF (pdfplumber)
│   ├── pdf_generator.py            # Generador de PDFs de auditoría (interno + taller)
│   ├── test_invoice_generator.py   # Generador de PDFs de FACTURAS DE PRUEBA (formato SRI)
│   ├── models.py                   # Modelos SQLAlchemy (con UniqueConstraint + is_test flag)
│   ├── database.py                 # Configuración SQLite + migración liviana de columnas
│   ├── seed_data.py                # Datos demo con anomalías plantadas
│   └── requirements.txt
├── frontend/
│   ├── index.html                  # SPA shell (script type="module")
│   ├── style.css                   # Design system (Premium dark theme)
│   └── js/                         # ★ Frontend modular ES Modules (sin build step)
│       ├── main.js                 # Entry: expone fns a window para inline onclick
│       ├── api.js                  # Cliente HTTP
│       ├── state.js                # Estado mutable compartido
│       ├── utils.js                # Toast, badges, animaciones
│       ├── router.js               # SPA routing por hash
│       ├── components/
│       │   └── charts.js           # SVG donut + scatter
│       └── pages/
│           └── ...                 # Vistas de la aplicación
├── docs/
│   ├── facturas_muestra/           # PDFs de ejemplo generados
│   ├── MANUAL_USO.md               # ★ Manual de uso paso a paso (usuario final)
│   └── DOC_FUNCIONES.md            # Manual de funciones
├── .dev_tools/                     # Scripts y utilidades de desarrollo
├── landing.html                    # Página de presentación para el Hackathon
└── README.md
```

---

## Stack Tecnológico

| Componente       | Tecnología                                     |
|------------------|------------------------------------------------|
| Backend          | Python 3.10+ / FastAPI                         |
| Base de Datos    | SQLite (vía SQLAlchemy)                        |
| Frontend         | HTML + CSS + JavaScript (ES Modules nativos)   |
| Motor reglas     | rules_engine determinístico (1-2s)             |
| Motor IA         | **Gemini 2.5 Flash** (Google AI, opcional)     |
| Extracción PDF   | pdfplumber                                     |
| Generación PDF   | reportlab                                      |

---

## Instalación y Ejecución

### 1. (Opcional) Configurar API Key de Google AI

Solo si quieres usar el motor IA Gemini. El sistema funciona sin ella usando el motor de reglas.

Crear archivo `.env` en la raíz del repo:

```
GOOGLE_API_KEY=tu_api_key_aqui
```

Obtener key gratis en: https://aistudio.google.com/app/apikey

### 2. Backend

```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

### 3. Frontend

Abrir en navegador: `http://localhost:8000/app/`

**Inicio rápido**: doble-click `start.bat` (Windows) o `bash start.sh` (Mac/Linux).

> 📖 **Manual de uso paso a paso para usuarios:** [`docs/MANUAL_USO.md`](docs/MANUAL_USO.md)

---

## Páginas de la App Web

| Ruta                | Descripción                                                                |
|---------------------|----------------------------------------------------------------------------|
| `#dashboard`        | KPIs + scatter de siniestros + donut hallazgos + toggle TEST              |
| `#auditorias`       | Tabs Pendientes/Revisadas con búsqueda + filtro TEST + badge motor (REGLAS/IA) |
| `#tarifario`        | Categorías colapsables + **botón Añadir Tarifario Manual** + Eliminar     |
| `#siniestros`       | Tabla expandible — preview de facturas asociadas inline                    |
| `#upload`           | Drag-drop PDF + checkbox TEST + generador random formato SRI               |
| `#pending/{id}`     | Selector de motor: ⚡ Reglas (rápido) o 🤖 IA Gemini (lento)               |
| `#audit/{id}`       | Detalle + **botones Re-auditar Reglas / Re-auditar IA** (reemplaza, no duplica) |

---

## Doble Motor de Auditoría — Sin Duplicación

**Garantía**: existe **un único `AuditResult` por `invoice_id`**. Re-auditar la misma factura con cualquier motor:

1. Encuentra el `AuditResult` existente.
2. Reemplaza `status`, `risk_score`, `total_overcharge`, `summary`.
3. Actualiza `audit_engine` al motor recién usado (`rules` o `gemini`).
4. **Borra todos los `AuditFinding` previos** y reinserta los nuevos.

Ningún flujo crea un segundo `AuditResult` para el mismo invoice. La columna `audit_engine` siempre refleja el último motor empleado, visible como badge en `#auditorias` y en el header de `#audit/{id}`.

### Cuándo usar cada motor

| Motor       | Cuándo                                              | Latencia | Hallazgos                                      |
|-------------|-----------------------------------------------------|----------|------------------------------------------------|
| Reglas (⚡) | Default. Producción, batch, validación rápida       | 1-2 s    | Sobrecobro, Duplicado, Cantidad, Incoherencia, Re-Facturación |
| IA Gemini   | Casos ambiguos, análisis cualitativo, justificación | 15-30 s  | Lo anterior + razonamiento textual + patrones cruzados |

---

## Generar PDFs de Prueba y Drag-Drop

La página **Subir PDF** (`#upload`) tiene dos paneles + un checkbox TEST.

### Checkbox "Marcar como factura de prueba (TEST)"

Default ON al subir desde el generador random. Las facturas TEST:
- **Sí entran a la DB** y son auditadas con el mismo flujo (no se duplican).
- **No cuentan en el dashboard real** (se filtran via `?include_test=0`).
- Visible con badge gris **TEST** en listas y detalle.
- Toggle "Incluir TEST" en dashboard y auditorías para ver/ocultar.

### Panel izquierdo — Drag-drop

1. (Opcional) Selecciona un siniestro asociado.
2. Marca/desmarca TEST según corresponda.
3. Arrastra un PDF o click para elegir.
4. El sistema extrae datos con `pdf_extractor.py` y queda **pendiente** de auditoría.
5. Ve a `#auditorias` → tab Pendientes → "Auditar ahora" → elige motor.

Restricciones: solo `.pdf`, máximo 10 MB. **Race condition prevenida**: doble-click al subir está guardado por flag interno, y la DB tiene `UniqueConstraint(invoice_number, workshop_id)`.

### Panel derecho — Generador Random (formato SRI Ecuador)

Cada click genera una factura PDF aleatoria y única con formato SRI:
RUC random 13-dígitos, número factura `eee-ppp-sssssssss`, clave de acceso 49-dígitos
con módulo 11, fecha aleatoria últimos 25 días, items random según tipo de siniestro.

| Botón          | Escenario                                                | Hallazgo esperado                       |
|----------------|----------------------------------------------------------|------------------------------------------|
| + Limpia       | Items dentro de tarifario, siniestro coherente           | **Aprobado** — sin hallazgos             |
| + Sobrecobro   | Un ítem aleatorio +30-65% sobre tarifario                | **WARNING/CRITICAL** — sobrecobro        |
| + Fraude       | Ítem duplicado + ítem incoherente con el siniestro       | **CRITICAL** — duplicado + incoherencia  |
| + Aleatorio    | Mezcla aleatoria entre los 3 anteriores                  | Variable                                 |

**Acciones por card:** Descargar PDF + **Auditar directo** (lo inyecta al drag-drop con TEST=on).

### Generación vía CLI / API

```bash
python -m backend.test_invoice_generator
# Genera los 3 escenarios canónicos en backend/test_pdfs/

# Una factura random por escenario
curl -X POST "http://localhost:8000/api/test-pdfs/random?scenario=fraude&count=1"

# Batch de 5 mixed
curl -X POST "http://localhost:8000/api/test-pdfs/random?scenario=mixed&count=5"
```

---

## Reglas de Auditoría (motor determinístico)

| Regla              | Descripción                                              | Severidad         |
|--------------------|----------------------------------------------------------|-------------------|
| Sobrecobro         | Precio unitario excede tarifario + tolerancia            | WARNING / CRITICAL |
| Duplicado          | Mismo ítem facturado más de una vez                      | CRITICAL          |
| Cantidad Anómala   | Cantidades fuera del rango esperado                      | WARNING / INFO    |
| Incoherencia       | Ítems no corresponden al tipo de siniestro               | CRITICAL          |
| Re-Facturación     | Mismo invoice_number en histórico con siniestro distinto | CRITICAL          |

Calibración severidad: `exceso ≤ tolerancia → INFO`, `tolerancia < exceso ≤ 30% → WARNING`, `exceso > 30% → CRITICAL`.

Risk score: `CRITICAL × 35 + WARNING × 20 + INFO × 5`, cap a 100.

---

## Tarifarios Manuales

Desde `#tarifario` → botón **"+ Añadir Tarifario Manual"**:

- Form con: código, descripción, categoría (repuesto/pintura/material/mano_obra/servicio), precio máx, tolerancia %, cant. min/max, **checkboxes de siniestros aplicables** (8 tipos).
- Validación: código único (DB rechaza duplicados con HTTP 409).
- **Eliminar** desde cada fila de tarifario.

Endpoints: `POST /api/tariffs`, `PUT /api/tariffs/{id}`, `DELETE /api/tariffs/{id}`.

---

## PDFs Generados por el Sistema

Dos modos (configurable vía `?type=`):

| Modo        | Audiencia | Contenido                                                          |
|-------------|-----------|--------------------------------------------------------------------|
| `internal`  | Auditor   | Risk score color-codeado, severidad por hallazgo, items con flags ⚠ |
| `workshop`  | Taller    | Profesional, sin risk score, ajustes requeridos + mensaje fijo     |

Ambos PDFs usan **plantillas predeterminadas** en `pdf_generator.py`. El texto del taller usa el `resumen_ejecutivo_taller` si existe; si no, mensaje genérico fijo. Esto evita depender de Gemini para el texto narrativo y mantiene los reportes consistentes.

Endpoint: `GET /api/audit-results/{id}/report-preview?type=internal|workshop`

---

## API Endpoints

### Dashboard

| Método | Endpoint                                          | Descripción                         |
|--------|---------------------------------------------------|-------------------------------------|
| GET    | `/api/dashboard?include_test=0\|1`               | KPIs (filtra TEST por defecto)      |
| GET    | `/api/dashboard/claims-by-day?days=N`             | Serie diaria scatter                |

### Auditoría

| Método | Endpoint                                          | Motor    | Descripción                              |
|--------|---------------------------------------------------|----------|------------------------------------------|
| POST   | `/api/audit-rules/{invoice_id}`                   | reglas   | **★ Auditoría rápida (~1-2s)**           |
| POST   | `/api/audit/{invoice_id}`                         | reglas   | Alias del anterior                       |
| POST   | `/api/audit-all`                                  | reglas   | Auditar todas con reglas                 |
| POST   | `/api/audit-ai/{invoice_id}`                      | gemini   | Auditar 1 factura con Gemini             |
| POST   | `/api/audit-ai-all`                               | gemini   | Auditar todas con Gemini                 |
| POST   | `/api/audit-gemini-batch`                         | gemini   | Batch con análisis de patrones cruzados  |
| POST   | `/api/audit-pdf`                                  | -        | Subir PDF (Form: file, claim_number, is_test) |
| GET    | `/api/audit-results?include_test=0\|1`           | -        | Listar resultados                        |
| GET    | `/api/audit-results/{id}`                         | -        | Detalle                                  |
| GET    | `/api/audit-results/{id}/report-preview?type=...` | -        | Preview PDF                              |
| POST   | `/api/audit-results/{id}/notify`                  | -        | Notificación + simular email             |
| POST   | `/api/audit-results/{id}/{approve\|reject\|escalate}` | -    | Acción manual                            |

### Catálogos

| Método | Endpoint                              | Descripción                       |
|--------|---------------------------------------|-----------------------------------|
| GET    | `/api/tariffs`                        | Listar tarifario                  |
| **POST** | **`/api/tariffs`**                  | **Crear tarifario manual**        |
| PUT    | `/api/tariffs/{id}`                   | Modificar precio máximo           |
| **DELETE** | **`/api/tariffs/{id}`**           | **Eliminar tarifario**            |
| GET    | `/api/claims`                         | Siniestros                        |
| GET    | `/api/claims/{id}/invoices`           | Facturas preliminares             |
| GET    | `/api/invoices/pending?include_test=0\|1` | Facturas sin auditoría        |

### PDFs de Prueba

| Método | Endpoint                                                | Descripción                                       |
|--------|---------------------------------------------------------|---------------------------------------------------|
| GET    | `/api/test-pdfs`                                        | Lista escenarios disponibles                      |
| POST   | `/api/test-pdfs/generate`                               | (Re)generar los 3 PDFs canónicos                  |
| POST   | `/api/test-pdfs/random?scenario=X&count=N`              | Generar N facturas random                         |
| GET    | `/api/test-pdfs/{filename}`                             | Descargar PDF                                     |

---

## Modelo de Datos

### Tablas (SQLAlchemy)

- `workshops` — talleres (RUC unique).
- `claims` — siniestros (claim_number unique).
- `invoices` — facturas. **`UniqueConstraint(invoice_number, workshop_id)` previene duplicados.** Columna `is_test` flag.
- `invoice_items` — ítems (cascade delete).
- `tariff_items` — tarifario maestro (code unique).
- `audit_results` — **un único registro por invoice_id**. Columnas: `audit_engine` (rules|gemini), `is_test`, status, risk_score, total_overcharge, summary, agent_notes, audited_at.
- `audit_findings` — hallazgos (cascade delete con audit_result).

### Migración liviana

`init_db()` ejecuta `Base.metadata.create_all` + `_migrate_columns()` que añade `is_test` y `audit_engine` si faltan en DBs existentes (idempotente).

---

## Patrones SOTA del Auditor IA (Gemini)

Implementados en `backend/gemini_auditor.py`:

1. **Chain-of-Thought forzado** — schema con orden de campos: razonamiento ANTES de veredicto.
2. **Few-shot calibration** — 2 ejemplos worked en system prompt (limpio + fraude).
3. **Citación de evidencia** — cada hallazgo requiere `evidencia_citada` literal del input.
4. **Confianza calibrada** — score 0.0-1.0 por hallazgo. CRITICAL requiere ≥ 0.7.
5. **Self-reflection** — opcional (`enable_self_reflection=False` por default para velocidad).
6. **Validación semántica + retry** — coherencia status ↔ severidad. 1 retry con feedback.
7. **Mock mode** — si falta `GOOGLE_API_KEY`, devuelve respuesta de prueba sin llamar al API.

---

## Escenarios Demo (Seed)

| # | Siniestro          | Taller        | Anomalía                           | Severidad  |
|---|--------------------|---------------|-------------------------------------|------------|
| 1 | Choque frontal     | AutoFix S.A.  | Limpio                             | -          |
| 2 | Robo accesorios    | TallerPro     | Sobrecobro mano obra +35%          | WARNING    |
| 3 | Daño granizo       | CarGlass      | Cobro duplicado parabrisas         | CRITICAL   |
| 4 | Choque lateral     | AutoFix S.A.  | Repuesto motor en siniestro puerta | CRITICAL   |
| 5 | Rayón pintura      | TallerPro     | Cantidad excesiva pintura (5 gal)  | WARNING    |

---

## Cambios recientes

- ★ **Doble motor con un único resultado**: rules + gemini upsert garantizado, no hay duplicación de `AuditResult`. Botones "Re-auditar Reglas" y "Re-auditar IA" en `#audit/{id}` reemplazan el resultado existente.
- ★ **Frontend modular** ES Modules en `frontend/js/` (sin build step).
- ★ **Tarifarios manuales**: POST/DELETE + UI con form completo (code, desc, cat, precio, tol, qty, claim_types).
- ★ **Flag TEST**: facturas de prueba en DB pero filtrables del dashboard real.
- ★ **Anti-duplicado**: `UniqueConstraint` + `IntegrityError` handling + frontend in-flight guard.
- ★ **Velocidad**: rules-engine como motor default (~1s). Gemini opcional con self-reflection desactivada.
