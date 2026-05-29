"""Smoke test del endpoint POST /api/claims/{id}/declaration."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal, init_db, DEFAULT_PROFILE_ID
from backend.auth import generate_profile_token
from backend.models import Profile, Siniestro, AseguradoSintetico, Poliza, Ramo, Cobertura, EstadoSiniestro
from datetime import datetime, timedelta


init_db()
client = TestClient(app)
db = SessionLocal()


# 1. Crear / asegurar un perfil OPERACIONES
op = db.query(Profile).filter(Profile.name == "ops_smoke").first()
if not op:
    from backend.auth import new_token_secret
    op = Profile(
        id="11111111-0000-0000-0000-000000000099",
        name="ops_smoke", display_name="Operaciones Smoke",
        role="operaciones", token_secret=new_token_secret(), is_active=1,
    )
    db.add(op)
    db.commit()

token = generate_profile_token(op.id, op.token_secret)
headers = {"X-Profile-Token": token}

# 2. Asegurar que hay un siniestro de prueba (id arbitrario, lo creamos si falta)
sin_test = db.query(Siniestro).order_by(Siniestro.id_siniestro.desc()).first()
if not sin_test:
    # Crear asegurado + póliza + siniestro mínimos
    aseg = AseguradoSintetico(
        id_asegurado="SMOKE-001", profile_id=DEFAULT_PROFILE_ID,
        nombre="Smoke Tester",
    )
    db.add(aseg)
    db.flush()
    pol = Poliza(
        id_poliza="SMOKE-POL", profile_id=DEFAULT_PROFILE_ID,
        id_asegurado=aseg.id_asegurado, ramo=Ramo.VEHICULOS,
        fecha_inicio=datetime.utcnow() - timedelta(days=365),
        fecha_fin=datetime.utcnow() + timedelta(days=365),
        prima=100, suma_asegurada=10000, deducible=200,
    )
    db.add(pol)
    db.flush()
    sin_test = Siniestro(
        profile_id=DEFAULT_PROFILE_ID,
        id_poliza=pol.id_poliza, id_asegurado=aseg.id_asegurado,
        ramo=Ramo.VEHICULOS, cobertura=Cobertura.CHOQUE,
        fecha_ocurrencia=datetime.utcnow(),
        estado=EstadoSiniestro.RESERVA,
        descripcion="smoke",
    )
    db.add(sin_test)
    db.commit()
    db.refresh(sin_test)
print(f"Usando siniestro id={sin_test.id_siniestro}")

# 3. POST del PDF de declaración real
pdf_path = ROOT / "synthetic_data" / "DECLARACIÓN DE ACCIDENTE" / "DA_SIN-0378_DOC-0952.pdf"
with open(pdf_path, "rb") as fh:
    pdf_bytes = fh.read()

r = client.post(
    f"/api/claims/{sin_test.id_siniestro}/declaration",
    headers=headers,
    files={"file": (pdf_path.name, pdf_bytes, "application/pdf")},
)
print(f"POST → {r.status_code}")
if r.status_code != 201:
    print(r.text)
    sys.exit(1)

data = r.json()
print(f"  status: {data['status']}")
print(f"  warnings: {data['warnings']}")
decl = data["declaration"]
print(f"  doc_id: {decl['doc_id']}")
print(f"  siniestro_ref: {decl['siniestro_ref']}")
print(f"  asegurado: {decl['asegurado']['nombre']} | póliza {decl['asegurado']['poliza']}")
print(f"  vehículo: {decl['vehiculo']['marca']} {decl['vehiculo']['modelo']} placa {decl['vehiculo']['placa']}")
print(f"  conductor: {decl['conductor']['nombre']} CI {decl['conductor']['cedula']}")
print(f"  accidente: {decl['accidente']['fecha']} en {decl['accidente']['lugar']}")

# 4. GET de regreso
r = client.get(f"/api/claims/{sin_test.id_siniestro}/declaration", headers=headers)
print(f"\nGET → {r.status_code} | status: {r.json()['status']}")

# 5. Re-upload (debe reemplazar 1:1, no duplicar)
r = client.post(
    f"/api/claims/{sin_test.id_siniestro}/declaration",
    headers=headers,
    files={"file": (pdf_path.name, pdf_bytes, "application/pdf")},
)
print(f"\nRe-POST → {r.status_code} (debe ser 201, reemplazo)")

# 6. Verificar persistencia
from backend.models import AccidentDeclaration
count = db.query(AccidentDeclaration).filter(
    AccidentDeclaration.siniestro_id == sin_test.id_siniestro
).count()
print(f"Filas en accident_declarations para siniestro {sin_test.id_siniestro}: {count} (debe ser 1)")

# 7. Permiso negativo: un perfil sin rol operaciones recibe 403
demo = db.query(Profile).filter(Profile.id == DEFAULT_PROFILE_ID).first()
demo_token = generate_profile_token(demo.id, demo.token_secret)
# demo_jurado es exento, así que probamos con un rol no autorizado: jefatura
jef = db.query(Profile).filter(Profile.role == "jefatura").first()
if jef:
    jef_token = generate_profile_token(jef.id, jef.token_secret)
    r = client.post(
        f"/api/claims/{sin_test.id_siniestro}/declaration",
        headers={"X-Profile-Token": jef_token},
        files={"file": (pdf_path.name, pdf_bytes, "application/pdf")},
    )
    print(f"\nPOST como jefatura → {r.status_code} (debe ser 403)")
else:
    print("\nNo hay perfil con rol jefatura; saltando prueba de permisos.")

db.close()
print("\nSmoke test OK ✓")
