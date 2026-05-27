# Matriz de Cumplimiento - HackIAthon 2026

Proyecto: Detector de Posibles Fraudes en Siniestros usando IA  
Repositorio: `Final-reto`  
Fecha: 27 / 05 / 2026  
Revisor: DeepSeek v4 Flash (OpenCode Go) — Auditoría Estricta

---

## Instrucciones de uso (DeepSeek)

1. Revisar codigo, endpoints, frontend y documentacion.
2. Marcar cada requisito como `CUMPLE`, `PARCIAL` o `NO CUMPLE`.
3. Agregar evidencia concreta (archivo/endpoint/pantalla).
4. Si no cumple: proponer ajuste puntual (archivo + cambio esperado).
5. No usar lenguaje general; solo hallazgos verificables.

---

## 1) Datos Minimos Requeridos

| Requisito | Estado | Evidencia | Gap detectado | Correccion propuesta |
|---|---|---|---|---|
| Tabla Siniestros con campos minimos del reto | **CUMPLE** | `backend/models.py:87-113` — Siniestro model con: id_siniestro, id_poliza, id_asegurado, ramo, cobertura, fecha_ocurrencia, fecha_reporte, monto_reclamado, monto_estimado, monto_pagado, estado, sucursal, descripcion, documentos_completos, beneficiario. Ademas campos extras (dias_desde_inicio_poliza, dias_desde_fin_poliza, dias_entre_ocurrencia_reporte, historial_siniestros_asegurado, etiqueta_fraude_simulada) | Ninguno | N/A |
| Tabla/estructura Polizas (`id_poliza`, `fecha_inicio`, `fecha_fin`, `suma_asegurada`, `deducible`) | **NO CUMPLE** | `backend/models.py` — NO existe modelo Poliza. `id_poliza` es solo un `Column(String(20))` en Siniestro (line 92). No hay fecha_inicio, fecha_fin, suma_asegurada, ni deducible en ninguna tabla | Falta modelo Poliza completo con sus campos. No se pueden aplicar reglas de borde de vigencia ni monto cercano a suma asegurada | Crear `backend/models.py`: clase `Poliza` con campos: id_poliza (PK), fecha_inicio, fecha_fin, suma_asegurada, deducible, ramo, asegurado_id. Migrar `id_poliza` en Siniestro a FK |
| Tabla Asegurados sinteticos | **NO CUMPLE** | `backend/models.py` — NO existe modelo Asegurado. `id_asegurado` es solo un `Column(String(50))` en Siniestro (line 93). seed_data usa strings literales como "Carlos Mendoza" | Sin tabla de asegurados no se puede calcular frecuencia historica de reclamos por asegurado | Crear `backend/models.py`: clase `Asegurado` con: id, identificacion, nombres, direccion, telefono, historial_siniestros. Poblar en seed_data |
| Tabla Beneficiarios/Proveedores | **PARCIAL** | `backend/models.py:71-84` — Workshop (taller) model existe con: id, name, ruc, address, phone, email. Pero `beneficiario` en Siniestro (line 105) es solo un string | Falta modelo Beneficiario independiente. Workshop cubre solo proveedores tipo taller | Crear modelo Beneficiario o al menos documentar que Workshop cumple como "Proveedor" |
| Tabla Documentos e inconsistencias | **NO CUMPLE** | `backend/models.py` — No existe modelo Documento. `documentos_completos` (line 104) es solo un `Integer` flag 0/1 en Siniestro. `campos_faltantes` solo existe en `pdf_extractor.py` como salida de extraccion | Sin tabla de documentos no se puede trackear que documentos faltan, cuales estan inconsistentes, ni versiones | Crear `backend/models.py`: clase `Documento` con: id, siniestro_id, tipo_documento (factura, poliza, fotos, etc.), estado (completo, faltante, inconsistente), observaciones |
| Cruce entre siniestro, poliza y factura | **PARCIAL** | `backend/models.py`: Siniestro tiene `id_poliza` (string), Invoice tiene `siniestro_id` (FK a Siniestro). Cruce siniestro→factura existe via FK. Cruce siniestro→poliza es solo string, no hay FK real a tabla Poliza | El cruce siniestro→poliza es debil (string, no FK). No hay validacion de integridad referencial poliza→siniestro | Al crear modelo Poliza, convertir `id_poliza` en FK y agregar `UniqueConstraint` |

---

## 2) Reglas de Negocio y Senales

