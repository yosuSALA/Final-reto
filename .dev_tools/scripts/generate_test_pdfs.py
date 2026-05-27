"""
Generador de PDFs de prueba para el Auditor Agéntico de Facturación de Siniestros.
Genera: 5 facturas de taller + tabla de tipos de siniestro + tarifario acordado.
Ejecutar: python generate_test_pdfs.py
"""
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

OUTPUT_DIR = "test_pdfs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Paleta ──────────────────────────────────────────────
AZUL_OSCURO = colors.HexColor("#1a2b4a")
AZUL_MEDIO  = colors.HexColor("#2d5086")
AZUL_CLARO  = colors.HexColor("#e8f0fb")
ROJO        = colors.HexColor("#c0392b")
NARANJA     = colors.HexColor("#e67e22")
VERDE       = colors.HexColor("#1e8449")
GRIS_CLARO  = colors.HexColor("#f5f5f5")
GRIS_MEDIO  = colors.HexColor("#cccccc")

# ── Estilos ─────────────────────────────────────────────
styles = getSampleStyleSheet()

def estilo(nombre, padre="Normal", **kw):
    s = ParagraphStyle(nombre, parent=styles[padre], **kw)
    return s

S_TITULO    = estilo("Titulo",    fontSize=18, textColor=AZUL_OSCURO, spaceAfter=2, leading=22, alignment=TA_CENTER)
S_SUBTITULO = estilo("Subtitulo", fontSize=11, textColor=AZUL_MEDIO,  spaceAfter=4, leading=14, alignment=TA_CENTER)
S_BOLD      = estilo("Bold",      fontSize=9,  fontName="Helvetica-Bold")
S_NORMAL    = estilo("Normal9",   fontSize=9)
S_SMALL     = estilo("Small",     fontSize=7.5, textColor=colors.gray)
S_HEADER    = estilo("Header",    fontSize=8,  fontName="Helvetica-Bold", textColor=colors.white)
S_DERECHA   = estilo("Derecha",   fontSize=9,  alignment=TA_RIGHT)
S_CENTRO    = estilo("Centro",    fontSize=9,  alignment=TA_CENTER)
S_ADVERTENCIA = estilo("Advert",  fontSize=8,  textColor=ROJO, fontName="Helvetica-Bold")

# ── Datos: Talleres ──────────────────────────────────────
TALLERES = {
    1: {"nombre": "AutoFix S.A.",        "ruc": "0992847561001", "dir": "Av. Juan Tanca Marengo Km 4.5, Guayaquil", "tel": "04-2345678"},
    2: {"nombre": "TallerPro Cia. Ltda.","ruc": "0991234567001", "dir": "Cdla. Kennedy Norte, Guayaquil",            "tel": "04-3456789"},
    3: {"nombre": "CarGlass Ecuador",     "ruc": "0990987654001", "dir": "Via Daule Km 10, Guayaquil",               "tel": "04-4567890"},
}

# ── Datos: Siniestros + Facturas ──────────────────────────
now = datetime(2026, 5, 6)

