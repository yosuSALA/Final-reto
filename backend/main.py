"""
API FastAPI — Auditor Agéntico de Facturación de Siniestros.
Sistema de perfiles aislados: cada request lleva X-Profile-Token.
"""
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import sys
import os
import csv
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from dotenv import load_dotenv

load_dotenv()

from backend.database import get_db, init_db, DEFAULT_PROFILE_ID
from backend.seed_data import seed_database
from backend.agent import AuditAgent
from backend.auth import verify_profile_token, generate_profile_token, new_token_secret, verify_profile_access_password
from backend.profile_scope import ProfileScope
from backend.models import (
    Profile, Siniestro, Invoice, InvoiceItem, TariffItem,
    AuditResult, AuditFinding, Workshop, AuditStatus,
    FindingSeverity, FindingType, Ramo, Cobertura, EstadoSiniestro,
    Poliza, AseguradoSintetico, Vehiculo, Documento,
)

app = FastAPI(title="Auditor Agentico de Siniestros", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class NoCacheDevMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/app/") and (path.endswith(".js") or path.endswith(".css")):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app.add_middleware(NoCacheDevMiddleware)

frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")

logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logo")
if os.path.exists(logo_path):
    app.mount("/logo", StaticFiles(directory=logo_path), name="logo")


@app.on_event("startup")
def startup():
    init_db()
    seed_database()


@app.get("/")
def read_root():
    landing_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "landing.html")
    if os.path.exists(landing_path):
        return FileResponse(landing_path)
    return {"message": "landing.html not found"}


# ── Dependencias de autenticación de perfil ────────────

def get_profile(
    x_profile_token: str = Header(None, alias="X-Profile-Token"),
    db: Session = Depends(get_db),
) -> Profile:
    """Valida X-Profile-Token y retorna el perfil activo. 403 si falta o es inválido."""
    if not x_profile_token:
        raise HTTPException(
            status_code=403,
            detail="Header X-Profile-Token requerido. Selecciona un perfil primero.",
        )
    profile = verify_profile_token(x_profile_token, db)
    if not profile:
        raise HTTPException(
            status_code=403,
            detail="Token de perfil inválido o perfil inactivo.",
        )
    return profile


def get_scope(
    profile: Profile = Depends(get_profile),
    db: Session = Depends(get_db),
) -> ProfileScope:
    """Retorna un ProfileScope listo para filtrar datos por perfil."""
    return ProfileScope(db, profile)


# ── Endpoints de perfiles (sin autenticación) ──────────

class ProfileCreate(BaseModel):
    name: str
    display_name: str = ""
    role: str = "analista"


class ProfileUpdate(BaseModel):
    display_name: str


class ProfileAccessRequest(BaseModel):
    password: str


@app.get("/api/profiles")
def list_profiles(db: Session = Depends(get_db)):
    """Lista todos los perfiles activos. No requiere token."""
    profiles = db.query(Profile).filter(Profile.is_active == 1).order_by(Profile.created_at).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "display_name": p.display_name or p.name,
            "role": p.role or "analista",
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in profiles
    ]


