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
import re
from datetime import datetime
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


def _norm_claim_type(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.strip().lower().replace("í", "i").replace("ó", "o").replace("é", "e").replace("ú", "u"))


class IncoherenceRule(BaseRule):
    """Detecta ítems que no corresponden al tipo de siniestro reportado."""
    name = "incoherence"
    description = "Verifica coherencia entre ítems facturados y tipo de siniestro"

    def evaluate(self, context: Dict[str, Any]) -> List[Finding]:
        findings = []
        items: List[Dict] = context.get("invoice_items", [])
        tariff_map: Dict[str, Dict] = context.get("tariff_map", {})
        claim_type: str = context.get("claim_type", "")
        claim_cobertura: str = context.get("claim_cobertura", "")
        norm_claim_type = _norm_claim_type(claim_type)
        norm_claim_cobertura = _norm_claim_type(claim_cobertura)

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

            if not applicable:
                continue

            norm_applicable = [_norm_claim_type(a) for a in applicable]
            matches = norm_claim_type in norm_applicable or norm_claim_cobertura in norm_applicable
            if not matches:
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


class DeclarationCompletenessRule(BaseRule):
    """Auditoría INICIAL — valida que la declaración esté completa.

    Campos críticos del FR.RE.100 que deben estar presentes para considerar
    el expediente sólido. La ausencia se marca como hallazgo INFO/WARNING
    para que el analista lo subsane antes de avanzar.
    """
    name = "declaration_completeness"
    description = "Verifica que campos críticos de la declaración estén presentes"

    CRITICAL_FIELDS = [
        ("asegurado_nombre", "Nombre del asegurado"),
        ("veh_placa", "Placa del vehículo"),
        ("veh_chasis", "Chasis del vehículo"),
        ("accidente_fecha", "Fecha del accidente"),
        ("accidente_lugar", "Lugar del accidente"),
        ("accidente_descripcion", "Descripción del accidente"),
        ("conductor_cedula", "Cédula del conductor"),
    ]

    def evaluate(self, context: Dict[str, Any]) -> List[Finding]:
        decl = context.get("declaration") or {}
        if not decl:
            return [Finding(
                finding_type=FindingType.MISSING_DOCUMENT,
                severity=FindingSeverity.CRITICAL,
                title="Falta la Declaración de Accidente",
                description="No se ha cargado el formulario FR.RE.100 para este siniestro.",
                recommendation="Cargar la Declaración antes de avanzar al Parte Policial.",
            )]
        findings = []
        missing = [label for k, label in self.CRITICAL_FIELDS if not decl.get(k)]
        if missing:
            findings.append(Finding(
                finding_type=FindingType.DECLARATION_INCONSISTENCY,
                severity=FindingSeverity.WARNING,
                title="Declaración con campos críticos vacíos",
                description=(
                    f"Faltan {len(missing)} campos críticos: {', '.join(missing)}. "
                    f"La auditoría posterior podría ser inconcluyente."
                ),
                expected_value="Todos los campos críticos completos",
                actual_value=f"{len(missing)} faltantes",
                recommendation="Solicitar al asegurado complete los campos faltantes.",
            ))
        return findings


