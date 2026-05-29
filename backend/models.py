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
    SENT_TO_LEGAL = "sent_to_legal"


class AuditStage(str, enum.Enum):
    """Etapa del nuevo flujo operativo de 6 pasos.

    INITIAL  → ejecutada tras el registro del siniestro (declaración + historial).
    POST_PAYMENT → ejecutada tras recibir el parte policial y las facturas;
                   cruza declaración ↔ parte ↔ factura.
    LEGACY   → auditoría previa al rediseño del flujo (compatibilidad).
    """
    LEGACY = "legacy"
    INITIAL = "initial"
    POST_PAYMENT = "post_payment"


class ClaimStage(str, enum.Enum):
    """Etapa del expediente del siniestro en el flujo de 6 pasos."""
    REGISTERED = "registered"            # 1. Registro de Siniestro
    INITIAL_AUDIT = "initial_audit"      # 2. Auditoría Inicial de Fraude
    POLICE_REPORT = "police_report"      # 3. Reporte Policial recibido
    INVOICES = "invoices"                # 4. Facturas recibidas
    POST_PAYMENT_AUDIT = "post_payment_audit"  # 5. Auditoría Posterior al Pago
    FINAL_DECISION = "final_decision"    # 6. Decisión Final


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
    # Nuevos — flujo de 6 etapas (declaración + parte policial + factura)
    MISSING_POLICE_REPORT = "missing_police_report"
    DECLARATION_INCONSISTENCY = "declaration_inconsistency"
    INVOICE_DECLARATION_MISMATCH = "invoice_declaration_mismatch"
    POLICE_DECLARATION_MISMATCH = "police_declaration_mismatch"


# ── Perfil de usuario ───────────────────────────────────