| Requisito | Estado | Evidencia | Gap detectado | Correccion propuesta |
|---|---|---|---|---|
| Reclamo cercano al borde de vigencia | **NO CUMPLE** | `backend/rules_engine.py` — No existe regla. Siniestro tiene `dias_desde_inicio_poliza` y `dias_desde_fin_poliza` (models.py:106-107) pero no hay tabla Poliza con fecha_inicio/fecha_fin para calcularlo | Sin modelo Poliza con fechas no se puede implementar esta regla | P0: Crear Poliza, implementar regla `BorderVigencyRule`: si `fecha_ocurrencia` esta a <48h de `fecha_inicio` o `fecha_fin` → WARNING/CRITICAL |
| Demora de denuncia/reporte | **PARCIAL** | `backend/models.py:108` — `dias_entre_ocurrencia_reporte` se incluye en seed_data? NO: seed_data.py no calcula este campo. `rules_engine.py` no tiene regla | El campo existe en modelo pero no se calcula en seed_data ni hay regla que lo evalue | P1: Implementar `ReportingDelayRule` en rules_engine.py: si dias_entre_ocurrencia_reporte > 4 → WARNING, > 7 → CRITICAL. Calcular en seed_data |
| Frecuencia alta de reclamos por asegurado | **NO CUMPLE** | `backend/models.py:109` — `historial_siniestros_asegurado` existe como Integer. Pero no hay regla que lo evalua ni seed_data lo establece. Sin tabla Asegurado no hay historial real | Campo existe pero no se usa en reglas ni se puebla | P1: Crear modelo Asegurado con contador de siniestros. Implementar `HighClaimFrequencyRule`: si historial_siniestros_asegurado > 3 en 12 meses → WARNING |
| Frecuencia alta por vehiculo/conductor | **NO CUMPLE** | `backend/models.py` — No existe campo vehiculo ni conductor en Siniestro. Solo `descripcion` (texto libre) menciona a veces el vehiculo | Sin datos estructurados de vehiculo (placa, VIN, modelo) no se puede trackear frecuencia por vehiculo | P1: Agregar campos `vehiculo_placa`, `vehiculo_modelo` a Siniestro. Implementar `VehicleFrequencyRule` |
| Proveedor recurrente / lista restrictiva | **NO CUMPLE** | `backend/rules_engine.py` — No hay regla de proveedor recurrente. Workshop tiene `notify_automatically` (models.py:81) pero no hay concepto de "lista restrictiva" o "proveedor recurrente" | Sin lista restrictiva configurable ni regla que detecte recurrencia | P1: Agregar campo `restricted` a Workshop. Implementar `RecurrentProviderRule`: si mismo workshop aparece en ≥3 siniestros distintos en 30 dias → WARNING |
| Documentos incompletos | **PARCIAL** | `backend/pdf_extractor.py` — Extrae `campos_faltantes` del PDF. `backend/models.py:104` — `documentos_completos` flag. Pero no hay regla en `rules_engine.py` que use este flag | Documentacion incompleta se detecta en extraccion pero no genera hallazgo de auditoria | P1: Agregar regla `IncompleteDocumentationRule`: si documentos_completos==0 en siniestro → MISSING_DOCUMENT WARNING |
| Documentos inconsistentes | **NO CUMPLE** | No hay modelo Documento. No hay logica que compare datos entre documentos. pdf_extractor.py solo extrae, no valida consistencia | Sin tabla Documentos ni logica de verificacion cruzada no se puede detectar inconsistencias documentales | P2: Crear modelo Documento y endpoint de verificacion. Por ahora marcar como no implementado |
| Narrativas similares (NLP) | **NO CUMPLE** | `backend/models.py:103` — `descripcion` en Siniestro es texto libre. `backend/gemini_auditor.py` — Gemini podria analizar narrativas en modo batch, pero no hay logica dedicada de NLP para comparar descripciones | Sin implementacion de NLP no se pueden detectar narrativas clonadas entre siniestros | P2: Agregar endpoint de analisis de similitud de descripciones usando embeddings o Gemini |
| Monto cercano/superior a suma asegurada | **NO CUMPLE** | `backend/models.py` — No existe `suma_asegurada` en ninguna tabla (falta modelo Poliza). Siniestro tiene `monto_reclamado`, `monto_estimado`, `monto_pagado` pero sin referencia a suma asegurada | Sin suma_asegurada no se puede evaluar si el monto reclamado es cercano/superior | P0: Al crear modelo Poliza incluir suma_asegurada. Implementar `AmountNearLimitRule`: si monto_reclamado > 80% de suma_asegurada → WARNING |

### RF criticas (del documento)

