# Documentación de Funciones: Auditor Agéntico de Facturación

Este documento describe detalladamente las funciones principales de la aplicación para que cualquier usuario o desarrollador que la descargue entienda de qué va el proyecto y cómo utilizarlo.

## 🎯 ¿De qué trata esta aplicación?

Esta aplicación es un **Sistema de Auditoría Agéntico** multi-ramo (vehículos, salud, vida, hogar, generales). Su objetivo es revisar automáticamente las facturas enviadas por los talleres y proveedores para detectar fraudes, errores o cobros excesivos antes de que un agente humano las apruebe para el pago.

Combina **dos motores complementarios**:

1. **Motor de Reglas determinístico** (default, ~1-2 segundos): aplica las reglas de tarifario, duplicados, cantidades anómalas, incoherencia con el siniestro y re-facturación.
2. **Motor IA DeepSeek V4 Flash** (5-8 segundos): añade razonamiento cualitativo, citación de evidencia y patrones cruzados.

> **Importante**: aunque puedas auditar la misma factura primero con reglas y luego con IA, el sistema **no genera dos registros**. Existe un único `AuditResult` por factura, y al re-auditar simplemente se reemplaza su contenido y se actualiza el campo `audit_engine` para reflejar el último motor utilizado. No hay duplicación.

---

## 🛠️ Funciones Principales

### 1. Panel de Control (Dashboard)

- **KPIs en tiempo real**: total de facturas auditadas, monto total facturado, sobrecobro detectado y porcentaje de ahorro estimado para la aseguradora.
- **Toggle "Incluir TEST"**: por defecto, el dashboard muestra solo facturas reales. Activa el toggle para ver también las facturas de prueba.
- **Gráficos**: scatter de siniestros diarios + donut de hallazgos por severidad (Crítico / Advertencia / Limpio).

### 2. Gestión de Auditorías (Pendientes vs. Revisadas)

- **Pendientes**: facturas recién recibidas que aún no han sido auditadas por ningún motor.
- **Revisadas**: historial con badge del motor usado (⚡ REGLAS o 🤖 IA), risk score y estado.
- **Búsqueda** por número de factura o nombre de taller.
- **Filtro TEST**: incluye o excluye facturas de prueba.
- **Auditoría JIT (Just-In-Time)**: desde una factura pendiente puedes elegir el motor:
  - ⚡ **Auditar con Reglas** — rápido (~1s), determinístico.
  - 🤖 **Auditar con IA DeepSeek** — completo (~5-8s), requiere `OPENCODE_GO_API_KEY`.

### 3. Detalle de Auditoría con Re-auditoría sin Duplicación

En la vista detalle (`#audit/{id}`):

- **Badge del motor**: muestra qué motor produjo el resultado actual (REGLAS o IA).
- **Botones "Re-auditar Reglas" / "Re-auditar IA"**: re-ejecutan el análisis con el motor elegido. El resultado **reemplaza** al anterior — el `audit_id` no cambia, los hallazgos antiguos se borran y se insertan los nuevos.
- **Acciones manuales**: Aprobar, Rechazar, Escalar.
- **Reportes PDF**: vista previa del reporte interno con risk score, hallazgos e items de factura.

### 4. Motor de Reglas (rápido, default)

`backend/rules_engine.py` evalúa cinco reglas:

- **Sobrecobro**: precio unitario vs tarifario + tolerancia.
- **Duplicado**: mismo ítem cobrado más de una vez en la misma factura.
- **Cantidad Anómala**: cantidad fuera del rango esperado del tarifario.
- **Incoherencia**: ítem que no aplica al tipo de siniestro declarado.
- **Re-Facturación**: número de factura ya presente en otro siniestro del histórico.

Calibración: `exceso ≤ tolerancia → INFO`, `tolerancia < exceso ≤ 30% → WARNING`, `exceso > 30% → CRITICAL`.

### 5. Motor IA Gemini (opcional)

`backend/gemini_auditor.py` aplica patrones SOTA:

- Chain-of-Thought forzado por orden de campos en schema JSON.
- Few-shot calibration con 2 ejemplos (limpio + fraude).
- Citación de evidencia literal del input para cada hallazgo.
- Confianza calibrada 0.0-1.0; CRITICAL requiere ≥ 0.7.
- Validación semántica + retry con feedback.
- Mock mode si falta `GOOGLE_API_KEY` (devuelve respuesta de prueba).

