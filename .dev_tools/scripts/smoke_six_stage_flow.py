"""Smoke test del flujo completo de 6 etapas con PDFs reales.

Cubre:
  1. Registro de siniestro (POST /api/claims)
  2. Subir declaración + verificar auditoría inicial automática
  3. Bloqueo: intentar subir factura sin parte → 409
  4. Subir parte policial
  5. Subir factura → verificar auditoría post-pago automática
  6. Consultar timeline → todas las etapas done
  7. Sanity: re-uploadear parte y verificar que dispara post-payment con
     auditoría incluyendo cross-checks.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal, init_db, DEFAULT_PROFILE_ID
from backend.auth import generate_profile_token, new_token_secret
from backend.models import Profile

init_db()
client = TestClient(app)
db = SessionLocal()


def ensure_profile(name, role):
    p = db.query(Profile).filter(Profile.name == name).first()
    if not p:
        p = Profile(
            id=f"99999999-0000-0000-0000-{abs(hash(name)) % 10**11:011d}"[:36],
            name=name, display_name=name, role=role,
            token_secret=new_token_secret(), is_active=1,
        )
        db.add(p)
        db.commit()
    return p


ops = ensure_profile("ops_e2e", "operaciones")
ops_headers = {"X-Profile-Token": generate_profile_token(ops.id, ops.token_secret)}

# Limpiar artefactos de runs anteriores con este perfil — el test debe ser
# idempotente. Borrar en orden inverso de FKs.
from backend.models import (
    Invoice as _Inv, InvoiceItem as _II, AuditResult as _AR, AuditFinding as _AF,
    AccidentDeclaration as _AD, PoliceReport as _PR, Siniestro as _Sin,
)
inv_ids = [i.id for i in db.query(_Inv).filter(_Inv.profile_id == ops.id).all()]
ar_ids = [a.id for a in db.query(_AR).filter(_AR.profile_id == ops.id).all()]
sin_ids = [s.id_siniestro for s in db.query(_Sin).filter(_Sin.profile_id == ops.id).all()]
if ar_ids:
    db.query(_AF).filter(_AF.audit_result_id.in_(ar_ids)).delete(synchronize_session=False)
    db.query(_AR).filter(_AR.id.in_(ar_ids)).delete(synchronize_session=False)
if inv_ids:
    db.query(_II).filter(_II.invoice_id.in_(inv_ids)).delete(synchronize_session=False)
    db.query(_Inv).filter(_Inv.id.in_(inv_ids)).delete(synchronize_session=False)
if sin_ids:
    db.query(_AD).filter(_AD.siniestro_id.in_(sin_ids)).delete(synchronize_session=False)
    db.query(_PR).filter(_PR.siniestro_id.in_(sin_ids)).delete(synchronize_session=False)
    db.query(_Sin).filter(_Sin.id_siniestro.in_(sin_ids)).delete(synchronize_session=False)
db.commit()
print(f"[cleanup] removed {len(sin_ids)} siniestros, {len(inv_ids)} facturas, {len(ar_ids)} auditorías del perfil ops_e2e")

# ── ETAPA 1: registrar siniestro ──
print("\n=== ETAPA 1: Registro de Siniestro ===")
r = client.post(
    "/api/claims", headers=ops_headers,
    json={
        "policy_number": "POL-E2E-001",
        "insured_id": "E2E-INS-001",
        "insured_name": "Ruiz Andrade Patricia Elena",
        "ramo": "Vehículos",
        "cobertura": "Choque",
        "estado": "Reserva",
        "incident_date": "2025-01-15",
        "monto_reclamado": 5528.0,
        "sucursal": "Quito",
        "descripcion": "Choque frontal en intersección",
        "vehicle_plate": "PIC-5519",
        "vehicle_brand": "NISSAN",
        "vehicle_model": "X-TRAIL",
        "vehicle_year": 2022,
    },
)
assert r.status_code == 201, f"POST claims falló: {r.status_code} {r.text}"
claim = r.json()
claim_id = claim["id"]
print(f"  ✓ Siniestro {claim_id} (SIN-{claim_id}) creado")

# ── ETAPA 4 ANTES DE 3: debe fallar con 409 ──
print("\n=== Bloqueo: factura sin parte policial debe rechazarse ===")
fact_pdf = ROOT / "synthetic_data" / "FACTURAS" / "Muestras_Facturas_Siniestros- SIN-0001.pdf"
with open(fact_pdf, "rb") as fh:
    fact_bytes = fh.read()
r = client.post(
    "/api/audit-pdf", headers=ops_headers,
    files={"file": (fact_pdf.name, fact_bytes, "application/pdf")},
    data={"claim_number": f"SIN-{claim_id}"},
)
print(f"  POST factura sin parte → {r.status_code}")
assert r.status_code == 409, f"Esperado 409, obtuve {r.status_code}: {r.text}"
print(f"  ✓ Bloqueado: {r.json()['detail'][:80]}...")

# ── ETAPA 1 → 2: subir declaración + verificar auditoría inicial ──
print("\n=== ETAPA 1→2: Declaración + Auditoría Inicial automática ===")
decl_pdf = ROOT / "synthetic_data" / "DECLARACIÓN DE ACCIDENTE" / "DA_SIN-0378_DOC-0952.pdf"
with open(decl_pdf, "rb") as fh:
    decl_bytes = fh.read()
r = client.post(
    f"/api/claims/{claim_id}/declaration", headers=ops_headers,
    files={"file": (decl_pdf.name, decl_bytes, "application/pdf")},
)
assert r.status_code == 201, f"POST decl falló: {r.status_code} {r.text}"
resp = r.json()
print(f"  ✓ Declaración cargada (doc_id={resp['declaration']['doc_id']})")
init_audit = resp["initial_audit"]
assert init_audit is not None, "audit_initial no se disparó"
print(f"  ✓ Auditoría inicial: stage={init_audit['audit_stage']} risk={init_audit['risk_score']} status={init_audit['status']}")
print(f"     hallazgos: {init_audit['findings_count']}")

# ── ETAPA 4 ANTES DE 3: aún debe fallar (sólo declaración) ──
r = client.post(
    "/api/audit-pdf", headers=ops_headers,
    files={"file": (fact_pdf.name, fact_bytes, "application/pdf")},
    data={"claim_number": f"SIN-{claim_id}"},
)
assert r.status_code == 409, f"Aún debería bloquear; obtuve {r.status_code}"
print("  ✓ Factura aún bloqueada (sólo declaración no basta)")

# ── ETAPA 3: subir parte policial ──
print("\n=== ETAPA 3: Parte Policial ===")
pp_pdf = ROOT / "synthetic_data" / "PARTE POLICIAL" / "PP_SIN-0005_DOC-0012.pdf"
with open(pp_pdf, "rb") as fh:
    pp_bytes = fh.read()
r = client.post(
    f"/api/claims/{claim_id}/police-report", headers=ops_headers,
    files={"file": (pp_pdf.name, pp_bytes, "application/pdf")},
)
assert r.status_code == 201, f"POST parte falló: {r.status_code} {r.text}"
resp = r.json()
print(f"  ✓ Parte cargado (parte_no={resp['police_report']['parte_no']})")
print(f"     warnings: {resp['warnings']}")
print(f"     post_payment_audit: {resp['post_payment_audit']} (debe ser None — sin facturas aún)")

# ── ETAPA 4: subir factura → debe permitirse + disparar post-payment ──
print("\n=== ETAPA 4→5: Factura + Auditoría Post-Pago automática ===")
r = client.post(
    "/api/audit-pdf", headers=ops_headers,
    files={"file": (fact_pdf.name, fact_bytes, "application/pdf")},
    data={"claim_number": f"SIN-{claim_id}"},
)
assert r.status_code == 200, f"POST factura falló: {r.status_code} {r.text}"
resp = r.json()
print(f"  ✓ Factura cargada (id={resp['invoice_id']})")
post_audit = resp.get("post_payment_audit")
assert post_audit and not post_audit.get("error"), f"post_payment_audit no se disparó: {post_audit}"
print(f"  ✓ Auditoría post-pago: stage={post_audit['audit_stage']} risk={post_audit['risk_score']} status={post_audit['status']}")
print(f"     hallazgos: {post_audit['findings_count']}")
print(f"     sobrecobro detectado: ${post_audit['total_overcharge']}")
for f in post_audit["findings"][:5]:
    print(f"       • [{f['severity']}] {f['title']}")

# ── ETAPA: Timeline ──
print("\n=== TIMELINE ===")
r = client.get(f"/api/claims/{claim_id}/timeline", headers=ops_headers)
assert r.status_code == 200
tl = r.json()
print(f"  siniestro: {tl['claim_number']}")
for stage_name, stage in tl["stages"].items():
    status = "✓" if stage["done"] else "✗"
    blocked = f" (bloqueado por: {stage['blocked_by']})" if stage["blocked_by"] else ""
    print(f"  {status} {stage_name}{blocked}")

# Verificar que las primeras 5 etapas están done; la 6 puede no estarlo
# (depende de approve/reject manual).
assert tl["stages"]["1_registered"]["done"], "Etapa 1 debe estar done"
assert tl["stages"]["2_initial_audit"]["done"], "Etapa 2 debe estar done"
assert tl["stages"]["3_police_report"]["done"], "Etapa 3 debe estar done"
assert tl["stages"]["4_invoices"]["done"], "Etapa 4 debe estar done"
assert tl["stages"]["5_post_payment_audit"]["done"], "Etapa 5 debe estar done"

# ── Sanity: re-subir parte → debe re-ejecutar post-pago porque ya hay factura ──
print("\n=== Sanity: re-upload parte con facturas existentes ===")
r = client.post(
    f"/api/claims/{claim_id}/police-report", headers=ops_headers,
    files={"file": (pp_pdf.name, pp_bytes, "application/pdf")},
)
assert r.status_code == 201
resp = r.json()
post = resp.get("post_payment_audit")
assert post and not post.get("error"), f"Re-trigger falló: {post}"
print(f"  ✓ Re-trigger post-pago: status={post['status']}, hallazgos={post['findings_count']}")

db.close()
print("\nSmoke test END-TO-END del flujo de 6 etapas: OK ✓")