| Codigo | Regla | Estado | Evidencia | Gap detectado | Correccion propuesta |
|---|---|---|---|---|---|
| RF-01 | Cobertura Perdida Total por Robo (PTxRB) | **NO CUMPLE** | No existe logica que evalue si un siniestro de robo deberia calificar como perdida total. `backend/rules_engine.py` no tiene esta regla | Regla de negocio critica del reto no implementada | P0: Implementar `TheftTotalLossRule`: si cobertura=Robo y monto_reclamado > 75% del valor_vehiculo (nuevo campo en Poliza o Siniestro) → CRITICAL |
| RF-02 | Evidencia de falsificacion/adulteracion documental | **NO CUMPLE** | No hay logica de deteccion de falsificacion. `pdf_extractor.py` solo extrae datos, no verifica autenticidad. `gemini_auditor.py` podria detectar anomalias pero no falsificacion activa | Sin verificacion de firma digital, metadatos PDF, o consistencia de clave SRI no se puede detectar falsificacion | P2: Agregar verificacion de modulo 11 de clave de acceso SRI. Comparar RUC vs base de datos SRI |
| RF-03 | Coincidencia exacta en lista restrictiva | **NO CUMPLE** | `backend/models.py` — Workshop no tiene campo `restricted` ni `risk_level`. No hay endpoint de lista restrictiva. No hay regla que la evalua | Sin concepto de lista restrictiva no se puede implementar | P1: Agregar campo `risk_level` (bajo/medio/alto) a Workshop con seed data. Implementar `RestrictedProviderRule`: si workshop.risk_level==alto → CRITICAL |
| RF-04 | Dinamica fisicamente imposible | **PARCIAL** | `backend/rules_engine.py:224-268` — `IncoherenceRule` evalua si items son compatibles con tipo de siniestro. Pero usa ramo (Vehículos) no tipo especifico | La regla actual es demasiado generica (solo evalua ramo "Vehículos" vs "Salud"). No evalua coherencia mecanica real (ej. soporte de motor en choque lateral) | P1: Refinar `IncoherenceRule` para usar `cobertura` (Choque, Robo, Daño) no solo `ramo`. Mapear items a coberturas especificas |
| RF-05 | Borde de vigencia < 48h | **NO CUMPLE** | Sin modelo Poliza con fecha_inicio/fecha_fin es imposible calcular. `dias_desde_inicio_poliza` y `dias_desde_fin_poliza` existen en Siniestro pero seed_data no los puebla | Mismo gap que "Reclamo cercano al borde de vigencia" | P0: Ver correccion de "Reclamo cercano al borde de vigencia" arriba |
| RF-06 | Demora atipica de denuncia (>4 dias) | **PARCIAL** | `backend/models.py:108` — `dias_entre_ocurrencia_reporte` existe. Seed_data establece valores (1-3 dias) pero no hay regla que lo evalua | Datos disponibles, regla no implementada | P1: Implementar `ReportingDelayRule` (ver arriba) con umbral >4 dias CRITICAL |
| RF-07 | Narrativa identica/clonada | **NO CUMPLE** | `backend/models.py:103` — descripcion texto libre. No hay logica de comparacion de narrativas entre siniestros. `gemini_auditor.py` batch mode podria detectar pero no hay implementacion dedicada | Sin NLP no se puede detectar narrativas identicas | P2: Implementar comparacion de descripciones usando TF-IDF o Gemini. Si similitud > 90% entre dos siniestros distintos → CRITICAL |

---

## 3) Score de Riesgo

| Requisito | Estado | Evidencia | Gap detectado | Correccion propuesta |
|---|---|---|---|---|
| Score total 0-100 trazable | **CUMPLE** | `backend/rules_engine.py:377-391` — `calculate_risk_score()`: CRITICAL*35 + WARNING*20 + INFO*5, cap 100. Trazable: cada hallazgo contribuye con peso fijo | Ninguno | N/A |
| Clasificacion Verde (0-40) | **PARCIAL** | `backend/agent.py:92-97` — Usa rangos: 0-29 → APPROVED, 30-69 → COMPLETED, >=70 → ESCALATED. `pdf_generator.py:88-89`: BAJO 0-29, MEDIO 30-69, ALTO 70-100 | Rangos no coinciden con lo solicitado (Verde 0-40, Amarillo 41-75, Rojo 76-100). El codigo usa 0-29/30-69/70-100 | P1: Ajustar thresholds: Verde 0-40, Amarillo 41-75, Rojo 76-100 en agent.py, pdf_generator.py, frontend/utils.js |
| Clasificacion Amarillo (41-75) | **PARCIAL** | Misma evidencia que arriba | Rangos incorrectos | P1: Ver correccion arriba |
| Clasificacion Rojo (76-100) | **PARCIAL** | Misma evidencia que arriba | Rangos incorrectos | P1: Ver correccion arriba |
| Reglas excluyentes aplicadas antes del score gradual | **NO CUMPLE** | `backend/rules_engine.py` — No hay concepto de reglas excluyentes. Todas las reglas suman al score. No hay reglas que automaticamente pongan score=100 sin importar otras reglas | Las RF criticas (RF-01..RF-07) deberian ser excluyentes: si una RF se activa, score=100 directamente sin evaluar gradual | P0: Implementar reglas excluyentes: si cualquier RF (01-07) es CRITICAL → risk_score=100 directamente. Ejecutar RF excluyentes primero, si hay match saltar score gradual |
| Accion sugerida visible por nivel | **PARCIAL** | `backend/agent.py:83-88` — `_generate_summary` sugiere accion: >=70 "ESCALAR", >=40 "Solicitar justificacion", <40 "Revisar hallazgos menores". `frontend/js/utils.js` — `riskBadge()` pinta colores. Pero no hay panel de "Accion sugerida" dedicado en UI | Accion sugerida solo en texto del summary, no como badge visual independiente. Umbrales desalineados (40 no 30) | P1: Agregar componente visual "Accion requerida" en auditDetail.js. Sincronizar umbrales Verde/Amarillo/Rojo |

