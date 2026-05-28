# Diagrama — Matriz de Cumplimiento del Reto

> Fuente: [`docs/MATRIZ_CUMPLIMIENTO_RETO.md`](../MATRIZ_CUMPLIMIENTO_RETO.md)

## Estado de cumplimiento por categoría

```mermaid
pie title Cumplimiento general (estimado 62%)
    "CUMPLE" : 18
    "PARCIAL" : 9
    "NO CUMPLE" : 14
```

## Heatmap de cumplimiento por sección

```mermaid
xychart-beta
    title "Estado por sección del reto (CUMPLE=3, PARCIAL=2, NO CUMPLE=1)"
    x-axis ["Datos Mínimos", "Reglas Negocio", "Score Riesgo", "Funcionalidades", "Agente IA", "Seguridad/Ética", "Entregables"]
    y-axis "Promedio de cumplimiento" 0 --> 3
    bar [1.5, 1.2, 2.0, 2.6, 2.8, 3.0, 2.4]
```

## Prioridades de corrección (P0 → P2)

```mermaid
flowchart TD
    subgraph P0["🔴 P0 — Bloquea demo (corregir YA)"]
        P0A["Crear modelo Poliza\n(fecha_inicio, fecha_fin,\nsuma_asegurada, deducible)"]
        P0B["Crear modelo Asegurado\n(id, identificacion, historial)"]
        P0C["Implementar 7 RF críticas\ncomo reglas excluyentes"]
        P0D["Mecanismo score=100\nsi alguna RF es CRITICAL"]
        P0E["Poblar seed_data\ncon todos los campos de fraude"]
    end

    subgraph P1["🟡 P1 — Importante para puntaje"]
        P1A["Ajustar rangos semáforo\nVerde 0-40 / Amarillo 41-75 / Rojo 76-100"]
        P1B["ReportingDelayRule\nHighClaimFrequencyRule\nVehicleFrequencyRule"]
        P1C["Refinar IncoherenceRule\ncon cobertura específica"]
        P1D["Campo restricted/risk_level\nen Workshop"]
        P1E["Crear docs/ARQUITECTURA.md\ncon diagrama formal"]
        P1F["Presentación ejecutiva\ncon pitch para jurado"]
    end

    subgraph P2["🟢 P2 — Mejoras de robustez"]
        P2A["Widget Top 10 Riesgos\nen dashboard"]
        P2B["NLP semántico para\nnarrativas similares"]
        P2C["Verificación módulo 11\nclave SRI"]
        P2D["Respuestas chatbot\ndiferenciadas por perfil"]
        P2E["Diagrama ER en\ndocs/MODELO_DATOS.md"]
    end

    P0 --> P1 --> P2
```

## Top 10 hallazgos críticos

```mermaid
flowchart LR
    subgraph ALTO["🔴 Impacto ALTO"]
        H1["#1 Falta modelo Poliza\n(bloquea RF-01, RF-05, S01, S14)"]
        H2["#2 Falta modelo Asegurado\n(bloquea frecuencia histórica S03)"]
        H3["#3 7 RF críticas no implementadas"]
        H4["#4 Falta tabla Documentos"]
    end

    subgraph MEDIO["🟡 Impacto MEDIO"]
        H5["#5 Rangos score incorrectos\n(0-29/30-69/70-100 en lugar de 0-40/41-75/76-100)"]
        H6["#6 Sin reglas excluyentes\n(score siempre lineal)"]
        H7["#7 IncoherenceRule demasiado genérica"]
        H8["#8 Seed data no puebla campos de fraude"]
        H9["#9 Sin presentación ejecutiva\npara jurado"]
    end

    subgraph BAJO["🟢 Impacto BAJO"]
        H10["#10 Dashboard sin Top 10 Riesgos\n(solo en chatbot)"]
    end
```