FACTURAS = [
    {
        "siniestro": "SIN-2026-001",
        "tipo":      "Choque Frontal",
        "descripcion":"Choque frontal leve en interseccion",
        "placa":     "GYE-1234",
        "marca":     "Toyota Corolla 2022",
        "poliza":    "POL-50001",
        "asegurado": "Carlos Mendoza",
        "fecha_sin": now - timedelta(days=15),
        "factura":   "001-001-000045",
        "taller":    1,
        "fecha_fac": now - timedelta(days=10),
        "items": [
            ("REP-GUA01", "Guardachoque delantero",        "repuesto",   1, 340.00),
            ("REP-FAR01", "Faro delantero (unidad)",       "repuesto",   1, 145.00),
            ("MO-MEC01",  "Mano de obra mecánica (hora)",  "mano_obra",  8,  25.00),
        ],
        "anomalia":  None,
        "severidad": None,
    },
    {
        "siniestro": "SIN-2026-002",
        "tipo":      "Robo de Accesorios",
        "descripcion":"Robo de accesorios en estacionamiento",
        "placa":     "GYE-5678",
        "marca":     "Hyundai Tucson 2023",
        "poliza":    "POL-50002",
        "asegurado": "Maria Fernanda Lopez",
        "fecha_sin": now - timedelta(days=12),
        "factura":   "001-002-000123",
        "taller":    2,
        "fecha_fac": now - timedelta(days=7),
        "items": [
            ("REP-ESP01", "Espejo retrovisor (unidad)",    "repuesto",   2,  82.00),
            ("REP-RAD02", "Radio/Consola",                 "repuesto",   1, 245.00),
            ("REP-CER01", "Cerradura puerta",              "repuesto",   2,  63.00),
            ("MO-MEC01",  "Mano de obra mecánica (hora)",  "mano_obra",  5,  33.75),
        ],
        "anomalia":  "SOBRECOBRO: MO mecánica $33.75/h (tarifario $25.00 + 10% tol. = $27.50) — exceso +35%",
        "severidad": "WARNING",
    },
    {
        "siniestro": "SIN-2026-003",
        "tipo":      "Daño por Granizo",
        "descripcion":"Daño por granizo en vehículo estacionado",
        "placa":     "GYE-9012",
        "marca":     "Kia Sportage 2021",
        "poliza":    "POL-50003",
        "asegurado": "Roberto Andrade",
        "fecha_sin": now - timedelta(days=20),
        "factura":   "001-003-000067",
        "taller":    3,
        "fecha_fac": now - timedelta(days=5),
        "items": [
            ("REP-PAR01", "Parabrisas delantero",          "repuesto",   1, 275.00),
            ("REP-PAR01", "Parabrisas delantero",          "repuesto",   1, 275.00),
            ("MO-LAM01",  "Mano de obra latonería (hora)", "mano_obra",  6,  27.00),
            ("PIN-BASE01","Pintura base (galón)",          "pintura",    1,  42.00),
            ("MAT-LIJ01", "Kit lijas y masilla",           "material",   2,  34.00),
        ],
        "anomalia":  "DUPLICADO: Parabrisas delantero (REP-PAR01) cobrado 2 veces — sobrecobro $275.00",
        "severidad": "CRITICAL",
    },
    {
        "siniestro": "SIN-2026-004",
        "tipo":      "Choque Lateral",
        "descripcion":"Choque lateral en avenida principal",
        "placa":     "GYE-3456",
        "marca":     "Chevrolet Sail 2020",
        "poliza":    "POL-50004",
        "asegurado": "Andrea Villavicencio",
        "fecha_sin": now - timedelta(days=8),
        "factura":   "001-001-000046",
        "taller":    1,
        "fecha_fac": now - timedelta(days=3),
        "items": [
            ("REP-PUE01", "Puerta lateral (unidad)",       "repuesto",   1, 440.00),
            ("REP-MOT01", "Soporte de motor",              "repuesto",   1, 175.00),
            ("MO-LAM01",  "Mano de obra latonería (hora)", "mano_obra",  8,  27.00),
            ("PIN-ACAB01","Pintura acabado (galón)",       "pintura",    1,  62.00),
            ("MAT-LIJ01", "Kit lijas y masilla",           "material",   1,  33.00),
        ],
        "anomalia":  "INCOHERENCIA: Soporte de motor (REP-MOT01) no corresponde a siniestro de choque lateral/puerta",
        "severidad": "CRITICAL",
    },
    {
        "siniestro": "SIN-2026-005",
        "tipo":      "Rayón en Pintura",
        "descripcion":"Rayón en puerta y guardachoque",
        "placa":     "GYE-7890",
        "marca":     "Nissan Sentra 2023",
        "poliza":    "POL-50005",
        "asegurado": "Jorge Parrales",
        "fecha_sin": now - timedelta(days=5),
        "factura":   "001-002-000124",
        "taller":    2,
        "fecha_fac": now - timedelta(days=2),
        "items": [
            ("PIN-BASE01","Pintura base (galón)",          "pintura",    5,  44.00),
            ("PIN-ACAB01","Pintura acabado (galón)",       "pintura",    1,  63.00),
            ("MAT-LIJ01", "Kit lijas y masilla",           "material",   2,  32.00),
            ("MO-PIN01",  "Mano de obra pintura (hora)",   "mano_obra",  6,  21.00),
        ],
        "anomalia":  "CANTIDAD ANÓMALA: Pintura base 5 galones (máx. esperado: 2 gal) para rayón menor",
        "severidad": "WARNING",
    },
]

# ── Colores por severidad ────────────────────────────────
COLOR_SEVERIDAD = {
    "CRITICAL": ROJO,
    "WARNING":  NARANJA,
    None:       VERDE,
}

LABEL_SEVERIDAD = {
    "CRITICAL": "CRITICO",
    "WARNING":  "ADVERTENCIA",
    None:       "LIMPIA",
}


# ═══════════════════════════════════════════════════════════
# Generador de factura individual
# ═══════════════════════════════════════════════════════════

