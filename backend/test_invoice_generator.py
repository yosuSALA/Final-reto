"""
Generador aleatorio de facturas PDF de prueba.

Cada llamada genera una factura única (RUC, número, items, valores aleatorios) con
formato compatible con el SRI de Ecuador:
  • Bloque emisor (razón social, dirección, contribuyente especial, obligado contabilidad).
  • Caja de factura derecha con RUC, No., autorización, ambiente, emisión, clave de acceso.
  • Bloque comprador.
  • Tabla items SRI: COD. PRINCIPAL / DESCRIPCIÓN / CANT. / P. UNIT. / DESC. / TOTAL.
  • Caja de valores: SUBTOTAL 12%, SUBTOTAL 0%, NO OBJ. IVA, EXENTO, SIN IMPUESTOS,
    DESCUENTO, IVA 15%, VALOR TOTAL.

Escenarios:
  • limpia      → items dentro de tarifario.
  • sobrecobro  → un item +30-60% sobre tarifario.
  • fraude      → ítem duplicado + ítem incoherente con el siniestro.
  • mixed       → aleatorio entre los 3 anteriores.
"""
from __future__ import annotations

import os
import random
import shutil
import string
from datetime import datetime, timedelta
from typing import Dict, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


OUTPUT_DIR_DEFAULT = "backend/test_pdfs"


# ──────────────────────────────────────────────────────────────────────────────
# Pools de datos realistas (Ecuador)
# ──────────────────────────────────────────────────────────────────────────────

WORKSHOPS_POOL = [
    {
        "razon_social": "AUTOFIX SERVICIOS AUTOMOTRICES S.A.",
        "comercial": "AutoFix",
        "address": "Av. Francisco de Orellana N32-145 y Eloy Alfaro, Edificio Trade Building, Piso 5, Guayaquil, Guayas",
        "phone": "(04) 222-3344",
        "email": "facturacion@autofix.ec",
        "contribuyente_especial": "5829",
    },
    {
        "razon_social": "TALLERPRO CIA. LTDA.",
        "comercial": "TallerPro",
        "address": "Av. 10 de Agosto N24-455 y Cordero, Quito, Pichincha",
        "phone": "(02) 333-4455",
        "email": "info@tallerpro.ec",
        "contribuyente_especial": "1247",
    },
    {
        "razon_social": "CARGLASS EXPRESS DEL ECUADOR S.A.",
        "comercial": "CarGlass",
        "address": "Av. de las Américas Km 2.5 frente al CC Mall del Sol, Guayaquil, Guayas",
        "phone": "(04) 999-1122",
        "email": "ventas@carglass.com.ec",
        "contribuyente_especial": "8341",
    },
    {
        "razon_social": "MULTISERVICIOS AUTOMOTRICES DEL PACIFICO MULSERVAUTO S.A.",
        "comercial": "MulservAuto",
        "address": "Av. Juan Tanca Marengo Km 4.5, Lotización Los Vergeles, Guayaquil, Guayas",
        "phone": "(04) 280-0011",
        "email": "facturacion@mulservauto.com",
        "contribuyente_especial": "3920",
    },
    {
        "razon_social": "TECNICENTRO LATINOAMERICANO TECLAT S.A.S.",
        "comercial": "TecLat",
        "address": "Av. Galo Plaza Lasso N52-31 y Joaquín Mancheno, Sector Carcelén, Quito",
        "phone": "(02) 281-7755",
        "email": "ventas@teclat.ec",
        "contribuyente_especial": "6582",
    },
    {
        "razon_social": "CHEVROCENTRO DEL SUR CHEVROSUR CIA. LTDA.",
        "comercial": "ChevroSur",
        "address": "Av. 25 de Julio Km 4.5 vía Puerto Marítimo, Guayaquil",
        "phone": "(04) 480-5566",
        "email": "info@chevrosur.ec",
        "contribuyente_especial": "1098",
    },
    {
        "razon_social": "TALLER MECANICO LOS ANDES S.A.",
        "comercial": "Los Andes",
        "address": "Av. Simón Bolívar y Av. Eloy Alfaro, Sector La Carolina, Quito",
        "phone": "(02) 245-9911",
        "email": "contacto@losandestaller.com",
        "contribuyente_especial": "4471",
    },
]

