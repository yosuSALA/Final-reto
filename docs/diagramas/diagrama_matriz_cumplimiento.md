# Diagrama — Matriz de Cumplimiento

> Fuente: [`docs/MATRIZ_CUMPLIMIENTO_RETO.md`](../MATRIZ_CUMPLIMIENTO_RETO.md)

## Estado final por categoría

```mermaid
pie title Cumplimiento demo funcional
    "Cumple" : 12
    "Riesgo residual documentado" : 2
```

## Capacidades verificables

```mermaid
flowchart TD
    A[Arranque portable] --> B[Frontend SPA]
    B --> C[Generador manual de PDFs]
    B --> D[Expediente automático con IA]
    C --> E[Resolución automática por SIN]
    D --> F[Auditoría DeepSeek]
    E --> F
    F --> G[Fallback reglas si API falla]
    F --> H[Detalle y reportes]
    H --> I[Decisión humana]
```

## Riesgos residuales

```mermaid
flowchart LR
    R1[API key requerida para IA real] --> M1[Fallback de reglas]
    R2[Sin OCR de imágenes] --> M2[Alcance limitado a PDFs]
```
