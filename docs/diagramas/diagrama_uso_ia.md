# Diagrama — Uso de Inteligencia Artificial

> Fuente: [`docs/uso_ia.md`](../uso_ia.md)

## Mapa de componentes IA

```mermaid
mindmap
  root((IA en Miraclex))
    Gemini 2.5 Flash
      Auditoría de facturas
        Chain-of-Thought forzado
        Few-shot calibration
        Self-reflection pass
        Validación semántica + retry
      Chatbot fallback
        Reescritura elocuente
        Si no hay clave DeepSeek
    DeepSeek Chat
      Chatbot principal
        Inferencia SQL local
        Contextualización de prompts
        Respuesta ejecutiva
    SequenceMatcher stdlib
      Señal S13
        Similitud caracteres
        Umbral 75%
        Detección narrativas clonadas
    Formateador local
      Fallback técnico
        Sin ninguna API key
        Datos SQL en Markdown
```

## Pipeline — Auditoría cognitiva de facturas (Gemini)

```mermaid
flowchart TD
    INPUT["📄 Factura PDF procesada\n(items, montos, RUC, tipo siniestro)"] --> SYSTEM_PROMPT

    subgraph GEMINI_PIPELINE["GeminiAuditor — gemini_auditor.py"]
        SYSTEM_PROMPT["📝 System Prompt\n• Few-shot: 1 factura limpia\n• Few-shot: 1 factura con fraude\n• Instrucciones de análisis"]

        SYSTEM_PROMPT --> FIRST_CALL["1️⃣ Primera llamada\nGemini 2.5 Flash\nSchema JSON con campo\ncadena_de_razonamiento primero"]

        FIRST_CALL --> COT_CHECK{"¿CoT\ncompletado?"}
        COT_CHECK -->|"No / inválido"| RETRY["🔄 Retry con feedback\nexplícito de la regla violada"]
        RETRY --> FIRST_CALL
        COT_CHECK -->|"Sí"| SELF_REFLECT

        SELF_REFLECT["2️⃣ Self-reflection pass\n'Actúa como revisor escéptico\nde tu propia respuesta'"]
        SELF_REFLECT --> VALIDATE{"¿Respuesta\nconsistente?"}
        VALIDATE -->|"No"| RETRY2["🔄 Retry semántico\ncon contraejemplo"]
        RETRY2 --> SELF_REFLECT
        VALIDATE -->|"Sí"| CONFIDENCE

        CONFIDENCE["3️⃣ Filtro de confianza\nCRITICAL requiere ≥ 0.7\nWARNING requiere ≥ 0.5"]
        CONFIDENCE --> FINDINGS["📋 findings[]\ntype, severity, title,\ndescription, recommendation,\nconfidence, evidence_quote"]
    end

    FINDINGS --> AGENT["AuditAgent\ncalculate_risk_score()\nupsert AuditResult"]
```

## Pipeline — Chatbot conversacional (DeepSeek / Gemini)

```mermaid
sequenceDiagram
    participant U as 👤 Analista
    participant BOT as chatbotBubble.js
    participant API as FastAPI
    participant DB as SQLite
    participant LLM as DeepSeek / Gemini

    U->>BOT: Pregunta libre o FAQ
    BOT->>API: POST /api/chatbot {query, profile_token}
    API->>API: Clasificar intención\n(top_risks / siniestro específico / taller / resumen)

    alt Pregunta sobre siniestro SIN-XXX
        API->>DB: SELECT findings, score WHERE siniestro_id=XXX\n+ WHERE profile_id=?
    else Top 10 riesgos
        API->>DB: SELECT TOP 10 ORDER BY risk_score DESC\n+ WHERE profile_id=?
    else Taller con más alertas
        API->>DB: GROUP BY workshop COUNT(CRITICAL findings)\n+ WHERE profile_id=?
    end

    DB-->>API: datos_estructurados{}
    API->>API: Construir prompt:\n"Datos: {datos}\nPregunta: {query}"

    alt DEEPSEEK_API_KEY disponible
        API->>LLM: POST api.deepseek.com/v1/chat/completions
    else GOOGLE_API_KEY disponible
        API->>LLM: google-genai gemini-2.5-flash
    else Sin claves
        API->>API: Formateador local → Markdown
    end

    LLM-->>API: respuesta_redactada
    API->>API: _safe_policy_text()\n(filtra lenguaje acusatorio)
    API-->>BOT: {response, disclaimer}
    BOT-->>U: Respuesta con disclaimer\n"requiere revisión humana"
```

## Señal S13 — Similitud de narrativas (SequenceMatcher)

```mermaid
flowchart LR
    NEW["Nueva descripción\ndel siniestro"] --> SM["difflib.SequenceMatcher\n.ratio()"]
    HIST["Historial de descripciones\nen la BD"] --> SM
    SM --> RATIO{Similitud\n≥ 75%?}
    RATIO -->|"Sí"| ALERT["⚠️ Señal S13 activada\n+8 puntos al fraud_score\nNarrativa posiblemente clonada"]
    RATIO -->|"No"| PASS["✅ Sin alerta S13"]
```
