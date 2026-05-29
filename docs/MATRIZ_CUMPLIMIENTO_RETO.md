# Matriz de Cumplimiento — HackIAthon 2026

Proyecto: Miraclex — Auditor Agéntico de Siniestros  
Fecha de actualización: 29/05/2026  
Estado: listo para demo funcional

## Resumen

1. Descripción general del proyecto

Miraclex es una solución tecnológica orientada a la detección de posibles fraudes, sobrecobros, duplicados e incoherencias en siniestros de seguros antes del pago.

El sistema permite auditar facturas asociadas a siniestros, priorizar casos críticos y entregar alertas explicables para apoyar la revisión humana. La solución no acusa fraude ni toma decisiones automáticas de aprobación o rechazo; únicamente genera alertas de posible riesgo para que un analista autorizado realice la validación correspondiente.

2. Alcance funcional validado
Requerimiento / Criterio	Estado	Evidencia de cumplimiento	Observación
Auditoría de facturas de siniestros	Cumple	El sistema permite cargar y auditar facturas PDF relacionadas con siniestros.	La auditoría identifica posibles inconsistencias, sobrecostos, duplicados y señales de alerta.
Detección de posibles fraudes	Cumple	El sistema aplica reglas determinísticas y análisis asistido por IA para detectar señales de posible fraude.	El lenguaje debe mantenerse como “posible fraude” o “alerta de riesgo”, evitando acusaciones directas.
Priorización de casos críticos	Cumple	El sistema utiliza un score de riesgo de 0 a 100 y semáforo de criticidad.	Permite enfocar la revisión humana en casos de mayor prioridad.
Semáforo de riesgo	Cumple	Se define clasificación Verde, Amarillo y Rojo según nivel de riesgo.	Debe mantenerse consistente en todos los documentos.
Score de riesgo 0-100	Cumple	El sistema asigna un puntaje para clasificar el nivel de alerta.	El score es orientativo y no implica decisión automática.
Dashboard de visualización	Cumple	El proyecto incluye dashboard para visualizar casos, alertas y priorización.	Debe describirse como herramienta de apoyo a la revisión.
Chatbot de consulta	Cumple	El sistema incluye chatbot para consultar información del sistema y casos de siniestros.	Debe estar alineado con el motor IA definido en el README.
Revisión humana obligatoria	Cumple	El README establece que toda alerta requiere validación humana.	Punto clave para evitar interpretación de decisión automática.
No acusación ni decisión automática	Cumple	El sistema genera alertas, pero no acusa ni aprueba/rechaza pagos automáticamente.	Debe reforzarse en matriz, manuales y documentos funcionales.
Uso de datos sintéticos	Cumple	El proyecto trabaja con información sintética para demostración y validación.	Importante para enfoque ético y de privacidad.
3. Cumplimiento técnico
Componente técnico	Estado	Evidencia de cumplimiento	Observación
Backend FastAPI	Cumple	El README define FastAPI como backend principal.	Se debe mantener consistente con documentos técnicos.
Frontend / Dashboard	Cumple	El README presenta una interfaz para visualizar resultados y alertas.	El dashboard debe describirse como componente funcional del sistema.
Base de datos SQLite	Cumple	El sistema utiliza estructura de datos normalizada para siniestros, pólizas, asegurados, documentos, facturas e ítems.	La matriz no debe indicar que estos modelos no existen si el README los reconoce.
Modelo de datos normalizado	Cumple	El README menciona tablas normalizadas para gestionar información del sistema.	Debe alinearse con modelo_datos.md.
Motor de reglas determinísticas	Cumple	El sistema aplica reglas de negocio para detectar señales de alerta.	Debe vincularse con las reglas RF01-RF07 y señales de riesgo.
Motor IA	Cumple	El README define el uso de DeepSeek V4 Flash / OpenCode Go como motor principal.	Otros documentos deben corregirse si mencionan Gemini como motor principal.
Auditoría de facturas PDF	Cumple	El sistema contempla análisis de facturas PDF, incluyendo revisión documental.	Debe mantenerse como parte del sistema de fraude en siniestros, no como único alcance.
Arquitectura documentada	Cumple	Existe documentación de arquitectura en la carpeta docs.	No debe marcarse como “no cumple”.
4. Cumplimiento de reglas de negocio
Regla / Señal	Estado	Evidencia de cumplimiento	Observación
Validación de cobertura y ramo	Cumple	El sistema contempla revisión de coherencia entre siniestro, póliza, cobertura y factura.	Debe estar alineado con reglas_negocio.md.
Validación de vigencia de póliza	Cumple	El sistema permite identificar alertas relacionadas con vigencia o fechas del siniestro.	Debe mantenerse como regla crítica.
Validación de documentación mínima	Cumple	Se contempla revisión de documentos asociados al siniestro.	Aplica para soporte documental y consistencia del caso.
Detección de facturas duplicadas	Cumple	El sistema detecta duplicidad o posibles facturas repetidas.	Debe mantenerse como señal clave de riesgo.
Detección de sobrecostos	Cumple	El sistema identifica posibles valores superiores o incoherentes.	Debe describirse como alerta, no como conclusión definitiva.
Detección de incoherencias	Cumple	El sistema identifica diferencias entre narrativa, documentos, póliza y factura.	Debe enfocarse como apoyo al analista.
Clasificación por criticidad	Cumple	El sistema clasifica los casos mediante score y semáforo.	Verde, Amarillo y Rojo deben usarse de forma uniforme.
5. Cumplimiento de criterios éticos y de gobernanza
Criterio	Estado	Evidencia de cumplimiento	Observación
Revisión humana obligatoria	Cumple	El sistema exige que un analista revise las alertas antes de cualquier decisión.	Punto obligatorio en todos los documentos.
No acusación automática	Cumple	El sistema habla de “alertas” o “posible fraude”, no de fraude confirmado.	Evitar frases como “fraude detectado” o “culpable”.
No decisión automática de pago/rechazo	Cumple	La solución no aprueba ni rechaza pagos automáticamente.	Las acciones finales corresponden al usuario humano autorizado.
Explicabilidad de alertas	Cumple	El sistema presenta razones o señales que justifican el nivel de riesgo.	Debe mantenerse para sustentar el score.
Uso responsable de IA	Cumple	La IA se utiliza como apoyo al análisis y no como autoridad final.	El analista conserva la decisión final.
6. Correcciones aplicadas respecto a versiones anteriores

