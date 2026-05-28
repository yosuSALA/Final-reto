"""
Agente Auditor — el corazón del sistema.
Ejecuta el pipeline completo de auditoría sobre una factura.
"""
import json
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.models import (
    Invoice, InvoiceItem, TariffItem, Siniestro, AuditResult,
    AuditFinding, AuditStatus, FindingSeverity
)
from backend.rules_engine import RulesEngine, Finding


class AuditAgent:
    def __init__(self, db: Session, profile_id: str = None):
        self.db = db
        self.profile_id = profile_id
        self.engine = RulesEngine()

    def _q(self, model):
        """Query filtrada por profile_id cuando está disponible."""
        q = self.db.query(model)
        if self.profile_id and hasattr(model, "profile_id"):
            q = q.filter(model.profile_id == self.profile_id)
        return q

    def audit_invoice(self, invoice_id: int) -> Dict[str, Any]:
        invoice = self._q(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return {"error": f"Factura {invoice_id} no encontrada"}
        claim = self._q(Siniestro).filter(Siniestro.id_siniestro == invoice.siniestro_id).first()
        if not claim:
            return {"error": f"Siniestro no encontrado para factura {invoice_id}"}
        items = self.db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).all()
        tariff_items = self._q(TariffItem).all()
        tariff_map = {t.code: {"code": t.code, "description": t.description, "category": t.category, "max_price": t.max_price, "tolerance_pct": t.tolerance_pct, "expected_qty_min": t.expected_qty_min, "expected_qty_max": t.expected_qty_max, "applicable_claim_types": t.applicable_claim_types or "[]"} for t in tariff_items}

        # Historial filtrado al perfil para detección de re-facturación
        all_invoices = self._q(Invoice).all()
        invoice_history = [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "claim_number": str(inv.siniestro.id_siniestro) if inv.siniestro else "",
                "claim_type": inv.siniestro.ramo.value if inv.siniestro and inv.siniestro.ramo else "",
                "workshop_ruc": inv.workshop.ruc if inv.workshop else "",
                "total": inv.total or 0.0,
            }
            for inv in all_invoices
        ]

        context = {
            "invoice_id": invoice.id, "invoice_number": invoice.invoice_number,
            "claim_id": claim.id_siniestro, "claim_number": str(claim.id_siniestro),
            "claim_type": claim.ramo.value if claim.ramo else "",
            "workshop_ruc": invoice.workshop.ruc if invoice.workshop else "",
            "invoice_items": [{"id": i.id, "code": i.code or "", "description": i.description, "category": i.category or "", "quantity": i.quantity, "unit_price": i.unit_price, "total_price": i.total_price} for i in items],
            "tariff_map": tariff_map,
            "invoice_history": invoice_history,  # para InvoiceResubmissionRule
        }
        findings = self.engine.run_audit(context)
        risk_score = self.engine.calculate_risk_score(findings)
        total_overcharge = sum(f.difference for f in findings if f.difference > 0)
        summary = self._generate_summary(invoice, claim, findings, risk_score)
        audit_result = self._save_result(invoice, claim, findings, risk_score, total_overcharge, summary)
        return {
            "audit_id": audit_result.id, "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number, "claim_number": str(claim.id_siniestro),
            "claim_type": claim.ramo.value if claim.ramo else "",
            "workshop_name": invoice.workshop.name if invoice.workshop else "",
            "status": audit_result.status.value, "risk_score": risk_score,
            "total_overcharge": round(total_overcharge, 2), "invoice_total": invoice.total,
            "summary": summary, "findings": [f.to_dict() for f in findings],
            "findings_count": {"critical": sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL), "warning": sum(1 for f in findings if f.severity == FindingSeverity.WARNING), "info": sum(1 for f in findings if f.severity == FindingSeverity.INFO)},
            "items_audited": len(items),
            "audited_at": audit_result.audited_at.isoformat() if audit_result.audited_at else None,
        }

    def _generate_summary(self, invoice, claim, findings, risk_score):
        if not findings:
            return f"La factura {invoice.invoice_number} del siniestro {str(claim.id_siniestro)} no presenta anomalias. Todos los items estan dentro del tarifario acordado."
        critical = sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)
        warnings = sum(1 for f in findings if f.severity == FindingSeverity.WARNING)
        parts = [f"La factura {invoice.invoice_number} del siniestro {str(claim.id_siniestro)} presenta {len(findings)} hallazgo(s):"]
        if critical:
            parts.append(f"  {critical} hallazgo(s) CRITICO(S)")
        if warnings:
            parts.append(f"  {warnings} advertencia(s)")
        if risk_score >= 70:
            parts.append("  Recomendacion: ESCALAR para revision manual inmediata.")
        elif risk_score >= 40:
            parts.append("  Recomendacion: Solicitar justificacion al taller.")
        else:
            parts.append("  Recomendacion: Revisar hallazgos menores.")
        return "\n".join(parts)

    def _save_result(self, invoice, claim, findings, risk_score, total_overcharge, summary):
        if risk_score >= 70:
            status = AuditStatus.ESCALATED
        elif risk_score >= 30:
            status = AuditStatus.COMPLETED
        else:
            status = AuditStatus.APPROVED
        is_test = getattr(invoice, "is_test", 0) or 0
        existing = self._q(AuditResult).filter(AuditResult.invoice_id == invoice.id).first()
        if existing:
            existing.status = status
            existing.risk_score = risk_score
            existing.total_overcharge = total_overcharge
            existing.summary = summary
            existing.audit_engine = "rules"
            existing.is_test = is_test
            existing.audited_at = datetime.utcnow()
            self.db.query(AuditFinding).filter(AuditFinding.audit_result_id == existing.id).delete()
            audit_result = existing
        else:
            audit_result = AuditResult(
                profile_id=self.profile_id,
                siniestro_id=claim.id_siniestro, invoice_id=invoice.id, status=status,
                risk_score=risk_score, total_overcharge=total_overcharge, summary=summary,
                audit_engine="rules", is_test=is_test, audited_at=datetime.utcnow(),
            )
            self.db.add(audit_result)
        self.db.flush()
        for f in findings:
            self.db.add(AuditFinding(audit_result_id=audit_result.id, finding_type=f.finding_type, severity=f.severity, title=f.title, description=f.description, item_description=f.item_description, expected_value=f.expected_value, actual_value=f.actual_value, difference=f.difference, recommendation=f.recommendation))
        self.db.commit()
        self.db.refresh(audit_result)
        return audit_result

    def audit_all_pending(self):
        invoices = self._q(Invoice).all()
        results = []
        for inv in invoices:
            existing = self._q(AuditResult).filter(AuditResult.invoice_id == inv.id).first()
            if not existing:
                results.append(self.audit_invoice(inv.id))
        return results
