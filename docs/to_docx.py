"""
Convierte todos los .md de docs/ y docs/diagramas/ a un único .docx.
Renderiza los bloques Mermaid como imágenes usando la API pública mermaid.ink.

Uso:
    python docs/to_docx.py
    python docs/to_docx.py --output mi_documento.docx
    python docs/to_docx.py --skip-mermaid   # omite las imágenes (más rápido)

Dependencias:
    pip install python-docx requests
"""

import argparse
import base64
import sys
import re
import zlib
import urllib.request
import urllib.error
from io import BytesIO
from pathlib import Path

# Forzar UTF-8 en stdout para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError:
    sys.exit("ERROR: Instala python-docx primero:  pip install python-docx")


# ─── Configuración ────────────────────────────────────────────────────────────

DOCS_DIR = Path(__file__).parent

# Orden de los documentos en el .docx (primero el stack, luego docs principales,
# luego los diagramas de cada doc).
MAIN_DOCS_ORDER = [
    "stack.md",
    "arquitectura.md",
    "arquitectura_seguridad.md",
    "modelo_datos.md",
    "reglas_negocio.md",
    "uso_ia.md",
    "PERFILES_ACCESO.md",
    "MANUAL_USO.md",
    "limitaciones.md",
    "DOC_FUNCIONES.md",
    "DEEPSEEK_REVIEW_LOOP.md",
    "PLAN_SOFISTICADO_IMPLEMENTACION.md",
    "PROMPT_DEEPSEEK_P0_FINAL.md",
    "MATRIZ_CUMPLIMIENTO_RETO.md",
]

DIAGRAMS_ORDER = [
    "diagramas/diagrama_stack.md",
    "diagramas/diagrama_arquitectura.md",
    "diagramas/diagrama_arquitectura_seguridad.md",
    "diagramas/diagrama_modelo_datos.md",
    "diagramas/diagrama_reglas_negocio.md",
    "diagramas/diagrama_uso_ia.md",
    "diagramas/diagrama_perfiles_acceso.md",
    "diagramas/diagrama_manual_uso.md",
    "diagramas/diagrama_limitaciones.md",
    "diagramas/diagrama_doc_funciones.md",
    "diagramas/diagrama_deepseek_review_loop.md",
    "diagramas/diagrama_plan_implementacion.md",
    "diagramas/diagrama_prompt_deepseek.md",
    "diagramas/diagrama_matriz_cumplimiento.md",
]

# ─── Colores del tema ──────────────────────────────────────────────────────────

COLOR_H1 = RGBColor(0x1E, 0x40, 0xAF)   # azul oscuro
COLOR_H2 = RGBColor(0x16, 0x50, 0x37)   # verde oscuro
COLOR_H3 = RGBColor(0x4B, 0x21, 0x88)   # violeta
COLOR_CODE_BG = RGBColor(0xF3, 0xF4, 0xF6)
COLOR_CODE_TEXT = RGBColor(0x1F, 0x29, 0x37)
COLOR_CAPTION = RGBColor(0x6B, 0x72, 0x80)
COLOR_BLOCKQUOTE = RGBColor(0x37, 0x51, 0x8C)
COLOR_HR = RGBColor(0xD1, 0xD5, 0xDB)


# ─── Mermaid → imagen PNG via kroki.io ────────────────────────────────────────
# kroki.io es un servicio público gratuito de renderizado de diagramas.
# Formato: https://kroki.io/mermaid/png/{base64_zlib_compressed}

KROKI_URL = "https://kroki.io/mermaid/png/{encoded}"


