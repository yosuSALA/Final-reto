# Stack Tecnologico — Aseguradora del Sur

**Proyecto:** Auditor Tecnico y Detector de Riesgo Agentico
**Equipo:** Miraclex — HackIAthon 2026
**Version:** 2.0.0

---

## Resumen ejecutivo

Sistema de auditoría agéntica para aseguradoras que usa DeepSeek V4 Flash como motor principal y reglas determinísticas como fallback/manual. La arquitectura es compacta: un solo proceso Python sirve API REST, frontend estático y PDFs de demo.

---

## 1. Backend

| Capa | Tecnologia | Version | Rol |
|------|-----------|---------|-----|
| Framework web | **FastAPI** | >= 0.111 | API REST asincrona, Swagger UI automatico en `/docs` |
| Servidor ASGI | **Uvicorn** | >= 0.29 (`[standard]`) | Servidor de produccion con WebSockets |
| ORM | **SQLAlchemy** | >= 2.0 | Modelos relacionales, sesiones, migraciones inline |
| Base de datos | **SQLite 3** | (bundled Python) | Archivo `auditor.db`; FK pragma activado |
| Validacion | **Pydantic** | v2 | Schemas de request/response |
| Extraccion PDF | **pdfplumber** | >= 0.11 | Extrae texto y tablas de facturas SRI Ecuador |
| Generacion PDF | **reportlab** | >= 4.2 | PDFs internos y notificaciones al taller |
| Multipart | **python-multipart** | >= 0.0.9 | Soporte `UploadFile` en FastAPI |
| Variables entorno | **python-dotenv** | >= 1.0 | Carga `.env` en desarrollo |
| Hot-reload | **watchdog** | >= 4.0 | Reloader de archivos en desarrollo |
| NLP similitud | **difflib (stdlib)** | -- | `SequenceMatcher` para senial S13 |
| Seguridad tokens | **hmac + secrets (stdlib)** | -- | HMAC-SHA256 para tokens de perfil |

### Modulos del backend

```
backend/
├── main.py                -- App FastAPI, 65+ endpoints REST
├── models.py              -- SQLAlchemy ORM (13+ tablas + enums)
├── database.py            -- Engine SQLite, SessionLocal, init_db
├── fraud_scoring.py       -- scoring de riesgo de siniestros (14 señales + 7 RF)
├── rules_engine.py        -- reglas locales de auditoría de facturas
├── agent.py               -- AuditAgent: pipeline de reglas/fallback
├── deepseek_auditor.py    -- DeepSeekAuditor: CoT, few-shot, self-reflection
├── chatbot_agent.py       -- Chatbot: inferencia SQL + reescritura DeepSeek V4 Flash
├── pdf_extractor.py       -- Extraccion de facturas PDF
├── declaration_extractor.py -- Extraccion de declaraciones PDF
├── police_report_extractor.py -- Extraccion de partes policiales PDF
├── police_report_policy.py -- Politicas de partes policiales
├── pdf_generator.py       -- Generacion de reportes PDF
├── auth.py                -- Tokens HMAC + contraseñas con hash/salt
├── seed_data.py           -- Datos demo
├── seed_fraud_data.py     -- Datos demo con patrones de fraude plantados
├── profile_scope.py       -- ProfileScope: aislamiento por perfil
└── test_invoice_generator.py -- Generador de facturas SRI de prueba
```

---

## 2. Inteligencia Artificial

| Modelo / Tecnica | Proveedor | Uso |
|-----------------|-----------|-----|
| **DeepSeek V4 Flash** (`deepseek-v4-flash`) | OpenCode Go Gateway | Auditoria cognitiva de facturas: CoT, few-shot, self-reflection, validacion semantica + retry |
| **DeepSeek V4 Flash** (`deepseek-v4-flash`) | OpenCode Go Gateway | Chatbot inteligente: inferencia SQL + reescritura en lenguaje natural |
| **DeepSeek V4 Flash** (`deepseek-v4-flash`) | OpenCode Go Gateway | Insights de inteligencia operativa bajo demanda |
| **DeepSeek Chat** (`deepseek-chat`) | DeepSeek API (fallback directo) | Alternativa si no se usa OpenCode Go |
| **Reglas locales** | Backend propio | Fallback técnico si DeepSeek/API falla o auditoría manual |
| **SequenceMatcher** | Python stdlib (`difflib`) | Similitud local de narrativas |