def generar_factura(datos: dict, num: int):
    taller  = TALLERES[datos["taller"]]
    nombre_archivo = os.path.join(
        OUTPUT_DIR,
        f"factura_{num:02d}_{datos['siniestro'].replace('-','_')}.pdf"
    )
    doc = SimpleDocTemplate(
        nombre_archivo,
        pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )

    elems = []

    # ── Cabecera taller ──────────────────────────────────
    cab_datos = [
        [Paragraph(f"<b>{taller['nombre']}</b>", estilo("TN", fontSize=14, textColor=colors.white, leading=18)),
         Paragraph("FACTURA", estilo("FA", fontSize=20, textColor=colors.white, alignment=TA_RIGHT, fontName="Helvetica-Bold"))],
        [Paragraph(f"RUC: {taller['ruc']}", estilo("RS", fontSize=8, textColor=AZUL_CLARO)),
         Paragraph(f"N° <b>{datos['factura']}</b>", estilo("NF", fontSize=10, textColor=colors.white, alignment=TA_RIGHT))],
        [Paragraph(f"{taller['dir']}", estilo("AD", fontSize=7.5, textColor=AZUL_CLARO)),
         Paragraph(f"Fecha: {datos['fecha_fac'].strftime('%d/%m/%Y')}", estilo("FD", fontSize=8, textColor=AZUL_CLARO, alignment=TA_RIGHT))],
        [Paragraph(f"Tel: {taller['tel']}", estilo("TE", fontSize=7.5, textColor=AZUL_CLARO)),
         Paragraph("Autorización SRI: 2306202600123456789", estilo("SR", fontSize=7, textColor=AZUL_CLARO, alignment=TA_RIGHT))],
    ]
    t_cab = Table(cab_datos, colWidths=[10*cm, 7.5*cm])
    t_cab.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), AZUL_OSCURO),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING",(0,0), (-1,-1), 8),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
    ]))
    elems.append(t_cab)
    elems.append(Spacer(1, 5*mm))

    # ── Severidad badge ──────────────────────────────────
    color_sev = COLOR_SEVERIDAD[datos["severidad"]]
    label_sev = LABEL_SEVERIDAD[datos["severidad"]]
    badge_texto = f"Estado auditoría: {label_sev}"
    badge_datos = [[Paragraph(badge_texto, estilo("BDG", fontSize=9, textColor=colors.white, fontName="Helvetica-Bold", alignment=TA_CENTER))]]
    t_badge = Table(badge_datos, colWidths=[17.5*cm])
    t_badge.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), color_sev),
        ("TOPPADDING",   (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
    ]))
    elems.append(t_badge)
    elems.append(Spacer(1, 4*mm))

    # ── Datos del siniestro ──────────────────────────────
    sin_datos = [
        [Paragraph("<b>DATOS DEL SINIESTRO Y ASEGURADO</b>", estilo("DH", fontSize=9, textColor=colors.white, fontName="Helvetica-Bold")),
         "", "", ""],
        [Paragraph("<b>N° Siniestro:</b>", S_BOLD), Paragraph(datos["siniestro"], S_NORMAL),
         Paragraph("<b>Tipo:</b>", S_BOLD), Paragraph(datos["tipo"], S_NORMAL)],
        [Paragraph("<b>Asegurado:</b>", S_BOLD), Paragraph(datos["asegurado"], S_NORMAL),
         Paragraph("<b>Póliza:</b>", S_BOLD), Paragraph(datos["poliza"], S_NORMAL)],
        [Paragraph("<b>Vehículo:</b>", S_BOLD), Paragraph(datos["marca"], S_NORMAL),
         Paragraph("<b>Placa:</b>", S_BOLD), Paragraph(datos["placa"], S_NORMAL)],
        [Paragraph("<b>Descripción:</b>", S_BOLD), Paragraph(datos["descripcion"], S_NORMAL),
         Paragraph("<b>Fecha siniestro:</b>", S_BOLD), Paragraph(datos["fecha_sin"].strftime("%d/%m/%Y"), S_NORMAL)],
    ]
    t_sin = Table(sin_datos, colWidths=[3.5*cm, 5*cm, 3.5*cm, 5.5*cm])
    t_sin.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), AZUL_MEDIO),
        ("SPAN",         (0,0), (-1,0)),
        ("BACKGROUND",   (0,1), (-1,-1), AZUL_CLARO),
        ("GRID",         (0,0), (-1,-1), 0.5, GRIS_MEDIO),
        ("TOPPADDING",   (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
    ]))
    elems.append(t_sin)
    elems.append(Spacer(1, 5*mm))

    # ── Tabla de ítems ───────────────────────────────────
    items_header = [
        Paragraph("CÓDIGO",       S_HEADER),
        Paragraph("DESCRIPCIÓN",  S_HEADER),
        Paragraph("CAT.",         S_HEADER),
        Paragraph("CANT.",        S_HEADER),
        Paragraph("P. UNIT.",     S_HEADER),
        Paragraph("TOTAL",        S_HEADER),
    ]
    items_rows = [items_header]

    subtotal = 0.0
    for i, (cod, desc, cat, qty, up) in enumerate(datos["items"]):
        total_item = qty * up
        subtotal += total_item
        bg = GRIS_CLARO if i % 2 == 0 else colors.white

        # Marcar duplicados (mismo código que fila anterior)
        es_dup = i > 0 and datos["items"][i][0] == datos["items"][i-1][0]

        items_rows.append([
            Paragraph(cod,  estilo(f"C{i}", fontSize=8, fontName="Helvetica-Bold" if es_dup else "Helvetica", textColor=ROJO if es_dup else colors.black)),
            Paragraph(desc, estilo(f"D{i}", fontSize=8, textColor=ROJO if es_dup else colors.black)),
            Paragraph(cat,  estilo(f"T{i}", fontSize=7.5, textColor=colors.gray)),
            Paragraph(f"{qty:.0f}",           estilo(f"Q{i}", fontSize=8, alignment=TA_CENTER)),
            Paragraph(f"$ {up:>8.2f}",        estilo(f"U{i}", fontSize=8, alignment=TA_RIGHT)),
            Paragraph(f"$ {total_item:>8.2f}", estilo(f"L{i}", fontSize=8, alignment=TA_RIGHT)),
        ])

    iva     = round(subtotal * 0.15, 2)
    total   = round(subtotal + iva, 2)

    t_items = Table(items_rows, colWidths=[2.8*cm, 6.2*cm, 2.2*cm, 1.5*cm, 2.4*cm, 2.4*cm])
    item_style = [
        ("BACKGROUND",   (0,0), (-1,0), AZUL_OSCURO),
        ("GRID",         (0,0), (-1,-1), 0.5, GRIS_MEDIO),
        ("TOPPADDING",   (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("LEFTPADDING",  (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
    ]
    for i in range(1, len(items_rows)):
        bg = GRIS_CLARO if i % 2 == 1 else colors.white
        item_style.append(("BACKGROUND", (0,i), (-1,i), bg))

    t_items.setStyle(TableStyle(item_style))
    elems.append(t_items)
    elems.append(Spacer(1, 3*mm))

    # ── Totales ──────────────────────────────────────────
    totales_data = [
        ["", "", Paragraph("<b>SUBTOTAL:</b>",    S_BOLD), Paragraph(f"$ {subtotal:.2f}", S_DERECHA)],
        ["", "", Paragraph("<b>IVA 15%:</b>",     S_BOLD), Paragraph(f"$ {iva:.2f}",     S_DERECHA)],
        ["", "", Paragraph("<b>TOTAL:</b>",        estilo("TOT", fontSize=11, fontName="Helvetica-Bold", textColor=AZUL_OSCURO)), Paragraph(f"$ {total:.2f}", estilo("TV", fontSize=11, fontName="Helvetica-Bold", textColor=AZUL_OSCURO, alignment=TA_RIGHT))],
    ]
    t_tot = Table(totales_data, colWidths=[8*cm, 3.5*cm, 3.5*cm, 2.5*cm])
    t_tot.setStyle(TableStyle([
        ("BACKGROUND",   (2,2), (-1,2), AZUL_CLARO),
        ("LINEABOVE",    (2,2), (-1,2), 1.5, AZUL_MEDIO),
        ("TOPPADDING",   (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0), (-1,-1), 3),
        ("RIGHTPADDING", (3,0), (3,-1),  6),
    ]))
    elems.append(t_tot)
    elems.append(Spacer(1, 5*mm))

    # ── Anomalía (si existe) ─────────────────────────────
    if datos["anomalia"]:
        anom_data = [[
            Paragraph(f"⚠ ANOMALÍA DETECTADA [{datos['severidad']}]: {datos['anomalia']}",
                      estilo("AOM", fontSize=8.5, textColor=colors.white, fontName="Helvetica-Bold"))
        ]]
        t_anom = Table(anom_data, colWidths=[17.5*cm])
        t_anom.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,-1), COLOR_SEVERIDAD[datos["severidad"]]),
            ("TOPPADDING",   (0,0), (-1,-1), 6),
            ("BOTTOMPADDING",(0,0), (-1,-1), 6),
            ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ]))
        elems.append(t_anom)
        elems.append(Spacer(1, 4*mm))

    # ── Firmas ───────────────────────────────────────────
    elems.append(HRFlowable(width="100%", thickness=1, color=GRIS_MEDIO))
    elems.append(Spacer(1, 5*mm))
    firmas_data = [[
        Paragraph("_______________________\n<b>Firma del Taller</b>",
                  estilo("FT", fontSize=8, alignment=TA_CENTER)),
        Paragraph("_______________________\n<b>Firma del Asegurado</b>",
                  estilo("FA2", fontSize=8, alignment=TA_CENTER)),
        Paragraph("_______________________\n<b>Revisado Auditor</b>",
                  estilo("RA", fontSize=8, alignment=TA_CENTER)),
    ]]
    t_firmas = Table(firmas_data, colWidths=[5.8*cm, 5.8*cm, 5.9*cm])
    t_firmas.setStyle(TableStyle([
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING",  (0,0), (-1,-1), 10),
    ]))
    elems.append(t_firmas)
    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph(
        "Documento generado para pruebas del sistema. Auditor Agéntico de Facturación de Siniestros — Hackathon 2026.",
        estilo("FOOT", fontSize=7, textColor=colors.gray, alignment=TA_CENTER)
    ))

    doc.build(elems)
    print(f"  OK: {nombre_archivo}")