def mermaid_to_png(diagram_code: str) -> bytes | None:
    """Renderiza un diagrama Mermaid como PNG usando kroki.io.
    Retorna los bytes del PNG o None si falla.
    """
    compressed = zlib.compress(diagram_code.encode("utf-8"), 9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    url = KROKI_URL.format(encoded=encoded)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 miraclex-docs/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 200:
                return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
        print(f"  ⚠️  kroki.io falló: {e}")
    return None


# ─── Helpers de formato Word ───────────────────────────────────────────────────

def set_cell_bg(cell, hex_color: str):
    """Pinta el fondo de una celda de tabla."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def add_horizontal_rule(doc: Document):
    """Añade una línea horizontal."""
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "D1D5DB")
    pBdr.append(bottom)
    pPr.append(pBdr)


def add_page_break(doc: Document):
    doc.add_page_break()


def style_run_code(run):
    """Aplica estilo monoespaciado a un run."""
    run.font.name = "Courier New"
    run.font.size = Pt(9)
    run.font.color.rgb = COLOR_CODE_TEXT


# ─── Parser de Markdown → Word ────────────────────────────────────────────────

# Regex para bloques de código
RE_CODE_BLOCK = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
# Regex para tablas Markdown
RE_TABLE_ROW = re.compile(r"^\|(.+)\|$")
# Inline: negrita, cursiva, código, link
RE_BOLD = re.compile(r"\*\*(.+?)\*\*")
RE_ITALIC = re.compile(r"\*(.+?)\*|_(.+?)_")
RE_INLINE_CODE = re.compile(r"`(.+?)`")
RE_LINK = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
# Listas
RE_BULLET = re.compile(r"^(\s*)([-*+])\s+(.+)$")
RE_ORDERED = re.compile(r"^(\s*)\d+\.\s+(.+)$")


def add_inline_text(paragraph, text: str):
    """Procesa texto inline (negrita, cursiva, código, links) y lo agrega al párrafo."""
    parts = re.split(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*|\[[^\]]+\]\([^\)]+\))", text)
    for part in parts:
        if not part:
            continue
        if RE_BOLD.fullmatch(part):
            run = paragraph.add_run(RE_BOLD.fullmatch(part).group(1))
            run.bold = True
        elif RE_INLINE_CODE.fullmatch(part):
            run = paragraph.add_run(RE_INLINE_CODE.fullmatch(part).group(1))
            style_run_code(run)
        elif RE_ITALIC.fullmatch(part):
            m = RE_ITALIC.fullmatch(part)
            run = paragraph.add_run(m.group(1) or m.group(2))
            run.italic = True
        elif RE_LINK.fullmatch(part):
            run = paragraph.add_run(RE_LINK.fullmatch(part).group(1))
            run.underline = True
            run.font.color.rgb = COLOR_H1
        else:
            paragraph.add_run(part)


def parse_table(lines: list[str], doc: Document):
    """Convierte líneas de tabla Markdown en tabla Word."""
    rows = []
    for line in lines:
        if RE_TABLE_ROW.match(line):
            cells = [c.strip() for c in line.strip("|").split("|")]
            rows.append(cells)

    if not rows:
        return

    # Filtrar la fila separadora (---|---|---)
    data_rows = [r for r in rows if not all(re.match(r"^[-: ]+$", c) for c in r)]
    if not data_rows:
        return

    col_count = max(len(r) for r in data_rows)
    table = doc.add_table(rows=len(data_rows), cols=col_count)
    table.style = "Table Grid"

    for ri, row in enumerate(data_rows):
        for ci in range(col_count):
            cell = table.cell(ri, ci)
            text = row[ci] if ci < len(row) else ""
            # Limpiar emojis de estado para mejor rendering
            text = re.sub(r"[✅❌⚠️🔴🟡🟢]", lambda m: {"✅": "[OK]", "❌": "[NO]", "⚠️": "[!]",
                                                         "🔴": "[ROJO]", "🟡": "[AMARILLO]", "🟢": "[VERDE]"}.get(m.group(), m.group()), text)
            cell.text = ""
            p = cell.paragraphs[0]
            add_inline_text(p, text)
            p.runs[0].font.size = Pt(9) if p.runs else None
            if ri == 0:
                for run in p.runs:
                    run.bold = True
                set_cell_bg(cell, "DBEAFE")

    doc.add_paragraph()  # espacio tras tabla


def render_markdown_to_docx(md_text: str, doc: Document, skip_mermaid: bool = False,
                             section_title: str = ""):
    """Convierte texto Markdown al documento Word."""
    if section_title:
        p = doc.add_heading(section_title, level=0)
        p.runs[0].font.color.rgb = COLOR_H1

    # Separar bloques de código (incluyendo Mermaid) del resto
    segments = []
    last = 0
    for m in RE_CODE_BLOCK.finditer(md_text):
        if m.start() > last:
            segments.append(("text", md_text[last:m.start()]))
        segments.append(("code", m.group(1), m.group(2)))
        last = m.end()
    if last < len(md_text):
        segments.append(("text", md_text[last:]))

    for seg in segments:
        if seg[0] == "code":
            lang = seg[1].lower()
            code = seg[2].rstrip()

            if lang == "mermaid" and not skip_mermaid:
                _insert_mermaid(doc, code)
            else:
                # Bloque de código normal
                p = doc.add_paragraph()
                p.style = "Normal"
                pPr = p._p.get_or_add_pPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:color"), "auto")
                shd.set(qn("w:fill"), "F3F4F6")
                pPr.append(shd)
                run = p.add_run(code)
                style_run_code(run)
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
                p.paragraph_format.left_indent = Inches(0.3)

        else:  # texto normal
            _parse_text_block(seg[1], doc)


def _insert_mermaid(doc: Document, code: str):
    """Intenta renderizar Mermaid como imagen; si falla, inserta como bloque de código."""
    print(f"  🎨 Renderizando diagrama Mermaid ({len(code)} chars)...")
    png_bytes = mermaid_to_png(code)
    if png_bytes:
        print("     ✅ OK")
        img_stream = BytesIO(png_bytes)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(img_stream, width=Inches(6.0))
        caption = doc.add_paragraph("Diagrama generado con Mermaid")
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in caption.runs:
            run.font.size = Pt(8)
            run.font.italic = True
            run.font.color.rgb = COLOR_CAPTION
    else:
        print("     ⚠️  Sin imagen, insertando código fuente")
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.3)
        pPr = p._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "F0FDF4")
        pPr.append(shd)
        run = p.add_run(f"[Mermaid diagram — renderizar en editor compatible]\n\n{code}")
        style_run_code(run)
        run.font.color.rgb = RGBColor(0x06, 0x6B, 0x31)


def _parse_text_block(text: str, doc: Document):
    """Procesa el texto no-código de un .md."""
    # Acumular líneas de tabla
    table_buffer: list[str] = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Tabla Markdown
        if RE_TABLE_ROW.match(line):
            table_buffer.append(line)
            i += 1
            continue
        else:
            if table_buffer:
                parse_table(table_buffer, doc)
                table_buffer = []

        stripped = line.strip()

        # Línea horizontal
        if re.match(r"^---+$|^===+$|^\*\*\*+$", stripped):
            add_horizontal_rule(doc)
            i += 1
            continue

        # Encabezados
        hm = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if hm:
            level = len(hm.group(1))
            text_h = hm.group(2).strip()
            # Limpiar emojis del encabezado para Word
            text_h = re.sub(r"[^\x00-\x7FÀ-ɏЀ-ӿ\s\w\-\./,:;!?()\[\]{}'\"]", "", text_h).strip()
            p = doc.add_heading(text_h, level=min(level, 4))
            colors = {1: COLOR_H1, 2: COLOR_H2, 3: COLOR_H3, 4: COLOR_CAPTION}
            for run in p.runs:
                run.font.color.rgb = colors.get(level, COLOR_H3)
            i += 1
            continue

        # Blockquote
        if stripped.startswith(">"):
            bq_text = stripped.lstrip("> ").strip()
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.4)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            add_inline_text(p, bq_text)
            for run in p.runs:
                run.font.italic = True
                run.font.color.rgb = COLOR_BLOCKQUOTE
            # Borde izquierdo
            pPr = p._p.get_or_add_pPr()
            pBdr = OxmlElement("w:pBdr")
            left = OxmlElement("w:left")
            left.set(qn("w:val"), "single")
            left.set(qn("w:sz"), "12")
            left.set(qn("w:color"), "6366F1")
            pBdr.append(left)
            pPr.append(pBdr)
            i += 1
            continue

        # Lista con viñetas
        bm = RE_BULLET.match(line)
        if bm:
            indent_level = len(bm.group(1)) // 2
            item_text = bm.group(3)
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.left_indent = Inches(0.2 + indent_level * 0.2)
            add_inline_text(p, item_text)
            i += 1
            continue

        # Lista ordenada
        om = RE_ORDERED.match(line)
        if om:
            item_text = om.group(2)
            p = doc.add_paragraph(style="List Number")
            add_inline_text(p, item_text)
            i += 1
            continue

        # Párrafo normal
        if stripped:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(4)
            add_inline_text(p, stripped)

        i += 1

    # Vaciar buffer de tabla al final
    if table_buffer:
        parse_table(table_buffer, doc)


# ─── Construcción del documento ───────────────────────────────────────────────

def build_docx(output_path: Path, skip_mermaid: bool = False):
    doc = Document()

    # ── Portada ──────────────────────────────────────────────────────────────
    doc.add_heading("Documentación Técnica", 0)
    title_run = doc.paragraphs[-1].runs[0]
    title_run.font.color.rgb = COLOR_H1
    title_run.font.size = Pt(28)

    sub = doc.add_paragraph("Aseguradora del Sur — Auditor Técnico y Detector de Riesgo Agéntico")
    sub.runs[0].font.size = Pt(14)
    sub.runs[0].font.italic = True
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

    team = doc.add_paragraph("Equipo Miraclex · HackIAthon 2026\nJosue Salazar · Andres Abad · Andres Falconi")
    team.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in team.runs:
        run.font.size = Pt(11)
        run.font.color.rgb = COLOR_CAPTION

    add_page_break(doc)

    # ── Índice de contenidos ─────────────────────────────────────────────────
    doc.add_heading("Índice", level=1)
    doc.paragraphs[-1].runs[0].font.color.rgb = COLOR_H1

    all_files = [(DOCS_DIR / f) for f in MAIN_DOCS_ORDER] + [(DOCS_DIR / f) for f in DIAGRAMS_ORDER]
    existing = [(f, f.stem) for f in all_files if f.exists()]

    for _, stem in existing:
        p = doc.add_paragraph(style="List Bullet")
        run = p.add_run(stem.replace("_", " ").replace("-", " ").title())
        run.font.size = Pt(10)

    add_page_break(doc)

    # ── Sección 1: Documentación principal ──────────────────────────────────
    doc.add_heading("Parte I — Documentación del Sistema", level=1)
    doc.paragraphs[-1].runs[0].font.color.rgb = COLOR_H1
    doc.add_paragraph()

    for rel_path in MAIN_DOCS_ORDER:
        fpath = DOCS_DIR / rel_path
        if not fpath.exists():
            print(f"  ⚠️  No encontrado: {fpath}")
            continue
        print(f"📄 Procesando: {rel_path}")
        md = fpath.read_text(encoding="utf-8")
        render_markdown_to_docx(md, doc, skip_mermaid=skip_mermaid)
        add_horizontal_rule(doc)
        add_page_break(doc)

    # ── Sección 2: Diagramas ─────────────────────────────────────────────────
    doc.add_heading("Parte II — Diagramas Mermaid", level=1)
    doc.paragraphs[-1].runs[0].font.color.rgb = COLOR_H1
    intro = doc.add_paragraph(
        "Esta sección contiene los diagramas Mermaid correspondientes a cada documento "
        "de la Parte I. Los diagramas se renderizan como imágenes PNG via mermaid.ink."
    )
    intro.runs[0].font.size = Pt(10)
    intro.runs[0].font.italic = True
    doc.add_paragraph()

    for rel_path in DIAGRAMS_ORDER:
        fpath = DOCS_DIR / rel_path
        if not fpath.exists():
            print(f"  ⚠️  No encontrado: {fpath}")
            continue
        print(f"📊 Procesando: {rel_path}")
        md = fpath.read_text(encoding="utf-8")
        render_markdown_to_docx(md, doc, skip_mermaid=skip_mermaid)
        add_horizontal_rule(doc)
        add_page_break(doc)

    # ── Guardar ──────────────────────────────────────────────────────────────
    doc.save(str(output_path))
    print(f"\n✅ Documento generado: {output_path}")
    print(f"   Páginas aprox.: {len(doc.paragraphs) // 4} (estimado)")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Convierte docs/ + diagramas/ a un único .docx con imágenes Mermaid."
    )
    parser.add_argument(
        "--output", "-o",
        default="docs/Documentacion_Miraclex.docx",
        help="Ruta del archivo .docx de salida (default: docs/Documentacion_Miraclex.docx)",
    )
    parser.add_argument(
        "--skip-mermaid",
        action="store_true",
        help="Omitir renderizado de imágenes Mermaid (más rápido, inserta código fuente)",
    )
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = Path(__file__).parent.parent / args.output

    print("=" * 60)
    print("  Miraclex — Generador de Documentación .docx")
    print("=" * 60)
    print(f"  Salida: {output}")
    print(f"  Mermaid: {'OMITIDO' if args.skip_mermaid else 'mermaid.ink (requiere internet)'}")
    print()

    build_docx(output, skip_mermaid=args.skip_mermaid)


if __name__ == "__main__":
    main()
