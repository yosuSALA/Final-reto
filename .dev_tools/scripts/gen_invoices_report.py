import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.test_invoice_generator import generate_random_invoice

print("=" * 60)
print("GENERACION DE FACTURAS DE PRUEBA ADICIONALES")
print("=" * 60)

for i in range(8):
    r = generate_random_invoice("mixed")
    print(f"\n  Factura {i+1}: {r['filename']}")
    print(f"  Taller: {r['workshop_comercial']}")
    print(f"  Siniestro: {r['claim_number']} - {r['claim_type']}")
    print(f"  Items: {r['items_count']}")
    print(f"  Subtotal: ${r['subtotal']} | IVA: ${r['iva']} | Total: ${r['total']}")
    print(f"  Hallazgo esperado: {r['expected_finding']}")

print("\n" + "=" * 60)
print(F"TOTAL: 8 facturas generadas en backend/test_pdfs/")
print("=" * 60)
