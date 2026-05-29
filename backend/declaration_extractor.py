"""
Extractor del PDF "Formulario de Reclamación para Accidentes de Vehículo"
(FR.RE.100 v01 — Aseguradora del Sur).

Fuente de referencia: synthetic_data/DECLARACIÓN DE ACCIDENTE/

El formulario tiene estructura fija; los campos están marcados con "•" y
muchos comparten línea (p. ej. "• Marca X • Modelo Y • Tipo Z").

La función pública es `extract_declaration_from_pdf(pdf_bytes) -> dict`.
"""
from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


# ── Helpers ────────────────────────────────────────────────────────────


def _read_text(pdf_bytes: bytes) -> str:
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("Instalar pdfplumber: pip install pdfplumber")

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        raw = "\n".join((p.extract_text() or "") for p in pdf.pages)
    # El bullet "•" se exporta a veces como "(cid:127)" porque la fuente no
    # tiene mapping a Unicode. Normalizamos para que los regex matchen.
    return raw.replace("(cid:127)", "•").replace("(cid:1)", "")


def _clean(value: Optional[str]) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip(" •\t")


def _inline_field(line: str, label: str) -> str:
    """Captura el valor de un campo "• LABEL ..." dentro de una línea
    posiblemente compartida con otros campos separados por "•".
    """
    pat = rf"•\s*{re.escape(label)}\s+(.*?)(?=\s*•|$)"
    m = re.search(pat, line, re.IGNORECASE)
    return _clean(m.group(1)) if m else ""


def _find_inline(lines: List[str], label: str) -> str:
    for ln in lines:
        if label.lower() in ln.lower():
            v = _inline_field(ln, label)
            if v:
                return v
    return ""


def _block_after(lines: List[str], marker: str, stop_markers: List[str]) -> str:
    """Devuelve las líneas que siguen a `marker` hasta el siguiente marker
    (sección o cualquiera de `stop_markers`). El marker puede aparecer al final
    de una línea ("...:"); en ese caso solo capturamos las siguientes líneas.
    """
    result: List[str] = []
    capturing = False
    marker_lc = marker.lower()
    stops_lc = [s.lower() for s in stop_markers]

    for raw in lines:
        ln = raw.strip()
        ln_lc = ln.lower()
        if not capturing:
            if marker_lc in ln_lc:
                capturing = True
                # Si en la misma línea quedó texto tras el marker, capturarlo
                idx = ln_lc.find(marker_lc) + len(marker_lc)
                tail = ln[idx:].strip(" :•")
                if tail:
                    result.append(tail)
            continue
        # Capturando
        if any(s in ln_lc for s in stops_lc):
            break
        # Líneas vacías o boilerplate del documento no aportan
        if not ln or "DOCUMENTO SINTÉTICO" in ln or "DOCUMENTO SINTETICO" in ln:
            continue
        # Una nueva sección suele empezar con "•" — si es un campo nuevo, romper
        if ln.startswith("•"):
            break
        result.append(ln)

    return _clean(" ".join(result))


def _parse_date_es(raw: str) -> Optional[datetime]:
    """Parsea fechas en formato europeo. Tolera 15-01-2025, 15/01/2025,
    "27 de Enero de 2025", "27 de enero de 2025"."""
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass

    meses = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
        "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
        "noviembre": 11, "diciembre": 12,
    }
    m = re.search(r"(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})", raw, re.IGNORECASE)
    if m:
        day, mon, year = int(m.group(1)), meses.get(m.group(2).lower()), int(m.group(3))
        if mon:
            try:
                return datetime(year, mon, day)
            except ValueError:
                pass
    return None


# ── Extractor principal ────────────────────────────────────────────────


