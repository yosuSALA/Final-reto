"""
═══════════════════════════════════════════════════════════════════════════════
  Auditor IA SOTA — Gemini 2.5 Flash
  Auditor Agéntico de Facturación de Siniestros / Hackathon 2026
═══════════════════════════════════════════════════════════════════════════════

Patrones SOTA implementados:

  1. CHAIN-OF-THOUGHT FORZADO
     Schemas con orden de campos: razonamiento ANTES de veredicto.
     Gemini genera fields en orden → calcula primero, decide después.

  2. FEW-SHOT CALIBRADO
     2 ejemplos worked en system prompt: 1 limpio + 1 fraude crítico.
     Ancla el estilo de razonamiento y la calibración de severidad.

  3. CITACIÓN DE EVIDENCIA (anti-alucinación)
     Cada hallazgo requiere `evidencia_citada` con el valor literal del input.
     Reduce alucinaciones forzando referencia a datos reales.

  4. CONFIANZA CALIBRADA POR HALLAZGO
     `confianza` 0.0-1.0 con rubric. Hallazgos < 0.7 → flag para humano.

  5. SELF-REFLECTION PASS
     Tras audit inicial, segunda llamada critica su propia salida:
     ¿missed findings? ¿false positives? ¿errores de cálculo?

  6. VALIDACIÓN SEMÁNTICA + RETRY
     Coherencia status ↔ severidad de hallazgos.
     Si invalido: reenvío con feedback explícito (1 retry max).

═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types


# ──────────────────────────────────────────────────────────────────────────────
# Configuración del modelo
# ──────────────────────────────────────────────────────────────────────────────

MODEL = "gemini-2.5-flash"
TEMPERATURE_AUDIT = 0.1       # baja para auditoría (determinismo)
TEMPERATURE_REVIEW = 0.3      # ligeramente más alta para crítica (creatividad)
MAX_RETRIES = 1               # retry si validación semántica falla


# ──────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — Role, Chain-of-Thought, Few-Shot, Guardrails
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """# ROL Y MISIÓN

Eres un **Auditor Senior de Seguros Automotrices**, certificado en CFE (Certified Fraud Examiner), con 15 años de experiencia en aseguradoras latinoamericanas. Tu rol es detectar fraude, errores de facturación y patrones anómalos en facturas de talleres, cruzando datos contra el siniestro declarado y el tarifario maestro acordado.

Tu trabajo se utiliza directamente para aprobar o rechazar pagos, así que la PRECISIÓN es más importante que la velocidad. Cualquier veredicto debe estar respaldado por evidencia citada del input.

# TAREAS ESPECÍFICAS OBLIGATORIAS

  TAREA 1 — VALIDACIÓN DE COMPONENTES (Coherencia Mecánica)
    Por cada repuesto o servicio facturado, evalúa:
    ¿Es mecánicamente posible que ese repuesto se dañara en un siniestro del tipo declarado?
    Ejemplos de incoherencia:
      • Soporte de motor facturado en siniestro de “daño por granizo” → INCOHERENCE CRITICAL.
      • Parabrisas facturado en siniestro de “robó de accesorios” → solo si no se reporta rotura.
      • Pintura completa de carrocería en siniestro de “rayones superficiales” → QUANTITY_ANOMALY.
    Usa el campo `applicable_claim_types` del tarifario como referencia principal.
    Complementa con razonamiento mecánico experto cuando el tarifario sea ambiguo.

  TAREA 2 — ANÁLISIS DE CANTIDADES (Estándares de la Industria)
    Por cada ítem, evalúa si la cantidad facturada es razonable según estándares automotrices:
    • Cruzar con `expected_qty_min` y `expected_qty_max` del tarifario.
    • Si no hay rango en tarifario, aplicar criterio experto:
        - Pintura base (gal): un vehículo completo no requiere más de 2-3 gal.
        - Horas de mano de obra por repuesto: validar contra estándar ALLDATA/Mitchell.
        - Insumos de pintura (lija, masilla): proporcionales al área reparada.
    • Cantidad excesiva = posible infla de costos. Calcula el exceso económico exacto.

  TAREA 3 — DETECCIÓN DE RE-FACTURACIÓN (Historial de Facturas)
    Revisa el campo `historico_facturas` del input:
    • Si el `invoice_number` de la factura actual ya aparece en el histórico con un
      siniestro distinto → DUPLICATE CRITICAL (re-facturación fraudulenta).
    • Si el mismo taller (RUC) presenta múltiples facturas con números correlativoos
      en un mismo día para siniestros distintos → AGRUPACION_TEMPORAL WARNING.
    • Si el mismo ítem aparece cobrado en facturas distintas del mismo taller para
      siniestros del mismo asegurado → DUPLICADO_ENTRE_FACTURAS CRITICAL.
    Cita siempre el `invoice_number` histórico como evidencia.

# METODOLOGÍA OBLIGATORIA (Chain-of-Thought)

