# Diagrama — Limitaciones y Consideraciones Éticas

> Fuente: [`docs/limitaciones.md`](../limitaciones.md)

## Mapa de limitaciones y mitigaciones

```mermaid
flowchart TD
    subgraph TEC["⚙️ Limitaciones Técnicas"]
        L1["📷 Calidad documental baja\nEscaneos de baja resolución\no documentos doblados"]
        L2["🔤 NLP sintáctico (S13)\nSequenceMatcher no detecta\nparáfrasis elaboradas\ncon sinónimos distintos"]
        L3["📐 Sin ML predictivo\nScore basado en reglas ponderadas\nno en modelo entrenado\ncon datos históricos etiquetados"]
    end

    subgraph MIT_TEC["✅ Mitigaciones actuales"]
        M1["Tolerancia del 10-15%\nsobre precios tarifario\npara evitar falsos positivos"]
        M2["Pendiente: embeddings semánticos\npara comparación vectorial\nde narrativas"]
        M3["Ventaja: explicabilidad 100%\nTransparente para el negocio\nsin caja negra"]
    end

    L1 --> M1
    L2 --> M2
    L3 --> M3

    subgraph FP["⚠️ Gestión de Falsos Positivos"]
        FP1["Precio dentro de tolerancia\n→ Hallazgo descartado\nautomáticamente"]
        FP2["Nombres comunes en S07\n(beneficiario recurrente)\n→ Riesgo de falsa alerta\nsin RUC / ID único"]
    end

    subgraph ETICA["🏛️ Principios Éticos"]
        E1["Alertas de revisión\nNo acusaciones automáticas\nLenguaje: 'posible riesgo'"]
        E2["Human-in-the-Loop obligatorio\nNingún pago bloqueado\nsin decisión humana"]
        E3["Privacidad LOPDP\nDatos 100% sintéticos\nEcuador"]
        E4["Palabras filtradas en LLM\nculpable / delito / estafa /\nacusado / sentencia"]
    end

    E1 & E2 & E3 & E4 --> HUMAN["👤 Analista como decisor final\n(Aprobar / Rechazar / Escalar)"]
```

## Comparativa: Reglas vs ML

```mermaid
graph TB
    subgraph COMPARATIVA["Comparativa: Reglas determinísticas vs ML"]
        REGLAS["✅ Reglas Ponderadas (ACTUAL)\n• Interpretabilidad: ALTA (100%)\n• Auto-aprendizaje: NO\n• Explicable al negocio: SÍ\n• Sesgo por datos: NO"]
        ML["⚙️ ML Supervisado (FUTURO)\n• Interpretabilidad: BAJA\n• Auto-aprendizaje: SÍ\n• Requiere datos históricos etiquetados\n• Riesgo de caja negra"]
        EMBED["🎯 Objetivo: Híbrido con Embeddings\n• Reglas + similitud semántica\n• Interpretabilidad: MEDIA-ALTA\n• Detecta paráfrasis elaboradas"]
    end

    REGLAS -->|"evolución"| EMBED
    ML -->|"combinar"| EMBED
```

## Ciclo de revisión humana (Human-in-the-Loop)

```mermaid
flowchart LR
    SISTEMA["🤖 Sistema\nGenera alerta\nrisk_score 0-100"] -->|"Alerta de posible riesgo"| ANALISTA

    ANALISTA["👤 Analista\nUnidad Antifraude"]
    ANALISTA --> REVIEW["Revisar hallazgos\ney evidencias"]
    REVIEW --> DECISION{Decisión}

    DECISION -->|"Aprobar"| FLUJO_NORMAL["✅ Flujo liquidación\nnormal"]
    DECISION -->|"Rechazar"| NOTIF_TALLER["❌ Notificación formal\nal taller (PDF)"]
    DECISION -->|"Escalar"| INSPECCION["🔍 Inspección física\nespecializada"]
    DECISION -->|"Re-auditar"| SISTEMA
```