def extract_declaration_from_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    text = _read_text(pdf_bytes)
    lines = [ln for ln in (raw.strip() for raw in text.splitlines()) if ln]

    # Cabecera: "Doc ID: DOC-0952 | Siniestro: SIN-0378 | Pág. 1"
    m = re.search(r"Doc\s*ID\s*[:\s]+([A-Z0-9\-]+)", text)
    doc_id = m.group(1).strip() if m else ""
    m = re.search(r"Siniestro\s*[:\s]+(SIN[\-\s]?\d+)", text, re.IGNORECASE)
    siniestro_ref = m.group(1).replace(" ", "").upper() if m else ""
    m = re.search(r"Modo[:\s]+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)", text)
    modo = m.group(1).strip() if m else ""

    # Asegurado
    asegurado_nombre = _find_inline(lines, "Asegurado")
    asegurado_email = _find_inline(lines, "Correo electrónico") or _find_inline(lines, "Correo electronico")
    asegurado_direccion = _find_inline(lines, "Dirección") or _find_inline(lines, "Direccion")
    asegurado_telefono = _find_inline(lines, "Teléfono") or _find_inline(lines, "Telefono")
    poliza_numero = _find_inline(lines, "Póliza") or _find_inline(lines, "Poliza")
    item = _find_inline(lines, "Ítem") or _find_inline(lines, "Item")
    agente = _find_inline(lines, "Agente")

    # Vehículo asegurado
    veh_marca = _find_inline(lines, "Marca")
    veh_modelo = _find_inline(lines, "Modelo")
    veh_tipo = _find_inline(lines, "Tipo")
    veh_color = _find_inline(lines, "Color")
    veh_placa = _find_inline(lines, "Placa")
    veh_motor = _find_inline(lines, "Motor")
    veh_chasis = _find_inline(lines, "Chasis")

    veh_detalle_danos = _block_after(
        lines,
        "Detalle de daños",
        stop_markers=["¿En dónde se halla el vehículo", "DATOS DEL ACCIDENTE"],
    ) or _block_after(
        lines,
        "Detalle de danos",
        stop_markers=["DATOS DEL ACCIDENTE"],
    )
    veh_lugar_inspeccion = _find_inline(
        lines, "¿En dónde se halla el vehículo para su inspección?"
    ) or _find_inline(lines, "halla el vehículo para su inspección")

    # Accidente
    accidente_lugar = _find_inline(lines, "Lugar")
    accidente_velocidad = _find_inline(lines, "Velocidad")
    accidente_fecha_raw = _find_inline(lines, "Fecha")
    accidente_hora = _find_inline(lines, "Hora")
    accidente_viniendo_de = _find_inline(lines, "Viniendo de")
    accidente_direccion_a = _find_inline(lines, "Con dirección a") or _find_inline(lines, "Con direccion a")
    accidente_descripcion = _block_after(
        lines,
        "Explique detalladamente cómo ocurrió el accidente",
        stop_markers=["A juicio del conductor", "CONDUCTOR DEL VEHÍCULO ASEGURADO"],
    ) or _block_after(
        lines,
        "Explique detalladamente",
        stop_markers=["CONDUCTOR DEL VEHÍCULO ASEGURADO"],
    )
    accidente_responsable = _find_inline(
        lines, "A juicio del conductor, ¿quién es el responsable?"
    )

    # Conductor del vehículo asegurado
    conductor_nombre = _find_inline(lines, "Nombres y apellidos")
    conductor_cedula = _find_inline(lines, "No. Cédula") or _find_inline(lines, "No. Cedula")
    conductor_categoria = _find_inline(lines, "Categoría") or _find_inline(lines, "Categoria")
    conductor_valido_hasta = _find_inline(lines, "Válido hasta") or _find_inline(lines, "Valido hasta")

    # Conductor: Dirección y Teléfono aparecen DESPUÉS de "CONDUCTOR DEL VEHÍCULO ASEGURADO"
    # y antes del bloque del contrario. Re-extraemos en esa franja para no chocar con la
    # dirección del Asegurado (capturada arriba).
    conductor_direccion = ""
    conductor_telefono = ""
    in_conductor_block = False
    for ln in lines:
        if "CONDUCTOR DEL VEHÍCULO ASEGURADO" in ln.upper() or "CONDUCTOR DEL VEHICULO ASEGURADO" in ln.upper():
            in_conductor_block = True
            continue
        if not in_conductor_block:
            continue
        if "DATOS SOBRE EL CONTRARIO" in ln.upper():
            break
        if "Dirección" in ln or "Direccion" in ln:
            if not conductor_direccion:
                conductor_direccion = _inline_field(ln, "Dirección") or _inline_field(ln, "Direccion")
        if "Teléfono" in ln or "Telefono" in ln:
            if not conductor_telefono:
                conductor_telefono = _inline_field(ln, "Teléfono") or _inline_field(ln, "Telefono")

    # Contrario — reusamos parsing por sección
    contrario_marca = contrario_modelo = contrario_placa = ""
    contrario_color = contrario_aseguradora = contrario_propietario = ""
    contrario_detalle = ""
    contrario_lugar_inspeccion = ""
    in_contrario = False
    contrario_lines: List[str] = []
    for ln in lines:
        if "DATOS SOBRE EL CONTRARIO" in ln.upper():
            in_contrario = True
            continue
        if not in_contrario:
            continue
        if "INTERVENCIÓN DE AUTORIDADES" in ln.upper() or "INTERVENCION DE AUTORIDADES" in ln.upper():
            break
        contrario_lines.append(ln)

    if contrario_lines:
        contrario_marca = _find_inline(contrario_lines, "Marca")
        contrario_modelo = _find_inline(contrario_lines, "Modelo")
        contrario_placa = _find_inline(contrario_lines, "Placa")
        contrario_color = _find_inline(contrario_lines, "Color")
        contrario_aseguradora = _find_inline(contrario_lines, "Asegurado en compañía") or _find_inline(contrario_lines, "Asegurado en compania")
        contrario_propietario = _find_inline(contrario_lines, "Nombre del propietario")
        contrario_detalle = _block_after(
            contrario_lines,
            "Detalle de daños al contrario",
            stop_markers=["¿En dónde se halla para inspección", "Testigos del accidente"],
        ) or _block_after(
            contrario_lines,
            "Detalle de danos al contrario",
            stop_markers=["Testigos del accidente"],
        )
        contrario_lugar_inspeccion = _find_inline(contrario_lines, "¿En dónde se halla para inspección?") or _find_inline(contrario_lines, "halla para inspección")

    testigos = _find_inline(lines, "Testigos del accidente")

    # Intervención de autoridades
    autoridades_agentes = _find_inline(lines, "¿Qué agentes tomaron nota del parte?") or _find_inline(lines, "agentes tomaron nota del parte")
    autoridades_juzgado = _find_inline(lines, "¿Qué juzgado interviene?") or _find_inline(lines, "juzgado interviene")
    autoridades_detenido = _find_inline(lines, "¿Está detenido el conductor?") or _find_inline(lines, "detenido el conductor")
    autoridades_asistencia = _find_inline(lines, "Lugar donde se recibe asistencia médica") or _find_inline(lines, "Lugar donde se recibe asistencia medica")

    # Fecha de firma: "En Quito a 27 de Enero de 2025"
    fecha_firma = None
    m = re.search(r"En\s+\S+\s+a\s+(.+?)\s*$", text, re.IGNORECASE | re.MULTILINE)
    if m:
        fecha_firma = _parse_date_es(m.group(1).strip())

    return {
        "doc_id": doc_id,
        "siniestro_ref": siniestro_ref,
        "modo": modo,
        "fecha_firma": fecha_firma.isoformat() if fecha_firma else None,

        "asegurado_nombre": asegurado_nombre,
        "asegurado_email": asegurado_email,
        "asegurado_direccion": asegurado_direccion,
        "asegurado_telefono": asegurado_telefono,
        "poliza_numero": poliza_numero,
        "item": item,
        "agente": agente,

        "veh_marca": veh_marca,
        "veh_modelo": veh_modelo,
        "veh_tipo": veh_tipo,
        "veh_color": veh_color,
        "veh_placa": veh_placa.upper().replace(" ", "") if veh_placa else "",
        "veh_motor": veh_motor,
        "veh_chasis": veh_chasis,
        "veh_detalle_danos": veh_detalle_danos,
        "veh_lugar_inspeccion": veh_lugar_inspeccion,

        "accidente_lugar": accidente_lugar,
        "accidente_velocidad": accidente_velocidad,
        "accidente_fecha": _parse_date_es(accidente_fecha_raw).isoformat() if _parse_date_es(accidente_fecha_raw) else None,
        "accidente_fecha_raw": accidente_fecha_raw,
        "accidente_hora": accidente_hora,
        "accidente_viniendo_de": accidente_viniendo_de,
        "accidente_direccion_a": accidente_direccion_a,
        "accidente_descripcion": accidente_descripcion,
        "accidente_responsable": accidente_responsable,

        "conductor_nombre": conductor_nombre,
        "conductor_direccion": conductor_direccion,
        "conductor_telefono": conductor_telefono,
        "conductor_cedula": conductor_cedula,
        "conductor_categoria_licencia": conductor_categoria,
        "conductor_licencia_valida_hasta": conductor_valido_hasta,

        "contrario_marca": contrario_marca,
        "contrario_modelo": contrario_modelo,
        "contrario_placa": contrario_placa.upper().replace(" ", "") if contrario_placa else "",
        "contrario_color": contrario_color,
        "contrario_aseguradora": contrario_aseguradora,
        "contrario_propietario": contrario_propietario,
        "contrario_detalle_danos": contrario_detalle,
        "contrario_lugar_inspeccion": contrario_lugar_inspeccion,

        "testigos": testigos,
        "autoridades_agentes": autoridades_agentes,
        "autoridades_juzgado": autoridades_juzgado,
        "autoridades_detenido": autoridades_detenido,
        "autoridades_lugar_asistencia_medica": autoridades_asistencia,

        "raw_text_preview": text[:2000],
    }