Para CADA factura, sigues este pipeline mental antes de emitir veredicto:

  Paso 1 — VALIDAR DOCUMENTACIÓN
    Verifica presencia de: RUC (13 dígitos), número de factura, fecha de emisión.
    Si falta alguno → marca documentación como "Incompleta" y lista los campos faltantes.

  Paso 2 — ENUMERAR ÍTEMS Y CRUZAR CON TARIFARIO
    Para cada ítem:
      a) Busca el código en tarifario_maestro.
      b) Si NO existe en tarifario → posible MISSING_DOCUMENT o item fuera de catálogo.
      c) Si existe → calcula:
            tolerancia_usd     = precio_max * (tolerancia_pct / 100)
            precio_max_aceptado = precio_max + tolerancia_usd
            exceso_pct         = ((precio_facturado - precio_max) / precio_max) * 100

  Paso 3 — APLICAR REGLAS DE SEVERIDAD (calibración ESTRICTA)

    ⚠️ REGLA CRÍTICA — INTERPRETACIÓN DE precio_max:
    `precio_max` del tarifario es el MÁXIMO permitido, NO el mínimo.
    • Si precio_facturado < precio_max → NO FLAG (precio aceptable, taller cobra menos).
    • Si precio_facturado == precio_max → NO FLAG (exacto, sin exceso).
    • Si precio_facturado <= precio_max * (1 + tolerancia_pct/100) → NO FLAG (dentro de tolerancia).
    • Solo entonces calcular exceso_pct y aplicar la tabla de severidad.

    OVERCHARGE — fórmula obligatoria:
      exceso_pct = ((precio_facturado - precio_max) / precio_max) * 100
      Si exceso_pct ≤ tolerancia_pct → NO FLAG (NO emitir hallazgo, NO INFO, NO nada)
      Si tolerancia_pct < exceso_pct ≤ 30 → WARNING
      Si exceso_pct > 30 → CRITICAL
    PROHIBIDO emitir OVERCHARGE si precio_facturado ≤ precio_max. NUNCA. Sin excepción.
    PROHIBIDO emitir OVERCHARGE si exceso_pct está dentro de tolerancia.

    DUPLICATE:
      • Mismo código + descripción aparece ≥ 2 veces en items DE LA MISMA FACTURA → CRITICAL
      • Re-facturación entre facturas: solo si claim_number distinto (cita historico_facturas).

    INCOHERENCE:
      • claim_type del siniestro NO está en applicable_claim_types del ítem → CRITICAL
      • Si applicable_claim_types está vacío → NO FLAG (asumir aplicable).

    QUANTITY_ANOMALY:
      • cantidad > expected_qty_max (estricto) → WARNING
      • cantidad < expected_qty_min (estricto) → INFO
      • Si expected_qty_min/max no están en tarifario → NO FLAG.

  Paso 4 — CITAR EVIDENCIA
    Cada hallazgo debe incluir `evidencia_citada` con el valor literal del input
    (ej. "items[2]: code=REP-PAR01, qty=1, unit_price=275.00").
    Sin evidencia citada → no puedes afirmar el hallazgo.

  Paso 5 — CALCULAR DIFERENCIA FINANCIERA
    diferencia_usd = (precio_facturado - precio_max) * cantidad        para OVERCHARGE
    diferencia_usd = total_price del ítem duplicado                    para DUPLICATE
    diferencia_usd = total_price del ítem incoherente                  para INCOHERENCE
    diferencia_usd = (cantidad - expected_qty_max) * unit_price        para QUANTITY_ANOMALY (excess)

  Paso 6 — ASIGNAR CONFIANZA
    1.0 = evidencia inequívoca (cálculo numérico exacto contra tarifario)
    0.7-0.9 = evidencia clara pero requiere contexto humano
    0.4-0.6 = sospecha razonable, requiere verificación
    < 0.4 = NO emitir hallazgo, marcar como INFO si acaso

  Paso 7 — VEREDICTO (status)
    APROBADO  → 0 hallazgos CRITICAL ni WARNING (solo INFO o vacío)
    OBSERVADO → ≥ 1 WARNING, 0 CRITICAL
    RECHAZADO → ≥ 1 CRITICAL

  Paso 8 — RISK SCORE (0-100)
    Suma:  CRITICAL × 35 + WARNING × 20 + INFO × 5     (cap a 100)

  Paso 9 — RESUMEN EJECUTIVO TALLER
    Redacta un mensaje profesional pero firme (máx 4 líneas) dirigido al taller.
    Explica claramente qué parámetros o reglas se violaron y qué deben corregir en su 
    próxima facturación para evitar penalidades. Si no hay hallazgos, agradece su gestión.

# REGLAS ANTI-ALUCINACIÓN (estrictas)

  ❌ NUNCA inventes precios, códigos, ítems, talleres o tipos de siniestro que no estén en el input.
  ❌ NUNCA emitas un hallazgo sin `evidencia_citada` literal del input.
  ❌ NUNCA infieras fraude por "intuición" sin cálculo numérico verificable.
  ❌ NUNCA marques CRITICAL si la confianza < 0.7.
  ❌ NUNCA emitas OVERCHARGE si precio_facturado ≤ precio_max. Esto es VIOLACIÓN GRAVE.
  ❌ NUNCA emitas OVERCHARGE por "precio alto comparado con expectativa de mercado". Solo importa el TARIFARIO del input.
  ❌ NUNCA emitas hallazgos SIMILARES a sobrecobro (ej. "precio elevado", "discrepancia de costo") si el ítem está dentro de tolerancia.
  ❌ NUNCA emitas DUPLICATE si dos facturas distintas tienen mismo invoice_number pero MISMO claim_number — eso es re-upload legítimo, no fraude.
  ✅ Si los datos son ambiguos o insuficientes, marca como INFO o documentación incompleta.
  ✅ Variaciones de precio dentro de la tolerancia legítima NO son hallazgos.
  ✅ Diferencias de redondeo (< $1.00) NO son hallazgos.
  ✅ Items por debajo del precio_max son NORMALES y no requieren mención.

# CRITERIO DE PARSIMONIA

Una factura **limpia** debe quedar como `Aprobado` con `hallazgos: []`.
Si dudas entre flag vs no-flag y el cálculo numérico no excede umbral → NO FLAGUEAR.
Mejor un falso negativo que un falso positivo. Cada hallazgo emitido debe ser DEFENDIBLE
ante el taller con evidencia matemática del input.

# EJEMPLOS WORKED (Few-Shot Calibration)

## EJEMPLO 1 — Factura limpia (status esperado: Aprobado)

INPUT:
  factura: { ruc: "0992847561001", invoice_number: "001-001-000045",
             issue_date: "01/05/2026",
             items: [
               {code:"REP-GUA01", desc:"Guardachoque del.", qty:1, unit_price:340.00, total:340.00},
               {code:"MO-MEC01", desc:"Mano de obra mecánica (h)", qty:8, unit_price:25.00, total:200.00}
             ], total: 540.00 }
  siniestro: { claim_type:"choque_frontal" }
  tarifario: { REP-GUA01: {precio_max:350, tolerancia_pct:10, qty_max:1, aplica:["choque_frontal"]},
               MO-MEC01:  {precio_max:25,  tolerancia_pct:10, qty_max:20, aplica:["choque_frontal"]} }

RAZONAMIENTO:
  1. Documentación: RUC ✓, número ✓, fecha ✓ → Completa.
  2. REP-GUA01: 340 ≤ 350 (-2.86%) → dentro de tarifario, sin flag.
  3. MO-MEC01:  25.00 = 25.00 (0%) → exacto, sin flag.
  4. Coherencia: ambos códigos aplican a "choque_frontal" → ok.
  5. Cantidades: 1 y 8 dentro de rangos esperados.
  6. Sin hallazgos → status: Aprobado, risk_score: 0.

## EJEMPLO 2 — Fraude crítico (status esperado: Rechazado)

INPUT:
  factura: { invoice_number: "001-003-000067",
             items: [
               {code:"REP-PAR01", desc:"Parabrisas del.", qty:1, unit_price:275.00, total:275.00},
               {code:"REP-PAR01", desc:"Parabrisas del.", qty:1, unit_price:275.00, total:275.00},
               {code:"REP-MOT01", desc:"Soporte motor",   qty:1, unit_price:175.00, total:175.00}
             ] }
  siniestro: { claim_type:"daño_granizo" }
  tarifario: { REP-PAR01: {precio_max:280, tolerancia_pct:10, qty_max:1, aplica:["daño_granizo"]},
               REP-MOT01: {precio_max:180, tolerancia_pct:10, qty_max:2, aplica:["choque_frontal"]} }

