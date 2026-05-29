# Matriz de Cumplimiento — HackIAthon 2026

Proyecto: Miraclex — Auditor Agéntico de Siniestros  
Fecha de actualización: 29/05/2026  
Estado: listo para demo funcional

## Resumen

## 1. Resumen general de cumplimiento

| Criterio general                 | Estado | Justificación                                                                                                            |
| -------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------ |
| Alineación con el README oficial | Cumple | La matriz se actualiza tomando como referencia principal el README del proyecto.                                         |
| Alcance del proyecto             | Cumple | El proyecto se define como un detector agéntico de posible fraude en siniestros, no únicamente como auditor de facturas. |
| Enfoque funcional                | Cumple | El sistema audita facturas, identifica señales de riesgo, prioriza casos críticos y apoya la revisión humana.            |
| Enfoque ético                    | Cumple | El sistema no acusa fraude, no aprueba pagos y no rechaza pagos automáticamente.                                         |
| Revisión humana                  | Cumple | Toda alerta generada por el sistema debe ser revisada por un analista humano autorizado.                                 |
| Estado general del proyecto      | Cumple | El proyecto integra backend, frontend, base de datos, reglas, score, semáforo, dashboard, chatbot e IA.                  |

---

## 2. Cumplimiento funcional

| Requerimiento                            | Estado | Evidencia de cumplimiento                                                                            | Observación                                                                              |
| ---------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Auditoría de facturas de siniestros      | Cumple | El sistema permite cargar y auditar facturas PDF asociadas a siniestros.                             | La auditoría de facturas es un componente del sistema, no el alcance total del proyecto. |
| Detección de posibles fraudes            | Cumple | El sistema aplica reglas y análisis asistido por IA para identificar señales de posible fraude.      | Debe usarse el término “posible fraude” o “alerta de riesgo”.                            |
| Detección de sobrecobros                 | Cumple | El sistema analiza valores facturados e identifica posibles montos inusuales o inconsistentes.       | No debe presentarse como conclusión definitiva sin revisión humana.                      |
| Detección de duplicados                  | Cumple | El sistema contempla la identificación de facturas o registros posiblemente duplicados.              | Apoya la prevención de pagos repetidos.                                                  |
| Detección de incoherencias               | Cumple | El sistema revisa inconsistencias entre factura, siniestro, póliza, documentos y narrativa del caso. | Las incoherencias deben tratarse como señales de alerta.                                 |
| Priorización de casos críticos           | Cumple | El sistema asigna un score de riesgo para ordenar los casos según criticidad.                        | Permite enfocar la revisión en los casos más relevantes.                                 |
| Score de riesgo 0-100                    | Cumple | El README define un puntaje de riesgo entre 0 y 100.                                                 | El score es referencial y no reemplaza la decisión humana.                               |
| Semáforo de riesgo                       | Cumple | El sistema clasifica los casos en Verde, Amarillo y Rojo.                                            | Los colores deben mantenerse consistentes en todos los documentos.                       |
| Dashboard de visualización               | Cumple | El proyecto incluye un dashboard para visualizar casos, alertas y resultados.                        | Debe describirse como herramienta de apoyo a la auditoría.                               |
| Chatbot de consulta                      | Cumple | El sistema incluye un chatbot para consultar información del sistema y de los casos.                 | Debe estar alineado con el motor IA oficial definido en el README.                       |
| Revisión humana obligatoria              | Cumple | El sistema requiere intervención humana para validar cualquier alerta.                               | Es un punto central del proyecto.                                                        |
| No acusación automática                  | Cumple | El sistema genera alertas, pero no acusa fraude directamente.                                        | Evitar expresiones como “fraude confirmado”.                                             |
| No decisión automática de pago o rechazo | Cumple | El sistema no aprueba ni rechaza pagos automáticamente.                                              | La decisión final corresponde al analista humano.                                        |

---

## 3. Cumplimiento técnico

