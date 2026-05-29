# Documentación de Funciones — Miraclex

Este documento resume las funciones reales implementadas en la aplicación.

## 1. Panel de Auditoría (Dashboard)

- Muestra el flujo verificable para jurado.
- Resume propósito, monto estimado a cubrir y control activo.
- Enlaza hacia Carga, Siniestros y Auditorías.
- Explica la ruta manual y automática de la demo.
- Serie temporal de siniestros por día (`GET /api/dashboard/claims-by-day`).

Endpoints:

- `GET /api/dashboard`
- `GET /api/dashboard/claims-by-day`

## 2. Carga y Generación de Documentos

Pantalla: `Carga`.

Funciones:

- Generar expediente manual completo: declaración, parte policial y factura.
- Generar solo declaración.
- Generar solo parte policial.
- Generar solo factura.
- Generar expediente automático con IA.
- Descargar PDFs generados.
- Cargar PDFs con drag and drop.
- Resolver automáticamente el siniestro desde referencias `SIN-...`.

Endpoints:

- `POST /api/demo/documents`
- `POST /api/demo/complete-case`
- `POST /api/claims/auto/declaration`
- `POST /api/claims/auto/police-report`
- `POST /api/audit-pdf`

## 3. Gestión de Siniestros

Pantalla: `Siniestros`.

Funciones:

- Listar siniestros.
- Filtrar por tipo, estado y búsqueda.
- Agrupar por asegurado.
- Expandir filas para revisar facturas asociadas.
- Consultar riesgo con DeepSeek V4 Flash según permisos.
- Abrir workspace del expediente.
- Importar siniestros desde CSV.

Endpoints principales:

- `GET /api/claims`
- `POST /api/claims`
- `POST /api/claims/import-csv`

## 4. Workspace del Siniestro

Vista centralizada del expediente.

Pantalla: `claimWorkspace.js`.

Pestañas principales:

- Resumen.
- Expediente.
- Timeline.
- Fraude/riesgo.
- Documentos.
- Póliza, cliente y vehículo.

Endpoints relacionados:

- `GET /api/claims/{id}/timeline`
- `GET /api/claims/{id}/declaration`
- `GET /api/claims/{id}/police-report`
- `GET /api/claims/{id}/police-requirement`
- `GET /api/claims/{id}/invoices`
- `GET /api/claims/{id}/executive-summary`
- `GET /api/siniestros/{id}/fraud-score`

## 5. Auditorías

Pantalla: `Auditorías`.

Funciones:

- Ver facturas pendientes.
- Ejecutar auditoría con DeepSeek V4 Flash.
- Ejecutar auditoría masiva IA (concurrente).
- Ejecutar reglas manualmente cuando aplique.
- Ver auditorías revisadas.
- Re-auditar desde el detalle.

Endpoints:

- `GET /api/invoices/pending`
- `POST /api/audit-ai/{invoice_id}`
- `POST /api/audit-ai-all`
- `POST /api/audit-deepseek-batch`
- `POST /api/audit/{invoice_id}`
- `POST /api/audit-rules/{invoice_id}`
- `POST /api/audit-all`
- `GET /api/audit-results`
- `GET /api/audit-results/{id}`

## 6. Flujo de Decisión Humana

Desde el detalle de auditoría, según el rol del perfil:

| Acción | Rol requerido | Precondición |
|---|---|---|
| Aprobar | Costos / Contabilidad | Siniestro no escalado |
| Aprobar (final) | Jefatura | Siniestro previamente escalado |
| Escalar | Costos / Contabilidad | — |
| Rechazar | Jefatura | Siniestro previamente escalado |
| Derivar a Legal | Jefatura | Siniestro en estado escalado |

Endpoints:

- `POST /api/audit-results/{id}/approve`
- `POST /api/audit-results/{id}/reject`
- `POST /api/audit-results/{id}/escalate`
- `POST /api/audit-results/{id}/send-to-legal`
- `GET /api/legal/notifications`

## 7. Motor IA DeepSeek V4 Flash

Archivo principal: `backend/deepseek_auditor.py`.

Uso:

- Auditoría cognitiva de facturas.
- Explicación de hallazgos.
- Evaluación de inconsistencias y sobrecobros.
- Revisión con evidencia del input.
- Detección cruzada con historial de facturas.

Configuración recomendada:

```env
OPENCODE_GO_API_KEY=tu_api_key
OPENCODE_GO_API_BASE=https://opencode.ai/zen/go/v1
OPENCODE_GO_MODEL=deepseek-v4-flash
```

Si la IA falla en endpoints críticos de demo, el sistema usa reglas locales como fallback.

## 8. Motor de Reglas

Archivo principal: `backend/rules_engine.py`.

Uso:

- Fallback técnico si DeepSeek/API no responde.
- Auditoría manual cuando el usuario lo solicita.
- Validación determinística de sobrecobros, duplicados, cantidades e incoherencias.

## 9. Chatbot Inteligente

Archivo principal: `backend/chatbot_agent.py`.
Componente frontend: `frontend/js/components/chatbotBubble.js`.

Funciones:

- Burbuja flotante en esquina inferior derecha.
- Preguntas en lenguaje natural sobre datos del sistema.
- Inferencia SQL automática + reescritura con DeepSeek V4 Flash.
- Restricciones por perfil/rol.
- Preguntas guiadas + pregunta libre.

Endpoint: `POST /api/agent/query`.

## 10. Inteligencia Operativa

Endpoints:

- `GET /api/intelligence/fraud`
- `GET /api/intelligence/portfolio`
- `GET /api/intelligence/operations`
- `GET /api/intelligence/audit-coverage`
- `GET /api/intelligence/claim/{claim_id}`
- `POST /api/intelligence/deepseek-insight`

Funciones:

- Métricas antifraude.
- Métricas de cartera.
- Métricas operativas.
- Cobertura de auditoría.
- Insight por siniestro.
- Insight generado por DeepSeek V4 Flash bajo demanda (7 tipos disponibles).

## 11. Scoring de Fraude

Archivo principal: `backend/fraud_scoring.py`.

Funciones:

- 14 señales de fraude (S01–S14) con pesos definidos por rúbrica.
- 7 reglas de negocio críticas (RF01–RF07).
- Score normalizado 0–100 con semáforo Verde/Amarillo/Rojo.
- Ranking por score descendente.
- Recalculación masiva.

Endpoints:

- `GET /api/siniestros/{id}/fraud-score`
- `POST /api/siniestros/score-all`
- `GET /api/siniestros/ranking`
- `GET /api/fraud-dashboard`

## 12. Reportes PDF

Funciones:

- Reporte interno para auditoría.
- Notificación al taller.
- Vista previa desde detalle de auditoría.

Endpoint:

- `GET /api/audit-results/{audit_id}/report-preview`

## 13. Perfiles y Seguridad

Funciones:

- Perfiles con permisos por rol.
- Tokens HMAC-SHA256 por perfil.
- Contraseñas con hash y salt.
- Modo administrador para testing.
- Clave maestra configurable (`ADMIN_PASSWORD`).
- Auditoría de acciones administrativas.

Endpoints principales:

- `GET /api/profiles`
- `POST /api/profiles`
- `POST /api/profiles/{profile_id}/token`
- `POST /api/profiles/admin-login`
- `PUT /api/profiles/{profile_id}`
- `PUT /api/profiles/{profile_id}/password`
- `DELETE /api/profiles/{profile_id}`

## 14. Panel de Administración

Funciones:

- Log de auditoría de todas las acciones del sistema.
- Filtrado por acción y perfil.
- Estadísticas agregadas.
- Solo accesible para el perfil administrador.

Endpoints:

- `GET /api/admin/audit-log`
- `GET /api/admin/audit-log/stats`

## 15. Tarifario

Pantalla: `Tarifario`.

Funciones:

- CRUD de entradas del tarifario maestro.
- Importación masiva desde CSV.
- Tolerancia porcentual configurable por repuesto.

Endpoints:

- `GET /api/tariffs`
- `POST /api/tariffs`
- `PUT /api/tariffs/{id}`
- `DELETE /api/tariffs/{id}`
- `POST /api/tariffs/import-csv`

## 16. Garantías de Demo

- No depende de rutas locales externas.
- Los PDFs demo se generan en `backend/test_pdfs`.
- El flujo manual y automático están disponibles desde la UI.
- La IA (DeepSeek V4 Flash) es el motor principal.
- Las reglas no reemplazan a DeepSeek salvo fallback o acción manual.
- La decisión final siempre es humana.
- Todas las acciones se registran en el log de auditoría.