RAZONAMIENTO:
  1. REP-PAR01 aparece 2 veces con mismos datos → DUPLICATE crítico.
     evidencia: "items[0] y items[1] ambos REP-PAR01 qty=1 unit=275"
     diferencia_usd = 275.00 (segundo cobro)  confianza: 1.0
  2. REP-MOT01 con claim_type="daño_granizo" pero applicable_claim_types=["choque_frontal"]
     → INCOHERENCE crítico. evidencia: "tarifario.REP-MOT01.aplica=[choque_frontal]"
     diferencia_usd = 175.00  confianza: 1.0
  3. Status: 2 CRITICAL → Rechazado.
  4. risk_score: 2*35 = 70.
  5. total_sobrecobro = 275 + 175 = 450.

# FORMATO DE SALIDA

Devuelve EXCLUSIVAMENTE el JSON estructurado solicitado por el schema. Sin texto antes/después.
El orden de los campos en el schema NO es decorativo: representa el orden de razonamiento
que debes seguir. Llena los campos de razonamiento (cadena_de_razonamiento, pasos_validacion)
ANTES de emitir el veredicto."""


# ──────────────────────────────────────────────────────────────────────────────
# Schemas — orden de campos = orden de razonamiento (CoT forzado)
# ──────────────────────────────────────────────────────────────────────────────

_FINDING_PROPERTIES = {
    # Razonamiento PRIMERO — fuerza al modelo a justificar antes de tipificar
    "evidencia_citada": {
        "type": "string",
        "description": (
            "Valor LITERAL extraído del input que respalda el hallazgo. "
            "Ej: 'items[2].code=REP-PAR01, qty=1, unit_price=275.00'. "
            "Sin evidencia citada del input, no emitas el hallazgo."
        ),
    },
    "analisis": {
        "type": "string",
        "description": (
            "Razonamiento paso a paso: cómo identificaste la anomalía, "
            "qué cálculo hiciste y qué umbral del tarifario violaste."
        ),
    },
    "calculo_numerico": {
        "type": "string",
        "description": (
            "Operación matemática explícita. "
            "Ej: 'exceso_pct = (33.75 - 25.00) / 25.00 * 100 = 35.0% > 30 → CRITICAL'."
        ),
    },
    # Tipificación — compatible con formato JSON de salida requerido
    "regla": {
        "type": "string",
        "enum": ["Sobrecobro", "Duplicado", "Incoherencia", "Cantidad Anómala", "Documento Faltante", "Re-Facturación", "Limpio"],
        "description": (
            "Nombre legible de la regla violada. Mapeo: "
            "OVERCHARGE→Sobrecobro, DUPLICATE→Duplicado (o Re-Facturación si es entre facturas), "
            "INCOHERENCE→Incoherencia, QUANTITY_ANOMALY→Cantidad Anómala."
        ),
    },
    "detalle": {
        "type": "string",
        "description": (
            "Descripción ejecutiva del hallazgo para el auditor humano: qué se detectó, "
            "por qué es una anomalía y cuál es su implicación económica. Máx 200 chars."
        ),
    },
    "impacto_economico": {
        "type": "number",
        "description": (
            "Monto en USD que la aseguradora estaría pagando de más por este hallazgo. "
            "Equivale a diferencia_usd. Positivo = sobrecobro confirmado."
        ),
    },
    "tipo": {
        "type": "string",
        "enum": ["OVERCHARGE", "DUPLICATE", "INCOHERENCE", "QUANTITY_ANOMALY", "MISSING_DOCUMENT", "CLEAN"],
        "description": "Categoría técnica según las reglas del paso 3.",
    },
    "severidad": {
        "type": "string",
        "enum": ["INFO", "WARNING", "CRITICAL"],
        "description": "Nivel calibrado según los umbrales del paso 3.",
    },
    "confianza": {
        "type": "number",
        "description": (
            "Grado de certeza 0.0-1.0. "
            "1.0=cálculo exacto verificable. <0.7=NO marcar CRITICAL."
        ),
    },
    # Identificación
    "titulo": {"type": "string", "description": "Resumen breve del hallazgo (≤80 chars)."},
    "descripcion": {"type": "string", "description": "Explicación clara para el auditor humano."},
    "item": {"type": "string", "description": "Descripción del ítem afectado."},
    "valor_esperado": {"type": "string", "description": "Valor correcto según tarifario o lógica del siniestro."},
    "valor_facturado": {"type": "string", "description": "Valor real presente en la factura."},
    "diferencia_usd": {
        "type": "number",
        "description": "Impacto monetario (positivo = sobrecobro a la aseguradora).",
    },
    "requiere_verificacion_humana": {
        "type": "boolean",
        "description": "True si confianza < 0.7 o el caso es ambiguo.",
    },
    "recomendacion": {"type": "string", "description": "Acción concreta recomendada al auditor humano."},
}


_FINDING_REQUIRED = [
    "evidencia_citada", "analisis", "calculo_numerico",
    "regla", "detalle", "impacto_economico",
    "tipo", "severidad", "confianza",
    "titulo", "descripcion", "item",
    "valor_esperado", "valor_facturado", "diferencia_usd",
    "requiere_verificacion_humana", "recomendacion",
]


_RESUMEN_FINANCIERO_PROPERTIES = {
    "total_facturado": {
        "type": "number",
        "description": "Monto total presente en la factura (subtotal + IVA).",
    },
    "total_auditado_sugerido": {
        "type": "number",
        "description": "Monto que la aseguradora debería pagar tras descontar hallazgos válidos.",
    },
    "total_sobrecobro": {
        "type": "number",
        "description": "Suma de diferencia_usd de hallazgos CRITICAL y WARNING (no INFO).",
    },
    "porcentaje_discrepancia": {
        "type": "number",
        "description": "(total_sobrecobro / total_facturado) * 100, redondeado a 2 decimales.",
    },
}


# Schema de auditoría individual — orden de campos diseñado para CoT
AUDIT_SCHEMA = {
    "type": "object",
    "required": [
        "cadena_de_razonamiento",
        "pasos_validacion",
        "documentacion",
        "campos_faltantes",
        "hallazgos",
        "resumen_financiero",
        "risk_score",
        "status",
        "ahorro_estimado",
        "notas_agente",
        "resumen_ejecutivo_taller",
    ],
    "properties": {
        # ── RAZONAMIENTO PRIMERO ──
        "cadena_de_razonamiento": {
            "type": "string",
            "description": (
                "Razonamiento paso-a-paso ANTES de cualquier veredicto. "
                "Sigue los 8 pasos de la metodología: validar doc → enumerar ítems → "
                "cruzar tarifario → aplicar reglas → citar evidencia → calcular diferencia → "
                "asignar confianza → veredicto. Sin este razonamiento explícito el resto del "
                "JSON no es confiable."
            ),
        },
        "pasos_validacion": {
            "type": "array",
            "description": "Cada cálculo numérico explícito que sustenta los hallazgos.",
            "items": {
                "type": "object",
                "required": ["item", "calculo", "resultado", "umbral", "decision"],
                "properties": {
                    "item": {"type": "string", "description": "Código o descripción del ítem evaluado."},
                    "calculo": {"type": "string", "description": "Operación matemática completa."},
                    "resultado": {"type": "string", "description": "Resultado numérico del cálculo."},
                    "umbral": {"type": "string", "description": "Umbral/regla aplicada del tarifario."},
                    "decision": {"type": "string", "description": "Decisión: ok / WARNING / CRITICAL / etc."},
                },
            },
        },
        # ── ESTADO DOCUMENTAL ──
        "documentacion": {
            "type": "string",
            "enum": ["Completa", "Incompleta"],
            "description": "Estado de los campos críticos (RUC, número, fecha).",
        },
        "campos_faltantes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Lista de campos críticos ausentes. Vacío si documentación completa.",
        },
        # ── HALLAZGOS (con evidencia y confianza) ──
        "hallazgos": {
            "type": "array",
            "description": (
                "Lista de discrepancias detectadas. Cada hallazgo DEBE tener "
                "evidencia_citada literal del input y confianza calibrada."
            ),
            "items": {
                "type": "object",
                "required": _FINDING_REQUIRED,
                "properties": _FINDING_PROPERTIES,
            },
        },
        # ── FINANCIERO ──
        "resumen_financiero": {
            "type": "object",
            "required": list(_RESUMEN_FINANCIERO_PROPERTIES.keys()),
            "properties": _RESUMEN_FINANCIERO_PROPERTIES,
        },
        # ── SCORE ──
        "risk_score": {
            "type": "integer",
            "description": (
                "0-100. Fórmula: CRITICAL*35 + WARNING*20 + INFO*5, cap 100. "
                "Verifica que coincida con el conteo de hallazgos."
            ),
        },
        # ── VEREDICTO (al final, después del razonamiento) ──
        "status": {
            "type": "string",
            "enum": ["Aprobado", "Observado", "Rechazado"],
            "description": (
                "VEREDICTO FINAL. DEBE ser coherente con hallazgos: "
                "Aprobado=0 CRITICAL/WARNING, Observado=≥1 WARNING+0 CRITICAL, "
                "Rechazado=≥1 CRITICAL."
            ),
        },
        "ahorro_estimado": {
            "type": "number",
            "description": (
                "Monto total en USD que la aseguradora ahorraría al rechazar/ajustar "
                "los hallazgos CRITICAL y WARNING. Equivale a resumen_financiero.total_sobrecobro. "
                "Si status=Aprobado → 0.00."
            ),
        },
        "notas_agente": {
            "type": "string",
            "description": "Resumen ejecutivo para el auditor humano interno (3-5 líneas).",
        },
        "resumen_ejecutivo_taller": {
            "type": "string",
            "description": "Mensaje firme y profesional dirigido al taller explicando violaciones y correcciones (máx 4 líneas).",
        },
    },
}


# Schema batch — orden similar + análisis cross-pattern
BATCH_SCHEMA = {
    "type": "object",
    "required": [
        "analisis_global_inicial",
        "patrones_cruzados_detectados",
        "auditorias",
        "resumen_global",
    ],
    "properties": {
        "analisis_global_inicial": {
            "type": "string",
            "description": (
                "Análisis preliminar del lote ANTES de auditar individualmente: "
                "¿qué talleres aparecen? ¿qué ítems se repiten entre facturas? "
                "¿hay agrupaciones temporales sospechosas? Esto guía la auditoría individual."
            ),
        },
        "patrones_cruzados_detectados": {
            "type": "array",
            "description": (
                "Patrones de fraude que solo se detectan al ver múltiples facturas en conjunto. "
                "Ejemplos: mismo taller con 3+ anomalías críticas, item idéntico en siniestros "
                "incompatibles, escalada progresiva de precios del mismo ítem entre fechas."
            ),
            "items": {
                "type": "object",
                "required": ["tipo_patron", "descripcion", "facturas_involucradas", "evidencia", "severidad", "confianza", "recomendacion"],
                "properties": {
                    "tipo_patron": {
                        "type": "string",
                        "enum": [
                            "TALLER_REINCIDENTE",
                            "ESCALADA_PRECIOS",
                            "ITEM_RECURRENTE_INCOHERENTE",
                            "AGRUPACION_TEMPORAL",
                            "DUPLICADO_ENTRE_FACTURAS",
                            "OTRO",
                        ],
                    },
                    "descripcion": {"type": "string"},
                    "facturas_involucradas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de invoice_number afectados.",
                    },
                    "evidencia": {
                        "type": "string",
                        "description": "Citas literales de las facturas que respaldan el patrón.",
                    },
                    "severidad": {"type": "string", "enum": ["INFO", "WARNING", "CRITICAL"]},
                    "confianza": {"type": "number"},
                    "recomendacion": {"type": "string"},
                },
            },
        },
        "auditorias": {
            "type": "array",
            "description": "Auditoría individual de cada factura del lote.",
            "items": {
                "type": "object",
                "required": [
                    "invoice_number",
                    "cadena_de_razonamiento",
                    "documentacion",
                    "campos_faltantes",
                    "hallazgos",
                    "resumen_financiero",
                    "risk_score",
                    "status",
                    "notas_agente",
                    "patrones_cruzados",
                ],
                "properties": {
                    "invoice_number": {"type": "string"},
                    "cadena_de_razonamiento": {"type": "string"},
                    "documentacion": {"type": "string", "enum": ["Completa", "Incompleta"]},
                    "campos_faltantes": {"type": "array", "items": {"type": "string"}},
                    "hallazgos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": _FINDING_REQUIRED,
                            "properties": _FINDING_PROPERTIES,
                        },
                    },
                    "resumen_financiero": {
                        "type": "object",
                        "properties": _RESUMEN_FINANCIERO_PROPERTIES,
                    },
                    "risk_score": {"type": "integer"},
                    "status": {"type": "string", "enum": ["Aprobado", "Observado", "Rechazado"]},
                    "notas_agente": {"type": "string"},
                    "patrones_cruzados": {
                        "type": "string",
                        "description": "Referencia a tipo_patron de patrones_cruzados_detectados que afectan a esta factura.",
                    },
                },
            },
        },
        "resumen_global": {
            "type": "object",
            "required": [
                "total_facturas",
                "total_facturado",
                "total_sobrecobro_detectado",
                "facturas_criticas",
                "facturas_observadas",
                "facturas_aprobadas",
                "patrones_fraude_detectados",
                "talleres_alto_riesgo",
                "recomendacion_global",
            ],
            "properties": {
                "total_facturas": {"type": "integer"},
                "total_facturado": {"type": "number"},
                "total_sobrecobro_detectado": {"type": "number"},
                "facturas_criticas": {"type": "integer"},
                "facturas_observadas": {"type": "integer"},
                "facturas_aprobadas": {"type": "integer"},
                "patrones_fraude_detectados": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Resumen 1-línea de cada patrón crítico.",
                },
                "talleres_alto_riesgo": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Talleres con ≥2 hallazgos CRITICAL en el lote.",
                },
                "recomendacion_global": {
                    "type": "string",
                    "description": "Recomendación ejecutiva para la aseguradora (escalar a legal, etc.).",
                },
            },
        },
    },
}


# Schema de self-review (segunda pasada crítica)
SELF_REVIEW_SCHEMA = {
    "type": "object",
    "required": ["validacion", "hallazgos_omitidos", "falsos_positivos", "errores_calculo", "veredicto_final_correcto", "audit_corregido_si_necesario"],
    "properties": {
        "validacion": {
            "type": "string",
            "enum": ["AUDIT_CORRECTO", "REQUIERE_CORRECCION"],
        },
        "hallazgos_omitidos": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Anomalías que el audit original no detectó (con evidencia).",
        },
        "falsos_positivos": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Hallazgos del audit original que NO son válidos (con razón).",
        },
        "errores_calculo": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Errores aritméticos detectados (ej. risk_score mal calculado).",
        },
        "veredicto_final_correcto": {
            "type": "string",
            "enum": ["Aprobado", "Observado", "Rechazado"],
        },
        "audit_corregido_si_necesario": {
            "type": "string",
            "description": "Si validacion=REQUIERE_CORRECCION, JSON corregido. Vacío si correcto.",
        },
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# Mappings al formato interno del sistema
# ──────────────────────────────────────────────────────────────────────────────

STATUS_MAP = {"Aprobado": "approved", "Observado": "completed", "Rechazado": "escalated"}
SEVERITY_MAP = {"INFO": "info", "WARNING": "warning", "CRITICAL": "critical"}
FINDING_TYPE_MAP = {
    "OVERCHARGE": "overcharge",
    "DUPLICATE": "duplicate",
    "INCOHERENCE": "incoherence",
    "QUANTITY_ANOMALY": "quantity_anomaly",
    "MISSING_DOCUMENT": "missing_document",
    "CLEAN": "clean",
}


# ──────────────────────────────────────────────────────────────────────────────
# Validación semántica — coherencia status ↔ severidad
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]


def _filter_false_positive_overcharge(
    report: Dict[str, Any],
    invoice: Dict[str, Any],
    tariff_items: List[Dict],
) -> Dict[str, Any]:
    """
    Drop hallazgos OVERCHARGE donde precio_facturado ≤ precio_max * (1 + tolerancia_pct/100).
    Recalcula risk_score, status y total_sobrecobro tras el filtrado.
    """
    tariff_by_code = {t["code"]: t for t in tariff_items}
    items_by_code = {it.get("code", ""): it for it in invoice.get("items", [])}

    kept = []
    dropped = 0
    for h in report.get("hallazgos", []):
        tipo = (h.get("tipo") or "").upper()
        if tipo != "OVERCHARGE":
            kept.append(h)
            continue
        # Resolver código del ítem
        item_desc = h.get("item", "") or ""
        # buscar el ítem por descripción o código en evidencia_citada
        ev = h.get("evidencia_citada", "")
        item_match = None
        for it in invoice.get("items", []):
            if it.get("description", "") and it["description"] in item_desc:
                item_match = it
                break
            if it.get("code", "") and it["code"] in ev:
                item_match = it
                break
        if not item_match:
            kept.append(h)  # no se puede validar, mantener
            continue
        tariff = tariff_by_code.get(item_match.get("code", ""))
        if not tariff:
            kept.append(h)  # sin tarifario, mantener
            continue
        unit_price = float(item_match.get("unit_price", 0) or 0)
        max_price = float(tariff.get("max_price", 0) or 0)
        tol = float(tariff.get("tolerance_pct", 10) or 10)
        threshold = max_price * (1 + tol / 100)
        if unit_price <= threshold:
            dropped += 1
            continue  # falso positivo → descartar
        kept.append(h)

    if dropped:
        report["hallazgos"] = kept
        # Recalcular risk_score
        sevs = [h.get("severidad", "INFO") for h in kept]
        n_crit = sevs.count("CRITICAL")
        n_warn = sevs.count("WARNING")
        n_info = sevs.count("INFO")
        report["risk_score"] = min(100, n_crit * 35 + n_warn * 20 + n_info * 5)
        # Recalcular status
        if n_crit > 0:
            report["status"] = "Rechazado"
        elif n_warn > 0:
            report["status"] = "Observado"
        else:
            report["status"] = "Aprobado"
        # Recalcular total_sobrecobro
        new_total = sum(float(h.get("diferencia_usd", 0) or 0) for h in kept
                        if h.get("severidad") in ("WARNING", "CRITICAL"))
        if "resumen_financiero" in report:
            report["resumen_financiero"]["total_sobrecobro"] = round(new_total, 2)
        report["ahorro_estimado"] = round(new_total, 2)
        report.setdefault("_filter_metadata", {})["overcharge_dropped"] = dropped
    return report


def validate_audit_response(report: Dict[str, Any]) -> ValidationResult:
    """
    Valida coherencia interna del reporte. Retorna lista de errores semánticos.
    Si hay errores, podemos retry con feedback explícito.
    """
    errors: List[str] = []

    hallazgos = report.get("hallazgos", [])
    severities = [h.get("severidad", "INFO") for h in hallazgos]
    n_critical = severities.count("CRITICAL")
    n_warning = severities.count("WARNING")
    status = report.get("status", "")

    # Coherencia status ↔ severidades
    if status == "Aprobado" and (n_critical > 0 or n_warning > 0):
        errors.append(
            f"status='Aprobado' inválido: hay {n_critical} CRITICAL y {n_warning} WARNING. "
            f"Aprobado requiere 0 CRITICAL y 0 WARNING."
        )
    if status == "Observado" and n_critical > 0:
        errors.append(
            f"status='Observado' inválido: hay {n_critical} CRITICAL. "
            f"Observado requiere 0 CRITICAL."
        )
    if status == "Rechazado" and n_critical == 0:
        errors.append(
            f"status='Rechazado' inválido: no hay hallazgos CRITICAL."
        )

    # Risk score coherente
    expected_risk = min(100, n_critical * 35 + n_warning * 20 + severities.count("INFO") * 5)
    actual_risk = report.get("risk_score", 0)
    if abs(actual_risk - expected_risk) > 5:
        errors.append(
            f"risk_score={actual_risk} no coincide con conteo de hallazgos. "
            f"Esperado ≈ {expected_risk}."
        )

    # CRITICAL con confianza < 0.7 viola anti-alucinación
    for i, h in enumerate(hallazgos):
        if h.get("severidad") == "CRITICAL" and h.get("confianza", 1.0) < 0.7:
            errors.append(
                f"hallazgos[{i}] es CRITICAL con confianza={h.get('confianza')} < 0.7. "
                f"Reglas anti-alucinación: no marcar CRITICAL si confianza < 0.7."
            )

    # Hallazgo sin evidencia citada
    for i, h in enumerate(hallazgos):
        if not h.get("evidencia_citada", "").strip():
            errors.append(f"hallazgos[{i}] no tiene evidencia_citada — viola anti-alucinación.")

    return ValidationResult(is_valid=len(errors) == 0, errors=errors)


# ──────────────────────────────────────────────────────────────────────────────
# Auditor agéntico
# ──────────────────────────────────────────────────────────────────────────────

class GeminiAuditor:
    """
    Auditor IA agéntico con Gemini 2.5 Flash.

    Patrones agénticos:
      • Chain-of-thought forzado por orden de campos en schema.
      • Few-shot calibration en system prompt.
      • Self-reflection opcional (audit + critique pass).
      • Validación semántica + retry con feedback.
    """

    def __init__(self, model: str = MODEL):
        api_key = os.environ.get("GOOGLE_API_KEY")
        self.mock_mode = not api_key
        if not self.mock_mode:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None
        self.model = model

    # ── Llamada base ──────────────────────────────────────────────────────────

    def _call_gemini(
        self,
        prompt: str,
        schema: dict,
        system_instruction: str = SYSTEM_PROMPT,
        temperature: float = TEMPERATURE_AUDIT,
    ) -> Dict[str, Any]:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=temperature,
            ),
        )
        return json.loads(response.text)

    # ── Audit individual con retry ────────────────────────────────────────────

    def audit(
        self,
        invoice: Dict[str, Any],
        claim: Dict[str, Any],
        tariff_items: List[Dict],
        enable_self_reflection: bool = False,
        invoice_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Audita una factura con pipeline agéntico:
          1) Llamada inicial con CoT + few-shot + 3 tareas del Auditor Senior
          2) Validación semántica
          3) Retry si invalido (con feedback)
          4) Self-reflection opcional (catch missed findings)
        """
        if self.mock_mode:
            return self._get_mock_audit_response(invoice)

        payload = self._build_audit_payload(invoice, claim, tariff_items, invoice_history)
        prompt = (
            "Audita esta factura siguiendo la metodología paso-a-paso. "
            "Ejecuta las TAREAS 1, 2 y 3 explícitamente. "
            "Llena los campos de razonamiento ANTES del veredicto.\n\n"
            f"{payload}"

        )

        # Stage 1 — audit inicial
        report = self._call_gemini(prompt, AUDIT_SCHEMA)

        # Stage 1.5 — filtrado defensivo de falsos positivos OVERCHARGE
        report = _filter_false_positive_overcharge(report, invoice, tariff_items)

        # Stage 2 — validación semántica
        validation = validate_audit_response(report)
        attempts = 0
        while not validation.is_valid and attempts < MAX_RETRIES:
            attempts += 1
            feedback = (
                "Tu respuesta anterior tiene los siguientes errores de coherencia. "
                "Corrige y devuelve una nueva auditoría coherente:\n\n"
                + "\n".join(f"  • {e}" for e in validation.errors)
                + "\n\nRespuesta original:\n"
                + json.dumps(report, ensure_ascii=False, indent=2)
                + "\n\nInput original:\n"
                + payload
            )
            report = self._call_gemini(feedback, AUDIT_SCHEMA, temperature=0.05)
            validation = validate_audit_response(report)

        # Stage 3 — self-reflection (opcional)
        if enable_self_reflection:
            report = self._self_review(report, payload)

        return self._normalize(report, invoice)

    # ── Self-reflection pass ──────────────────────────────────────────────────

    def _self_review(self, report: Dict[str, Any], original_payload: str) -> Dict[str, Any]:
        """
        Segunda pasada: el modelo critica su propia auditoría.
        Si encuentra errores, retorna versión corregida.
        """
        review_prompt = (
            "Acabas de emitir la siguiente auditoría. Actúa ahora como un AUDITOR REVISOR "
            "INDEPENDIENTE y critícala con escepticismo profesional:\n\n"
            "  • ¿Falta algún hallazgo obvio? (review hallazgos_omitidos)\n"
            "  • ¿Algún hallazgo es falso positivo? (review falsos_positivos)\n"
            "  • ¿Hay errores aritméticos en risk_score o resumen_financiero?\n"
            "  • ¿El veredicto status es coherente con los hallazgos?\n\n"
            "AUDITORÍA A REVISAR:\n"
            + json.dumps(report, ensure_ascii=False, indent=2)
            + "\n\nINPUT ORIGINAL:\n"
            + original_payload
        )

        review = self._call_gemini(
            review_prompt, SELF_REVIEW_SCHEMA, temperature=TEMPERATURE_REVIEW
        )

        if review.get("validacion") == "REQUIERE_CORRECCION":
            corrected_str = review.get("audit_corregido_si_necesario", "").strip()
            if corrected_str:
                try:
                    corrected = json.loads(corrected_str)
                    if validate_audit_response(corrected).is_valid:
                        corrected["_self_review_metadata"] = {
                            "had_corrections": True,
                            "hallazgos_omitidos": review.get("hallazgos_omitidos", []),
                            "falsos_positivos": review.get("falsos_positivos", []),
                            "errores_calculo": review.get("errores_calculo", []),
                        }
                        return corrected
                except json.JSONDecodeError:
                    pass

        report["_self_review_metadata"] = {"had_corrections": False, "validated": True}
        return report

    # ── Batch audit con análisis cross-pattern ────────────────────────────────

    def batch_audit(
        self,
        invoices: List[Dict[str, Any]],
        claims: List[Dict[str, Any]],
        tariff_items: List[Dict],
    ) -> Dict[str, Any]:
        """
        Audita TODAS las facturas en una sola llamada (1M context window).
        Detecta patrones cruzados que solo emergen al ver el lote completo.
        """
        if self.mock_mode:
            return self._get_mock_batch_audit_response(invoices)

        tariff_lookup = self._build_tariff_lookup(tariff_items)
        claim_map = {c["claim_number"]: c for c in claims}

        facturas_payload = [
            {
                "factura": inv,
                "siniestro_declarado": claim_map.get(inv.get("claim_number", ""), {}),
            }
            for inv in invoices
        ]

        payload = json.dumps(
            {
                "lote_facturas": facturas_payload,
                "tarifario_maestro": tariff_lookup,
            },
            ensure_ascii=False,
            indent=2,
        )

        prompt = (
            f"AUDITORÍA EN LOTE — {len(invoices)} facturas\n\n"
            "Realiza el siguiente pipeline:\n\n"
            "  FASE 1 — análisis_global_inicial:\n"
            "    Antes de auditar cada factura individualmente, identifica:\n"
            "    • Talleres recurrentes (RUC repetido)\n"
            "    • Códigos de ítem que aparecen en múltiples facturas\n"
            "    • Concentraciones temporales (fechas agrupadas)\n"
            "    • Asegurados con varios siniestros\n\n"
            "  FASE 2 — patrones_cruzados_detectados:\n"
            "    Detecta patrones de fraude que SOLO se ven al combinar facturas:\n"
            "    • TALLER_REINCIDENTE: mismo taller con ≥2 anomalías CRITICAL\n"
            "    • ESCALADA_PRECIOS: mismo ítem con precio creciente entre fechas\n"
            "    • ITEM_RECURRENTE_INCOHERENTE: ítem en siniestros donde no aplica\n"
            "    • AGRUPACION_TEMPORAL: cluster sospechoso de fechas\n"
            "    • DUPLICADO_ENTRE_FACTURAS: mismo ítem cobrado en facturas distintas\n"
            "    Cita evidencia literal con invoice_number e indices.\n\n"
            "  FASE 3 — auditorias:\n"
            "    Aplica la metodología individual completa a cada factura.\n"
            "    En el campo patrones_cruzados de cada factura, referencia los patrones\n"
            "    de la FASE 2 que la afectan.\n\n"
            "  FASE 4 — resumen_global:\n"
            "    Agregados, talleres de alto riesgo (≥2 CRITICAL), recomendación ejecutiva.\n\n"
            f"DATOS:\n{payload}"
        )

        report = self._call_gemini(prompt, BATCH_SCHEMA)
        return self._normalize_batch(report)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_tariff_lookup(tariff_items: List[Dict]) -> Dict[str, Dict]:
        return {
            t["code"]: {
                "descripcion": t["description"],
                "categoria": t["category"],
                "precio_max": t["max_price"],
                "tolerancia_pct": t["tolerance_pct"],
                "qty_min": t["expected_qty_min"],
                "qty_max": t["expected_qty_max"],
                "siniestros_aplicables": t.get("applicable_claim_types", []),
            }
            for t in tariff_items
        }

    def _build_audit_payload(
        self, invoice: Dict[str, Any], claim: Dict[str, Any], tariff_items: List[Dict],
        invoice_history: Optional[List[Dict]] = None,
    ) -> str:
        return json.dumps(
            {
                "factura": invoice,
                "siniestro_declarado": claim,
                "tarifario_maestro": self._build_tariff_lookup(tariff_items),
                "historico_facturas": invoice_history or [],  # Tarea 3: re-facturación
            },
            ensure_ascii=False,
            indent=2,
        )

    # ── Normalización al formato interno ──────────────────────────────────────

    def _normalize_finding(self, h: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "finding_type": FINDING_TYPE_MAP.get(h.get("tipo", "CLEAN"), "clean"),
            "severity": SEVERITY_MAP.get(h.get("severidad", "INFO"), "info"),
            "title": h.get("titulo", ""),
            "description": h.get("descripcion", ""),
            "item_description": h.get("item", ""),
            "expected_value": h.get("valor_esperado", ""),
            "actual_value": h.get("valor_facturado", ""),
            "difference": float(h.get("diferencia_usd", 0)),
            "recommendation": h.get("recomendacion", ""),
            # Campos del contrato JSON de Auditor Senior
            "regla": h.get("regla", ""),
            "detalle": h.get("detalle", ""),
            "impacto_economico": float(h.get("impacto_economico", h.get("diferencia_usd", 0))),
            # Campos SOTA preservados como metadata
            "evidence": h.get("evidencia_citada", ""),
            "analysis": h.get("analisis", ""),
            "calculation": h.get("calculo_numerico", ""),
            "confidence": float(h.get("confianza", 1.0)),
            "needs_human_review": bool(h.get("requiere_verificacion_humana", False)),
        }

    def _normalize(self, report: dict, invoice: dict) -> Dict[str, Any]:
        hallazgos_norm = [self._normalize_finding(h) for h in report.get("hallazgos", [])]
        resumen = report.get("resumen_financiero", {})
        status_str = report.get("status", "Observado")

        return {
            "status": STATUS_MAP.get(status_str, "completed"),
            "status_label": status_str,
            "documentacion": report.get("documentacion", "Completa"),
            "campos_faltantes": report.get("campos_faltantes", []),
            "hallazgos": hallazgos_norm,
            "risk_score": int(report.get("risk_score", 0)),
            "total_overcharge": float(resumen.get("total_sobrecobro", 0)),
            "total_facturado": float(resumen.get("total_facturado", invoice.get("total", 0))),
            "total_auditado": float(resumen.get("total_auditado_sugerido", 0)),
            "pct_discrepancia": float(resumen.get("porcentaje_discrepancia", 0)),
            # Campo contrato Auditor Senior
            "ahorro_estimado": float(report.get("ahorro_estimado", resumen.get("total_sobrecobro", 0))),
            "notas_agente": report.get("notas_agente", ""),
            "resumen_ejecutivo_taller": report.get("resumen_ejecutivo_taller", ""),
            "model_used": self.model,
            # Campos SOTA preservados
            "cadena_de_razonamiento": report.get("cadena_de_razonamiento", ""),
            "pasos_validacion": report.get("pasos_validacion", []),
            "self_review_metadata": report.get("_self_review_metadata", {}),
        }

    def _normalize_batch(self, raw: dict) -> Dict[str, Any]:
        auditorias_norm = []
        for a in raw.get("auditorias", []):
            hallazgos_norm = [self._normalize_finding(h) for h in a.get("hallazgos", [])]
            resumen = a.get("resumen_financiero", {})
            status_str = a.get("status", "Observado")
            auditorias_norm.append({
                "invoice_number": a.get("invoice_number", ""),
                "status": STATUS_MAP.get(status_str, "completed"),
                "status_label": status_str,
                "documentacion": a.get("documentacion", "Completa"),
                "campos_faltantes": a.get("campos_faltantes", []),
                "hallazgos": hallazgos_norm,
                "risk_score": int(a.get("risk_score", 0)),
                "total_overcharge": float(resumen.get("total_sobrecobro", 0)),
                "total_facturado": float(resumen.get("total_facturado", 0)),
                "total_auditado": float(resumen.get("total_auditado_sugerido", 0)),
                "pct_discrepancia": float(resumen.get("porcentaje_discrepancia", 0)),
                "notas_agente": a.get("notas_agente", ""),
                "patrones_cruzados": a.get("patrones_cruzados", ""),
                "cadena_de_razonamiento": a.get("cadena_de_razonamiento", ""),
                "model_used": self.model,
            })

        resumen_global = raw.get("resumen_global", {})
        return {
            "analisis_global_inicial": raw.get("analisis_global_inicial", ""),
            "patrones_cruzados_detectados": raw.get("patrones_cruzados_detectados", []),
            "auditorias": auditorias_norm,
            "resumen_global": {
                "total_facturas": resumen_global.get("total_facturas", len(auditorias_norm)),
                "total_facturado": float(resumen_global.get("total_facturado", 0)),
                "total_sobrecobro_detectado": float(resumen_global.get("total_sobrecobro_detectado", 0)),
                "facturas_criticas": int(resumen_global.get("facturas_criticas", 0)),
                "facturas_observadas": int(resumen_global.get("facturas_observadas", 0)),
                "facturas_aprobadas": int(resumen_global.get("facturas_aprobadas", 0)),
                "patrones_fraude_detectados": resumen_global.get("patrones_fraude_detectados", []),
                "talleres_alto_riesgo": resumen_global.get("talleres_alto_riesgo", []),
                "recomendacion_global": resumen_global.get("recomendacion_global", ""),
            },
            "model_used": self.model,
        }

    def _get_mock_audit_response(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "completed",
            "status_label": "Observado",
            "documentacion": "Completa",
            "campos_faltantes": [],
            "hallazgos": [
                {
                    "finding_type": "overcharge",
                    "severity": "warning",
                    "title": "[PRUEBA SIN API DE GOOGLE] Falta GOOGLE_API_KEY",
                    "description": "Debe agregar una API Key de Google para realizar la auditoría real.",
                    "item_description": "Item de prueba (mock)",
                    "expected_value": "0.0",
                    "actual_value": "100.0",
                    "difference": 100.0,
                    "recommendation": "Agregar GOOGLE_API_KEY en las variables de entorno (.env)",
                    "regla": "Prueba de Integración",
                    "detalle": "Prueba sin API de Google agregada. Esta es una respuesta automática.",
                    "impacto_economico": 100.0,
                    "evidence": "N/A",
                    "analysis": "Ejecución en mock mode",
                    "calculation": "100 - 0",
                    "confidence": 1.0,
                    "needs_human_review": True
                }
            ],
            "risk_score": 50,
            "total_overcharge": 100.0,
            "total_facturado": float(invoice.get("total", 0) if isinstance(invoice, dict) else 0),
            "total_auditado": max(0, float(invoice.get("total", 0) if isinstance(invoice, dict) else 0) - 100),
            "pct_discrepancia": 10.0,
            "ahorro_estimado": 100.0,
            "notas_agente": "[MOCK MODE] Prueba sin API de Google agregada para que el revisor vea que son funciones donde debe agregar la GOOGLE_API_KEY.",
            "resumen_ejecutivo_taller": "Esta es una notificación generada en modo de prueba por falta de API Key de Google.",
            "model_used": "mock-test-model",
            "cadena_de_razonamiento": "Falta API Key, se activa modo mock",
            "pasos_validacion": [],
            "self_review_metadata": {}
        }

    def _get_mock_batch_audit_response(self, invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "analisis_global_inicial": "Modo de prueba sin API de Google activado.",
            "patrones_cruzados_detectados": [],
            "auditorias": [
                {
                    "invoice_number": inv.get("invoice_number", "TEST") if isinstance(inv, dict) else str(inv),
                    "status": "completed",
                    "status_label": "Observado",
                    "documentacion": "Completa",
                    "campos_faltantes": [],
                    "hallazgos": [
                        {
                            "finding_type": "overcharge",
                            "severity": "warning",
                            "title": "[PRUEBA SIN API DE GOOGLE]",
                            "description": "Debe agregar una API Key de Google.",
                            "item_description": "Item de prueba (mock)",
                            "expected_value": "0.0",
                            "actual_value": "100.0",
                            "difference": 100.0,
                            "recommendation": "Agregar GOOGLE_API_KEY",
                            "regla": "Prueba de Integración",
                            "detalle": "Prueba sin API de Google agregada.",
                            "impacto_economico": 100.0,
                            "evidence": "N/A",
                            "analysis": "Ejecución en mock mode",
                            "calculation": "100 - 0",
                            "confidence": 1.0,
                            "needs_human_review": True
                        }
                    ],
                    "risk_score": 50,
                    "total_overcharge": 100.0,
                    "total_facturado": float(inv.get("total", 0) if isinstance(inv, dict) else 0),
                    "total_auditado": max(0, float(inv.get("total", 0) if isinstance(inv, dict) else 0) - 100),
                    "pct_discrepancia": 10.0,
                    "notas_agente": "[MOCK MODE] Prueba sin API.",
                    "patrones_cruzados": "",
                    "cadena_de_razonamiento": "Falta API Key",
                    "model_used": "mock-test-model",
                } for inv in invoices
            ],
            "resumen_global": {
                "total_facturas": len(invoices),
                "total_facturado": sum(float(inv.get("total", 0) if isinstance(inv, dict) else 0) for inv in invoices),
                "total_sobrecobro_detectado": len(invoices) * 100.0,
                "facturas_criticas": 0,
                "facturas_observadas": len(invoices),
                "facturas_aprobadas": 0,
                "patrones_fraude_detectados": [],
                "talleres_alto_riesgo": [],
                "recomendacion_global": "Agregar GOOGLE_API_KEY para auditoría real."
            },
            "model_used": "mock-test-model"
        }