| Componente técnico                       | Estado | Evidencia de cumplimiento                                                                                             | Observación                                                    |
| ---------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Backend FastAPI                          | Cumple | El README define FastAPI como backend principal del sistema.                                                          | Debe mantenerse igual en los documentos técnicos.              |
| Frontend / Dashboard                     | Cumple | El sistema incluye interfaz visual para consultar casos, alertas y resultados.                                        | Debe describirse como dashboard operativo.                     |
| Base de datos SQLite                     | Cumple | El proyecto contempla almacenamiento estructurado para la información del sistema.                                    | No debe indicarse como pendiente si el README ya lo reconoce.  |
| Modelo de datos normalizado              | Cumple | El README menciona tablas normalizadas para siniestros, pólizas, asegurados, vehículos, documentos, facturas e ítems. | Debe alinearse con `modelo_datos.md`.                          |
| Tabla de siniestros                      | Cumple | El sistema gestiona información de siniestros.                                                                        | Forma parte del núcleo funcional del proyecto.                 |
| Tabla de pólizas                         | Cumple | El sistema contempla información de pólizas.                                                                          | No debe figurar como modelo inexistente.                       |
| Tabla de asegurados sintéticos           | Cumple | El sistema utiliza información sintética de asegurados.                                                               | Refuerza el enfoque de privacidad y demostración.              |
| Tabla de vehículos                       | Cumple | El sistema contempla información vehicular cuando aplica.                                                             | Debe mantenerse alineado con el modelo de datos.               |
| Tabla de documentos                      | Cumple | El sistema considera documentos asociados al siniestro.                                                               | Sirve para validar soporte documental.                         |
| Tabla de facturas                        | Cumple | El sistema registra y analiza facturas.                                                                               | Elemento central para la auditoría documental.                 |
| Tabla de ítems de factura                | Cumple | El sistema analiza detalles o ítems facturados.                                                                       | Permite identificar sobrecostos o inconsistencias.             |
| Motor de reglas determinísticas          | Cumple | El sistema aplica reglas para detectar señales de alerta.                                                             | Debe vincularse con reglas de negocio y señales de riesgo.     |
| Motor IA DeepSeek V4 Flash / OpenCode Go | Cumple | El README define DeepSeek V4 Flash / OpenCode Go como motor principal.                                                | Corregir documentos que mencionen Gemini como motor principal. |
| Auditoría de facturas PDF                | Cumple | El sistema permite analizar facturas PDF.                                                                             | Debe tratarse como parte del sistema de siniestros.            |
| Arquitectura documentada                 | Cumple | Existe documentación de arquitectura dentro de la carpeta `docs`.                                                     | No debe marcarse como “no cumple”.                             |

---

## 4. Cumplimiento de reglas y señales de riesgo

| Regla / Señal                           | Estado | Evidencia de cumplimiento                                                                     | Observación                                                |
| --------------------------------------- | ------ | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Validación de cobertura y ramo          | Cumple | El sistema revisa coherencia entre siniestro, póliza, cobertura y factura.                    | Debe mantenerse alineado con las reglas de negocio.        |
| Validación de vigencia de póliza        | Cumple | El sistema identifica alertas relacionadas con fechas, vigencia o temporalidad del siniestro. | Es una señal crítica para revisión.                        |
| Validación de documentación mínima      | Cumple | El sistema contempla revisión de documentos asociados al siniestro.                           | Permite detectar expedientes incompletos o inconsistentes. |
| Validación de deducible                 | Cumple | El sistema puede contrastar valores aplicables al caso.                                       | Debe presentarse como apoyo al análisis.                   |
| Validación de suma asegurada            | Cumple | El sistema permite identificar posibles excesos frente a montos asegurados.                   | Debe considerarse señal de alerta.                         |
| Validación de proveedor o taller        | Cumple | El sistema contempla revisión del proveedor relacionado con la factura o siniestro.           | Aplica especialmente a facturas de reparación o servicios. |
| Detección de facturas duplicadas        | Cumple | El sistema identifica posibles duplicidades documentales.                                     | Ayuda a evitar pagos repetidos.                            |
| Detección de sobrecostos                | Cumple | El sistema detecta valores inusuales o superiores a lo esperado.                              | Debe tratarse como posible sobrecosto.                     |
| Detección de incoherencias documentales | Cumple | El sistema analiza diferencias entre documentos, narrativa y factura.                         | Debe validarse por revisión humana.                        |
| Clasificación por nivel de riesgo       | Cumple | El sistema utiliza score y semáforo para clasificar casos.                                    | Verde, Amarillo y Rojo deben ser uniformes.                |
| Generación de alertas explicables       | Cumple | El sistema presenta motivos o señales asociadas al riesgo.                                    | Refuerza la transparencia del análisis.                    |
| Priorización de casos para auditoría    | Cumple | Los casos con mayor riesgo pueden ser revisados primero.                                      | Mejora la eficiencia del proceso de auditoría.             |