class Profile(Base):
    """Perfil lógico de usuario. Toda entidad del sistema está vinculada a uno."""
    __tablename__ = "profiles"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(200))
    role = Column(String(50), default="analista")
    # HMAC secret por perfil — nunca se expone al cliente
    token_secret = Column(String(64), nullable=False)
    # Credenciales (PBKDF2-HMAC-SHA256). NULL para perfiles sin clave configurada.
    password_hash = Column(String(128), nullable=True)
    password_salt = Column(String(32), nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    siniestros = relationship("Siniestro", back_populates="profile")
    polizas = relationship("Poliza", back_populates="profile")
    asegurados = relationship("AseguradoSintetico", back_populates="profile")
    workshops = relationship("Workshop", back_populates="profile")
    invoices = relationship("Invoice", back_populates="profile")
    tariff_items = relationship("TariffItem", back_populates="profile")
    audit_results = relationship("AuditResult", back_populates="profile")


class AuditLog(Base):
    """Log inmutable de acciones de escritura y sesión, visible solo para admin."""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    profile_id = Column(String(36), nullable=True, index=True)
    profile_name = Column(String(200), nullable=True)
    role = Column(String(50), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    method = Column(String(10), nullable=True)
    path = Column(String(300), nullable=True)
    status_code = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True)
    actor_admin = Column(Integer, default=0)
    ip = Column(String(64), nullable=True)


# ── Modelos ────────────────────────────────────────────

class Workshop(Base):
    """Taller automotriz."""
    __tablename__ = "workshops"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(String(36), ForeignKey("profiles.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    ruc = Column(String(13), nullable=False)
    address = Column(String(300))
    phone = Column(String(20))
    email = Column(String(100))
    notify_automatically = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("profile_id", "ruc", name="uq_workshop_profile_ruc"),
    )

    profile = relationship("Profile", back_populates="workshops")
    invoices = relationship("Invoice", back_populates="workshop")


class AseguradoSintetico(Base):
    """Asegurado."""
    __tablename__ = "asegurados_sinteticos"

    id_asegurado = Column(String(50), primary_key=True)
    profile_id = Column(String(36), ForeignKey("profiles.id"), nullable=True, index=True)
    nombre = Column(String(150))
    segmento = Column(String(50))
    antiguedad = Column(Integer)
    ciudad = Column(String(100))
    numero_polizas = Column(Integer, default=1)
    reclamos_12m = Column(Integer, default=0)
    mora_actual = Column(Integer, default=0)
    score_cliente_simulado = Column(Float, default=100.0)

    profile = relationship("Profile", back_populates="asegurados")
    polizas = relationship("Poliza", back_populates="asegurado")
    siniestros = relationship("Siniestro", back_populates="asegurado_rel")


class Poliza(Base):
    """Póliza de seguro."""
    __tablename__ = "polizas"

    id_poliza = Column(String(20), primary_key=True)
    profile_id = Column(String(36), ForeignKey("profiles.id"), nullable=True, index=True)
    id_asegurado = Column(String(50), ForeignKey("asegurados_sinteticos.id_asegurado"), nullable=False)
    ramo = Column(SQLEnum(Ramo), nullable=False)
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_fin = Column(DateTime, nullable=False)
    prima = Column(Float, nullable=False)
    suma_asegurada = Column(Float, nullable=False)
    deducible = Column(Float, nullable=False)
    canal_venta = Column(String(50))
    ciudad = Column(String(100))
    estado_poliza = Column(String(20))

    profile = relationship("Profile", back_populates="polizas")
    asegurado = relationship("AseguradoSintetico", back_populates="polizas")
    vehiculos = relationship("Vehiculo", back_populates="poliza")
    siniestros = relationship("Siniestro", back_populates="poliza_rel")


class Vehiculo(Base):
    """Vehículo asociado a póliza y siniestros."""
    __tablename__ = "vehiculos"

    id = Column(Integer, primary_key=True, index=True)
    id_poliza = Column(String(20), ForeignKey("polizas.id_poliza"), nullable=True)
    placa = Column(String(20), index=True)
    chasis = Column(String(50))
    motor = Column(String(50))
    marca = Column(String(100))
    modelo = Column(String(100))
    anio = Column(Integer)

    poliza = relationship("Poliza", back_populates="vehiculos")
    siniestros = relationship("Siniestro", back_populates="vehiculo_rel")


class Documento(Base):
    """Documento digitalizado asociado al siniestro."""
    __tablename__ = "documentos"

    id_documento = Column(Integer, primary_key=True, index=True)
    id_siniestro = Column(Integer, ForeignKey("siniestros.id_siniestro"), nullable=False)
    tipo_documento = Column(String(100), nullable=False)
    entregado = Column(Integer, default=1)
    legible = Column(Integer, default=1)
    fecha_emision = Column(DateTime)
    inconsistencia_detectada = Column(Integer, default=0)
    observacion = Column(Text)

    siniestro = relationship("Siniestro", back_populates="documentos")


class Siniestro(Base):
    """Siniestro reportado."""
    __tablename__ = "siniestros"

    id_siniestro = Column(Integer, primary_key=True, index=True)
    profile_id = Column(String(36), ForeignKey("profiles.id"), nullable=True, index=True)
    id_poliza = Column(String(20), ForeignKey("polizas.id_poliza"), nullable=False, index=True)
    id_asegurado = Column(String(50), ForeignKey("asegurados_sinteticos.id_asegurado"), nullable=False, index=True)
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
    documentos_completos = Column(Integer, default=0)
    beneficiario = Column(String(100))
    dias_desde_inicio_poliza = Column(Integer)
    dias_desde_fin_poliza = Column(Integer)
    dias_entre_ocurrencia_reporte = Column(Integer)
    historial_siniestros_asegurado = Column(Integer, default=0)
    etiqueta_fraude_simulada = Column(Integer)

    fraud_score = Column(Float, default=0.0)
    fraud_classification = Column(String(20), default="Verde")
    fraud_indicators = Column(Text, default="[]")
    fraud_rules_failed = Column(Text, default="[]")

    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=True)

    profile = relationship("Profile", back_populates="siniestros")
    poliza_rel = relationship("Poliza", back_populates="siniestros")
    asegurado_rel = relationship("AseguradoSintetico", back_populates="siniestros")
    vehiculo_rel = relationship("Vehiculo", back_populates="siniestros")
    documentos = relationship("Documento", back_populates="siniestro", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="siniestro")
    audit_results = relationship("AuditResult", back_populates="siniestro")
    declaration = relationship("AccidentDeclaration", back_populates="siniestro", uselist=False, cascade="all, delete-orphan")
    police_report = relationship("PoliceReport", back_populates="siniestro", uselist=False, cascade="all, delete-orphan")


class Invoice(Base):
    """Factura del taller."""
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("invoice_number", "workshop_id", "profile_id", name="uq_invoice_workshop_profile"),
    )

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(String(36), ForeignKey("profiles.id"), nullable=True, index=True)
    invoice_number = Column(String(20), nullable=False)
    siniestro_id = Column(Integer, ForeignKey("siniestros.id_siniestro"), nullable=False)
    workshop_id = Column(Integer, ForeignKey("workshops.id"), nullable=False)
    issue_date = Column(DateTime, nullable=False)
    subtotal = Column(Float, default=0.0)
    iva = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    raw_data = Column(Text)
    is_test = Column(Integer, default=0, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="invoices")
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
    category = Column(String(50))
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="items")


