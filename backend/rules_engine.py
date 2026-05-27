"""
Motor de reglas determinístico para auditoría de facturas.

Reglas implementadas:
  1. PriceOverchargeRule      — sobrecobro vs tarifario
  2. DuplicateChargeRule      — ítems duplicados dentro de la misma factura
  3. QuantityAnomalyRule      — cantidades fuera del rango esperado
  4. IncoherenceRule          — repuesto mecánicamente incompatible con el siniestro
  5. InvoiceResubmissionRule  — re-facturación: número de factura ya procesado en historial
"""
import json
from typing import List, Dict, Any, Optional
from backend.models import (
    InvoiceItem, TariffItem,
    FindingSeverity, FindingType
)


class Finding:
    """Estructura de un hallazgo de auditoría."""

    def __init__(
        self,
        finding_type: FindingType,
        severity: FindingSeverity,
        title: str,
        description: str,
        item_description: str = "",
        expected_value: str = "",
        actual_value: str = "",
        difference: float = 0.0,
        recommendation: str = ""
    ):
        self.finding_type = finding_type
        self.severity = severity
        self.title = title
        self.description = description
        self.item_description = item_description
        self.expected_value = expected_value
        self.actual_value = actual_value
        self.difference = difference
        self.recommendation = recommendation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_type": self.finding_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "item_description": self.item_description,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "difference": self.difference,
            "recommendation": self.recommendation,
        }


class BaseRule:
    """Clase base para reglas de auditoría."""
    name: str = "base_rule"
    description: str = ""

    def evaluate(self, context: Dict[str, Any]) -> List[Finding]:
        raise NotImplementedError


class PriceOverchargeRule(BaseRule):
    """Detecta cuando el precio cobrado supera el tarifario acordado."""
    name = "price_overcharge"
    description = "Verifica que los precios no excedan el tarifario con tolerancia"

    def evaluate(self, context: Dict[str, Any]) -> List[Finding]:
        findings = []
        items: List[Dict] = context.get("invoice_items", [])
        tariff_map: Dict[str, Dict] = context.get("tariff_map", {})

        for item in items:
            code = item.get("code", "")
            tariff = tariff_map.get(code)

            if not tariff:
                continue

            max_price = tariff["max_price"]
            tolerance = tariff.get("tolerance_pct", 10.0)
            threshold = max_price * (1 + tolerance / 100)
            unit_price = item["unit_price"]

            if unit_price > threshold:
                overcharge_pct = ((unit_price - max_price) / max_price) * 100
                difference = (unit_price - max_price) * item.get("quantity", 1)

                severity = (
                    FindingSeverity.CRITICAL if overcharge_pct > 30
                    else FindingSeverity.WARNING
                )

                findings.append(Finding(
                    finding_type=FindingType.OVERCHARGE,
                    severity=severity,
                    title=f"Sobrecobro detectado: {item['description']}",
                    description=(
                        f"El precio unitario (${unit_price:.2f}) excede el tarifario "
                        f"acordado (${max_price:.2f}) en un {overcharge_pct:.1f}%. "
                        f"Tolerancia permitida: {tolerance}%."
                    ),
                    item_description=item["description"],
                    expected_value=f"${max_price:.2f}",
                    actual_value=f"${unit_price:.2f}",
                    difference=difference,
                    recommendation=(
                        f"Solicitar justificación al taller o ajustar a tarifa "
                        f"acordada. Diferencia total: ${difference:.2f}"
                    )
                ))

        return findings


class DuplicateChargeRule(BaseRule):
    """Detecta cobros duplicados (mismo ítem facturado más de una vez)."""
    name = "duplicate_charge"
    description = "Detecta ítems duplicados en la misma factura"

    def evaluate(self, context: Dict[str, Any]) -> List[Finding]:
        findings = []
        items: List[Dict] = context.get("invoice_items", [])

        seen = {}
        for item in items:
            key = (item.get("code", ""), item.get("description", "").lower().strip())

            if key[0] == "" and key[1] == "":
                continue

            if key in seen:
                seen[key].append(item)
            else:
                seen[key] = [item]

        for key, duplicates in seen.items():
            if len(duplicates) > 1:
                total_charged = sum(d.get("total_price", 0) for d in duplicates)
                findings.append(Finding(
                    finding_type=FindingType.DUPLICATE,
                    severity=FindingSeverity.CRITICAL,
                    title=f"Cobro duplicado: {duplicates[0]['description']}",
                    description=(
                        f"El ítem '{duplicates[0]['description']}' aparece "
                        f"{len(duplicates)} veces en la factura. "
                        f"Monto total cobrado por duplicados: ${total_charged:.2f}."
                    ),
                    item_description=duplicates[0]["description"],
                    expected_value="1 unidad",
                    actual_value=f"{len(duplicates)} entradas",
                    difference=total_charged - duplicates[0].get("total_price", 0),
                    recommendation=(
                        "Verificar si la duplicidad es intencional. "
                        "Solicitar documentación de respaldo al taller."
                    )
                ))

        return findings


