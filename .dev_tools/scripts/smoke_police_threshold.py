"""Smoke test del umbral de obligatoriedad del parte policial.

Escenario A — siniestro LEVE: rayón pintura, $400, sin terceros, sin lesionados
  → policy: parte OPCIONAL
  → factura se acepta sin parte (200, no 409)
  → timeline etapa 3 marca skipped=true, required=false
  → audit_post_payment se ejecuta sin finding MISSING_POLICE_REPORT

Escenario B — siniestro GRAVE: robo, $5000
  → policy: parte OBLIGATORIO (cobertura ROBO + monto > umbral)
  → factura sin parte da 409 con razones
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal, init_db
from backend.auth import generate_profile_token, new_token_secret
from backend.models import (
    Profile, Invoice as _Inv, InvoiceItem as _II, AuditResult as _AR,
    AuditFinding as _AF, AccidentDeclaration as _AD, PoliceReport as _PR,
    Siniestro as _Sin,
)

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


ops = ensure_profile("ops_threshold", "operaciones")
H = {"X-Profile-Token": generate_profile_token(ops.id, ops.token_secret)}


def cleanup():
    # Borrar invoices del perfil de este test + cualquier invoice de smoke tests
    # previos que use los invoice_numbers de nuestros PDFs de muestra (la lookup
    # de duplicados en /audit-pdf hoy es global, no por profile).
    sample_invoice_numbers = {"001-002-747311022"}
    invs = db.query(_Inv).filter(
        (_Inv.profile_id == ops.id) | (_Inv.invoice_number.in_(sample_invoice_numbers))
    ).all()
    inv_ids = [i.id for i in invs]
    ar_ids = [a.id for a in db.query(_AR).filter(
        (_AR.profile_id == ops.id) | (_AR.invoice_id.in_(inv_ids or [-1]))
    ).all()]
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


cleanup()
decl_pdf = ROOT / "synthetic_data" / "DECLARACIÓN DE ACCIDENTE" / "DA_SIN-0378_DOC-0952.pdf"
fact_pdf = ROOT / "synthetic_data" / "FACTURAS" / "Muestras_Facturas_Siniestros- SIN-0001.pdf"
fact_bytes = open(fact_pdf, "rb").read()
decl_bytes = open(decl_pdf, "rb").read()


# ═══════════════════════════════════════════════════════════════
# ESCENARIO A — LEVE: rayón pintura, $400, sin terceros declarado
# ═══════════════════════════════════════════════════════════════
print("\n══════════════ ESCENARIO A — leve (no requiere parte) ══════════════")

r = client.post("/api/claims", headers=H, json={
    "policy_number": "POL-LEVE-001",
    "insured_id": "INS-LEVE-001", "insured_name": "Cliente Leve",
    "ramo": "Vehículos", "cobertura": "Daño", "estado": "Reserva",
    "incident_date": "2025-02-01", "monto_reclamado": 400.0,
    "sucursal": "Quito", "descripcion": "Rayón menor en puerta",
    "vehicle_plate": "PIC-5519", "vehicle_brand": "NISSAN",
    "vehicle_model": "X-TRAIL", "vehicle_year": 2022,
})
assert r.status_code == 201, r.text
sid_leve = r.json()["id"]
print(f"  ✓ Siniestro leve creado: id={sid_leve}, monto=$400, cobertura=Daño")

# Sin declaración aún → policy debe decir NO requerido (sólo criterios de siniestro)
r = client.get(f"/api/claims/{sid_leve}/police-requirement", headers=H)
assert r.status_code == 200
pol = r.json()
print(f"  policy sin decl: required={pol['required']} reasons={pol['reasons']}")
assert pol["required"] is False, f"Esperado NO requerido, obtuve required={pol['required']}"

# Subir declaración (declaración real menciona ROBO en contrario, así que para
# este caso usamos una "leve" — pero el PDF de muestra no es leve. Aceptamos
# que la declaración mencionará terceros y eso elevará el flag).
r = client.post(f"/api/claims/{sid_leve}/declaration", headers=H,
                files={"file": (decl_pdf.name, decl_bytes, "application/pdf")})
assert r.status_code == 201

# Re-consultar la política — el PDF real tiene "Benítez Salazar Jorge Eduardo"
# como propietario del vehículo contrario, así que ahora SÍ requerirá parte.
r = client.get(f"/api/claims/{sid_leve}/police-requirement", headers=H)
pol = r.json()
print(f"  policy con decl (tiene tercero): required={pol['required']}")
print(f"    razones: {pol['reasons']}")
# La declaración del PDF tiene contrario → required=True. Eso es CORRECTO según
# nuestra política. El test verifica que el flag refleja los datos reales.

# Para forzar el escenario LEVE, borramos manualmente los campos del contrario
# en la declaración persistida.
decl_db = db.query(_AD).filter(_AD.siniestro_id == sid_leve).first()
decl_db.contrario_placa = None
decl_db.contrario_propietario = None
decl_db.autoridades_lugar_asistencia_medica = "No se reportan lesionados"
db.commit()

r = client.get(f"/api/claims/{sid_leve}/police-requirement", headers=H)
pol = r.json()
print(f"  policy LEVE (sin tercero, sin lesionados): required={pol['required']}")
assert pol["required"] is False, f"Esperado required=False, obtuve {pol}"
print(f"  ✓ Sin parte: {'OPCIONAL' if pol['can_skip'] else 'OBLIGATORIO'}")

# Subir factura SIN parte → debe aceptarse
r = client.post("/api/audit-pdf", headers=H,
                files={"file": (fact_pdf.name, fact_bytes, "application/pdf")},
                data={"claim_number": f"SIN-{sid_leve}"})
print(f"  POST factura sin parte → {r.status_code} (esperado 200)")
assert r.status_code == 200, f"Esperado 200, obtuve {r.status_code}: {r.text}"
resp = r.json()
print(f"    resp.status: {resp.get('status')}  message: {resp.get('message')}")
post_a = resp.get("post_payment_audit")
if not post_a and resp.get("status") == "already_exists":
    # La factura ya existía de un test previo; correrla manualmente para validar
    from backend.agent import AuditAgent
    agent = AuditAgent(db, profile_id=ops.id)
    post_a = agent.audit_post_payment(sid_leve, invoice_id=resp["invoice_id"])
assert post_a and not post_a.get("error"), f"audit_post_payment no se disparó: {post_a}"
print(f"  ✓ Auditoría post-pago ejecutada sin parte: risk={post_a['risk_score']}")
# Verificar que NO hay finding MISSING_POLICE_REPORT
missing = [f for f in post_a["findings"] if f["finding_type"] == "missing_police_report"]
assert not missing, f"No debería haber finding missing_police_report: {missing}"
print("  ✓ No emitió finding MISSING_POLICE_REPORT (parte era opcional)")

# Timeline: etapa 3 debe estar skipped
r = client.get(f"/api/claims/{sid_leve}/timeline", headers=H)
tl = r.json()
stage3 = tl["stages"]["3_police_report"]
print(f"  timeline etapa 3: done={stage3['done']} skipped={stage3['skipped']} required={stage3['required']}")
assert stage3["skipped"] is True, f"Etapa 3 debe estar skipped: {stage3}"
assert tl["stages"]["4_invoices"]["done"] is True
assert tl["stages"]["5_post_payment_audit"]["done"] is True


# ═══════════════════════════════════════════════════════════════
# ESCENARIO B — GRAVE: robo, $5000 (cobertura ROBO + monto alto)
# ═══════════════════════════════════════════════════════════════
print("\n══════════════ ESCENARIO B — grave (requiere parte) ══════════════")

r = client.post("/api/claims", headers=H, json={
    "policy_number": "POL-GRAVE-001",
    "insured_id": "INS-GRAVE-001", "insured_name": "Cliente Grave",
    "ramo": "Vehículos", "cobertura": "Robo", "estado": "Reserva",
    "incident_date": "2025-02-15", "monto_reclamado": 5000.0,
    "sucursal": "Cuenca", "descripcion": "Robo total del vehículo",
    "vehicle_plate": "AZY-7734", "vehicle_brand": "NISSAN",
    "vehicle_model": "FRONTIER", "vehicle_year": 2019,
})
assert r.status_code == 201, r.text
sid_grave = r.json()["id"]
print(f"  ✓ Siniestro grave creado: id={sid_grave}, monto=$5000, cobertura=Robo")

r = client.get(f"/api/claims/{sid_grave}/police-requirement", headers=H)
pol = r.json()
print(f"  policy: required={pol['required']}")
for reason in pol["reasons"]:
    print(f"    • {reason}")
assert pol["required"] is True, "Robo + monto alto debe requerir parte"

# Subir declaración
r = client.post(f"/api/claims/{sid_grave}/declaration", headers=H,
                files={"file": (decl_pdf.name, decl_bytes, "application/pdf")})
assert r.status_code == 201

# Subir factura SIN parte → debe dar 409
r = client.post("/api/audit-pdf", headers=H,
                files={"file": (fact_pdf.name, fact_bytes, "application/pdf")},
                data={"claim_number": f"SIN-{sid_grave}"})
print(f"  POST factura sin parte → {r.status_code} (esperado 409)")
assert r.status_code == 409, f"Esperado 409, obtuve {r.status_code}: {r.text}"
print(f"  ✓ Bloqueado correctamente: {r.json()['detail'][:140]}...")

db.close()
print("\nSmoke test umbral parte policial: OK ✓")