CLIENTS_POOL = [
    ("CARLOS ANDRES MENDOZA VERA", "0912345678"),
    ("MARIA FERNANDA LOPEZ RIVERA", "1718273645"),
    ("ROBERTO JAVIER ANDRADE QUISHPE", "1709876543"),
    ("ANDREA CAROLINA VILLAVICENCIO SOLANO", "0915678901"),
    ("JORGE ALBERTO PARRALES BERMUDEZ", "0907654321"),
    ("PATRICIA ESTRELLA SALAZAR MORA", "1712345678"),
    ("DIEGO FERNANDO CABRERA MENDOZA", "0918765432"),
    ("LUIS GABRIEL ESPINOZA TORRES", "1722334455"),
]

# Subset del tarifario (debe coincidir con seed_data)
TARIFFS = [
    {"code": "REP-PAR01", "desc": "PARABRISAS DELANTERO", "max": 280.00, "qty_max": 1,
     "aplica": ["daño_granizo", "rotura_parabrisas", "choque_frontal", "vandalismo"]},
    {"code": "REP-FAR01", "desc": "FARO DELANTERO (UNIDAD)", "max": 150.00, "qty_max": 2,
     "aplica": ["choque_frontal", "vandalismo"]},
    {"code": "REP-FAR02", "desc": "FARO TRASERO (UNIDAD)", "max": 120.00, "qty_max": 2,
     "aplica": ["choque_trasero", "vandalismo"]},
    {"code": "REP-GUA01", "desc": "GUARDACHOQUE DELANTERO", "max": 350.00, "qty_max": 1,
     "aplica": ["choque_frontal"]},
    {"code": "REP-GUA02", "desc": "GUARDACHOQUE TRASERO", "max": 320.00, "qty_max": 1,
     "aplica": ["choque_trasero"]},
    {"code": "REP-PUE01", "desc": "PUERTA LATERAL (UNIDAD)", "max": 450.00, "qty_max": 2,
     "aplica": ["choque_lateral", "vandalismo"]},
    {"code": "REP-CAP01", "desc": "CAPO DELANTERO", "max": 380.00, "qty_max": 1,
     "aplica": ["choque_frontal", "daño_granizo"]},
    {"code": "REP-ESP01", "desc": "ESPEJO RETROVISOR (UNIDAD)", "max": 85.00, "qty_max": 2,
     "aplica": ["choque_lateral", "robo_accesorios", "vandalismo"]},
    {"code": "REP-RAD01", "desc": "RADIADOR", "max": 200.00, "qty_max": 1,
     "aplica": ["choque_frontal"]},
    {"code": "REP-MOT01", "desc": "SOPORTE DE MOTOR", "max": 180.00, "qty_max": 2,
     "aplica": ["choque_frontal"]},
    {"code": "PIN-BASE01", "desc": "PINTURA BASE (GALON)", "max": 45.00, "qty_max": 2,
     "aplica": ["choque_frontal", "choque_lateral", "choque_trasero", "daño_granizo", "rayon_pintura"]},
    {"code": "PIN-ACAB01", "desc": "PINTURA ACABADO (GALON)", "max": 65.00, "qty_max": 2,
     "aplica": ["choque_frontal", "rayon_pintura", "daño_granizo"]},
    {"code": "MAT-LIJ01", "desc": "KIT LIJAS Y MASILLA", "max": 35.00, "qty_max": 3,
     "aplica": ["choque_frontal", "choque_lateral", "rayon_pintura"]},
    {"code": "MO-MEC01", "desc": "MANO DE OBRA MECANICA (HORA)", "max": 25.00, "qty_max": 20,
     "aplica": ["choque_frontal", "choque_lateral", "choque_trasero", "robo_accesorios"]},
    {"code": "MO-PIN01", "desc": "MANO DE OBRA PINTURA (HORA)", "max": 22.00, "qty_max": 15,
     "aplica": ["rayon_pintura", "daño_granizo", "choque_frontal"]},
    {"code": "MO-LAM01", "desc": "MANO DE OBRA LATONERIA (HORA)", "max": 28.00, "qty_max": 20,
     "aplica": ["choque_frontal", "choque_lateral", "choque_trasero", "daño_granizo"]},
    {"code": "REP-VID01", "desc": "VIDRIO VENTANA LATERAL", "max": 120.00, "qty_max": 2,
     "aplica": ["choque_lateral", "robo_accesorios", "vandalismo"]},
    {"code": "REP-CER01", "desc": "CERRADURA PUERTA", "max": 65.00, "qty_max": 4,
     "aplica": ["robo_accesorios", "vandalismo"]},
    {"code": "REP-RAD02", "desc": "RADIO/CONSOLA", "max": 250.00, "qty_max": 1,
     "aplica": ["robo_accesorios"]},
    {"code": "SRV-GRU01", "desc": "SERVICIO DE GRUA", "max": 80.00, "qty_max": 1,
     "aplica": ["choque_frontal", "choque_lateral", "choque_trasero"]},
]