class QuantityAnomalyRule(BaseRule):
    """Detecta cantidades fuera del rango esperado para un ítem."""
    name = "quantity_anomaly"
    description = "Verifica que las cantidades estén dentro de rangos razonables"

    def evaluate(self, context: Dict[str, Any]) -> List[Finding]:
        findings = []
        items: List[Dict] = context.get("invoice_items", [])
        tariff_map: Dict[str, Dict] = context.get("tariff_map", {})

        for item in items:
            code = item.get("code", "")
            tariff = tariff_map.get(code)

            if not tariff:
                continue

            qty = item.get("quantity", 1)
            min_qty = tariff.get("expected_qty_min", 0)
            max_qty = tariff.get("expected_qty_max", 100)

            if qty > max_qty:
                findings.append(Finding(
                    finding_type=FindingType.QUANTITY_ANOMALY,
                    severity=FindingSeverity.WARNING,
                    title=f"Cantidad excesiva: {item['description']}",
                    description=(
                        f"Se facturaron {qty} unidades de '{item['description']}'. "
                        f"El rango esperado es {min_qty}-{max_qty} unidades."
                    ),
                    item_description=item["description"],
                    expected_value=f"Máx. {max_qty} uds.",
                    actual_value=f"{qty} uds.",
                    difference=(qty - max_qty) * item.get("unit_price", 0),
                    recommendation=(
                        "Verificar justificación para la cantidad excesiva. "
                        "Podría ser un error de digitación."
                    )
                ))
            elif qty < min_qty:
                findings.append(Finding(
                    finding_type=FindingType.QUANTITY_ANOMALY,
                    severity=FindingSeverity.INFO,
                    title=f"Cantidad inusualmente baja: {item['description']}",
                    description=(
                        f"Se facturaron {qty} unidades de '{item['description']}'. "
                        f"El mínimo esperado es {min_qty} unidades."
                    ),
                    item_description=item["description"],
                    expected_value=f"Mín. {min_qty} uds.",
                    actual_value=f"{qty} uds.",
                    difference=0,
                    recommendation="Revisar si el servicio fue completado."
                ))

        return findings


class IncoherenceRule(BaseRule):
    """Detecta ítems que no corresponden al tipo de siniestro reportado."""
    name = "incoherence"
    description = "Verifica coherencia entre ítems facturados y tipo de siniestro"

    def evaluate(self, context: Dict[str, Any]) -> List[Finding]:
        findings = []
        items: List[Dict] = context.get("invoice_items", [])
        tariff_map: Dict[str, Dict] = context.get("tariff_map", {})
        claim_type: str = context.get("claim_type", "")

        for item in items:
            code = item.get("code", "")
            tariff = tariff_map.get(code)

            if not tariff:
                continue

            applicable_raw = tariff.get("applicable_claim_types", "[]")
            try:
                applicable = json.loads(applicable_raw) if isinstance(applicable_raw, str) else applicable_raw
            except (json.JSONDecodeError, TypeError):
                applicable = []

            if applicable and claim_type and claim_type not in applicable:
                findings.append(Finding(
                    finding_type=FindingType.INCOHERENCE,
                    severity=FindingSeverity.CRITICAL,
                    title=f"Ítem incoherente con siniestro: {item['description']}",
                    description=(
                        f"El ítem '{item['description']}' no corresponde al tipo "
                        f"de siniestro '{claim_type}'. Tipos aplicables: "
                        f"{', '.join(applicable)}."
                    ),
                    item_description=item["description"],
                    expected_value=f"Siniestro: {claim_type}",
                    actual_value=f"Ítem para: {', '.join(applicable)}",
                    difference=item.get("total_price", 0),
                    recommendation=(
                        "Este ítem podría no estar relacionado con el siniestro. "
                        "Escalar para revisión manual inmediata."
                    )
                ))

        return findings


