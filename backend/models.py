"""
Modelos SQLAlchemy para el Auditor Agéntico de Facturación de Siniestros.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum as SQLEnum,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from backend.database import Base


# ── Enums ──────────────────────────────────────────────

class Ramo(str, enum.Enum):
    VEHICULOS = "Vehículos"
    SALUD = "Salud"
    VIDA = "Vida"
    GENERALES = "Generales"
    HOGAR = "Hogar"
    OTRO = "Otro"


class Cobertura(str, enum.Enum):
    CHOQUE = "Choque"
    ROBO = "Robo"
    ATENCION_MEDICA = "Atención médica"
    INCENDIO = "Incendio"
    DANIO = "Daño"
    OTRO = "Otro"


class EstadoSiniestro(str, enum.Enum):
    RESERVA = "Reserva"
    PAGO_TOTAL = "Pago Total"
    PAGO_PARCIAL = "Pago Parcial"
    ANTICIPO = "Anticipo"
    NEGATIVA = "Negativa"
    CIERRE_SIN_CONSECUENCIA = "Cierre Sin Consecuencia"
    LIQUIDADO = "Liquidado"


class AuditStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class FindingSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class FindingType(str, enum.Enum):
    OVERCHARGE = "overcharge"
    DUPLICATE = "duplicate"
    QUANTITY_ANOMALY = "quantity_anomaly"
    INCOHERENCE = "incoherence"
    MISSING_DOCUMENT = "missing_document"
    CLEAN = "clean"


# ── Modelos ────────────────────────────────────────────

class Workshop(Base):
    """Taller automotriz."""
    __tablename__ = "workshops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    ruc = Column(String(13), unique=True, nullable=False)
    address = Column(String(300))
    phone = Column(String(20))
    email = Column(String(100))
    notify_automatically = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoices = relationship("Invoice", back_populates="workshop")


class Siniestro(Base):
    """Siniestro reportado."""
    __tablename__ = "siniestros"

    id_siniestro = Column(Integer, primary_key=True, index=True)
    id_poliza = Column(String(20), nullable=False, index=True)
    id_asegurado = Column(String(50), nullable=False, index=True)
    ramo = Column(SQLEnum(Ramo), nullable=False)
    cobertura = Column(SQLEnum(Cobertura), nullable=False)
    fecha_ocurrencia = Column(DateTime, nullable=False)
    fecha_reporte = Column(DateTime, default=datetime.utcnow)
    monto_reclamado = Column(Float)
    monto_estimado = Column(Float)
    monto_pagado = Column(Float)
    estado = Column(SQLEnum(EstadoSiniestro), nullable=False)
    sucursal = Column(String(100))
    descripcion = Column(Text)
    documentos_completos = Column(Integer, default=0)  # 0=No, 1=Sí
    beneficiario = Column(String(100))
    dias_desde_inicio_poliza = Column(Integer)
    dias_desde_fin_poliza = Column(Integer)
    dias_entre_ocurrencia_reporte = Column(Integer)
    historial_siniestros_asegurado = Column(Integer, default=0)
    etiqueta_fraude_simulada = Column(Integer)  # 0/1, solo para entrenamiento

    invoices = relationship("Invoice", back_populates="siniestro")
    audit_results = relationship("AuditResult", back_populates="siniestro")


class Invoice(Base):
    """Factura del taller."""
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("invoice_number", "workshop_id", name="uq_invoice_workshop"),
    )

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(20), nullable=False)
    siniestro_id = Column(Integer, ForeignKey("siniestros.id_siniestro"), nullable=False)
    workshop_id = Column(Integer, ForeignKey("workshops.id"), nullable=False)
    issue_date = Column(DateTime, nullable=False)
    subtotal = Column(Float, default=0.0)
    iva = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    raw_data = Column(Text)  # JSON/XML original
    is_test = Column(Integer, default=0, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    siniestro = relationship("Siniestro", back_populates="invoices")
    workshop = relationship("Workshop", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    audit_results = relationship("AuditResult", back_populates="invoice")


class InvoiceItem(Base):
    """Ítem individual de la factura."""
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    code = Column(String(20))
    description = Column(String(300), nullable=False)
    category = Column(String(50))  # repuesto, mano_obra, pintura, material
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="items")


class TariffItem(Base):
    """Ítem del tarifario acordado entre aseguradora y talleres."""
    __tablename__ = "tariff_items"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(String(300), nullable=False)
    category = Column(String(50), nullable=False)
    max_price = Column(Float, nullable=False)
    tolerance_pct = Column(Float, default=10.0)
    expected_qty_min = Column(Float, default=0.0)
    expected_qty_max = Column(Float, default=100.0)
    applicable_claim_types = Column(Text)  # JSON list de Ramo
    updated_at = Column(DateTime, default=datetime.utcnow)


class AuditResult(Base):
    """Resultado de la auditoría de una factura."""
    __tablename__ = "audit_results"

    id = Column(Integer, primary_key=True, index=True)
    siniestro_id = Column(Integer, ForeignKey("siniestros.id_siniestro"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    status = Column(SQLEnum(AuditStatus), default=AuditStatus.PENDING)
    risk_score = Column(Float, default=0.0)  # 0-100
    total_overcharge = Column(Float, default=0.0)
    summary = Column(Text)
    agent_notes = Column(Text)
    audit_engine = Column(String(20), default="rules")  # rules | gemini
    is_test = Column(Integer, default=0, index=True)
    audited_at = Column(DateTime)
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)

    siniestro = relationship("Siniestro", back_populates="audit_results")
    invoice = relationship("Invoice", back_populates="audit_results")
    findings = relationship("AuditFinding", back_populates="audit_result", cascade="all, delete-orphan")


class AuditFinding(Base):
    """Hallazgo individual detectado por el agente."""
    __tablename__ = "audit_findings"

    id = Column(Integer, primary_key=True, index=True)
    audit_result_id = Column(Integer, ForeignKey("audit_results.id"), nullable=False)
    finding_type = Column(SQLEnum(FindingType), nullable=False)
    severity = Column(SQLEnum(FindingSeverity), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    item_description = Column(String(300))
    expected_value = Column(String(100))
    actual_value = Column(String(100))
    difference = Column(Float)
    recommendation = Column(Text)

    audit_result = relationship("AuditResult", back_populates="findings")
