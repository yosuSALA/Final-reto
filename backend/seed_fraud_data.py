"""
Generación de Datos Sintéticos Expandidos para hackIAthon.
Crea ~60 siniestros, pólizas, asegurados, vehículos y documentos.
"""
import random
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models import (
    AseguradoSintetico, Poliza, Vehiculo, Documento, Siniestro,
    Workshop, Invoice, InvoiceItem, Ramo, Cobertura, EstadoSiniestro
)
from backend.fraud_scoring import update_siniestro_fraud_data

def seed_fraud_data(db: Session):
    # Evitar doble ejecución
    if db.query(AseguradoSintetico).count() > 0:
        print("Datos sintéticos ya existen en la base de datos.")
        return

    print("Iniciando generación de datos sintéticos (60+ siniestros)...")
    
    # 1. Asegurados
    # Necesitamos incluir los 5 originales y añadir otros 15
    asegurados_data = [
        {"id": "Carlos Mendoza", "nombre": "Carlos Mendoza", "segmento": "VIP", "antiguedad": 8, "ciudad": "Guayaquil", "n_polizas": 3, "reclamos_12m": 1, "mora": 0, "score": 95.0},
        {"id": "Maria Fernanda Lopez", "nombre": "María Fernanda López", "segmento": "Estándar", "antiguedad": 3, "ciudad": "Guayaquil", "n_polizas": 1, "reclamos_12m": 0, "mora": 0, "score": 88.0},
        {"id": "Roberto Andrade", "nombre": "Roberto Andrade", "segmento": "Estándar", "antiguedad": 1, "ciudad": "Quito", "n_polizas": 2, "reclamos_12m": 2, "mora": 0, "score": 75.0},
        {"id": "Andrea Villavicencio", "nombre": "Andrea Villavicencio", "segmento": "VIP", "antiguedad": 5, "ciudad": "Guayaquil", "n_polizas": 2, "reclamos_12m": 1, "mora": 0, "score": 92.0},
        {"id": "Jorge Parrales", "nombre": "Jorge Parrales", "segmento": "Básico", "antiguedad": 2, "ciudad": "Manta", "n_polizas": 1, "reclamos_12m": 1, "mora": 0, "score": 80.0},
        # Nuevos
        {"id": "ASEG-006", "nombre": "Juan Pérez", "segmento": "Básico", "antiguedad": 0, "ciudad": "Quito", "n_polizas": 1, "reclamos_12m": 4, "mora": 1, "score": 40.0}, # Sospechoso, mora, alta frec, nuevo
        {"id": "ASEG-007", "nombre": "Diana Salazar", "segmento": "VIP", "antiguedad": 10, "ciudad": "Quito", "n_polizas": 4, "reclamos_12m": 0, "mora": 0, "score": 98.0},
        {"id": "ASEG-008", "nombre": "Gisella Noboa", "segmento": "Estándar", "antiguedad": 4, "ciudad": "Cuenca", "n_polizas": 1, "reclamos_12m": 1, "mora": 0, "score": 85.0},
        {"id": "ASEG-009", "nombre": "Ricardo Torres", "segmento": "Básico", "antiguedad": 1, "ciudad": "Guayaquil", "n_polizas": 2, "reclamos_12m": 3, "mora": 0, "score": 62.0},
        {"id": "ASEG-010", "nombre": "Pedro Falconi", "segmento": "Estándar", "antiguedad": 2, "ciudad": "Ambato", "n_polizas": 1, "reclamos_12m": 0, "mora": 0, "score": 90.0},
        {"id": "ASEG-011", "nombre": "Valeria Castro", "segmento": "Estándar", "antiguedad": 6, "ciudad": "Quito", "n_polizas": 3, "reclamos_12m": 5, "mora": 0, "score": 50.0}, # Alta frecuencia
        {"id": "ASEG-012", "nombre": "Luis Chiriboga", "segmento": "VIP", "antiguedad": 7, "ciudad": "Guayaquil", "n_polizas": 2, "reclamos_12m": 0, "mora": 0, "score": 95.0},
        {"id": "ASEG-013", "nombre": "Carmen Espinoza", "segmento": "Básico", "antiguedad": 3, "ciudad": "Machala", "n_polizas": 1, "reclamos_12m": 1, "mora": 0, "score": 85.0},
        {"id": "ASEG-014", "nombre": "Santiago Cevallos", "segmento": "Estándar", "antiguedad": 1, "ciudad": "Loja", "n_polizas": 1, "reclamos_12m": 2, "mora": 0, "score": 78.0},
        {"id": "ASEG-015", "nombre": "Gabriela Pazmiño", "segmento": "Estándar", "antiguedad": 5, "ciudad": "Santo Domingo", "n_polizas": 2, "reclamos_12m": 0, "mora": 0, "score": 92.0},
        {"id": "ASEG-016", "nombre": "Mauricio Gomez", "segmento": "VIP", "antiguedad": 9, "ciudad": "Cuenca", "n_polizas": 3, "reclamos_12m": 0, "mora": 0, "score": 99.0},
        {"id": "ASEG-017", "nombre": "Olga Moncayo", "segmento": "Básico", "antiguedad": 0, "ciudad": "Portoviejo", "n_polizas": 1, "reclamos_12m": 3, "mora": 1, "score": 45.0}, # Sospechosa
    ]

    asegurados_map = {}
    for data in asegurados_data:
        aseg = AseguradoSintetico(
            id_asegurado=data["id"],
            nombre=data["nombre"],
            segmento=data["segmento"],
            antiguedad=data["antiguedad"],
            ciudad=data["ciudad"],
            numero_polizas=data["n_polizas"],
            reclamos_12m=data["reclamos_12m"],
            mora_actual=data["mora"],
            score_cliente_simulado=data["score"]
        )
        db.add(aseg)
        asegurados_map[data["id"]] = aseg
    db.flush()

    # 2. Pólizas
    # Pólizas de los 5 originales y otras 20
    now = datetime.utcnow()
    polizas_data = [
        {"id": "POL-50001", "aseg": "Carlos Mendoza", "ramo": Ramo.VEHICULOS, "inicio": now - timedelta(days=200), "fin": now + timedelta(days=165), "prima": 850.0, "suma": 25000.0, "deducible": 250.0, "canal": "Asesor", "ciudad": "Guayaquil", "estado": "Vigente"},
        {"id": "POL-50002", "aseg": "Maria Fernanda Lopez", "ramo": Ramo.VEHICULOS, "inicio": now - timedelta(days=150), "fin": now + timedelta(days=215), "prima": 720.0, "suma": 18000.0, "deducible": 200.0, "canal": "Web", "ciudad": "Guayaquil", "estado": "Vigente"},
        {"id": "POL-50003", "aseg": "Roberto Andrade", "ramo": Ramo.VEHICULOS, "inicio": now - timedelta(days=50), "fin": now + timedelta(days=315), "prima": 900.0, "suma": 30000.0, "deducible": 300.0, "canal": "Agencia", "ciudad": "Quito", "estado": "Vigente"},
        {"id": "POL-50004", "aseg": "Andrea Villavicencio", "ramo": Ramo.VEHICULOS, "inicio": now - timedelta(days=300), "fin": now + timedelta(days=65), "prima": 1100.0, "suma": 45000.0, "deducible": 450.0, "canal": "Asesor", "ciudad": "Guayaquil", "estado": "Vigente"},
        {"id": "POL-50005", "aseg": "Jorge Parrales", "ramo": Ramo.VEHICULOS, "inicio": now - timedelta(days=100), "fin": now + timedelta(days=265), "prima": 600.0, "suma": 14000.0, "deducible": 150.0, "canal": "Banco", "ciudad": "Manta", "estado": "Vigente"},
        
        # Pólizas nuevas con variedad de ramos y algunas con vigencia crítica (borde de inicio/fin)
        {"id": "POL-50006", "aseg": "ASEG-006", "ramo": Ramo.VEHICULOS, "inicio": now - timedelta(days=5), "fin": now + timedelta(days=360), "prima": 950.0, "suma": 22000.0, "deducible": 250.0, "canal": "Web", "ciudad": "Quito", "estado": "Vigente"}, # Vigencia crítica inicial
        {"id": "POL-50007", "aseg": "ASEG-007", "ramo": Ramo.SALUD, "inicio": now - timedelta(days=180), "fin": now + timedelta(days=185), "prima": 1500.0, "suma": 100000.0, "deducible": 100.0, "canal": "Asesor", "ciudad": "Quito", "estado": "Vigente"},
        {"id": "POL-50008", "aseg": "ASEG-008", "ramo": Ramo.VIDA, "inicio": now - timedelta(days=340), "fin": now + timedelta(days=25), "prima": 400.0, "suma": 50000.0, "deducible": 0.0, "canal": "Banco", "ciudad": "Cuenca", "estado": "Vigente"},
        {"id": "POL-50009", "aseg": "ASEG-009", "ramo": Ramo.VEHICULOS, "inicio": now - timedelta(days=360), "fin": now - timedelta(days=5), "prima": 800.0, "suma": 19000.0, "deducible": 200.0, "canal": "Web", "ciudad": "Guayaquil", "estado": "Vigente"}, # Vigencia crítica final (y vencida hace 5 días)
        {"id": "POL-50010", "aseg": "ASEG-010", "ramo": Ramo.HOGAR, "inicio": now - timedelta(days=80), "fin": now + timedelta(days=285), "prima": 350.0, "suma": 60000.0, "deducible": 500.0, "canal": "Asesor", "ciudad": "Ambato", "estado": "Vigente"},
        {"id": "POL-50011", "aseg": "ASEG-011", "ramo": Ramo.VEHICULOS, "inicio": now - timedelta(days=250), "fin": now + timedelta(days=115), "prima": 1200.0, "suma": 35000.0, "deducible": 350.0, "canal": "Agencia", "ciudad": "Quito", "estado": "Vigente"},
        {"id": "POL-50012", "aseg": "ASEG-012", "ramo": Ramo.SALUD, "inicio": now - timedelta(days=300), "fin": now + timedelta(days=65), "prima": 2500.0, "suma": 200000.0, "deducible": 200.0, "canal": "Asesor", "ciudad": "Guayaquil", "estado": "Vigente"},
        {"id": "POL-50013", "aseg": "ASEG-013", "ramo": Ramo.GENERALES, "inicio": now - timedelta(days=40), "fin": now + timedelta(days=325), "prima": 500.0, "suma": 15000.0, "deducible": 150.0, "canal": "Banco", "ciudad": "Machala", "estado": "Vigente"},
        {"id": "POL-50014", "aseg": "ASEG-014", "ramo": Ramo.VEHICULOS, "inicio": now - timedelta(days=120), "fin": now + timedelta(days=245), "prima": 700.0, "suma": 16000.0, "deducible": 200.0, "canal": "Web", "ciudad": "Loja", "estado": "Vigente"},
        {"id": "POL-50015", "aseg": "ASEG-015", "ramo": Ramo.HOGAR, "inicio": now - timedelta(days=15), "fin": now + timedelta(days=350), "prima": 450.0, "suma": 80000.0, "deducible": 400.0, "canal": "Web", "ciudad": "Santo Domingo", "estado": "Vigente"},
        {"id": "POL-50016", "aseg": "ASEG-016", "ramo": Ramo.VEHICULOS, "inicio": now - timedelta(days=150), "fin": now + timedelta(days=215), "prima": 1050.0, "suma": 28000.0, "deducible": 250.0, "canal": "Asesor", "ciudad": "Cuenca", "estado": "Vigente"},
        {"id": "POL-50017", "aseg": "ASEG-017", "ramo": Ramo.VEHICULOS, "inicio": now - timedelta(days=3), "fin": now + timedelta(days=362), "prima": 850.0, "suma": 20000.0, "deducible": 200.0, "canal": "Web", "ciudad": "Portoviejo", "estado": "Vigente"}, # Borde vigencia inicial
        {"id": "POL-50018", "aseg": "Carlos Mendoza", "ramo": Ramo.SALUD, "inicio": now - timedelta(days=100), "fin": now + timedelta(days=265), "prima": 1800.0, "suma": 50000.0, "deducible": 50.0, "canal": "Asesor", "ciudad": "Guayaquil", "estado": "Vigente"},
        {"id": "POL-50019", "aseg": "Andrea Villavicencio", "ramo": Ramo.HOGAR, "inicio": now - timedelta(days=180), "fin": now + timedelta(days=185), "prima": 400.0, "suma": 120000.0, "deducible": 500.0, "canal": "Asesor", "ciudad": "Guayaquil", "estado": "Vigente"},
        {"id": "POL-50020", "aseg": "ASEG-007", "ramo": Ramo.VEHICULOS, "inicio": now - timedelta(days=200), "fin": now + timedelta(days=165), "prima": 980.0, "suma": 24000.0, "deducible": 250.0, "canal": "Asesor", "ciudad": "Quito", "estado": "Vigente"},
    ]

    polizas_map = {}
    for p_data in polizas_data:
        pol = Poliza(
            id_poliza=p_data["id"],
            id_asegurado=p_data["aseg"],
            ramo=p_data["ramo"],
            fecha_inicio=p_data["inicio"],
            fecha_fin=p_data["fin"],
            prima=p_data["prima"],
            suma_asegurada=p_data["suma"],
            deducible=p_data["deducible"],
            canal_venta=p_data["canal"],
            ciudad=p_data["ciudad"],
            estado_poliza=p_data["estado"]
        )
        db.add(pol)
        polizas_map[p_data["id"]] = pol
    db.flush()

    # 3. Vehículos
    # Generamos vehículos para las pólizas del ramo VEHICULOS
    vehiculos_data = [
        {"pol": "POL-50001", "placa": "GBA-2481", "chasis": "93HB49204A81283", "motor": "M16A-128392", "marca": "Chevrolet", "modelo": "Sail", "anio": 2018},
        {"pol": "POL-50002", "placa": "GCE-9345", "chasis": "8A2H84920D92301", "motor": "K14B-481923", "marca": "Suzuki", "modelo": "Grand Vitara", "anio": 2017},
        {"pol": "POL-50003", "placa": "PBA-1092", "chasis": "KL4AG48102B9041", "motor": "A15D-190412", "marca": "Kia", "modelo": "Rio", "anio": 2020},
        {"pol": "POL-50004", "placa": "GDT-7734", "chasis": "1HGCR2F82H39420", "motor": "R20A-829402", "marca": "Honda", "modelo": "Civic", "anio": 2019},
        {"pol": "POL-50005", "placa": "MBA-8821", "chasis": "8AG248920C81932", "motor": "M13A-938210", "marca": "Chevrolet", "modelo": "Spark", "anio": 2015},
        
        {"pol": "POL-50006", "placa": "PBZ-3498", "chasis": "KL4AG2819C82390", "motor": "A15D-928394", "marca": "Kia", "modelo": "Soluto", "anio": 2021},
        {"pol": "POL-50009", "placa": "GCE-1123", "chasis": "93HB49204A81903", "motor": "M16A-829392", "marca": "Chevrolet", "modelo": "Sail", "anio": 2016},
        {"pol": "POL-50011", "placa": "PCY-8843", "chasis": "JTMDU4203K98293", "motor": "2TR-7829103", "marca": "Toyota", "modelo": "Fortuner", "anio": 2018},
        {"pol": "POL-50014", "placa": "LBA-4532", "chasis": "1HGB48192C92831", "motor": "R18A-293819", "marca": "Honda", "modelo": "Fit", "anio": 2014},
        {"pol": "POL-50016", "placa": "ABA-9921", "chasis": "8AG482930D98392", "motor": "K12M-983210", "marca": "Suzuki", "modelo": "Swift", "anio": 2019},
        {"pol": "POL-50017", "placa": "PBY-9382", "chasis": "KL4AG2910D92389", "motor": "A15D-829381", "marca": "Kia", "modelo": "Cerato", "anio": 2022},
        {"pol": "POL-50020", "placa": "PBW-7711", "chasis": "JTMDU4203K98109", "motor": "2TR-9283910", "marca": "Toyota", "modelo": "Hilux", "anio": 2020},
    ]

    vehiculos_map = {}
    for v_data in vehiculos_data:
        veh = Vehiculo(
            id_poliza=v_data["pol"],
            placa=v_data["placa"],
            chasis=v_data["chasis"],
            motor=v_data["motor"],
            marca=v_data["marca"],
            modelo=v_data["modelo"],
            anio=v_data["anio"]
        )
        db.add(veh)
        vehiculos_map[v_data["pol"]] = veh
    db.flush()

    # Vincular los 5 siniestros originales a sus vehículos y pólizas
    original_siniestros = db.query(Siniestro).order_by(Siniestro.id_siniestro).all()
    for s in original_siniestros:
        if s.id_poliza in vehiculos_map:
            s.vehiculo_id = vehiculos_map[s.id_poliza].id
    db.flush()

    # 4. Generar 55+ siniestros adicionales (para llegar a 60+ en total)
    sucursales = ["Guayaquil", "Quito", "Cuenca", "Manta", "Ambato", "Machala", "Loja", "Santo Domingo", "Portoviejo"]
    descripciones_limpias = [
        "Roce lateral leve al salir del garaje.",
        "Despiste menor por calzada mojada en circunvalación.",
        "Frenada brusca del auto delantero ocasiona impacto posterior leve.",
        "Choque frontal leve en parqueadero comercial.",
        "Rotura de faro posterior izquierdo al retroceder en calle estrecha.",
        "Asegurado refiere que al regresar a su vehículo estacionado encontró el retrovisor roto.",
        "Daño menor en guardachoque delantero por impacto de piedra en carretera.",
        "Asegurado refiere golpe leve en puerta del copiloto al abrirla contra un pilar.",
        "Colisión trasera de baja intensidad en semáforo en rojo.",
        "Raspones en lateral izquierdo al esquivar perro en zona urbana."
    ]

    talleres = db.query(Workshop).all()
    
    # Vamos a crear 55 nuevos siniestros con varios perfiles:
    # - 10 con alertas rojas (claros patrones de fraude plantados)
    # - 15 con alertas amarillas (dudas razonables, documentos incompletos, reporte levemente tardío)
    # - 30 limpios (alertas verdes)

    total_claims_to_add = 55
    added_claims = []

    for i in range(total_claims_to_add):
        claim_num = i + 6
        # Seleccionar póliza aleatoria
        pol_id = random.choice(list(polizas_map.keys()))
        pol = polizas_map[pol_id]
        
        # Determinar perfil de fraude
        # i de 0 a 9 -> ROJO (Fraude sospechoso)
        # i de 10 a 24 -> AMARILLO (Sospechoso leve / irregular)
        # i >= 25 -> VERDE (Limpio)
        
        monto_reclamado = round(random.uniform(300.0, 4500.0), 2)
        monto_estimado = round(monto_reclamado * random.uniform(0.85, 0.95), 2)
        
        fecha_ocurrencia = now - timedelta(days=random.randint(10, 180))
        fecha_reporte = fecha_ocurrencia + timedelta(days=random.randint(0, 3))
        
        # Ajustes basados en ramo y cobertura
        cobertura = random.choice([Cobertura.CHOQUE, Cobertura.DANIO, Cobertura.OTRO])
        if pol.ramo == Ramo.VEHICULOS:
            vehiculo_id = vehiculos_map[pol_id].id if pol_id in vehiculos_map else None
        else:
            vehiculo_id = None
            cobertura = Cobertura.ATENCION_MEDICA if pol.ramo == Ramo.SALUD else Cobertura.OTRO

        descripcion = random.choice(descripciones_limpias)
        beneficiario = None
        doc_completos = 1

        # Plantar patrones específicos para alertas ROJAS (0 a 9)
        if i < 10:
            if i == 0:
                # Patrón 1: Borde de vigencia extremo (ocurre 1 día después de iniciar)
                fecha_ocurrencia = pol.fecha_inicio + timedelta(days=1)
                fecha_reporte = fecha_ocurrencia + timedelta(days=1)
                descripcion = "Choque frontal severo contra objeto fijo en vía periférica. Vehículo pierde control."
                monto_reclamado = pol.suma_asegurada * 0.92 # Monto muy alto
            elif i == 1:
                # Patrón 2: Denuncia de robo reportada muy tarde (8 días después)
                cobertura = Cobertura.ROBO
                fecha_ocurrencia = now - timedelta(days=45)
                fecha_reporte = fecha_ocurrencia + timedelta(days=9)
                descripcion = "Robo total del vehículo estacionado fuera de domicilio por la noche."
                monto_reclamado = pol.suma_asegurada * 0.85
            elif i == 2:
                # Patrón 3: Asegurado con alta frecuencia de siniestros
                pol = polizas_map["POL-50006"] # Vinculado a ASEG-006 (Juan Pérez, reclamos_12m: 4, en mora)
                fecha_ocurrencia = now - timedelta(days=10)
                fecha_reporte = fecha_ocurrencia + timedelta(days=1)
                descripcion = "Choque trasero de gran impacto contra poste. Conductor alterno no familiarizado."
            elif i == 3:
                # Patrón 4: Beneficiario recurrente y cruce de pólizas
                beneficiario = "Importadora Autopartes Express"
                descripcion = "Colisión en intersección sin tercero identificado. Daño total en suspensión y capó."
            elif i == 4:
                # Patrón 5: Dinámica sospechosa (madrugada, sin testigos, lugar despoblado)
                descripcion = "El incidente ocurrió a las 3:30 AM en una vía solitaria de Guayaquil. Pérdida de control del vehículo sin intervención de otro auto y sin testigos presenciales."
                cobertura = Cobertura.DANIO
            elif i == 5:
                # Patrón 6: Eventos repetitivos del mismo vehículo
                pol = polizas_map["POL-50003"] # Roberto Andrade (frecuencia alta)
                fecha_ocurrencia = now - timedelta(days=12)
                fecha_reporte = fecha_ocurrencia
                descripcion = "Colisión contra pilar en parqueadero subterráneo. Guardachoque destrozado."
            elif i == 6:
                # Patrón 7: Narrativa coincidente (Copia semántica de patrón 4)
                beneficiario = "Importadora Autopartes Express"
                descripcion = "Colisión en intersección sin tercero identificado. Daño total en suspensión y capó."
            elif i == 7:
                # Patrón 8: Monto reclamado excesivamente cercano a suma asegurada
                monto_reclamado = pol.suma_asegurada * 0.98
                descripcion = "Asegurado reclama destrucción total de equipo electrónico residencial por fluctuación eléctrica extrema."
            elif i == 8:
                # Patrón 9: Siniestro fuera de vigencia de póliza (RF02 fallido)
                pol = polizas_map["POL-50009"] # Vencida hace 5 días
                fecha_ocurrencia = now - timedelta(days=2) # Ocurrió hace 2 días (después del vencimiento)
                fecha_reporte = now
                descripcion = "Accidente menor en avenida de Guayaquil. Choque por alcance trasero."
            elif i == 9:
                # Patrón 10: Ramo inconsistente (RF01 fallido)
                pol = polizas_map["POL-50007"] # Ramo SALUD
                cobertura = Cobertura.CHOQUE # Choque de auto en póliza de salud!
                descripcion = "Colisión vehicular. El conductor sufre golpes y daños en vehículo."
                
        # Plantar patrones específicos para alertas AMARILLAS (10 a 24)
        elif i < 25:
            doc_completos = 0
            if i % 3 == 0:
                descripcion = "Reporte del siniestro realizado tarde. Raspadura a lo largo del costado derecho."
                fecha_reporte = fecha_ocurrencia + timedelta(days=22) # Reporte tardío
            elif i % 3 == 1:
                descripcion = "Colisión menor contra objeto fijo (árbol). Guardachoque abollado."
                # Falta algún documento que setearemos más adelante
            else:
                descripcion = "Asegurado con mora de prima menor o reclamo de monto cercano al deducible."
                
        # VERDE (25 a 54): Limpio
        else:
            doc_completos = 1

        claim = Siniestro(
            id_poliza=pol.id_poliza,
            id_asegurado=pol.id_asegurado,
            ramo=pol.ramo,
            cobertura=cobertura,
            fecha_ocurrencia=fecha_ocurrencia,
            fecha_reporte=fecha_reporte,
            monto_reclamado=monto_reclamado,
            monto_estimado=monto_estimado,
            monto_pagado=round(monto_estimado * 0.9, 2) if i >= 25 else 0.0,
            estado=EstadoSiniestro.LIQUIDADO if i >= 25 else EstadoSiniestro.RESERVA,
            sucursal=random.choice(sucursales),
            descripcion=descripcion,
            documentos_completos=doc_completos,
            beneficiario=beneficiario,
            dias_desde_inicio_poliza=(fecha_ocurrencia - pol.fecha_inicio).days if fecha_ocurrencia else 0,
            dias_desde_fin_poliza=(pol.fecha_fin - fecha_ocurrencia).days if fecha_ocurrencia else 0,
            dias_entre_ocurrencia_reporte=(fecha_reporte - fecha_ocurrencia).days if fecha_ocurrencia and fecha_reporte else 0,
            historial_siniestros_asegurado=db.query(AseguradoSintetico).filter(AseguradoSintetico.id_asegurado == pol.id_asegurado).first().reclamos_12m,
            etiqueta_fraude_simulada=1 if i < 10 else 0,
            vehiculo_id=vehiculo_id
        )
        db.add(claim)
        added_claims.append((claim, i))
    
    db.flush()

    # 5. Generar Documentos
    # Para cada uno de los 60 siniestros, generamos su set de documentos
    todos_siniestros = db.query(Siniestro).all()
    tipos_documentos = ["Cédula", "Licencia", "Denuncia", "Presupuesto"]
    
    for s in todos_siniestros:
        # Si es un caso amarillo/rojo con documentos incompletos, omitiremos alguno
        is_missing_docs = s.documentos_completos == 0
        
        # Para el siniestro fuera de vigencia o ramo inválido
        for td in tipos_documentos:
            if is_missing_docs and td == "Denuncia" and random.random() > 0.4:
                # Omitir Denuncia para simular doc incompleto
                continue
                
            # Simular ilegibilidad o inconsistencia
            legible = 1
            inconsistencia = 0
            observacion = "Verificado correctamente."
            
            # Plantar inconsistencia extrema en caso i == 3 o i == 6 (inconsistencia doc)
            if s.id_asegurado == "ASEG-006" and td == "Presupuesto":
                inconsistencia = 1
                observacion = "El presupuesto presenta enmiendas físicas en las fechas de mano de obra."
            elif s.beneficiario == "Importadora Autopartes Express" and td == "Denuncia":
                inconsistencia = 1
                observacion = "Fecha de emisión de la denuncia es anterior a la fecha reportada de ocurrencia."
            elif s.documentos_completos == 0 and td == "Licencia" and random.random() > 0.5:
                legible = 0
                observacion = "La copia digitalizada de la licencia se encuentra borrosa e ilegible."

            doc = Documento(
                id_siniestro=s.id_siniestro,
                tipo_documento=td,
                entregado=1,
                legible=legible,
                fecha_emision=s.fecha_ocurrencia + timedelta(days=1) if s.fecha_ocurrencia else now,
                inconsistencia_detectada=inconsistencia,
                observacion=observacion
            )
            db.add(doc)
    db.flush()

    # 6. Generar Facturas e Invoices para las nuevas reclamaciones
    # Crearemos facturas para algunos de los reclamos agregados para que aparezcan en la cola
    # De los 55 nuevos, crearemos facturas para unos 20.
    for claim, idx in added_claims:
        if idx % 3 == 0 and claim.ramo == Ramo.VEHICULOS:
            taller = random.choice(talleres)
            subtotal = claim.monto_reclamado / 1.15
            iva = claim.monto_reclamado - subtotal
            
            # Plantar inconsistencia de fecha
            issue_date = claim.fecha_ocurrencia + timedelta(days=4)
            if idx == 0:
                # Factura emitida ANTES del siniestro
                issue_date = claim.fecha_ocurrencia - timedelta(days=2)
                
            inv = Invoice(
                invoice_number=f"001-003-{100000 + idx}",
                siniestro_id=claim.id_siniestro,
                workshop_id=taller.id,
                issue_date=issue_date,
                subtotal=round(subtotal, 2),
                iva=round(iva, 2),
                total=claim.monto_reclamado,
                raw_data=json.dumps({"items": []}),
                is_test=0
            )
            db.add(inv)
            db.flush()
            
            # Agregar ítems de la factura
            db.add_all([
                InvoiceItem(
                    invoice_id=inv.id,
                    code="REP-GUA01",
                    description="Guardachoque delantero",
                    category="repuesto",
                    quantity=1.0,
                    unit_price=round(subtotal * 0.6, 2),
                    total_price=round(subtotal * 0.6, 2)
                ),
                InvoiceItem(
                    invoice_id=inv.id,
                    code="MO-LAM01",
                    description="Mano de obra latoneria (hora)",
                    category="mano_obra",
                    quantity=8.0,
                    unit_price=round((subtotal * 0.4) / 8.0, 2),
                    total_price=round(subtotal * 0.4, 2)
                )
            ])
    db.flush()

    # 7. Calcular y persistir fraud score para todos los siniestros (incluyendo los 5 iniciales)
    print("Calculando scores de fraude para todos los registros...")
    siniestros_con_score = db.query(Siniestro).all()
    for s in siniestros_con_score:
        update_siniestro_fraud_data(s, db)

    db.commit()
    print(f"Seeding de fraude completado exitosamente. Total siniestros en BD: {db.query(Siniestro).count()}")