# ═══════════════════════════════════════════════════════════
# Tabla de Tipos de Siniestro
# ═══════════════════════════════════════════════════════════

TIPOS_SINIESTRO = [
    {
        "codigo":   "choque_frontal",
        "nombre":   "Choque Frontal",
        "descripcion": "Colisión frontal del vehículo. Daños en guardachoque, faros, capó, radiador y estructuras delanteras.",
        "items_tipicos": "Guardachoque del., Faro del., Capó, Radiador, Soporte motor, MO mecánica/latonería",
        "insumos":  "Pintura base/acabado, Kit lijas, Soldadura",
        "severidad_comun": "WARNING - CRITICAL",
    },
    {
        "codigo":   "choque_lateral",
        "nombre":   "Choque Lateral",
        "descripcion": "Impacto en costado del vehículo. Afecta puertas, espejos, vidrios laterales y estructura de carrocería.",
        "items_tipicos": "Puerta lateral, Espejo retrovisor, Vidrio ventana lateral, MO latonería/pintura",
        "insumos":  "Pintura, lijas, masilla, soldadura",
        "severidad_comun": "WARNING",
    },
    {
        "codigo":   "choque_trasero",
        "nombre":   "Choque Trasero",
        "descripcion": "Colisión en la parte trasera. Daños en guardachoque trasero, faros traseros y carrocería posterior.",
        "items_tipicos": "Guardachoque tras., Faro trasero, MO latonería/pintura, Alineación",
        "insumos":  "Pintura, lijas, masilla",
        "severidad_comun": "WARNING",
    },
    {
        "codigo":   "daño_granizo",
        "nombre":   "Daño por Granizo",
        "descripcion": "Abolladuras y daños superficiales en capó, techo y guardafangos por granizo. Posible rotura de parabrisas.",
        "items_tipicos": "Parabrisas del., Parabrisas tras., Capó, MO latonería/pintura",
        "insumos":  "Pintura, lijas, masilla",
        "severidad_comun": "WARNING - CRITICAL",
    },
    {
        "codigo":   "robo_accesorios",
        "nombre":   "Robo de Accesorios",
        "descripcion": "Sustracción de partes o accesorios del vehículo. Incluye radio, espejos, cerraduras, vidrios.",
        "items_tipicos": "Radio/Consola, Espejos, Cerraduras puerta, Vidrio ventana, MO eléctrica/mecánica",
        "insumos":  "Mínimos — solo instalación",
        "severidad_comun": "INFO - WARNING",
    },
    {
        "codigo":   "rayon_pintura",
        "nombre":   "Rayón en Pintura",
        "descripcion": "Daños superficiales de pintura por roce o vandalismo leve. Sin deformación estructural.",
        "items_tipicos": "Pintura base, Pintura acabado, Pintura transparente, MO pintura",
        "insumos":  "Kit lijas y masilla (máx. 2 gal pintura)",
        "severidad_comun": "INFO - WARNING",
    },
    {
        "codigo":   "rotura_parabrisas",
        "nombre":   "Rotura de Parabrisas",
        "descripcion": "Fractura o astillado del parabrisas por impacto de piedra u objeto. Reparación o reemplazo.",
        "items_tipicos": "Parabrisas delantero, Parabrisas trasero, MO instalación",
        "insumos":  "Mínimos",
        "severidad_comun": "INFO",
    },
    {
        "codigo":   "vandalismo",
        "nombre":   "Vandalismo",
        "descripcion": "Daños intencionales por terceros: rayones, golpes, rotura de vidrios, daño a cerraduras.",
        "items_tipicos": "Parabrisas, Vidrios, Espejos, Cerraduras, Pintura, MO múltiple",
        "insumos":  "Pintura, lijas, masilla, soldadura",
        "severidad_comun": "WARNING - CRITICAL",
    },
]