---

## 4) Funcionalidades Minimas del Prototipo

| Requisito | Estado | Evidencia | Gap detectado | Correccion propuesta |
|---|---|---|---|---|
| Carga de datos de siniestros | **CUMPLE** | `backend/seed_data.py` — 5 siniestros con anomalias plantadas. `GET /api/claims` — endpoint de listado. `POST /api/audit-pdf` — crea siniestro desde PDF si no existe. Frontend `siniestros.js` — vista expandible | Ninguno | N/A |
| Carga de facturas PDF y cola de pendientes | **CUMPLE** | `backend/main.py:705-853` — `POST /api/audit-pdf` con drag-drop. `GET /api/invoices/pending` — cola. Frontend `upload.js` — drag-drop UI. `components/auditQueue.js` — cola visual inferior izquierda. `frontend/js/pages/auditorias.js` — pestana Pendientes | Ninguna funcional critica faltante | N/A |
| Deteccion de alertas por reglas | **CUMPLE** | `backend/rules_engine.py` — 5 reglas implementadas: PriceOverchargeRule, DuplicateChargeRule, QuantityAnomalyRule, IncoherenceRule, InvoiceResubmissionRule. Ejecutadas via `POST /api/audit-rules/{id}` | Faltan las 7 RF criticas del reto (ver seccion 2) | P0: Implementar RF-01..RF-07 como reglas excluyentes |
| Modelo/IA para score de posible fraude | **CUMPLE** | `backend/gemini_auditor.py` — Gemini 2.5 Flash con CoT, few-shot, self-reflection, validacion semantica. `POST /api/audit-ai/{id}` y `POST /api/audit-gemini-batch` | Sin `GOOGLE_API_KEY` entra en modo mock (respuestas simuladas). No hay fallback automatico | P2: Documentar claramente que el modo IA requiere API key. El motor de reglas funciona siempre |
| Dashboard/interfaz funcional | **CUMPLE** | `frontend/js/pages/dashboard.js` — KPIs, scatter, donut, toggle TEST. `auditorias.js` — tabs pendientes/revisadas. `upload.js` — drag-drop + generador. `tarifario.js` — CRUD. `siniestros.js` — expandible. `auditDetail.js` — detalle con PDF preview. `style.css` — dark/light theme, glassmorphism | Dashboard no muestra top 10 riesgos ni ranking de proveedores (solo en chatbot) | P2: Agregar widget de Top 10 Riesgos en dashboard principal |
| Generacion de PDF (interno/taller) | **CUMPLE** | `backend/pdf_generator.py` — `generate_audit_report_pdf` (interno con risk score) y `generate_workshop_notification_pdf` (taller sin risk score). Sirven via `GET /api/audit-results/{id}/report-preview?type=internal`workshop` | PDFs no incluyen informacion de poliza (porque no existe modelo Poliza) | P1: Al crear Poliza, incluir datos de poliza en PDF |
| Explicacion automatica del motivo de alerta | **CUMPLE** | `backend/agent.py:73-89` — `_generate_summary()` produce texto explicativo. `backend/rules_engine.py` — cada Finding tiene title, description, recommendation. Frontend `auditDetail.js` — muestra hallazgos con severidad, descripcion, recomendacion | Ninguno | N/A |

---

## 5) Agente IA (Chatbot burbuja)

| Requisito | Estado | Evidencia | Gap detectado | Correccion propuesta |
|---|---|---|---|---|
| Burbuja flotante operativa | **CUMPLE** | `frontend/js/components/chatbotBubble.js` — Widget flotante esquina inferior derecha con toggle, input, FAQ buttons. Integrado en index.html | Ninguno | N/A |
| FAQs del jurado precargadas | **CUMPLE** | `chatbotBubble.js` — 4 botones FAQ: "Cuales son los top 10 riesgos?", "Por que SIN-1 esta en riesgo?", "Que taller tiene mas alertas?", "Resumen ejecutivo". Mapean a `_build_agent_answer` en main.py:1126-1174 | Ninguno | N/A |
| Consulta libre por siniestro (ej. SIN-123) | **CUMPLE** | `backend/main.py:1140-1150` — Regex `sin[-\s]?(\d+)` captura cualquier SIN-XXXX y retorna hallazgos | Ninguno | N/A |
| Respuestas basadas en datos reales del sistema | **CUMPLE** | `backend/main.py:1126-1174` — `_build_agent_answer()` consulta DB real: AuditResult, AuditFinding, Workshop, Siniestro. Respuestas no son genericas | Ninguno | N/A |
| Restricciones por perfil (si aplica) | **CUMPLE** | `frontend/js/auth.js` — 5 perfiles (demo_jurado, analista, antifraude, jefatura, auditoria) con permisos. `backend/main.py:1179-1182` — endpoint valida perfil permitido | Perfiles existen pero no hay diferenciacion real en respuestas del chatbot | P2: Implementar diferenciacion de respuestas segun perfil (ej. analista ve mas detalles que demo_jurado) |
| Sin acusaciones directas de fraude | **CUMPLE** | `backend/main.py:1068-1076` — `_safe_policy_text()` reemplaza palabras prohibidas (culpable, delito, estafa confirmada, acusado, sentencia, demanda) por "posible riesgo". Agrega disclaimer de revision humana | Ninguno | N/A |

---

## 6) Seguridad, Privacidad y Etica

| Requisito | Estado | Evidencia | Gap detectado | Correccion propuesta |
|---|---|---|---|---|
| No se usan datos personales reales | **CUMPLE** | `backend/seed_data.py` — todos los datos son sinteticos (Carlos Mendoza, Maria Lopez, etc.). `test_invoice_generator.py` — datos aleatorios sinteticos. `docs/facturas_muestra/` — PDFs generados con datos ficticios | Ninguno | N/A |
| No se suben credenciales al repo | **CUMPLE** | `.gitignore` incluye `.env`. No hay archivos con API keys en el repo. `backend/main.py:21` — `load_dotenv()` carga de `.env` | Ninguno | N/A |
| No hay llaves API hardcodeadas | **CUMPLE** | `backend/main.py:1081` — lee `GOOGLE_API_KEY` de `os.getenv`. `backend/gemini_auditor.py:822` — lee de `os.environ.get("GOOGLE_API_KEY")`. `backend/main.py:1081-1090` — lee `OPENCODE_GO_API_KEY` / `DEEPSEEK_API_KEY` de env vars | Ninguno | N/A |
| Se aclara "alerta, no acusacion" | **CUMPLE** | `backend/main.py:1068-1076` — disclaimer. `pdf_generator.py:257-260` — "Documento interno... No distribuir externamente". `chatbotBubble.js` — respuestas usan lenguaje de "posible riesgo" | Ninguno | N/A |
| Se enfatiza revision humana | **CUMPLE** | `backend/agent.py:83-88` — recomendacion de revision manual. `pdf_generator.py` — lenguaje de "sugerencia", no decision final. `main.py:1073-1075` — disclaimer "requiere revision humana" | Ninguno | N/A |
| Sin opiniones legales concluyentes | **CUMPLE** | `backend/main.py:1069` — banned words list incluye terminos legales. `_safe_policy_text()` los filtra. PDF taller usa "ajustes requeridos" no lenguaje legal | Ninguno | N/A |

---

## 7) Entregables Obligatorios

| Entregable | Estado | Evidencia | Gap detectado | Correccion propuesta |
|---|---|---|---|---|
| Prototipo funcional ejecutable | **CUMPLE** | `backend/main.py` — FastAPI app. `start.bat` / `start.sh` — scripts de inicio. `docker-compose.yml` — Docker. `server.js` — Express proxy. Funciona con `pip install -r backend/requirements.txt` + `uvicorn` | Ninguno | N/A |
| Codigo fuente en GitHub | **CUMPLE** | Repositorio `Final-reto` en `https://github.com/yosuSALA/Final-reto.git`. Commit `1d71e52` con 53 archivos | Ninguno | N/A |
| Dataset sintetico/publico documentado | **CUMPLE** | `backend/seed_data.py` — 3 workshops, 24 tarifas, 5 siniestros con anomalias plantadas. `docs/facturas_muestra/` — 7 PDFs de muestra. `test_invoice_generator.py` — generador de facturas aleatorias | Ninguno | N/A |
| README completo (instalacion, ejecucion, demo) | **CUMPLE** | `README.md` — existe con instrucciones. `docs/MANUAL_USO.md` — guia de usuario paso a paso. `docs/DOC_FUNCIONES.md` — documentacion de funciones | README podria incluir arquitectura explicita | P2: Mejorar README con diagrama de arquitectura y tabla de endpoints |
| Arquitectura | **PARCIAL** | No hay archivo `docs/ARQUITECTURA.md` dedicado. `docs/DOC_FUNCIONES.md` explica componentes pero sin diagrama. `DEEPSEEK_REVIEW_LOOP.md` y `PLAN_SOFISTICADO_IMPLEMENTACION.md` describen plan pero no arquitectura actual | Sin documento de arquitectura formal el jurado no puede evaluar el diseno del sistema | P1: Crear `docs/ARQUITECTURA.md` con: componentes (FastAPI, SQLite, Express, SPA vanilla), flujo de datos (upload→extract→audit→report), decisiones tecnicas |
| Modelo de datos | **CUMPLE** | `backend/models.py` — 7 modelos ORM con relaciones, enums, constraints. Diagrama implícito en relaciones | Sin diagrama visual ER | P2: Agregar diagrama ER (Mermaid) en docs/MODELO_DATOS.md |
| Explicacion de modelo IA | **CUMPLE** | `backend/gemini_auditor.py` — documentacion detallada de patrones SOTA: CoT, few-shot, evidence citation, confidence calibration, semantic validation, self-reflection. `docs/DOC_FUNCIONES.md` seccion 5 explica motor IA | Ninguno | N/A |
| Rubrica/reglas de alertas | **CUMPLE** | `backend/rules_engine.py` — 5 reglas documentadas con severidad. `docs/DOC_FUNCIONES.md` — seccion 4 explica cada regla y calibracion | Ninguno | N/A |
| Demo funcional | **CUMPLE** | Flujo completo: `start.bat` → `http://localhost:8000/` → upload → auditoria → PDF. `docs/MANUAL_USO.md` seccion 4 describe flujo de demo | Ninguno | N/A |
| Presentacion ejecutiva | **NO CUMPLE** | No existe archivo de presentacion (PPT, PDF, o documento ejecutivo) en el repositorio. `landing.html` es pagina web no presentacion | Sin presentacion el jurado no tiene material de apoyo para evaluar el proyecto | P1: Crear `docs/PRESENTACION_EJECUTIVA.md` con: problema, solucion, arquitectura, resultados, demo script, equipo |

