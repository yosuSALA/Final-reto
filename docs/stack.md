# Stack Tecnológico — Aseguradora del Sur

**Proyecto:** Auditor Técnico y Detector de Riesgo Agéntico  
**Equipo:** Miraclex — HackIAthon 2026  
**Versión:** 2.0.0

---

## Resumen ejecutivo

Sistema de auditoría agéntica para aseguradoras que combina un motor de reglas determinístico con IA generativa (Deepseek) para detectar fraude en siniestros y facturas de talleres mecánicos. La arquitectura es intencional­mente compacta: un solo proceso Python sirve tanto la API REST como los archivos estáticos del frontend.

---

## 1. Backend

| Capa | Tecnología | Versión | Rol |
|------|-----------|---------|-----|
| Framework web | **FastAPI** | ≥ 0.111 | API REST asíncrona, Swagger UI automático en `/docs` |
| Servidor ASGI | **Uvicorn** | ≥ 0.29 (`[standard]`) | Servidor de producción con WebSockets y HTTP/1.1 |
| ORM | **SQLAlchemy** | ≥ 2.0 | Modelos relacionales, sesiones, migraciones inline (`ALTER TABLE`) |
| Base de datos | **SQLite 3** | (bundled Python) | Archivo `auditor.db`; FK pragma activado; ideal para prototipo single-node |
| Validación | **Pydantic** | v2 | Schemas de request/response; validación automática de tipos |
| Extracción PDF | **pdfplumber** | ≥ 0.11 | Extrae texto y tablas de facturas SRI Ecuador |
| Generación PDF | **reportlab** | ≥ 4.2 | PDFs internos (con risk score) y notificaciones al taller |
| Multipart | **python-multipart** | ≥ 0.0.9 | Soporte `UploadFile` en FastAPI |
| Variables entorno | **python-dotenv** | ≥ 1.0 | Carga `.env` en desarrollo |
| Hot-reload | **watchdog** | ≥ 4.0 | Reloader de archivos en desarrollo |
| NLP similitud | **difflib (stdlib)** | — | `SequenceMatcher` para señal S13 (narrativas coincidentes ≥ 75 %) |
| Seguridad tokens | **hmac + secrets (stdlib)** | — | HMAC-SHA256 para tokens de perfil; `compare_digest` anti-timing |

### Módulos del backend

```
backend/
├── main.py           — App FastAPI, 50+ endpoints REST, middleware CORS/no-cache
├── models.py         — SQLAlchemy ORM (13 tablas + enums)
├── database.py       — Engine SQLite, SessionLocal, init_db, migración liviana
├── fraud_scoring.py  — Motor de scoring: 14 señales + 7 reglas (score 0-100)
├── rules_engine.py   — 5 reglas de auditoría de facturas (PriceOvercharge, Duplicate…)
├── agent.py          — AuditAgent: orquesta pipeline reglas → score → AuditResult
├── deepseek_auditor.py — GeminiAuditor: CoT, few-shot, self-reflection, retry
├── chatbot_agent.py  — Chatbot: inferencia SQL + reescritura LLM (DeepSeek / Gemini)
├── pdf_extractor.py  — Extracción de facturas PDF con regex + pdfplumber
├── pdf_generator.py  — Generación de reportes PDF con reportlab
├── auth.py           — Generación y verificación de tokens HMAC por perfil
├── seed_data.py       — Datos demo: talleres, tarifario (25 ítems), 60+ siniestros
└── profile_scope.py  — ProfileScope: wrapper SQLAlchemy para aislamiento por perfil
```

---

## 2. Inteligencia Artificial

| Modelo / Técnica | Proveedor | Uso |
|-----------------|-----------|-----|
| **Deepseek V4 Flash** | Auditoría cognitiva de facturas: Chain-of-Thought, few-shot calibration, self-reflection pass, validación semántica + retry |
| **DeepSeek Chat** (`deepseek-chat`) | DeepSeek API (REST directo) | Chatbot conversacional: reescritura elocuente de datos SQL |
| **Deepseek V4 Flash** (fallback) | Google AI | Chatbot cuando no hay clave DeepSeek |
| **Formateador local** | Ninguno | Fallback técnico si no hay ninguna API key; formatea datos SQL en Markdown |
| **SequenceMatcher** | Python stdlib (`difflib`) | Señal S13: similitud de narrativas ≥ 75 % → alerta de clonación |

### Patrones de prompting implementados

- **Chain-of-Thought forzado**: el schema JSON obliga al campo `cadena_de_razonamiento` antes del veredicto.
- **Few-shot calibration**: 2 ejemplos en el system prompt (factura limpia + factura con fraude).
- **Self-reflection pass**: segunda llamada actúa como revisor escéptico de la primera respuesta.
- **Validación semántica + retry**: si la respuesta viola reglas de consistencia se reenvía con feedback explícito.
- **Confianza calibrada 0.0–1.0**: hallazgos CRITICAL requieren confianza ≥ 0.7.

---

## 3. Frontend

| Tecnología | Rol |
|-----------|-----|
| **HTML5** | Estructura SPA (`index.html`), landing page |
| **JavaScript ES Modules (Vanilla)** | Lógica de cliente sin bundler ni framework |
| **CSS3 Custom Properties** | Temas claro/oscuro, glassmorphism, micro-animaciones |
| **Google Fonts CDN** | Tipografías Inter (UI) + JetBrains Mono (código) |

### Arquitectura SPA

