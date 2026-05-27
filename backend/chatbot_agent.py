"""
Agente Conversacional IA para Consultas del hackIAthon.
Clasifica la consulta, extrae datos de la BD y redacta una respuesta formal con Gemini/DeepSeek.
"""
import json
import os
import re
import urllib.request
import urllib.error
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models import (
    Siniestro, Poliza, AseguradoSintetico, Vehiculo, Documento, Invoice, Workshop, Ramo, Cobertura
)

def call_llm(prompt: str, system_prompt: str = "") -> str:
    """Realiza la llamada al LLM activo (DeepSeek o Gemini) usando APIs de forma robusta."""
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    google_key = os.environ.get("GOOGLE_API_KEY")

    if deepseek_key:
        # Llamar a DeepSeek Chat API
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {deepseek_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                return res_body["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Error llamando a DeepSeek API: {str(e)}. Intentando Gemini como fallback...")

    if google_key:
        # Llamar a Gemini API
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=google_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2
                )
            )
            return response.text
        except Exception as e:
            # Fallback a REST directo si la librería falla
            print(f"Librería google-genai falló: {str(e)}. Intentando request REST directo...")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={google_key}"
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "generationConfig": {"temperature": 0.2}
            }
            try:
                req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_body = json.loads(response.read().decode("utf-8"))
                    return res_body["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as re_err:
                print(f"Error REST Gemini API: {str(re_err)}")
                
    return ""

def process_chatbot_query(question: str, db: Session) -> str:
    """Clasifica la pregunta del usuario, obtiene datos de la BD y genera la respuesta formateada."""
    q_clean = question.lower().strip()
    raw_data = ""
    question_type = "GENERAL"

    # Clasificar basándose en los 12 tipos de preguntas del PDF
    # Q1: Top 10 siniestros
    if any(k in q_clean for k in ["top 10", "10 siniestros", "mayor riesgo", "más riesgosos", "mayor score", "ranking"]):
        question_type = "Q1"
        claims = db.query(Siniestro).order_by(Siniestro.fraud_score.desc()).limit(10).all()
        res = []
        for c in claims:
            res.append(f"- SIN-{c.id_siniestro}: Asegurado: {c.id_asegurado}, Ramo: {c.ramo.value}, Score: {c.fraud_score}, Clasificación: {c.fraud_classification}")
        raw_data = "\n".join(res) if res else "No hay siniestros en la base de datos."

    # Q2: ¿Por qué SIN-X fue marcado con alto riesgo?
    elif any(k in q_clean for k in ["por qué", "por que", "motivo", "razon"]) and ("sin-" in q_clean or "siniestro" in q_clean):
        question_type = "Q2"
        # Intentar extraer ID del siniestro
        claim_id_match = re.search(r"sin-(\d+)", q_clean) or re.search(r"siniestro\s+(\d+)", q_clean) or re.search(r"\b(\d+)\b", q_clean)
        if claim_id_match:
            claim_id = int(claim_id_match.group(1))
            c = db.query(Siniestro).filter(Siniestro.id_siniestro == claim_id).first()
            if c:
                aseg = db.query(AseguradoSintetico).filter(AseguradoSintetico.id_asegurado == c.id_asegurado).first()
                indicators = json.loads(c.fraud_indicators or "[]")
                rules_failed = json.loads(c.fraud_rules_failed or "[]")
                
                res = [
                    f"Siniestro SIN-{c.id_siniestro}:",
                    f"- Asegurado: {c.id_asegurado} (Segmento: {aseg.segmento if aseg else 'N/A'}, Mora: {'Sí' if aseg and aseg.mora_actual else 'No'})",
                    f"- Póliza: {c.id_poliza} (Ramo: {c.ramo.value}, Cobertura: {c.cobertura.value})",
                    f"- Monto Reclamado: ${c.monto_reclamado:.2f}",
                    f"- Score de Fraude: {c.fraud_score} ({c.fraud_classification})",
                    f"- Descripción: {c.descripcion}",
                    "\nSeñales de Alerta de Fraude:"
                ]
                for ind in indicators:
                    res.append(f" - [{ind['code']}] {ind['name']}: {ind['detail']} (+{ind['points']} pts)")
                res.append("\nReglas de Negocio Falladas:")
                for r in rules_failed:
                    res.append(f" - [{r['id']}] {r['name']}: {r['message']}")
                raw_data = "\n".join(res)
            else:
                raw_data = f"El siniestro SIN-{claim_id} no existe en la base de datos."
        else:
            raw_data = "No se pudo identificar el número de siniestro en tu pregunta. Por favor indica ej: '¿Por qué el siniestro SIN-2 fue marcado?'"

    # Q3: Proveedores con más alertas
    elif any(k in q_clean for k in ["proveedor", "proveedores", "taller", "talleres"]) and any(k in q_clean for k in ["alertas", "concentran", "sospechosos", "más"]):
        question_type = "Q3"
        results = db.query(
            Workshop.name,
            func.count(AuditResult.id).label("total_alertas"),
            func.sum(AuditResult.total_overcharge).label("total_sobrecobro")
        ).join(Invoice, Invoice.workshop_id == Workshop.id)\
         .join(AuditResult, AuditResult.invoice_id == Invoice.id)\
         .filter(AuditResult.risk_score > 30)\
         .group_by(Workshop.name)\
         .order_by(func.count(AuditResult.id).desc()).all()
        
        res = []
        for name, cnt, overcharge in results:
            res.append(f"- Taller: {name}, Facturas Observadas: {cnt}, Ahorro Potencial: ${overcharge:.2f}")
        raw_data = "\n".join(res) if res else "No hay talleres con facturas observadas."

    # Q4: Ramos con mayor % de casos sospechosos
    elif any(k in q_clean for k in ["ramo", "ramos"]) and any(k in q_clean for k in ["porcentaje", "porcentajes", "%", "sospechosos", "mayor"]):
        question_type = "Q4"
        from collections import defaultdict
        claims = db.query(Siniestro).all()
        ramo_totals = defaultdict(int)
        ramo_suspicious = defaultdict(int)
        for c in claims:
            ramo = c.ramo.value
            ramo_totals[ramo] += 1
            if c.fraud_score > 40:
                ramo_suspicious[ramo] += 1
                
        res = []
        for ramo, total in ramo_totals.items():
            susp = ramo_suspicious[ramo]
            pct = (susp / total) * 100
            res.append(f"- Ramo: {ramo}, Casos Sospechosos: {susp}/{total} ({pct:.1f}%)")
        res.sort(key=lambda x: float(x.split("(")[1].replace("%)", "")), reverse=True)
        raw_data = "\n".join(res)

    # Q5: Ciudades con mayor concentración
    elif any(k in q_clean for k in ["ciudad", "ciudades", "concentracion", "concentración", "sucursal", "sucursales"]):
        question_type = "Q5"
        from collections import defaultdict
        claims = db.query(Siniestro).all()
        city_counts = defaultdict(int)
        for c in claims:
            if c.fraud_score > 40:
                city_counts[c.sucursal or "Desconocida"] += 1
                
        res = []
        for city, count in city_counts.items():
            res.append(f"- Ciudad/Sucursal: {city}, Casos Sospechosos: {count}")
        res.sort(key=lambda x: int(x.split(": ")[1]), reverse=True)
        raw_data = "\n".join(res) if res else "No se encontraron alertas en sucursales."

    # Q6: Asegurados con mayor frecuencia
    elif any(k in q_clean for k in ["asegurado", "asegurados"]) and any(k in q_clean for k in ["frecuencia", "frecuentes", "más reclamos", "mas reclamos"]):
        question_type = "Q6"
        aseg = db.query(AseguradoSintetico).order_by(AseguradoSintetico.reclamos_12m.desc()).limit(10).all()
        res = []
        for a in aseg:
            res.append(f"- Asegurado: {a.nombre} (ID: {a.id_asegurado}), Reclamos últimos 12m: {a.reclamos_12m}, Score Cliente: {a.score_cliente_simulado}")
        raw_data = "\n".join(res)

    # Q7: Documentos faltantes en casos críticos
    elif any(k in q_clean for k in ["documento", "documentos", "falta", "faltan", "faltantes"]) and any(k in q_clean for k in ["crítico", "critico", "críticos", "criticos", "alto riesgo"]):
        question_type = "Q7"
        claims = db.query(Siniestro).filter(Siniestro.fraud_score > 75).all()
        res = []
        for c in claims:
            docs = db.query(Documento).filter(Documento.id_siniestro == c.id_siniestro).all()
            missing = [d.tipo_documento for d in docs if d.entregado == 0]
            present = [d.tipo_documento for d in docs if d.entregado == 1]
            canon = ["Cédula", "Licencia", "Denuncia", "Presupuesto"]
            for cn in canon:
                if cn not in present and cn not in missing:
                    missing.append(cn)
            if missing:
                res.append(f"- SIN-{c.id_siniestro} (Score: {c.fraud_score}, Ramo: {c.ramo.value}): Falta {', '.join(missing)}")
        raw_data = "\n".join(res) if res else "No hay documentos pendientes en casos críticos."

    # Q8: Montos atípicos
    elif any(k in q_clean for k in ["monto", "montos", "atípico", "atipico", "atípicos", "atipicos"]):
        question_type = "Q8"
        claims = db.query(Siniestro).all()
        res = []
        for c in claims:
            pol = db.query(Poliza).filter(Poliza.id_poliza == c.id_poliza).first()
            if pol and c.monto_reclamado and pol.suma_asegurada:
                pct = (c.monto_reclamado / pol.suma_asegurada) * 100
                if pct >= 80.0 or c.monto_reclamado > 15000:
                    res.append(f"- SIN-{c.id_siniestro}: Reclamado: ${c.monto_reclamado:.2f}, Suma Asegurada: ${pol.suma_asegurada:.2f} ({pct:.1f}%)")
        raw_data = "\n".join(res) if res else "No hay montos atípicos detectados."

    # Q9: Siniestros cerca del inicio de póliza
    elif any(k in q_clean for k in ["inicio", "borde", "vigencia", "cerca"]) and any(k in q_clean for k in ["poliza", "póliza"]):
        question_type = "Q9"
        claims = db.query(Siniestro).filter(Siniestro.dias_desde_inicio_poliza <= 30).all()
        res = []
        for c in claims:
            res.append(f"- SIN-{c.id_siniestro} (Asegurado: {c.id_asegurado}): Ocurrió a los {c.dias_desde_inicio_poliza} días del inicio. Score: {c.fraud_score}")
        raw_data = "\n".join(res) if res else "No hay siniestros al inicio de vigencia de pólizas."

    # Q10: Patrones comunes / repetidos
    elif any(k in q_clean for k in ["patron", "patrón", "patrones"]) and any(k in q_clean for k in ["repiten", "repetidos", "comunes"]):
        question_type = "Q10"
        from collections import Counter
        claims = db.query(Siniestro).filter(Siniestro.fraud_score > 40).all()
        indicators = []
        for c in claims:
            inds = json.loads(c.fraud_indicators or "[]")
            for ind in inds:
                indicators.append(ind["name"])
        counts = Counter(indicators)
        res = ["Patrones de fraude recurrentes en casos observados:"]
        for pattern, cnt in counts.most_common(5):
            res.append(f"- {pattern}: Identificado en {cnt} siniestros.")
        raw_data = "\n".join(res)

    # Q11: Resumen ejecutivo casos críticos
    elif any(k in q_clean for k in ["resumen", "resumen ejecutivo"]) and any(k in q_clean for k in ["crítico", "critico", "críticos", "criticos"]):
        question_type = "Q11"
        claims = db.query(Siniestro).filter(Siniestro.fraud_classification == "Rojo").all()
        total_reclamado = sum(c.monto_reclamado or 0 for c in claims)
        res = [
            f"Total de siniestros de Alerta Roja: {len(claims)}",
            f"Monto total bajo riesgo crítico: ${total_reclamado:.2f}",
            "\nListado de siniestros críticos:"
        ]
        for c in claims:
            rules_failed = json.loads(c.fraud_rules_failed or "[]")
            rules_str = f" [Falló: {', '.join(r['id'] for r in rules_failed)}]" if rules_failed else ""
            res.append(f"- SIN-{c.id_siniestro} ({c.id_asegurado}) - Score: {c.fraud_score}/100{rules_str}")
        raw_data = "\n".join(res)

    # Q12: Recomienda qué casos revisar primero
    elif any(k in q_clean for k in ["recomienda", "recomendar", "revisar", "prioridad"]):
        question_type = "Q12"
        claims = db.query(Siniestro).order_by(Siniestro.fraud_score.desc()).limit(5).all()
        res = []
        for c in claims:
            rules_failed = json.loads(c.fraud_rules_failed or "[]")
            reason = f"Incumple reglas: {', '.join(r['id'] for r in rules_failed)}" if rules_failed else "Puntuación de riesgo muy elevada"
            res.append(f"- SIN-{c.id_siniestro} (Score: {c.fraud_score}, {c.fraud_classification}): {reason}")
        raw_data = "\n".join(res)

    # Fallback general (buscar siniestros específicos o información)
    else:
        # Si menciona un siniestro específico, ej: SIN-4
        spec_match = re.search(r"sin-(\d+)", q_clean) or re.search(r"siniestro\s+(\d+)", q_clean)
        if spec_match:
            claim_id = int(spec_match.group(1))
            c = db.query(Siniestro).filter(Siniestro.id_siniestro == claim_id).first()
            if c:
                rules_failed = json.loads(c.fraud_rules_failed or "[]")
                raw_data = (
                    f"Siniestro SIN-{c.id_siniestro}:\n"
                    f"- Ramo: {c.ramo.value}\n"
                    f"- Asegurado: {c.id_asegurado}\n"
                    f"- Score de Alerta: {c.fraud_score} ({c.fraud_classification})\n"
                    f"- Descripción: {c.descripcion}\n"
                    f"- Reglas rotas: {', '.join(r['name'] for r in rules_failed) if rules_failed else 'Ninguna'}"
                )
            else:
                raw_data = f"No encontré el siniestro SIN-{claim_id} en la base de datos."
        else:
            # Dump general estadístico de siniestros
            total_claims = db.query(Siniestro).count()
            rojo = db.query(Siniestro).filter(Siniestro.fraud_classification == "Rojo").count()
            amarillo = db.query(Siniestro).filter(Siniestro.fraud_classification == "Amarillo").count()
            verde = db.query(Siniestro).filter(Siniestro.fraud_classification == "Verde").count()
            raw_data = (
                f"Estadísticas Generales:\n"
                f"- Total Siniestros: {total_claims}\n"
                f"- Alertas Rojas (Riesgo Alto): {rojo}\n"
                f"- Alertas Amarillas (Riesgo Medio): {amarillo}\n"
                f"- Alertas Verdes (Riesgo Bajo): {verde}"
            )

    # Formular Prompt para el LLM
    system_prompt = (
        "Eres un Asistente de IA de la Unidad Antifraude de Aseguradora del Sur.\n"
        "Tu misión es responder preguntas sobre el análisis de riesgo de los siniestros basándote estrictamente en los datos provistos.\n"
        "Redacta una respuesta muy profesional, amigable, formal y fluida en español.\n"
        "Importante: Nunca inventes datos que no se encuentren en el reporte estructurado de base de datos. "
        "Si los datos no responden directamente a la pregunta, dilo claramente de forma educada."
    )
    
    prompt = (
        f"Pregunta del usuario: '{question}'\n\n"
        f"Datos extraídos de la Base de Datos:\n"
        f"-----------------------------------------\n"
        f"{raw_data}\n"
        f"-----------------------------------------\n\n"
        f"Por favor, redacta la respuesta natural en base a esta información:"
    )

    # Ejecutar la llamada al LLM
    answer = call_llm(prompt, system_prompt)

    # Si por alguna razón la llamada de IA falla o devuelve vacío, estructuramos una respuesta en texto formateada
    if not answer.strip():
        answer = (
            f"### Resultados del Análisis Antifraude\n\n"
            f"Basado en tu consulta: **\"{question}\"**, he recopilado los siguientes datos estructurados directos de la base de datos:\n\n"
            f"{raw_data}\n\n"
            f"*Nota: Respuesta generada en modo local por desconexión de servicios de IA.*"
        )

    return answer