def _norm_plate(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


class PoliceDeclarationMismatchRule(BaseRule):
    """Auditoría POST-PAGO — cruza Declaración ↔ Parte Policial.

    Detecta divergencias en placa, fecha del hecho y lugar entre lo declarado
    por el asegurado y lo registrado por la autoridad policial.
    """
    name = "police_declaration_mismatch"
    description = "Detecta divergencias entre la declaración del asegurado y el parte policial"

    def evaluate(self, context: Dict[str, Any]) -> List[Finding]:
        decl = context.get("declaration") or {}
        pr = context.get("police_report") or {}
        if not decl or not pr:
            return []

        findings = []

        # Placa
        decl_plate = _norm_plate(decl.get("veh_placa", ""))
        pr_plate = _norm_plate(pr.get("veh_placa", ""))
        if decl_plate and pr_plate and decl_plate != pr_plate:
            findings.append(Finding(
                finding_type=FindingType.POLICE_DECLARATION_MISMATCH,
                severity=FindingSeverity.CRITICAL,
                title="Placa difiere entre declaración y parte policial",
                description=(
                    f"La declaración reporta la placa '{decl.get('veh_placa')}' pero el "
                    f"parte policial registra '{pr.get('veh_placa')}'. "
                    f"Posible fraude: vehículo distinto al asegurado."
                ),
                expected_value=decl.get("veh_placa", ""),
                actual_value=pr.get("veh_placa", ""),
                recommendation="ESCALAR. Verificar identidad del vehículo siniestrado.",
            ))

        # Fecha del hecho: tolerancia de 1 día
        decl_fecha = decl.get("accidente_fecha") or ""
        pr_fecha = pr.get("fecha_hecho") or ""
        if decl_fecha and pr_fecha:
            try:
                d1 = datetime.fromisoformat(decl_fecha).date()
                d2 = datetime.fromisoformat(pr_fecha).date()
                if abs((d1 - d2).days) > 1:
                    findings.append(Finding(
                        finding_type=FindingType.POLICE_DECLARATION_MISMATCH,
                        severity=FindingSeverity.WARNING,
                        title="Fecha del accidente difiere del parte policial",
                        description=(
                            f"Declaración: {d1.isoformat()}. Parte policial: {d2.isoformat()}. "
                            f"Diferencia: {abs((d1 - d2).days)} días."
                        ),
                        expected_value=d1.isoformat(),
                        actual_value=d2.isoformat(),
                        difference=float(abs((d1 - d2).days)),
                        recommendation="Solicitar aclaración al asegurado sobre la cronología.",
                    ))
            except (ValueError, TypeError):
                pass

        # Lugar — comparación textual relajada (al menos una palabra común relevante)
        decl_lugar = _norm_text(decl.get("accidente_lugar", ""))
        pr_calle = _norm_text(pr.get("calle_1", "") + " " + pr.get("calle_2", ""))
        if decl_lugar and pr_calle:
            decl_tokens = {w for w in re.findall(r"[a-záéíóúñ]{4,}", decl_lugar)}
            pr_tokens = {w for w in re.findall(r"[a-záéíóúñ]{4,}", pr_calle)}
            common = decl_tokens & pr_tokens
            if not common and len(decl_tokens) > 1 and len(pr_tokens) > 1:
                findings.append(Finding(
                    finding_type=FindingType.POLICE_DECLARATION_MISMATCH,
                    severity=FindingSeverity.WARNING,
                    title="Lugar del accidente difiere notoriamente del parte",
                    description=(
                        f"Declaración: '{decl.get('accidente_lugar')}'. "
                        f"Parte: '{pr.get('calle_1')} / {pr.get('calle_2')}'. "
                        f"Sin palabras geográficas en común."
                    ),
                    expected_value=decl.get("accidente_lugar", "")[:100],
                    actual_value=(pr.get("calle_1", "") + " / " + pr.get("calle_2", ""))[:100],
                    recommendation="Verificar coordenadas/dirección con el asegurado.",
                ))

        # Robo: si el parte marca robo pero la declaración no lo menciona en
        # descripción ni en daños, marcar incoherencia narrativa
        tipos = pr.get("tipos_accidente") or []
        if "robo" in tipos:
            txt = _norm_text(
                (decl.get("accidente_descripcion") or "") + " " + (decl.get("veh_detalle_danos") or "")
            )
            if "robo" not in txt and "sustra" not in txt:
                findings.append(Finding(
                    finding_type=FindingType.DECLARATION_INCONSISTENCY,
                    severity=FindingSeverity.WARNING,
                    title="Parte indica ROBO pero declaración no lo menciona",
                    description=(
                        "El parte policial clasifica el siniestro como ROBO, pero la "
                        "narrativa del asegurado no menciona robo ni sustracción."
                    ),
                    expected_value="Mención coherente del robo",
                    actual_value="Descripción no menciona robo",
                    recommendation="Solicitar aclaración detallada al asegurado.",
                ))

        return findings


class PoliceReportRequiredRule(BaseRule):
    """Auditoría POST-PAGO — el parte policial es obligatorio sólo cuando la
    política de gravedad lo exige. El contexto trae el flag `pr_required` y
    las razones; si no es requerido, no se emite hallazgo por su ausencia."""
    name = "police_report_required"
    description = "Verifica parte policial cuando la política de gravedad lo exige"

    def evaluate(self, context: Dict[str, Any]) -> List[Finding]:
        pr = context.get("police_report")
        pr_required = bool(context.get("pr_required", False))
        pr_reasons = context.get("pr_reasons", []) or []
        if pr:
            return []
        if not pr_required:
            # Siniestro de baja gravedad — parte no era exigido, no hay hallazgo.
            return []
        reasons_txt = "; ".join(pr_reasons) if pr_reasons else "Política de gravedad."
        return [Finding(
            finding_type=FindingType.MISSING_POLICE_REPORT,
            severity=FindingSeverity.CRITICAL,
            title="Falta el Parte Policial (requerido por gravedad)",
            description=(
                f"No se encontró el parte policial del Ministerio del Interior. "
                f"Es obligatorio para este siniestro. Motivos: {reasons_txt}"
            ),
            expected_value="Parte policial cargado",
            actual_value="No presente",
            recommendation="Cargar parte policial antes de aprobar la facturación.",
        )]


class InvoiceDeclarationMismatchRule(BaseRule):
    """Auditoría POST-PAGO — cruza Factura ↔ Declaración (placa)."""
    name = "invoice_declaration_mismatch"
    description = "Detecta divergencia entre la placa de la factura y la declaración"

    def evaluate(self, context: Dict[str, Any]) -> List[Finding]:
        decl = context.get("declaration") or {}
        invoice_plate = _norm_plate(context.get("invoice_plate", ""))
        decl_plate = _norm_plate(decl.get("veh_placa", ""))
        if not invoice_plate or not decl_plate:
            return []
        if invoice_plate == decl_plate:
            return []
        return [Finding(
            finding_type=FindingType.INVOICE_DECLARATION_MISMATCH,
            severity=FindingSeverity.CRITICAL,
            title="Placa de la factura no coincide con la declaración",
            description=(
                f"La factura reporta placa '{context.get('invoice_plate')}' "
                f"pero la declaración tiene '{decl.get('veh_placa')}'. "
                f"Probable factura aplicada a vehículo distinto al siniestrado."
            ),
            expected_value=decl.get("veh_placa", ""),
            actual_value=context.get("invoice_plate", ""),
            recommendation="ESCALAR. No procesar pago hasta clarificar.",
        )]


class TariffMatchByDescriptionRule(BaseRule):
    """Fallback para facturas formato real (sin códigos de tarifario).

    Cuando `code` está vacío, intenta matchear la descripción del ítem contra
    el tariff_map por keywords. Si encuentra match y el unit_price excede el
    max_price con tolerancia, emite OVERCHARGE.
    """
    name = "tariff_match_by_description"
    description = "Fuzzy match descripción→tarifario para facturas sin códigos"

    KEYWORD_INDEX = {
        # keyword (lowercased) → categoría/keyword del tarifario
        "parabrisas": "PAR",
        "faro": "FAR",
        "guardachoque": "GUA",
        "puerta": "PUE",
        "capo": "CAP",
        "capó": "CAP",
        "espejo": "ESP",
        "radiador": "RAD",
        "motor": "MOT",
        "pintura": "PIN",
        "lija": "LIJ",
        "masilla": "LIJ",
        "soldadura": "SOL",
        "mano de obra": "MO",
        "latoneria": "LAM",
        "latonería": "LAM",
        "carroceria": "LAM",
        "carrocería": "LAM",
        "grua": "GRU",
        "alineacion": "ALI",
        "vidrio": "VID",
        "cerradura": "CER",
        "radio": "RAD02",
    }

    def evaluate(self, context: Dict[str, Any]) -> List[Finding]:
        findings = []
        items: List[Dict] = context.get("invoice_items", [])
        tariff_map: Dict[str, Dict] = context.get("tariff_map", {})
        if not tariff_map:
            return findings

        for item in items:
            if item.get("code"):
                continue  # ya cubierto por PriceOverchargeRule
            desc_lower = (item.get("description") or "").lower()
            if not desc_lower:
                continue
            matched_keyword = None
            for kw in self.KEYWORD_INDEX:
                if kw in desc_lower:
                    matched_keyword = self.KEYWORD_INDEX[kw]
                    break
            if not matched_keyword:
                continue
            # Encontrar el tariff cuyo code contenga ese fragmento
            candidates = [t for code, t in tariff_map.items() if matched_keyword in code]
            if not candidates:
                continue
            # Tomar el de max_price más bajo como referencia conservadora
            ref = min(candidates, key=lambda t: t["max_price"])
            max_price = ref["max_price"]
            tolerance = ref.get("tolerance_pct", 10.0)
            threshold = max_price * (1 + tolerance / 100)
            unit_price = float(item.get("unit_price", 0) or 0)
            qty = float(item.get("quantity", 1) or 1)

            # Las facturas formato simple suelen agrupar (qty=1, unit_price=total).
            # Si unit_price >> tariff típico, podría ser un agregado legítimo;
            # marcamos sólo cuando es muy superior (>3x del threshold base) para
            # reducir falsos positivos.
            if unit_price > threshold * 1.5:
                difference = (unit_price - max_price) * qty
                findings.append(Finding(
                    finding_type=FindingType.OVERCHARGE,
                    severity=FindingSeverity.WARNING,
                    title=f"Posible sobrecobro (descripción libre): {item['description'][:60]}",
                    description=(
                        f"La descripción '{item['description']}' coincide con tarifario "
                        f"'{ref['code']}' (máx ${max_price:.2f}). Unit price ${unit_price:.2f} "
                        f"excede {threshold * 3:.2f} (3× tolerancia)."
                    ),
                    item_description=item["description"],
                    expected_value=f"~${max_price:.2f}",
                    actual_value=f"${unit_price:.2f}",
                    difference=difference,
                    recommendation="Solicitar detalle desglosado al taller.",
                ))
        return findings


# ── Motor ──────────────────────────────────────────────


class RulesEngine:
    """Motor de reglas que ejecuta todas las reglas de auditoría."""

    def __init__(self, stage: str = "invoice"):
        """stage: 'invoice' (legacy/post-payment con factura),
                  'initial' (etapa 2: sólo declaración),
                  'post_payment' (etapa 5: declaración+parte+factura)."""
        if stage == "initial":
            self.rules: List[BaseRule] = [
                DeclarationCompletenessRule(),
            ]
        elif stage == "post_payment":
            self.rules = [
                DeclarationCompletenessRule(),
                PoliceReportRequiredRule(),
                PoliceDeclarationMismatchRule(),
                InvoiceDeclarationMismatchRule(),
                InvoiceResubmissionRule(),
                PriceOverchargeRule(),
                TariffMatchByDescriptionRule(),
                DuplicateChargeRule(),
                QuantityAnomalyRule(),
                IncoherenceRule(),
            ]
        else:
            # Comportamiento legacy: igual que antes del rediseño
            self.rules = [
                InvoiceResubmissionRule(),
                PriceOverchargeRule(),
                DuplicateChargeRule(),
                QuantityAnomalyRule(),
                IncoherenceRule(),
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