CLAIMS_POOL = [
    {"num": "SIN-2026-001", "type": "choque_frontal", "plate": "GYE-1234",
     "vehicle": "TOYOTA COROLLA 2022 - GRIS PLATA", "policy": "POL-50001"},
    {"num": "SIN-2026-002", "type": "robo_accesorios", "plate": "PCH-5678",
     "vehicle": "HYUNDAI TUCSON 2023 - BLANCO", "policy": "POL-50002"},
    {"num": "SIN-2026-003", "type": "daño_granizo", "plate": "GYE-9012",
     "vehicle": "KIA SPORTAGE 2021 - NEGRO", "policy": "POL-50003"},
    {"num": "SIN-2026-004", "type": "choque_lateral", "plate": "GYE-3456",
     "vehicle": "CHEVROLET SAIL 2020 - ROJO", "policy": "POL-50004"},
    {"num": "SIN-2026-005", "type": "rayon_pintura", "plate": "PCH-7890",
     "vehicle": "NISSAN SENTRA 2023 - AZUL MARINO", "policy": "POL-50005"},
]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers aleatorios
# ──────────────────────────────────────────────────────────────────────────────

def _random_invoice_number() -> str:
    estab = f"{random.randint(1, 7):03d}"
    punto = f"{random.randint(1, 5):03d}"
    secuencial = f"{random.randint(1, 999_999_999):09d}"
    return f"{estab}-{punto}-{secuencial}"


def _random_ruc() -> str:
    provincia = random.choice(["09", "17", "01", "06", "13"])
    middle = "".join(random.choices(string.digits, k=8))
    return f"{provincia}{middle}001"


def _random_clave_acceso(fecha: datetime, ruc: str, invoice_num: str) -> str:
    """49 dígitos formato SRI."""
    parts = invoice_num.split("-")
    serie = (parts[0] + parts[1])[:6]
    secuencial = parts[2][:9].rjust(9, "0")
    numerico = "".join(random.choices(string.digits, k=8))
    base = (
        fecha.strftime("%d%m%Y")
        + "01"
        + ruc
        + "1"
        + serie
        + secuencial
        + numerico
        + "1"
    )
    factores = [2, 3, 4, 5, 6, 7]
    suma = sum(int(d) * factores[i % 6] for i, d in enumerate(reversed(base)))
    digit = 11 - (suma % 11)
    if digit == 11:
        digit = 0
    elif digit == 10:
        digit = 1
    return base + str(digit)


def _gen_items(scenario: str, claim_type: str) -> List[Dict]:
    aplicables = [t for t in TARIFFS if claim_type in t["aplica"]]
    if not aplicables:
        aplicables = TARIFFS[:6]

    if scenario == "mixed":
        scenario = random.choice(["limpia", "sobrecobro", "fraude"])

    items: List[Dict] = []
    n_normal = random.randint(2, 5)
    base_pool = aplicables if len(aplicables) >= n_normal else (aplicables + random.sample(TARIFFS, n_normal))
    sample_normal = random.sample(base_pool, min(n_normal, len(base_pool)))
    for t in sample_normal:
        qty = random.randint(1, max(1, int(t["qty_max"])))
        unit = round(t["max"] * random.uniform(0.85, 1.0), 2)
        items.append({"code": t["code"], "description": t["desc"],
                      "quantity": qty, "unit_price": unit})

    if scenario == "sobrecobro":
        t = random.choice(aplicables)
        unit = round(t["max"] * random.uniform(1.30, 1.65), 2)
        items.append({"code": t["code"], "description": t["desc"],
                      "quantity": random.randint(1, max(1, int(t["qty_max"]))),
                      "unit_price": unit})

    if scenario == "fraude":
        t = random.choice(aplicables)
        dup_unit = round(t["max"] * random.uniform(0.95, 1.05), 2)
        items.append({"code": t["code"], "description": t["desc"],
                      "quantity": 1, "unit_price": dup_unit})
        items.append({"code": t["code"], "description": t["desc"],
                      "quantity": 1, "unit_price": dup_unit})
        no_aplicables = [x for x in TARIFFS if claim_type not in x["aplica"]]
        if no_aplicables:
            t2 = random.choice(no_aplicables)
            items.append({"code": t2["code"], "description": t2["desc"],
                          "quantity": 1,
                          "unit_price": round(t2["max"] * random.uniform(0.9, 1.05), 2)})

    random.shuffle(items)
    return items


