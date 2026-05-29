"""
Extractor del PDF "Parte Policial — Noticia del Incidente"
(Ministerio del Interior — República del Ecuador).

Fuente de referencia: synthetic_data/PARTE POLICIAL/

La estructura del documento es una tabla con etiquetas; el texto extraído
suele venir como pares "Label: Valor" pegados en la misma línea.
"""
from __future__ import annotations

import io
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ── Helpers ────────────────────────────────────────────────────────────


def _read_pages(pdf_bytes: bytes) -> Tuple[str, list]:
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("Instalar pdfplumber: pip install pdfplumber")

    tables: list = []
    text_parts: List[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
            try:
                for t in page.extract_tables():
                    tables.append(t)
            except Exception:
                pass
    return "\n".join(text_parts), tables


def _clean(value: Optional[str]) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip(" :")


def _grab(text: str, label: str, until_labels: List[str]) -> str:
    """Captura el valor que sigue a `Label:` hasta el siguiente label conocido
    o hasta fin de línea / fin de texto."""
    until_alt = "|".join(re.escape(u) + r"\s*:" for u in until_labels)
    pat = rf"{re.escape(label)}\s*:\s*(.*?)(?=\s+(?:{until_alt})|$)"
    m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return ""
    val = m.group(1)
    # Cortar en saltos de línea para campos cortos
    val = val.split("\n")[0]
    return _clean(val)


def _grab_multiline(text: str, label: str, stops: List[str]) -> str:
    """Captura un bloque (puede atravesar líneas) hasta uno de los marcadores
    `stops` (matchea por línea que CONTENGA el marcador)."""
    lines = text.splitlines()
    out: List[str] = []
    capturing = False
    lbl_pat = re.compile(rf"^\s*{re.escape(label)}\s*:?", re.IGNORECASE)
    stops_lc = [s.lower() for s in stops]
    for ln in lines:
        if not capturing:
            m = lbl_pat.search(ln)
            if m:
                capturing = True
                tail = ln[m.end():].strip(" :")
                if tail:
                    out.append(tail)
            continue
        if any(s in ln.lower() for s in stops_lc):
            break
        if not ln.strip():
            continue
        if "DOCUMENTO SINTÉTICO" in ln.upper() or "DOCUMENTO SINTETICO" in ln.upper():
            continue
        out.append(ln.strip())
    return _clean(" ".join(out))


def _parse_date(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _parse_datetime(raw_date: str, raw_time: str) -> Optional[datetime]:
    base = _parse_date(raw_date)
    if not base:
        return None
    t = (raw_time or "").strip()
    m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", t)
    if m:
        hh, mm, ss = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
        try:
            return base.replace(hour=hh, minute=mm, second=ss)
        except ValueError:
            pass
    return base


# Tipos de accidente reconocidos (orden = orden de aparición en el PDF)
_ACCIDENT_TYPE_LABELS = [
    "Atropello", "Arrollamiento", "Caida Pasajero", "Choque Frontal",
    "Choque Lateral", "Choque Alcance", "Colision",
    "Atipico", "Estrellamiento", "Perdida Pista", "Roce",
    "Volcamiento", "Rozamiento", "Robo",
]


def _extract_accident_types(text: str) -> List[str]:
    """Busca patrones [X] LABEL o [ ] LABEL y devuelve los marcados con X.

    El PDF parte a veces los checkboxes en dos líneas (los `[X]/[ ]` en una
    línea y los labels en la siguiente). En ese caso reconstruimos por orden
    posicional: enumeramos checkboxes y labels en la región entre
    'Informacion del Accidente' y 'Consecuencias', y asociamos por índice.
    """
    marked: List[str] = []

    # 1. Caso directo: "[X] Robo", "[X] Colision" — match en una línea
    for label in _ACCIDENT_TYPE_LABELS:
        label_pat = re.escape(label).replace(r"\ ", r"\s+")
        pat = rf"\[\s*([Xx])\s*\]\s*{label_pat}"
        if re.search(pat, text):
            slug = label.lower().replace(" ", "_")
            if slug not in marked:
                marked.append(slug)

    if marked:
        return marked

    # 2. Fallback: el documento parte checkboxes y labels en dos líneas.
    # Aislamos la región y enumeramos en orden de aparición.
    region_match = re.search(
        r"Informacion del Accidente de Transito(.*?)Consecuencias",
        text, re.DOTALL | re.IGNORECASE,
    )
    if not region_match:
        return marked
    region = region_match.group(1)

    # Tokens en orden: cada [X] o [ ], y cada palabra-label conocida
    box_iter = list(re.finditer(r"\[\s*([Xx ])\s*\]", region))
    if not box_iter:
        return marked

    # Construye la secuencia esperada de labels por ORDEN POSICIONAL.
    # Como los labels pueden estar fragmentados ("Choque" arriba, "Frontal" abajo),
    # juntamos todas las palabras "etiqueta" del region en orden y reconstruimos
    # por proximidad espacial — heurística simple: descartamos el caso compuesto
    # y dejamos el match por keyword único.
    SIMPLE_KEYWORDS = {
        "atropello": "atropello",
        "arrollamiento": "arrollamiento",
        "colision": "colision",
        "colisión": "colision",
        "atipico": "atipico",
        "atípico": "atipico",
        "estrellamiento": "estrellamiento",
        "roce": "roce",
        "volcamiento": "volcamiento",
        "rozamiento": "rozamiento",
        "robo": "robo",
    }
    # Para "Choque Frontal/Lateral/Alcance" usamos el sufijo (Frontal, Lateral, Alcance)
    SUFFIX_KEYWORDS = {
        "frontal": "choque_frontal",
        "lateral": "choque_lateral",
        "alcance": "choque_alcance",
        "pasajero": "caida_pasajero",
        "pista": "perdida_pista",
    }

    # Concatena todo el region, ya secuenciado, y matchea por checkbox seguido del label
    # más cercano (en el texto) hacia adelante.
    for m in box_iter:
        is_marked = m.group(1).lower() == "x"
        if not is_marked:
            continue
        # Look ahead: palabras hasta el siguiente "[" o fin
        after = region[m.end():]
        next_box = re.search(r"\[", after)
        chunk = after[:next_box.start()] if next_box else after
        words = re.findall(r"[A-Za-záéíóúñÁÉÍÓÚÑ]+", chunk)
        slug = None
        for w in words:
            lw = w.lower()
            if lw in SIMPLE_KEYWORDS:
                slug = SIMPLE_KEYWORDS[lw]
                break
            if lw in SUFFIX_KEYWORDS:
                slug = SUFFIX_KEYWORDS[lw]
                break
        if slug and slug not in marked:
            marked.append(slug)

    return marked


# ── Extractor principal ────────────────────────────────────────────────


def extract_police_report_from_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    text, tables = _read_pages(pdf_bytes)

    # Cabecera — "Doc ID: DOC-0012" (no confundir con "Doc ID Sistema: DOC-0054")
    m = re.search(r"Doc\s*ID(?!\s*Sistema)\s*[:\s]+([A-Z]{3,}-?\d+)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"Doc\s*ID\s+Sistema\s*[:\s]+([A-Z]{3,}-?\d+)", text, re.IGNORECASE)
    doc_id = m.group(1).strip() if m else ""
    m = re.search(r"Siniestro\s*[:\s]+(SIN[\-\s]?\d+)", text, re.IGNORECASE)
    siniestro_ref = m.group(1).replace(" ", "").upper() if m else ""
    m = re.search(r"Parte\s*Policial\s*No\s*[:\s]+([A-Z0-9]+)", text, re.IGNORECASE)
    parte_no = m.group(1).strip() if m else ""

    # "Fecha de Elaboracion: 2026-03-22 Hora: 13:55:00 Parte Policial No: ..."
    fecha_elab_raw = _grab(text, "Fecha de Elaboracion", ["Hora", "Parte Policial No"]) \
        or _grab(text, "Fecha de Elaboración", ["Hora", "Parte Policial No"])
    hora_elab = _grab(text, "Hora", ["Parte Policial No", "Servicio Policial"])
    fecha_elaboracion = _parse_datetime(fecha_elab_raw, hora_elab)
    servicio_policial = _grab(text, "Servicio Policial", ["Identificacion", "Identificación", "Zona"])

    # Unidad de policía
    zona = _grab(text, "Zona", ["Sub Zona", "Distrito"])
    sub_zona = _grab(text, "Sub Zona", ["Distrito", "Circuito"])
    distrito = _grab(text, "Distrito", ["Circuito", "Sub Circuito"])
    circuito = _grab(text, "Circuito", ["Sub Circuito", "Unidad"])
    sub_circuito = _grab(text, "Sub Circuito", ["Unidad", "Identificacion"])
    unidad = _grab(text, "Unidad", ["Identificacion", "Identificación", "Calle 1"])

    # Geográfica/cronológica
    # Las calles pueden ocupar 2 líneas; capturamos hasta la siguiente label.
    calle_1 = _grab_multiline(text, "Calle 1", ["Calle 2", "Fecha del Hecho", "Tipo de via"])
    calle_2 = _grab_multiline(text, "Calle 2", ["Tipo de via", "Hora Aproximada", "Composicion"])

    fecha_hecho_raw = _grab(text, "Fecha del Hecho", ["Hora Aproximada", "Tipo de via"])
    hora_aproximada = _grab(text, "Hora Aproximada", ["Tipo de via", "Composicion"])
    fecha_hecho = _parse_datetime(fecha_hecho_raw, hora_aproximada)

    tipo_via = _grab(text, "Tipo de via", ["Composicion", "Estado via"])
    composicion = _grab(text, "Composicion", ["Estado via", "Carriles"]) \
        or _grab(text, "Composición", ["Estado via", "Carriles"])
    estado_via = _grab(text, "Estado via", ["Carriles", "Semaforos"]) \
        or _grab(text, "Estado vía", ["Carriles", "Semaforos"])
    carriles = _grab(text, "Carriles", ["Semaforos", "Alumbrado"])
    semaforos = _grab(text, "Semaforos", ["Alumbrado", "Latitud"]) \
        or _grab(text, "Semáforos", ["Alumbrado", "Latitud"])
    alumbrado = _grab(text, "Alumbrado", ["Latitud", "Longitud"])
    latitud = _grab(text, "Latitud", ["Longitud", "Clasificacion", "Clasificación"])
    longitud = _grab(text, "Longitud", ["Clasificacion", "Clasificación", "Informacion del Accidente"])

    # Clasificación
    clasificacion_tipo = _grab(text, "Tipo", ["Flagrancia", "Operativo"])
    # "Tipo" puede colisionar con "Tipo de via", así que filtramos cuando matcheó esa frase
    if clasificacion_tipo and "via" in clasificacion_tipo.lower():
        clasificacion_tipo = ""
    flagrancia = _grab(text, "Flagrancia", ["Operativo", "Informacion del Accidente"])
    operativo = _grab(text, "Operativo", ["Informacion del Accidente", "Atropello"])

    # Tipos de accidente
    tipos_accidente = _extract_accident_types(text)

    # Consecuencias / Clima / Día festivo
    consecuencias = _grab(text, "Consecuencias", ["Clima", "Dia Festivo"])
    clima = _grab(text, "Clima", ["Dia Festivo", "Día Festivo", "Circunstancias"])
    dia_festivo = _grab(text, "Dia Festivo", ["Circunstancias", "Parte Elevado"]) \
        or _grab(text, "Día Festivo", ["Circunstancias", "Parte Elevado"])

    circunstancias = _grab_multiline(
        text,
        "Circunstancias del Hecho",
        stops=["Parte Elevado", "PARTICIPANTE", "Personal Policial"],
    )
    parte_elevado_a = _grab(text, "Parte Elevado al Sr/a", ["PARTICIPANTE", "Personal Policial"])

    # Participante 1 (conductor)
    p1_nombre = _grab(text, "Apellidos y Nombres", ["Cedula", "Cédula"])
    p1_cedula = _grab(text, "Cedula", ["Edad", "Sexo"]) or _grab(text, "Cédula", ["Edad", "Sexo"])
    p1_edad_raw = _grab(text, "Edad", ["Sexo", "Estado", "Tipo Licencia"])
    p1_sexo = _grab(text, "Sexo", ["Estado", "Tipo Licencia"])
    p1_estado = _grab(text, "Estado", ["Tipo Licencia", "Detenido"])
    # "Estado" puede pisar "Estado via" → si es así, descartar
    if p1_estado and "via" in p1_estado.lower():
        p1_estado = ""
    p1_tipo_licencia = _grab(text, "Tipo Licencia", ["Detenido", "Observaciones"])
    p1_detenido = _grab(text, "Detenido", ["Observaciones", "Vehiculo Placa", "Vehículo Placa"])
    p1_observaciones = _grab_multiline(
        text,
        "Observaciones",
        stops=["Vehiculo Placa", "Vehículo Placa", "Personal Policial"],
    )

    try:
        p1_edad = int(re.sub(r"[^\d]", "", p1_edad_raw)) if p1_edad_raw else None
    except (TypeError, ValueError):
        p1_edad = None

    # Vehículo principal (primer bloque después de "Vehiculo Placa XXX")
    veh_placa = ""
    m = re.search(r"Vehiculo\s+Placa\s+([A-Z0-9\-]+)", text, re.IGNORECASE) \
        or re.search(r"Vehículo\s+Placa\s+([A-Z0-9\-]+)", text, re.IGNORECASE)
    if m:
        veh_placa = m.group(1).replace(" ", "").upper()

    # Placa (campo dentro del bloque del vehículo)
    if not veh_placa:
        veh_placa = _grab(text, "Placa", ["Marca", "Modelo"])

    veh_marca = _grab(text, "Marca", ["Modelo", "Tipo", "Ano Fab"])
    veh_modelo = _grab(text, "Modelo", ["Tipo", "Ano Fab", "Año Fab"])
    veh_tipo = _grab(text, "Tipo", ["Ano Fab", "Año Fab", "Color"])
    if veh_tipo and "administrativo" in veh_tipo.lower():
        # falso positivo con el Tipo de la clasificación
        veh_tipo = ""
    veh_anio_raw = _grab(text, "Ano Fab", ["Color", "Motor"]) or _grab(text, "Año Fab", ["Color", "Motor"])
    veh_color = _grab(text, "Color", ["Motor", "Chasis"])
    veh_motor = _grab(text, "Motor", ["Chasis", "Estado"])
    veh_chasis = _grab(text, "Chasis", ["Estado", "Personal Policial"])
    veh_estado = _grab_multiline(text, "Estado", stops=["Personal Policial", "Grado"])

    try:
        veh_anio = int(re.sub(r"[^\d]", "", veh_anio_raw)) if veh_anio_raw else None
    except (TypeError, ValueError):
        veh_anio = None

    # Personal policial: tabla con Grado | Apellidos y Nombres | Servicio | Funcion | Firma
    personal: List[Dict[str, str]] = []
    for tbl in tables:
        if not tbl or len(tbl) < 2:
            continue
        header = [str(c or "").upper().strip() for c in (tbl[0] or [])]
        if any("GRADO" in h for h in header) and any("SERVICIO" in h for h in header):
            for row in tbl[1:]:
                if not row or all(c is None for c in row):
                    continue
                personal.append({
                    "grado": _clean(str(row[0] or "")) if len(row) > 0 else "",
                    "nombre": _clean(str(row[1] or "")) if len(row) > 1 else "",
                    "servicio": _clean(str(row[2] or "")) if len(row) > 2 else "",
                    "funcion": _clean(str(row[3] or "")) if len(row) > 3 else "",
                })

    return {
        "doc_id": doc_id,
        "siniestro_ref": siniestro_ref,
        "parte_no": parte_no,
        "fecha_elaboracion": fecha_elaboracion.isoformat() if fecha_elaboracion else None,
        "servicio_policial": servicio_policial,

        "zona": zona, "sub_zona": sub_zona, "distrito": distrito,
        "circuito": circuito, "sub_circuito": sub_circuito, "unidad": unidad,

        "calle_1": calle_1, "calle_2": calle_2,
        "fecha_hecho": fecha_hecho.isoformat() if fecha_hecho else None,
        "hora_aproximada": hora_aproximada,
        "tipo_via": tipo_via, "composicion": composicion, "estado_via": estado_via,
        "carriles": carriles, "semaforos": semaforos, "alumbrado": alumbrado,
        "latitud": latitud, "longitud": longitud,

        "clasificacion_tipo": clasificacion_tipo,
        "flagrancia": flagrancia,
        "operativo": operativo,
        "tipos_accidente": tipos_accidente,

        "consecuencias": consecuencias,
        "clima": clima,
        "dia_festivo": dia_festivo,
        "circunstancias": circunstancias,
        "parte_elevado_a": parte_elevado_a,

        "p1_nombre": p1_nombre,
        "p1_cedula": p1_cedula,
        "p1_edad": p1_edad,
        "p1_sexo": p1_sexo,
        "p1_estado": p1_estado,
        "p1_tipo_licencia": p1_tipo_licencia,
        "p1_detenido": p1_detenido,
        "p1_observaciones": p1_observaciones,

        "veh_placa": veh_placa,
        "veh_marca": veh_marca,
        "veh_modelo": veh_modelo,
        "veh_tipo": veh_tipo,
        "veh_anio": veh_anio,
        "veh_color": veh_color,
        "veh_motor": veh_motor,
        "veh_chasis": veh_chasis,
        "veh_estado": veh_estado,

        "personal_policial": personal,
        "raw_text_preview": text[:2500],
    }