---

## 5. Cumplimiento ético y de gobernanza

| Criterio ético              | Estado | Evidencia de cumplimiento                                                   | Observación                                                         |
| --------------------------- | ------ | --------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Uso de lenguaje responsable | Cumple | El sistema debe referirse a “alertas”, “riesgo” o “posible fraude”.         | Evitar lenguaje acusatorio.                                         |
| No acusación de fraude      | Cumple | El README establece que el sistema no acusa directamente.                   | El fraude solo puede confirmarse mediante revisión correspondiente. |
| No decisión automática      | Cumple | El sistema no decide pagos, rechazos ni sanciones.                          | Solo apoya la revisión.                                             |
| Revisión humana obligatoria | Cumple | Toda alerta requiere análisis de un usuario autorizado.                     | Debe mantenerse en todos los documentos.                            |
| Explicabilidad              | Cumple | Las alertas deben estar acompañadas de razones o señales.                   | Permite que el analista entienda el resultado.                      |
| Uso responsable de IA       | Cumple | La IA funciona como apoyo al análisis, no como autoridad final.             | El analista mantiene la responsabilidad de la decisión.             |
| Uso de datos sintéticos     | Cumple | El proyecto trabaja con información sintética para efectos de demostración. | Reduce riesgos de privacidad.                                       |
| Trazabilidad de alertas     | Cumple | El sistema permite consultar casos, resultados y señales generadas.         | Fortalece auditoría y control.                                      |

---

## 6. Correcciones frente a la versión anterior de la matriz

| Punto corregido      | Estado anterior             | Estado actualizado                                | Justificación                                                                                                         |
| -------------------- | --------------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Arquitectura formal  | No cumple / pendiente       | Cumple                                            | El repositorio sí cuenta con documentación de arquitectura dentro de `docs`.                                          |
| Modelo de datos      | No cumple / pendiente       | Cumple                                            | El README reconoce tablas normalizadas para siniestros, pólizas, asegurados, vehículos, documentos, facturas e ítems. |
| Modelo de póliza     | No existe                   | Cumple                                            | El README contempla pólizas dentro del modelo de datos.                                                               |
| Modelo de asegurado  | No existe                   | Cumple                                            | El README contempla asegurados sintéticos.                                                                            |
| Modelo de documentos | No existe                   | Cumple                                            | El README contempla documentos asociados al siniestro.                                                                |
| Alcance del sistema  | Auditor de facturas         | Detector agéntico de posible fraude en siniestros | El README oficial define un alcance más amplio.                                                                       |
| Motor IA             | Gemini / ambiguo            | DeepSeek V4 Flash / OpenCode Go                   | El README define este motor como referencia principal.                                                                |
| Chatbot              | Pendiente o fase futura     | Cumple                                            | El README incluye chatbot como parte del sistema.                                                                     |
| Dashboard            | Pendiente o fase futura     | Cumple                                            | El README incluye dashboard para visualización y priorización.                                                        |
| Reglas de negocio    | Pendientes o incompletas    | Cumple                                            | El README contempla reglas determinísticas y señales de riesgo.                                                       |
| Score de riesgo      | Pendiente o parcial         | Cumple                                            | El README define score 0-100.                                                                                         |
| Semáforo de riesgo   | Pendiente o parcial         | Cumple                                            | El README define clasificación Verde, Amarillo y Rojo.                                                                |
| Decisión automática  | No aclarado                 | Corregido                                         | Se deja claro que el sistema no aprueba ni rechaza automáticamente.                                                   |
| Lenguaje de fraude   | Riesgo de acusación directa | Corregido                                         | Se usa “posible fraude”, “alerta” o “riesgo”.                                                                         |

