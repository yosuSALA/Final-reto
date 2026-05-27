# Manual de Uso — Auditor Agéntico de Facturación

> Guía paso a paso para usuarios del sistema (auditores, supervisores y demo).
> Para detalles técnicos ver [`README.md`](../README.md). Para descripción de funciones internas ver [`DOC_FUNCIONES.md`](DOC_FUNCIONES.md).

---

## 1. ¿Qué hace la aplicación?

Plataforma agéntica que audita facturas de talleres mecánicos enviadas a la aseguradora. El sistema:

1. **Recibe** la factura en PDF (drag-drop o generador de prueba).
2. **Extrae** los ítems automáticamente.
3. **Audita** cruzando contra el siniestro declarado y el tarifario maestro.
4. **Genera** un reporte interno (con riesgo) y una notificación formal al taller.

Existen dos motores intercambiables sobre la misma factura:

- ⚡ **Reglas** — rápido (~1-2 s), determinístico.
- 🤖 **IA Gemini** — más lento (~15-30 s), añade razonamiento textual.

Re-auditar **reemplaza** el resultado existente. Nunca se duplican registros.

---

## 2. Cómo arrancar

### Opción A — Inicio rápido

- **Windows:** doble-click en `start.bat`.
- **Mac/Linux:** `bash start.sh`.

### Opción B — Manual

```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

Luego abrir en navegador:

- Landing: <http://localhost:8000/>
- Aplicación: <http://localhost:8000/app/>

> **API Key Gemini (opcional):** crear `.env` en la raíz con `GOOGLE_API_KEY=tu_key`. Sin esta clave el motor IA corre en modo prueba (mock). El motor de reglas funciona siempre.

---

## 3. Recorrido por la aplicación

### 3.1 Dashboard (`#dashboard`)

Pantalla de inicio. Muestra:

- KPIs: facturas auditadas, monto total, sobrecobro detectado, ahorro estimado.
- Scatter de siniestros por día.
- Donut de hallazgos por severidad.
- Toggle **Incluir TEST** — por defecto oculta facturas de prueba.

### 3.2 Subir Factura (`#upload`)

Dos paneles + un checkbox:

1. **Drag-drop (panel izquierdo):**
   - (Opcional) Asocia un siniestro del listado.
   - Marca/desmarca **TEST** según corresponda.
   - Arrastra el PDF o haz click para elegir.
   - El sistema lo extrae y queda **pendiente** de auditoría.

2. **Generador random (panel derecho):**
   - Genera facturas con formato SRI Ecuador (RUC, clave acceso 49 dígitos, módulo 11).
   - Botones: `+ Limpia`, `+ Sobrecobro`, `+ Fraude`, `+ Aleatorio`.
   - Cada card permite **Descargar PDF** o **Auditar directo** (lo inyecta al drag-drop con TEST=on).

> **Restricciones:** solo `.pdf`, máximo 10 MB.

### 3.3 Auditorías (`#auditorias`)

Dos pestañas:

- **Pendientes** — facturas sin auditar. Botón **Auditar ahora** abre selector de motor.
- **Revisadas** — historial con badge del motor (⚡ REGLAS / 🤖 IA), risk score, estado.

Filtros disponibles: búsqueda por número o taller, toggle TEST.

### 3.4 Detalle de auditoría (`#audit/{id}`)

Pantalla central del auditor. Contiene:

- Header con risk score y badge del motor usado.
- Lista de hallazgos con severidad (CRÍTICO / WARNING / INFO).
- Tabla de ítems con flags ⚠ en filas con problema.
- Botones de acción:
  - **Re-auditar Reglas** / **Re-auditar IA** — reemplaza el resultado.
  - **Aprobar** / **Rechazar** / **Escalar** — decisión humana.
  - **Reporte Interno** — PDF con risk score y análisis completo.
  - **Notificación Taller** — PDF profesional, sin risk score, con el mensaje formal del Departamento de Auditoría Técnica de Siniestros.