def generar_tabla_siniestros():
    nombre_archivo = os.path.join(OUTPUT_DIR, "tabla_tipos_siniestro.pdf")
    doc = SimpleDocTemplate(
        nombre_archivo,
        pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )
    elems = []

    # Título
    titulo_data = [[
        Paragraph("AUDITOR AGÉNTICO DE FACTURACIÓN DE SINIESTROS", estilo("T1", fontSize=13, textColor=colors.white, fontName="Helvetica-Bold", alignment=TA_CENTER)),
    ],[
        Paragraph("TABLA DE TIPOS DE SINIESTRO — Referencia para Auditoría", estilo("T2", fontSize=10, textColor=AZUL_CLARO, alignment=TA_CENTER)),
    ]]
    t_titulo = Table(titulo_data, colWidths=[17.5*cm])
    t_titulo.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), AZUL_OSCURO),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
    ]))
    elems.append(t_titulo)
    elems.append(Spacer(1, 6*mm))

    # Encabezado tabla
    header = [
        Paragraph("TIPO DE\nSINIESTRO", S_HEADER),
        Paragraph("DESCRIPCIÓN", S_HEADER),
        Paragraph("ÍTEMS TÍPICOS\nAUTORIZADOS", S_HEADER),
        Paragraph("INSUMOS\nESPERADOS", S_HEADER),
        Paragraph("SEVERIDAD\nCOMÚN", S_HEADER),
    ]
    filas = [header]

    for i, ts in enumerate(TIPOS_SINIESTRO):
        bg = AZUL_CLARO if i % 2 == 0 else colors.white
        filas.append([
            Paragraph(f"<b>{ts['nombre']}</b>\n<font size='7' color='gray'>{ts['codigo']}</font>",
                      estilo(f"N{i}", fontSize=8.5, leading=12)),
            Paragraph(ts["descripcion"], estilo(f"D{i}", fontSize=8, leading=11)),
            Paragraph(ts["items_tipicos"], estilo(f"I{i}", fontSize=7.5, leading=11)),
            Paragraph(ts["insumos"], estilo(f"S{i}", fontSize=7.5, leading=11, textColor=colors.darkgreen)),
            Paragraph(ts["severidad_comun"], estilo(f"SV{i}", fontSize=7.5, fontName="Helvetica-Bold",
                      textColor=ROJO if "CRITICAL" in ts["severidad_comun"] else NARANJA if "WARNING" in ts["severidad_comun"] else VERDE)),
        ])

    t_tipos = Table(filas, colWidths=[3.2*cm, 4.8*cm, 4.5*cm, 2.8*cm, 2.2*cm])
    ts_style = [
        ("BACKGROUND",    (0,0), (-1,0), AZUL_OSCURO),
        ("GRID",          (0,0), (-1,-1), 0.5, GRIS_MEDIO),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]
    for i in range(1, len(filas)):
        bg = AZUL_CLARO if (i-1) % 2 == 0 else colors.white
        ts_style.append(("BACKGROUND", (0,i), (-1,i), bg))

    t_tipos.setStyle(TableStyle(ts_style))
    elems.append(t_tipos)
    elems.append(Spacer(1, 6*mm))

    # Leyenda
    leyenda_data = [
        [Paragraph("<b>LEYENDA DE SEVERIDAD</b>", estilo("LD", fontSize=8, fontName="Helvetica-Bold"))],
        [Paragraph("INFO: Sin anomalías detectadas. Factura dentro de parámetros normales.", estilo("LI", fontSize=7.5, textColor=VERDE))],
        [Paragraph("WARNING: Precio o cantidad ligeramente fuera del tarifario. Requiere revisión.", estilo("LW", fontSize=7.5, textColor=NARANJA))],
        [Paragraph("CRITICAL: Duplicado confirmado o ítem completamente incoherente con el siniestro. Acción inmediata.", estilo("LC", fontSize=7.5, textColor=ROJO))],
    ]
    t_leyenda = Table(leyenda_data, colWidths=[17.5*cm])
    t_leyenda.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), GRIS_CLARO),
        ("TOPPADDING",   (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("BOX",          (0,0), (-1,-1), 0.5, GRIS_MEDIO),
    ]))
    elems.append(t_leyenda)
    elems.append(Spacer(1, 5*mm))
    elems.append(Paragraph(
        f"Generado: {now.strftime('%d/%m/%Y')} | Auditor Agéntico — Hackathon 2026",
        estilo("FOOT2", fontSize=7, textColor=colors.gray, alignment=TA_CENTER)
    ))

    doc.build(elems)
    print(f"  OK: {nombre_archivo}")