---

## 7. Documentos que deben quedar alineados con esta matriz

| Documento                            | Estado esperado       | Acción recomendada                                                          |
| ------------------------------------ | --------------------- | --------------------------------------------------------------------------- |
| `README.md`                          | Fuente oficial        | Mantener como documento principal de referencia.                            |
| `MATRIZ_CUMPLIMIENTO_RETO.md`        | Debe actualizarse     | Reemplazar la versión anterior por esta matriz actualizada.                 |
| `modelo_datos.md`                    | Alineado parcialmente | Verificar que use los mismos nombres de tablas y alcance del README.        |
| `reglas_negocio.md`                  | Alineado parcialmente | Confirmar que las reglas RF01-RF07 coincidan con lo oficial.                |
| `arquitectura.md`                    | Alineado parcialmente | Mantener la arquitectura como evidencia de cumplimiento.                    |
| `stack.md`                           | Requiere ajuste       | Corregir puertos, motor IA y descripción del backend/frontend según README. |
| `uso_ia.md`                          | Requiere ajuste       | Dejar DeepSeek V4 Flash / OpenCode Go como motor principal.                 |
| `MANUAL_USO.md`                      | Requiere ajuste       | Cambiar enfoque de auditor de facturas a detector de fraude en siniestros.  |
| `DOC_FUNCIONES.md`                   | Requiere ajuste       | Unificar el motor IA y el alcance funcional con el README.                  |
| `PLAN_SOFISTICADO_IMPLEMENTACION.md` | Requiere ajuste       | Marcar como histórico o actualizarlo como plan de evolución futura.         |
| `DEEPSEEK_REVIEW_LOOP.md`            | Requiere ajuste       | Actualizar las fases pendientes según el estado actual del README.          |

---

## 8. Conclusión de cumplimiento

| Resultado                      | Estado                                                                         |
| ------------------------------ | ------------------------------------------------------------------------------ |
| Estado general de cumplimiento | Cumple                                                                         |
| Fuente oficial utilizada       | README.md                                                                      |
| Nivel de alineación funcional  | Alto                                                                           |
| Nivel de alineación técnica    | Alto                                                                           |
| Nivel de alineación ética      | Alto                                                                           |
| Riesgo principal identificado  | Documentos secundarios desactualizados o contradictorios                       |
| Acción principal recomendada   | Actualizar la matriz y documentos secundarios para que coincidan con el README |

---

## 9. Conclusión final

La matriz actualizada refleja que el proyecto **Miraclex — Detector Agéntico de Fraude en Siniestros** cumple con los principales criterios funcionales, técnicos y éticos definidos en el README oficial.

El sistema permite apoyar a una aseguradora en la revisión temprana de siniestros mediante reglas determinísticas, análisis asistido por IA, auditoría de facturas PDF, score de riesgo, semáforo de criticidad, dashboard, chatbot y revisión humana obligatoria.

Toda alerta generada por el sistema debe interpretarse como una señal de revisión o posible riesgo, no como una acusación ni como una decisión automática. La decisión final corresponde siempre a un analista humano autorizado.

