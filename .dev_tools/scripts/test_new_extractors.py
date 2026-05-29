"""
Valida los extractores nuevos contra los PDFs reales de synthetic_data.

Uso:
    python -m Final-reto.dev_tools.scripts.test_new_extractors
    (o ejecutar directo desde Final-reto/)

Recorre los 3 directorios:
  • synthetic_data/DECLARACIÓN DE ACCIDENTE/  → declaration_extractor
  • synthetic_data/PARTE POLICIAL/            → police_report_extractor
  • synthetic_data/FACTURAS/                  → pdf_extractor (formato simple)

Reporta por archivo qué campos clave salieron extraídos y cuáles faltan.
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path

# Permitir ejecución directa desde Final-reto/ sin instalar el paquete
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.declaration_extractor import extract_declaration_from_pdf  # noqa: E402
from backend.police_report_extractor import extract_police_report_from_pdf  # noqa: E402
from backend.pdf_extractor import extract_invoice_from_pdf  # noqa: E402


SYNTHETIC = ROOT / "synthetic_data"


KEY_FIELDS = {
    "declaration": [
        "doc_id", "siniestro_ref", "asegurado_nombre", "poliza_numero",
        "veh_marca", "veh_modelo", "veh_placa", "veh_chasis",
        "accidente_lugar", "accidente_fecha", "accidente_hora",
        "accidente_descripcion", "conductor_cedula",
    ],
    "police": [
        "doc_id", "siniestro_ref", "parte_no", "fecha_elaboracion",
        "zona", "distrito", "calle_1", "fecha_hecho", "hora_aproximada",
        "tipos_accidente", "circunstancias", "p1_nombre", "p1_cedula",
        "veh_placa", "veh_marca",
    ],
    "invoice": [
        "invoice_number", "ruc", "workshop_name", "issue_date",
        "claim_number", "vehicle_plate", "insured_name",
        "subtotal", "iva", "total", "items",
    ],
}


def _is_filled(value) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, (list, dict)) and len(value) == 0:
        return False
    return True


def _report(label: str, data: dict, keys: list) -> tuple[int, int]:
    filled = [k for k in keys if _is_filled(data.get(k))]
    missing = [k for k in keys if not _is_filled(data.get(k))]
    print(f"  ✓ {len(filled)}/{len(keys)}  faltan: {missing}" if missing else f"  ✓ {len(filled)}/{len(keys)}  OK")
    return len(filled), len(keys)


def run_directory(label: str, subdir: str, extractor, key_set: str):
    folder = SYNTHETIC / subdir
    if not folder.exists():
        print(f"[{label}] carpeta no encontrada: {folder}")
        return
    print(f"\n=== {label} ({folder.name}) ===")
    total_f = total_t = 0
    for pdf in sorted(folder.glob("*.pdf")):
        print(f"• {pdf.name}")
        try:
            with open(pdf, "rb") as fh:
                data = extractor(fh.read())
        except Exception as e:
            print(f"  ✗ ERROR: {type(e).__name__}: {e}")
            continue
        f, t = _report(label, data, KEY_FIELDS[key_set])
        total_f += f
        total_t += t
    if total_t:
        pct = total_f / total_t * 100
        print(f"  ── Promedio cobertura: {total_f}/{total_t} ({pct:.0f}%)")


def main():
    run_directory("DECLARACIÓN", "DECLARACIÓN DE ACCIDENTE",
                  extract_declaration_from_pdf, "declaration")
    run_directory("PARTE POLICIAL", "PARTE POLICIAL",
                  extract_police_report_from_pdf, "police")
    run_directory("FACTURAS", "FACTURAS",
                  extract_invoice_from_pdf, "invoice")

    # Dump completo de un PDF de cada tipo para inspección visual
    print("\n=== DUMP COMPLETO (1 ejemplo por tipo) ===")
    samples = [
        ("DECLARACIÓN", "DECLARACIÓN DE ACCIDENTE", extract_declaration_from_pdf),
        ("PARTE POLICIAL", "PARTE POLICIAL", extract_police_report_from_pdf),
        ("FACTURA", "FACTURAS", extract_invoice_from_pdf),
    ]
    for label, sub, ext in samples:
        folder = SYNTHETIC / sub
        if not folder.exists():
            continue
        first = next(iter(sorted(folder.glob("*.pdf"))), None)
        if not first:
            continue
        print(f"\n--- {label}: {first.name} ---")
        try:
            with open(first, "rb") as fh:
                data = ext(fh.read())
            for k, v in data.items():
                if isinstance(v, (str,)) and len(v) > 200:
                    v = v[:200] + "..."
                print(f"  {k}: {v!r}")
        except Exception as e:
            print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()