---

## 8) Hallazgos Criticos (Top 10)

| # | Hallazgo | Impacto (alto/medio/bajo) | Evidencia | Accion recomendada |
|---|---|---|---|---|
| 1 | **Falta modelo Poliza completo** — No existe tabla Poliza con fecha_inicio, fecha_fin, suma_asegurada, deducible. Esto bloquea RF-01, RF-05, regla de borde de vigencia, regla de monto cercano a suma asegurada | **ALTO** | `backend/models.py` — no existe clase `Poliza`. `id_poliza` es solo string en Siniestro (line 92) | Crear modelo Poliza con todos los campos requeridos. Migrar id_poliza a FK. Poblar seed_data |
| 2 | **Falta modelo Asegurado** — No existe tabla Asegurado. `id_asegurado` es solo string. No se puede calcular frecuencia historica de reclamos por asegurado | **ALTO** | `backend/models.py` — no existe clase `Asegurado`. seed_data usa strings literales | Crear modelo Asegurado con identificacion, nombres, historial. Poblar seed_data |
| 3 | **7 RF criticas no implementadas** — RF-01 a RF-07 del documento del reto no existen como reglas. Solo se implementaron las 5 reglas base (sobrecobro, duplicado, cantidad, incoherencia, re-facturacion) | **ALTO** | `backend/rules_engine.py` — solo 5 reglas. Ninguna RF del reto implementada | Implementar RF-01 a RF-07 como reglas excluyentes (ver seccion 2 para detalle por RF) |
| 4 | **Falta tabla Documentos** — No existe modelo para trackear documentos del siniestro. No se pueden detectar documentos faltantes ni inconsistentes a nivel de BD | **ALTO** | `backend/models.py` — no existe clase `Documento`. Solo flag `documentos_completos` en Siniestro | Crear modelo Documento con tipo, estado, observaciones. Implementar regla de documentos incompletos |
| 5 | **Score de riesgo usa rangos incorrectos** — Codigo usa Verde 0-29 / Amarillo 30-69 / Rojo 70-100. El reto exige Verde 0-40 / Amarillo 41-75 / Rojo 76-100 | **MEDIO** | `backend/agent.py:92-97`, `pdf_generator.py:88-89`, `utils.js:riskBadge` — thresholds desalineados | Ajustar thresholds en agent.py, pdf_generator.py, y frontend/utils.js para coincidir con especificacion del reto |
| 6 | **Sin reglas excluyentes** — No hay concepto de reglas que automaticamente pongan score=100. Todas las reglas se suman linealmente | **MEDIO** | `backend/rules_engine.py:377-391` — score se calcula como suma lineal. No hay `if critical_findings_that_are_exclusionary: score=100` | Implementar reglas excluyentes: si alguna RF (01-07) es CRITICAL → risk_score=100 directamente |
| 7 | **IncoherenceRule demasiado generica** — Solo evalua ramo (Vehículos vs Salud), no tipo especifico de siniestro (Choque, Robo, Daño). Todos los items de Vehículos pasan aunque sean mecanicamente incoherentes | **MEDIO** | `backend/seed_data.py` — todos los tariff items tienen `applicable_claim_types=["Vehículos"]`. Siniestro 4 (choque lateral con soporte de motor) no se detecta | Refinar IncoherenceRule para usar cobertura especifica. Mapear items en seed_data a tipos especificos |
| 8 | **Seed data no usa campos de fraude** — `dias_desde_inicio_poliza`, `dias_desde_fin_poliza`, `dias_entre_ocurrencia_reporte`, `historial_siniestros_asegurado`, `etiqueta_fraude_simulada` existen en modelo pero seed_data no los puebla | **MEDIO** | `backend/seed_data.py` — Siniestro creados sin estos campos. Solo seed_data.py:107-109 tiene `fecha_ocurrencia` y `fecha_reporte` | Poblar todos los campos de Siniestro en seed_data con valores realistas y anomalias plantadas |
| 9 | **Sin presentacion ejecutiva para jurado** — No existe archivo de presentacion (PPT/PDF/MD ejecutivo) en el repositorio. El landing.html no es una presentacion formal | **MEDIO** | No existe `docs/PRESENTACION_EJECUTIVA.md` ni ningun archivo similar | Crear presentacion ejecutiva con: problema, solucion, arquitectura, resultados de auditoria, metricas, demo script, equipo |
| 10 | **Dashboard no muestra Top 10 Riesgos** — Aunque el chatbot puede responder "top 10 riesgos", el dashboard principal no tiene un widget dedicado a priorizacion de casos | **BAJO** | `frontend/js/pages/dashboard.js` — no hay componente de "Top 10 Riesgos". Solo KPIs y graficos | Agregar componente de tabla "Top 10 Riesgos" en dashboard con link a detalle de auditoria |