### Patrones de prompting implementados

- **Chain-of-Thought forzado**: schema JSON obliga a `cadena_de_razonamiento` antes del veredicto.
- **Few-shot calibration**: 2 ejemplos en system prompt (factura limpia + factura con fraude).
- **Self-reflection pass**: segunda llamada como revisor esceptico.
- **Validacion semantica + retry**: si la respuesta viola reglas, se reenvia con feedback.
- **Confianza calibrada 0.0-1.0**: hallazgos CRITICAL requieren confianza >= 0.7.
- **Prompts adaptativos por rol**: el sistema ajusta el prompt según el rol del usuario para insights.

### Modalidades de uso de IA

| Modalidad | Endpoint | Descripcion |
|-----------|----------|-------------|
| Auditoría individual | `POST /api/audit-ai/{invoice_id}` | Una factura con DeepSeek V4 Flash |
| Auditoría masiva | `POST /api/audit-ai-all` | Todas las facturas, concurrencia configurable |
| Auditoría batch | `POST /api/audit-deepseek-batch` | Batch optimizado |
| Chatbot | `POST /api/agent/query` | Pregunta libre con inferencia SQL |
| Insight operativo | `POST /api/intelligence/deepseek-insight` | 7 tipos de análisis bajo demanda |

---

## 3. Frontend

| Tecnologia | Rol |
|-----------|-----|
| **HTML5** | Estructura SPA (`index.html`), landing page |
| **JavaScript ES Modules (Vanilla)** | Logica de cliente sin bundler ni framework |
| **CSS3 Custom Properties** | Temas claro/oscuro, glassmorphism, micro-animaciones |
| **Google Fonts CDN** | Tipografias Inter (UI) + JetBrains Mono (codigo) |

### Arquitectura SPA

```
frontend/
├── index.html              -- Shell: nav, #main-content, widgets flotantes
├── style.css               -- Diseno completo (dark/light theme, responsive)
└── js/
    ├── main.js             -- Entry point; expone globals
    ├── router.js           -- SPA hash-router
    ├── state.js            -- Estado global
    ├── api.js              -- Capa HTTP con X-Profile-Token
    ├── auth.js             -- Selector de perfil, login, tokens
    ├── utils.js            -- Utilidades compartidas
    ├── components/
    │   ├── auditQueue.js   -- Cola de auditoria colapsable
    │   ├── chatbotBubble.js-- Burbuja de chat flotante (DeepSeek V4 Flash)
    │   ├── charts.js       -- Graficos (scatter, donut)
    │   └── csvUpload.js    -- Componente de importación CSV
    └── pages/
        ├── dashboard.js    -- KPIs, semaforo, inteligencia
        ├── auditorias.js   -- Pendientes / Revisadas
        ├── tarifario.js    -- CRUD tarifario + import CSV
        ├── siniestros.js   -- Vista expandible + workspace
        ├── upload.js       -- Drag-drop PDF + generador SRI
        ├── auditDetail.js  -- Detalle de auditoria + decisiones
        ├── pendingDetail.js-- Detalle de factura pendiente
        ├── claimWorkspace.js-- Workspace centralizado del siniestro
        └── adminAuditLog.js-- Panel de log de auditoría (admin)
```

---

## 4. Proxy y despliegue

| Herramienta | Uso |
|------------|-----|
| **Node.js + Express** | Proxy de desarrollo: `/api` -> FastAPI `:8000` |
| **http-proxy-middleware** | Middleware de proxy |
| **Docker + Compose** | Imagen `python:3.11-slim` |
| **Render.com** | Plataforma de deployment (`render.yaml`) |

### Scripts de inicio

| Comando | Plataforma | Descripcion |
|---------|-----------|-------------|
| `start.bat` | Windows | Instala deps + lanza uvicorn |
| `bash start.sh` | Mac/Linux | Idem |
| `npm start` | Cualquiera | Launcher portable vía Node |
| `npm run dev` | Cualquiera | Igual que `npm start` |
| `docker-compose up` | Cualquiera | Contenedor |