@app.post("/api/profiles", status_code=201)
def create_profile(data: ProfileCreate, db: Session = Depends(get_db)):
    """Crea un perfil nuevo y retorna su token firmado."""
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="El nombre del perfil es requerido.")
    if db.query(Profile).filter(Profile.name == name).first():
        raise HTTPException(status_code=409, detail=f"Ya existe un perfil con el nombre '{name}'.")

    valid_roles = {"demo_jurado", "analista", "antifraude", "jefatura", "auditoria"}
    role = data.role if data.role in valid_roles else "analista"

    import uuid
    secret = new_token_secret()
    profile = Profile(
        id=str(uuid.uuid4()),
        name=name,
        display_name=(data.display_name or name).strip(),
        role=role,
        token_secret=secret,
        is_active=1,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    token = generate_profile_token(profile.id, secret)
    return {
        "id": profile.id,
        "name": profile.name,
        "display_name": profile.display_name,
        "role": profile.role or "analista",
        "token": token,
        "created_at": profile.created_at.isoformat(),
    }


@app.post("/api/profiles/{profile_id}/token")
def get_profile_token(profile_id: str, data: ProfileAccessRequest, db: Session = Depends(get_db)):
    """
    Genera (o regenera) el token para un perfil existente.
    Equivale al 'login': quien conoce el profile_id puede obtener su token.
    Los UUIDs no son adivinables, lo que previene enumeración de perfiles.
    """
    if not os.environ.get("PROFILE_ACCESS_PASSWORD"):
        raise HTTPException(
            status_code=503,
            detail="PROFILE_ACCESS_PASSWORD no está configurada en .env.",
        )
    if not verify_profile_access_password(data.password):
        raise HTTPException(status_code=403, detail="Contraseña de acceso inválida.")

    profile = db.query(Profile).filter(
        Profile.id == profile_id, Profile.is_active == 1
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado.")
    token = generate_profile_token(profile.id, profile.token_secret)
    return {
        "token": token,
        "profile_id": profile.id,
        "name": profile.name,
        "display_name": profile.display_name or profile.name,
        "role": profile.role or "analista",
    }


@app.put("/api/profiles/{profile_id}")
def update_profile(
    profile_id: str,
    data: ProfileUpdate,
    profile: Profile = Depends(get_profile),
    db: Session = Depends(get_db),
):
    """Actualiza el display_name de un perfil. Solo puede actualizar el propio."""
    if profile.id != profile_id:
        raise HTTPException(status_code=403, detail="Solo puedes modificar tu propio perfil.")
    profile.display_name = data.display_name.strip()
    db.commit()
    return {"id": profile.id, "display_name": profile.display_name}


@app.delete("/api/profiles/{profile_id}")
def delete_profile(
    profile_id: str,
    profile: Profile = Depends(get_profile),
    db: Session = Depends(get_db),
):
    """Desactiva un perfil (soft delete). Solo puede borrarse a sí mismo."""
    if profile.id != profile_id:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tu propio perfil.")
    if profile_id == DEFAULT_PROFILE_ID:
        raise HTTPException(status_code=400, detail="El perfil por defecto no puede eliminarse.")
    profile.is_active = 0
    db.commit()
    return {"status": "deleted", "profile_id": profile_id}


# ── Dashboard ──────────────────────────────────────────

@app.get("/api/dashboard")
def get_dashboard(
    include_test: int = 0,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    inv_q = scope.invoices()
    ar_q = scope.audit_results()
    if not include_test:
        inv_q = inv_q.filter((Invoice.is_test == 0) | (Invoice.is_test.is_(None)))
        ar_q = ar_q.filter((AuditResult.is_test == 0) | (AuditResult.is_test.is_(None)))

    total_invoices = inv_q.count()
    total_audited = ar_q.count()
    total_claims = scope.siniestros().count()
    results = ar_q.all()
    total_overcharge = sum(r.total_overcharge or 0 for r in results)

    critical_count = warning_count = clean_count = escalated_count = 0
    for r in results:
        findings = db.query(AuditFinding).filter(AuditFinding.audit_result_id == r.id).all()
        has_critical = any(f.severity.value == "critical" for f in findings)
        has_warning = any(f.severity.value == "warning" for f in findings)
        if has_critical:
            critical_count += 1
        elif has_warning:
            warning_count += 1
        else:
            clean_count += 1
        if r.status == AuditStatus.ESCALATED:
            escalated_count += 1

    invoice_total_sum = sum(i.total or 0 for i in inv_q.all())
    test_count = scope.invoices().filter(Invoice.is_test == 1).count()
    return {
        "total_invoices": total_invoices,
        "total_audited": total_audited,
        "total_claims": total_claims,
        "total_overcharge": round(total_overcharge, 2),
        "invoice_total_sum": round(invoice_total_sum, 2),
        "savings_pct": round((total_overcharge / invoice_total_sum * 100) if invoice_total_sum > 0 else 0, 1),
        "by_severity": {"critical": critical_count, "warning": warning_count, "clean": clean_count},
        "escalated_count": escalated_count,
        "test_count": test_count,
        "include_test": bool(include_test),
    }


@app.get("/api/dashboard/claims-by-day")
def get_claims_by_day(
    days: int = 30,
    scope: ProfileScope = Depends(get_scope),
):
    from datetime import timedelta
    from collections import Counter

    siniestros = scope.siniestros().all()
    counts = Counter()
    for s in siniestros:
        d = s.fecha_ocurrencia or s.fecha_reporte
        if d:
            counts[d.date().isoformat()] += 1

    today = datetime.utcnow().date()
    series = []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        key = day.isoformat()
        series.append({"date": key, "count": counts.get(key, 0)})
    return {"days": days, "series": series, "total": sum(p["count"] for p in series)}


# ── Auditoría ──────────────────────────────────────────

@app.post("/api/audit/{invoice_id}")
def audit_invoice(
    invoice_id: int,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("audit_results")
    invoice = scope.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada o no pertenece a este perfil.")
    agent = AuditAgent(db, profile_id=scope.profile_id)
    result = agent.audit_invoice(invoice_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/api/audit-rules/{invoice_id}")
def audit_invoice_rules(
    invoice_id: int,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("audit_results")
    invoice = scope.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada o no pertenece a este perfil.")
    agent = AuditAgent(db, profile_id=scope.profile_id)
    result = agent.audit_invoice(invoice_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    result["audit_engine"] = "rules"
    return result


@app.post("/api/audit-all")
def audit_all(
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("audit_results")
    agent = AuditAgent(db, profile_id=scope.profile_id)
    invoices = scope.invoices().all()
    results = [agent.audit_invoice(inv.id) for inv in invoices]
    return {"audited": len(results), "results": results}


@app.get("/api/audit-results")
def get_audit_results(
    include_test: int = 1,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    q = scope.audit_results()
    if not include_test:
        q = q.filter((AuditResult.is_test == 0) | (AuditResult.is_test.is_(None)))
    results = q.all()
    output = []
    for r in results:
        invoice = scope.get_invoice(r.invoice_id)
        siniestro = scope.get_siniestro(r.siniestro_id)
        workshop = scope.get_workshop(invoice.workshop_id) if invoice else None
        findings = db.query(AuditFinding).filter(AuditFinding.audit_result_id == r.id).all()
        output.append({
            "audit_id": r.id,
            "invoice_id": r.invoice_id,
            "invoice_number": invoice.invoice_number if invoice else "",
            "claim_number": f"SIN-{siniestro.id_siniestro}" if siniestro else "",
            "claim_type": siniestro.ramo.value if siniestro else "",
            "workshop_name": workshop.name if workshop else "",
            "status": r.status.value,
            "risk_score": r.risk_score,
            "total_overcharge": r.total_overcharge,
            "invoice_total": invoice.total if invoice else 0,
            "summary": r.summary,
            "audit_engine": getattr(r, "audit_engine", "rules") or "rules",
            "is_test": bool(getattr(r, "is_test", 0) or 0),
            "audited_at": r.audited_at.isoformat() if r.audited_at else None,
            "findings_count": {
                "critical": sum(1 for f in findings if f.severity.value == "critical"),
                "warning": sum(1 for f in findings if f.severity.value == "warning"),
                "info": sum(1 for f in findings if f.severity.value == "info"),
            },
            "findings": [{
                "id": f.id, "finding_type": f.finding_type.value, "severity": f.severity.value,
                "title": f.title, "description": f.description, "item_description": f.item_description,
                "expected_value": f.expected_value, "actual_value": f.actual_value,
                "difference": f.difference, "recommendation": f.recommendation,
            } for f in findings],
        })
    return output


@app.get("/api/audit-results/{audit_id}")
def get_audit_result(
    audit_id: int,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    r = scope.get_audit_result(audit_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resultado no encontrado o no pertenece a este perfil.")
    invoice = scope.get_invoice(r.invoice_id)
    siniestro = scope.get_siniestro(r.siniestro_id)
    workshop = scope.get_workshop(invoice.workshop_id) if invoice else None
    findings = db.query(AuditFinding).filter(AuditFinding.audit_result_id == r.id).all()
    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == r.invoice_id).all()
    tariff_map = {t.code: {"code": t.code, "description": t.description, "max_price": t.max_price, "tolerance_pct": t.tolerance_pct}
                  for t in scope.tariffs().all()}
    return {
        "audit_id": r.id, "invoice_id": r.invoice_id,
        "invoice_number": invoice.invoice_number if invoice else "",
        "claim_number": f"SIN-{siniestro.id_siniestro}" if siniestro else "",
        "claim_type": siniestro.ramo.value if siniestro else "",
        "claim_description": siniestro.descripcion if siniestro else "",
        "vehicle": "", "vehicle_plate": "",
        "insured_name": siniestro.id_asegurado if siniestro else "",
        "workshop_name": workshop.name if workshop else "",
        "workshop_ruc": workshop.ruc if workshop else "",
        "status": r.status.value, "risk_score": r.risk_score,
        "total_overcharge": r.total_overcharge,
        "invoice_subtotal": invoice.subtotal if invoice else 0,
        "invoice_iva": invoice.iva if invoice else 0,
        "invoice_total": invoice.total if invoice else 0,
        "summary": r.summary,
        "audited_at": r.audited_at.isoformat() if r.audited_at else None,
        "items": [{
            "id": i.id, "code": i.code, "description": i.description, "category": i.category,
            "quantity": i.quantity, "unit_price": i.unit_price, "total_price": i.total_price,
            "tariff_price": tariff_map.get(i.code, {}).get("max_price"),
            "tariff_tolerance": tariff_map.get(i.code, {}).get("tolerance_pct"),
        } for i in items],
        "findings": [{
            "id": f.id, "finding_type": f.finding_type.value, "severity": f.severity.value,
            "title": f.title, "description": f.description, "item_description": f.item_description,
            "expected_value": f.expected_value, "actual_value": f.actual_value,
            "difference": f.difference, "recommendation": f.recommendation,
        } for f in findings],
    }


# ── Tarifario ──────────────────────────────────────────

def _tariff_dict(t: TariffItem) -> dict:
    try:
        applicable = json.loads(t.applicable_claim_types) if t.applicable_claim_types else []
    except Exception:
        applicable = []
    return {
        "id": t.id, "code": t.code, "description": t.description, "category": t.category,
        "max_price": t.max_price, "tolerance_pct": t.tolerance_pct,
        "expected_qty_min": t.expected_qty_min, "expected_qty_max": t.expected_qty_max,
        "applicable_claim_types": applicable,
    }


@app.get("/api/tariffs")
def get_tariffs(scope: ProfileScope = Depends(get_scope)):
    return [_tariff_dict(t) for t in scope.tariffs().all()]


class TariffCreate(BaseModel):
    code: str
    description: str
    category: str
    max_price: float
    tolerance_pct: float = 10.0
    expected_qty_min: float = 1.0
    expected_qty_max: float = 100.0
    applicable_claim_types: list[str] = []


@app.post("/api/tariffs", status_code=201)
def create_tariff(
    data: TariffCreate,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("tariffs")
    code = (data.code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Codigo requerido")
    if scope.get_tariff_by_code(code):
        raise HTTPException(status_code=409, detail=f"Codigo {code} ya existe en este perfil")
    t = TariffItem(
        profile_id=scope.profile_id,
        code=code,
        description=data.description.strip(),
        category=(data.category or "general").lower().strip(),
        max_price=float(data.max_price),
        tolerance_pct=float(data.tolerance_pct),
        expected_qty_min=float(data.expected_qty_min),
        expected_qty_max=float(data.expected_qty_max),
        applicable_claim_types=json.dumps(data.applicable_claim_types or []),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _tariff_dict(t)


class TariffUpdate(BaseModel):
    max_price: float


@app.put("/api/tariffs/{tariff_id}")
def update_tariff(
    tariff_id: int,
    data: TariffUpdate,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("tariffs")
    tariff = scope.get_tariff(tariff_id)
    if not tariff:
        raise HTTPException(status_code=404, detail="Item no encontrado o no pertenece a este perfil.")
    tariff.max_price = data.max_price
    db.commit()
    db.refresh(tariff)
    return {"status": "success", "max_price": tariff.max_price}


@app.delete("/api/tariffs/{tariff_id}")
def delete_tariff(
    tariff_id: int,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("tariffs")
    t = scope.get_tariff(tariff_id)
    if not t:
        raise HTTPException(status_code=404, detail="Item no encontrado o no pertenece a este perfil.")
    db.delete(t)
    db.commit()
    return {"status": "deleted", "id": tariff_id}


VALID_CATEGORIES = {"repuesto", "pintura", "material", "mano_obra", "servicio"}
VALID_CLAIM_TYPES = {
    "choque_frontal", "choque_lateral", "choque_trasero",
    "robo_accesorios", "daño_granizo", "rayon_pintura",
    "rotura_parabrisas", "vandalismo",
}
TARIFF_CSV_REQUIRED_COLS = {"code", "description", "category", "max_price"}


def parse_tariff_csv_content(text: str, existing_codes: set[str] | None = None) -> dict:
    reader = csv.DictReader(io.StringIO(text))
    headers = {h.strip().lower() for h in (reader.fieldnames or [])}
    missing = TARIFF_CSV_REQUIRED_COLS - headers
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Columnas requeridas faltantes: {', '.join(sorted(missing))}",
        )

    existing_codes = set(existing_codes or set())
    seen_codes = set()
    inserted, skipped, errors = [], [], []

    for i, row in enumerate(reader, start=2):  # row 1 = header
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items()}
        code = row.get("code", "").upper()
        description = row.get("description", "")

        if not code or not description:
            errors.append({"row": i, "reason": "code y description son obligatorios"})
            continue

        category = row.get("category", "general").lower().strip()
        if category not in VALID_CATEGORIES:
            errors.append({"row": i, "code": code, "reason": f"categoria '{category}' no valida. Use: {', '.join(sorted(VALID_CATEGORIES))}"})
            continue

        try:
            max_price = float(row.get("max_price", "0").replace(",", "."))
        except ValueError:
            errors.append({"row": i, "code": code, "reason": "max_price debe ser numerico"})
            continue

        if max_price < 0:
            errors.append({"row": i, "code": code, "reason": "max_price no puede ser negativo"})
            continue

        try:
            tolerance_pct = float(row.get("tolerance_pct", "10").replace(",", "."))
            expected_qty_min = float(row.get("expected_qty_min", "1").replace(",", "."))
            expected_qty_max = float(row.get("expected_qty_max", "2").replace(",", "."))
        except ValueError:
            errors.append({"row": i, "code": code, "reason": "tolerance_pct, expected_qty_min, expected_qty_max deben ser numericos"})
            continue

        raw_claim_types = row.get("applicable_claim_types", "")
        applicable = []
        if raw_claim_types:
            for ct in raw_claim_types.split(";"):
                ct = ct.strip().lower()
                if ct and ct in VALID_CLAIM_TYPES:
                    applicable.append(ct)

        if code in existing_codes or code in seen_codes:
            skipped.append({"row": i, "code": code, "reason": "codigo ya existe en este perfil"})
            continue

        seen_codes.add(code)
        inserted.append({
            "row": i,
            "code": code,
            "description": description,
            "category": category,
            "max_price": max_price,
            "tolerance_pct": tolerance_pct,
            "expected_qty_min": expected_qty_min,
            "expected_qty_max": expected_qty_max,
            "applicable_claim_types": applicable,
        })

    return {"inserted": inserted, "skipped": skipped, "errors": errors}


@app.post("/api/tariffs/import-csv", status_code=200)
async def import_tariffs_csv(
    file: UploadFile = File(...),
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    """Importación masiva de tarifario desde CSV."""
    scope.require_write("tariffs")
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .csv")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")  # utf-8-sig strips BOM from Excel exports
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    existing_codes = {t.code for t in scope.tariffs().all()}
    parsed = parse_tariff_csv_content(text, existing_codes=existing_codes)
    inserted, skipped, errors = parsed["inserted"], parsed["skipped"], parsed["errors"]

    for item in inserted:
        t = TariffItem(
            profile_id=scope.profile_id,
            code=item["code"],
            description=item["description"],
            category=item["category"],
            max_price=item["max_price"],
            tolerance_pct=item["tolerance_pct"],
            expected_qty_min=item["expected_qty_min"],
            expected_qty_max=item["expected_qty_max"],
            applicable_claim_types=json.dumps(item["applicable_claim_types"]),
        )
        db.add(t)

    if inserted:
        db.commit()

    return {
        "status": "ok",
        "inserted": len(inserted),
        "skipped": len(skipped),
        "errors": len(errors),
        "detail": {
            "inserted": inserted,
            "skipped": skipped,
            "errors": errors,
        },
    }


# ── Siniestros ─────────────────────────────────────────

@app.get("/api/claims")
def get_claims(
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    siniestros = scope.siniestros().filter(Siniestro.ramo == Ramo.VEHICULOS).all()
    output = []
    for s in siniestros:
        invoices = scope.invoices().filter(Invoice.siniestro_id == s.id_siniestro).all()
        audit = scope.audit_results().filter(AuditResult.siniestro_id == s.id_siniestro).first()
        owner_name = s.id_asegurado
        if s.asegurado_rel and s.asegurado_rel.nombre:
            owner_name = s.asegurado_rel.nombre
        vehicle_plate = s.vehiculo_rel.placa if s.vehiculo_rel and s.vehiculo_rel.placa else "N/D"
        if s.vehiculo_rel:
            vehicle = " ".join([x for x in [s.vehiculo_rel.marca, s.vehiculo_rel.modelo, str(s.vehiculo_rel.anio or "")] if x]).strip()
        else:
            vehicle = "N/D"
        output.append({
            "id": s.id_siniestro,
            "claim_number": f"SIN-{s.id_siniestro}",
            "claim_type": s.ramo.value,
            "description": s.descripcion or "",
            "vehicle_plate": vehicle_plate,
            "vehicle": vehicle or "N/D",
            "insured_name": owner_name,
            "policy_number": s.id_poliza,
            "incident_date": s.fecha_ocurrencia.isoformat() if s.fecha_ocurrencia else None,
            "invoice_count": len(invoices),
            "audit_status": audit.status.value if audit else "pending",
            "risk_score": audit.risk_score if audit else None,
        })
    return output


@app.get("/api/claims/{claim_id}/executive-summary")
def get_claim_executive_summary(
    claim_id: int,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    siniestro = scope.get_siniestro(claim_id)
    if not siniestro:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado o no pertenece a este perfil.")

    owner_id = siniestro.id_asegurado
    owner_name = siniestro.asegurado_rel.nombre if siniestro.asegurado_rel and siniestro.asegurado_rel.nombre else owner_id
    veh = siniestro.vehiculo_rel

    owner_claims = (
        scope.siniestros()
        .filter(Siniestro.id_asegurado == owner_id, Siniestro.ramo == Ramo.VEHICULOS)
        .order_by(Siniestro.fecha_ocurrencia.desc())
        .all()
    )

    if veh and veh.id:
        vehicle_claims = (
            scope.siniestros()
            .filter(Siniestro.vehiculo_id == veh.id)
            .order_by(Siniestro.fecha_ocurrencia.desc())
            .all()
        )
    else:
        vehicle_claims = (
            scope.siniestros()
            .filter(Siniestro.id_poliza == siniestro.id_poliza, Siniestro.ramo == Ramo.VEHICULOS)
            .order_by(Siniestro.fecha_ocurrencia.desc())
            .all()
        )

    def _row(c):
        a = (
            scope.audit_results()
            .filter(AuditResult.siniestro_id == c.id_siniestro)
            .order_by(AuditResult.audited_at.desc())
            .first()
        )
        return {
            "claim_number": f"SIN-{c.id_siniestro}",
            "coverage": c.cobertura.value if c.cobertura else "",
            "date": c.fecha_ocurrencia.isoformat() if c.fecha_ocurrencia else None,
            "amount": c.monto_reclamado or 0,
            "risk_score": a.risk_score if a else None,
            "audit_status": a.status.value if a else "pending",
        }

    current_audit = (
        scope.audit_results()
        .filter(AuditResult.siniestro_id == siniestro.id_siniestro)
        .order_by(AuditResult.audited_at.desc())
        .first()
    )
    missing_docs = [d.tipo_documento for d in (siniestro.documentos or []) if not d.entregado]
    inconsistent_docs = [d.tipo_documento for d in (siniestro.documentos or []) if d.inconsistencia_detectada]

    return {
        "claim": {
            "claim_number": f"SIN-{siniestro.id_siniestro}",
            "policy_number": siniestro.id_poliza,
            "insured_name": owner_name,
            "insured_id": owner_id,
            "vehicle": {
                "plate": veh.placa if veh else "N/D",
                "brand": veh.marca if veh else "N/D",
                "model": veh.modelo if veh else "N/D",
                "year": veh.anio if veh else None,
            },
            "risk_score": current_audit.risk_score if current_audit else None,
            "audit_status": current_audit.status.value if current_audit else "pending",
            "missing_documents": missing_docs,
            "inconsistent_documents": inconsistent_docs,
        },
        "owner_history": [_row(c) for c in owner_claims],
        "vehicle_history": [_row(c) for c in vehicle_claims],
        "executive_summary": (
            f"Vehiculo {veh.placa if veh and veh.placa else 'N/D'} asociado a {len(vehicle_claims)} siniestro(s). "
            f"Asegurado {owner_name} registra {len(owner_claims)} siniestro(s) en historial. "
            f"Caso actual requiere revision humana priorizada."
        ),
        "note": "Alerta de posible fraude; no constituye acusacion automatica.",
    }


@app.get("/api/claims/{claim_id}/invoices")
def get_claim_invoices(
    claim_id: int,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    siniestro = scope.get_siniestro(claim_id)
    if not siniestro:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado o no pertenece a este perfil.")
    invoices = scope.invoices().filter(Invoice.siniestro_id == claim_id).all()
    output = []
    for inv in invoices:
        items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == inv.id).all()
        workshop = scope.get_workshop(inv.workshop_id) if inv.workshop_id else None
        audit = scope.audit_results().filter(AuditResult.invoice_id == inv.id).first()
        output.append({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
            "workshop_name": workshop.name if workshop else "",
            "workshop_ruc": workshop.ruc if workshop else "",
            "subtotal": inv.subtotal or 0,
            "iva": inv.iva or 0,
            "total": inv.total or 0,
            "audit_id": audit.id if audit else None,
            "audit_status": audit.status.value if audit else "pending",
            "risk_score": audit.risk_score if audit else None,
            "items": [{
                "code": i.code or "",
                "description": i.description,
                "category": i.category or "",
                "quantity": i.quantity,
                "unit_price": i.unit_price,
                "total_price": i.total_price,
            } for i in items],
        })
    return output


# ── Acción manual sobre auditoría ──────────────────────

@app.post("/api/audit-results/{audit_id}/approve")
def approve_audit(
    audit_id: int,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("audit_results")
    r = scope.get_audit_result(audit_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resultado de auditoría no encontrado.")
    r.status = AuditStatus.APPROVED
    r.reviewed_at = datetime.utcnow()
    r.reviewed_by = "auditor_manual"
    db.commit()
    return {"status": "approved", "audit_id": audit_id}


@app.post("/api/audit-results/{audit_id}/reject")
def reject_audit(
    audit_id: int,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("audit_results")
    r = scope.get_audit_result(audit_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resultado de auditoría no encontrado.")
    r.status = AuditStatus.REJECTED
    r.reviewed_at = datetime.utcnow()
    r.reviewed_by = "auditor_manual"
    db.commit()
    return {"status": "rejected", "audit_id": audit_id}


@app.post("/api/audit-results/{audit_id}/escalate")
def escalate_audit(
    audit_id: int,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("audit_results")
    r = scope.get_audit_result(audit_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resultado de auditoría no encontrado.")
    r.status = AuditStatus.ESCALATED
    r.reviewed_at = datetime.utcnow()
    r.reviewed_by = "auditor_manual"
    db.commit()
    return {"status": "escalated", "audit_id": audit_id}


# ── Auditoría IA (Gemini 2.5 Flash) ─────────────────────

def _build_invoice_dict(invoice, items) -> dict:
    return {
        "invoice_number": invoice.invoice_number,
        "ruc": invoice.workshop.ruc if invoice.workshop else "",
        "workshop_name": invoice.workshop.name if invoice.workshop else "",
        "issue_date": invoice.issue_date.strftime("%d/%m/%Y") if invoice.issue_date else "",
        "subtotal": invoice.subtotal, "iva": invoice.iva, "total": invoice.total,
        "items": [
            {"code": i.code or "", "description": i.description, "category": i.category or "",
             "quantity": i.quantity, "unit_price": i.unit_price, "total_price": i.total_price}
            for i in items
        ],
    }


def _build_siniestro_dict(siniestro) -> dict:
    return {
        "claim_number": f"SIN-{siniestro.id_siniestro}",
        "claim_type": siniestro.ramo.value if siniestro.ramo else "",
        "description": siniestro.descripcion or "",
        "vehicle": "", "vehicle_plate": "",
        "insured_name": siniestro.id_asegurado or "",
        "policy_number": siniestro.id_poliza or "",
        "incident_date": siniestro.fecha_ocurrencia.strftime("%d/%m/%Y") if siniestro.fecha_ocurrencia else "",
    }


def _save_ai_result(db, invoice, siniestro, ai_result: dict, profile_id: str = None):
    from backend.models import AuditStatus, AuditFinding, FindingSeverity, FindingType
    status_val = getattr(AuditStatus, ai_result["status"].upper(), AuditStatus.COMPLETED)
    is_test = getattr(invoice, "is_test", 0) or 0
    existing = db.query(AuditResult).filter(
        AuditResult.invoice_id == invoice.id,
    ).first()
    if existing:
        existing.status = status_val
        existing.risk_score = ai_result["risk_score"]
        existing.total_overcharge = ai_result["total_overcharge"]
        existing.summary = ai_result.get("notas_agente", "")
        existing.agent_notes = json.dumps({"ai": True, "model": ai_result.get("model_used", "")}, ensure_ascii=False)
        existing.audit_engine = "gemini"
        existing.is_test = is_test
        existing.audited_at = datetime.utcnow()
        db.query(AuditFinding).filter(AuditFinding.audit_result_id == existing.id).delete()
        audit_result = existing
    else:
        audit_result = AuditResult(
            profile_id=profile_id,
            siniestro_id=siniestro.id_siniestro,
            invoice_id=invoice.id,
            status=status_val,
            risk_score=ai_result["risk_score"],
            total_overcharge=ai_result["total_overcharge"],
            summary=ai_result.get("notas_agente", ""),
            agent_notes=json.dumps({"ai": True, "model": ai_result.get("model_used", "")}, ensure_ascii=False),
            audit_engine="gemini",
            is_test=is_test,
            audited_at=datetime.utcnow(),
        )
        db.add(audit_result)
    db.flush()

    severity_map = {"info": FindingSeverity.INFO, "warning": FindingSeverity.WARNING, "critical": FindingSeverity.CRITICAL}
    type_map = {
        "overcharge": FindingType.OVERCHARGE, "duplicate": FindingType.DUPLICATE,
        "incoherence": FindingType.INCOHERENCE, "quantity_anomaly": FindingType.QUANTITY_ANOMALY,
        "missing_document": FindingType.MISSING_DOCUMENT, "clean": FindingType.CLEAN,
    }
    for h in ai_result.get("hallazgos", []):
        db.add(AuditFinding(
            audit_result_id=audit_result.id,
            finding_type=type_map.get(h["finding_type"], FindingType.CLEAN),
            severity=severity_map.get(h["severity"], FindingSeverity.INFO),
            title=h["title"], description=h["description"],
            item_description=h.get("item_description", ""),
            expected_value=h.get("expected_value", ""), actual_value=h.get("actual_value", ""),
            difference=h.get("difference", 0), recommendation=h.get("recommendation", ""),
        ))
    db.commit()
    db.refresh(audit_result)
    return audit_result


def _get_tariff_list_for_scope(scope: ProfileScope) -> list:
    return [
        {
            "code": t.code, "description": t.description, "category": t.category,
            "max_price": t.max_price, "tolerance_pct": t.tolerance_pct,
            "expected_qty_min": t.expected_qty_min, "expected_qty_max": t.expected_qty_max,
            "applicable_claim_types": json.loads(t.applicable_claim_types) if t.applicable_claim_types else [],
        }
        for t in scope.tariffs().all()
    ]


def _run_gemini_audit(invoice_id: int, scope: ProfileScope, db: Session) -> dict:
    from backend.gemini_auditor import GeminiAuditor

    invoice = scope.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Factura {invoice_id} no encontrada en este perfil.")
    siniestro = scope.get_siniestro(invoice.siniestro_id)
    if not siniestro:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado.")

    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).all()

    # Historial de facturas del mismo perfil para detección cruzada
    all_invoices = scope.invoices().all()
    invoice_history = [
        {
            "id": inv.id, "invoice_number": inv.invoice_number,
            "claim_number": f"SIN-{inv.siniestro.id_siniestro}" if inv.siniestro else "",
            "claim_type": inv.siniestro.ramo.value if inv.siniestro and inv.siniestro.ramo else "",
            "workshop_ruc": inv.workshop.ruc if inv.workshop else "",
            "total": inv.total or 0.0,
        }
        for inv in all_invoices
    ]

    try:
        auditor = GeminiAuditor()
        ai_result = auditor.audit(
            invoice=_build_invoice_dict(invoice, items),
            claim=_build_siniestro_dict(siniestro),
            tariff_items=_get_tariff_list_for_scope(scope),
            invoice_history=invoice_history,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error Gemini: {str(e)}")

    audit_result = _save_ai_result(db, invoice, siniestro, ai_result, profile_id=scope.profile_id)

    return {
        "audit_id": audit_result.id, "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "claim_number": f"SIN-{siniestro.id_siniestro}",
        "claim_type": siniestro.ramo.value if siniestro.ramo else "",
        "workshop_name": invoice.workshop.name if invoice.workshop else "",
        "status": audit_result.status.value,
        "status_label": ai_result["status_label"],
        "documentacion": ai_result["documentacion"],
        "risk_score": ai_result["risk_score"],
        "total_overcharge": ai_result["total_overcharge"],
        "total_facturado": ai_result["total_facturado"],
        "total_auditado": ai_result["total_auditado"],
        "pct_discrepancia": ai_result["pct_discrepancia"],
        "ahorro_estimado": ai_result.get("ahorro_estimado", ai_result["total_overcharge"]),
        "hallazgos": ai_result["hallazgos"],
        "notas_agente": ai_result["notas_agente"],
        "resumen_ejecutivo_taller": ai_result.get("resumen_ejecutivo_taller", ""),
        "model_used": ai_result["model_used"],
        "audited_at": audit_result.audited_at.isoformat(),
    }


@app.post("/api/audit-ai/{invoice_id}")
def audit_invoice_ai(
    invoice_id: int,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("audit_results")
    return _run_gemini_audit(invoice_id, scope, db)


@app.post("/api/audit-ai-all")
def audit_all_ai(
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("audit_results")
    invoices = scope.invoices().all()
    results, errors = [], []
    for inv in invoices:
        try:
            results.append(_run_gemini_audit(inv.id, scope, db))
        except HTTPException as e:
            errors.append({"invoice_id": inv.id, "error": e.detail})
    return {"audited": len(results), "errors": errors, "results": results}


@app.post("/api/audit-gemini/{invoice_id}")
def audit_invoice_gemini(
    invoice_id: int,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("audit_results")
    return _run_gemini_audit(invoice_id, scope, db)


@app.post("/api/audit-gemini-batch")
def audit_gemini_batch(
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("audit_results")
    from backend.gemini_auditor import GeminiAuditor

    invoices_db = scope.invoices().all()
    siniestros_db = scope.siniestros().all()
    tariff_list = _get_tariff_list_for_scope(scope)

    siniestro_map = {s.id_siniestro: s for s in siniestros_db}
    invoices_payload, siniestros_payload = [], []

    for inv in invoices_db:
        items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == inv.id).all()
        inv_dict = _build_invoice_dict(inv, items)
        siniestro = siniestro_map.get(inv.siniestro_id)
        inv_dict["claim_number"] = f"SIN-{siniestro.id_siniestro}" if siniestro else ""
        invoices_payload.append(inv_dict)
        if siniestro:
            siniestros_payload.append(_build_siniestro_dict(siniestro))

    try:
        auditor = GeminiAuditor()
        batch_result = auditor.batch_audit(
            invoices=invoices_payload, claims=siniestros_payload, tariff_items=tariff_list,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error Gemini batch: {str(e)}")

    inv_by_number = {inv.invoice_number: inv for inv in invoices_db}
    saved = []
    for a in batch_result.get("auditorias", []):
        inv = inv_by_number.get(a["invoice_number"])
        if inv:
            siniestro = siniestro_map.get(inv.siniestro_id)
            if siniestro:
                a_for_save = dict(a)
                a_for_save["model_used"] = batch_result.get("model_used", "")
                a_for_save["status_label"] = a.get("status_label", "Observado")
                try:
                    saved.append(_save_ai_result(db, inv, siniestro, a_for_save, profile_id=scope.profile_id).id)
                except Exception:
                    pass

    return {
        "model_used": batch_result.get("model_used", ""),
        "facturas_en_lote": len(invoices_payload),
        "auditorias_guardadas": len(saved),
        "resumen_global": batch_result["resumen_global"],
        "auditorias": batch_result["auditorias"],
    }


# ── Upload PDF ──────────────────────────────────────────

@app.post("/api/audit-pdf")
async def audit_pdf_upload(
    file: UploadFile = File(...),
    claim_number: str = Form(None),
    is_test: int = Form(0),
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    from backend.pdf_extractor import extract_invoice_from_pdf
    scope.require_write("invoices")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF demasiado grande (máx 10MB).")

    try:
        invoice_data = extract_invoice_from_pdf(pdf_bytes)
    except ImportError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"No se pudo parsear el PDF: {str(e)}")

    ruc = (invoice_data.get("ruc") or "").strip() or "0000000000001"
    workshop = scope.get_workshop_by_ruc(ruc)
    if not workshop:
        workshop = Workshop(
            profile_id=scope.profile_id,
            name=invoice_data.get("workshop_name") or "Taller Desconocido",
            ruc=ruc,
        )
        db.add(workshop)
        db.flush()

    pdf_claim_number = (invoice_data.get("claim_number") or "").strip()
    pdf_claim_type = (invoice_data.get("claim_type") or "").strip()
    pdf_policy = (invoice_data.get("policy_number") or "").strip()
    pdf_insured = (invoice_data.get("insured_name") or "").strip()

    ramo_enum = Ramo.VEHICULOS

    siniestro = None
    effective_ref = (claim_number or "").strip() or pdf_claim_number or pdf_policy
    if effective_ref:
        siniestro = scope.siniestros().filter(Siniestro.id_poliza == effective_ref).first()
    if not siniestro:
        placeholder_poliza = effective_ref or f"PDF-{file.filename[:20]}"
        siniestro = scope.siniestros().filter(Siniestro.id_poliza == placeholder_poliza).first()
        if not siniestro:
            siniestro = Siniestro(
                profile_id=scope.profile_id,
                id_poliza=placeholder_poliza,
                id_asegurado=pdf_insured[:50] if pdf_insured else "Desconocido",
                ramo=ramo_enum,
                cobertura=Cobertura.OTRO,
                fecha_ocurrencia=datetime.utcnow(),
                estado=EstadoSiniestro.RESERVA,
                descripcion=f"Siniestro importado desde PDF ({pdf_claim_type or 'tipo no especificado'})",
                sucursal="Por determinar",
            )
            db.add(siniestro)
            db.flush()

    try:
        issue_date = datetime.strptime(invoice_data.get("issue_date", ""), "%d/%m/%Y")
    except Exception:
        issue_date = datetime.utcnow()

    invoice_number = (invoice_data.get("invoice_number") or "").strip() or f"PDF-{file.filename}"

    existing = scope.invoices().filter(
        Invoice.invoice_number == invoice_number,
        Invoice.workshop_id == workshop.id,
    ).first()
    if existing:
        db.rollback()
        return {
            "filename": file.filename, "invoice_id": existing.id,
            "invoice_extracted": invoice_data, "status": "already_exists",
            "is_test": bool(existing.is_test),
            "message": f"La factura {invoice_number} de este taller ya está registrada.",
        }

    invoice = Invoice(
        profile_id=scope.profile_id,
        invoice_number=invoice_number,
        siniestro_id=siniestro.id_siniestro,
        workshop_id=workshop.id,
        issue_date=issue_date,
        subtotal=float(invoice_data.get("subtotal") or 0),
        iva=float(invoice_data.get("iva") or 0),
        total=float(invoice_data.get("total") or 0),
        raw_data=json.dumps(invoice_data),
        is_test=1 if int(is_test) else 0,
    )
    db.add(invoice)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = scope.invoices().filter(
            Invoice.invoice_number == invoice_number, Invoice.workshop_id == workshop.id,
        ).first()
        if existing:
            return {
                "filename": file.filename, "invoice_id": existing.id,
                "invoice_extracted": invoice_data, "status": "already_exists",
                "is_test": bool(existing.is_test),
                "message": f"La factura {invoice_number} ya estaba registrada.",
            }
        raise HTTPException(status_code=409, detail="Conflicto registrando factura.")

    for item in invoice_data.get("items", []):
        db.add(InvoiceItem(
            invoice_id=invoice.id,
            code=str(item.get("code") or ""),
            description=str(item.get("description") or ""),
            category=str(item.get("category") or ""),
            quantity=float(item.get("quantity") or 1),
            unit_price=float(item.get("unit_price") or 0),
            total_price=float(item.get("total_price") or 0),
        ))
    db.commit()

    return {
        "filename": file.filename, "invoice_id": invoice.id,
        "invoice_extracted": invoice_data, "status": "pending",
        "is_test": bool(invoice.is_test),
        "message": "Factura cargada y añadida a la cola de auditoría.",
    }


# ── Generador de Facturas PDF de Prueba ─────────────────

@app.get("/api/test-pdfs")
def list_test_pdfs(scope: ProfileScope = Depends(get_scope)):
    from backend.test_invoice_generator import SCENARIOS, OUTPUT_DIR_DEFAULT
    output = []
    for name, scen in SCENARIOS.items():
        full_path = os.path.join(OUTPUT_DIR_DEFAULT, name)
        exists = os.path.exists(full_path)
        output.append({
            "filename": name, "label": scen["label"], "description": scen["description"],
            "exists": exists,
            "size_kb": round(os.path.getsize(full_path) / 1024, 1) if exists else 0,
        })
    return {"output_dir": OUTPUT_DIR_DEFAULT, "scenarios": output}


@app.post("/api/test-pdfs/generate")
def generate_test_pdfs(scope: ProfileScope = Depends(get_scope)):
    from backend.test_invoice_generator import generate_all_test_invoices
    try:
        results = generate_all_test_invoices()
        return {"status": "success", "count": len(results), "files": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDFs de prueba: {str(e)}")


@app.post("/api/test-pdfs/random")
def generate_random_test_pdf(
    scenario: str = "mixed",
    count: int = 1,
    scope: ProfileScope = Depends(get_scope),
):
    from backend.test_invoice_generator import generate_random_invoice
    valid = {"limpia", "sobrecobro", "fraude", "mixed"}
    if scenario not in valid:
        raise HTTPException(status_code=400, detail=f"scenario inválido. Use: {sorted(valid)}")
    count = max(1, min(int(count or 1), 10))
    try:
        results = [generate_random_invoice(scenario) for _ in range(count)]
        return {"status": "success", "count": len(results), "files": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/test-pdfs/{filename:path}")
def download_test_pdf(filename: str):
    """Descarga PDF de prueba. No requiere token (son archivos estáticos de prueba)."""
    from backend.test_invoice_generator import SCENARIOS, OUTPUT_DIR_DEFAULT, generate_test_invoice
    safe = os.path.basename(filename)
    if not safe.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Archivo inválido")
    full_path = os.path.join(OUTPUT_DIR_DEFAULT, safe)
    if not os.path.exists(full_path):
        if safe in SCENARIOS:
            try:
                generate_test_invoice(safe)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error generando: {str(e)}")
        else:
            raise HTTPException(status_code=404, detail="PDF no encontrado")
    return FileResponse(path=full_path, filename=safe, media_type="application/pdf")


# ── Facturas pendientes ─────────────────────────────────

@app.get("/api/invoices/pending")
def get_pending_invoices(
    include_test: int = 1,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    audited_ids = [a.invoice_id for a in scope.audit_results().with_entities(AuditResult.invoice_id).all()]
    q = scope.invoices().filter(~Invoice.id.in_(audited_ids))
    if not include_test:
        q = q.filter((Invoice.is_test == 0) | (Invoice.is_test.is_(None)))
    return [
        {
            "id": inv.id, "invoice_number": inv.invoice_number,
            "claim_number": f"SIN-{inv.siniestro.id_siniestro}" if inv.siniestro else "N/A",
            "claim_type": inv.siniestro.ramo.value if inv.siniestro and inv.siniestro.ramo else "N/A",
            "workshop_name": inv.workshop.name if inv.workshop else "N/A",
            "total": inv.total, "is_test": bool(inv.is_test),
        }
        for inv in q.all()
    ]


# ── Reporte PDF ─────────────────────────────────────────

def _build_full_audit_dict(scope: ProfileScope, db: Session, audit: AuditResult):
    invoice = scope.get_invoice(audit.invoice_id)
    siniestro = scope.get_siniestro(audit.siniestro_id)
    workshop = scope.get_workshop(invoice.workshop_id) if invoice and invoice.workshop_id else None
    workshop_name = workshop.name if workshop else "Taller Desconocido"

    findings_db = db.query(AuditFinding).filter(AuditFinding.audit_result_id == audit.id).all()
    items_db = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == audit.invoice_id).all() if invoice else []
    tariff_map = scope.tariff_map()

    findings = []
    for f in findings_db:
        ftype = f.finding_type.value if f.finding_type else ""
        findings.append({
            "finding_type": ftype, "severity": f.severity.value if f.severity else "info",
            "title": f.title or "", "description": f.description or "",
            "item_description": f.item_description or "",
            "expected_value": f.expected_value or "", "actual_value": f.actual_value or "",
            "difference": f.difference or 0, "recommendation": f.recommendation or "",
            "regla": ftype.replace("_", " ").title() if ftype else "",
            "detalle": f.description or "", "impacto_economico": f.difference or 0,
        })

    items = []
    for it in items_db:
        tar = tariff_map.get(it.code)
        items.append({
            "code": it.code or "", "description": it.description or "",
            "category": it.category or "", "quantity": it.quantity,
            "unit_price": it.unit_price, "total_price": it.total_price,
            "tariff_price": tar.max_price if tar else None,
            "tariff_tolerance": tar.tolerance_pct if tar else None,
        })

    audit_data = {
        "audit_id": audit.id,
        "invoice_number": invoice.invoice_number if invoice else "N/A",
        "claim_number": f"SIN-{siniestro.id_siniestro}" if siniestro else "-",
        "claim_type": siniestro.ramo.value if siniestro and siniestro.ramo else "-",
        "vehicle": "-", "vehicle_plate": "-",
        "insured_name": siniestro.id_asegurado if siniestro else "-",
        "workshop_name": workshop_name,
        "status": audit.status.value if audit.status else "pending",
        "risk_score": audit.risk_score or 0, "total_overcharge": audit.total_overcharge or 0,
        "invoice_subtotal": invoice.subtotal if invoice else 0,
        "invoice_iva": invoice.iva if invoice else 0,
        "invoice_total": invoice.total if invoice else 0,
        "items": items, "findings": findings, "hallazgos": findings,
        "notas_agente": audit.summary or "",
        "resumen_ejecutivo_taller": (
            f"{audit.summary}\n\nLa presente comunicación es emitida por el Departamento de Auditoría Técnica "
            f"de Siniestros como parte del proceso formal de validación y conciliación de facturación."
            if audit.summary else
            "Tras la revisión completa de la factura presentada, se han identificado los ajustes detallados a "
            "continuación a aplicar en su próxima facturación."
        ),
        "ahorro_estimado": audit.total_overcharge or 0,
    }
    return audit_data, workshop_name


@app.get("/api/audit-results/{audit_id}/report-preview")
def preview_workshop_report(
    audit_id: int,
    type: str = "internal",
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    from backend.pdf_generator import generate_audit_report_pdf, generate_workshop_notification_pdf

    audit = scope.get_audit_result(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada o no pertenece a este perfil.")

    audit_data, workshop_name = _build_full_audit_dict(scope, db, audit)
    try:
        if type == "workshop":
            pdf_path = generate_workshop_notification_pdf(audit_data, workshop_name)
        else:
            pdf_path = generate_audit_report_pdf(audit_data, workshop_name)
        return FileResponse(
            path=pdf_path, media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{os.path.basename(pdf_path)}"',
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


@app.post("/api/audit-results/{audit_id}/notify")
def notify_workshop(
    audit_id: int,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    from backend.pdf_generator import generate_workshop_notification_pdf

    audit = scope.get_audit_result(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada o no pertenece a este perfil.")

    invoice = scope.get_invoice(audit.invoice_id)
    if not invoice:
        raise HTTPException(status_code=400, detail="Falta información de la factura.")

    workshop = scope.get_workshop(invoice.workshop_id) if invoice.workshop_id else None
    workshop_name = workshop.name if workshop else "Taller Desconocido"

    recipients = []
    if workshop and workshop.email:
        recipients.append(workshop.email)

    siniestro = scope.get_siniestro(audit.siniestro_id)
    if siniestro and siniestro.descripcion:
        try:
            meta = json.loads(siniestro.descripcion)
            extra_emails_raw = meta.get("notify_emails", "")
            for e in str(extra_emails_raw).split(","):
                e = e.strip()
                if e and e not in recipients:
                    recipients.append(e)
        except Exception:
            pass

    if not recipients:
        recipients = [
            "auditor.jefe@aseguradora-hackiathon.ec",
            "siniestros@aseguradora-hackiathon.ec",
        ]

    audit_data, _ = _build_full_audit_dict(scope, db, audit)
    try:
        pdf_path = generate_workshop_notification_pdf(audit_data, workshop_name)
        simulated_log = [f"✅ EMAIL SIMULADO → {addr}" for addr in recipients]
        for addr in recipients:
            print(f"✅ EMAIL ENVIADO SIMULADO: Para: {addr} | Adjunto: {os.path.basename(pdf_path)}")
        return {
            "status": "success",
            "message": f"Notificación enviada a {len(recipients)} destinatario(s)",
            "recipients": recipients, "pdf_path": pdf_path, "log": simulated_log,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


@app.put("/api/claims/{claim_id}/notify-config")
def update_claim_notify_config(
    claim_id: int,
    data: dict,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("siniestros")
    siniestro = scope.get_siniestro(claim_id)
    if not siniestro:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado o no pertenece a este perfil.")
    notify_emails = data.get("notify_emails", "")
    try:
        meta = json.loads(siniestro.descripcion or "{}")
    except Exception:
        meta = {"original_description": siniestro.descripcion or ""}
    meta["notify_emails"] = notify_emails
    siniestro.descripcion = json.dumps(meta, ensure_ascii=False)
    db.commit()
    return {"status": "ok", "claim_id": claim_id, "notify_emails": notify_emails}


@app.get("/api/claims/{claim_id}/notify-config")
def get_claim_notify_config(
    claim_id: int,
    scope: ProfileScope = Depends(get_scope),
):
    siniestro = scope.get_siniestro(claim_id)
    if not siniestro:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado o no pertenece a este perfil.")
    try:
        meta = json.loads(siniestro.descripcion or "{}")
        notify_emails = meta.get("notify_emails", "")
    except Exception:
        notify_emails = ""
    workshop_email = ""
    for inv in (siniestro.invoices or []):
        if inv.profile_id == scope.profile_id and inv.workshop and inv.workshop.email:
            workshop_email = inv.workshop.email
            break
    return {"claim_id": claim_id, "workshop_email": workshop_email, "notify_emails": notify_emails}


# ── Scoring de fraude y chatbot ─────────────────────────

@app.post("/api/agent/query")
def query_agent(
    data: dict,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    question = data.get("question", "")
    if not question:
        raise HTTPException(status_code=400, detail="Falta la pregunta")
    from backend.chatbot_agent import process_chatbot_query
    answer = process_chatbot_query(question, db, profile_id=scope.profile_id)
    return {"answer": answer}


@app.get("/api/siniestros/{claim_id}/fraud-score")
def get_claim_fraud_score(
    claim_id: int,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    siniestro = scope.get_siniestro(claim_id)
    if not siniestro:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado o no pertenece a este perfil.")
    from backend.fraud_scoring import evaluate_fraud_scoring
    return evaluate_fraud_scoring(siniestro, db)


@app.post("/api/siniestros/score-all")
def score_all_claims(
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    scope.require_write("siniestros")
    siniestros = scope.siniestros().filter(Siniestro.ramo == Ramo.VEHICULOS).all()
    from backend.fraud_scoring import update_siniestro_fraud_data
    cnt = 0
    for s in siniestros:
        update_siniestro_fraud_data(s, db)
        cnt += 1
    db.commit()
    return {"status": "success", "scored_count": cnt}


@app.get("/api/siniestros/ranking")
def get_claims_ranking(scope: ProfileScope = Depends(get_scope)):
    claims = (
        scope.siniestros()
        .filter(Siniestro.ramo == Ramo.VEHICULOS)
        .order_by(Siniestro.fraud_score.desc())
        .all()
    )
    return [
        {
            "id_siniestro": c.id_siniestro, "id_poliza": c.id_poliza,
            "id_asegurado": c.id_asegurado, "ramo": c.ramo.value,
            "cobertura": c.cobertura.value,
            "fecha_ocurrencia": c.fecha_ocurrencia.isoformat() if c.fecha_ocurrencia else None,
            "monto_reclamado": c.monto_reclamado,
            "fraud_score": c.fraud_score, "fraud_classification": c.fraud_classification,
            "description": c.descripcion, "documentos_completos": bool(c.documentos_completos),
        }
        for c in claims
    ]


@app.get("/api/fraud-dashboard")
def get_fraud_dashboard(scope: ProfileScope = Depends(get_scope)):
    claims = scope.siniestros().filter(Siniestro.ramo == Ramo.VEHICULOS).all()
    total_claims = len(claims)
    if total_claims == 0:
        return {
            "total_claims": 0,
            "by_classification": {"rojo": 0, "amarillo": 0, "verde": 0},
            "total_reclaimed": 0.0, "reclaimed_under_risk": 0.0, "pct_under_risk": 0.0,
            "by_ramo": [],
        }

    rojo_count = sum(1 for c in claims if c.fraud_classification == "Rojo")
    amarillo_count = sum(1 for c in claims if c.fraud_classification == "Amarillo")
    verde_count = sum(1 for c in claims if c.fraud_classification == "Verde")
    total_reclamado = sum(c.monto_reclamado or 0 for c in claims)
    reclamado_rojo = sum(c.monto_reclamado or 0 for c in claims if c.fraud_classification == "Rojo")
    reclamado_amarillo = sum(c.monto_reclamado or 0 for c in claims if c.fraud_classification == "Amarillo")

    from collections import defaultdict
    ramo_totals, ramo_rojo = defaultdict(int), defaultdict(int)
    for c in claims:
        r = c.ramo.value
        ramo_totals[r] += 1
        if c.fraud_classification == "Rojo":
            ramo_rojo[r] += 1

    ramos_data = [
        {"ramo": r, "total": total, "rojos": ramo_rojo[r],
         "pct_rojo": round((ramo_rojo[r] / total * 100) if total > 0 else 0, 1)}
        for r, total in ramo_totals.items()
    ]
    ramos_data.sort(key=lambda x: x["pct_rojo"], reverse=True)

    return {
        "total_claims": total_claims,
        "by_classification": {"rojo": rojo_count, "amarillo": amarillo_count, "verde": verde_count},
        "total_reclaimed": round(total_reclamado, 2),
        "reclaimed_under_risk": round(reclamado_rojo + reclamado_amarillo, 2),
        "pct_under_risk": round(((rojo_count + amarillo_count) / total_claims * 100) if total_claims > 0 else 0, 1),
        "by_ramo": ramos_data,
    }


# ── Intelligence Platform Endpoints ────────────────────

@app.get("/api/intelligence/portfolio")
def get_portfolio_intelligence(
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    from collections import defaultdict
    from datetime import timedelta

    siniestros = scope.siniestros().all()
    polizas = scope.polizas().all()
    audit_results = scope.audit_results().all()

    total_claimed = sum(s.monto_reclamado or 0 for s in siniestros)
    total_paid = sum(s.monto_pagado or 0 for s in siniestros)
    total_estimated = sum(s.monto_estimado or 0 for s in siniestros)
    open_claims = sum(1 for s in siniestros if s.estado and s.estado.value in ["Reserva", "Anticipo", "Pago Parcial"])

    fraud_scores = [s.fraud_score for s in siniestros if s.fraud_score]
    avg_fraud_score = sum(fraud_scores) / len(fraud_scores) if fraud_scores else 0
    high_risk = sum(1 for s in siniestros if (s.fraud_score or 0) >= 75)

    by_branch = {}
    for s in siniestros:
        branch = s.sucursal or "Sin sucursal"
        if branch not in by_branch:
            by_branch[branch] = {"claims": 0, "paid": 0, "fraud_alerts": 0, "avg_score": 0.0, "_scores": []}
        by_branch[branch]["claims"] += 1
        by_branch[branch]["paid"] += s.monto_pagado or 0
        if (s.fraud_score or 0) >= 75:
            by_branch[branch]["fraud_alerts"] += 1
        if s.fraud_score:
            by_branch[branch]["_scores"].append(s.fraud_score)

    branch_ranking = []
    for branch, d in by_branch.items():
        scores = d.pop("_scores")
        d["avg_score"] = round(sum(scores) / len(scores) if scores else 0, 1)
        branch_ranking.append({"branch": branch, **d})
    branch_ranking.sort(key=lambda x: x["claims"], reverse=True)

    today = datetime.utcnow()
    monthly = defaultdict(lambda: {"claims": 0, "paid": 0})
    for s in siniestros:
        d = s.fecha_reporte or s.fecha_ocurrencia
        if d:
            monthly[d.strftime("%Y-%m")]["claims"] += 1
            monthly[d.strftime("%Y-%m")]["paid"] += s.monto_pagado or 0

    months = []
    for i in range(5, -1, -1):
        d = today - timedelta(days=i * 30)
        key = d.strftime("%Y-%m")
        months.append({"month": key, **monthly.get(key, {"claims": 0, "paid": 0})})

    active_policies = sum(1 for p in polizas if (p.estado_poliza or "").lower() == "activa")
    total_overcharge = sum(a.total_overcharge or 0 for a in audit_results)
    escalated = sum(1 for a in audit_results if a.status == AuditStatus.ESCALATED)
    avg_claim_cost = total_paid / len(siniestros) if siniestros else 0

    claims_by_state = {}
    for s in siniestros:
        k = s.estado.value if s.estado else "Desconocido"
        claims_by_state[k] = claims_by_state.get(k, 0) + 1

    return {
        "total_claims": len(siniestros),
        "open_claims": open_claims,
        "total_claimed": round(total_claimed, 2),
        "total_paid": round(total_paid, 2),
        "total_reserved": round(total_estimated, 2),
        "total_overcharge": round(total_overcharge, 2),
        "avg_fraud_score": round(avg_fraud_score, 1),
        "fraud_alerts": high_risk,
        "active_policies": active_policies,
        "avg_claim_cost": round(avg_claim_cost, 2),
        "claims_by_state": claims_by_state,
        "branch_ranking": branch_ranking[:10],
        "monthly_trend": months,
        "escalated": escalated,
    }


@app.get("/api/intelligence/fraud")
def get_fraud_intelligence(
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    import json as _json

    siniestros = scope.siniestros().all()

    high_risk_claims = []
    for s in sorted(siniestros, key=lambda x: x.fraud_score or 0, reverse=True)[:25]:
        if (s.fraud_score or 0) >= 40:
            audit = scope.audit_results().filter(AuditResult.siniestro_id == s.id_siniestro).first()
            try:
                indicators = _json.loads(s.fraud_indicators or "[]")
            except Exception:
                indicators = []
            try:
                rules_failed = _json.loads(s.fraud_rules_failed or "[]")
            except Exception:
                rules_failed = []
            high_risk_claims.append({
                "claim_id": s.id_siniestro,
                "claim_number": f"SIN-{s.id_siniestro}",
                "fraud_score": s.fraud_score or 0,
                "fraud_classification": s.fraud_classification or "Verde",
                "amount_claimed": s.monto_reclamado or 0,
                "amount_paid": s.monto_pagado or 0,
                "beneficiary": s.beneficiario or "",
                "sucursal": s.sucursal or "",
                "docs_complete": bool(s.documentos_completos),
                "audit_id": audit.id if audit else None,
                "audit_status": audit.status.value if audit else "pending",
                "indicators": indicators[:4],
                "rules_failed": rules_failed[:3],
                "days_delay": s.dias_entre_ocurrencia_reporte or 0,
            })

    dist = {"verde": 0, "amarillo": 0, "rojo": 0}
    for s in siniestros:
        score = s.fraud_score or 0
        if score >= 75:
            dist["rojo"] += 1
        elif score >= 40:
            dist["amarillo"] += 1
        else:
            dist["verde"] += 1

    indicator_freq = {}
    for s in siniestros:
        try:
            for ind in _json.loads(s.fraud_indicators or "[]"):
                indicator_freq[ind] = indicator_freq.get(ind, 0) + 1
        except Exception:
            pass

    top_indicators = sorted(
        [{"indicator": k, "count": v} for k, v in indicator_freq.items()],
        key=lambda x: x["count"], reverse=True
    )[:12]

    beneficiary_claims = {}
    for s in siniestros:
        if s.beneficiario:
            beneficiary_claims.setdefault(s.beneficiario, []).append(s.id_siniestro)
    shared_beneficiaries = [
        {"beneficiary": k, "claim_count": len(v), "claim_ids": v[:5]}
        for k, v in beneficiary_claims.items() if len(v) > 1
    ][:10]

    customer_claims = {}
    for s in siniestros:
        if s.id_asegurado:
            customer_claims.setdefault(s.id_asegurado, []).append({
                "claim_id": s.id_siniestro, "score": s.fraud_score or 0
            })
    frequent_claimants = [
        {"customer_id": k, "claim_count": len(v), "max_score": max(c["score"] for c in v)}
        for k, v in customer_claims.items() if len(v) > 1
    ]
    frequent_claimants.sort(key=lambda x: x["max_score"], reverse=True)

    return {
        "high_risk_claims": high_risk_claims,
        "score_distribution": dist,
        "top_indicators": top_indicators,
        "shared_beneficiaries": shared_beneficiaries,
        "frequent_claimants": frequent_claimants[:10],
        "total_high_risk": dist["rojo"],
        "total_medium_risk": dist["amarillo"],
        "total_low_risk": dist["verde"],
    }


@app.get("/api/intelligence/operations")
def get_operations_intelligence(
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    siniestros = scope.siniestros().all()
    audit_results = scope.audit_results().all()
    invoices = scope.invoices().filter((Invoice.is_test == 0) | (Invoice.is_test.is_(None))).all()

    by_state = {}
    for s in siniestros:
        k = s.estado.value if s.estado else "Desconocido"
        by_state[k] = by_state.get(k, 0) + 1

    sla_ok = sla_risk = sla_breach = 0
    for s in siniestros:
        days = s.dias_entre_ocurrencia_reporte or 0
        if days > 30:
            sla_breach += 1
        elif days > 15:
            sla_risk += 1
        else:
            sla_ok += 1

    docs_missing = sum(1 for s in siniestros if not s.documentos_completos)
    docs_ok = len(siniestros) - docs_missing

    pending_count = sum(1 for a in audit_results if a.status.value == "pending")
    in_progress_count = sum(1 for a in audit_results if a.status.value == "in_progress")
    escalated_count = sum(1 for a in audit_results if a.status == AuditStatus.ESCALATED)
    completed_count = sum(1 for a in audit_results if a.status.value in ["approved", "rejected", "completed"])

    audited_ids = {a.siniestro_id for a in audit_results}
    claims_queue = []
    for s in sorted(siniestros, key=lambda x: (x.dias_entre_ocurrencia_reporte or 0), reverse=True)[:20]:
        audit = scope.audit_results().filter(AuditResult.siniestro_id == s.id_siniestro).first()
        claims_queue.append({
            "claim_id": s.id_siniestro,
            "claim_number": f"SIN-{s.id_siniestro}",
            "ramo": s.ramo.value if s.ramo else "",
            "estado": s.estado.value if s.estado else "",
            "amount_claimed": s.monto_reclamado or 0,
            "dias_reporte": s.dias_entre_ocurrencia_reporte or 0,
            "docs_complete": bool(s.documentos_completos),
            "audit_status": audit.status.value if audit else "sin_auditoria",
            "fraud_score": s.fraud_score or 0,
            "sucursal": s.sucursal or "",
        })

    return {
        "by_state": by_state,
        "sla": {"ok": sla_ok, "at_risk": sla_risk, "breach": sla_breach},
        "documentation": {"complete": docs_ok, "missing": docs_missing},
        "audit_queue": {
            "pending": pending_count,
            "in_progress": in_progress_count,
            "escalated": escalated_count,
            "completed": completed_count,
        },
        "claims_queue": claims_queue,
        "total_invoices": len(invoices),
    }


@app.get("/api/intelligence/audit-coverage")
def get_audit_coverage(
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    siniestros = scope.siniestros().all()
    audit_results = scope.audit_results().all()

    total_claims = len(siniestros)
    audited_claims = len(audit_results)
    coverage_pct = round((audited_claims / total_claims * 100) if total_claims > 0 else 0, 1)

    by_status = {}
    for a in audit_results:
        by_status[a.status.value] = by_status.get(a.status.value, 0) + 1

    by_engine = {}
    for a in audit_results:
        e = a.audit_engine or "rules"
        by_engine[e] = by_engine.get(e, 0) + 1

    reviewed = sum(1 for a in audit_results if a.reviewed_at is not None)
    overrides = sum(1 for a in audit_results if a.reviewed_by and a.status.value in ["approved", "rejected"])

    critical_findings = db.query(AuditFinding).join(AuditResult).filter(
        AuditFinding.severity == FindingSeverity.CRITICAL,
    ).count()
    warning_findings = db.query(AuditFinding).join(AuditResult).filter(
        AuditFinding.severity == FindingSeverity.WARNING,
    ).count()

    violation_rate = (critical_findings + warning_findings * 0.5) / max(audited_claims, 1)
    compliance_score = round(max(0, 100 - violation_rate * 10), 1)

    recent_trail = []
    for a in sorted(audit_results, key=lambda x: x.audited_at or datetime.min, reverse=True)[:25]:
        recent_trail.append({
            "audit_id": a.id,
            "claim_id": a.siniestro_id,
            "status": a.status.value,
            "engine": a.audit_engine or "rules",
            "risk_score": a.risk_score or 0,
            "reviewed_by": a.reviewed_by or "",
            "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
            "audited_at": a.audited_at.isoformat() if a.audited_at else None,
        })

    return {
        "total_claims": total_claims,
        "audited_claims": audited_claims,
        "coverage_pct": coverage_pct,
        "compliance_score": compliance_score,
        "by_status": by_status,
        "by_engine": by_engine,
        "reviewed": reviewed,
        "not_reviewed": audited_claims - reviewed,
        "overrides": overrides,
        "critical_findings": critical_findings,
        "warning_findings": warning_findings,
        "recent_audit_trail": recent_trail,
    }


@app.get("/api/intelligence/claim/{claim_id}")
def get_claim_workspace(
    claim_id: int,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    import json as _json

    siniestro = scope.get_siniestro(claim_id)
    if not siniestro:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado.")

    poliza = siniestro.poliza_rel
    asegurado = siniestro.asegurado_rel
    vehiculo = siniestro.vehiculo_rel

    all_claims_customer = scope.siniestros().filter(
        Siniestro.id_asegurado == siniestro.id_asegurado
    ).order_by(Siniestro.fecha_ocurrencia.desc()).all() if siniestro.id_asegurado else []

    audit = scope.audit_results().filter(
        AuditResult.siniestro_id == claim_id
    ).order_by(AuditResult.audited_at.desc()).first()

    findings = []
    if audit:
        findings = [
            {
                "id": f.id, "type": f.finding_type.value, "severity": f.severity.value,
                "title": f.title, "description": f.description,
                "expected": f.expected_value, "actual": f.actual_value,
                "difference": f.difference, "recommendation": f.recommendation,
            }
            for f in audit.findings
        ]

    invoices = scope.invoices().filter(Invoice.siniestro_id == claim_id).all()
    invoice_summary = []
    for inv in invoices:
        w = scope.get_workshop(inv.workshop_id) if inv.workshop_id else None
        ar = scope.audit_results().filter(AuditResult.invoice_id == inv.id).first()
        invoice_summary.append({
            "id": inv.id, "invoice_number": inv.invoice_number,
            "total": inv.total or 0,
            "workshop": w.name if w else "",
            "audit_status": ar.status.value if ar else "pending",
            "risk_score": ar.risk_score if ar else None,
        })

    docs = [
        {
            "type": d.tipo_documento, "delivered": bool(d.entregado),
            "legible": bool(d.legible), "inconsistency": bool(d.inconsistencia_detectada),
            "observation": d.observacion or "",
        }
        for d in (siniestro.documentos or [])
    ]

    try:
        indicators = _json.loads(siniestro.fraud_indicators or "[]")
    except Exception:
        indicators = []
    try:
        rules_failed = _json.loads(siniestro.fraud_rules_failed or "[]")
    except Exception:
        rules_failed = []

    timeline = [
        {"event": "Ocurrencia", "date": siniestro.fecha_ocurrencia.isoformat() if siniestro.fecha_ocurrencia else None},
        {"event": "Reporte", "date": siniestro.fecha_reporte.isoformat() if siniestro.fecha_reporte else None},
    ]
    if audit and audit.audited_at:
        timeline.append({"event": "Auditoría", "date": audit.audited_at.isoformat()})
    if audit and audit.reviewed_at:
        timeline.append({"event": "Revisión manual", "date": audit.reviewed_at.isoformat()})

    audit_trail = []
    for a in scope.audit_results().filter(AuditResult.siniestro_id == claim_id).order_by(AuditResult.audited_at.desc()).all():
        audit_trail.append({
            "audit_id": a.id, "engine": a.audit_engine or "rules",
            "status": a.status.value, "risk_score": a.risk_score or 0,
            "total_overcharge": a.total_overcharge or 0,
            "audited_at": a.audited_at.isoformat() if a.audited_at else None,
            "reviewed_by": a.reviewed_by or "",
            "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
        })

    return {
        "claim": {
            "id": siniestro.id_siniestro,
            "claim_number": f"SIN-{siniestro.id_siniestro}",
            "ramo": siniestro.ramo.value if siniestro.ramo else "",
            "cobertura": siniestro.cobertura.value if siniestro.cobertura else "",
            "estado": siniestro.estado.value if siniestro.estado else "",
            "sucursal": siniestro.sucursal or "",
            "amount_claimed": siniestro.monto_reclamado or 0,
            "amount_estimated": siniestro.monto_estimado or 0,
            "amount_paid": siniestro.monto_pagado or 0,
            "fraud_score": siniestro.fraud_score or 0,
            "fraud_classification": siniestro.fraud_classification or "Verde",
            "fraud_indicators": indicators,
            "rules_failed": rules_failed,
            "docs_complete": bool(siniestro.documentos_completos),
            "days_delay": siniestro.dias_entre_ocurrencia_reporte or 0,
            "beneficiary": siniestro.beneficiario or "",
        },
        "policy": {
            "id": poliza.id_poliza if poliza else "",
            "ramo": poliza.ramo.value if poliza and poliza.ramo else "",
            "prima": poliza.prima if poliza else 0,
            "suma_asegurada": poliza.suma_asegurada if poliza else 0,
            "deducible": poliza.deducible if poliza else 0,
            "estado": poliza.estado_poliza if poliza else "",
            "canal": poliza.canal_venta if poliza else "",
        } if poliza else {},
        "customer": {
            "id": asegurado.id_asegurado if asegurado else "",
            "name": asegurado.nombre if asegurado else "",
            "segment": asegurado.segmento if asegurado else "",
            "city": asegurado.ciudad if asegurado else "",
            "claims_12m": asegurado.reclamos_12m if asegurado else 0,
            "score": asegurado.score_cliente_simulado if asegurado else 0,
            "total_claims": len(all_claims_customer),
        } if asegurado else {},
        "vehicle": {
            "plate": vehiculo.placa if vehiculo else "",
            "brand": vehiculo.marca if vehiculo else "",
            "model": vehiculo.modelo if vehiculo else "",
            "year": vehiculo.anio if vehiculo else None,
            "chasis": vehiculo.chasis if vehiculo else "",
        } if vehiculo else {},
        "audit": {
            "id": audit.id if audit else None,
            "status": audit.status.value if audit else "sin_auditoria",
            "engine": audit.audit_engine if audit else "",
            "risk_score": audit.risk_score if audit else 0,
            "total_overcharge": audit.total_overcharge if audit else 0,
            "summary": audit.summary if audit else "",
        } if audit else {},
        "findings": findings,
        "invoices": invoice_summary,
        "documents": docs,
        "timeline": [t for t in timeline if t["date"]],
        "audit_trail": audit_trail,
        "customer_history": [
            {
                "claim_id": c.id_siniestro,
                "claim_number": f"SIN-{c.id_siniestro}",
                "date": c.fecha_ocurrencia.isoformat() if c.fecha_ocurrencia else None,
                "amount": c.monto_reclamado or 0,
                "estado": c.estado.value if c.estado else "",
                "fraud_score": c.fraud_score or 0,
            }
            for c in all_claims_customer[:10]
        ],
    }


@app.post("/api/intelligence/gemini-insight")
async def gemini_insight(
    data: dict,
    scope: ProfileScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    """Generate a Gemini insight for a specific context. Always explicit, never automatic."""
    insight_type = data.get("type", "")
    context = data.get("context", {})
    role = data.get("role", "analista")

    role_objectives = {
        "demo_jurado": "Showcase the platform value and demonstrate key insurance fraud detection capabilities.",
        "analista": "Improve claims processing efficiency and identify documentation bottlenecks.",
        "antifraude": "Explain suspicious fraud patterns and recommend investigative actions.",
        "jefatura": "Summarize business performance and identify strategic risks.",
        "auditoria": "Explain compliance findings and decision traceability.",
    }

    type_instructions = {
        "explain_risk": "Explain the fraud risk indicators for this claim. Cite specific values from the data.",
        "explain_fraud_score": "Break down the fraud score components and explain what drives the risk level.",
        "summarize_claim": "Provide a concise claim summary with key facts and risk assessment.",
        "portfolio_summary": "Summarize portfolio performance, highlight anomalies and strategic risks.",
        "branch_analysis": "Analyze branch performance, compare to portfolio average, identify concerns.",
        "executive_briefing": "Generate a structured executive briefing with key findings and recommended actions.",
        "explain_anomaly": "Explain detected anomalies and their operational significance.",
    }

    system_prompt = f"""You are an insurance analytics copilot for a Latin American insurer.
Role: {role}
Objective: {role_objectives.get(role, role_objectives['analista'])}

Rules:
- Use ONLY the supplied data. Never invent metrics.
- Never speculate beyond what the data shows.
- Cite specific numbers and values from the context.
- Keep responses concise and actionable (max 250 words unless explicitly requested).
- Structure: Key Findings → Supporting Evidence → Recommended Actions.
- If evidence is insufficient, state it clearly.
- Respond in Spanish."""

    user_prompt = f"""Task: {type_instructions.get(insight_type, 'Analyze the provided context.')}

Context data:
{__import__('json').dumps(context, ensure_ascii=False, indent=2)}

Provide your analysis."""

    try:
        import google.generativeai as genai
        import os
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_prompt,
        )
        response = model.generate_content(user_prompt)
        return {"status": "success", "insight": response.text, "type": insight_type}
    except Exception as e:
        return {"status": "error", "insight": f"Servicio de IA no disponible: {str(e)}", "type": insight_type}