---

## 9) Plan de Correccion por Prioridad

### P0 (bloquea demo/jurado — corregir antes de presentar)
1. **Crear modelo Poliza** (`backend/models.py`): clase `Poliza` con id_poliza (PK), fecha_inicio, fecha_fin, suma_asegurada, deducible, ramo. Migrar `id_poliza` en Siniestro a FK.
2. **Crear modelo Asegurado** (`backend/models.py`): clase `Asegurado` con id, identificacion, nombres, direccion, telefono, historial_siniestros.
3. **Implementar 7 RF criticas** (`backend/rules_engine.py`): RF-01 a RF-07 como reglas excluyentes con severidad CRITICAL y efecto de score=100.
4. **Implementar reglas excluyentes** (`backend/rules_engine.py`): mecanismo de "si RF → score=100 directo, saltar score gradual".
5. **Poblar seed_data** (`backend/seed_data.py`): usar todos los campos de Siniestro incluyendo los de fraude.

### P1 (importante para puntaje — corregir idealmente antes)
1. **Ajustar rangos de score** a Verde 0-40, Amarillo 41-75, Rojo 76-100 en agent.py, pdf_generator.py, utils.js.
2. **Implementar reglas de negocio faltantes**: ReportingDelayRule, HighClaimFrequencyRule, VehicleFrequencyRule, RecurrentProviderRule, IncompleteDocumentationRule, AmountNearLimitRule.
3. **Refinar IncoherenceRule** para usar cobertura especifica (Choque, Robo, Daño) en lugar de solo ramo.
4. **Agregar campo `restricted`/`risk_level` a Workshop** y crear RestrictedProviderRule.
5. **Crear modelo Documento** con tipo y estado.
6. **Crear docs/ARQUITECTURA.md** con diagrama y descripcion de componentes.
7. **Crear docs/PRESENTACION_EJECUTIVA.md** con pitch para jurado.
8. **Agregar campos vehiculo** (placa, modelo) a Siniestro.

