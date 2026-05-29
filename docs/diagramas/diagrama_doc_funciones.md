# Diagrama — Funciones del Sistema (DOC_FUNCIONES)

> Fuente: [`docs/DOC_FUNCIONES.md`](../DOC_FUNCIONES.md)

## Mapa de funciones principales

```mermaid
mindmap
  root((Auditor Agéntico\nMiraclex))
    Dashboard
      KPIs en tiempo real
        Total auditadas
        Monto facturado
        Sobrecobro detectado
        Ahorro estimado
      Gráficos
        Scatter siniestros diarios
        Donut severidad
      Toggle TEST
    Gestión de Auditorías
      Pendientes
        Cola de facturas sin auditar
        Auditoría JIT
      Revisadas
        Historial con badge motor
        Búsqueda y filtros
    Detalle de Auditoría
      Re-auditoría sin duplicación
        Upsert AuditResult
        Borra findings anteriores
      Acciones manuales
        Aprobar
        Rechazar
        Escalar
      Reportes PDF
        Reporte Interno
        Notificación Taller
    Motor de Reglas
      PriceOverchargeRule
      DuplicateChargeRule
      QuantityAnomalyRule
      IncoherenceRule
      InvoiceResubmissionRule
    Motor IA DeepSeek
      Chain-of-Thought
      Few-shot calibration
      Evidence citation
      Confidence calibration
      Semantic validation
      Self-reflection pass
      Mock mode sin API key
    Tarifario Maestro
      Vista por categorías
      Modificar precio máximo
      Añadir tarifario manual
      Eliminar por fila
    Vista 360° Siniestro
      Siniestro + facturas asociadas
      Detección re-facturación
    Generador Random SRI
      Limpia
      Sobrecobro
      Fraude
      Aleatorio
    Garantías No Duplicación
      UniqueConstraint DB
      Upsert backend
      Flag uploadInFlight frontend
```

## Calibración del Motor de Reglas

```mermaid
flowchart LR
    ITEM["📦 Ítem de factura"] --> COMPARE["Comparar vs tarifario\nprecio unitario / cantidad / tipo"]

    COMPARE --> EXCESO{Exceso sobre\ntolerancia}
    EXCESO -->|"≤ tolerancia (10-15%)"| INFO["ℹ️ INFO\nHallazgo descartado\no informativo"]
    EXCESO -->|"tolerancia < exceso ≤ 30%"| WARNING["⚠️ WARNING\nSobrecobro moderado"]
    EXCESO -->|"exceso > 30%"| CRITICAL["🔴 CRITICAL\nSobrecobro grave"]

    subgraph RULES_TYPES["Tipos de regla"]
        R1["PriceOverchargeRule\nprecio > máx_tarifario + tolerancia"]
        R2["DuplicateChargeRule\nmismo código 2+ veces en factura"]
        R3["QuantityAnomalyRule\ncantidad fuera de rango min/max"]
        R4["IncoherenceRule\nítem no aplica al tipo de siniestro"]
        R5["InvoiceResubmissionRule\nnúmero factura ya en otro siniestro"]
    end

    subgraph SCORE_CALC["Cálculo de risk_score"]
        SC1["CRITICAL × 35 pts"]
        SC2["WARNING × 20 pts"]
        SC3["INFO × 5 pts"]
        SC4["Cap: 100 pts"]
        SC1 & SC2 & SC3 --> SC4
    end
```

## Garantías de no-duplicación (3 niveles)

```mermaid
flowchart TD
    UPLOAD["📤 Upload de factura PDF"] --> DB_CHECK

    subgraph NIVEL1["Nivel 1 — Base de datos"]
        DB_CHECK["UniqueConstraint\n(invoice_number, workshop_id)"]
        DB_CHECK -->|"Duplicado"| DB_REJECT["IntegrityError\n→ Retornar factura existente"]
        DB_CHECK -->|"Nueva"| BACKEND_CHECK
    end

    subgraph NIVEL2["Nivel 2 — Backend upsert"]
        BACKEND_CHECK["audit_invoice() / _save_ai_result()\n¿Existe AuditResult para invoice?"]
        BACKEND_CHECK -->|"Sí"| UPDATE["UPDATE AuditResult\nDELETE findings anteriores\nINSERT findings nuevos"]
        BACKEND_CHECK -->|"No"| INSERT["INSERT AuditResult\nINSERT findings"]
    end

    subgraph NIVEL3["Nivel 3 — Frontend"]
        FE_CHECK["Flag uploadInFlight\nen upload.js"]
        FE_CHECK -->|"true (en vuelo)"| FE_BLOCK["Bloquear nuevo upload\ndel mismo archivo"]
        FE_CHECK -->|"false"| FE_ALLOW["Permitir upload\nsetFlag(true)"]
    end

    UPDATE & INSERT --> FE_CHECK
    UPLOAD --> FE_CHECK
```
