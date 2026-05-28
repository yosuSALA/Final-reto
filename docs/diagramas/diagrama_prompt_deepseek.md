# Diagrama — Prompt DeepSeek P0 Final

> Fuente: [`docs/PROMPT_DEEPSEEK_P0_FINAL.md`](../PROMPT_DEEPSEEK_P0_FINAL.md)

## Estructura del prompt de revisión P0

```mermaid
flowchart TD
    subgraph PROMPT_STRUCT["Estructura del Prompt P0"]
        ROLE["🎭 Rol del agente:\nRevisor de código estricto\npara hackathon HackIAthon 2026"]

        CONTEXT["📋 Contexto inyectado:\n• Código fuente backend/\n• Código fuente frontend/\n• Documentación docs/\n• Matriz de cumplimiento del reto"]

        TASK["🎯 Tarea:\nRevisar TODOS los requisitos del PDF del reto\ny emitir veredicto binario por ítem"]

        OUTPUT_FORMAT["📤 Formato de salida:\nTabla Markdown estructurada:\n| Requisito | Estado | Evidencia | Gap | Corrección |"]

        CONSTRAINTS["⛔ Restricciones:\n• Solo hallazgos verificables\n• Evidencia = archivo:línea\n• No usar lenguaje general\n• Si no cumple: proponer cambio exacto"]
    end

    ROLE --> CONTEXT --> TASK --> OUTPUT_FORMAT --> CONSTRAINTS
    CONSTRAINTS --> DEEPSEEK["DeepSeek v4 Flash\n(via OpenCode Go)"]
    DEEPSEEK --> MATRIZ["MATRIZ_CUMPLIMIENTO_RETO.md\n+ Hallazgos críticos P0/P1/P2"]
```

## Clasificación de requisitos evaluados

```mermaid
flowchart LR
    subgraph CATEGORIES["Categorías evaluadas en el prompt P0"]
        C1["1️⃣ Datos Mínimos\n(modelos, tablas, campos)"]
        C2["2️⃣ Reglas de Negocio\n(14 señales + 7 RF)"]
        C3["3️⃣ Score de Riesgo\n(rangos, clasificación)"]
        C4["4️⃣ Funcionalidades\n(prototipo funcional)"]
        C5["5️⃣ Agente IA\n(chatbot, FAQs)"]
        C6["6️⃣ Seguridad/Ética\n(datos sintéticos, sin credenciales)"]
        C7["7️⃣ Entregables\n(README, código, dataset)"]
    end

    subgraph STATES["Estados posibles"]
        S1["✅ CUMPLE\nRequisito satisfecho con evidencia"]
        S2["⚠️ PARCIAL\nImplementado pero incompleto\no con gaps"]
        S3["❌ NO CUMPLE\nNo implementado o faltante"]
    end

    C1 & C2 & C3 & C4 & C5 & C6 & C7 --> DEEPSEEK["DeepSeek\nAsigna estado + evidencia"]
    DEEPSEEK --> S1 & S2 & S3
```

## Priorización P0 resultante del prompt

```mermaid
flowchart TD
    subgraph P0_RESULT["Hallazgos P0 identificados por DeepSeek"]
        R1["❌ Modelo Poliza faltante\nBloquea 4 señales + 2 RF"]
        R2["❌ Modelo Asegurado faltante\nBloquea frecuencia histórica"]
        R3["❌ 7 RF críticas sin implementar"]
        R4["❌ Sin reglas excluyentes\n(score=100 automático)"]
        R5["❌ seed_data sin campos de fraude"]
    end

    subgraph P0_ACTIONS["Acciones P0 propuestas"]
        A1["backend/models.py:\nclass Poliza con 8 campos"]
        A2["backend/models.py:\nclass Asegurado con historial"]
        A3["backend/rules_engine.py:\nRF01-RF07 como reglas excluyentes"]
        A4["backend/rules_engine.py:\nif any_RF_critical: score = 100"]
        A5["backend/seed_data.py:\nPoblar todos los campos Siniestro"]
    end

    R1 --> A1
    R2 --> A2
    R3 --> A3
    R4 --> A4
    R5 --> A5
```