def _expected_label(scenario: str) -> str:
    return {
        "limpia": "Aprobado (sin hallazgos)",
        "sobrecobro": "WARNING/CRITICAL — Sobrecobro",
        "fraude": "CRITICAL — Duplicado + Incoherencia",
        "mixed": "Aleatorio (limpia / sobrecobro / fraude)",
    }.get(scenario, "Aleatorio")


# ──────────────────────────────────────────────────────────────────────────────
# PDF builder — formato SRI Ecuador
# ──────────────────────────────────────────────────────────────────────────────

def _build_invoice_pdf(filepath: str, workshop: Dict, factura_meta: Dict,
                       items: List[Dict], output_dir: str) -> tuple:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            rightMargin=36, leftMargin=36, topMargin=32, bottomMargin=32)
    styles = getSampleStyleSheet()
    p_xs = ParagraphStyle("Xs", parent=styles["Normal"], fontSize=6.8, leading=8.5)
    p_sm = ParagraphStyle("Sm", parent=styles["Normal"], fontSize=8, leading=10)
    p_smb = ParagraphStyle("SmB", parent=styles["Normal"], fontSize=8, leading=10,
                           fontName="Helvetica-Bold")
    p_title = ParagraphStyle("Title", parent=styles["Normal"], fontSize=11, leading=13,
                             fontName="Helvetica-Bold")
    p_factura = ParagraphStyle("FactT", parent=styles["Normal"], fontSize=14,
                               alignment=1, fontName="Helvetica-Bold")
    p_clave = ParagraphStyle("Clave", parent=styles["Normal"], fontSize=6.5,
                             leading=8, fontName="Courier")

    elements = []

    # ── HEADER ──
    emisor_lines = [
        Paragraph(workshop["razon_social"], p_title),
        Spacer(1, 2),
        Paragraph(f"<b>Nombre Comercial:</b> {workshop['comercial']}", p_xs),
        Paragraph(f"<b>Dirección Matriz:</b> {workshop['address']}", p_xs),
        Paragraph(f"<b>Dirección Sucursal:</b> {workshop['address']}", p_xs),
        Paragraph(f"<b>Contribuyente Especial Nro:</b> {workshop['contribuyente_especial']}", p_xs),
        Paragraph("<b>OBLIGADO A LLEVAR CONTABILIDAD:</b> SI", p_xs),
        Paragraph(f"<b>Tel:</b> {workshop['phone']} &nbsp;&nbsp; <b>Email:</b> {workshop['email']}", p_xs),
    ]

    factura_box_data = [
        [Paragraph(f"<b>R.U.C.:</b> {factura_meta['ruc']}", p_sm)],
        [Paragraph("FACTURA", p_factura)],
        [Paragraph(f"<b>No.</b> {factura_meta['invoice_number']}", p_sm)],
        [Paragraph(f"<b>NÚMERO DE AUTORIZACIÓN:</b><br/>{factura_meta['clave_acceso']}", p_clave)],
        [Paragraph(f"<b>FECHA Y HORA AUTORIZACIÓN:</b><br/>{factura_meta['fecha_autorizacion']}", p_xs)],
        [Paragraph("<b>AMBIENTE:</b> PRODUCCIÓN<br/><b>EMISIÓN:</b> NORMAL", p_xs)],
        [Paragraph(f"<b>CLAVE DE ACCESO:</b><br/>{factura_meta['clave_acceso']}", p_clave)],
    ]
    factura_box = Table(factura_box_data, colWidths=[230])
    factura_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.9, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    emisor_box = Table([[emisor_lines]], colWidths=[280])
    emisor_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.9, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    header_t = Table([[emisor_box, factura_box]], colWidths=[290, 240])
    header_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_t)
    elements.append(Spacer(1, 8))

    # ── COMPRADOR ──
    comp_data = [
        [Paragraph("<b>Razón Social / Nombres y Apellidos:</b>", p_xs),
         Paragraph(factura_meta["client_name"], p_xs),
         Paragraph("<b>Identificación:</b>", p_xs),
         Paragraph(factura_meta["client_id"], p_xs)],
        [Paragraph("<b>Fecha Emisión:</b>", p_xs),
         Paragraph(factura_meta["issue_date"], p_xs),
         Paragraph("<b>Guía Remisión:</b>", p_xs),
         Paragraph("-", p_xs)],
        [Paragraph("<b>Dirección:</b>", p_xs),
         Paragraph(factura_meta.get("client_address", "-"), p_xs),
         Paragraph("<b>Placa:</b>", p_xs),
         Paragraph(factura_meta.get("plate", "-"), p_xs)],
    ]
    comp_t = Table(comp_data, colWidths=[120, 200, 75, 135])
    comp_t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.9, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(comp_t)
    elements.append(Spacer(1, 8))

    # ── ITEMS ──
    head = ["CÓD. PRINCIPAL", "DESCRIPCIÓN", "CANT.", "P. UNIT.", "DESC.", "TOTAL"]
    data = [head]
    subtotal = 0.0
    for it in items:
        ttl = round(it["quantity"] * it["unit_price"], 2)
        subtotal += ttl
        data.append([
            it["code"],
            Paragraph(it["description"], p_xs),
            f"{it['quantity']:.0f}",
            f"{it['unit_price']:.2f}",
            "0.00",
            f"{ttl:.2f}",
        ])
    items_t = Table(data, colWidths=[80, 220, 45, 60, 45, 65])
    items_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(items_t)
    elements.append(Spacer(1, 6))

    # ── INFO ADICIONAL + VALORES ──
    iva_pct = 15
    iva = round(subtotal * iva_pct / 100, 2)
    total = round(subtotal + iva, 2)

    info_data = [
        [Paragraph("<b>Información Adicional</b>", p_smb), ""],
        [Paragraph("<b>Vehículo:</b>", p_xs), Paragraph(factura_meta.get("vehicle", "-"), p_xs)],
        [Paragraph("<b>Siniestro:</b>", p_xs), Paragraph(factura_meta.get("claim_number", "-"), p_xs)],
        [Paragraph("<b>Tipo Siniestro:</b>", p_xs),
         Paragraph(factura_meta.get("claim_type", "-").replace("_", " ").upper(), p_xs)],
        [Paragraph("<b>Póliza:</b>", p_xs), Paragraph(factura_meta.get("policy", "-"), p_xs)],
        [Paragraph("<b>Forma de Pago:</b>", p_xs),
         Paragraph("TRANSFERENCIA / DÉBITO BANCARIO", p_xs)],
    ]
    info_t = Table(info_data, colWidths=[100, 200])
    info_t.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    valores = [
        ["SUBTOTAL 12%", f"{subtotal:.2f}"],
        ["SUBTOTAL 0%", "0.00"],
        ["SUBTOTAL NO OBJ. IVA", "0.00"],
        ["SUBTOTAL EXENTO IVA", "0.00"],
        ["SUBTOTAL SIN IMPUESTOS", f"{subtotal:.2f}"],
        ["DESCUENTO", "0.00"],
        [f"IVA {iva_pct}%", f"{iva:.2f}"],
        ["VALOR TOTAL", f"{total:.2f}"],
    ]
    val_t = Table(valores, colWidths=[140, 80])
    val_t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTSIZE", (0, -1), (-1, -1), 9.5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    foot_t = Table([[info_t, val_t]], colWidths=[305, 225])
    foot_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(foot_t)

    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "<font color='#64748b' size='7'>Documento generado automáticamente como FACTURA DE PRUEBA "
        "para el sistema Auditor Agéntico HackIATon 2026. Sin validez tributaria.</font>",
        styles["Normal"]))

    doc.build(elements)
    return filepath, subtotal, iva, total