Se actualiza la matriz de cumplimiento para alinearla con el README oficial del proyecto. En versiones anteriores se indicaba que ciertos componentes estaban pendientes o no existían; sin embargo, el README oficial establece que el sistema ya contempla dichos elementos.

Correcciones principales:

Se cambia el estado de la arquitectura formal a Cumple, debido a que existe documentación de arquitectura dentro de la carpeta docs.
Se actualiza el estado del modelo de datos a Cumple, considerando que el README describe una estructura normalizada con tablas para siniestros, pólizas, asegurados, vehículos, documentos, facturas e ítems.
Se corrige la referencia al motor IA, dejando como oficial el uso de DeepSeek V4 Flash / OpenCode Go, según el README.
Se actualiza el alcance del proyecto para que no sea descrito únicamente como auditor de facturas, sino como detector agéntico de fraude en siniestros.
Se refuerza que el sistema no acusa fraude, no rechaza pagos y no toma decisiones automáticas.
Se mantiene la auditoría de facturas PDF como un componente del sistema, pero no como el alcance completo del proyecto.
Se corrige el estado de cumplimiento de las reglas de negocio y señales de alerta, alineándolas con el enfoque de score, semáforo y revisión humana.
7. Observaciones finales

La matriz actualizada refleja que el proyecto Miraclex cumple con los principales criterios funcionales, técnicos y éticos definidos en el README oficial.

El sistema permite apoyar a una aseguradora en la revisión temprana de siniestros mediante reglas de negocio, análisis de facturas, señales de posible fraude, score de riesgo, semáforo de criticidad, dashboard y chatbot.

Toda alerta generada por el sistema debe interpretarse como una recomendación o señal de revisión, no como una acusación ni como una decisión automática. La decisión final corresponde siempre a un analista humano autorizado.

8. Estado general de cumplimiento

Resultado general: Cumple.

Justificación:
El proyecto implementa una solución integral para apoyar la detección temprana de posibles fraudes en siniestros, combinando reglas determinísticas, análisis asistido por IA, priorización de casos, visualización en dashboard, chatbot de consulta y revisión humana obligatoria.

La matriz queda alineada con el README oficial y corrige inconsistencias presentes en versiones anteriores de la documentación.