# ═══════════════════════════════════════════════════════════
# Tarifario Acordado
# ═══════════════════════════════════════════════════════════

TARIFARIO = [
    ("REP-PAR01", "Parabrisas delantero",        "repuesto",   280.00, 10, 1, 1, ["daño_granizo","rotura_parabrisas","choque_frontal","vandalismo"]),
    ("REP-PAR02", "Parabrisas trasero",           "repuesto",   220.00, 10, 1, 1, ["daño_granizo","rotura_parabrisas","choque_trasero","vandalismo"]),
    ("REP-FAR01", "Faro delantero (unidad)",      "repuesto",   150.00, 10, 1, 2, ["choque_frontal","vandalismo"]),
    ("REP-FAR02", "Faro trasero (unidad)",        "repuesto",   120.00, 10, 1, 2, ["choque_trasero","vandalismo"]),
    ("REP-GUA01", "Guardachoque delantero",       "repuesto",   350.00, 10, 1, 1, ["choque_frontal"]),
    ("REP-GUA02", "Guardachoque trasero",         "repuesto",   320.00, 10, 1, 1, ["choque_trasero"]),
    ("REP-PUE01", "Puerta lateral (unidad)",      "repuesto",   450.00, 10, 1, 2, ["choque_lateral","vandalismo"]),
    ("REP-CAP01", "Capó delantero",               "repuesto",   380.00, 10, 1, 1, ["choque_frontal","daño_granizo"]),
    ("REP-ESP01", "Espejo retrovisor (unidad)",   "repuesto",    85.00, 15, 1, 2, ["choque_lateral","robo_accesorios","vandalismo"]),
    ("REP-RAD01", "Radiador",                     "repuesto",   200.00, 10, 1, 1, ["choque_frontal"]),
    ("REP-MOT01", "Soporte de motor",             "repuesto",   180.00, 10, 1, 2, ["choque_frontal"]),
    ("REP-VID01", "Vidrio ventana lateral",       "repuesto",   120.00, 10, 1, 2, ["choque_lateral","robo_accesorios","vandalismo"]),
    ("REP-CER01", "Cerradura puerta",             "repuesto",    65.00, 10, 1, 4, ["robo_accesorios","vandalismo"]),
    ("REP-RAD02", "Radio/Consola",                "repuesto",   250.00, 10, 1, 1, ["robo_accesorios"]),
    ("PIN-BASE01","Pintura base (galón)",         "pintura",     45.00, 10, 1, 2, ["choque_frontal","choque_lateral","choque_trasero","daño_granizo","rayon_pintura","vandalismo"]),
    ("PIN-ACAB01","Pintura acabado (galón)",      "pintura",     65.00, 10, 1, 2, ["choque_frontal","choque_lateral","choque_trasero","daño_granizo","rayon_pintura","vandalismo"]),
    ("PIN-TRAN01","Pintura transparente (galón)", "pintura",     55.00, 10, 1, 2, ["choque_frontal","choque_lateral","choque_trasero","daño_granizo","rayon_pintura","vandalismo"]),
    ("MAT-LIJ01", "Kit lijas y masilla",          "material",    35.00, 15, 1, 3, ["choque_frontal","choque_lateral","choque_trasero","daño_granizo","rayon_pintura","vandalismo"]),
    ("MAT-SOL01", "Soldadura y materiales",       "material",    60.00, 10, 1, 2, ["choque_frontal","choque_lateral","choque_trasero"]),
    ("MO-MEC01",  "Mano de obra mecánica (h)",    "mano_obra",   25.00, 10, 1,20, ["choque_frontal","choque_lateral","choque_trasero","robo_accesorios"]),
    ("MO-PIN01",  "Mano de obra pintura (h)",     "mano_obra",   22.00, 10, 1,15, ["choque_frontal","choque_lateral","choque_trasero","daño_granizo","rayon_pintura","vandalismo"]),
    ("MO-ELE01",  "Mano de obra eléctrica (h)",   "mano_obra",   30.00, 10, 1,10, ["choque_frontal","choque_lateral","robo_accesorios"]),
    ("MO-LAM01",  "Mano de obra latonería (h)",   "mano_obra",   28.00, 10, 1,20, ["choque_frontal","choque_lateral","choque_trasero","daño_granizo","vandalismo"]),
    ("SRV-GRU01", "Servicio de grúa",             "servicio",    80.00, 15, 1, 1, ["choque_frontal","choque_lateral","choque_trasero"]),
    ("SRV-ALI01", "Alineación y balanceo",        "servicio",    40.00, 10, 1, 1, ["choque_frontal","choque_lateral","choque_trasero"]),
]

