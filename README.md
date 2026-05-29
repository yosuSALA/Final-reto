# Miraclex — Auditor Agéntico de Siniestros | HackIAthon 2026

Miraclex es una plataforma web para gestionar expedientes de siniestros, generar documentación sintética para demo, cargar PDFs, extraer datos, auditar facturas y priorizar posibles riesgos antes del pago. La demo final funciona de forma portable: un solo comando levanta FastAPI, SQLite y el frontend SPA.

La IA principal es **DeepSeek V4 Flash vía OpenCode Go**. El motor de reglas queda disponible como respaldo técnico si la API no responde o como opción manual de auditoría.

## Estado Final

- App lista en `http://localhost:8000/app/`.
- Arranque portable con `start.bat`, `start.sh` o `npm start`.
- Generador demo manual: declaración, parte policial y factura descargables.
- Generador demo automático: expediente completo con auditoría IA.
- Carga de documentos sin selector obligatorio: si el PDF trae referencia `SIN-...`, el sistema detecta o crea el siniestro.
- Auditoría DeepSeek V4 Flash como acción principal; reglas solo como fallback/manual.
- Chatbot inteligente con restricciones por perfil.
- Plataforma de inteligencia operativa con insights DeepSeek.
- Flujo de decisión humana por roles: aprobar, rechazar, escalar y derivar a Legal.
- Workspace centralizado por siniestro con timeline y expediente completo.
- Panel de administración con log de auditoría de acciones.
- Datos sintéticos: no se usan datos personales reales.

## Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy.
- **Base de datos**: SQLite (`backend/auditor.db`).
- **Frontend**: HTML, CSS y JavaScript modular sin build.
- **PDFs**: `pdfplumber` para extracción y `reportlab` para generación.
- **IA**: DeepSeek V4 Flash vía OpenCode Go, con fallback directo opcional a DeepSeek API.

## Instalación y Arranque

### Windows

```bat
start.bat
```

### macOS/Linux

```bash
./start.sh
```

### Con Node/npm

```bash
npm start
```

El launcher crea `.venv`, instala `backend/requirements.txt` y levanta Uvicorn en `127.0.0.1:8000`. Si el puerto ya tiene una instancia válida de la app, lo informa y no falla.

URLs útiles:

- Landing: `http://localhost:8000/`
- App: `http://localhost:8000/app/`
- Swagger/API: `http://localhost:8000/docs`

## Variables de Entorno

Copia `.env.example` a `.env` si vas a usar IA real:

```env
OPENCODE_GO_API_KEY=tu_api_key
OPENCODE_GO_API_BASE=https://opencode.ai/zen/go/v1
OPENCODE_GO_MODEL=deepseek-v4-flash

DEEPSEEK_API_KEY=
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

Prioridad de IA:

1. `OPENCODE_GO_API_KEY` con `OPENCODE_GO_MODEL=deepseek-v4-flash`.
2. `DEEPSEEK_API_KEY` como fallback directo.
3. Motor de reglas local si la IA no está disponible o si el usuario lo ejecuta manualmente.

## Flujo Demo Recomendado

### Opción A: Expediente Automático con IA

1. Abrir `http://localhost:8000/app/`.
2. Entrar con perfil `Demo / Jurado` o un perfil con permisos de operación/auditoría.
3. Ir a `Carga`.
4. En `Generador de documentos demo`, elegir `Expediente automático con IA`.
5. Elegir nivel de riesgo de factura: `Aleatorio`, `Limpio`, `Sobrecobro` o `Fraude`.
6. Pulsar `Generar`.
7. El sistema crea siniestro, declaración, parte policial, factura y auditoría. Al terminar abre el detalle de auditoría.

### Opción B: Flujo Manual Paso a Paso

1. Ir a `Carga`.
2. En `Qué generar`, elegir `Expediente manual completo (3 PDFs)`.
3. Pulsar `Generar` y descargar los PDFs.
4. Cargar primero la `Declaración`, luego el `Parte Policial`, luego la `Factura`.
5. Dejar `Siniestro destino` en `Detectar automáticamente desde el PDF` si los PDFs traen referencia `SIN-...`.
6. Revisar la cola de auditorías y ejecutar la auditoría IA desde la vista de pendientes.

