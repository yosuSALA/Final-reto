# Diagrama — Uso de Inteligencia Artificial

> Fuente: [`docs/uso_ia.md`](../uso_ia.md)

## Mapa de componentes IA

```mermaid
mindmap
  root((IA en Miraclex))
    DeepSeek V4 Flash
      Auditoria de facturas
        Chain-of-Thought forzado
        Few-shot calibration
        Self-reflection pass
        Validacion semantica + retry
        Filtro defensivo sobrecobro
      Chatbot conversacional
        Inferencia SQL local
        Contextualizacion de prompts
        Respuesta ejecutiva
    DeepSeek Chat (fallback directo)
      Alternativa sin OpenCode Go
    SequenceMatcher stdlib
      Senial S13
        Similitud caracteres
        Umbral 75%
        Deteccion narrativas clonadas
    Formateador local
      Fallback tecnico
        Sin API key
        Datos SQL en Markdown
```

## Pipeline — Auditoria cognitiva de facturas (DeepSeek)

```mermaid
flowchart TD
    INPUT["Factura PDF procesada\n(items, montos, RUC, tipo siniestro)"] --> SYSTEM_PROMPT

    subgraph DS_PIPELINE["DeepSeekAuditor — deepseek_auditor.py"]
        SYSTEM_PROMPT["System Prompt\nFew-shot: 1 factura limpia\nFew-shot: 1 factura con fraude\nInstrucciones de analisis"]

        SYSTEM_PROMPT --> FIRST_CALL["1 Primera llamada\nDeepSeek V4 Flash\nSchema JSON con campo\ncadena_de_razonamiento primero"]

        FIRST_CALL --> COT_CHECK{"CoT\ncompletado?"}
        COT_CHECK -->|"No / invalido"| RETRY["Retry con feedback\nexplicito de la regla violada"]
        RETRY --> FIRST_CALL
        COT_CHECK -->|"Si"| SELF_REFLECT

        SELF_REFLECT["2 Self-reflection pass\n'Actua como revisor esceptico\nde tu propia respuesta'"]
        SELF_REFLECT --> VALIDATE{"Respuesta\nconsistente?"}
        VALIDATE -->|"No"| RETRY2["Retry semantico\ncon contraejemplo"]
        RETRY2 --> SELF_REFLECT
        VALIDATE -->|"Si"| CONFIDENCE

        CONFIDENCE["3 Filtro de confianza\nCRITICAL requiere >= 0.7\nWARNING requiere >= 0.5"]
        CONFIDENCE --> FINDINGS["findings[]\ntype, severity, title,\ndescription, recommendation,\nconfidence, evidence_quote"]
    end

    FINDINGS --> AGENT["AuditAgent\ncalculate_risk_score()\nupsert AuditResult"]
```

## Pipeline — Chatbot conversacional (DeepSeek)

```mermaid
sequenceDiagram
    participant U as Analista
    participant BOT as chatbotBubble.js
    participant API as FastAPI
    participant DB as SQLite
    participant LLM as DeepSeek V4 Flash

    U->>BOT: Pregunta libre o FAQ
    BOT->>API: POST /api/chatbot {query, profile_token}
    API->>API: Clasificar intencion\n(top_risks / siniestro / taller / resumen)

    alt Pregunta sobre siniestro SIN-XXX
        API->>DB: SELECT findings, score WHERE siniestro_id=XXX
    else Top 10 riesgos
        API->>DB: SELECT TOP 10 ORDER BY risk_score DESC
    else Taller con mas alertas
        API->>DB: GROUP BY workshop COUNT(CRITICAL findings)
    end

    DB-->>API: datos_estructurados{}
    API->>API: Construir prompt:\n"Datos: {datos}\nPregunta: {query}"

    alt OPENCODE_GO_API_KEY disponible
        API->>LLM: OpenCode Go Gateway\ndeepseek-v4-flash
    else Sin claves
        API->>API: Formateador local -> Markdown
    end

    LLM-->>API: respuesta_redactada
    API->>API: _safe_policy_text()\n(filtra lenguaje acusatorio)
    API-->>BOT: {response, disclaimer}
    BOT-->>U: Respuesta con disclaimer\n"requiere revision humana"
```

## Senial S13 — Similitud de narrativas (SequenceMatcher)

```mermaid
flowchart LR
    NEW["Nueva descripcion\ndel siniestro"] --> SM["difflib.SequenceMatcher\n.ratio()"]
    HIST["Historial de descripciones\nen la BD"] --> SM
    SM --> RATIO{Similitud\n>= 75%?}
    RATIO -->|"Si"| ALERT["Senial S13 activada\n+8 puntos al fraud_score\nNarrativa posiblemente clonada"]
    RATIO -->|"No"| PASS["Sin alerta S13"]
```