### P2 (mejoras de robustez — si hay tiempo)
1. **Agregar widget Top 10 Riesgos** en dashboard.
2. **Implementar NLP para narrativas similares** (comparacion de descripciones).
3. **Verificacion de modulo 11** de clave de acceso SRI en PDFs.
4. **Diferenciacion de respuestas del chatbot** por perfil.
5. **Diagrama ER** en docs/MODELO_DATOS.md.
6. **Endpoint de health check** `/api/health`.
7. **Pruebas unitarias** con pytest para rules_engine.

---

## 10) Casos de Prueba Recomendados

### Facturas (desde generador o seed_data)
1. **Siniestro con borde de vigencia <= 48h** — No implementado (requiere Poliza). Seed: crear siniestro con fecha_ocurrencia = fecha_inicio_poliza + 1 día. Esperado: CRITICAL borde vigencia.
2. **Siniestro con reporte tardio > 7 dias** — Seed: siniestro con fecha_ocurrencia = 2026-01-01, fecha_reporte = 2026-01-10. Esperado: CRITICAL demora denuncia (RF-06).
3. **Caso con proveedor recurrente/lista restrictiva** — Seed: workshop con risk_level=alto, 3 siniestros asociados. Esperado: CRITICAL proveedor restrictivo (RF-03).
4. **Caso con documentos incompletos e inconsistentes** — Seed: siniestro con documentos_completos=0, factura sin RUC. Esperado: WARNING/MISSING_DOCUMENT.
5. **Caso con monto cercano a suma asegurada** — No implementado (requiere Poliza). Seed: suma_asegurada=5000, monto_reclamado=4800. Esperado: WARNING monto cercano.
6. **Factura limpia** — Generar via `generate_random_invoice("limpia")`. Esperado: risk_score=0, status=approved.
7. **Factura con sobrecobro** — Generar via `generate_random_invoice("sobrecobro")`. Esperado: al menos 1 OVERCHARGE WARNING o CRITICAL.
8. **Factura con fraude** — Generar via `generate_random_invoice("fraude")`. Esperado: DUPLICATE + INCOHERENCE, ambos CRITICAL.
9. **Re-facturacion** — Subir misma factura con mismo invoice_number a dos siniestros distintos. Esperado: CRITICAL re-facturacion.
10. **Auditoria batch Gemini** — `POST /api/audit-gemini-batch` con todas las facturas. Esperado: analisis cross-pattern con talleres recurrentes.

