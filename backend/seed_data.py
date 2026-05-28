"""
Datos demo realistas para presentacion del hackathon.
Incluye talleres, tarifario, siniestros y facturas con anomalias plantadas.
Todos los datos se crean bajo el perfil por defecto (DEFAULT_PROFILE_ID).
"""
import json
from datetime import datetime, timedelta
from backend.database import SessionLocal, init_db, DEFAULT_PROFILE_ID
from backend.models import (
    Workshop, Siniestro, Invoice, InvoiceItem, TariffItem,
    Ramo, Cobertura, EstadoSiniestro
)

PID = DEFAULT_PROFILE_ID


def seed_database():
    init_db()
    db = SessionLocal()

    # --- TALLERES ---
    if db.query(Workshop).filter(Workshop.profile_id == PID).count() == 0:
        workshops = [
            Workshop(profile_id=PID, name="AutoFix S.A.", ruc="0992847561001", address="Av. Juan Tanca Marengo Km 4.5, Guayaquil", phone="04-2345678", email="contacto@autofix.demo.ec", notify_automatically=1),
            Workshop(profile_id=PID, name="TallerPro Cia. Ltda.", ruc="0991234567001", address="Cdla. Kennedy Norte, Guayaquil", phone="04-3456789", email="gerencia@tallerpro.demo.ec", notify_automatically=1),
            Workshop(profile_id=PID, name="CarGlass Ecuador", ruc="0990987654001", address="Via Daule Km 10, Guayaquil", phone="04-4567890", email="info@carglass.demo.ec", notify_automatically=0),
        ]
        db.add_all(workshops)
        db.flush()
    else:
        workshops = db.query(Workshop).filter(Workshop.profile_id == PID).order_by(Workshop.id).all()

    # --- TARIFARIO ---
    if db.query(TariffItem).filter(TariffItem.profile_id == PID).count() == 0:
        tariff_items = [
            TariffItem(profile_id=PID, code="REP-PAR01", description="Parabrisas delantero", category="repuesto", max_price=280.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=1, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(profile_id=PID, code="REP-PAR02", description="Parabrisas trasero", category="repuesto", max_price=220.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=1, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="REP-FAR01", description="Faro delantero (unidad)", category="repuesto", max_price=150.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=2, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="REP-FAR02", description="Faro trasero (unidad)", category="repuesto", max_price=120.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=2, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="REP-GUA01", description="Guardachoque delantero", category="repuesto", max_price=350.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=1, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="REP-GUA02", description="Guardachoque trasero", category="repuesto", max_price=320.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=1, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="REP-PUE01", description="Puerta lateral (unidad)", category="repuesto", max_price=450.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=2, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="REP-CAP01", description="Capo delantero", category="repuesto", max_price=380.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=1, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="REP-ESP01", description="Espejo retrovisor (unidad)", category="repuesto", max_price=85.00, tolerance_pct=15, expected_qty_min=1, expected_qty_max=2, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="REP-RAD01", description="Radiador", category="repuesto", max_price=200.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=1, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="REP-MOT01", description="Soporte de motor", category="repuesto", max_price=180.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=2, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="PIN-BASE01", description="Pintura base (galon)", category="pintura", max_price=45.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=2, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="PIN-ACAB01", description="Pintura acabado (galon)", category="pintura", max_price=65.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=2, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="PIN-TRAN01", description="Pintura transparente (galon)", category="pintura", max_price=55.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=2, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="MAT-LIJ01", description="Kit lijas y masilla", category="material", max_price=35.00, tolerance_pct=15, expected_qty_min=1, expected_qty_max=3, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="MAT-SOL01", description="Soldadura y materiales", category="material", max_price=60.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=2, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="MO-MEC01", description="Mano de obra mecanica (hora)", category="mano_obra", max_price=25.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=20, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="MO-PIN01", description="Mano de obra pintura (hora)", category="mano_obra", max_price=22.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=15, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="MO-ELE01", description="Mano de obra electrica (hora)", category="mano_obra", max_price=30.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=10, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="MO-LAM01", description="Mano de obra latoneria (hora)", category="mano_obra", max_price=28.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=20, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="SRV-GRU01", description="Servicio de grua", category="servicio", max_price=80.00, tolerance_pct=15, expected_qty_min=1, expected_qty_max=1, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="SRV-ALI01", description="Alineacion y balanceo", category="servicio", max_price=40.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=1, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="REP-VID01", description="Vidrio ventana lateral", category="repuesto", max_price=120.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=2, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="REP-CER01", description="Cerradura puerta", category="repuesto", max_price=65.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=4, applicable_claim_types=json.dumps(["Vehículos"])),
            TariffItem(code="REP-RAD02", description="Radio/Consola", category="repuesto", max_price=250.00, tolerance_pct=10, expected_qty_min=1, expected_qty_max=1, applicable_claim_types=json.dumps(["Vehículos"])),
        ]
        db.add_all(tariff_items)
        db.flush()

    # ── Seed de datos de fraude (Asegurados, Pólizas, Vehículos, Documentos, +60 siniestros) ──
    # DEBE ejecutarse ANTES de crear los 5 siniestros originales para respetar FKs
    from backend.seed_fraud_data import seed_fraud_data
    seed_fraud_data(db)
    db.close()
    return

    now = datetime.utcnow()
    # --- SINIESTRO 1: Limpio ---
    c1 = Siniestro(
        id_poliza="POL-50001", id_asegurado="Carlos Mendoza",
        ramo=Ramo.VEHICULOS, cobertura=Cobertura.CHOQUE,
        fecha_ocurrencia=now - timedelta(days=15), fecha_reporte=now - timedelta(days=14),
        monto_reclamado=787.75, estado=EstadoSiniestro.RESERVA,
        sucursal="Guayaquil", descripcion="Choque frontal leve en interseccion",
    )
    db.add(c1)
    db.flush()
    inv1 = Invoice(invoice_number="001-001-000045", siniestro_id=c1.id_siniestro, workshop_id=workshops[0].id, issue_date=now - timedelta(days=10), subtotal=685.00, iva=102.75, total=787.75)
    db.add(inv1)
    db.flush()
    db.add_all([
        InvoiceItem(invoice_id=inv1.id, code="REP-GUA01", description="Guardachoque delantero", category="repuesto", quantity=1, unit_price=340.00, total_price=340.00),
        InvoiceItem(invoice_id=inv1.id, code="REP-FAR01", description="Faro delantero (unidad)", category="repuesto", quantity=1, unit_price=145.00, total_price=145.00),
        InvoiceItem(invoice_id=inv1.id, code="MO-MEC01", description="Mano de obra mecanica (hora)", category="mano_obra", quantity=8, unit_price=25.00, total_price=200.00),
    ])
    # --- SINIESTRO 2: Sobrecobro mano de obra ---
    c2 = Siniestro(
        id_poliza="POL-50002", id_asegurado="Maria Fernanda Lopez",
        ramo=Ramo.VEHICULOS, cobertura=Cobertura.ROBO,
        fecha_ocurrencia=now - timedelta(days=12), fecha_reporte=now - timedelta(days=11),
        monto_reclamado=796.38, estado=EstadoSiniestro.RESERVA,
        sucursal="Guayaquil", descripcion="Robo de accesorios en estacionamiento",
    )
    db.add(c2)
    db.flush()
    inv2 = Invoice(invoice_number="001-002-000123", siniestro_id=c2.id_siniestro, workshop_id=workshops[1].id, issue_date=now - timedelta(days=7), subtotal=692.50, iva=103.88, total=796.38)
    db.add(inv2)
    db.flush()
    db.add_all([
        InvoiceItem(invoice_id=inv2.id, code="REP-ESP01", description="Espejo retrovisor (unidad)", category="repuesto", quantity=2, unit_price=82.00, total_price=164.00),
        InvoiceItem(invoice_id=inv2.id, code="REP-RAD02", description="Radio/Consola", category="repuesto", quantity=1, unit_price=245.00, total_price=245.00),
        InvoiceItem(invoice_id=inv2.id, code="REP-CER01", description="Cerradura puerta", category="repuesto", quantity=2, unit_price=63.00, total_price=126.00),
        InvoiceItem(invoice_id=inv2.id, code="MO-MEC01", description="Mano de obra mecanica (hora)", category="mano_obra", quantity=5, unit_price=33.75, total_price=168.75),
    ])
    # --- SINIESTRO 3: Cobro duplicado parabrisas ---
    c3 = Siniestro(
        id_poliza="POL-50003", id_asegurado="Roberto Andrade",
        ramo=Ramo.VEHICULOS, cobertura=Cobertura.DANIO,
        fecha_ocurrencia=now - timedelta(days=20), fecha_reporte=now - timedelta(days=19),
        monto_reclamado=1014.30, estado=EstadoSiniestro.RESERVA,
        sucursal="Guayaquil", descripcion="Dano por granizo en vehiculo estacionado",
    )
    db.add(c3)
    db.flush()
    inv3 = Invoice(invoice_number="001-003-000067", siniestro_id=c3.id_siniestro, workshop_id=workshops[2].id, issue_date=now - timedelta(days=5), subtotal=882.00, iva=132.30, total=1014.30)
    db.add(inv3)
    db.flush()
    db.add_all([
        InvoiceItem(invoice_id=inv3.id, code="REP-PAR01", description="Parabrisas delantero", category="repuesto", quantity=1, unit_price=275.00, total_price=275.00),
        InvoiceItem(invoice_id=inv3.id, code="REP-PAR01", description="Parabrisas delantero", category="repuesto", quantity=1, unit_price=275.00, total_price=275.00),
        InvoiceItem(invoice_id=inv3.id, code="MO-LAM01", description="Mano de obra latoneria (hora)", category="mano_obra", quantity=6, unit_price=27.00, total_price=162.00),
        InvoiceItem(invoice_id=inv3.id, code="PIN-BASE01", description="Pintura base (galon)", category="pintura", quantity=1, unit_price=42.00, total_price=42.00),
        InvoiceItem(invoice_id=inv3.id, code="MAT-LIJ01", description="Kit lijas y masilla", category="material", quantity=2, unit_price=34.00, total_price=68.00),
    ])
    # --- SINIESTRO 4: Incoherencia (repuesto motor en siniestro de puerta) ---
    c4 = Siniestro(
        id_poliza="POL-50004", id_asegurado="Andrea Villavicencio",
        ramo=Ramo.VEHICULOS, cobertura=Cobertura.CHOQUE,
        fecha_ocurrencia=now - timedelta(days=8), fecha_reporte=now - timedelta(days=7),
        monto_reclamado=1078.70, estado=EstadoSiniestro.RESERVA,
        sucursal="Guayaquil", descripcion="Choque lateral en avenida principal",
    )
    db.add(c4)
    db.flush()
    inv4 = Invoice(invoice_number="001-001-000046", siniestro_id=c4.id_siniestro, workshop_id=workshops[0].id, issue_date=now - timedelta(days=3), subtotal=938.00, iva=140.70, total=1078.70)
    db.add(inv4)
    db.flush()
    db.add_all([
        InvoiceItem(invoice_id=inv4.id, code="REP-PUE01", description="Puerta lateral (unidad)", category="repuesto", quantity=1, unit_price=440.00, total_price=440.00),
        InvoiceItem(invoice_id=inv4.id, code="REP-MOT01", description="Soporte de motor", category="repuesto", quantity=1, unit_price=175.00, total_price=175.00),
        InvoiceItem(invoice_id=inv4.id, code="MO-LAM01", description="Mano de obra latoneria (hora)", category="mano_obra", quantity=8, unit_price=27.00, total_price=216.00),
        InvoiceItem(invoice_id=inv4.id, code="PIN-ACAB01", description="Pintura acabado (galon)", category="pintura", quantity=1, unit_price=62.00, total_price=62.00),
        InvoiceItem(invoice_id=inv4.id, code="MAT-LIJ01", description="Kit lijas y masilla", category="material", quantity=1, unit_price=33.00, total_price=33.00),
    ])
    # --- SINIESTRO 5: Cantidad excesiva pintura ---
    c5 = Siniestro(
        id_poliza="POL-50005", id_asegurado="Jorge Parrales",
        ramo=Ramo.VEHICULOS, cobertura=Cobertura.DANIO,
        fecha_ocurrencia=now - timedelta(days=5), fecha_reporte=now - timedelta(days=4),
        monto_reclamado=548.55, estado=EstadoSiniestro.RESERVA,
        sucursal="Guayaquil", descripcion="Rayon en puerta y guardachoque",
    )
    db.add(c5)
    db.flush()
    inv5 = Invoice(invoice_number="001-002-000124", siniestro_id=c5.id_siniestro, workshop_id=workshops[1].id, issue_date=now - timedelta(days=2), subtotal=477.00, iva=71.55, total=548.55)
    db.add(inv5)
    db.flush()
    db.add_all([
        InvoiceItem(invoice_id=inv5.id, code="PIN-BASE01", description="Pintura base (galon)", category="pintura", quantity=5, unit_price=44.00, total_price=220.00),
        InvoiceItem(invoice_id=inv5.id, code="PIN-ACAB01", description="Pintura acabado (galon)", category="pintura", quantity=1, unit_price=63.00, total_price=63.00),
        InvoiceItem(invoice_id=inv5.id, code="MAT-LIJ01", description="Kit lijas y masilla", category="material", quantity=2, unit_price=32.00, total_price=64.00),
        InvoiceItem(invoice_id=inv5.id, code="MO-PIN01", description="Mano de obra pintura (hora)", category="mano_obra", quantity=6, unit_price=21.00, total_price=126.00),
    ])
    db.commit()
    db.close()
    print("Base de datos inicializada con datos demo.")


if __name__ == "__main__":
    seed_database()
