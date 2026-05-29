# Diagrama — Plan Sofisticado de Implementación

> Fuente: [`docs/PLAN_SOFISTICADO_IMPLEMENTACION.md`](../PLAN_SOFISTICADO_IMPLEMENTACION.md)

## Hoja de ruta de implementación

```mermaid
gantt
    title Hoja de ruta — Auditor Agéntico Miraclex
    dateFormat YYYY-MM-DD
    section Fase 0 — Base
        Modelos SQLAlchemy (Siniestro, Poliza, Asegurado)   :done, f0a, 2026-05-01, 3d
        seed_data con datos sintéticos                       :done, f0b, 2026-05-03, 2d
        API REST básica (FastAPI)                           :done, f0c, 2026-05-04, 3d

    section Fase 1 — Motor de Reglas
        rules_engine.py (5 reglas base)                     :done, f1a, 2026-05-07, 4d
        Motor de scoring fraude (14 señales)                :done, f1b, 2026-05-10, 3d
        AuditAgent + upsert AuditResult                     :done, f1c, 2026-05-12, 2d

    section Fase 2 — IA Generativa
        DeepSeekAuditor (CoT + few-shot)                    :done, f2a, 2026-05-14, 4d
        Self-reflection pass + retry semántico              :done, f2b, 2026-05-17, 3d
        Chatbot DeepSeek                                    :done, f2c, 2026-05-19, 3d

    section Fase 3 — Frontend SPA
        Dashboard + KPIs                                    :done, f3a, 2026-05-20, 3d
        Upload drag-drop + generador SRI                    :done, f3b, 2026-05-22, 2d
        Detalle auditoría + acciones                        :done, f3c, 2026-05-23, 2d

    section Fase 4 — Seguridad
        Perfiles HMAC (ProfileScope)                        :done, f4a, 2026-05-24, 2d
        Aislamiento por profile_id en 7 tablas              :done, f4b, 2026-05-25, 1d

    section Fase 5 — Entregables
        Documentación técnica (docs/)                       :done, f5a, 2026-05-26, 1d
        Diagrama ER + stack.md + diagramas                  :active, f5b, 2026-05-27, 1d
```

## Arquitectura por fases de madurez

```mermaid
flowchart LR
    subgraph V1["v1 — MVP Básico"]
        V1A["FastAPI + SQLite\nCRUD siniestros\nSeed data"]
    end

    subgraph V2["v1.5 — Motor de Reglas"]
        V2A["5 reglas determinísticas\nrisk_score 0-100\nPDF interno"]
    end

    subgraph V3["v2.0 — IA Agéntica (actual)"]
        V3A["DeepSeek V4 Flash\nCoT + self-reflection\nChatbot DeepSeek\nPerfiles HMAC\nGenerador SRI Ecuador"]
    end

    subgraph FUTURE["v3.0 — Producción (roadmap)"]
        FA["Modelo ML\nentrenado con histórico"]
        FB["Embeddings semánticos\nnarrat. similares"]
        FC["JWT/OAuth\nautenticación real"]
        FD["PostgreSQL\nescalabilidad"]
    end

    V1 --> V2 --> V3 --> FUTURE
```

## Decisiones de arquitectura clave

```mermaid
mindmap
  root((Decisiones\nArquitecturales))
    SQLite elegido sobre PostgreSQL
      Prototipo single-node
      Sin infraestructura de BD
      Migración inline ALTER TABLE
      Suficiente para hackathon
    Vanilla JS sobre React/Vue
      Sin build step
      Sin node_modules en producción
      SPA hash-router propio
      Menor complejidad de despliegue
    Upsert en lugar de insert
      Evita duplicación de auditorías
      Un AuditResult por Invoice
      Re-auditar reemplaza, no duplica
    HMAC sin contraseña
      Demo sin backend de auth completo
      Aislamiento real de datos por perfil
      UUID v4 no adivinable
    Motor dual Reglas + IA
      Reglas: 1-2s, sin API key
      IA: 3-8s, más rico
      Mismo pipeline, diferente engine
      Intercambiables sin cambiar DB
```