Si el PDF no trae referencia de siniestro y no se puede resolver automáticamente, la app pedirá selección manual.

## Flujo Operativo del Expediente

| Etapa | Acción | Endpoint principal |
|---|---|---|
| 1 | Crear o resolver siniestro | `POST /api/claims` o resolución automática |
| 2 | Cargar declaración | `POST /api/claims/auto/declaration` o `POST /api/claims/{id}/declaration` |
| 3 | Cargar parte policial | `POST /api/claims/auto/police-report` o `POST /api/claims/{id}/police-report` |
| 4 | Cargar factura | `POST /api/audit-pdf` |
| 5 | Auditar con IA | `POST /api/audit-ai/{invoice_id}` (DeepSeek V4 Flash) |
| 5b | Auditar con reglas (fallback/manual) | `POST /api/audit-rules/{invoice_id}` |
| 5c | Auditoría masiva IA | `POST /api/audit-ai-all` o `POST /api/audit-deepseek-batch` |
| 6 | Decisión humana | Ver sección "Flujo de Decisión Humana" |

El parte policial es condicional, pero en la demo completa se genera para dejar el expediente totalmente verificable.

## Flujo de Decisión Humana

El sistema implementa un flujo de decisión por roles con las siguientes transiciones:

| Acción | Endpoint | Quién puede | Precondición |
|---|---|---|---|
| Aprobar | `POST /api/audit-results/{id}/approve` | Costos / Contabilidad | Siniestro no escalado |
| Aprobar (final) | `POST /api/audit-results/{id}/approve` | Jefatura | Siniestro escalado |
| Escalar | `POST /api/audit-results/{id}/escalate` | Costos / Contabilidad | — |
| Rechazar | `POST /api/audit-results/{id}/reject` | Jefatura | Siniestro previamente escalado |
| Derivar a Legal | `POST /api/audit-results/{id}/send-to-legal` | Jefatura | Siniestro en estado escalado |

Legal puede consultar los siniestros derivados en `GET /api/legal/notifications`.

## Chatbot Inteligente

Burbuja flotante en la esquina inferior derecha de la app.

- Endpoint: `POST /api/agent/query`.
- Inferencia SQL + reescritura con DeepSeek V4 Flash.
- Restricciones por perfil: cada rol recibe respuestas limitadas a su ámbito.
- Preguntas guiadas + pregunta libre.

## Plataforma de Inteligencia

Endpoints de inteligencia operativa accesibles desde el dashboard:

| Endpoint | Descripción |
|---|---|
| `GET /api/intelligence/fraud` | Métricas antifraude |
| `GET /api/intelligence/portfolio` | Métricas de cartera |
| `GET /api/intelligence/operations` | Métricas operativas |
| `GET /api/intelligence/audit-coverage` | Cobertura de auditoría |
| `GET /api/intelligence/claim/{claim_id}` | Insight por siniestro |
| `POST /api/intelligence/deepseek-insight` | Insight generado por DeepSeek V4 Flash bajo demanda |

## Endpoints Clave

### Demo y Generación

- `POST /api/demo/documents`: genera PDFs demo descargables para carga manual.
- `POST /api/demo/complete-case`: genera expediente completo y audita con IA.

### Expediente

- `POST /api/claims`: crea siniestro.
- `POST /api/claims/import-csv`: importa siniestros desde CSV.
- `POST /api/claims/auto/declaration`: carga declaración detectando/creando siniestro desde el PDF.
- `POST /api/claims/auto/police-report`: carga parte policial detectando siniestro desde el PDF.
- `GET /api/claims`: lista siniestros.
- `GET /api/claims/{id}/executive-summary`: resumen ejecutivo del siniestro.
- `GET /api/claims/{id}/timeline`: timeline del expediente.
- `GET /api/claims/{id}/declaration`: declaración del siniestro.
- `GET /api/claims/{id}/police-report`: parte policial.
- `GET /api/claims/{id}/police-requirement`: requisito de parte policial.
- `GET /api/claims/{id}/invoices`: facturas del siniestro.

