"""
Extractor de facturas desde PDF.
Soporta: PDFs de talleres del sistema (reportlab) y PDFs genéricos con texto.
"""
import re
import io
from typing import Dict, Any, Optional, List


def extract_invoice_from_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Extrae datos estructurados de una factura PDF.

    Detecta automáticamente el formato:
      • SRI Ecuador (formato legacy del test_invoice_generator)
        — claves: "SUBTOTAL 12%", "VALOR TOTAL", "CÓD. PRINCIPAL"
      • Formato simple real (synthetic_data/FACTURAS)
        — claves: "Subtotal 15%", "TOTAL A PAGAR", "Siniestro Ref:"

    Retorna dict compatible con el formato de auditoría.
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("Instalar pdfplumber: pip install pdfplumber")

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        full_text = ""
        all_tables = []
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)

    if _is_simple_invoice(full_text):
        invoice = _parse_text_simple(full_text, all_tables)
    else:
        invoice = _parse_text(full_text, all_tables)
    return invoice


def _is_simple_invoice(text: str) -> bool:
    """Heurística: el formato real (synthetic_data) tiene 'Siniestro Ref:' y
    'TOTAL A PAGAR'. El SRI legacy tiene 'VALOR TOTAL' y 'CÓD. PRINCIPAL'."""
    t = text.upper()
    if "SINIESTRO REF" in t and ("TOTAL A PAGAR" in t or "SUBTOTAL 15%" in t):
        return True
    # Sin marcador SRI fuerte → asumir simple
    if "CÓD. PRINCIPAL" not in t and "VALOR TOTAL" not in t and "TOTAL A PAGAR" in t:
        return True
    return False