---

## 5. Seguridad

| Mecanismo | Implementacion |
|-----------|---------------|
| **Autenticacion con contrasena** | Hash + salt para cada perfil |
| **Tokens de sesion** | HMAC-SHA256(`profile_id`, `token_secret`) |
| **Header de sesion** | `X-Profile-Token: {profile_id}:{firma}` |
| **Anti-timing attack** | `hmac.compare_digest()` |
| **Aislamiento de datos** | `ProfileScope`: toda query lleva `WHERE profile_id = ?` |
| **IDs no adivinables** | UUIDs v4 para `profile_id` |
| **FK en 7 tablas** | Integridad referencial por `profile_id` |
| **Clave maestra** | Perfil admin con password configurable (`ADMIN_PASSWORD`) |
| **Log de auditoría** | Middleware registra todas las escrituras en `audit_log` |

---

## 6. Modelo de datos (tablas principales)

| Tabla | Registros demo | Descripcion |
|-------|---------------|-------------|
| `profiles` | ~5 | Perfiles de usuario con token_secret y password_hash |
| `siniestros` | Variable | Reclamos con trazabilidad y fraud_score |
| `polizas` | Variable | Contratos con vigencia y suma asegurada |
| `asegurados_sinteticos` | Variable | Titulares de pólizas |
| `vehiculos` | Variable | Vehículos asegurados |
| `documentos` | Variable | Evidencias por siniestro |
| `accident_declarations` | Variable | Declaraciones de accidente |
| `police_reports` | Variable | Partes policiales |
| `workshops` | 3 | Talleres mecanicos |
| `invoices` | Variable | Facturas |
| `invoice_items` | Variable | Lineas de factura |
| `tariff_items` | 25 | Tarifario maestro con tolerancia % |
| `audit_results` | Variable | Resultados de auditoria (upsert) |
| `audit_findings` | Variable | Hallazgos individuales |
| `audit_log` | Variable | Log de acciones del sistema |

---

## 7. Variables de entorno

| Variable | Obligatoria | Descripcion |
|----------|------------|-------------|
| `OPENCODE_GO_API_KEY` | No | Habilita DeepSeek V4 Flash via OpenCode Go |
| `OPENCODE_GO_API_BASE` | No | Gateway URL (default: `https://opencode.ai/zen/go/v1`) |
| `OPENCODE_GO_MODEL` | No | Modelo (default: `deepseek-v4-flash`) |
| `DEEPSEEK_API_KEY` | No | Fallback directo a DeepSeek |
| `DEEPSEEK_API_BASE` | No | API base DeepSeek (default: `https://api.deepseek.com`) |
| `DEEPSEEK_MODEL` | No | Modelo fallback (default: `deepseek-chat`) |
| `DATABASE_PATH` | No | Ruta SQLite (default: `auditor.db`) |
| `ADMIN_PASSWORD` | No | Clave maestra del perfil admin (default: `admin`) |
| `AI_AUDIT_CONCURRENCY` | No | Workers concurrentes para auditoría masiva (default: `4`, max: `8`) |

---

## 8. Flujo de datos

```
PDF factura
    |
    v
pdf_extractor.py (pdfplumber + regex)
    |  items[], ruc, invoice_number, fecha
    v
Invoice + InvoiceItems
    |
    v
Motor principal / fallback
    |
    +-- rules_engine.py (fallback/manual) -> findings[]
    |
    +-- deepseek_auditor.py (CoT + few-shot + self-reflection) -> findings[]
    |
    v
agent.py
    |  calculate_risk_score() -> 0-100
    |  _generate_summary()
    |  _save_result() [upsert]
    v
AuditResult + AuditFindings
    |
    +-> GET /api/audit-results (dashboard)
    +-> GET /api/audit-results/{id} (detalle)
    +-> pdf_generator.py -> Reporte Interno PDF
    +-> pdf_generator.py -> Notificacion Taller PDF
    +-> Decisión humana (approve/reject/escalate/send-to-legal)
    +-> GET /api/legal/notifications (siniestros derivados)
```