class InvoiceResubmissionRule(BaseRule):
    """
    TAREA 3 — Detección de Re-Facturación.

    Verifica si el número de factura ya fue procesado previamente en el
    histórico de facturas auditadas (invoice_history del contexto).
    Permite detectar reclamos duplicados enviados en siniestros distintos.
    """
    name = "invoice_resubmission"
    description = "Detecta si el número de factura ya fue presentado anteriormente"

    def evaluate(self, context: Dict[str, Any]) -> List[Finding]:
        findings = []
        current_invoice_number: str = context.get("invoice_number", "")
        current_invoice_id: int = context.get("invoice_id", -1)
        current_claim_number: str = context.get("claim_number", "")
        current_workshop_ruc: str = context.get("workshop_ruc", "")
        # invoice_history: lista {id, invoice_number, claim_number, claim_type, workshop_ruc, total}
        history: List[Dict] = context.get("invoice_history", [])

        if not current_invoice_number:
            return findings

        for hist in history:
            if hist.get("id") == current_invoice_id:
                continue  # mismo registro, ignorar
            if hist.get("invoice_number", "") != current_invoice_number:
                continue
            hist_claim = hist.get("claim_number", "")
            hist_ruc = hist.get("workshop_ruc", "")

            # Solo flag si es realmente sospechoso:
            #   • Mismo invoice_number en SINIESTRO DISTINTO → re-facturación cruzada (CRITICAL)
            #   • Mismo invoice_number, mismo siniestro, distinto taller → posible duplicado admin (WARNING)
            #   • Mismo invoice_number, mismo siniestro, mismo taller → re-upload legítimo, NO flag
            if hist_claim and current_claim_number and hist_claim != current_claim_number:
                findings.append(Finding(
                    finding_type=FindingType.DUPLICATE,
                    severity=FindingSeverity.CRITICAL,
                    title=f"Re-facturación cruzada: {current_invoice_number}",
                    description=(
                        f"El número '{current_invoice_number}' aparece en el siniestro "
                        f"'{hist_claim}' Y en el siniestro actual '{current_claim_number}'. "
                        f"Posible re-facturación fraudulenta entre siniestros distintos."
                    ),
                    item_description=f"Factura {current_invoice_number}",
                    expected_value=f"Número único por siniestro",
                    actual_value=f"Aparece en siniestros: {hist_claim} y {current_claim_number}",
                    difference=hist.get("total", 0),
                    recommendation=(
                        f"ESCALAR. Verificar si la factura cobra el mismo daño en dos "
                        f"siniestros distintos. Cruzar items con expediente {hist_claim}."
                    )
                ))
            elif hist_ruc and current_workshop_ruc and hist_ruc != current_workshop_ruc:
                findings.append(Finding(
                    finding_type=FindingType.DUPLICATE,
                    severity=FindingSeverity.WARNING,
                    title=f"Mismo número en talleres distintos: {current_invoice_number}",
                    description=(
                        f"El número '{current_invoice_number}' fue emitido por dos talleres "
                        f"distintos (RUC {hist_ruc} y RUC {current_workshop_ruc}). "
                        f"Probable error administrativo o coincidencia."
                    ),
                    item_description=f"Factura {current_invoice_number}",
                    expected_value=f"Cada taller tiene secuencia única",
                    actual_value=f"Mismo número en RUC {hist_ruc} y {current_workshop_ruc}",
                    difference=0,
                    recommendation="Revisar manualmente; baja probabilidad de fraude."
                ))
            # Mismo siniestro + mismo taller: re-upload o corrección — NO flag

        return findings


class RulesEngine:
    """Motor de reglas que ejecuta todas las reglas de auditoría."""

    def __init__(self):
        self.rules: List[BaseRule] = [
            InvoiceResubmissionRule(),   # Tarea 3 — re-facturación (primero: falla rápida)
            PriceOverchargeRule(),        # Tarea 1 — sobrecobro
            DuplicateChargeRule(),        # Tarea 1 — duplicados en la factura
            QuantityAnomalyRule(),        # Tarea 2 — cantidades anómalas
            IncoherenceRule(),            # Tarea 1 — coherencia mecánica
        ]

    def run_audit(self, context: Dict[str, Any]) -> List[Finding]:
        """Ejecutar todas las reglas y recopilar hallazgos."""
        all_findings: List[Finding] = []

        for rule in self.rules:
            try:
                findings = rule.evaluate(context)
                all_findings.extend(findings)
            except Exception as e:
                all_findings.append(Finding(
                    finding_type=FindingType.INFO,
                    severity=FindingSeverity.INFO,
                    title=f"Error en regla: {rule.name}",
                    description=f"La regla '{rule.name}' falló: {str(e)}",
                    recommendation="Revisar manualmente."
                ))

        return all_findings

    def calculate_risk_score(self, findings: List[Finding]) -> float:
        """Calcular score de riesgo (0-100) basado en hallazgos."""
        if not findings:
            return 0.0

        score = 0.0
        for f in findings:
            if f.severity == FindingSeverity.CRITICAL:
                score += 35.0
            elif f.severity == FindingSeverity.WARNING:
                score += 20.0
            elif f.severity == FindingSeverity.INFO:
                score += 5.0

        return min(score, 100.0)