### 3.5 Tarifario (`#tarifario`)

Catálogo maestro contra el que se auditan los ítems.

- Categorías colapsables (repuesto, pintura, material, mano de obra, servicio).
- Botón **+ Añadir Tarifario Manual** — abre form con: código, descripción, categoría, precio máx, tolerancia %, cantidades min/max, checkboxes de siniestros aplicables.
- **Eliminar** por fila.

### 3.6 Siniestros (`#siniestros`)

Tabla expandible. Cada fila despliega las facturas asociadas al siniestro.

---

## 4. Flujo recomendado para la demo

1. Abrir landing → click **Lanzar Aplicación Web**.
2. Ir a `#upload` → panel derecho → click **+ Fraude** → click **Auditar directo**.
3. La factura aparece en `#auditorias` (pestaña Pendientes) → **Auditar ahora** → elegir motor.
4. Abrir `#audit/{id}` → mostrar hallazgos + Risk Score.
5. Click **Notificación Taller** → mostrar PDF con mensaje formal del Departamento de Auditoría Técnica de Siniestros.
6. Click **Re-auditar IA** → mostrar el cambio de motor sin duplicación.
7. Volver a `#dashboard` → activar toggle TEST para ver el impacto.

---

## 5. Reportes generados

| Reporte               | Audiencia | Contenido                                                    |
|-----------------------|-----------|--------------------------------------------------------------|
| Reporte Interno       | Auditor   | Risk score, severidad por hallazgo, ítems con flags          |
| Notificación Taller   | Taller    | Profesional, sin risk score, ajustes requeridos, mensaje formal del Departamento de Auditoría Técnica de Siniestros |

Ambos se generan con `reportlab` desde `backend/pdf_generator.py` y se sirven inline en el navegador. Los PDFs persistidos quedan en `backend/generated_reports/`.

---

## 6. Modo prueba (TEST)

Para no contaminar las métricas reales con datos de demo:

- El generador random marca por defecto las facturas como **TEST**.
- Las facturas TEST entran a la DB y se auditan con el flujo normal.
- El dashboard real las **oculta** por defecto. Toggle **Incluir TEST** las muestra.
- Visible con badge gris **TEST** en listas y detalle.

---

## 7. Preguntas frecuentes

**¿Necesito API Key para la demo?**
No. El motor de reglas no la requiere. Sin `GOOGLE_API_KEY`, el motor IA usa modo prueba (mock) y devuelve respuestas simuladas.

**¿Puedo re-auditar la misma factura varias veces?**
Sí. Cada re-auditoría reemplaza el resultado anterior. El badge del motor refleja siempre el último usado.

**¿Dónde quedan los PDFs generados?**
En `backend/generated_reports/`. El nombre incluye número de factura y timestamp.

**¿Qué pasa si subo dos veces el mismo PDF?**
La DB tiene `UniqueConstraint(invoice_number, workshop_id)`. El segundo intento es rechazado y el frontend bloquea cargas concurrentes con un flag in-flight.

**¿Cómo cambio el puerto?**
Editar `--port 8000` en el comando `uvicorn` (o en `start.bat` / `start.sh`).

---

## 8. Atajos útiles

| Acción                          | Cómo                                                |
|---------------------------------|-----------------------------------------------------|
| Generar 5 facturas mixtas       | `curl -X POST "http://localhost:8000/api/test-pdfs/random?scenario=mixed&count=5"` |
| Listar resultados sin TEST      | `GET /api/audit-results?include_test=0`             |
| Forzar regeneración escenarios  | `python -m backend.test_invoice_generator`          |
| Ver lista de endpoints          | <http://localhost:8000/docs> (Swagger UI)           |

---

## 9. Equipo

**Miraclex — HackIAthon 2026**
Josue Salazar · Andres Abad · Andres Falconi