CAT_COLORES = {
    "repuesto":  colors.HexColor("#1a5276"),
    "pintura":   colors.HexColor("#7d6608"),
    "material":  colors.HexColor("#4d5656"),
    "mano_obra": colors.HexColor("#1e8449"),
    "servicio":  colors.HexColor("#6c3483"),
}


def generar_tarifario():
    nombre_archivo = os.path.join(OUTPUT_DIR, "tarifario_acordado.pdf")
    doc = SimpleDocTemplate(
        nombre_archivo,
        pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )
    elems = []

    titulo_data = [[
        Paragraph("TARIFARIO ACORDADO — ASEGURADORA / TALLERES", estilo("TT", fontSize=13, textColor=colors.white, fontName="Helvetica-Bold", alignment=TA_CENTER)),
    ],[
        Paragraph(f"Vigente: Enero–Diciembre 2026  |  IVA 15%  |  Tolerancia indicada por ítem",
                  estilo("TS", fontSize=9, textColor=AZUL_CLARO, alignment=TA_CENTER)),
    ]]
    t_titulo = Table(titulo_data, colWidths=[17.5*cm])
    t_titulo.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), AZUL_OSCURO),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
    ]))
    elems.append(t_titulo)
    elems.append(Spacer(1, 5*mm))

    header = [
        Paragraph("CÓDIGO",     S_HEADER),
        Paragraph("DESCRIPCIÓN",S_HEADER),
        Paragraph("CAT.",       S_HEADER),
        Paragraph("P. MÁX\n(USD)", S_HEADER),
        Paragraph("TOL\n(%)",   S_HEADER),
        Paragraph("QTY\nMÍN",   S_HEADER),
        Paragraph("QTY\nMÁX",   S_HEADER),
        Paragraph("SINIESTROS APLICABLES", S_HEADER),
    ]
    filas = [header]

    for i, (cod, desc, cat, precio, tol, qmin, qmax, sins) in enumerate(TARIFARIO):
        bg = GRIS_CLARO if i % 2 == 0 else colors.white
        col_cat = CAT_COLORES.get(cat, AZUL_MEDIO)
        sins_txt = ", ".join(s.replace("_", " ") for s in sins)
        p_max_tolerado = precio * (1 + tol/100)
        filas.append([
            Paragraph(cod,  estilo(f"C{i}", fontSize=7.5, fontName="Helvetica-Bold")),
            Paragraph(desc, estilo(f"D{i}", fontSize=8)),
            Paragraph(cat.replace("_"," "), estilo(f"T{i}", fontSize=7, textColor=col_cat, fontName="Helvetica-Bold")),
            Paragraph(f"<b>${precio:.2f}</b>\n<font size='6.5' color='gray'>(máx+tol: ${p_max_tolerado:.2f})</font>",
                      estilo(f"P{i}", fontSize=8, alignment=TA_RIGHT)),
            Paragraph(f"{tol:.0f}%", estilo(f"O{i}", fontSize=8, alignment=TA_CENTER)),
            Paragraph(str(qmin), estilo(f"Mn{i}", fontSize=8, alignment=TA_CENTER)),
            Paragraph(str(qmax), estilo(f"Mx{i}", fontSize=8, alignment=TA_CENTER)),
            Paragraph(sins_txt, estilo(f"S{i}", fontSize=6.5, textColor=colors.darkblue)),
        ])

    col_w = [2.5*cm, 4.3*cm, 1.7*cm, 2.2*cm, 1*cm, 0.9*cm, 0.9*cm, 3.9*cm]
    t_tar = Table(filas, colWidths=col_w)
    tar_style = [
        ("BACKGROUND",    (0,0), (-1,0), AZUL_OSCURO),
        ("GRID",          (0,0), (-1,-1), 0.5, GRIS_MEDIO),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 4),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]
    for i in range(1, len(filas)):
        bg = GRIS_CLARO if (i-1) % 2 == 0 else colors.white
        tar_style.append(("BACKGROUND", (0,i), (-1,i), bg))

    t_tar.setStyle(TableStyle(tar_style))
    elems.append(t_tar)
    elems.append(Spacer(1, 5*mm))

    # Leyenda categorías
    cat_data = [[
        Paragraph(
            " | ".join(f'<font color="{CAT_COLORES[c].hexval() if hasattr(CAT_COLORES[c],"hexval") else "#000"}">'
                      f'■ {c.replace("_"," ").upper()}</font>' for c in CAT_COLORES),
            estilo("CLEG", fontSize=7.5, alignment=TA_CENTER)
        )
    ]]
    t_cat = Table(cat_data, colWidths=[17.5*cm])
    t_cat.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), GRIS_CLARO),
        ("TOPPADDING",   (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("BOX",          (0,0), (-1,-1), 0.5, GRIS_MEDIO),
    ]))
    elems.append(t_cat)
    elems.append(Spacer(1, 3*mm))
    elems.append(Paragraph(
        f"Generado: {now.strftime('%d/%m/%Y')} | Auditor Agéntico — Hackathon 2026",
        estilo("FOOT3", fontSize=7, textColor=colors.gray, alignment=TA_CENTER)
    ))

    doc.build(elems)
    print(f"  OK: {nombre_archivo}")


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\nGenerando PDFs de prueba en '{OUTPUT_DIR}/'...\n")

    print("Facturas:")
    for i, f in enumerate(FACTURAS, 1):
        generar_factura(f, i)

    print("\nTabla tipos de siniestro:")
    generar_tabla_siniestros()

    print("\nTarifario:")
    generar_tarifario()

    print(f"\nTotal: {len(FACTURAS) + 2} PDFs generados en '{OUTPUT_DIR}/'")
    print("  5 facturas (1 limpia, 2 warning, 2 critical)")
    print("  1 tabla tipos de siniestro (8 tipos)")
    print("  1 tarifario acordado (25 ítems)")