### 6. Tarifario Maestro con Tarifarios Manuales

- **Vista**: categorías colapsables (repuesto, pintura, material, mano_obra, servicio).
- **Modificar precio máximo** de cualquier ítem en línea.
- ★ **Añadir Tarifario Manual**: form completo con código, descripción, categoría, precio máx, tolerancia %, cantidad mín/máx, y checkboxes para los 8 tipos de siniestro aplicables.
- ★ **Eliminar Tarifario**: botón por fila (con confirmación).

### 7. Vista 360° del Siniestro

Permite ver un siniestro y todas las facturas asociadas a ese mismo caso, facilitando la detección de re-facturación (intentar cobrar el mismo daño en varias facturas separadas).

### 8. Generación y Previsualización de Reportes (PDF)

- **Reporte Interno**: PDF detallado para el auditor humano. Incluye Risk Score, severidad por hallazgo y items con flag ⚠ sobre tarifario.
- **Notificación al Taller**: PDF profesional sin Risk Score, con la lista de ajustes requeridos y un mensaje ejecutivo. Usa **plantillas predeterminadas**: si la auditoría no tiene `resumen_ejecutivo_taller`, se usa un texto fijo. Esto evita depender de Gemini para el texto narrativo y mantiene los reportes consistentes y rápidos.

### 9. Ingreso de Nuevas Facturas (Drag & Drop) con Flag TEST

- **Drag-drop**: arrastra una factura PDF; el extractor la procesa y queda **pendiente** de auditoría.
- ★ **Checkbox "Marcar como factura de prueba (TEST)"**: las facturas TEST entran a la DB y se auditan, pero no aparecen en el dashboard real (filtrables vía toggle).
- **Anti-duplicado**: `UniqueConstraint(invoice_number, workshop_id)` en DB + flag interno que bloquea cargas concurrentes en el frontend. Si por race condition llega un duplicado, el backend captura el `IntegrityError` y devuelve la factura existente sin crear una nueva.

### 10. Generador Random de Facturas SRI Ecuador

Cada click genera un PDF único con formato SRI: RUC random 13-dígitos, número factura `eee-ppp-sssssssss`, clave de acceso 49-dígitos con módulo 11, fecha aleatoria, items según tipo de siniestro.

Cuatro escenarios:
- **+ Limpia** — items dentro de tarifario.
- **+ Sobrecobro** — un ítem +30-65% sobre tarifario.
- **+ Fraude** — duplicado + ítem incoherente.
- **+ Aleatorio** — mezcla de los anteriores.

Cada card del generador tiene **Descargar PDF** y **Auditar directo** (lo inyecta al drag-drop con TEST=on).

---

## 🚀 ¿Cómo iniciar el proyecto rápidamente?

- **En Windows**: doble clic en `start.bat`.
- **En Mac/Linux**: `bash start.sh`.

La aplicación queda disponible en `http://localhost:8000/app/`.

Si no configuras `GOOGLE_API_KEY` en `.env`, el motor IA entra en **modo mock** y el motor de reglas funciona sin cambios. El sistema es completamente usable sin Gemini.

---

## 🔒 Garantías de No Duplicación

El sistema asegura que ninguna re-auditoría genere registros duplicados, en tres niveles:

1. **DB**: `UniqueConstraint(invoice_number, workshop_id)` en `invoices` impide insertar la misma factura dos veces.
2. **Backend**: tanto `agent.audit_invoice` (reglas) como `_save_ai_result` (Gemini) hacen **upsert** — si ya existe un `AuditResult` para el invoice, lo actualizan en vez de crear uno nuevo, y borran los hallazgos antiguos antes de insertar los nuevos.
3. **Frontend**: flag `uploadInFlight` en `upload.js` bloquea cargas concurrentes; el componente de drag-drop solo dispara el upload una vez por archivo.

El campo `audit_engine` en cada `AuditResult` siempre refleja el último motor empleado. Si auditas con reglas y luego con IA, verás un único registro con `audit_engine="gemini"` y los hallazgos de Gemini (los de reglas se reemplazaron). Si vuelves a auditar con reglas, se sobrescribe nuevamente. Sin duplicación, sin estado intermedio.
