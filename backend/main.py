"""
API FastAPI — Auditor Agéntico de Facturación de Siniestros.
"""
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import sys
import os
# Inyectar la raíz del proyecto para que Vercel encuentre la carpeta "backend"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import os
from dotenv import load_dotenv
load_dotenv()  # carga .env automáticamente al arrancar
from backend.database import get_db, init_db
from backend.seed_data import seed_database
from backend.agent import AuditAgent
from backend.models import (
    Siniestro, Invoice, InvoiceItem, TariffItem,
    AuditResult, AuditFinding, Workshop, AuditStatus,
    FindingSeverity, FindingType, Ramo, Cobertura, EstadoSiniestro
)

app = FastAPI(title="Auditor Agentico de Siniestros", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir frontend y logo (con no-cache para desarrollo)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class NoCacheDevMiddleware(BaseHTTPMiddleware):
    """En desarrollo, fuerza no-cache en archivos JS/CSS del frontend."""
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


# ── Dashboard ──────────────────────────────────────────

@app.get("/api/dashboard")
def get_dashboard(include_test: int = 0, db: Session = Depends(get_db)):
    inv_q = db.query(Invoice)
    ar_q = db.query(AuditResult)
    if not include_test:
        inv_q = inv_q.filter((Invoice.is_test == 0) | (Invoice.is_test.is_(None)))
        ar_q = ar_q.filter((AuditResult.is_test == 0) | (AuditResult.is_test.is_(None)))
    total_invoices = inv_q.count()
    total_audited = ar_q.count()
    total_claims = db.query(Siniestro).count()
    results = ar_q.all()
    total_overcharge = sum(r.total_overcharge or 0 for r in results)
    critical_count = 0
    warning_count = 0
    clean_count = 0
    escalated_count = 0
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
    test_count = db.query(Invoice).filter(Invoice.is_test == 1).count()
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
def get_claims_by_day(days: int = 30, db: Session = Depends(get_db)):
    """Conteo diario de siniestros (basado en fecha_ocurrencia) para diagrama de puntos."""
    from datetime import timedelta
    from collections import Counter
    siniestros = db.query(Siniestro).all()
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
def audit_invoice(invoice_id: int, db: Session = Depends(get_db)):
    agent = AuditAgent(db)
    result = agent.audit_invoice(invoice_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/api/audit-rules/{invoice_id}")
def audit_invoice_rules(invoice_id: int, db: Session = Depends(get_db)):
    """Auditoría rápida 100% determinística (rules_engine). Sin Gemini. ~1-2s."""
    agent = AuditAgent(db)
    result = agent.audit_invoice(invoice_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    result["audit_engine"] = "rules"
    return result


@app.post("/api/audit-all")
def audit_all(db: Session = Depends(get_db)):
    agent = AuditAgent(db)
    # Re-audit all invoices
    invoices = db.query(Invoice).all()
    results = []
    for inv in invoices:
        results.append(agent.audit_invoice(inv.id))
    return {"audited": len(results), "results": results}


@app.get("/api/audit-results")
def get_audit_results(include_test: int = 1, db: Session = Depends(get_db)):
    q = db.query(AuditResult)
    if not include_test:
        q = q.filter((AuditResult.is_test == 0) | (AuditResult.is_test.is_(None)))
    results = q.all()
    output = []
    for r in results:
        invoice = db.query(Invoice).filter(Invoice.id == r.invoice_id).first()
        siniestro = db.query(Siniestro).filter(Siniestro.id_siniestro == r.siniestro_id).first()
        workshop = db.query(Workshop).filter(Workshop.id == invoice.workshop_id).first() if invoice else None
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
def get_audit_result(audit_id: int, db: Session = Depends(get_db)):
    r = db.query(AuditResult).filter(AuditResult.id == audit_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")
    invoice = db.query(Invoice).filter(Invoice.id == r.invoice_id).first()
    siniestro = db.query(Siniestro).filter(Siniestro.id_siniestro == r.siniestro_id).first()
    workshop = db.query(Workshop).filter(Workshop.id == invoice.workshop_id).first() if invoice else None
    findings = db.query(AuditFinding).filter(AuditFinding.audit_result_id == r.id).all()
    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == r.invoice_id).all()
    tariffs = db.query(TariffItem).all()
    tariff_map = {t.code: {"code": t.code, "description": t.description, "max_price": t.max_price, "tolerance_pct": t.tolerance_pct} for t in tariffs}
    return {
        "audit_id": r.id, "invoice_id": r.invoice_id,
        "invoice_number": invoice.invoice_number if invoice else "",
        "claim_number": f"SIN-{siniestro.id_siniestro}" if siniestro else "",
        "claim_type": siniestro.ramo.value if siniestro else "",
        "claim_description": siniestro.descripcion if siniestro else "",
        "vehicle": "",
        "vehicle_plate": "",
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
def get_tariffs(db: Session = Depends(get_db)):
    return [_tariff_dict(t) for t in db.query(TariffItem).all()]


from pydantic import BaseModel as _PModel  # local alias to avoid clash with later import


class TariffCreate(_PModel):
    code: str
    description: str
    category: str
    max_price: float
    tolerance_pct: float = 10.0
    expected_qty_min: float = 1.0
    expected_qty_max: float = 100.0
    applicable_claim_types: list[str] = []


@app.post("/api/tariffs", status_code=201)
def create_tariff(data: TariffCreate, db: Session = Depends(get_db)):
    code = (data.code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Codigo requerido")
    if db.query(TariffItem).filter(TariffItem.code == code).first():
        raise HTTPException(status_code=409, detail=f"Codigo {code} ya existe")
    t = TariffItem(
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


@app.delete("/api/tariffs/{tariff_id}")
def delete_tariff(tariff_id: int, db: Session = Depends(get_db)):
    t = db.query(TariffItem).filter(TariffItem.id == tariff_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    db.delete(t)
    db.commit()
    return {"status": "deleted", "id": tariff_id}


# ── Siniestros ─────────────────────────────────────────

@app.get("/api/claims")
def get_claims(db: Session = Depends(get_db)):
    siniestros = db.query(Siniestro).all()
    output = []
    for s in siniestros:
        invoices = db.query(Invoice).filter(Invoice.siniestro_id == s.id_siniestro).all()
        audit = db.query(AuditResult).filter(AuditResult.siniestro_id == s.id_siniestro).first()
        output.append({
            "id": s.id_siniestro,
            "claim_number": f"SIN-{s.id_siniestro}",
            "claim_type": s.ramo.value,
            "description": s.descripcion or "",
            "vehicle_plate": "",
            "vehicle": "",
            "insured_name": s.id_asegurado,
            "policy_number": s.id_poliza,
            "incident_date": s.fecha_ocurrencia.isoformat() if s.fecha_ocurrencia else None,
            "invoice_count": len(invoices),
            "audit_status": audit.status.value if audit else "pending",
            "risk_score": audit.risk_score if audit else None,
        })
    return output


@app.get("/api/claims/{claim_id}/invoices")
def get_claim_invoices(claim_id: int, db: Session = Depends(get_db)):
    """Lista de facturas preliminares asociadas al siniestro, con items y estado de auditoría."""
    siniestro = db.query(Siniestro).filter(Siniestro.id_siniestro == claim_id).first()
    if not siniestro:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado")
    invoices = db.query(Invoice).filter(Invoice.siniestro_id == claim_id).all()
    output = []
    for inv in invoices:
        items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == inv.id).all()
        workshop = db.query(Workshop).filter(Workshop.id == inv.workshop_id).first() if inv.workshop_id else None
        audit = db.query(AuditResult).filter(AuditResult.invoice_id == inv.id).first()
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


# ── Accion manual sobre auditoria ──────────────────────

@app.post("/api/audit-results/{audit_id}/approve")
def approve_audit(audit_id: int, db: Session = Depends(get_db)):
    r = db.query(AuditResult).filter(AuditResult.id == audit_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="No encontrado")
    r.status = AuditStatus.APPROVED
    r.reviewed_at = datetime.utcnow()
    r.reviewed_by = "auditor_manual"
    db.commit()
    return {"status": "approved", "audit_id": audit_id}


@app.post("/api/audit-results/{audit_id}/reject")
def reject_audit(audit_id: int, db: Session = Depends(get_db)):
    r = db.query(AuditResult).filter(AuditResult.id == audit_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="No encontrado")
    r.status = AuditStatus.REJECTED
    r.reviewed_at = datetime.utcnow()
    r.reviewed_by = "auditor_manual"
    db.commit()
    return {"status": "rejected", "audit_id": audit_id}


@app.post("/api/audit-results/{audit_id}/escalate")
def escalate_audit(audit_id: int, db: Session = Depends(get_db)):
    r = db.query(AuditResult).filter(AuditResult.id == audit_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="No encontrado")
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
        "subtotal": invoice.subtotal,
        "iva": invoice.iva,
        "total": invoice.total,
        "items": [
            {
                "code": i.code or "",
                "description": i.description,
                "category": i.category or "",
                "quantity": i.quantity,
                "unit_price": i.unit_price,
                "total_price": i.total_price,
            }
            for i in items
        ],
    }


def _build_siniestro_dict(siniestro) -> dict:
    return {
        "claim_number": f"SIN-{siniestro.id_siniestro}",
        "claim_type": siniestro.ramo.value if siniestro.ramo else "",
        "description": siniestro.descripcion or "",
        "vehicle": "",
        "vehicle_plate": "",
        "insured_name": siniestro.id_asegurado or "",
        "policy_number": siniestro.id_poliza or "",
        "incident_date": siniestro.fecha_ocurrencia.strftime("%d/%m/%Y") if siniestro.fecha_ocurrencia else "",
    }


def _save_ai_result(db, invoice, siniestro, ai_result: dict):
    from backend.models import AuditStatus, AuditFinding, FindingSeverity, FindingType
    status_val = getattr(AuditStatus, ai_result["status"].upper(), AuditStatus.COMPLETED)
    is_test = getattr(invoice, "is_test", 0) or 0
    existing = db.query(AuditResult).filter(AuditResult.invoice_id == invoice.id).first()
    if existing:
        existing.status = status_val
        existing.risk_score = ai_result["risk_score"]
        existing.total_overcharge = ai_result["total_overcharge"]
        existing.summary = ai_result.get("notas_agente", "")
        existing.agent_notes = json.dumps({"ai": True, "model": ai_result.get("model_used", ""), "documentacion": ai_result.get("documentacion")}, ensure_ascii=False)
        existing.audit_engine = "gemini"
        existing.is_test = is_test
        existing.audited_at = datetime.utcnow()
        db.query(AuditFinding).filter(AuditFinding.audit_result_id == existing.id).delete()
        audit_result = existing
    else:
        audit_result = AuditResult(
            siniestro_id=siniestro.id_siniestro, invoice_id=invoice.id,
            status=status_val,
            risk_score=ai_result["risk_score"],
            total_overcharge=ai_result["total_overcharge"],
            summary=ai_result.get("notas_agente", ""),
            agent_notes=json.dumps({"ai": True, "model": ai_result.get("model_used", ""), "documentacion": ai_result.get("documentacion")}, ensure_ascii=False),
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
            title=h["title"],
            description=h["description"],
            item_description=h.get("item_description", ""),
            expected_value=h.get("expected_value", ""),
            actual_value=h.get("actual_value", ""),
            difference=h.get("difference", 0),
            recommendation=h.get("recommendation", ""),
        ))
    db.commit()
    db.refresh(audit_result)
    return audit_result


def _get_tariff_list(db) -> list:
    tariffs = db.query(TariffItem).all()
    return [
        {
            "code": t.code, "description": t.description, "category": t.category,
            "max_price": t.max_price, "tolerance_pct": t.tolerance_pct,
            "expected_qty_min": t.expected_qty_min, "expected_qty_max": t.expected_qty_max,
            "applicable_claim_types": json.loads(t.applicable_claim_types) if t.applicable_claim_types else [],
        }
        for t in tariffs
    ]


def _run_gemini_audit(invoice_id: int, db) -> dict:
    """Lógica compartida: audita factura con Gemini, guarda y retorna resultado."""
    from backend.gemini_auditor import GeminiAuditor

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Factura {invoice_id} no encontrada")
    siniestro = db.query(Siniestro).filter(Siniestro.id_siniestro == invoice.siniestro_id).first()
    if not siniestro:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado")

    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).all()

    # Tarea 3: historial de todas las facturas para detección de re-facturación
    all_invoices = db.query(Invoice).all()
    invoice_history = [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
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
            tariff_items=_get_tariff_list(db),
            invoice_history=invoice_history,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error Gemini: {str(e)}")

    audit_result = _save_ai_result(db, invoice, siniestro, ai_result)

    return {
        "audit_id": audit_result.id,
        "invoice_id": invoice.id,
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
def audit_invoice_ai(invoice_id: int, db: Session = Depends(get_db)):
    """Auditar factura existente en DB usando Gemini 2.5 Flash."""
    return _run_gemini_audit(invoice_id, db)


@app.post("/api/audit-ai-all")
def audit_all_ai(db: Session = Depends(get_db)):
    """Auditar todas las facturas individualmente con Gemini 2.5 Flash."""
    invoices = db.query(Invoice).all()
    results = []
    errors = []
    for inv in invoices:
        try:
            results.append(_run_gemini_audit(inv.id, db))
        except HTTPException as e:
            errors.append({"invoice_id": inv.id, "error": e.detail})
    return {"audited": len(results), "errors": errors, "results": results}


@app.post("/api/audit-gemini/{invoice_id}")
def audit_invoice_gemini(invoice_id: int, db: Session = Depends(get_db)):
    """Auditar factura existente en DB usando Gemini 2.5 Flash (alias de /audit-ai/{id})."""
    return _run_gemini_audit(invoice_id, db)


@app.post("/api/audit-gemini-batch")
def audit_gemini_batch(db: Session = Depends(get_db)):
    """
    Auditar TODAS las facturas en una sola llamada Gemini 2.5 Flash.
    Aprovecha el contexto de 1M tokens para detectar patrones cruzados entre talleres.
    """
    from backend.gemini_auditor import GeminiAuditor

    invoices_db = db.query(Invoice).all()
    siniestros_db = db.query(Siniestro).all()
    tariffs_db = db.query(TariffItem).all()

    tariff_list = [
        {
            "code": t.code, "description": t.description, "category": t.category,
            "max_price": t.max_price, "tolerance_pct": t.tolerance_pct,
            "expected_qty_min": t.expected_qty_min, "expected_qty_max": t.expected_qty_max,
            "applicable_claim_types": json.loads(t.applicable_claim_types) if t.applicable_claim_types else [],
        }
        for t in tariffs_db
    ]

    siniestro_map = {s.id_siniestro: s for s in siniestros_db}
    invoices_payload = []
    siniestros_payload = []

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
            invoices=invoices_payload,
            claims=siniestros_payload,
            tariff_items=tariff_list,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error Gemini batch: {str(e)}")

    # Persistir resultados individuales
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
                    saved_result = _save_ai_result(db, inv, siniestro, a_for_save)
                    saved.append(saved_result.id)
                except Exception:
                    pass

    return {
        "model_used": batch_result.get("model_used", ""),
        "facturas_en_lote": len(invoices_payload),
        "auditorias_guardadas": len(saved),
        "resumen_global": batch_result["resumen_global"],
        "auditorias": batch_result["auditorias"],
    }


@app.post("/api/audit-pdf")
async def audit_pdf_upload(
    file: UploadFile = File(...),
    claim_number: str = Form(None),
    is_test: int = Form(0),
    db: Session = Depends(get_db),
):
    """
    Sube PDF de factura, extrae datos y guarda como pendiente de auditoría.
    is_test=1 → marca factura como prueba (filtrable en dashboard real).
    """
    from backend.pdf_extractor import extract_invoice_from_pdf

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
    workshop = db.query(Workshop).filter(Workshop.ruc == ruc).first()
    if not workshop:
        workshop = Workshop(
            name=invoice_data.get("workshop_name") or "Taller Desconocido",
            ruc=ruc,
        )
        db.add(workshop)
        db.flush()

    # Datos del siniestro extraídos del PDF
    pdf_claim_number = (invoice_data.get("claim_number") or "").strip()
    pdf_claim_type = (invoice_data.get("claim_type") or "").strip()
    pdf_policy = (invoice_data.get("policy_number") or "").strip()
    pdf_insured = (invoice_data.get("insured_name") or "").strip()

    ramo_enum = Ramo.VEHICULOS
    if pdf_claim_type:
        try:
            ramo_enum = Ramo(pdf_claim_type)
        except ValueError:
            pass

    siniestro = None
    effective_ref = (claim_number or "").strip() or pdf_claim_number or pdf_policy
    if effective_ref:
        siniestro = db.query(Siniestro).filter(Siniestro.id_poliza == effective_ref).first()
    if not siniestro:
        placeholder_poliza = effective_ref or f"PDF-{file.filename[:20]}"
        siniestro = db.query(Siniestro).filter(Siniestro.id_poliza == placeholder_poliza).first()
        if not siniestro:
            siniestro = Siniestro(
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
        else:
            if (not siniestro.id_asegurado or siniestro.id_asegurado == "Desconocido") and pdf_insured:
                siniestro.id_asegurado = pdf_insured[:50]

    try:
        issue_date = datetime.strptime(invoice_data.get("issue_date", ""), "%d/%m/%Y")
    except Exception:
        issue_date = datetime.utcnow()

    invoice_number = (invoice_data.get("invoice_number") or "").strip() or f"PDF-{file.filename}"

    # Dedupe estricto: mismo (invoice_number, workshop_id) y mismo invoice_number global
    existing = db.query(Invoice).filter(
        Invoice.invoice_number == invoice_number,
        Invoice.workshop_id == workshop.id,
    ).first()
    if existing:
        db.rollback()
        return {
            "filename": file.filename,
            "invoice_id": existing.id,
            "invoice_extracted": invoice_data,
            "status": "already_exists",
            "is_test": bool(existing.is_test),
            "message": f"La factura {invoice_number} de este taller ya está registrada.",
        }

    invoice = Invoice(
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
        existing = db.query(Invoice).filter(
            Invoice.invoice_number == invoice_number,
            Invoice.workshop_id == workshop.id,
        ).first()
        if existing:
            return {
                "filename": file.filename,
                "invoice_id": existing.id,
                "invoice_extracted": invoice_data,
                "status": "already_exists",
                "is_test": bool(existing.is_test),
                "message": f"La factura {invoice_number} ya estaba registrada (race resuelto).",
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
        "filename": file.filename,
        "invoice_id": invoice.id,
        "invoice_extracted": invoice_data,
        "status": "pending",
        "is_test": bool(invoice.is_test),
        "message": "Factura cargada y añadida a la cola de auditoría.",
    }

# ── Generador de Facturas PDF de Prueba ─────────────────

@app.get("/api/test-pdfs")
def list_test_pdfs():
    """Lista escenarios de prueba disponibles + PDFs ya generados."""
    from backend.test_invoice_generator import SCENARIOS, OUTPUT_DIR_DEFAULT

    output = []
    for name, scen in SCENARIOS.items():
        full_path = os.path.join(OUTPUT_DIR_DEFAULT, name)
        exists = os.path.exists(full_path)
        output.append({
            "filename": name,
            "label": scen["label"],
            "description": scen["description"],
            "exists": exists,
            "size_kb": round(os.path.getsize(full_path) / 1024, 1) if exists else 0,
        })
    return {"output_dir": OUTPUT_DIR_DEFAULT, "scenarios": output}


@app.post("/api/test-pdfs/generate")
def generate_test_pdfs():
    """Genera (o regenera) los 3 PDFs canónicos de factura de prueba."""
    from backend.test_invoice_generator import generate_all_test_invoices
    try:
        results = generate_all_test_invoices()
        return {"status": "success", "count": len(results), "files": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDFs de prueba: {str(e)}")


@app.post("/api/test-pdfs/random")
def generate_random_test_pdf(scenario: str = "mixed", count: int = 1):
    """
    Genera 1 o más facturas SRI aleatorias.
      scenario: limpia | sobrecobro | fraude | mixed
      count:    número de facturas a generar (1-10)
    Retorna metadata de cada factura (preview values, sin el PDF embebido).
    """
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
    """Descarga un PDF de prueba (canónico o aleatorio) por filename."""
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


# --- Nuevos Endpoints del Sistema Operativo Agéntico ---

@app.get("/api/invoices/pending")
def get_pending_invoices(include_test: int = 1, db: Session = Depends(get_db)):
    """Retorna facturas que no tienen un registro en AuditResult."""
    audited_invoice_ids = [a.invoice_id for a in db.query(AuditResult.invoice_id).all()]
    q = db.query(Invoice).filter(~Invoice.id.in_(audited_invoice_ids))
    if not include_test:
        q = q.filter((Invoice.is_test == 0) | (Invoice.is_test.is_(None)))
    pending = q.all()

    res = []
    for inv in pending:
        res.append({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "claim_number": f"SIN-{inv.siniestro.id_siniestro}" if inv.siniestro else "N/A",
            "claim_type": inv.siniestro.ramo.value if inv.siniestro and inv.siniestro.ramo else "N/A",
            "workshop_name": inv.workshop.name if inv.workshop else "N/A",
            "total": inv.total,
            "is_test": bool(inv.is_test),
        })
    return res

def _build_full_audit_dict(db: Session, audit: AuditResult) -> tuple[dict, str]:
    """Construye dict completo (con items, findings, siniestro, workshop) para PDFs."""
    invoice = db.query(Invoice).filter(Invoice.id == audit.invoice_id).first()
    siniestro = db.query(Siniestro).filter(Siniestro.id_siniestro == audit.siniestro_id).first()
    workshop = invoice.workshop if invoice and invoice.workshop_id else None
    workshop_name = workshop.name if workshop else "Taller Desconocido"

    findings_db = db.query(AuditFinding).filter(AuditFinding.audit_result_id == audit.id).all()
    items_db = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == audit.invoice_id).all() if invoice else []
    tariff_map = {t.code: t for t in db.query(TariffItem).all()}

    findings = []
    for f in findings_db:
        ftype = f.finding_type.value if f.finding_type else ""
        findings.append({
            "finding_type": ftype,
            "severity": f.severity.value if f.severity else "info",
            "title": f.title or "",
            "description": f.description or "",
            "item_description": f.item_description or "",
            "expected_value": f.expected_value or "",
            "actual_value": f.actual_value or "",
            "difference": f.difference or 0,
            "recommendation": f.recommendation or "",
            "regla": ftype.replace("_", " ").title() if ftype else "",
            "detalle": f.description or "",
            "impacto_economico": f.difference or 0,
        })

    items = []
    for it in items_db:
        tar = tariff_map.get(it.code)
        items.append({
            "code": it.code or "",
            "description": it.description or "",
            "category": it.category or "",
            "quantity": it.quantity,
            "unit_price": it.unit_price,
            "total_price": it.total_price,
            "tariff_price": tar.max_price if tar else None,
            "tariff_tolerance": tar.tolerance_pct if tar else None,
        })

    audit_data = {
        "audit_id": audit.id,
        "invoice_number": invoice.invoice_number if invoice else "N/A",
        "claim_number": f"SIN-{siniestro.id_siniestro}" if siniestro else "-",
        "claim_type": siniestro.ramo.value if siniestro and siniestro.ramo else "-",
        "vehicle": "-",
        "vehicle_plate": "-",
        "insured_name": siniestro.id_asegurado if siniestro else "-",
        "workshop_name": workshop_name,
        "status": audit.status.value if audit.status else "pending",
        "risk_score": audit.risk_score or 0,
        "total_overcharge": audit.total_overcharge or 0,
        "invoice_subtotal": invoice.subtotal if invoice else 0,
        "invoice_iva": invoice.iva if invoice else 0,
        "invoice_total": invoice.total if invoice else 0,
        "items": items,
        "findings": findings,
        "hallazgos": findings,
        "notas_agente": audit.summary or "",
        "resumen_ejecutivo_taller": (
            f"{audit.summary}\n\nLa presente comunicación es emitida por el Departamento de Auditoría Técnica de Siniestros como parte del proceso formal de validación y conciliación de facturación. Solicitamos atentamente la aplicación de los ajustes detallados en su próxima emisión y quedamos a su disposición para cualquier aclaración dentro de los plazos contractuales establecidos.\n\nAtentamente,\nDepartamento de Auditoría Técnica de Siniestros\nEquipo Miraclex — HackIAthon 2026"
            if audit.summary else
            "Tras la revisión completa de la factura presentada, se han identificado los ajustes detallados a continuación a aplicar en su próxima facturación.\n\nLa presente comunicación es emitida por el Departamento de Auditoría Técnica de Siniestros como parte del proceso formal de validación y conciliación de facturación. Solicitamos atentamente la aplicación de los ajustes detallados en su próxima emisión y quedamos a su disposición para cualquier aclaración dentro de los plazos contractuales establecidos.\n\nAtentamente,\nDepartamento de Auditoría Técnica de Siniestros\nEquipo Miraclex — HackIAthon 2026"
        ),
        "ahorro_estimado": audit.total_overcharge or 0,
    }
    return audit_data, workshop_name


@app.get("/api/audit-results/{audit_id}/report-preview")
def preview_workshop_report(audit_id: int, type: str = "internal", db: Session = Depends(get_db)):
    """
    Genera PDF preview.
      type=internal  → reporte interno con análisis de riesgo (preview al aprobar).
      type=workshop  → notificación profesional al taller (sin riesgo).
    """
    from backend.pdf_generator import generate_audit_report_pdf, generate_workshop_notification_pdf

    audit = db.query(AuditResult).filter(AuditResult.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")

    audit_data, workshop_name = _build_full_audit_dict(db, audit)

    try:
        if type == "workshop":
            pdf_path = generate_workshop_notification_pdf(audit_data, workshop_name)
        else:
            pdf_path = generate_audit_report_pdf(audit_data, workshop_name)
        # inline → render en <iframe> sin forzar descarga
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{os.path.basename(pdf_path)}"',
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")

# --- Nuevos Endpoints del Sistema Operativo Agéntico ---

from pydantic import BaseModel

class TariffUpdate(BaseModel):
    max_price: float

@app.put("/api/tariffs/{tariff_id}")
def update_tariff(tariff_id: int, data: TariffUpdate, db: Session = Depends(get_db)):
    """Actualiza el precio máximo de un tarifario."""
    tariff = db.query(TariffItem).filter(TariffItem.id == tariff_id).first()
    if not tariff:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    tariff.max_price = data.max_price
    db.commit()
    db.refresh(tariff)
    return {"status": "success", "max_price": tariff.max_price}

@app.post("/api/audit-results/{audit_id}/notify")
def notify_workshop(audit_id: int, db: Session = Depends(get_db)):
    """
    Genera PDF de notificación profesional y simula envío a múltiples destinatarios.
    Se basa en el email del taller + correos extra configurados en el siniestro.
    """
    from backend.pdf_generator import generate_workshop_notification_pdf

    audit = db.query(AuditResult).filter(AuditResult.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")

    invoice = db.query(Invoice).filter(Invoice.id == audit.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=400, detail="Falta información de la factura")

    workshop = invoice.workshop
    workshop_name = workshop.name if workshop else "Taller Desconocido"

    # Construir lista de destinatarios
    recipients = []
    if workshop and workshop.email:
        recipients.append(workshop.email)

    # Correos extra guardados en siniestro.descripcion como JSON (campo notify_emails)
    siniestro = db.query(Siniestro).filter(Siniestro.id_siniestro == audit.siniestro_id).first()
    extra_emails_raw = None
    if siniestro and siniestro.descripcion:
        try:
            siniestro_meta = json.loads(siniestro.descripcion)
            extra_emails_raw = siniestro_meta.get("notify_emails", "")
        except Exception:
            pass

    if extra_emails_raw:
        for e in str(extra_emails_raw).split(","):
            e = e.strip()
            if e and e not in recipients:
                recipients.append(e)

    # Fallback demo si no hay ninguno
    if not recipients:
        recipients = [
            "auditor.jefe@aseguradora-hackiathon.ec",
            "siniestros@aseguradora-hackiathon.ec",
            "revisor@aseguradora-hackiathon.ec",
        ]

    audit_data, _ = _build_full_audit_dict(db, audit)

    try:
        pdf_path = generate_workshop_notification_pdf(audit_data, workshop_name)
        simulated_log = []
        for addr in recipients:
            simulated_log.append(f"✅ EMAIL SIMULADO → {addr}")
            print(f"✅ EMAIL ENVIADO SIMULADO: Para: {addr} | Adjunto: {os.path.basename(pdf_path)}")
        return {
            "status": "success",
            "message": f"Notificación enviada a {len(recipients)} destinatario(s)",
            "recipients": recipients,
            "pdf_path": pdf_path,
            "log": simulated_log,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


@app.put("/api/claims/{claim_id}/notify-config")
def update_claim_notify_config(claim_id: int, data: dict, db: Session = Depends(get_db)):
    """
    Guarda los correos adicionales de notificación para un siniestro.
    Body: {"notify_emails": "a@b.com, c@d.com"}
    """
    siniestro = db.query(Siniestro).filter(Siniestro.id_siniestro == claim_id).first()
    if not siniestro:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado")

    notify_emails = data.get("notify_emails", "")

    # Fusionar con descripción existente (puede ser JSON o texto libre)
    try:
        meta = json.loads(siniestro.descripcion or "{}")
    except Exception:
        meta = {"original_description": siniestro.descripcion or ""}

    meta["notify_emails"] = notify_emails
    siniestro.descripcion = json.dumps(meta, ensure_ascii=False)
    db.commit()
    return {"status": "ok", "claim_id": claim_id, "notify_emails": notify_emails}


@app.get("/api/claims/{claim_id}/notify-config")
def get_claim_notify_config(claim_id: int, db: Session = Depends(get_db)):
    """Devuelve la configuración de notificación del siniestro."""
    siniestro = db.query(Siniestro).filter(Siniestro.id_siniestro == claim_id).first()
    if not siniestro:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado")
    try:
        meta = json.loads(siniestro.descripcion or "{}")
        notify_emails = meta.get("notify_emails", "")
    except Exception:
        notify_emails = ""
    workshop_email = ""
    for inv in (siniestro.invoices or []):
        if inv.workshop and inv.workshop.email:
            workshop_email = inv.workshop.email
            break
    return {"claim_id": claim_id, "workshop_email": workshop_email, "notify_emails": notify_emails}
