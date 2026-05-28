"""
Capa de acceso a datos con permisos por rol a nivel de tabla.
No filtra filas por profile_id — todos los perfiles ven los mismos datos.
El role del perfil determina a qué tablas puede leer/escribir (como GRANT en SQL).
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.models import (
    Profile, Siniestro, Poliza, AseguradoSintetico, Vehiculo,
    Documento, Invoice, InvoiceItem, TariffItem, AuditResult,
    AuditFinding, Workshop,
)

_ALL = frozenset({
    "siniestros", "polizas", "asegurados", "workshops",
    "invoices", "tariffs", "audit_results",
})

# Permisos por rol: read/write sobre tablas (análogo a GRANT en SQL)
TABLE_PERMISSIONS: dict[str, dict[str, frozenset]] = {
    "admin": {
        # Administrador del sistema: acceso completo. Además puede borrar
        # perfiles y ver el log de auditoría interna (chequeo aparte en main.py).
        "read":  _ALL,
        "write": _ALL,
    },
    "demo_jurado": {
        "read":  _ALL,
        "write": _ALL,
    },
    "analista": {
        "read":  _ALL,
        "write": frozenset({
            "siniestros", "invoices", "workshops", "tariffs", "audit_results",
        }),
    },
    "antifraude": {
        "read":  _ALL,
        "write": frozenset(),
    },
    "jefatura": {
        # Jefatura toma decisiones finales sobre siniestros escalados (audit_results)
        "read":  _ALL,
        "write": frozenset({"audit_results"}),
    },
    "auditoria": {
        "read":  _ALL,
        "write": frozenset({"audit_results"}),
    },
    # ── Roles nuevos ──────────────────────────────────────
    "operaciones": {
        # Sólo Operaciones registra nuevos siniestros
        "read":  _ALL,
        "write": frozenset({"siniestros", "polizas", "asegurados", "workshops", "invoices"}),
    },
    "costos": {
        # Costos modifica tarifario + aprobación inicial / escalamiento
        "read":  _ALL,
        "write": frozenset({"tariffs", "audit_results"}),
    },
    "contabilidad": {
        # Contabilidad: igual que Costos
        "read":  _ALL,
        "write": frozenset({"tariffs", "audit_results"}),
    },
    "legal": {
        # Legal: sólo lectura de tarifarios, siniestros y notificaciones
        "read":  frozenset({"tariffs", "siniestros", "audit_results", "polizas", "asegurados", "workshops", "invoices"}),
        "write": frozenset(),
    },
}


class ProfileScope:
    """Wrapper de sesión con control de acceso por rol a nivel de tabla."""

    def __init__(self, db: Session, profile: Profile):
        self.db = db
        self.profile_id = profile.id  # guardado para audit trail al crear registros
        self.role = profile.role or "analista"
        self._perms = TABLE_PERMISSIONS.get(self.role, TABLE_PERMISSIONS["analista"])

    # ── Permisos ───────────────────────────────────────────

    def can_read(self, table: str) -> bool:
        return table in self._perms["read"]

    def can_write(self, table: str) -> bool:
        return table in self._perms["write"]

    def require_write(self, table: str) -> None:
        if not self.can_write(table):
            raise HTTPException(
                status_code=403,
                detail=f"El rol '{self.role}' no tiene permisos de escritura sobre '{table}'.",
            )

    def require_role(self, *allowed_roles: str) -> None:
        """Verifica que el rol activo esté en la lista permitida. 403 si no.
        Los roles 'admin' y 'demo_jurado' son exentos (acceso total)."""
        if self.role not in allowed_roles and self.role not in ("demo_jurado", "admin"):
            raise HTTPException(
                status_code=403,
                detail=f"Esta acción está restringida a: {', '.join(allowed_roles)}. Tu rol actual: '{self.role}'.",
            )

    # ── Queries sin filtro por profile_id ─────────────────

    def siniestros(self):
        return self.db.query(Siniestro)

    def polizas(self):
        return self.db.query(Poliza)

    def asegurados(self):
        return self.db.query(AseguradoSintetico)

    def workshops(self):
        return self.db.query(Workshop)

    def invoices(self):
        return self.db.query(Invoice)

    def tariffs(self):
        return self.db.query(TariffItem)

    def audit_results(self):
        return self.db.query(AuditResult)

    # ── Getters individuales ───────────────────────────────

    def get_invoice(self, invoice_id: int):
        return self.invoices().filter(Invoice.id == invoice_id).first()

    def get_siniestro(self, siniestro_id: int):
        return self.siniestros().filter(Siniestro.id_siniestro == siniestro_id).first()

    def get_audit_result(self, audit_id: int):
        return self.audit_results().filter(AuditResult.id == audit_id).first()

    def get_tariff(self, tariff_id: int):
        return self.tariffs().filter(TariffItem.id == tariff_id).first()

    def get_workshop(self, workshop_id: int):
        return self.workshops().filter(Workshop.id == workshop_id).first()

    def get_workshop_by_ruc(self, ruc: str):
        return self.workshops().filter(Workshop.ruc == ruc).first()

    def get_tariff_by_code(self, code: str):
        return self.tariffs().filter(TariffItem.code == code).first()

    def tariff_map(self) -> dict:
        return {t.code: t for t in self.tariffs().all()}