class TariffItem(Base):
    """Ítem del tarifario acordado entre aseguradora y talleres."""
    __tablename__ = "tariff_items"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(String(36), ForeignKey("profiles.id"), nullable=True, index=True)
    code = Column(String(20), nullable=False)
    description = Column(String(300), nullable=False)
    category = Column(String(50), nullable=False)
    max_price = Column(Float, nullable=False)
    tolerance_pct = Column(Float, default=10.0)
    expected_qty_min = Column(Float, default=0.0)
    expected_qty_max = Column(Float, default=100.0)
    applicable_claim_types = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("profile_id", "code", name="uq_tariff_profile_code"),
    )

    profile = relationship("Profile", back_populates="tariff_items")


class AuditResult(Base):
    """Resultado de la auditoría de una factura."""
    __tablename__ = "audit_results"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(String(36), ForeignKey("profiles.id"), nullable=True, index=True)
    siniestro_id = Column(Integer, ForeignKey("siniestros.id_siniestro"), nullable=False)
    # Nullable: la AUDITORÍA INICIAL (etapa 2) ocurre antes de existir factura.
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    status = Column(SQLEnum(AuditStatus), default=AuditStatus.PENDING)
    audit_stage = Column(SQLEnum(AuditStage), default=AuditStage.LEGACY, index=True)
    risk_score = Column(Float, default=0.0)
    total_overcharge = Column(Float, default=0.0)
    summary = Column(Text)
    agent_notes = Column(Text)
    audit_engine = Column(String(20), default="rules")
    is_test = Column(Integer, default=0, index=True)
    audited_at = Column(DateTime)
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)

    profile = relationship("Profile", back_populates="audit_results")
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


# ── Declaración de Accidente (FR.RE.100 v01) ────────────
# Documento que envía el cliente al reportar el siniestro.
# Fuente: synthetic_data/DECLARACIÓN DE ACCIDENTE/

class AccidentDeclaration(Base):
    """Formulario de Reclamación para Accidentes de Vehículo (FR.RE.100 v01).

    Es la evidencia principal inicial del caso. Relación 1:1 con Siniestro.
    Los datos extraídos se preservan también en `raw_extract` (JSON) por trazabilidad.
    """
    __tablename__ = "accident_declarations"

    id = Column(Integer, primary_key=True, index=True)
    siniestro_id = Column(Integer, ForeignKey("siniestros.id_siniestro"), nullable=False, unique=True, index=True)
    profile_id = Column(String(36), ForeignKey("profiles.id"), nullable=True, index=True)

    # Trazabilidad del documento
    doc_id = Column(String(50), index=True)              # DOC-0952
    siniestro_ref = Column(String(20), index=True)       # SIN-0378 (tal como aparece en el PDF)
    modo = Column(String(50))                            # Manuscrito / Digital
    fecha_firma = Column(DateTime)

    # Asegurado
    asegurado_nombre = Column(String(200))
    asegurado_email = Column(String(150))
    asegurado_direccion = Column(String(300))
    asegurado_telefono = Column(String(30))
    poliza_numero = Column(String(50))
    item = Column(String(20))
    agente = Column(String(100))

    # Vehículo asegurado
    veh_marca = Column(String(50))
    veh_modelo = Column(String(50))
    veh_tipo = Column(String(50))
    veh_color = Column(String(50))
    veh_placa = Column(String(20), index=True)
    veh_motor = Column(String(50))
    veh_chasis = Column(String(50))
    veh_detalle_danos = Column(Text)
    veh_lugar_inspeccion = Column(String(300))

    # Datos del accidente
    accidente_lugar = Column(String(300))
    accidente_velocidad = Column(String(30))
    accidente_fecha = Column(DateTime)
    accidente_hora = Column(String(10))
    accidente_viniendo_de = Column(String(150))
    accidente_direccion_a = Column(String(150))
    accidente_descripcion = Column(Text)
    accidente_responsable = Column(String(200))

    # Conductor del vehículo asegurado
    conductor_nombre = Column(String(200))
    conductor_direccion = Column(String(300))
    conductor_telefono = Column(String(30))
    conductor_cedula = Column(String(20))
    conductor_categoria_licencia = Column(String(20))
    conductor_licencia_valida_hasta = Column(String(20))

    # Vehículo contrario
    contrario_marca = Column(String(50))
    contrario_modelo = Column(String(50))
    contrario_placa = Column(String(20))
    contrario_color = Column(String(50))
    contrario_aseguradora = Column(String(100))
    contrario_propietario = Column(String(200))
    contrario_detalle_danos = Column(Text)
    contrario_lugar_inspeccion = Column(String(300))

    testigos = Column(Text)

    # Intervención de autoridades
    autoridades_agentes = Column(String(300))
    autoridades_juzgado = Column(String(150))
    autoridades_detenido = Column(String(10))            # "Sí" / "No"
    autoridades_lugar_asistencia_medica = Column(String(300))

    # Datos crudos + auditoría
    raw_extract = Column(Text)                            # JSON completo del extractor
    source_filename = Column(String(255))
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    siniestro = relationship("Siniestro", back_populates="declaration")