### Auditoría

- `POST /api/audit-pdf`: carga factura y la deja en cola de auditoría.
- `POST /api/audit-ai/{invoice_id}`: auditoría individual con DeepSeek V4 Flash.
- `POST /api/audit-ai-all`: auditoría masiva con DeepSeek V4 Flash (concurrente).
- `POST /api/audit-deepseek-batch`: auditoría batch con DeepSeek V4 Flash.
- `POST /api/audit/{invoice_id}`: auditoría con agente (motor principal + fallback).
- `POST /api/audit-rules/{invoice_id}`: auditoría solo con reglas locales.
- `POST /api/audit-all`: auditoría masiva con agente.
- `GET /api/audit-results`: lista auditorías.
- `GET /api/audit-results/{id}`: detalle de auditoría.
- `GET /api/audit-results/{id}/report-preview`: reporte PDF.
- `GET /api/invoices/pending`: facturas pendientes de auditoría.
- `GET /api/dashboard`: KPIs principales.
- `GET /api/dashboard/claims-by-day`: serie temporal de siniestros por día.

### Tarifario

- `GET /api/tariffs`: listar tarifario.
- `POST /api/tariffs`: crear entrada.
- `PUT /api/tariffs/{id}`: actualizar entrada.
- `DELETE /api/tariffs/{id}`: eliminar entrada.
- `POST /api/tariffs/import-csv`: importar tarifario desde CSV.

### Perfiles y Seguridad

- `GET /api/profiles`: listar perfiles.
- `POST /api/profiles`: crear perfil con contraseña.
- `POST /api/profiles/{id}/token`: login con contraseña.
- `POST /api/profiles/admin-login`: login de administrador con clave maestra.
- `PUT /api/profiles/{id}`: actualizar perfil.
- `PUT /api/profiles/{id}/password`: cambiar contraseña.
- `DELETE /api/profiles/{id}`: eliminar perfil (soft delete).
- `GET /api/admin/audit-log`: log de auditoría de acciones.
- `GET /api/admin/audit-log/stats`: estadísticas del log.

## Documentación

- Manual de uso: `docs/MANUAL_USO.md`
- Funciones del sistema: `docs/DOC_FUNCIONES.md`
- Arquitectura: `docs/arquitectura.md`
- Uso de IA: `docs/uso_ia.md`
- Modelo de datos: `docs/modelo_datos.md`
- Reglas de negocio: `docs/reglas_negocio.md`
- Perfiles: `docs/PERFILES_ACCESO.md`
- Matriz de cumplimiento: `docs/MATRIZ_CUMPLIMIENTO_RETO.md`
- Arquitectura de seguridad: `docs/arquitectura_seguridad.md`
- Stack tecnológico: `docs/stack.md`

## Verificación Técnica

Comandos usados para validar cambios críticos:

```bash
python -m py_compile backend/main.py
python -m py_compile backend/test_invoice_generator.py
node --check frontend/js/pages/upload.js
node --check frontend/js/pages/dashboard.js
node --check frontend/js/pages/siniestros.js
node --check frontend/js/pages/pendingDetail.js
node --check frontend/js/pages/auditDetail.js
node --check frontend/js/main.js
```

## Seguridad y Ética

- Todos los datos de demo son sintéticos.
- La plataforma produce alertas de posible riesgo, no acusaciones.
- La decisión final sigue siendo humana.
- Flujo de aprobación por roles con trazabilidad.
- Autenticación HMAC-SHA256 con aislamiento por perfil.
- Log de auditoría de acciones administrativas.
- `.env` no debe subirse al repositorio.

## Equipo

Miraclex — HackIAthon 2026  
Josué Salazar · Andrés Abad · Andrés Falconí