```
frontend/
├── index.html            — Shell: nav, #main-content, toast, widgets flotantes
├── landing.html          — Página de entrada pública
├── style.css             — Diseño completo (dark/light theme, responsive)
└── js/
    ├── main.js           — Entry point; expone globals para onclick handlers
    ├── router.js         — SPA hash-router (#dashboard, #auditorias, etc.)
    ├── state.js          — Estado global: perfil activo, resultados, selección
    ├── api.js            — Capa HTTP: GET/POST con inyección de X-Profile-Token
    ├── auth.js           — Selector de perfil, generación/verificación de tokens
    ├── components/
    │   ├── auditQueue.js     — Widget colapsable de cola de auditoría
    │   ├── chatbotBubble.js  — Burbuja flotante de chat con FAQs precargadas
    │   └── charts.js         — Gráficos (scatter, donut)
    └── pages/
        ├── dashboard.js      — KPIs, semáforo, auditoría masiva
        ├── auditorias.js     — Pestañas: Pendientes / Revisadas
        ├── tarifario.js      — CRUD del tarifario maestro
        ├── siniestros.js     — Vista expandible de siniestros + notificaciones
        ├── upload.js         — Drag-drop PDF + generador random SRI Ecuador
        ├── auditDetail.js    — Detalle de auditoría, acciones (Aprobar/Rechazar/Escalar)
        └── pendingDetail.js  — Detalle de factura pendiente (JIT audit)
```

---

## 4. Proxy y despliegue

| Herramienta | Versión | Uso |
|------------|---------|-----|
| **Node.js + Express** | ≥ 18 / ^4.19 | Proxy de desarrollo: `/api` → FastAPI `:8000`, estáticos desde `/public` |
| **http-proxy-middleware** | ^3.0.2 | Middleware de proxy en Express |
| **Docker** | — | Imagen base `python:3.11-slim` + gcc + libffi |
| **Docker Compose** | — | Servicio `app` con volúmenes para `auditor.db` y `.env` |
| **Render.com** | — | Plataforma de deployment (`render.yaml`); runtime Python, start uvicorn |

### Scripts de inicio

| Comando | Plataforma | Descripción |
|---------|-----------|-------------|
| `start.bat` | Windows | Instala deps + lanza uvicorn |
| `bash start.sh` | Mac/Linux | Ídem |
| `npm run dev` | Cualquiera | Express dev proxy en `:8010` |
| `docker-compose up` | Cualquiera | Contenedor con bind de BD y `.env` |

---

## 5. Seguridad

| Mecanismo | Implementación |
|-----------|---------------|
| **Autenticación sin contraseña** | HMAC-SHA256(`profile_id`, `token_secret`) almacenado en `localStorage` |
| **Header de sesión** | `X-Profile-Token: {profile_id}:{firma}` inyectado en cada request |
| **Anti-timing attack** | `hmac.compare_digest()` en la verificación del backend |
| **Aislamiento de datos** | `ProfileScope`: toda query lleva `WHERE profile_id = ?` |
| **IDs no adivinables** | UUIDs v4 para `profile_id` (2¹²² combinaciones) |
| **FK en 7 tablas** | Integridad referencial por `profile_id` en SQLite |

---

## 6. Modelo de datos (tablas principales)

| Tabla | Registros demo | Descripción |
|-------|---------------|-------------|
| `profiles` | 5 | Perfiles de usuario con token_secret |
| `siniestros` | 60+ | Reclamos con 34 campos + fraud_score |
| `polizas` | 60+ | Contratos de seguro con vigencia y suma asegurada |
| `asegurados_sinteticos` | ~20 | Titulares de pólizas |
| `vehiculos` | ~20 | Vehículos asegurados |
| `documentos` | ~120 | Evidencias por siniestro |
| `workshops` | 3 | Talleres mecánicos |
| `invoices` | Variable | Facturas con UniqueConstraint(invoice_number, workshop_id) |
| `invoice_items` | Variable | Líneas de factura |
| `tariff_items` | 25 | Tarifario maestro con tolerancia % |
| `audit_results` | Variable | Resultados de auditoría (upsert, no duplicación) |
| `audit_findings` | Variable | Hallazgos individuales por resultado |

---

## 7. Variables de entorno

| Variable | Obligatoria | Descripción |
|----------|------------|-------------|
| `DEEPSEEK_API_KEY` | No | Habilita el motor IA Deepseek V4 Flash. Sin ella, modo mock. |
| `DEEPSEEK_API_KEY` | No | Chatbot con DeepSeek. Fallback a Gemini o formateador local. |
| `DATABASE_PATH` | No | Ruta del archivo SQLite (default: `auditor.db`) |
| `PORT` | No | Puerto Express proxy (default: `8010`) |
| `HOST` | No | Host Express proxy (default: `127.0.0.1`) |

---

## 8. Flujo de datos de extremo a extremo

```
PDF factura
    │
    ▼
pdf_extractor.py  (pdfplumber + regex)
    │  items[], ruc, invoice_number, fecha
    ▼
Invoice + InvoiceItems  ──────────────────────────────────┐
    │                                                      │
    ▼                                                      │
Motor elegido por el analista                             │
    │                                                      │
    ├─ ⚡ rules_engine.py (PriceOvercharge,               │
    │      Duplicate, Quantity, Incoherence,               │
    │      Resubmission) → findings[]                     │
    │                                                      │
    └─ 🤖 deepseek_auditor.py (CoT + few-shot              │
           + self-reflection) → findings[]                │
    │                                                      │
    ▼                                                      │
agent.py                                                  │
    │  calculate_risk_score() → 0-100                     │
    │  _generate_summary()                                │
    │  _save_result() [upsert]                            │
    ▼                                                      │
AuditResult + AuditFindings ◄────────────────────────────┘
    │
    ├─► GET /api/audit-results  (dashboard)
    ├─► GET /api/audit-results/{id}  (detalle)
    ├─► pdf_generator.py  → Reporte Interno PDF
    └─► pdf_generator.py  → Notificación Taller PDF
```
