# Matriz de Cumplimiento — HackIAthon 2026

Proyecto: Miraclex — Auditor Agéntico de Siniestros  
Fecha de actualización: 29/05/2026  
Estado: listo para demo funcional

## Resumen

| Área | Estado | Evidencia |
|---|---|---|
| Prototipo ejecutable | CUMPLE | `start.bat`, `start.sh`, `scripts/start.py`, `npm start` |
| Frontend funcional | CUMPLE | `frontend/js/pages/*`, SPA servida en `/app/` |
| API REST | CUMPLE | `backend/main.py`, Swagger en `/docs`, 65+ endpoints |
| Base de datos | CUMPLE | SQLite + SQLAlchemy en `backend/models.py` |
| Datos sintéticos | CUMPLE | Generadores demo y seed data sintético |
| Carga de PDFs | CUMPLE | `POST /api/claims/auto/declaration`, `POST /api/claims/auto/police-report`, `POST /api/audit-pdf` |
| Demo manual | CUMPLE | `POST /api/demo/documents` |
| Demo automática con IA | CUMPLE | `POST /api/demo/complete-case` |
| IA principal | CUMPLE | DeepSeek V4 Flash vía OpenCode Go |
| Fallback de reglas | CUMPLE | Motor local si DeepSeek falla o por acción manual |
| Revisión humana | CUMPLE | Acciones approve/reject/escalate/send-to-legal por rol |
| Chatbot inteligente | CUMPLE | `POST /api/agent/query` + burbuja flotante |
| Inteligencia operativa | CUMPLE | 5 endpoints de inteligencia + insight DeepSeek |
| Scoring de fraude | CUMPLE | 14 señales + 7 RF, semáforo, ranking |
| Perfiles y seguridad | CUMPLE | HMAC + contraseñas + aislamiento + log auditoría |
| Ética y privacidad | CUMPLE | Datos sintéticos y lenguaje de posible riesgo |

## Requisitos de Datos

| Requisito | Estado | Evidencia |
|---|---|---|
| Siniestros | CUMPLE | `Siniestro` en `backend/models.py` |
| Pólizas | CUMPLE | `Poliza` en `backend/models.py` |
| Asegurados | CUMPLE | `AseguradoSintetico` en `backend/models.py` |
| Vehículos | CUMPLE | `Vehiculo` en `backend/models.py` |
| Documentos | CUMPLE | `Documento`, `AccidentDeclaration`, `PoliceReport` |
| Facturas e ítems | CUMPLE | `Invoice`, `InvoiceItem` |
| Auditorías y hallazgos | CUMPLE | `AuditResult`, `AuditFinding` |
| Log de auditoría | CUMPLE | `AuditLog` en `backend/models.py` |

## Funcionalidades de Demo

| Funcionalidad | Estado | Cómo verificar |
|---|---|---|
| Generar 3 PDFs manuales | CUMPLE | `Carga` → `Expediente manual completo (3 PDFs)` |
| Descargar PDFs | CUMPLE | Botones `Descargar` en la lista generada |
| Cargar declaración | CUMPLE | `Tipo de documento` → `Declaración` |
| Cargar parte policial | CUMPLE | `Tipo de documento` → `Parte Policial` |
| Cargar factura | CUMPLE | `Tipo de documento` → `Factura` |
| Resolver siniestro desde PDF | CUMPLE | Dejar selector en automático con PDFs `SIN-...` |
| Crear expediente automático | CUMPLE | `Qué generar` → `Expediente automático con IA` |
| Auditar con DeepSeek V4 Flash | CUMPLE | Acción principal en auditorías |
| Auditoría masiva IA | CUMPLE | `POST /api/audit-ai-all` con concurrencia |
| Fallback de reglas | CUMPLE | Se activa si DeepSeek/API falla |
| Reportes PDF | CUMPLE | Detalle de auditoría → reportes |
| Decisión humana por roles | CUMPLE | Aprobar/Rechazar/Escalar/Derivar a Legal |
| Chatbot inteligente | CUMPLE | Burbuja flotante → pregunta libre |
| Workspace siniestro | CUMPLE | Vista centralizada con timeline |
| Inteligencia operativa | CUMPLE | Dashboard → métricas + insights DeepSeek |
| Scoring de fraude | CUMPLE | 14 señales + 7 RF, semáforo, ranking |
| Importación CSV | CUMPLE | Siniestros y tarifario desde CSV |
| Panel admin | CUMPLE | Log de auditoría de acciones |

