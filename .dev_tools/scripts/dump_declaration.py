"""Dump del texto y tablas crudas de un PDF de declaración para debugging."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pdfplumber

PDF = ROOT / "synthetic_data" / "DECLARACIÓN DE ACCIDENTE" / "DA_SIN-0378_DOC-0952.pdf"

with pdfplumber.open(PDF) as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"\n========== PÁGINA {i+1} — TEXTO ==========")
        print(page.extract_text())
        print(f"\n========== PÁGINA {i+1} — TABLAS ==========")
        for j, t in enumerate(page.extract_tables()):
            print(f"--- tabla {j} ---")
            for row in t:
                print(row)
