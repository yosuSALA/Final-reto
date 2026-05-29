"""
Política de obligatoriedad del Parte Policial.

No todos los siniestros requieren parte policial — depende de la gravedad y de
la naturaleza del evento. Esta lógica es **interna** (no configurable por
perfil hoy) y se computa on-demand a partir del siniestro y su declaración.

La función pública `requires_police_report(siniestro, declaration)` devuelve
una tupla `(required: bool, reasons: list[str])`.

Criterios actuales (ver memoria `project-police-report-threshold`):
  1. Cobertura ROBO o INCENDIO → siempre requerido (delito / evento crítico).
  2. Monto reclamado ≥ $3,000 USD → requerido por exposición económica.
  3. Lesionados reportados en la declaración → requerido.
  4. Vehículo contrario involucrado (placa en declaración) → requerido.
  5. Estado del siniestro indica pérdida total alta → requerido.

Si ningún criterio aplica → opcional (etapa 3 se puede saltar).
"""
from __future__ import annotations

from typing import List, Tuple, Optional

from backend.models import (
    Siniestro, AccidentDeclaration, Cobertura, EstadoSiniestro,
)


# ── Umbrales ──────────────────────────────────────────────────────────

# Monto reclamado a partir del cual el parte es obligatorio (USD).
MONTO_UMBRAL_USD = 3000.0

# Coberturas que siempre requieren parte (delitos / eventos críticos).
COBERTURAS_OBLIGATORIAS = frozenset({
    Cobertura.ROBO,
    Cobertura.INCENDIO,
})

# Estados que indican siniestro "pesado" (pérdida total / pago total).
ESTADOS_PESADOS = frozenset({
    EstadoSiniestro.PAGO_TOTAL,
    EstadoSiniestro.LIQUIDADO,
})

# Marcadores textuales que indican "no hubo lesionados" en el campo de
# asistencia médica de la declaración. Si el campo está vacío o contiene
# alguno de estos marcadores, NO se considera lesionados.
NO_LESIONADOS_MARKERS = (
    "no se reportan",
    "no aplica",
    "ninguno",
    "ningun",
    "sin lesionados",
    "n/a",
)


def _had_lesionados(declaration: Optional[AccidentDeclaration]) -> bool:
    """True si la declaración indica que hubo lesionados."""
    if not declaration:
        return False
    val = (declaration.autoridades_lugar_asistencia_medica or "").strip().lower()
    if not val:
        return False
    return not any(m in val for m in NO_LESIONADOS_MARKERS)


def _had_third_party(declaration: Optional[AccidentDeclaration]) -> bool:
    """True si la declaración registra un vehículo contrario (placa o propietario)."""
    if not declaration:
        return False
    return bool(
        (declaration.contrario_placa or "").strip()
        or (declaration.contrario_propietario or "").strip()
    )


def requires_police_report(
    siniestro: Siniestro,
    declaration: Optional[AccidentDeclaration] = None,
) -> Tuple[bool, List[str]]:
    """Devuelve (required, reasons).

    `declaration` puede ser None (cuando la declaración aún no se cargó).
    En ese caso aplicamos sólo los criterios derivables del siniestro
    (cobertura, monto, estado) — los criterios derivados de la declaración
    (lesionados, terceros) se evalúan como False.
    """
    reasons: List[str] = []

    # 1. Cobertura crítica
    if siniestro.cobertura in COBERTURAS_OBLIGATORIAS:
        reasons.append(
            f"Cobertura '{siniestro.cobertura.value}' requiere parte policial "
            f"(delito o evento crítico)."
        )

    # 2. Monto reclamado significativo
    monto = float(siniestro.monto_reclamado or 0)
    if monto >= MONTO_UMBRAL_USD:
        reasons.append(
            f"Monto reclamado ${monto:,.2f} ≥ umbral ${MONTO_UMBRAL_USD:,.0f}."
        )

    # 3. Lesionados (sólo si hay declaración)
    if _had_lesionados(declaration):
        reasons.append(
            "La declaración reporta lesionados / asistencia médica brindada."
        )

    # 4. Vehículo contrario involucrado
    if _had_third_party(declaration):
        reasons.append(
            "La declaración registra un vehículo contrario (terceros implicados)."
        )

    # 5. Estado pesado con monto razonable (pérdida total declarada)
    if (
        siniestro.estado in ESTADOS_PESADOS
        and monto >= (MONTO_UMBRAL_USD / 2)
    ):
        reasons.append(
            f"Estado '{siniestro.estado.value}' con monto ${monto:,.2f} "
            f"sugiere pérdida significativa."
        )

    return (bool(reasons), reasons)
