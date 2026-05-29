# Uso de Inteligencia Artificial — Miraclex

La IA principal del sistema es **DeepSeek V4 Flash vía OpenCode Go**. Se usa para auditar facturas, generar explicaciones de riesgo en lenguaje natural, alimentar el chatbot inteligente y producir insights operativos bajo demanda.

## 1. Prioridad de Motores

1. **DeepSeek V4 Flash vía OpenCode Go**: motor principal recomendado.
2. **DeepSeek API directa**: fallback opcional si se configura `DEEPSEEK_API_KEY`.
3. **Reglas locales**: fallback técnico si la IA falla o modo manual cuando el usuario lo solicita.

## 2. Configuración

Archivo `.env`:

```env
OPENCODE_GO_API_KEY=tu_api_key
OPENCODE_GO_API_BASE=https://opencode.ai/zen/go/v1
OPENCODE_GO_MODEL=deepseek-v4-flash

DEEPSEEK_API_KEY=
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

## 3. Auditoría de Facturas

Archivo: `backend/deepseek_auditor.py`.

Capacidades:

- Extrae contexto de factura, siniestro, declaración, parte policial y tarifario.
- Evalúa sobrecobros, duplicados, incoherencias y señales de riesgo.
- Devuelve hallazgos estructurados.
- Incluye severidad, evidencia, recomendación y confianza.
- Aplica validación semántica y reintento si la respuesta no cumple el esquema esperado.
- Soporte de historial de facturas para detección cruzada.

Modalidades de auditoría IA:

| Endpoint | Descripción |
|---|---|
| `POST /api/audit-ai/{invoice_id}` | Auditoría individual con DeepSeek V4 Flash |
| `POST /api/audit-ai-all` | Auditoría masiva concurrente (configurable con `AI_AUDIT_CONCURRENCY`) |
| `POST /api/audit-deepseek-batch` | Auditoría batch |
| `POST /api/audit/{invoice_id}` | Auditoría con agente (DeepSeek principal + reglas como fallback) |

## 4. Chatbot Inteligente

Archivo: `backend/chatbot_agent.py`.

Capacidades:

- Preguntas en lenguaje natural sobre datos del sistema.
- Inferencia SQL automática desde la pregunta del usuario.
- Reescritura de respuestas con DeepSeek V4 Flash para lenguaje natural.
- Restricciones por perfil: cada rol recibe respuestas limitadas a su ámbito.
- Widget de burbuja flotante en el frontend (`frontend/js/components/chatbotBubble.js`).

Endpoint: `POST /api/agent/query`.

## 5. Insights de Inteligencia Operativa

Endpoint: `POST /api/intelligence/deepseek-insight`.

Tipos de insight disponibles:

| Tipo | Descripción |
|---|---|
| `explain_risk` | Explica indicadores de riesgo de un siniestro |
| `explain_fraud_score` | Desglosa componentes del score de fraude |
| `summarize_claim` | Resumen ejecutivo del siniestro |
| `portfolio_summary` | Resumen de desempeño de cartera |
| `branch_analysis` | Análisis comparativo por sucursal |
| `executive_briefing` | Briefing ejecutivo con hallazgos y acciones |
| `explain_anomaly` | Explicación de anomalías detectadas |

El sistema adapta el prompt según el rol del usuario (demo_jurado, analista, antifraude, jefatura, auditoria).

## 6. Patrones de Prompting

- **Chain-of-Thought forzado**: schema JSON obliga a `cadena_de_razonamiento` antes del veredicto.
- **Few-shot calibration**: 2 ejemplos en system prompt (factura limpia + factura con fraude).
- **Self-reflection pass**: segunda llamada como revisor escéptico.
- **Validación semántica + retry**: si la respuesta viola reglas, se reenvía con feedback.
- **Confianza calibrada 0.0-1.0**: hallazgos CRITICAL requieren confianza >= 0.7.

## 7. Fallback de Reglas

El fallback existe para que la demo no se bloquee si la API de IA no responde.

Casos en que se usan reglas:

- Error 500/503 al llamar DeepSeek.
- Falta de configuración de API en una ruta crítica.
- Acción manual seleccionada por el usuario.

La UI muestra cuando se usó fallback.

## 8. Principios Éticos

- La IA no acusa ni determina culpabilidad.
- La IA genera alertas de posible riesgo.
- Toda aprobación, rechazo, escalamiento o envío a legal es decisión humana.
- Los datos de demo son sintéticos.
- Los insights siempre citan datos suministrados; nunca inventan métricas.