# ── Parte Policial (Ministerio del Interior) ────────────
# Documento obligatorio dentro del flujo (etapa 3).
# Fuente: synthetic_data/PARTE POLICIAL/

class PoliceReport(Base):
    """Noticia del Incidente del Ministerio del Interior (parte policial)."""
    __tablename__ = "police_reports"

    id = Column(Integer, primary_key=True, index=True)
    siniestro_id = Column(Integer, ForeignKey("siniestros.id_siniestro"), nullable=False, unique=True, index=True)
    profile_id = Column(String(36), ForeignKey("profiles.id"), nullable=True, index=True)

    # Trazabilidad
    doc_id = Column(String(50), index=True)              # DOC-0012
    siniestro_ref = Column(String(20), index=True)       # SIN-0005
    parte_no = Column(String(40), index=True)            # PTACP20260492817
    fecha_elaboracion = Column(DateTime)
    servicio_policial = Column(String(100))

    # Unidad
    zona = Column(String(80))
    sub_zona = Column(String(80))
    distrito = Column(String(80))
    circuito = Column(String(80))
    sub_circuito = Column(String(80))
    unidad = Column(String(120))

    # Geográfica
    calle_1 = Column(String(300))
    calle_2 = Column(String(300))
    fecha_hecho = Column(DateTime)
    hora_aproximada = Column(String(10))
    tipo_via = Column(String(80))
    composicion = Column(String(80))
    estado_via = Column(String(80))
    carriles = Column(String(10))
    semaforos = Column(String(10))
    alumbrado = Column(String(10))
    latitud = Column(String(30))
    longitud = Column(String(30))

    # Clasificación
    clasificacion_tipo = Column(String(40))              # Administrativo / Penal
    flagrancia = Column(String(10))                       # SI / NO
    operativo = Column(String(50))                        # ORDINARIO / ESPECIAL

    # Tipo de accidente (checkboxes): se serializa como CSV en `tipos_accidente`
    tipos_accidente = Column(String(400))                 # "robo,choque_alcance" etc.

    consecuencias = Column(String(200))
    clima = Column(String(50))
    dia_festivo = Column(String(10))

    circunstancias = Column(Text)
    parte_elevado_a = Column(String(200))

    # Participante 1 (conductor principal). Adicionales en raw_extract.
    p1_nombre = Column(String(200))
    p1_cedula = Column(String(20))
    p1_edad = Column(Integer)
    p1_sexo = Column(String(20))
    p1_estado = Column(String(40))                       # ILESO / HERIDO / FALLECIDO
    p1_tipo_licencia = Column(String(10))
    p1_detenido = Column(String(10))
    p1_observaciones = Column(Text)

    # Vehículo principal (primero del parte). Adicionales en raw_extract.
    veh_placa = Column(String(20), index=True)
    veh_marca = Column(String(50))
    veh_modelo = Column(String(50))
    veh_tipo = Column(String(50))
    veh_anio = Column(Integer)
    veh_color = Column(String(50))
    veh_motor = Column(String(50))
    veh_chasis = Column(String(50))
    veh_estado = Column(String(100))

    personal_policial = Column(Text)                      # JSON list

    raw_extract = Column(Text)                            # JSON completo
    source_filename = Column(String(255))
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    siniestro = relationship("Siniestro", back_populates="police_report")
