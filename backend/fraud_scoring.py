"""
Motor de Scoring de Fraude para Siniestros.
Calcula las 14 señales del PDF y valida las reglas de negocio RF01-RF07.
"""
import json
from datetime import datetime
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from backend.models import (
    Siniestro, Poliza, AseguradoSintetico, Vehiculo, Documento, Invoice, Workshop, Ramo, Cobertura
)

def get_similarity(a: str, b: str) -> float:
    """Calcula la similitud de texto entre dos strings."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def evaluate_fraud_scoring(siniestro: Siniestro, db: Session):
    """
    Evalúa un siniestro contra las 14 señales de fraude y las reglas RF01-RF07.
    Devuelve un diccionario con:
    - score: float (0-100)
    - classification: str (Verde, Amarillo, Rojo)
    - indicators: list of dict (señales activadas)
    - rules: list of dict (estado de RF01-RF07)
    """
    indicators = []
    rules = []
    
    # Obtener modelos relacionados
    poliza = db.query(Poliza).filter(Poliza.id_poliza == siniestro.id_poliza).first()
    asegurado = db.query(AseguradoSintetico).filter(AseguradoSintetico.id_asegurado == siniestro.id_asegurado).first()
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id == siniestro.vehiculo_id).first() if siniestro.vehiculo_id else None
    documentos = db.query(Documento).filter(Documento.id_siniestro == siniestro.id_siniestro).all()
    invoices = db.query(Invoice).filter(Invoice.siniestro_id == siniestro.id_siniestro).all()

    # --- REGLAS DE NEGOCIO RF01-RF07 ---
    
    # RF01: Ramo y Cobertura Válidos
    rf01_passed = True
    rf01_msg = "Ramo y cobertura válidos."
    if poliza:
        if poliza.ramo != siniestro.ramo:
            rf01_passed = False
            rf01_msg = f"Inconsistencia de Ramo: Siniestro reportado como '{siniestro.ramo.value}' pero Póliza es de '{poliza.ramo.value}'."
    else:
        rf01_passed = False
        rf01_msg = "Póliza asociada no encontrada."
    rules.append({"id": "RF01", "name": "Ramo y Cobertura Válidos", "passed": rf01_passed, "message": rf01_msg})

    # RF02: Vigencia de Póliza
    rf02_passed = True
    rf02_msg = "Siniestro dentro de la vigencia de la póliza."
    if poliza and siniestro.fecha_ocurrencia:
        if not (poliza.fecha_inicio <= siniestro.fecha_ocurrencia <= poliza.fecha_fin):
            rf02_passed = False
            rf02_msg = f"Siniestro fuera de vigencia: Ocurrió el {siniestro.fecha_ocurrencia.strftime('%Y-%m-%d')}, póliza vigente desde {poliza.fecha_inicio.strftime('%Y-%m-%d')} hasta {poliza.fecha_fin.strftime('%Y-%m-%d')}."
    rules.append({"id": "RF02", "name": "Vigencia de Póliza", "passed": rf02_passed, "message": rf02_msg})

    # RF03: Pago de Prima al Día
    rf03_passed = True
    rf03_msg = "Cliente al día con sus pagos."
    if asegurado and asegurado.mora_actual > 0:
        rf03_passed = False
        rf03_msg = f"Asegurado presenta mora activa en sus cuotas de prima."
    rules.append({"id": "RF03", "name": "Pago de Prima al Día", "passed": rf03_passed, "message": rf03_msg})

    # RF04: Documentación Mínima Presentada
    rf04_passed = True
    rf04_msg = "Documentación mínima completa entregada."
    required_docs = ["Cédula", "Licencia", "Denuncia", "Presupuesto"]
    if siniestro.ramo == Ramo.VEHICULOS:
        present_docs = [doc.tipo_documento for doc in documentos if doc.entregado == 1]
        missing = [d for d in required_docs if d not in present_docs]
        if missing:
            rf04_passed = False
            rf04_msg = f"Faltan documentos obligatorios: {', '.join(missing)}."
        else:
            # Check legibilidad
            illegible = [doc.tipo_documento for doc in documentos if doc.entregado == 1 and doc.legible == 0]
            if illegible:
                rf04_passed = False
                rf04_msg = f"Documentos ilegibles: {', '.join(illegible)}."
    rules.append({"id": "RF04", "name": "Documentación Mínima Presentada", "passed": rf04_passed, "message": rf04_msg})

    # RF05: Deducible Aplicado Correctamente
    rf05_passed = True
    rf05_msg = "Monto del siniestro supera el deducible de la póliza."
    if poliza and siniestro.monto_reclamado is not None:
        if siniestro.monto_reclamado <= poliza.deducible:
            rf05_passed = False
            rf05_msg = f"Monto reclamado (${siniestro.monto_reclamado:.2f}) es menor o igual al deducible de la póliza (${poliza.deducible:.2f})."
    rules.append({"id": "RF05", "name": "Deducible Aplicado Correctamente", "passed": rf05_passed, "message": rf05_msg})

    # RF06: Suma Asegurada No Excedida
    rf06_passed = True
    rf06_msg = "Monto reclamado no supera la suma asegurada."
    if poliza and siniestro.monto_reclamado is not None:
        if siniestro.monto_reclamado > poliza.suma_asegurada:
            rf06_passed = False
            rf06_msg = f"Monto reclamado (${siniestro.monto_reclamado:.2f}) excede la suma asegurada de la póliza (${poliza.suma_asegurada:.2f})."
    rules.append({"id": "RF06", "name": "Suma Asegurada No Excedida", "passed": rf06_passed, "message": rf06_msg})

    # RF07: Validación del Taller/Proveedor
    rf07_passed = True
    rf07_msg = "Taller autorizado y activo."
    for inv in invoices:
        workshop = db.query(Workshop).filter(Workshop.id == inv.workshop_id).first()
        if workshop:
            if not workshop.ruc or len(workshop.ruc) != 13:
                rf07_passed = False
                rf07_msg = f"Taller '{workshop.name}' presenta un RUC inválido o inactivo: '{workshop.ruc}'."
            # Simulación: si el email contiene "suspendido" o similar, o por nombre del taller
            if "suspendido" in (workshop.email or "").lower():
                rf07_passed = False
                rf07_msg = f"Taller '{workshop.name}' se encuentra suspendido del panel de proveedores."
    rules.append({"id": "RF07", "name": "Validación de Taller/Proveedor", "passed": rf07_passed, "message": rf07_msg})


    # --- LAS 14 SEÑALES DE FRAUDE ---
    pts = 0
    max_pts = 98

    # 1. Reclamo cercano a borde de vigencia (hasta 8 pts)
    # Si ocurre en los primeros 15 días o últimos 15 días de vigencia de la póliza
    if poliza and siniestro.fecha_ocurrencia:
        days_from_start = (siniestro.fecha_ocurrencia - poliza.fecha_inicio).days
        days_to_end = (poliza.fecha_fin - siniestro.fecha_ocurrencia).days
        
        if 0 <= days_from_start <= 15 or 0 <= days_to_end <= 15:
            indicators.append({
                "code": "S01",
                "name": "Borde de Vigencia",
                "points": 8,
                "detail": f"Ocurrió a los {days_from_start} días de iniciada o a los {days_to_end} días de terminar la póliza."
            })
            pts += 8
        elif 0 <= days_from_start <= 30 or 0 <= days_to_end <= 30:
            indicators.append({
                "code": "S01",
                "name": "Borde de Vigencia",
                "points": 4,
                "detail": f"Ocurrió a los {days_from_start} días de iniciada o a los {days_to_end} días de terminar la póliza."
            })
            pts += 4

    # 2. Demora denuncia por robo (hasta 8 pts)
    # Para cobertura de robo, si la denuncia demora más de 48h (2 días)
    if siniestro.cobertura == Cobertura.ROBO and siniestro.fecha_ocurrencia and siniestro.fecha_reporte:
        delay = (siniestro.fecha_reporte - siniestro.fecha_ocurrencia).days
        if delay > 3:
            indicators.append({
                "code": "S02",
                "name": "Demora Reporte Robo",
                "points": 8,
                "detail": f"Denuncia de robo realizada con {delay} días de retraso."
            })
            pts += 8
        elif delay > 1:
            indicators.append({
                "code": "S02",
                "name": "Demora Reporte Robo",
                "points": 4,
                "detail": f"Denuncia de robo realizada con {delay} días de retraso."
            })
            pts += 4

    # 3. Alta frecuencia reclamos asegurado (hasta 8 pts)
    if asegurado and asegurado.reclamos_12m > 3:
        indicators.append({
            "code": "S03",
            "name": "Alta Frecuencia Asegurado",
            "points": 8,
            "detail": f"Asegurado reporta {asegurado.reclamos_12m} siniestros en los últimos 12 meses."
        })
        pts += 8
    elif asegurado and asegurado.reclamos_12m >= 2:
        indicators.append({
            "code": "S03",
            "name": "Alta Frecuencia Asegurado",
            "points": 4,
            "detail": f"Asegurado reporta {asegurado.reclamos_12m} siniestros en los últimos 12 meses."
        })
        pts += 4

    # 4. Alta frecuencia reclamos vehículo (hasta 6 pts)
    if vehiculo:
        veh_claims = db.query(Siniestro).filter(
            Siniestro.vehiculo_id == vehiculo.id,
            Siniestro.id_siniestro != siniestro.id_siniestro
        ).count()
        if veh_claims >= 2:
            indicators.append({
                "code": "S04",
                "name": "Alta Frecuencia Vehículo",
                "points": 6,
                "detail": f"El vehículo de placa {vehiculo.placa} registra {veh_claims} siniestros anteriores."
            })
            pts += 6
        elif veh_claims == 1:
            indicators.append({
                "code": "S04",
                "name": "Alta Frecuencia Vehículo",
                "points": 3,
                "detail": f"El vehículo registra 1 siniestro anterior."
            })
            pts += 3

    # 5. Alta frecuencia conductor (hasta 8 pts)
    # Para efectos prácticos, si en la descripción menciona conductores que tienen historial
    # o si se asume frecuencia alta del conductor principal (derivado del asegurado)
    if asegurado and asegurado.reclamos_12m > 3 and "conductor" in (siniestro.descripcion or "").lower():
        indicators.append({
            "code": "S05",
            "name": "Frecuencia Conductor",
            "points": 8,
            "detail": "El conductor implicado registra múltiples reclamos activos en el sistema."
        })
        pts += 8

    # 6. Alta frecuencia solo RC (hasta 6 pts)
    # Reclamos recurrentes donde solo se afecta Responsabilidad Civil (terceros)
    if "responsabilidad civil" in (siniestro.descripcion or "").lower() or "choque a tercero" in (siniestro.descripcion or "").lower():
        # Contar siniestros de RC para este asegurado
        rc_count = db.query(Siniestro).filter(
            Siniestro.id_asegurado == siniestro.id_asegurado,
            Siniestro.descripcion.like("%tercero%") | Siniestro.descripcion.like("%responsabilidad%")
        ).count()
        if rc_count >= 2:
            indicators.append({
                "code": "S06",
                "name": "Frecuencia Responsabilidad Civil",
                "points": 6,
                "detail": f"Asegurado tiene {rc_count} reclamos acumulados enfocados solo en daños a terceros."
            })
            pts += 6

    # 7. Beneficiario/proveedor recurrente (hasta 10 pts)
    # Taller o beneficiario recurrente sospechoso
    # Si el beneficiario tiene otros siniestros con pólizas distintas
    if siniestro.beneficiario:
        other_ben_claims = db.query(Siniestro).filter(
            Siniestro.beneficiario == siniestro.beneficiario,
            Siniestro.id_poliza != siniestro.id_poliza
        ).count()
        if other_ben_claims >= 2:
            indicators.append({
                "code": "S07",
                "name": "Beneficiario Recurrente Sospechoso",
                "points": 10,
                "detail": f"El beneficiario '{siniestro.beneficiario}' registra reclamos cruzados en {other_ben_claims} pólizas distintas."
            })
            pts += 10
        elif other_ben_claims == 1:
            indicators.append({
                "code": "S07",
                "name": "Beneficiario Recurrente",
                "points": 5,
                "detail": f"El beneficiario '{siniestro.beneficiario}' registra reclamos en otra póliza."
            })
            pts += 5

    # 8. Documentos incompletos (hasta 4 pts)
    if not rf04_passed:
        indicators.append({
            "code": "S08",
            "name": "Documentación Incompleta/Ilegible",
            "points": 4,
            "detail": rf04_msg
        })
        pts += 4

    # 9. Dinámica sospechosa (hasta 6 pts)
    # Siniestros sin testigos, de madrugada, o relatos vagos
    desc_lower = (siniestro.descripcion or "").lower()
    if any(k in desc_lower for k in ["madrugada", "sin testigos", "vía solitaria", "lugar despoblado", "no recuerda", "3 am", "2 am", "1 am", "4 am"]):
        indicators.append({
            "code": "S09",
            "name": "Dinámica Sospechosa",
            "points": 6,
            "detail": "El relato del siniestro indica ocurrencia en horario nocturno tardío, sin testigos y con dinámica inusual."
        })
        pts += 6

    # 10. Eventos sin tercero (hasta 6 pts)
    # Daños contra objeto fijo, postes, autovolcamientos
    if any(k in desc_lower for k in ["objeto fijo", "poste", "árbol", "volcamiento", "despiste", "cuneta", "contra la pared"]):
        if not any(k in desc_lower for k in ["otro vehículo", "placa", "choque con auto"]):
            indicators.append({
                "code": "S10",
                "name": "Evento Sin Tercero Involucrado",
                "points": 6,
                "detail": "Daños por colisión contra objeto fijo o pérdida de control sin participación de terceros."
            })
            pts += 6

    # 11. Documentos inconsistentes (hasta 10 pts)
    # Fecha de factura anterior a siniestro, o inconsistencias detectadas
    doc_inc = [doc.tipo_documento for doc in documentos if doc.inconsistencia_detectada == 1]
    inv_inc = False
    for inv in invoices:
        if inv.issue_date and siniestro.fecha_ocurrencia and inv.issue_date < siniestro.fecha_ocurrencia:
            inv_inc = True
            
    if doc_inc or inv_inc:
        detail_msg = ""
        if doc_inc:
            detail_msg += f"Inconsistencia en documentos: {', '.join(doc_inc)}. "
        if inv_inc:
            detail_msg += "Factura emitida antes de la fecha de ocurrencia del siniestro. "
        indicators.append({
            "code": "S11",
            "name": "Documentación Inconsistente",
            "points": 10,
            "detail": detail_msg.strip()
        })
        pts += 10

    # 12. Reporte tardío (hasta 5 pts)
    # Más de 15 días entre ocurrencia y reporte
    if siniestro.fecha_ocurrencia and siniestro.fecha_reporte:
        days_diff = (siniestro.fecha_reporte - siniestro.fecha_ocurrencia).days
        if days_diff > 30:
            indicators.append({
                "code": "S12",
                "name": "Reporte Tardío Extremo",
                "points": 5,
                "detail": f"Siniestro reportado {days_diff} días después de su ocurrencia."
            })
            pts += 5
        elif days_diff > 15:
            indicators.append({
                "code": "S12",
                "name": "Reporte Tardío",
                "points": 3,
                "detail": f"Siniestro reportado {days_diff} días después de su ocurrencia."
            })
            pts += 3

    # 13. Narrativas similares (hasta 8 pts)
    # Verificar si hay otro siniestro con descripción muy similar (>80% coincidencia)
    similar_found = False
    similar_id = None
    if desc_lower and len(desc_lower) > 20:
        other_claims = db.query(Siniestro).filter(Siniestro.id_siniestro != siniestro.id_siniestro).all()
        for oc in other_claims:
            oc_desc = (oc.descripcion or "")
            if oc_desc and len(oc_desc) > 20:
                sim = get_similarity(siniestro.descripcion, oc_desc)
                if sim >= 0.75:
                    similar_found = True
                    similar_id = oc.id_siniestro
                    break
    if similar_found:
        indicators.append({
            "code": "S13",
            "name": "Narrativas Coincidentes",
            "points": 8,
            "detail": f"La descripción física del siniestro tiene una alta coincidencia semántica con el caso #{similar_id}."
        })
        pts += 8

    # 14. Monto cercano a suma asegurada (hasta 5 pts)
    # Reclamado >= 85% de la suma asegurada
    if poliza and siniestro.monto_reclamado and poliza.suma_asegurada:
        pct = (siniestro.monto_reclamado / poliza.suma_asegurada) * 100.0
        if pct >= 90.0:
            indicators.append({
                "code": "S14",
                "name": "Monto Cercano a Suma Asegurada",
                "points": 5,
                "detail": f"Monto reclamado equivale al {pct:.1f}% de la suma asegurada de la póliza (${poliza.suma_asegurada:.2f})."
            })
            pts += 5
        elif pct >= 75.0:
            indicators.append({
                "code": "S14",
                "name": "Monto Cercano a Suma Asegurada",
                "points": 3,
                "detail": f"Monto reclamado equivale al {pct:.1f}% de la suma asegurada."
            })
            pts += 3

    # Normalizar score a rango 0-100 (basado en el total obtenido vs max_pts)
    final_score = min(100.0, (pts / max_pts) * 100.0)
    
    # Si alguna regla crítica de negocio falla (ej: póliza no vigente, o ramo inválido),
    # eso también incrementa el score de fraude o alerta de forma severa
    if not rf02_passed or not rf01_passed:
        final_score = max(final_score, 85.0)  # Forzar riesgo alto si no hay cobertura o póliza vencida
        
    # Clasificación por semáforo
    if final_score <= 40.0:
        classification = "Verde"
    elif final_score <= 75.0:
        classification = "Amarillo"
    else:
        classification = "Rojo"

    return {
        "score": round(final_score, 2),
        "classification": classification,
        "indicators": indicators,
        "rules": rules
    }

def update_siniestro_fraud_data(siniestro: Siniestro, db: Session):
    """Calcula y persiste el scoring de fraude de un siniestro en la base de datos."""
    res = evaluate_fraud_scoring(siniestro, db)
    siniestro.fraud_score = res["score"]
    siniestro.fraud_classification = res["classification"]
    siniestro.fraud_indicators = json.dumps(res["indicators"], ensure_ascii=False)
    siniestro.fraud_rules_failed = json.dumps([r for r in res["rules"] if not r["passed"]], ensure_ascii=False)
    db.flush()
    return res