## Endpoints Clave

| Endpoint | Estado | Uso |
|---|---|---|
| `GET /api/profiles` | CUMPLE | Perfiles |
| `POST /api/profiles` | CUMPLE | Crear perfil con contraseña |
| `POST /api/profiles/{id}/token` | CUMPLE | Login con contraseña |
| `POST /api/profiles/admin-login` | CUMPLE | Login admin |
| `GET /api/dashboard` | CUMPLE | KPIs |
| `GET /api/dashboard/claims-by-day` | CUMPLE | Serie temporal |
| `GET /api/claims` | CUMPLE | Siniestros |
| `POST /api/claims` | CUMPLE | Crear siniestro |
| `POST /api/claims/import-csv` | CUMPLE | Importar siniestros CSV |
| `POST /api/claims/auto/declaration` | CUMPLE | Declaración automática |
| `POST /api/claims/auto/police-report` | CUMPLE | Parte automático |
| `GET /api/claims/{id}/timeline` | CUMPLE | Timeline |
| `GET /api/claims/{id}/executive-summary` | CUMPLE | Resumen ejecutivo |
| `POST /api/audit-pdf` | CUMPLE | Factura PDF |
| `POST /api/audit-ai/{invoice_id}` | CUMPLE | Auditoría IA individual |
| `POST /api/audit-ai-all` | CUMPLE | Auditoría IA masiva |
| `POST /api/audit-deepseek-batch` | CUMPLE | Auditoría batch |
| `GET /api/audit-results` | CUMPLE | Auditorías |
| `POST /api/audit-results/{id}/approve` | CUMPLE | Aprobar |
| `POST /api/audit-results/{id}/reject` | CUMPLE | Rechazar |
| `POST /api/audit-results/{id}/escalate` | CUMPLE | Escalar |
| `POST /api/audit-results/{id}/send-to-legal` | CUMPLE | Derivar a Legal |
| `GET /api/legal/notifications` | CUMPLE | Notificaciones Legal |
| `POST /api/demo/documents` | CUMPLE | PDFs manuales |
| `POST /api/demo/complete-case` | CUMPLE | Demo automática |
| `GET /api/intelligence/fraud` | CUMPLE | Inteligencia antifraude |
| `GET /api/intelligence/portfolio` | CUMPLE | Cartera |
| `GET /api/intelligence/operations` | CUMPLE | Operaciones |
| `GET /api/intelligence/audit-coverage` | CUMPLE | Cobertura |
| `GET /api/intelligence/claim/{id}` | CUMPLE | Insight siniestro |
| `POST /api/intelligence/deepseek-insight` | CUMPLE | Insight DeepSeek V4 Flash |
| `POST /api/agent/query` | CUMPLE | Chatbot inteligente |
| `GET /api/siniestros/{id}/fraud-score` | CUMPLE | Score individual |
| `POST /api/siniestros/score-all` | CUMPLE | Recalcular scores |
| `GET /api/siniestros/ranking` | CUMPLE | Ranking fraude |
| `GET /api/fraud-dashboard` | CUMPLE | Dashboard fraude |
| `GET /api/admin/audit-log` | CUMPLE | Log auditoría |
| `GET /api/admin/audit-log/stats` | CUMPLE | Stats log |

## Evidencia de No Dependencia Local

- Los documentos demo se generan en `backend/test_pdfs`.
- No se requiere `Downloads` ni rutas absolutas del equipo del desarrollador.
- El launcher usa rutas relativas al proyecto.
- La base de datos es local al repositorio.

## Riesgos Residuales

- Para auditoría IA real se requiere API key válida.
- Si no hay API key o la API falla, la demo sigue con reglas locales como fallback.
- OCR de imágenes/fotos no es alcance actual; se procesan PDFs.

## Conclusión

El prototipo cumple los elementos necesarios para presentación: ejecución portable, demo manual, demo automática con DeepSeek V4 Flash, carga documental, auditoría cognitiva, flujo de decisión humana por roles, chatbot inteligente, inteligencia operativa, scoring de fraude, reportes, perfiles con seguridad y trazabilidad del expediente.