# ──────────────────────────────────────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────────────────────────────────────

def generate_random_invoice(scenario: str = "mixed",
                             output_dir: str = OUTPUT_DIR_DEFAULT,
                             claim_override: Dict | None = None) -> Dict:
    """Genera un PDF aleatorio + retorna metadata para preview en UI."""
    workshop = random.choice(WORKSHOPS_POOL)
    client_name, client_id = random.choice(CLIENTS_POOL)
    claim = claim_override or random.choice(CLAIMS_POOL)

    fecha = datetime.now() - timedelta(days=random.randint(0, 25),
                                        hours=random.randint(0, 23),
                                        minutes=random.randint(0, 59))
    invoice_num = _random_invoice_number()
    ruc = _random_ruc()
    clave = _random_clave_acceso(fecha, ruc, invoice_num)

    factura_meta = {
        "ruc": ruc,
        "invoice_number": invoice_num,
        "issue_date": fecha.strftime("%d/%m/%Y"),
        "fecha_autorizacion": fecha.strftime("%d/%m/%Y %H:%M:%S"),
        "clave_acceso": clave,
        "client_name": client_name,
        "client_id": client_id,
        "client_address": "ASEGURADORA HACKIATON 2026 - Av. Amazonas N34-451 y Atahualpa, Quito, Pichincha",
        "vehicle": claim["vehicle"],
        "plate": claim["plate"],
        "claim_number": claim["num"],
        "claim_type": claim["type"],
        "policy": claim["policy"],
    }

    items = _gen_items(scenario, claim["type"])

    suffix = datetime.now().strftime("%H%M%S") + str(random.randint(100, 999))
    filename = f"factura_{scenario}_{invoice_num.replace('-', '')}_{suffix}.pdf"
    filepath = os.path.join(output_dir, filename)
    _, subtotal, iva, total = _build_invoice_pdf(filepath, workshop, factura_meta, items, output_dir)

    return {
        "filename": filename,
        "scenario": scenario,
        "workshop_name": workshop["razon_social"],
        "workshop_comercial": workshop["comercial"],
        "ruc": ruc,
        "invoice_number": invoice_num,
        "issue_date": factura_meta["issue_date"],
        "client_name": client_name,
        "client_id": client_id,
        "claim_number": claim["num"],
        "claim_type": claim["type"],
        "vehicle": claim["vehicle"],
        "plate": claim["plate"],
        "items_count": len(items),
        "items_preview": [
            {
                "code": i["code"],
                "description": i["description"],
                "quantity": i["quantity"],
                "unit_price": i["unit_price"],
                "total_price": round(i["quantity"] * i["unit_price"], 2),
            }
            for i in items
        ],
        "subtotal": round(subtotal, 2),
        "iva": round(iva, 2),
        "total": round(total, 2),
        "expected_finding": _expected_label(scenario),
        "size_kb": round(os.path.getsize(filepath) / 1024, 1),
        "path": filepath,
    }


