"""
Tests unitarios para el motor de scoring de fraude y reglas de negocio.
"""
import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import (
    Siniestro, Poliza, AseguradoSintetico, Vehiculo, Documento, Ramo, Cobertura, EstadoSiniestro
)
from backend.fraud_scoring import evaluate_fraud_scoring

class TestFraudRules(unittest.TestCase):
    def setUp(self):
        # Crear base de datos SQLite en memoria para pruebas
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
        
        # Generar registros básicos de prueba
        self.now = datetime.utcnow()
        
        self.asegurado = AseguradoSintetico(
            id_asegurado="ASEG-TEST",
            nombre="Juan Prueba",
            segmento="Estándar",
            antiguedad=2,
            ciudad="Quito",
            numero_polizas=1,
            reclamos_12m=0,
            mora_actual=0,
            score_cliente_simulado=100.0
        )
        self.db.add(self.asegurado)
        
        self.poliza = Poliza(
            id_poliza="POL-TEST",
            id_asegurado="ASEG-TEST",
            ramo=Ramo.VEHICULOS,
            fecha_inicio=self.now - timedelta(days=100),
            fecha_fin=self.now + timedelta(days=265),
            prima=500.0,
            suma_asegurada=15000.0,
            deducible=200.0,
            canal_venta="Web",
            ciudad="Quito",
            estado_poliza="Vigente"
        )
        self.db.add(self.poliza)
        self.db.flush()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_rule_rf01_mismatch_ramo(self):
        """Verifica que RF01 falle si el ramo del siniestro no corresponde con el de la póliza."""
        siniestro = Siniestro(
            id_poliza="POL-TEST",
            id_asegurado="ASEG-TEST",
            ramo=Ramo.SALUD, # Mismatch: póliza es de VEHICULOS
            cobertura=Cobertura.CHOQUE,
            fecha_ocurrencia=self.now - timedelta(days=10),
            fecha_reporte=self.now - timedelta(days=9),
            monto_reclamado=500.0,
            estado=EstadoSiniestro.RESERVA,
            descripcion="Reclamo médico de prueba"
        )
        self.db.add(siniestro)
        self.db.flush()
        
        res = evaluate_fraud_scoring(siniestro, self.db)
        rf01 = next(r for r in res["rules"] if r["id"] == "RF01")
        
        self.assertFalse(rf01["passed"])
        self.assertIn("Inconsistencia de Ramo", rf01["message"])
        self.assertGreaterEqual(res["score"], 85.0) # Rojo forzado

    def test_rule_rf02_out_of_vigencia(self):
        """Verifica que RF02 falle si el siniestro ocurre fuera del rango de vigencia."""
        siniestro = Siniestro(
            id_poliza="POL-TEST",
            id_asegurado="ASEG-TEST",
            ramo=Ramo.VEHICULOS,
            cobertura=Cobertura.CHOQUE,
            fecha_ocurrencia=self.now - timedelta(days=150), # Fuera de vigencia (inició hace 100 días)
            fecha_reporte=self.now - timedelta(days=9),
            monto_reclamado=500.0,
            estado=EstadoSiniestro.RESERVA,
            descripcion="Choque menor de prueba"
        )
        self.db.add(siniestro)
        self.db.flush()
        
        res = evaluate_fraud_scoring(siniestro, self.db)
        rf02 = next(r for r in res["rules"] if r["id"] == "RF02")
        
        self.assertFalse(rf02["passed"])
        self.assertIn("Siniestro fuera de vigencia", rf02["message"])
        self.assertGreaterEqual(res["score"], 85.0) # Rojo forzado

    def test_signal_s01_borde_vigencia(self):
        """Verifica que se active S01 si ocurre cerca del borde de vigencia."""
        # Configurar siniestro a los 5 días de iniciada la póliza
        siniestro = Siniestro(
            id_poliza="POL-TEST",
            id_asegurado="ASEG-TEST",
            ramo=Ramo.VEHICULOS,
            cobertura=Cobertura.CHOQUE,
            fecha_ocurrencia=self.poliza.fecha_inicio + timedelta(days=5),
            fecha_reporte=self.poliza.fecha_inicio + timedelta(days=6),
            monto_reclamado=500.0,
            estado=EstadoSiniestro.RESERVA,
            descripcion="Choque menor a los 5 días de iniciar"
        )
        self.db.add(siniestro)
        self.db.flush() # Populate id_siniestro
        
        # Añadir documentos básicos requeridos para que no fallen otras reglas
        for doc_type in ["Cédula", "Licencia", "Denuncia", "Presupuesto"]:
            self.db.add(Documento(
                id_siniestro=siniestro.id_siniestro,
                tipo_documento=doc_type,
                entregado=1,
                legible=1
            ))
        self.db.flush()
        
        res = evaluate_fraud_scoring(siniestro, self.db)
        s01 = next((ind for ind in res["indicators"] if ind["code"] == "S01"), None)
        
        self.assertIsNotNone(s01)
        self.assertEqual(s01["points"], 8)

if __name__ == "__main__":
    unittest.main()
