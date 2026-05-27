# 📋 Reglas de Negocio y Scoring Antifraude — Aseguradora del Sur

Este documento detalla las 14 señales de alerta y las 7 reglas críticas utilizadas para evaluar el riesgo de fraude en los siniestros.

## 1. Las 14 Señales de Fraude (Sección 7 del PDF)

El motor evalúa cada siniestro y asigna un puntaje acumulativo basado en pesos definidos por la rúbrica del reto. El puntaje máximo es de **98 puntos**, el cual se normaliza a una escala de **0-100**:

| Código | Alerta / Señal | Peso Máx | Descripción del Algoritmo de Evaluación |
|--------|----------------|----------|-----------------------------------------|
| **S01** | Borde de Vigencia | 8 pts | Si ocurre en los primeros 15 días o últimos 15 días de vigencia de la póliza (+8). Si ocurre en los primeros/últimos 30 días (+4). |
| **S02** | Demora Reporte Robo | 8 pts | En cobertura de Robo, si el reporte demora >3 días (+8), o si demora >1 día (+4). |
| **S03** | Alta Frecuencia Asegurado | 8 pts | Si el asegurado registra >3 reclamos en los últimos 12 meses (+8) o >=2 reclamos (+4). |
| **S04** | Alta Frecuencia Vehículo | 6 pts | Si el vehículo de placa asociada registra >=2 siniestros anteriores (+6) o 1 anterior (+3). |
| **S05** | Frecuencia Conductor | 8 pts | Si el asegurado tiene alta frecuencia y en la descripción se menciona la intervención de conductores adicionales. |
| **S06** | Frecuencia solo RC | 6 pts | Si hay >=2 siniestros acumulados de Responsabilidad Civil (daños a terceros) para el mismo asegurado. |
| **S07** | Beneficiario/Proveedor Recurrente | 10 pts | Si el beneficiario del pago registra reclamos cruzados en >=2 pólizas distintas (+10) o 1 póliza extra (+5). |
| **S08** | Documentación Incompleta | 4 pts | Si el flag `documentos_completos == 0` o falta alguno de los requeridos (Cédula, Licencia, Denuncia, Presupuesto). |
| **S09** | Dinámica Sospechosa | 6 pts | Si la descripción menciona ocurrencias en horario nocturno tardío (madrugada), sin testigos o vías solitarias. |
| **S10** | Evento Sin Tercero Involucrado | 6 pts | Colisiones contra objetos fijos (postes, pilares, muros) o autovolcamientos sin participación de otro auto. |
| **S11** | Documentación Inconsistente | 10 pts | Si el taller emite la factura antes de la fecha del siniestro o si los documentos presentan enmiendas físicas. |
| **S12** | Reporte Tardío | 5 pts | Si los días transcurridos entre el accidente y el reporte son >30 días (+5) o >15 días (+3). |
| **S13** | Narrativas Coincidentes | 8 pts | Si la descripción coincide en >=75% de similitud de caracteres (SequenceMatcher) con otra reclamación registrada. |
| **S14** | Monto Cercano a Suma Asegurada | 5 pts | Si el monto reclamado es >=90% de la suma asegurada (+5) o >=75% (+3). |

---

## 2. Reglas de Negocio Críticas (RF01-RF07)

Estas reglas validan la viabilidad técnica y contractual del reclamo. Si una regla crítica (RF01 o RF02) falla, el reclamo se cataloga **automáticamente** como **Rojo (Riesgo Alto - Score 85+)** para revisión obligatoria de la Unidad Antifraude:

- **RF01: Ramo y Cobertura Válidos**: Compara el ramo del siniestro contra el ramo contratado en la póliza. Falla si hay discrepancia (ej. siniestro de Choque en póliza de Salud).
- **RF02: Vigencia de Póliza**: Falla si el siniestro ocurrió fuera de los límites de vigencia (`fecha_inicio` y `fecha_fin`) de la póliza contratada.
- **RF03: Pago de Prima al Día**: Alerta si el asegurado presenta una mora activa en el pago de sus cuotas de prima.
- **RF04: Documentación Mínima Presentada**: Falla si falta alguno de los documentos clave (Cédula, Licencia, Denuncia, Presupuesto) o si alguno de ellos se marca como ilegible.
- **RF05: Deducible Aplicado Correctamente**: Falla si el monto reclamado es menor o igual al deducible pactado en la póliza (el reclamo no procede).
- **RF06: Suma Asegurada No Excedida**: Falla si el monto del siniestro supera el monto total asegurado por contrato.
- **RF07: Validación del Taller/Proveedor**: Falla si el taller no presenta un RUC válido (13 dígitos) o se encuentra inactivo/suspendido.

---

## 3. Semáforo de Riesgo (Sección 13 del PDF)

Una vez calculado el score ponderado normalizado, el caso se clasifica:

- **🟢 Verde / Riesgo Bajo (0-40)**: El caso continúa su flujo de liquidación normal.
- **🟡 Amarillo / Riesgo Medio (41-75)**: El caso es retenido y escalado a la Unidad Antifraude para verificación documental.
- **🔴 Rojo / Riesgo Alto (76-100)**: El caso es bloqueado y enviado a la Unidad Antifraude para una inspección física y especializada en el campo.