def _parse_text_simple(text: str, tables: list) -> Dict[str, Any]:
    """Parser para el formato real `Muestras_Facturas_Siniestros-SIN-XXXX.pdf`.

    Estructura observada:
      • Razón social (línea grande)
      • RUC: 1792293312001
      • Quito, Ecuador / Tel: ...
      • FACTURA  Nº: 001-002-747311022  Fecha: 2025-07-17  Siniestro Ref: SIN-0001
      • Cliente: ... / Placa: ... / C.I./RUC: ... / Vehículo: ...
      • Items en tabla: Cant. | Descripción | V. Unitario | V. Total
      • Subtotal 15% / IVA 15% / TOTAL A PAGAR
      • "Caso: Legítimo|Fraudulento" (marcador sintético para debugging)
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    invoice_number = _extract_pattern(text, [
        r"N[°ºo]\s*[:\-]?\s*([\d\-]+)",
        r"FACTURA[^\n]*?(\d{3}-\d{3}-\d{6,12})",
        r"(\d{3}-\d{3}-\d{6,12})",
    ])

    # RUC: capturamos cualquier secuencia tras "RUC:" para detectar también
    # facturas con RUC inválido (señal de fraude). La validación de longitud
    # 13 dígitos queda para una regla de auditoría aguas abajo.
    ruc = _extract_pattern(text, [
        r"RUC[:\s]+([\d]{8,13})",
        r"\b(\d{13})\b",
    ])

    issue_date = _extract_pattern(text, [
        r"Fecha[:\s]+(\d{4}-\d{2}-\d{2})",
        r"Fecha[:\s]+(\d{2}/\d{2}/\d{4})",
        r"(\d{4}-\d{2}-\d{2})",
    ])
    # Normalizar a dd/mm/yyyy para compatibilidad con el código de carga existente
    if issue_date and re.match(r"^\d{4}-\d{2}-\d{2}$", issue_date):
        y, m, d = issue_date.split("-")
        issue_date = f"{d}/{m}/{y}"

    # Razón social = primera línea no boilerplate del texto
    workshop_name = ""
    for line in lines[:6]:
        if any(skip in line.upper() for skip in ["FACTURA", "RUC", "TEL:", "FECHA", "Nº", "N°"]):
            continue
        # filtra líneas muy cortas o que parecen direcciones genéricas
        if len(line) >= 6 and not line[0].isdigit():
            workshop_name = line
            break

    # Siniestro de referencia
    claim_number = _extract_pattern(text, [
        r"Siniestro\s*Ref[:\s]+(SIN[\-\s]?\d+(?:[\-\s]?\d+)?)",
        r"\b(SIN-\d{4}(?:-\d{1,4})?)\b",
    ])
    claim_number = (claim_number or "").replace(" ", "").upper()

    # Placa
    plate = _extract_pattern(text, [
        r"Placa[:\s]+([A-Z]{2,4}[\-\s]?\d{3,4}[A-Z]?)",
        r"\b([A-Z]{3}-?\d{4})\b",
    ])
    plate = (plate or "").replace(" ", "").upper()

    # Vehículo
    vehicle_full = _extract_pattern(text, [
        r"Veh[ií]culo[:\s]+([^\n]+)",
    ])
    vehicle_brand, vehicle_model, vehicle_year = _split_vehicle(vehicle_full or "")

    # Cliente (asegurado)
    insured_name = _extract_pattern(text, [
        r"Cliente[:\s]+([A-Za-zÁÉÍÓÚÑáéíóúñ\s\.]+?)\s+(?:Placa|C\.I)",
        r"Cliente[:\s]+([^\n]+)",
    ])

    # Items: usar tabla si existe; fallback a parseo de texto.
    items = _extract_items_simple(text, tables)

    # Totales — formato "Subtotal 15% $4806.96", "IVA 15% $721.04", "TOTAL A PAGAR $5528.00"
    subtotal = _extract_amount(text, [r"Subtotal\s+15%", r"SUBTOTAL\s+15%", r"SUBTOTAL"])
    iva = _extract_amount(text, [r"IVA\s+15%", r"IVA"])
    total = _extract_amount(text, [r"TOTAL\s+A\s+PAGAR", r"VALOR\s+TOTAL", r"TOTAL"])

    if not subtotal and items:
        subtotal = round(sum(i["total_price"] for i in items), 2)
    if not iva and subtotal:
        iva = round(subtotal * 0.15, 2)
    if not total and subtotal:
        total = round(subtotal + iva, 2)

    missing = []
    if not invoice_number:
        missing.append("numero_factura")
    if not ruc:
        missing.append("ruc")
    if not issue_date:
        missing.append("fecha_emision")
    if not claim_number:
        missing.append("siniestro_ref")

    return {
        "invoice_number": invoice_number or "",
        "ruc":            ruc or "",
        "workshop_name":  workshop_name,
        "issue_date":     issue_date or "",
        "items":          items,
        "subtotal":       subtotal or 0.0,
        "iva":            iva or 0.0,
        "total":          total or 0.0,
        "vehicle_plate":  plate,
        "vehicle":        (vehicle_full or "").strip(),
        "vehicle_brand":  vehicle_brand,
        "vehicle_model":  vehicle_model,
        "vehicle_year":   vehicle_year,
        "claim_number":   claim_number,
        "claim_type":     "",  # el formato real no codifica claim_type
        "policy_number":  "",
        "insured_name":   (insured_name or "").strip(),
        "raw_text":       text[:2000],
        "campos_faltantes": missing,
        "documentacion":  "Completa" if not missing else "Incompleta",
        "_format":        "simple",
    }


def _extract_items_simple(text: str, tables: list) -> List[Dict[str, Any]]:
    """Extrae ítems del formato simple. Las descripciones son genéricas
    (no hay códigos de tarifa); `code` queda vacío y `category` se deduce
    por keywords en la descripción."""
    items: List[Dict[str, Any]] = []

    # Tablas primero
    for table in tables:
        if not table or len(table) < 2:
            continue
        header = [str(c or "").upper().strip() for c in (table[0] or [])]
        if not any("CANT" in h for h in header):
            continue
        if not any("DESCRIP" in h for h in header):
            continue

        idx = {
            "qty":   _col_idx(header, ["CANT"]),
            "desc":  _col_idx(header, ["DESCRIPCIÓN", "DESCRIPCION"]),
            "unit":  _col_idx(header, ["V. UNITARIO", "V.UNITARIO", "UNITARIO", "UNIT"]),
            "total": _col_idx(header, ["V. TOTAL", "V.TOTAL", "TOTAL"]),
        }

        for row in table[1:]:
            if not row or all(c is None for c in row):
                continue
            try:
                desc = _cell(row, idx["desc"])
                if not desc:
                    continue
                qty = _to_float(_cell(row, idx["qty"])) or 1.0
                unit = _to_float(_cell(row, idx["unit"]))
                ttl = _to_float(_cell(row, idx["total"]))
                if not unit and not ttl:
                    continue
                items.append({
                    "code":        "",
                    "description": desc,
                    "category":    _guess_category(desc),
                    "quantity":    qty,
                    "unit_price":  unit or (ttl / qty if qty else 0),
                    "total_price": ttl or (unit * qty if unit else 0),
                })
            except (IndexError, TypeError, ZeroDivisionError):
                continue
        if items:
            return items

    # Fallback texto: "1 Descripción $123.45 $123.45"
    pattern = re.compile(
        r"^\s*(\d+(?:\.\d+)?)\s+"           # cantidad
        r"([A-Za-záéíóúñÁÉÍÓÚÑ][^\$\n]{4,80}?)\s+"  # descripción
        r"\$?\s*(\d+(?:\.\d+)?)\s+"          # unitario
        r"\$?\s*(\d+(?:\.\d+)?)\s*$",         # total
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        try:
            qty = float(m.group(1))
            desc = m.group(2).strip()
            unit = float(m.group(3))
            ttl = float(m.group(4))
            if unit < 0.5 or ttl < 0.5:
                continue
            items.append({
                "code":        "",
                "description": desc,
                "category":    _guess_category(desc),
                "quantity":    qty,
                "unit_price":  unit,
                "total_price": ttl,
            })
        except (ValueError, IndexError):
            continue
    return items


def _parse_text(text: str, tables: list) -> Dict[str, Any]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    invoice_number = _extract_pattern(
        text,
        [
            r"N[°o]\s*[:\-]?\s*([\d\-]+)",
            r"FACTURA\s+([\d\-]+)",
            r"(\d{3}-\d{3}-\d{6,9})",
        ]
    )

    ruc = _extract_pattern(
        text,
        [r"RUC[:\s]+([\d]{13})", r"(\d{13})"]
    )

    issue_date = _extract_pattern(
        text,
        [
            r"Fecha[:\s]+(\d{2}/\d{2}/\d{4})",
            r"(\d{2}/\d{2}/\d{4})",
        ]
    )

    workshop_name = ""
    for line in lines[:8]:
        if any(kw in line.upper() for kw in ["S.A.", "CIA", "LTDA", "TALLER", "AUTO", "GLASS", "GLASS"]):
            workshop_name = line
            break

    # Vehículo y siniestro (formato del generador SRI)
    plate = _extract_pattern(text, [
        r"Placa[:\s]+([A-Z]{2,4}[\-\s]?\d{3,4}[A-Z]?)",
        r"\b([A-Z]{3}-?\d{4})\b",
    ])
    vehicle_full = _extract_pattern(text, [
        r"Veh[ií]culo[:\s]+([^\n]+?)\s+SUBTOTAL",
        r"Veh[ií]culo[:\s]+([^\n]+)",
    ])
    claim_number = _extract_pattern(text, [
        r"Siniestro[:\s]+(SIN[\-\s]?\d{4}[\-\s]?\d{1,4})",
        r"(SIN-\d{4}-\d{3,4})",
    ])
    claim_type_raw = _extract_pattern(text, [
        r"Tipo\s+Siniestro[:\s]+([^\n]+?)\s+SUBTOTAL",
        r"Tipo\s+Siniestro[:\s]+([^\n]+)",
    ])
    policy = _extract_pattern(text, [
        r"P[oó]liza[:\s]+(POL[\-\s]?\d{3,6})",
        r"(POL-\d{3,6})",
    ])
    insured_name = _extract_pattern(text, [
        r"\sy\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,80}?)\s+Identifi",
    ])

    vehicle_brand, vehicle_model, vehicle_year = _split_vehicle(vehicle_full or "")

    items = _extract_items(text, tables)

    subtotal = _extract_amount(text, [r"SUBTOTAL\s+SIN\s+IMPUESTOS", r"SUBTOTAL\s+12%", r"SUBTOTAL"])
    iva      = _extract_amount(text, [r"IVA\s+15%", r"IVA\s+12%", r"IVA"])
    total    = _extract_amount(text, [r"VALOR\s+TOTAL", r"TOTAL\s+A\s+PAGAR", r"TOTAL"])

    if not subtotal and items:
        subtotal = round(sum(i["total_price"] for i in items), 2)
    if not iva and subtotal:
        iva = round(subtotal * 0.15, 2)
    if not total and subtotal:
        total = round(subtotal + iva, 2)

    missing = []
    if not invoice_number:
        missing.append("numero_factura")
    if not ruc:
        missing.append("ruc")
    if not issue_date:
        missing.append("fecha_emision")

    return {
        "invoice_number": invoice_number or "",
        "ruc":            ruc or "",
        "workshop_name":  workshop_name,
        "issue_date":     issue_date or "",
        "items":          items,
        "subtotal":       subtotal or 0.0,
        "iva":            iva or 0.0,
        "total":          total or 0.0,
        "vehicle_plate":  (plate or "").replace(" ", "").upper(),
        "vehicle":        (vehicle_full or "").strip(),
        "vehicle_brand":  vehicle_brand,
        "vehicle_model":  vehicle_model,
        "vehicle_year":   vehicle_year,
        "claim_number":   (claim_number or "").replace(" ", "").upper(),
        "claim_type":     _normalize_claim_type(claim_type_raw),
        "policy_number":  (policy or "").replace(" ", "").upper(),
        "insured_name":   (insured_name or "").strip(),
        "raw_text":       text[:2000],
        "campos_faltantes": missing,
        "documentacion":  "Completa" if not missing else "Incompleta",
    }


def _split_vehicle(vehicle_full: str) -> tuple:
    """'TOYOTA COROLLA 2022 - GRIS PLATA' → ('TOYOTA', 'COROLLA', 2022)."""
    if not vehicle_full:
        return "", "", 2024
    parts = vehicle_full.replace("-", " ").split()
    brand = parts[0] if parts else ""
    model = parts[1] if len(parts) > 1 else ""
    year = 2024
    for p in parts:
        if p.isdigit() and 1980 <= int(p) <= 2030:
            year = int(p)
            break
    return brand, model, year


def _normalize_claim_type(raw: Optional[str]) -> str:
    """'CHOQUE FRONTAL' → 'choque_frontal'."""
    if not raw:
        return ""
    s = raw.strip().lower().replace(" ", "_")
    valid = {
        "choque_frontal", "choque_lateral", "choque_trasero",
        "robo_accesorios", "daño_granizo", "rayon_pintura",
        "rotura_parabrisas", "vandalismo",
    }
    return s if s in valid else ""


def _extract_pattern(text: str, patterns: List[str]) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _extract_amount(text: str, labels: List[str]) -> Optional[float]:
    """
    Captura valor monetario de 2 decimales adyacente al label.
    Tolera prefijos tipo `12%` o `:` entre label y número.
    Requerir 2 decimales evita falso match a "12" en "SUBTOTAL 12%".
    """
    for label in labels:
        pat = rf"{label}\s*(?:\d+%\s*)?[:\s]*\$?\s*([\d,]+\.\d{{2}})"
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
    return None


def _extract_items(text: str, tables: list) -> List[Dict[str, Any]]:
    """Extrae ítems de tablas o texto estructurado."""
    items = []

    # Intentar desde tablas primero
    for table in tables:
        if not table or len(table) < 2:
            continue
        # Detectar tabla de ítems por encabezado
        header = [str(c or "").upper().strip() for c in (table[0] or [])]
        if not any(h in header for h in ["CÓDIGO", "DESCRIPCION", "DESCRIPCIÓN", "CANT", "CANTIDAD"]):
            continue

        idx = {
            "code":      _col_idx(header, ["CÓDIGO", "CODIGO", "COD"]),
            "desc":      _col_idx(header, ["DESCRIPCIÓN", "DESCRIPCION", "DETALLE"]),
            "qty":       _col_idx(header, ["CANT", "CANTIDAD"]),
            "unit":      _col_idx(header, ["P. UNIT", "PRECIO", "UNITARIO", "UNIT"]),
            "total":     _col_idx(header, ["TOTAL"]),
            "category":  _col_idx(header, ["CAT", "CATEGORÍA", "CATEGORIA"]),
        }

        for row in table[1:]:
            if not row or all(c is None for c in row):
                continue
            try:
                code = _cell(row, idx["code"])
                desc = _cell(row, idx["desc"])
                if not desc:
                    continue
                qty  = _to_float(_cell(row, idx["qty"]))
                unit = _to_float(_cell(row, idx["unit"]))
                ttl  = _to_float(_cell(row, idx["total"]))
                cat  = _cell(row, idx["category"]) or _guess_category(code or desc)

                if not unit and not ttl:
                    continue

                items.append({
                    "code":        code or "",
                    "description": desc,
                    "category":    cat,
                    "quantity":    qty or 1.0,
                    "unit_price":  unit or (ttl / (qty or 1)),
                    "total_price": ttl or (unit * (qty or 1)),
                })
            except (IndexError, TypeError, ZeroDivisionError):
                continue

    # Fallback: parsear líneas de texto si no hay tablas
    if not items:
        items = _items_from_text(text)

    return items


def _col_idx(header: List[str], candidates: List[str]) -> Optional[int]:
    for c in candidates:
        for i, h in enumerate(header):
            if c in h:
                return i
    return None


def _cell(row: list, idx: Optional[int]) -> str:
    if idx is None or idx >= len(row):
        return ""
    return str(row[idx] or "").strip()


def _to_float(val: str) -> Optional[float]:
    if not val:
        return None
    clean = re.sub(r"[^\d.]", "", val.replace(",", "."))
    try:
        return float(clean)
    except ValueError:
        return None


def _guess_category(text: str) -> str:
    t = text.upper()
    if any(k in t for k in ["REP-", "REPUESTO", "PARABRISAS", "FARO", "PUERTA", "ESPEJO", "RADIADOR"]):
        return "repuesto"
    if any(k in t for k in ["PIN-", "PINTURA", "GALON"]):
        return "pintura"
    if any(k in t for k in ["MO-", "MANO DE OBRA", "HORA"]):
        return "mano_obra"
    if any(k in t for k in ["MAT-", "LIJAS", "MASILLA", "SOLDADURA"]):
        return "material"
    if any(k in t for k in ["SRV-", "GRUA", "ALINEACION"]):
        return "servicio"
    return "general"


def _items_from_text(text: str) -> List[Dict[str, Any]]:
    """Parseo de respaldo: busca patrones precio en líneas de texto."""
    items = []
    pattern = re.compile(
        r"(REP-\w+|PIN-\w+|MO-\w+|MAT-\w+|SRV-\w+)?\s*"
        r"([A-Za-záéíóúÁÉÍÓÚüÜñÑ][^\$\n]{5,50}?)\s+"
        r"(\d+(?:\.\d+)?)\s+\$?\s*(\d+(?:\.\d+)?)\s+\$?\s*(\d+(?:\.\d+)?)"
    )
    for m in pattern.finditer(text):
        try:
            code = (m.group(1) or "").strip()
            desc = m.group(2).strip()
            qty  = float(m.group(3))
            unit = float(m.group(4))
            ttl  = float(m.group(5))
            if unit < 0.5 or ttl < 0.5:
                continue
            items.append({
                "code":        code,
                "description": desc,
                "category":    _guess_category(code + desc),
                "quantity":    qty,
                "unit_price":  unit,
                "total_price": ttl,
            })
        except (ValueError, IndexError):
            continue
    return items