def generate_random_batch(scenarios: List[str],
                           output_dir: str = OUTPUT_DIR_DEFAULT) -> List[Dict]:
    return [generate_random_invoice(s, output_dir) for s in scenarios]


# ── Backward compat con los 3 nombres fijos previos ──────────────────────────

SCENARIOS = {
    "factura_limpia.pdf": {"label": "Limpia (sin hallazgos)", "scenario": "limpia",
                            "description": "Factura aleatoria con items dentro de tarifario."},
    "factura_sobrecobro.pdf": {"label": "Sobrecobro (WARNING/CRITICAL)", "scenario": "sobrecobro",
                                "description": "Factura aleatoria con un item +30-65% sobre tarifario."},
    "factura_fraude.pdf": {"label": "Fraude crítico (duplicado + incoherencia)", "scenario": "fraude",
                            "description": "Factura aleatoria con duplicado e item incoherente con el siniestro."},
}


def generate_test_invoice(name: str, output_dir: str = OUTPUT_DIR_DEFAULT) -> str:
    if name not in SCENARIOS:
        raise ValueError(f"Escenario desconocido: {name}")
    info = generate_random_invoice(SCENARIOS[name]["scenario"], output_dir)
    canonical = os.path.join(output_dir, name)
    shutil.copy(info["path"], canonical)
    return canonical


def generate_all_test_invoices(output_dir: str = OUTPUT_DIR_DEFAULT) -> List[Dict]:
    """Compat: genera los 3 con nombres fijos (contenido aleatorio cada llamada)."""
    out = []
    for name, scen in SCENARIOS.items():
        info = generate_random_invoice(scen["scenario"], output_dir)
        canonical = os.path.join(output_dir, name)
        shutil.copy(info["path"], canonical)
        try:
            os.remove(info["path"])
        except OSError:
            pass
        out.append({
            "filename": name,
            "label": scen["label"],
            "description": scen["description"],
            "path": canonical,
            "size_kb": round(os.path.getsize(canonical) / 1024, 1),
        })
    return out


if __name__ == "__main__":
    res = generate_all_test_invoices()
    for r in res:
        print(f"  [OK] {r['filename']}  ({r['size_kb']} KB) - {r['label']}")
