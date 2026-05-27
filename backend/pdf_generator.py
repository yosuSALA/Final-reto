"""
Generador de PDFs — dos modos:
  • generate_audit_report_pdf: INTERNO (con análisis de riesgo, severidad por hallazgo, items completos).
  • generate_workshop_notification_pdf: EXTERNO (sin riesgo, profesional, ajustes y mensaje ejecutivo).
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


OUTPUT_DIR_DEFAULT = "backend/generated_reports"

PRIMARY = colors.HexColor("#6366f1")
DANGER = colors.HexColor("#ef4444")
WARNING_C = colors.HexColor("#f59e0b")
SUCCESS = colors.HexColor("#10b981")
SLATE = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
LIGHT_BG = colors.HexColor("#f1f5f9")


def _ensure_output_dir(output_dir: str) -> str:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir


def _get_styles():
    styles = getSampleStyleSheet()
    if "JustifyES" not in styles.byName:
        styles.add(ParagraphStyle(name="JustifyES", alignment=4))
    if "Important" not in styles.byName:
        styles.add(ParagraphStyle(name="Important", parent=styles["Normal"], textColor=DANGER,
                                  fontSize=12, fontName="Helvetica-Bold"))
    if "Muted" not in styles.byName:
        styles.add(ParagraphStyle(name="Muted", parent=styles["Normal"], textColor=MUTED, fontSize=8))
    if "Subhead" not in styles.byName:
        styles.add(ParagraphStyle(name="Subhead", parent=styles["Heading3"], textColor=PRIMARY,
                                  fontSize=12, spaceAfter=8, spaceBefore=4))
    if "SmallNormal" not in styles.byName:
        # Estilo compacto para celdas de tabla con texto largo (IA)
        styles.add(ParagraphStyle(
            name="SmallNormal",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=10,
            wordWrap="LTR",
            splitLongWords=True,
        ))
    return styles


def _severity_color(sev: str):
    return {"critical": DANGER, "warning": WARNING_C, "info": SUCCESS}.get(sev, MUTED)


def _status_label(status: str) -> str:
    return {
        "approved": "APROBADO", "completed": "OBSERVADO",
        "escalated": "ESCALADO", "rejected": "RECHAZADO",
        "pending": "PENDIENTE", "in_progress": "EN PROCESO",
    }.get(status, str(status).upper())


# ──────────────────────────────────────────────────────────────────────────────
# PDF INTERNO — con análisis de riesgo (preview al aprobar)
# ──────────────────────────────────────────────────────────────────────────────

def generate_audit_report_pdf(audit_data: dict, workshop_name: str,
                              output_dir: str = OUTPUT_DIR_DEFAULT) -> str:
    output_dir = _ensure_output_dir(output_dir)
    invoice_number = audit_data.get("invoice_number", "N_A")
    filename = f"Auditoria_Interna_{invoice_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=54, leftMargin=54,
                            topMargin=54, bottomMargin=36)
    styles = _get_styles()
    elements = []

    elements.append(Paragraph("<font color='#6366f1'><b>Aseguradora HackIATon 2026</b></font>", styles["Heading1"]))
    elements.append(Paragraph("<b>Reporte de Auditoría Interna</b> — con análisis de riesgo", styles["Heading3"]))
    elements.append(Spacer(1, 8))

    risk_score = float(audit_data.get("risk_score", 0) or 0)
    risk_label = "ALTO" if risk_score >= 70 else "MEDIO" if risk_score >= 30 else "BAJO"
    risk_hex = "#ef4444" if risk_score >= 70 else "#f59e0b" if risk_score >= 30 else "#10b981"

    p = styles["SmallNormal"]
    info_data = [
        [Paragraph("Factura", p), Paragraph(str(audit_data.get("invoice_number", "-")), p),
         Paragraph("Siniestro", p), Paragraph(str(audit_data.get("claim_number", "-")), p)],
        [Paragraph("Taller", p), Paragraph(str(workshop_name), p),
         Paragraph("Tipo Siniestro", p), Paragraph(str(audit_data.get("claim_type", "-")), p)],
        [Paragraph("Vehículo", p), Paragraph(str(audit_data.get("vehicle", "-")), p),
         Paragraph("Placa", p), Paragraph(str(audit_data.get("vehicle_plate", "-")), p)],
        [Paragraph("Asegurado", p), Paragraph(str(audit_data.get("insured_name", "-")), p),
         Paragraph("Fecha audit.", p), Paragraph(datetime.now().strftime("%d/%m/%Y %H:%M"), p)],
    ]
    info_t = Table(info_data, colWidths=[72, 170, 80, 158])
    info_t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
        ("BACKGROUND", (2, 0), (2, -1), LIGHT_BG),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    elements.append(info_t)
    elements.append(Spacer(1, 12))

    status_str = _status_label(audit_data.get("status", "pending"))
    risk_data = [[
        Paragraph(f"<b>ESTADO:</b><br/>{status_str}", styles["Normal"]),
        Paragraph(f"<b>RISK SCORE:</b><br/><font color='{risk_hex}' size='14'><b>{risk_score:.0f} / 100 ({risk_label})</b></font>", styles["Normal"]),
        Paragraph(f"<b>SOBRECOBRO DETECTADO:</b><br/><font color='#ef4444' size='14'><b>${float(audit_data.get('total_overcharge', 0) or 0):.2f}</b></font>", styles["Normal"]),
    ]]
    risk_bg = colors.HexColor("#fee2e2") if risk_score >= 70 else colors.HexColor("#fef3c7") if risk_score >= 30 else colors.HexColor("#dcfce7")
    risk_t = Table(risk_data, colWidths=[150, 175, 175])
    risk_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), risk_bg),
        ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor(risk_hex)),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(risk_t)
    elements.append(Spacer(1, 16))

    items = audit_data.get("items", [])
    if items:
        elements.append(Paragraph("<b>Ítems Facturados</b>", styles["Subhead"]))
        items_data = [["Código", "Descripción", "Cant.", "P. Unit.", "Tarifario", "Total", "⚠"]]
        for it in items:
            tariff_p = it.get("tariff_price")
            tol = it.get("tariff_tolerance") or 10
            unit_p = float(it.get("unit_price", 0) or 0)
            is_over = tariff_p and unit_p > float(tariff_p) * (1 + tol / 100)
            mark = "⚠" if is_over else ""
            items_data.append([
                it.get("code", "-") or "-",
                Paragraph(it.get("description", ""), styles["Normal"]),
                f"{float(it.get('quantity', 0) or 0):.0f}",
                f"${unit_p:.2f}",
                f"${float(tariff_p):.2f}" if tariff_p else "-",
                f"${float(it.get('total_price', 0) or 0):.2f}",
                mark,
            ])
        items_t = Table(items_data, colWidths=[55, 175, 35, 55, 60, 60, 20])
        items_style = [
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("ALIGN", (3, 1), (5, -1), "RIGHT"),
            ("ALIGN", (2, 1), (2, -1), "CENTER"),
            ("ALIGN", (-1, 0), (-1, -1), "CENTER"),
        ]
        # Marcar filas con sobrecobro
        for row_idx, it in enumerate(items, start=1):
            tariff_p = it.get("tariff_price")
            tol = it.get("tariff_tolerance") or 10
            unit_p = float(it.get("unit_price", 0) or 0)
            if tariff_p and unit_p > float(tariff_p) * (1 + tol / 100):
                items_style.append(("TEXTCOLOR", (3, row_idx), (3, row_idx), DANGER))
                items_style.append(("FONTNAME", (3, row_idx), (3, row_idx), "Helvetica-Bold"))
        items_t.setStyle(TableStyle(items_style))
        elements.append(items_t)

        totals_data = [
            ["", "Subtotal:", f"${float(audit_data.get('invoice_subtotal', 0) or 0):.2f}"],
            ["", "IVA:", f"${float(audit_data.get('invoice_iva', 0) or 0):.2f}"],
            ["", "TOTAL:", f"${float(audit_data.get('invoice_total', 0) or 0):.2f}"],
        ]
        totals_t = Table(totals_data, colWidths=[290, 90, 80])
        totals_t.setStyle(TableStyle([
            ("FONTNAME", (1, -1), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LINEABOVE", (1, -1), (-1, -1), 1.2, SLATE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(totals_t)
        elements.append(Spacer(1, 14))

    hallazgos = audit_data.get("hallazgos") or audit_data.get("findings") or []
    elements.append(Paragraph(f"<b>Hallazgos del Agente IA ({len(hallazgos)})</b>", styles["Subhead"]))
    if not hallazgos:
        elements.append(Paragraph("<i>Sin hallazgos. Factura limpia y dentro de los parámetros del tarifario.</i>",
                                  styles["Normal"]))
    else:
        head = ["Severidad", "Tipo", "Hallazgo / Detalle", "Esperado", "Real", "Diferencia"]
        h_data = [head]
        sev_styles = []
        for idx, h in enumerate(hallazgos):
            sev = (h.get("severity") or h.get("severidad") or "info").lower()
            tipo = (h.get("finding_type") or h.get("tipo") or h.get("regla") or "-")
            titulo = h.get("title") or h.get("titulo") or h.get("regla") or "-"
            desc = h.get("description") or h.get("descripcion") or h.get("detalle") or ""
            esperado = h.get("expected_value") or h.get("valor_esperado") or "-"
            real = h.get("actual_value") or h.get("valor_facturado") or "-"
            diff = h.get("difference") if h.get("difference") is not None else (
                h.get("diferencia_usd") if h.get("diferencia_usd") is not None else h.get("impacto_economico", 0))
            import xml.sax.saxutils as saxutils
            safe_titulo = saxutils.escape(str(titulo))
            safe_desc = saxutils.escape(str(desc)).replace("\n", "<br/>")
            h_data.append([
                Paragraph(sev.upper(), styles["SmallNormal"]),
                Paragraph(str(tipo).upper().replace("_", " "), styles["SmallNormal"]),
                Paragraph(f"<b>{safe_titulo}</b><br/>{safe_desc}", styles["SmallNormal"]),
                Paragraph(str(esperado), styles["SmallNormal"]),
                Paragraph(str(real), styles["SmallNormal"]),
                Paragraph(f"${float(diff or 0):.2f}", styles["SmallNormal"]),
            ])
            sev_styles.append(("BACKGROUND", (0, idx + 1), (0, idx + 1), _severity_color(sev)))
            sev_styles.append(("TEXTCOLOR", (0, idx + 1), (0, idx + 1), colors.white))
            sev_styles.append(("FONTNAME", (0, idx + 1), (0, idx + 1), "Helvetica-Bold"))
        # Anchos: Severidad | Tipo | Detalle(ancho) | Esperado | Real | Diferencia
        h_t = Table(h_data, colWidths=[52, 68, 185, 60, 60, 55], repeatRows=1)
        h_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SLATE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("ALIGN", (0, 1), (1, -1), "CENTER"),
            ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ] + sev_styles))
        elements.append(h_t)

    elements.append(Spacer(1, 14))
    notas = audit_data.get("notas_agente") or audit_data.get("summary") or ""
    if notas:
        elements.append(Paragraph("<b>Notas del Agente</b>", styles["Subhead"]))
        import xml.sax.saxutils as saxutils
        safe_notas = saxutils.escape(str(notas)).replace("\n", "<br/>")
        elements.append(Paragraph(safe_notas, styles["JustifyES"]))
        elements.append(Spacer(1, 12))

    elements.append(Spacer(1, 14))
    elements.append(Paragraph(
        "Documento interno generado automáticamente por el Agente de Auditoría IA. "
        "Contiene análisis de riesgo confidencial. No distribuir externamente.",
        styles["Muted"]))

    doc.build(elements)
    return filepath


# ──────────────────────────────────────────────────────────────────────────────
# PDF EXTERNO — sin análisis de riesgo (notificación al taller)
# ──────────────────────────────────────────────────────────────────────────────

def generate_workshop_notification_pdf(audit_data: dict, workshop_name: str,
                                        output_dir: str = OUTPUT_DIR_DEFAULT) -> str:
    output_dir = _ensure_output_dir(output_dir)
    invoice_number = audit_data.get("invoice_number", "N_A")
    filename = f"Notificacion_Taller_{invoice_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=54, leftMargin=54,
                            topMargin=54, bottomMargin=36)
    styles = _get_styles()
    elements = []

    elements.append(Paragraph("<font color='#6366f1'><b>Aseguradora HackIATon 2026</b></font>", styles["Heading1"]))
    elements.append(Paragraph("<b>Resolución de Facturación de Siniestro</b>", styles["Heading2"]))
    elements.append(Spacer(1, 14))

    p = styles["SmallNormal"]
    info_data = [
        [Paragraph("Fecha", p), Paragraph(datetime.now().strftime("%d/%m/%Y"), p),
         Paragraph("Factura", p), Paragraph(str(audit_data.get("invoice_number", "-")), p)],
        [Paragraph("Taller", p), Paragraph(str(workshop_name), p),
         Paragraph("Siniestro", p), Paragraph(str(audit_data.get("claim_number", "-")), p)],
        [Paragraph("Vehículo", p), Paragraph(str(audit_data.get("vehicle", "-")), p),
         Paragraph("Placa", p), Paragraph(str(audit_data.get("vehicle_plate", "-")), p)],
        [Paragraph("Asegurado", p), Paragraph(str(audit_data.get("insured_name", "-")), p),
         Paragraph("Tipo", p), Paragraph(str(audit_data.get("claim_type", "-")), p)],
    ]
    info_t = Table(info_data, colWidths=[72, 165, 70, 178])
    info_t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
        ("BACKGROUND", (2, 0), (2, -1), LIGHT_BG),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    elements.append(info_t)
    elements.append(Spacer(1, 18))

    elements.append(Paragraph("<b>Estimado equipo del taller:</b>", styles["Heading3"]))
    resumen = (audit_data.get("resumen_ejecutivo_taller")
               or audit_data.get("notas_agente")
               or "Tras revisar la factura presentada, se ha completado el proceso de auditoría correspondiente y emitimos la presente resolución.")
    
    import xml.sax.saxutils as saxutils
    safe_resumen = saxutils.escape(str(resumen)).replace("\n", "<br/>")
    elements.append(Paragraph(safe_resumen, styles["JustifyES"]))
    elements.append(Spacer(1, 16))

    hallazgos = audit_data.get("hallazgos") or audit_data.get("findings") or []
    if hallazgos:
        elements.append(Paragraph("<b>Ajustes Requeridos en la Próxima Facturación</b>", styles["Subhead"]))
        ajuste_data = [["Concepto", "Detalle", "Ajuste (USD)"]]
        for h in hallazgos:
            regla = h.get("regla") or h.get("title") or h.get("titulo") or "-"
            detalle = h.get("detalle") or h.get("description") or h.get("descripcion") or ""
            recomend = h.get("recommendation") or h.get("recomendacion") or ""
            full_detail = detalle
            if recomend:
                full_detail += f"<br/><i>Acción sugerida: {recomend}</i>"
            diff = h.get("impacto_economico") if h.get("impacto_economico") is not None else (
                h.get("difference") if h.get("difference") is not None else h.get("diferencia_usd", 0))
            import xml.sax.saxutils as saxutils
            safe_regla = saxutils.escape(str(regla))
            safe_full_detail = saxutils.escape(str(detalle)).replace("\n", "<br/>")
            if recomend:
                safe_recomend = saxutils.escape(str(recomend))
                safe_full_detail += f"<br/><i>Acción sugerida: {safe_recomend}</i>"
            ajuste_data.append([
                Paragraph(safe_regla, styles["SmallNormal"]),
                Paragraph(safe_full_detail, styles["SmallNormal"]),
                Paragraph(f"${float(diff or 0):.2f}", styles["SmallNormal"]),
            ])
        a_t = Table(ajuste_data, colWidths=[125, 295, 65], repeatRows=1)
        a_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        elements.append(a_t)
        elements.append(Spacer(1, 14))
        ajuste_total = float(audit_data.get("ahorro_estimado") or audit_data.get("total_overcharge", 0) or 0)
        elements.append(Paragraph(f"<b>Ajuste Total Sugerido:</b> ${ajuste_total:.2f}", styles["Important"]))
    else:
        elements.append(Paragraph(
            "Su factura ha sido <b>aprobada sin observaciones</b>. Agradecemos la precisión y "
            "profesionalismo en la presentación de su documentación.",
            styles["JustifyES"]))

    elements.append(Spacer(1, 28))
    elements.append(Paragraph("Atentamente,", styles["Normal"]))
    elements.append(Paragraph("<b>Departamento de Auditoría de Siniestros</b>", styles["Normal"]))
    elements.append(Paragraph("Aseguradora HackIATon 2026", styles["Muted"]))

    elements.append(Spacer(1, 22))
    elements.append(Paragraph(
        "Este documento corresponde a la resolución oficial de la auditoría. Para consultas "
        "adicionales, contactar al área de siniestros.",
        styles["Muted"]))

    doc.build(elements)
    return filepath


# Backward compat
def generate_workshop_report(audit_data: dict, workshop_name: str,
                             output_dir: str = OUTPUT_DIR_DEFAULT) -> str:
    return generate_workshop_notification_pdf(audit_data, workshop_name, output_dir)
