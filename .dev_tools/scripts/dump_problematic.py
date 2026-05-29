"""Dump del raw text de los PDFs que fallan en algunos campos."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pdfplumber

cases = [
    ("PARTE", ROOT / "synthetic_data" / "PARTE POLICIAL" / "PP_SIN-0022_DOC-0054.pdf"),
    ("FACTURA", ROOT / "synthetic_data" / "FACTURAS" / "Muestras_Facturas_Siniestros-SIN-0004.pdf"),
]

for label, pdf_path in cases:
    print(f"\n###### {label}: {pdf_path.name} ######")
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"--- página {i+1} ---")
            print(page.extract_text())