### API
6. `GET /api/dashboard?include_test=1` — KPIs correctos.
7. `POST /api/audit-rules/{id}` — auditoria deterministica funcional.
8. `POST /api/audit-ai/{id}` — auditoria IA funcional (si hay GOOGLE_API_KEY).
9. `GET /api/audit-results/{id}/report-preview?type=internal` — PDF interno descargable.
10. `GET /api/audit-results/{id}/report-preview?type=workshop` — PDF taller descargable sin risk score.

### Chatbot
11. Consulta chatbot: "Cuales son los top 10 riesgos?" → lista de 10 siniestros ordenados por risk_score.
12. Consulta chatbot: "Por que SIN-1 esta en riesgo?" → hallazgos del siniestro 1.
13. Consulta chatbot: "Que taller tiene mas alertas?" → ranking de talleres por concentracion.
14. Generacion PDF interno y taller sin lenguaje acusatorio → verificar que PDF no contenga "fraude", "culpable", "delito".

---

## 11) Resultado Final de la Revision

- Cumplimiento general estimado: **62%**  
- Riesgo para demo en vivo: **Alto**  
- Apto para presentacion de jurado: **Si, condicionado a:** implementar P0 completo (modelo Poliza, Asegurado, Documentos, 7 RF criticas, reglas excluyentes, seed_data completo) y al menos P1 de ajuste de rangos de score y reglas de negocio basicas.

**Resumen:** El prototipo actual tiene una base solida (FastAPI, 5 reglas funcionales, Gemini IA, dashboard completo, PDFs, chatbot) pero carece de los componentes centrales del reto: modelo Poliza, modelo Asegurado, y las 7 RF criticas. Sin estos, el detector de fraudes no puede evaluar las senales mas importantes del dominio asegurador. Se recomienda priorizar P0 antes de la presentacion al jurado.
